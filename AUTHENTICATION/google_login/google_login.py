import os
from flask import Blueprint, current_app, flash, redirect, render_template, session, url_for
from authlib.integrations.flask_client import OAuth
from . import services
from AUTHENTICATION.login.login import HOME_BY_ROLE, ROLE_LABELS

google_login_bp = Blueprint("google_login", __name__, url_prefix="/login", template_folder=".")

def _google_client():
    oauth = current_app.extensions.get("authentication_oauth")
    if oauth is None:
        oauth = OAuth(current_app)
        oauth.register(
            name="google",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
        current_app.extensions["authentication_oauth"] = oauth
    if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_CLIENT_SECRET"):
        raise RuntimeError("Google OAuth is not configured.")
    return oauth.google

@google_login_bp.get("/google")
def google_login():
    try:
        client = _google_client()
    except RuntimeError:
        return render_template("google_login.html", configured=False), 503
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI") or url_for("google_login.google_callback", _external=True)
    return client.authorize_redirect(redirect_uri)

@google_login_bp.get("/google/callback")
def google_callback():
    try:
        client = _google_client()
        token = client.authorize_access_token()
        info = token.get("userinfo") or client.userinfo()
        if not info or str(info.get("email_verified", "")).lower() not in {"true", "1"} or not info.get("email"):
            flash("Google could not verify this email address.", "error")
            return redirect("/login")
        user = services.find_active_user_by_verified_email(info["email"])
        if not user:
            flash("No active account is linked to this Google email. Please contact your administrator.", "error")
            return redirect("/login")
        session.clear()
        session["authenticated"] = True
        session["user_id"] = str(user["_id"])
        session["_id"] = str(user["_id"])
        session["username"] = user.get("username") or user.get("user_name") or user.get("email", "")
        session["email"] = user.get("email", "")
        session["role"] = str(user.get("role") or user.get("power") or user.get("user_role") or "MEMBER").strip().upper()
        if user.get("branch_id") is not None:
            session["branch_id"] = str(user["branch_id"])
        session.permanent = True
        # Replace this generic destination with the app's existing role-aware redirect helper.
        return redirect(HOME_BY_ROLE.get(session["role"], "/member/home"))
    except Exception:
        current_app.logger.exception("Google sign-in failed")
        flash("Google sign-in failed. Please try again.", "error")
        return redirect("/login")
