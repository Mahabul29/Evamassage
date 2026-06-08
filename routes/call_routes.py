from flask import Blueprint, request, jsonify, session
from datetime import datetime
from functools import wraps
import uuid

# Import your user lookup — adjust path if needed
try:
    from models.user import get_user_by_id
except ImportError:
    get_user_by_id = None

call_bp = Blueprint('call', __name__)

# In-memory signaling store
# { call_id: { offer, answer, candidates_caller, candidates_callee, status, ... } }
call_signals = {}

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return decorated


# ── Initiate a call (caller) ─────────────────────────────────────────────────
@call_bp.route('/api/call/initiate', methods=['POST'])
@login_required
def initiate_call():
    data = request.get_json()
    callee_id = data.get('callee_id')
    call_type  = data.get('call_type', 'voice')

    if not callee_id:
        return jsonify({"error": "callee_id required"}), 400

    call_id = str(uuid.uuid4())
    call_signals[call_id] = {
        'caller_id':         session['user_id'],
        'caller_name':       session.get('full_name') or session.get('username', 'Unknown'),
        'callee_id':         callee_id,
        'call_type':         call_type,
        'status':            'ringing',
        'offer':             None,
        'answer':            None,
        'candidates_caller': [],
        'candidates_callee': [],
        'created_at':        datetime.now().isoformat()
    }
    return jsonify({"success": True, "call_id": call_id})


# ── Poll for incoming calls (callee) ─────────────────────────────────────────
@call_bp.route('/api/call/incoming', methods=['GET'])
@login_required
def incoming_calls():
    my_id = session['user_id']
    for call_id, info in list(call_signals.items()):
        if info['callee_id'] == my_id and info['status'] == 'ringing':
            # Get caller name from SQL via model, fallback to session name
            caller_name = info.get('caller_name', 'Unknown')
            return jsonify({
                "call_id":     call_id,
                "caller_id":   info['caller_id'],
                "caller_name": caller_name,
                "call_type":   info['call_type']
            })
    return jsonify(None)


# ── Poll call status ──────────────────────────────────────────────────────────
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


# ── Reject / End ──────────────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/end', methods=['POST'])
@login_required
def end_call(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"error": "Call not found"}), 404
    data = request.get_json() or {}
    info['status'] = data.get('status', 'ended')
    return jsonify({"success": True})


# ── SDP Offer ─────────────────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/offer', methods=['POST'])
@login_required
def send_offer(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"error": "Call not found"}), 404
    info['offer'] = request.get_json().get('offer')
    return jsonify({"success": True})

@call_bp.route('/api/call/<call_id>/offer', methods=['GET'])
@login_required
def get_offer(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"error": "Call not found"}), 404
    return jsonify({"offer": info.get('offer')})


# ── SDP Answer ────────────────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/answer', methods=['POST'])
@login_required
def send_answer(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"error": "Call not found"}), 404
    info['answer'] = request.get_json().get('answer')
    return jsonify({"success": True})

@call_bp.route('/api/call/<call_id>/answer', methods=['GET'])
@login_required
def get_answer(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"error": "Call not found"}), 404
    return jsonify({"answer": info.get('answer')})


# ── ICE Candidates ────────────────────────────────────────────────────────────
@call_bp.route('/api/call/<call_id>/candidate', methods=['POST'])
@login_required
def send_candidate(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"error": "Call not found"}), 404
    data = request.get_json()
    candidate = data.get('candidate')
    role = data.get('role', 'caller')
    if candidate:
        key = 'candidates_caller' if role == 'caller' else 'candidates_callee'
        info[key].append(candidate)
    return jsonify({"success": True})

@call_bp.route('/api/call/<call_id>/candidates', methods=['GET'])
@login_required
def get_candidates(call_id):
    info = call_signals.get(call_id)
    if not info:
        return jsonify({"error": "Call not found"}), 404
    # callee fetches caller's candidates and vice versa
    role = request.args.get('role', 'callee')
    key  = 'candidates_callee' if role == 'callee' else 'candidates_caller'
    candidates = list(info.get(key, []))
    info[key] = []   # BUG FIX: clear after fetching to prevent duplicate ICE candidates
    return jsonify({"candidates": candidates})


# ── Cleanup stale calls ───────────────────────────────────────────────────────
@call_bp.route('/api/call/cleanup', methods=['POST'])
@login_required
def cleanup_calls():
    to_delete = []
    now = datetime.now()
    for call_id, info in list(call_signals.items()):
        created = datetime.fromisoformat(info['created_at'])
        age_min = (now - created).total_seconds() / 60
        if info['status'] in ('ended', 'rejected') or age_min > 30:
            to_delete.append(call_id)
    for cid in to_delete:
        del call_signals[cid]
    return jsonify({"cleaned": len(to_delete)})
    
