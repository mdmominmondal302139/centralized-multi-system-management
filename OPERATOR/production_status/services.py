ROLE="OPERATOR"
def update(ctx,data):
    if ctx.get("role")!=ROLE or not ctx.get("user_id"): raise PermissionError("Operator authentication is required.")
    return {"ok":True,"record_type":"production_status","data":data}
