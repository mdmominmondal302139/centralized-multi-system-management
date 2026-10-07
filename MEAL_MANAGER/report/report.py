from flask import Blueprint,render_template,request,session
from pathlib import Path
HTML_DIR = Path(__file__).resolve().parent
bp=Blueprint("meal_manager_report",__name__,url_prefix="/meal_manager/meal_reports",template_folder=str(HTML_DIR))
@bp.route("/",methods=["GET","POST"])
def meal_manager_meal_reports(): return render_template("MEAL_MANAGER/report/report.html",user=session.get("meal_manager_user",{}))
