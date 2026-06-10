from bson.objectid import ObjectId
from datetime import datetime, timedelta
from config import db

channel_members = db['channel_members']
channels        = db['channels']
channel_messages= db['channel_messages']


def _oid(channel_id):
    try:
        return ObjectId(channel_id)
    except Exception:
        return None


def get_channel_detail(channel_id, user_id):
    oid = _oid(channel_id)
    if not oid:
        return None, "Invalid channel ID"
    channel = channels.find_one({'_id': oid})
    if not channel:
        return None, "Channel not found"
    member = channel_members.find_one({'channel_id': oid, 'user_id': user_id})
    if not member:
        return None, "Not a member"
    member_count = channel_members.count_documents({'channel_id': oid})
    return {
        'id':           str(channel['_id']),
        'name':         channel.get('name', ''),
        'username':     channel.get('username', ''),
        'description':  channel.get('description', ''),
        'is_public':    channel.get('is_public', False),
        'member_count': member_count,
        'role':         member.get('role', 'member'),
        'auto_delete':  channel.get('auto_delete', 'never'),
        'created_at':   str(channel.get('created_at', ''))
    }, None


def search_public_channels(query):
    if not query or len(query) < 2:
        return []
    regex = {'$regex': query, '$options': 'i'}
    results = channels.find({
        'is_public': True,
        '$or': [{'name': regex}, {'description': regex}]
    }).limit(20)
    out = []
    for ch in results:
        out.append({
            'id':          str(ch['_id']),
            'name':        ch.get('name', ''),
            'username':    ch.get('username', ''),
            'description': ch.get('description', ''),
            'member_count': channel_members.count_documents({'channel_id': ch['_id']})
        })
    return out


def update_channel(channel_id, user_id, **data):
    oid = _oid(channel_id)
    if not oid:
        return False, "Invalid channel ID"
    member = channel_members.find_one({'channel_id': oid, 'user_id': user_id, 'role': 'admin'})
    if not member:
        return False, "Admin access required"
    upd = {}
    if 'name' in data and data['name']:
        upd['name'] = data['name'].strip()
    if 'description' in data:
        upd['description'] = data['description'].strip()
    if 'is_public' in data:
        upd['is_public'] = bool(data['is_public'])
    if 'auto_delete' in data:
        upd['auto_delete'] = data['auto_delete']
    if upd:
        channels.update_one({'_id': oid}, {'$set': upd})
    return True, "Updated successfully"


def delete_channel(channel_id, user_id, hard=False):
    oid = _oid(channel_id)
    if not oid:
        return False, "Invalid channel ID"
    member = channel_members.find_one({'channel_id': oid, 'user_id': user_id, 'role': 'admin'})
    if not member:
        return False, "Admin access required"
    if hard:
        channel_messages.delete_many({'channel_id': oid})
        channel_members.delete_many({'channel_id': oid})
        channels.delete_one({'_id': oid})
    else:
        channels.update_one({'_id': oid}, {'$set': {'is_active': False}})
    return True, "Channel deleted"


def leave_channel(channel_id, user_id):
    oid = _oid(channel_id)
    if not oid:
        return False, "Invalid channel ID"
    result = channel_members.delete_one({'channel_id': oid, 'user_id': user_id})
    if result.deleted_count == 0:
        return False, "Not a member"
    return True, "Left channel"


def apply_auto_delete(channel_id):
    oid = _oid(channel_id)
    if not oid:
        return 0
    channel = channels.find_one({'_id': oid})
    if not channel:
        return 0
    setting = channel.get('auto_delete', 'never')
    if setting == 'never':
        return 0
    days_map = {'1day': 1, '2days': 2, '3days': 3, '7days': 7}
    days = days_map.get(setting)
    if not days:
        return 0
    cutoff = datetime.now() - timedelta(days=days)
    result = channel_messages.delete_many({
        'channel_id': oid,
        'created_at': {'$lt': cutoff}
    })
    return result.deleted_count
    
