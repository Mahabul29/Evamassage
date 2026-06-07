from flask import Blueprint, request, jsonify, session, send_from_directory
from datetime import datetime
from functools import wraps
from bson.objectid import ObjectId
import os, uuid, mimetypes

file_bp = Blueprint('file', __name__)

UPLOAD_FOLDER = os.path.join('static', 'uploads')
MAX_IMAGE_MB  = 10
MAX_FILE_MB   = 25

ALLOWED_IMAGES = {'png','jpg','jpeg','gif','webp','heic','bmp'}
ALLOWED_AUDIO  = {'mp3','wav','ogg','m4a','aac'}
ALLOWED_DOCS   = {'pdf','doc','docx','txt','csv','zip','rar','7z',
                  'xls','xlsx','ppt','pptx','mp4','mov','avi','mkv'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return decorated

def allowed_file(filename, file_type):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if file_type == 'image':    return ext in ALLOWED_IMAGES
    if file_type == 'audio':    return ext in ALLOWED_AUDIO
    return ext in (ALLOWED_DOCS | ALLOWED_AUDIO | ALLOWED_IMAGES)

def get_file_type(filename, requested_type):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext in ALLOWED_IMAGES: return 'image'
    if ext in ALLOWED_AUDIO:  return 'audio'
    return 'document'


# ── Upload ────────────────────────────────────────────────────────────────────
@file_bp.route('/api/files/upload', methods=['POST'])
@login_required
def upload_file():
    # Get db — same way channel_routes does it
    db = request.db

    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f          = request.files['file']
    file_type  = request.form.get('file_type', 'document')
    to_id      = request.form.get('to_id')
    channel_id = request.form.get('channel_id')
    chat_type  = request.form.get('chat_type', 'user')

    if not f or not f.filename:
        return jsonify({"error": "Empty file"}), 400

    if not allowed_file(f.filename, file_type):
        return jsonify({"error": "File type not allowed"}), 400

    # Size check
    f.seek(0, 2); size = f.tell(); f.seek(0)
    max_mb    = MAX_IMAGE_MB if file_type == 'image' else MAX_FILE_MB
    max_bytes = max_mb * 1024 * 1024
    if size > max_bytes:
        return jsonify({"error": f"File too large. Max {max_mb}MB"}), 400

    # Save to disk
    ext      = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else 'bin'
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    f.save(filepath)

    file_url  = f"/static/uploads/{filename}"
    orig_name = f.filename
    actual_type = get_file_type(orig_name, file_type)

    # Build message doc — same fields as channel_routes messages
    msg_doc = {
        'from_id':    session['user_id'],
        'message':    f"[{actual_type.capitalize()}] {orig_name}",
        'file_url':   file_url,
        'file_name':  orig_name,
        'file_type':  actual_type,
        'file_size':  size,
        'created_at': datetime.now()
    }

    try:
        if chat_type == 'channel' and channel_id:
            oid = ObjectId(channel_id)
            is_member = db['channel_members'].find_one({
                'channel_id': oid, 'user_id': session['user_id']
            })
            if not is_member:
                return jsonify({"error": "Not a channel member"}), 403

            user = db['users'].find_one({'user_id': session['user_id']})
            msg_doc['channel_id'] = oid
            msg_doc['from_name']  = user.get('full_name', user.get('username','')) if user else ''
            db['channel_messages'].insert_one(msg_doc)

        else:
            # Private message — use same collection as send_private_message model
            if not to_id:
                return jsonify({"error": "to_id required"}), 400
            try:
                to_id_int = int(to_id)
            except (ValueError, TypeError):
                to_id_int = to_id
            msg_doc['to_id'] = to_id_int
            # Use 'messages' collection — same as your message model
            db['messages'].insert_one(msg_doc)

    except Exception as e:
        # Clean up saved file if DB fails
        try: os.remove(filepath)
        except: pass
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    return jsonify({"success": True, "file_url": file_url, "file_name": orig_name})


# ── Fetch messages with file fields (replaces /api/messages/<id>) ─────────────
# This endpoint returns messages INCLUDING file fields so the frontend renders them
@file_bp.route('/api/messages/full/<int:user_id>')
@login_required
def get_messages_full(user_id):
    db = request.db
    my_id = session['user_id']
    msgs = db['messages'].find({
        '$or': [
            {'from_id': my_id, 'to_id': user_id},
            {'from_id': user_id, 'to_id': my_id}
        ]
    }).sort('created_at', 1).limit(100)

    result = []
    for m in msgs:
        result.append({
            'from_id':    m.get('from_id'),
            'to_id':      m.get('to_id'),
            'message':    m.get('message',''),
            'file_url':   m.get('file_url'),
            'file_name':  m.get('file_name'),
            'file_type':  m.get('file_type'),
            'file_size':  m.get('file_size'),
            'created_at': m['created_at'].isoformat() if hasattr(m.get('created_at'), 'isoformat') else str(m.get('created_at',''))
        })
    return jsonify(result)
  
