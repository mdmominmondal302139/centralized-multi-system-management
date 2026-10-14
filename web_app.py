import os
import importlib.util
import sys
from pathlib import Path

from flask import Flask, session, redirect
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")

app = Flask(
    __name__,
    static_folder="STATIC",
    static_url_path="/static",
    template_folder=str(BASE),
)

app.secret_key = os.getenv("SECRET_KEY", "change-this-secret")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
if os.getenv("FLASK_ENV", "").lower() == "production":
    app.config["SESSION_COOKIE_SECURE"] = True


# ------------------------------------------------------
# Existing MongoDB connection
# Uses config/member_database.py already present in project.
# No new project file or folder is required.
# ------------------------------------------------------
def initialize_database_connection():
    """Initialize and verify the project's existing MongoDB connection."""
    mongo_uri = (os.getenv("MONGODB_URI") or "").strip()

    if not mongo_uri:
        print("[WARN] MongoDB connection skipped: MONGODB_URI is not set in .env")
        return None

    try:
        from config.member_database import get_database

        client, database = get_database()
        client.admin.command("ping")
        app.extensions["mongo_client"] = client
        app.extensions["mongo_db"] = database
        print(f"[OK] MongoDB connected: {database.name}")
        return database
    except Exception as exc:
        print(f"[ERROR] MongoDB connection failed: {exc}")
        return None


# Establish the connection before importing route modules.
initialize_database_connection()


def import_module_from_file(route_file: Path, module_name: str):
    """Load a page module from its file path."""
    spec = importlib.util.spec_from_file_location(
        module_name,
        route_file,
    )

    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module: {route_file}")

    module = importlib.util.module_from_spec(spec)

    # Make the module available during execution.
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise

    return module


def register_blueprint_once(module, route_file: Path):
    """Register a module's Blueprint only once."""
    if not hasattr(module, "bp"):
        print(f"[INFO] No Blueprint found in: {route_file}")
        return

    bp = module.bp

    if bp.name not in app.blueprints:
        app.register_blueprint(bp)
        print(
            f"[OK] Blueprint registered: "
            f"{bp.name} <- {route_file}"
        )
    else:
        print(
            f"[INFO] Blueprint already registered: "
            f"{bp.name} ({route_file})"
        )


def load_blueprints():
    # --------------------------------------------------
    # 1. Authentication routes
    # --------------------------------------------------
    authentication_files = (
        "AUTHENTICATION/login/login.py",
        "AUTHENTICATION/logout/logout.py",
    )

    for rel in authentication_files:
        route_file = BASE / rel

        if not route_file.is_file():
            print(f"[WARN] Authentication route not found: {route_file}")
            continue

        try:
            module = import_module_from_file(
                route_file,
                f"authentication_{route_file.parent.name}_{route_file.stem}",
            )
            register_blueprint_once(module, route_file)

        except Exception as exc:
            print(f"[ERROR] Could not load {route_file}: {exc}")

    # --------------------------------------------------
    # 2. Role page routes
    # --------------------------------------------------
    excluded_dirs = {
        "DATABASE",
        "AUTHENTICATION",
        "STATIC",
        "DOCUMENTATION",
    }

    role_dirs = sorted(
        (
            p for p in BASE.iterdir()
            if p.is_dir()
            and p.name.isupper()
            and p.name not in excluded_dirs
        ),
        key=lambda p: p.name.lower(),
    )

    for role_dir in role_dirs:
        page_dirs = sorted(
            (p for p in role_dir.iterdir() if p.is_dir()),
            key=lambda p: p.name.lower(),
        )

        for page_dir in page_dirs:
            # Default convention:
            # ROLE/page_name/page_name.py
            route_file = page_dir / f"{page_dir.name}.py"

            # Home pages whose Python file is named home.py.
            # Example:
            # MEMBER/member_home/home.py
            # BRANCH_OFFICER/branch_officer_home/home.py
            home_route_files = {
                ("MEMBER", "member_home"),
                ("BRANCH_OFFICER", "branch_officer_home"),
                ("MEAL_MANAGER", "meal_manager_home"),
            }

            if (
                (role_dir.name, page_dir.name) in home_route_files
                and not route_file.is_file()
                and (page_dir / "home.py").is_file()
            ):
                route_file = page_dir / "home.py"

            # Load the selected route module.
            if route_file.is_file():
                module_name = (
                    f"page_{role_dir.name}_{page_dir.name}"
                )

                try:
                    module = import_module_from_file(
                        route_file,
                        module_name,
                    )
                    register_blueprint_once(module, route_file)

                except Exception as exc:
                    print(
                        f"[ERROR] Could not load "
                        f"{route_file}: {exc}"
                    )

            elif page_dir.name not in {
                "member_home",
                "branch_officer_home",
                "meal_manager_home",
            }:
                print(
                    f"[INFO] No page route file found for: "
                    f"{page_dir}"
                )

            # --------------------------------------------------
            # Nested Daily Bazar List
            # --------------------------------------------------
            nested_bazar_route = (
                page_dir / "bazar_list" / "bazar_list.py"
            )

            if nested_bazar_route.is_file():
                try:
                    nested_module = import_module_from_file(
                        nested_bazar_route,
                        (
                            f"page_{role_dir.name}_"
                            f"{page_dir.name}_bazar_list"
                        ),
                    )

                    register_blueprint_once(
                        nested_module,
                        nested_bazar_route,
                    )

                except Exception as exc:
                    print(
                        f"[ERROR] Could not load "
                        f"{nested_bazar_route}: {exc}"
                    )


    # --------------------------------------------------
    # 3. Existing lowercase modules supplied in download.zip
    # These use their own existing HTML and services files.
    # --------------------------------------------------
    member_module_files = (
        "home/home.py",
        "profile/profile.py",
        "income/income.py",
        "expense/expense.py",
        "meal/meal.py",
        "meal_management/meal_management.py",
        "savings/savings.py",
        "records/records.py",
        "work/work.py",
    )

    for rel in member_module_files:
        route_file = BASE / rel
        if not route_file.is_file():
            print(f"[WARN] Member module not found: {route_file}")
            continue
        try:
            module = import_module_from_file(
                route_file,
                f"existing_member_{route_file.parent.name}_{route_file.stem}",
            )
            register_blueprint_once(module, route_file)
        except Exception as exc:
            print(f"[ERROR] Could not load member module {route_file}: {exc}")


