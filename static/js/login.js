const API_BASE = "http://localhost:8000/api";

function switchTab(tabName) {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const tabLoginBtn = document.getElementById('tabLoginBtn');
    const tabRegisterBtn = document.getElementById('tabRegisterBtn');

    if (loginForm) loginForm.style.display = tabName === 'login' ? 'block' : 'none';
    if (registerForm) registerForm.style.display = tabName === 'register' ? 'block' : 'none';
    if (tabLoginBtn) tabLoginBtn.classList.toggle('active', tabName === 'login');
    if (tabRegisterBtn) tabRegisterBtn.classList.toggle('active', tabName === 'register');
}

// Xử lý Đăng Ký
const regForm = document.getElementById('registerForm');
if (regForm) {
    regForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const data = {
            fullName: document.getElementById('regFullName').value,
            email: document.getElementById('regEmail').value,
            password: document.getElementById('regPassword').value
        };

        try {
            const res = await fetch(`${API_BASE}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (res.ok) {
                alert('Đăng ký tài khoản thành công! Vui lòng đăng nhập.');
                document.getElementById('loginEmail').value = data.email;
                switchTab('login');
            } else {
                const err = await res.json();
                alert(err.detail || 'Đăng ký thất bại!');
            }
        } catch (err) {
            alert('Lỗi kết nối đến server!');
        }
    });
}

// Xử lý Đăng Nhập
const loginForm = document.getElementById('loginForm');
if (loginForm) {
    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;

        try {
            const res = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            const result = await res.json();
            if (res.ok) {
                localStorage.setItem('token', result.token);
                localStorage.setItem('user_name', result.user_name);
                localStorage.setItem('role', result.role);
                window.location.href = '/static/dashboard.html';
            } else {
                alert(result.detail || 'Sai email hoặc mật khẩu!');
            }
        } catch (err) {
            alert('Không thể kết nối đến máy chủ!');
        }
    });
}