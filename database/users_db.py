import sqlite3
from datetime import datetime
import hashlib
import secrets

class UserDatabase:
    def __init__(self, db_path="evamassage.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Users table - NO EMAIL FIELD
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
                      created_at TIMESTAMP,
                      FOREIGN KEY (from_id) REFERENCES users(user_id),
                      FOREIGN KEY (to_id) REFERENCES users(user_id))''')
        
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
    
    def register_user(self, user_id, username, password, full_name=None):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Simple password hashing (you can use bcrypt for production)
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        try:
            c.execute("""INSERT INTO users (user_id, username, password, full_name, created_at) 
                         VALUES (?, ?, ?, ?, ?)""",
                     (user_id, username, hashed_password, full_name, datetime.now()))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def authenticate(self, username, password):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        c.execute("SELECT user_id, username, full_name FROM users WHERE username=? AND password=? AND is_active=1",
                 (username, hashed_password))
        user = c.fetchone()
        conn.close()
        
        if user:
            return {"user_id": user[0], "username": user[1], "full_name": user[2]}
        return None
    
    def get_user_profile(self, user_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT user_id, username, full_name, bio, profile_pic, created_at FROM users WHERE user_id=?",
                 (user_id,))
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
    
    def search_users(self, query, current_user_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""SELECT user_id, username, full_name, bio 
                     FROM users 
                     WHERE (username LIKE ? OR full_name LIKE ?) 
                     AND user_id != ? 
                     LIMIT 20""",
                 (f"%{query}%", f"%{query}%", current_user_id))
        users = c.fetchall()
        conn.close()
        
        return [{"user_id": u[0], "username": u[1], "full_name": u[2] or u[1], "bio": u[3]} for u in users]
    
    def update_last_login(self, user_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE users SET last_login=? WHERE user_id=?", (datetime.now(), user_id))
        conn.commit()
        conn.close()
    
    def update_profile(self, user_id, full_name=None, bio=None):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        if full_name:
            c.execute("UPDATE users SET full_name=? WHERE user_id=?", (full_name, user_id))
        if bio:
            c.execute("UPDATE users SET bio=? WHERE user_id=?", (bio, user_id))
        conn.commit()
        conn.close()
