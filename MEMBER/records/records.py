from flask import Blueprint,request,jsonify,send_file,abort
from pathlib import Path
import importlib.util
BASE=Path(__file__).resolve().parents[1];S=Path(__file__).resolve().parent/"services.py";sp=importlib.util.spec_from_file_location("svc",S);svc=importlib.util.module_from_spec(sp);sp.loader.exec_module(svc)
bp=Blueprint("member_records",__name__,url_prefix="/member")
def c():return {"role":request.headers.get("X-Role") or request.args.get("role","MEMBER"),"user_id":request.headers.get("X-User-ID") or request.args.get("user_id"),"name":request.args.get("name",""),"mobile":request.args.get("mobile","")}
@bp.get("/records")
def page():
 if not svc.ok(c()):abort(403)
 return send_file(BASE/"HTML/member_records.html")
@bp.get("/api/records")
def listing():
 if not svc.ok(c()):abort(403)
 return jsonify(svc.list_months(c(),request.args.get("month")))
@bp.post("/api/records")
def save():
 if not svc.ok(c()):abort(403)
 return jsonify(svc.upsert_month(c(),request.get_json(silent=True) or {}))
@bp.delete("/api/records/<month>")
def remove(month):
 if not svc.ok(c()):abort(403)
 return jsonify({"ok":svc.delete_month(c(),month)})
@bp.get("/records/<month>/download")
def download(month):
 if not svc.ok(c()):abort(403)
 f=svc.export_doc(c(),month);return send_file(f,as_attachment=True,download_name=f"member_{c()["user_id"]}_{month}.docx",mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
