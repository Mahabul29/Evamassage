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

@msg_bp.route('/api/chats/repair', methods=['POST', 'GET'])
@login_required  
def repair_chats():
    """Rebuild chats collection from existing messages — run once if chats are empty"""
    from config import messages as msgs_col, chats as chats_col
    from datetime import datetime
    
    # Find all messages involving any user
    all_msgs = list(msgs_col.find({}, {'from_id': 1, 'to_id': 1, 'message': 1, 'created_at': 1}))
    
    repaired = 0
    seen = set()
    for m in sorted(all_msgs, key=lambda x: x.get('created_at') or datetime.min):
        try:
            fid = int(m['from_id'])
            tid = int(m['to_id'])
        except Exception:
            continue
        u1, u2 = sorted([fid, tid])
        key = (u1, u2)
        # Always update so last message is correct
        chats_col.update_one(
            {'user1_id': u1, 'user2_id': u2},
            {'$set': {
                'last_message':      m.get('message', ''),
                'last_message_time': m.get('created_at', datetime.now())
            }},
            upsert=True
        )
        if key not in seen:
            seen.add(key)
            repaired += 1
    
    return jsonify({
        'success': True,
        'message': f'Repaired {repaired} chat(s) from {len(all_msgs)} message(s)',
        'chats_count': repaired,
        'messages_count': len(all_msgs)
    })
    
