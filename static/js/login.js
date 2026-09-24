const API_BASE = "http://localhost:8000/api";

function switchTab(tabName) {
    document.getElementById('loginForm').style.display = tabName === 'login' ? 'block' : 'none';
    document.getElementById('registerForm').style.display = tabName === 'register' ? 'block' : 'none';
    document.getElementById('tabLoginBtn').classList.toggle('active', tabName === 'login');
    document.getElementById('tabRegisterBtn').classList.toggle('active', tabName === 'register');
}

document.getElementById('registerForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const data = {
        fullName: document.getElementById('regFullName').value,
        email: document.getElementById('regEmail').value,
        password: document.getElementById('regPassword').value
    };

    const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (res.ok) {
        alert('Đăng ký thành công! Hãy đăng nhập.');
        document.getElementById('loginEmail').value = data.email;
        switchTab('login');
    } else {
        const err = await res.json();
        alert(err.detail || 'Đăng ký thất bại!');
    }
});

document.getElementById('loginForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const data = {
        email: document.getElementById('loginEmail').value,
        password: document.getElementById('loginPassword').value
    };

    const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    const result = await res.json();
    if (res.ok) {
        localStorage.setItem('token', result.token);
        window.location.href = 'dashboard.html';
    } else {
        alert(result.detail || 'Sai thông tin đăng nhập!');
    }
});