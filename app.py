from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import secrets
from datetime import datetime
import hashlib
from pymongo import MongoClient
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-12345'

# MongoDB Connection
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'evamassage')

try:
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]
    users_collection = db['users']
    messages_collection = db['messages']
    chats_collection = db['chats']
    
    # Create indexes
    users_collection.create_index('username', unique=True)
    users_collection.create_index('user_id', unique=True)
    
    # Create channel collections
    if 'channels' not in db.list_collection_names():
        db.create_collection('channels')
    if 'channel_members' not in db.list_collection_names():
        db.create_collection('channel_members')
    if 'channel_messages' not in db.list_collection_names():
        db.create_collection('channel_messages')
    
    print("✅ MongoDB Connected")
except Exception as e:
    print(f"❌ MongoDB Error: {e}")
    db = None
    users_collection = None

# Helper Functions
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
            "joined": user.get('created_at')
        }
    return None

# ========== PAGE ROUTES ==========
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

# ========== AUTH API ==========
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
        
        if users_collection is None:
            return jsonify({"success": False, "error": "Database not connected"}), 500
        
        if users_collection.find_one({'username': username}):
            return jsonify({"success": False, "error": "Username already exists"}), 400
        
        user_id = secrets.randbelow(1000000000)
        user = {
            'user_id': user_id,
            'username': username,
            'password': hash_password(password),
            'full_name': full_name if full_name else username,
            'bio': '',
            'is_active': True,
            'created_at': datetime.now()
        }
        
        users_collection.insert_one(user)
        return jsonify({"success": True, "message": "Registration successful!"})
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
        
        user = users_collection.find_one({'username': username, 'password': hashed_password})
        
        if user:
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['full_name'] = user.get('full_name', user['username'])
            
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
        return jsonify({"success": False, "error": str(e)}), 500

# ========== USER API ==========
@app.route('/api/users/search')
@login_required
def search_users():
    query = request.args.get('q', '').strip().lower()
    if len(query) < 2 or users_collection is None:
        return jsonify([])
    
    users = users_collection.find({
        'user_id': {'$ne': session['user_id']},
        '$or': [
            {'username': {'$regex': query, '$options': 'i'}},
            {'full_name': {'$regex': query, '$options': 'i'}}
        ]
    }).limit(20)
    
    result = [{"user_id": u['user_id'], "username": u['username'], "full_name": u.get('full_name', u['username'])} for u in users]
    return jsonify(result)

@app.route('/api/users/profile/<int:user_id>')
@login_required
def get_profile(user_id):
    profile = get_user_profile(user_id)
    if profile:
        return jsonify(profile)
    return jsonify({"error": "User not found"}), 404

# ========== MESSAGES API ==========
@app.route('/api/messages/send', methods=['POST'])
@login_required
def send_message():
    try:
        data = request.json
        to_id = data.get('to_id')
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({"error": "Message cannot be empty"}), 400
        
        if db is None:
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
            {'$set': {'last_message': message, 'last_message_time': datetime.now()}},
            upsert=True
        )
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/messages/<int:user_id>')
@login_required
def get_messages(user_id):
    try:
        if db is None:
            return jsonify([])
        
        messages = messages_collection.find({
            '$or': [
                {'from_id': session['user_id'], 'to_id': user_id},
                {'from_id': user_id, 'to_id': session['user_id']}
            ]
        }).sort('created_at', 1).limit(100)
        
        result = [{"id": str(m['_id']), "from_id": m['from_id'], "to_id": m['to_id'], "message": m['message'], "created_at": m['created_at']} for m in messages]
        return jsonify(result)
    except Exception:
        return jsonify([])

