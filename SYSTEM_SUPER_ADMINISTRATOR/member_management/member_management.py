from flask import Blueprint, render_template, request, session, redirect, url_for
from pathlib import Path
import importlib.util

ROLE = "SYSTEM_SUPER_ADMINISTRATOR"
PAGE = "member_management"
BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(f"{ROLE}_{PAGE}_services", BASE / "services.py")
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)

bp = Blueprint(
    "system_super_administrator_member_management_bp",
    __name__,
    url_prefix="/system_super_administrator/member-management",
)


def _context():
    return {
        "role": session.get("role"),
        "user_id": session.get("user_id"),
        "username": session.get("username"),
        "branch_id": session.get("branch_id"),
        "branch_name": session.get("branch_name"),
    }


def _authorized():
    return session.get("authenticated") is True and session.get("role") == ROLE


@bp.route("/", methods=["GET", "POST"], strict_slashes=False)
def page():
    if not _authorized():
        return redirect(url_for("login"))

    message = None
    error = None
    try:
        if request.method == "POST":
            action = request.form.get("action", "").strip()
            record_id = request.form.get("record_id", "").strip()
            if action == "delete":
                service.delete_record(_context(), record_id)
                message = "Account permanently deleted."
            elif action == "deactivate":
                service.deactivate_record(_context(), record_id)
                message = "Account marked Inactive."
            elif action == "activate":
                service.activate_record(_context(), record_id)
                message = "Account marked Active."
            elif action == "update":
                service.update_record(_context(), record_id, request.form)
                message = "Account updated successfully."
            else:
                raise ValueError("Unsupported action.")

        service.ensure_member_ids(_context())
        branches = service.list_branches(_context())
        filters = {
            "branch": request.args.get("branch", "").strip(),
            "search": request.args.get("search", "").strip(),
            "role": request.args.get("role", "").strip(),
            "status": request.args.get("status", "").strip(),
        }
        records = service.list_records(_context(), filters) if filters["branch"] else []
        edit_id = request.args.get("edit", "").strip()
        edit_record = service.get_record(_context(), edit_id) if edit_id else None
        view_id = request.args.get("view", "").strip()
        view_record = service.get_record(_context(), view_id) if view_id else None
    except Exception as exc:
        branches = locals().get("branches", [])
        filters = locals().get("filters", {
            "branch": request.args.get("branch", "").strip(),
            "search": request.args.get("search", "").strip(),
            "role": request.args.get("role", "").strip(),
            "status": request.args.get("status", "").strip(),
        })
        records = locals().get("records", [])
        edit_record = locals().get("edit_record")
        view_record = locals().get("view_record")
        error = str(exc)

    roles = [
        "SYSTEM_SUPER_ADMINISTRATOR", "DISTRICT_DIRECTORY", "BRANCH_OFFICER",
        "ACCOUNT_OFFICER", "MEAL_MANAGER", "BLOOD_DONOR", "OPERATOR", "MEMBER",
    ]
    statuses = ["Active", "Inactive", "Suspended"]
    return render_template(
        "SYSTEM_SUPER_ADMINISTRATOR/member_management/member_management.html",
        records=records,
        branches=branches,
        filters=filters,
        edit_record=edit_record,
        view_record=view_record,
        roles=roles,
        statuses=statuses,
        message=message,
        error=error,
        session=session,
    )
