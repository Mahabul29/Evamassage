# ... all your existing routes above ...

# ── TEMPORARY DEBUG ──
@app.route('/debug')
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
    from datetime import datetime
    def fix(o):
        if isinstance(o, datetime): return str(o)
        if isinstance(o, dict): return {k: fix(v) for k, v in o.items()}
        if isinstance(o, list): return [fix(i) for i in o]
        return o
    result = {
        "session_user_id": uid,
        "session_user_id_type": type(uid).__name__,
        "my_user_record": fix(me),
        "all_chats_sample": fix(all_chats),
        "my_chats": fix(my_chats),
        "my_messages_sample": fix(my_msgs),
        "chats_count": db['chats'].count_documents({}),
        "messages_count": db['messages'].count_documents({}),
    }
    return f"<pre>{json.dumps(result, indent=2)}</pre>"


# ↓ These are the LAST 3 lines — paste ABOVE here ↓
if __name__ == '__main__':
    print(f"🚀 Server running on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
