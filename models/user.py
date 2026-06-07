import secrets
import hashlib
from datetime import datetime
from config import users

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password, full_name):
    if len(username) < 3 or len(password) < 4:
        return None, "Invalid input"
    
    if users.find_one({'username': username}):
        return None, "Username exists"
    
    user_id = secrets.randbelow(1000000000)
    user = {
        'user_id': user_id,
        'username': username.lower(),
        'password': hash_password(password),
        'full_name': full_name or username,
        'bio': '',
        'created_at': datetime.now()
    }
    users.insert_one(user)
    return user, "Success"

def authenticate_user(username, password):
    user = users.find_one({
        'username': username.lower(),
        'password': hash_password(password)
    })
    return user

def get_user(user_id):
    return users.find_one({'user_id': user_id})

def search_users(query, current_user_id):
    if len(query) < 2:
        return []
    
    results = users.find({
        'user_id': {'$ne': current_user_id},
        '$or': [
            {'username': {'$regex': query, '$options': 'i'}},
            {'full_name': {'$regex': query, '$options': 'i'}}
        ]
    }).limit(20)
    
    return [{
        'user_id': u['user_id'],
        'username': u['username'],
        'full_name': u.get('full_name', u['username'])
    } for u in results]

def update_profile(user_id, full_name=None, bio=None):
    update = {}
    if full_name:
        update['full_name'] = full_name
    if bio is not None:
        update['bio'] = bio
    
    if update:
        users.update_one({'user_id': user_id}, {'$set': update})
    return True
