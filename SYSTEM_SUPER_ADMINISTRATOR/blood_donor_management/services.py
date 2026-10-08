from datetime import datetime, timezone
from bson import ObjectId
from DATABASE.mongodb import get_database, clean
import calendar
import secrets

ROLE = "SYSTEM_SUPER_ADMINISTRATOR"

DONOR_COLLECTION = "blood_donor_management"
REQUEST_COLLECTION = "blood_requests"
DONATION_COLLECTION = "blood_donations"
MATCH_COLLECTION = "blood_request_matches"
AUDIT_COLLECTION = "blood_audit_logs"
OTP_COLLECTION = "blood_otp_verifications"

BLOOD_GROUPS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")

AVAILABILITY_OPTIONS = (
    "Available",
    "Temporarily Unavailable",
    "Do Not Contact",
    "Inactive",
)

DONOR_STATUS_OPTIONS = (
    "Pending Verification",
    "Active",
    "Inactive",
    "Archived",
    "Suspended",
)

REQUEST_STATUS_OPTIONS = (
    "Pending",
    "Matching",
    "Donors Contacted",
    "Donor Confirmed",
    "Emergency Escalated",
    "Fulfilled",
    "Cancelled",
    "Expired",
)

OPEN_REQUEST_STATUSES = (
    "Pending",
    "Matching",
    "Donors Contacted",
    "Donor Confirmed",
    "Emergency Escalated",
)


def _guard(context):
    if not isinstance(context, dict) or context.get("role") != ROLE:
        raise PermissionError("Access denied.")


def _oid(value):
    value = str(value or "")
    return ObjectId(value) if ObjectId.is_valid(value) else value


def _now():
    return datetime.now(timezone.utc)


def _today():
    return _now().date()


def _date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _three_months_after(value):
    d = _date(value)
    if not d:
        return ""
    month = d.month + 3
    year = d.year + (month - 1) // 12
    month = ((month - 1) % 12) + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return f"{year:04d}-{month:02d}-{day:02d}"


def _next_id(db, collection, field, prefix, width=6):
    last = db[collection].find_one(
        {field: {"$regex": f"^{prefix}[0-9]+$"}},
        sort=[(field, -1)],
    )
    if not last:
        return f"{prefix}{1:0{width}d}"

    raw = str(last.get(field, ""))
    digits = "".join(ch for ch in raw if ch.isdigit())
    number = int(digits or 0) + 1
    return f"{prefix}{number:0{width}d}"


def _audit(context, action, entity, entity_id="", before=None, after=None):
    db = get_database()
    db[AUDIT_COLLECTION].insert_one(
        {
            "actor_user_id": context.get("user_id"),
            "actor_username": context.get("username"),
            "actor_role": context.get("role"),
            "action": action,
            "entity": entity,
            "entity_id": str(entity_id or ""),
            "before": clean(before) if before else None,
            "after": clean(after) if after else None,
            "created_at": _now(),
        }
    )


def _refresh_availability(db):
    today = _today().isoformat()
    db[DONOR_COLLECTION].update_many(
        {
            "availability": "Temporarily Unavailable",
            "next_eligible_date": {"$lte": today},
            "status": {"$nin": ["Inactive", "Archived", "Suspended"]},
        },
        {
            "$set": {
                "availability": "Available",
                "updated_at": _now(),
            }
        },
    )


def empty_stats():
    return {
        "total_donors": 0,
        "active_donors": 0,
        "verified_donors": 0,
        "pending_verification": 0,
        "available_donors": 0,
        "temporary_unavailable": 0,
        "do_not_contact": 0,
        "total_requests": 0,
        "open_requests": 0,
        "emergency_requests": 0,
        "total_donations": 0,
        "donations_this_month": 0,
        "fulfilled_requests": 0,
        "groups": {
            g: {"total": 0, "available": 0}
            for g in BLOOD_GROUPS
        },
    }


def _safe_int(value, default=0):
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


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
            for k in (
                "donor_name",
                "donor_id",
                "mobile",
                "email",
                "branch_name",
                "district",
                "upazila",
                "blood_group",
                "status",
                "availability",
            )
        ]

    for key in (
        "blood_group",
        "branch_name",
        "district",
        "upazila",
        "availability",
        "status",
        "verification_status",
    ):
        value = str(filters.get(key) or "").strip()
        if value:
            query[key] = value

    return [
        clean(x)
        for x in db[DONOR_COLLECTION]
        .find(query)
        .sort("_id", -1)
        .limit(1000)
    ]


