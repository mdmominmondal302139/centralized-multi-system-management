from datetime import datetime, timezone
from bson import ObjectId
from werkzeug.security import generate_password_hash
from DATABASE.mongodb import get_database, clean
ROLE="SYSTEM_SUPER_ADMINISTRATOR"
COLLECTION="users"

def _guard(c):
    if not isinstance(c,dict) or c.get("role")!=ROLE: raise PermissionError("Access denied.")

def list_records(c,filters=None):
    _guard(c); query={"role":"MEMBER"}
    term=str((filters or {}).get("search") or "").strip()
    if term:
        import re
        rx={"$regex":re.escape(term),"$options":"i"}
        query={"role":"MEMBER","$or":[{"full_name":rx},{"username":rx},{"email":rx},{"phone":rx},{"branch":rx},{"department":rx}]}
    rows=list(get_database()[COLLECTION].find(query).sort("_id",-1).limit(500))
    return [clean(x) for x in rows]

def create_record(c,data):
    _guard(c); d=dict(data or {}); password=str(d.pop("password","") or ""); d["role"]=str(d.get("role") or "Member").upper(); d["status"]=str(d.get("status") or "Active");
    if not d.get("full_name") or not d.get("username") or not password: raise ValueError("Full Name, Username and Password are required.")
    if len(password)<8: raise ValueError("Password must be at least 8 characters.")
    db=get_database(); username=str(d["username"]).strip(); email=str(d.get("email") or "").strip().lower();
    if db[COLLECTION].find_one({"$or":[{"username":username}]+([{"email":email}] if email else [])}): raise ValueError("Username or email already exists.")
    d["username"]=username; d["email"]=email; d["password_hash"]=generate_password_hash(password); d["created_at"]=datetime.now(timezone.utc); d["updated_at"]=datetime.now(timezone.utc); d["created_by"]=c.get("user_id"); r=db[COLLECTION].insert_one(d); return str(r.inserted_id)

def update_record(c,record_id,data):
    _guard(c); oid=ObjectId(record_id) if ObjectId.is_valid(str(record_id)) else record_id; d=dict(data or {}); d.pop("password",None); d.pop("_id",None); d["updated_at"]=datetime.now(timezone.utc); r=get_database()[COLLECTION].update_one({"_id":oid},{"$set":d}); return r.modified_count or r.matched_count

def delete_record(c,record_id):
    _guard(c); oid=ObjectId(record_id) if ObjectId.is_valid(str(record_id)) else record_id; return get_database()[COLLECTION].delete_one({"_id":oid}).deleted_count
