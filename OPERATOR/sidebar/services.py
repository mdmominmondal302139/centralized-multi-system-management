from datetime import datetime, timezone
ROLE="OPERATOR"
def context(session): return {"role":session.get("role"),"user_id":session.get("user_id"),"branch_id":session.get("branch_id"),"section_id":session.get("section_id")}
def authorized(ctx): return bool(ctx.get("user_id")) and ctx.get("role")==ROLE
def summary(ctx):
    if not authorized(ctx): raise PermissionError("Operator authentication is required.")
    return {"ok":True,"today_work":0,"target":0,"completed":0,"status":"Pending","timestamp":datetime.now(timezone.utc).isoformat()}
