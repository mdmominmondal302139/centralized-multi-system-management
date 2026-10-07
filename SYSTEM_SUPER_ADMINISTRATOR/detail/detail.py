from flask import Blueprint, render_template, request, session, redirect, url_for
from pathlib import Path
import importlib.util
ROLE="SYSTEM_SUPER_ADMINISTRATOR"
BASE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("services",BASE/"services.py"); service=importlib.util.module_from_spec(spec); spec.loader.exec_module(service)
bp=Blueprint("system_super_administrator_detail_bp",__name__,url_prefix="/system_super_administrator/information-directory/detail")
def ctx(): return {"role":session.get("role"),"user_id":session.get("user_id")}
@bp.route("/",methods=["GET","POST"])
def page():
 if session.get("authenticated") is not True or session.get("role")!="SYSTEM_SUPER_ADMINISTRATOR": return redirect(url_for("login"))
 message=None; error=None
 try:
  if request.method=="POST":
   a=request.form.get("action","save")
   if a=="delete": service.delete_record(ctx(),request.form.get("record_id","")); message="Deleted successfully."
   else: service.create_record(ctx(),dict(request.form)); message="Saved successfully."
  records=service.list_records(ctx(),request.args.to_dict())
 except Exception as exc: records=[]; error=str(exc)
 return render_template("SYSTEM_SUPER_ADMINISTRATOR/detail/detail.html",records=records,message=message,error=error,session=session)
