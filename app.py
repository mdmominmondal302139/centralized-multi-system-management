from datetime import datetime

from services.auth_service import AuthService
from services.developer_service import DeveloperService
from services.expense_service import ExpenseService
from services.income_service import IncomeService
from services.meal_service import MealService
from services.saving_service import SavingService


# =========================================================
# GENERAL HELPERS
# =========================================================

def get_current_date():
    return datetime.now().strftime("%d-%m-%Y")


def get_current_time():
    return datetime.now().strftime("%I:%M %p")


def get_valid_date(label, default_value=None):

    while True:

        if default_value:
            value = input(
                f"{label} [{default_value}]: "
            ).strip()

            if not value:
                return default_value

        else:
            value = input(
                f"{label} (DD-MM-YYYY): "
            ).strip()

        try:
            datetime.strptime(
                value,
                "%d-%m-%Y"
            )
            return value

        except ValueError:
            print(
                "Invalid date. Use DD-MM-YYYY."
            )


def get_valid_time(label, default_value=None):

    while True:

        if default_value:
            value = input(
                f"{label} [{default_value}]: "
            ).strip()

            if not value:
                return default_value

        else:
            value = input(
                f"{label} (HH:MM AM/PM): "
            ).strip()

        try:
            datetime.strptime(
                value,
                "%I:%M %p"
            )
            return value.upper()

        except ValueError:
            print(
                "Invalid time. Example: 02:30 PM"
            )


def get_non_negative_float(label):

    while True:

        try:

            value = float(
                input(f"{label}: ").strip()
            )

            if value < 0:
                print("Value cannot be negative.")
                continue

            return value

        except ValueError:
            print("Please enter a valid number.")


def get_non_negative_int(label):

    while True:

        try:

            value = int(
                input(f"{label}: ").strip()
            )

            if value < 0:
                print("Value cannot be negative.")
                continue

            return value

        except ValueError:
            print("Please enter a valid number.")


# =========================================================
# EXPENSE
# =========================================================

def add_expense(user):

    print("\n========== Add Expense ==========")

    amount = get_non_negative_float(
        "Amount"
    )

    category = input(
        "Category: "
    ).strip()

    description = input(
        "Description: "
    ).strip()

    current_date = get_current_date()
    current_time = get_current_time()

    date = get_valid_date(
        "Date",
        current_date
    )

    time = get_valid_time(
        "Time",
        current_time
    )

    success, message = ExpenseService.add_expense(
        user_id=user["_id"],
        amount=amount,
        category=category,
        description=description,
        date=date,
        time=time
    )

    print(message)


def view_expenses(user):

    print("\n========== View Expenses ==========")

    expenses = ExpenseService.get_expenses(
        user["_id"]
    )

    if not expenses:
        print("No expenses found.")
        return

    print(
        "\nSL   Category       Amount      "
        "Time        Date         Description"
    )

    print("-" * 90)

    for index, expense in enumerate(
        expenses,
        start=1
    ):

        print(
            f"{index:<4}"
            f"{expense.get('category', ''):<15}"
            f"{expense.get('amount', 0):<12.2f}"
            f"{expense.get('time', ''):<12}"
            f"{expense.get('date', ''):<13}"
            f"{expense.get('description', '')}"
        )


