const API_BASE = "http://localhost:8000/api";
let allRooms = [];
let myBookings = [];

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'index.html';
        return;
    }

    const userName = localStorage.getItem('user_name') || 'Nguyễn Minh Tuấn';
    const role = localStorage.getItem('role') || 'user';
    const isAdmin = role === 'admin';

    // Cập nhật thông tin giao diện người dùng
    const nameDisplay = document.getElementById('userNameDisplay');
    if (nameDisplay) nameDisplay.innerText = userName;

    const settingsName = document.getElementById('settingsName');
    if (settingsName) settingsName.innerText = userName;

    const settingsInputName = document.getElementById('settingsInputName');
    if (settingsInputName) settingsInputName.value = userName;
    
    const initial = userName.charAt(0).toUpperCase();
    ['avatarText', 'headerAvatarText', 'settingsAvatar'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerText = initial;
    });

    const roleText = isAdmin ? 'Quản trị viên' : 'Nhân viên';
    const roleBadge = document.getElementById('userRoleBadge');
    if (roleBadge) roleBadge.innerText = roleText;

    const settingsRole = document.getElementById('settingsRole');
    if (settingsRole) settingsRole.innerText = roleText;

    // Ngày tháng hiển thị
    const now = new Date();
    const dateStr = `Thứ ${now.getDay() + 1}, ${now.getDate()} tháng ${now.getMonth() + 1} năm ${now.getFullYear()}`;
    const currentDateText = document.getElementById('currentDateText');
    if (currentDateText) currentDateText.innerText = `${dateStr} · Đang hiển thị danh sách phòng`;

    const filterDateLabel = document.getElementById('filterDateLabel');
    if (filterDateLabel) filterDateLabel.innerText = `${now.getDate()}/${now.getMonth() + 1}/${now.getFullYear()}`;

    // Ẩn / hiện nút thêm phòng theo quyền Admin
    if (isAdmin) {
        const btn1 = document.getElementById('addRoomBtnOverview');
        const btn2 = document.getElementById('addRoomBtnRooms');
        if (btn1) btn1.style.display = 'block';
        if (btn2) btn2.style.display = 'block';
    }

    // Tải dữ liệu ban đầu
    fetchRooms(isAdmin);
    fetchMyBookings();
});

/* ==========================================================================
   NAVIGATION & UI CONTROLS
   ========================================================================== */

function toggleSidebar() {
    const layout = document.getElementById('appLayout');
    if (layout) layout.classList.toggle('collapsed');
}

function switchToOverview() {
    const overviewTab = document.getElementById('navOverview');
    switchMainTab('overview', overviewTab);
}

