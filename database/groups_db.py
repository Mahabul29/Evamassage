import sqlite3
from datetime import datetime
from typing import List, Dict

class GroupsDatabase:
    def __init__(self, db_path="evamassage.db"):
        self.db_path = db_path
        self.init_tables()
    
    def init_tables(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Groups table
        c.execute('''CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            avatar TEXT,
            created_by INTEGER,
            created_at TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (created_by) REFERENCES users(user_id)
        )''')
        
        # Group members table
        c.execute('''CREATE TABLE IF NOT EXISTS group_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            user_id INTEGER,
            role TEXT DEFAULT 'member',
            joined_at TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups(id),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(group_id, user_id)
        )''')
        
        # Group messages table
        c.execute('''CREATE TABLE IF NOT EXISTS group_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            from_id INTEGER,
            message TEXT,
            message_type TEXT DEFAULT 'text',
            file_path TEXT,
            created_at TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups(id),
            FOREIGN KEY (from_id) REFERENCES users(user_id)
        )''')
        
        conn.commit()
        conn.close()
    
    def create_group(self, name: str, created_by: int, description: str = "") -> int:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""INSERT INTO groups (name, description, created_by, created_at) 
                     VALUES (?, ?, ?, ?)""",
                  (name, description, created_by, datetime.now()))
        group_id = c.lastrowid
        
        # Add creator as admin
        c.execute("""INSERT INTO group_members (group_id, user_id, role, joined_at) 
                     VALUES (?, ?, ?, ?)""",
                  (group_id, created_by, 'admin', datetime.now()))
        conn.commit()
        conn.close()
        return group_id
    
    def add_member(self, group_id: int, user_id: int, role: str = 'member') -> bool:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute("""INSERT INTO group_members (group_id, user_id, role, joined_at) 
                         VALUES (?, ?, ?, ?)""",
                      (group_id, user_id, role, datetime.now()))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_user_groups(self, user_id: int) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""SELECT g.id, g.name, g.description, g.avatar, gm.role 
                     FROM groups g 
                     JOIN group_members gm ON g.id = gm.group_id 
                     WHERE gm.user_id = ? AND g.is_active = 1""", (user_id,))
        groups = c.fetchall()
        conn.close()
        
        return [{
            "id": g[0],
            "name": g[1],
            "description": g[2],
            "avatar": g[3],
            "role": g[4]
        } for g in groups]
    
    def get_group_members(self, group_id: int) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""SELECT u.user_id, u.username, u.full_name, gm.role, gm.joined_at 
                     FROM group_members gm 
                     JOIN users u ON gm.user_id = u.user_id 
                     WHERE gm.group_id = ?""", (group_id,))
        members = c.fetchall()
        conn.close()
        
        return [{
            "user_id": m[0],
            "username": m[1],
            "full_name": m[2],
            "role": m[3],
            "joined_at": m[4]
        } for m in members]
