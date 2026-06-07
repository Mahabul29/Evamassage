from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import secrets
import os
from datetime import datetime
from database import user_db, banned_users, maintenance

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

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

@app.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    profile = user_db.get_user_profile(session['user_id'])
    return render_template('index.html', user=session, profile=profile)

@app.route('/profile')
@login_required
def profile_page():
    profile = user_db.get_user_profile(session['user_id'])
    return render_template('profile.html', profile=profile)

# ============== AUTH API ROUTES ==============
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    full_name = data.get('full_name', '').strip()
    
    # Validation
    if not username or len(username) < 3:
        return jsonify({"success": False, "error": "Username must be at least 3 characters"}), 400
    
    if not password or len(password) < 4:
        return jsonify({"success": False, "error": "Password must be at least 4 characters"}), 400
    
    if not full_name:
        full_name = username
    
    # Generate unique user_id
    user_id = secrets.randbelow(1000000000)
    
    if user_db.register_user(user_id, username, password, full_name):
        return jsonify({"success": True, "message": "Registration successful! Please login."})
    
    return jsonify({"success": False, "error": "Username already exists"}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    user = user_db.authenticate(username, password)
    if user:
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['full_name'] = user['full_name']
        user_db.update_last_login(user['user_id'])
        return jsonify({"success": True, "user": user})
    
    return jsonify({"success": False, "error": "Invalid username or password"}), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ============== USER API ROUTES ==============
@app.route('/api/users/search')
@login_required
def search_users():
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    users = user_db.search_users(query, session['user_id'])
    return jsonify(users)

@app.route('/api/users/profile/<int:user_id>')
@login_required
def get_profile(user_id):
    profile = user_db.get_user_profile(user_id)
    if profile:
        return jsonify(profile)
    return jsonify({"error": "User not found"}), 404

@app.route('/api/users/update_profile', methods=['POST'])
@login_required
def update_profile():
    data = request.json
    user_db.update_profile(
        session['user_id'],
        full_name=data.get('full_name'),
        bio=data.get('bio')
    )
    session['full_name'] = data.get('full_name')
    return jsonify({"success": True, "message": "Profile updated"})

# ============== MESSAGE API ROUTES ==============
@app.route('/api/messages/send', methods=['POST'])
@login_required
def send_message():
    data = request.json
    to_id = data.get('to_id')
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400
    
    import sqlite3
    conn = sqlite3.connect(user_db.db_path)
    c = conn.cursor()
    c.execute("""INSERT INTO messages (from_id, to_id, message, created_at) 
                 VALUES (?, ?, ?, ?)""",
              (session['user_id'], to_id, message, datetime.now()))
    conn.commit()
    
    # Update or create chat
    user1, user2 = sorted([session['user_id'], to_id])
    c.execute("""INSERT OR REPLACE INTO chats (user1_id, user2_id, last_message, last_message_time)
                 VALUES (?, ?, ?, ?)""",
              (user1, user2, message, datetime.now()))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": "Message sent"})

@app.route('/api/messages/<int:user_id>')
@login_required
def get_messages(user_id):
    import sqlite3
    conn = sqlite3.connect(user_db.db_path)
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
    import sqlite3
    conn = sqlite3.connect(user_db.db_path)
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
        profile = user_db.get_user_profile(chat[0])
        if profile:
            profile['last_message'] = chat[1]
            profile['last_message_time'] = chat[2]
            chat_list.append(profile)
    
    return jsonify(chat_list)

@app.route('/api/unread_count')
@login_required
def unread_count():
    import sqlite3
    conn = sqlite3.connect(user_db.db_path)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM messages WHERE to_id=? AND is_read=0", (session['user_id'],))
    count = c.fetchone()[0]
    conn.close()
    return jsonify({"count": count})

@app.route('/api/messages/mark_read', methods=['POST'])
@login_required
def mark_read():
    data = request.json
    from_user_id = data.get('user_id')
    
    import sqlite3
    conn = sqlite3.connect(user_db.db_path)
    c = conn.cursor()
    c.execute("""UPDATE messages SET is_read=1 
                 WHERE from_id=? AND to_id=? AND is_read=0""",
              (from_user_id, session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
