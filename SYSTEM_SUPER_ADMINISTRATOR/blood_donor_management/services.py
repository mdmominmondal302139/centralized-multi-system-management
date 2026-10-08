from datetime import datetime, timezone
from bson import ObjectId
from DATABASE.mongodb import get_database, clean

ROLE = "SYSTEM_SUPER_ADMINISTRATOR"
DONOR_COLLECTION = "blood_donor_management"
REQUEST_COLLECTION = "blood_requests"

BLOOD_GROUPS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")


def _guard(context):
    if not isinstance(context, dict) or context.get("role") != ROLE:
        raise PermissionError("Access denied.")


def _oid(value):
    value = str(value or "")
    return ObjectId(value) if ObjectId.is_valid(value) else value


def _today():
    return datetime.now(timezone.utc).date()


def _date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _three_months_after(value):
    d = _date(value)
    if not d:
        return ""
    # Three calendar months later, with end-of-month protection.
    month = d.month + 3
    year = d.year + (month - 1) // 12
    month = ((month - 1) % 12) + 1
    import calendar
    day = min(d.day, calendar.monthrange(year, month)[1])
    return f"{year:04d}-{month:02d}-{day:02d}"


def _refresh_availability(db):
    today = _today().isoformat()
    db[DONOR_COLLECTION].update_many(
        {
            "availability": "Temporarily Unavailable",
            "next_eligible_date": {"$lte": today},
            "status": {"$ne": "Inactive"},
        },
        {"$set": {"availability": "Available", "updated_at": datetime.now(timezone.utc)}},
    )


def empty_stats():
    return {
        "total_donors": 0,
        "active_donors": 0,
        "available_donors": 0,
        "temporary_unavailable": 0,
        "total_requests": 0,
        "open_requests": 0,
        "emergency_requests": 0,
        "total_donations": 0,
        "groups": {g: {"total": 0, "available": 0} for g in BLOOD_GROUPS},
    }


def list_donors(context, filters=None):
    _guard(context)
    filters = filters or {}
    db = get_database()
    _refresh_availability(db)
    query = {}

    search = str(filters.get("search") or "").strip()
    if search:
        query["$or"] = [
            {k: {"$regex": search, "$options": "i"}}
            for k in ("donor_name", "donor_id", "mobile", "phone", "email", "branch_name", "district", "upazila", "blood_group", "status", "availability")
        ]
    for key in ("blood_group", "branch_name", "district", "upazila", "availability", "status"):
        value = str(filters.get(key) or "").strip()
        if value:
            query[key] = value

    return [clean(x) for x in db[DONOR_COLLECTION].find(query).sort("_id", -1).limit(1000)]


def create_donor(context, data):
    _guard(context)
    db = get_database()
    item = dict(data or {})
    item.pop("action", None)
    item.pop("record_id", None)
    item["donor_name"] = item.get("donor_name", "").strip()
    item["blood_group"] = item.get("blood_group", "").strip()
    item["status"] = item.get("status") or "Active"
    item["availability"] = item.get("availability") or "Available"
    item["donation_count"] = int(item.get("donation_count") or 0)
    if not item.get("donor_id"):
        sequence = db[DONOR_COLLECTION].count_documents({}) + 1
        item["donor_id"] = f"BD-{sequence:05d}"
    item["created_at"] = datetime.now(timezone.utc)
    item["updated_at"] = datetime.now(timezone.utc)
    item["created_by"] = context.get("user_id")
    item["created_by_role"] = ROLE
    if not item.get("next_eligible_date") and item.get("last_donation_date"):
        item["next_eligible_date"] = _three_months_after(item["last_donation_date"])
    result = db[DONOR_COLLECTION].insert_one(item)
    return str(result.inserted_id)


def update_donor(context, record_id, data):
    _guard(context)
    db = get_database()
    oid = _oid(record_id)
    item = dict(data or {})
    for key in ("action", "record_id", "_id"):
        item.pop(key, None)
    if item.get("last_donation_date"):
        item["next_eligible_date"] = _three_months_after(item["last_donation_date"])
    item["updated_at"] = datetime.now(timezone.utc)
    result = db[DONOR_COLLECTION].update_one({"_id": oid}, {"$set": item})
    return result.modified_count or result.matched_count


