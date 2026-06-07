from flask import Blueprint, request, jsonify, session
from functools import wraps
from models.user import search_users, get_user, update_profile

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
def search():
    q = request.args.get('q', '')
    return jsonify(search_users(q, session['user_id']))

@user_bp.route('/api/users/profile/<int:user_id>')
@login_required
def profile(user_id):
    user = get_user(user_id)
    if user:
        return jsonify({
            'user_id': user['user_id'],
            'username': user['username'],
            'full_name': user.get('full_name', user['username']),
            'bio': user.get('bio', 'No bio'),
            'joined': user.get('created_at')
        })
    return jsonify({"error": "Not found"}), 404

@user_bp.route('/api/users/update_profile', methods=['POST'])
@login_required
def update():
    data = request.json
    update_profile(
        session['user_id'],
        data.get('full_name'),
        data.get('bio')
    )
    if data.get('full_name'):
        session['full_name'] = data.get('full_name')
    return jsonify({"success": True})
