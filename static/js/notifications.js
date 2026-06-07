// WebSocket or polling notifications
class NotificationManager {
    constructor() {
        this.enabled = false;
        this.init();
    }
    
    init() {
        if ('Notification' in window) {
            Notification.requestPermission().then(permission => {
                this.enabled = permission === 'granted';
            });
        }
        
        this.startNotificationPolling();
    }
    
    startNotificationPolling() {
        setInterval(() => {
            this.checkNewMessages();
        }, 5000);
    }
    
    checkNewMessages() {
        $.get('/api/unread_count', (count) => {
            if (count > 0) {
                this.showNotification(`You have ${count} new messages`);
                this.updateBadge(count);
            }
        });
    }
    
    showNotification(message) {
        if (this.enabled) {
            new Notification('EvaMassage', {
                body: message,
                icon: '/static/images/logo.png',
                sound: '/static/sounds/notification.mp3'
            });
        }
    }
    
    updateBadge(count) {
        const badge = document.getElementById('notificationBadge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'inline';
            } else {
                badge.style.display = 'none';
            }
        }
    }
}

const notifications = new NotificationManager();