@app.route('/api/chats')
@login_required
def get_chats():
    try:
        if db is None:
            return jsonify([])
        
        chats = chats_collection.find({
            '$or': [{'user1_id': session['user_id']}, {'user2_id': session['user_id']}]
        }).sort('last_message_time', -1)
        
        chat_list = []
        for chat in chats:
            other_user_id = chat['user2_id'] if chat['user1_id'] == session['user_id'] else chat['user1_id']
            profile = get_user_profile(other_user_id)
            if profile:
                profile['last_message'] = chat.get('last_message', '')
                chat_list.append(profile)
        
        return jsonify(chat_list)
    except Exception:
        return jsonify([])

# ========== CHANNEL API ==========
@app.route('/api/channels', methods=['GET'])
@login_required
def get_channels():
    if db is None:
        return jsonify([])
    
    members = db['channel_members'].find({'user_id': session['user_id']})
    result = []
    
    for member in members:
        channel = db['channels'].find_one({'_id': member['channel_id']})
        if channel:
            member_count = db['channel_members'].count_documents({'channel_id': channel['_id']})
            result.append({
                'id': str(channel['_id']),
                'name': channel['name'],
                'description': channel.get('description', ''),
                'member_count': member_count,
                'role': member.get('role', 'member')
            })
    
    return jsonify(result)

@app.route('/api/channels', methods=['POST'])
@login_required
def create_channel():
    if db is None:
        return jsonify({"error": "Database not connected"}), 500
    
    data = request.get_json()
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    
    if not name or len(name) < 2:
        return jsonify({"error": "Channel name must be at least 2 characters"}), 400
    
    existing = db['channels'].find_one({'name': name})
    if existing:
        return jsonify({"error": "Channel name already exists"}), 400
    
    channel = {
        'name': name,
        'description': description,
        'created_by': session['user_id'],
        'created_at': datetime.now(),
        'is_active': True
    }
    result = db['channels'].insert_one(channel)
    channel_id = result.inserted_id
    
    db['channel_members'].insert_one({
        'channel_id': channel_id,
        'user_id': session['user_id'],
        'role': 'admin',
        'joined_at': datetime.now()
    })
    
    return jsonify({"success": True, "id": str(channel_id), "name": name})

@app.route('/api/channels/<channel_id>/send', methods=['POST'])
@login_required
def send_channel_message(channel_id):
    if db is None:
        return jsonify({"error": "Database error"}), 500
    
    from bson.objectid import ObjectId
    try:
        oid = ObjectId(channel_id)
    except:
        return jsonify({"error": "Invalid channel ID"}), 400
    
    is_member = db['channel_members'].find_one({'channel_id': oid, 'user_id': session['user_id']})
    if not is_member:
        return jsonify({"error": "You are not a member"}), 403
    
    data = request.get_json()
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400
    
    db['channel_messages'].insert_one({
        'channel_id': oid,
        'from_id': session['user_id'],
        'message': message,
        'created_at': datetime.now()
    })
    
    return jsonify({"success": True})

@app.route('/api/channels/<channel_id>/messages', methods=['GET'])
@login_required
def get_channel_messages(channel_id):
    if db is None:
        return jsonify([])
    
    from bson.objectid import ObjectId
    try:
        oid = ObjectId(channel_id)
    except:
        return jsonify([])
    
    is_member = db['channel_members'].find_one({'channel_id': oid, 'user_id': session['user_id']})
    if not is_member:
        return jsonify([])
    
    messages = db['channel_messages'].find({'channel_id': oid}).sort('created_at', 1).limit(100)
    result = []
    
    for msg in messages:
        user = db['users'].find_one({'user_id': msg['from_id']})
        sender_name = user.get('full_name', user.get('username', 'Unknown')) if user else 'Unknown'
        
        result.append({
            'id': str(msg['_id']),
            'from_id': msg['from_id'],
            'from_name': sender_name,
            'message': msg['message'],
            'created_at': msg['created_at'].isoformat() if hasattr(msg['created_at'], 'isoformat') else str(msg['created_at'])
        })
    
    return jsonify(result)

# ========== HEALTH CHECK ==========
@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 EvaMassage starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
