"""Mobile OTP generation, verification, and SMS-provider hook."""
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from flask import current_app
from AUTHENTICATION.account_store import get_db, find_active_account_by_mobile

OTP_TTL_MINUTES = 5
MAX_ATTEMPTS = 5

def normalize_mobile(value: str) -> str:
    # Use E.164 format (e.g. +8801XXXXXXXXX) in the database.
    return "".join(ch for ch in value.strip() if ch.isdigit() or ch == "+")

def issue_otp(mobile: str):
    mobile = normalize_mobile(mobile)
    if len(mobile) < 10 or len(mobile) > 16:
        raise ValueError("Enter a valid mobile number with country code.")
    user = find_active_account_by_mobile(mobile)
    if not user:
        # Caller should show the same generic message whether or not account exists.
        return False
    otp = f"{secrets.randbelow(1_000_000):06d}"
    now = datetime.now(timezone.utc)
    get_db().mobile_login_otps.insert_one({
        "user_id": user["_id"], "collection": user.get("_auth_collection", "users"), "mobile": mobile,
        "otp_hash": hashlib.sha256(otp.encode()).hexdigest(),
        "created_at": now, "expires_at": now + timedelta(minutes=OTP_TTL_MINUTES),
        "attempts": 0, "used": False,
    })
    send_sms(mobile, f"Your login code is {otp}. It expires in {OTP_TTL_MINUTES} minutes.")
    return True

def send_sms(mobile: str, message: str):
    """Integrate your chosen SMS gateway here; refuses to pretend SMS was sent."""
    provider_url = os.getenv("SMS_PROVIDER_URL")
    provider_token = os.getenv("SMS_PROVIDER_TOKEN")
    if not provider_url or not provider_token:
        current_app.logger.error("Mobile OTP requested but SMS provider is not configured.")
        raise RuntimeError("SMS provider is not configured.")
    # Provider APIs differ. Implement the authenticated HTTP request for your selected vendor here.
    raise RuntimeError("SMS provider adapter is not implemented; configure your provider-specific API request.")

def verify_otp(mobile: str, otp: str):
    mobile = normalize_mobile(mobile)
    if len(otp) != 6 or not otp.isdigit():
        return None
    db = get_db()
    now = datetime.now(timezone.utc)
    record = db.mobile_login_otps.find_one({"mobile": mobile, "used": False, "expires_at": {"$gt": now}, "attempts": {"$lt": MAX_ATTEMPTS}}, sort=[("created_at", -1)])
    if not record:
        return None
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()
    if not secrets.compare_digest(otp_hash, record["otp_hash"]):
        db.mobile_login_otps.update_one({"_id": record["_id"]}, {"$inc": {"attempts": 1}})
        return None
    db.mobile_login_otps.update_one({"_id": record["_id"], "used": False}, {"$set": {"used": True, "used_at": now}})
    return db[record.get("collection", "users")].find_one({"_id": record["user_id"]})