def create_donor(context, data):
    _guard(context)
    db = get_database()
    item = dict(data or {})

    for key in ("action", "record_id", "_csrf"):
        item.pop(key, None)

    item["donor_name"] = str(item.get("donor_name") or "").strip()
    item["blood_group"] = str(item.get("blood_group") or "").strip()

    if not item["donor_name"]:
        raise ValueError("Donor name is required.")
    if item["blood_group"] not in BLOOD_GROUPS:
        raise ValueError("Please select a valid blood group.")
    if not str(item.get("mobile") or "").strip():
        raise ValueError("Mobile number is required.")

    mobile = str(item.get("mobile")).strip()
    duplicate = db[DONOR_COLLECTION].find_one(
        {
            "mobile": mobile,
            "status": {"$ne": "Archived"},
        }
    )
    if duplicate:
        raise ValueError(
            "A donor profile with this mobile number already exists."
        )

    item["status"] = (
        item.get("status")
        if item.get("status") in DONOR_STATUS_OPTIONS
        else "Pending Verification"
    )
    item["availability"] = (
        item.get("availability")
        if item.get("availability") in AVAILABILITY_OPTIONS
        else "Available"
    )
    item["verification_status"] = (
        "Verified"
        if item.get("verification_status") == "Verified"
        else "Pending"
    )
    item["donation_count"] = _safe_int(item.get("donation_count"))
    item["donor_id"] = _next_id(
        db,
        DONOR_COLLECTION,
        "donor_id",
        "SBC-",
        7,
    )

    if not item.get("next_eligible_date") and item.get("last_donation_date"):
        item["next_eligible_date"] = _three_months_after(
            item["last_donation_date"]
        )

    item["created_at"] = _now()
    item["updated_at"] = _now()
    item["created_by"] = context.get("user_id")
    item["created_by_role"] = ROLE

    result = db[DONOR_COLLECTION].insert_one(item)
    _audit(
        context,
        "CREATE",
        "donor",
        item["donor_id"],
        after=item,
    )
    return str(result.inserted_id)


def update_donor(context, record_id, data):
    _guard(context)
    db = get_database()
    oid = _oid(record_id)
    before = db[DONOR_COLLECTION].find_one({"_id": oid})

    if not before:
        raise ValueError("Donor not found.")

    item = dict(data or {})
    for key in ("action", "record_id", "_id", "_csrf"):
        item.pop(key, None)

    protected = {
        "donor_id",
        "created_at",
        "created_by",
        "created_by_role",
    }
    for key in list(item):
        if key in protected:
            item.pop(key, None)

    if item.get("blood_group") not in BLOOD_GROUPS:
        item["blood_group"] = before.get("blood_group")

    if item.get("status") not in DONOR_STATUS_OPTIONS:
        item["status"] = before.get("status", "Active")

    if item.get("availability") not in AVAILABILITY_OPTIONS:
        item["availability"] = before.get("availability", "Available")

    if item.get("last_donation_date"):
        item["next_eligible_date"] = _three_months_after(
            item["last_donation_date"]
        )

    item["updated_at"] = _now()

    result = db[DONOR_COLLECTION].update_one(
        {"_id": oid},
        {"$set": item},
    )
    after = db[DONOR_COLLECTION].find_one({"_id": oid})

    _audit(
        context,
        "UPDATE",
        "donor",
        before.get("donor_id"),
        before=before,
        after=after,
    )
    return result.modified_count or result.matched_count


def set_donor_status(context, record_id, status):
    _guard(context)
    if status not in DONOR_STATUS_OPTIONS:
        raise ValueError("Invalid donor status.")

    db = get_database()
    oid = _oid(record_id)
    before = db[DONOR_COLLECTION].find_one({"_id": oid})
    if not before:
        raise ValueError("Donor not found.")

    db[DONOR_COLLECTION].update_one(
        {"_id": oid},
        {
            "$set": {
                "status": status,
                "updated_at": _now(),
            }
        },
    )
    after = db[DONOR_COLLECTION].find_one({"_id": oid})
    _audit(
        context,
        "STATUS_CHANGE",
        "donor",
        before.get("donor_id"),
        before=before,
        after=after,
    )


def set_donor_availability(context, record_id, availability):
    _guard(context)
    if availability not in AVAILABILITY_OPTIONS:
        raise ValueError("Invalid availability status.")

    db = get_database()
    oid = _oid(record_id)
    before = db[DONOR_COLLECTION].find_one({"_id": oid})
    if not before:
        raise ValueError("Donor not found.")

    db[DONOR_COLLECTION].update_one(
        {"_id": oid},
        {
            "$set": {
                "availability": availability,
                "updated_at": _now(),
            }
        },
    )
    after = db[DONOR_COLLECTION].find_one({"_id": oid})
    _audit(
        context,
        "AVAILABILITY_CHANGE",
        "donor",
        before.get("donor_id"),
        before=before,
        after=after,
    )


