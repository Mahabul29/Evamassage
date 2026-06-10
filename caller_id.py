"""
caller_id.py
============
Centralised helper module for all call-related ID handling and validation.

Responsibilities:
  - Normalize user IDs to int consistently (fixes str vs int mismatch in MongoDB)
  - Validate caller / callee before a call is created
  - Look up caller display info (name, avatar) from the users collection
  - Check if a user is currently busy on another call
  - Build the full call document that gets inserted into MongoDB
  - Provide a clean call-info dict safe to send to the frontend

Usage in call_routes.py:
  from caller_id import (
      normalize_id, validate_call_parties,
      get_caller_info, is_user_busy,
      build_call_doc, format_call_for_client
  )
"""

from datetime import datetime, timedelta
from config import db
import uuid

# Collections
calls = db['calls']
users = db['users']


# ══════════════════════════════════════════════════════
# 1.  ID NORMALIZATION
# ══════════════════════════════════════════════════════

def normalize_id(uid):
    """
    Always return user_id as int.
    Accepts int, str, float, or None.
    Returns None if conversion is impossible.

    This is the single source of truth for ID type —
    every caller_id / callee_id stored in MongoDB goes
    through this function so queries always match.
    """
    if uid is None:
        return None
    try:
        return int(uid)
    except (ValueError, TypeError):
        return None


# ══════════════════════════════════════════════════════
# 2.  CALLER INFO LOOKUP
# ══════════════════════════════════════════════════════

def get_caller_info(user_id):
    """
    Return a dict with display name and avatar for the caller.
    Falls back gracefully if the user document is missing.

    Returns:
        {
            "user_id":   int,
            "name":      str,   # full_name or username
            "username":  str,
            "avatar":    str    # URL string or 'default'
        }
    """
    uid = normalize_id(user_id)
    if uid is None:
        return {"user_id": None, "name": "Unknown", "username": "", "avatar": "default"}

    user = users.find_one({'user_id': uid}, {'_id': 0, 'password': 0})
    if not user:
        return {"user_id": uid, "name": "Unknown", "username": "", "avatar": "default"}

    return {
        "user_id":  uid,
        "name":     user.get('full_name') or user.get('username', 'Unknown'),
        "username": user.get('username', ''),
        "avatar":   user.get('avatar', 'default'),
    }


# ══════════════════════════════════════════════════════
# 3.  BUSY CHECK
# ══════════════════════════════════════════════════════

def is_user_busy(user_id):
    """
    Return True if the user already has an active or ringing call.
    Used to reject a new call initiation or show 'busy' to the caller.
    """
    uid = normalize_id(user_id)
    if uid is None:
        return False

    existing = calls.find_one({
        '$or': [
            {'caller_id': uid},
            {'callee_id': uid},
        ],
        'status': {'$in': ['ringing', 'active']}
    })
    return existing is not None


def get_active_call(user_id):
    """
    Return the current active/ringing call document for a user, or None.
    """
    uid = normalize_id(user_id)
    if uid is None:
        return None
    return calls.find_one({
        '$or': [
            {'caller_id': uid},
            {'callee_id': uid},
        ],
        'status': {'$in': ['ringing', 'active']}
    })


# ══════════════════════════════════════════════════════
# 4.  VALIDATE CALL PARTIES
# ══════════════════════════════════════════════════════

def validate_call_parties(caller_id, callee_id):
    """
    Validate both IDs before creating a call.

    Returns:
        (caller_int, callee_int, error_message)
        On success:  (int, int, None)
        On failure:  (None, None, "error string")
    """
    caller = normalize_id(caller_id)
    callee = normalize_id(callee_id)

    if caller is None:
        return None, None, "Invalid caller_id"

    if callee is None:
        return None, None, "callee_id required"

    if caller == callee:
        return None, None, "Cannot call yourself"

    # Make sure callee exists in DB
    callee_user = users.find_one({'user_id': callee})
    if not callee_user:
        return None, None, "User not found"

    # Check if callee is busy
    if is_user_busy(callee):
        return None, None, "User is busy"

    return caller, callee, None


# ══════════════════════════════════════════════════════
# 5.  BUILD CALL DOCUMENT
# ══════════════════════════════════════════════════════

