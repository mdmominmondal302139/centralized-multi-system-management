from datetime import datetime, timezone, date, timedelta
from bson import ObjectId
from DATABASE.mongodb import get_database, clean
ROLE = 'SYSTEM_SUPER_ADMINISTRATOR'
COLLECTION = 'meal_management'

def _guard(context):
    if not isinstance(context, dict) or context.get("role") != ROLE:
        raise PermissionError("Access denied.")

def _record_date(value):
    # MongoDB records may store date as a native datetime/date, not only a string.
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    value = str(value or "").strip()
    # Support ISO date strings and ISO timestamps (including timezone suffixes).
    if value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except Exception:
            pass
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except Exception:
            pass
    return None

def _record_value(x, *keys):
    for k in keys:
        v = x.get(k)
        if v is not None and str(v).strip() != "":
            return v
    return ""

def list_records(context, filters=None):
    _guard(context); filters=filters or {}; db=get_database(); query={}
    for key in ("search","date","month","member","branch","status"):
        value=str(filters.get(key) or "").strip()
        if not value: continue
        if key=="search":
            query["$or"]=[{k:{"$regex":value,"$options":"i"}} for k in ("name","username","email","phone","note","source","member_name","branch_name","type","meal_type","status")]
        elif key=="month": query["date"]={"$regex":f"^{value}"}
        elif key=="member": query["$or"]=[{"member_name":{"$regex":value,"$options":"i"}},{"member_id":{"$regex":value,"$options":"i"}}]
        elif key=="branch": query["branch_name"]={"$regex":value,"$options":"i"}
        else: query[key]=value
    return [clean(x) for x in db[COLLECTION].find(query).sort("_id",-1).limit(500)]

def create_record(context, data):
    _guard(context)
    item = dict(data or {})
    now = datetime.now(timezone.utc)
    item.update({"created_at":now,"updated_at":now,"created_by":context.get("user_id"),"created_by_role":ROLE})
    r = get_database()[COLLECTION].insert_one(item)
    return str(r.inserted_id)

def save_or_update_record(context, data):
    """Keep one row per date + member + branch + meal type.

    Re-saving the same selection updates the existing record instead of adding a duplicate.
    Any older duplicate records with the same identity are removed.
    """
    _guard(context)
    item = dict(data or {})
    target_date = _record_date(_record_value(item, "date"))
    target_member = str(_record_value(item, "member_name", "member", "name", "username")).strip().casefold()
    target_branch = str(_record_value(item, "branch_name", "branch")).strip().casefold()
    target_type = str(_record_value(item, "type", "meal_type")).strip().casefold()
    if not target_date or not target_member or not target_branch or not target_type:
        return create_record(context, item)

    collection = get_database()[COLLECTION]
    matches = []
    for old in collection.find({}).sort("_id", 1):
        old_date = _record_date(_record_value(old, "date"))
        old_member = str(_record_value(old, "member_name", "member", "name", "username")).strip().casefold()
        old_branch = str(_record_value(old, "branch_name", "branch")).strip().casefold()
        old_type = str(_record_value(old, "type", "meal_type")).strip().casefold()
        if (old_date, old_member, old_branch, old_type) == (target_date, target_member, target_branch, target_type):
            matches.append(old)

    now = datetime.now(timezone.utc)
    item.update({"updated_at": now, "created_by": context.get("user_id"), "created_by_role": ROLE})
    if not matches:
        item.setdefault("created_at", now)
        result = collection.insert_one(item)
        return str(result.inserted_id)

    keep = matches[-1]
    item.pop("_id", None)
    item.setdefault("created_at", keep.get("created_at", now))
    collection.update_one({"_id": keep["_id"]}, {"$set": item})
    duplicate_ids = [x["_id"] for x in matches[:-1]]
    if duplicate_ids:
        collection.delete_many({"_id": {"$in": duplicate_ids}})
    return str(keep["_id"])


def update_record(context, record_id, data):
    _guard(context)
    oid=ObjectId(record_id) if ObjectId.is_valid(str(record_id)) else record_id
    item=dict(data or {}); item.pop("_id",None); item.pop("action",None); item.pop("record_id",None); item.pop("return_month",None)
    item["updated_at"]=datetime.now(timezone.utc)
    r=get_database()[COLLECTION].update_one({"_id":oid},{"$set":item})
    return r.modified_count or r.matched_count

