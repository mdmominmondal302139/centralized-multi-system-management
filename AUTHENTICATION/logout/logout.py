from flask import Blueprint,session,redirect

bp=Blueprint("logout_page",__name__)

def _logout():
    session.clear()
    return redirect("/login")

@bp.route("/logout")
def logout():
    return _logout()

@bp.route("/member/logout")
def member_logout():
    return _logout()
