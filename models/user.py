from flask import Blueprint, request, jsonify, session
from config import users
import hashlib

user_bp = Blueprint('user_bp', __name__)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@user_bp.route('/api/users/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    full_name = request.form.get('full_name', '').strip()
    username = request.form.get('username', '').strip().lower()
    bio = request.form.get('bio', '').strip()
    avatar = request.form.get('avatar', 'avatar1')
    
    if not username or len(username) < 3:
        return jsonify({'success': False, 'error': 'Username must be at least 3 characters.'})
    
    # Verify username uniqueness
    existing_user = users.find_one({'username': username})
    if existing_user and existing_user['user_id'] != user_id:
        return jsonify({'success': False, 'error': 'Username is already taken.'})
    
    # Update Database Record
    users.update_one(
        {'user_id': user_id},
        {'$set': {
            'full_name': full_name,
            'username': username,
            'bio': bio,
            'avatar': avatar
        }}
    )
    
    # Update current session states
    session['username'] = username
    session['full_name'] = full_name
    session['avatar'] = avatar
    
    return jsonify({'success': True, 'message': 'Profile updated successfully!'})


@user_bp.route('/api/users/change_password', methods=['POST'])
def change_password():
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
    
