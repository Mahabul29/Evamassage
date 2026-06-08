from flask import Blueprint, request, jsonify, session
from functools import wraps
from config import db  # FIX: use db directly from config

user_bp = Blueprint('user', __name__)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return decorated

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
            'user_id':   u['user_id'],
            'username':  u.get('username', ''),
            'full_name': u.get('full_name', u.get('username', ''))
        })
    return jsonify(result)

@user_bp.route('/api/users/profile/<int:user_id>')
@login_required
def get_profile(user_id):
    user = db['users'].find_one({'user_id': user_id})
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        'user_id':   user['user_id'],
        'username':  user.get('username', ''),
        'full_name': user.get('full_name', user.get('username', '')),
        'bio':       user.get('bio', 'Hi there!')
    })

@user_bp.route('/api/users/me')
@login_required
def get_me():
    return jsonify({
        'user_id':   session['user_id'],
        'username':  session.get('username', ''),
        'full_name': session.get('full_name', '')
    })
    