def edit_expense(user):

    expenses = ExpenseService.get_expenses(
        user["_id"]
    )

    if not expenses:
        print("\nNo expenses found.")
        return

    view_expenses(user)

    try:

        number = int(
            input(
                "\nEnter SL to edit: "
            ).strip()
        )

        if number < 1 or number > len(expenses):
            print("Invalid SL.")
            return

    except ValueError:

        print("Invalid input.")
        return

    expense = expenses[number - 1]

    old_amount = expense.get(
        "amount",
        0
    )

    old_category = expense.get(
        "category",
        ""
    )

    old_description = expense.get(
        "description",
        ""
    )

    old_date = expense.get(
        "date",
        get_current_date()
    )

    old_time = expense.get(
        "time",
        get_current_time()
    )

    print(
        "\nPress Enter to keep old value."
    )

    amount_input = input(
        f"Amount [{old_amount}]: "
    ).strip()

    if amount_input:

        try:

            amount = float(
                amount_input
            )

            if amount < 0:

                print(
                    "Amount cannot be negative."
                )

                return

        except ValueError:

            print(
                "Invalid amount."
            )

            return

    else:

        amount = old_amount

    category = input(
        f"Category [{old_category}]: "
    ).strip()

    if not category:
        category = old_category

    description = input(
        f"Description [{old_description}]: "
    ).strip()

    if not description:
        description = old_description

    date = get_valid_date(
        "Date",
        old_date
    )

    time = get_valid_time(
        "Time",
        old_time
    )

    success, message = ExpenseService.update_expense(
        expense_id=str(
            expense["_id"]
        ),
        user_id=user["_id"],
        amount=amount,
        category=category,
        description=description,
        date=date,
        time=time
    )

    print(message)


def delete_expense(user):

    expenses = ExpenseService.get_expenses(
        user["_id"]
    )

    if not expenses:
        print("\nNo expenses found.")
        return

    view_expenses(user)

    try:

        number = int(
            input(
                "\nEnter SL to delete: "
            ).strip()
        )

        if number < 1 or number > len(expenses):

            print(
                "Invalid SL."
            )

            return

    except ValueError:

        print(
            "Invalid input."
        )

        return

    expense = expenses[number - 1]

    confirm = input(
        "Are you sure? (y/n): "
    ).strip().lower()

    if confirm != "y":

        print(
            "Delete cancelled."
        )

        return

    success, message = ExpenseService.delete_expense(
        expense_id=str(
            expense["_id"]
        ),
        user_id=user["_id"]
    )

    print(message)


def expense_management(user):

    while True:

        print(
            "\n========== Expense Management =========="
        )

        print("1. Add Expense")
        print("2. View Expenses")
        print("3. Edit Expense")
        print("4. Delete Expense")
        print("5. Back")

        choice = input(
            "Select option: "
        ).strip()

        if choice == "1":

            add_expense(user)

        elif choice == "2":

            view_expenses(user)

        elif choice == "3":

            edit_expense(user)

        elif choice == "4":

            delete_expense(user)

        elif choice == "5":

            break

        else:

            print(
                "Invalid option."
            )


# =========================================================
# INCOME
# =========================================================

def add_income(user):

    print("\n========== Add Income ==========")

    amount = get_non_negative_float(
        "Amount"
    )

    category = input(
        "Category: "
    ).strip()

    description = input(
        "Description: "
    ).strip()

    current_date = get_current_date()
    current_time = get_current_time()

    date = get_valid_date(
        "Date",
        current_date
    )

    time = get_valid_time(
        "Time",
        current_time
    )

    success, message = IncomeService.add_income(
        user_id=user["_id"],
        amount=amount,
        category=category,
        description=description,
        date=date,
        time=time
    )

    print(message)


def view_incomes(user):

    print("\n========== View Income ==========")

    incomes = IncomeService.get_incomes(
        user["_id"]
    )

    if not incomes:
        print("No income found.")
        return

    print(
        "\nSL   Month        Category       "
        "Amount      Time        Date         Description"
    )

    print("-" * 100)

    for index, income in enumerate(
        incomes,
        start=1
    ):

        print(
            f"{index:<4}"
            f"{income.get('month', ''):<13}"
            f"{income.get('category', ''):<15}"
            f"{income.get('amount', 0):<12.2f}"
            f"{income.get('time', ''):<12}"
            f"{income.get('date', ''):<13}"
            f"{income.get('description', '')}"
        )