def delete_record(context, record_id):
    _guard(context)
    oid=ObjectId(record_id) if ObjectId.is_valid(str(record_id)) else record_id
    collection = get_database()[COLLECTION]
    target = collection.find_one({"_id": oid})
    if not target:
        return 0
    target_date = _record_date(_record_value(target, "date"))
    target_member = str(_record_value(target, "member_name", "member", "name", "username")).strip().casefold()
    target_branch = str(_record_value(target, "branch_name", "branch")).strip().casefold()
    target_type = str(_record_value(target, "type", "meal_type")).strip().casefold()
    if target_date and target_member and target_branch and target_type:
        ids = []
        for old in collection.find({}):
            identity = (
                _record_date(_record_value(old, "date")),
                str(_record_value(old, "member_name", "member", "name", "username")).strip().casefold(),
                str(_record_value(old, "branch_name", "branch")).strip().casefold(),
                str(_record_value(old, "type", "meal_type")).strip().casefold(),
            )
            if identity == (target_date, target_member, target_branch, target_type):
                ids.append(old["_id"])
        r = collection.delete_many({"_id": {"$in": ids}})
        return r.deleted_count
    r=collection.delete_one({"_id":oid})
    return r.deleted_count

def _normalized_record(x):
    d = _record_date(_record_value(x, "date"))
    return {
        "id": str(x.get("_id","")),
        "date_obj": d,
        "date": d.strftime("%d.%m.%Y") if d else str(_record_value(x,"date")),
        "day": d.strftime("%a") if d else "",
        "member": str(_record_value(x,"member_name","member","name","username")),
        "branch": str(_record_value(x,"branch_name","branch")),
        "meal_type": str(_record_value(x,"type","meal_type")),
        "meal": str(_record_value(x,"quantity","meal")),
        "meal_charge": str(_record_value(x,"meal_charge")),
        "rice_charge": str(_record_value(x,"rice_charge")),
        "note": str(_record_value(x,"note"))
    }

def month_rows(context, month_key, search="", member=""):
    _guard(context)
    y,m = [int(v) for v in month_key.split("-")]
    start = date(y,m,1)
    last = calendar_month_days(y,m)
    end = date(y,m,last)
    raw = get_database()[COLLECTION].find({}).sort("_id",1)
    by_day = {}
    needle = str(search or "").strip().casefold()
    member_needle = str(member or "").strip().casefold()
    # Collapse legacy duplicates but preserve separate rows for different members,
    # branches, dates, or meal types. Since raw records are sorted oldest-first,
    # the newest matching record is the one retained.
    unique_records = {}
    for x in raw:
        r = _normalized_record(x)
        d = r["date_obj"]
        if not d or d < start or d > end:
            continue
        if member_needle and r["member"].casefold() != member_needle:
            continue
        if needle and not any(needle in str(r[k]).casefold() for k in ("member","branch","meal_type","date")):
            continue
        identity = (d, r["member"].strip().casefold(), r["branch"].strip().casefold(), r["meal_type"].strip().casefold())
        unique_records[identity] = r
    for r in unique_records.values():
        by_day.setdefault(r["date_obj"], []).append(r)
    for day_records in by_day.values():
        day_records.sort(key=lambda r: (r["member"].casefold(), r["branch"].casefold(), r["meal_type"].casefold()))

    rows=[]
    cur=start
    while cur <= end:
        records=by_day.get(cur, [])
        rows.append({"date":cur.strftime("%d.%m.%Y"),"day":cur.strftime("%a"),"status":"ON" if records else "OFF","records":records})
        cur += timedelta(days=1)
    return rows

def calendar_month_days(year, month):
    import calendar
    return calendar.monthrange(year, month)[1]

def available_months(context, limit=12):
    _guard(context)
    found=set()
    for x in get_database()[COLLECTION].find({}, {"date":1}):
        d=_record_date(x.get("date"))
        if d:
            found.add(d.strftime("%Y-%m"))
    found.add(date.today().strftime("%Y-%m"))
    keys=sorted(found, reverse=True)
    return [{"key":k,"label":datetime.strptime(k,"%Y-%m").strftime("%B %Y")} for k in keys[:limit]]

def _member_mobile_map():
    db=get_database()
    result={}
    for x in db["users"].find({}, {"full_name":1,"name":1,"username":1,"mobile":1,"phone":1,"mobile_number":1,"contact_number":1}):
        name=str(_record_value(x,"full_name","name","username")).strip()
        if not name:
            continue
        mobile=str(_record_value(x,"mobile","mobile_number","phone","contact_number")).strip()
        result[name.casefold()]=mobile
    return result

def member_status_rows(context, limit=500):
    _guard(context)
    mobile_map=_member_mobile_map()
    grouped={}
    for x in get_database()[COLLECTION].find({}, {"date":1,"member_name":1,"member":1,"name":1,"username":1,"member_id":1,"branch_name":1,"branch":1}).sort("_id",1):
        d=_record_date(_record_value(x,"date"))
        name=str(_record_value(x,"member_name","member","name","username")).strip()
        if not d or not name:
            continue
        key=(name.casefold(), d.strftime("%Y-%m"))
        grouped[key]={"member":name,"mobile":mobile_map.get(name.casefold(),"—"),"month":d.strftime("%Y-%m"),"label":d.strftime("%B %Y")}
    rows=sorted(grouped.values(), key=lambda x:(x["month"],x["member"].casefold()), reverse=True)
    return rows[:limit]
