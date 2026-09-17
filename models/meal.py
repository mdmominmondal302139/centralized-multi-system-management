from datetime import datetime


class Meal:
    ALLOWED_MEAL_TYPES = {
        "Breakfast",
        "Lunch",
        "Dinner",
        "Extra",
        "Guest",
        "In Dining",
        "Out Dinning"
    }

    def __init__(
        self,
        user_id,
        name,
        mobile,
        meal_type,
        date,
        meal_charge,
        rice_charge,
        month,
        time,
        note=""
    ):
        self.user_id = str(user_id).strip()
        self.name = str(name).strip()
        self.mobile = str(mobile).strip()
        self.meal_type = str(meal_type).strip()
        self.date = self._normalize_date(date)
        self.meal_charge = self._number(meal_charge)
        self.rice_charge = self._number(rice_charge)
        self.month = str(month).strip()
        self.time = str(time).strip()
        self.note = str(note).strip()

        self._validate()

    @staticmethod
    def _number(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValueError(
                "Invalid meal charge or rice charge."
            )

    @staticmethod
    def _normalize_date(value):
        value = str(value).strip()

        if not value:
            raise ValueError("Invalid date.")

        formats = [
            "%d-%m-%Y",
            "%Y-%m-%d"
        ]

        for date_format in formats:
            try:
                parsed = datetime.strptime(
                    value,
                    date_format
                )

                return parsed.strftime(
                    "%d-%m-%Y"
                )

            except ValueError:
                continue

        raise ValueError("Invalid date.")

    def _validate(self):
        if not self.user_id:
            raise ValueError(
                "User ID is required."
            )

        if not self.name:
            raise ValueError(
                "Member name is required."
            )

        if not self.mobile:
            raise ValueError(
                "Member mobile is required."
            )

        if self.meal_type not in self.ALLOWED_MEAL_TYPES:
            raise ValueError(
                "Invalid meal type."
            )

        try:
            selected_date = datetime.strptime(
                self.date,
                "%d-%m-%Y"
            )

        except (TypeError, ValueError):
            raise ValueError(
                "Invalid date."
            )

        if self.month:
            expected_month = selected_date.strftime(
                "%B"
            )

            if self.month.lower() != expected_month.lower():
                raise ValueError(
                    "Month does not match the selected date."
                )

    def to_dict(self):
        selected_date = datetime.strptime(
            self.date,
            "%d-%m-%Y"
        )

        return {
            "user_id": self.user_id,
            "name": self.name,
            "mobile": self.mobile,
            "meal_type": self.meal_type,
            "date": self.date,
            "meal_charge": self.meal_charge,
            "rice_charge": self.rice_charge,
            "month": self.month,
            "month_number": selected_date.month,
            "year": selected_date.year,
            "time": self.time,
            "note": self.note
        }