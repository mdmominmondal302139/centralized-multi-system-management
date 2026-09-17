import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")

if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI is missing from .env")

if not DATABASE_NAME:
    raise RuntimeError("DATABASE_NAME is missing from .env")

client = MongoClient(MONGODB_URI)
db = client[DATABASE_NAME]

users_collection = db["users"]
