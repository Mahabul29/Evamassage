from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import secrets
import os
from datetime import datetime
import hashlib
from pymongo import MongoClient
from bson.objectid import ObjectId
from config import *

# ============================================
# INITIALIZE FLASK APP
# ============================================
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

# ============================================
# MONGODB CONNECTION
# ============================================
try:
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]
    
    # Test connection
    client.admin.command('ping')
    print(f"✅ MongoDB Connected successfully to {MONGO_DB_NAME}")
    
    # Create collections if they don't exist
    users_collection = db['users']
    messages_collection = db['messages']
    chats_collection = db['chats']
    
    # Create indexes for better performance
    users_collection.create_index('username', unique=True)
    users_collection.create_index('user_id', unique=True)
    messages_collection.create_index([('from_id', 1), ('to_id', 1)])
    messages_collection.create_index([('created_at', -1)])
    chats_collection.create_index([('user1_id', 1), ('user2_id', 1)], unique=True)
    
    print("✅ MongoDB indexes created")
    
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    print("⚠️ Falling back to SQLite mode")
    # You can add SQLite fallback here if needed

# ============================================
# HELPER FUNCTIONS
# ============================================

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    """Decorator to require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Please login first"}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_user_profile(user_id):
    """Get user profile from MongoDB"""
    user = users_collection.find_one({'user_id': user_id})
    if user:
        return {
            "user_id": user['user_id'],
            "username": user['username'],
            "full_name": user.get('full_name', user['username']),
            "bio": user.get('bio', "Hey! I'm using EvaMassage"),
            "profile_pic": user.get('profile_pic'),
            "joined": user.get('created_at')
        }
    return None

# ============================================
# PAGE ROUTES
# ============================================

@app.route('/')
def index():
    """Home page - redirect to dashboard if logged in"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with chat interface"""
    profile = get_user_profile(session['user_id'])
    return render_template('index.html', user=session, profile=profile)

@app.route('/profile')
@login_required
def profile_page():
    """User profile page"""
    profile = get_user_profile(session['user_id'])
    return render_template('profile.html', profile=profile)

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('index'))

