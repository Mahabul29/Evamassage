from datetime import datetime
from bson.objectid import ObjectId
from config import channels, channel_members, channel_msgs, users

def create_channel(name, created_by, description=""):
    if len(name) < 2:
        return None, "Name too short"
    
    if channels.find_one({'name': name}):
        return None, "Name exists"
    
    channel = {
        'name': name,
        'description': description,
        'created_by': created_by,
        'created_at': datetime.now(),
        'is_active': True
    }
    result = channels.insert_one(channel)
    channel_id = result.inserted_id
    
    # Add creator as member
    channel_members.insert_one({
        'channel_id': channel_id,
        'user_id': created_by,
        'role': 'admin',
        'joined_at': datetime.now()
    })
    
    return str(channel_id), "Success"

def get_user_channels(user_id):
    members = channel_members.find({'user_id': user_id})
    result = []
    
    for member in members:
        channel = channels.find_one({'_id': member['channel_id']})
        if channel:
            count = channel_members.count_documents({'channel_id': channel['_id']})
            result.append({
                'id': str(channel['_id']),
                'name': channel['name'],
                'description': channel.get('description', ''),
                'member_count': count,
                'role': member.get('role', 'member')
            })
    return result

def send_channel_message(channel_id, from_id, message):
    try:
        oid = ObjectId(channel_id)
    except:
        return False, "Invalid channel"
    
    # Check membership
    is_member = channel_members.find_one({'channel_id': oid, 'user_id': from_id})
    if not is_member:
        return False, "Not a member"
    
    if not message.strip():
        return False, "Empty message"
    
    channel_msgs.insert_one({
        'channel_id': oid,
        'from_id': from_id,
        'message': message.strip(),
        'created_at': datetime.now()
    })
    return True, "Sent"

def get_channel_messages(channel_id, user_id, limit=100):
    try:
        oid = ObjectId(channel_id)
    except:
        return []
    
    # Check membership
    is_member = channel_members.find_one({'channel_id': oid, 'user_id': user_id})
    if not is_member:
        return []
    
    msgs = channel_msgs.find({'channel_id': oid}).sort('created_at', 1).limit(limit)
    
    result = []
    for msg in msgs:
        sender = users.find_one({'user_id': msg['from_id']})
        sender_name = sender.get('full_name', sender.get('username', 'Unknown')) if sender else 'Unknown'
        
        result.append({
            'from_id': msg['from_id'],
            'from_name': sender_name,
            'message': msg['message'],
            'created_at': msg['created_at']
        })
    return result

def join_channel(channel_id, user_id):
    try:
        oid = ObjectId(channel_id)
    except:
        return False, "Invalid channel"
    
    channel = channels.find_one({'_id': oid, 'is_active': True})
    if not channel:
        return False, "Channel not found"
    
    existing = channel_members.find_one({'channel_id': oid, 'user_id': user_id})
    if existing:
        return False, "Already a member"
    
    channel_members.insert_one({
        'channel_id': oid,
        'user_id': user_id,
        'role': 'member',
        'joined_at': datetime.now()
    })
    return True, "Joined"