function switchMainTab(tabName, el) {
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    if (el) el.classList.add('active');

    document.querySelectorAll('.tab-view').forEach(view => view.style.display = 'none');

    const searchContainer = document.getElementById('topbarSearchContainer');

    if (tabName === 'overview') {
        const view = document.getElementById('viewOverview');
        if (view) view.style.display = 'block';
        if (searchContainer) searchContainer.style.display = 'flex';
    } else if (tabName === 'rooms') {
        const view = document.getElementById('viewRooms');
        if (view) view.style.display = 'block';
        if (searchContainer) searchContainer.style.display = 'flex';
    } else if (tabName === 'my-bookings') {
        const view = document.getElementById('viewMyBookings');
        if (view) view.style.display = 'block';
        if (searchContainer) searchContainer.style.display = 'none';
        fetchMyBookings();
    } else if (tabName === 'settings') {
        const view = document.getElementById('viewSettings');
        if (view) view.style.display = 'block';
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

function toggleNotificationPopup() {
    const popup = document.getElementById('notificationPopup');
    if (popup) {
        popup.style.display = (popup.style.display === 'none' || !popup.style.display) ? 'block' : 'none';
    }
}

/* ==========================================================================
   ROOM MANAGEMENT & FETCH
   ========================================================================== */

async function fetchRooms(isAdmin) {
    try {
        const token = localStorage.getItem('token') || '';
        const res = await fetch(`${API_BASE}/rooms/`, {
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

function renderRooms(rooms, isAdmin) {
    const gridOverview = document.getElementById('roomGridOverview');
    const gridRooms = document.getElementById('roomGridRooms');

    const htmlContent = rooms.map(room => {
        const isAvailable = room.is_available !== false;
        const statusClass = isAvailable ? 'status-green' : 'status-red';
        const statusText = isAvailable ? '• Còn trống' : '• Đã đặt';

        let amenitiesHTML = '';
        if (room.amenities) {
            let amenitiesList = room.amenities;
            if (typeof amenitiesList === 'string') {
                try {
                    amenitiesList = JSON.parse(amenitiesList);
                } catch (e) {
                    amenitiesList = [amenitiesList];
                }
            }
            if (Array.isArray(amenitiesList)) {
                amenitiesHTML = amenitiesList.map(a => `<span class="tag">📺 ${a}</span>`).join(' ');
            }
        }
        
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

function updateStats(rooms) {
    const total = rooms.length;
    const availableCount = rooms.filter(r => r.is_available !== false).length;
    const inUseCount = rooms.filter(r => r.is_available === false).length;
    const capacityPercent = total > 0 ? Math.round((inUseCount / total) * 100) : 0;

    const setTxt = (id, val) => { const el = document.getElementById(id); if(el) el.innerText = val; };

    setTxt('statTotal', total);
    setTxt('statAvailable', availableCount);
    setTxt('statInUse', inUseCount);
    setTxt('statCapacityText', `${capacityPercent}% công suất`);
    setTxt('statRatioText', `trong ${total} phòng`);

    setTxt('summaryAvailable', availableCount);
    setTxt('summaryInUse', inUseCount);
}

/* ==========================================================================
   BOOKING & SCHEDULE MODALS
   ========================================================================== */

function openScheduleModal(roomId) {
    const room = allRooms.find(r => r.id === roomId);
    if (!room) return;

    const titleEl = document.getElementById('scheduleRoomTitle');
    if (titleEl) titleEl.innerText = `Lịch trình: ${room.name}`;

    const container = document.getElementById('timelineContainer');
    if (container) {
        const isAvail = room.is_available !== false;
        container.innerHTML = `
            <div class="timeline-item"><span>08:00 - 09:30</span><span class="time-free">Còn trống</span></div>
            <div class="timeline-item"><span>10:00 - 11:30</span><span class="${isAvail ? 'time-free' : 'time-busy'}">${isAvail ? 'Còn trống' : 'Đã có cuộc họp'}</span></div>
            <div class="timeline-item"><span>13:30 - 15:00</span><span class="time-free">Còn trống</span></div>
            <div class="timeline-item"><span>15:30 - 17:00</span><span class="time-free">Còn trống</span></div>
        `;
    }
    const modal = document.getElementById('scheduleModal');
    if (modal) modal.style.display = 'flex';
}

function closeScheduleModal() {
    const modal = document.getElementById('scheduleModal');
    if (modal) modal.style.display = 'none';
}

function openBookModal(roomId) {
    const roomIdInput = document.getElementById('bookRoomId');
    if (roomIdInput) roomIdInput.value = roomId;

    const room = allRooms.find(r => r.id === roomId);
    if (room) {
        const titleEl = document.getElementById('bookModalTitle');
        if (titleEl) titleEl.innerText = `Đặt ngay: ${room.name}`;
    }
    const modal = document.getElementById('bookModal');
    if (modal) modal.style.display = 'flex';
}

function closeBookModal() {
    const modal = document.getElementById('bookModal');
    if (modal) modal.style.display = 'none';
}

async function handleBookSubmit(e) {
    e.preventDefault();

    const roomIdEl = document.getElementById('bookRoomId');
    const timeSlotEl = document.getElementById('bookTimeSlot');
    const purposeEl = document.getElementById('bookPurpose') || document.getElementById('bookTitle');
    const dateEl = document.getElementById('bookDate');
    const recurrenceTypeEl = document.getElementById('bookRecurrenceType');
    const recurrenceEndDateEl = document.getElementById('bookRecurrenceEndDate');

    const roomId = roomIdEl ? roomIdEl.value : null;
    const timeSlot = timeSlotEl ? timeSlotEl.value : "08:00 - 09:30";
    const purpose = purposeEl ? purposeEl.value : "Họp";
    const selectedDate = (dateEl && dateEl.value) ? dateEl.value : new Date().toISOString().split('T')[0];

    const timeParts = timeSlot.split('-').map(s => s.trim());
    const startStr = timeParts[0] || "08:00";
    const endStr = timeParts[1] || "09:30";

    const start_time = `${selectedDate}T${startStr}:00`;
    const end_time = `${selectedDate}T${endStr}:00`;

    const recurrenceType = recurrenceTypeEl ? recurrenceTypeEl.value : 'none';
    const recurrenceEndDate = (recurrenceEndDateEl && recurrenceEndDateEl.value) ? `${recurrenceEndDateEl.value}T23:59:59` : null;

    const payload = {
        title: purpose,
        description: "Đặt từ giao diện web",
        room_id: parseInt(roomId),
        start_time: start_time,
        end_time: end_time,
        is_recurring: recurrenceType !== 'none',
        recurrence_type: recurrenceType,
        recurrence_end_date: recurrenceEndDate
    };

    const token = localStorage.getItem('token') || '';

    try {
        const res = await fetch(`${API_BASE}/meetings/book`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            alert("Đã đặt lịch họp thành công!");
            closeBookModal();
            
            const role = localStorage.getItem('role') || 'user';
            fetchRooms(role === 'admin');
            fetchMyBookings();
        } else {
            const err = await res.json();
            alert(`Lỗi đặt phòng: ${err.detail || 'Không thể đặt phòng vào khung giờ này'}`);
        }
    } catch (err) {
        console.error("Lỗi đặt phòng:", err);
        alert("Lỗi kết nối máy chủ!");
    }
}

/* ==========================================================================
   MY BOOKINGS MANAGEMENT
   ========================================================================== */

async function fetchMyBookings() {
    const token = localStorage.getItem('token') || '';
    if (!token) return;

    try {
        const res = await fetch(`${API_BASE}/meetings/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
            myBookings = await res.json();
            renderMyBookings();
        }
    } catch (err) {
        console.error("Lỗi lấy danh sách lịch họp:", err);
    }
}

function renderMyBookings() {
    const tbody = document.getElementById('myBookingsTableBody');
    if (!tbody) return;

    if (!myBookings || myBookings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#94a3b8;">Bạn chưa đăng ký lịch họp nào.</td></tr>';
        return;
    }

    tbody.innerHTML = myBookings.map(b => {
        const startTime = new Date(b.start_time).toLocaleString('vi-VN');
        const endTime = new Date(b.end_time).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });

        return `
            <tr>
                <td><strong>${b.title || b.roomName || 'Cuộc họp'}</strong></td>
                <td>${startTime} - ${endTime}</td>
                <td><span class="tag" style="background:#dcfce7; color:#15803d;">${b.status || 'Đã xác nhận'}</span></td>
                <td><button class="btn-admin-action btn-admin-delete" onclick="cancelBooking(${b.id})">Hủy đặt</button></td>
            </tr>
        `;
    }).join('');
}

async function cancelBooking(meetingId) {
    if (!confirm("Bạn có chắc chắn muốn hủy lịch họp này?")) return;

    const token = localStorage.getItem('token') || '';
    try {
        const res = await fetch(`${API_BASE}/meetings/${meetingId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
            alert("Đã hủy lịch họp!");
            fetchMyBookings();
            fetchRooms(localStorage.getItem('role') === 'admin');
        } else {
            const err = await res.json();
            alert(`Lỗi hủy phòng: ${err.detail || 'Không thể hủy!'}`);
        }
    } catch (err) {
        alert("Lỗi kết nối máy chủ!");
    }
}

/* ==========================================================================
   SEARCH & FILTERING
   ========================================================================== */

function handleSearch() { applyFilters(); }
function filterToday() { alert("Đã đồng bộ lịch họp hôm nay!"); }

function applyFilters() {
    const searchInput = document.getElementById('searchInput');
    const capSelect = document.getElementById('capacitySelect');

    const query = searchInput ? searchInput.value.toLowerCase() : '';
    const cap = capSelect ? capSelect.value : 'all';

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
    if (btn) btn.classList.add('active');

    const role = localStorage.getItem('role') || 'user';
    if (amenity === 'all') {
        renderRooms(allRooms, role === 'admin');
    } else {
        const filtered = allRooms.filter(r => {
            if (!r.amenities) return false;
            if (Array.isArray(r.amenities)) return r.amenities.includes(amenity);
            if (typeof r.amenities === 'string') return r.amenities.includes(amenity);
            return false;
        });
        renderRooms(filtered, role === 'admin');
    }
}

/* ==========================================================================
   ADMIN ACTIONS (ADD / EDIT / DELETE ROOMS)
   ========================================================================== */

function openRoomModal() {
    const modalTitle = document.getElementById('modalTitle');
    if (modalTitle) modalTitle.innerText = 'Thêm Phòng Họp Mới';

    const editId = document.getElementById('editRoomId');
    if (editId) editId.value = '';

    const form = document.getElementById('roomForm');
    if (form) form.reset();

    const modal = document.getElementById('roomModal');
    if (modal) modal.style.display = 'flex';
}

function openEditModal(roomId) {
    const room = allRooms.find(r => r.id === roomId);
    if (!room) return;

    const modalTitle = document.getElementById('modalTitle');
    if (modalTitle) modalTitle.innerText = 'Sửa Thông Tin Phòng Họp';

    document.getElementById('editRoomId').value = room.id;
    document.getElementById('roomName').value = room.name;
    document.getElementById('roomLocation').value = room.location || '';
    document.getElementById('roomCapacity').value = room.capacity || '';
    
    let amenitiesStr = '';
    if (room.amenities) {
        if (typeof room.amenities === 'string') {
            try {
                let parsed = JSON.parse(room.amenities);
                amenitiesStr = Array.isArray(parsed) ? parsed.join(', ') : room.amenities;
            } catch (e) {
                amenitiesStr = room.amenities;
            }
        } else if (Array.isArray(room.amenities)) {
            amenitiesStr = room.amenities.join(', ');
        }
    }
    
    document.getElementById('roomAmenities').value = amenitiesStr;
    const modal = document.getElementById('roomModal');
    if (modal) modal.style.display = 'flex';
}

function closeRoomModal() {
    const modal = document.getElementById('roomModal');
    if (modal) modal.style.display = 'none';
}

async function handleFormSubmit(e) {
    e.preventDefault();
    const token = localStorage.getItem('token') || '';
    const editId = document.getElementById('editRoomId').value;

    const payload = {
        name: document.getElementById('roomName').value,
        location: document.getElementById('roomLocation').value,
        capacity: parseInt(document.getElementById('roomCapacity').value) || 0,
        amenities: document.getElementById('roomAmenities').value.split(',').map(s => s.trim()).filter(Boolean),
        is_available: true
    };

    const method = editId ? 'PUT' : 'POST';
    const url = editId ? `${API_BASE}/rooms/${editId}/` : `${API_BASE}/rooms/`;

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
            alert(editId ? "Cập nhật phòng thành công!" : "Thêm phòng thành công!");
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
        const res = await fetch(`${API_BASE}/rooms/${roomId}/`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
            allRooms = allRooms.filter(r => r.id !== roomId);
            const role = localStorage.getItem('role') || 'user';
            renderRooms(allRooms, role === 'admin');
            updateStats(allRooms);
            alert("Xóa phòng thành công!");
        } else {
            const err = await res.json();
            alert(err.detail || "Thao tác thất bại!");
        }
    } catch (err) {
        alert("Lỗi máy chủ!");
    }
}

function logout() {
    localStorage.clear();
    window.location.href = 'index.html';
}

/* ==========================================================================
   GLOBAL EXPORTS (Đảm bảo HTML inline event handlers gọi thành công)
   ========================================================================== */
window.toggleSidebar = toggleSidebar;
window.switchToOverview = switchToOverview;
window.switchMainTab = switchMainTab;
window.navigateToSettings = navigateToSettings;
window.scrollToRooms = scrollToRooms;
window.toggleNotificationPopup = toggleNotificationPopup;
window.openScheduleModal = openScheduleModal;
window.closeScheduleModal = closeScheduleModal;
window.openBookModal = openBookModal;
window.closeBookModal = closeBookModal;
window.handleBookSubmit = handleBookSubmit;
window.cancelBooking = cancelBooking;
window.handleSearch = handleSearch;
window.filterToday = filterToday;
window.applyFilters = applyFilters;
window.setFilter = setFilter;
window.openRoomModal = openRoomModal;
window.openEditModal = openEditModal;
window.closeRoomModal = closeRoomModal;
window.handleFormSubmit = handleFormSubmit;
window.deleteRoom = deleteRoom;
window.logout = logout;