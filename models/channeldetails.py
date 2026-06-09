from datetime import datetime, timedelta
from bson.objectid import ObjectId
from config import channels, channel_members, channel_msgs, users
import re


# ═══════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _slugify(name):
    """Turn a channel name into a safe lowercase username."""
    slug = re.sub(r'[^a-z0-9_]', lambda m: '_' if m.group() == ' ' else '', name.lower())
    return slug[:30] or 'channel'


def _serialize_channel(channel, member_doc=None):
    """Convert a MongoDB channel doc into a clean API-ready dict."""
    cid = str(channel['_id'])
    count = channel_members.count_documents({'channel_id': channel['_id']})
    return {
        'id':          cid,
        'name':        channel.get('name', ''),
        'description': channel.get('description', ''),
        'username':    channel.get('username') or '',
        'is_public':   channel.get('is_public', False),
        'is_active':   channel.get('is_active', True),
        'created_by':  channel.get('created_by'),
        'created_at':  channel.get('created_at').isoformat() if hasattr(channel.get('created_at'), 'isoformat') else str(channel.get('created_at', '')),
        'member_count': count,
        'role':        member_doc.get('role', 'member') if member_doc else 'member',
        'auto_delete': channel.get('auto_delete', None),   # minutes or None
    }


def _get_user_name(user_id):
    """Fetch display name for a user_id."""
    u = users.find_one({'user_id': user_id})
    if not u:
        return 'Unknown'
    return u.get('full_name') or u.get('username') or 'Unknown'


def _can_manage(channel_id, user_id):
    """Return True if user is admin or creator of the channel."""
    member = channel_members.find_one({
        'channel_id': ObjectId(channel_id),
        'user_id':    user_id
    })
    if not member:
        return False
    if member.get('role') == 'admin':
        return True
    # Also allow the original creator
    ch = channels.find_one({'_id': ObjectId(channel_id)})
    return ch and ch.get('created_by') == user_id


# ═══════════════════════════════════════════════════════════════════════════
#  CREATE
# ═══════════════════════════════════════════════════════════════════════════

def create_channel(name, created_by, description="", is_public=False, username=None):
    if len(name) < 2:
        return None, "Name too short (min 2 chars)"

    if channels.find_one({'name': name, 'is_active': True}):
        return None, "Channel name already exists"

    # Resolve public username
    if is_public:
        uname = (username or _slugify(name)).lower().strip()
        uname = re.sub(r'[^a-z0-9_]', '', uname)[:30]
        if not uname:
            uname = _slugify(name)
        if channels.find_one({'username': uname, 'is_active': True}):
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
        'auto_delete': None,          # disabled by default
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


# ═══════════════════════════════════════════════════════════════════════════
#  READ  (list + detail)
# ═══════════════════════════════════════════════════════════════════════════

def get_user_channels(user_id):
    """All channels the user is a member of."""
    members = channel_members.find({'user_id': user_id})
    result = []
    for member in members:
        channel = channels.find_one({'_id': member['channel_id'], 'is_active': True})
        if channel:
            result.append(_serialize_channel(channel, member))
    return result


def get_channel_detail(channel_id, user_id):
    """Full profile view of a single channel."""
    try:
        oid = ObjectId(channel_id)
    except Exception:
        return None, "Invalid channel ID"

    channel = channels.find_one({'_id': oid, 'is_active': True})
    if not channel:
        return None, "Channel not found"

    # Must be member (or public — you can relax this if you want public preview)
    if not channel.get('is_public') and not channel_members.find_one({'channel_id': oid, 'user_id': user_id}):
        return None, "Private channel — members only"

    detail = _serialize_channel(channel)

    # Member list
    members_cursor = channel_members.find({'channel_id': oid})
    detail['members'] = []
    for m in members_cursor:
        detail['members'].append({
            'user_id':   m['user_id'],
            'name':      _get_user_name(m['user_id']),
            'role':      m.get('role', 'member'),
            'joined_at': m.get('joined_at').isoformat() if hasattr(m.get('joined_at'), 'isoformat') else str(m.get('joined_at', '')),
        })

    # Can the viewer manage this channel?
    detail['can_manage'] = _can_manage(channel_id, user_id)

    return detail, None


def search_public_channels(query):
    """Search public channels by name or username (for discovery)."""
    q = query.lower().strip()
    if len(q) < 2:
        return []
    regex = re.compile(q, re.IGNORECASE)
    found = channels.find({
        'is_active': True,
        'is_public': True,
        '$or': [
            {'name': regex},
            {'username': regex},
        ]
    }).limit(20)
    return [_serialize_channel(ch) for ch in found]


# ═══════════════════════════════════════════════════════════════════════════
#  UPDATE  (settings)
# ═══════════════════════════════════════════════════════════════════════════

