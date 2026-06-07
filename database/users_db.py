import sqlite3
from datetime import datetime
import hashlib

class UserDatabase:
    def __init__(self, db_path="evamassage.db"):
        self.db_path = db_path
    
    def authenticate(self, username, password):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        c.execute("SELECT user_id, username, full_name FROM users WHERE username=? AND password=?", 
                 (username, hashed_password))
        user = c.fetchone()
        conn.close()
        if user:
            return {"user_id": user[0], "username": user[1], "full_name": user[2]}
        return None
    
    def register_user(self, user_id, username, password, full_name):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        try:
            c.execute("INSERT INTO users (user_id, username, password, full_name, created_at) VALUES (?, ?, ?, ?, ?)",
                     (user_id, username, hashed_password, full_name, datetime.now()))
            conn.commit()
            return True
        except:
            return False
        finally:
            conn.close()
    
    def get_user_profile(self, user_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT user_id, username, full_name, bio, created_at FROM users WHERE user_id=?", (user_id,))
        user = c.fetchone()
        conn.close()
        if user:
            return {"user_id": user[0], "username": user[1], "full_name": user[2] or user[1], "bio": user[3] or "Hi!", "joined": user[4]}
        return None
    
    def search_users(self, query, current_user_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT user_id, username, full_name FROM users WHERE (username LIKE ? OR full_name LIKE ?) AND user_id != ? LIMIT 20",
                 (f"%{query}%", f"%{query}%", current_user_id))
        users = c.fetchall()
        conn.close()
        return [{"user_id": u[0], "username": u[1], "full_name": u[2] or u[1]} for u in users]
    
    def update_last_login(self, user_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE users SET last_login=? WHERE user_id=?", (datetime.now(), user_id))
        conn.commit()
        conn.close()
