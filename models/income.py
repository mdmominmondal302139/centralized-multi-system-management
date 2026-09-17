from datetime import datetime


class Income:
    def __init__(self, user_id, amount, income_type, received_method, source, description, date, time):
        self.user_id = str(user_id)
        self.amount = float(amount)
        self.income_type = income_type
        self.received_method = received_method
        self.source = source
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
            "income_type": self.income_type,
            "received_method": self.received_method,
            "source": self.source,
            "description": self.description,
            "date": self.date,
            "time": self.time,
        }
