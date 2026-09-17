from datetime import datetime

class Saving:
    def __init__(self, user_id, amount, description, date, time):
        self.user_id = user_id
        self.amount = float(amount)
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
            "date": self.date,
            "time": self.time,
            "month": self.month,
            "month_number": self.month_number,
            "year": self.year,
            "amount": self.amount,
            "description": self.description
        }
