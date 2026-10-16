document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('changePasswordForm');
    const errorMessage = document.getElementById('changePasswordError');
    const successMessage = document.getElementById('changePasswordSuccess');
    const submitButton = document.getElementById('changePasswordSubmit');
    if (!(form instanceof HTMLFormElement)) return;

    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (!form.reportValidity()) return;
        if (errorMessage) {
            errorMessage.hidden = true;
            errorMessage.textContent = '';
        }
        if (successMessage) {
            successMessage.hidden = true;
            successMessage.textContent = '';
        }

        const formData = new FormData(form);
        const payload = {
            email: String(formData.get('email') || '').trim(),
            current_password: String(formData.get('current_password') || ''),
            new_password: String(formData.get('new_password') || ''),
            confirm_password: String(formData.get('confirm_password') || ''),
        };
        if (submitButton instanceof HTMLButtonElement) {
            submitButton.disabled = true;
            submitButton.textContent = 'Đang cập nhật...';
        }

        try {
            const response = await fetch('/api/v1/auth/change-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
                body: JSON.stringify(payload),
            });
            const result = await response.json();
            if (!response.ok) {
                const detail = typeof result.detail === 'string'
                    ? result.detail
                    : 'Không thể đổi mật khẩu. Vui lòng kiểm tra lại thông tin.';
                throw new Error(detail);
            }
            if (successMessage) {
                successMessage.textContent = `${result.message} Đang chuyển đến trang đăng nhập...`;
                successMessage.hidden = false;
            }
            form.reset();
            window.setTimeout(() => {
                window.location.assign('/static/login.html');
            }, 1500);
        } catch (error) {
            if (errorMessage) {
                errorMessage.textContent = error instanceof Error
                    ? error.message
                    : 'Không thể kết nối máy chủ. Vui lòng thử lại.';
                errorMessage.hidden = false;
            }
        } finally {
            if (submitButton instanceof HTMLButtonElement) {
                submitButton.disabled = false;
                submitButton.textContent = 'Đổi mật khẩu & kích hoạt';
            }
        }
    });
});
