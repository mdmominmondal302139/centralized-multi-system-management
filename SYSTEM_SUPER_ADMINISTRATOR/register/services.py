"""Business/data service for Blood Donor Management.

Database access is intentionally isolated in the Database directory.
Routes call this service; HTML never contains database logic.
"""

from __future__ import annotations

import importlib.util
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from bson import ObjectId
from werkzeug.security import check_password_hash, generate_password_hash

BASE = Path(__file__).resolve().parents[1]
DATABASE_FILE = (
    BASE
    / "database"
    / "database.py"
)

spec = importlib.util.spec_from_file_location(
    "system_super_administrator_blood_donor_database",
    DATABASE_FILE,
)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load database module: {DATABASE_FILE}")

database_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(database_module)


DONOR_COLLECTION = "system_super_administrator_blood_donors"
DONATION_COLLECTION = "system_super_administrator_blood_donations"
SCREENING_COLLECTION = "system_super_administrator_blood_donation_screenings"
REQUEST_COLLECTION = "system_super_administrator_blood_requests"
MATCH_COLLECTION = "system_super_administrator_blood_request_matches"
UNIT_COLLECTION = "system_super_administrator_blood_units"
NOTIFICATION_COLLECTION = "system_super_administrator_blood_notifications"
AUDIT_COLLECTION = "system_super_administrator_blood_audit_logs"
ACCOUNT_COLLECTION = "system_super_administrator_blood_donor_accounts"

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
GENDERS = ["Male", "Female", "Other", "Prefer not to say"]
DONOR_STATUSES = ["Active", "Inactive", "Temporarily Deferred", "Permanently Deferred"]
AVAILABILITY_STATUSES = ["Available", "Unavailable", "Do Not Contact"]
REQUEST_STATUSES = [
    "Pending",
    "Searching Donor",
    "Donor Found",
    "Blood Collected",
    "Completed",
    "Cancelled",
    "Expired",
]
URGENCY_LEVELS = ["Normal", "Emergency"]
MATCH_STATUSES = ["Suggested", "Contacted", "Accepted", "Declined", "Completed", "Cancelled"]
UNIT_STATUSES = ["Available", "Reserved", "Issued", "Expired", "Discarded"]
SCREENING_STATUSES = ["Pending", "Passed", "Deferred", "Rejected"]
NOTIFICATION_TYPES = ["Request", "Donation", "Eligibility", "System"]


