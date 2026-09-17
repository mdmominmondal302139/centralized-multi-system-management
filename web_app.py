from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session
)

from services.auth_service import AuthService
from services.income_service import IncomeService
from services.expense_service import ExpenseService
from services.meal_service import MealService
from meal import register_meal_routes
from services.saving_service import SavingService
from services.developer_service import DeveloperService
from services.audit_service import AuditService
from services.request_service import RequestService
from services.storage_service import StorageService

from config.database import db
from bson import ObjectId
from datetime import datetime

import os
from urllib.parse import urlencode


app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "development-my-expense-software-secret-key"
)


# =========================================================
# COMMON HELPERS
# =========================================================

def logged_in():
    return "user_id" in session


def current_user():

    if not logged_in():
        return None

    try:

        return db["users"].find_one(
            {
                "_id": ObjectId(
                    session["user_id"]
                )
            }
        )

    except Exception:

        return None


def role():

    u = current_user()

    return (
        u.get("role", "")
        if u
        else ""
    )


def developer_only():

    return role() == "Expense Developer"


def manager_only():

    return role() in (
        "Manager",
        "Expense Developer"
    )


def now_values():

    d = datetime.now()

    return (
        d.strftime("%d-%m-%Y"),
        d.strftime("%I:%M %p")
    )


def set_message(
    message,
    message_type="success"
):

    session["page_message"] = {
        "text": message,
        "type": message_type
    }


def consume_message():

    return session.pop(
        "page_message",
        None
    )


def unauthorized():

    set_message(
        "Access denied.",
        "error"
    )

    if logged_in():

        return redirect(
            url_for("dashboard")
        )

    return redirect(
        url_for("login")
    )


def month_key(
    value,
    year=None
):

    if not value:
        return None

    if year:

        try:

            return datetime.strptime(
                f"{value} {year}",
                "%B %Y"
            ).strftime("%Y-%m")

        except Exception:

            return None

    return str(value)


def active_members(
    exclude=None
):

    rows = (
        DeveloperService.get_active_members()
    )

    return [
        r
        for r in rows
        if (
            not exclude
            or str(r.get("_id"))
            != str(exclude)
        )
    ]


# =========================================================
# EMBEDDED WORKING PAGE HELPERS
# =========================================================

def embedded_url(
    endpoint,
    **values
):

    values["embedded"] = "1"

    return url_for(
        endpoint,
        **values
    )


def embedded_redirect(
    endpoint,
    **values
):

    return redirect(
        embedded_url(
            endpoint,
            **values
        )
    )


def redirect_referrer_or_embedded(
    default_endpoint,
    **default_values
):

    referrer = request.referrer or ""

    if (
        referrer
        and "embedded=1" in referrer
    ):

        return redirect(
            referrer
        )

    return embedded_redirect(
        default_endpoint,
        **default_values
    )


# =========================================================
# PERMANENT DASHBOARD / SIDEBAR ROUTING
# =========================================================

SHELL_MODULES = {
    "income",
    "expense",
    "meal",
    "savings",
    "developer"
}


def is_shell_module_path(path):

    if not path:
        return False

    clean_path = path.rstrip("/")

    if clean_path == "":
        return False

    parts = clean_path.split("/")

    if (
        len(parts) >= 2
        and parts[1] in SHELL_MODULES
    ):

        return True

    return False


def dashboard_open_url():

    path = request.path

    args = request.args.to_dict(
        flat=False
    )

    args.pop(
        "embedded",
        None
    )

    query_parts = []

    for key, values in args.items():

        for value in values:

            query_parts.append(
                (
                    key,
                    value
                )
            )

    if query_parts:

        query = urlencode(
            query_parts,
            doseq=True
        )

        target = (
            f"{path}?{query}"
        )

    else:

        target = path

    return url_for(
        "dashboard",
        open=target
    )


@app.before_request
def permanent_sidebar_guard():

    if not logged_in():
        return None

    path = request.path.rstrip("/")

    if path == "/dashboard":
        return None

    if not is_shell_module_path(
        request.path
    ):
        return None

    if request.args.get(
        "embedded"
    ) == "1":

        return None

    if request.method == "POST":

        referer = request.referrer or ""

        dashboard_prefix = (
            request.host_url.rstrip("/")
            + "/dashboard"
        )

        if referer.startswith(
            dashboard_prefix
        ):

            return None

    return redirect(
        dashboard_open_url()
    )


# =========================================================
# HOME GRAPH HELPERS
# =========================================================

def number_value(value):

    try:

        return float(
            value or 0
        )

    except (
        TypeError,
        ValueError
    ):

        return 0.0


