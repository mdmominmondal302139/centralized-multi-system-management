"""Business logic for secure password reset."""
import os
import secrets
from datetime import datetime, timedelta, timezone
from flask import current_app, url_for
from werkzeug.security import generate_password_hash
from AUTHENTICATION.account_store import get_db, find_active_account_by_email

TOKEN_TTL_MINUTES = 20

def request_reset(email: str):
    """Return a reset token for an existing active user; caller must avoid account enumeration."""
    db = get_db()
    user = find_active_account_by_email(email)
    if not user:
        return None
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    db.password_reset_tokens.insert_one({
        "user_id": user["_id"],
        "collection": user.get("_auth_collection", "users"),
        "token_hash": __import__("hashlib").sha256(token.encode()).hexdigest(),
        "created_at": now,
        "expires_at": now + timedelta(minutes=TOKEN_TTL_MINUTES),
        "used": False,
    })
    reset_url = url_for("forgot_password.reset_password_page", token=token, _external=True)
    send_reset_email(email.strip().lower(), reset_url)
    return True

def send_reset_email(email: str, reset_url: str):
    """Send reset email over configured SMTP. Raises a safe configuration error if not configured."""
    import smtplib
    from email.message import EmailMessage
    host = os.getenv("SMTP_HOST")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("MAIL_FROM", username or "")
    if not host or not sender or not username or not password:
        current_app.logger.error("Password reset email requested but SMTP is not configured.")
        raise RuntimeError("Password reset email service is not configured.")
    msg = EmailMessage()
    msg["Subject"] = "Password reset request"
    msg["From"] = sender
    msg["To"] = email
    msg.set_content(f"Use this link within {TOKEN_TTL_MINUTES} minutes to reset your password:\n{reset_url}\n\nIf you did not request this, ignore this email.")
    port = int(os.getenv("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=15) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(msg)

def reset_password(token: str, new_password: str) -> bool:
    import hashlib
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    db = get_db()
    now = datetime.now(timezone.utc)
    record = db.password_reset_tokens.find_one({"token_hash": token_hash, "used": False, "expires_at": {"$gt": now}})
    if not record:
        return False
    collection_name = record.get("collection", "users")
    result = db[collection_name].update_one({"_id": record["user_id"]}, {"$set": {"password_hash": generate_password_hash(new_password), "password_updated_at": now}})
    if result.modified_count != 1:
        return False
    db.password_reset_tokens.update_one({"_id": record["_id"], "used": False}, {"$set": {"used": True, "used_at": now}})
    return True
