from datetime import datetime
from DATABASE.mongodb import get_database, clean
ROLE="MEMBER"
def context_ok(c): return isinstance(c,dict) and c.get("role")==ROLE and bool(c.get("user_id"))
def _ok(c): return context_ok(c)
def _rows(name,c):
 if not _ok(c): raise PermissionError("Access denied")
 db=get_database(); return [clean(x) for x in db[name].find({"user_id":c.get("user_id")}).sort("_id",-1).limit(100)]
def dashboard(c):
 return {"income":_rows("member_income",c),"expense":_rows("member_expense",c),"savings":_rows("member_savings",c),"meals":_rows("member_meals",c),"records":_rows("member_records",c)}


def summary(c):
    if not context_ok(c):
        raise PermissionError("Access denied")
    from datetime import datetime
    now=datetime.now()
    def total(name):
        rows=_rows(name,c)
        total=0.0
        for row in rows:
            value=row.get("amount", row.get("total", row.get("value", 0)))
            try: total += float(value or 0)
            except (TypeError,ValueError): pass
        return total
    return {"income":total("member_income"),"expense":total("member_expense"),"savings":total("member_savings"),"month":now.strftime("%Y-%m")}
