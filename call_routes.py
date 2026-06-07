from flask import Blueprint, request, jsonify, session
from datetime import datetime
from functools import wraps
import uuid

call_bp = Blueprint('call', __name__)

# In-memory signaling store (replace with Redis/DB for production)
# Structure: { call_id: { offer, answer, candidates_caller, candidates_callee, status, ... } }
call_signals = {}

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return decorated


# ── Initiate a call ──────────────────────────────────────────────────────────
@call_bp.route('/api/call/initiate', methods=['POST'])
@login_required
def initiate_call():
    data = request.get_json()
    callee_id = data.get('callee_id')
    call_type  = data.get('call_type', 'voice')   # 'voice' | 'video'

    if not callee_id:
        return jsonify({"error": "callee_id required"}), 400

    call_id = str(uuid.uuid4())
    call_signals[call_id] = {
        'caller_id':   session['user_id'],
        'callee_id':   callee_id,
        'call_type':   call_type,
        'status':      'ringing',       # ringing | active | ended | rejected
        'offer':       None,
        'answer':      None,
        'candidates_caller': [],
        'candidates_callee': [],
        'created_at':  datetime.now().isoformat()
    }
    return jsonify({"success": True, "call_id": call_id})


# ── Poll for incoming calls ──────────────────────────────────────────────────
@call_bp.route('/api/call/incoming', methods=['GET'])
@login_required
def incoming_calls():
    my_id = session['user_id']
    for call_id, info in call_signals.items():
        if info['callee_id'] == my_id and info['status'] == 'ringing':
            db = request.db
            caller_name = 'Unknown'
            if db:
                user = db['users'].find_one({'user_id': info['caller_id']})
                if user:
                    caller_name = user.get('full_name', user.get('username', 'Unknown'))
            return jsonify({
                "call_id":     call_id,
                "caller_id":   info['caller_id'],
                "caller_name": caller_name,
                "call_type":   info['call_type']
            })
    return jsonify(None)


# ── Poll call status (caller side) ──────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/status', methods=['GET'])
@login_required
def call_status(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"status": "ended"})
    return jsonify({"status": info['status']})


# ── Accept a call ────────────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/accept', methods=['POST'])
@login_required
def accept_call(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"error": "Call not found"}), 404
    info['status'] = 'active'
    return jsonify({"success": True})


# ── Reject / End a call ──────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/end', methods=['POST'])
@login_required
def end_call(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"error": "Call not found"}), 404
    data = request.get_json() or {}
    info['status'] = data.get('status', 'ended')   # 'ended' | 'rejected'
    return jsonify({"success": True})


# ── WebRTC: send SDP offer ───────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/offer', methods=['POST'])
@login_required
def send_offer(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"error": "Call not found"}), 404
    data = request.get_json()
    info['offer'] = data.get('offer')
    return jsonify({"success": True})


# ── WebRTC: get SDP offer (callee polls) ────────────────────────────────────
@call_bp.route('/api/call/<call_id>/offer', methods=['GET'])
@login_required
def get_offer(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"error": "Call not found"}), 404
    return jsonify({"offer": info.get('offer')})


# ── WebRTC: send SDP answer ──────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/answer', methods=['POST'])
@login_required
def send_answer(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"error": "Call not found"}), 404
    data = request.get_json()
    info['answer'] = data.get('answer')
    return jsonify({"success": True})


# ── WebRTC: get SDP answer (caller polls) ───────────────────────────────────
@call_bp.route('/api/call/<call_id>/answer', methods=['GET'])
@login_required
def get_answer(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"error": "Call not found"}), 404
    return jsonify({"answer": info.get('answer')})


# ── WebRTC: send ICE candidate ───────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/candidate', methods=['POST'])
@login_required
def send_candidate(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"error": "Call not found"}), 404
    data = request.get_json()
    candidate = data.get('candidate')
    role = data.get('role', 'caller')   # 'caller' | 'callee'
    if candidate:
        key = 'candidates_caller' if role == 'caller' else 'candidates_callee'
        info[key].append(candidate)
    return jsonify({"success": True})


# ── WebRTC: get ICE candidates ───────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/candidates', methods=['GET'])
@login_required
def get_candidates(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"error": "Call not found"}), 404
    role = request.args.get('role', 'callee')   # callee gets caller's candidates, vice versa
    key  = 'candidates_callee' if role == 'callee' else 'candidates_caller'
    return jsonify({"candidates": info.get(key, [])})


# ── Cleanup stale calls (optional cron or call manually) ────────────────────
@call_bp.route('/api/call/cleanup', methods=['POST'])
@login_required
def cleanup_calls():
    to_delete = []
    now = datetime.now()
    for call_id, info in call_signals.items():
        created = datetime.fromisoformat(info['created_at'])
        age_minutes = (now - created).total_seconds() / 60
        if info['status'] in ('ended', 'rejected') or age_minutes > 30:
            to_delete.append(call_id)
    for cid in to_delete:
        del call_signals[cid]
    return jsonify({"cleaned": len(to_delete)})
