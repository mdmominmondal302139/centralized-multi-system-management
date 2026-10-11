"""Standalone Flask routes for System Super Administrator Daily Bazar List."""
from flask import Blueprint, render_template_string, request, session, redirect, url_for
from pathlib import Path
from datetime import date
import json
import importlib.util

BASE = Path(__file__).resolve().parent
_service_spec = importlib.util.spec_from_file_location("system_super_administrator_daily_bazar_list_services", BASE / "bazar_list_services.py")
service = importlib.util.module_from_spec(_service_spec)
_service_spec.loader.exec_module(service)

ROLE = "SYSTEM_SUPER_ADMINISTRATOR"
TEMPLATE_FILE = BASE / "bazar_list.html"
bp = Blueprint(
    "system_super_administrator_daily_bazar_list_bp",
    __name__,
    url_prefix="/system_super_administrator/daily-bazar-list",
)


def _context():
    return {
        "role": session.get("role"),
        "user_id": session.get("user_id"),
        "username": session.get("username"),
    }


def _template():
    return TEMPLATE_FILE.read_text(encoding="utf-8")


def _render(**context):
    context.setdefault("today", date.today().isoformat())
    context.setdefault("editing", None)
    context.setdefault("filters", {})
    context.setdefault("message", None)
    context.setdefault("error", None)
    context.setdefault("members", [])
    context.setdefault("records", [])
    return render_template_string(_template(), **context)


@bp.route("/", methods=["GET", "POST"])
def page():
    if session.get("authenticated") is not True or session.get("role") != ROLE:
        return redirect(url_for("login"))

    message = None
    error = None
    ctx = _context()
    try:
        members = service.list_members(ctx)
        if request.method == "POST":
            action = str(request.form.get("action", "save")).strip().lower()
            filters = {
                "date": request.form.get("filter_date", "").strip(),
                "month": request.form.get("filter_month", "").strip(),
                "member": request.form.get("filter_member", "").strip(),
                "search": request.form.get("filter_search", "").strip(),
            }
            if action == "delete":
                service.delete_record(ctx, request.form.get("record_id", ""))
                return redirect(url_for(
                    "system_super_administrator_daily_bazar_list_bp.page",
                    deleted="1",
                    **{k: v for k, v in filters.items() if v}
                ))
            items_raw = request.form.get("items_json", "[]")
            try:
                items = json.loads(items_raw)
            except (TypeError, ValueError):
                items = []
            data = {
                "bazar_date": request.form.get("bazar_date", ""),
                "member_id": request.form.get("member_id", ""),
                "member_name": request.form.get("member_name", ""),
                "member_mobile": request.form.get("member_mobile", ""),
                "items": items,
                "paid_amount": request.form.get("paid_amount", "0"),
                "note": request.form.get("note", ""),
            }
            if action == "update":
                service.update_record(ctx, request.form.get("record_id", ""), data)
                return redirect(url_for("system_super_administrator_daily_bazar_list_bp.page", updated="1"))
            if action != "save":
                raise ValueError("Unknown action.")
            service.create_record(ctx, data)
            return redirect(url_for("system_super_administrator_daily_bazar_list_bp.page", saved="1"))

        filters = {
            "date": request.args.get("date", "").strip(),
            "month": request.args.get("month", "").strip(),
            "member": request.args.get("member", "").strip(),
            "search": request.args.get("search", "").strip(),
        }
        message = ("Daily Bazar record saved successfully." if request.args.get("saved")
                   else "Daily Bazar record updated successfully." if request.args.get("updated")
                   else "Daily Bazar record deleted successfully." if request.args.get("deleted")
                   else None)
        records = service.list_records(ctx, filters)
        editing = None
        edit_id = request.args.get("edit", "").strip()
        if edit_id:
            editing = service.get_record(ctx, edit_id)
        return _render(members=members, records=records, editing=editing,
                       filters=filters, message=message, error=error)
    except Exception as exc:
        try:
            records = service.list_records(ctx, {})
        except Exception:
            records = []
        return _render(members=locals().get("members", []), records=records,
                       editing=None, filters=locals().get("filters", {}),
                       message=message, error=str(exc))


@bp.route("/edit/<record_id>", methods=["GET"])
def edit_record(record_id):
    if session.get("authenticated") is not True or session.get("role") != ROLE:
        return redirect(url_for("login"))
    return redirect(url_for("system_super_administrator_daily_bazar_list_bp.page", edit=record_id))


@bp.route("/delete/<record_id>", methods=["POST"])
def delete_record(record_id):
    if session.get("authenticated") is not True or session.get("role") != ROLE:
        return redirect(url_for("login"))
    try:
        service.delete_record(_context(), record_id)
        return redirect(url_for("system_super_administrator_daily_bazar_list_bp.page", deleted="1"))
    except Exception as exc:
        return _render(members=service.list_members(_context()), records=[],
                       error=str(exc))
