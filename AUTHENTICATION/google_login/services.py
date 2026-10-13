"""Google OAuth account lookup helpers."""
from AUTHENTICATION.account_store import find_active_account_by_email

def find_active_user_by_verified_email(email: str):
    return find_active_account_by_email(email)