def edit_income(user):

    incomes = IncomeService.get_incomes(
        user["_id"]
    )

    if not incomes:
        print("\nNo income found.")
        return

    view_incomes(user)

    try:

        number = int(
            input(
                "\nEnter SL to edit: "
            ).strip()
        )

        if number < 1 or number > len(incomes):
            print("Invalid SL.")
            return

    except ValueError:

        print("Invalid input.")
        return

    income = incomes[number - 1]

    old_amount = income.get(
        "amount",
        0
    )

    old_category = income.get(
        "category",
        ""
    )

    old_description = income.get(
        "description",
        ""
    )

    old_date = income.get(
        "date",
        get_current_date()
    )

    old_time = income.get(
        "time",
        get_current_time()
    )

    print(
        "\nPress Enter to keep old value."
    )

    amount_input = input(
        f"Amount [{old_amount}]: "
    ).strip()

    if amount_input:

        try:

            amount = float(
                amount_input
            )

            if amount < 0:

                print(
                    "Amount cannot be negative."
                )

                return

        except ValueError:

            print(
                "Invalid amount."
            )

            return

    else:

        amount = old_amount

    category = input(
        f"Category [{old_category}]: "
    ).strip()

    if not category:
        category = old_category

    description = input(
        f"Description [{old_description}]: "
    ).strip()

    if not description:
        description = old_description

    date = get_valid_date(
        "Date",
        old_date
    )

    time = get_valid_time(
        "Time",
        old_time
    )

    success, message = IncomeService.update_income(
        income_id=str(
            income["_id"]
        ),
        user_id=user["_id"],
        amount=amount,
        category=category,
        description=description,
        date=date,
        time=time
    )

    print(message)


def delete_income(user):

    incomes = IncomeService.get_incomes(
        user["_id"]
    )

    if not incomes:
        print("\nNo income found.")
        return

    view_incomes(user)

    try:

        number = int(
            input(
                "\nEnter SL to delete: "
            ).strip()
        )

        if number < 1 or number > len(incomes):
            print("Invalid SL.")
            return

    except ValueError:

        print("Invalid input.")
        return

    income = incomes[number - 1]

    confirm = input(
        "Are you sure? (y/n): "
    ).strip().lower()

    if confirm != "y":
        print("Delete cancelled.")
        return

    success, message = IncomeService.delete_income(
        income_id=str(
            income["_id"]
        ),
        user_id=user["_id"]
    )

    print(message)


def income_management(user):

    while True:

        print("\n========== Income Management ==========")
        print("1. Add Income")
        print("2. View Income")
        print("3. Edit Income")
        print("4. Delete Income")
        print("5. Back")

        choice = input(
            "Select option: "
        ).strip()

        if choice == "1":
            add_income(user)

        elif choice == "2":
            view_incomes(user)

        elif choice == "3":
            edit_income(user)

        elif choice == "4":
            delete_income(user)

        elif choice == "5":
            break

        else:
            print("Invalid option.")


# =========================================================
# MEAL
# =========================================================

def meal_entry(user):

    print("\n========== Meal Entry ==========")

    print(
        f"Name   : {user.get('name', '')}"
    )

    print(
        f"Mobile : {user.get('mobile', '')}"
    )

    print("\n1. Meal Types")
    print("2. Back")

    choice = input(
        "Select option: "
    ).strip()

    if choice == "2":
        return

    if choice != "1":
        print("Invalid option.")
        return

    print("\n========== Meal Types ==========")

    dinner = get_non_negative_int(
        "Dinner"
    )

    lunch = get_non_negative_int(
        "Lunch"
    )

    breakfast = get_non_negative_int(
        "Breakfast"
    )

    extra = get_non_negative_int(
        "Extra"
    )

    guest = get_non_negative_int(
        "Guest"
    )

    in_dining = get_non_negative_int(
        "In Dining"
    )

    out_dining = get_non_negative_int(
        "Out Dining"
    )

    meal_charge = get_non_negative_float(
        "Meal Charge"
    )

    rice_charge = get_non_negative_float(
        "Rice Charge"
    )

    current_date = get_current_date()
    current_time = get_current_time()

    date = get_valid_date(
        "Date",
        current_date
    )

    time = get_valid_time(
        "Time",
        current_time
    )

    success, message = MealService.add_meal(
        user_id=user["_id"],
        name=user.get("name", ""),
        mobile=user.get("mobile", ""),
        dinner=dinner,
        lunch=lunch,
        breakfast=breakfast,
        extra=extra,
        guest=guest,
        in_dining=in_dining,
        out_dining=out_dining,
        meal_charge=meal_charge,
        rice_charge=rice_charge,
        date=date,
        time=time
    )

    print(message)


