from __future__ import annotations
from datetime import datetime,timezone,date
import importlib.util
from pathlib import Path
DB_FILE=Path(__file__).resolve().parents[1]/"config"/"branch_officer_database.py"
spec=importlib.util.spec_from_file_location("member_transfer_sent_details_db",DB_FILE)
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

def get(c,tid):
    b=guard(c); o=oid(tid)
    if not o:return None
    client,d=db.get_mongo()
    try:
        x=d.member_transfer_requests.find_one({"_id":o,"from_branch_id":b})
        if not x:return None
        x["_id"]=str(x["_id"]); x["from_branch_name"]=branch_name(d,x.get("from_branch_id")); x["to_branch_name"]=branch_name(d,x.get("to_branch_id")); return x
    finally:client.close()
def cancel(c,tid):
    b=guard(c); o=oid(tid)
    if not o:raise ValueError("Invalid transfer ID.")
    client,d=db.get_mongo()
    try:
        x=d.member_transfer_requests.find_one({"_id":o,"from_branch_id":b,"status":"PENDING"})
        if not x:raise ValueError("Only your own pending request can be cancelled.")
        t=now(); d.member_transfer_requests.update_one({"_id":o,"status":"PENDING"},{"$set":{"status":"CANCELLED","updated_at":t}}); d.member_transfer_audit.insert_one({"transfer_id":tid,"action":"CANCELLED","actor_id":c.get("user_id"),"actor_username":c.get("username"),"member_id":x.get("member_id"),"from_branch_id":b,"to_branch_id":x.get("to_branch_id"),"created_at":t})
    finally:client.close()
