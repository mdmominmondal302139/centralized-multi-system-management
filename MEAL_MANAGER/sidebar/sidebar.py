from flask import Blueprint,render_template,request,session
from pathlib import Path
HTML_DIR = Path(__file__).resolve().parent
bp=Blueprint("meal_manager_sidebar",__name__,url_prefix="/meal_manager/income",template_folder=str(HTML_DIR))
@bp.route("/",methods=["GET","POST"])
def meal_manager_income(): return render_template("MEAL_MANAGER/sidebar/sidebar.html",user=session.get("meal_manager_user",{}))
