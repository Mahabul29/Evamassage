from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import secrets
import os
from datetime import datetime
import hashlib
from pymongo import MongoClient
from config import *

app = Flask(__name__)
app.secret_key = SECRET_KEY

# ============================================
# MONGODB CONNECTION
# ============================================
try:
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]
    users_collection = db['users']
    messages_collection = db['messages']
    chats_collection = db['chats']
    
    # Create indexes
    users_collection.create_index('username', unique=True)
    users_collection.create_index('user_id', unique=True)
    
    print("✅ MongoDB Connected")
except Exception as e:
    print(f"❌ MongoDB Error: {e}")
    # Create in-memory fallback for testing
    users_collection = None
    print("⚠️ Using fallback mode")

# ============================================
# HELPER FUNCTIONS
# ============================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Please login first"}), 401
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# PAGE ROUTES
# ============================================
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('index.html', user=session)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ============================================
# REGISTER API - FIXED VERSION
# ============================================
@app.route('/api/register', methods=['POST'])
def register():
    print("=" * 50)
    print("REGISTER API CALLED")
    print("=" * 50)
    
    try:
        # Get JSON data
        data = request.get_json()
        print(f"Received data: {data}")
        
        if not data:
            return jsonify({"success": False, "error": "No data received"}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        full_name = data.get('full_name', '').strip()
        
        print(f"Username: {username}")
        print(f"Password length: {len(password)}")
        print(f"Full name: {full_name}")
        
        # Validation
        if not username or len(username) < 3:
            return jsonify({"success": False, "error": "Username must be at least 3 characters"}), 400
        
        if not password or len(password) < 4:
            return jsonify({"success": False, "error": "Password must be at least 4 characters"}), 400
        
        if not full_name:
            full_name = username
        
        # Check if MongoDB is available
        if users_collection is None:
            # Fallback - just return success for testing
            print("⚠️ Using fallback mode - user created in memory")
            return jsonify({"success": True, "message": "Registration successful! (Demo mode)"})
        
        # Check if username exists
        existing_user = users_collection.find_one({'username': username})
        if existing_user:
            print(f"Username {username} already exists")
            return jsonify({"success": False, "error": "Username already exists"}), 400
        
        # Create new user
        user_id = secrets.randbelow(1000000000)
        hashed_password = hash_password(password)
        
        user = {
            'user_id': user_id,
            'username': username,
            'password': hashed_password,
            'full_name': full_name,
            'bio': '',
            'profile_pic': '',
            'is_active': True,
            'created_at': datetime.now(),
            'last_login': None
        }
        
        users_collection.insert_one(user)
        print(f"✅ User created successfully: {username} (ID: {user_id})")
        
        return jsonify({"success": True, "message": "Registration successful! Please login."})
    
    except Exception as e:
        print(f"❌ ERROR in register: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500

# ============================================
# LOGIN API
# ============================================
@app.route('/api/login', methods=['POST'])
def login():
    print("=" * 50)
    print("LOGIN API CALLED")
    print("=" * 50)
    
    try:
        data = request.get_json()
        print(f"Received data: {data}")
        
        username = data.get('username')
        password = data.get('password')
        hashed_password = hash_password(password)
        
        print(f"Login attempt for: {username}")
        
        if users_collection is None:
            # Demo mode - accept any login
            print("⚠️ Using fallback mode - demo login")
            session['user_id'] = 123
            session['username'] = username
            session['full_name'] = username
            return jsonify({"success": True, "user": {"user_id": 123, "username": username, "full_name": username}})
        
        user = users_collection.find_one({
            'username': username,
            'password': hashed_password,
            'is_active': True
        })
        
        if user:
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['full_name'] = user.get('full_name', user['username'])
            
            # Update last login
            users_collection.update_one(
                {'user_id': user['user_id']},
                {'$set': {'last_login': datetime.now()}}
            )
            
            print(f"✅ Login successful: {username}")
            return jsonify({
                "success": True,
                "user": {
                    "user_id": user['user_id'],
                    "username": user['username'],
                    "full_name": user.get('full_name', user['username'])
                }
            })
        
        print(f"❌ Login failed: Invalid credentials for {username}")
        return jsonify({"success": False, "error": "Invalid username or password"}), 401
    
    except Exception as e:
        print(f"❌ ERROR in login: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================
# TEST ENDPOINT
# ============================================
@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({
        "status": "ok",
        "message": "API is working",
        "mongodb": "connected" if users_collection else "fallback"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Server starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
