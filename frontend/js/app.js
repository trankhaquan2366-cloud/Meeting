const API_BASE = "http://localhost:8000/api";
let allRooms = [];
let myBookings = [];
let selectedRoomId = null;

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

    // Set giá trị mặc định cho ô chọn ngày trong Modal Đặt phòng
    setDefaultBookingTimes();

    // Ẩn / hiện nút thêm phòng theo quyền Admin
    if (isAdmin) {
        const btn1 = document.getElementById('addRoomBtnOverview');
        const btn2 = document.getElementById('addRoomBtnRooms');
        if (btn1) btn1.style.display = 'block';
        if (btn2) btn2.style.display = 'block';
    }

    // Tải dữ liệu ban đầu
    fetchRooms(isAdmin).then(fetchMyBookings);
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

function formatDateInput(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function formatTimeInput(date) {
    return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}

function setDefaultBookingTimes() {
    const start = new Date();
    if (start.getMinutes() || start.getSeconds() || start.getMilliseconds()) {
        start.setHours(start.getHours() + 1, 0, 0, 0);
    }

    const end = new Date(start);
    end.setHours(end.getHours() + 1);

    const dateInput = document.querySelector('#bookingModal input[name="meeting_date"]');
    const startInput = document.querySelector('#bookingModal input[name="start_time"]');
    const endInput = document.querySelector('#bookingModal input[name="end_time"]');
    if (dateInput) dateInput.value = formatDateInput(start);
    if (startInput) startInput.value = formatTimeInput(start);
    if (endInput) endInput.value = formatTimeInput(end);
}

async function openQuickBooking() {
    const isAdmin = localStorage.getItem('role') === 'admin';
    if (!allRooms.length) await fetchRooms(isAdmin);

    const room = allRooms.find(item => item.is_active !== false);
    if (!room) {
        alert('Hiện chưa có phòng họp đang hoạt động.');
        return;
    }

    openBookingModal(room.id);
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
                        <button class="btn-book ${isAvailable ? '' : 'disabled'}" ${isAvailable ? `onclick="openBookingModal(${room.id})"` : 'disabled'}>
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

/* --- MỞ & ĐÓNG MODAL ĐẶT PHÒNG (FIGMA UI) --- */
function openBookingModal(roomId) {
    const room = allRooms.find(r => r.id === roomId && r.is_active !== false);
    if (!room) return;

    setDefaultBookingTimes();
    selectBookingRoom(room);
    renderRoomOptions();

    const modal = document.getElementById('bookingModal');
    if (modal) modal.style.display = 'flex';
}

function selectBookingRoom(room) {
    selectedRoomId = room.id;
    const roomNameEl = document.querySelector('#bookingModal .room-name');
    const roomMetaEl = document.querySelector('#bookingModal .room-meta');
    if (roomNameEl) roomNameEl.innerText = room.name;
    if (roomMetaEl) {
        roomMetaEl.innerHTML = `${room.capacity || 10} người · <span class="status-available">Đang hoạt động</span>`;
    }

    const roomMenu = document.getElementById('roomMenu');
    const roomButton = document.getElementById('room-select');
    if (roomMenu) roomMenu.hidden = true;
    if (roomButton) {
        roomButton.classList.remove('is-open');
        roomButton.setAttribute('aria-expanded', 'false');
    }
}

function renderRoomOptions() {
    const roomMenu = document.getElementById('roomMenu');
    if (!roomMenu) return;

    roomMenu.replaceChildren();
    allRooms.filter(room => room.is_active !== false).forEach(room => {
        const option = document.createElement('button');
        option.type = 'button';
        option.className = `room-option${room.id === selectedRoomId ? ' selected' : ''}`;
        option.setAttribute('role', 'option');
        option.setAttribute('aria-selected', String(room.id === selectedRoomId));
        option.textContent = `${room.name} · ${room.capacity || 10} người`;
        option.addEventListener('click', () => selectBookingRoom(room));
        roomMenu.appendChild(option);
    });
}

function toggleRoomMenu() {
    const roomMenu = document.getElementById('roomMenu');
    const roomButton = document.getElementById('room-select');
    if (!roomMenu || !roomButton) return;

    roomMenu.hidden = !roomMenu.hidden;
    roomButton.classList.toggle('is-open', !roomMenu.hidden);
    roomButton.setAttribute('aria-expanded', String(!roomMenu.hidden));
}

async function findAvailableTime() {
    if (!selectedRoomId) return;

    const form = document.querySelector('#bookingModal .booking-form');
    const dateInput = form.querySelector('[name="meeting_date"]');
    const startInput = form.querySelector('[name="start_time"]');
    const endInput = form.querySelector('[name="end_time"]');
    const button = document.getElementById('findAvailabilityBtn');
    const message = document.getElementById('availabilityMessage');
    const results = document.getElementById('availabilityResults');
    const meetingDate = dateInput.value;
    const requestedStart = new Date(`${meetingDate}T${startInput.value}:00`);
    const requestedEnd = new Date(`${meetingDate}T${endInput.value}:00`);
    if (requestedEnd <= requestedStart) requestedEnd.setDate(requestedEnd.getDate() + 1);

    const duration = requestedEnd.getTime() - requestedStart.getTime();
    const workEnd = new Date(`${meetingDate}T17:00:00`);
    if (!duration || requestedStart >= workEnd) {
        message.textContent = 'Không còn khung giờ phù hợp trong giờ làm việc hôm nay.';
        message.classList.add('is-error');
        message.hidden = false;
        return;
    }

    button.disabled = true;
    message.classList.remove('is-error');
    message.textContent = 'Đang tìm khung giờ trống...';
    message.hidden = false;
    results.replaceChildren();

    try {
        const availableSlots = [];
        for (let candidate = new Date(requestedStart); candidate.getTime() + duration <= workEnd.getTime(); candidate.setMinutes(candidate.getMinutes() + 30)) {
            const candidateEnd = new Date(candidate.getTime() + duration);
            const params = new URLSearchParams({
                start_time: `${formatDateInput(candidate)}T${formatTimeInput(candidate)}:00`,
                end_time: `${formatDateInput(candidateEnd)}T${formatTimeInput(candidateEnd)}:00`,
            });
            const response = await fetch(`${API_BASE}/rooms/available?${params}`);
            if (!response.ok) throw new Error('Không thể kiểm tra lịch phòng.');

            const availableRooms = await response.json();
            if (availableRooms.some(room => room.id === selectedRoomId)) {
                availableSlots.push({
                    date: formatDateInput(candidate),
                    start: formatTimeInput(candidate),
                    end: formatTimeInput(candidateEnd),
                });
                if (availableSlots.length === 5) break;
            }
        }

        if (availableSlots.length) {
            message.textContent = `Tìm thấy ${availableSlots.length} khung giờ trống. Chọn giờ bạn muốn:`;
            availableSlots.forEach(slot => {
                const option = document.createElement('button');
                option.type = 'button';
                option.className = 'time-suggestion';
                option.textContent = `${slot.start}–${slot.end}`;
                option.addEventListener('click', () => {
                    dateInput.value = slot.date;
                    startInput.value = slot.start;
                    endInput.value = slot.end;
                    results.querySelectorAll('.time-suggestion').forEach(item => item.classList.remove('selected'));
                    option.classList.add('selected');
                    message.textContent = `Đã chọn ${slot.start}–${slot.end}.`;
                });
                results.appendChild(option);
            });
        } else {
            message.textContent = 'Không tìm thấy khung giờ trống phù hợp trong ngày.';
            message.classList.add('is-error');
        }
    } catch (error) {
        console.error('Lỗi tìm giờ trống:', error);
        message.textContent = 'Không thể kiểm tra lịch phòng. Vui lòng thử lại.';
        message.classList.add('is-error');
    } finally {
        button.disabled = false;
    }
}

function closeBookingModal() {
    const modal = document.getElementById('bookingModal');
    if (modal) modal.style.display = 'none';
}

/* Alias hỗ trợ tương thích mã cũ */
function openBookModal(roomId) { openBookingModal(roomId); }
function closeBookModal() { closeBookingModal(); }

/* --- XỬ LÝ GỬI LỊCH ĐẶT PHÒNG --- */
async function handleBookingSubmit(e) {
    e.preventDefault();

    const form = e.target;
    const title = form.querySelector('[name="title"]')?.value || 'Cuộc họp';
    const meetingDate = form.querySelector('[name="meeting_date"]')?.value || new Date().toISOString().split('T')[0];
    const startTime = form.querySelector('[name="start_time"]')?.value || '09:00';
    const endTime = form.querySelector('[name="end_time"]')?.value || '10:00';
    const description = form.querySelector('[name="description"]')?.value || '';

    const recurrenceType = document.getElementById('recurrence-select')?.value || 'none';
    const isRecurring = recurrenceType !== 'none';

    const start = new Date(`${meetingDate}T${startTime}:00`);
    const end = new Date(`${meetingDate}T${endTime}:00`);
    if (end <= start) end.setDate(end.getDate() + 1);

    let recurrenceEndDate = null;
    if (recurrenceType === 'monthly') {
        recurrenceEndDate = new Date(start);
        recurrenceEndDate.setMonth(recurrenceEndDate.getMonth() + 1);
    } else if (recurrenceType === 'until_changed') {
        recurrenceEndDate = new Date(start);
        recurrenceEndDate.setFullYear(recurrenceEndDate.getFullYear() + 1);
    }

    const payload = {
        title: title,
        description: description || "Đặt từ giao diện web",
        room_id: parseInt(selectedRoomId),
        start_time: `${formatDateInput(start)}T${formatTimeInput(start)}:00`,
        end_time: `${formatDateInput(end)}T${formatTimeInput(end)}:00`,
        is_recurring: isRecurring,
        recurrence_type: recurrenceType,
        recurrence_end_date: recurrenceEndDate ? `${formatDateInput(recurrenceEndDate)}T${formatTimeInput(recurrenceEndDate)}:00` : null
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
            closeBookingModal();
            
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

function handleBookSubmit(e) { handleBookingSubmit(e); }

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

    const statusLabels = {
        scheduled: { label: 'Đã lên lịch', className: 'booking-status-scheduled' },
        confirmed: { label: 'Đã xác nhận', className: 'booking-status-scheduled' },
        in_progress: { label: 'Đang diễn ra', className: 'booking-status-progress' },
        completed: { label: 'Đã hoàn thành', className: 'booking-status-completed' },
        canceled: { label: 'Đã hủy', className: 'booking-status-canceled' },
    };
    const timeOptions = { hour: '2-digit', minute: '2-digit', hour12: false };

    tbody.innerHTML = myBookings.map(b => {
        const roomName = allRooms.find(room => room.id === b.room_id)?.name || b.room_name || `Phòng ${b.room_id}`;
        const start = new Date(b.start_time);
        const end = new Date(b.end_time);
        const dateLabel = start.toLocaleDateString('vi-VN', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
        });
        const timeRange = `${start.toLocaleTimeString('vi-VN', timeOptions)} – ${end.toLocaleTimeString('vi-VN', timeOptions)}`;
        const status = statusLabels[b.status] || { label: 'Không xác định', className: 'booking-status-unknown' };

        return `
            <tr>
                <td><strong>${escapeHtml(roomName)}</strong></td>
                <td><div class="booking-datetime"><span class="booking-date">${dateLabel}</span><strong class="booking-time">${timeRange}</strong></div></td>
                <td><span class="booking-status ${status.className}">${status.label}</span></td>
                <td><button class="btn-admin-action btn-admin-delete" onclick="cancelBooking(${b.id})">Hủy đặt</button></td>
            </tr>
        `;
    }).join('');
}

function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, character => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
    })[character]);
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
                "Authorization": `Bearer ${localStorage.getItem("token")}`
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
   GLOBAL EXPORTS
   ========================================================================== */
window.toggleSidebar = toggleSidebar;
window.switchToOverview = switchToOverview;
window.switchMainTab = switchMainTab;
window.navigateToSettings = navigateToSettings;
window.scrollToRooms = scrollToRooms;
window.toggleNotificationPopup = toggleNotificationPopup;
window.toggleRoomMenu = toggleRoomMenu;
window.findAvailableTime = findAvailableTime;
window.openScheduleModal = openScheduleModal;
window.closeScheduleModal = closeScheduleModal;
window.openBookingModal = openBookingModal;
window.closeBookingModal = closeBookingModal;
window.openBookModal = openBookModal;
window.closeBookModal = closeBookModal;
window.handleBookingSubmit = handleBookingSubmit;
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