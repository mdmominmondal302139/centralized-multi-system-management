from datetime import datetime
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
ROOT=Path(__file__).resolve().parents[1]
def ok(c):return isinstance(c,dict) and c.get("role")=="MEMBER" and bool(c.get("user_id"))
def db():
 s=spec_from_file_location("db",ROOT/"config/member_database.py");m=module_from_spec(s);s.loader.exec_module(m);return m.get_database()
def list_records(c,month=None):
 if not ok(c):raise PermissionError("Access denied")
 try:
  client,d=db();q={"user_id":c["user_id"]};
  if month:q["month"]=month
  rows=list(d.member_meal.find(q,{"_id":0}).sort("date",-1));client.close();return rows
 except Exception:return []
def save(c,data):
 if not ok(c):raise PermissionError("Access denied")
 x=dict(data);x["user_id"]=c["user_id"];x["updated_at"]=datetime.utcnow().isoformat();client,d=db();r=d.member_meal.insert_one(x);client.close();x["id"]=str(r.inserted_id);return x
def update(c,rid,data):
 if not ok(c):raise PermissionError("Access denied")
 from bson import ObjectId
 client,d=db();d.member_meal.update_one({"_id":ObjectId(rid),"user_id":c["user_id"]},{"$set":dict(data,updated_at=datetime.utcnow().isoformat())});row=d.member_meal.find_one({"_id":ObjectId(rid),"user_id":c["user_id"]},{"_id":0});client.close();return row
def delete(c,rid):
 if not ok(c):raise PermissionError("Access denied")
 from bson import ObjectId
 client,d=db();r=d.member_meal.delete_one({"_id":ObjectId(rid),"user_id":c["user_id"]});client.close();return r.deleted_count==1
