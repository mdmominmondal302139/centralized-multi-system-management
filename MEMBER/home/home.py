from flask import Blueprint, request, jsonify, send_file, abort, session
from pathlib import Path
import importlib.util

BASE = Path(__file__).resolve().parent
HOME_HTML = BASE / "home.html"
SERVICE_FILE = BASE / "services.py"

if not SERVICE_FILE.is_file():
    raise FileNotFoundError(f"Member home services.py not found: {SERVICE_FILE}")

spec = importlib.util.spec_from_file_location("member_home_service", SERVICE_FILE)
if spec is None or spec.loader is None:
    raise ImportError(f"Unable to load service module: {SERVICE_FILE}")

svc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(svc)

bp = Blueprint("member_home", __name__, url_prefix="/member")


def ctx():
    # Trust the authenticated session for identity. Do not accept user_id/role
    # from query parameters or request headers for record access.
    return {
        "role": session.get("role"),
        "user_id": session.get("user_id"),
        "name": session.get("name") or "Member",
        "mobile": session.get("mobile") or "",
    }


@bp.get("/home")
@bp.get("/home/")
def home():
    if not svc.context_ok(ctx()):
        abort(403)
    if not HOME_HTML.is_file():
        abort(500, description=f"Home HTML file not found: {HOME_HTML}")
    return send_file(str(HOME_HTML))


@bp.get("/api/home")
def api_home():
    c = ctx()
    if not svc.context_ok(c):
        abort(403)
    return jsonify(svc.summary(c))
