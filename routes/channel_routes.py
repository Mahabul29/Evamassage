from flask import Blueprint, request, jsonify, session
from functools import wraps
from bson.objectid import ObjectId
from config import db
from models.channel import (
    create_channel,
    get_user_channels,
    send_channel_message,
    send_channel_file,
    get_channel_messages,
    join_channel,
    join_channel_by_username,
)
import os, uuid, base64, mimetypes

channel_bp = Blueprint('channel_bp', __name__)

channel_members = db['channel_members']
channels = db['channels']


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


# ── List user's channels ──────────────────────────────────────────────────────

@channel_bp.route('/api/channels', methods=['GET'])
@login_required
def list_channels():
    user_id = session['user_id']
    return jsonify(get_user_channels(user_id))


# ── Create channel ────────────────────────────────────────────────────────────

@channel_bp.route('/api/channels', methods=['POST'])
@login_required
def api_create_channel():
    user_id = session['user_id']
    data = request.get_json(silent=True) or {}
    name        = data.get('name', '').strip()
    description = data.get('description', '').strip()
    is_public   = bool(data.get('is_public', False))
    username    = data.get('username', '').strip() or None

    if not name or len(name) < 2:
        return jsonify({'success': False, 'error': 'Name must be at least 2 characters'})

    result = create_channel(name, user_id, description, is_public, username)
    channel_id, msg = result[0], result[1]
    uname = result[2] if len(result) > 2 else None

    if not channel_id:
        return jsonify({'success': False, 'error': msg})

    return jsonify({'success': True, 'channel_id': channel_id, 'username': uname})


# ── Get messages ──────────────────────────────────────────────────────────────

@channel_bp.route('/api/channels/<channel_id>/messages', methods=['GET'])
@login_required
def api_channel_messages(channel_id):
    user_id = session['user_id']
    msgs = get_channel_messages(channel_id, user_id)
    return jsonify(msgs)


# ── Send text message ─────────────────────────────────────────────────────────

@channel_bp.route('/api/channels/<channel_id>/send', methods=['POST'])
@login_required
def api_send_channel_message(channel_id):
    user_id = session['user_id']
    data = request.get_json(silent=True) or {}
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'success': False, 'error': 'Empty message'})
    ok, msg = send_channel_message(channel_id, user_id, message)
    return jsonify({'success': ok, 'error': msg if not ok else None})


# ── Send file ─────────────────────────────────────────────────────────────────

@channel_bp.route('/api/channels/<channel_id>/send_file', methods=['POST'])
@login_required
def api_send_channel_file(channel_id):
    user_id = session['user_id']
    msg_type = request.form.get('msg_type', 'file')
    file = request.files.get('file')

    if not file:
        return jsonify({'success': False, 'error': 'No file'})

    MAX = 20 * 1024 * 1024
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX:
        return jsonify({'success': False, 'error': 'File too large (max 20 MB)'})

    ext = os.path.splitext(file.filename)[1].lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    upload_dir = os.path.join('static', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, filename)
    file.save(save_path)

    file_url  = f"/static/uploads/{filename}"
    mime      = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    file_type = 'image' if mime.startswith('image') else 'file'

    ok, msg = send_channel_file(
        channel_id, user_id,
        file_url, file.filename, file_type, size, msg_type
    )
    return jsonify({'success': ok, 'file_url': file_url if ok else None, 'error': msg if not ok else None})


# ── Join by channel ID ────────────────────────────────────────────────────────

@channel_bp.route('/api/channels/<channel_id>/join', methods=['POST'])
@login_required
def api_join_channel(channel_id):
    user_id = session['user_id']
    ok, msg = join_channel(channel_id, user_id)
    return jsonify({'success': ok, 'message': msg})


# ── Join by public username (alias used by frontend: /api/channels/join/<username>) ──

@channel_bp.route('/api/channels/join/<username>', methods=['POST'])
@login_required
def api_join_by_username_path(username):
    user_id = session['user_id']
    username = username.strip()
    if not username:
        return jsonify({'success': False, 'error': 'Missing username'})
    ok, msg, channel = join_channel_by_username(username, user_id)
    if not ok:
        return jsonify({'success': False, 'error': msg})
    return jsonify({
        'success': True,
        'message': msg,
        'channel_id': str(channel['_id']),
        'channel_name': channel.get('name', ''),
    })


# ── Join by public username ───────────────────────────────────────────────────

@channel_bp.route('/api/channels/join_by_username', methods=['POST'])
@login_required
def api_join_by_username():
    user_id = session['user_id']
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    if not username:
        return jsonify({'success': False, 'error': 'Missing username'})
    ok, msg, channel = join_channel_by_username(username, user_id)
    if not ok:
        return jsonify({'success': False, 'error': msg})
    return jsonify({
        'success': True,
        'message': msg,
        'channel_id': str(channel['_id']),
        'channel_name': channel.get('name', ''),
    })


# ── Member check ──────────────────────────────────────────────────────────────

@channel_bp.route('/api/channels/<channel_id>/is_member', methods=['GET'])
@login_required
def api_is_member(channel_id):
    user_id = session['user_id']
    try:
        oid = ObjectId(channel_id)
    except Exception:
        return jsonify({'is_member': False})
    member = channel_members.find_one({'channel_id': oid, 'user_id': user_id})
    return jsonify({'is_member': bool(member), 'role': member.get('role') if member else None})
    
