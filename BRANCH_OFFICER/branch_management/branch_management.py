from __future__ import annotations

import importlib.util
from pathlib import Path

from flask import Blueprint, redirect, render_template, request, session, url_for

ROLE = "BRANCH_OFFICER"
HTML_DIR = Path(__file__).resolve().parent
SERVICE_FILE = HTML_DIR / "services.py"

_spec = importlib.util.spec_from_file_location("branch_officer_branch_services", SERVICE_FILE)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load branch management services from {SERVICE_FILE}")
service = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(service)

bp = Blueprint(
    "branch_officer_branch_management",
    __name__,
    url_prefix="/branch_officer/branch_management",
    template_folder=str(HTML_DIR),
)

def _context():
    return {
        "role": session.get("role"),
        "user_id": session.get("user_id"),
        "username": session.get("username"),
        "branch_id": session.get("branch_id"),
    }

def _guard():
    return (
        session.get("authenticated") is True
        and session.get("role") == ROLE
        and bool(session.get("branch_id"))
    )

@bp.route("/", methods=["GET", "POST"])
def branch_management():
    if not _guard():
        return redirect(url_for("login"))

    message = None
    error = None
    branch = {
        "branch_id": session.get("branch_id", ""),
        "name": "",
        "status": "",
        "member_count": 0,
        "active_member_count": 0,
    }

    try:
        if request.method == "POST":
            service.update_branch(
                _context(),
                {key: value for key, value in request.form.items() if key != "action"},
            )
            message = "Assigned Branch information updated successfully."
        branch = service.get_branch(_context()) or branch
    except Exception as exc:
        error = str(exc)

    # HTML is stored alongside services.py and this Python file.
    return render_template(
        "branch_management.html",
        branch=branch,
        message=message,
        error=error,
    )