def view_recent_meals(user):

    print("\n========== Meal Recent Month ==========")

    now = datetime.now()

    meals = MealService.get_recent_month(
        user_id=user["_id"],
        year=now.year,
        month_number=now.month
    )

    if not meals:
        print("No meal records found.")
        return

    print(
        "\nSL   Name                 "
        "Date         Time        Dinner Lunch Breakfast"
    )

    print("-" * 90)

    for index, meal in enumerate(
        meals,
        start=1
    ):

        print(
            f"{index:<4}"
            f"{meal.get('name', ''):<21}"
            f"{meal.get('date', ''):<13}"
            f"{meal.get('time', ''):<12}"
            f"{meal.get('dinner', 0):<7}"
            f"{meal.get('lunch', 0):<7}"
            f"{meal.get('breakfast', 0):<10}"
        )


def view_all_meals(user):

    print("\n========== Meal All Years ==========")

    meals = MealService.get_all_meals(
        user["_id"]
    )

    if not meals:
        print("No meal records found.")
        return

    print(
        "\nSL   Name                 "
        "Date         Time        Dinner Lunch Breakfast"
    )

    print("-" * 90)

    for index, meal in enumerate(
        meals,
        start=1
    ):

        print(
            f"{index:<4}"
            f"{meal.get('name', ''):<21}"
            f"{meal.get('date', ''):<13}"
            f"{meal.get('time', ''):<12}"
            f"{meal.get('dinner', 0):<7}"
            f"{meal.get('lunch', 0):<7}"
            f"{meal.get('breakfast', 0):<10}"
        )


def meal_management(user):

    while True:

        print("\n========== Meal Management ==========")
        print("1. Meal Entry")
        print("2. Meal Recent Month")
        print("3. Meal All Years")
        print("4. Back")

        choice = input(
            "Select option: "
        ).strip()

        if choice == "1":
            meal_entry(user)

        elif choice == "2":
            view_recent_meals(user)

        elif choice == "3":
            view_all_meals(user)

        elif choice == "4":
            break

        else:
            print("Invalid option.")


# =========================================================
# SAVINGS
# =========================================================

def add_saving(user):

    print("\n========== Add Savings ==========")

    amount = get_non_negative_float(
        "Amount"
    )

    description = input(
        "Description: "
    ).strip()

    current_date = get_current_date()
    current_time = get_current_time()

    date = get_valid_date(
        "Date",
        current_date
    )

    time = get_valid_time(
        "Time",
        current_time
    )

    success, message = SavingService.add_saving(
        user_id=user["_id"],
        amount=amount,
        description=description,
        date=date,
        time=time
    )

    print(message)


def view_savings(user):

    print("\n========== View Savings ==========")

    savings = SavingService.get_savings(
        user["_id"]
    )

    if not savings:
        print("No savings found.")
        return

    print(
        "\nSL   Date         Time        "
        "Month        Amount      Description"
    )

    print("-" * 80)

    for index, saving in enumerate(
        savings,
        start=1
    ):

        print(
            f"{index:<4}"
            f"{saving.get('date', ''):<13}"
            f"{saving.get('time', ''):<12}"
            f"{saving.get('month', ''):<13}"
            f"{saving.get('amount', 0):<12.2f}"
            f"{saving.get('description', '')}"
        )


