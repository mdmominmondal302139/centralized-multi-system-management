from flask import Blueprint, render_template, request, session, redirect, url_for
from pathlib import Path
import importlib.util

ROLE = "SYSTEM_SUPER_ADMINISTRATOR"
PAGE = "blood_donor_management"
BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(f"{ROLE}_{PAGE}_services", BASE / "services.py")
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)

bp = Blueprint(
    "system_super_administrator_blood_donor_management_bp",
    __name__,
    url_prefix="/system_super_administrator/blood-donor-management",
)


def _context():
    return {
        "role": session.get("role"),
        "user_id": session.get("user_id"),
        "username": session.get("username"),
        "branch_id": session.get("branch_id"),
        "branch_name": session.get("branch_name"),
    }


def _form_options():
    from DATABASE.mongodb import get_database
    db = get_database()
    branch_names = set()
    for collection_name in ("branches", "branch_management"):
        try:
            for item in db[collection_name].find({}):
                value = str(
                    item.get("branch_name")
                    or item.get("name")
                    or item.get("branch")
                    or ""
                ).strip()
                if value:
                    branch_names.add(value)
        except Exception:
            continue
    return {"branches": sorted(branch_names, key=str.casefold)}


@bp.route("/", methods=["GET", "POST"])
@bp.route("/dashboard/", methods=["GET", "POST"])
def page():
    if session.get("authenticated") is not True or session.get("role") != ROLE:
        return redirect(url_for("login"))

    message = None
    error = None
    records = []
    requests_list = []
    options = {"branches": []}

    try:
        options = _form_options()
    except Exception as exc:
        error = f"Option loading error: {exc}"

    try:
        if request.method == "POST":
            action = request.form.get("action", "")
            data = request.form.to_dict(flat=True)

            if action == "delete_donor":
                service.delete_donor(_context(), request.form.get("record_id", ""))
                message = "Donor deleted successfully."
            elif action == "update_donor":
                service.update_donor(_context(), request.form.get("record_id", ""), data)
                message = "Donor updated successfully."
            elif action == "save_donor":
                service.create_donor(_context(), data)
                message = "Donor saved successfully."
            elif action == "save_request":
                service.create_blood_request(_context(), data)
                message = "Blood request saved successfully."
            elif action == "update_request":
                service.update_blood_request(_context(), request.form.get("record_id", ""), data)
                message = "Blood request updated successfully."
            elif action == "complete_request":
                service.set_request_status(_context(), request.form.get("record_id", ""), "Completed")
                message = "Blood request marked as completed."
            elif action == "cancel_request":
                service.set_request_status(_context(), request.form.get("record_id", ""), "Cancelled")
                message = "Blood request cancelled."
            elif action == "record_donation":
                service.record_donation(_context(), request.form.get("record_id", ""), data)
                message = "Donation recorded. Donor is temporarily unavailable for 3 months."

        records = service.list_donors(_context(), request.args.to_dict())
        requests_list = service.list_blood_requests(_context(), request.args.to_dict())
        stats = service.dashboard_stats(_context())
    except Exception as exc:
        error = str(exc)
        stats = service.empty_stats()

    return render_template(
        "SYSTEM_SUPER_ADMINISTRATOR/blood_donor_management/blood_donor_management.html",
        records=records,
        requests_list=requests_list,
        stats=stats,
        message=message,
        error=error,
        session=session,
        options=options,
        today_date=service._today().isoformat(),
        request_args=request.args,
    )
