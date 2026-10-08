from flask import Blueprint, render_template, request, session, redirect, url_for
from pathlib import Path
import importlib.util
import secrets

ROLE = "SYSTEM_SUPER_ADMINISTRATOR"
PAGE = "access_management"
BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(f"{ROLE}_{PAGE}_services", BASE / "services.py")
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)
bp = Blueprint("system_super_administrator_access_management_bp", __name__, url_prefix="/system_super_administrator/access-management")


def _context():
    return {
        "role": session.get("role"), "user_id": session.get("user_id"),
        "username": session.get("username") or session.get("name") or "",
        "branch_id": session.get("branch_id"), "branch_name": session.get("branch_name")
    }


def _csrf():
    token = session.get("access_management_csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["access_management_csrf"] = token
    return token


def _check_csrf():
    return secrets.compare_digest(str(request.form.get("csrf_token", "")), str(session.get("access_management_csrf", "")))


@bp.route("/", methods=["GET", "POST"])
def page():
    if session.get("authenticated") is not True or session.get("role") != ROLE:
        return redirect(url_for("login"))

    context = _context()
    section = request.args.get("section", "dashboard")
    valid_sections = {x[0] for x in service.SECTIONS}
    if section not in valid_sections:
        section = "dashboard"
    message = None
    error = None

    try:
        service.seed_defaults(context)
        if request.method == "POST":
            if not _check_csrf():
                raise PermissionError("Security token expired. Please reload the page and try again.")
            action = request.form.get("action", "create")
            target = request.form.get("section", section)
            if action == "create":
                service.create_record(context, target, request.form)
                message = f"{dict(service.SECTIONS).get(target, target)} saved successfully."
            elif action == "update":
                service.update_record(context, target, request.form.get("record_id", ""), request.form)
                message = "Record updated successfully."
            elif action == "delete":
                service.delete_record(context, target, request.form.get("record_id", ""))
                message = "Record deleted successfully."
            section = target
    except Exception as exc:
        error = str(exc)

    try:
        data = service.dashboard(context)
        rows = [] if section == "dashboard" else service.list_records(context, section, request.args.to_dict())
        user_rows = service.users(context)
        role_options = service.role_options(context)
    except Exception as exc:
        data = {"counts": {}, "active_roles": 0, "active_permissions": 0, "pending_requests": 0, "temporary": 0, "blocked": 0}
        rows = []
        user_rows = []
        role_options = [dict(x) for x in getattr(service, "DEFAULT_ROLES", [])]
        error = error or str(exc)

    return render_template(
        "SYSTEM_SUPER_ADMINISTRATOR/access_management/access_management.html",
        sections=service.SECTIONS, section=section, records=rows, dashboard=data,
        users=user_rows, role_options=role_options, message=message, error=error, csrf_token=_csrf(), session=session
    )
