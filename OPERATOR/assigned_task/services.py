ROLE="OPERATOR"
def list_tasks(ctx):
    if ctx.get("role")!=ROLE or not ctx.get("user_id"): raise PermissionError("Operator authentication is required.")
    return []
def update_task(ctx,data):
    if ctx.get("role")!=ROLE or not ctx.get("user_id"): raise PermissionError("Operator authentication is required.")
    return {"ok":True,"record_type":"assigned_task_update","data":data}
