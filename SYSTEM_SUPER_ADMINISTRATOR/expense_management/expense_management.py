from datetime import datetime as _datetime  # explicit standard-library import
from flask import Blueprint, render_template, request, session, redirect, url_for, Response
from pathlib import Path
import importlib.util
import csv
import io

ROLE = "SYSTEM_SUPER_ADMINISTRATOR"
PAGE = "expense_management"
BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(f"{ROLE}_{PAGE}_services", BASE / "services.py")
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)
bp = Blueprint("system_super_administrator_expense_management_bp", __name__, url_prefix="/system_super_administrator/expense-management")

def _context():
    return {"role": session.get("role"), "user_id": session.get("user_id"), "username": session.get("username"), "branch_id": session.get("branch_id"), "branch_name": session.get("branch_name")}

def _full_name():
    """Return the logged-in account's stored full name, never its username as the display name."""
    try:
        from DATABASE.mongodb import get_database
        from bson import ObjectId
        db = get_database()
        user_id = session.get("user_id")
        username = session.get("username")
        candidates = []
        if user_id is not None:
            candidates.append({"_id": ObjectId(str(user_id))} if ObjectId.is_valid(str(user_id)) else {"_id": user_id})
            candidates.extend([{"user_id": user_id}, {"id": user_id}])
        if username:
            candidates.extend([{"username": username}, {"user_name": username}])
        for collection_name in ("users", "user", "members", "accounts"):
            collection = db[collection_name]
            for query in candidates:
                doc = collection.find_one(query)
                if doc:
                    for key in ("full_name", "fullname", "fullName", "name", "member_name"):
                        value = str(doc.get(key) or "").strip()
                        if value:
                            return value
    except Exception:
        pass
    # Avoid showing a username such as SAblue when a stored full name cannot be found.
    return str(session.get("full_name") or session.get("name") or "System Super Administrator").strip()

def _format_date(value):
    value = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return _datetime.strptime(value, fmt).strftime("%d.%m.%Y")
        except ValueError:
            pass
    return value

def _format_time(value):
    value = str(value or "").strip()
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p", "%I:%M:%S %p"):
        try:
            return _datetime.strptime(value.upper(), fmt).strftime("%I:%M %p")
        except ValueError:
            pass
    return value

def _authorized():
    return session.get("authenticated") is True and session.get("role") == ROLE

def _form_options():
    from DATABASE.mongodb import get_database
    db = get_database()
    branch_names = set()
    for collection_name in ("branches", "branch_management"):
        for x in db[collection_name].find({}):
            value = str(x.get("branch_name") or x.get("name") or x.get("branch") or "").strip()
            if value:
                branch_names.add(value)
    return {"branches": sorted(branch_names, key=str.casefold)}

@bp.route("/export.csv", methods=["GET"])
def export_csv():
    if not _authorized():
        return redirect(url_for("login"))
    records = service.list_records(_context(), request.args.to_dict())
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["SL", "Date", "Time", "Amount", "Expense Type", "Method", "Note"])
    for i, record in enumerate(records, 1):
        writer.writerow([i, _format_date(record.get("date", "")), _format_time(record.get("time", "")), record.get("amount", ""), record.get("category", record.get("type", "")), record.get("method", ""), record.get("note", "")])
    return Response("\ufeff" + output.getvalue(), mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=expense_records.csv"})

@bp.route("/", methods=["GET", "POST"])
def page():
    if not _authorized():
        return redirect(url_for("login"))
    message = session.pop("expense_management_message", None)
    error = None
    records = []
    try:
        options = _form_options()
    except Exception as exc:
        options = {"branches": []}
        error = f"Option loading error: {exc}"
    try:
        if request.method == "POST":
            action = request.form.get("action", "save")
            data = dict(request.form)
            if action == "delete":
                service.delete_record(_context(), request.form.get("record_id", ""))
                session["expense_management_message"] = "Deleted successfully."
            elif action == "update":
                service.update_record(_context(), request.form.get("record_id", ""), data)
                session["expense_management_message"] = "Updated successfully."
            else:
                service.create_record(_context(), data)
                session["expense_management_message"] = "Saved successfully."
            # Post/Redirect/Get prevents browser refresh from submitting the same entry again.
            return redirect(url_for("system_super_administrator_expense_management_bp.page"))
        records = service.list_records(_context(), request.args.to_dict())
    except Exception as exc:
        error = str(exc)
    return render_template("SYSTEM_SUPER_ADMINISTRATOR/expense_management/expense_management.html", records=records, message=message, error=error, session=session, options=options, full_name=_full_name(), format_date=_format_date, format_time=_format_time)
