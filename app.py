from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import secrets
import os
from datetime import datetime
import hashlib
from pymongo import MongoClient
from config import *
from channel import channel_bp

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
    
    users_collection.create_index('username', unique=True)
    users_collection.create_index('user_id', unique=True)
    messages_collection.create_index([('from_id', 1), ('to_id', 1)])
    messages_collection.create_index('created_at')
    chats_collection.create_index([('user1_id', 1), ('user2_id', 1)], unique=True)
    
    print(f"✅ MongoDB Connected to {MONGO_DB_NAME}")
except Exception as e:
    print(f"❌ MongoDB Error: {e}")
    users_collection = None
    db = None

# ============================================
# CHANNEL COLLECTIONS INIT
# ============================================
def init_channel_collections():
    if db is not None:
        if 'channels' not in db.list_collection_names():
            db.create_collection('channels')
        if 'channel_members' not in db.list_collection_names():
            db.create_collection('channel_members')
        if 'channel_messages' not in db.list_collection_names():
            db.create_collection('channel_messages')
        db['channels'].create_index('name')
        db['channel_members'].create_index([('channel_id', 1), ('user_id', 1)], unique=True)

if users_collection is not None:
    init_channel_collections()

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

def get_user_profile(user_id):
    if users_collection is None:
        return None
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
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('index.html', user=session)

@app.route('/profile')
@login_required
def profile_page():
    profile = get_user_profile(session['user_id'])
    return render_template('profile.html', profile=profile)

@app.route('/settings')
@login_required
def settings_page():
    return render_template('settings.html', user=session)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/sw.js')
def service_worker():
    return app.send_static_file('sw.js')

# ============================================
# AUTHENTICATION API
# ============================================
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        username = data.get('username', '').strip().lower()
        password = data.get('password', '')
        full_name = data.get('full_name', '').strip()
        
        if not username or len(username) < 3:
            return jsonify({"success": False, "error": "Username must be at least 3 characters"}), 400
        
        if not password or len(password) < 4:
            return jsonify({"success": False, "error": "Password must be at least 4 characters"}), 400
        
        if not full_name:
            full_name = username
        
        if users_collection is None:
            return jsonify({"success": False, "error": "Database not connected"}), 500
        
        if users_collection.find_one({'username': username}):
            return jsonify({"success": False, "error": "Username already exists"}), 400
        
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
        return jsonify({"success": True, "message": "Registration successful! Please login."})
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username', '').strip().lower()
        password = data.get('password', '')
        hashed_password = hash_password(password)
        
        if users_collection is None:
            return jsonify({"success": False, "error": "Database not connected"}), 500
        
        user = users_collection.find_one({
            'username': username,
            'password': hashed_password,
            'is_active': True
        })
        
        if user:
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['full_name'] = user.get('full_name', user['username'])
            
            users_collection.update_one(
                {'user_id': user['user_id']},
                {'$set': {'last_login': datetime.now()}}
            )
            
            return jsonify({
                "success": True,
                "user": {
                    "user_id": user['user_id'],
                    "username": user['username'],
                    "full_name': user.get('full_name', user['username'])
                }
            })
        
        return jsonify({"success": False, "error": "Invalid username or password"}), 401
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================
# USER API
# ============================================
@app.route('/api/users/search')
@login_required
def search_users():
    query = request.args.get('q', '').strip().lower()
    if len(query) < 2:
        return jsonify([])
    
    if users_collection is None:
        return jsonify([])
    
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
    profile = get_user_profile(user_id)
    if profile:
        return jsonify(profile)
    return jsonify({"error": "User not found"}), 404

@app.route('/api/users/update_profile', methods=['POST'])
@login_required
def update_profile():
    try:
        data = request.json
        update_data = {}
        
        if data.get('full_name'):
            update_data['full_name'] = data.get('full_name')
            session['full_name'] = data.get('full_name')
        
        if data.get('bio'):
            update_data['bio'] = data.get('bio')
        
        if update_data and users_collection is not None:
            users_collection.update_one(
                {'user_id': session['user_id']},
                {'$set': update_data}
            )
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/change_password', methods=['POST'])
@login_required
def change_password():
    try:
        data = request.json
        current_password = data.get('current')
        new_password = data.get('new')
        
        if not new_password or len(new_password) < 4:
            return jsonify({"success": False, "error": "Password must be at least 4 characters"}), 400
        
        hashed_current = hash_password(current_password)
        
        user = users_collection.find_one({
            'user_id': session['user_id'],
            'password': hashed_current
        })
        
        if not user:
            return jsonify({"success": False, "error": "Current password is incorrect"}), 400
        
        users_collection.update_one(
            {'user_id': session['user_id']},
            {'$set': {'password': hash_password(new_password)}}
        )
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/delete_account', methods=['POST'])
@login_required
def delete_account():
    try:
        users_collection.delete_one({'user_id': session['user_id']})
        messages_collection.delete_many({
            '$or': [
                {'from_id': session['user_id']},
                {'to_id': session['user_id']}
            ]
        })
        chats_collection.delete_many({
            '$or': [
                {'user1_id': session['user_id']},
                {'user2_id': session['user_id']}
            ]
        })
        session.clear()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/create_test_users', methods=['GET'])
