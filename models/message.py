from datetime import datetime
from config import messages, chats, users

def send_private_message(from_id, to_id, text):
    if not text.strip():
        return False
    
    messages.insert_one({
        'from_id': from_id,
        'to_id': to_id,
        'message': text.strip(),
        'created_at': datetime.now()
    })
    
    # Update chat list
    u1, u2 = sorted([from_id, to_id])
    chats.update_one(
        {'user1_id': u1, 'user2_id': u2},
        {'$set': {
            'last_message': text.strip(),
            'last_message_time': datetime.now()
        }},
        upsert=True
    )
    return True

def get_private_messages(user1_id, user2_id, limit=100):
    msgs = messages.find({
        '$or': [
            {'from_id': user1_id, 'to_id': user2_id},
            {'from_id': user2_id, 'to_id': user1_id}
        ]
    }).sort('created_at', 1).limit(limit)
    
    return [{
        'from_id': m['from_id'],
        'message': m['message'],
        'created_at': m['created_at']
    } for m in msgs]

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
                'user_id': other_id,
                'full_name': user.get('full_name', user['username']),
                'last_message': chat.get('last_message', '')
            })
    return result
