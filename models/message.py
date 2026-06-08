from datetime import datetime
from config import messages, chats, users

def send_private_message(from_id, to_id, text):
    if not text or not text.strip():
        return False

    messages.insert_one({
        'from_id':    from_id,
        'to_id':      to_id,
        'message':    text.strip(),
        'file_url':   None,
        'file_name':  None,
        'file_type':  None,
        'file_size':  None,
        'created_at': datetime.now()
    })

    # Update chat list
    u1, u2 = sorted([from_id, to_id])
    chats.update_one(
        {'user1_id': u1, 'user2_id': u2},
        {'$set': {
            'last_message':      text.strip(),
            'last_message_time': datetime.now()
        }},
        upsert=True
    )
    return True


def get_private_messages(user1_id, user2_id, limit=100):
    """FIX: now returns file_url, file_name, file_type, file_size
    so the frontend can render image/audio/file bubbles correctly."""
    msgs = messages.find({
        '$or': [
            {'from_id': user1_id, 'to_id': user2_id},
            {'from_id': user2_id, 'to_id': user1_id}
        ]
    }).sort('created_at', 1).limit(limit)

    result = []
    for m in msgs:
        created = m.get('created_at')
        if hasattr(created, 'isoformat'):
            created_str = created.isoformat()
        else:
            created_str = str(created) if created else ''

        result.append({
            'from_id':    m.get('from_id'),
            'to_id':      m.get('to_id'),
            'message':    m.get('message', ''),
            'file_url':   m.get('file_url'),
            'file_name':  m.get('file_name'),
            'file_type':  m.get('file_type'),
            'file_size':  m.get('file_size'),
            'created_at': created_str
        })
    return result


def get_chat_list(user_id):
    chat_list = chats.find({
        '$or': [{'user1_id': user_id}, {'user2_id': user_id}]
    }).sort('last_message_time', -1)

    result = []
    for chat in chat_list:
        other_id = chat['user2_id'] if chat['user1_id'] == user_id else chat['user1_id']
        user = users.find_one({'user_id': other_id})
        if user:
            result.append({
                'user_id':      other_id,
                'full_name':    user.get('full_name', user.get('username', '')),
                'last_message': chat.get('last_message', '')
            })
    return result
    
