from pathlib import Path
import importlib.util
from datetime import datetime, timezone
ROLE="MEAL_MANAGER"
s=importlib.util.spec_from_file_location("income_db",Path(__file__).resolve().parents[1]/"config"/"database.py"); dbm=importlib.util.module_from_spec(s); s.loader.exec_module(dbm)
def _scope(c):
    if not isinstance(c,dict) or c.get("role")!=ROLE: raise PermissionError("Access denied: Meal Manager role is required.")
    if not c.get("branch_id") and not c.get("branch_name"): raise PermissionError("Assigned Branch is required.")
    return c.get("branch_id"),c.get("branch_name")
def _user(c): return {"user_id":str(c.get("user_id","")),"username":str(c.get("username",""))}
def _branch(c):
    bid,bn=_scope(c); return {"branch_id":bid} if bid else {"branch_name":bn}
def now(): return datetime.now(timezone.utc)
COLLECTION="income"
def list_records(c,q=""):
    _scope(c); client,db=dbm.get_mongo()
    try:
        f={**_user(c),"role":ROLE}; q=str(q or "").strip()
        if q:f["$or"]=[{"income_type":{"$regex":q,"$options":"i"}},{"source":{"$regex":q,"$options":"i"}},{"note":{"$regex":q,"$options":"i"}}]
        return list(db[COLLECTION].find(f).sort("date",-1))
    finally:client.close()
def save(c,d,rid=None):
    _scope(c); client,db=dbm.get_mongo()
    try:
        x={k:d.get(k,"") for k in ("amount","income_type","received_method","source","date","time","note")}; x.update(_user(c),{"role":ROLE,"updated_at":now()})
        if rid: db[COLLECTION].update_one({"_id":rid,**_user(c)},{"$set":x})
        else: db[COLLECTION].insert_one(x)
    finally:client.close()
def delete(c,rid):
    _scope(c); client,db=dbm.get_mongo()
    try:db[COLLECTION].delete_one({"_id":rid,**_user(c)})
    finally:client.close()
