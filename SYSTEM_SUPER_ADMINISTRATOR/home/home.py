from flask import Blueprint, render_template, session, redirect, url_for
from pathlib import Path
import importlib.util

ROLE = "SYSTEM_SUPER_ADMINISTRATOR"
PAGE = "home"
BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(f"{ROLE}_{PAGE}_services", BASE / "services.py")
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)

bp = Blueprint("system_super_administrator_home_bp", __name__, url_prefix="/system_super_administrator")


def _context():
    return {
        "role": session.get("role"),
        "user_id": session.get("user_id"),
        "username": session.get("username"),
        "branch_id": session.get("branch_id"),
        "branch_name": session.get("branch_name"),
    }


@bp.route("/", methods=["GET"])
def page():
    if session.get("authenticated") is not True or session.get("role") not in (ROLE, "SYSTEM_SUPER_ADMINISTRATOR"):
        return redirect(url_for("login"))

    error = None
    try:
        data = service.dashboard(_context())
    except Exception as exc:
        data = {
            "totals": {"branches": 0, "members": 0, "roles": 0, "income": 0, "expense": 0, "meal": 0, "savings": 0},
            "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            "monthly": {"income": [0] * 12, "expense": [0] * 12, "meal": [0] * 12, "savings": [0] * 12},
            "branch_rows": [], "financial": [], "roles": {}, "recent": [],
        }
        error = str(exc)

    return render_template(
        "SYSTEM_SUPER_ADMINISTRATOR/home/home.html",
        dashboard=data,
        error=error,
        session=session,
    )
