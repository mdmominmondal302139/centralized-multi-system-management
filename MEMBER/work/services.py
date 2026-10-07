from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
ROOT=Path(__file__).resolve().parents[1]
def ok(c):return isinstance(c,dict) and c.get("role")=="MEMBER" and bool(c.get("user_id"))
def db():
 s=spec_from_file_location("db",ROOT/"config/member_database.py");m=module_from_spec(s);s.loader.exec_module(m);return m.get_database()
def list_work(c):
 if not ok(c):raise PermissionError("Access denied")
 try:
  client,d=db();rows=list(d.member_work.find({"user_id":c["user_id"]},{"_id":0}).sort("created_at",-1));client.close();return rows
 except Exception:return []
def update_status(c,work_id,status):
 if not ok(c):raise PermissionError("Access denied")
 from bson import ObjectId
 client,d=db();r=d.member_work.update_one({"_id":ObjectId(work_id),"user_id":c["user_id"]},{"$set":{"status":status}});client.close();return r.modified_count==1
