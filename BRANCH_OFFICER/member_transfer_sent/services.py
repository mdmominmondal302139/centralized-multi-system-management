from __future__ import annotations
from datetime import datetime,timezone,date
import importlib.util
from pathlib import Path
DB_FILE=Path(__file__).resolve().parents[1]/"config"/"branch_officer_database.py"
spec=importlib.util.spec_from_file_location("member_transfer_sent_db",DB_FILE)
if spec is None or spec.loader is None: raise RuntimeError("Unable to load database.")
db=importlib.util.module_from_spec(spec); spec.loader.exec_module(db)
ROLE="BRANCH_OFFICER"
def guard(c):
    if not isinstance(c,dict) or c.get("role")!=ROLE or not c.get("branch_id"): raise PermissionError("Branch Officer access denied.")
    return str(c["branch_id"])
def now(): return datetime.now(timezone.utc)
def oid(v):
    from bson import ObjectId
    try:return ObjectId(str(v))
    except:return None
def branch_name(database,bid):
    o=oid(bid); x=database.branches.find_one({"_id":o}) if o else None
    if not x:x=database.branches.find_one({"id":str(bid)})
    if not x:x=database.branches.find_one({"branch_id":str(bid)})
    return (x or {}).get("name") or (x or {}).get("branch_name") or str(bid)

def sent(c):
    b=guard(c); client,d=db.get_mongo()
    try:
        out=[]
        for x in d.member_transfer_requests.find({"from_branch_id":b}).sort("created_at",-1):
            x["_id"]=str(x["_id"]); x["from_branch_name"]=branch_name(d,x.get("from_branch_id")); x["to_branch_name"]=branch_name(d,x.get("to_branch_id")); out.append(x)
        return out
    finally:client.close()