def verify_donor(context, record_id):
    _guard(context)
    db = get_database()
    oid = _oid(record_id)
    before = db[DONOR_COLLECTION].find_one({"_id": oid})
    if not before:
        raise ValueError("Donor not found.")

    db[DONOR_COLLECTION].update_one(
        {"_id": oid},
        {
            "$set": {
                "verification_status": "Verified",
                "status": "Active",
                "verified_at": _now(),
                "verified_by": context.get("user_id"),
                "updated_at": _now(),
            }
        },
    )
    after = db[DONOR_COLLECTION].find_one({"_id": oid})
    _audit(
        context,
        "VERIFY",
        "donor",
        before.get("donor_id"),
        before=before,
        after=after,
    )


def record_donation(context, record_id, data):
    _guard(context)
    db = get_database()
    oid = _oid(record_id)
    donor = db[DONOR_COLLECTION].find_one({"_id": oid})

    if not donor:
        raise ValueError("Donor not found.")

    donation_date = str(
        data.get("donation_date") or _today().isoformat()
    )[:10]

    donation_id = _next_id(
        db,
        DONATION_COLLECTION,
        "donation_id",
        "QDON-",
        7,
    )

    next_date = _three_months_after(donation_date)
    donation = {
        "donation_id": donation_id,
        "donor_id": donor.get("donor_id"),
        "donor_record_id": donor.get("_id"),
        "donor_name": donor.get("donor_name"),
        "blood_group": donor.get("blood_group"),
        "branch_name": donor.get("branch_name"),
        "donation_date": donation_date,
        "donation_type": data.get("donation_type") or "Whole Blood",
        "screening_status": data.get("screening_status") or "Pending",
        "collection_status": data.get("collection_status") or "Collected",
        "deferral_status": data.get("deferral_status") or "None",
        "staff_member": context.get("username"),
        "notes": data.get("notes") or "",
        "created_at": _now(),
        "created_by": context.get("user_id"),
    }

    db[DONATION_COLLECTION].insert_one(donation)

    count = _safe_int(donor.get("donation_count")) + 1

    db[DONOR_COLLECTION].update_one(
        {"_id": oid},
        {
            "$set": {
                "last_donation_date": donation_date,
                "next_eligible_date": next_date,
                "donation_count": count,
                "availability": "Temporarily Unavailable",
                "status": (
                    donor.get("status")
                    if donor.get("status") not in ("Archived", "Inactive")
                    else "Active"
                ),
                "updated_at": _now(),
            }
        },
    )

    after = db[DONOR_COLLECTION].find_one({"_id": oid})
    _audit(
        context,
        "RECORD_DONATION",
        "donation",
        donation_id,
        after=donation,
    )
    _audit(
        context,
        "DONOR_UPDATED_AFTER_DONATION",
        "donor",
        donor.get("donor_id"),
        before=donor,
        after=after,
    )
    return donation_id


def dashboard_stats(context):
    _guard(context)
    db = get_database()
    _refresh_availability(db)

    donors = list(db[DONOR_COLLECTION].find({}))
    requests = list(db[REQUEST_COLLECTION].find({}))
    donations = list(db[DONATION_COLLECTION].find({}))

    stats = empty_stats()
    stats["total_donors"] = len(donors)
    stats["active_donors"] = sum(
        1 for x in donors if x.get("status") == "Active"
    )
    stats["verified_donors"] = sum(
        1 for x in donors if x.get("verification_status") == "Verified"
    )
    stats["pending_verification"] = sum(
        1 for x in donors
        if x.get("verification_status") != "Verified"
    )
    stats["available_donors"] = sum(
        1
        for x in donors
        if x.get("availability") == "Available"
        and x.get("status") == "Active"
    )
    stats["temporary_unavailable"] = sum(
        1 for x in donors
        if x.get("availability") == "Temporarily Unavailable"
    )
    stats["do_not_contact"] = sum(
        1 for x in donors
        if x.get("availability") == "Do Not Contact"
    )
    stats["total_requests"] = len(requests)
    stats["open_requests"] = sum(
        1 for x in requests if x.get("status") in OPEN_REQUEST_STATUSES
    )
    stats["emergency_requests"] = sum(
        1
        for x in requests
        if x.get("urgency") == "Emergency"
        and x.get("status") not in ("Fulfilled", "Cancelled", "Expired")
    )
    stats["total_donations"] = len(donations)
    stats["fulfilled_requests"] = sum(
        1 for x in requests if x.get("status") == "Fulfilled"
    )

    month_key = _today().strftime("%Y-%m")
    stats["donations_this_month"] = sum(
        1
        for x in donations
        if str(x.get("donation_date") or "").startswith(month_key)
    )

    for group in BLOOD_GROUPS:
        matching = [
            x for x in donors
            if x.get("blood_group") == group
        ]
        stats["groups"][group]["total"] = len(matching)
        stats["groups"][group]["available"] = sum(
            1
            for x in matching
            if x.get("availability") == "Available"
            and x.get("status") == "Active"
        )

    return stats


