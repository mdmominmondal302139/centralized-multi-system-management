from functools import wraps
from flask import session, redirect, url_for, jsonify

def context():
    return {
        "authenticated": session.get("authenticated") is True,
        "role": session.get("role"),
        "user_id": session.get("user_id"),
        "username": session.get("username"),
        "branch_id": session.get("branch_id"),
        "branch_name": session.get("branch_name"),
    }

def role_guard(role):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if session.get("authenticated") is not True or session.get("role") != role:
                return redirect(url_for("login"))
            return fn(*args, **kwargs)
        return wrapped
    return decorator
