from flask import Blueprint, request, jsonify, session
from datetime import datetime
from functools import wraps
import uuid, threading

call_bp = Blueprint('call', __name__)
call_signals = {}
_lock = threading.Lock()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return decorated

def sid(uid):
    """Normalize any user_id to string for safe comparison"""
    return str(uid) if uid is not None else ''


# ── Initiate ──────────────────────────────────────────────────────────────────
@call_bp.route('/api/call/initiate', methods=['POST'])
@login_required
def initiate_call():
    data      = request.get_json() or {}
    callee_id = sid(data.get('callee_id'))
    call_type = data.get('call_type', 'voice')
    if not callee_id:
        return jsonify({"error": "callee_id required"}), 400

    # Cancel any previous ringing calls from this caller
    with _lock:
        for info in call_signals.values():
            if sid(info['caller_id']) == sid(session['user_id']) and info['status'] == 'ringing':
                info['status'] = 'ended'
        _cleanup_stale_unlocked()

        call_id = str(uuid.uuid4())
        call_signals[call_id] = {
            'caller_id':         sid(session['user_id']),
            'caller_name':       session.get('full_name') or session.get('username', 'Unknown'),
            'callee_id':         callee_id,   # stored as string
            'call_type':         call_type,
            'status':            'ringing',
            'offer':             None,
            'answer':            None,
            'candidates_caller': [],
            'candidates_callee': [],
            'created_at':        datetime.now().isoformat()
        }
    return jsonify({"success": True, "call_id": call_id})


# ── Incoming poll ──────────────────────────────────────────────────────────────
@call_bp.route('/api/call/incoming', methods=['GET'])
@login_required
def incoming_calls():
    my_id = sid(session['user_id'])   # FIX: normalize to string
    with _lock:
        for call_id, info in call_signals.items():
            if sid(info['callee_id']) == my_id and info['status'] == 'ringing':
                return jsonify({
                    "call_id":     call_id,
                    "caller_id":   info['caller_id'],
                    "caller_name": info.get('caller_name', 'Unknown'),
                    "call_type":   info['call_type']
                })
    return jsonify(None)


# ── Status ────────────────────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/status', methods=['GET'])
@login_required
def call_status(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"status": "ended"})
    return jsonify({"status": info['status']})


# ── Accept ────────────────────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/accept', methods=['POST'])
@login_required
def accept_call(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"error": "Call not found"}), 404
    info['status'] = 'active'
    return jsonify({"success": True})


# ── End / Reject ──────────────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/end', methods=['POST'])
@login_required
def end_call(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"success": True})
    data = request.get_json() or {}
    info['status'] = data.get('status', 'ended')
    return jsonify({"success": True})


# ── Offer ─────────────────────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/offer', methods=['POST'])
@login_required
def send_offer(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"error": "Call not found"}), 404
    info['offer'] = (request.get_json() or {}).get('offer')
    return jsonify({"success": True})

@call_bp.route('/api/call/<call_id>/offer', methods=['GET'])
@login_required
def get_offer(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"offer": None})
    return jsonify({"offer": info.get('offer')})


# ── Answer ────────────────────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/answer', methods=['POST'])
@login_required
def send_answer(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"error": "Call not found"}), 404
    info['answer'] = (request.get_json() or {}).get('answer')
    return jsonify({"success": True})

@call_bp.route('/api/call/<call_id>/answer', methods=['GET'])
@login_required
def get_answer(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"answer": None})
    return jsonify({"answer": info.get('answer')})


# ── ICE Candidates ────────────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/candidate', methods=['POST'])
@login_required
def send_candidate(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"error": "Call not found"}), 404
    data      = request.get_json() or {}
    candidate = data.get('candidate')
    role      = data.get('role', 'caller')
    if candidate:
        key = 'candidates_caller' if role == 'caller' else 'candidates_callee'
        with _lock:
            info[key].append(candidate)
    return jsonify({"success": True})

@call_bp.route('/api/call/<call_id>/candidates', methods=['GET'])
@login_required
def get_candidates(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"candidates": []})
    role = request.args.get('role', 'callee')
    # Each side fetches the OTHER side's candidates
    key  = 'candidates_callee' if role == 'callee' else 'candidates_caller'
    with _lock:
        candidates = list(info.get(key, []))
        info[key]  = []  # Clear after fetch — prevents duplicate ICE candidates
    return jsonify({"candidates": candidates})


# ── Cleanup helpers ───────────────────────────────────────────────────────────
def _cleanup_stale_unlocked():
    """Call only while holding _lock"""
    now   = datetime.now()
    stale = [
        cid for cid, info in call_signals.items()
        if info['status'] in ('ended', 'rejected')
        or (now - datetime.fromisoformat(info['created_at'])).total_seconds() > 1800
    ]
    for cid in stale:
        del call_signals[cid]

@call_bp.route('/api/call/cleanup', methods=['POST'])
@login_required
def cleanup_calls():
    with _lock:
        _cleanup_stale_unlocked()
    return jsonify({"success": True})
               
