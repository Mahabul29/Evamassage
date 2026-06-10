from datetime import datetime
from config import messages, chats, users


def _coerce_id(val):
    """Normalise user_ids to int everywhere. Accepts int or numeric string."""
    try:
        return int(val)
    except (ValueError, TypeError):
        return val


def send_private_message(from_id, to_id, text):
    if not text or not text.strip():
        return False

    from_id = _coerce_id(from_id)
    to_id   = _coerce_id(to_id)

    messages.insert_one({
        'from_id':    from_id,
        'to_id':      to_id,
        'message':    text.strip(),
        'file_url':   None,
        'file_name':  None,
        'file_type':  None,
        'file_size':  None,
        'created_at': datetime.now(),
        'read':       False          # ← NEW: track unread state
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
    """Returns messages with file_url, file_name, file_type, file_size
    so the frontend can render image/audio/file bubbles correctly."""
    user1_id = _coerce_id(user1_id)
    user2_id = _coerce_id(user2_id)
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


def get_unread_count(user_id):
    """Count all unread messages for a given user."""
    user_id = _coerce_id(user_id)
    return messages.count_documents({
        'to_id': user_id,
        'read':  False
    })


def mark_messages_read(from_id, to_id):
    """Mark all messages from from_id → to_id as read."""
    from_id = _coerce_id(from_id)
    to_id   = _coerce_id(to_id)
    messages.update_many(
        {'from_id': from_id, 'to_id': to_id, 'read': False},
        {'$set': {'read': True}}
    )


def get_chat_list(user_id):
    user_id = _coerce_id(user_id)

    chat_list = list(chats.find({
        '$or': [{'user1_id': user_id}, {'user2_id': user_id}]
    }).sort('last_message_time', -1))

    # FALLBACK: chats collection empty — rebuild from messages on the fly
    if not chat_list:
        seen = {}
        all_msgs = messages.find({
            '$or': [{'from_id': user_id}, {'to_id': user_id}]
        }).sort('created_at', -1)
        for m in all_msgs:
            fid = _coerce_id(m.get('from_id'))
            tid = _coerce_id(m.get('to_id'))
            u1, u2 = sorted([fid, tid])
            key = (u1, u2)
            if key not in seen:
                seen[key] = m
                chat_list.append({
                    'user1_id': u1,
                    'user2_id': u2,
                    'last_message': m.get('message', ''),
                    'last_message_time': m.get('created_at')
                })
                # Repair chats collection so next load is fast
                chats.update_one(
                    {'user1_id': u1, 'user2_id': u2},
                    {'$set': {'last_message': m.get('message', ''), 'last_message_time': m.get('created_at')}},
                    upsert=True
                )

    result = []
    for chat in chat_list:
        u1 = _coerce_id(chat.get('user1_id'))
        u2 = _coerce_id(chat.get('user2_id'))
        other_id = u2 if u1 == user_id else u1
        user = users.find_one({'user_id': other_id})
        if user:
            # Count unread from this specific user
            unread = messages.count_documents({
                'from_id': other_id,
                'to_id':   user_id,
                'read':    False
            })
            result.append({
                'user_id':      other_id,
                'username':     user.get('username', ''),
                'full_name':    user.get('full_name', user.get('username', '')),
                'last_message': chat.get('last_message', ''),
                'avatar':       user.get('avatar', 'default'),
                'unread_count': unread   # ← NEW: per-chat badge count
            })
    return result
    
