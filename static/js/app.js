const API_BASE = "http://localhost:8000/api";
let allRooms = [];
let myBookings = [
    { id: 101, roomName: "Phòng Họp Sáng Tạo", timeSlot: "10:00 - 11:30", status: "Đã xác nhận" }
];

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'index.html';
        return;
    }

    const userName = localStorage.getItem('user_name') || 'Nguyễn Minh Tuấn';
    const role = localStorage.getItem('role') || 'admin';
    const isAdmin = role === 'admin';

    // Cập nhật thông tin giao diện
    document.getElementById('userNameDisplay').innerText = userName;
    document.getElementById('settingsName').innerText = userName;
    document.getElementById('settingsInputName').value = userName;
    
    const initial = userName.charAt(0).toUpperCase();
    document.getElementById('avatarText').innerText = initial;
    document.getElementById('headerAvatarText').innerText = initial;
    document.getElementById('settingsAvatar').innerText = initial;

    const roleText = isAdmin ? 'Quản trị viên' : 'Nhân viên';
    document.getElementById('userRoleBadge').innerText = roleText;
    document.getElementById('settingsRole').innerText = roleText;

    // Ngày tháng
    const now = new Date();
    const dateStr = `Thứ ${now.getDay() + 1}, ${now.getDate()} tháng ${now.getMonth() + 1} năm ${now.getFullYear()}`;
    document.getElementById('currentDateText').innerText = `${dateStr} · Đang hiển thị danh sách phòng`;
    document.getElementById('filterDateLabel').innerText = `${now.getDate()}/${now.getMonth() + 1}/${now.getFullYear()}`;

    // Nút Thêm phòng
    if (isAdmin) {
        const btn1 = document.getElementById('addRoomBtnOverview');
        const btn2 = document.getElementById('addRoomBtnRooms');
        if (btn1) btn1.style.display = 'block';
        if (btn2) btn2.style.display = 'block';
    }

    fetchRooms(isAdmin);
    renderMyBookings();
});

// THU GỌN / MỞ RỘNG SIDEBAR KHI BẤM NÚT 3 GẠCH TRÊN TOPBAR
function toggleSidebar() {
    const layout = document.getElementById('appLayout');
    layout.classList.toggle('collapsed');
}

// CHUYỂN VỀ TỔNG QUAN KHI BẤM LOGO RS ROOMSYNC
function switchToOverview() {
    const overviewTab = document.getElementById('navOverview');
    switchMainTab('overview', overviewTab);
}

// CHUYỂN TAB CÁC MÀN HÌNH
function switchMainTab(tabName, el) {
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    if (el) el.classList.add('active');

    document.querySelectorAll('.tab-view').forEach(view => view.style.display = 'none');

    const searchContainer = document.getElementById('topbarSearchContainer');

    if (tabName === 'overview') {
        document.getElementById('viewOverview').style.display = 'block';
        if (searchContainer) searchContainer.style.display = 'flex';
    } else if (tabName === 'rooms') {
        document.getElementById('viewRooms').style.display = 'block';
        if (searchContainer) searchContainer.style.display = 'flex';
    } else if (tabName === 'my-bookings') {
        document.getElementById('viewMyBookings').style.display = 'block';
        if (searchContainer) searchContainer.style.display = 'none';
    } else if (tabName === 'settings') {
        document.getElementById('viewSettings').style.display = 'block';
        if (searchContainer) searchContainer.style.display = 'none';
    }
}

function navigateToSettings() {
    const settingsTab = document.getElementById('navSettings');
    switchMainTab('settings', settingsTab);
}

function scrollToRooms() {
    const elem = document.getElementById('roomsSection');
    if (elem) elem.scrollIntoView({ behavior: 'smooth' });
}

// FETCH DANH SÁCH PHÒNG
async function fetchRooms(isAdmin) {
    try {
        const token = localStorage.getItem('token');
        const res = await fetch(`${API_BASE}/rooms`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
            allRooms = await res.json();
            renderRooms(allRooms, isAdmin);
            updateStats(allRooms);
        }
    } catch (err) {
        console.error("Lỗi lấy danh sách phòng:", err);
    }
}

