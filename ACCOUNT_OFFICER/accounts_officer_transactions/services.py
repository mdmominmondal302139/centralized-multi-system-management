"""ACCOUNTS OFFICER scoped service: accounts_transactions_service."""
from datetime import datetime, timezone
ROLE='ACCOUNT_OFFICER'
ROLE_TITLE='ACCOUNTS OFFICER'
ROLE_SCOPE='ASSIGNED FINANCIAL SECTION'

def _authorized(context):
    if not isinstance(context, dict) or context.get("role") != ROLE: return False
    if ROLE == "SYSTEM_SUPER_ADMINISTRATOR": return True
    if ROLE in {"CENTRAL_SYSTEM_ADMINISTRATOR", "CENTRAL_ADMINISTRATION_DIRECTOR", "CENTRAL_SYSTEM_DIRECTOR"}:
        return bool(context.get("branch_id") or context.get("central_id"))
    if ROLE in {"MEMBER", "BRANCH_MEMBER"}: return bool(context.get("user_id"))
    return bool(context.get("section_id") or context.get("branch_id"))

def authorized(context):
    return _authorized(context)

def status(context, payload=None):
    if not _authorized(context): raise PermissionError("Access denied: role or assigned scope is invalid")
    return {"ok":True,"role":ROLE,"scope":ROLE_SCOPE,"module":'accounts_transactions_service',"payload":payload or {},"timestamp":datetime.now(timezone.utc).isoformat()}

def list_records(context, records=None):
    result=status(context); result["records"]=list(records or []); result["count"]=len(result["records"]); return result

def save_record(context, record):
    status(context)
    if not isinstance(record,dict): raise ValueError("record must be a dictionary")
    item=dict(record); item["updated_at"]=datetime.now(timezone.utc).isoformat(); return {"ok":True,"record":item}