def savings_management(user):

    while True:

        print("\n========== Savings Management ==========")
        print("1. Add Savings")
        print("2. View Savings")
        print("3. Back")

        choice = input(
            "Select option: "
        ).strip()

        if choice == "1":
            add_saving(user)

        elif choice == "2":
            view_savings(user)

        elif choice == "3":
            break

        else:
            print("Invalid option.")


# =========================================================
# DEVELOPER - MEMBER VIEW
# =========================================================

def print_member_list(members):

    if not members:
        print("No members found.")
        return

    print(
        "\nSL   Name                 Mobile          "
        "Email                         Role"
    )

    print("-" * 100)

    for index, member in enumerate(
        members,
        start=1
    ):

        print(
            f"{index:<4}"
            f"{member.get('name', ''):<21}"
            f"{member.get('mobile', ''):<16}"
            f"{member.get('email', ''):<30}"
            f"{member.get('role', '')}"
        )


def select_member(members):

    if not members:
        return None

    print_member_list(members)

    try:

        number = int(
            input(
                "\nSelect Member SL: "
            ).strip()
        )

        if number < 1 or number > len(members):
            print("Invalid SL.")
            return None

        return members[number - 1]

    except ValueError:

        print("Invalid input.")
        return None


def member_view():

    while True:

        print("\n========== Member View ==========")
        print("1. Active")
        print("2. Inactive")
        print("3. Back")

        choice = input(
            "Select option: "
        ).strip()

        if choice == "1":

            members = DeveloperService.get_active_members()

            if members:
                print("\n========== Active Members ==========")
                print_member_list(members)
            else:
                print("No active members found.")

        elif choice == "2":

            members = DeveloperService.get_inactive_members()

            if members:
                print("\n========== Inactive Members ==========")
                print_member_list(members)
            else:
                print("No inactive members found.")

        elif choice == "3":
            break

        else:
            print("Invalid option.")


# =========================================================
# DEVELOPER - CREATE MEMBER
# =========================================================

def create_member():

    print("\n========== Create Member ==========")

    name = input(
        "Name: "
    ).strip()

    mobile = input(
        "Mobile: "
    ).strip()

    email = input(
        "Email: "
    ).strip()

    password = input(
        "Password: "
    )

    if not name:
        print("Name is required.")
        return

    if not mobile:
        print("Mobile is required.")
        return

    if not email:
        print("Email is required.")
        return

    if not password:
        print("Password is required.")
        return

    print("\nRole")
    print("1. Expense Developer")
    print("2. Manager")

    role_choice = input(
        "Select Role: "
    ).strip()

    if role_choice == "1":
        role = "Expense Developer"

    elif role_choice == "2":
        role = "Manager"

    else:
        print("Invalid role.")
        return

    success, message = DeveloperService.create_member(
        name=name,
        mobile=mobile,
        email=email,
        password=password,
        role=role
    )

    print(message)


# =========================================================
# DEVELOPER - PERMISSION
# =========================================================

def permission_member():

    while True:

        print("\n========== Permission Member ==========")
        print("1. Inactive -> Active")
        print("2. Active -> Inactive")
        print("3. Back")

        choice = input(
            "Select option: "
        ).strip()

        if choice == "1":

            members = DeveloperService.get_inactive_members()

            if not members:
                print("No inactive members found.")
                continue

            member = select_member(members)

            if member:

                success, message = DeveloperService.activate_member(
                    str(member["_id"])
                )

                print(message)

        elif choice == "2":

            members = DeveloperService.get_active_members()

            if not members:
                print("No active members found.")
                continue

            member = select_member(members)

            if member:

                success, message = DeveloperService.deactivate_member(
                    str(member["_id"])
                )

                print(message)

        elif choice == "3":
            break

        else:
            print("Invalid option.")