def calculate_home_graph(
    user_id
):

    # -----------------------------------------------------
    # INCOME
    # -----------------------------------------------------

    income_total = 0.0

    try:

        income_records = db[
            "incomes"
        ].find(
            {
                "user_id": str(user_id)
            }
        )

        for record in income_records:

            income_total += number_value(
                record.get(
                    "amount",
                    0
                )
            )

    except Exception:

        income_total = 0.0


    # -----------------------------------------------------
    # EXPENSE
    # -----------------------------------------------------

    expense_total = 0.0

    try:

        expense_records = db[
            "expenses"
        ].find(
            {
                "user_id": str(user_id)
            }
        )

        for record in expense_records:

            expense_total += number_value(
                record.get(
                    "amount",
                    0
                )
            )

    except Exception:

        expense_total = 0.0


    # -----------------------------------------------------
    # MEAL
    # -----------------------------------------------------

    meal_total = 0.0

    try:

        meal_records = db[
            "meals"
        ].find(
            {
                "user_id": str(user_id)
            }
        )

        for record in meal_records:

            meal_charge = number_value(
                record.get(
                    "meal_charge",
                    0
                )
            )

            rice_charge = number_value(
                record.get(
                    "rice_charge",
                    0
                )
            )

            meal_total += (
                meal_charge
                + rice_charge
            )

    except Exception:

        meal_total = 0.0


    # -----------------------------------------------------
    # SAVINGS
    # -----------------------------------------------------

    savings_total = 0.0

    try:

        savings_records = db[
            "savings"
        ].find(
            {
                "user_id": str(user_id)
            }
        )

        for record in savings_records:

            savings_total += number_value(
                record.get(
                    "amount",
                    0
                )
            )

    except Exception:

        savings_total = 0.0


    # -----------------------------------------------------
    # TOTAL
    # -----------------------------------------------------

    graph_total = (
        income_total
        + expense_total
        + meal_total
        + savings_total
    )


    # -----------------------------------------------------
    # PERCENTAGES
    # -----------------------------------------------------

    if graph_total > 0:

        income_percent = (
            income_total
            / graph_total
        ) * 100

        expense_percent = (
            expense_total
            / graph_total
        ) * 100

        meal_percent = (
            meal_total
            / graph_total
        ) * 100

        savings_percent = (
            savings_total
            / graph_total
        ) * 100

    else:

        income_percent = 0.0
        expense_percent = 0.0
        meal_percent = 0.0
        savings_percent = 0.0


    return {

        "income_total":
            income_total,

        "expense_total":
            expense_total,

        "meal_total":
            meal_total,

        "savings_total":
            savings_total,

        "graph_total":
            graph_total,

        "income_percent":
            income_percent,

        "expense_percent":
            expense_percent,

        "meal_percent":
            meal_percent,

        "savings_percent":
            savings_percent
    }


# =========================================================
# HOME
# =========================================================

