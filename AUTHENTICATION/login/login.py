from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
from pathlib import Path
import importlib.util

BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("login_services", BASE / "services.py")
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)

bp = Blueprint("login_page", __name__)

HOME_BY_ROLE = {
    "SYSTEM_SUPER_ADMINISTRATOR": "/system_super_administrator",
    "BRANCH_OFFICER": "/branch_officer/home",
    "ACCOUNT_OFFICER": "/account_officer/home",
    "MEAL_MANAGER": "/meal_manager/home",
    "OPERATOR": "/operator/dashboard",
    "MEMBER": "/member/home",
    "BLOOD_DONOR": "/system_super_administrator/blood-donor-account",
}

ROLE_LABELS = {
    "SYSTEM_SUPER_ADMINISTRATOR": "System Super Administrator",
    "BRANCH_OFFICER": "Branch Officer",
    "ACCOUNT_OFFICER": "Account Officer",
    "MEAL_MANAGER": "Meal Manager",
    "OPERATOR": "Operator",
    "MEMBER": "Member",
    "BLOOD_DONOR": "Blood Donor",
}


def _is_ajax_login():
    return request.headers.get("X-Login-Flow") == "account-verification"


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        try:
            # Role is intentionally not submitted by the user. Authentication
            # automatically determines the role from the existing account.
            row = service.authenticate(username, password, "")
            if not row:
                error = "Invalid username or password!"
                if _is_ajax_login():
                    return jsonify({"ok": False, "error": error}), 401
            else:
                role = str(row.get("role") or "MEMBER").upper()
                session.clear()
                session.update({
                    "authenticated": True,
                    "user_id": str(row.get("_id") or row.get("id") or row.get("user_id") or ""),
                    "username": row.get("username", ""),
                    "role": role,
                    "branch_id": row.get("branch_id", row.get("branch", "")),
                    "branch_name": row.get("branch_name", ""),
                })
                home = HOME_BY_ROLE.get(role, "/")
                if _is_ajax_login():
                    return jsonify({
                        "ok": True,
                        "redirect": home,
                        "role": ROLE_LABELS.get(role, role.replace("_", " ").title()),
                    })
                return redirect(home)
        except Exception as exc:
            # Keep the real exception in the terminal for diagnosis instead of
            # silently converting every infrastructure error into a bad password.
            print(f"[LOGIN ERROR] {type(exc).__name__}: {exc}")
            error = "Login service is temporarily unavailable. Please try again."
            if _is_ajax_login():
                return jsonify({"ok": False, "error": error}), 500
    return render_template("AUTHENTICATION/login/login.html", error=error)
