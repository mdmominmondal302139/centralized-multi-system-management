from flask import Blueprint, render_template, request, session, redirect, url_for, Response
from pathlib import Path
import importlib.util
from datetime import datetime, date
import calendar
import re
import json

ROLE = "SYSTEM_SUPER_ADMINISTRATOR"
PAGE = "meal_management"
BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(f"{ROLE}_{PAGE}_services", BASE / "services.py")
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)
bp = Blueprint("system_super_administrator_meal_management_bp", __name__, url_prefix="/system_super_administrator/meal-management")

MONTH_NAMES = ["January","February","March","April","May","June","July","August","September","October","November","December"]

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

    members = []
    seen = set()
    for x in db["users"].find({"role":{"$regex":"^MEMBER$","$options":"i"},"status":{"$ne":"Inactive"}}):
        name = str(x.get("full_name") or x.get("name") or x.get("username") or "").strip()
        if not name or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        # Member's branch is sourced from the account record created during registration.
        member_branch = str(x.get("branch_name") or x.get("branch") or x.get("branchName") or "").strip()
        members.append({"name": name, "branch": member_branch})
    members.sort(key=lambda item: item["name"].casefold())
    return {"branches": sorted(branch_names, key=str.casefold), "members": members}

def _month_key(value):
    try:
        d = datetime.strptime(str(value), "%Y-%m")
        return d.strftime("%Y-%m")
    except Exception:
        return None

def _month_label(key):
    d = datetime.strptime(key, "%Y-%m")
    return d.strftime("%B %Y")

def _requested_month():
    raw = request.args.get("month", "")
    return _month_key(raw)

def _requested_member():
    return str(request.args.get("member", "")).strip()

@bp.route("/", methods=["GET", "POST"])
def page():
    if session.get("authenticated") is not True or session.get("role") != ROLE:
        return redirect(url_for("login"))

    # Consume the last action notice once, so refreshing the page won't repeat it.
    message = session.pop("_meal_management_notice", None)
    error = None
    try:
        options = _form_options()
    except Exception as exc:
        options = {"branches": [], "members": []}
        error = f"Option loading error: {exc}"

    try:
        if request.method == "POST":
            action = request.form.get("action", "save")
            data = dict(request.form)
            return_month = _month_key(request.form.get("return_month", ""))
            if action == "delete":
                service.delete_record(_context(), request.form.get("record_id", ""))
                message = "Deleted successfully."
            elif action == "update":
                service.update_record(_context(), request.form.get("record_id", ""), data)
                message = "Updated successfully."
            elif action == "bulk_save":
                try:
                    entries = json.loads(request.form.get("meal_entries", "[]"))
                except (TypeError, ValueError):
                    entries = []
                if not isinstance(entries, list) or not entries:
                    raise ValueError("Please select at least one meal type before saving.")
                common = {
                    "member_name": request.form.get("member_name", "").strip(),
                    "branch_name": request.form.get("branch_name", "").strip(),
                    "month": request.form.get("month", "").strip(),
                    "date": request.form.get("date", "").strip(),
                    "note": request.form.get("note", "").strip(),
                }
                if not common["member_name"] or not common["branch_name"] or not common["date"]:
                    raise ValueError("Please select Member, Branch and Date.")
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    item = dict(common)
                    item.update({
                        "type": str(entry.get("type", "")).strip(),
                        "quantity": str(entry.get("quantity", "1")).strip(),
                        "meal_charge": str(entry.get("meal_charge", "0")).strip(),
                        "rice_charge": str(entry.get("rice_charge", "0")).strip(),
                        "status": str(entry.get("status", "ON")).strip().upper(),
                    })
                    if item["type"] not in ("Breakfast", "Lunch", "Dinner"):
                        continue
                    service.save_or_update_record(_context(), item)
                message = "Selected meals saved successfully."
            else:
                service.create_record(_context(), data)
                message = "Saved successfully."
            # Post/Redirect/Get: store a one-time notice and preserve the month/member view.
            session["_meal_management_notice"] = message
            target_month = return_month or _month_key(request.form.get("month", ""))
            target_member = str(request.args.get("member") or request.form.get("return_member") or "").strip()
            if target_month:
                args = {"month": target_month}
                if target_member:
                    args["member"] = target_member
                return redirect(url_for("system_super_administrator_meal_management_bp.page", **args))
            return redirect(url_for("system_super_administrator_meal_management_bp.page"))
    except Exception as exc:
        error = str(exc)

    month_key = _requested_month()
    if month_key:
        try:
            search = str(request.args.get("search", "")).strip()
            member = _requested_member()
            month_rows = service.month_rows(_context(), month_key, search=search, member=member)
        except Exception as exc:
            month_rows = []
            error = str(exc)
        return render_template(
            "SYSTEM_SUPER_ADMINISTRATOR/meal_management/meal_management.html",
            view="month", month_key=month_key, month_label=_month_label(month_key),
            month_rows=month_rows, search=str(request.args.get("search","")).strip(), member=member,
            message=message, error=error, session=session, options=options,
            month_names=MONTH_NAMES, today=date.today().isoformat(), today_display=date.today().strftime("%d.%m.%Y"), current_month=date.today().strftime("%Y-%m"), current_year=date.today().year
        )

    try:
        member_rows = service.member_status_rows(_context(), limit=500)
    except Exception as exc:
        member_rows = []
        error = str(exc)

    return render_template(
        "SYSTEM_SUPER_ADMINISTRATOR/meal_management/meal_management.html",
        view="list", member_rows=member_rows, month_names=MONTH_NAMES,
        today=date.today().isoformat(), today_display=date.today().strftime("%d.%m.%Y"), current_month=date.today().strftime("%Y-%m"), current_year=date.today().year, message=message, error=error,
        session=session, options=options
    )

