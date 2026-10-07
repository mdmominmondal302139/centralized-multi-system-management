from flask import Blueprint, render_template, request, session, redirect, url_for
from pathlib import Path
import importlib.util
ROLE='SYSTEM_SUPER_ADMINISTRATOR'
PAGE='member_audit'
BASE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location(f"{ROLE}_{PAGE}_services", BASE/"services.py")
service=importlib.util.module_from_spec(spec); spec.loader.exec_module(service)
bp=Blueprint('system_super_administrator_member_audit_bp', __name__, url_prefix='/system_super_administrator/member-audit')

def _context(): return {"role":session.get("role"),"user_id":session.get("user_id"),"username":session.get("username"),"branch_id":session.get("branch_id"),"branch_name":session.get("branch_name")}

@bp.route("/", methods=["GET","POST"])
def page():
    if session.get("authenticated") is not True or session.get("role") not in (ROLE,"SYSTEM_SUPER_ADMINISTRATOR"):
        return redirect(url_for("login"))
    message=None; error=None
    try:
        if request.method=="POST":
            action=request.form.get("action","save")
            if action=="delete": service.delete_record(_context(),request.form.get("record_id","")); message="Deleted successfully."
            elif action=="update": service.update_record(_context(),request.form.get("record_id",""),dict(request.form)); message="Updated successfully."
            else: service.create_record(_context(),dict(request.form)); message="Saved successfully."
        records=service.list_records(_context(),request.args.to_dict())
    except Exception as exc:
        records=[]; error=str(exc)
    return render_template("SYSTEM_SUPER_ADMINISTRATOR/member_audit/member_audit.html", records=records, message=message, error=error, session=session)
