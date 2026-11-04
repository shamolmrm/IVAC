"""Registration, login, sessions, email verification and password reset/change."""

import logging
import secrets
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core import mailer, sms
from app.core.cache import KeyValueStore, get_redis, hit_rate_limit
from app.core.config import get_settings
from app.core.db import as_utc, get_db, utcnow
from app.core.net import client_ip
from app.modules.audit.service import audit
from app.modules.auth.models import TokenPurpose, User, UserToken
from app.modules.auth.security import (
    current_user,
    end_all_sessions,
    end_session,
    hash_password,
    needs_rehash,
    sha256,
    start_session,
    verify_password,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
TOKEN_TTL = {
    TokenPurpose.verify_email: timedelta(days=2),
    TokenPurpose.reset_password: timedelta(hours=1),
}
BAD_LOGIN = "ইমেইল বা পাসওয়ার্ড সঠিক নয়।"
BAD_LINK = "লিংকটি সঠিক নয় অথবা মেয়াদ শেষ হয়ে গেছে।"


# ── Schemas ──


class RegisterIn(BaseModel):
    email: str = Field(max_length=254, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=10, max_length=200)
    full_name: str = Field(min_length=2, max_length=120)


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=200)


class TokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class ForgotIn(BaseModel):
    email: str = Field(max_length=254)


class ResetIn(TokenIn):
    password: str = Field(min_length=10, max_length=200)


class ChangeIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=10, max_length=200)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    email_verified: bool
    phone_verified: bool
    is_superadmin: bool
    created_at: datetime | None


class FeaturesOut(BaseModel):
    email: bool
    sms: bool


def to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        email_verified=user.email_verified_at is not None,
        phone_verified=user.phone_verified_at is not None,
        is_superadmin=user.is_superadmin,
        created_at=user.created_at,
    )


# ── Helpers ──


def _normalise(email: str) -> str:
    return email.strip().lower()


async def _limit(request: Request, store: KeyValueStore, bucket: str) -> None:
    limit = get_settings().auth_rate_limit_per_minute
    if await hit_rate_limit(store, f"rl:{bucket}:{client_ip(request)}", limit):
        raise HTTPException(status_code=429, detail="অনেকবার চেষ্টা হয়েছে। এক মিনিট পরে আবার চেষ্টা করুন।")


def _lock_key(email: str) -> str:
    return f"lock:login:{sha256(email)}"


async def _locked(store: KeyValueStore, email: str) -> bool:
    try:
        count = await store.get(_lock_key(email))
        return int(count or 0) >= get_settings().login_failures_per_email
    except Exception:  # Redis down: fail open, the per-IP limit still applies
        return False


async def _record_failure(store: KeyValueStore, email: str) -> None:
    await hit_rate_limit(store, _lock_key(email), 10**6, get_settings().login_lock_seconds)


async def _clear_failures(store: KeyValueStore, email: str) -> None:
    try:
        await store.set(_lock_key(email), "0", ex=1)
    except Exception:
        pass


def _issue(db: Session, user: User, purpose: TokenPurpose) -> str:
    """One live token per purpose; only its hash is stored."""
    db.execute(delete(UserToken).where(UserToken.user_id == user.id, UserToken.purpose == purpose))
    token = secrets.token_urlsafe(32)
    db.add(
        UserToken(
            id=sha256(token), user_id=user.id, purpose=purpose,
            expires_at=utcnow() + TOKEN_TTL[purpose],
        )
    )
    return token


def _consume(db: Session, token: str, purpose: TokenPurpose) -> User:
    row = db.get(UserToken, sha256(token))
    if (
        row is None
        or row.purpose != purpose
        or row.used_at is not None
        or as_utc(row.expires_at) < utcnow()
    ):
        raise HTTPException(status_code=400, detail=BAD_LINK)
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail=BAD_LINK)
    row.used_at = utcnow()
    return user


def _require_email() -> None:
    if not mailer.email_enabled():
        raise HTTPException(status_code=503, detail="ইমেইল সেবা এখনো চালু হয়নি।")


def send_verification(db: Session, user: User) -> None:
    """Issue a verification token and email it. Commits the token first."""
    s = get_settings()
    token = _issue(db, user, TokenPurpose.verify_email)
    db.commit()
    link = f"{s.public_url}/verify-email?token={token}"
    mailer.send_email(
        user.email,
        f"{s.brand_name}: আপনার ইমেইল নিশ্চিত করুন",
        f"প্রিয় {user.full_name},\n\nআপনার ইমেইল নিশ্চিত করতে এই লিংকে যান:\n{link}\n\n"
        "লিংকটি ২ দিন বৈধ থাকবে। আপনি অ্যাকাউন্ট না খুলে থাকলে এই ইমেইলটি উপেক্ষা করুন।\n",
    )


# ── Endpoints ──


@router.get("/features", response_model=FeaturesOut)
def features() -> FeaturesOut:
    return FeaturesOut(email=mailer.email_enabled(), sms=sms.sms_enabled())


@router.post("/register", response_model=UserOut, status_code=201)
async def register(
    body: RegisterIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    store: KeyValueStore = Depends(get_redis),
) -> UserOut:
    await _limit(request, store, "auth")
    email = _normalise(body.email)
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail="এই ইমেইল দিয়ে আগেই একটি অ্যাকাউন্ট আছে।")
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.full_name.strip(),
        last_login_at=utcnow(),
    )
    db.add(user)
    db.flush()
    start_session(db, user, request, response)
    audit(db, "user.register", actor_id=user.id, target_type="user", target_id=user.id,
          request=request)
    db.commit()
    if mailer.email_enabled():
        try:
            send_verification(db, user)
        except Exception as exc:  # registration must not fail because of email
            log.error("verification email failed: %s", exc)
    return to_out(user)


