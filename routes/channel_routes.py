from flask import Blueprint, request, jsonify, session
from datetime import datetime
from bson.objectid import ObjectId
from functools import wraps
from config import db  # FIX: use db directly from config

channel_bp = Blueprint('channel', __name__)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return decorated

@channel_bp.route('/api/channels', methods=['POST'])
@login_required
def create_channel():
    data = request.get_json()
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()

    if not name or len(name) < 2:
        return jsonify({"error": "Channel name must be at least 2 characters"}), 400

    existing = db['channels'].find_one({'name': name})
    if existing:
        return jsonify({"error": "Channel name already exists"}), 400

    channel = {
        'name': name,
        'description': description,
        'created_by': session['user_id'],
        'created_at': datetime.now(),
        'is_active': True
    }
    result = db['channels'].insert_one(channel)
    channel_id = result.inserted_id

    db['channel_members'].insert_one({
        'channel_id': channel_id,
        'user_id': session['user_id'],
        'role': 'admin',
        'joined_at': datetime.now()
    })

    return jsonify({"success": True, "id": str(channel_id), "name": name})

@channel_bp.route('/api/channels', methods=['GET'])
@login_required
def get_channels():
    members = db['channel_members'].find({'user_id': session['user_id']})
    result = []
    for member in members:
        channel = db['channels'].find_one({'_id': member['channel_id']})
        if channel:
            member_count = db['channel_members'].count_documents({'channel_id': channel['_id']})
            result.append({
                'id':           str(channel['_id']),
                'name':         channel['name'],
                'description':  channel.get('description', ''),
                'member_count': member_count,
                'role':         member.get('role', 'member')
            })
    return jsonify(result)

@channel_bp.route('/api/channels/<channel_id>/send', methods=['POST'])
@login_required
def send_channel_message(channel_id):
    try:
        oid = ObjectId(channel_id)
    except Exception:
        return jsonify({"error": "Invalid channel ID"}), 400

    is_member = db['channel_members'].find_one({'channel_id': oid, 'user_id': session['user_id']})
    if not is_member:
        return jsonify({"error": "You are not a member"}), 403

    data = request.get_json()
    message = data.get('message', '').strip()
    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400

    db['channel_messages'].insert_one({
        'channel_id': oid,
        'from_id':    session['user_id'],
        'message':    message,
        'created_at': datetime.now()
    })
    return jsonify({"success": True})

@channel_bp.route('/api/channels/<channel_id>/messages', methods=['GET'])
@login_required
def get_channel_messages(channel_id):
    try:
        oid = ObjectId(channel_id)
    except Exception:
        return jsonify([])

    is_member = db['channel_members'].find_one({'channel_id': oid, 'user_id': session['user_id']})
    if not is_member:
        return jsonify([])

    msgs = db['channel_messages'].find({'channel_id': oid}).sort('created_at', 1).limit(100)
    result = []
    for msg in msgs:
        user = db['users'].find_one({'user_id': msg['from_id']})
        sender_name = user.get('full_name', user.get('username', 'Unknown')) if user else 'Unknown'
        created = msg.get('created_at')
        result.append({
            'id':         str(msg['_id']),
            'from_id':    msg['from_id'],
            'from_name':  sender_name,
            'message':    msg.get('message', ''),
            'file_url':   msg.get('file_url'),
            'file_name':  msg.get('file_name'),
            'file_type':  msg.get('file_type'),
            'file_size':  msg.get('file_size'),
            'created_at': created.isoformat() if hasattr(created, 'isoformat') else str(created or '')
        })
    return jsonify(result)
        
