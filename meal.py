from flask import (
    render_template,
    request,
    redirect,
    url_for
)

from services.meal_service import MealService


def register_meal_routes(
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
):

    @app.route("/meal", methods=["GET", "POST"])
    def meal():

        # =========================================================
        # LOGIN CHECK
        # =========================================================

        if not logged_in():
            return redirect(
                url_for("login")
            )

        user = current_user()

        if not user:
            return redirect(
                url_for("login")
            )

        uid = str(
            user["_id"]
        )

        current_role = role()

        # =========================================================
        # MESSAGE
        #
        # consume_message() may return:
        #   None
        #   dict
        #   tuple/list
        #
        # This safely handles all cases.
        # =========================================================

        raw_message = consume_message()

        message = None
        message_type = "success"

        if raw_message:

            if isinstance(
                raw_message,
                dict
            ):

                message = raw_message.get(
                    "text"
                )

                message_type = raw_message.get(
                    "type",
                    "success"
                )

            elif isinstance(
                raw_message,
                (tuple, list)
            ):

                if len(raw_message) >= 1:
                    message = raw_message[0]

                if len(raw_message) >= 2:
                    message_type = raw_message[1]

            else:

                message = str(
                    raw_message
                )

        # =========================================================
        # VIEW
        #
        # entry   = Meal Entry
        # monthly = Monthly Meal / All Meal Entries
        # =========================================================

        view = request.args.get(
            "view",
            "entry"
        ).strip().lower()

        if view not in (
            "entry",
            "monthly"
        ):
            view = "entry"

        # =========================================================
        # SELECTED MONTH
        # =========================================================

        selected = month_key(
            request.args.get("month"),
            request.args.get("year")
        )

        selected_member_ids = []

        # =========================================================
        # POST - ADD MEAL
        # =========================================================

        if request.method == "POST":

            # -----------------------------------------------------
            # Determine target members
            # -----------------------------------------------------

            if current_role in (
                "Manager",
                "Expense Developer"
            ):

                selected_member_ids = [
                    str(member_id).strip()
                    for member_id in request.form.getlist(
                        "member_ids"
                    )
                    if str(member_id).strip()
                ]

                # -------------------------------------------------
                # No member selected
                # -------------------------------------------------

                if not selected_member_ids:

                    message = (
                        "Please select at least one member."
                    )

                    message_type = "error"

                else:

                    created_count = 0
                    failed_message = None

                    # ---------------------------------------------
                    # Add meal for selected members
                    # ---------------------------------------------

                    for target_id in selected_member_ids:

                        target_member = None

                        try:

                            members = active_members()

                            target_member = next(
                                (
                                    member
                                    for member in members
                                    if str(
                                        member.get("_id")
                                    ) == target_id
                                ),
                                None
                            )

                        except Exception:

                            target_member = None

                        # -----------------------------------------
                        # Member not found
                        # -----------------------------------------

                        if not target_member:

                            failed_message = (
                                "Selected member was not found."
                            )

                            break

                        target_name = str(
                            target_member.get(
                                "name",
                                ""
                            )
                        ).strip()

                        target_mobile = str(
                            target_member.get(
                                "mobile",
                                ""
                            )
                        ).strip()

                        # -----------------------------------------
                        # Add meal
                        # -----------------------------------------

                        ok, msg = MealService.add_meal(

                            target_id,

                            target_name,

                            target_mobile,

                            request.form.get(
                                "meal_type",
                                ""
                            ).strip(),

                            request.form.get(
                                "date",
                                ""
                            ).strip(),

                            request.form.get(
                                "meal_charge",
                                ""
                            ).strip(),

                            request.form.get(
                                "rice_charge",
                                ""
                            ).strip(),

                            request.form.get(
                                "month",
                                ""
                            ).strip(),

                            request.form.get(
                                "time",
                                ""
                            ).strip(),

                            request.form.get(
                                "note",
                                ""
                            ).strip(),

                            created_by=uid
                        )

                        if not ok:

                            failed_message = msg

                            break

                        created_count += 1

                    # ---------------------------------------------
                    # Failed
                    # ---------------------------------------------

                    if failed_message:

                        message = failed_message
                        message_type = "error"

                    # ---------------------------------------------
                    # Successfully created
                    # ---------------------------------------------

                    elif created_count > 0:

                        set_message(
                            (
                                "Meal record added successfully "
                                f"for {created_count} member(s)."
                            ),
                            "success"
                        )

                        # Preserve embedded mode
                        # and current view.

                        redirect_args = {
                            "view": view
                        }

                        if request.args.get(
                            "embedded"
                        ) == "1":

                            redirect_args[
                                "embedded"
                            ] = "1"

                        return redirect(
                            url_for(
                                "meal",
                                **redirect_args
                            )
                        )

            else:

                # =================================================
                # NORMAL MEMBER
                # =================================================

                target_name = str(
                    user.get(
                        "name",
                        ""
                    )
                ).strip()

                target_mobile = str(
                    user.get(
                        "mobile",
                        ""
                    )
                ).strip()

                # -------------------------------------------------
                # Add meal
                # -------------------------------------------------

                ok, msg = MealService.add_meal(

                    uid,

                    target_name,

                    target_mobile,

                    request.form.get(
                        "meal_type",
                        ""
                    ).strip(),

                    request.form.get(
                        "date",
                        ""
                    ).strip(),

                    request.form.get(
                        "meal_charge",
                        ""
                    ).strip(),

                    request.form.get(
                        "rice_charge",
                        ""
                    ).strip(),

                    request.form.get(
                        "month",
                        ""
                    ).strip(),

                    request.form.get(
                        "time",
                        ""
                    ).strip(),

                    request.form.get(
                        "note",
                        ""
                    ).strip(),

                    created_by=uid
                )

                # -------------------------------------------------
                # Success
                # -------------------------------------------------

                if ok:

                    set_message(
                        "Meal record added successfully.",
                        "success"
                    )

                    redirect_args = {
                        "view": view
                    }

                    if request.args.get(
                        "embedded"
                    ) == "1":

                        redirect_args[
                            "embedded"
                        ] = "1"

                    return redirect(
                        url_for(
                            "meal",
                            **redirect_args
                        )
                    )

                # -------------------------------------------------
                # Error
                # -------------------------------------------------

                message = msg
                message_type = "error"

        # =========================================================
        # MONTH LOCK STATUS
        # =========================================================

        locked = bool(
            selected
            and MealService.is_month_locked(
                uid,
                selected
            )
        )

        # =========================================================
        # ACTIVE MEMBERS
        #
        # Manager / Expense Developer can select members.
        # =========================================================

        selectable_members = []

        if current_role in (
            "Manager",
            "Expense Developer"
        ):

            try:

                selectable_members = (
                    active_members()
                    or []
                )

            except Exception:

                selectable_members = []

        # =========================================================
        # CURRENT USER'S SELECTED MONTH MEALS
        # =========================================================

        month_meals = []

        if selected:

            month_meals = (
                MealService.get_month_meals(
                    uid,
                    selected
                )
            )

        # =========================================================
        # ALL MEALS
        #
        # Monthly Meal view needs all meal records.
        #
        # get_all_meals() should exist in MealService.
        # =========================================================

        all_meals = []

        if view == "monthly":

            try:

                all_meals = (
                    MealService.get_all_meals(
                        uid
                    )
                    or []
                )

            except AttributeError:

                # If get_all_meals() is not yet present,
                # fall back to the currently selected month.

                all_meals = list(
                    month_meals
                )

            except Exception:

                all_meals = []

        # =========================================================
        # CURRENT DATE / TIME
        # =========================================================

        current_date, current_time = (
            now_values()
        )

        # =========================================================
        # MONTH SUMMARIES
        # =========================================================

        summaries = (
            MealService.get_month_summaries(
                uid
            )
        )

        # =========================================================
        # RENDER TEMPLATE
        # =========================================================

        return render_template(

            "meal.html",

            # -----------------------------------------------------
            # Page view
            # -----------------------------------------------------

            view=view,

            # -----------------------------------------------------
            # Month data
            # -----------------------------------------------------

            summaries=summaries,

            selected_month=selected,

            selected_locked=locked,

            month_meals=month_meals,

            all_meals=all_meals,

            # -----------------------------------------------------
            # Date / Time
            # -----------------------------------------------------

            current_date=current_date,

            current_time=current_time,

            # -----------------------------------------------------
            # User
            # -----------------------------------------------------

            current_user=user,

            user=user,

            role=current_role,

            current_role=current_role,

            # -----------------------------------------------------
            # Members
            # -----------------------------------------------------

            selectable_members=selectable_members,

            selected_member_ids=selected_member_ids,

            # -----------------------------------------------------
            # Message
            # -----------------------------------------------------

            message=message,

            message_type=message_type
        )


    # =============================================================
    # DELETE MEAL
    # =============================================================

    @app.route(
        "/meal/delete/<meal_id>"
    )
    def meal_delete(meal_id):

        # ---------------------------------------------------------
        # LOGIN CHECK
        # ---------------------------------------------------------

        if not logged_in():

            return redirect(
                url_for("login")
            )

        user = current_user()

        if not user:

            return redirect(
                url_for("login")
            )

        uid = str(
            user["_id"]
        )

        # ---------------------------------------------------------
        # Delete
        # ---------------------------------------------------------

        ok, msg, old = (
            MealService.delete_meal(
                meal_id,
                uid
            )
        )

        # ---------------------------------------------------------
        # Success
        # ---------------------------------------------------------

        if ok:

            set_message(
                "Record permanently deleted.",
                "success"
            )

        # ---------------------------------------------------------
        # Error
        # ---------------------------------------------------------

        else:

            set_message(
                msg,
                "error"
            )

        # ---------------------------------------------------------
        # Preserve Monthly view
        # ---------------------------------------------------------

        view = request.args.get(
            "view",
            "entry"
        ).strip().lower()

        if view not in (
            "entry",
            "monthly"
        ):

            view = "entry"

        redirect_args = {
            "view": view
        }

        # Keep embedded=1 so the page remains
        # inside the dashboard iframe.

        if request.args.get(
            "embedded"
        ) == "1":

            redirect_args[
                "embedded"
            ] = "1"

        # Keep selected month/year if present.

        month = request.args.get(
            "month"
        )

        year = request.args.get(
            "year"
        )

        if month:

            redirect_args[
                "month"
            ] = month

        if year:

            redirect_args[
                "year"
            ] = year

        return redirect(
            url_for(
                "meal",
                **redirect_args
            )
        )