def update_channel(channel_id, user_id, **fields):
    """
    Update channel settings. Allowed fields:
      - name
      - description
      - username  (public only)
      - is_public
      - auto_delete  (int minutes, or None/0 to disable)
    """
    if not _can_manage(channel_id, user_id):
        return False, "Only admins can update channel settings"

    try:
        oid = ObjectId(channel_id)
    except Exception:
        return False, "Invalid channel ID"

    channel = channels.find_one({'_id': oid})
    if not channel:
        return False, "Channel not found"

    updates = {}

    if 'name' in fields:
        new_name = fields['name'].strip()
        if len(new_name) < 2:
            return False, "Name too short"
        # ensure uniqueness
        existing = channels.find_one({'name': new_name, 'is_active': True, '_id': {'$ne': oid}})
        if existing:
            return False, "Channel name already taken"
        updates['name'] = new_name

    if 'description' in fields:
        updates['description'] = fields['description'].strip()

    if 'is_public' in fields:
        updates['is_public'] = bool(fields['is_public'])
        # If switching to private, clear username
        if not updates['is_public']:
            updates['username'] = None

    if 'username' in fields and (channel.get('is_public') or updates.get('is_public')):
        uname = fields['username'].lower().strip()
        uname = re.sub(r'[^a-z0-9_]', '', uname)[:30]
        if uname:
            existing = channels.find_one({'username': uname, 'is_active': True, '_id': {'$ne': oid}})
            if existing:
                return False, f"Username @{uname} is already taken"
            updates['username'] = uname

    if 'auto_delete' in fields:
        val = fields['auto_delete']
        if val is None or val == 0 or val == '':
            updates['auto_delete'] = None
        else:
            try:
                minutes = int(val)
                if minutes < 1:
                    return False, "Auto-delete must be at least 1 minute"
                updates['auto_delete'] = minutes
            except (ValueError, TypeError):
                return False, "Auto-delete must be a number (minutes)"

    if updates:
        channels.update_one({'_id': oid}, {'$set': updates})

    return True, "Updated"


# ═══════════════════════════════════════════════════════════════════════════
#  DELETE  (soft + hard)
# ═══════════════════════════════════════════════════════════════════════════

def delete_channel(channel_id, user_id, hard=False):
    """
    Soft-delete (mark inactive) by default.
    Only the creator or an admin can delete.
    """
    if not _can_manage(channel_id, user_id):
        return False, "Only admins can delete this channel"

    try:
        oid = ObjectId(channel_id)
    except Exception:
        return False, "Invalid channel ID"

    if hard:
        # Permanent wipe
        channels.delete_one({'_id': oid})
        channel_members.delete_many({'channel_id': oid})
        channel_msgs.delete_many({'channel_id': oid})
        return True, "Channel permanently deleted"
    else:
        # Soft delete
        channels.update_one({'_id': oid}, {'$set': {'is_active': False, 'deleted_at': datetime.now()}})
        return True, "Channel deleted"


def leave_channel(channel_id, user_id):
    """A member can leave (admin can leave too; if last admin, channel auto-deletes)."""
    try:
        oid = ObjectId(channel_id)
    except Exception:
        return False, "Invalid channel ID"

    member = channel_members.find_one({'channel_id': oid, 'user_id': user_id})
    if not member:
        return False, "Not a member"

    channel_members.delete_one({'channel_id': oid, 'user_id': user_id})

    # If no admins left, soft-delete the channel
    remaining_admins = channel_members.find_one({'channel_id': oid, 'role': 'admin'})
    if not remaining_admins:
        channels.update_one({'_id': oid}, {'$set': {'is_active': False, 'deleted_at': datetime.now()}})
        return True, "You left — channel was deleted (no admins left)"

    return True, "Left channel"


# ═══════════════════════════════════════════════════════════════════════════
#  AUTO-DELETE  (message cleanup)
# ═══════════════════════════════════════════════════════════════════════════

def apply_auto_delete(channel_id):
    """
    Call this periodically (e.g. via a cron job or before fetching messages)
    to wipe messages older than the channel's auto_delete setting.
    """
    try:
        oid = ObjectId(channel_id)
    except Exception:
        return 0

    channel = channels.find_one({'_id': oid})
    if not channel:
        return 0

    minutes = channel.get('auto_delete')
    if not minutes:
        return 0

    cutoff = datetime.now() - timedelta(minutes=minutes)
    result = channel_msgs.delete_many({
        'channel_id': oid,
        'created_at': {'$lt': cutoff}
    })
    return result.deleted_count


def get_channel_messages(channel_id, user_id, limit=100):
    """Fetch messages — auto-delete is applied first."""
    try:
        oid = ObjectId(channel_id)
    except Exception:
        return []

    if not channel_members.find_one({'channel_id': oid, 'user_id': user_id}):
        return []

    # Enforce auto-delete before returning
    apply_auto_delete(channel_id)

    msgs = channel_msgs.find({'channel_id': oid}).sort('created_at', 1).limit(limit)
    result = []
    for msg in msgs:
        sender = users.find_one({'user_id': msg['from_id']})
        sender_name = sender.get('full_name') or sender.get('username', 'Unknown') if sender else 'Unknown'
        created = msg.get('created_at')
        created_str = created.isoformat() if hasattr(created, 'isoformat') else (str(created) if created else '')

        result.append({
            'id':         str(msg['_id']),
            'from_id':    msg['from_id'],
            'from_name':  sender_name,
            'message':    msg.get('message', ''),
            'msg_type':   msg.get('msg_type', 'text'),
            'file_url':   msg.get('file_url'),
            'file_name':  msg.get('file_name'),
            'file_type':  msg.get('file_type'),
            'file_size':  msg.get('file_size'),
            'created_at': created_str,
        })
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  JOIN  (by ID or by public username)
# ═══════════════════════════════════════════════════════════════════════════

def join_channel_by_id(channel_id, user_id):
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


def join_channel_by_username(username, user_id):
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


# ═══════════════════════════════════════════════════════════════════════════
#  MESSAGES  (send text / file / voice)
# ═══════════════════════════════════════════════════════════════════════════

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


def send_channel_file(channel_id, from_id, file_url, file_name, file_type,
                      file_size=None, msg_type='file'):
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
