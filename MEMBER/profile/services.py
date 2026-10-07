from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
ROOT=Path(__file__).resolve().parents[1]
def context_ok(c): return isinstance(c,dict) and c.get("role")=="MEMBER" and bool(c.get("user_id"))
def _db():
    s=spec_from_file_location("db",ROOT/"config/member_database.py"); m=module_from_spec(s); s.loader.exec_module(m); return m.get_database()
def get_profile(c):
    if not context_ok(c): raise PermissionError("MEMBER role and user_id are required")
    try:
        client,db=_db(); doc=db.members.find_one({"user_id":c["user_id"]},{"_id":0}) or {} ; client.close()
    except Exception: doc={}
    return {"user_id":c["user_id"],"name":doc.get("name",c.get("name","")),"username":doc.get("username",c.get("username","")),"member_id":doc.get("member_id",c["user_id"]),"mobile":doc.get("mobile",c.get("mobile","")),"branch":doc.get("branch",c.get("branch_id","")),"role":"MEMBER","status":doc.get("status","Active")}
def update_profile(c,data):
    if not context_ok(c): raise PermissionError("Access denied")
    allowed={k:data[k] for k in ("name","mobile","username") if k in data}
    if not allowed: return get_profile(c)
    client,db=_db(); db.members.update_one({"user_id":c["user_id"]},{"$set":allowed},upsert=True); client.close(); return get_profile(c)