# =========================================================
# DEVELOPER - MEMBER DATA
# =========================================================

def view_member_income():

    members = DeveloperService.get_active_members()

    member = select_member(members)

    if not member:
        return

    print(
        f"\n========== Income: {member.get('name', '')} =========="
    )

    incomes = IncomeService.get_incomes(
        member["_id"]
    )

    if not incomes:
        print("No income found.")
        return

    print(
        "\nSL   Month        Category       "
        "Amount      Time        Date         Description"
    )

    print("-" * 100)

    for index, income in enumerate(
        incomes,
        start=1
    ):

        print(
            f"{index:<4}"
            f"{income.get('month', ''):<13}"
            f"{income.get('category', ''):<15}"
            f"{income.get('amount', 0):<12.2f}"
            f"{income.get('time', ''):<12}"
            f"{income.get('date', ''):<13}"
            f"{income.get('description', '')}"
        )


def view_member_expense():

    members = DeveloperService.get_active_members()

    member = select_member(members)

    if not member:
        return

    print(
        f"\n========== Expense: {member.get('name', '')} =========="
    )

    expenses = ExpenseService.get_expenses(
        member["_id"]
    )

    if not expenses:
        print("No expenses found.")
        return

    print(
        "\nSL   Category       Amount      "
        "Time        Date         Description"
    )

    print("-" * 90)

    for index, expense in enumerate(
        expenses,
        start=1
    ):

        print(
            f"{index:<4}"
            f"{expense.get('category', ''):<15}"
            f"{expense.get('amount', 0):<12.2f}"
            f"{expense.get('time', ''):<12}"
            f"{expense.get('date', ''):<13}"
            f"{expense.get('description', '')}"
        )


def view_member_meals():

    members = DeveloperService.get_active_members()

    member = select_member(members)

    if not member:
        return

    print(
        f"\n========== Meals: {member.get('name', '')} =========="
    )

    meals = MealService.get_all_meals(
        member["_id"]
    )

    if not meals:
        print("No meals found.")
        return

    print(
        "\nSL   Name                 Date         "
        "Time        Dinner Lunch Breakfast"
    )

    print("-" * 90)

    for index, meal in enumerate(
        meals,
        start=1
    ):

        print(
            f"{index:<4}"
            f"{meal.get('name', ''):<21}"
            f"{meal.get('date', ''):<13}"
            f"{meal.get('time', ''):<12}"
            f"{meal.get('dinner', 0):<7}"
            f"{meal.get('lunch', 0):<7}"
            f"{meal.get('breakfast', 0):<10}"
        )


def view_member_savings():

    members = DeveloperService.get_active_members()

    member = select_member(members)

    if not member:
        return

    print(
        f"\n========== Savings: {member.get('name', '')} =========="
    )

    savings = SavingService.get_savings(
        member["_id"]
    )

    if not savings:
        print("No savings found.")
        return

    print(
        "\nSL   Date         Time        "
        "Month        Amount      Description"
    )

    print("-" * 80)

    for index, saving in enumerate(
        savings,
        start=1
    ):

        print(
            f"{index:<4}"
            f"{saving.get('date', ''):<13}"
            f"{saving.get('time', ''):<12}"
            f"{saving.get('month', ''):<13}"
            f"{saving.get('amount', 0):<12.2f}"
            f"{saving.get('description', '')}"
        )


# =========================================================
# DEVELOPER DEPARTMENT
# =========================================================

def developer_department(user):

    if user.get("role") != "Expense Developer":

        print(
            "\nAccess denied."
        )

        return

    while True:

        print(
            "\n========== Developer Department =========="
        )

        print("1. Create Member")
        print("2. Member View")
        print("3. Permission Member")
        print("4. View Member Income")
        print("5. View Member Expense")
        print("6. View Member Meals")
        print("7. View Member Savings")
        print("8. Back")

        choice = input(
            "Select option: "
        ).strip()

        if choice == "1":
            create_member()

        elif choice == "2":
            member_view()

        elif choice == "3":
            permission_member()

        elif choice == "4":
            view_member_income()

        elif choice == "5":
            view_member_expense()

        elif choice == "6":
            view_member_meals()

        elif choice == "7":
            view_member_savings()

        elif choice == "8":
            break

        else:
            print("Invalid option.")


