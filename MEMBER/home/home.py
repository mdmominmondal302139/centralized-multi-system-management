from flask import Blueprint, request, jsonify, send_file, abort, session
from pathlib import Path
import importlib.util

BASE=Path(__file__).resolve().parents[1]
S=Path(__file__).resolve().parent/"services.py"
sp=importlib.util.spec_from_file_location("member_home_service", S)
svc=importlib.util.module_from_spec(sp)
sp.loader.exec_module(svc)

bp=Blueprint("member_home", __name__, url_prefix="/member")

def ctx():
    return {
        "role": session.get("role") or request.headers.get("X-Role") or request.args.get("role", "MEMBER"),
        "user_id": session.get("user_id") or request.headers.get("X-User-ID") or request.args.get("user_id"),
        "name": session.get("name") or request.args.get("name", ""),
        "mobile": session.get("mobile") or request.args.get("mobile", ""),
    }

@bp.get("/home")
@bp.get("/home/")
def home():
    if not svc.context_ok(ctx()):
        abort(403)
    return send_file(Path(__file__).resolve().parent/"home.html")

@bp.get("/api/home")
def api_home():
    c=ctx()
    if not svc.context_ok(c):
        abort(403)
    return jsonify(svc.summary(c))
