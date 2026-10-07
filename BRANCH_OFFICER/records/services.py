"""BRANCH_OFFICER Records page service only."""
from __future__ import annotations
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("branch_officer_database_records", Path(__file__).resolve().parents[1]/"config"/"branch_officer_database.py")
db = importlib.util.module_from_spec(spec); spec.loader.exec_module(db)
ROLE = "BRANCH_OFFICER"

def _branch(context):
    if not isinstance(context, dict) or context.get("role") != ROLE:
        raise PermissionError("Access denied.")
    branch_id = str(context.get("branch_id") or "").strip()
    if not branch_id:
        raise PermissionError("A branch assignment is required.")
    return branch_id

def history(context, record_type="all", period="all", date_value="", search=""):
    branch_id = _branch(context)
    client, database = db.get_mongo()
    try:
        mapping = {"income":("income","Income"),"expense":("expenses","Expense"),"meal":("meals","Meal"),"savings":("savings","Savings"),"work":("works","Work")}
        chosen = mapping if record_type == "all" else {record_type:mapping.get(record_type)}
        result=[]
        for key, spec_item in chosen.items():
            if not spec_item: continue
            collection,label=spec_item
            query={"branch_id":branch_id}
            if date_value: query["date"]=date_value
            elif period=="today":
                from datetime import datetime, timezone
                query["date"]=datetime.now(timezone.utc).date().isoformat()
            elif period=="this_month":
                from datetime import datetime, timezone
                query["date"]={"$regex":f"^{datetime.now(timezone.utc).strftime('%Y-%m')}"}
            if search:
                query["$or"]=[{"source":{"$regex":search,"$options":"i"}},{"purpose":{"$regex":search,"$options":"i"}},{"member_name":{"$regex":search,"$options":"i"}},{"task_title":{"$regex":search,"$options":"i"}},{"work_id":{"$regex":search,"$options":"i"}}]
            for row in database[collection].find(query).sort("created_at",-1).limit(300):
                row["_id"]=str(row["_id"]); row["record_type"]=label; result.append(row)
        result.sort(key=lambda x:str(x.get("created_at","")),reverse=True)
        return result[:500]
    finally:
        client.close()
