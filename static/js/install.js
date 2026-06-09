// Must be declared at top level
let deferredPrompt = null;

// Capture the install prompt before browser shows it
window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    console.log('Install prompt captured ✓');
    showInstallPopup();
});

// Show popup after 3 seconds on first visit
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
        // Native PWA install prompt
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
            console.log('User choice:', choiceResult.outcome);
            deferredPrompt = null;
            closeInstallPopup();
        });
    } else {
        // Already installed or iOS
        alert('To install: Tap the Share button ↑ then "Add to Home Screen"');
        closeInstallPopup();
    }
}

window.addEventListener('appinstalled', () => {
    console.log('EvaMassage installed successfully!');
    deferredPrompt = null;
    closeInstallPopup();
    localStorage.setItem('popupClosed', 'true');
});
