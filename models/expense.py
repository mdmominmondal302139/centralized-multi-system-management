from datetime import datetime


class Expense:
    def __init__(self, user_id, amount, category, description, date, time):
        self.user_id = str(user_id)
        self.amount = float(amount)
        self.category = category
        self.description = description
        self.date = date
        self.time = time

        date_object = datetime.strptime(date, "%d-%m-%Y")
        self.month = date_object.strftime("%B")
        self.month_number = date_object.month
        self.year = date_object.year

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "month": self.month,
            "month_number": self.month_number,
            "year": self.year,
            "amount": self.amount,
            "category": self.category,
            "description": self.description,
            "date": self.date,
            "time": self.time,
        }
