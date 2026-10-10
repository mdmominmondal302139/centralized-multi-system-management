from flask import Blueprint, render_template_string, request, session, redirect, url_for, Response
from pathlib import Path
from datetime import datetime, timezone
import csv
import io
import importlib.util
import secrets

ROLE = "SYSTEM_SUPER_ADMINISTRATOR"
PAGE = "blood_donor_management"
BASE = Path(__file__).resolve().parent
TEMPLATE_FILE = BASE / "blood_donor_management.html"

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


def _profile_identity():
    """Resolve the signed-in account's saved full name and role from MongoDB.

    The login name is used only to locate the account, never as the displayed
    full name. Supports common field names used by account/member collections.
    """
    from DATABASE.mongodb import get_database
    from bson import ObjectId

    username = str(session.get("username") or "").strip()
    user_id = str(session.get("user_id") or "").strip()
    candidates = []
    if user_id:
        if ObjectId.is_valid(user_id):
            candidates.append({"_id": ObjectId(user_id)})
        candidates.extend([
            {"user_id": user_id}, {"_id": user_id}, {"id": user_id},
        ])
    if username:
        candidates.extend([
            {"username": username}, {"user_name": username},
            {"userName": username}, {"email": username},
            {"login_username": username}, {"login_id": username},
        ])

    full_name_fields = (
        "full_name", "fullName", "fullname", "full_name_of_user",
        "user_full_name", "account_full_name", "real_name", "display_name",
        "member_full_name", "member_name", "name", "legal_name",
    )
    first_name_fields = ("first_name", "firstName", "firstname", "given_name")
    last_name_fields = ("last_name", "lastName", "lastname", "surname", "family_name")

    def saved_full_name(record):
        for field in full_name_fields:
            value = record.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip()
        first = next((str(record.get(k)).strip() for k in first_name_fields if record.get(k)), "")
        last = next((str(record.get(k)).strip() for k in last_name_fields if record.get(k)), "")
        combined = " ".join(part for part in (first, last) if part).strip()
        if combined:
            return combined
        # Some apps store account/profile details in a nested object.
        for key in ("profile", "personal_info", "personal_information", "account"):
            nested = record.get(key)
            if isinstance(nested, dict):
                nested_name = saved_full_name(nested)
                if nested_name:
                    return nested_name
        return ""

    try:
        db = get_database()
        for collection_name in ("users", "members", "member_management", "user_management", "accounts"):
            try:
                collection = db[collection_name]
                for query in candidates:
                    record = collection.find_one(query)
                    if not record:
                        continue
                    full_name = saved_full_name(record)
                    role = (record.get("role_name") or record.get("role_title")
                            or record.get("role") or record.get("user_role")
                            or session.get("role_name") or session.get("role"))
                    if isinstance(role, dict):
                        role = role.get("name") or role.get("role_name") or role.get("title")
                    if full_name:
                        return full_name, str(role or "System Super Administrator")
            except Exception:
                continue
    except Exception:
        pass

    # Prefer a name already stored in the authenticated session; deliberately
    # do not fall back to the username, because it is not the requested label.
    session_name = next((str(session.get(k)).strip() for k in
                         ("full_name", "fullName", "fullname", "display_name", "name")
                         if session.get(k) and str(session.get(k)).strip()), "")
    role = session.get("role_name") or session.get("role") or "System Super Administrator"
    return session_name or "Full name unavailable", str(role)


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
    profile_full_name, profile_role = _profile_identity()
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

            elif action == "save_unit":
                from DATABASE.mongodb import get_database
                db = get_database()
                units = int(data.get("units", "0"))
                if units < 1:
                    raise ValueError("Units must be at least 1.")
                if not data.get("expiry_date") or not data.get("collection_date"):
                    raise ValueError("Collection date and expiry date are required.")
                if data["expiry_date"] < data["collection_date"]:
                    raise ValueError("Expiry date cannot be before collection date.")
                db["blood_inventory"].insert_one({
                    "blood_group": data.get("blood_group", ""),
                    "units": units,
                    "branch_name": data.get("branch_name", "Central"),
                    "collection_date": data.get("collection_date", ""),
                    "expiry_date": data.get("expiry_date", ""),
                    "status": data.get("status", "Available"),
                    "created_at": datetime.now(timezone.utc),
                    "created_by": session.get("username", ""),
                })
                message = "Blood inventory record saved."

        query_args = request.args.to_dict()
        records = service.list_donors(_context(), query_args)
        requests_list = service.list_blood_requests(_context(), query_args)
        stats = service.dashboard_stats(_context())
        request_matches = service.request_match_summary(_context())
        recent_donations = service.recent_donations(_context())
        audit_logs = service.recent_audit_logs(_context())
        from DATABASE.mongodb import get_database
        db = get_database()
        inventory = [service.clean(x) if hasattr(service, "clean") else x for x in db["blood_inventory"].find({}).sort("_id", -1).limit(500)]
        notifications = [service.clean(x) if hasattr(service, "clean") else x for x in db["blood_notifications"].find({}).sort("_id", -1).limit(100)]
        inventory_total = sum(int(x.get("units", 0) or 0) for x in inventory if x.get("status", "Available") == "Available")

    except Exception as exc:
        error = str(exc)
        stats = service.empty_stats()
        request_matches = []
        recent_donations = []
        audit_logs = []
        inventory = []
        notifications = []
        inventory_total = 0

    return render_template_string(
        TEMPLATE_FILE.read_text(encoding="utf-8"),
        records=records,
        requests_list=requests_list,
        stats=stats,
        request_matches=request_matches,
        recent_donations=recent_donations,
        audit_logs=audit_logs,
        inventory=inventory,
        notifications=notifications,
        inventory_total=inventory_total,
        message=message,
        error=error,
        session=session,
        profile_full_name=profile_full_name,
        profile_role=profile_role,
        options=options,
        csrf_token=_csrf(),
        today_date=service._today().isoformat(),
        request_args=request.args,
        blood_groups=service.BLOOD_GROUPS,
        availability_options=service.AVAILABILITY_OPTIONS,
        donor_statuses=service.DONOR_STATUS_OPTIONS,
        request_statuses=service.REQUEST_STATUS_OPTIONS,
    )


@bp.get("/reports.csv")
def export_report():
    if session.get("authenticated") is not True or session.get("role") != ROLE:
        return redirect(url_for("login"))
    try:
        donors = service.list_donors(_context(), {})
        requests_rows = service.list_blood_requests(_context(), {})
        from DATABASE.mongodb import get_database
        db = get_database()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["record_type", "record_id", "name_or_patient", "blood_group", "status", "branch", "date"])
        for d in donors:
            writer.writerow(["donor", d.get("donor_id", ""), d.get("donor_name", ""), d.get("blood_group", ""), d.get("status", ""), d.get("branch_name", ""), d.get("last_donation_date", "")])
        for r in requests_rows:
            writer.writerow(["request", r.get("request_id", ""), r.get("patient_name", ""), r.get("blood_group", ""), r.get("status", ""), r.get("branch_name", ""), r.get("required_date", "")])
        for u in db["blood_inventory"].find({}):
            writer.writerow(["inventory", str(u.get("_id", "")), u.get("units", 0), u.get("blood_group", ""), u.get("status", ""), u.get("branch_name", ""), u.get("expiry_date", "")])
        return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=blood_donor_report.csv"})
    except Exception as exc:
        return Response("Could not export report: " + str(exc), status=500, mimetype="text/plain")
