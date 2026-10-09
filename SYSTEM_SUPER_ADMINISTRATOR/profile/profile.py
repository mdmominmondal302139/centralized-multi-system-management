from flask import Blueprint, render_template, request, session, redirect, url_for
from pathlib import Path
import importlib.util

ROLE = "SYSTEM_SUPER_ADMINISTRATOR"
PAGE = "profile"
BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(f"{ROLE}_{PAGE}_services", BASE / "services.py")
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)

bp = Blueprint(
    "system_super_administrator_profile_bp",
    __name__,
    url_prefix="/system_super_administrator/profile",
)

def _context():
    # Preserve the login identity keys that different existing login routes may set.
    # The profile service uses these exact values to locate the signed-in MongoDB user.
    keys = (
        "role", "user_id", "username", "email", "phone", "name",
        "id", "_id", "administrator_id", "member_id", "login_id",
        "account_user_id", "branch_id", "branch_name",
    )
    return {key: session.get(key) for key in keys}

@bp.route("/", methods=["GET", "POST"])
def page():
    if session.get("authenticated") is not True or session.get("role") not in (ROLE, "SYSTEM_SUPER_ADMINISTRATOR"):
        return redirect(url_for("login"))

    message = None
    error = None
    profile = {}

    try:
        if request.method == "POST":
            action = request.form.get("action", "save")

            if action == "delete":
                service.delete_record(_context(), request.form.get("record_id", ""))
                message = "Deleted successfully."

            elif action == "update":
                service.update_record(
                    _context(),
                    request.form.get("record_id", ""),
                    dict(request.form),
                )
                message = "Record updated successfully."

            elif action == "update_profile":
                profile = service.update_profile(_context(), dict(request.form))
                session["username"] = profile.get("username", session.get("username"))
                session["email"] = profile.get("email", session.get("email"))
                session["name"] = profile.get("name", session.get("name"))
                session["phone"] = profile.get("phone", session.get("phone"))
                message = "Profile updated successfully."

            elif action == "change_password":
                service.change_password(
                    _context(),
                    request.form.get("current_password", ""),
                    request.form.get("new_password", ""),
                    request.form.get("confirm_password", ""),
                )
                message = "Password changed successfully."

            else:
                service.create_record(_context(), dict(request.form))
                message = "Saved successfully."

        profile = service.get_current_profile(_context())
        # Keep the generated public Administrator ID available to the session.
        if profile.get("administrator_id"):
            session["administrator_id"] = str(profile["administrator_id"])
        records = service.list_records(_context(), request.args.to_dict())

    except Exception as exc:
        records = []
        error = str(exc)
        if not profile:
            try:
                profile = service.get_current_profile(_context())
            except Exception:
                profile = {}

    return render_template(
        "SYSTEM_SUPER_ADMINISTRATOR/profile/profile.html",
        records=records,
        profile=profile,
        message=message,
        error=error,
        session=session,
    )
