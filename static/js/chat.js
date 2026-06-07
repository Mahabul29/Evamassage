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
