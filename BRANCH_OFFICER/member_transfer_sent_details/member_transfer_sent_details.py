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
bp=Blueprint("branch_officer_member_transfer_sent_details",__name__,url_prefix="/branch_officer/member_transfer/sent",template_folder=str(HTML_DIR))
def ctx(): return {"role":ROLE,"user_id":session.get("user_id"),"username":session.get("username"),"branch_id":session.get("branch_id")}
def guard(): return session.get("authenticated") is True and str(session.get("role","")).upper()==ROLE and bool(session.get("branch_id"))
@bp.route("/<transfer_id>/",methods=["GET","POST"])
def page(transfer_id):
    if not guard(): return redirect(url_for("login"))
    error=message=None
    if request.method=="POST":
        try:
            if request.form.get("action")!="cancel": raise ValueError("Invalid transfer action.")
            service.cancel(ctx(),transfer_id); message="Transfer request cancelled."
        except Exception as exc: error=str(exc)
    row=service.get(ctx(),transfer_id)
    if not row: return ("Transfer request not found or access denied.",404)
    return render_template("BRANCH_OFFICER/member_transfer_sent_details/member_transfer_sent_details.html",row=row,error=error,message=message)
