import os

from pymongo import MongoClient
from dotenv import load_dotenv


load_dotenv()


MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")


if not MONGODB_URI:
    raise RuntimeError(
        "MONGODB_URI is missing from environment variables."
    )


if not DATABASE_NAME:
    raise RuntimeError(
        "DATABASE_NAME is missing from environment variables."
    )


client = MongoClient(
    MONGODB_URI,
    tls=True,
    tlsAllowInvalidCertificates=False,
    serverSelectionTimeoutMS=30000,
    connectTimeoutMS=30000,
    socketTimeoutMS=30000,
    retryWrites=True,
)


db = client[DATABASE_NAME]


users_collection = db["users"]