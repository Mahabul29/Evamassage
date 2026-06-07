// Global variables
let currentId = null;
let currentType = 'user';
let currentName = '';
let msgTimer = null;
let profileId = null;
let deferredPrompt = null;

// Switch tabs
function switchTab(tab) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(tab + 'Tab').classList.add('active');
    event.target.classList.add('active');
    
    if(tab === 'chats') loadChats();
    if(tab === 'channels') loadChannels();
}

// Go back on mobile
function goBack() {
    document.getElementById('sidebar').classList.add('hide');
}

// Open profile from chat
function openProfile() {
    if(currentId && currentType === 'user') {
        viewProfile(currentId, currentName);
    }
}

// Logout
function logout() {
    if(confirm('Are you sure you want to logout?')) {
        window.location.href = '/logout';
    }
}

// Escape HTML
function escapeHtml(t) {
    if(!t) return '';
    return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

// Format time
function formatTime(s) {
    try {
        let d = new Date(s);
        if(isNaN(d)) return '';
        let now = new Date();
        if(d.toDateString() === now.toDateString()) {
            return d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
        }
        return d.toLocaleDateString([], {month:'short', day:'numeric'});
    } catch(e) {
        return '';
    }
}

// Show/hide modals
function showChannelModal() {
    new bootstrap.Modal(document.getElementById('channelModal')).show();
}
