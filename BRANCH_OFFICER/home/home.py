from __future__ import annotations
import importlib.util
from pathlib import Path
from flask import Blueprint, redirect, render_template, session, url_for, request

ROLE = "BRANCH_OFFICER"
HTML_DIR = Path(__file__).resolve().parent
SERVICE_FILE = Path(__file__).resolve().parent / "services.py"
_spec = importlib.util.spec_from_file_location("page_services", Path(__file__).resolve().parent / "services.py")
service = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(service)
bp = Blueprint("branch_officer_home", __name__, url_prefix="/branch_officer/home", template_folder=str(HTML_DIR))

def _require_branch_officer():
    if session.get("authenticated") is not True or session.get("role") != ROLE:
        return redirect(url_for("login"))
    return None


def _account_name():
    return (session.get("full_name") or session.get("name") or
            session.get("username") or "Branch Officer")


@bp.get("/")
def home():
    denied = _require_branch_officer()
    if denied:
        return denied
    try:
        data = service.summary({"role":session.get("role"),"user_id":session.get("user_id"),"username":session.get("username"),"branch_id":session.get("branch_id")})
    except Exception:
        data = {"income":0,"expense":0,"meal":0,"savings":0,"pending_work":0,"completed_work":0,"recent_income":[],"recent_expense":[],"recent_meal":[],"recent_savings":[],"recent_work":[]}
    return render_template("home.html", username=_account_name(),
                    branch_id=session.get("branch_id") or "Not assigned", data=data,
                    embedded=request.args.get("embedded") == "1",
                    profile_view=False, role_name="Branch Officer")


@bp.get("/profile")
def profile():
    denied = _require_branch_officer()
    if denied:
        return denied
    return render_template(
        "home.html", username=_account_name(),
        branch_id=session.get("branch_id") or "Not assigned",
        data={"income":0,"expense":0,"meal":0,"savings":0,
              "pending_work":0,"completed_work":0,"recent_income":[],
              "recent_expense":[],"recent_meal":[],"recent_savings":[],
              "recent_work":[]},
        embedded=False, profile_view=True, role_name="Branch Officer")


@bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
