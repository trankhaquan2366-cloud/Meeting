const installButton = document.createElement('button');
installButton.className = 'pwa-install-button';
installButton.type = 'button';
installButton.textContent = 'Install RoomSync';
installButton.setAttribute('aria-label', 'Install RoomSync app');
installButton.hidden = true;
document.body.append(installButton);

let pendingInstallPrompt = null;

window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    pendingInstallPrompt = event;
    installButton.hidden = false;
});

installButton.addEventListener('click', async () => {
    if (!pendingInstallPrompt) return;

    const prompt = pendingInstallPrompt;
    pendingInstallPrompt = null;
    installButton.disabled = true;

    try {
        await prompt.prompt();
        await prompt.userChoice;
        installButton.hidden = true;
    } catch (error) {
        console.error('Không thể mở lời nhắc cài đặt RoomSync.', error);
        installButton.hidden = true;
    } finally {
        installButton.disabled = false;
    }
});

window.addEventListener('appinstalled', () => {
    pendingInstallPrompt = null;
    installButton.hidden = true;
});

if ('serviceWorker' in navigator && window.isSecureContext) {
    navigator.serviceWorker.register('/sw.js')
        .catch(error => console.error('Không thể đăng ký RoomSync service worker.', error));
}
