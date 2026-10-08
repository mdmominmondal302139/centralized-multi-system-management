from flask import Blueprint, render_template, request, session, redirect, url_for
from pathlib import Path
import importlib.util
import secrets

ROLE = "SYSTEM_SUPER_ADMINISTRATOR"
PAGE = "blood_donor_management"
BASE = Path(__file__).resolve().parent

spec = importlib.util.spec_from_file_location(
    f"{ROLE}_{PAGE}_services",
    BASE / "services.py",
)
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


def _csrf():
    token = session.get("sbc_csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["sbc_csrf"] = token
    return token


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

    return {
        "branches": sorted(branch_names, key=str.casefold),
    }


def _check_csrf():
    sent = request.form.get("_csrf", "")
    expected = session.get("sbc_csrf", "")
    if not sent or not expected or not secrets.compare_digest(sent, expected):
        raise PermissionError("Security token expired. Please refresh the page and try again.")


@bp.route("/", methods=["GET", "POST"])
@bp.route("/dashboard/", methods=["GET", "POST"])
def page():
    if (
        session.get("authenticated") is not True
        or session.get("role") != ROLE
    ):
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
            _check_csrf()
            action = request.form.get("action", "")
            data = request.form.to_dict(flat=True)

            if action == "save_donor":
                service.create_donor(_context(), data)
                message = "Donor profile created successfully."

            elif action == "update_donor":
                service.update_donor(
                    _context(),
                    request.form.get("record_id", ""),
                    data,
                )
                message = "Donor profile updated successfully."

            elif action == "archive_donor":
                service.set_donor_status(
                    _context(),
                    request.form.get("record_id", ""),
                    "Archived",
                )
                message = "Donor archived successfully."

            elif action == "activate_donor":
                service.set_donor_status(
                    _context(),
                    request.form.get("record_id", ""),
                    "Active",
                )
                message = "Donor activated successfully."

            elif action == "set_availability":
                service.set_donor_availability(
                    _context(),
                    request.form.get("record_id", ""),
                    request.form.get("availability", ""),
                )
                message = "Donor availability updated."

            elif action == "verify_donor":
                service.verify_donor(
                    _context(),
                    request.form.get("record_id", ""),
                )
                message = "Donor verification completed."

            elif action == "save_request":
                request_id = service.create_blood_request(_context(), data)
                service.create_matches_for_request(_context(), request_id)
                message = "Blood request created and donor matching started."

            elif action == "update_request":
                service.update_blood_request(
                    _context(),
                    request.form.get("record_id", ""),
                    data,
                )
                message = "Blood request updated."

            elif action == "complete_request":
                service.set_request_status(
                    _context(),
                    request.form.get("record_id", ""),
                    "Fulfilled",
                )
                message = "Blood request marked as fulfilled."

            elif action == "cancel_request":
                service.set_request_status(
                    _context(),
                    request.form.get("record_id", ""),
                    "Cancelled",
                )
                message = "Blood request cancelled."

            elif action == "match_request":
                count = service.create_matches_for_request(
                    _context(),
                    request.form.get("record_id", ""),
                )
                message = f"{count} donor match(es) prepared."

            elif action == "confirm_match":
                service.confirm_match(
                    _context(),
                    request.form.get("match_id", ""),
                )
                message = "Donor response confirmed."

            elif action == "record_donation":
                service.record_donation(
                    _context(),
                    request.form.get("record_id", ""),
                    data,
                )
                message = (
                    "Donation recorded. Donor availability was updated "
                    "according to the configured eligibility policy."
                )

        query_args = request.args.to_dict()
        records = service.list_donors(_context(), query_args)
        requests_list = service.list_blood_requests(_context(), query_args)
        stats = service.dashboard_stats(_context())
        request_matches = service.request_match_summary(_context())
        recent_donations = service.recent_donations(_context())
        audit_logs = service.recent_audit_logs(_context())

    except Exception as exc:
        error = str(exc)
        stats = service.empty_stats()
        request_matches = []
        recent_donations = []
        audit_logs = []

    return render_template(
        "SYSTEM_SUPER_ADMINISTRATOR/blood_donor_management/blood_donor_management.html",
        records=records,
        requests_list=requests_list,
        stats=stats,
        request_matches=request_matches,
        recent_donations=recent_donations,
        audit_logs=audit_logs,
        message=message,
        error=error,
        session=session,
        options=options,
        csrf_token=_csrf(),
        today_date=service._today().isoformat(),
        request_args=request.args,
        blood_groups=service.BLOOD_GROUPS,
        availability_options=service.AVAILABILITY_OPTIONS,
        donor_statuses=service.DONOR_STATUS_OPTIONS,
        request_statuses=service.REQUEST_STATUS_OPTIONS,
    )
