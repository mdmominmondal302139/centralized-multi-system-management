from __future__ import annotations
import importlib.util
from pathlib import Path
from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify, abort
ROLE="OPERATOR"
SERVICE_FILE = Path(__file__).resolve().parent / "services.py"
spec = importlib.util.spec_from_file_location("page_services", Path(__file__).resolve().parent / "services.py")
service=importlib.util.module_from_spec(spec); spec.loader.exec_module(service)
bp=Blueprint("operator_machine_operation", __name__, url_prefix="/operator/machine-operation")
def _ctx(): return {"role":session.get("role"),"user_id":session.get("user_id"),"branch_id":session.get("branch_id"),"section_id":session.get("section_id")}
@bp.route("/", methods=["GET"])
def operator_machine_operation():
    if not session.get("authenticated") or session.get("role")!=ROLE: return redirect(url_for("login"))
    return render_template("OPERATOR/machine_operation/machine_operation.html")
