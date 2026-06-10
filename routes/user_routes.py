from flask import Blueprint, request, jsonify, session
from config import db
import hashlib

user_bp = Blueprint('user_bp', __name__)

users = db['users']


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ── GET current user profile ──
@user_bp.route('/api/user/profile', methods=['GET'])
def get_profile():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    user = users.find_one({'user_id': session['user_id']}, {'_id': 0, 'password': 0})
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    return jsonify({'success': True, 'user': user})


# ── UPDATE profile (full_name, bio, avatar) ──
@user_bp.route('/api/user/profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    data = request.get_json(silent=True) or {}

    allowed = ['full_name', 'bio', 'avatar']
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({'success': False, 'error': 'Nothing to update'})

    users.update_one({'user_id': session['user_id']}, {'$set': updates})

    # Keep session in sync
    if 'full_name' in updates:
        session['full_name'] = updates['full_name']

    return jsonify({'success': True})


# ── UPDATE settings (theme, text_size, language, auto_delete) ──
@user_bp.route('/api/user/settings', methods=['POST'])
def update_settings():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    data = request.get_json(silent=True) or {}

    allowed = ['theme', 'text_size', 'language', 'auto_delete']
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({'success': False, 'error': 'Nothing to update'})

    users.update_one({'user_id': session['user_id']}, {'$set': updates})
    return jsonify({'success': True})


# ── CHANGE password ──
@user_bp.route('/api/user/change-password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    data = request.get_json(silent=True) or {}
    current = data.get('current_password', '').strip()
    new_pw  = data.get('new_password', '').strip()

    if not current or not new_pw:
        return jsonify({'success': False, 'error': 'Missing fields'})
    if len(new_pw) < 4:
        return jsonify({'success': False, 'error': 'Password too short'})

    user = users.find_one({'user_id': session['user_id']})
    if not user or user['password'] != hash_password(current):
        return jsonify({'success': False, 'error': 'Current password incorrect'})

    users.update_one({'user_id': session['user_id']}, {'$set': {'password': hash_password(new_pw)}})
    return jsonify({'success': True})


# ── SEARCH users (for new chat overlay) ──
@user_bp.route('/api/users/search', methods=['GET'])
def search_users():
    if 'user_id' not in session:
        return jsonify([]), 401
    q = request.args.get('q', '').strip().lower()
    if not q or len(q) < 2:
        return jsonify([])

    try:
        current_uid = int(session['user_id'])
    except (TypeError, ValueError):
        current_uid = session['user_id']

    results = users.find(
        {
            '$or': [
                {'username':  {'$regex': q, '$options': 'i'}},
                {'full_name': {'$regex': q, '$options': 'i'}},
            ],
            'user_id': {'$ne': current_uid}
        },
        {'_id': 0, 'password': 0}
    ).limit(20)

    return jsonify([{
        'user_id': u['user_id'],
        'username': u.get('username', ''),
        'full_name': u.get('full_name', ''),
        'bio': u.get('bio', ''),
        'avatar': u.get('avatar', 'default'),
    } for u in results])


# ── GET user by ID (for profile popups) ──
@user_bp.route('/api/users/<int:user_id>', methods=['GET'])
def get_user_by_id(user_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    user = users.find_one({'user_id': user_id}, {'_id': 0, 'password': 0})
    if not user:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    return jsonify({'success': True, 'user': user})

