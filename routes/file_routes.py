from flask import Blueprint, request, jsonify, session, send_from_directory
from datetime import datetime
from functools import wraps
from bson.objectid import ObjectId
import os, uuid, mimetypes

file_bp = Blueprint('file', __name__)

# ── Config ────────────────────────────────────────────────────────────────────
UPLOAD_FOLDER = os.path.join('static', 'uploads')
MAX_IMAGE_MB  = 10
MAX_FILE_MB   = 25

ALLOWED_IMAGES = {'png','jpg','jpeg','gif','webp','heic'}
ALLOWED_DOCS   = {'pdf','doc','docx','txt','csv','zip','rar','7z',
                  'xls','xlsx','ppt','pptx','mp3','wav','ogg','m4a',
                  'mp4','mov','avi','mkv'}

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
    if file_type == 'image': return ext in ALLOWED_IMAGES
    if file_type == 'audio': return ext in {'mp3','wav','ogg','m4a','aac'}
    return ext in ALLOWED_DOCS

def get_file_type_from_mime(mime):
    if mime and mime.startswith('image/'): return 'image'
    if mime and mime.startswith('audio/'): return 'audio'
    if mime and mime.startswith('video/'): return 'video'
    return 'document'


# ── Upload endpoint ───────────────────────────────────────────────────────────
@file_bp.route('/api/files/upload', methods=['POST'])
@login_required
def upload_file():
    db = getattr(request, 'db', None)
    if db is None:
        return jsonify({"error": "Database error"}), 500

    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f         = request.files['file']
    file_type = request.form.get('file_type', 'document')
    to_id     = request.form.get('to_id')
    channel_id= request.form.get('channel_id')
    chat_type = request.form.get('chat_type', 'user')

    if not f or f.filename == '':
        return jsonify({"error": "Empty file"}), 400

    if not allowed_file(f.filename, file_type):
        return jsonify({"error": "File type not allowed"}), 400

    # Size check
    f.seek(0, 2); size = f.tell(); f.seek(0)
    max_bytes = MAX_IMAGE_MB * 1024 * 1024 if file_type == 'image' else MAX_FILE_MB * 1024 * 1024
    if size > max_bytes:
        return jsonify({"error": f"File too large (max {MAX_IMAGE_MB if file_type=='image' else MAX_FILE_MB}MB)"}), 400

    # Save file
    ext      = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else 'bin'
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    f.save(filepath)

    file_url  = f"/static/uploads/{filename}"
    orig_name = f.filename

    # Determine actual file type from mime if needed
    mime = mimetypes.guess_type(orig_name)[0] or ''
    if file_type not in ('image','audio','document'):
        file_type = get_file_type_from_mime(mime)

    # Save message record
    msg_doc = {
        'from_id':    session['user_id'],
        'message':    f"[{file_type.capitalize()}] {orig_name}",
        'file_url':   file_url,
        'file_name':  orig_name,
        'file_type':  file_type,
        'file_size':  size,
        'created_at': datetime.now()
    }

    if chat_type == 'channel' and channel_id:
        try:
            oid = ObjectId(channel_id)
        except:
            return jsonify({"error": "Invalid channel ID"}), 400
        is_member = db['channel_members'].find_one({'channel_id': oid, 'user_id': session['user_id']})
        if not is_member:
            return jsonify({"error": "Not a member"}), 403
        msg_doc['channel_id'] = oid
        # from_name for channel display
        user = db['users'].find_one({'user_id': session['user_id']})
        msg_doc['from_name'] = user.get('full_name', user.get('username','')) if user else ''
        db['channel_messages'].insert_one(msg_doc)
    else:
        if not to_id:
            return jsonify({"error": "to_id required"}), 400
        try:
            to_id = int(to_id)
        except:
            pass
        msg_doc['to_id'] = to_id
        db['messages'].insert_one(msg_doc)

    return jsonify({"success": True, "file_url": file_url, "file_name": orig_name})


# ── Serve uploaded files (if not handled by nginx) ───────────────────────────
@file_bp.route('/static/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)
  
