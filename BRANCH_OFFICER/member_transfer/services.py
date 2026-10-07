from __future__ import annotations
from datetime import datetime,timezone,date
import importlib.util
from pathlib import Path
DB_FILE=Path(__file__).resolve().parents[1]/"config"/"branch_officer_database.py"
spec=importlib.util.spec_from_file_location("member_transfer_db",DB_FILE)
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

def dashboard(c):
    b=guard(c); client,d=db.get_mongo()
    try:
        q={"$or":[{"from_branch_id":b},{"to_branch_id":b}]}
        return {"pending_sent":d.member_transfer_requests.count_documents({"from_branch_id":b,"status":"PENDING"}),"pending_received":d.member_transfer_requests.count_documents({"to_branch_id":b,"status":"PENDING"}),"accepted":d.member_transfer_requests.count_documents({**q,"status":"ACCEPTED"}),"rejected":d.member_transfer_requests.count_documents({**q,"status":"REJECTED"}),"completed":d.member_transfer_requests.count_documents({**q,"status":"COMPLETED"})}
    finally: client.close()
