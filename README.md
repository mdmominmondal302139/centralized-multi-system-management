# CENTRALIZED MULTI SYSTEM MANAGEMENT

Converted from nextjs_native_full_system_super_admin_v48.zip into page-isolated Flask architecture.

Each page owns exactly three primary files:
- `<page>/<page>.py`
- `<page>/services.py`
- `<page>/<page>.html`

Shared infrastructure is limited to DATABASE, AUTHENTICATION, STATIC and the root orchestrator.

Run:
```bat
pip install -r requirements.txt
copy .env.example .env
python web_app.py
```
