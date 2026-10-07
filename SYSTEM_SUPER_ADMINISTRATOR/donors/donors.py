"""SYSTEM SUPER ADMINISTRATOR — Blood Donor canonical API and Donors page."""
from __future__ import annotations

import importlib.util
from functools import wraps
from pathlib import Path

from flask import Blueprint, jsonify, redirect, request, session, send_file, send_from_directory, url_for

ROLE="SYSTEM_SUPER_ADMINISTRATOR"
BASE=Path(__file__).resolve().parent
STATIC=BASE.parents[1]/"STATIC"
SERVICE_FILE=BASE/"services.py"
_spec=importlib.util.spec_from_file_location("system_super_administrator_donors_services", SERVICE_FILE)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Could not load service: {SERVICE_FILE}")
_service=importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_service)
service=_service.BloodDonorService()

bp=Blueprint("system_super_administrator_blood_donor", __name__, url_prefix="/system_super_administrator")

def _context():
    return {"role":session.get("role") or request.headers.get("X-Role") or request.args.get("role"),"user_id":session.get("user_id") or request.headers.get("X-User-ID") or request.args.get("user_id"),"username":session.get("username") or request.headers.get("X-Username") or request.args.get("username"),"name":session.get("name") or request.headers.get("X-Name") or request.args.get("name")}

def _login_required(view):
    @wraps(view)
    def wrapped(*args,**kwargs):
        if _context().get("role") != ROLE:
            return redirect(url_for("login"))
        return view(*args,**kwargs)
    return wrapped

def _json_or_form():
    return dict(request.get_json(silent=True) or request.form.to_dict())

@bp.get("/blood-donor-management")
@bp.get("/blood-donor-management/")
def dashboard_page():
    if _context().get("role") != ROLE:
        return redirect(url_for("login"))
    return redirect("/system_super_administrator/blood-donor-management/dashboard")

@bp.get("/blood-donor-management/donors")
@_login_required
def donors_page():
    return send_file(BASE/"donors.html")

@bp.get("/blood-donor-management/static/<path:filename>")
def static_file(filename):
    return send_from_directory(STATIC, filename)

@bp.get("/blood-donor-management/api/metadata")
@_login_required
def metadata():
    return jsonify({"ok": True, **service.metadata()})


@bp.get("/blood-donor-management/api/dashboard")
@_login_required
def dashboard():
    try:
        return jsonify({"ok": True, "dashboard": service.dashboard()})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.get("/blood-donor-management/api/donors")
@_login_required
def donors():
    try:
        return jsonify({"ok": True, "donors": service.list_donors(request.args)})
    except Exception as exc:
        return jsonify({"ok": False, "donors": [], "error": str(exc)}), 500


@bp.get("/blood-donor-management/api/donor/<donor_id>")
@_login_required
def donor(donor_id):
    item = service.get_donor(donor_id)
    if not item:
        return jsonify({"ok": False, "error": "Donor not found."}), 404
    return jsonify({"ok": True, "donor": item})


@bp.post("/blood-donor-management/api/donor/create")
@_login_required
def donor_create():
    try:
        return jsonify({"ok": True, "donor": service.create_donor(_json_or_form(), _context().get("user_id"))})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.post("/blood-donor-management/api/donor/<donor_id>/update")
@_login_required
def donor_update(donor_id):
    try:
        item = service.update_donor(donor_id, _json_or_form(), _context().get("user_id"))
        if not item:
            return jsonify({"ok": False, "error": "Donor not found."}), 404
        return jsonify({"ok": True, "donor": item})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.post("/blood-donor-management/api/donor/<donor_id>/delete")
@_login_required
def donor_delete(donor_id):
    try:
        return jsonify({"ok": service.delete_donor(donor_id, _context().get("user_id"))})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.get("/blood-donor-management/api/donations")
@_login_required
def donations():
    return jsonify({"ok": True, "donations": service.list_donations(request.args.get("donor_id", ""))})


