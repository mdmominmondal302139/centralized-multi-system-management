from __future__ import annotations
from datetime import datetime,timezone,date
import importlib.util
from pathlib import Path
DB_FILE=Path(__file__).resolve().parents[1]/"config"/"branch_officer_database.py"
spec=importlib.util.spec_from_file_location("member_transfer_request_db",DB_FILE)
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

def current_branch_name(c):
    b=guard(c); client,d=db.get_mongo()
    try:return branch_name(d,b)
    finally:client.close()
def active_members(c):
    b=guard(c); client,d=db.get_mongo()
    try:
        q={"branch_id":b,"role":"MEMBER","$or":[{"active":True},{"is_active":True},{"status":{"$in":["Active","active","ACTIVE","Enabled","enabled"]}}]}
        return [{"id":str(x["_id"]),"name":x.get("name") or x.get("full_name") or x.get("fullName") or x.get("username") or "","username":x.get("username","")} for x in d.members.find(q).sort("name",1)]
    finally:client.close()
def target_branches(c):
    b=guard(c); client,d=db.get_mongo()
    try:
        out=[]
        for x in d.branches.find({}):
            i=str(x.get("_id")) if x.get("_id") is not None else str(x.get("id") or x.get("branch_id") or "")
            if not i or i==b: continue
            if str(x.get("status","Active")).lower() in {"inactive","locked","closed","suspended","disabled"}: continue
            out.append({"id":i,"name":x.get("name") or x.get("branch_name") or i})
        return sorted(out,key=lambda z:str(z["name"]).lower())
    finally:client.close()
def create(c,f):
    b=guard(c); mid=str(f.get("member_id","")).strip(); to=str(f.get("to_branch_id","")).strip(); eff=str(f.get("effective_date","")).strip()
    reason=str(f.get("reason","")).strip(); note=str(f.get("note","")).strip()
    if not mid or not to or not eff: raise ValueError("Member, target branch and effective date are required.")
    try: date.fromisoformat(eff)
    except: raise ValueError("Effective date is invalid.")
    if to==b: raise ValueError("Target branch must be different from your current branch.")
    mo=oid(mid); to_o=oid(to)
    if not mo: raise ValueError("Invalid member ID.")
    client,d=db.get_mongo()
    try:
        m=d.members.find_one({"_id":mo,"branch_id":b,"role":"MEMBER","$or":[{"active":True},{"is_active":True},{"status":{"$in":["Active","active","ACTIVE","Enabled","enabled"]}}]})
        if not m: raise ValueError("Selected member is not an active member of your branch.")
        target=d.branches.find_one({"_id":to_o}) if to_o else None
        if not target: target=d.branches.find_one({"id":to})
        if not target: target=d.branches.find_one({"branch_id":to})
        if not target or str(target.get("status","Active")).lower() in {"inactive","locked","closed","suspended","disabled"}: raise ValueError("Target branch was not found or is not active.")
        if d.member_transfer_requests.find_one({"member_id":mid,"status":"PENDING"}): raise ValueError("This member already has a pending transfer request.")
        t=now(); r=d.member_transfer_requests.insert_one({"member_id":mid,"member_name":m.get("name") or m.get("full_name") or m.get("fullName") or m.get("username") or "","member_username":m.get("username",""),"from_branch_id":b,"to_branch_id":to,"requested_by":c.get("user_id"),"requested_by_username":c.get("username"),"request_date":t,"effective_date":eff,"reason":reason,"note":note,"status":"PENDING","accepted_by":None,"accepted_at":None,"rejected_by":None,"rejected_at":None,"rejection_reason":None,"completed_by":None,"completed_at":None,"created_at":t,"updated_at":t})
        tid=str(r.inserted_id); d.member_transfer_audit.insert_one({"transfer_id":tid,"action":"CREATED","actor_id":c.get("user_id"),"actor_username":c.get("username"),"member_id":mid,"from_branch_id":b,"to_branch_id":to,"created_at":t}); return tid
    finally: client.close()
