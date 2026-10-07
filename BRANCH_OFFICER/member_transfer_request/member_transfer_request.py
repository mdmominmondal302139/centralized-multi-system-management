from __future__ import annotations
import importlib.util
from pathlib import Path
from flask import Blueprint,redirect,render_template,request,session,url_for
ROLE="BRANCH_OFFICER"
HTML_DIR = Path(__file__).resolve().parent
SERVICE_FILE = Path(__file__).resolve().parent / "services.py"
spec = importlib.util.spec_from_file_location("page_services", Path(__file__).resolve().parent / "services.py")
if spec is None or spec.loader is None: raise RuntimeError("Unable to load service.")
service=importlib.util.module_from_spec(spec); spec.loader.exec_module(service)
bp=Blueprint("branch_officer_member_transfer_request",__name__,url_prefix="/branch_officer/member_transfer/request",template_folder=str(HTML_DIR))
def ctx(): return {"role":ROLE,"user_id":session.get("user_id"),"username":session.get("username"),"branch_id":session.get("branch_id")}
def guard(): return session.get("authenticated") is True and str(session.get("role","")).upper()==ROLE and bool(session.get("branch_id"))
@bp.route("/",methods=["GET","POST"])
def page():
    if not guard(): return redirect(url_for("login"))
    error=None
    if request.method=="POST":
        try:
            tid=service.create(ctx(),request.form)
            return redirect(url_for("branch_officer_member_transfer_sent.page",created=tid))
        except Exception as exc: error=str(exc)
    return render_template("BRANCH_OFFICER/member_transfer_request/member_transfer_request.html",members=service.active_members(ctx()),branches=service.target_branches(ctx()),branch_name=service.current_branch_name(ctx()),branch_id=session.get("branch_id"),error=error)