// RENDER PHÒNG
function renderRooms(rooms, isAdmin) {
    const gridOverview = document.getElementById('roomGridOverview');
    const gridRooms = document.getElementById('roomGridRooms');

    const htmlContent = rooms.map(room => {
        const isAvailable = room.is_available !== false;
        const statusClass = isAvailable ? 'status-green' : 'status-red';
        const statusText = isAvailable ? '• Còn trống' : '• Đã đặt';

        const amenitiesList = Array.isArray(room.amenities) ? room.amenities : [];
        const amenitiesHTML = amenitiesList.map(a => `<span class="tag">📺 ${a}</span>`).join(' ');

        let adminButtons = '';
        if (isAdmin) {
            adminButtons = `
                <button class="btn-admin-action btn-admin-edit" onclick="openEditModal(${room.id})">Sửa</button>
                <button class="btn-admin-action btn-admin-delete" onclick="deleteRoom(${room.id})">Xóa</button>
            `;
        }

        return `
            <div class="room-card">
                <div class="card-image">
                    <img src="${room.image_url || 'https://images.unsplash.com/photo-1497366216548-37526070297c'}" alt="${room.name}">
                    <span class="status-badge ${statusClass}">${statusText}</span>
                </div>
                <div class="card-body">
                    <h3>${room.name}</h3>
                    <p class="location">📍 ${room.location || 'Tầng 1'} | 👥 ${room.capacity || '10 người'}</p>
                    <div class="amenities-tags">${amenitiesHTML}</div>
                    <div class="card-actions">
                        <button class="btn-schedule" onclick="openScheduleModal(${room.id})">Xem lịch</button>
                        <button class="btn-book ${isAvailable ? '' : 'disabled'}" ${isAvailable ? `onclick="openBookModal(${room.id})"` : 'disabled'}>
                            ${isAvailable ? 'Đặt ngay' : 'Hết chỗ'}
                        </button>
                        ${adminButtons}
                    </div>
                </div>
            </div>
        `;
    }).join('');

    if (gridOverview) gridOverview.innerHTML = htmlContent;
    if (gridRooms) gridRooms.innerHTML = htmlContent;
}

// MODALS
function openScheduleModal(roomId) {
    const room = allRooms.find(r => r.id === roomId);
    if (!room) return;

    document.getElementById('scheduleRoomTitle').innerText = `Lịch trình: ${room.name}`;
    const container = document.getElementById('timelineContainer');

    const isAvail = room.is_available !== false;
    container.innerHTML = `
        <div class="timeline-item"><span>08:00 - 09:30</span><span class="time-free">Còn trống</span></div>
        <div class="timeline-item"><span>10:00 - 11:30</span><span class="${isAvail ? 'time-free' : 'time-busy'}">${isAvail ? 'Còn trống' : 'Đã có cuộc họp'}</span></div>
        <div class="timeline-item"><span>13:30 - 15:00</span><span class="time-free">Còn trống</span></div>
        <div class="timeline-item"><span>15:30 - 17:00</span><span class="time-free">Còn trống</span></div>
    `;
    document.getElementById('scheduleModal').style.display = 'flex';
}

function closeScheduleModal() {
    document.getElementById('scheduleModal').style.display = 'none';
}

function openBookModal(roomId) {
    document.getElementById('bookRoomId').value = roomId;
    const room = allRooms.find(r => r.id === roomId);
    if (room) {
        document.getElementById('bookModalTitle').innerText = `Đặt ngay: ${room.name}`;
    }
    document.getElementById('bookModal').style.display = 'flex';
}

function closeBookModal() {
    document.getElementById('bookModal').style.display = 'none';
}

function handleBookSubmit(e) {
    e.preventDefault();
    const roomId = document.getElementById('bookRoomId').value;
    const timeSlot = document.getElementById('bookTimeSlot').value;
    const purpose = document.getElementById('bookPurpose').value;

    const room = allRooms.find(r => r.id == roomId);
    if (room) {
        room.is_available = false;
        myBookings.push({
            id: Date.now(),
            roomName: room.name,
            timeSlot: timeSlot,
            status: "Đã xác nhận"
        });

        alert(`Đặt phòng thành công cho mục đích: ${purpose}!`);
        closeBookModal();

        const role = localStorage.getItem('role') || 'user';
        renderRooms(allRooms, role === 'admin');
        updateStats(allRooms);
        renderMyBookings();
    }
}

