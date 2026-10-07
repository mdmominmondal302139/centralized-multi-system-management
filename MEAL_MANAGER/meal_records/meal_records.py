from flask import Blueprint,render_template,request,session
from pathlib import Path
HTML_DIR = Path(__file__).resolve().parent
bp=Blueprint("meal_manager_meal_records",__name__,url_prefix="/meal_manager/meal_records",template_folder=str(HTML_DIR))
@bp.route("/",methods=["GET","POST"])
def meal_manager_meal_records(): return render_template("MEAL_MANAGER/meal_records/meal_records.html",user=session.get("meal_manager_user",{}))