@bp.post("/blood-donor-management/api/donation/create")
@_login_required
def donation_create():
    try:
        return jsonify({"ok": True, "donation": service.create_donation(_json_or_form(), _context().get("user_id"))})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.get("/blood-donor-management/api/screenings")
@_login_required
def screenings():
    return jsonify({"ok": True, "screenings": service.list_screenings(request.args.get("donor_id", ""))})


@bp.post("/blood-donor-management/api/screening/create")
@_login_required
def screening_create():
    try:
        return jsonify({"ok": True, "screening": service.create_screening(_json_or_form(), _context().get("user_id"))})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.get("/blood-donor-management/api/requests")
@_login_required
def blood_requests():
    try:
        return jsonify({"ok": True, "requests": service.list_requests(request.args)})
    except Exception as exc:
        return jsonify({"ok": False, "requests": [], "error": str(exc)}), 500


@bp.post("/blood-donor-management/api/request/create")
@_login_required
def request_create():
    try:
        return jsonify({"ok": True, "request": service.create_request(_json_or_form(), _context().get("user_id"))})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.post("/blood-donor-management/api/request/<request_id>/update")
@_login_required
def request_update(request_id):
    try:
        item = service.update_request(request_id, _json_or_form(), _context().get("user_id"))
        if not item:
            return jsonify({"ok": False, "error": "Request not found."}), 404
        return jsonify({"ok": True, "request": item})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.get("/blood-donor-management/api/request/<request_id>")
@_login_required
def request_detail(request_id):
    item = service.get_request(request_id)
    if not item:
        return jsonify({"ok": False, "error": "Request not found."}), 404
    return jsonify({"ok": True, "request": item, "matches": service.list_matches(item.get("request_id"))})


@bp.post("/blood-donor-management/api/request/<request_id>/match")
@_login_required
def request_match(request_id):
    try:
        return jsonify({"ok": True, "matches": service.match_donors(request_id, _context().get("user_id"))})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.get("/blood-donor-management/api/matches")
@_login_required
def matches():
    return jsonify({"ok": True, "matches": service.list_matches(request.args.get("request_id", ""))})


@bp.post("/blood-donor-management/api/match/<match_id>/status")
@_login_required
def match_status(match_id):
    try:
        data = _json_or_form()
        return jsonify({"ok": True, "match": service.update_match(match_id, str(data.get("status") or ""), _context().get("user_id"))})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@bp.get("/blood-donor-management/api/units")
@_login_required
def units():
    return jsonify({"ok": True, "units": service.list_units(request.args)})


@bp.post("/blood-donor-management/api/unit/create")
@_login_required
def unit_create():
    try:
        return jsonify({"ok": True, "unit": service.create_unit(_json_or_form(), _context().get("user_id"))})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.post("/blood-donor-management/api/unit/<unit_id>/update")
@_login_required
def unit_update(unit_id):
    try:
        item = service.update_unit(unit_id, _json_or_form(), _context().get("user_id"))
        if not item:
            return jsonify({"ok": False, "error": "Blood unit not found."}), 404
        return jsonify({"ok": True, "unit": item})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.get("/blood-donor-management/api/notifications")
@_login_required
def notifications():
    return jsonify({"ok": True, "notifications": service.list_notifications(_context().get("user_id"))})


@bp.post("/blood-donor-management/api/notification/<notification_id>/read")
@_login_required
def notification_read(notification_id):
    return jsonify({"ok": service.mark_notification_read(notification_id, _context().get("user_id"))})


@bp.get("/blood-donor-management/api/reports")
@_login_required
def reports():
    try:
        return jsonify({"ok": True, "reports": service.reports()})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ---------------------------------------------------------------------------
# NORMAL BLOOD DONOR ACCOUNT
# The normal account uses the same donor/request data layer but has a
# separate UI and backend permission boundary. It does not expose admin APIs.
# ---------------------------------------------------------------------------

NORMAL_DONOR_ROLES = {"MEMBER", "BLOOD_DONOR", "NORMAL_USER", "NORMAL BLOOD DONOR"}
