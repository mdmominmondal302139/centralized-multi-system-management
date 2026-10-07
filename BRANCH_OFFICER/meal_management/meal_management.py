from __future__ import annotations
import importlib.util
from pathlib import Path
from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
ROLE = "BRANCH_OFFICER"
HTML_DIR = Path(__file__).resolve().parent

def _context():
    return {
        "role": session.get("role"),
        "user_id": session.get("user_id"),
        "username": session.get("username"),
        "branch_id": session.get("branch_id"),
    }

def _guard():
    return session.get("authenticated") is True and session.get("role") == ROLE and bool(session.get("branch_id"))
SERVICE_FILE = Path(__file__).resolve().parent / "services.py"
_spec = importlib.util.spec_from_file_location("page_services", Path(__file__).resolve().parent / "services.py")
service = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(service)

bp = Blueprint("branch_officer_meal_management", __name__, url_prefix="/branch_officer/meal_management", template_folder=str(HTML_DIR))

@bp.route("/", methods=["GET","POST"])
def meal_management():
    if not _guard(): return redirect(url_for("login"))
    message = None
    error = None
    if request.method == "POST":
        action = request.form.get("action","save")
        try:
            if action == "delete":
                service.delete_record(_context(), request.form.get("record_id",""))
                message = "Record deleted successfully."
            elif action == "update":
                rid = request.form.get("record_id","")
                payload = {k:v for k,v in request.form.items() if k not in ("action","record_id")}
                service.update_record(_context(), rid, payload)
                message = "Record updated successfully."
            else:
                payload = {k:v for k,v in request.form.items() if k not in ("action","record_id")}
                service.create_record(_context(), payload)
                message = "Saved successfully."
        except Exception as exc:
            error = str(exc)
    try:
        records = service.list_records(_context(), {"search":request.args.get("search",""),"date":request.args.get("date",""),"month":request.args.get("month",""),"member":request.args.get("member","")})
        edit_id = request.args.get("edit","")
        edit_record = next((r for r in records if str(r.get("_id")) == edit_id), None)
    except Exception as exc:
        records = []
        error = str(exc)
    return render_template("BRANCH_OFFICER/meal_management/meal_management.html", records=records, edit_record=edit_record if "edit_record" in locals() else None, message=message, error=error)