function renderMyBookings() {
    const tbody = document.getElementById('myBookingsTableBody');
    if (!tbody) return;

    if (myBookings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#94a3b8;">Bạn chưa đăng ký lịch họp nào.</td></tr>';
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

function cancelBooking(bookingId) {
    if (confirm("Bạn có muốn hủy lịch họp này không?")) {
        myBookings = myBookings.filter(b => b.id !== bookingId);
        renderMyBookings();
    }
}

// LỌC VÀ TÌM KIẾM
function handleSearch() { applyFilters(); }
function filterToday() { alert("Đã đồng bộ lịch họp hôm nay!"); }

function applyFilters() {
    const query = document.getElementById('searchInput').value.toLowerCase();
    const cap = document.getElementById('capacitySelect').value;

    let filtered = allRooms.filter(r => 
        r.name.toLowerCase().includes(query) || 
        (r.location && r.location.toLowerCase().includes(query))
    );

    if (cap !== 'all') {
        filtered = filtered.filter(r => {
            const num = parseInt(r.capacity) || 10;
            if (cap === 'small') return num <= 5;
            if (cap === 'medium') return num > 5 && num <= 12;
            if (cap === 'large') return num > 12;
            return true;
        });
    }

    const role = localStorage.getItem('role') || 'user';
    renderRooms(filtered, role === 'admin');
}

function setFilter(amenity, btn) {
    document.querySelectorAll('.chip').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const role = localStorage.getItem('role') || 'user';
    if (amenity === 'all') {
        renderRooms(allRooms, role === 'admin');
    } else {
        const filtered = allRooms.filter(r => (r.amenities || []).includes(amenity));
        renderRooms(filtered, role === 'admin');
    }
}

function toggleNotificationPopup() {
    const popup = document.getElementById('notificationPopup');
    popup.style.display = popup.style.display === 'none' ? 'block' : 'none';
}

function updateStats(rooms) {
    const total = rooms.length;
    const availableCount = rooms.filter(r => r.is_available !== false).length;
    const inUseCount = rooms.filter(r => r.is_available === false).length;
    const capacityPercent = total > 0 ? Math.round((inUseCount / total) * 100) : 0;

    document.getElementById('statTotal').innerText = total;
    document.getElementById('statAvailable').innerText = availableCount;
    document.getElementById('statInUse').innerText = inUseCount;
    document.getElementById('statCapacityText').innerText = `${capacityPercent}% công suất`;
    document.getElementById('statRatioText').innerText = `trong ${total} phòng`;

    document.getElementById('summaryAvailable').innerText = availableCount;
    document.getElementById('summaryInUse').innerText = inUseCount;
}

// ADMIN MODAL
function openRoomModal() {
    document.getElementById('modalTitle').innerText = 'Thêm Phòng Họp Mới';
    document.getElementById('editRoomId').value = '';
    document.getElementById('roomForm').reset();
    document.getElementById('roomModal').style.display = 'flex';
}

function openEditModal(roomId) {
    const room = allRooms.find(r => r.id === roomId);
    if (!room) return;

    document.getElementById('modalTitle').innerText = 'Sửa Thông Tin Phòng Họp';
    document.getElementById('editRoomId').value = room.id;
    document.getElementById('roomName').value = room.name;
    document.getElementById('roomLocation').value = room.location || '';
    document.getElementById('roomCapacity').value = room.capacity || '';
    document.getElementById('roomAmenities').value = (room.amenities || []).join(', ');
    document.getElementById('roomModal').style.display = 'flex';
}

function closeRoomModal() {
    document.getElementById('roomModal').style.display = 'none';
}

async function handleFormSubmit(e) {
    e.preventDefault();
    const token = localStorage.getItem('token') || '';
    const editId = document.getElementById('editRoomId').value;

    const payload = {
        name: document.getElementById('roomName').value,
        location: document.getElementById('roomLocation').value,
        capacity: document.getElementById('roomCapacity').value,
        amenities: document.getElementById('roomAmenities').value.split(',').map(s => s.trim()).filter(Boolean),
        is_available: true
    };

    const method = editId ? 'PUT' : 'POST';
    const url = editId ? `${API_BASE}/rooms/${editId}` : `${API_BASE}/rooms`;

    try {
        const res = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            closeRoomModal();
            const role = localStorage.getItem('role') || 'user';
            fetchRooms(role === 'admin');
        } else {
            const err = await res.json();
            alert(err.detail || "Thao tác thất bại!");
        }
    } catch (err) {
        alert("Lỗi kết nối máy chủ!");
    }
}

async function deleteRoom(roomId) {
    if (!confirm("Bạn có chắc chắn muốn xóa phòng này?")) return;

    const token = localStorage.getItem('token') || '';

    try {
        const res = await fetch(`${API_BASE}/rooms/${roomId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
            allRooms = allRooms.filter(r => r.id !== roomId);
            const role = localStorage.getItem('role') || 'user';
            renderRooms(allRooms, role === 'admin');
            updateStats(allRooms);
        }
    } catch (err) {
        alert("Lỗi máy chủ!");
    }
}

function logout() {
    localStorage.clear();
    window.location.href = 'index.html';
}