from config.database import db
from models.meal import Meal
from bson import ObjectId
from datetime import datetime
from services.storage_service import StorageService


meals_collection = db["meals"]
meal_locks_collection = db["meal_locks"]
users_collection = db["users"]


class MealService:

    @staticmethod
    def _uid(value):
        return str(value)

    # =========================================================
    # MEMBER LOCK
    # =========================================================

    @staticmethod
    def is_member_locked(user_id):

        uid = MealService._uid(user_id)

        try:
            user = users_collection.find_one({
                "_id": ObjectId(uid)
            })

        except Exception:

            user = users_collection.find_one({
                "_id": uid
            })

        return bool(
            user and
            user.get("locked", False)
        )

    # =========================================================
    # MONTH
    # =========================================================

    @staticmethod
    def get_month_key(date):

        return datetime.strptime(
            str(date),
            "%d-%m-%Y"
        ).strftime("%Y-%m")

    @staticmethod
    def get_month_name(month_key):

        return datetime.strptime(
            str(month_key),
            "%Y-%m"
        ).strftime("%B")

    # =========================================================
    # MONTH LOCK
    # =========================================================

    @staticmethod
    def is_month_locked(
        user_id,
        month_key
    ):

        if not month_key:
            return False

        return meal_locks_collection.find_one({
            "user_id":
                MealService._uid(user_id),

            "month_key":
                str(month_key)
        }) is not None

    @staticmethod
    def toggle_month_lock(
        user_id,
        month_key
    ):

        uid = MealService._uid(user_id)

        if not month_key:
            return False

        existing = meal_locks_collection.find_one({
            "user_id": uid,
            "month_key": str(month_key)
        })

        if existing:

            meal_locks_collection.delete_one({
                "_id": existing["_id"]
            })

            return False

        meal_locks_collection.insert_one({
            "user_id": uid,
            "month_key": str(month_key)
        })

        return True

    # =========================================================
    # ADD MEAL
    # =========================================================

    @staticmethod
    def add_meal(
        user_id,
        name,
        mobile,
        meal_type,
        date,
        meal_charge,
        rice_charge,
        month,
        time,
        note,
        created_by=None
    ):

        uid = MealService._uid(user_id)

        if MealService.is_member_locked(uid):

            return (
                False,
                "This member account is locked. You cannot add or edit meals."
            )

        try:

            month_key = MealService.get_month_key(
                date
            )

            meal = Meal(
                user_id=uid,
                name=name,
                mobile=mobile,
                meal_type=meal_type,
                date=date,
                meal_charge=meal_charge,
                rice_charge=rice_charge,
                month=month,
                time=time,
                note=note
            )

            if MealService.is_month_locked(
                uid,
                month_key
            ):

                return (
                    False,
                    "This meal month is locked."
                )

            data = meal.to_dict()

            if created_by:

                data["created_by"] = (
                    MealService._uid(created_by)
                )

            ok, msg = StorageService.can_add(
                uid,
                data
            )

            if not ok:
                return False, msg

            meals_collection.insert_one(
                data
            )

            return (
                True,
                "Record added successfully."
            )

        except ValueError as exc:

            if "Month does not match" in str(exc):

                return (
                    False,
                    "Selected month does not match the selected date."
                )

            if "Invalid meal type" in str(exc):

                return (
                    False,
                    "Please select a valid meal type."
                )

            return (
                False,
                "Invalid date or meal values."
            )

        except (
            TypeError,
            OverflowError
        ):

            return (
                False,
                "Invalid meal values."
            )

    # =========================================================
    # MONTH SUMMARY
    # =========================================================

    @staticmethod
    def get_month_summaries(user_id):

        uid = MealService._uid(user_id)

        summaries = {}

        for record in meals_collection.find({
            "user_id": uid
        }):

            try:

                key = MealService.get_month_key(
                    record.get("date", "")
                )

                d = datetime.strptime(
                    key,
                    "%Y-%m"
                )

            except (
                ValueError,
                TypeError
            ):

                continue

            summaries.setdefault(
                key,
                {
                    "month_key": key,
                    "month": d.strftime("%B"),
                    "year": d.year,
                    "month_number": d.month,
                    "total_meals": 0,
                    "locked":
                        MealService.is_month_locked(
                            uid,
                            key
                        )
                }
            )

            summaries[key]["total_meals"] += 1

        return sorted(
            summaries.values(),
            key=lambda x: x["month_key"],
            reverse=True
        )

    # =========================================================
    # MONTH MEALS
    # =========================================================

    @staticmethod
    def get_month_meals(
        user_id,
        month_key
    ):

        uid = MealService._uid(user_id)

        result = []

        if not month_key:
            return result

        for record in meals_collection.find(
            {
                "user_id": uid
            }
        ).sort("_id", -1):

            try:

                if (
                    MealService.get_month_key(
                        record.get("date", "")
                    )
                    ==
                    str(month_key)
                ):

                    result.append(record)

            except (
                ValueError,
                TypeError
            ):

                continue

        return result

    # =========================================================
    # ALL MEALS
    #
    # Used by:
    # Meal Management -> Monthly Meal
    #
    # This returns every meal entry of the logged-in member.
    # =========================================================

    @staticmethod
    def get_all_meals(user_id):

        uid = MealService._uid(user_id)

        result = []

        for record in meals_collection.find(
            {
                "user_id": uid
            }
        ).sort("_id", -1):

            result.append(record)

        return result

    # =========================================================
    # DELETE MEAL
    # =========================================================

    @staticmethod
    def delete_meal(
        meal_id,
        user_id
    ):

        uid = MealService._uid(user_id)

        if MealService.is_member_locked(uid):

            return (
                False,
                "Your account is locked. You cannot delete meals.",
                None
            )

        try:

            record = meals_collection.find_one({
                "_id": ObjectId(meal_id),
                "user_id": uid
            })

            if not record:

                return (
                    False,
                    "Meal not found.",
                    None
                )

            key = MealService.get_month_key(
                record.get("date", "")
            )

            if MealService.is_month_locked(
                uid,
                key
            ):

                return (
                    False,
                    "This month is locked. Unlock it before editing/deleting.",
                    None
                )

            result = meals_collection.delete_one({
                "_id": ObjectId(meal_id),
                "user_id": uid
            })

            if result.deleted_count != 1:

                return (
                    False,
                    "Meal not found.",
                    None
                )

            return (
                True,
                "Record permanently deleted.",
                record
            )

        except (
            ValueError,
            TypeError
        ):

            return (
                False,
                "Invalid Meal ID.",
                None
            )

        except Exception:

            return (
                False,
                "Invalid Meal ID.",
                None
            )