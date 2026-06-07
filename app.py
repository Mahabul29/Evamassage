from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import secrets
import os
from datetime import datetime
from database import user_db, banned_users, maintenance
from config import SECRET_KEY, PORT, ADMIN_USERNAME, ADMIN_PASSWORD

app = Flask(__name__)
app.secret_key = SECRET_KEY

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

# Routes
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

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    # Check admin login
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['user_id'] = 1
        session['username'] = ADMIN_USERNAME
        session['full_name'] = 'Administrator'
        session['is_admin'] = True
        return jsonify({"success": True, "is_admin": True})
    
    # Check regular user
    user = user_db.authenticate(username, password)
    if user:
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['full_name'] = user['full_name']
        session['is_admin'] = False
        user_db.update_last_login(user['user_id'])
        return jsonify({"success": True, "is_admin": False})
    
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    user_id = secrets.randbelow(1000000000)
    
    if user_db.register_user(
        user_id, 
        data.get('username'), 
        data.get('password'), 
        data.get('full_name')
    ):
        return jsonify({"success": True, "message": "Registration successful"})
    
    return jsonify({"success": False, "error": "Username already exists"}), 400

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('index.html', 
                         user=session,
                         fqdn=os.environ.get('FQDN', ''))

@app.route('/api/users/search')
@login_required
def search_users():
    query = request.args.get('q', '')
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
    # Update user profile logic
    return jsonify({"success": True})

@app.route('/api/messages/send', methods=['POST'])
@login_required
def send_message():
    data = request.json
    to_id = data.get('to_id')
    message = data.get('message')
    
    # Save message to database
    from database import user_db
    import sqlite3
    from datetime import datetime
    
    conn = sqlite3.connect(user_db.db_path)
    c = conn.cursor()
    c.execute("""INSERT INTO messages (from_id, to_id, message, created_at) 
                 VALUES (?, ?, ?, ?)""",
              (session['user_id'], to_id, message, datetime.now()))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": "Message sent"})

@app.route('/api/messages/<int:user_id>')
@login_required
def get_messages(user_id):
    from database import user_db
    import sqlite3
    
    conn = sqlite3.connect(user_db.db_path)
    c = conn.cursor()
    c.execute("""SELECT from_id, to_id, message, created_at 
                 FROM messages 
                 WHERE (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)
                 ORDER BY created_at ASC LIMIT 100""",
              (session['user_id'], user_id, user_id, session['user_id']))
    messages = c.fetchall()
    conn.close()
    
    return jsonify([{
        "from_id": m[0],
        "to_id": m[1],
        "message": m[2],
        "created_at": m[3]
    } for m in messages])

@app.route('/api/chats')
@login_required
def get_chats():
    from database import user_db
    import sqlite3
    
    conn = sqlite3.connect(user_db.db_path)
    c = conn.cursor()
    c.execute("""SELECT DISTINCT 
                    CASE 
                        WHEN from_id = ? THEN to_id
                        ELSE from_id
                    END as chat_user_id,
                    MAX(created_at) as last_message_time
                 FROM messages 
                 WHERE from_id = ? OR to_id = ?
                 GROUP BY chat_user_id
                 ORDER BY last_message_time DESC""",
              (session['user_id'], session['user_id'], session['user_id']))
    chats = c.fetchall()
    conn.close()
    
    chat_list = []
    for chat in chats:
        profile = user_db.get_user_profile(chat[0])
        if profile:
            chat_list.append(profile)
    
    return jsonify(chat_list)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Admin routes
@app.route('/api/admin/stats')
@admin_required
def get_stats():
    from database import user_db
    import sqlite3
    
    conn = sqlite3.connect(user_db.db_path)
    c = conn.cursor()
    
    total_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_messages = c.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    active_today = c.execute("SELECT COUNT(*) FROM users WHERE last_login >= date('now')").fetchone()[0]
    
    conn.close()
    
    return jsonify({
        "total_users": total_users,
        "total_messages": total_messages,
        "active_today": active_today
    })

@app.route('/api/admin/users')
@admin_required
def get_all_users():
    from database import user_db
    import sqlite3
    
    conn = sqlite3.connect(user_db.db_path)
    c = conn.cursor()
    c.execute("SELECT user_id, username, full_name, created_at, last_login FROM users ORDER BY created_at DESC")
    users = c.fetchall()
    conn.close()
    
    return jsonify([{
        "user_id": u[0],
        "username": u[1],
        "full_name": u[2],
        "joined": u[3],
        "last_login": u[4]
    } for u in users])

@app.route('/api/admin/ban/<int:user_id>', methods=['POST'])
@admin_required
def ban_user(user_id):
    from database import banned_users
    banned_users.ban_user(user_id, request.json.get('reason', 'Banned by admin'))
    return jsonify({"success": True})

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
