// app.js - Main Application Logic

document.addEventListener('DOMContentLoaded', () => {
    // 1. Toast Notification System
    function showToast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icon = type === 'success' ? 'bx-check-circle' : 'bx-error-circle';
        toast.innerHTML = `<i class='bx ${icon}'></i> <span>${message}</span>`;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideInRight 0.4s ease reverse forwards';
            setTimeout(() => toast.remove(), 400);
        }, 3000);
    }
    window.showToast = showToast;

    // 2. Auth Logic
    const viewLogin = document.getElementById('view-login');
    const viewAdmin = document.getElementById('view-admin');
    
    // Auth Tabs
    const authTabs = document.querySelectorAll('.auth-tab');
    authTabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            authTabs.forEach(t => t.classList.remove('active'));
            e.target.classList.add('active');
            
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
            document.getElementById(`tab-${e.target.dataset.tab}`).classList.add('active');
        });
    });

    // Demo Login Function
    window.loginDemo = function(role) {
        const user = window.cineData.users[role];
        document.getElementById('current-user-name').innerText = user.name;
        document.getElementById('current-user-role').innerText = user.role;
        
        showToast(`Đăng nhập thành công: ${user.name}`);
        
        // Hide Login, Show Admin
        viewLogin.classList.remove('active');
        viewLogin.classList.add('hidden');
        viewAdmin.classList.remove('hidden');
        viewAdmin.classList.add('active');
        
        // Init Admin features
        initAdmin();
    };

    // Standard Login Form
    document.getElementById('login-form').addEventListener('submit', (e) => {
        e.preventDefault();
        window.loginDemo('admin');
    });

    // FaceID Simulation
    document.getElementById('btn-start-scan').addEventListener('click', (e) => {
        const scanner = document.querySelector('.face-scanner');
        scanner.classList.add('scanning');
        e.target.innerText = 'Đang phân tích 3D...';
        
        setTimeout(() => {
            scanner.classList.remove('scanning');
            e.target.innerText = 'Xác thực thành công!';
            e.target.style.background = 'var(--color-success)';
            e.target.style.color = '#fff';
            e.target.style.borderColor = 'var(--color-success)';
            
            setTimeout(() => window.loginDemo('manager'), 800);
        }, 2500);
    });

    // Logout
    document.getElementById('btn-logout').addEventListener('click', () => {
        viewAdmin.classList.remove('active');
        viewAdmin.classList.add('hidden');
        viewLogin.classList.remove('hidden');
        viewLogin.classList.add('active');
        showToast('Đã đăng xuất', 'success');
    });

    // Toggle Password
    document.querySelector('.toggle-pwd').addEventListener('click', function() {
        const input = document.getElementById('password');
        if(input.type === 'password') {
            input.type = 'text';
            this.classList.replace('bx-show', 'bx-hide');
        } else {
            input.type = 'password';
            this.classList.replace('bx-hide', 'bx-show');
        }
    });

    // 3. Admin Dashboard Logic
    function initAdmin() {
        if(document.getElementById('revenue-chart').innerHTML === '') {
            window.renderRevenueChart('revenue-chart');
        }
        renderSeatmap();
    }

    // Sidebar Routing
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            navItems.forEach(i => i.classList.remove('active'));
            const target = e.currentTarget;
            target.classList.add('active');
            
            const targetView = target.dataset.target;
            document.querySelectorAll('.content-view').forEach(v => v.classList.remove('active'));
            
            const viewEl = document.getElementById(`content-${targetView}`);
            if(viewEl) viewEl.classList.add('active');
            else showToast('Tính năng đang được cập nhật bởi AI', 'error');
        });
    });

    // Seatmap Render
    function renderSeatmap() {
        const grid = document.getElementById('seats-grid');
        grid.innerHTML = '';
        const rows = 8;
        const cols = 16;
        
        for(let r = 0; r < rows; r++) {
            const row = document.createElement('div');
            row.className = 'seat-row';
            for(let c = 0; c < cols; c++) {
                const seat = document.createElement('div');
                seat.className = 'seat';
                
                // Randomly assign types
                const rand = Math.random();
                if(r < 2) seat.classList.add('vip');
                else if(r > 2 && r < 5 && c > 3 && c < 12) seat.classList.add('prime');
                
                if(rand < 0.4) seat.classList.add('occupied');
                
                // AI Heatmap data (simulated)
                if(r > 2 && r < 6 && c > 4 && c < 11) seat.classList.add('hot');
                
                seat.addEventListener('click', function() {
                    if(!this.classList.contains('occupied')) {
                        this.classList.toggle('selected');
                        if(this.classList.contains('selected')) {
                            this.style.background = 'var(--color-primary)';
                        } else {
                            this.style.background = '';
                        }
                    }
                });
                
                row.appendChild(seat);
            }
            grid.appendChild(row);
        }
    }

    // Heatmap Toggle
    const heatmapToggle = document.getElementById('toggle-heatmap');
    if(heatmapToggle) {
        heatmapToggle.addEventListener('change', (e) => {
            const container = document.querySelector('.seatmap-container');
            if(e.target.checked) {
                container.classList.add('heatmap-active');
                showToast('AI Heatmap kích hoạt. Vùng đỏ là khu vực VIP tiềm năng.');
            } else {
                container.classList.remove('heatmap-active');
            }
        });
    }

    // AI Auto Schedule Simulation
    document.getElementById('btn-auto-schedule')?.addEventListener('click', (e) => {
        const btn = e.currentTarget;
        btn.innerHTML = `<i class='bx bx-loader-alt bx-spin'></i> AI đang tính toán...`;
        
        setTimeout(() => {
            btn.innerHTML = `<i class='bx bx-check'></i> Đã Tối Ưu Xong`;
            btn.style.background = 'var(--color-success)';
            
            document.getElementById('schedule-grid').innerHTML = `
                <div style="padding: 20px; background: rgba(0,255,136,0.1); border-left: 4px solid var(--color-success); border-radius: 8px;">
                    <h4><i class='bx bx-trending-up'></i> Kết quả tối ưu từ CineBrain AI</h4>
                    <p style="font-size:0.9rem; margin-top:8px; color:var(--color-text-muted);">Đã chuyển suất chiếu "Dune: Part Two" sang 20:00 (Hall 1) - Dự kiến tăng doanh thu +18% so với lịch cũ.</p>
                </div>
            `;
            showToast('Lịch chiếu đã được cập nhật bởi AI');
        }, 2000);
    });

    // AI Chat Copilot Drawer
    const btnChat = document.getElementById('btn-ai-chat');
    const drawer = document.getElementById('ai-chat-drawer');
    const btnCloseChat = document.getElementById('btn-close-chat');
    
    btnChat.addEventListener('click', () => drawer.classList.add('open'));
    btnCloseChat.addEventListener('click', () => drawer.classList.remove('open'));

    window.sendPrompt = function(text) {
        const body = document.getElementById('chat-body');
        
        // Add User Message
        body.innerHTML += `<div class="message user"><p>${text}</p></div>`;
        
        // Add Loading...
        const loadingId = 'msg-' + Date.now();
        body.innerHTML += `<div class="message ai" id="${loadingId}"><p><i class='bx bx-dots-horizontal-rounded bx-burst'></i></p></div>`;
        body.scrollTop = body.scrollHeight;

        setTimeout(() => {
            const el = document.getElementById(loadingId);
            if(text.includes('F&B')) {
                el.innerHTML = `<p>Dự báo cuối tuần này (dựa trên lượng đặt vé): <br>- Bắp rang bơ: cần 1.200 hộp <br>- Nước ngọt: cần 2.500 ly <br>=> Đề xuất nhập thêm 20% nguyên liệu kho A.</p>`;
            } else {
                el.innerHTML = `<p>Đã chạy thuật toán Dynamic Pricing. Giá vé suất 20:00 tăng +15% (Prime Time) do nhu cầu cao. Áp dụng ngay?</p>`;
            }
            body.scrollTop = body.scrollHeight;
        }, 1500);
    };

    document.getElementById('btn-send-chat').addEventListener('click', () => {
        const input = document.getElementById('chat-input');
        if(input.value.trim() !== '') {
            window.sendPrompt(input.value);
            input.value = '';
        }
    });
});
