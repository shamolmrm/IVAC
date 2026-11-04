import hashlib
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import as_utc, get_db, utcnow
from app.core.net import client_ip
from app.modules.auth.models import AuthSession, User

_hasher = PasswordHasher()
# Keeps login timing equal when the email does not exist.
_DUMMY_HASH = _hasher.hash("ivac-timing-equaliser")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def sha256(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(db: Session, user: User, request: Request, response: Response) -> None:
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            id=sha256(token),
            user_id=user.id,
            expires_at=utcnow() + timedelta(days=settings.session_ttl_days),
            ip=client_ip(request),
            user_agent=(request.headers.get("user-agent") or "")[:255],
        )
    )
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=settings.session_ttl_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def end_session(db: Session, request: Request, response: Response) -> None:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        session = db.get(AuthSession, sha256(token))
        if session:
            db.delete(session)
    response.delete_cookie(settings.session_cookie_name, path="/")


def end_all_sessions(db: Session, user: User) -> None:
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))


# ── FastAPI dependencies ──


def current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        return None
    session = db.get(AuthSession, sha256(token))
    if not session or as_utc(session.expires_at) < utcnow():
        return None
    user = db.get(User, session.user_id)
    return user if user and user.is_active else None


def current_user(user: User | None = Depends(current_user_optional)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="অনুগ্রহ করে লগইন করুন।")
    return user


def verified_user(user: User = Depends(current_user)) -> User:
    """For actions that need a confirmed email (document upload, applications, payments)."""
    if user.email_verified_at is None:
        raise HTTPException(status_code=403, detail="আগে আপনার ইমেইল যাচাই করুন।")
    return user


def superadmin(user: User = Depends(current_user)) -> User:
    if not user.is_superadmin:
        raise HTTPException(status_code=403, detail="এই কাজের অনুমতি আপনার নেই।")
    return user
