from pathlib import Path
from flask import Blueprint, jsonify, request, send_file, session, redirect
import importlib.util

BASE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location("system_super_administrator_blood_donor_account_services", BASE/"services.py")
_service=importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_service)
service=_service.BloodDonorService()
bp=Blueprint("system_super_administrator_blood_donor_account_bp", __name__, url_prefix="/system_super_administrator/blood-donor-account")

def guard():
    if not session.get("authenticated"):
        return redirect("/login")
    return None

@bp.get("/")
@bp.get("/<page>")
def page(page="home"):
    blocked=guard()
    if blocked: return blocked
    return send_file(BASE/"account.html")


@bp.get("/api/home")
def home_api():
    blocked=guard()
    if blocked: return blocked
    try:
        return jsonify({"ok":True,"account":service.normal_account(session.get("user_id"),session.get("username"),session.get("name"))})
    except Exception as exc:
        return jsonify({"ok":False,"error":str(exc)}),500

@bp.get("/api/profile")
def profile_api():
    blocked=guard()
    if blocked: return blocked
    try:
        return jsonify({"ok":True,"account":service.normal_account(session.get("user_id"),session.get("username"),session.get("name"))})
    except Exception as exc:
        return jsonify({"ok":False,"error":str(exc)}),500
