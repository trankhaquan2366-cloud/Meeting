document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const errorAlert = document.getElementById('errorAlert');

    if (!loginForm) return;

    loginForm.addEventListener('submit', async function (e) {
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
            // Thay vì dùng URLSearchParams, hãy gửi dạng JSON chuẩn
            const res = await fetch('http://localhost:8000/api/auth/login', {
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
                // Lưu Token vào LocalStorage[cite: 5]
                const token = result.access_token || result.token;
                localStorage.setItem('token', token);

                if (result.full_name) localStorage.setItem('user_name', result.full_name);
                const email = result.email || result.user?.email;
                if (email) localStorage.setItem('user_email', email);
                if (result.user_name) localStorage.setItem('user_name', result.user_name);
                if (result.role) localStorage.setItem('role', result.role);

                // 👉 LƯU THÊM EMAIL THẬT TỪ DATABASE VÀO LOCALSTORAGE
                localStorage.setItem('user_email', result.email || username);

                // Chuyển hướng sang trang Dashboard[cite: 5]
                window.location.href = 'dashboard.html';
            } else {
                if (errorAlert) {
                    // Xử lý an toàn để tránh hiện chữ [object Object] khi FastAPI trả về lỗi cấu trúc
                    let errorMessage = 'Tài khoản hoặc mật khẩu không chính xác!';
                    if (result.detail) {
                        if (typeof result.detail === 'string') {
                            errorMessage = result.detail;
                        } else if (Array.isArray(result.detail)) {
                            errorMessage = result.detail.map(err => err.msg || JSON.stringify(err)).join(', ');
                        } else if (typeof result.detail === 'object') {
                            errorMessage = result.detail.msg || JSON.stringify(result.detail);
                        }
                    }

                    errorAlert.textContent = errorMessage;
                    errorAlert.classList.remove('hidden');
                } else {
                    alert('Tài khoản hoặc mật khẩu không chính xác!');
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