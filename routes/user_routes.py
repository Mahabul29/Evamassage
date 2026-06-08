from flask import Blueprint, request, jsonify, session
from functools import wraps
from config import db
from datetime import datetime, timedelta
import hashlib

user_bp = Blueprint('user', __name__)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return decorated

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@user_bp.route('/api/users/search')
@login_required
def search_users():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    regex = {'$regex': q, '$options': 'i'}
    users = db['users'].find({
        '$and': [
            {'$or': [{'username': regex}, {'full_name': regex}]},
            {'user_id': {'$ne': session['user_id']}}
        ]
    }).limit(20)
    result = []
    for u in users:
        result.append({
            'user_id': u['user_id'],
            'username': u.get('username', ''),
            'full_name': u.get('full_name', u.get('username', '')),
            'avatar': u.get('avatar', 'default')
        })
    return jsonify(result)

@user_bp.route('/api/users/profile/<int:user_id>')
@login_required
def get_profile(user_id):
    user = db['users'].find_one({'user_id': user_id})
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        'user_id': user['user_id'],
        'username': user.get('username', ''),
        'full_name': user.get('full_name', user.get('username', '')),
        'bio': user.get('bio', 'Hi there!'),
        'avatar': user.get('avatar', 'default'),
        'language': user.get('language', 'en'),
        'theme': user.get('theme', 'light'),
        'text_size': user.get('text_size', 'medium'),
        'auto_delete': user.get('auto_delete', 'never'),
        'created_at': str(user.get('created_at', ''))
    })

@user_bp.route('/api/users/me')
@login_required
def get_me():
    user = db['users'].find_one({'user_id': session['user_id']})
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        'user_id': session['user_id'],
        'username': session.get('username', ''),
        'full_name': session.get('full_name', ''),
        'avatar': user.get('avatar', 'default'),
        'language': user.get('language', 'en'),
        'theme': user.get('theme', 'light'),
        'text_size': user.get('text_size', 'medium'),
        'auto_delete': user.get('auto_delete', 'never')
    })

# ========== UPDATE PROFILE ==========
@user_bp.route('/api/users/update_profile', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json() or request.form
    user_id = session['user_id']

    update = {}

    # Update full name
    if 'full_name' in data and data['full_name']:
        update['full_name'] = data['full_name'].strip()
        session['full_name'] = update['full_name']

    # Update username
    if 'username' in data and data['username']:
        new_username = data['username'].strip().lower()
        if len(new_username) < 3:
            return jsonify({"error": "Username must be at least 3 characters"}), 400
        # Check if username is taken by another user
        existing = db['users'].find_one({
            'username': new_username,
            'user_id': {'$ne': user_id}
        })
        if existing:
            return jsonify({"error": "Username already taken"}), 400
        update['username'] = new_username
        session['username'] = new_username

    # Update bio
    if 'bio' in data:
        update['bio'] = data['bio'].strip()

    # Update avatar
    if 'avatar' in data and data['avatar']:
        avatar = data['avatar']
        valid_avatars = ['default', 'avatar1', 'avatar2', 'avatar3', 'avatar4', 'avatar5']
        if avatar in valid_avatars:
            update['avatar'] = avatar

    # Update language
    if 'language' in data and data['language']:
        valid_langs = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko', 'ar', 'hi', 'bn']
        if data['language'] in valid_langs:
            update['language'] = data['language']

    # Update theme
    if 'theme' in data and data['theme'] in ['light', 'dark']:
        update['theme'] = data['theme']

    # Update text size
    if 'text_size' in data and data['text_size'] in ['small', 'medium', 'large']:
        update['text_size'] = data['text_size']

    # Update auto delete
    if 'auto_delete' in data and data['auto_delete'] in ['never', '1day', '2days', '3days']:
        update['auto_delete'] = data['auto_delete']

    if update:
        db['users'].update_one({'user_id': user_id}, {'$set': update})

    return jsonify({"success": True, "message": "Profile updated successfully"})

# ========== CHANGE PASSWORD ==========
@user_bp.route('/api/change_password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json() or {}
    current = data.get('current', '')
    new_pass = data.get('new', '')

    if not current or not new_pass:
        return jsonify({"error": "Current and new password required"}), 400

    if len(new_pass) < 4:
        return jsonify({"error": "New password must be at least 4 characters"}), 400

    user = db['users'].find_one({'user_id': session['user_id']})
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user['password'] != hash_password(current):
        return jsonify({"error": "Current password is incorrect"}), 400

    db['users'].update_one(
        {'user_id': session['user_id']},
        {'$set': {'password': hash_password(new_pass)}}
    )

    return jsonify({"success": True, "message": "Password changed successfully"})

# ========== DELETE ACCOUNT ==========
@user_bp.route('/api/delete_account', methods=['POST'])
@login_required
def delete_account():
    user_id = session['user_id']

    # Delete user's messages
    db['messages'].delete_many({'$or': [{'from_id': user_id}, {'to_id': user_id}]})

    # Delete user's chats
    db['chats'].delete_many({'$or': [{'user1_id': user_id}, {'user2_id': user_id}]})

    # Delete user from channel memberships
    db['channel_members'].delete_many({'user_id': user_id})

    # Delete user's channel messages
    db['channel_messages'].delete_many({'from_id': user_id})

    # Delete user
    db['users'].delete_one({'user_id': user_id})

    session.clear()

    return jsonify({"success": True, "message": "Account deleted permanently"})

# ========== AUTO DELETE MESSAGES ==========
@user_bp.route('/api/auto_delete_cleanup', methods=['POST'])
def auto_delete_cleanup():
    """Run this periodically (e.g., via cron) to delete old messages"""
    now = datetime.now()

    # Find users with auto-delete enabled
    for setting in ['1day', '2days', '3days']:
        days = int(setting.replace('day', '').replace('days', ''))
        cutoff = now - timedelta(days=days)

        users_with_setting = db['users'].find({'auto_delete': setting})
        for user in users_with_setting:
            user_id = user['user_id']
            # Delete old private messages
            db['messages'].delete_many({
                '$or': [{'from_id': user_id}, {'to_id': user_id}],
                'created_at': {'$lt': cutoff}
            })

    return jsonify({"success": True, "message": "Cleanup completed"})

# ========== CREATE TEST USERS ==========
@user_bp.route('/api/create_test_users', methods=['GET', 'POST'])
@login_required
def create_test_users():
    test_users = [
        {'username': 'alice', 'password': '1234', 'full_name': 'Alice'},
        {'username': 'bob', 'password': '1234', 'full_name': 'Bob'},
        {'username': 'charlie', 'password': '1234', 'full_name': 'Charlie'},
        {'username': 'diana', 'password': '1234', 'full_name': 'Diana'},
        {'username': 'eve', 'password': '1234', 'full_name': 'Eve'},
    ]

    created = []
    for tu in test_users:
        existing = db['users'].find_one({'username': tu['username']})
        if not existing:
            from models.user import create_user
            user, msg = create_user(tu['username'], tu['password'], tu['full_name'])
            if user:
                created.append(tu['username'])

    return jsonify({
        "success": True,
        "message": f"Created {len(created)} test users: {', '.join(created)}" if created else "Test users already exist",
        "created": created
    })
