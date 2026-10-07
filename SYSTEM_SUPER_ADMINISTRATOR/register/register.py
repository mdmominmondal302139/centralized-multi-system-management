from pathlib import Path
from flask import Blueprint, jsonify, request, send_file
import importlib.util

BASE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location("system_super_administrator_blood_donor_register_services", BASE/"services.py")
_service=importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_service)
service=_service.BloodDonorService()
bp=Blueprint("system_super_administrator_blood_donor_register_bp", __name__, url_prefix="/system_super_administrator/blood-donor-register")

@bp.get("/")
def page():
    return send_file(BASE/"register.html")

@bp.post("/api/register")
def register_api():
    try:
        data=request.get_json(silent=True) or request.form.to_dict()
        result=service.register_normal_donor(data)
        return jsonify({"ok":True,"message":"Normal Blood Donor account created successfully.","account":{"username":result["username"],"user_id":result["user_id"],"role":result["role"]}}),201
    except ValueError as exc:
        return jsonify({"ok":False,"error":str(exc)}),400
    except Exception as exc:
        return jsonify({"ok":False,"error":str(exc)}),500
