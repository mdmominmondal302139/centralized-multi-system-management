from __future__ import annotations
from datetime import datetime,timezone,date
import importlib.util
from pathlib import Path
DB_FILE=Path(__file__).resolve().parents[1]/"config"/"branch_officer_database.py"
spec=importlib.util.spec_from_file_location("member_transfer_history_db",DB_FILE)
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

def history(c,filters=None):
    b=guard(c); filters=filters or {}; client,d=db.get_mongo()
    try:
        scope={"$or":[{"from_branch_id":b},{"to_branch_id":b}]}
        clauses=[scope,{"status":{"$in":["COMPLETED","REJECTED","CANCELLED"]}}]
        if filters.get("status") in {"COMPLETED","REJECTED","CANCELLED"}:
            clauses.append({"status":filters["status"]})
        if filters.get("branch") and filters["branch"]!=b:
            clauses.append({"$or":[{"from_branch_id":filters["branch"]},{"to_branch_id":filters["branch"]}]})
        if filters.get("search"):
            clauses.append({"member_name":{"$regex":re.escape(filters["search"]),"$options":"i"}})
        if filters.get("from_date"):
            try: clauses.append({"updated_at":{"$gte":datetime.fromisoformat(filters["from_date"]).replace(tzinfo=timezone.utc)}})
            except ValueError: pass
        if filters.get("to_date"):
            try: clauses.append({"updated_at":{"$lt":datetime.fromisoformat(filters["to_date"]).replace(tzinfo=timezone.utc)+__import__("datetime").timedelta(days=1)}})
            except ValueError: pass
        query={"$and":clauses}
        out=[]
        for x in d.member_transfer_requests.find(query).sort("updated_at",-1).limit(500):
            x["_id"]=str(x["_id"]); x["from_branch_name"]=branch_name(d,x.get("from_branch_id")); x["to_branch_name"]=branch_name(d,x.get("to_branch_id")); out.append(x)
        branches=[]
        for x in d.branches.find({}):
            i=str(x.get("_id")) if x.get("_id") is not None else str(x.get("id") or x.get("branch_id") or "")
            if i and i!=b: branches.append({"id":i,"name":x.get("name") or x.get("branch_name") or i})
        return {"rows":out,"branches":sorted(branches,key=lambda z:str(z["name"]).lower())}
    finally: client.close()
