from flask import Blueprint, request, jsonify, session
from functools import wraps
from models.message import send_private_message, get_private_messages, get_chat_list

msg_bp = Blueprint('message', __name__)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return decorated

@msg_bp.route('/api/messages/send', methods=['POST'])
@login_required
def send():
    # FIX: jQuery $.post() sends form data not JSON — handle both
    data = request.get_json(silent=True) or request.form
    to_id = data.get('to_id')
    message = (data.get('message') or '').strip()

    if not to_id or not message:
        return jsonify({"error": "Missing to_id or message"}), 400

    try:
        to_id = int(to_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid to_id"}), 400

    success = send_private_message(session['user_id'], to_id, message)
    if success:
        return jsonify({"success": True})
    return jsonify({"error": "Failed to send"}), 400

@msg_bp.route('/api/messages/<int:user_id>')
@login_required
def get(user_id):
    msgs = get_private_messages(session['user_id'], user_id)
    return jsonify(msgs)

# FIX: /full/ route — returns file fields because get_private_messages was fixed
@msg_bp.route('/api/messages/full/<int:user_id>')
@login_required
def get_full(user_id):
    msgs = get_private_messages(session['user_id'], user_id)
    return jsonify(msgs)

@msg_bp.route('/api/chats')
@login_required
def chats():
    return jsonify(get_chat_list(session['user_id']))

