// Real-time chat functionality
class ChatManager {
    constructor() {
        this.currentChat = null;
        this.messageInterval = null;
        this.typingTimeout = null;
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.startPolling();
    }
    
    setupEventListeners() {
        $('#messageInput').on('keypress', (e) => {
            if (e.which === 13) this.sendMessage();
            this.sendTypingIndicator();
        });
        
        $('#sendBtn').on('click', () => this.sendMessage());
    }
    
    loadChat(userId) {
        this.currentChat = userId;
        this.loadMessages();
        this.markAsRead();
    }
    
    loadMessages() {
        if (!this.currentChat) return;
        
        $.get(`/api/messages/${this.currentChat}`, (messages) => {
            this.renderMessages(messages);
        });
    }
    
    renderMessages(messages) {
        let html = '';
        messages.forEach(msg => {
            const isSent = msg.from_id === currentUserId;
            html += `
                <div class="message ${isSent ? 'sent' : 'received'}">
                    <div class="message-content">
                        ${this.escapeHtml(msg.message)}
                        <div class="message-time">
                            ${new Date(msg.created_at).toLocaleTimeString()}
                            ${msg.is_read && isSent ? '✓✓' : ''}
                        </div>
                    </div>
                </div>
            `;
        });
        $('#messagesArea').html(html);
        this.scrollToBottom();
    }
    
    sendMessage() {
        const message = $('#messageInput').val();
        if (message && this.currentChat) {
            $.post('/api/messages/send', {
                to_id: this.currentChat,
                message: message
            }, () => {
                $('#messageInput').val('');
                this.loadMessages();
            });
        }
    }
    
    sendTypingIndicator() {
        clearTimeout(this.typingTimeout);
        $.post('/api/typing', { to_id: this.currentChat });
        this.typingTimeout = setTimeout(() => {
            $.post('/api/stop_typing', { to_id: this.currentChat });
        }, 2000);
    }
    
    markAsRead() {
        if (this.currentChat) {
            $.post('/api/messages/mark_read', { user_id: this.currentChat });
        }
    }
    
    startPolling() {
        this.messageInterval = setInterval(() => {
            if (this.currentChat) {
                this.loadMessages();
            }
        }, 3000);
    }
    
    scrollToBottom() {
        const area = document.getElementById('messagesArea');
        if (area) area.scrollTop = area.scrollHeight;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize chat
const chat = new ChatManager();
