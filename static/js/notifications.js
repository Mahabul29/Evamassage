// ═══════════════════════════════════════════════════════════
//  NOTIFICATION FIXES — replace / patch in index.html
// ═══════════════════════════════════════════════════════════

// ── 1. REPLACE your NotificationManager class with this ──

class NotificationManager {
    constructor() {
        this.enabled = false;
        this.lastCount = 0;
        // Permission is NOT requested here — browser blocks auto-prompts.
        // It is requested only on explicit user tap (enableNotifications()).
        this.startPolling();
    }

    async requestPermission() {
        if (!('Notification' in window)) return false;
        const permission = await Notification.requestPermission();
        this.enabled = permission === 'granted';
        return this.enabled;
    }

    startPolling() {
        setInterval(() => this.checkNewMessages(), 5000);
    }

    checkNewMessages() {
        fetch('/api/unread_count', { credentials: 'same-origin' })
            .then(r => r.ok ? r.json() : 0)
            .then(count => {
                this.updateBadge(count);
                // Only fire a notification when the count goes UP
                // and the app is in the background
                if (count > this.lastCount && this.enabled && document.visibilityState !== 'visible') {
                    this.showNotification(count);
                }
                this.lastCount = count;
            })
            .catch(() => {}); // never crash on network error
    }

    showNotification(count) {
        new Notification('EvaMassage', {
            body: `You have ${count} unread message${count > 1 ? 's' : ''}`,
            icon: '/static/images/logo.png'
        });
    }

    updateBadge(count) {
        const badge = document.getElementById('notificationBadge');
        if (!badge) return;
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.style.display = 'inline-flex';
        } else {
            badge.style.display = 'none';
        }
    }
}

const notifications = new NotificationManager();

// Called by the bell button — needs a real user tap to request permission
async function enableNotifications() {
    const granted = await notifications.requestPermission();
    showToast(granted ? '🔔 Notifications enabled' : '🔕 Notifications blocked — check browser settings');
}


// ── 2. REPLACE your topbar bell button (add this in .topbar-actions) ──
//
// <button class="topbar-btn" onclick="enableNotifications()" title="Notifications" style="position:relative;">
//   <i class="fas fa-bell"></i>
//   <span id="notificationBadge"
//     style="display:none;position:absolute;top:2px;right:2px;
//            background:#f44336;color:#fff;border-radius:50%;
//            font-size:9px;width:16px;height:16px;
//            align-items:center;justify-content:center;font-weight:700;">
//   </span>
// </button>


// ── 3. PATCH openChat() — add mark-read call at the top ──
//
// function openChat(userId, name) {
//   // Mark incoming messages from this user as read
//   fetch(`/api/messages/mark_read/${userId}`, {
//     method: 'POST',
//     credentials: 'same-origin'
//   }).catch(() => {});
//
//   // ... rest of your existing openChat code unchanged ...
// }


// ── 4. OPTIONAL — show per-chat unread badge in renderChats / _doRenderUnified ──
//
// The updated get_chat_list() now returns `unread_count` per chat.
// To show a green badge on each chat row, add this inside the forEach
// where you build the chat-item innerHTML:
//
//   const unreadBadge = c.unread_count > 0
//     ? `<span style="background:var(--accent);color:#fff;border-radius:50%;
//                     font-size:11px;font-weight:700;min-width:20px;height:20px;
//                     display:inline-flex;align-items:center;justify-content:center;
//                     padding:0 4px;">${c.unread_count > 99 ? '99+' : c.unread_count}</span>`
//     : '';
//
// Then place {unreadBadge} in the div.innerHTML where you want it shown.
