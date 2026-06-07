from flask import Blueprint, request, jsonify, session
from functools import wraps
from models.channel import (
    create_channel, get_user_channels, 
    send_channel_message, get_channel_messages, join_channel
)

channel_bp = Blueprint('channel', __name__)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return decorated

@channel_bp.route('/api/channels', methods=['GET'])
@login_required
def get():
    return jsonify(get_user_channels(session['user_id']))

@channel_bp.route('/api/channels', methods=['POST'])
@login_required
def create():
    data = request.json
    channel_id, msg = create_channel(
        data.get('name', ''),
        session['user_id'],
        data.get('description', '')
    )
    if channel_id:
        return jsonify({"success": True, "id": channel_id, "name": data.get('name')})
    return jsonify({"error": msg}), 400

@channel_bp.route('/api/channels/<channel_id>/send', methods=['POST'])
@login_required
def send(channel_id):
    data = request.json
    success, msg = send_channel_message(channel_id, session['user_id'], data.get('message', ''))
    if success:
        return jsonify({"success": True})
    return jsonify({"error": msg}), 400

@channel_bp.route('/api/channels/<channel_id>/messages', methods=['GET'])
@login_required
def get_messages(channel_id):
    msgs = get_channel_messages(channel_id, session['user_id'])
    return jsonify(msgs)

@channel_bp.route('/api/channels/<channel_id>/join', methods=['POST'])
@login_required
def join(channel_id):
    success, msg = join_channel(channel_id, session['user_id'])
    if success:
        return jsonify({"success": True})
    return jsonify({"error": msg}), 400
