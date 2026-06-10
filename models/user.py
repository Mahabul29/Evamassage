import secrets
import hashlib
from datetime import datetime
from config import users
from pymongo.errors import DuplicateKeyError


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(username, password, full_name):
    if len(username) < 3 or len(password) < 4:
        return None, "Invalid input"

    username = username.lower()

    if users.find_one({'username': username}):
        return None, "Username exists"

    user_id = secrets.randbelow(1000000000)
    user = {
        'user_id': user_id,
        'username': username,
        'password': hash_password(password),
        'full_name': full_name or username,
        'bio': '',
        'avatar': 'default',
        'language': 'en',
        'theme': 'light',
        'text_size': 'medium',
        'auto_delete': 'never',
        'created_at': datetime.now()
    }
    try:
        users.insert_one(user)
    except DuplicateKeyError:
        return None, "Username exists"

    return user, "Success"


def authenticate_user(username, password):
    return users.find_one({
        'username': username.lower(),
        'password': hash_password(password)
    })


def get_user(user_id):
    return users.find_one({'user_id': user_id})
    
