from flask import Blueprint, request, session, redirect, url_for, flash, render_template_string
from pathlib import Path

import importlib.util

_SERVICE_PATH = Path(__file__).with_name("bazar_duty_services.py")
_service_spec = importlib.util.spec_from_file_location("system_super_administrator_bazar_duty_services", _SERVICE_PATH)
_service_module = importlib.util.module_from_spec(_service_spec)
_service_spec.loader.exec_module(_service_module)
BazarDutyService = _service_module.BazarDutyService

# Register this Blueprint in your existing Flask app.
bazar_duty_bp = Blueprint("bazar_duty", __name__, url_prefix="/bazar-duty")
_service = BazarDutyService()

_HTML_PATH = Path(__file__).with_name("bazar_duty.html")


def _render_page(**context):
    """Load the separate HTML file without requiring a new templates folder."""
    html = _HTML_PATH.read_text(encoding="utf-8")
    return render_template_string(html, **context)


def _scope():
    """Keep records separated by the signed-in account/branch where possible."""
    account_id = str(session.get("user_id") or session.get("account_id") or "")
    branch_id = str(session.get("branch_id") or session.get("branch") or "")
    account_name = (
        session.get("full_name")
        or session.get("name")
        or session.get("username")
        or "Account Full Name"
    )
    return account_id, branch_id, str(account_name)


@bazar_duty_bp.route("/", methods=["GET", "POST"])
def monthly_bazar_list():
    account_id, branch_id, account_name = _scope()
    month = request.values.get("month", "")
    if not month:
        from datetime import date
        month = date.today().strftime("%Y-%m")

    if request.method == "POST":
        action = request.form.get("action", "").strip()
        try:
            if action == "save_header":
                _service.save_header(
                    account_id=account_id,
                    branch_id=branch_id,
                    month=month,
                    header_name=request.form.get("header_name", "").strip(),
                    list_title=request.form.get("list_title", "বাজার লিস্ট").strip(),
                    instruction=request.form.get("instruction", "").strip(),
                )
                flash("Header settings saved.", "success")

            elif action == "save_duty":
                duty_id = request.form.get("duty_id", "").strip()
                _service.save_duty(
                    account_id=account_id,
                    branch_id=branch_id,
                    month=month,
                    duty_id=duty_id,
                    duty_date=request.form.get("duty_date", "").strip(),
                    member_one=request.form.get("member_one", "").strip(),
                    member_two=request.form.get("member_two", "").strip(),
                    bazar_time=request.form.get("bazar_time", "").strip(),
                    status=request.form.get("status", "Pending").strip(),
                    note=request.form.get("note", "").strip(),
                )
                flash("Bazar duty saved.", "success")

            elif action == "delete_duty":
                _service.delete_duty(
                    account_id=account_id,
                    branch_id=branch_id,
                    duty_id=request.form.get("duty_id", "").strip(),
                )
                flash("Bazar duty deleted.", "success")

            elif action == "add_member":
                _service.add_member(
                    account_id=account_id,
                    branch_id=branch_id,
                    name=request.form.get("new_member_name", "").strip(),
                )
                flash("Member added.", "success")

            else:
                flash("Unknown action.", "error")

        except ValueError as exc:
            flash(str(exc), "error")
        except Exception:
            # Avoid exposing database details to end users.
            flash("Could not save the information. Check database configuration and server logs.", "error")

        return redirect(url_for("system_super_administrator_meal_management_bp.bazar_duty.monthly_bazar_list", month=month))

    header = _service.get_header(account_id, branch_id, month)
    duties = _service.list_duties(account_id, branch_id, month)
    members = _service.list_members(account_id, branch_id)

    return _render_page(
        month=month,
        account_name=account_name,
        header=header,
        duties=duties,
        members=members,
    )


@bazar_duty_bp.route("/print", methods=["GET"])
def print_monthly_bazar_list():
    account_id, branch_id, account_name = _scope()
    month = request.args.get("month", "")
    if not month:
        from datetime import date
        month = date.today().strftime("%Y-%m")

    return _render_page(
        month=month,
        account_name=account_name,
        header=_service.get_header(account_id, branch_id, month),
        duties=_service.list_duties(account_id, branch_id, month),
        members=_service.list_members(account_id, branch_id),
        print_mode=True,
    )
