"""ACCOUNTS OFFICER — Accounts route. This file belongs only to this page."""
from pathlib import Path
import importlib.util
from flask import Blueprint, render_template, request, session, redirect, url_for, abort

BASE_DIR = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("page_services", Path(__file__).resolve().parent / "services.py")
_service = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_service)
bp = Blueprint("account_officer_accounts_officer_income", __name__, url_prefix="/accounts_officer/accounts")

def _context():
    return {"role": session.get("role"), "user_id": session.get("user_id"), "branch_id": session.get("branch_id"), "section_id": session.get("section_id")}

def _guard():
    if session.get("role") != "ACCOUNT_OFFICER":
        return redirect(url_for("login"))
    return None

@bp.route("/", methods=["GET","POST"])
def accounts():
    blocked = _guard()
    if blocked: return blocked
    context = _context()
    records = []
    try:
        if request.method == "POST":
            _service.save_record(context, request.form.to_dict())
        records = _service.list_records(context)
    except Exception:
        records = []
    return render_template("ACCOUNT_OFFICER/accounts_officer_income/accounts_officer_income.html", user={k:v for k,v in session.items()}, records=records, summary={"today_income":"0.00","today_expense":"0.00","today_savings":"0.00","cash_balance":"0.00","pending_verification":0,"pending_reconciliation":0,"pending_correction":0,"opening":"0.00","received":"0.00","payment":"0.00","closing":"0.00"}, total="0.00", balance="0.00", monthly="0.00", recent=[])

