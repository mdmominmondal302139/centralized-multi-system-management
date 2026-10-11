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
                ("ACCOUNT_OFFICER", "account_officer_home"),
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
                "account_officer_home",
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


# Load all routes before starting the server.
load_blueprints()


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

            "ACCOUNT_OFFICER":
                "/account_officer/home",

            "MEAL_MANAGER":
                "/meal_manager/home",

            "OPERATOR":
                "/operator/dashboard",

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
