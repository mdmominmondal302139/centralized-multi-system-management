# ROLE: OPERATOR
# OPERATOR expense module

def get_expense_scope():
    return {"role": "OPERATOR", "module": "expense"}

def create_expense(data):
    return data

def list_expense(filters=None):
    return []
