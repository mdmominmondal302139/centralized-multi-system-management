import os, importlib.util
from pathlib import Path
from flask import Flask, session, redirect, url_for
from dotenv import load_dotenv

BASE=Path(__file__).resolve().parent
load_dotenv(BASE/".env")
app=Flask(__name__, static_folder="STATIC", static_url_path="/static", template_folder=str(BASE))
app.secret_key=os.getenv("SECRET_KEY","change-this-secret")

def load_blueprints():
    # Authentication first.
    for rel in ["AUTHENTICATION/login/login.py","AUTHENTICATION/logout/logout.py"]:
        p=BASE/rel; spec=importlib.util.spec_from_file_location(p.stem+"_module",p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); app.register_blueprint(m.bp)
    # Every page is independently registered from its own route file.
    for role in [p for p in BASE.iterdir() if p.is_dir() and p.name.isupper() and p.name not in {"DATABASE","AUTHENTICATION","STATIC","DOCUMENTATION"}]:
        for page in role.iterdir():
            if not page.is_dir(): continue
            route=page/(page.name+".py")
            if not route.exists(): continue
            spec=importlib.util.spec_from_file_location(f"page_{role.name}_{page.name}",route); m=importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(m)
                if hasattr(m,"bp"): app.register_blueprint(m.bp)
            except Exception as exc:
                print(f"[WARN] Could not load {route}: {exc}")

load_blueprints()

@app.route("/")
def root():
    if session.get("authenticated"):
        return redirect({"SYSTEM_SUPER_ADMINISTRATOR":"/system_super_administrator","BRANCH_OFFICER":"/branch_officer/home","ACCOUNT_OFFICER":"/account_officer/home","MEAL_MANAGER":"/meal_manager/home","OPERATOR":"/operator/dashboard","MEMBER":"/member/home"}.get(session.get("role"),"/login"))
    return redirect("/login")

if __name__=="__main__":
    app.run(host="127.0.0.1",port=int(os.getenv("PORT","5000")),debug=True)
