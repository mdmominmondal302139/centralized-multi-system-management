from config.database import db
from models.expense import Expense
from bson import ObjectId
from datetime import datetime
from services.storage_service import StorageService

expenses_collection=db["expenses"]; expense_locks_collection=db["expense_locks"]; users_collection=db["users"]
class ExpenseService:
    @staticmethod
    def _uid(v):return str(v)
    @staticmethod
    def is_member_locked(user_id):
        uid=str(user_id)
        try:u=users_collection.find_one({"_id":ObjectId(uid)})
        except Exception:u=users_collection.find_one({"_id":uid})
        return bool(u and (u.get("locked") is True or u.get("suspended") is True))
    @staticmethod
    def get_month_key(date):
        d=datetime.strptime(date,"%d-%m-%Y");return f"{d.year}-{d.month:02d}"
    @staticmethod
    def is_month_locked(user_id,month_key):return expense_locks_collection.find_one({"user_id":str(user_id),"month_key":str(month_key)}) is not None
    @staticmethod
    def toggle_month_lock(user_id,month_key):
        q={"user_id":str(user_id),"month_key":str(month_key)};old=expense_locks_collection.find_one(q)
        if old:expense_locks_collection.delete_one({"_id":old["_id"]});return False
        expense_locks_collection.insert_one(q);return True
    @staticmethod
    def add_expense(user_id,amount,category,description,date,time):
        uid=str(user_id)
        if ExpenseService.is_member_locked(uid):return False,"Your account is locked. You cannot add or edit expense."
        try:key=ExpenseService.get_month_key(date);float(amount)
        except Exception:return False,"Invalid amount or date. Use DD-MM-YYYY for date."
        if ExpenseService.is_month_locked(uid,key):return False,"This month is locked. Unlock it before editing/deleting."
        data=Expense(uid,amount,category,description,date,time).to_dict();ok,msg=StorageService.can_add(uid,data)
        if not ok:return False,msg
        expenses_collection.insert_one(data);return True,"Record added successfully."
    @staticmethod
    def get_month_summaries(user_id):
        uid=str(user_id);out={}
        for r in expenses_collection.find({"user_id":uid}):
            try:key=ExpenseService.get_month_key(r.get("date",""));d=datetime.strptime(key,"%Y-%m")
            except Exception:continue
            out.setdefault(key,{"month_key":key,"month":d.strftime("%B"),"year":d.year,"month_number":d.month,"total":0,"locked":ExpenseService.is_month_locked(uid,key)})["total"]+=float(r.get("amount",0))
        return sorted(out.values(),key=lambda x:x["month_key"],reverse=True)
    @staticmethod
    def get_month_expenses(user_id,month_key):
        uid=str(user_id);return [r for r in expenses_collection.find({"user_id":uid}).sort("_id",-1) if ExpenseService.get_month_key(r.get("date",""))==str(month_key)]
    @staticmethod
    def update_expense(expense_id,user_id,amount,category,description,date,time):
        uid=str(user_id)
        if ExpenseService.is_member_locked(uid):return False,"Your account is locked. You cannot edit expense.",None,None
        try:
            old=expenses_collection.find_one({"_id":ObjectId(expense_id),"user_id":uid})
            if not old:return False,"Expense not found.",None,None
            old_key=ExpenseService.get_month_key(old["date"]);new_key=ExpenseService.get_month_key(date)
            if ExpenseService.is_month_locked(uid,old_key) or ExpenseService.is_month_locked(uid,new_key):return False,"This month is locked. Unlock it before editing/deleting.",None,None
            new=Expense(uid,amount,category,description,date,time).to_dict();new["_id"]=old["_id"]
            expenses_collection.update_one({"_id":old["_id"]},{"$set":new});return True,"Record updated successfully.",old,new
        except Exception:return False,"Invalid Expense ID, amount or date.",None,None
    @staticmethod
    def delete_expense(expense_id,user_id):
        uid=str(user_id)
        if ExpenseService.is_member_locked(uid):return False,"Your account is locked. You cannot delete expense.",None
        try:
            old=expenses_collection.find_one({"_id":ObjectId(expense_id),"user_id":uid})
            if not old:return False,"Expense not found.",None
            if ExpenseService.is_month_locked(uid,ExpenseService.get_month_key(old["date"])):return False,"This month is locked. Unlock it before editing/deleting.",None
            expenses_collection.delete_one({"_id":old["_id"]});return True,"Record permanently deleted.",old
        except Exception:return False,"Invalid Expense ID.",None
