const API_BASE = "http://localhost:8000/api";

let allRooms = [
    { id: 1, name: "Phòng Họp Hội Đồng", location: "Tầng 5", capacity: "18-20 người", amenities: ["Màn hình", "Wifi", "Video"], image_url: "https://images.unsplash.com/photo-1497366216548-37526070297c" },
    { id: 2, name: "Phòng Họp Sáng Tạo", location: "Tầng 3", capacity: "6-8 người", amenities: ["Màn hình", "Wifi", "Đồ uống"], image_url: "https://images.unsplash.com/photo-1517502884422-41eaead166d4" },
    { id: 3, name: "Phòng Hội Nghị A", location: "Tầng 2", capacity: "10-12 người", amenities: ["Màn hình", "Wifi"], image_url: "https://images.unsplash.com/photo-1431540015161-0bf868a2d407" }
];

let availableUsers = []; 
let selectedUserIds = []; 

// 1. LẤY HOẶC KHỞI TẠO KHO LƯU TRỮ LỊCH HỌP DÙNG CHUNG CẢ HỆ THỐNG
function getGlobalBookings() {
    const bookings = localStorage.getItem('app_bookings');
    return bookings ? JSON.parse(bookings) : [];
}

function saveGlobalBookings(bookings) {
    localStorage.setItem('app_bookings', JSON.stringify(bookings));
}

document.addEventListener('DOMContentLoaded', () => {
    const userEmail = localStorage.getItem('user_email') || 'user@company.com';
    const userName = localStorage.getItem('user_name') || 'Người dùng mới';
    const role = localStorage.getItem('role') || 'user';
    const isAdmin = role === 'admin';

    // Cập nhật thông tin giao diện người dùng
    document.getElementById('userNameDisplay').innerText = userName;
    document.getElementById('settingsName').innerText = userName;
    document.getElementById('settingsInputName').value = userName;
    document.getElementById('settingsInputEmail').value = userEmail;

    const initial = userName.charAt(0).toUpperCase();
    document.getElementById('avatarText').innerText = initial;
    document.getElementById('headerAvatarText').innerText = initial;
    document.getElementById('settingsAvatar').innerText = initial;

    const roleText = isAdmin ? 'Quản trị viên' : 'Nhân viên';
    document.getElementById('userRoleBadge').innerText = roleText;
    document.getElementById('settingsRole').innerText = roleText;

    loadUsers();
    renderRooms(allRooms, isAdmin);
    renderMyBookings();

    document.addEventListener('click', (e) => {
        const container = document.querySelector('.multi-select-container');
        if (container && !container.contains(e.target)) {
            hideUserDropdown();
        }
    });
});

// 2. RENDER BẢNG LỊCH HỌP DÀNH RIÊNG CHO TÀI KHOẢN ĐANG ĐĂNG NHẬP
function renderMyBookings(filterQuery = '') {
    const tbody = document.getElementById('myBookingsTableBody');
    if (!tbody) return;

    const currentEmail = localStorage.getItem('user_email');
    const globalBookings = getGlobalBookings();

    // Lọc danh sách lịch họp do chính tài khoản này tạo ra
    let myBookings = globalBookings.filter(b => b.user_email === currentEmail);

    if (filterQuery) {
        const q = filterQuery.toLowerCase();
        myBookings = myBookings.filter(b => 
            b.roomName.toLowerCase().includes(q) || 
            b.timeSlot.toLowerCase().includes(q) ||
            b.status.toLowerCase().includes(q)
        );
    }

    if (myBookings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#94a3b8; padding: 24px;">Bạn chưa đặt lịch họp nào.</td></tr>';
        return;
    }

    tbody.innerHTML = myBookings.map(b => `
        <tr>
            <td><strong>${b.roomName}</strong></td>
            <td>${b.timeSlot}</td>
            <td><span class="tag" style="background:#dcfce7; color:#15803d;">${b.status}</span></td>
            <td><button class="btn-admin-action btn-admin-delete" onclick="cancelBooking(${b.id})">Hủy đặt</button></td>
        </tr>
    `).join('');
}

function filterMyBookings() {
    const input = document.getElementById('myBookingSearchInput');
    renderMyBookings(input ? input.value : '');
}

function cancelBooking(id) {
    if (confirm("Bạn có chắc chắn muốn hủy lịch họp này?")) {
        let globalBookings = getGlobalBookings();
        globalBookings = globalBookings.filter(b => b.id !== id);
        saveGlobalBookings(globalBookings);
        
        // Cập nhật lại giao diện ngay lập tức
        renderMyBookings();
        renderRooms(allRooms, localStorage.getItem('role') === 'admin');
    }
}

