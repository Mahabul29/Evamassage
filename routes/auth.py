from flask import Blueprint, request, jsonify, session, render_template, redirect
from models.user import create_user, authenticate_user, get_user

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        if 'user_id' in session:
            return redirect('/dashboard')
        return render_template('register.html')

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    full_name = request.form.get('full_name', '').strip()

    if not username or not password:
        return jsonify({'success': False, 'error': 'Missing username or password'})

    user, message = create_user(username, password, full_name)
    if user:
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['full_name'] = user.get('full_name', user['username'])
        return jsonify({'success': True, 'message': 'Registration successful'})
    else:
        return jsonify({'success': False, 'error': message})

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if 'user_id' in session:
            return redirect('/dashboard')
        return render_template('login.html')

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()

    user = authenticate_user(username, password)
    if user:
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['full_name'] = user.get('full_name', user['username'])
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Invalid credentials'})

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/')
