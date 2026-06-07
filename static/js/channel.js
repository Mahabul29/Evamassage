// Load channels
function loadChannels() {
    $.get('/api/channels', function(data) {
        let html = '';
        if(!data || data.length === 0) {
            html = '<div class="empty-state"><i class="fas fa-hashtag fa-3x mb-2 d-block"></i>No channels yet<br><button class="btn btn-sm btn-success mt-2" onclick="showChannelModal()">Create First Channel</button></div>';
        } else {
            data.forEach(c => {
                html += `<div class="channel-item" onclick="selectChat('${c.id}','${escapeHtml(c.name)}','channel')">
                    <div><i class="fas fa-hashtag"></i> <b>${escapeHtml(c.name)}</b><br><small>${c.description || 'No description'}</small></div>
                    <span class="badge bg-secondary">${c.member_count} members</span>
                </div>`;
            });
        }
        $('#channelsList').html(html);
    }).fail(() => $('#channelsList').html('<div class="empty-state">Error loading channels</div>'));
}

// Load channel messages
function loadChannelMessages() {
    if(!currentId || currentType !== 'channel') return;
    
    $.get('/api/channels/' + currentId + '/messages', function(msgs) {
        let html = '';
        if(!msgs || msgs.length === 0) {
            html = '<div class="empty-state"><i class="fas fa-hashtag fa-3x mb-2 d-block"></i>No messages in channel<br><small>Be the first to message!</small></div>';
        } else {
            msgs.forEach(m => {
                let sent = (m.from_id === ME);
                html += `<div class="msg ${sent ? 'sent' : 'recv'}">
                    ${!sent ? '<div class="msg-name">' + escapeHtml(m.from_name) + '</div>' : ''}
                    ${escapeHtml(m.message)}
                    <div class="msg-time">${formatTime(m.created_at)}</div>
                </div>`;
            });
        }
        $('#messagesArea').html(html);
        $('#messagesArea').scrollTop($('#messagesArea')[0].scrollHeight);
    });
}

// Create channel
function createChannel() {
    let name = $('#channelName').val().trim();
    if(!name) {
        alert('Please enter a channel name');
        return;
    }
    
    $.ajax({
        url: '/api/channels',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({name: name, description: $('#channelDesc').val()}),
        success: function(r) {
            if(r.success) {
                $('#channelModal').modal('hide');
                $('#channelName').val('');
                $('#channelDesc').val('');
                loadChannels();
                switchTab('channels');
                alert('Channel "' + r.name + '" created!');
            } else {
                alert(r.error || 'Failed to create channel');
            }
        },
        error: function(xhr) {
            let error = 'Failed to create channel';
            if(xhr.responseJSON && xhr.responseJSON.error) error = xhr.responseJSON.error;
            alert(error);
        }
    });
      }
