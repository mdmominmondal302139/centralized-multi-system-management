from pathlib import Path
import importlib.util
from datetime import datetime, timezone
ROLE="MEAL_MANAGER"
s=importlib.util.spec_from_file_location("meal_entry_db",Path(__file__).resolve().parents[1]/"config"/"database.py"); dbm=importlib.util.module_from_spec(s); s.loader.exec_module(dbm)
def _scope(c):
    if not isinstance(c,dict) or c.get("role")!=ROLE: raise PermissionError("Access denied: Meal Manager role is required.")
    if not c.get("branch_id") and not c.get("branch_name"): raise PermissionError("Assigned Branch is required.")
    return c.get("branch_id"),c.get("branch_name")
def _user(c): return {"user_id":str(c.get("user_id","")),"username":str(c.get("username",""))}
def _branch(c):
    bid,bn=_scope(c); return {"branch_id":bid} if bid else {"branch_name":bn}
def now(): return datetime.now(timezone.utc)
MEAL_TYPES=["Breakfast","Lunch","Dinner","Extra"]
def search_members(c,q=""):
    b=_branch(c);client,db=dbm.get_mongo()
    try:
        q=str(q or "").strip();f=dict(b)
        if q:f["$or"]=[{"name":{"$regex":q,"$options":"i"}},{"role":{"$regex":q,"$options":"i"}},{"mobile":{"$regex":q,"$options":"i"}},{"username":{"$regex":q,"$options":"i"}}]
        return list(db["users"].find(f,{"password":0,"password_hash":0}).limit(50))
    finally:client.close()
def save(c,d,rid=None):
    if d.get("meal_type") not in MEAL_TYPES:raise ValueError("Invalid Meal Type.")
    bid,bn=_scope(c);client,db=dbm.get_mongo()
    try:
        x={k:d.get(k,"") for k in ("member_id","member_name","member_role","member_mobile","meal_type","month","year","date","time","description")};x.update({"branch_id":bid,"branch_name":bn,"created_by":_user(c),"role":ROLE,"updated_at":now()})
        if rid:db["meal_entries"].update_one({"_id":rid,"branch_id":bid},{"$set":x})
        else:db["meal_entries"].insert_one(x)
    finally:client.close()
