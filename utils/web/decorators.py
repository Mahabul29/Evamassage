from functools import wraps
from flask import session, request, jsonify
from database import banned_users, maintenance

def login_required(f):
    """Decorator to require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin', False):
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

def not_banned(f):
    """Decorator to check if user is banned"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' in session and banned_users.is_banned(session['user_id']):
            return jsonify({"error": "You have been banned"}), 403
        return f(*args, **kwargs)
    return decorated_function

def maintenance_check(f):
    """Decorator to check maintenance mode"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if maintenance.is_maintenance() and not session.get('is_admin', False):
            return jsonify({"error": "Under maintenance"}), 503
        return f(*args, **kwargs)
    return decorated_function

def rate_limit(limit=100, window=60):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Implement rate limiting logic here
            return f(*args, **kwargs)
        return decorated_function
    return decorator
