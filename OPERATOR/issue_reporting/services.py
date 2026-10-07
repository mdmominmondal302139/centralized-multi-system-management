ROLE="OPERATOR"
def save(ctx,data):
    if ctx.get("role")!=ROLE or not ctx.get("user_id"): raise PermissionError("Operator authentication is required.")
    return {"ok":True,"record_type":"issue_report","data":data}