# Explicit Member Meal Management route (keeps all existing role blueprints intact).
_member_meal_route = BASE / "MEMBER" / "meal" / "meal_management.py"
if _member_meal_route.is_file():
    try:
        _member_meal_module = import_module_from_file(
            _member_meal_route, "page_MEMBER_meal_management"
        )
        register_blueprint_once(_member_meal_module, _member_meal_route)
    except Exception as exc:
        print(f"[ERROR] Could not load Member Meal Management {_member_meal_route}: {exc}")

# Register the new authentication features using package imports so relative imports work.
def register_authentication_features():
    # Authentication feature files are optional in partial project archives.
    feature_imports = (
        ("AUTHENTICATION.forgot_password.forgot_password", "forgot_password_bp"),
        ("AUTHENTICATION.google_login.google_login", "google_login_bp"),
        ("AUTHENTICATION.mobile_login.mobile_login", "mobile_login_bp"),
    )
    for module_path, attribute in feature_imports:
        try:
            module = __import__(module_path, fromlist=[attribute])
            blueprint = getattr(module, attribute)
            if blueprint.name not in app.blueprints:
                app.register_blueprint(blueprint)
                print(f"[OK] Authentication feature registered: {blueprint.name}")
        except Exception as exc:
            print(f"[WARN] Authentication feature not loaded ({module_path}): {exc}")

# Load all routes before starting the server.
load_blueprints()
register_authentication_features()


# ------------------------------------------------------
# Member navigation aliases
# The existing HTML sidebar may point to the trailing slash or
# to New/List submenu URLs. Keep these routes inside this app file.
# ------------------------------------------------------
@app.route("/member/")
def member_root():
    if session.get("authenticated") and session.get("role") == "MEMBER":
        return redirect("/member/home")
    return redirect("/login")


@app.route("/member/<section>/<view>")
def member_section_alias(section, view):
    aliases = {
        "income": {"new", "list"},
        "expense": {"new", "list"},
        "meal": {"new", "list"},
        "savings": {"new", "list"},
    }
    if section in aliases and view in aliases[section]:
        if session.get("authenticated") and session.get("role") == "MEMBER":
            return redirect(f"/member/{section}")
        return redirect("/login")
    return "Not Found", 404


# ------------------------------------------------------
# Root route
# ------------------------------------------------------
@app.route("/")
def root():
    if session.get("authenticated"):
        destinations = {
            "SYSTEM_SUPER_ADMINISTRATOR":
                "/system_super_administrator",

            "BRANCH_OFFICER":
                "/branch_officer/home",

            "MEAL_MANAGER":
                "/meal_manager/home",

            "MEMBER":
                "/member/home",
        }

        role = session.get("role")
        return redirect(destinations.get(role, "/login"))

    return redirect("/login")


# ------------------------------------------------------
# Debug route list
# ------------------------------------------------------
@app.route("/__routes")
def show_routes():
    """Display registered routes for development debugging."""
    if not app.debug:
        return "Not Found", 404

    lines = []

    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        methods = ",".join(
            sorted(m for m in rule.methods if m not in {"HEAD", "OPTIONS"})
        )
        lines.append(f"{rule.rule}  [{methods}]")

    return "<pre>" + "\n".join(lines) + "</pre>"


# ------------------------------------------------------
# Start server
# ------------------------------------------------------
if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5000")),
        debug=True,
    )
