from datetime import datetime
from DATABASE.mongodb import get_database, clean

ROLE = "MEMBER"


def context_ok(context):
    return (
        isinstance(context, dict)
        and context.get("role") == ROLE
        and bool(context.get("user_id"))
    )


def _rows(collection_name, context, limit=100):
    if not context_ok(context):
        raise PermissionError("Access denied")
    db = get_database()
    records = db[collection_name].find(
        {"user_id": context.get("user_id")}
    ).sort("_id", -1).limit(limit)
    return [clean(record) for record in records]


def dashboard(context):
    return {
        "income": _rows("member_income", context),
        "expense": _rows("member_expense", context),
        "savings": _rows("member_savings", context),
        "meals": _rows("member_meals", context),
        "records": _rows("member_records", context),
    }


def _amount(record):
    for key in ("amount", "total", "value", "charge", "meal_charge", "rice_charge"):
        value = record.get(key)
        if value not in (None, ""):
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return 0.0


def _date_text(record):
    for key in ("date", "created_at", "createdAt", "timestamp", "entry_date"):
        value = record.get(key)
        if value:
            if isinstance(value, datetime):
                return value.strftime("%Y-%m-%d")
            return str(value)[:10]
    return ""


def _description(record, fallback):
    for key in ("title", "description", "details", "category", "note", "name", "type"):
        value = record.get(key)
        if value:
            return str(value)
    return fallback


def summary(context):
    if not context_ok(context):
        raise PermissionError("Access denied")

    now = datetime.now()
    month_key = now.strftime("%Y-%m")
    income_rows = _rows("member_income", context)
    expense_rows = _rows("member_expense", context)
    savings_rows = _rows("member_savings", context)
    meal_rows = _rows("member_meals", context)

    def total(rows, current_month=False):
        result = 0.0
        for row in rows:
            date_text = _date_text(row)
            if current_month and date_text and not date_text.startswith(month_key):
                continue
            result += _amount(row)
        return round(result, 2)

    recent = []
    for collection, rows, kind in (
        ("member_income", income_rows, "Income"),
        ("member_expense", expense_rows, "Expense"),
    ):
        for row in rows:
            recent.append({
                "type": kind,
                "description": _description(row, kind),
                "amount": _amount(row),
                "date": _date_text(row),
            })
    recent.sort(key=lambda row: row.get("date", ""), reverse=True)

    return {
        "name": context.get("name") or "Member",
        "month": month_key,
        "income": total(income_rows, current_month=True),
        "expense": total(expense_rows, current_month=True),
        "savings": total(savings_rows, current_month=True),
        "meal_charge": total(meal_rows, current_month=True),
        "monthly": {
            "income": total(income_rows, current_month=True),
            "expense": total(expense_rows, current_month=True),
            "savings": total(savings_rows, current_month=True),
        },
        "recent": recent[:8],
    }
