import secrets
import hashlib
from datetime import datetime
from config import users
from flask import Blueprint, request, jsonify, session
from pymongo.errors import DuplicateKeyError

user_bp = Blueprint('user_bp', __name__)

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

# ========== API ROUTES ==========

@user_bp.route('/api/users/search')
def search_users_route():
    if 'user_id' not in session:
        return jsonify([])
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    regex = {'$regex': q, '$options': 'i'}
    results = users.find({
        '$and': [
            {'$or': [{'username': regex}, {'full_name': regex}]},
            {'user_id': {'$ne': session['user_id']}}
        ]
    }).limit(20)
    return jsonify([{
        'user_id': u['user_id'],
        'username': u.get('username', ''),
        'full_name': u.get('full_name', u.get('username', ''))
    } for u in results])

@user_bp.route('/api/users/profile/<int:user_id>')
def get_profile(user_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user = users.find_one({'user_id': user_id})
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        'user_id': user['user_id'],
        'username': user.get('username', ''),
        'full_name': user.get('full_name', user.get('username', '')),
        'bio': user.get('bio', 'Hi there!')
    })

@user_bp.route('/api/users/update_profile', methods=['POST'])
def update_profile_route():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    full_name = request.form.get('full_name', '').strip()
    username = request.form.get('username', '').strip().lower()
    bio = request.form.get('bio', '').strip()
    avatar = request.form.get('avatar', 'default')
    language = request.form.get('language', 'en')
    theme = request.form.get('theme', 'light')
    text_size = request.form.get('text_size', 'medium')
    auto_delete = request.form.get('auto_delete', 'never')

    if not username or len(username) < 3:
        return jsonify({'success': False, 'error': 'Username must be at least 3 characters.'})

    existing_user = users.find_one({'username': username})
    if existing_user and existing_user['user_id'] != user_id:
        return jsonify({'success': False, 'error': 'Username is already taken.'})

    users.update_one(
        {'user_id': user_id},
        {'$set': {
            'full_name': full_name,
            'username': username,
            'bio': bio,
            'avatar': avatar,
            'language': language,
            'theme': theme,
            'text_size': text_size,
            'auto_delete': auto_delete
        }}
    )
    session['username'] = username
    session['full_name'] = full_name
    return jsonify({'success': True, 'message': 'Profile updated successfully!'})

@user_bp.route('/api/users/change_password', methods=['POST'])
def change_password_route():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')

    user = users.find_one({'user_id': user_id})
    if not user or user['password'] != hash_password(current_password):
        return jsonify({'success': False, 'error': 'Current password matching failed.'})

    if len(new_password) < 4:
        return jsonify({'success': False, 'error': 'New password must be at least 4 characters long.'})

    users.update_one({'user_id': user_id}, {'$set': {'password': hash_password(new_password)}})
    return jsonify({'success': True, 'message': 'Password updated successfully!'})

@user_bp.route('/api/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    from config import messages, chats, channel_members, channel_messages
    messages.delete_many({'$or': [{'from_id': user_id}, {'to_id': user_id}]})
    chats.delete_many({'$or': [{'user1_id': user_id}, {'user2_id': user_id}]})
    channel_members.delete_many({'user_id': user_id})
    channel_messages.delete_many({'from_id': user_id})
    users.delete_one({'user_id': user_id})
    session.clear()
    return jsonify({'success': True, 'message': 'Account deleted permanently'})

@user_bp.route('/api/create_test_users', methods=['GET', 'POST'])
def create_test_users_route():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    test_users = [
        {'username': 'alice', 'password': '1234', 'full_name': 'Alice'},
        {'username': 'bob', 'password': '1234', 'full_name': 'Bob'},
        {'username': 'charlie', 'password': '1234', 'full_name': 'Charlie'},
        {'username': 'diana', 'password': '1234', 'full_name': 'Diana'},
        {'username': 'eve', 'password': '1234', 'full_name': 'Eve'},
    ]

    created = []
    for tu in test_users:
        existing = users.find_one({'username': tu['username']})
        if not existing:
            user, msg = create_user(tu['username'], tu['password'], tu['full_name'])
            if user:
                created.append(tu['username'])

    return jsonify({
        "success": True,
        "message": f"Created {len(created)} test users: {', '.join(created)}" if created else "Test users already exist",
        "created": created
    })
