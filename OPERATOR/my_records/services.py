ROLE="OPERATOR"
def list_records(ctx):
    if ctx.get("role")!=ROLE or not ctx.get("user_id"): raise PermissionError("Operator authentication is required.")
    return []
