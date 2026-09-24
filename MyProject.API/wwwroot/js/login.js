// Function chuyển đổi giữa Tab Đăng Nhập và Đăng Ký
function switchTab(tabName) {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const tabLoginBtn = document.getElementById('tabLoginBtn');
    const tabRegisterBtn = document.getElementById('tabRegisterBtn');

    if (tabName === 'login') {
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
        tabLoginBtn.classList.add('active');
        tabRegisterBtn.classList.remove('active');
    } else {
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
        tabRegisterBtn.classList.add('active');
        tabLoginBtn.classList.remove('active');
    }
}

// 1. XỬ LÝ ĐĂNG KÝ
document.getElementById('registerForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const fullName = document.getElementById('regFullName').value;
    const email = document.getElementById('regEmail').value;
    const password = document.getElementById('regPassword').value;
    const confirmPassword = document.getElementById('regConfirmPassword').value;

    if (password !== confirmPassword) {
        alert('Mật khẩu xác nhận không khớp!');
        return;
    }

    try {
        // Nối tới API Đăng ký ở Backend .NET
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fullName, email, password })
        });

        if (response.ok) {
            alert('Tạo tài khoản thành công! Bạn có thể đăng nhập ngay.');

            // TỰ ĐỘNG ĐIỀN EMAIL ĐÃ ĐĂNG KÝ SANG FORM ĐĂNG NHẬP
            document.getElementById('loginEmail').value = email;
            document.getElementById('loginPassword').value = '';

            // CHUYỂN NGAY SANG TAB ĐĂNG NHẬP
            switchTab('login');
        } else {
            const data = await response.json();
            alert(data.message || 'Đăng ký thất bại. Email có thể đã tồn tại!');
        }
    } catch (error) {
        // Giả lập Đăng ký thành công nếu chưa nối API CSDL
        alert('Đăng ký thành công (Giả lập Client)!');
        document.getElementById('loginEmail').value = email;
        switchTab('login');
    }
});

// 2. XỬ LÝ ĐĂNG NHẬP
document.getElementById('loginForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();
        if (response.ok) {
            localStorage.setItem('token', data.token);
            window.location.href = 'dashboard.html';
        } else {
            alert(data.message || 'Sai email hoặc mật khẩu!');
        }
    } catch (error) {
        // Giả lập đăng nhập thành công để test giao diện
        if (email && password) {
            alert('Đăng nhập thành công!');
            window.location.href = 'dashboard.html';
        }
    }
});