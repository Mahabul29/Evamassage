from flask import Blueprint, request, jsonify, session
from datetime import datetime
from bson.objectid import ObjectId
from functools import wraps

channel_bp = Blueprint('channel', __name__)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return decorated

def get_user_profile(user_id, db):
    user = db['users'].find_one({'user_id': user_id})
    if user:
        return {"full_name": user.get('full_name', user['username'])}
    return {"full_name": "Unknown"}

@channel_bp.route('/api/channels', methods=['GET'])
@login_required
def get_channels():
    db = request.db
    members = db['channel_members']
    channels = db['channels']
    
    user_channels = members.find({'user_id': session['user_id']})
    result = []
    for m in user_channels:
        ch = channels.find_one({'_id': m['channel_id']})
        if ch:
            count = members.count_documents({'channel_id': ch['_id']})
            result.append({
                'id': str(ch['_id']),
                'name': ch['name'],
                'description': ch.get('description', ''),
                'member_count': count,
                'role': m.get('role', 'member')
            })
    return jsonify(result)

@channel_bp.route('/api/channels', methods=['POST'])
@login_required
def create_channel():
    db = request.db
    data = request.json
    name = data.get('name', '').strip()
    desc = data.get('description', '')
    
    if len(name) < 3:
        return jsonify({"error": "Name too short"}), 400
    
    if db['channels'].find_one({'name': name}):
        return jsonify({"error": "Name exists"}), 400
    
    ch_id = db['channels'].insert_one({
        'name': name,
        'description': desc,
        'created_by': session['user_id'],
        'created_at': datetime.now(),
        'is_active': True
    }).inserted_id
    
    db['channel_members'].insert_one({
        'channel_id': ch_id,
        'user_id': session['user_id'],
        'role': 'admin',
        'joined_at': datetime.now()
    })
    
    return jsonify({"success": True, "id": str(ch_id), "name": name})

@channel_bp.route('/api/channels/<id>/join', methods=['POST'])
@login_required
def join_channel(id):
    db = request.db
    oid = ObjectId(id)
    
    ch = db['channels'].find_one({'_id': oid, 'is_active': True})
    if not ch:
        return jsonify({"error": "Not found"}), 404
    
    existing = db['channel_members'].find_one({'channel_id': oid, 'user_id': session['user_id']})
    if existing:
        return jsonify({"error": "Already member"}), 400
    
    db['channel_members'].insert_one({
        'channel_id': oid,
        'user_id': session['user_id'],
        'role': 'member',
        'joined_at': datetime.now()
    })
    
    return jsonify({"success": True})

@channel_bp.route('/api/channels/<id>/messages', methods=['GET'])
@login_required
def get_messages(id):
    db = request.db
    oid = ObjectId(id)
    
    is_member = db['channel_members'].find_one({'channel_id': oid, 'user_id': session['user_id']})
    if not is_member:
        return jsonify([]), 403
    
    msgs = db['channel_messages'].find({'channel_id': oid}).sort('created_at', 1).limit(100)
    result = []
    for m in msgs:
        sender = get_user_profile(m['from_id'], db)
        result.append({
            'id': str(m['_id']),
            'from_id': m['from_id'],
            'from_name': sender['full_name'],
            'message': m['message'],
            'created_at': m['created_at'].isoformat()
        })
    return jsonify(result)

@channel_bp.route('/api/channels/<id>/send', methods=['POST'])
@login_required
def send_message(id):
    db = request.db
    oid = ObjectId(id)
    
    data = request.json
    msg = data.get('message', '').strip()
    if not msg:
        return jsonify({"error": "Empty message"}), 400
    
    is_member = db['channel_members'].find_one({'channel_id': oid, 'user_id': session['user_id']})
    if not is_member:
        return jsonify({"error": "Not member"}), 403
    
    db['channel_messages'].insert_one({
        'channel_id': oid,
        'from_id': session['user_id'],
        'message': msg,
        'created_at': datetime.now()
    })
    
    return jsonify({"success": True})

@channel_bp.route('/api/channels/search')
@login_required
def search():
    db = request.db
    q = request.args.get('q', '').strip()
    
    query = {'is_active': True}
    if q:
        query['name'] = {'$regex': q, '$options': 'i'}
    
    results = db['channels'].find(query).limit(20)
    output = []
    for ch in results:
        is_member = db['channel_members'].find_one({'channel_id': ch['_id'], 'user_id': session['user_id']}) is not None
        output.append({
            'id': str(ch['_id']),
            'name': ch['name'],
            'description': ch.get('description', ''),
            'is_member': is_member
        })
    return jsonify(output)
