from pathlib import Path
from flask import Blueprint, send_file, session, redirect, url_for

ROLE="SYSTEM_SUPER_ADMINISTRATOR"
BASE=Path(__file__).resolve().parent
bp=Blueprint("system_super_administrator_screening_bp", __name__, url_prefix="/system_super_administrator/blood-donor-management/screening")


def _guard():
    if session.get("authenticated") is not True or session.get("role") != ROLE:
        return redirect(url_for("login"))
    return None

@bp.get("/")
def page():
    blocked=_guard()
    if blocked: return blocked
    return send_file(BASE / "screening.html")
