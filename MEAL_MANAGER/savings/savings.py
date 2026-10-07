from flask import Blueprint,render_template,request,session
from pathlib import Path
HTML_DIR = Path(__file__).resolve().parent
bp=Blueprint("meal_manager_savings",__name__,url_prefix="/meal_manager/savings",template_folder=str(HTML_DIR))
@bp.route("/",methods=["GET","POST"])
def meal_manager_savings(): return render_template("MEAL_MANAGER/savings/savings.html",user=session.get("meal_manager_user",{}))
