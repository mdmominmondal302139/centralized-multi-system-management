from __future__ import annotations
import importlib.util
from pathlib import Path
from flask import Blueprint, redirect, render_template, request, session, url_for
ROLE="BRANCH_OFFICER"
HTML_DIR = Path(__file__).resolve().parent
SERVICE_FILE = Path(__file__).resolve().parent / "services.py"
spec = importlib.util.spec_from_file_location("page_services", Path(__file__).resolve().parent / "services.py")
bp=Blueprint("branch_officer_branch_officer_records",__name__,url_prefix="/branch_officer/branch_members",template_folder=str(HTML_DIR))
def _context(): return {"role":session.get("role"),"user_id":session.get("user_id"),"username":session.get("username"),"branch_id":session.get("branch_id")}
def _guard(): return session.get("authenticated") is True and session.get("role")==ROLE and bool(session.get("branch_id"))
@bp.route("/",methods=["GET","POST"])
def branch_members():
    if not _guard(): return redirect(url_for("login"))
    message=None; error=None
    try:
        if request.method=="POST":
            action=request.form.get("action","")
            if action=="create": service.create_member(_context(),dict(request.form)) ; message="Branch member created successfully."
            elif action=="update": service.update_member(_context(),request.form.get("member_id",""),{k:v for k,v in request.form.items() if k not in ("action","member_id")}); message="Branch member updated successfully."
            elif action=="delete": service.delete_member(_context(),request.form.get("member_id","")); message="Branch member deleted successfully."
            elif action=="password": service.reset_member_password(_context(),request.form.get("member_id",""),request.form.get("password","")); message="Branch member password reset successfully."
        members=service.list_members(_context(),request.args.get("search",""),request.args.get("status",""))
    except Exception as exc:
        error=str(exc); members=[]
    return render_template("BRANCH_OFFICER/branch_officer_records/branch_officer_records.html",members=members,message=message,error=error)
