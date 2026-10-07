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

bp = Blueprint("branch_officer_work", __name__, url_prefix="/branch_officer/work", template_folder=str(HTML_DIR))

@bp.route("/", methods=["GET","POST"])
def work():
    if not _guard(): return redirect(url_for("login"))
    message = None
    error = None
    if request.method == "POST":
        action = request.form.get("action","save")
        try:
            if action == "branch_update":
                payload = {k:v for k,v in request.form.items() if k != "action"}
                service.update_branch(_context(), payload)
                message = "Assigned Branch information updated successfully."
            elif action == "member_create":
                payload = {k:v for k,v in request.form.items() if k != "action"}
                service.create_member(_context(), payload)
                message = "Branch member created successfully."
            elif action == "member_update":
                payload = {k:v for k,v in request.form.items() if k not in ("action","member_id")}
                service.update_member(_context(), request.form.get("member_id",""), payload)
                message = "Branch member updated successfully."
            elif action == "member_delete":
                service.delete_member(_context(), request.form.get("member_id",""))
                message = "Branch member deleted successfully."
            elif action == "member_password":
                service.reset_member_password(_context(), request.form.get("member_id",""), request.form.get("password",""))
                message = "Branch member password reset successfully."
            elif action == "delete":
                service.delete_record(_context(), request.form.get("record_id",""))
                message = "Record deleted successfully."
            elif action == "status":
                rid = request.form.get("record_id","")
                payload = {"status": request.form.get("status","Pending")}
                if request.form.get("problem_report"):
                    payload["problem_report"] = request.form.get("problem_report")
                service.update_record(_context(), rid, payload)
                message = "Work status updated successfully."
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
        branch_info = service.branch_overview(_context())
        members = service.list_members(_context(), request.args.get("member_search",""), request.args.get("member_status",""))
        member_edit_id = request.args.get("member_edit", "")
        member_edit = next((m for m in members if str(m.get("_id")) == member_edit_id), None)
        records = service.list_records(_context(), {"search":request.args.get("search",""),"date":request.args.get("date",""),"month":request.args.get("month",""),"member":request.args.get("member",""),"status":request.args.get("status",""),"priority":request.args.get("priority","")})
        edit_id = request.args.get("edit","")
        edit_record = next((r for r in records if str(r.get("_id")) == edit_id), None)
    except Exception as exc:
        records = []
        branch_info = {"branch_id":session.get("branch_id"),"name":session.get("branch_id"),"status":"Active","member_count":0,"active_member_count":0}
        members = []
        member_edit = None
        error = str(exc)
    return render_template("BRANCH_OFFICER/work/work.html", records=records, edit_record=edit_record if "edit_record" in locals() else None, branch_info=branch_info, members=members, member_edit=member_edit, message=message, error=error)