@router.post("/login", response_model=UserOut)
async def login(
    body: LoginIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    store: KeyValueStore = Depends(get_redis),
) -> UserOut:
    await _limit(request, store, "auth")
    email = _normalise(body.email)
    if await _locked(store, email):
        raise HTTPException(
            status_code=429, detail="অনেকবার ভুল পাসওয়ার্ড দেওয়া হয়েছে। ১৫ মিনিট পরে আবার চেষ্টা করুন।"
        )
    user = db.scalar(select(User).where(User.email == email))
    if not verify_password(user.password_hash if user else None, body.password) or not user:
        await _record_failure(store, email)
        if user:
            audit(db, "user.login_failed", actor_id=user.id, target_type="user",
                  target_id=user.id, request=request)
            db.commit()
        raise HTTPException(status_code=401, detail=BAD_LOGIN)
    if not user.is_active:
        raise HTTPException(status_code=403, detail="এই অ্যাকাউন্টটি বন্ধ করা আছে।")
    await _clear_failures(store, email)
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
    user.last_login_at = utcnow()
    start_session(db, user, request, response)
    audit(db, "user.login", actor_id=user.id, target_type="user", target_id=user.id,
          request=request)
    db.commit()
    return to_out(user)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> Response:
    end_session(db, request, response)
    db.commit()
    response.status_code = 204
    return response


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> UserOut:
    return to_out(user)


@router.post("/verify/request", status_code=202)
async def request_verification(
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    store: KeyValueStore = Depends(get_redis),
) -> dict[str, str]:
    _require_email()
    await _limit(request, store, "verify")
    if user.email_verified_at:
        return {"status": "already_verified"}
    try:
        send_verification(db, user)
    except Exception as exc:
        log.error("verification email failed: %s", exc)
        raise HTTPException(status_code=502, detail="ইমেইল পাঠানো যায়নি। পরে চেষ্টা করুন।") from exc
    return {"status": "sent"}


@router.post("/verify/confirm")
def confirm_verification(
    body: TokenIn, request: Request, db: Session = Depends(get_db)
) -> dict[str, str]:
    user = _consume(db, body.token, TokenPurpose.verify_email)
    user.email_verified_at = user.email_verified_at or utcnow()
    audit(db, "user.email_verified", actor_id=user.id, target_type="user", target_id=user.id,
          request=request)
    db.commit()
    return {"status": "verified"}


@router.post("/password/forgot", status_code=202)
async def forgot_password(
    body: ForgotIn,
    request: Request,
    db: Session = Depends(get_db),
    store: KeyValueStore = Depends(get_redis),
) -> dict[str, str]:
    """Always answers the same way, whether or not the email exists."""
    _require_email()
    await _limit(request, store, "forgot")
    s = get_settings()
    user = db.scalar(select(User).where(User.email == _normalise(body.email)))
    if user and user.is_active:
        token = _issue(db, user, TokenPurpose.reset_password)
        db.commit()
        link = f"{s.public_url}/reset-password?token={token}"
        try:
            mailer.send_email(
                user.email,
                f"{s.brand_name}: পাসওয়ার্ড রিসেট",
                f"প্রিয় {user.full_name},\n\nনতুন পাসওয়ার্ড দিতে এই লিংকে যান:\n{link}\n\n"
                "লিংকটি ১ ঘণ্টা বৈধ থাকবে। আপনি অনুরোধ না করে থাকলে এই ইমেইলটি উপেক্ষা করুন; "
                "আপনার পাসওয়ার্ড বদলাবে না।\n",
            )
        except Exception as exc:
            log.error("reset email failed: %s", exc)
    return {"status": "অ্যাকাউন্ট থাকলে ওই ইমেইলে রিসেট লিংক পাঠানো হয়েছে।"}


@router.post("/password/reset")
def reset_password(
    body: ResetIn, request: Request, response: Response, db: Session = Depends(get_db)
) -> dict[str, str]:
    user = _consume(db, body.token, TokenPurpose.reset_password)
    user.password_hash = hash_password(body.password)
    user.email_verified_at = user.email_verified_at or utcnow()  # they proved mailbox access
    end_all_sessions(db, user)
    start_session(db, user, request, response)
    audit(db, "user.password_reset", actor_id=user.id, target_type="user", target_id=user.id,
          request=request)
    db.commit()
    return {"status": "reset"}


@router.post("/password/change")
async def change_password(
    body: ChangeIn,
    request: Request,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    store: KeyValueStore = Depends(get_redis),
) -> dict[str, str]:
    await _limit(request, store, "change")
    if not verify_password(user.password_hash, body.current_password):
        raise HTTPException(status_code=400, detail="বর্তমান পাসওয়ার্ড সঠিক নয়।")
    user.password_hash = hash_password(body.new_password)
    end_all_sessions(db, user)  # sign out every other device
    start_session(db, user, request, response)
    audit(db, "user.password_change", actor_id=user.id, target_type="user", target_id=user.id,
          request=request)
    db.commit()
    return {"status": "changed"}