# ============================================
# AUTHENTICATION API ROUTES
# ============================================

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '')
        full_name = data.get('full_name', '').strip()
        
        print(f"📝 Registration attempt: {username}")
        
        # Validation
        if not username or len(username) < 3:
            return jsonify({"success": False, "error": "Username must be at least 3 characters"}), 400
        
        if not password or len(password) < 4:
            return jsonify({"success": False, "error": "Password must be at least 4 characters"}), 400
        
        if not full_name:
            full_name = username
        
        # Check if username exists
        if users_collection.find_one({'username': username}):
            return jsonify({"success": False, "error": "Username already exists"}), 400
        
        # Create new user
        user_id = secrets.randbelow(1000000000)
        user = {
            'user_id': user_id,
            'username': username,
            'password': hash_password(password),
            'full_name': full_name,
            'bio': '',
            'profile_pic': '',
            'is_active': True,
            'created_at': datetime.now(),
            'last_login': None
        }
        
        users_collection.insert_one(user)
        print(f"✅ User registered: {username} (ID: {user_id})")
        
        return jsonify({"success": True, "message": "Registration successful! Please login."})
    
    except Exception as e:
        print(f"❌ Registration error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        hashed_password = hash_password(password)
        
        # Find user in MongoDB
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
            
            return jsonify({
                "success": True,
                "user": {
                    "user_id": user['user_id'],
                    "username": user['username'],
                    "full_name": user.get('full_name', user['username'])
                }
            })
        
        return jsonify({"success": False, "error": "Invalid username or password"}), 401
    
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================
# USER API ROUTES
# ============================================

@app.route('/api/users/search')
@login_required
def search_users():
    """Search for users by username or full name"""
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    # Search users in MongoDB
    users = users_collection.find({
        '$and': [
            {'user_id': {'$ne': session['user_id']}},
            {'$or': [
                {'username': {'$regex': query, '$options': 'i'}},
                {'full_name': {'$regex': query, '$options': 'i'}}
            ]}
        ]
    }).limit(20)
    
    result = []
    for user in users:
        result.append({
            "user_id": user['user_id'],
            "username": user['username'],
            "full_name": user.get('full_name', user['username']),
            "bio": user.get('bio', '')
        })
    
    return jsonify(result)

@app.route('/api/users/profile/<int:user_id>')
@login_required
def get_profile(user_id):
    """Get user profile by ID"""
    profile = get_user_profile(user_id)
    if profile:
        return jsonify(profile)
    return jsonify({"error": "User not found"}), 404

@app.route('/api/users/update_profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    try:
        data = request.json
        update_data = {}
        
        if data.get('full_name'):
            update_data['full_name'] = data.get('full_name')
            session['full_name'] = data.get('full_name')
        
        if data.get('bio'):
            update_data['bio'] = data.get('bio')
        
        if update_data:
            users_collection.update_one(
                {'user_id': session['user_id']},
                {'$set': update_data}
            )
        
        return jsonify({"success": True, "message": "Profile updated"})
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================
# MESSAGES API ROUTES
# ============================================

@app.route('/api/messages/send', methods=['POST'])
@login_required
def send_message():
    """Send a message to another user"""
    try:
        data = request.json
        to_id = data.get('to_id')
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({"error": "Message cannot be empty"}), 400
        
        # Save message to MongoDB
        message_doc = {
            'from_id': session['user_id'],
            'to_id': to_id,
            'message': message,
            'is_read': False,
            'created_at': datetime.now()
        }
        messages_collection.insert_one(message_doc)
        
        # Update or create chat
        user1, user2 = sorted([session['user_id'], to_id])
        chats_collection.update_one(
            {'user1_id': user1, 'user2_id': user2},
            {'$set': {
                'last_message': message,
                'last_message_time': datetime.now()
            }},
            upsert=True
        )
        
        return jsonify({"success": True, "message": "Message sent"})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/messages/<int:user_id>')
@login_required
def get_messages(user_id):
    """Get all messages between current user and another user"""
    try:
        # Get messages from MongoDB
        messages = messages_collection.find({
            '$or': [
                {'from_id': session['user_id'], 'to_id': user_id},
                {'from_id': user_id, 'to_id': session['user_id']}
            ]
        }).sort('created_at', 1).limit(100)
        
        result = []
        for msg in messages:
            result.append({
                "id": str(msg['_id']),
                "from_id": msg['from_id'],
                "to_id": msg['to_id'],
                "message": msg['message'],
                "is_read": msg.get('is_read', False),
                "created_at": msg['created_at']
            })
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chats')
@login_required
def get_chats():
    """Get all chats for current user"""
    try:
        # Get all chats for user
        chats = chats_collection.find({
            '$or': [
                {'user1_id': session['user_id']},
                {'user2_id': session['user_id']}
            ]
        }).sort('last_message_time', -1)
        
        chat_list = []
        for chat in chats:
            other_user_id = chat['user2_id'] if chat['user1_id'] == session['user_id'] else chat['user1_id']
            profile = get_user_profile(other_user_id)
            if profile:
                profile['last_message'] = chat.get('last_message', '')
                profile['last_message_time'] = chat.get('last_message_time')
                chat_list.append(profile)
        
        return jsonify(chat_list)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/unread_count')
@login_required
def unread_count():
    """Get count of unread messages"""
    try:
        count = messages_collection.count_documents({
            'to_id': session['user_id'],
            'is_read': False
        })
        return jsonify({"count": count})
    
    except Exception as e:
        return jsonify({"count": 0})

@app.route('/api/messages/mark_read', methods=['POST'])
@login_required
def mark_read():
    """Mark messages as read"""
    try:
        data = request.json
        from_user_id = data.get('user_id')
        
        messages_collection.update_many(
            {'from_id': from_user_id, 'to_id': session['user_id'], 'is_read': False},
            {'$set': {'is_read': True}}
        )
        
        return jsonify({"success": True})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# DEBUG & HEALTH CHECK ROUTES
# ============================================

@app.route('/health')
def health_check():
    """Health check endpoint for Koyeb"""
    return jsonify({
        "status": "healthy",
        "database": "mongodb",
        "timestamp": datetime.now()
    })

@app.route('/api/debug/db', methods=['GET'])
@login_required
def debug_db():
    """Debug endpoint to check database status"""
    try:
        stats = {
            "status": "ok",
            "database": "MongoDB",
            "database_name": MONGO_DB_NAME,
            "users_count": users_collection.count_documents({}),
            "messages_count": messages_collection.count_documents({}),
            "chats_count": chats_collection.count_documents({})
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return jsonify({"error": "Internal server error"}), 500

# ============================================
# RUN THE APP
# ============================================

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 EvaMassage Server Starting...")
    print("=" * 50)
    print(f"📍 Local URL: http://localhost:{PORT}")
    print(f"🔧 Debug Mode: {DEBUG}")
    print(f"💾 Database: {DATABASE_TYPE}")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
