from flask import Blueprint, request, jsonify, session
from datetime import datetime
from bson.objectid import ObjectId
from functools import wraps
from config import db
import re, base64, os, uuid, mimetypes

channel_bp = Blueprint('channel', __name__)

UPLOAD_FOLDER = os.path.join('static', 'channel_uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return decorated

def make_username(name):
    """Convert channel name to a clean @username"""
    u = re.sub(r'[^a-zA-Z0-9_]', '', name.replace(' ', '_')).lower()
    return u[:30] or 'channel'

# ── CREATE CHANNEL ──
@channel_bp.route('/api/channels', methods=['POST'])
@login_required
def create_channel():
    data = request.get_json()
    name        = data.get('name', '').strip()
    description = data.get('description', '').strip()
    is_public   = bool(data.get('is_public', False))
    custom_uname = data.get('username', '').strip().lower()

    if not name or len(name) < 2:
        return jsonify({"error": "Channel name must be at least 2 characters"}), 400

    existing = db['channels'].find_one({'name': name})
    if existing:
        return jsonify({"error": "Channel name already exists"}), 400

    # Username: use custom if public & provided, else auto-generate
    if is_public and custom_uname:
        username = re.sub(r'[^a-z0-9_]', '', custom_uname)[:30] or make_username(name)
    else:
        username = make_username(name)

    # Ensure username uniqueness
    base = username; i = 1
    while db['channels'].find_one({'username': username}):
        username = f"{base}{i}"; i += 1

    channel = {
        'name':        name,
        'username':    username,
        'description': description,
        'is_public':   is_public,
        'created_by':  session['user_id'],
        'created_at':  datetime.now(),
        'is_active':   True
    }
    result = db['channels'].insert_one(channel)
    channel_id = result.inserted_id

    db['channel_members'].insert_one({
        'channel_id': channel_id,
        'user_id':    session['user_id'],
        'role':       'admin',
        'joined_at':  datetime.now()
    })

    return jsonify({"success": True, "id": str(channel_id), "name": name,
                    "username": username, "is_public": is_public})

# ── GET CHANNELS ──
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
                'username':     channel.get('username', make_username(channel['name'])),
                'description':  channel.get('description', ''),
                'is_public':    channel.get('is_public', False),
                'member_count': member_count,
                'role':         member.get('role', 'member')
            })
    return jsonify(result)

# ── CHANNEL INFO ──
@channel_bp.route('/api/channels/<channel_id>/info', methods=['GET'])
@login_required
def channel_info(channel_id):
    try:
        oid = ObjectId(channel_id)
    except Exception:
        return jsonify({"error": "Invalid channel ID"}), 400
    channel = db['channels'].find_one({'_id': oid})
    if not channel:
        return jsonify({"error": "Channel not found"}), 404
    member_count = db['channel_members'].count_documents({'channel_id': oid})
    username = channel.get('username', make_username(channel['name']))
    return jsonify({
        'id':           str(channel['_id']),
        'name':         channel['name'],
        'username':     username,
        'description':  channel.get('description', ''),
        'is_public':    channel.get('is_public', False),
        'member_count': member_count,
        'invite_link':  f"evamassage://join/{username}"
    })

# ── SEND TEXT MESSAGE ──
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

    user = db['users'].find_one({'user_id': session['user_id']})
    from_name = user.get('full_name', user.get('username', '')) if user else ''

    db['channel_messages'].insert_one({
        'channel_id': oid,
        'from_id':    session['user_id'],
        'from_name':  from_name,
        'message':    message,
        'msg_type':   'text',
        'created_at': datetime.now()
    })
    return jsonify({"success": True})

# ── SEND FILE / PHOTO / VOICE ──
@channel_bp.route('/api/channels/<channel_id>/send_file', methods=['POST'])
@login_required
def send_channel_file(channel_id):
    try:
        oid = ObjectId(channel_id)
    except Exception:
        return jsonify({"error": "Invalid channel ID"}), 400

    is_member = db['channel_members'].find_one({'channel_id': oid, 'user_id': session['user_id']})
    if not is_member:
        return jsonify({"error": "You are not a member"}), 403

    user = db['users'].find_one({'user_id': session['user_id']})
    from_name = user.get('full_name', user.get('username', '')) if user else ''

    # Accept multipart file upload
    if 'file' in request.files:
        f = request.files['file']
        filename = f.filename or 'file'
        ext = os.path.splitext(filename)[1].lower()
        safe_name = f"{uuid.uuid4().hex}{ext}"
        save_path = os.path.join(UPLOAD_FOLDER, safe_name)
        f.save(save_path)
        file_url  = f"/static/channel_uploads/{safe_name}"
        file_type = f.content_type or mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        file_size = os.path.getsize(save_path)
        msg_type  = request.form.get('msg_type', 'file')

    # Accept base64 (voice recording from browser MediaRecorder)
    elif request.is_json:
        data      = request.get_json()
        b64       = data.get('data', '')
        file_type = data.get('file_type', 'audio/webm')
        filename  = data.get('file_name', 'voice.webm')
        msg_type  = data.get('msg_type', 'voice')
        ext       = os.path.splitext(filename)[1] or '.webm'
        safe_name = f"{uuid.uuid4().hex}{ext}"
        save_path = os.path.join(UPLOAD_FOLDER, safe_name)
        with open(save_path, 'wb') as fp:
            fp.write(base64.b64decode(b64))
        file_url  = f"/static/channel_uploads/{safe_name}"
        file_size = os.path.getsize(save_path)
    else:
        return jsonify({"error": "No file provided"}), 400

    db['channel_messages'].insert_one({
        'channel_id': oid,
        'from_id':    session['user_id'],
        'from_name':  from_name,
        'message':    '',
        'msg_type':   msg_type,
        'file_url':   file_url,
        'file_name':  filename,
        'file_type':  file_type,
        'file_size':  file_size,
        'created_at': datetime.now()
    })
    return jsonify({"success": True, "file_url": file_url})

# ── GET MESSAGES ──
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
        from_name = msg.get('from_name')
        if not from_name:
            user = db['users'].find_one({'user_id': msg['from_id']})
            from_name = user.get('full_name', user.get('username', 'Unknown')) if user else 'Unknown'
        created = msg.get('created_at')
        result.append({
            'id':         str(msg['_id']),
            'from_id':    msg['from_id'],
            'from_name':  from_name,
            'message':    msg.get('message', ''),
            'msg_type':   msg.get('msg_type', 'text'),
            'file_url':   msg.get('file_url'),
            'file_name':  msg.get('file_name'),
            'file_type':  msg.get('file_type'),
            'file_size':  msg.get('file_size'),
            'created_at': created.isoformat() if hasattr(created, 'isoformat') else str(created or '')
        })
    return jsonify(result)

# ── JOIN BY USERNAME ──
@channel_bp.route('/api/channels/join/<username>', methods=['POST'])
@login_required
def join_by_username(username):
    channel = db['channels'].find_one({'username': username.lower()})
    if not channel:
        return jsonify({"error": "Channel not found"}), 404
    if not channel.get('is_public', False):
        return jsonify({"error": "This channel is private"}), 403
    oid = channel['_id']
    already = db['channel_members'].find_one({'channel_id': oid, 'user_id': session['user_id']})
    if already:
        return jsonify({"success": True, "already_member": True, "id": str(oid), "name": channel['name']})
    db['channel_members'].insert_one({
        'channel_id': oid,
        'user_id':    session['user_id'],
        'role':       'member',
        'joined_at':  datetime.now()
    })
    return jsonify({"success": True, "id": str(oid), "name": channel['name']})
