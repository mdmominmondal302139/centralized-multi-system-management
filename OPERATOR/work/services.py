"""Garments Operator authorization and scoped service definitions."""
from datetime import datetime, timezone

ROLE = "OPERATOR"
ROLE_TITLE = "Garments Operator"
ROLE_SCOPE = "ASSIGNED TASK / OWN RECORDS"

ALLOWED_MODULES = {
    "home": "View own dashboard summary",
    "production_entry": "Enter own production data",
    "assigned_task": "View assigned tasks and update own task status",
    "machine_operation": "View assigned machine/operation/order information",
    "production_status": "Update own production status",
    "quality_entry": "Enter own defect/reject/rework data",
    "attendance_work_time": "Check-in/check-out and submit overtime request",
    "issue_reporting": "Report production, machine, material and quality issues",
    "my_records": "View own production, attendance, task and report history",
}

FORBIDDEN_ACTIONS = {
    "manage_other_operator_accounts",
    "create_employee_staff",
    "change_salary",
    "change_user_role",
    "change_factory_settings",
    "change_production_target",
    "delete_order_buyer_data",
    "view_other_department_confidential_data",
    "control_admin_manager_accounts",
    "delete_users",
}


def _authorized(context):
    if not isinstance(context, dict):
        return False
    if context.get("role") != ROLE:
        return False
    # Operator must have an assigned user identity and scope.
    return bool(context.get("user_id") and (context.get("section_id") or context.get("branch_id")))


def authorized(context):
    return _authorized(context)


def status(context, payload=None):
    if not _authorized(context):
        raise PermissionError("Access denied: OPERATOR role and assigned scope are required")
    return {
        "ok": True,
        "role": ROLE,
        "scope": ROLE_SCOPE,
        "allowed_modules": list(ALLOWED_MODULES.keys()),
        "payload": payload or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def list_records(context, records=None):
    result = status(context)
    result["records"] = list(records or [])
    result["count"] = len(result["records"])
    return result


def save_record(context, record):
    status(context)
    if not isinstance(record, dict):
        raise ValueError("record must be a dictionary")
    item = dict(record)
    item["role"] = ROLE
    item["user_id"] = context.get("user_id")
    item["updated_at"] = datetime.now(timezone.utc).isoformat()
    return {"ok": True, "record": item}
