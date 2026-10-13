from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from . import services
from AUTHENTICATION.login.login import HOME_BY_ROLE

mobile_login_bp = Blueprint("mobile_login", __name__, url_prefix="/login", template_folder=".")

@mobile_login_bp.route("/mobile", methods=["GET", "POST"])
def mobile_login():
    if request.method == "GET":
        return render_template("mobile_login.html", step="request")
    mobile = request.form.get("mobile", "").strip()
    try:
        sent = services.issue_otp(mobile)
        if sent:
            session["mobile_otp_target"] = services.normalize_mobile(mobile)
            flash("If the number belongs to an active account, a login code will be sent.", "success")
            return render_template("mobile_login.html", step="verify", mobile=session["mobile_otp_target"])
        flash("If the number belongs to an active account, a login code will be sent.", "success")
        return render_template("mobile_login.html", step="request")
    except (ValueError, RuntimeError) as exc:
        current_app.logger.warning("Mobile OTP request unavailable: %s", exc)
        flash("Mobile verification is not available yet. Please contact support.", "error")
        return render_template("mobile_login.html", step="request"), 503

@mobile_login_bp.post("/mobile/verify")
def verify_mobile_login():
    mobile = session.get("mobile_otp_target", "")
    otp = request.form.get("otp", "").strip()
    user = services.verify_otp(mobile, otp) if mobile else None
    if not user:
        flash("The code is invalid, expired, or has reached its attempt limit.", "error")
        return render_template("mobile_login.html", step="verify", mobile=mobile), 400
    session.clear()
    session["authenticated"] = True
    session["user_id"] = str(user["_id"])
    session["_id"] = str(user["_id"])
    session["username"] = user.get("username") or user.get("user_name") or user.get("mobile", mobile)
    session["role"] = str(user.get("role") or user.get("power") or user.get("user_role") or "MEMBER").strip().upper()
    if user.get("branch_id") is not None:
        session["branch_id"] = str(user["branch_id"])
    session.permanent = True
    # Replace this generic destination with the app's existing role-aware redirect helper.
    return redirect(HOME_BY_ROLE.get(session["role"], "/member/home"))
