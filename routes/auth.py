from flask import Blueprint, request, jsonify, session
from models.user import create_user, authenticate_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/register', methods=['POST'])
def register():
    data = request.json
    user, msg = create_user(
        data.get('username', ''),
        data.get('password', ''),
        data.get('full_name', '')
    )
    if user:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = authenticate_user(data.get('username', ''), data.get('password', ''))
    
    if user:
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['full_name'] = user.get('full_name', user['username'])
        return jsonify({"success": True})
    
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

@auth_bp.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})
