from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import secrets
import os
from datetime import datetime
import sqlite3
import hashlib

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Database setup
DB_PATH = "evamassage.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT UNIQUE,
                  password TEXT,
                  full_name TEXT,
                  bio TEXT,
                  profile_pic TEXT,
                  is_active BOOLEAN DEFAULT 1,
                  created_at TIMESTAMP,
                  last_login TIMESTAMP)''')
    
    # Messages table
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  from_id INTEGER,
                  to_id INTEGER,
                  message TEXT,
                  is_read BOOLEAN DEFAULT 0,
                  created_at TIMESTAMP)''')
    
    # Chats table
    c.execute('''CREATE TABLE IF NOT EXISTS chats
                 (chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user1_id INTEGER,
                  user2_id INTEGER,
                  last_message TEXT,
                  last_message_time TIMESTAMP,
                  UNIQUE(user1_id, user2_id))''')
    
    conn.commit()
    conn.close()

init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Please login first"}), 401
        return f(*args, **kwargs)
    return decorated_function

# ============== PAGE ROUTES ==============
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    profile = get_user_profile(session['user_id'])
    return render_template('index.html', user=session, profile=profile)

# ============== AUTH API ==============
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    full_name = data.get('full_name', '').strip()
    
    if not username or len(username) < 3:
        return jsonify({"success": False, "error": "Username must be at least 3 characters"}), 400
    
    if not password or len(password) < 4:
        return jsonify({"success": False, "error": "Password must be at least 4 characters"}), 400
    
    if not full_name:
        full_name = username
    
    user_id = secrets.randbelow(1000000000)
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (user_id, username, password, full_name, created_at) VALUES (?, ?, ?, ?, ?)",
                 (user_id, username, hashed_password, full_name, datetime.now()))
        conn.commit()
        return jsonify({"success": True, "message": "Registration successful!"})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "error": "Username already exists"}), 400
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, full_name FROM users WHERE username=? AND password=? AND is_active=1",
             (username, hashed_password))
    user = c.fetchone()
    conn.close()
    
    if user:
        session['user_id'] = user[0]
        session['username'] = user[1]
        session['full_name'] = user[2]
        
        # Update last login
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE users SET last_login=? WHERE user_id=?", (datetime.now(), user[0]))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "user": {"user_id": user[0], "username": user[1], "full_name": user[2]}})
    
    return jsonify({"success": False, "error": "Invalid username or password"}), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ============== USER API ==============
def get_user_profile(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, full_name, bio, profile_pic, created_at FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    
    if user:
        return {
            "user_id": user[0],
            "username": user[1],
            "full_name": user[2] or user[1],
            "bio": user[3] or "Hey! I'm using EvaMassage",
            "profile_pic": user[4],
            "joined": user[5]
        }
    return None

@app.route('/api/users/search')
@login_required
def search_users():
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT user_id, username, full_name, bio 
                 FROM users 
                 WHERE (username LIKE ? OR full_name LIKE ?) 
                 AND user_id != ? 
                 LIMIT 20""",
             (f"%{query}%", f"%{query}%", session['user_id']))
    users = c.fetchall()
    conn.close()
    
    return jsonify([{"user_id": u[0], "username": u[1], "full_name": u[2] or u[1], "bio": u[3]} for u in users])

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
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if data.get('full_name'):
        c.execute("UPDATE users SET full_name=? WHERE user_id=?", (data.get('full_name'), session['user_id']))
        session['full_name'] = data.get('full_name')
    if data.get('bio'):
        c.execute("UPDATE users SET bio=? WHERE user_id=?", (data.get('bio'), session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# ============== MESSAGES API ==============
@app.route('/api/messages/send', methods=['POST'])
@login_required
def send_message():
    data = request.json
    to_id = data.get('to_id')
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO messages (from_id, to_id, message, created_at) VALUES (?, ?, ?, ?)",
             (session['user_id'], to_id, message, datetime.now()))
    
    # Update chat
    user1, user2 = sorted([session['user_id'], to_id])
    c.execute("INSERT OR REPLACE INTO chats (user1_id, user2_id, last_message, last_message_time) VALUES (?, ?, ?, ?)",
             (user1, user2, message, datetime.now()))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

@app.route('/api/messages/<int:user_id>')
@login_required
def get_messages(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT msg_id, from_id, to_id, message, is_read, created_at 
                 FROM messages 
                 WHERE (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)
                 ORDER BY created_at ASC LIMIT 100""",
             (session['user_id'], user_id, user_id, session['user_id']))
    messages = c.fetchall()
    conn.close()
    
    return jsonify([{
        "id": m[0],
        "from_id": m[1],
        "to_id": m[2],
        "message": m[3],
        "is_read": m[4],
        "created_at": m[5]
    } for m in messages])

@app.route('/api/chats')
@login_required
def get_chats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT 
                    CASE 
                        WHEN user1_id = ? THEN user2_id
                        ELSE user1_id
                    END as chat_user_id,
                    last_message,
                    last_message_time
                 FROM chats 
                 WHERE user1_id = ? OR user2_id = ?
                 ORDER BY last_message_time DESC""",
             (session['user_id'], session['user_id'], session['user_id']))
    chats = c.fetchall()
    conn.close()
    
    chat_list = []
    for chat in chats:
        profile = get_user_profile(chat[0])
        if profile:
            profile['last_message'] = chat[1]
            profile['last_message_time'] = chat[2]
            chat_list.append(profile)
    
    return jsonify(chat_list)

@app.route('/api/unread_count')
@login_required
def unread_count():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM messages WHERE to_id=? AND is_read=0", (session['user_id'],))
    count = c.fetchone()[0]
    conn.close()
    return jsonify({"count": count})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
