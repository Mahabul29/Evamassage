# debug_route.py - safe standalone version
# This is registered as a blueprint, NOT pasted into app.py

from flask import Blueprint, session, jsonify
from config import db
from datetime import datetime

debug_bp = Blueprint('debug', __name__)

def fix_types(o):
    if isinstance(o, datetime): return str(o)
    if isinstance(o, dict): return {k: fix_types(v) for k, v in o.items()}
    if isinstance(o, list): return [fix_types(i) for i in o]
    return o

@debug_bp.route('/debug')
def debug():
    if 'user_id' not in session:
        return "Not logged in", 401

    uid = session['user_id']

    all_chats = list(db['chats'].find({}, {'_id': 0}).limit(10))
    my_chats = list(db['chats'].find({
        '$or': [{'user1_id': uid}, {'user2_id': uid}]
    }, {'_id': 0}).limit(10))
    my_msgs = list(db['messages'].find({
        '$or': [{'from_id': uid}, {'to_id': uid}]
    }, {'_id': 0}).limit(5))
    me = db['users'].find_one({'user_id': uid}, {'_id': 0, 'password': 0})

    import json
    result = {
        "session_user_id": uid,
        "session_user_id_type": type(uid).__name__,
        "my_user_record": fix_types(me),
        "all_chats_sample": fix_types(all_chats),
        "my_chats": fix_types(my_chats),
        "my_messages_sample": fix_types(my_msgs),
        "chats_count": db['chats'].count_documents({}),
        "messages_count": db['messages'].count_documents({}),
    }
    return f"<pre>{json.dumps(result, indent=2)}</pre>"
    
