from flask import Blueprint, render_template, request, session, redirect, url_for
from pathlib import Path
import importlib.util

ROLE = "SYSTEM_SUPER_ADMINISTRATOR"
PAGE = "savings_management"
BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(f"{ROLE}_{PAGE}_services", BASE / "services.py")
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)
bp = Blueprint("system_super_administrator_savings_management_bp", __name__, url_prefix="/system_super_administrator/savings-management")

def _context():
    return {"role": session.get("role"), "user_id": session.get("user_id"), "username": session.get("username"), "branch_id": session.get("branch_id"), "branch_name": session.get("branch_name")}

def _form_options():
    from DATABASE.mongodb import get_database
    db = get_database()
    branch_names = set()
    for collection_name in ("branches", "branch_management"):
        for x in db[collection_name].find({}):
            value = str(x.get("branch_name") or x.get("name") or x.get("branch") or "").strip()
            if value:
                branch_names.add(value)
    branches = sorted(branch_names, key=str.casefold)
    members=sorted({str(x.get("full_name") or x.get("name") or x.get("username") or "").strip() for x in db["users"].find({"role":{"$regex":"^MEMBER$","$options":"i"},"status":{"$ne":"Inactive"}}) if str(x.get("full_name") or x.get("name") or x.get("username") or "").strip()})
    return {'branches': branches, 'members': members}

@bp.route("/", methods=["GET", "POST"])
def page():
    if session.get("authenticated") is not True or session.get("role") != ROLE:
        return redirect(url_for("login"))
    message = None
    error = None
    records = []
    try:
        options = _form_options()
    except Exception as exc:
        options = {'branches': [], 'members': []}
        error = f"Option loading error: {exc}"
    try:
        if request.method == "POST":
            action = request.form.get("action", "save")
            data = dict(request.form)
            if action == "delete":
                service.delete_record(_context(), request.form.get("record_id", ""))
                message = "Deleted successfully."
            elif action == "update":
                service.update_record(_context(), request.form.get("record_id", ""), data)
                message = "Updated successfully."
            else:
                service.create_record(_context(), data)
                message = "Saved successfully."
        records = service.list_records(_context(), request.args.to_dict())
    except Exception as exc:
        error = str(exc)
    return render_template("SYSTEM_SUPER_ADMINISTRATOR/savings_management/savings_management.html", records=records, message=message, error=error, session=session, options=options)
