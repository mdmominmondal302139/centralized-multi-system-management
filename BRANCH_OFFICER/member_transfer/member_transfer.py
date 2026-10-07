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
bp=Blueprint("branch_officer_member_transfer",__name__,url_prefix="/branch_officer/member_transfer",template_folder=str(HTML_DIR))
def ctx(): return {"role":ROLE,"user_id":session.get("user_id"),"username":session.get("username"),"branch_id":session.get("branch_id")}
def guard(): return session.get("authenticated") is True and str(session.get("role","")).upper()==ROLE and bool(session.get("branch_id"))
@bp.get("/")
def page():
    if not guard(): return redirect(url_for("login"))
    return render_template("BRANCH_OFFICER/member_transfer/member_transfer.html",summary=service.dashboard(ctx()))
