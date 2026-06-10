from flask import Blueprint, request, jsonify, session
from datetime import datetime
from functools import wraps
from config import db
from caller_id import (
    normalize_id,
    build_call_doc,
    format_call_for_client,
    get_call_history,
    record_call_end,
    is_user_busy,
)

call_bp = Blueprint('call', __name__)
calls   = db['calls']


# ── Auth decorator ─────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return decorated


def me():
    """Return current user's ID as int."""
    return normalize_id(session['user_id'])


# ── Initiate ───────────────────────────────────────────────────────────────────
@call_bp.route('/api/call/initiate', methods=['POST'])
@login_required
def initiate_call():
    data      = request.get_json() or {}
    callee_id = data.get('callee_id')
    call_type = data.get('call_type', 'voice')

    call_id, err = build_call_doc(me(), callee_id, call_type)
    if err:
        return jsonify({"error": err}), 400

    return jsonify({"success": True, "call_id": call_id})


# ── Incoming poll ──────────────────────────────────────────────────────────────
@call_bp.route('/api/call/incoming', methods=['GET'])
@login_required
def incoming_calls():
    call = calls.find_one({'callee_id': me(), 'status': 'ringing'})
    return jsonify(format_call_for_client(call))


# ── Status ─────────────────────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/status', methods=['GET'])
@login_required
def call_status(call_id):
    call = calls.find_one({'call_id': call_id})
    if not call:
        return jsonify({"status": "ended"})
    return jsonify({"status": call['status']})


# ── Accept ─────────────────────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/accept', methods=['POST'])
@login_required
def accept_call(call_id):
    result = calls.update_one(
        {'call_id': call_id},
        {'$set': {'status': 'active', 'accepted_at': datetime.now()}}
    )
    if result.matched_count == 0:
        return jsonify({"error": "Call not found"}), 404
    return jsonify({"success": True})


# ── End / Reject ───────────────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/end', methods=['POST'])
@login_required
def end_call(call_id):
    data   = request.get_json() or {}
    status = data.get('status', 'ended')

    if status == 'ended':
        record_call_end(call_id)
    else:
        calls.update_one({'call_id': call_id}, {'$set': {'status': status}})

    return jsonify({"success": True})


# ── Busy check ─────────────────────────────────────────────────────────────────
@call_bp.route('/api/call/busy/<int:user_id>', methods=['GET'])
@login_required
def check_busy(user_id):
    return jsonify({"busy": is_user_busy(user_id)})


# ── Offer ──────────────────────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/offer', methods=['POST'])
@login_required
def send_offer(call_id):
    offer = (request.get_json() or {}).get('offer')
    calls.update_one({'call_id': call_id}, {'$set': {'offer': offer}})
    return jsonify({"success": True})

@call_bp.route('/api/call/<call_id>/offer', methods=['GET'])
@login_required
def get_offer(call_id):
    call = calls.find_one({'call_id': call_id})
    return jsonify({"offer": call.get('offer') if call else None})


# ── Answer ─────────────────────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/answer', methods=['POST'])
@login_required
def send_answer(call_id):
    answer = (request.get_json() or {}).get('answer')
    calls.update_one({'call_id': call_id}, {'$set': {'answer': answer}})
    return jsonify({"success": True})

@call_bp.route('/api/call/<call_id>/answer', methods=['GET'])
@login_required
def get_answer(call_id):
    call = calls.find_one({'call_id': call_id})
    return jsonify({"answer": call.get('answer') if call else None})


# ── ICE Candidates ─────────────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/candidate', methods=['POST'])
@login_required
def send_candidate(call_id):
    data      = request.get_json() or {}
    candidate = data.get('candidate')
    role      = data.get('role', 'caller')
    if candidate:
        field = 'candidates_caller' if role == 'caller' else 'candidates_callee'
        calls.update_one({'call_id': call_id}, {'$push': {field: candidate}})
    return jsonify({"success": True})

@call_bp.route('/api/call/<call_id>/candidates', methods=['GET'])
@login_required
def get_candidates(call_id):
    role  = request.args.get('role', 'callee')
    field = 'candidates_callee' if role == 'callee' else 'candidates_caller'
    call  = calls.find_one({'call_id': call_id})
    if not call:
        return jsonify({"candidates": []})
    candidates = call.get(field, [])
    calls.update_one({'call_id': call_id}, {'$set': {field: []}})
    return jsonify({"candidates": candidates})


# ── Call history ───────────────────────────────────────────────────────────────
@call_bp.route('/api/call/history', methods=['GET'])
@login_required
def call_history():
    limit   = min(int(request.args.get('limit', 50)), 100)
    history = get_call_history(me(), limit)
    return jsonify(history)


# ── Cleanup expired calls ──────────────────────────────────────────────────────
@call_bp.route('/api/call/cleanup', methods=['POST'])
@login_required
def cleanup_calls():
    result = calls.delete_many({
        '$or': [
            {'status': {'$in': ['ended', 'rejected']}},
            {'expires_at': {'$lt': datetime.now()}}
        ]
    })
    return jsonify({"cleaned": result.deleted_count})
    
