from datetime import datetime, timezone
ROLE="OPERATOR"
def save(ctx,data):
    if ctx.get("role")!=ROLE or not ctx.get("user_id"): raise PermissionError("Operator authentication is required.")
    return {"ok":True,"record_type":"production_entry","user_id":ctx["user_id"],"data":data,"created_at":datetime.now(timezone.utc).isoformat()}
