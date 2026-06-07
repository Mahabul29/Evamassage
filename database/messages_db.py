import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

class MessagesDatabase:
    def __init__(self, db_path="evamassage.db"):
        self.db_path = db_path
        self.init_tables()
    
    def init_tables(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Messages table with reactions
        c.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id INTEGER,
            to_id INTEGER,
            message TEXT,
            message_type TEXT DEFAULT 'text',
            file_path TEXT,
            file_name TEXT,
            file_size INTEGER,
            is_read BOOLEAN DEFAULT 0,
            is_deleted BOOLEAN DEFAULT 0,
            reply_to INTEGER,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            FOREIGN KEY (from_id) REFERENCES users(user_id),
            FOREIGN KEY (to_id) REFERENCES users(user_id),
            FOREIGN KEY (reply_to) REFERENCES messages(id)
        )''')
        
        # Message reactions table
        c.execute('''CREATE TABLE IF NOT EXISTS message_reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            user_id INTEGER,
            reaction TEXT,
            created_at TIMESTAMP,
            FOREIGN KEY (message_id) REFERENCES messages(id),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(message_id, user_id)
        )''')
        
        # Message attachments table
        c.execute('''CREATE TABLE IF NOT EXISTS message_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            file_path TEXT,
            file_name TEXT,
            file_type TEXT,
            file_size INTEGER,
            created_at TIMESTAMP,
            FOREIGN KEY (message_id) REFERENCES messages(id)
        )''')
        
        conn.commit()
        conn.close()
    
    def send_message(self, from_id: int, to_id: int, message: str, reply_to: int = None) -> int:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""INSERT INTO messages (from_id, to_id, message, reply_to, created_at, updated_at) 
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (from_id, to_id, message, reply_to, datetime.now(), datetime.now()))
        message_id = c.lastrowid
        conn.commit()
        conn.close()
        return message_id
    
    def get_messages(self, user1_id: int, user2_id: int, limit: int = 50, offset: int = 0) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""SELECT id, from_id, to_id, message, message_type, file_path, 
                            is_read, reply_to, created_at 
                     FROM messages 
                     WHERE ((from_id=? AND to_id=?) OR (from_id=? AND to_id=?))
                     AND is_deleted=0
                     ORDER BY created_at DESC LIMIT ? OFFSET ?""",
                  (user1_id, user2_id, user2_id, user1_id, limit, offset))
        messages = c.fetchall()
        conn.close()
        
        return [{
            "id": m[0],
            "from_id": m[1],
            "to_id": m[2],
            "message": m[3],
            "type": m[4],
            "file_path": m[5],
            "is_read": m[6],
            "reply_to": m[7],
            "created_at": m[8]
        } for m in messages]
    
    def mark_as_read(self, message_ids: List[int]):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(f"UPDATE messages SET is_read=1 WHERE id IN ({','.join('?' * len(message_ids))})", message_ids)
        conn.commit()
        conn.close()
    
    def delete_message(self, message_id: int, user_id: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE messages SET is_deleted=1 WHERE id=? AND (from_id=? OR to_id=?)", 
                  (message_id, user_id, user_id))
        affected = c.rowcount
        conn.commit()
        conn.close()
        return affected > 0
    
    def add_reaction(self, message_id: int, user_id: int, reaction: str):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""INSERT OR REPLACE INTO message_reactions (message_id, user_id, reaction, created_at) 
                     VALUES (?, ?, ?, ?)""",
                  (message_id, user_id, reaction, datetime.now()))
        conn.commit()
        conn.close()
    
    def get_reactions(self, message_id: int) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""SELECT user_id, reaction FROM message_reactions WHERE message_id=?""", (message_id,))
        reactions = c.fetchall()
        conn.close()
        return [{"user_id": r[0], "reaction": r[1]} for r in reactions]
    
    def get_unread_count(self, user_id: int) -> int:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM messages WHERE to_id=? AND is_read=0", (user_id,))
        count = c.fetchone()[0]
        conn.close()
        return count
