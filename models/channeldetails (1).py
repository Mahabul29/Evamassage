from datetime import datetime, timedelta
from bson.objectid import ObjectId
from config import db
import re

# Collection references
channels       = db.channels
channel_members = db.channel_members
channel_msgs    = db.channel_messages
users          = db.users


def _slugify(name):
    slug = re.sub(r'[^a-z0-9_]', lambda m: '_' if m.group() == ' ' else '', name.lower())
    return slug[:30] or 'channel'


def _serialize_channel(channel, member_doc=None):
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
        'auto_delete': channel.get('auto_delete', None),
    }


def _get_user_name(user_id):
    u = users.find_one({'user_id': user_id})
    if not u:
        return 'Unknown'
    return u.get('full_name') or u.get('username') or 'Unknown'


def _can_manage(channel_id, user_id):
    member = channel_members.find_one({
        'channel_id': ObjectId(channel_id),
        'user_id':    user_id
    })
    if not member:
        return False
    if member.get('role') == 'admin':
        return True
    ch = channels.find_one({'_id': ObjectId(channel_id)})
    return ch and ch.get('created_by') == user_id


def get_channel_detail(channel_id, user_id):
    try:
        oid = ObjectId(channel_id)
    except Exception:
        return None, "Invalid channel ID"

    channel = channels.find_one({'_id': oid, 'is_active': True})
    if not channel:
        return None, "Channel not found"

    if not channel.get('is_public') and not channel_members.find_one({'channel_id': oid, 'user_id': user_id}):
        return None, "Private channel"

    detail = _serialize_channel(channel)

    members_cursor = channel_members.find({'channel_id': oid})
    detail['members'] = []
    for m in members_cursor:
        detail['members'].append({
            'user_id':   m['user_id'],
            'name':      _get_user_name(m['user_id']),
            'role':      m.get('role', 'member'),
            'joined_at': m.get('joined_at').isoformat() if hasattr(m.get('joined_at'), 'isoformat') else str(m.get('joined_at', '')),
        })

    detail['can_manage'] = _can_manage(channel_id, user_id)
    return detail, None


def search_public_channels(query):
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


def update_channel(channel_id, user_id, **fields):
    if not _can_manage(channel_id, user_id):
        return False, "Only admins can update"

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
        existing = channels.find_one({'name': new_name, 'is_active': True, '_id': {'$ne': oid}})
        if existing:
            return False, "Name already taken"
        updates['name'] = new_name

    if 'description' in fields:
        updates['description'] = fields['description'].strip()

    if 'is_public' in fields:
        updates['is_public'] = bool(fields['is_public'])
        if not updates['is_public']:
            updates['username'] = None

    if 'username' in fields and (channel.get('is_public') or updates.get('is_public')):
        uname = fields['username'].lower().strip()
        uname = re.sub(r'[^a-z0-9_]', '', uname)[:30]
        if uname:
            existing = channels.find_one({'username': uname, 'is_active': True, '_id': {'$ne': oid}})
            if existing:
                return False, f"Username @{uname} taken"
            updates['username'] = uname

    if 'auto_delete' in fields:
        val = fields['auto_delete']
        if val is None or val == 0 or val == '':
            updates['auto_delete'] = None
        else:
            try:
                minutes = int(val)
                if minutes < 1:
                    return False, "Min 1 minute"
                updates['auto_delete'] = minutes
            except (ValueError, TypeError):
                return False, "Must be a number"

    if updates:
        channels.update_one({'_id': oid}, {'$set': updates})

    return True, "Updated"


def delete_channel(channel_id, user_id, hard=False):
    if not _can_manage(channel_id, user_id):
        return False, "Only admins can delete"

    try:
        oid = ObjectId(channel_id)
    except Exception:
        return False, "Invalid channel ID"

    if hard:
        channels.delete_one({'_id': oid})
        channel_members.delete_many({'channel_id': oid})
        channel_msgs.delete_many({'channel_id': oid})
        return True, "Permanently deleted"
    else:
        channels.update_one({'_id': oid}, {'$set': {'is_active': False, 'deleted_at': datetime.now()}})
        return True, "Deleted"


def leave_channel(channel_id, user_id):
    try:
        oid = ObjectId(channel_id)
    except Exception:
        return False, "Invalid channel ID"

    member = channel_members.find_one({'channel_id': oid, 'user_id': user_id})
    if not member:
        return False, "Not a member"

    channel_members.delete_one({'channel_id': oid, 'user_id': user_id})

    remaining_admins = channel_members.find_one({'channel_id': oid, 'role': 'admin'})
    if not remaining_admins:
        channels.update_one({'_id': oid}, {'$set': {'is_active': False, 'deleted_at': datetime.now()}})
        return True, "Left — channel deleted (no admins)"

    return True, "Left channel"


def apply_auto_delete(channel_id):
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
