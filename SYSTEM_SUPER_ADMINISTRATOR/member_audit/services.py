from datetime import datetime, timezone
from bson import ObjectId
from DATABASE.mongodb import get_database, clean
ROLE = 'SYSTEM_SUPER_ADMINISTRATOR'
COLLECTION = 'user_audit'

def _guard(context):
    if not isinstance(context, dict) or context.get("role") != ROLE:
        raise PermissionError("Access denied.")

def list_records(context, filters=None):
    _guard(context); filters=filters or {}; db=get_database(); query={}
    for key in ("search","date","month","member","branch","status"):
        value=str(filters.get(key) or "").strip()
        if not value: continue
        if key=="search": query["$or"]=[{k:{"$regex":value,"$options":"i"}} for k in ("name","username","email","phone","note","source","member_name","branch_name","type","status")]
        elif key=="month": query["date"]={"$regex":f"^{value}"}
        elif key=="member": query["$or"]=[{"member_name":{"$regex":value,"$options":"i"}},{"member_id":{"$regex":value,"$options":"i"}}]
        elif key=="branch": query["branch_name"]={"$regex":value,"$options":"i"}
        else: query[key]=value
    return [clean(x) for x in db[COLLECTION].find(query).sort("_id",-1).limit(500)]

def create_record(context, data):
    _guard(context); item=dict(data or {}); item.update({"created_at":datetime.now(timezone.utc),"updated_at":datetime.now(timezone.utc),"created_by":context.get("user_id"),"created_by_role":ROLE}); r=get_database()[COLLECTION].insert_one(item); return str(r.inserted_id)

def update_record(context, record_id, data):
    _guard(context); oid=ObjectId(record_id) if ObjectId.is_valid(str(record_id)) else record_id; item=dict(data or {}); item.pop("_id",None); item["updated_at"]=datetime.now(timezone.utc); r=get_database()[COLLECTION].update_one({"_id":oid},{"$set":item}); return r.modified_count or r.matched_count

def delete_record(context, record_id):
    _guard(context); oid=ObjectId(record_id) if ObjectId.is_valid(str(record_id)) else record_id; r=get_database()[COLLECTION].delete_one({"_id":oid}); return r.deleted_count