@login_required
def create_test_users():
    test_users = [
        {'username': 'alice', 'password': '1234', 'full_name': 'Alice Wonder', 'bio': 'Love to chat!'},
        {'username': 'bob', 'password': '1234', 'full_name': 'Bob Martin', 'bio': 'Tech enthusiast'},
        {'username': 'charlie', 'password': '1234', 'full_name': 'Charlie Brown', 'bio': 'Music lover'},
        {'username': 'diana', 'password': '1234', 'full_name': 'Diana Prince', 'bio': 'Adventurer'},
        {'username': 'eva', 'password': '1234', 'full_name': 'Eva Adams', 'bio': 'Artist'},
        {'username': 'frank', 'password': '1234', 'full_name': 'Frank Ocean', 'bio': 'Singer'},
        {'username': 'grace', 'password': '1234', 'full_name': 'Grace Hopper', 'bio': 'Coder'},
        {'username': 'henry', 'password': '1234', 'full_name': 'Henry Cavill', 'bio': 'Actor'},
    ]
    
    created = []
    for user in test_users:
        try:
            if not users_collection.find_one({'username': user['username']}):
                user_id = secrets.randbelow(1000000000)
                users_collection.insert_one({
                    'user_id': user_id,
                    'username': user['username'],
                    'password': hash_password(user['password']),
                    'full_name': user['full_name'],
                    'bio': user['bio'],
                    'profile_pic': '',
                    'is_active': True,
                    'created_at': datetime.now(),
                    'last_login': None
                })
                created.append(user['username'])
        except:
            pass
    
    return jsonify({"created": created, "count": len(created), "message": f"Created {len(created)} test users"})

# ============================================
# MESSAGES API
# ============================================
@app.route('/api/messages/send', methods=['POST'])
@login_required
def send_message():
    try:
        data = request.json
        to_id = data.get('to_id')
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({"error": "Message cannot be empty"}), 400
        
        if users_collection is None:
            return jsonify({"error": "Database error"}), 500
        
        message_doc = {
            'from_id': session['user_id'],
            'to_id': to_id,
            'message': message,
            'is_read': False,
            'created_at': datetime.now()
        }
        messages_collection.insert_one(message_doc)
        
        user1, user2 = sorted([session['user_id'], to_id])
        chats_collection.update_one(
            {'user1_id': user1, 'user2_id': user2},
            {'$set': {
                'last_message': message,
                'last_message_time': datetime.now()
            }},
            upsert=True
        )
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/messages/<int:user_id>')
@login_required
def get_messages(user_id):
    try:
        if users_collection is None:
            return jsonify([])
        
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
        return jsonify([])

@app.route('/api/chats')
@login_required
def get_chats():
    try:
        if users_collection is None:
            return jsonify([])
        
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
        return jsonify([])

@app.route('/api/unread_count')
@login_required
def unread_count():
    try:
        if users_collection is None:
            return jsonify({"count": 0})
        
        count = messages_collection.count_documents({
            'to_id': session['user_id'],
            'is_read': False
        })
        return jsonify({"count": count})
    except Exception:
        return jsonify({"count": 0})

@app.route('/api/messages/mark_read', methods=['POST'])
@login_required
def mark_read():
    try:
        data = request.json
        from_user_id = data.get('user_id')
        
        if users_collection is not None:
            messages_collection.update_many(
                {'from_id': from_user_id, 'to_id': session['user_id'], 'is_read': False},
                {'$set': {'is_read': True}}
            )
        
        return jsonify({"success": True})
    except Exception:
        return jsonify({"success": False})

# ============================================
# REQUEST CONTEXT (for channel.py)
# ============================================
@app.before_request
def before_request():
    request.db = db

# ============================================
# REGISTER CHANNEL BLUEPRINT
# ============================================
app.register_blueprint(channel_bp)

# ============================================
# HEALTH CHECK
# ============================================
@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "database": "mongodb" if users_collection is not None else "disconnected",
        "timestamp": datetime.now()
    })

# ============================================
# RUN APP
# ============================================
if __name__ == '__main__':
    print(f"🚀 EvaMassage starting on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
