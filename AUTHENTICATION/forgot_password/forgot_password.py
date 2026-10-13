from flask import Blueprint, flash, redirect, render_template, request, url_for
from . import services

forgot_password_bp = Blueprint("forgot_password", __name__, url_prefix="/login", template_folder=".")

@forgot_password_bp.get("/forgot-password")
def forgot_password():
    return render_template("forgot_password.html", page="request")

@forgot_password_bp.post("/forgot-password")
def send_reset_link():
    email = request.form.get("email", "").strip().lower()
    if not email or "@" not in email or len(email) > 254:
        flash("Please enter a valid email address.", "error")
        return redirect(url_for("forgot_password.forgot_password"))
    try:
        services.request_reset(email)
    except RuntimeError:
        flash("Password reset is temporarily unavailable. Please contact support.", "error")
        return redirect(url_for("forgot_password.forgot_password"))
    flash("If an active account matches that email, a reset link will be sent.", "success")
    return redirect(url_for("forgot_password.forgot_password"))

@forgot_password_bp.get("/forgot-password/reset/<token>")
def reset_password_page(token):
    return render_template("forgot_password.html", page="reset", token=token)

@forgot_password_bp.post("/forgot-password/reset/<token>")
def save_new_password(token):
    password = request.form.get("password", "")
    confirm = request.form.get("confirm_password", "")
    if len(password) < 10 or password != confirm:
        flash("Use at least 10 characters and make sure both passwords match.", "error")
        return redirect(url_for("forgot_password.reset_password_page", token=token))
    if not services.reset_password(token, password):
        flash("This reset link is invalid, expired, or already used.", "error")
        return redirect(url_for("forgot_password.forgot_password"))
    flash("Password updated. You can now sign in.", "success")
    return redirect("/login")
