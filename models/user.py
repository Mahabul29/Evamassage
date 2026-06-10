import secrets
import hashlib
from datetime import datetime
from config import users, db
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
        'user_id':    user_id,
        'username':   username,
        'password':   hash_password(password),
        'full_name':  full_name or username,
        'bio':        '',
        'avatar':     'default',
        'language':   'en',
        'theme':      'light',
        'text_size':  'medium',
        'auto_delete':'never',
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

# ── SEARCH USERS ──
@user_bp.route('/api/users/search')
def search_users_route():
    if 'user_id' not in session:
        return jsonify([])
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    try:
        current_uid = int(session['user_id'])
    except Exception:
        current_uid = session['user_id']
    regex = {'$regex': q, '$options': 'i'}
    results = users.find({
        '$and': [
            {'$or': [{'username': regex}, {'full_name': regex}]},
            {'user_id': {'$ne': current_uid}}
        ]
    }).limit(20)
    out = []
    for u in results:
        if str(u.get('user_id')) == str(current_uid):
            continue
        out.append({
            'user_id':   u['user_id'],
            'username':  u.get('username', ''),
            'full_name': u.get('full_name', u.get('username', '')),
            'avatar':    u.get('avatar', 'default')
        })
    return jsonify(out)

# ── GET PROFILE ──
@user_bp.route('/api/users/profile/<int:user_id>')
def get_profile(user_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user = users.find_one({'user_id': user_id})
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        'user_id':   user['user_id'],
        'username':  user.get('username', ''),
        'full_name': user.get('full_name', user.get('username', '')),
        'bio':       user.get('bio', ''),
        'avatar':    user.get('avatar', 'default')
    })

# ── GET ME ──
@user_bp.route('/api/users/me')
def get_me():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user = users.find_one({'user_id': session['user_id']})
    if not user:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        'user_id':    session['user_id'],
        'username':   session.get('username', ''),
        'full_name':  session.get('full_name', ''),
        'avatar':     user.get('avatar', 'default'),
        'language':   user.get('language', 'en'),
        'theme':      user.get('theme', 'light'),
        'text_size':  user.get('text_size', 'medium'),
        'auto_delete':user.get('auto_delete', 'never')
    })

# ── UPDATE PROFILE ──
@user_bp.route('/api/users/update_profile', methods=['POST'])
def update_profile_route():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    data = request.get_json(silent=True) or request.form
    upd = {}
    full_name  = (data.get('full_name') or '').strip()
    username   = (data.get('username') or '').strip().lower()
    bio        = (data.get('bio') or '').strip()
    avatar     = data.get('avatar', 'default')
    language   = data.get('language', 'en')
    theme      = data.get('theme', 'light')
    text_size  = data.get('text_size', 'medium')
    auto_del   = data.get('auto_delete', 'never')
    if username and len(username) >= 3:
        existing = users.find_one({'username': username})
        if existing and existing['user_id'] != user_id:
            return jsonify({'success': False, 'error': 'Username already taken'})
        upd['username'] = username
        session['username'] = username
    if full_name:
        upd['full_name'] = full_name
        session['full_name'] = full_name
    upd['bio'] = bio
    upd['avatar'] = avatar
    upd['language'] = language
    upd['theme'] = theme
    upd['text_size'] = text_size
    upd['auto_delete'] = auto_del
    users.update_one({'user_id': user_id}, {'$set': upd})
    return jsonify({'success': True, 'message': 'Profile updated!'})

# ── CHANGE PASSWORD ──
@user_bp.route('/api/users/change_password', methods=['POST'])
def change_password_route():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    data = request.get_json(silent=True) or request.form
    cur  = (data.get('current') or data.get('current_password') or '')
    new  = (data.get('new') or data.get('new_password') or '')
    user = users.find_one({'user_id': session['user_id']})
    if not user or user['password'] != hash_password(cur):
        return jsonify({'success': False, 'error': 'Current password incorrect'})
    if len(new) < 4:
        return jsonify({'success': False, 'error': 'Min 4 characters'})
    users.update_one({'user_id': session['user_id']}, {'$set': {'password': hash_password(new)}})
    return jsonify({'success': True, 'message': 'Password changed!'})

# ── DELETE ACCOUNT ──
@user_bp.route('/api/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    uid = session['user_id']
    db['messages'].delete_many({'$or': [{'from_id': uid}, {'to_id': uid}]})
    db['chats'].delete_many({'$or': [{'user1_id': uid}, {'user2_id': uid}]})
    db['channel_members'].delete_many({'user_id': uid})
    db['channel_messages'].delete_many({'from_id': uid})
    db['users'].delete_one({'user_id': uid})
    session.clear()
    return jsonify({'success': True})
        
