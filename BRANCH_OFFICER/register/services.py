# ROLE: BRANCH_OFFICER
from __future__ import annotations
import os
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash
try:
    from pymongo import MongoClient
except ImportError:
    MongoClient = None
ROLE="BRANCH_OFFICER"
COLLECTION_NAME="branch_officers"
BASE_DIR=Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR/".env")
def _mongo():
    if MongoClient is None: raise RuntimeError("PyMongo is not installed. Install it with: pip install pymongo")
    uri=(os.getenv("MONGODB_URI") or "").strip()
    if not uri: raise RuntimeError("MongoDB URI is not configured. Set MONGODB_URI in .env.")
    db_name=(os.getenv("DATABASE_NAME") or "ultimate_management_system").strip()
    timeout=int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS") or "10000")
    try:
        import certifi; ca={"tlsCAFile":certifi.where()}
    except ImportError: ca={}
    client=MongoClient(uri,tls=True,serverSelectionTimeoutMS=timeout,connectTimeoutMS=timeout,socketTimeoutMS=timeout,retryWrites=True,retryReads=True,**ca)
    return client,client[db_name]
def registration_available():
    client,db=_mongo()
    try: return db[COLLECTION_NAME].find_one({"_id":{"$exists":True}}) is None
    finally: client.close()
def register_user(data):
    missing=[k for k in ("name","username","password") if not str(data.get(k,"")).strip()]
    if missing: return {"ok":False,"error":"Missing required fields: "+", ".join(missing)}
    password=str(data.get("password",""))
    if len(password)<6: return {"ok":False,"error":"Password must be at least 6 characters."}
    client,db=_mongo()
    try:
        c=db[COLLECTION_NAME]; username=str(data.get("username","")).strip(); email=str(data.get("email","")).strip()
        if c.find_one({"username":username}): return {"ok":False,"error":"Username already exists."}
        if email and c.find_one({"email":email}): return {"ok":False,"error":"Email already exists."}
        now=datetime.now(timezone.utc); doc={"name":str(data.get("name","")).strip(),"username":username,"password_hash":generate_password_hash(password),"role":ROLE,"power":ROLE,"active":True,"created_at":now,"updated_at":now}
        for key in ("mobile","email","sex","date_of_birth","blood_group","occupation","department","present_address","permanent_address","branch_id","central_id","section_id"):
            value=str(data.get(key,"")).strip()
            if value: doc[key]=value
        r=c.insert_one(doc); return {"ok":True,"user_id":str(r.inserted_id),"username":username,"role":ROLE}
    finally: client.close()
def authenticate_user(username,password):
    username=str(username or "").strip()
    if not username or not password: return {"ok":False,"error":"Username and password are required."}
    client,db=_mongo()
    try:
        user=db[COLLECTION_NAME].find_one({"username":username,"role":ROLE})
        if not user or not user.get("active",True): return {"ok":False,"error":"Invalid username or password."}
        if not check_password_hash(user.get("password_hash",""),password): return {"ok":False,"error":"Invalid username or password."}
        return {"ok":True,"user":user}
    finally: client.close()