// 3. ĐĂNG XUẤT CHUẨN: CHỈ XÓA SESSION NGƯỜI DÙNG, GIỮ LẠI APP_USERS VÀ APP_BOOKINGS
function logout() {
    if (confirm("Bạn có chắc chắn muốn đăng xuất khỏi hệ thống?")) {
        localStorage.removeItem('token');
        localStorage.removeItem('user_email');
        localStorage.removeItem('user_name');
        localStorage.removeItem('role');
        window.location.href = 'index.html';
    }
}

// 4. XỬ LÝ ĐẶT PHÒNG HỌP & ĐỒNG BỘ ĐẾN TẤT CẢ TÀI KHOẢN
async function handleBookSubmit(e) {
    e.preventDefault();
    
    const roomId = parseInt(document.getElementById('bookRoomId').value);
    const timeSlot = document.getElementById('bookTimeSlot').value;
    const purpose = document.getElementById('bookPurpose').value;
    const userEmail = localStorage.getItem('user_email');

    const globalBookings = getGlobalBookings();

    // KIỂM TRA XEM KHUNG GIỜ NÀY CỦA PHÒNG ĐÃ CÓ AI ĐẶT CHƯA (KỂ CẢ TÀI KHOẢN KHÁC)
    const isConflict = globalBookings.some(b => b.roomId === roomId && b.timeSlot === timeSlot);
    if (isConflict) {
        alert("Khung giờ này của phòng đã có người khác đặt trước đó! Vui lòng chọn khung giờ khác.");
        return;
    }

    const room = allRooms.find(r => r.id === roomId);
    const newBooking = {
        id: Date.now(),
        roomId: roomId,
        roomName: room ? room.name : "Phòng họp",
        timeSlot: timeSlot,
        purpose: purpose,
        user_email: userEmail,
        participant_ids: selectedUserIds,
        status: "Đã xác nhận"
    };

    // Lưu vào kho dữ liệu chung toàn bộ hệ thống
    globalBookings.push(newBooking);
    saveGlobalBookings(globalBookings);

    alert(`Đặt lịch thành công! Đã đồng bộ lên hệ thống và mời ${selectedUserIds.length} người tham dự.`);
    closeBookModal();

    renderRooms(allRooms, localStorage.getItem('role') === 'admin');
    renderMyBookings();
}

// 5. HIỂN THỊ PHÒNG HỌP VÀ LỊCH TRÌNH KHUNG GIỜ TƯƠNG ỨNG
function renderRooms(rooms, isAdmin) {
    const grid1 = document.getElementById('roomGridOverview');
    const grid2 = document.getElementById('roomGridRooms');
    const globalBookings = getGlobalBookings();

    const html = rooms.map(room => {
        // Kiểm tra xem phòng có cuộc họp nào trong ngày không
        const roomBookings = globalBookings.filter(b => b.roomId === room.id);
        const isFullyBooked = roomBookings.length >= 4; // Giả định tối đa 4 khung giờ/ngày

        return `
            <div class="room-card">
                <div class="card-image">
                    <img src="${room.image_url}" alt="${room.name}">
                    <span class="status-badge ${isFullyBooked ? 'status-red' : 'status-green'}">
                        ${isFullyBooked ? '• Đã kín lịch' : '• Còn trống'}
                    </span>
                </div>
                <div class="card-body">
                    <h3>${room.name}</h3>
                    <p class="location">📍 ${room.location} | 👥 ${room.capacity}</p>
                    <div class="amenities-tags">${room.amenities.map(a => `<span class="tag">📺 ${a}</span>`).join(' ')}</div>
                    <div class="card-actions">
                        <button class="btn-schedule" onclick="openScheduleModal(${room.id})">Xem lịch</button>
                        <button class="btn-book ${isFullyBooked ? 'disabled' : ''}" ${isFullyBooked ? 'disabled' : `onclick="openBookModal(${room.id})"`}>
                            ${isFullyBooked ? 'Hết chỗ' : 'Đặt ngay'}
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    if (grid1) grid1.innerHTML = html;
    if (grid2) grid2.innerHTML = html;
}

// XEM LỊCH TRÌNH CHI TIẾT CỦA PHÒNG
function openScheduleModal(roomId) {
    const room = allRooms.find(r => r.id === roomId);
    if (!room) return;

    document.getElementById('scheduleRoomTitle').innerText = `Lịch trình: ${room.name}`;
    const container = document.getElementById('timelineContainer');
    const globalBookings = getGlobalBookings();

    const slots = ["08:00 - 09:30", "10:00 - 11:30", "13:30 - 15:00", "15:30 - 17:00"];

    container.innerHTML = slots.map(slot => {
        const booking = globalBookings.find(b => b.roomId === roomId && b.timeSlot === slot);
        if (booking) {
            return `<div class="timeline-item"><span>${slot}</span><span class="time-busy">Đã được đặt bởi: ${booking.user_email}</span></div>`;
        } else {
            return `<div class="timeline-item"><span>${slot}</span><span class="time-free">Còn trống</span></div>`;
        }
    }).join('');

    document.getElementById('scheduleModal').style.display = 'flex';
}

function closeScheduleModal() { document.getElementById('scheduleModal').style.display = 'none'; }

async function loadUsers() {
    try {
        const token = localStorage.getItem('token');
        const res = await fetch(`${API_BASE}/users/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
            availableUsers = await res.json();
        } else {
            throw new Error("API /api/users/ không khả dụng");
        }
    } catch (err) {
        try {
            const mockRes = await fetch('static/js/mockUsers.json');
            availableUsers = await mockRes.json();
        } catch (mockErr) {
            console.error("Lỗi tải mockUsers.json:", mockErr);
        }
    }
}

