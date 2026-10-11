"""Register the Daily Bazar List blueprint without editing existing page files.

Call register_bazar_list(app) once from the application's existing Flask setup,
after the Flask app object has been created.
"""
from .daily_bazar_list import bp as daily_bazar_list_bp

def register_bazar_list(app):
    if daily_bazar_list_bp.name not in app.blueprints:
        app.register_blueprint(daily_bazar_list_bp)