def create_blood_request(context, data):
    _guard(context)
    db = get_database()
    item = dict(data or {})

    for key in ("action", "record_id", "_csrf"):
        item.pop(key, None)

    if item.get("blood_group") not in BLOOD_GROUPS:
        raise ValueError("Please select a valid blood group.")

    item["patient_name"] = str(
        item.get("patient_name") or ""
    ).strip()
    if not item["patient_name"]:
        raise ValueError("Patient name is required.")

    item["status"] = "Pending"
    item["request_id"] = _next_id(
        db,
        REQUEST_COLLECTION,
        "request_id",
        "SBR-2026-",
        6,
    )
    item["branch_name"] = str(
        item.get("branch_name") or ""
    ).strip()
    item["required_date"] = str(
        item.get("required_date") or _today().isoformat()
    )[:10]
    item["quantity"] = _safe_int(item.get("quantity"), 1)
    item["created_at"] = _now()
    item["updated_at"] = _now()
    item["created_by"] = context.get("user_id")
    item["created_by_role"] = ROLE

    result = db[REQUEST_COLLECTION].insert_one(item)
    _audit(
        context,
        "CREATE",
        "blood_request",
        item["request_id"],
        after=item,
    )
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
            for k in (
                "request_id",
                "patient_name",
                "blood_group",
                "hospital_name",
                "branch_name",
                "district",
                "upazila",
                "mobile",
                "status",
                "urgency",
            )
        ]

    for key in (
        "blood_group",
        "branch_name",
        "district",
        "upazila",
        "urgency",
        "status",
    ):
        value = str(filters.get(key) or "").strip()
        if value:
            query[key] = value

    return [
        clean(x)
        for x in db[REQUEST_COLLECTION]
        .find(query)
        .sort("_id", -1)
        .limit(1000)
    ]


def update_blood_request(context, record_id, data):
    _guard(context)
    db = get_database()
    oid = _oid(record_id)
    before = db[REQUEST_COLLECTION].find_one({"_id": oid})

    if not before:
        raise ValueError("Blood request not found.")

    item = dict(data or {})
    for key in ("action", "record_id", "_id", "_csrf"):
        item.pop(key, None)

    if "blood_group" in item and item["blood_group"] not in BLOOD_GROUPS:
        item["blood_group"] = before.get("blood_group")

    item["updated_at"] = _now()
    db[REQUEST_COLLECTION].update_one(
        {"_id": oid},
        {"$set": item},
    )
    after = db[REQUEST_COLLECTION].find_one({"_id": oid})

    _audit(
        context,
        "UPDATE",
        "blood_request",
        before.get("request_id"),
        before=before,
        after=after,
    )

    if item.get("blood_group") or item.get("district") or item.get("branch_name"):
        create_matches_for_request(
            context,
            str(before.get("_id")),
        )


def set_request_status(context, record_id, status):
    _guard(context)
    if status not in REQUEST_STATUS_OPTIONS:
        raise ValueError("Invalid request status.")

    db = get_database()
    oid = _oid(record_id)
    before = db[REQUEST_COLLECTION].find_one({"_id": oid})
    if not before:
        raise ValueError("Blood request not found.")

    db[REQUEST_COLLECTION].update_one(
        {"_id": oid},
        {
            "$set": {
                "status": status,
                "updated_at": _now(),
            }
        },
    )
    after = db[REQUEST_COLLECTION].find_one({"_id": oid})
    _audit(
        context,
        "REQUEST_STATUS_CHANGE",
        "blood_request",
        before.get("request_id"),
        before=before,
        after=after,
    )


def _compatibility_allowed(request_group, donor_group):
    # This module deliberately does NOT make a transfusion compatibility
    # decision. Matching starts with exact blood-group requests; broader
    # compatibility rules must be configured/approved by medical authority.
    return request_group == donor_group


