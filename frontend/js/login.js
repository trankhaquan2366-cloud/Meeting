document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const errorAlert = document.getElementById('errorAlert');

    if (!loginForm) return;

    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        if (errorAlert) errorAlert.classList.add('hidden');

        const usernameInput = document.getElementById('username') || document.getElementById('loginEmail');
        const passwordInput = document.getElementById('password') || document.getElementById('loginPassword');

        if (!usernameInput || !passwordInput) {
            console.error("Không tìm thấy input username/password!");
            return;
        }

        const username = usernameInput.value.trim();
        const password = passwordInput.value;

        try {
            // Gửi dữ liệu JSON tới API /api/login
            const res = await fetch('http://localhost:8000/api/login', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json' 
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });

            const result = await res.json();

            if (res.ok) {
                // Lưu Token vào LocalStorage
                const token = result.access_token || result.token;
                localStorage.setItem('token', token);

                const email = result.email || result.user?.email;
                if (email) localStorage.setItem('user_email', email);
                
                if (result.user_name) localStorage.setItem('user_name', result.user_name);
                if (result.role) localStorage.setItem('role', result.role);

                // Chuyển hướng sang trang Dashboard
                window.location.href = 'dashboard.html';
            } else {
                if (errorAlert) {
                    errorAlert.textContent = result.detail || 'Tài khoản hoặc mật khẩu không chính xác!';
                    errorAlert.classList.remove('hidden');
                } else {
                    alert(result.detail || 'Tài khoản hoặc mật khẩu không chính xác!');
                }
            }
        } catch (err) {
            console.error('Lỗi kết nối:', err);
            if (errorAlert) {
                errorAlert.textContent = 'Không thể kết nối đến máy chủ Backend!';
                errorAlert.classList.remove('hidden');
            }
        }
    });
});