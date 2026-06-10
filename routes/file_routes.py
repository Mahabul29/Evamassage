from flask import Blueprint, request, jsonify, session
from datetime import datetime
from functools import wraps
from bson.objectid import ObjectId
from config import db  # FIX: use db directly from config
import os, uuid

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
    if file_type == 'image': return ext in ALLOWED_IMAGES
    if file_type == 'audio': return ext in ALLOWED_AUDIO
    return ext in (ALLOWED_DOCS | ALLOWED_AUDIO | ALLOWED_IMAGES)

def get_file_type(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext in ALLOWED_IMAGES: return 'image'
    if ext in ALLOWED_AUDIO:  return 'audio'
    return 'document'


@file_bp.route('/api/files/send', methods=['POST'])
@file_bp.route('/api/files/upload', methods=['POST'])
@login_required
def upload_file():
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
    max_mb = MAX_IMAGE_MB if file_type == 'image' else MAX_FILE_MB
    if size > max_mb * 1024 * 1024:
        return jsonify({"error": f"File too large. Max {max_mb}MB"}), 400

    # Save to disk
    ext      = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else 'bin'
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    f.save(filepath)

    file_url    = f"/static/uploads/{filename}"
    orig_name   = f.filename
    actual_type = get_file_type(orig_name)

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
            try:
                oid = ObjectId(channel_id)
            except Exception:
                oid = channel_id

            is_member = db['channel_members'].find_one({
                'channel_id': oid, 'user_id': session['user_id']
            })
            if not is_member:
                try: os.remove(filepath)
                except: pass
                return jsonify({"error": "Not a channel member"}), 403

            user = db['users'].find_one({'user_id': session['user_id']})
            msg_doc['channel_id'] = oid
            msg_doc['from_name']  = user.get('full_name', user.get('username', '')) if user else ''
            db['channel_messages'].insert_one(msg_doc)

        else:
            if not to_id:
                try: os.remove(filepath)
                except: pass
                return jsonify({"error": "to_id required"}), 400
            try:
                to_id_val = int(to_id)
            except (ValueError, TypeError):
                to_id_val = to_id

            msg_doc['to_id'] = to_id_val
            db['messages'].insert_one(msg_doc)

            # Update chat list so file appears as last message
            u1, u2 = sorted([session['user_id'], to_id_val])
            db['chats'].update_one(
                {'user1_id': u1, 'user2_id': u2},
                {'$set': {
                    'last_message':      f"[{actual_type.capitalize()}]",
                    'last_message_time': datetime.now()
                }},
                upsert=True
            )

    except Exception as e:
        try: os.remove(filepath)
        except: pass
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    return jsonify({"success": True, "file_url": file_url, "file_name": orig_name})

