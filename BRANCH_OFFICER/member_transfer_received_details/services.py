from __future__ import annotations
from datetime import datetime,timezone,date
import importlib.util
from pathlib import Path
DB_FILE=Path(__file__).resolve().parents[1]/"config"/"branch_officer_database.py"
spec=importlib.util.spec_from_file_location("member_transfer_received_details_db",DB_FILE)
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
        x=d.member_transfer_requests.find_one({"_id":o,"to_branch_id":b})
        if not x:return None
        x["_id"]=str(x["_id"]); x["from_branch_name"]=branch_name(d,x.get("from_branch_id")); x["to_branch_name"]=branch_name(d,x.get("to_branch_id")); return x
    finally:client.close()
def decision(c,tid,status,reason=""):
    b=guard(c); o=oid(tid)
    if not o:raise ValueError("Invalid transfer ID.")
    client,d=db.get_mongo()
    try:
        x=d.member_transfer_requests.find_one({"_id":o,"to_branch_id":b,"status":"PENDING"})
        if not x:raise ValueError("Pending received transfer request not found.")
        if status=="REJECTED" and not reason.strip():raise ValueError("Rejection reason is required.")
        t=now(); u={"status":status,"updated_at":t}
        if status=="ACCEPTED":u.update({"accepted_by":c.get("user_id"),"accepted_at":t})
        else:u.update({"rejected_by":c.get("user_id"),"rejected_at":t,"rejection_reason":reason.strip()})
        d.member_transfer_requests.update_one({"_id":o},{"$set":u}); d.member_transfer_audit.insert_one({"transfer_id":tid,"action":status,"actor_id":c.get("user_id"),"actor_username":c.get("username"),"member_id":x.get("member_id"),"from_branch_id":x.get("from_branch_id"),"to_branch_id":b,"created_at":t,"note":reason.strip()})
    finally:client.close()
def accept(c,tid): return decision(c,tid,"ACCEPTED")
def reject(c,tid,reason): return decision(c,tid,"REJECTED",reason)
def complete(c,tid):
    b=guard(c); o=oid(tid)
    if not o:raise ValueError("Invalid transfer ID.")
    client,d=db.get_mongo()
    try:
        x=d.member_transfer_requests.find_one({"_id":o,"to_branch_id":b,"status":"ACCEPTED"})
        if not x:raise ValueError("Only an accepted request can be completed.")
        mo=oid(x.get("member_id"))
        if not mo:raise ValueError("Invalid member ID.")
        m=d.members.find_one({"_id":mo,"branch_id":x.get("from_branch_id"),"role":"MEMBER"})
        if not m:raise ValueError("Member is no longer in the requesting branch.")
        t=now()
        u=d.members.update_one({"_id":mo,"branch_id":x.get("from_branch_id"),"role":"MEMBER"},{"$set":{"branch_id":b,"updated_at":t}})
        if u.modified_count!=1:raise ValueError("Member transfer could not be completed.")
        d.member_branch_history.insert_one({"member_id":x.get("member_id"),"from_branch_id":x.get("from_branch_id"),"to_branch_id":b,"transfer_id":tid,"from_date":x.get("request_date"),"to_date":t,"created_at":t})
        d.member_transfer_requests.update_one({"_id":o},{"$set":{"status":"COMPLETED","completed_by":c.get("user_id"),"completed_at":t,"updated_at":t}})
        d.member_transfer_audit.insert_one({"transfer_id":tid,"action":"COMPLETED","actor_id":c.get("user_id"),"actor_username":c.get("username"),"member_id":x.get("member_id"),"from_branch_id":x.get("from_branch_id"),"to_branch_id":b,"created_at":t})
    finally:client.close()
