from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
from functools import wraps
from config import db
import uuid

call_bp = Blueprint('call', __name__)
calls = db['calls']  # MongoDB so all gunicorn workers share state

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return decorated

# FIX: store user_id as INT (not string) so queries always match
def sid(uid):
    try:
        return int(uid)
    except (ValueError, TypeError):
        return uid


# ── Initiate ──────────────────────────────────────────────────────────────────
@call_bp.route('/api/call/initiate', methods=['POST'])
@login_required
def initiate_call():
    data      = request.get_json() or {}
    callee_id = sid(data.get('callee_id'))
    call_type = data.get('call_type', 'voice')
    if not callee_id:
        return jsonify({"error": "callee_id required"}), 400

    caller_id = sid(session['user_id'])

    # End any previous ringing calls from this caller
    calls.update_many(
        {'caller_id': caller_id, 'status': 'ringing'},
        {'$set': {'status': 'ended'}}
    )

    call_id = str(uuid.uuid4())
    calls.insert_one({
        'call_id':           call_id,
        'caller_id':         caller_id,
        'caller_name':       session.get('full_name') or session.get('username', 'Unknown'),
        'callee_id':         callee_id,
        'call_type':         call_type,
        'status':            'ringing',
        'offer':             None,
        'answer':            None,
        'candidates_caller': [],
        'candidates_callee': [],
        'created_at':        datetime.now(),
        'expires_at':        datetime.now() + timedelta(minutes=30)
    })
    return jsonify({"success": True, "call_id": call_id})


# ── Incoming poll ─────────────────────────────────────────────────────────────
@call_bp.route('/api/call/incoming', methods=['GET'])
@login_required
def incoming_calls():
    callee_id = sid(session['user_id'])
    call = calls.find_one({
        'callee_id': callee_id,
        'status':    'ringing'
    })
    if not call:
        return jsonify(None)
    return jsonify({
        "call_id":     call['call_id'],
        "caller_id":   call['caller_id'],
        "caller_name": call.get('caller_name', 'Unknown'),
        "call_type":   call['call_type']
    })


# ── Status ────────────────────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/status', methods=['GET'])
@login_required
def call_status(call_id):
    call = calls.find_one({'call_id': call_id})
    if not call:
        return jsonify({"status": "ended"})
    return jsonify({"status": call['status']})


# ── Accept ────────────────────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/accept', methods=['POST'])
@login_required
def accept_call(call_id):
    result = calls.update_one({'call_id': call_id}, {'$set': {'status': 'active'}})
    if result.matched_count == 0:
        return jsonify({"error": "Call not found"}), 404
    return jsonify({"success": True})


# ── End / Reject ──────────────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/end', methods=['POST'])
@login_required
def end_call(call_id):
    data   = request.get_json() or {}
    status = data.get('status', 'ended')
    calls.update_one({'call_id': call_id}, {'$set': {'status': status}})
    return jsonify({"success": True})


# ── Offer ─────────────────────────────────────────────────────────────────────
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
    if not call:
        return jsonify({"offer": None})
    return jsonify({"offer": call.get('offer')})


# ── Answer ────────────────────────────────────────────────────────────────────
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
    if not call:
        return jsonify({"answer": None})
    return jsonify({"answer": call.get('answer')})


# ── ICE Candidates ────────────────────────────────────────────────────────────
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
    # Clear after fetching — prevents duplicate ICE candidates
    calls.update_one({'call_id': call_id}, {'$set': {field: []}})
    return jsonify({"candidates": candidates})


# ── Cleanup ───────────────────────────────────────────────────────────────────
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
               
