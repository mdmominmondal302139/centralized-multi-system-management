from datetime import datetime
from collections import defaultdict
from DATABASE.mongodb import get_database, clean

ROLE = "SYSTEM_SUPER_ADMINISTRATOR"

BRANCH_COLLECTION = "branches"
LEGACY_BRANCH_COLLECTION = "branch_management"
USER_COLLECTION = "users"
INCOME_COLLECTION = "system_super_administrator_income_records"
EXPENSE_COLLECTION = "system_super_administrator_expense_records"
MEAL_COLLECTION = "system_super_administrator_meal_records"
SAVINGS_COLLECTION = "system_super_administrator_savings_records"


def _number(value):
    try:
        if value is None or value == "":
            return 0.0
        return float(str(value).replace(",", "").replace("৳", "").strip())
    except Exception:
        return 0.0


def _amount(row):
    for key in ("amount", "total", "value", "income", "expense", "savings", "meal_cost", "charge", "price"):
        if key in row:
            n = _number(row.get(key))
            if n:
                return n
    return 0.0


def _date(row):
    for key in ("date", "created_at", "createdAt", "entry_date", "record_date", "month"):
        value = row.get(key)
        if isinstance(value, datetime):
            return value
        if value:
            text = str(value).strip()
            for fmt in (
                "%Y-%m-%d",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%d.%m.%Y",
                "%d/%m/%Y",
            ):
                try:
                    return datetime.strptime(text[:19], fmt)
                except Exception:
                    pass
    return None


def _records(db, collection):
    try:
        return list(db[collection].find({}).limit(5000))
    except Exception:
        return []


def _all_branches(db):
    """Read both the canonical branches collection and the legacy branch page collection.

    Older versions saved Branch Management entries in branch_management, while the
    Home dashboard used branches.  Reading both keeps old data visible and makes newly
    created branches immediately available on Home without deleting or migrating data.
    """
    primary = _records(db, BRANCH_COLLECTION)
    legacy = _records(db, LEGACY_BRANCH_COLLECTION)
    result = []
    seen = set()
    for row in primary + legacy:
        key = (
            str(row.get("branch_reg_no") or "").strip().lower(),
            str(row.get("branch_name") or row.get("name") or "").strip().lower(),
            str(row.get("district") or "").strip().lower(),
        )
        if key == ("", "", ""):
            key = ("_id", str(row.get("_id")))
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def _branch_name(row):
    return str(row.get("branch_name") or row.get("branch") or row.get("name") or "Unassigned").strip() or "Unassigned"


def _role(row):
    value = row.get("role") or row.get("power") or row.get("user_role") or "MEMBER"
    return str(value).replace("_", " ").title()


def _branch_match(row, name, branch_map):
    rb = str(row.get("branch_name") or row.get("branch") or row.get("branch_id") or "").strip()
    return rb == name or branch_map.get(rb) == name


def dashboard(context):
    if context.get("role") != ROLE:
        raise PermissionError("Access denied.")

    db = get_database()
    branches = _all_branches(db)
    users = _records(db, USER_COLLECTION)
    incomes = _records(db, INCOME_COLLECTION)
    expenses = _records(db, EXPENSE_COLLECTION)
    meals = _records(db, MEAL_COLLECTION)
    savings = _records(db, SAVINGS_COLLECTION)

    try:
        super_admins = _records(db, "system_super_administrators")
    except Exception:
        super_admins = []
    all_accounts = users + super_admins

    branch_map = {}
    for b in branches:
        name = _branch_name(b)
        branch_map[str(b.get("_id"))] = name
        if b.get("branch_id") is not None:
            branch_map[str(b.get("branch_id"))] = name
        if b.get("branch_name"):
            branch_map[str(b.get("branch_name"))] = name
        if b.get("name"):
            branch_map[str(b.get("name"))] = name

    branch_rows = defaultdict(lambda: {"members": 0, "branch_admin": 0, "meal_manager": 0, "member": 0})
    # Show every created branch on Home, even when it has no member yet.
    for b in branches:
        branch_rows[_branch_name(b)]
    for u in users:
        bid = str(u.get("branch_id") or u.get("branch") or u.get("branch_name") or "Unassigned")
        name = branch_map.get(bid, bid if bid != "Unassigned" else "Unassigned")
        r = str(u.get("role") or u.get("power") or u.get("user_role") or "MEMBER").upper()
        branch_rows[name]["members"] += 1
        if "BRANCH" in r and "OFFICER" in r:
            branch_rows[name]["branch_admin"] += 1
        if "MEAL" in r:
            branch_rows[name]["meal_manager"] += 1
        if r == "MEMBER":
            branch_rows[name]["member"] += 1

    role_counts = defaultdict(int)
    for u in all_accounts:
        role_counts[_role(u)] += 1

    def monthly(rows):
        result = [0.0] * 12
        current_year = datetime.now().year
        for row in rows:
            d = _date(row)
            if d and d.year == current_year:
                result[d.month - 1] += _amount(row)
        return result

    income_monthly = monthly(incomes)
    expense_monthly = monthly(expenses)
    meal_monthly = monthly(meals)
    savings_monthly = monthly(savings)

    financial = []
    names = sorted(branch_rows.keys())
    for name in names:
        def branch_total(rows):
            return sum(_amount(row) for row in rows if _branch_match(row, name, branch_map))
        financial.append({
            "branch": name,
            "income": branch_total(incomes),
            "expense": branch_total(expenses),
            "meal": branch_total(meals),
            "savings": branch_total(savings),
        })

    recent = []
    activity_sources = [
        ("Income record", incomes),
        ("Expense record", expenses),
        ("Meal record", meals),
        ("Savings record", savings),
    ]
    for label, rows in activity_sources:
        for row in rows:
            d = _date(row)
            recent.append({"label": label, "date": d.isoformat() if d else ""})
    recent.sort(key=lambda x: x["date"], reverse=True)

    # Summary cards are all-record totals. The monthly charts remain current-year
    # views, so old records are not silently excluded from the headline totals.
    total_income = sum(_amount(row) for row in incomes)
    total_expense = sum(_amount(row) for row in expenses)
    total_savings = sum(_amount(row) for row in savings)

    return clean({
        "totals": {
            "branches": len(branches),
            "members": len(users),
            "roles": len(role_counts),
            "income": total_income,
            "expense": total_expense,
            "meal": len(meals),
            "savings": total_savings,
        },
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "monthly": {
            "income": income_monthly,
            "expense": expense_monthly,
            "meal": meal_monthly,
            "savings": savings_monthly,
        },
        "branch_rows": [
            {"branch": name, **values, "total": values["members"]}
            for name, values in sorted(branch_rows.items())
        ],
        "financial": financial,
        "roles": dict(sorted(role_counts.items(), key=lambda x: x[1], reverse=True)),
        "recent": recent[:7],
    })
