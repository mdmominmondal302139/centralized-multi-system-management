from config.database import db
from models.saving import Saving
from bson import ObjectId
from datetime import datetime
from services.storage_service import StorageService
savings_collection=db["savings"];saving_locks_collection=db["saving_locks"];users_collection=db["users"]
class SavingService:
    @staticmethod
    def is_member_locked(uid):
        try:u=users_collection.find_one({"_id":ObjectId(str(uid))})
        except Exception:u=users_collection.find_one({"_id":str(uid)})
        return bool(u and (u.get("locked") is True or u.get("suspended") is True))
    @staticmethod
    def get_month_key(date):d=datetime.strptime(date,"%d-%m-%Y");return f"{d.year}-{d.month:02d}"
    @staticmethod
    def is_month_locked(uid,key):return saving_locks_collection.find_one({"user_id":str(uid),"month_key":str(key)}) is not None
    @staticmethod
    def toggle_month_lock(uid,key):
        q={"user_id":str(uid),"month_key":str(key)};old=saving_locks_collection.find_one(q)
        if old:saving_locks_collection.delete_one({"_id":old["_id"]});return False
        saving_locks_collection.insert_one(q);return True
    @staticmethod
    def add_saving(uid,amount,description,date,time):
        uid=str(uid)
        if SavingService.is_member_locked(uid):return False,"Your account is locked. You cannot add or edit savings."
        try:key=SavingService.get_month_key(date);float(amount)
        except Exception:return False,"Invalid amount or date. Use DD-MM-YYYY for date."
        if SavingService.is_month_locked(uid,key):return False,"This month is locked. Unlock it before editing/deleting."
        data=Saving(uid,amount,description,date,time).to_dict();ok,msg=StorageService.can_add(uid,data)
        if not ok:return False,msg
        savings_collection.insert_one(data);return True,"Record added successfully."
    @staticmethod
    def get_month_summaries(uid):
        out={};uid=str(uid)
        for r in savings_collection.find({"user_id":uid}):
            try:key=SavingService.get_month_key(r.get("date",""));d=datetime.strptime(key,"%Y-%m")
            except Exception:continue
            out.setdefault(key,{"month_key":key,"month":d.strftime("%B"),"year":d.year,"total":0,"locked":SavingService.is_month_locked(uid,key)})["total"]+=float(r.get("amount",0))
        return sorted(out.values(),key=lambda x:x["month_key"],reverse=True)
    @staticmethod
    def get_month_savings(uid,key):return [r for r in savings_collection.find({"user_id":str(uid)}).sort("_id",-1) if SavingService.get_month_key(r.get("date",""))==str(key)]
    @staticmethod
    def update_saving(sid,uid,amount,description,date,time):
        uid=str(uid)
        if SavingService.is_member_locked(uid):return False,"Your account is locked. You cannot edit savings.",None,None
        try:
            old=savings_collection.find_one({"_id":ObjectId(sid),"user_id":uid})
            if not old:return False,"Saving not found.",None,None
            ok1=SavingService.is_month_locked(uid,SavingService.get_month_key(old["date"]));ok2=SavingService.is_month_locked(uid,SavingService.get_month_key(date))
            if ok1 or ok2:return False,"This month is locked. Unlock it before editing/deleting.",None,None
            new=Saving(uid,amount,description,date,time).to_dict();savings_collection.update_one({"_id":old["_id"]},{"$set":new});return True,"Record updated successfully.",old,new
        except Exception:return False,"Invalid Saving ID, amount or date.",None,None
    @staticmethod
    def delete_saving(sid,uid):
        uid=str(uid)
        if SavingService.is_member_locked(uid):return False,"Your account is locked. You cannot delete savings.",None
        try:
            old=savings_collection.find_one({"_id":ObjectId(sid),"user_id":uid})
            if not old:return False,"Saving not found.",None
            if SavingService.is_month_locked(uid,SavingService.get_month_key(old["date"])):return False,"This month is locked. Unlock it before editing/deleting.",None
            savings_collection.delete_one({"_id":old["_id"]});return True,"Record permanently deleted.",old
        except Exception:return False,"Invalid Saving ID.",None
