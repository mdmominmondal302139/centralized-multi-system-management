from datetime import datetime

class User:
    def __init__(self, name, username, mobile, email, password,
                 role="Member", status="Inactive", approved=False,
                 locked=False, suspended=False):
        self.name = name
        self.username = username
        self.mobile = mobile
        self.email = email
        self.password = password
        self.role = role
        self.status = status
        self.approved = approved
        self.locked = locked
        self.suspended = suspended
        self.created_at = datetime.now()

    def to_dict(self):
        return {
            "name": self.name,
            "username": self.username,
            "mobile": self.mobile,
            "email": self.email,
            "password": self.password,
            "role": self.role,
            "status": self.status,
            "approved": self.approved,
            "locked": self.locked,
            "suspended": self.suspended,
            "created_at": self.created_at,
        }
