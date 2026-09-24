document.getElementById('loginForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    try {
        // Nối tới API Backend .NET của bạn
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
            // Lưu token JWT vào localStorage
            localStorage.setItem('token', data.token);
            alert('Đăng nhập thành công!');
            window.location.href = 'dashboard.html'; // Chuyển sang màn hình chính
        } else {
            alert(data.message || 'Đăng nhập thất bại!');
        }
    } catch (error) {
        console.error('Lỗi kết nối:', error);
        alert('Không thể kết nối tới máy chủ!');
    }
});