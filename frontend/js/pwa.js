const installSlot = document.getElementById('pwaInstallSlot');
const installButton = installSlot ? document.createElement('button') : null;

if (installButton) {
    installButton.className = 'pwa-install-button';
    installButton.type = 'button';
    installButton.innerHTML = `
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M12 3v11m0 0 4-4m-4 4-4-4M5 16v4h14v-4" />
        </svg>
        <span>Tải ứng dụng</span>
    `;
    installButton.setAttribute('aria-label', 'Tải ứng dụng RoomSync');
    installButton.title = 'Tải ứng dụng RoomSync';
    installButton.hidden = true;
    installSlot.append(installButton);
}

let pendingInstallPrompt = null;

window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    pendingInstallPrompt = event;
    if (installButton) installButton.hidden = false;
});

installButton?.addEventListener('click', async () => {
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
    if (installButton) installButton.hidden = true;
});

if ('serviceWorker' in navigator && window.isSecureContext) {
    navigator.serviceWorker.register('/sw.js')
        .catch(error => console.error('Không thể đăng ký RoomSync service worker.', error));
}
