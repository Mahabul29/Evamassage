from datetime import datetime
from bson.objectid import ObjectId
from config import channels, channel_members, channel_msgs, users
import re


# ── helpers ──────────────────────────────────────────────────────────────────

def _slugify(name):
    """Turn a channel name into a safe lowercase username."""
    slug = re.sub(r'[^a-z0-9_]', lambda m: '_' if m.group() == ' ' else '', name.lower())
    return slug[:30] or 'channel'


# ── create ────────────────────────────────────────────────────────────────────

def create_channel(name, created_by, description="", is_public=False, username=None):
    if len(name) < 2:
        return None, "Name too short"

    if channels.find_one({'name': name}):
        return None, "Channel name already exists"

    # resolve username
    if is_public:
        uname = (username or _slugify(name)).lower().strip()
        uname = re.sub(r'[^a-z0-9_]', '', uname)[:30]
        if not uname:
            uname = _slugify(name)
        if channels.find_one({'username': uname}):
            return None, f"Username @{uname} is already taken"
    else:
        uname = None

    channel = {
        'name':        name,
        'description': description,
        'created_by':  created_by,
        'created_at':  datetime.now(),
        'is_active':   True,
        'is_public':   is_public,
        'username':    uname,
    }
    result = channels.insert_one(channel)
    channel_id = result.inserted_id

    channel_members.insert_one({
        'channel_id': channel_id,
        'user_id':    created_by,
        'role':       'admin',
        'joined_at':  datetime.now(),
    })

    return str(channel_id), "Success", uname


# ── read ──────────────────────────────────────────────────────────────────────

def get_user_channels(user_id):
    members = channel_members.find({'user_id': user_id})
    result = []
    for member in members:
        channel = channels.find_one({'_id': member['channel_id']})
        if channel:
            count = channel_members.count_documents({'channel_id': channel['_id']})
            result.append({
                'id':           str(channel['_id']),
                'name':         channel['name'],
                'description':  channel.get('description', ''),
                'member_count': count,
                'role':         member.get('role', 'member'),
                'is_public':    channel.get('is_public', False),
                'username':     channel.get('username') or '',
            })
    return result


# ── send text message ─────────────────────────────────────────────────────────

def send_channel_message(channel_id, from_id, message):
    try:
        oid = ObjectId(channel_id)
    except Exception:
        return False, "Invalid channel"

    if not channel_members.find_one({'channel_id': oid, 'user_id': from_id}):
        return False, "Not a member"

    if not message or not message.strip():
        return False, "Empty message"

    channel_msgs.insert_one({
        'channel_id': oid,
        'from_id':    from_id,
        'message':    message.strip(),
        'msg_type':   'text',
        'file_url':   None,
        'file_name':  None,
        'file_type':  None,
        'file_size':  None,
        'created_at': datetime.now(),
    })
    return True, "Sent"


# ── send file / photo / voice message ────────────────────────────────────────

def send_channel_file(channel_id, from_id, file_url, file_name, file_type,
                      file_size=None, msg_type='file'):
    """
    msg_type: 'photo' | 'file' | 'voice'
    """
    try:
        oid = ObjectId(channel_id)
    except Exception:
        return False, "Invalid channel"

    if not channel_members.find_one({'channel_id': oid, 'user_id': from_id}):
        return False, "Not a member"

    if not file_url:
        return False, "No file URL"

    channel_msgs.insert_one({
        'channel_id': oid,
        'from_id':    from_id,
        'message':    '',
        'msg_type':   msg_type,
        'file_url':   file_url,
        'file_name':  file_name,
        'file_type':  file_type,
        'file_size':  file_size,
        'created_at': datetime.now(),
    })
    return True, "Sent"


# ── read messages ─────────────────────────────────────────────────────────────

def get_channel_messages(channel_id, user_id, limit=100):
    try:
        oid = ObjectId(channel_id)
    except Exception:
        return []

    if not channel_members.find_one({'channel_id': oid, 'user_id': user_id}):
        return []

    msgs = channel_msgs.find({'channel_id': oid}).sort('created_at', 1).limit(limit)
    result = []
    for msg in msgs:
        sender = users.find_one({'user_id': msg['from_id']})
        sender_name = (
            sender.get('full_name', sender.get('username', 'Unknown'))
            if sender else 'Unknown'
        )
        created = msg.get('created_at')
        created_str = created.isoformat() if hasattr(created, 'isoformat') else (str(created) if created else '')

        result.append({
            'id':        str(msg['_id']),
            'from_id':   msg['from_id'],
            'from_name': sender_name,
            'message':   msg.get('message', ''),
            'msg_type':  msg.get('msg_type', 'text'),
            'file_url':  msg.get('file_url'),
            'file_name': msg.get('file_name'),
            'file_type': msg.get('file_type'),
            'file_size': msg.get('file_size'),
            'created_at': created_str,
        })
    return result


# ── join by ObjectId ──────────────────────────────────────────────────────────

def join_channel(channel_id, user_id):
    try:
        oid = ObjectId(channel_id)
    except Exception:
        return False, "Invalid channel"

    channel = channels.find_one({'_id': oid, 'is_active': True})
    if not channel:
        return False, "Channel not found"

    if channel_members.find_one({'channel_id': oid, 'user_id': user_id}):
        return True, "Already a member"

    channel_members.insert_one({
        'channel_id': oid,
        'user_id':    user_id,
        'role':       'member',
        'joined_at':  datetime.now(),
    })
    return True, "Joined"


# ── join by public username ───────────────────────────────────────────────────

def join_channel_by_username(username, user_id):
    """Find a public channel by @username and add the user as member."""
    uname = username.lstrip('@').lower().strip()
    channel = channels.find_one({'username': uname, 'is_public': True, 'is_active': True})
    if not channel:
        return False, "Channel not found", None

    oid = channel['_id']
    if channel_members.find_one({'channel_id': oid, 'user_id': user_id}):
        return True, "Already a member", channel

    channel_members.insert_one({
        'channel_id': oid,
        'user_id':    user_id,
        'role':       'member',
        'joined_at':  datetime.now(),
    })
    return True, "Joined", channel
        