class BloodDonorService:
    def __init__(self):
        self._indexes_ready = False

    @property
    def db(self):
        db = database_module.get_database()[1]
        if not self._indexes_ready:
            self._ensure_indexes(db)
            self._indexes_ready = True
        return db

    @property
    def donors(self):
        return self.db[DONOR_COLLECTION]

    @property
    def donations(self):
        return self.db[DONATION_COLLECTION]

    @property
    def screenings(self):
        return self.db[SCREENING_COLLECTION]

    @property
    def requests(self):
        return self.db[REQUEST_COLLECTION]

    @property
    def matches(self):
        return self.db[MATCH_COLLECTION]

    @property
    def units(self):
        return self.db[UNIT_COLLECTION]

    @property
    def notifications(self):
        return self.db[NOTIFICATION_COLLECTION]

    @property
    def audits(self):
        return self.db[AUDIT_COLLECTION]

    @property
    def accounts(self):
        return self.db[ACCOUNT_COLLECTION]

    def _ensure_indexes(self, db):
        try:
            db[DONOR_COLLECTION].create_index("donor_id", unique=True)
            db[DONOR_COLLECTION].create_index([("blood_group", 1), ("availability_status", 1)])
            db[DONOR_COLLECTION].create_index([("district", 1), ("upazila", 1)])
            db[DONOR_COLLECTION].create_index("phone")
            db[DONATION_COLLECTION].create_index("donation_id", unique=True)
            db[DONATION_COLLECTION].create_index([("donor_id", 1), ("donation_date", -1)])
            db[SCREENING_COLLECTION].create_index("screening_id", unique=True)
            db[REQUEST_COLLECTION].create_index("request_id", unique=True)
            db[REQUEST_COLLECTION].create_index([("required_blood_group", 1), ("status", 1), ("urgency", 1)])
            db[MATCH_COLLECTION].create_index("match_id", unique=True)
            db[UNIT_COLLECTION].create_index("unit_id", unique=True)
            db[UNIT_COLLECTION].create_index([("blood_group", 1), ("status", 1), ("expiry_date", 1)])
            db[NOTIFICATION_COLLECTION].create_index([("user_id", 1), ("created_at", -1)])
            db[AUDIT_COLLECTION].create_index([("created_at", -1)])
            db[ACCOUNT_COLLECTION].create_index("username", unique=True)
            db[ACCOUNT_COLLECTION].create_index("user_id", unique=True)
            db[ACCOUNT_COLLECTION].create_index("email")
        except Exception:
            # Index creation should not prevent the application from starting.
            pass

    @staticmethod
    def _now() -> datetime:
        return datetime.utcnow()

    @staticmethod
    def _oid(value: Any):
        try:
            return ObjectId(str(value))
        except Exception:
            return None

    @classmethod
    def _serialize(cls, value: Any):
        if isinstance(value, ObjectId):
            return str(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, dict):
            return {k: cls._serialize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [cls._serialize(v) for v in value]
        return value

    @staticmethod
    def _clean_payload(payload: dict[str, Any], fields: set[str]) -> dict[str, Any]:
        result = {}
        for key in fields:
            if key in payload:
                value = payload[key]
                if value is None:
                    result[key] = ""
                elif isinstance(value, str):
                    result[key] = value.strip()
                else:
                    result[key] = value
        return result

    def _audit(self, action: str, entity: str, entity_id: str, user_id: str | None, details: dict | None = None):
        self.audits.insert_one({
            "action": action,
            "entity": entity,
            "entity_id": str(entity_id),
            "user_id": user_id,
            "details": details or {},
            "created_at": self._now(),
        })

    # ---------------------------- metadata ----------------------------
    def metadata(self):
        return {
            "blood_groups": BLOOD_GROUPS,
            "genders": GENDERS,
            "donor_statuses": DONOR_STATUSES,
            "availability_statuses": AVAILABILITY_STATUSES,
            "request_statuses": REQUEST_STATUSES,
            "urgency_levels": URGENCY_LEVELS,
            "match_statuses": MATCH_STATUSES,
            "unit_statuses": UNIT_STATUSES,
            "screening_statuses": SCREENING_STATUSES,
            "notification_types": NOTIFICATION_TYPES,
        }

    # ---------------------------- dashboard ----------------------------
    def dashboard(self):
        today = date.today().isoformat()
        return {
            "donors": self.donors.count_documents({}),
            "active_donors": self.donors.count_documents({"donor_status": "Active"}),
            "available_donors": self.donors.count_documents({"availability_status": "Available", "donor_status": "Active"}),
            "emergency_requests": self.requests.count_documents({"urgency": "Emergency", "status": {"$in": ["Pending", "Searching Donor"]}}),
            "open_requests": self.requests.count_documents({"status": {"$in": ["Pending", "Searching Donor", "Donor Found"]}}),
            "donations": self.donations.count_documents({}),
            "available_units": self.units.count_documents({"status": "Available", "expiry_date": {"$gte": today}}),
            "expired_units": self.units.count_documents({"status": "Expired"}),
        }

    # ---------------------------- donors ----------------------------
    def _next_id(self, prefix: str, collection) -> str:
        # Timestamp + random ObjectId suffix gives a readable, collision-resistant ID.
        return f"{prefix}-{datetime.utcnow():%Y%m%d%H%M%S}-{str(ObjectId())[-6:].upper()}"

    def list_donors(self, params):
        q = str(params.get("q") or "").strip()
        blood_group = str(params.get("blood_group") or "").strip()
        district = str(params.get("district") or "").strip()
        upazila = str(params.get("upazila") or "").strip()
        availability = str(params.get("availability_status") or "").strip()
        status = str(params.get("donor_status") or "").strip()
        limit = min(max(int(params.get("limit") or 100), 1), 500)

        criteria = {}
        if blood_group in BLOOD_GROUPS:
            criteria["blood_group"] = blood_group
        if district:
            criteria["district"] = {"$regex": district, "$options": "i"}
        if upazila:
            criteria["upazila"] = {"$regex": upazila, "$options": "i"}
        if availability in AVAILABILITY_STATUSES:
            criteria["availability_status"] = availability
        if status in DONOR_STATUSES:
            criteria["donor_status"] = status
        if q:
            criteria["$or"] = [
                {"full_name": {"$regex": q, "$options": "i"}},
                {"donor_id": {"$regex": q, "$options": "i"}},
                {"phone": {"$regex": q, "$options": "i"}},
                {"email": {"$regex": q, "$options": "i"}},
                {"district": {"$regex": q, "$options": "i"}},
                {"upazila": {"$regex": q, "$options": "i"}},
            ]

        rows = self.donors.find(criteria).sort("created_at", -1).limit(limit)
        return [self._serialize(row) for row in rows]

    def get_donor(self, donor_id):
        oid = self._oid(donor_id)
        query = {"_id": oid} if oid else {"donor_id": str(donor_id)}
        row = self.donors.find_one(query)
        return self._serialize(row) if row else None

    def create_donor(self, payload, user_id):
        required = ["full_name", "blood_group", "phone"]
        for field in required:
            if not str(payload.get(field) or "").strip():
                raise ValueError(f"{field.replace('_', ' ').title()} is required.")
        if payload["blood_group"] not in BLOOD_GROUPS:
            raise ValueError("Invalid blood group.")
        now = self._now()
        donor = self._clean_payload(payload, {
            "full_name", "profile_photo", "blood_group", "date_of_birth", "age", "gender", "phone", "email",
            "address", "district", "upazila", "area", "emergency_contact", "donor_status", "last_donation_date",
            "next_eligible_date", "total_donation_count", "availability_status", "notes"
        })
        donor.setdefault("donor_status", "Active")
        donor.setdefault("availability_status", "Available")
        donor.setdefault("total_donation_count", 0)
        donor["donor_id"] = self._next_id("DONOR", self.donors)
        donor["created_at"] = now
        donor["updated_at"] = now
        donor["created_by"] = user_id
        result = self.donors.insert_one(donor)
        self._audit("CREATE", "donor", result.inserted_id, user_id)
        return self.get_donor(result.inserted_id)

    def update_donor(self, donor_id, payload, user_id):
        oid = self._oid(donor_id)
        if not oid:
            raise ValueError("Invalid donor ID.")
        if payload.get("blood_group") and payload["blood_group"] not in BLOOD_GROUPS:
            raise ValueError("Invalid blood group.")
        data = self._clean_payload(payload, {
            "full_name", "profile_photo", "blood_group", "date_of_birth", "age", "gender", "phone", "email",
            "address", "district", "upazila", "area", "emergency_contact", "donor_status", "last_donation_date",
            "next_eligible_date", "total_donation_count", "availability_status", "notes"
        })
        data["updated_at"] = self._now()
        data["updated_by"] = user_id
        result = self.donors.update_one({"_id": oid}, {"$set": data})
        if not result.matched_count:
            return None
        self._audit("UPDATE", "donor", oid, user_id, {"fields": list(data.keys())})
        return self.get_donor(oid)

    def delete_donor(self, donor_id, user_id):
        oid = self._oid(donor_id)
        if not oid:
            return False
        result = self.donors.delete_one({"_id": oid})
        if result.deleted_count:
            self._audit("DELETE", "donor", oid, user_id)
            return True
        return False

    # ---------------------------- donations ----------------------------
    def list_donations(self, donor_id="", limit=300):
        criteria = {}
        if donor_id:
            criteria["donor_id"] = str(donor_id)
        rows = self.donations.find(criteria).sort("donation_date", -1).limit(min(int(limit), 500))
        return [self._serialize(x) for x in rows]

    def create_donation(self, payload, user_id):
        donor_id = str(payload.get("donor_id") or "").strip()
        if not donor_id:
            raise ValueError("Donor ID is required.")
        donor = self.get_donor(donor_id)
        if not donor:
            raise ValueError("Donor not found.")
        if donor.get("blood_group") not in BLOOD_GROUPS:
            raise ValueError("Donor blood group is invalid.")
        data = self._clean_payload(payload, {
            "donor_id", "donation_date", "blood_group", "quantity", "donation_location", "hospital_blood_center",
            "screening_status", "collection_status", "staff_officer", "notes"
        })
        data["donation_id"] = self._next_id("DONATION", self.donations)
        data["blood_group"] = data.get("blood_group") or donor.get("blood_group")
        data["quantity"] = data.get("quantity") or "1"
        data["created_at"] = self._now()
        data["created_by"] = user_id
        result = self.donations.insert_one(data)
        self.donors.update_one({"_id": self._oid(donor["_id"])}, {"$set": {
            "last_donation_date": data.get("donation_date", ""),
            "total_donation_count": int(donor.get("total_donation_count") or 0) + 1,
            "updated_at": self._now(),
        }})
        self._audit("CREATE", "donation", result.inserted_id, user_id, {"donor_id": donor_id})
        return self._serialize(self.donations.find_one({"_id": result.inserted_id}))

    # ---------------------------- screening ----------------------------
    def list_screenings(self, donor_id="", limit=300):
        criteria = {"donor_id": str(donor_id)} if donor_id else {}
        rows = self.screenings.find(criteria).sort("screening_date", -1).limit(min(int(limit), 500))
        return [self._serialize(x) for x in rows]

    def create_screening(self, payload, user_id):
        donor_id = str(payload.get("donor_id") or "").strip()
        if not self.get_donor(donor_id):
            raise ValueError("Donor not found.")
        data = self._clean_payload(payload, {
            "donor_id", "screening_date", "eligibility_status", "hemoglobin", "blood_pressure", "temperature",
            "weight", "deferral_type", "deferral_reason", "screening_officer", "notes"
        })
        data["screening_id"] = self._next_id("SCREEN", self.screenings)
        data["created_at"] = self._now()
        data["created_by"] = user_id
        result = self.screenings.insert_one(data)
        self._audit("CREATE", "screening", result.inserted_id, user_id, {"donor_id": donor_id})
        return self._serialize(self.screenings.find_one({"_id": result.inserted_id}))

    # ---------------------------- requests ----------------------------
    def list_requests(self, params):
        criteria = {}
        status = str(params.get("status") or "").strip()
        blood_group = str(params.get("blood_group") or "").strip()
        urgency = str(params.get("urgency") or "").strip()
        q = str(params.get("q") or "").strip()
        if status in REQUEST_STATUSES:
            criteria["status"] = status
        if blood_group in BLOOD_GROUPS:
            criteria["required_blood_group"] = blood_group
        if urgency in URGENCY_LEVELS:
            criteria["urgency"] = urgency
        if q:
            criteria["$or"] = [
                {"patient_name": {"$regex": q, "$options": "i"}},
                {"hospital_name": {"$regex": q, "$options": "i"}},
                {"request_id": {"$regex": q, "$options": "i"}},
            ]
        rows = self.requests.find(criteria).sort([("urgency", -1), ("created_at", -1)]).limit(500)
        return [self._serialize(x) for x in rows]

    def get_request(self, request_id):
        oid = self._oid(request_id)
        query = {"_id": oid} if oid else {"request_id": str(request_id)}
        row = self.requests.find_one(query)
        return self._serialize(row) if row else None

    def create_request(self, payload, user_id):
        required = ["patient_name", "required_blood_group", "quantity", "hospital_name", "required_datetime"]
        for field in required:
            if not str(payload.get(field) or "").strip():
                raise ValueError(f"{field.replace('_', ' ').title()} is required.")
        if payload["required_blood_group"] not in BLOOD_GROUPS:
            raise ValueError("Invalid required blood group.")
        if payload.get("urgency") not in URGENCY_LEVELS:
            payload["urgency"] = "Normal"
        data = self._clean_payload(payload, {
            "patient_name", "patient_blood_group", "required_blood_group", "quantity", "hospital_name", "hospital_address",
            "doctor_contact_person", "attendant_contact", "required_datetime", "urgency", "notes", "requester_name",
            "requester_contact"
        })
        data["request_id"] = self._next_id("REQUEST", self.requests)
        data["status"] = "Pending"
        data["created_at"] = self._now()
        data["updated_at"] = self._now()
        data["created_by"] = user_id
        result = self.requests.insert_one(data)
        self._audit("CREATE", "blood_request", result.inserted_id, user_id)
        return self.get_request(result.inserted_id)

    def update_request(self, request_id, payload, user_id):
        oid = self._oid(request_id)
        if not oid:
            raise ValueError("Invalid request ID.")
        if payload.get("status") and payload["status"] not in REQUEST_STATUSES:
            raise ValueError("Invalid request status.")
        data = self._clean_payload(payload, {
            "patient_name", "patient_blood_group", "required_blood_group", "quantity", "hospital_name", "hospital_address",
            "doctor_contact_person", "attendant_contact", "required_datetime", "urgency", "notes", "requester_name",
            "requester_contact", "status"
        })
        data["updated_at"] = self._now()
        result = self.requests.update_one({"_id": oid}, {"$set": data})
        if not result.matched_count:
            return None
        self._audit("UPDATE", "blood_request", oid, user_id)
        return self.get_request(oid)

    # ---------------------------- donor matching ----------------------------
    def match_donors(self, request_id, user_id, limit=50):
        request = self.get_request(request_id)
        if not request:
            raise ValueError("Blood request not found.")
        group = request.get("required_blood_group")
        district = str(request.get("hospital_address") or "").strip()
        criteria = {
            "blood_group": group,
            "donor_status": "Active",
            "availability_status": "Available",
        }
        # Eligibility is data-driven: an explicit next_eligible_date in the future excludes the donor.
        today = date.today().isoformat()
        criteria["$or"] = [
            {"next_eligible_date": {"$exists": False}},
            {"next_eligible_date": ""},
            {"next_eligible_date": {"$lte": today}},
        ]
        rows = list(self.donors.find(criteria).sort("last_donation_date", 1).limit(min(int(limit), 100)))
        output = []
        for donor in rows:
            match_id = self._next_id("MATCH", self.matches)
            existing = self.matches.find_one({"request_id": request["request_id"], "donor_id": donor["donor_id"]})
            if existing:
                output.append(self._serialize(existing))
                continue
            record = {
                "match_id": match_id,
                "request_id": request["request_id"],
                "donor_id": donor["donor_id"],
                "donor_name": donor.get("full_name", ""),
                "blood_group": donor.get("blood_group", ""),
                "district": donor.get("district", ""),
                "upazila": donor.get("upazila", ""),
                "phone": donor.get("phone", ""),
                "status": "Suggested",
                "created_at": self._now(),
                "created_by": user_id,
            }
            result = self.matches.insert_one(record)
            record["_id"] = result.inserted_id
            output.append(self._serialize(record))
        self.requests.update_one({"_id": self._oid(request["_id"])}, {"$set": {"status": "Searching Donor", "updated_at": self._now()}})
        self._audit("MATCH", "blood_request", request["_id"], user_id, {"count": len(output)})
        return output

    def list_matches(self, request_id=""):
        criteria = {"request_id": str(request_id)} if request_id else {}
        rows = self.matches.find(criteria).sort("created_at", -1).limit(500)
        return [self._serialize(x) for x in rows]

    def update_match(self, match_id, status, user_id):
        if status not in MATCH_STATUSES:
            raise ValueError("Invalid match status.")
        oid = self._oid(match_id)
        if not oid:
            raise ValueError("Invalid match ID.")
        result = self.matches.update_one({"_id": oid}, {"$set": {"status": status, "updated_at": self._now(), "updated_by": user_id}})
        if not result.matched_count:
            return None
        self._audit("UPDATE", "request_match", oid, user_id, {"status": status})
        return self._serialize(self.matches.find_one({"_id": oid}))

    # ---------------------------- blood units/inventory ----------------------------
    def list_units(self, params):
        criteria = {}
        group = str(params.get("blood_group") or "").strip()
        status = str(params.get("status") or "").strip()
        if group in BLOOD_GROUPS:
            criteria["blood_group"] = group
        if status in UNIT_STATUSES:
            criteria["status"] = status
        rows = self.units.find(criteria).sort("collection_date", -1).limit(500)
        return [self._serialize(x) for x in rows]

    def create_unit(self, payload, user_id):
        group = str(payload.get("blood_group") or "").strip()
        if group not in BLOOD_GROUPS:
            raise ValueError("Invalid blood group.")
        if not str(payload.get("collection_date") or "").strip():
            raise ValueError("Collection date is required.")
        data = self._clean_payload(payload, {
            "blood_group", "collection_date", "expiry_date", "collection_center", "screening_result", "storage_location", "status", "donation_id", "notes"
        })
        data["unit_id"] = self._next_id("UNIT", self.units)
        data.setdefault("status", "Available")
        data["created_at"] = self._now()
        data["created_by"] = user_id
        result = self.units.insert_one(data)
        self._audit("CREATE", "blood_unit", result.inserted_id, user_id)
        return self._serialize(self.units.find_one({"_id": result.inserted_id}))

    def update_unit(self, unit_id, payload, user_id):
        oid = self._oid(unit_id)
        if not oid:
            raise ValueError("Invalid unit ID.")
        if payload.get("status") and payload["status"] not in UNIT_STATUSES:
            raise ValueError("Invalid unit status.")
        data = self._clean_payload(payload, {"blood_group", "collection_date", "expiry_date", "collection_center", "screening_result", "storage_location", "status", "donation_id", "notes"})
        data["updated_at"] = self._now()
        result = self.units.update_one({"_id": oid}, {"$set": data})
        if not result.matched_count:
            return None
        self._audit("UPDATE", "blood_unit", oid, user_id)
        return self._serialize(self.units.find_one({"_id": oid}))


    # ---------------- temporary normal donor authentication ----------------
    def register_normal_donor(self, payload):
        data = dict(payload or {})
        required = ["full_name", "username", "password", "confirm_password", "blood_group", "phone", "district", "area"]
        for field in required:
            if not str(data.get(field) or "").strip():
                raise ValueError(f"{field.replace('_', ' ').title()} is required.")
        username = str(data.get("username") or "").strip().lower()
        if len(username) < 3:
            raise ValueError("Username must contain at least 3 characters.")
        if not username.replace(".", "").replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username may contain only letters, numbers, dot, underscore, or hyphen.")
        password = str(data.get("password") or "")
        if len(password) < 6:
            raise ValueError("Password must contain at least 6 characters.")
        if password != str(data.get("confirm_password") or ""):
            raise ValueError("Password and confirm password do not match.")
        if data.get("blood_group") not in BLOOD_GROUPS:
            raise ValueError("Invalid blood group.")
        if self.accounts.find_one({"username": username}):
            raise ValueError("Username already exists.")
        phone = str(data.get("phone") or "").strip()
        if self.accounts.find_one({"phone": phone}):
            raise ValueError("Mobile number is already registered.")
        email = str(data.get("email") or "").strip().lower()
        if email and self.accounts.find_one({"email": email}):
            raise ValueError("Email is already registered.")

        now = self._now()
        user_id = self._next_id("USER", self.accounts)
        account = {
            "user_id": user_id,
            "username": username,
            "password_hash": generate_password_hash(password),
            "role": "MEMBER",
            "full_name": str(data.get("full_name") or "").strip(),
            "email": email,
            "phone": phone,
            "status": "ACTIVE",
            "created_at": now,
            "updated_at": now,
        }
        self.accounts.insert_one(account)
        donor_payload = {
            "full_name": account["full_name"],
            "blood_group": data.get("blood_group"),
            "date_of_birth": str(data.get("date_of_birth") or "").strip(),
            "gender": str(data.get("gender") or "").strip(),
            "phone": phone,
            "email": email,
            "district": str(data.get("district") or "").strip(),
            "upazila": str(data.get("upazila") or "").strip(),
            "area": str(data.get("area") or "").strip(),
            "address": str(data.get("address") or "").strip(),
            "donor_status": "Active",
            "availability_status": "Available",
            "total_donation_count": 0,
            "user_id": user_id,
            "account_user_id": user_id,
            "username": username,
            "created_by": user_id,
        }
        try:
            donor = self.create_donor(donor_payload, user_id)
        except Exception:
            self.accounts.delete_one({"user_id": user_id})
            raise
        return {"user_id": user_id, "username": username, "role": "MEMBER", "donor": donor}

    def authenticate_normal_donor(self, username, password):
        username = str(username or "").strip().lower()
        account = self.accounts.find_one({"username": username})
        if not account or account.get("status") != "ACTIVE":
            raise ValueError("Invalid username or password.")
        if not check_password_hash(str(account.get("password_hash") or ""), str(password or "")):
            raise ValueError("Invalid username or password.")
        return {
            "user_id": account.get("user_id"),
            "username": account.get("username"),
            "name": account.get("full_name") or account.get("username"),
            "role": "MEMBER",
        }

    # ------------------------ normal donor account ------------------------
    def _find_account_donor(self, user_id=None, username=None, name=None):
        """Resolve the donor record belonging to the logged-in normal account."""
        values = [str(v).strip() for v in (user_id, username) if v]
        clauses = []
        for value in values:
            clauses.extend([
                {"user_id": value},
                {"account_user_id": value},
                {"created_by": value},
            ])
        if username:
            clauses.extend([{"username": str(username).strip()}, {"login_username": str(username).strip()}])
        if name:
            clauses.append({"full_name": str(name).strip()})
        if not clauses:
            return None
        row = self.donors.find_one({"$or": clauses}, sort=[("updated_at", -1), ("created_at", -1)])
        return self._serialize(row) if row else None

    def normal_account(self, user_id=None, username=None, name=None):
        donor = self._find_account_donor(user_id, username, name)
        if not donor:
            return {
                "donor": None,
                "last_donation": None,
                "next_eligible_date": None,
                "total_donations": 0,
                "eligibility": "Unknown",
            }

        donor_id = donor.get("donor_id", "")
        donations = list(self.donations.find({"donor_id": donor_id}).sort("donation_date", -1).limit(1))
        last = self._serialize(donations[0]) if donations else None
        total = self.donations.count_documents({"donor_id": donor_id})
        next_date = donor.get("next_eligible_date") or ""
        eligibility = "Eligible"
        if next_date and str(next_date) > date.today().isoformat():
            eligibility = "Not Eligible"
        elif donor.get("donor_status") in {"Temporarily Deferred", "Permanently Deferred", "Inactive"}:
            eligibility = donor.get("donor_status")
        return {
            "donor": donor,
            "last_donation": last,
            "next_eligible_date": next_date or None,
            "total_donations": total if total else int(donor.get("total_donation_count") or 0),
            "eligibility": eligibility,
        }

    def find_public_donors(self, params):
        group = str(params.get("blood_group") or "").strip()
        district = str(params.get("district") or "").strip()
        area = str(params.get("area") or "").strip()
        if group not in BLOOD_GROUPS:
            raise ValueError("Please select a valid blood group.")
        criteria = {
            "blood_group": group,
            "donor_status": "Active",
            "availability_status": "Available",
        }
        if district:
            criteria["district"] = {"$regex": district, "$options": "i"}
        if area:
            criteria["area"] = {"$regex": area, "$options": "i"}
        today = date.today().isoformat()
        criteria["$or"] = [
            {"next_eligible_date": {"$exists": False}},
            {"next_eligible_date": ""},
            {"next_eligible_date": {"$lte": today}},
        ]
        rows = self.donors.find(criteria).sort([("last_donation_date", 1), ("full_name", 1)]).limit(100)
        # Public response intentionally excludes sensitive fields.
        output = []
        for row in rows:
            output.append({
                "donor_id": row.get("donor_id", ""),
                "full_name": row.get("full_name", ""),
                "blood_group": row.get("blood_group", ""),
                "district": row.get("district", ""),
                "upazila": row.get("upazila", ""),
                "area": row.get("area", ""),
                "availability_status": row.get("availability_status", ""),
                "donor_status": row.get("donor_status", ""),
            })
        return output

    def public_donor_detail(self, donor_id):
        donor = self.get_donor(donor_id)
        if not donor:
            return None
        return {
            "donor_id": donor.get("donor_id", ""),
            "full_name": donor.get("full_name", ""),
            "blood_group": donor.get("blood_group", ""),
            "district": donor.get("district", ""),
            "upazila": donor.get("upazila", ""),
            "area": donor.get("area", ""),
            "availability_status": donor.get("availability_status", ""),
            "donor_status": donor.get("donor_status", ""),
        }

    def normal_public_requests(self, params):
        # Public request view intentionally excludes private patient/contact fields.
        criteria = {"status": {"$in": ["Pending", "Searching Donor", "Donor Found"]}}
        group = str(params.get("blood_group") or "").strip()
        status = str(params.get("status") or "").strip()
        q = str(params.get("q") or "").strip()
        location = str(params.get("location") or "").strip()
        if group in BLOOD_GROUPS:
            criteria["required_blood_group"] = group
        if status in REQUEST_STATUSES and status in {"Pending", "Searching Donor", "Donor Found"}:
            criteria["status"] = status
        if location:
            criteria["hospital_address"] = {"$regex": location, "$options": "i"}
        if q:
            criteria["$or"] = [
                {"request_id": {"$regex": q, "$options": "i"}},
                {"required_blood_group": {"$regex": q, "$options": "i"}},
                {"hospital_name": {"$regex": q, "$options": "i"}},
                {"hospital_address": {"$regex": q, "$options": "i"}},
            ]
        rows = self.requests.find(criteria).sort("created_at", -1).limit(300)
        return [{
            "request_id": r.get("request_id", ""),
            "required_blood_group": r.get("required_blood_group", ""),
            "quantity": r.get("quantity", ""),
            "hospital_name": r.get("hospital_name", ""),
            "location": r.get("hospital_address", ""),
            "required_datetime": r.get("required_datetime", ""),
            "urgency": r.get("urgency", "Normal"),
            "status": r.get("status", ""),
            "created_by": r.get("created_by", ""),
        } for r in rows]

    def normal_request_detail(self, request_id, user_id=None):
        row = self.get_request(request_id)
        if not row:
            return None
        owner = str(row.get("created_by") or "") == str(user_id or "")
        # Keep sensitive patient/contact information private to the request owner.
        result = {
            "request_id": row.get("request_id", ""),
            "required_blood_group": row.get("required_blood_group", ""),
            "quantity": row.get("quantity", ""),
            "hospital_name": row.get("hospital_name", ""),
            "location": row.get("hospital_address", ""),
            "required_datetime": row.get("required_datetime", ""),
            "urgency": row.get("urgency", "Normal"),
            "status": row.get("status", ""),
            "requester_name": row.get("requester_name", "") if owner else "",
            "patient_name": row.get("patient_name", "") if owner else "",
            "requester_contact": row.get("requester_contact", "") if owner else "",
            "attendant_contact": row.get("attendant_contact", "") if owner else "",
            "notes": row.get("notes", "") if owner else "",
            "is_owner": owner,
        }
        result["matches"] = self.list_matches(row.get("request_id", ""))
        return result

    def normal_create_request(self, payload, user_id, username=None, name=None):
        data = dict(payload or {})
        # The normal-user form deliberately uses only the fields specified by the workflow.
        required = ["required_blood_group", "quantity", "hospital_name", "required_datetime"]
        for field in required:
            if not str(data.get(field) or "").strip():
                raise ValueError(f"{field.replace('_', ' ').title()} is required.")
        if data.get("required_blood_group") not in BLOOD_GROUPS:
            raise ValueError("Invalid required blood group.")
        data["requester_name"] = data.get("requester_name") or name or username or ""
        data["requester_contact"] = data.get("requester_contact") or ""
        data["patient_name"] = data.get("patient_name") or data.get("requester_name") or ""
        return self.create_request(data, user_id)

    def normal_my_records(self, user_id=None, username=None, name=None):
        donor = self._find_account_donor(user_id, username, name)
        donor_id = donor.get("donor_id") if donor else ""
        donations = [self._serialize(x) for x in self.donations.find({"donor_id": donor_id}).sort("donation_date", -1).limit(300)] if donor_id else []
        requests = [self._serialize(x) for x in self.requests.find({"created_by": str(user_id or "")}).sort("created_at", -1).limit(300)]
        return {"donations": donations, "requests": requests}

    def normal_profile(self, user_id=None, username=None, name=None):
        return self._find_account_donor(user_id, username, name)

    def normal_update_profile(self, user_id, payload, username=None, name=None):
        donor = self._find_account_donor(user_id, username, name)
        if not donor:
            raise ValueError("Donor profile not found.")
        oid = self._oid(donor.get("_id"))
        # Sensitive/verified fields are intentionally not editable here.
        allowed = self._clean_payload(payload, {
            "full_name", "phone", "email", "district", "upazila", "area", "address", "emergency_contact", "profile_photo"
        })
        allowed["updated_at"] = self._now()
        allowed["updated_by"] = user_id
        if allowed:
            self.donors.update_one({"_id": oid}, {"$set": allowed})
            self._audit("UPDATE_PROFILE", "donor", oid, user_id, {"fields": list(allowed.keys())})
        return self.get_donor(oid)

    def normal_accept_match(self, match_id, user_id):
        oid = self._oid(match_id)
        if not oid:
            raise ValueError("Invalid match ID.")
        match = self.matches.find_one({"_id": oid})
        if not match:
            raise ValueError("Matching donor record not found.")
        if match.get("status") in {"Completed", "Cancelled"}:
            raise ValueError("This donor match is already closed.")
        account_donor = self._find_account_donor(user_id)
        if not account_donor or str(account_donor.get("donor_id") or "") != str(match.get("donor_id") or ""):
            raise ValueError("Only the matched donor can accept this blood request.")
        result = self.matches.update_one(
            {"_id": oid, "status": {"$in": ["Suggested", "Contacted"]}},
            {"$set": {"status": "Accepted", "updated_at": self._now(), "updated_by": user_id}},
        )
        if not result.matched_count:
            raise ValueError("This request is no longer available for acceptance.")
        self._audit("ACCEPT", "request_match", oid, user_id)
        return self._serialize(self.matches.find_one({"_id": oid}))

    # ---------------------------- notifications ----------------------------
    def list_notifications(self, user_id, limit=100):
        rows = self.notifications.find({"user_id": str(user_id)}).sort("created_at", -1).limit(min(int(limit), 200))
        return [self._serialize(x) for x in rows]

    def create_notification(self, user_id, title, message, notification_type="System"):
        record = {
            "user_id": str(user_id),
            "title": str(title).strip(),
            "message": str(message).strip(),
            "type": notification_type if notification_type in NOTIFICATION_TYPES else "System",
            "read": False,
            "created_at": self._now(),
        }
        result = self.notifications.insert_one(record)
        record["_id"] = result.inserted_id
        return self._serialize(record)

    def mark_notification_read(self, notification_id, user_id):
        oid = self._oid(notification_id)
        if not oid:
            return False
        result = self.notifications.update_one({"_id": oid, "user_id": str(user_id)}, {"$set": {"read": True}})
        return bool(result.matched_count)

    # ---------------------------- reports ----------------------------
    def reports(self):
        by_group = list(self.donors.aggregate([{"$group": {"_id": "$blood_group", "count": {"$sum": 1}}}, {"$sort": {"_id": 1}}]))
        by_district = list(self.donors.aggregate([{"$group": {"_id": "$district", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}, {"$limit": 30}]))
        donations_by_month = list(self.donations.aggregate([
            {"$group": {"_id": {"$substr": ["$donation_date", 0, 7]}, "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]))
        return {
            "by_blood_group": self._serialize(by_group),
            "by_district": self._serialize(by_district),
            "donations_by_month": self._serialize(donations_by_month),
        }
