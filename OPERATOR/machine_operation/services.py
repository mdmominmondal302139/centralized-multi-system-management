ROLE="OPERATOR"
def get_assignment(ctx):
    if ctx.get("role")!=ROLE or not ctx.get("user_id"): raise PermissionError("Operator authentication is required.")
    return {"machine":None,"operation":None,"style_order":None,"buyer_po":None}
