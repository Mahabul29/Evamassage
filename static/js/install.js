// FIX: deferredPrompt declared at top level
let deferredPrompt = null;

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    console.log('Install prompt ready');
    showInstallPopup();
});

// Show popup after 3 seconds if not already closed
setTimeout(() => {
    if (!localStorage.getItem('popupClosed')) {
        showInstallPopup();
    }
}, 3000);

function showInstallPopup() {
    if (!localStorage.getItem('popupClosed')) {
        const popup = document.getElementById('installPopup');
        if (popup) popup.style.display = 'block';
    }
}

function closeInstallPopup() {
    const popup = document.getElementById('installPopup');
    if (popup) popup.style.display = 'none';
    localStorage.setItem('popupClosed', 'true');
}

function installApp() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
            console.log('User choice:', choiceResult.outcome);
            deferredPrompt = null;
            closeInstallPopup();
        });
    } else {
        // Fallback for iOS / browsers without prompt support
        alert('To install: Tap the Share button ↑ then "Add to Home Screen"');
        closeInstallPopup();
    }
}

window.addEventListener('appinstalled', () => {
    console.log('EvaMassage installed successfully!');
    deferredPrompt = null;
    closeInstallPopup();
});