@bp.route("/download/<month>", methods=["GET"])
def download_month(month):
    if session.get("authenticated") is not True or session.get("role") != ROLE:
        return redirect(url_for("login"))
    month_key = _month_key(month)
    if not month_key:
        return Response("Invalid month.", status=400, mimetype="text/plain")
    member = str(request.args.get("member", "")).strip()
    rows = service.month_rows(_context(), month_key, member=member)
    label = _month_label(month_key)

    html = ["<html><head><meta charset='utf-8'><title>Meal Record - %s</title>"
            "<style>body{font-family:Arial,sans-serif;font-size:13px}h1{text-align:center}table{width:100%%;border-collapse:collapse}th,td{border:1px solid #555;padding:7px;text-align:left}th{background:#eee}.off{color:#c62828;font-weight:bold}.on{color:#087f46;font-weight:bold}</style></head><body>"
            "<h1>%s — MEMBER-WISE MEAL RECORD</h1><table><thead><tr><th>SL</th><th>Date</th><th>Day</th><th>Member</th><th>Branch</th><th>Meal Type</th><th>Meal</th><th>Meal Charge</th><th>Rice Charge</th><th>Status</th></tr></thead><tbody>" % (label, label)]
    sl = 0
    for day in rows:
        if day["status"] == "OFF":
            sl += 1
            html.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td class='off'>OFF</td></tr>" % (sl, day["date"], day["day"]))
        else:
            for r in day["records"]:
                sl += 1
                html.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class='on'>ON</td></tr>" %
                            (sl, day["date"], day["day"], r["member"], r["branch"], r["meal_type"], r["meal"], r["meal_charge"], r["rice_charge"]))
    html.append("</tbody></table></body></html>")
    body = "".join(html)
    suffix = ("_" + re.sub(r"[^A-Za-z0-9_-]+", "_", member)) if member else ""
    filename = "Meal_Record_%s%s.doc" % (month_key, suffix)
    return Response(body, mimetype="application/msword; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
