from __future__ import annotations
import importlib.util
from pathlib import Path
from flask import Blueprint, render_template, session, redirect, url_for
SERVICE_FILE = Path(__file__).resolve().parent / "services.py"
spec = importlib.util.spec_from_file_location("page_services", Path(__file__).resolve().parent / "services.py")
TEMPLATE_DIR = str(Path(__file__).resolve().parent)
bp=Blueprint("operator_dashboard",__name__,url_prefix="/operator/dashboard",template_folder=TEMPLATE_DIR)
@bp.get("/")
def operator_dashboard():
    if not session.get("authenticated") or session.get("role")!="OPERATOR": return redirect(url_for("login"))
    summary=service.summary(service.context(session))
    return render_template("OPERATOR/dashboard/dashboard.html",summary=summary)