def delete_donor(context, record_id):
    _guard(context)
    return get_database()[DONOR_COLLECTION].delete_one({"_id": _oid(record_id)}).deleted_count


def record_donation(context, record_id, data):
    _guard(context)
    db = get_database()
    oid = _oid(record_id)
    donor = db[DONOR_COLLECTION].find_one({"_id": oid})
    if not donor:
        raise ValueError("Donor not found.")
    donation_date = data.get("donation_date") or _today().isoformat()
    count = int(donor.get("donation_count") or 0) + 1
    next_date = _three_months_after(donation_date)
    db[DONOR_COLLECTION].update_one(
        {"_id": oid},
        {"$set": {
            "last_donation_date": donation_date,
            "next_eligible_date": next_date,
            "donation_count": count,
            "availability": "Temporarily Unavailable",
            "status": donor.get("status") or "Active",
            "updated_at": datetime.now(timezone.utc),
        }},
    )
    return count


def dashboard_stats(context):
    _guard(context)
    db = get_database()
    _refresh_availability(db)
    donors = list(db[DONOR_COLLECTION].find({}))
    requests = list(db[REQUEST_COLLECTION].find({}))
    stats = empty_stats()
    stats["total_donors"] = len(donors)
    stats["active_donors"] = sum(1 for x in donors if x.get("status") == "Active")
    stats["available_donors"] = sum(1 for x in donors if x.get("availability") == "Available" and x.get("status") != "Inactive")
    stats["temporary_unavailable"] = sum(1 for x in donors if x.get("availability") == "Temporarily Unavailable")
    stats["total_requests"] = len(requests)
    stats["open_requests"] = sum(1 for x in requests if x.get("status") in ("Pending", "Searching", "Donor Found"))
    stats["emergency_requests"] = sum(1 for x in requests if x.get("urgency") == "Emergency" and x.get("status") not in ("Completed", "Cancelled"))
    stats["total_donations"] = sum(int(x.get("donation_count") or 0) for x in donors)
    for group in BLOOD_GROUPS:
        matching = [x for x in donors if x.get("blood_group") == group]
        stats["groups"][group]["total"] = len(matching)
        stats["groups"][group]["available"] = sum(1 for x in matching if x.get("availability") == "Available" and x.get("status") != "Inactive")
    return stats


def create_blood_request(context, data):
    _guard(context)
    item = dict(data or {})
    item.pop("action", None)
    item.pop("record_id", None)
    item["status"] = item.get("request_status") or item.get("status") or "Pending"
    item["branch_name"] = str(item.get("branch_name") or "").strip()
    item["required_date"] = str(item.get("required_date") or _today().isoformat())[:10]
    item["created_at"] = datetime.now(timezone.utc)
    item["updated_at"] = datetime.now(timezone.utc)
    item["created_by"] = context.get("user_id")
    item["created_by_role"] = ROLE
    result = get_database()[REQUEST_COLLECTION].insert_one(item)
    return str(result.inserted_id)


def list_blood_requests(context, filters=None):
    _guard(context)
    filters = filters or {}
    db = get_database()
    query = {}
    search = str(filters.get("search") or "").strip()
    if search:
        query["$or"] = [
            {k: {"$regex": search, "$options": "i"}}
            for k in ("patient_name", "blood_group", "hospital_name", "branch_name", "district", "upazila", "mobile", "status", "urgency")
        ]
    for key in ("blood_group", "branch_name", "district", "upazila", "urgency", "status"):
        value = str(filters.get(key) or "").strip()
        if value:
            query[key] = value
    return [clean(x) for x in db[REQUEST_COLLECTION].find(query).sort("_id", -1).limit(1000)]


def update_blood_request(context, record_id, data):
    _guard(context)
    item = dict(data or {})
    for key in ("action", "record_id", "_id"):
        item.pop(key, None)
    item["updated_at"] = datetime.now(timezone.utc)
    return get_database()[REQUEST_COLLECTION].update_one({"_id": _oid(record_id)}, {"$set": item}).modified_count


def set_request_status(context, record_id, status):
    _guard(context)
    return get_database()[REQUEST_COLLECTION].update_one(
        {"_id": _oid(record_id)},
        {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}},
    ).modified_count
