from __future__ import annotations
import importlib.util
from pathlib import Path
from flask import Blueprint, redirect, render_template, request, session, url_for

ROLE = "BRANCH_OFFICER"
HTML_DIR = Path(__file__).resolve().parent
SERVICE_FILE = Path(__file__).resolve().parent / "services.py"
_spec = importlib.util.spec_from_file_location("page_services", Path(__file__).resolve().parent / "services.py")
service = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(service)
bp = Blueprint("branch_officer_register", __name__, url_prefix="/branch_officer/records", template_folder=str(HTML_DIR))

@bp.get("/")
def records():
    if session.get("authenticated") is not True or session.get("role") != ROLE or not session.get("branch_id"):
        return redirect(url_for("login"))
    try:
        rows = service.history({"role":session.get("role"),"user_id":session.get("user_id"),"branch_id":session.get("branch_id")}, request.args.get("type","all"), request.args.get("period","all"), request.args.get("date",""), request.args.get("search",""))
    except Exception:
        rows = []
    return render_template("BRANCH_OFFICER/register/register.html", records=rows)
