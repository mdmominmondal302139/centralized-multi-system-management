# Architecture

Every page is isolated in its own folder. Route/controller code is in the page Python file, business/database code is in that page's services.py, and UI is in that page's HTML.

The root web_app.py only loads environment, creates Flask, registers page blueprints, and exposes authentication.
