// Load chats list
function loadChats() {
    $.get('/api/chats', function(data) {
        let html = '';
        if(!data || data.length === 0) {
            html = '<div class="empty-state"><i class="fas fa-comments fa-3x mb-2 d-block"></i>No chats yet<br><small>Search for people above</small></div>';
        } else {
            data.forEach(c => {
                html += `<div class="chat-item">
                    <div onclick="selectChat(${c.user_id},'${escapeHtml(c.full_name)}','user')" style="flex:1;display:flex;gap:12px;">
                        <div class="avatar">${escapeHtml(c.full_name.charAt(0).toUpperCase())}</div>
                        <div><b>${escapeHtml(c.full_name)}</b><br><small>${c.last_message ? escapeHtml(c.last_message.substring(0,30)) : 'Tap to chat'}</small></div>
                    </div>
                    <button class="btn btn-sm" onclick="viewProfile(${c.user_id},'${escapeHtml(c.full_name)}')">
                        <i class="fas fa-info-circle"></i>
                    </button>
                </div>`;
            });
        }
        $('#chatList').html(html);
    }).fail(() => $('#chatList').html('<div class="empty-state">Error loading chats</div>'));
}

// Load private messages
function loadMessages() {
    if(!currentId || currentType !== 'user') return;
    
    $.get('/api/messages/' + currentId, function(msgs) {
        let html = '';
        if(!msgs || msgs.length === 0) {
            html = '<div class="empty-state"><i class="fas fa-comment-dots fa-3x mb-2 d-block"></i>No messages yet<br><small>Say hello!</small></div>';
        } else {
            msgs.forEach(m => {
                let sent = (m.from_id === ME);
                html += `<div class="msg ${sent ? 'sent' : 'recv'}">
                    ${escapeHtml(m.message)}
                    <div class="msg-time">${formatTime(m.created_at)}</div>
                </div>`;
            });
        }
        $('#messagesArea').html(html);
        $('#messagesArea').scrollTop($('#messagesArea')[0].scrollHeight);
    });
}

// Select a chat
function selectChat(id, name, type) {
    currentId = id;
    currentType = type;
    currentName = name;
    $('#chatTitle').html('<i class="fas fa-comment"></i> ' + escapeHtml(name));
    
    if(type === 'user') {
        loadMessages();
        if(msgTimer) clearInterval(msgTimer);
        msgTimer = setInterval(loadMessages, 3000);
    } else {
        loadChannelMessages();
        if(msgTimer) clearInterval(msgTimer);
        msgTimer = setInterval(loadChannelMessages, 3000);
    }
    
    if(window.innerWidth <= 768) {
        document.getElementById('sidebar').classList.add('hide');
    }
}

// Send message
function sendMsg() {
    let msg = $('#msgInput').val().trim();
    if(!msg || !currentId) return;
    
    $('#msgInput').val('');
    $('#msgInput').prop('disabled', true);
    
    if(currentType === 'user') {
        $.ajax({
            url: '/api/messages/send',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({to_id: currentId, message: msg}),
            success: function(r) {
                if(r.success) {
                    loadMessages();
                    loadChats();
                } else {
                    alert(r.error || 'Failed to send');
                    $('#msgInput').val(msg);
                }
            },
            error: function() {
                alert('Failed to send');
                $('#msgInput').val(msg);
            },
            complete: function() {
                $('#msgInput').prop('disabled', false);
                $('#msgInput').focus();
            }
        });
    } else {
        $.ajax({
            url: '/api/channels/' + currentId + '/send',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({message: msg}),
            success: function(r) {
                if(r.success) {
                    loadChannelMessages();
                } else {
                    alert(r.error || 'Failed to send');
                    $('#msgInput').val(msg);
                }
            },
            error: function() {
                alert('Failed to send');
                $('#msgInput').val(msg);
            },
            complete: function() {
                $('#msgInput').prop('disabled', false);
                $('#msgInput').focus();
            }
        });
    }
}

// View profile
function viewProfile(id, name) {
    profileId = id;
    $('#pName').text(name);
    $('#pUsername').text('@loading...');
    $('#pBio').text('Loading...');
    
    $.get('/api/users/profile/' + id, function(p) {
        $('#pName').text(p.full_name || name);
        $('#pUsername').text('@' + (p.username || ''));
        $('#pBio').text(p.bio || 'No bio available');
    }).fail(() => $('#pBio').text('Could not load profile'));
    
    new bootstrap.Modal(document.getElementById('profileModal')).show();
}

// Send message from profile
function sendFromProfile() {
    if(profileId) {
        bootstrap.Modal.getInstance(document.getElementById('profileModal')).hide();
        $.get('/api/users/profile/' + profileId, function(p) {
            selectChat(profileId, p.full_name, 'user');
        });
    }
}

// Search users
let searchTimer;
$('#searchInput').on('input', function() {
    let q = $(this).val().trim();
    clearTimeout(searchTimer);
    if(q.length < 2) {
        loadChats();
        return;
    }
    searchTimer = setTimeout(() => {
        $.get('/api/users/search', {q: q}, function(users) {
            let html = '';
            if(!users || users.length === 0) {
                html = '<div class="empty-state">No users found</div>';
            } else {
                users.forEach(u => {
                    html += `<div class="chat-item" onclick="selectChat(${u.user_id},'${escapeHtml(u.full_name)}','user');$('#searchInput').val('');loadChats();">
                        <div class="avatar">${escapeHtml(u.full_name.charAt(0).toUpperCase())}</div>
                        <div><b>${escapeHtml(u.full_name)}</b><br><small>@${escapeHtml(u.username)}</small></div>
                    </div>`;
                });
            }
            $('#chatList').html(html);
        });
    }, 300);
});
