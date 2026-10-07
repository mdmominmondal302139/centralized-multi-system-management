from datetime import datetime, timezone
from bson import ObjectId
from DATABASE.mongodb import get_database, clean
ROLE="SYSTEM_SUPER_ADMINISTRATOR"
COLLECTION="system_information_directory"
def guard(c):
 if c.get("role")!=ROLE: raise PermissionError("Access denied.")
def list_records(c,filters=None):
 guard(c); return [clean(x) for x in get_database()[COLLECTION].find({}).sort("_id",-1).limit(500)]
def create_record(c,data):
 guard(c); d=dict(data or {}); d.update({"created_at":datetime.now(timezone.utc),"updated_at":datetime.now(timezone.utc),"created_by":c.get("user_id")}); return str(get_database()[COLLECTION].insert_one(d).inserted_id)
def delete_record(c,rid):
 guard(c); oid=ObjectId(rid) if ObjectId.is_valid(str(rid)) else rid; return get_database()[COLLECTION].delete_one({"_id":oid}).deleted_count
