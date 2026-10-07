from flask import Blueprint,request,jsonify,send_file,abort
from pathlib import Path
import importlib.util
BASE=Path(__file__).resolve().parents[1];S=Path(__file__).resolve().parent/"services.py";sp=importlib.util.spec_from_file_location("svc",S);svc=importlib.util.module_from_spec(sp);sp.loader.exec_module(svc)
bp=Blueprint("member_meal",__name__,url_prefix="/member")
def c():return {"role":request.headers.get("X-Role") or request.args.get("role","MEMBER"),"user_id":request.headers.get("X-User-ID") or request.args.get("user_id")}
@bp.get("/meal")
def page():
 if not svc.ok(c()):abort(403)
 return send_file(BASE/"HTML/member_meal.html")
@bp.get("/api/meal")
def listing():
 if not svc.ok(c()):abort(403)
 return jsonify(svc.list_records(c(),request.args.get("month")))
@bp.post("/api/meal")
def add():
 if not svc.ok(c()):abort(403)
 return jsonify(svc.save(c(),request.get_json(silent=True) or {}))
@bp.put("/api/meal/<rid>")
def edit(rid):
 if not svc.ok(c()):abort(403)
 return jsonify(svc.update(c(),rid,request.get_json(silent=True) or {}))
@bp.delete("/api/meal/<rid>")
def remove(rid):
 if not svc.ok(c()):abort(403)
 return jsonify({"ok":svc.delete(c(),rid)})
