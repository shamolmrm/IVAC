"""Mobile number verification by SMS one-time code."""

import hmac
import logging
import re
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core import sms
from app.core.config import get_settings
from app.core.db import as_utc, get_db, utcnow
from app.modules.audit.service import audit
from app.modules.auth.models import PhoneOtp, User
from app.modules.auth.router import UserOut, to_out
from app.modules.auth.security import current_user, sha256

log = logging.getLogger(__name__)
router = APIRouter(prefix="/auth/phone", tags=["auth"])

BD_MOBILE = re.compile(r"^01[3-9]\d{8}$")
BAD_CODE = "কোডটি সঠিক নয় অথবা মেয়াদ শেষ। নতুন কোড নিন।"


class PhoneIn(BaseModel):
    phone: str = Field(min_length=10, max_length=20)


class CodeIn(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


def normalise_phone(raw: str) -> str | None:
    """Bangladeshi mobile number in any common form -> +8801XXXXXXXXX, else None."""
    digits = re.sub(r"[\s\-()]", "", raw)
    if digits.startswith("+"):
        digits = digits[1:]
    if digits.startswith("880"):
        digits = digits[2:]
    return f"+88{digits}" if BD_MOBILE.match(digits) else None


def _code_hash(otp_id: str, code: str) -> str:
    return sha256(f"{otp_id}:{code}")


@router.post("/request", status_code=202)
def request_code(
    body: PhoneIn,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    s = get_settings()
    if not sms.sms_enabled():
        raise HTTPException(status_code=503, detail="SMS সেবা এখনো চালু হয়নি।")
    phone = normalise_phone(body.phone)
    if phone is None:
        raise HTTPException(status_code=422, detail="সঠিক বাংলাদেশি মোবাইল নম্বর দিন (01XXXXXXXXX)।")
    if user.phone == phone and user.phone_verified_at:
        return {"status": "already_verified"}
    taken = db.scalar(select(User.id).where(User.phone == phone, User.id != user.id))
    if taken:
        raise HTTPException(status_code=409, detail="এই নম্বরটি অন্য একটি অ্যাকাউন্টে যুক্ত আছে।")

    now = utcnow()
    last = db.scalar(
        select(PhoneOtp).where(PhoneOtp.user_id == user.id).order_by(PhoneOtp.created_at.desc())
    )
    if last and as_utc(last.created_at) > now - timedelta(seconds=s.otp_resend_seconds):
        raise HTTPException(status_code=429, detail="এক মিনিট পরে আবার কোড চাইতে পারবেন।")
    recent = db.scalar(
        select(func.count(PhoneOtp.id)).where(
            PhoneOtp.user_id == user.id, PhoneOtp.created_at > now - timedelta(hours=1)
        )
    )
    if (recent or 0) >= s.otp_per_hour:
        raise HTTPException(status_code=429, detail="এক ঘণ্টায় অনেকবার কোড চাওয়া হয়েছে। পরে চেষ্টা করুন।")

    # only one live code per user
    db.execute(
        update(PhoneOtp)
        .where(PhoneOtp.user_id == user.id, PhoneOtp.used_at.is_(None))
        .values(used_at=now)
    )
    code = f"{secrets.randbelow(10**6):06d}"
    otp = PhoneOtp(user_id=user.id, phone=phone, code_hash="", expires_at=now)
    db.add(otp)
    db.flush()
    otp.code_hash = _code_hash(str(otp.id), code)
    otp.expires_at = now + timedelta(seconds=s.otp_ttl_seconds)
    otp.created_at = now
    try:
        sms.send_sms(
            phone,
            f"{s.brand_name} যাচাই কোড: {code}। {s.otp_ttl_seconds // 60} মিনিট বৈধ। কাউকে বলবেন না।",
        )
    except Exception as exc:
        db.rollback()
        log.error("OTP SMS failed: %s", exc)
        raise HTTPException(status_code=502, detail="SMS পাঠানো যায়নি। পরে চেষ্টা করুন।") from exc
    audit(db, "user.phone_otp_sent", actor_id=user.id, target_type="user", target_id=user.id,
          detail={"phone": phone[:-4] + "****"}, request=request)
    db.commit()
    return {"status": "sent", "phone": phone, "expires_in": s.otp_ttl_seconds}


@router.post("/verify", response_model=UserOut)
def verify_code(
    body: CodeIn,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    s = get_settings()
    otp = db.scalar(
        select(PhoneOtp)
        .where(PhoneOtp.user_id == user.id, PhoneOtp.used_at.is_(None))
        .order_by(PhoneOtp.created_at.desc())
    )
    if otp is None or as_utc(otp.expires_at) < utcnow() or otp.attempts >= s.otp_max_attempts:
        raise HTTPException(status_code=400, detail=BAD_CODE)
    otp.attempts += 1
    if not hmac.compare_digest(otp.code_hash, _code_hash(str(otp.id), body.code)):
        if otp.attempts >= s.otp_max_attempts:
            otp.used_at = utcnow()  # burn it
        db.commit()
        raise HTTPException(status_code=400, detail="কোডটি সঠিক নয়।")
    if db.scalar(select(User.id).where(User.phone == otp.phone, User.id != user.id)):
        otp.used_at = utcnow()
        db.commit()
        raise HTTPException(status_code=409, detail="এই নম্বরটি অন্য একটি অ্যাকাউন্টে যুক্ত আছে।")
    otp.used_at = utcnow()
    user.phone = otp.phone
    user.phone_verified_at = utcnow()
    audit(db, "user.phone_verified", actor_id=user.id, target_type="user", target_id=user.id,
          detail={"phone": otp.phone[:-4] + "****"}, request=request)
    db.commit()
    return to_out(user)
