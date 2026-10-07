from pathlib import Path
import importlib.util
from datetime import datetime, timezone
ROLE="MEAL_MANAGER"
s=importlib.util.spec_from_file_location("member_meal_records_db",Path(__file__).resolve().parents[1]/"config"/"database.py"); dbm=importlib.util.module_from_spec(s); s.loader.exec_module(dbm)
def _scope(c):
    if not isinstance(c,dict) or c.get("role")!=ROLE: raise PermissionError("Access denied: Meal Manager role is required.")
    if not c.get("branch_id") and not c.get("branch_name"): raise PermissionError("Assigned Branch is required.")
    return c.get("branch_id"),c.get("branch_name")
def _user(c): return {"user_id":str(c.get("user_id","")),"username":str(c.get("username",""))}
def _branch(c):
    bid,bn=_scope(c); return {"branch_id":bid} if bid else {"branch_name":bn}
def now(): return datetime.now(timezone.utc)
def get_month(c,member_id,year,month):
    b=_branch(c);client,db=dbm.get_mongo()
    try:return list(db["meal_entries"].find({**b,"role":ROLE,"member_id":str(member_id),"year":int(year),"month":str(month)}).sort("date",1))
    finally:client.close()
