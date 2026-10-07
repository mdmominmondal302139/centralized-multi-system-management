from pathlib import Path
import importlib.util
from datetime import datetime, timezone
ROLE="MEAL_MANAGER"
s=importlib.util.spec_from_file_location("meal_reports_db",Path(__file__).resolve().parents[1]/"config"/"database.py"); dbm=importlib.util.module_from_spec(s); s.loader.exec_module(dbm)
def _scope(c):
    if not isinstance(c,dict) or c.get("role")!=ROLE: raise PermissionError("Access denied: Meal Manager role is required.")
    if not c.get("branch_id") and not c.get("branch_name"): raise PermissionError("Assigned Branch is required.")
    return c.get("branch_id"),c.get("branch_name")
def _user(c): return {"user_id":str(c.get("user_id","")),"username":str(c.get("username",""))}
def _branch(c):
    bid,bn=_scope(c); return {"branch_id":bid} if bid else {"branch_name":bn}
def now(): return datetime.now(timezone.utc)
def report(c,month="",member="",role=""):
    b=_branch(c);client,db=dbm.get_mongo()
    try:
        f={**b,"role":ROLE}
        if month:f["month"]=month
        if member:f["member_name"]={"$regex":str(member),"$options":"i"}
        if role:f["member_role"]=role
        return list(db["meal_entries"].aggregate([{"$match":f},{"$group":{"_id":{"member_id":"$member_id","name":"$member_name","mobile":"$member_mobile","role":"$member_role","month":"$month"},"meal_count":{"$sum":1}}},{"$sort":{"meal_count":-1}}]))
    finally:client.close()