@app.route("/")
def index():

    return redirect(
        url_for("login")
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    message = consume_message()

    if request.method == "POST":

        # -------------------------------------------------
        # ONLY USERNAME IS ACCEPTED
        # -------------------------------------------------

        login_value = request.form.get(
            "login_value",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        # -------------------------------------------------
        # AUTH SERVICE
        # -------------------------------------------------

        ok, msg, user = AuthService.login(
            login_value,
            password
        )

        if ok:

            session.clear()

            session["user_id"] = str(
                user["_id"]
            )

            session["role"] = user.get(
                "role",
                "Member"
            )

            # ---------------------------------------------
            # LOGIN AUDIT
            # ---------------------------------------------

            AuditService.log(
                user["_id"],
                "Login",
                "Login successful",
                user
            )

            set_message(
                "Login successful!",
                "success"
            )

            return redirect(
                url_for("dashboard")
            )

        # -------------------------------------------------
        # LOGIN FAILED
        # -------------------------------------------------

        AuditService.log(
            None,
            "Login Fail",
            (
                "Login failed for "
                f"username: {login_value}"
            ),
            None
        )

        message = {
            "text": msg,
            "type": "error"
        }


    return render_template(
        "login.html",

        message=(
            message.get("text")
            if message
            else None
        ),

        message_type=(
            message.get("type")
            if message
            else "error"
        )
    )


# =========================================================
# NOTE:
#
# PUBLIC /REGISTER ROUTE IS INTENTIONALLY REMOVED.
#
# Accounts can ONLY be created through:
#
# Expense Developer
#      ↓
# Developer Department
#      ↓
# Member Create
#
# =========================================================


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if not logged_in():

        return redirect(
            url_for("login")
        )

    message = consume_message()

    u = current_user()

    storage = StorageService.percent()

    graph = calculate_home_graph(
        session["user_id"]
    )

    initial_page = request.args.get(
        "open",
        ""
    ).strip()

    if initial_page:

        if not initial_page.startswith(
            "/"
        ):

            initial_page = ""

        elif initial_page.startswith(
            "//"
        ):

            initial_page = ""

        elif initial_page.startswith(
            "/dashboard"
        ):

            initial_page = ""

    return render_template(
        "dashboard.html",

        user=u,

        storage=storage,

        initial_page=initial_page,

        message=(
            message.get("text")
            if message
            else None
        ),

        message_type=(
            message.get("type")
            if message
            else "success"
        ),

        income_total=graph[
            "income_total"
        ],

        expense_total=graph[
            "expense_total"
        ],

        meal_total=graph[
            "meal_total"
        ],

        savings_total=graph[
            "savings_total"
        ],

        graph_total=graph[
            "graph_total"
        ],

        income_percent=graph[
            "income_percent"
        ],

        expense_percent=graph[
            "expense_percent"
        ],

        meal_percent=graph[
            "meal_percent"
        ],

        savings_percent=graph[
            "savings_percent"
        ]
    )


# =========================================================
# INCOME
# =========================================================

@app.route(
    "/income",
    methods=["GET", "POST"]
)
def income():

    if not logged_in():

        return redirect(
            url_for("login")
        )

    uid = session["user_id"]

    message = consume_message()

    view = request.args.get(
        "view",
        "add"
    ).strip().lower()

    if view not in {
        "add",
        "monthly"
    }:

        view = "add"

    selected = month_key(
        request.args.get("month"),
        request.args.get("year")
    )

    if request.method == "POST":

        ok, msg = IncomeService.add_income(

            uid,

            request.form.get(
                "amount",
                ""
            ),

            request.form.get(
                "income_type",
                ""
            ).strip(),

            request.form.get(
                "received_method",
                ""
            ).strip(),

            request.form.get(
                "source",
                ""
            ).strip(),

            request.form.get(
                "description",
                ""
            ).strip() or "N/A",

            request.form.get(
                "date",
                ""
            ),

            request.form.get(
                "time",
                ""
            )
        )

        if ok:

            AuditService.log(
                uid,
                "Income",
                (
                    "Add Income: "
                    f"{request.form.get('amount', '')}"
                ),
                current_user()
            )

            set_message(
                "Record added successfully."
            )

            return embedded_redirect(
                "income",
                view="add"
            )

        message = {
            "text": msg,
            "type": "error"
        }

    locked = bool(
        selected
        and IncomeService.is_month_locked(
            uid,
            selected
        )
    )

    return render_template(
        "income.html",

        view=view,

        summaries=(
            IncomeService.get_month_summaries(
                uid
            )
        ),

        selected_month=selected,

        selected_locked=locked,

        month_incomes=(
            IncomeService.get_month_incomes(
                uid,
                selected
            )
            if selected
            else []
        ),

        current_date=now_values()[0],

        current_time=now_values()[1],

        message=(
            message.get("text")
            if message
            else None
        ),

        message_type=(
            message.get("type")
            if message
            else "success"
        ),

        user=current_user()
    )


@app.route("/income/lock")
def income_lock():

    if not logged_in():

        return redirect(
            url_for("login")
        )

    uid = session["user_id"]

    key = request.args.get(
        "month"
    )

    if not key:

        return embedded_redirect(
            "income",
            view="monthly"
        )

    if (
        IncomeService.is_month_locked(
            uid,
            key
        )
        and not developer_only()
    ):

        set_message(
            "Locked month cannot be unlocked by this account.",
            "error"
        )

        return embedded_redirect(
            "income",
            view="monthly",
            month=key
        )

    new = IncomeService.toggle_month_lock(
        uid,
        key
    )

    set_message(
        "Month locked successfully."
        if new
        else "Month unlocked successfully."
    )

    return embedded_redirect(
        "income",
        view="monthly",
        month=key
    )


@app.route(
    "/income/delete/<income_id>"
)
def income_delete(
    income_id
):

    if not logged_in():

        return redirect(
            url_for("login")
        )

    ok, msg, old = (
        IncomeService.delete_income(
            income_id,
            session["user_id"]
        )
    )

    if ok:

        AuditService.log(
            session["user_id"],
            "Delete",
            {
                "module": "Income",
                "record": old
            },
            current_user()
        )

    set_message(
        msg,
        "success"
        if ok
        else "error"
    )

    return redirect_referrer_or_embedded(
        "income",
        view="monthly"
    )


@app.route(
    "/income/delete-month"
)
def income_delete_month():

    if not logged_in():

        return redirect(
            url_for("login")
        )

    key = request.args.get(
        "month"
    )

    records = (
        IncomeService.get_month_incomes(
            session["user_id"],
            key
        )
        if key
        else []
    )

    ok, msg = IncomeService.delete_month(
        session["user_id"],
        key
    )

    if ok:

        for r in records:

            AuditService.log(
                session["user_id"],
                "Delete",
                {
                    "module": "Income",
                    "record": r
                },
                current_user()
            )

    set_message(
        msg,
        "success"
        if ok
        else "error"
    )

    return embedded_redirect(
        "income",
        view="monthly"
    )


# =========================================================
# EXPENSE
# =========================================================

@app.route(
    "/expense",
    methods=["GET", "POST"]
)
def expense():

    if not logged_in():

        return redirect(
            url_for("login")
        )

    uid = session["user_id"]

    message = consume_message()

    view = request.args.get(
        "view",
        "add"
    ).strip().lower()

    if view not in {
        "add",
        "monthly"
    }:

        view = "add"

    selected = month_key(
        request.args.get("month"),
        request.args.get("year")
    )

    if request.method == "POST":

        data = {

            "amount": request.form.get(
                "amount",
                ""
            ),

            "category": request.form.get(
                "category",
                ""
            ).strip(),

            "description": request.form.get(
                "description",
                ""
            ).strip() or "N/A",

            "date": request.form.get(
                "date",
                ""
            ),

            "time": request.form.get(
                "time",
                ""
            )
        }

        eid = request.form.get(
            "expense_id"
        )

        if eid:

            ok, msg, old, new = (
                ExpenseService.update_expense(
                    eid,
                    uid,
                    **data
                )
            )

            if ok:

                AuditService.log(
                    uid,
                    "Edit",
                    {
                        "module": "Expense",
                        "before": old,
                        "after": new
                    },
                    current_user()
                )

        else:

            ok, msg = (
                ExpenseService.add_expense(
                    uid,
                    **data
                )
            )

            if ok:

                AuditService.log(
                    uid,
                    "Expense",
                    {
                        "module": "Expense",
                        "record": data
                    },
                    current_user()
                )

        if ok:

            set_message(msg)

            return embedded_redirect(
                "expense",
                view="add"
            )

        message = {
            "text": msg,
            "type": "error"
        }

    locked = bool(
        selected
        and ExpenseService.is_month_locked(
            uid,
            selected
        )
    )

    edit = None

    if (
        request.args.get("edit")
        and not locked
    ):

        try:

            edit = db["expenses"].find_one({

                "_id": ObjectId(
                    request.args["edit"]
                ),

                "user_id": uid
            })

        except Exception:

            edit = None

    return render_template(
        "expense.html",

        view=view,

        summaries=(
            ExpenseService.get_month_summaries(
                uid
            )
        ),

        selected_month=selected,

        selected_locked=locked,

        month_expenses=(
            ExpenseService.get_month_expenses(
                uid,
                selected
            )
            if selected
            else []
        ),

        edit_expense=edit,

        current_date=now_values()[0],

        current_time=now_values()[1],

        message=(
            message.get("text")
            if message
            else None
        ),

        message_type=(
            message.get("type")
            if message
            else "success"
        ),

        user=current_user()
    )


@app.route(
    "/expense/month/lock"
)
def expense_month_lock():

    if not logged_in():

        return redirect(
            url_for("login")
        )

    uid = session["user_id"]

    key = request.args.get(
        "month"
    )

    if (
        ExpenseService.is_month_locked(
            uid,
            key
        )
        and not developer_only()
    ):

        set_message(
            "Locked month cannot be unlocked by this account.",
            "error"
        )

        return embedded_redirect(
            "expense",
            view="monthly",
            month=key
        )

    new = ExpenseService.toggle_month_lock(
        uid,
        key
    )

    set_message(
        "Month locked successfully."
        if new
        else "Month unlocked successfully."
    )

    return embedded_redirect(
        "expense",
        view="monthly",
        month=key
    )


@app.route(
    "/expense/month/unlock"
)
def expense_month_unlock():

    if not developer_only():

        return unauthorized()

    key = request.args.get(
        "month"
    )

    if (
        key
        and ExpenseService.is_month_locked(
            session["user_id"],
            key
        )
    ):

        ExpenseService.toggle_month_lock(
            session["user_id"],
            key
        )

    set_message(
        "Month unlocked successfully."
    )

    return embedded_redirect(
        "expense",
        view="monthly",
        month=key
    )


@app.route(
    "/expense/delete/<expense_id>"
)
def expense_delete(
    expense_id
):

    if not logged_in():

        return redirect(
            url_for("login")
        )

    ok, msg, old = (
        ExpenseService.delete_expense(
            expense_id,
            session["user_id"]
        )
    )

    if ok:

        AuditService.log(
            session["user_id"],
            "Delete",
            {
                "module": "Expense",
                "record": old
            },
            current_user()
        )

    set_message(
        msg,
        "success"
        if ok
        else "error"
    )

    return redirect_referrer_or_embedded(
        "expense",
        view="monthly"
    )


@app.route(
    "/expense/delete-month"
)
def expense_delete_month():

    if not logged_in():

        return redirect(
            url_for("login")
        )

    uid = session["user_id"]

    key = request.args.get(
        "month"
    )

    records = ExpenseService.get_month_expenses(
        uid,
        key
    )

    if (
        ExpenseService.is_member_locked(uid)
        or ExpenseService.is_month_locked(
            uid,
            key
        )
    ):

        set_message(
            "This month is locked. Unlock it before editing/deleting.",
            "error"
        )

        return embedded_redirect(
            "expense",
            view="monthly",
            month=key
        )

    db["expenses"].delete_many({

        "_id": {
            "$in": [
                r["_id"]
                for r in records
            ]
        }

    })

    for r in records:

        AuditService.log(
            uid,
            "Delete",
            {
                "module": "Expense",
                "record": r
            },
            current_user()
        )

    set_message(
        "Record permanently deleted."
    )

    return embedded_redirect(
        "expense",
        view="monthly"
    )


# =========================================================
# SAVINGS
# =========================================================

@app.route(
    "/savings",
    methods=["GET", "POST"]
)
def savings():

    if not logged_in():

        return redirect(
            url_for("login")
        )

    uid = session["user_id"]

    message = consume_message()

    view = request.args.get(
        "view",
        "add"
    ).strip().lower()

    if view not in {
        "add",
        "monthly"
    }:

        view = "add"

    selected = month_key(
        request.args.get("month"),
        request.args.get("year")
    )

    if request.method == "POST":

        if request.form.get(
            "action"
        ) == "edit":

            ok, msg, old, new = (
                SavingService.update_saving(

                    request.form.get(
                        "saving_id"
                    ),

                    uid,

                    request.form.get(
                        "amount"
                    ),

                    request.form.get(
                        "description",
                        ""
                    ).strip() or "N/A",

                    request.form.get(
                        "date"
                    ),

                    request.form.get(
                        "time"
                    )
                )
            )

        else:

            ok, msg = (
                SavingService.add_saving(

                    uid,

                    request.form.get(
                        "amount"
                    ),

                    request.form.get(
                        "description",
                        ""
                    ).strip() or "N/A",

                    request.form.get(
                        "date"
                    ),

                    request.form.get(
                        "time"
                    )
                )
            )

            old = None
            new = None

        if ok:

            if request.form.get(
                "action"
            ) == "edit":

                AuditService.log(
                    uid,
                    "Edit",
                    {
                        "module": "Savings",
                        "before": old,
                        "after": new
                    },
                    current_user()
                )

            else:

                AuditService.log(
                    uid,
                    "Savings",
                    {
                        "module": "Savings",
                        "record": request.form.to_dict()
                    },
                    current_user()
                )

            set_message(msg)

            return embedded_redirect(
                "savings",
                view="add"
            )

        message = {
            "text": msg,
            "type": "error"
        }

    locked = bool(
        selected
        and SavingService.is_month_locked(
            uid,
            selected
        )
    )

    edit = None

    if (
        request.args.get("edit_id")
        and not locked
    ):

        try:

            edit = db["savings"].find_one({

                "_id": ObjectId(
                    request.args["edit_id"]
                ),

                "user_id": uid
            })

            view = "add"

        except Exception:

            edit = None

    return render_template(
        "savings.html",

        view=view,

        summaries=(
            SavingService.get_month_summaries(
                uid
            )
        ),

        selected_month=selected,

        selected_locked=locked,

        month_savings=(
            SavingService.get_month_savings(
                uid,
                selected
            )
            if selected
            else []
        ),

        edit_record=edit,

        current_date=now_values()[0],

        current_time=now_values()[1],

        message=(
            message.get("text")
            if message
            else None
        ),

        message_type=(
            message.get("type")
            if message
            else "success"
        ),

        user=current_user(),

        developer=developer_only()
    )


@app.route("/savings/lock")
def savings_lock():

    if not logged_in():

        return redirect(
            url_for("login")
        )

    uid = session["user_id"]

    key = request.args.get(
        "month"
    )

    if (
        SavingService.is_month_locked(
            uid,
            key
        )
        and not developer_only()
    ):

        set_message(
            "Locked month cannot be unlocked by this account.",
            "error"
        )

        return embedded_redirect(
            "savings",
            view="monthly",
            month=key
        )

    new = SavingService.toggle_month_lock(
        uid,
        key
    )

    set_message(
        "Month locked successfully."
        if new
        else "Month unlocked successfully."
    )

    return embedded_redirect(
        "savings",
        view="monthly",
        month=key
    )


@app.route(
    "/savings/delete/<saving_id>"
)
def savings_delete(
    saving_id
):

    if not logged_in():

        return redirect(
            url_for("login")
        )

    ok, msg, old = (
        SavingService.delete_saving(
            saving_id,
            session["user_id"]
        )
    )

    if ok:

        AuditService.log(
            session["user_id"],
            "Delete",
            {
                "module": "Savings",
                "record": old
            },
            current_user()
        )

    set_message(
        msg,
        "success"
        if ok
        else "error"
    )

    return redirect_referrer_or_embedded(
        "savings",
        view="monthly"
    )


# =========================================================
# MEAL LOCK
# =========================================================

@app.route("/meal/lock")
def meal_lock():

    if not logged_in():

        return redirect(
            url_for("login")
        )

    uid = session["user_id"]

    key = request.args.get(
        "month"
    )

    if (
        MealService.is_month_locked(
            uid,
            key
        )
        and not developer_only()
    ):

        set_message(
            "Locked month cannot be unlocked by this account.",
            "error"
        )

        return embedded_redirect(
            "meal",
            month=key
        )

    new = MealService.toggle_month_lock(
        uid,
        key
    )

    set_message(
        "Month locked successfully."
        if new
        else "Month unlocked successfully."
    )

    return embedded_redirect(
        "meal",
        month=key
    )


# =========================================================
# DEVELOPER
# =========================================================

def member_history(uid):

    return any(

        db[c].find_one({
            "user_id": str(uid)
        })

        for c in [
            "incomes",
            "expenses",
            "meals",
            "savings"
        ]
    )


@app.route("/developer")
def developer_department():

    if not developer_only():

        return unauthorized()

    message = consume_message()

    storage = StorageService.percent()

    u = current_user()

    view = request.args.get(
        "view",
        "create"
    ).strip().lower()

    allowed_views = {
        "create",
        "summary",
        "inactive",
        "members",
        "storage"
    }

    if view not in allowed_views:

        view = "create"

    return render_template(
        "developer.html",

        view=view,

        members=(
            DeveloperService.get_active_members()
        ),

        inactive_members=(
            DeveloperService.get_inactive_members()
        ),

        storage=storage,

        message=(
            message.get("text")
            if message
            else None
        ),

        message_type=(
            message.get("type")
            if message
            else "success"
        ),

        requests=RequestService.get_all(),

        current_user=u
    )


# =========================================================
# DEVELOPER ALIAS
# =========================================================

@app.route(
    "/developer",
    endpoint="developer"
)
def developer():

    return developer_department()


# =========================================================
# DEVELOPER MEMBER CREATE
# =========================================================

@app.route(
    "/developer/member/create",
    methods=["POST"]
)
def developer_member_create():

    # ONLY EXPENSE DEVELOPER
    if not developer_only():

        return unauthorized()

    role_value = request.form.get(
        "role",
        ""
    )

    if role_value not in (
        "Manager",
        "Expense Developer"
    ):

        set_message(
            "Invalid account role.",
            "error"
        )

        return embedded_redirect(
            "developer_department",
            view="create"
        )

    ok, msg = DeveloperService.create_member(

        request.form.get(
            "name",
            ""
        ).strip(),

        request.form.get(
            "username",
            ""
        ).strip(),

        request.form.get(
            "mobile",
            ""
        ).strip(),

        request.form.get(
            "email",
            ""
        ).strip(),

        request.form.get(
            "password",
            ""
        ),

        role_value
    )

    set_message(
        msg,
        "success"
        if ok
        else "error"
    )

    return embedded_redirect(
        "developer_department",
        view="create"
    )


# =========================================================
# DEVELOPER MEMBER ACTIVATE
# =========================================================

@app.route(
    "/developer/member/activate/<member_id>"
)
def developer_member_activate(
    member_id
):

    if not developer_only():

        return unauthorized()

    ok, msg = (
        DeveloperService.activate_member(
            member_id
        )
    )

    set_message(
        msg,
        "success"
        if ok
        else "error"
    )

    return embedded_redirect(
        "developer_department",
        view="inactive"
    )


# =========================================================
# DEVELOPER MEMBER DEACTIVATE
# =========================================================

@app.route(
    "/developer/member/deactivate/<member_id>"
)
def developer_member_deactivate(
    member_id
):

    if not developer_only():

        return unauthorized()

    ok, msg = (
        DeveloperService.deactivate_member(
            member_id
        )
    )

    set_message(
        msg,
        "success"
        if ok
        else "error"
    )

    return embedded_redirect(
        "developer_department",
        view="members"
    )


# =========================================================
# DEVELOPER MEMBER LOCK
# =========================================================

@app.route(
    "/developer/member/lock/<member_id>"
)
def developer_member_lock(
    member_id
):

    if not developer_only():

        return unauthorized()

    ok, msg = (
        DeveloperService.lock_member(
            member_id
        )
    )

    set_message(
        msg,
        "success"
        if ok
        else "error"
    )

    return embedded_redirect(
        "developer_department",
        view="members"
    )


# =========================================================
# DEVELOPER MEMBER UNLOCK
# =========================================================

@app.route(
    "/developer/member/unlock/<member_id>"
)
def developer_member_unlock(
    member_id
):

    if not developer_only():

        return unauthorized()

    ok, msg = (
        DeveloperService.unlock_member(
            member_id
        )
    )

    set_message(
        msg,
        "success"
        if ok
        else "error"
    )

    return embedded_redirect(
        "developer_department",
        view="members"
    )


# =========================================================
# DEVELOPER MEMBER SUSPEND
# =========================================================

@app.route(
    "/developer/member/suspend/<member_id>"
)
def developer_member_suspend(
    member_id
):

    if not developer_only():

        return unauthorized()

    ok, msg = (
        DeveloperService.suspend_member(
            member_id
        )
    )

    set_message(
        msg,
        "success"
        if ok
        else "error"
    )

    return embedded_redirect(
        "developer_department",
        view="members"
    )


# =========================================================
# DEVELOPER MEMBER DELETE
# =========================================================

@app.route(
    "/developer/member/delete/<member_id>"
)
def developer_member_delete(
    member_id
):

    if not developer_only():

        return unauthorized()

    ok, msg = (
        DeveloperService.delete_account(
            member_id
        )
    )

    set_message(
        msg,
        "success"
        if ok
        else "error"
    )

    return embedded_redirect(
        "developer_department",
        view="members"
    )


# =========================================================
# DEVELOPER MEMBER VIEW
# =========================================================

@app.route(
    "/developer/member/<member_id>"
)
def developer_member(
    member_id
):

    if not developer_only():

        return unauthorized()

    member = DeveloperService.get_member(
        member_id
    )

    if not member:

        return embedded_redirect(
            "developer_department",
            view="members"
        )

    module = request.args.get(
        "module",
        "income"
    )

    uid = str(
        member["_id"]
    )

    rows = []
    summaries = []

    services = {

        "income":
            IncomeService,

        "expense":
            ExpenseService,

        "meal":
            MealService,

        "savings":
            SavingService
    }

    if module in services:

        summaries = (
            services[module]
            .get_month_summaries(uid)
        )

    if module == "income":

        headers = [
            "SL",
            "Month",
            "Income Type",
            "Received Method",
            "Source",
            "Amount",
            "Time",
            "Date",
            "Description"
        ]

        for i, r in enumerate(

            db["incomes"].find(
                {
                    "user_id": uid
                }
            ).sort(
                "_id",
                -1
            ),

            1
        ):

            rows.append([

                i,

                f"{r.get('month', '')} "
                f"{r.get('year', '')}",

                r.get(
                    "income_type",
                    ""
                ),

                r.get(
                    "received_method",
                    ""
                ),

                r.get(
                    "source",
                    ""
                ),

                f"{float(r.get('amount', 0)):.2f}",

                r.get(
                    "time",
                    ""
                ),

                r.get(
                    "date",
                    ""
                ),

                r.get(
                    "description",
                    ""
                )
            ])

    elif module == "expense":

        headers = [
            "SL",
            "Month",
            "Category",
            "Amount",
            "Time",
            "Date",
            "Description"
        ]

        for i, r in enumerate(

            db["expenses"].find(
                {
                    "user_id": uid
                }
            ).sort(
                "_id",
                -1
            ),

            1
        ):

            rows.append([

                i,

                f"{r.get('month', '')} "
                f"{r.get('year', '')}",

                r.get(
                    "category",
                    ""
                ),

                f"{float(r.get('amount', 0)):.2f}",

                r.get(
                    "time",
                    ""
                ),

                r.get(
                    "date",
                    ""
                ),

                r.get(
                    "description",
                    ""
                )
            ])

    elif module == "meal":

        headers = [
            "SL",
            "Name",
            "Mobile",
            "Dinner",
            "Lunch",
            "Breakfast",
            "Extra",
            "Guest",
            "In Dining",
            "Out Dining",
            "Meal Charge",
            "Rice Charge",
            "Time",
            "Date"
        ]

        for i, r in enumerate(

            db["meals"].find(
                {
                    "user_id": uid
                }
            ).sort(
                "_id",
                -1
            ),

            1
        ):

            rows.append([

                i,

                r.get(
                    "name",
                    ""
                ),

                r.get(
                    "mobile",
                    ""
                ),

                r.get(
                    "dinner",
                    0
                ),

                r.get(
                    "lunch",
                    0
                ),

                r.get(
                    "breakfast",
                    0
                ),

                r.get(
                    "extra",
                    0
                ),

                r.get(
                    "guest",
                    0
                ),

                r.get(
                    "in_dining",
                    0
                ),

                r.get(
                    "out_dining",
                    0
                ),

                r.get(
                    "meal_charge",
                    0
                ),

                r.get(
                    "rice_charge",
                    0
                ),

                r.get(
                    "time",
                    ""
                ),

                r.get(
                    "date",
                    ""
                )
            ])

    else:

        headers = [
            "SL",
            "Month",
            "Amount",
            "Time",
            "Date",
            "Description"
        ]

        for i, r in enumerate(

            db["savings"].find(
                {
                    "user_id": uid
                }
            ).sort(
                "_id",
                -1
            ),

            1
        ):

            rows.append([

                i,

                f"{r.get('month', '')} "
                f"{r.get('year', '')}",

                f"{float(r.get('amount', 0)):.2f}",

                r.get(
                    "time",
                    ""
                ),

                r.get(
                    "date",
                    ""
                ),

                r.get(
                    "description",
                    ""
                )
            ])

    return render_template(

        "developer_member.html",

        member=member,

        module=module,

        headers=headers,

        rows=rows,

        summaries=summaries,

        history=member_history(uid)
    )


# =========================================================
# DEVELOPER MEMBER MODULE TOGGLE
# =========================================================

@app.route(
    "/developer/member/<member_id>/toggle/<module>"
)
def developer_member_module_toggle(
    member_id,
    module
):

    if not developer_only():

        return unauthorized()

    member = DeveloperService.get_member(
        member_id
    )

    key = request.args.get(
        "month"
    )

    services = {

        "income":
            IncomeService,

        "expense":
            ExpenseService,

        "meal":
            MealService,

        "savings":
            SavingService
    }

    if (
        member
        and key
        and module in services
    ):

        services[module].toggle_month_lock(
            str(member["_id"]),
            key
        )

    set_message(
        "Month lock status updated."
    )

    return redirect(
        url_for(
            "developer_member",
            member_id=member_id,
            module=module,
            embedded="1"
        )
    )


# =========================================================
# MULTI MEMBER
# =========================================================

@app.route(
    "/developer/multi-members",
    methods=["GET", "POST"]
)
def developer_multi_members():

    if not developer_only():

        return unauthorized()

    members = active_members()

    if request.method == "POST":

        session[
            "developer_selected_member_ids"
        ] = request.form.getlist(
            "member_ids"
        )

        set_message(
            "Member selection updated."
        )

        return embedded_redirect(
            "developer_multi_members"
        )

    selected = session.get(
        "developer_selected_member_ids",
        []
    )

    chosen = [

        m

        for m in members

        if str(
            m.get("_id")
        ) in selected
    ]

    message = consume_message()

    return render_template(

        "developer_multi_member.html",

        members=members,

        selected_members=chosen,

        selected_ids=selected,

        message=(
            message.get("text")
            if message
            else None
        )
    )


# =========================================================
# MULTI MEMBER VIEW
# =========================================================

@app.route(
    "/developer/multi-members/view"
)
def developer_multi_members_view():

    if not developer_only():

        return unauthorized()

    ids = session.get(
        "developer_selected_member_ids",
        []
    )

    module = request.args.get(
        "module",
        "income"
    )

    if not ids:

        set_message(
            "Please select members first.",
            "error"
        )

        return embedded_redirect(
            "developer_multi_members"
        )

    members = [

        m

        for m in (
            DeveloperService.get_member(i)
            for i in ids
        )

        if (
            m
            and m.get("status")
            == "Active"
        )
    ]

    headers = []
    rows = []

    for m in members:

        uid = str(
            m["_id"]
        )

        if module == "income":

            headers = [
                "SL",
                "Name",
                "Month",
                "Income Type",
                "Received Method",
                "Source",
                "Amount",
                "Time",
                "Date",
                "Description"
            ]

            recs = db[
                "incomes"
            ].find(
                {
                    "user_id": uid
                }
            ).sort(
                "_id",
                -1
            )

            for r in recs:

                rows.append([

                    len(rows) + 1,

                    m.get(
                        "name",
                        ""
                    ),

                    f"{r.get('month', '')} "
                    f"{r.get('year', '')}",

                    r.get(
                        "income_type",
                        ""
                    ),

                    r.get(
                        "received_method",
                        ""
                    ),

                    r.get(
                        "source",
                        ""
                    ),

                    r.get(
                        "amount",
                        0
                    ),

                    r.get(
                        "time",
                        ""
                    ),

                    r.get(
                        "date",
                        ""
                    ),

                    r.get(
                        "description",
                        ""
                    )
                ])

        elif module == "expense":

            headers = [
                "SL",
                "Name",
                "Month",
                "Category",
                "Amount",
                "Time",
                "Date",
                "Description"
            ]

            for r in db[
                "expenses"
            ].find(
                {
                    "user_id": uid
                }
            ).sort(
                "_id",
                -1
            ):

                rows.append([

                    len(rows) + 1,

                    m.get(
                        "name",
                        ""
                    ),

                    f"{r.get('month', '')} "
                    f"{r.get('year', '')}",

                    r.get(
                        "category",
                        ""
                    ),

                    r.get(
                        "amount",
                        0
                    ),

                    r.get(
                        "time",
                        ""
                    ),

                    r.get(
                        "date",
                        ""
                    ),

                    r.get(
                        "description",
                        ""
                    )
                ])

        elif module == "meal":

            headers = [
                "SL",
                "Name",
                "Mobile",
                "Dinner",
                "Lunch",
                "Breakfast",
                "Extra",
                "Guest",
                "In Dining",
                "Out Dining",
                "Meal Charge",
                "Rice Charge",
                "Time",
                "Date"
            ]

            for r in db[
                "meals"
            ].find(
                {
                    "user_id": uid
                }
            ).sort(
                "_id",
                -1
            ):

                rows.append([

                    len(rows) + 1,

                    m.get(
                        "name",
                        ""
                    ),

                    m.get(
                        "mobile",
                        ""
                    ),

                    r.get(
                        "dinner",
                        0
                    ),

                    r.get(
                        "lunch",
                        0
                    ),

                    r.get(
                        "breakfast",
                        0
                    ),

                    r.get(
                        "extra",
                        0
                    ),

                    r.get(
                        "guest",
                        0
                    ),

                    r.get(
                        "in_dining",
                        0
                    ),

                    r.get(
                        "out_dining",
                        0
                    ),

                    r.get(
                        "meal_charge",
                        0
                    ),

                    r.get(
                        "rice_charge",
                        0
                    ),

                    r.get(
                        "time",
                        ""
                    ),

                    r.get(
                        "date",
                        ""
                    )
                ])

        else:

            headers = [
                "SL",
                "Name",
                "Month",
                "Amount",
                "Time",
                "Date",
                "Description"
            ]

            for r in db[
                "savings"
            ].find(
                {
                    "user_id": uid
                }
            ).sort(
                "_id",
                -1
            ):

                rows.append([

                    len(rows) + 1,

                    m.get(
                        "name",
                        ""
                    ),

                    f"{r.get('month', '')} "
                    f"{r.get('year', '')}",

                    r.get(
                        "amount",
                        0
                    ),

                    r.get(
                        "time",
                        ""
                    ),

                    r.get(
                        "date",
                        ""
                    ),

                    r.get(
                        "description",
                        ""
                    )
                ])

    return render_template(

        "developer_multi_member_view.html",

        module=module,

        members=members,

        headers=headers,

        rows=rows
    )


# =========================================================
# AUDIT
# =========================================================

@app.route(
    "/developer/audit"
)
def audit():

    if not developer_only():

        return unauthorized()

    activity = request.args.get(
        "activity"
    )

    logs = AuditService.get_logs(
        activity=activity
    )

    message = (
        consume_message()
        or {}
    )

    return render_template(

        "audit.html",

        logs=logs,

        activity=activity,

        message=message.get(
            "text"
        )
    )


# =========================================================
# REQUESTS
# =========================================================

@app.route(
    "/developer/requests"
)
def requests_page():

    if not developer_only():

        return unauthorized()

    message = (
        consume_message()
        or {}
    )

    return render_template(

        "requests.html",

        requests=RequestService.get_all(),

        message=message.get(
            "text"
        )
    )


@app.route(
    "/request",
    methods=["GET", "POST"]
)
def member_request():

    if not logged_in():

        return redirect(
            url_for("login")
        )

    if request.method == "POST":

        RequestService.create(

            current_user(),

            request.form.get(
                "request_type",
                ""
            ),

            request.form.get(
                "details",
                ""
            ).strip()
        )

        set_message(
            "Request submitted successfully."
        )

        return redirect(
            url_for(
                "member_request"
            )
        )

    message = (
        consume_message()
        or {}
    )

    return render_template(

        "member_request.html",

        message=message.get(
            "text"
        )
    )


@app.route(
    "/developer/request/delete/<request_id>"
)
def request_delete(
    request_id
):

    if not developer_only():

        return unauthorized()

    ok = RequestService.delete(
        request_id
    )

    set_message(

        "Request deleted successfully."
        if ok
        else "Request not found.",

        "success"
        if ok
        else "error"
    )

    return redirect(
        url_for(
            "requests_page"
        )
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route(
    "/logout"
)
def logout():

    u = current_user()

    if u:

        AuditService.log(
            u["_id"],
            "Logout",
            "Logout successful",
            u
        )

    session.clear()

    session["page_message"] = {

        "text":
            "Logged out successfully.",

        "type":
            "success"
    }

    return redirect(
        url_for("login")
    )


# =========================================================
# REGISTER MEAL ROUTES
# =========================================================

register_meal_routes(

    app,

    logged_in,

    current_user,

    role,

    manager_only,

    now_values,

    set_message,

    consume_message,

    month_key,

    active_members
)


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )