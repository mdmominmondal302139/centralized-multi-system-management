from flask import Blueprint, request, jsonify, send_file, abort
from pathlib import Path
import importlib.util
BASE=Path(__file__).resolve().parents[1];S=Path(__file__).resolve().parent/"services.py";sp=importlib.util.spec_from_file_location("svc",S);svc=importlib.util.module_from_spec(sp);sp.loader.exec_module(svc)
bp=Blueprint("member_profile",__name__,url_prefix="/member")
def ctx():return {"role":request.headers.get("X-Role") or request.args.get("role","MEMBER"),"user_id":request.headers.get("X-User-ID") or request.args.get("user_id"),"name":request.args.get("name",""),"username":request.args.get("username",""),"mobile":request.args.get("mobile",""),"branch_id":request.args.get("branch_id","")}
@bp.route("/profile",methods=["GET"])
def profile():
 if not svc.context_ok(ctx()):abort(403)
 return send_file(BASE/"HTML/member_profile.html")
@bp.get("/api/profile")
def get_profile():
 c=ctx();
 if not svc.context_ok(c):abort(403)
 return jsonify(svc.get_profile(c))
@bp.post("/api/profile")
def update_profile():
 c=ctx();
 if not svc.context_ok(c):abort(403)
 return jsonify(svc.update_profile(c,request.get_json(silent=True) or {}))
