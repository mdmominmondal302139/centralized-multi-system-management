from flask import Blueprint, render_template, request, session, redirect, jsonify
from pathlib import Path
import importlib.util

BASE = Path(__file__).resolve().parent
SERVICE_PATH = BASE / "services.py"

spec = importlib.util.spec_from_file_location("login_services", SERVICE_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load login services from: {SERVICE_PATH}")

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


def _first_value(row, *keys, default=""):
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return value
    return default


def _session_text(row, *keys):
    value = _first_value(row, *keys, default="")
    return str(value) if value is not None else ""


def _build_login_session(row, role, submitted_username):
    """
    Keep MongoDB _id separate from the account's business user_id.
    Profile lookup in this project needs the MongoDB _id in session['user_id'].
    The original UUID/business user_id is preserved in account_user_id.
    """
    mongo_id = _session_text(row, "_id", "id")
    business_user_id = _session_text(row, "user_id", "account_user_id")
    username = _session_text(
        row, "username", "user_name", "login_username", "login", "user"
    ) or submitted_username

    return {
        "authenticated": True,
        "user_id": mongo_id or business_user_id,
        "_id": mongo_id,
        "id": mongo_id,
        "account_user_id": business_user_id,
        "username": username,
        "email": _session_text(row, "email"),
        "phone": _session_text(row, "phone", "mobile", "phone_number"),
        "name": _session_text(
            row, "name", "full_name", "fullName", "display_name"
        ),
        "administrator_id": _session_text(row, "administrator_id"),
        "member_id": _session_text(row, "member_id"),
        "login_id": _session_text(row, "login_id"),
        "role": role,
        "branch_id": _session_text(row, "branch_id", "branch", "branch_name"),
        "branch_name": _session_text(row, "branch_name", "branch"),
    }


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            error = "Please enter your username and password."
            if _is_ajax_login():
                return jsonify({"ok": False, "error": error}), 400
            return render_template("AUTHENTICATION/login/login.html", error=error)

        try:
            # Role is determined from the saved account, not from the form.
            row = service.authenticate(username, password, "")

            if not row:
                error = "Invalid username or password!"
                if _is_ajax_login():
                    return jsonify({"ok": False, "error": error}), 401
            else:
                role = str(row.get("role") or "MEMBER").strip().upper()
                session.clear()
                session.update(_build_login_session(row, role, username))

                home = HOME_BY_ROLE.get(role, "/")
                if _is_ajax_login():
                    return jsonify({
                        "ok": True,
                        "redirect": home,
                        "role": ROLE_LABELS.get(
                            role, role.replace("_", " ").title()
                        ),
                    })
                return redirect(home)

        except Exception as exc:
            print(f"[LOGIN ERROR] {type(exc).__name__}: {exc}")
            error = "Login service is temporarily unavailable. Please try again."
            if _is_ajax_login():
                return jsonify({"ok": False, "error": error}), 500

    return render_template("AUTHENTICATION/login/login.html", error=error)
