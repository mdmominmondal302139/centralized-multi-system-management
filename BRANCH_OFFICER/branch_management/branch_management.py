from __future__ import annotations
import importlib.util
from pathlib import Path
from flask import Blueprint, redirect, render_template, request, session, url_for
ROLE="BRANCH_OFFICER"
HTML_DIR = Path(__file__).resolve().parent
SERVICE_FILE = Path(__file__).resolve().parent / "services.py"
spec = importlib.util.spec_from_file_location("page_services", Path(__file__).resolve().parent / "services.py")
bp=Blueprint("branch_officer_branch_management",__name__,url_prefix="/branch_officer/branch_management",template_folder=str(HTML_DIR))
def _context(): return {"role":session.get("role"),"user_id":session.get("user_id"),"username":session.get("username"),"branch_id":session.get("branch_id")}
def _guard(): return session.get("authenticated") is True and session.get("role")==ROLE and bool(session.get("branch_id"))
@bp.route("/",methods=["GET","POST"])
def branch_management():
    if not _guard(): return redirect(url_for("login"))
    message=None; error=None
    try:
        if request.method=="POST":
            service.update_branch(_context(), {k:v for k,v in request.form.items() if k!="action"})
            message="Assigned Branch information updated successfully."
        branch=service.get_branch(_context())
    except Exception as exc:
        branch={"branch_id":session.get("branch_id"),"name":"","status":""}; error=str(exc)
    return render_template("BRANCH_OFFICER/branch_management/branch_management.html",branch=branch,message=message,error=error)
