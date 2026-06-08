from flask import Blueprint, request, jsonify, session
from config import users
import hashlib

user_bp = Blueprint('user_bp', __name__)

def hash_password(password):
    """Encrypt password configurations uniformly across files."""
    return hashlib.sha256(password.encode()).hexdigest()

@user_bp.route('/api/users/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized account clearance.'}), 401
    
    user_id = session['user_id']
    full_name = request.form.get('full_name', '').strip()
    username = request.form.get('username', '').strip().lower()
    bio = request.form.get('bio', '').strip()
    avatar = request.form.get('avatar', 'avatar1')
    
    if not username or len(username) < 3:
        return jsonify({'success': False, 'error': 'Username string must contain at least 3 elements.'})
    
    # Check if target username matches someone else's document record
    existing_user = users.find_one({'username': username})
    if existing_user and existing_user['user_id'] != user_id:
        return jsonify({'success': False, 'error': 'Selected username matches an active container record.'})
    
    # Save target attributes inside your database collection
    users.update_one(
        {'user_id': user_id},
        {'$set': {
            'full_name': full_name,
            'username': username,
            'bio': bio,
            'avatar': avatar
        }}
    )
    
    # Keep flask local session cookies in sync
    session['username'] = username
    session['full_name'] = full_name
    session['avatar'] = avatar
    
    return jsonify({'success': True, 'message': 'Profile settings updated successfully!'})


@user_bp.route('/api/users/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized account clearance.'}), 401
        
    user_id = session['user_id']
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    
    user = users.find_one({'user_id': user_id})
    if not user or user['password'] != hash_password(current_password):
        return jsonify({'success': False, 'error': 'Current password matching verified invalid.'})
        
    if not new_password or len(new_password) < 4:
        return jsonify({'success': False, 'error': 'Target password string must have at least 4 characters.'})
        
    users.update_one({'user_id': user_id}, {'$set': {'password': hash_password(new_password)}})
    return jsonify({'success': True, 'message': 'Password modified successfully!'})
    
