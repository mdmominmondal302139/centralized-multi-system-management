from flask import Blueprint,request,jsonify,send_file,abort
from pathlib import Path
import importlib.util
BASE=Path(__file__).resolve().parents[1];S=Path(__file__).resolve().parent/"services.py";sp=importlib.util.spec_from_file_location("svc",S);svc=importlib.util.module_from_spec(sp);sp.loader.exec_module(svc)
bp=Blueprint("member_work_alternate",__name__,url_prefix="/member")
def c():return {"role":request.headers.get("X-Role") or request.args.get("role","MEMBER"),"user_id":request.headers.get("X-User-ID") or request.args.get("user_id")}
@bp.get("/work")
def page():
 if not svc.ok(c()):abort(403)
 return send_file(BASE/"HTML/member_work.html")
@bp.get("/api/work")
def listing():
 if not svc.ok(c()):abort(403)
 return jsonify(svc.list_work(c()))
@bp.put("/api/work/<wid>")
def update(wid):
 if not svc.ok(c()):abort(403)
 return jsonify({"ok":svc.update_status(c(),wid,(request.get_json(silent=True) or {}).get("status",""))})