def build_call_doc(caller_id, callee_id, call_type='voice', expires_minutes=30):
    """
    Create and insert a new call document into MongoDB.

    Steps:
      1. Normalize both IDs
      2. End any previous ringing calls from this caller
      3. Insert the new call document
      4. Return the call_id string

    Returns:
        (call_id, error_message)
        On success:  ("uuid-string", None)
        On failure:  (None, "error string")
    """
    caller, callee, err = validate_call_parties(caller_id, callee_id)
    if err:
        return None, err

    caller_info = get_caller_info(caller)

    # Cancel any stale ringing calls from this caller
    calls.update_many(
        {'caller_id': caller, 'status': 'ringing'},
        {'$set': {'status': 'ended', 'ended_at': datetime.now()}}
    )

    call_id = str(uuid.uuid4())
    now     = datetime.now()

    calls.insert_one({
        'call_id':           call_id,
        'caller_id':         caller,            # stored as int
        'callee_id':         callee,            # stored as int
        'caller_name':       caller_info['name'],
        'caller_username':   caller_info['username'],
        'caller_avatar':     caller_info['avatar'],
        'call_type':         call_type,         # 'voice' | 'video'
        'status':            'ringing',
        'offer':             None,
        'answer':            None,
        'candidates_caller': [],
        'candidates_callee': [],
        'created_at':        now,
        'expires_at':        now + timedelta(minutes=expires_minutes),
        'accepted_at':       None,
        'ended_at':          None,
        'duration_seconds':  None,
    })

    return call_id, None


# ══════════════════════════════════════════════════════
# 6.  FORMAT CALL FOR CLIENT
# ══════════════════════════════════════════════════════

def format_call_for_client(call_doc):
    """
    Convert a raw MongoDB call document into a clean dict
    safe to send as JSON to the frontend.

    Strips internal fields (_id, raw candidates) and
    normalises all IDs to int.
    """
    if not call_doc:
        return None

    return {
        "call_id":         call_doc.get('call_id'),
        "caller_id":       normalize_id(call_doc.get('caller_id')),
        "callee_id":       normalize_id(call_doc.get('callee_id')),
        "caller_name":     call_doc.get('caller_name', 'Unknown'),
        "caller_username": call_doc.get('caller_username', ''),
        "caller_avatar":   call_doc.get('caller_avatar', 'default'),
        "call_type":       call_doc.get('call_type', 'voice'),
        "status":          call_doc.get('status', 'ended'),
        "created_at":      call_doc['created_at'].isoformat() if call_doc.get('created_at') else None,
    }


# ══════════════════════════════════════════════════════
# 7.  CALL HISTORY HELPERS
# ══════════════════════════════════════════════════════

def get_call_history(user_id, limit=50):
    """
    Return recent call history for a user (both as caller and callee).
    Ordered newest first.
    """
    uid = normalize_id(user_id)
    if uid is None:
        return []

    history = calls.find(
        {'$or': [{'caller_id': uid}, {'callee_id': uid}]},
        {'_id': 0, 'candidates_caller': 0, 'candidates_callee': 0,
         'offer': 0, 'answer': 0}
    ).sort('created_at', -1).limit(limit)

    result = []
    for c in history:
        other_id = c['callee_id'] if normalize_id(c['caller_id']) == uid else c['caller_id']
        other    = get_caller_info(other_id)
        duration = c.get('duration_seconds')
        result.append({
            "call_id":        c.get('call_id'),
            "direction":      'outgoing' if normalize_id(c.get('caller_id')) == uid else 'incoming',
            "other_user_id":  normalize_id(other_id),
            "other_name":     other['name'],
            "other_avatar":   other['avatar'],
            "call_type":      c.get('call_type', 'voice'),
            "status":         c.get('status', 'ended'),
            "duration":       duration,
            "created_at":     c['created_at'].isoformat() if c.get('created_at') else None,
        })
    return result


def record_call_end(call_id):
    """
    Mark a call as ended and calculate its duration.
    Call this when either party hangs up.
    """
    call = calls.find_one({'call_id': call_id})
    if not call:
        return

    now      = datetime.now()
    accepted = call.get('accepted_at')
    duration = int((now - accepted).total_seconds()) if accepted else 0

    calls.update_one(
        {'call_id': call_id},
        {'$set': {
            'status':           'ended',
            'ended_at':         now,
            'duration_seconds': duration,
        }}
    )
