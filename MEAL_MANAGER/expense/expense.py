from flask import Blueprint,render_template,request,session
from pathlib import Path
HTML_DIR = Path(__file__).resolve().parent
bp=Blueprint("meal_manager_expense",__name__,url_prefix="/meal_manager/expense",template_folder=str(HTML_DIR))
@bp.route("/",methods=["GET","POST"])
def meal_manager_expense(): return render_template("MEAL_MANAGER/expense/expense.html",user=session.get("meal_manager_user",{}))
