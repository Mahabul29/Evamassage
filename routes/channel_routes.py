from flask import Blueprint, request, jsonify, session, g
from bson.objectid import ObjectId
from functools import wraps
from models.channeldetails import (
    get_channel_detail,
    search_public_channels,
    update_channel,
    delete_channel,
    leave_channel,
    apply_auto_delete,
)

channel_settings_bp = Blueprint('channel_settings', __name__)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        g.user_id = session['user_id']
        return f(*args, **kwargs)
    return decorated_function


def _current_user_id():
    return g.get('user_id') or session.get('user_id')


@channel_settings_bp.route('/channels/<channel_id>', methods=['GET'])
@login_required
def api_channel_detail(channel_id):
    user_id = _current_user_id()
    detail, error = get_channel_detail(channel_id, user_id)
    if error:
        return jsonify({'success': False, 'error': error}), 404
    return jsonify({'success': True, 'channel': detail})


@channel_settings_bp.route('/channels/<channel_id>', methods=['PUT', 'PATCH'])
@login_required
def api_update_channel(channel_id):
    user_id = _current_user_id()
    data = request.get_json() or {}
    ok, msg = update_channel(channel_id, user_id, **data)
    if not ok:
        return jsonify({'success': False, 'error': msg}), 403
    return jsonify({'success': True, 'message': msg})


@channel_settings_bp.route('/channels/<channel_id>', methods=['DELETE'])
@login_required
def api_delete_channel(channel_id):
    user_id = _current_user_id()
    hard = request.args.get('hard', 'false').lower() == 'true'
    ok, msg = delete_channel(channel_id, user_id, hard=hard)
    if not ok:
        return jsonify({'success': False, 'error': msg}), 403
    return jsonify({'success': True, 'message': msg})


@channel_settings_bp.route('/channels/<channel_id>/leave', methods=['POST'])
@login_required
def api_leave_channel(channel_id):
    user_id = _current_user_id()
    ok, msg = leave_channel(channel_id, user_id)
    return jsonify({'success': ok, 'message': msg})


@channel_settings_bp.route('/channels/search', methods=['GET'])
@login_required
def api_search_channels():
    query = request.args.get('q', '')
    return jsonify(search_public_channels(query))


@channel_settings_bp.route('/channels/<channel_id>/cleanup', methods=['POST'])
@login_required
def api_cleanup_messages(channel_id):
    user_id = _current_user_id()
    from channeldetails import channel_members
    if not channel_members.find_one({'channel_id': ObjectId(channel_id), 'user_id': user_id}):
        return jsonify({'success': False, 'error': 'Not a member'}), 403
    deleted = apply_auto_delete(channel_id)
    return jsonify({'success': True, 'deleted_count': deleted})

