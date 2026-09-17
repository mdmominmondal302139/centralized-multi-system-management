from config.database import db
from models.income import Income
from bson import ObjectId
from datetime import datetime
from services.storage_service import StorageService

incomes_collection = db["incomes"]
income_locks_collection = db["income_locks"]
users_collection = db["users"]

class IncomeService:
    @staticmethod
    def _uid(v): return str(v)
    @staticmethod
    def is_member_locked(user_id):
        uid = IncomeService._uid(user_id)
        try: u = users_collection.find_one({"_id": ObjectId(uid)})
        except Exception: u = users_collection.find_one({"_id": uid})
        return bool(u and (u.get("locked") is True or u.get("suspended") is True))
    @staticmethod
    def get_month_key(date):
        d = datetime.strptime(date, "%d-%m-%Y"); return f"{d.year}-{d.month:02d}"
    @staticmethod
    def is_month_locked(user_id, month_key):
        return income_locks_collection.find_one({"user_id": IncomeService._uid(user_id), "month_key": str(month_key)}) is not None
    @staticmethod
    def toggle_month_lock(user_id, month_key):
        uid = IncomeService._uid(user_id); q={"user_id":uid,"month_key":str(month_key)}
        old=income_locks_collection.find_one(q)
        if old: income_locks_collection.delete_one({"_id":old["_id"]}); return False
        income_locks_collection.insert_one(q); return True
    @staticmethod
    def add_income(user_id, amount, income_type, received_method, source, description, date, time):
        uid=IncomeService._uid(user_id)
        if IncomeService.is_member_locked(uid): return False,"Your account is locked. You cannot add or edit income."
        try: key=IncomeService.get_month_key(date); float(amount)
        except Exception: return False,"Invalid amount or date. Use DD-MM-YYYY for date."
        if IncomeService.is_month_locked(uid,key): return False,"This month is locked. Unlock it before editing/deleting."
        data=Income(uid,amount,income_type,received_method,source,description,date,time).to_dict()
        ok,msg=StorageService.can_add(uid,data)
        if not ok:return False,msg
        incomes_collection.insert_one(data); return True,"Record added successfully."
    @staticmethod
    def get_month_summaries(user_id):
        uid=IncomeService._uid(user_id); out={}
        for r in incomes_collection.find({"user_id":uid}):
            try:key=IncomeService.get_month_key(r.get("date","")); d=datetime.strptime(key,"%Y-%m")
            except Exception:continue
            out.setdefault(key,{"month_key":key,"month":d.strftime("%B"),"year":d.year,"month_number":d.month,"total":0,"locked":IncomeService.is_month_locked(uid,key)})["total"]+=float(r.get("amount",0))
        return sorted(out.values(),key=lambda x:x["month_key"],reverse=True)
    @staticmethod
    def get_month_incomes(user_id,month_key):
        uid=IncomeService._uid(user_id); return [r for r in incomes_collection.find({"user_id":uid}).sort("_id",-1) if IncomeService.get_month_key(r.get("date",""))==str(month_key)]
    @staticmethod
    def delete_month(user_id,month_key):
        uid=IncomeService._uid(user_id)
        if IncomeService.is_member_locked(uid):return False,"Your account is locked. You cannot delete income."
        if IncomeService.is_month_locked(uid,month_key):return False,"This month is locked. Unlock it before editing/deleting."
        records=IncomeService.get_month_incomes(uid,month_key)
        if not records:return False,"No income found."
        incomes_collection.delete_many({"_id":{"$in":[r["_id"] for r in records]}}); return True,"Record permanently deleted."
    @staticmethod
    def delete_income(income_id,user_id):
        uid=IncomeService._uid(user_id)
        if IncomeService.is_member_locked(uid):return False,"Your account is locked. You cannot delete income."
        try:
            r=incomes_collection.find_one({"_id":ObjectId(income_id),"user_id":uid})
            if not r:return False,"Income not found."
            if IncomeService.is_month_locked(uid,IncomeService.get_month_key(r["date"])):return False,"This month is locked. Unlock it before editing/deleting."
            incomes_collection.delete_one({"_id":r["_id"]}); return True,"Record permanently deleted.",r
        except Exception:return False,"Invalid Income ID.",None
