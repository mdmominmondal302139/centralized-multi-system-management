"""BRANCH_OFFICER Home page service only."""
from __future__ import annotations
from datetime import datetime, timezone
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("branch_officer_database_home", Path(__file__).resolve().parents[1]/"config"/"branch_officer_database.py")
db = importlib.util.module_from_spec(spec); spec.loader.exec_module(db)

ROLE = "BRANCH_OFFICER"

def summary(context):
    if not isinstance(context, dict) or context.get("role") != ROLE:
        raise PermissionError("Access denied.")
    branch_id = str(context.get("branch_id") or "").strip()
    if not branch_id:
        raise PermissionError("A branch assignment is required.")
    today = datetime.now(timezone.utc).date().isoformat()
    client, database = db.get_mongo()
    try:
        def total(collection, amount_field="amount"):
            value = database[collection].aggregate([
                {"$match":{"branch_id":branch_id, "date":today}},
                {"$group":{"_id":None,"total":{"$sum":{"$convert":{"input":f"${amount_field}","to":"double","onError":0,"onNull":0}}}}}
            ])
            row = next(iter(value), None)
            return float(row["total"]) if row else 0.0
        return {
            "date": today,
            "income": total("income"),
            "expense": total("expenses"),
            "meal": database["meals"].count_documents({"branch_id":branch_id,"date":today}),
            "savings": total("savings"),
            "pending_work": database["works"].count_documents({"branch_id":branch_id,"status":{"$in":["Pending","Started","In Progress","On Hold"]}}),
            "completed_work": database["works"].count_documents({"branch_id":branch_id,"status":"Completed"}),
            "recent_income": list(database["income"].find({"branch_id":branch_id}).sort("created_at",-1).limit(5)),
            "recent_expense": list(database["expenses"].find({"branch_id":branch_id}).sort("created_at",-1).limit(5)),
            "recent_meal": list(database["meals"].find({"branch_id":branch_id}).sort("created_at",-1).limit(5)),
            "recent_savings": list(database["savings"].find({"branch_id":branch_id}).sort("created_at",-1).limit(5)),
            "recent_work": list(database["works"].find({"branch_id":branch_id}).sort("created_at",-1).limit(5)),
        }
    finally:
        client.close()
