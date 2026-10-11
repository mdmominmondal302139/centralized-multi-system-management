import os
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient


class BazarDutyService:
    """
    MongoDB service for Monthly Bazar List and member duty management.

    It first tries the project's existing config.database.get_database().
    If unavailable, it uses MONGODB_URI and DATABASE_NAME from environment.
    Collections:
      - bazar_duty_headers
      - bazar_duties
      - bazar_duty_members
    """

    def __init__(self):
        self._client = None
        self._db = None

    def _database(self):
        if self._db is not None:
            return self._db

        try:
            from config.database import get_database
            self._db = get_database()
            return self._db
        except (ImportError, AttributeError):
            pass

        uri = os.getenv("MONGODB_URI", "").strip()
        if not uri:
            raise RuntimeError(
                "MongoDB is not configured. Set MONGODB_URI or provide config.database.get_database()."
            )

        self._client = MongoClient(
            uri,
            serverSelectionTimeoutMS=int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "10000")),
            retryWrites=True,
            retryReads=True,
        )
        self._db = self._client[os.getenv("DATABASE_NAME", "development_my_expense_software")]
        return self._db

    @staticmethod
    def _scope_filter(account_id, branch_id):
        # Empty values are retained as a scope for installations that do not store these session keys.
        return {"account_id": str(account_id or ""), "branch_id": str(branch_id or "")}

    @staticmethod
    def _clean(doc):
        if not doc:
            return None
        result = dict(doc)
        if "_id" in result:
            result["_id"] = str(result["_id"])
        return result

    def get_header(self, account_id, branch_id, month):
        query = {**self._scope_filter(account_id, branch_id), "month": month}
        doc = self._database().bazar_duty_headers.find_one(query)
        return self._clean(doc) or {
            "header_name": "",
            "list_title": "বাজার লিস্ট",
            "instruction": "দুপুর ২:০০টা থেকে বিকেল ৫:৩০টার মধ্যে বাজার সম্পন্ন করুন।",
        }

    def save_header(self, account_id, branch_id, month, header_name, list_title, instruction):
        if not month or len(month) != 7 or month[4] != "-":
            raise ValueError("Please choose a valid month.")
        query = {**self._scope_filter(account_id, branch_id), "month": month}
        values = {
            "header_name": header_name[:160],
            "list_title": (list_title or "বাজার লিস্ট")[:120],
            "instruction": instruction[:1000],
            "updated_at": datetime.utcnow(),
        }
        self._database().bazar_duty_headers.update_one(
            query, {"$set": values, "$setOnInsert": {"created_at": datetime.utcnow()}}, upsert=True
        )

    def list_duties(self, account_id, branch_id, month):
        query = {**self._scope_filter(account_id, branch_id), "month": month}
        docs = self._database().bazar_duties.find(query).sort("duty_date", 1)
        return [self._clean(doc) for doc in docs]

    def save_duty(self, account_id, branch_id, month, duty_id, duty_date,
                  member_one, member_two, bazar_time, status, note):
        if not duty_date or not duty_date.startswith(month + "-"):
            raise ValueError("Duty date must belong to the selected month.")
        try:
            datetime.strptime(duty_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Please enter a valid duty date.")
        if not member_one or not member_two:
            raise ValueError("Please select both responsible members.")
        if member_one.casefold() == member_two.casefold():
            raise ValueError("Select two different members for one duty.")
        if status not in {"Pending", "Completed", "Missed"}:
            raise ValueError("Invalid duty status.")

        scope = self._scope_filter(account_id, branch_id)
        values = {
            **scope,
            "month": month,
            "duty_date": duty_date,
            "member_one": member_one[:160],
            "member_two": member_two[:160],
            "bazar_time": bazar_time[:100],
            "status": status,
            "note": note[:1000],
            "updated_at": datetime.utcnow(),
        }
        collection = self._database().bazar_duties

        # Warn against assigning a person twice on the same date in this scope.
        duplicate = collection.find_one({
            **scope,
            "duty_date": duty_date,
            "$or": [
                {"member_one": {"$in": [member_one, member_two]}},
                {"member_two": {"$in": [member_one, member_two]}},
            ],
        })
        if duplicate and (not duty_id or str(duplicate.get("_id")) != duty_id):
            raise ValueError("One of these members is already assigned on this date.")

        if duty_id:
            if not ObjectId.is_valid(duty_id):
                raise ValueError("Invalid duty record.")
            result = collection.update_one(
                {**scope, "_id": ObjectId(duty_id)},
                {"$set": values},
            )
            if result.matched_count == 0:
                raise ValueError("Duty record not found or access denied.")
        else:
            values["created_at"] = datetime.utcnow()
            collection.insert_one(values)

    def delete_duty(self, account_id, branch_id, duty_id):
        if not ObjectId.is_valid(duty_id):
            raise ValueError("Invalid duty record.")
        result = self._database().bazar_duties.delete_one({
            **self._scope_filter(account_id, branch_id),
            "_id": ObjectId(duty_id),
        })
        if result.deleted_count == 0:
            raise ValueError("Duty record not found or access denied.")

    def list_members(self, account_id, branch_id):
        query = {
            **self._scope_filter(account_id, branch_id),
            "active": {"$ne": False},
        }
        docs = self._database().bazar_duty_members.find(query).sort("name", 1)
        return [self._clean(doc) for doc in docs]

    def add_member(self, account_id, branch_id, name):
        name = (name or "").strip()
        if not name:
            raise ValueError("Enter a member name.")
        if len(name) > 160:
            raise ValueError("Member name must be 160 characters or fewer.")

        collection = self._database().bazar_duty_members
        scope = self._scope_filter(account_id, branch_id)
        existing = collection.find_one({**scope, "name_key": name.casefold()})
        if existing:
            raise ValueError("This member already exists.")

        collection.insert_one({
            **scope,
            "name": name,
            "name_key": name.casefold(),
            "active": True,
            "created_at": datetime.utcnow(),
        })