function openBookModal(roomId) {
    document.getElementById('bookRoomId').value = roomId;
    const room = allRooms.find(r => r.id === roomId);
    if (room) {
        document.getElementById('bookModalTitle').innerText = `Đặt ngay: ${room.name}`;
    }
    
    selectedUserIds = [];
    renderSelectedTags();
    document.getElementById('bookModal').style.display = 'flex';
}

function closeBookModal() {
    document.getElementById('bookModal').style.display = 'none';
    hideUserDropdown();
}

function showUserDropdown() {
    filterUsers();
    document.getElementById('userDropdown').style.display = 'block';
}

function hideUserDropdown() {
    const dropdown = document.getElementById('userDropdown');
    if (dropdown) dropdown.style.display = 'none';
}

function filterUsers() {
    const query = document.getElementById('userSearchInput').value.toLowerCase();
    const dropdown = document.getElementById('userDropdown');
    dropdown.innerHTML = '';

    const filtered = availableUsers.filter(u => 
        !selectedUserIds.includes(u.id) && 
        (u.full_name.toLowerCase().includes(query) || u.email.toLowerCase().includes(query))
    );

    if (filtered.length === 0) {
        dropdown.innerHTML = `<div class="user-option" style="color: #94a3b8; cursor: default;">Không tìm thấy nhân viên</div>`;
    } else {
        filtered.forEach(user => {
            const item = document.createElement('div');
            item.className = 'user-option';
            item.innerHTML = `
                <span><strong>${user.full_name}</strong></span>
                <span class="user-email">${user.email}</span>
            `;
            item.onclick = () => selectUser(user);
            dropdown.appendChild(item);
        });
    }
    dropdown.style.display = 'block';
}

function selectUser(user) {
    if (!selectedUserIds.includes(user.id)) {
        selectedUserIds.push(user.id);
        renderSelectedTags();
    }
    document.getElementById('userSearchInput').value = '';
    filterUsers();
}

function removeUser(userId) {
    selectedUserIds = selectedUserIds.filter(id => id !== userId);
    renderSelectedTags();
    filterUsers();
}

function renderSelectedTags() {
    const container = document.getElementById('selectedTagsContainer');
    container.innerHTML = '';

    selectedUserIds.forEach(id => {
        const user = availableUsers.find(u => u.id === id);
        if (user) {
            const tag = document.createElement('div');
            tag.className = 'user-tag';
            tag.innerHTML = `
                <span>[x] ${user.full_name}</span>
                <span class="remove-btn" onclick="removeUser(${user.id})">&times;</span>
            `;
            container.appendChild(tag);
        }
    });
}

function toggleSidebar() {
    document.getElementById('appLayout').classList.toggle('collapsed');
}

function switchMainTab(tabName, el) {
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    if (el) el.classList.add('active');
    document.querySelectorAll('.tab-view').forEach(v => v.style.display = 'none');

    const topbarSearch = document.getElementById('topbarSearchContainer');

    if (tabName === 'overview') {
        document.getElementById('viewOverview').style.display = 'block';
        if (topbarSearch) topbarSearch.style.display = 'flex';
    } else if (tabName === 'rooms') {
        document.getElementById('viewRooms').style.display = 'block';
        if (topbarSearch) topbarSearch.style.display = 'flex';
    } else if (tabName === 'my-bookings') {
        document.getElementById('viewMyBookings').style.display = 'block';
        if (topbarSearch) topbarSearch.style.display = 'none';
    } else if (tabName === 'settings') {
        document.getElementById('viewSettings').style.display = 'block';
        if (topbarSearch) topbarSearch.style.display = 'none';
    }
}

function switchToOverview() { switchMainTab('overview', document.getElementById('navOverview')); }
function navigateToSettings() { switchMainTab('settings', document.getElementById('navSettings')); }
function scrollToRooms() { document.getElementById('roomsSection').scrollIntoView({ behavior: 'smooth' }); }
function toggleNotificationPopup() {
    const p = document.getElementById('notificationPopup');
    p.style.display = p.style.display === 'none' ? 'block' : 'none';
}