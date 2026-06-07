from functools import wraps
from flask import session, request, jsonify
import hashlib
import secrets
from datetime import datetime, timedelta

class AuthManager:
    def __init__(self, user_db):
        self.user_db = user_db
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256 with salt"""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.sha256((password + salt).encode())
        return f"{salt}:{hash_obj.hexdigest()}"
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        salt, hash_value = hashed.split(':')
        hash_obj = hashlib.sha256((password + salt).encode())
        return hash_obj.hexdigest() == hash_value
    
    def generate_reset_token(self, user_id: int) -> str:
        """Generate password reset token"""
        token = secrets.token_urlsafe(32)
        # Store token in database with expiry
        return token
    
    def is_logged_in(self) -> bool:
        """Check if user is logged in"""
        return 'user_id' in session
    
    def require_login(self):
        """Decorator for requiring login"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not self.is_logged_in():
                    return jsonify({"error": "Please login first"}), 401
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def logout(self):
        """Logout user"""
        session.clear()
