const AUTH_API_BASE = window.AUTH_API_BASE || window.API_URL || 'http://localhost:8000/api';

function handleGoogleAuthCallback() {
    const callbackValues = new URLSearchParams(window.location.hash.slice(1));
    const accessToken = callbackValues.get('access_token');

    if (accessToken) {
        localStorage.setItem('token', accessToken);
        localStorage.setItem('access_token', accessToken);

        const valuesToStore = {
            role: callbackValues.get('role'),
            user_name: callbackValues.get('full_name'),
            user_email: callbackValues.get('email'),
            user_id: callbackValues.get('user_id'),
            user_picture: callbackValues.get('picture'),
        };
        Object.entries(valuesToStore).forEach(([key, value]) => {
            if (value) localStorage.setItem(key, value);
        });

        const dashboardUrl = new URL('dashboard.html', window.location.href);
        window.location.replace(dashboardUrl.href);
        return;
    }

    const query = new URLSearchParams(window.location.search);
    if (query.get('calendar_connected') === '1') {
        const successAlert = document.getElementById('errorAlert');
        if (successAlert) {
            successAlert.textContent = 'Đã kết nối Google Calendar. Các cuộc họp được mời sẽ được đồng bộ.';
            successAlert.classList.remove('hidden', 'bg-red-50', 'border-red-200', 'text-red-600');
            successAlert.classList.add('bg-green-50', 'border-green-200', 'text-green-700');
        }
        window.history.replaceState({}, document.title, window.location.pathname);
        return;
    }
    const oauthError = query.get('google_error');
    if (!oauthError) return;

    const errorAlert = document.getElementById('errorAlert');
    const messages = {
        access_denied: 'Bạn đã hủy đăng nhập bằng Google.',
        calendar_permission_denied: 'Bạn chưa cấp quyền Google Calendar cho RoomSync.',
        oauth_failed: 'Không thể đăng nhập bằng Google. Vui lòng thử lại.',
    };
    if (errorAlert) {
        errorAlert.textContent = messages[oauthError] || messages.oauth_failed;
        errorAlert.classList.remove('hidden');
    }
    window.history.replaceState({}, document.title, window.location.pathname);
}

document.addEventListener('DOMContentLoaded', () => {
    const googleButton = document.getElementById('googleLoginButton');
    googleButton?.addEventListener('click', () => {
        window.location.assign(`${AUTH_API_BASE}/auth/google/login`);
    });

    handleGoogleAuthCallback();
});