def _match_score(request_item, donor):
    score = 0
    if request_item.get("blood_group") == donor.get("blood_group"):
        score += 60
    if (
        request_item.get("branch_name")
        and request_item.get("branch_name")
        == donor.get("branch_name")
    ):
        score += 20
    elif (
        request_item.get("district")
        and request_item.get("district")
        == donor.get("district")
    ):
        score += 10

    if donor.get("availability") == "Available":
        score += 15

    if donor.get("verification_status") == "Verified":
        score += 10

    if request_item.get("urgency") == "Emergency" and donor.get(
        "emergency_available"
    ) in (True, "true", "True", "1", 1, "yes", "Yes"):
        score += 15

    return score


def create_matches_for_request(context, record_id):
    _guard(context)
    db = get_database()
    oid = _oid(record_id)
    request_item = db[REQUEST_COLLECTION].find_one({"_id": oid})

    if not request_item:
        request_item = db[REQUEST_COLLECTION].find_one(
            {"request_id": str(record_id)}
        )

    if not request_item:
        raise ValueError("Blood request not found.")

    request_id = request_item.get("request_id")
    group = request_item.get("blood_group")

    donors = db[DONOR_COLLECTION].find(
        {
            "blood_group": group,
            "status": "Active",
            "verification_status": "Verified",
            "availability": "Available",
        }
    )

    created = 0
    seen = set()

    for donor in donors:
        donor_key = str(donor.get("_id"))
        if donor_key in seen:
            continue
        seen.add(donor_key)

        if not _compatibility_allowed(
            request_item.get("blood_group"),
            donor.get("blood_group"),
        ):
            continue

        existing = db[MATCH_COLLECTION].find_one(
            {
                "request_id": request_id,
                "donor_id": donor.get("donor_id"),
            }
        )
        if existing:
            continue

        db[MATCH_COLLECTION].insert_one(
            {
                "match_id": _next_id(
                    db,
                    MATCH_COLLECTION,
                    "match_id",
                    "MATCH-",
                    7,
                ),
                "request_id": request_id,
                "request_record_id": request_item.get("_id"),
                "donor_id": donor.get("donor_id"),
                "donor_record_id": donor.get("_id"),
                "donor_name": donor.get("donor_name"),
                "blood_group": donor.get("blood_group"),
                "branch_name": donor.get("branch_name"),
                "district": donor.get("district"),
                "score": _match_score(request_item, donor),
                "response": "Pending",
                "created_at": _now(),
            }
        )
        created += 1

    if created:
        new_status = (
            "Emergency Escalated"
            if request_item.get("urgency") == "Emergency"
            else "Matching"
        )
        db[REQUEST_COLLECTION].update_one(
            {"_id": request_item["_id"]},
            {
                "$set": {
                    "status": new_status,
                    "matched_at": _now(),
                    "updated_at": _now(),
                }
            },
        )

    _audit(
        context,
        "MATCHING_RUN",
        "blood_request",
        request_id,
        after={"matches_created": created},
    )
    return created


def confirm_match(context, match_id):
    _guard(context)
    db = get_database()
    match = db[MATCH_COLLECTION].find_one(
        {"match_id": str(match_id)}
    )
    if not match:
        raise ValueError("Match not found.")

    db[MATCH_COLLECTION].update_one(
        {"_id": match["_id"]},
        {
            "$set": {
                "response": "Confirmed",
                "confirmed_at": _now(),
            }
        },
    )
    db[REQUEST_COLLECTION].update_one(
        {"request_id": match.get("request_id")},
        {
            "$set": {
                "status": "Donor Confirmed",
                "confirmed_donor_id": match.get("donor_id"),
                "updated_at": _now(),
            }
        },
    )

    _audit(
        context,
        "CONFIRM_DONOR_MATCH",
        "blood_request_match",
        match_id,
        after={"response": "Confirmed"},
    )


def request_match_summary(context):
    _guard(context)
    db = get_database()
    rows = []

    for item in db[MATCH_COLLECTION].find(
        {}
    ).sort("score", -1).limit(30):
        rows.append(clean(item))

    return rows


def recent_donations(context):
    _guard(context)
    db = get_database()
    return [
        clean(x)
        for x in db[DONATION_COLLECTION]
        .find({})
        .sort("_id", -1)
        .limit(20)
    ]


def recent_audit_logs(context):
    _guard(context)
    db = get_database()
    return [
        clean(x)
        for x in db[AUDIT_COLLECTION]
        .find({})
        .sort("_id", -1)
        .limit(30)
    ]
