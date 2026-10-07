from __future__ import annotations
import importlib.util
from pathlib import Path
from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify, abort
ROLE="OPERATOR"
SERVICE_FILE = Path(__file__).resolve().parent / "services.py"
spec = importlib.util.spec_from_file_location("page_services", Path(__file__).resolve().parent / "services.py")
service=importlib.util.module_from_spec(spec); spec.loader.exec_module(service)
bp=Blueprint("operator_quality_entry", __name__, url_prefix="/operator/quality-entry")
def _ctx(): return {"role":session.get("role"),"user_id":session.get("user_id"),"branch_id":session.get("branch_id"),"section_id":session.get("section_id")}
@bp.route("/", methods=["GET", "POST"])
def operator_quality_entry():
    if not session.get("authenticated") or session.get("role")!=ROLE: return redirect(url_for("login"))
    data={k:request.form.get(k,"").strip() for k in ("defect_quantity","reject_quantity","rework_quantity","defect_type")}
    try: result=service.save(_ctx(),data)
    except Exception as exc: return str(exc),403
    return render_template("OPERATOR/quality_entry/quality_entry.html",result=result)
