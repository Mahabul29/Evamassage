// Install popup functions
function initInstallPopup() {
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        showInstallPopup();
    });
    
    setTimeout(() => {
        if(!localStorage.getItem('popupClosed') && !deferredPrompt) {
            showInstallPopup();
        }
    }, 3000);
}

function showInstallPopup() {
    if(!localStorage.getItem('popupClosed')) {
        document.getElementById('installPopup').style.display = 'block';
    }
}

function closeInstallPopup() {
    document.getElementById('installPopup').style.display = 'none';
    localStorage.setItem('popupClosed', 'true');
}

function installApp() {
    if(deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(() => {
            deferredPrompt = null;
            closeInstallPopup();
        });
    } else {
        alert('To install: Tap Share button → Add to Home Screen');
        closeInstallPopup();
    }
}

window.addEventListener('appinstalled', () => {
    console.log('App installed');
    closeInstallPopup();
});