# =========================================================
# REGISTER
# =========================================================

def register():

    print("\n========== Register ==========")

    name = input(
        "Name: "
    ).strip()

    mobile = input(
        "Mobile: "
    ).strip()

    email = input(
        "Email: "
    ).strip()

    password = input(
        "Password: "
    )

    if not name:
        print("Name is required.")
        return

    if not mobile:
        print("Mobile is required.")
        return

    if not email:
        print("Email is required.")
        return

    if not password:
        print("Password is required.")
        return

    success, message = AuthService.register(
        name=name,
        mobile=mobile,
        email=email,
        password=password
    )

    print(message)


# =========================================================
# LOGIN
# =========================================================

def login():

    print("\n========== Login ==========")

    login_value = input(
        "Name or Mobile: "
    ).strip()

    password = input(
        "Password: "
    )

    success, message, user = AuthService.login(
        login_value=login_value,
        password=password
    )

    print(message)

    if not success:
        return None

    return user


# =========================================================
# LOGGED-IN USER MENU
# =========================================================

def user_menu(user):

    while True:

        print(
            "\n========================================"
        )

        print(
            f"Welcome, {user.get('name', '')}"
        )

        print(
            f"Role: {user.get('role', '')}"
        )

        print(
            "========================================"
        )

        print("1. Income")
        print("2. Expense")
        print("3. Meal Management")
        print("4. Savings")
        print("5. Developer Department")
        print("6. Login")
        print("7. Register")
        print("8. Logout")

        choice = input(
            "Select option: "
        ).strip()

        if choice == "1":

            income_management(user)

        elif choice == "2":

            expense_management(user)

        elif choice == "3":

            meal_management(user)

        elif choice == "4":

            savings_management(user)

        elif choice == "5":

            if user.get("role") == "Expense Developer":

                developer_department(user)

            else:

                print(
                    "\nAccess denied."
                )

                print(
                    "Only Expense Developer can access Developer Department."
                )

        elif choice == "6":

            print(
                "\nYou are already logged in."
            )

        elif choice == "7":

            print(
                "\nRegistration is available from the main menu."
            )

        elif choice == "8":

            print(
                "\nLogged out successfully."
            )

            break

        else:

            print(
                "Invalid option."
            )


# =========================================================
# MAIN MENU
# =========================================================

def main():

    while True:

        print(
            "\n========================================"
        )

        print(
            "     DEVELOPMENT MY EXPENSE SOFTWARE"
        )

        print(
            "========================================"
        )

        print("1. Income")
        print("2. Expense")
        print("3. Meal Management")
        print("4. Savings")
        print("5. Developer Department")
        print("6. Login")
        print("7. Register")
        print("8. Exit")

        choice = input(
            "Select option: "
        ).strip()

        # -------------------------------------------------
        # Login
        # -------------------------------------------------

        if choice == "6":

            user = login()

            if user:

                user_menu(user)

        # -------------------------------------------------
        # Register
        # -------------------------------------------------

        elif choice == "7":

            register()

        # -------------------------------------------------
        # Other options require login
        # -------------------------------------------------

        elif choice in [
            "1",
            "2",
            "3",
            "4",
            "5"
        ]:

            print(
                "\nPlease Login first."
            )

        # -------------------------------------------------
        # Exit
        # -------------------------------------------------

        elif choice == "8":

            print(
                "\nThank you for using "
                "Development My Expense Software."
            )

            break

        else:

            print(
                "Invalid option."
            )


# =========================================================
# START PROGRAM
# =========================================================

if __name__ == "__main__":

    main()