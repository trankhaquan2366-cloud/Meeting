/* ==========================================================================
   GLOBAL CONFIGURATION & STATE MANAGEMENT
   ========================================================================== */
const API_BASE = "http://localhost:8000/api";
let allRooms = [];
let myBookings = [];
let selectedRoomId = null;
let equipmentAvailabilityTimer = null;

// Hàm bổ trợ lấy Auth Token
function getAuthToken() {
    return localStorage.getItem('token') || localStorage.getItem('access_token') || '';
}

// Xử lý Escape HTML an toàn
function escapeHtml(value) {
    if (!value) return '';
    return String(value).replace(/[&<>"']/g, character => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
    })[character]);
}

/* ==========================================================================
   INITIALIZATION & DOM LOAD
   ========================================================================== */
document.addEventListener('DOMContentLoaded', () => {
    const token = getAuthToken();
    const isMeetingPreview = new URLSearchParams(location.search).get('preview') === 'meeting';
    if (!token && !isMeetingPreview) {
        window.location.href = 'login.html';
        return;
    }

    const userName = localStorage.getItem('user_name') || 'Nguyễn Minh Tuấn';
    const role = localStorage.getItem('role') || 'user';
    const isAdmin = role === 'admin';

    // Cập nhật thông tin người dùng trên giao diện
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

    // Hiển thị ngày tháng
    const now = new Date();
    const dateStr = `Thứ ${now.getDay() + 1}, ${now.getDate()} tháng ${now.getMonth() + 1} năm ${now.getFullYear()}`;
    const currentDateText = document.getElementById('currentDateText');
    if (currentDateText) currentDateText.innerText = `${dateStr} · Đang hiển thị danh sách phòng`;

    const filterDateLabel = document.getElementById('filterDateLabel');
    if (filterDateLabel) filterDateLabel.innerText = `${now.getDate()}/${now.getMonth() + 1}/${now.getFullYear()}`;

    // Cài đặt thời gian mặc định cho Modal
    setDefaultBookingTimes();

    // Hiển thị nút quản trị nếu là Admin
    if (isAdmin) {
        const btn1 = document.getElementById('addRoomBtnOverview');
        const btn2 = document.getElementById('addRoomBtnRooms');
        const addEqBtn = document.getElementById('addEquipmentBtn');
        const adminEqSection = document.getElementById('adminEquipmentSection');
        if (btn1) btn1.style.display = 'block';
        if (btn2) btn2.style.display = 'block';
        if (addEqBtn) addEqBtn.style.display = 'block';
        if (adminEqSection) adminEqSection.style.display = 'block';
    }

    // Tải dữ liệu ban đầu
    fetchRooms(isAdmin).then(fetchMyBookings);
    setDefaultEquipmentAvailabilityTimes();
    if (isAdmin) {
        fetchAdminEquipments();
    }
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
    } else if (tabName === 'equipments') {
        const view = document.getElementById('viewEquipments');
        if (view) view.style.display = 'block';
        if (searchContainer) searchContainer.style.display = 'none';
        fetchEquipmentAvailability();
        const role = localStorage.getItem('role') || 'user';
        if (role === 'admin') {
            fetchAdminEquipments();
        }
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

/* ==========================================================================
   NOTIFICATION MANAGEMENT
   ========================================================================== */

async function fetchNotifications() {
    const token = getAuthToken();
    if (!token) return;

    try {
        const res = await fetch(`${API_BASE}/notifications/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
            const notifications = await res.json();
            renderNotifications(notifications);
        }
    } catch (err) {
        console.error("Lỗi lấy danh sách thông báo:", err);
    }
}

function renderNotifications(notifications) {
    const popup = document.getElementById('notificationPopup');
    if (!popup) return;

    if (!notifications || notifications.length === 0) {
        popup.innerHTML = '<div style="padding: 16px; color: #94a3b8; text-align: center; font-size: 0.85rem;">Không có thông báo nào.</div>';
        updateNotificationDot(0);
        return;
    }

    const unreadCount = notifications.filter(n => !n.is_read).length;

    // Chỉ cập nhật chấm đỏ khi popup ĐANG ĐÓNG (fetch nền / trang tải)
    // Khi popup đang mở thì không tự động ẩn chấm đỏ qua hàm này
    const popupVisible = popup.style.display !== 'none';
    if (!popupVisible) {
        updateNotificationDot(unreadCount);
    }

    popup.innerHTML = `
        <div style="padding: 12px 16px; font-weight: 600; font-size: 0.9rem; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
            <span>Thông báo</span>
            ${unreadCount > 0 ? `<span style="font-size: 0.75rem; background: #e0e7ff; color: #3730a3; padding: 2px 8px; border-radius: 9999px;">${unreadCount} chưa đọc</span>` : ''}
        </div>
        <div style="max-height: 320px; overflow-y: auto;">
            ${notifications.map(n => `
                <div style="padding: 12px 16px; border-bottom: 1px solid #f1f5f9; background-color: ${n.is_read ? '#ffffff' : '#f0fdf4'}; cursor: pointer;">
                    <div style="font-weight: 600; font-size: 0.85rem; color: #0f172a; margin-bottom: 4px;">${escapeHtml(n.title)}</div>
                    <div style="font-size: 0.8rem; color: #475569; line-height: 1.4;">${escapeHtml(n.content)}</div>
                </div>
            `).join('')}
        </div>
    `;
}

// Hiển thị hoặc ẩn chấm đỏ nhấp nháy trên nút chuông
function updateNotificationDot(unreadCount) {
    const dot = document.getElementById('notificationDot');
    if (!dot) return;
    dot.style.display = unreadCount > 0 ? 'block' : 'none';
}

// Toggle popup thông báo: mở thì ẩn chấm đỏ ngay + load data; đóng thì ẩn popup
function toggleNotificationPopup() {
    const popup = document.getElementById('notificationPopup');
    if (!popup) return;

    const isHidden = popup.style.display === 'none' || !popup.style.display;
    popup.style.display = isHidden ? 'block' : 'none';

    if (isHidden) {
        // Ẩn chấm đỏ ngay khi người dùng mở popup (đã "xem" thông báo)
        updateNotificationDot(0);
        fetchNotifications();
    }
}

// Đóng popup khi bấm ra ngoài vùng notification-wrapper
document.addEventListener('click', function (e) {
    const wrapper = document.querySelector('.notification-wrapper');
    const popup = document.getElementById('notificationPopup');
    if (!wrapper || !popup) return;
    if (!wrapper.contains(e.target) && popup.style.display !== 'none') {
        popup.style.display = 'none';
    }
});

// Fetch khi trang tải để hiển thị chấm đỏ nếu có thông báo chưa đọc
document.addEventListener('DOMContentLoaded', () => {
    fetchNotifications();
});

window.fetchNotifications = fetchNotifications;
window.updateNotificationDot = updateNotificationDot;

/* ==========================================================================
   MANUAL GUEST INVITE (nhập tên + gmail người ngoài hệ thống)
   ========================================================================== */
// Mảng lưu danh sách khách mời thủ công
let _manualGuests = [];

function addManualGuest() {
    const nameInput  = document.getElementById('inviteGuestName');
    const emailInput = document.getElementById('inviteGuestEmail');
    if (!nameInput || !emailInput) return;

    const name  = nameInput.value.trim();
    const email = emailInput.value.trim();

    if (!name && !email) {
        nameInput.focus();
        return;
    }
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        emailInput.style.borderColor = '#ef4444';
        emailInput.focus();
        setTimeout(() => emailInput.style.borderColor = '', 1500);
        return;
    }

    // Tránh trùng email
    if (_manualGuests.find(g => g.email === email)) {
        emailInput.style.borderColor = '#f59e0b';
        setTimeout(() => emailInput.style.borderColor = '', 1500);
        return;
    }

    _manualGuests.push({ name, email });
    nameInput.value  = '';
    emailInput.value = '';
    nameInput.focus();
    renderManualGuestList();
}

function removeManualGuest(email) {
    _manualGuests = _manualGuests.filter(g => g.email !== email);
    renderManualGuestList();
}

function renderManualGuestList() {
    const container = document.getElementById('manualGuestList');
    if (!container) return;
    if (_manualGuests.length === 0) {
        container.innerHTML = '';
        return;
    }
    container.innerHTML = _manualGuests.map(g => `
        <span class="manual-guest-tag" title="${g.email}">
            ${g.name ? `<strong>${escapeHtml(g.name)}</strong>&nbsp;` : ''}
            <span style="opacity:0.75">${escapeHtml(g.email)}</span>
            <button type="button" onclick="removeManualGuest('${g.email}')" title="Xóa">✕</button>
        </span>
    `).join('');
}

// Cho phép nhấn Enter trên ô email để thêm nhanh + keyboard navigation cho suggestions
document.addEventListener('DOMContentLoaded', () => {
    const emailInput = document.getElementById('inviteGuestEmail');
    const nameInput  = document.getElementById('inviteGuestName');

    if (emailInput) {
        emailInput.addEventListener('keydown', e => {
            if (handleSuggestionKeydown(e)) return;
            if (e.key === 'Enter') { e.preventDefault(); addManualGuest(); }
        });
    }
    if (nameInput) {
        nameInput.addEventListener('keydown', e => {
            if (handleSuggestionKeydown(e)) return;
            if (e.key === 'Enter') { e.preventDefault(); emailInput?.focus(); }
        });
    }

    // Bấm ngoài vùng invite → ẩn suggestions
    document.addEventListener('click', e => {
        const wrapper = document.querySelector('.invite-manual-wrapper');
        if (wrapper && !wrapper.contains(e.target)) hideSuggestions();
    });
});

/* ---------- AUTOCOMPLETE LOGIC ---------- */
let _activeSugIndex = -1;

function onInviteInput() {
    const nameVal  = (document.getElementById('inviteGuestName')?.value  || '').trim().toLowerCase();
    const emailVal = (document.getElementById('inviteGuestEmail')?.value || '').trim().toLowerCase();
    const query    = nameVal || emailVal;

    if (!query || query.length < 1 || _allUsers.length === 0) {
        hideSuggestions();
        return;
    }

    // Lọc users khớp tên hoặc email, loại trừ người đã thêm
    const addedEmails = new Set(_manualGuests.map(g => g.email.toLowerCase()));
    const matches = _allUsers.filter(u => {
        if (addedEmails.has((u.email || '').toLowerCase())) return false;
        const fullName = (u.full_name || '').toLowerCase();
        const email    = (u.email || '').toLowerCase();
        return fullName.includes(query) || email.includes(query);
    }).slice(0, 8); // tối đa 8 gợi ý

    if (matches.length === 0) { hideSuggestions(); return; }

    renderSuggestions(matches, query);
}

function highlightMatch(text, query) {
    if (!query) return escapeHtml(text);
    const idx = text.toLowerCase().indexOf(query.toLowerCase());
    if (idx === -1) return escapeHtml(text);
    return escapeHtml(text.slice(0, idx))
        + `<mark>${escapeHtml(text.slice(idx, idx + query.length))}</mark>`
        + escapeHtml(text.slice(idx + query.length));
}

function renderSuggestions(users, query) {
    const list = document.getElementById('inviteSuggestions');
    if (!list) return;
    _activeSugIndex = -1;

    list.innerHTML = users.map((u, i) => {
        const initials = (u.full_name || u.email || '?')[0].toUpperCase();
        return `
        <li data-index="${i}" data-name="${escapeHtml(u.full_name || '')}" data-email="${escapeHtml(u.email || '')}"
            onmousedown="selectSuggestion('${escapeHtml(u.full_name || '')}', '${escapeHtml(u.email || '')}')">
            <div class="sug-avatar">${initials}</div>
            <div class="sug-info">
                <strong>${highlightMatch(u.full_name || 'Người dùng', query)}</strong>
                <span>${highlightMatch(u.email || '', query)}</span>
            </div>
        </li>`;
    }).join('');

    list.style.display = 'block';
}

function selectSuggestion(name, email) {
    const nameInput  = document.getElementById('inviteGuestName');
    const emailInput = document.getElementById('inviteGuestEmail');
    if (nameInput)  nameInput.value  = name;
    if (emailInput) emailInput.value = email;
    hideSuggestions();
    // Tự động thêm ngay khi chọn
    addManualGuest();
}

function hideSuggestions() {
    const list = document.getElementById('inviteSuggestions');
    if (list) { list.style.display = 'none'; list.innerHTML = ''; }
    _activeSugIndex = -1;
}

function handleSuggestionKeydown(e) {
    const list = document.getElementById('inviteSuggestions');
    if (!list || list.style.display === 'none') return false;
    const items = list.querySelectorAll('li');
    if (!items.length) return false;

    if (e.key === 'ArrowDown') {
        e.preventDefault();
        _activeSugIndex = Math.min(_activeSugIndex + 1, items.length - 1);
        items.forEach((li, i) => li.classList.toggle('active', i === _activeSugIndex));
        return true;
    }
    if (e.key === 'ArrowUp') {
        e.preventDefault();
        _activeSugIndex = Math.max(_activeSugIndex - 1, 0);
        items.forEach((li, i) => li.classList.toggle('active', i === _activeSugIndex));
        return true;
    }
    if (e.key === 'Enter' && _activeSugIndex >= 0) {
        e.preventDefault();
        const active = items[_activeSugIndex];
        if (active) selectSuggestion(active.dataset.name, active.dataset.email);
        return true;
    }
    if (e.key === 'Escape') {
        hideSuggestions();
        return true;
    }
    return false;
}

// Lấy danh sách guest thủ công để gửi cùng form (nếu cần)
function getManualGuests() { return [..._manualGuests]; }

// Reset khi đóng modal
function resetManualGuests() {
    _manualGuests = [];
    renderManualGuestList();
    hideSuggestions();
    const nameInput  = document.getElementById('inviteGuestName');
    const emailInput = document.getElementById('inviteGuestEmail');
    if (nameInput)  nameInput.value  = '';
    if (emailInput) emailInput.value = '';
}

window.addManualGuest    = addManualGuest;
window.removeManualGuest = removeManualGuest;
window.getManualGuests   = getManualGuests;
window.resetManualGuests = resetManualGuests;
window.onInviteInput     = onInviteInput;
window.selectSuggestion  = selectSuggestion;

/* ==========================================================================
   DATE & TIME FORMATTING UTILITIES (ĐÃ CẢI TIẾN TIẾNG VIỆT FIGMA UI)
   ========================================================================== */
function formatDateInput(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function formatTimeInput(date) {
    return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}

function formatDateTimeLocal(date) {
    return `${formatDateInput(date)}T${formatTimeInput(date)}`;
}

/**
 * Định dạng nhãn hiển thị thời gian Tiếng Việt (Ví dụ: 08:30 (8h30 sáng), 14:00 (14h chiều))
 */
function formatVietnameseTimeLabel(hour, minute) {
    const timeStr = `${String(hour).padStart(2, '0')}:${minute}`;
    let period = 'sáng';
    if (hour === 12) period = 'trưa';
    else if (hour > 12 && hour < 18) period = 'chiều';
    else if (hour >= 18) period = 'tối';

    const minText = minute === '00' ? '' : `${minute}`;
    return `${timeStr} (${hour}h${minText} ${period})`;
}

/**
 * Tạo danh sách mốc thời gian mỗi 30 phút từ 07:00 đến 21:00
 */
function buildViTimeOptions(selectEl, defaultTimeStr) {
    if (!selectEl) return;
    selectEl.innerHTML = '';
    
    for (let h = 7; h <= 21; h++) {
        for (let m of ['00', '30']) {
            if (h === 21 && m === '30') continue; // Giới hạn đến 21:00
            
            const valueStr = `${String(h).padStart(2, '0')}:${m}`;
            const opt = document.createElement('option');
            opt.value = valueStr;
            opt.textContent = formatVietnameseTimeLabel(h, m);
            if (defaultTimeStr && valueStr === defaultTimeStr) {
                opt.selected = true;
            }
            selectEl.appendChild(opt);
        }
    }
}

function syncHiddenStartTime(selectEl) {
    const hiddenInput = document.getElementById('startTimeHidden');
    if (hiddenInput && selectEl) {
        hiddenInput.value = selectEl.value;
    }
}

function updateDateDisplay(dateVal) {
    const label = document.getElementById('dateDisplayLabel');
    if (!label || !dateVal) return;
    const [y, m, d] = dateVal.split('-');
    const days = ['CN', 'Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7'];
    const dt = new Date(parseInt(y), parseInt(m) - 1, parseInt(d));
    label.textContent = `${days[dt.getDay()]} ${d}/${m}/${y}`;
}

function triggerDatePicker() {
    const inp = document.getElementById('meetingDateInput');
    if (!inp) return;
    inp.style.position = 'fixed';
    inp.style.opacity = '0';
    inp.style.width = '1px';
    inp.style.height = '1px';
    inp.style.pointerEvents = 'none';
    inp.showPicker ? inp.showPicker() : inp.click();
    inp.addEventListener('change', function onDateChange() {
        updateDateDisplay(inp.value);
        inp.removeEventListener('change', onDateChange);
    }, { once: true });
}

function setDefaultBookingTimes() {
    const now = new Date();
    let startHour = now.getHours();
    let startMin = now.getMinutes() < 30 ? '30' : '00';
    if (now.getMinutes() >= 30) startHour += 1;

    if (startHour < 7) startHour = 8;
    if (startHour > 20) startHour = 20;

    let endHour = startHour + 1;
    
    const startTimeStr = `${String(startHour).padStart(2, '0')}:${startMin}`;
    const endTimeStr = `${String(endHour).padStart(2, '0')}:${startMin}`;

    const dateInp = document.getElementById('meetingDateInput');
    if (dateInp) {
        dateInp.value = formatDateInput(now);
        updateDateDisplay(dateInp.value);
    }

    const startSel = document.getElementById('startTimeSelect');
    buildViTimeOptions(startSel, startTimeStr);

    const endSel = document.getElementById('endTimeSelect');
    buildViTimeOptions(endSel, endTimeStr);

    syncHiddenStartTime(startSel);
}

/* ==========================================================================
   ROOM MANAGEMENT & FETCHING
   ========================================================================== */
async function fetchRooms(isAdmin) {
    try {
        const token = getAuthToken();
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

    if (!rooms || rooms.length === 0) {
        const emptyHTML = '<p class="text-muted" style="padding: 16px;">Chưa có phòng họp nào trong hệ thống.</p>';
        if (gridOverview) gridOverview.innerHTML = emptyHTML;
        if (gridRooms) gridRooms.innerHTML = emptyHTML;
        return;
    }

    const htmlContent = rooms.map(room => {
        const isAvailable = room.is_available !== false && room.is_active !== false;
        const statusClass = isAvailable ? 'status-green' : 'status-red';
        const statusText = isAvailable ? '• Còn trống' : '• Đã đặt';

        let amenitiesHTML = '';
        if (room.amenities) {
            let amenitiesList = room.amenities;
            if (typeof amenitiesList === 'string') {
                try { amenitiesList = JSON.parse(amenitiesList); } 
                catch (e) { amenitiesList = [amenitiesList]; }
            }
            if (Array.isArray(amenitiesList)) {
                amenitiesHTML = amenitiesList.map(a => `<span class="tag">${getAmenityIcon(a)} ${escapeHtml(a)}</span>`).join(' ');
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
                    <img src="${room.image_url || 'https://images.unsplash.com/photo-1497366216548-37526070297c'}" alt="${escapeHtml(room.name)}">
                    <span class="status-badge ${statusClass}">${statusText}</span>
                </div>
                <div class="card-body">
                    <h3>${escapeHtml(room.name)}</h3>
                    <p class="location">📍 ${escapeHtml(room.location || 'Tầng 1')} | 👥 ${room.capacity || '10'} người</p>
                    <div class="amenities-tags">${amenitiesHTML}</div>
                    <div class="card-actions">
                        <button class="btn-schedule" onclick="openScheduleModal(${room.id})">Xem lịch</button>
                        <button class="btn-book ${isAvailable ? '' : 'disabled'}" ${isAvailable ? `onclick="openCreateMeeting({ roomId: ${room.id} })"` : 'disabled'}>
                            ${isAvailable ? 'Tạo cuộc họp' : 'Hết chỗ'}
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
    const availableCount = rooms.filter(r => r.is_available !== false && r.is_active !== false).length;
    const inUseCount = total - availableCount;
    const capacityPercent = total > 0 ? Math.round((inUseCount / total) * 100) : 0;

    const setTxt = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };

    setTxt('statTotal', total);
    setTxt('statAvailable', availableCount);
    setTxt('statInUse', inUseCount);
    setTxt('statCapacityText', `${capacityPercent}% công suất`);
    setTxt('statRatioText', `trong ${total} phòng`);

    setTxt('summaryAvailable', availableCount);
    setTxt('summaryInUse', inUseCount);
}

function getAmenityIcon(name) {
    const lower = (name || '').toLowerCase();
    if (lower.includes('màn hình') || lower.includes('tv') || lower.includes('display')) return '📺';
    if (lower.includes('wifi') || lower.includes('mạng') || lower.includes('internet')) return '📶';
    if (lower.includes('video') || lower.includes('camera') || lower.includes('webcam')) return '🎥';
    if (lower.includes('chiếu') || lower.includes('projector')) return '📽️';
    if (lower.includes('mic') || lower.includes('loa') || lower.includes('âm thanh') || lower.includes('sound')) return '🎙️';
    if (lower.includes('đồ uống') || lower.includes('nước') || lower.includes('trà') || lower.includes('cà phê') || lower.includes('coffee')) return '☕';
    if (lower.includes('bảng') || lower.includes('board') || lower.includes('flipchart')) return '📋';
    if (lower.includes('điều hòa') || lower.includes('máy lạnh') || lower.includes('ac')) return '❄️';
    return '✨';
}

function renderRoomAmenities(room) {
    const container = document.getElementById('roomAvailableAmenities');
    if (!container) return;

    if (!room) {
        container.innerHTML = '<span style="color: #94a3b8; font-size: 0.82rem; font-style: italic;">Chưa chọn phòng họp.</span>';
        return;
    }

    let list = room.amenities || [];
    if (typeof list === 'string') {
        try { list = JSON.parse(list); } 
        catch (e) { list = list.split(',').map(s => s.trim()).filter(Boolean); }
    }

    if (!Array.isArray(list) || list.length === 0) {
        container.innerHTML = `
            <div style="display:flex; align-items:center; gap:6px; color: #64748b; font-size: 0.82rem; font-style: italic;">
                <span>ℹ️ Phòng này chưa cấu hình tiện ích cố định.</span>
            </div>
        `;
        return;
    }

    container.innerHTML = list.map(item => `
        <span style="display: inline-flex; align-items: center; gap: 5px; background: #ffffff; color: #166534; border: 1px solid #86efac; border-radius: 9999px; padding: 4px 10px; font-size: 0.8rem; font-weight: 500; box-shadow: 0 1px 2px rgba(0,0,0,0.03);">
            <span>${getAmenityIcon(item)}</span>
            <span>${escapeHtml(item)}</span>
        </span>
    `).join('');
}

/* ==========================================================================
   PARTICIPANT MANAGEMENT
   ========================================================================== */
let _allUsers = []; // Cache danh sách người dùng để dùng cho autocomplete

async function fetchAndRenderParticipants() {
    const container = document.getElementById('participantListContainer');
    if (!container) return;

    const token = getAuthToken();
    try {
        const res = await fetch(`${API_BASE}/users/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) throw new Error("Không thể lấy danh sách người dùng");

        const users = await res.json();
        _allUsers = users || []; // Lưu cache

        if (!users || users.length === 0) {
            container.innerHTML = '<div style="color: #94a3b8; font-size: 0.82rem;">Chưa có người dùng khác trong hệ thống.</div>';
            return;
        }

        container.innerHTML = users.map(user => `
            <label style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 0.85rem; cursor: pointer; color: #1e293b;">
                <input type="checkbox" class="participant-checkbox" value="${user.id}">
                <span><strong>${escapeHtml(user.full_name || 'Người dùng')}</strong> (${escapeHtml(user.email)})</span>
            </label>
        `).join('');

    } catch (err) {
        console.error("Lỗi tải danh sách người dùng:", err);
        container.innerHTML = '<div style="color: #ef4444; font-size: 0.82rem;">❌ Không thể tải danh sách người dùng!</div>';
    }
}

function getSelectedParticipantIds() {
    const checkboxes = document.querySelectorAll('.participant-checkbox:checked');
    return Array.from(checkboxes).map(cb => parseInt(cb.value));
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

function openBookingModal(roomId) {
    if (typeof openCreateMeeting === 'function') {
        openCreateMeeting(roomId ? { roomId } : {});
        return;
    }
}

function closeBookingModal() {
    if (typeof closeCreateMeeting === 'function') closeCreateMeeting();
}

async function openQuickBooking() {
    if (typeof openCreateMeeting === 'function') {
        openCreateMeeting();
        return;
    }
}

function selectBookingRoom(room) {
    selectedRoomId = room.id;
    const roomNameEl = document.querySelector('#bookingModal .room-name');
    const roomMetaEl = document.querySelector('#bookingModal .room-meta');
    if (roomNameEl) roomNameEl.innerText = room.name;
    if (roomMetaEl) {
        roomMetaEl.innerHTML = `${room.capacity || 10} người · <span class="status-available">Đang hoạt động</span>`;
    }

    renderRoomAmenities(room);

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

    const dateInput = document.getElementById('meetingDateInput');
    const startInput = document.getElementById('startTimeSelect');
    const endInput = document.getElementById('endTimeSelect');
    const button = document.getElementById('findAvailabilityBtn');
    const message = document.getElementById('availabilityMessage');
    const results = document.getElementById('availabilityResults');
    const meetingDate = dateInput ? dateInput.value : '';

    if (!meetingDate) return;
    const requestedStart = new Date(`${meetingDate}T${startInput.value}:00`);
    const requestedEnd = new Date(`${meetingDate}T${endInput.value}:00`);
    if (requestedEnd <= requestedStart) requestedEnd.setDate(requestedEnd.getDate() + 1);

    const duration = requestedEnd.getTime() - requestedStart.getTime();
    const workEnd = new Date(`${meetingDate}T18:00:00`);
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
                    const di = document.getElementById('meetingDateInput');
                    if (di) { di.value = slot.date; updateDateDisplay(slot.date); }
                    const ss = document.getElementById('startTimeSelect');
                    if (ss) { ss.value = slot.start; syncHiddenStartTime(ss); }
                    const es = document.getElementById('endTimeSelect');
                    if (es) es.value = slot.end;
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

async function handleBookingSubmit(e) {
    e.preventDefault();

    const form = e.target;
    const title = form.querySelector('[name="title"]')?.value || 'Cuộc họp';
    const meetingDate = document.getElementById('meetingDateInput')?.value || new Date().toISOString().split('T')[0];
    const startTime = document.getElementById('startTimeSelect')?.value || '09:00';
    const endTime = document.getElementById('endTimeSelect')?.value || '10:00';
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
        recurrence_end_date: recurrenceEndDate ? `${formatDateInput(recurrenceEndDate)}T${formatTimeInput(recurrenceEndDate)}:00` : null,
        equipments: getSelectedEquipmentsData(),
        participant_ids: getSelectedParticipantIds()
    };

    const token = getAuthToken();

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

/* ==========================================================================
   MY BOOKINGS MANAGEMENT
   ========================================================================== */
async function fetchMyBookings() {
    const token = getAuthToken();
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
        cancelled: { label: 'Đã hủy', className: 'booking-status-canceled' },
    };
    const timeOptions = { hour: '2-digit', minute: '2-digit', hour12: false };

    tbody.innerHTML = myBookings.map(b => {
        const roomName = allRooms.find(room => room.id === b.room_id)?.name
            || b.room?.name
            || b.room_name
            || (b.room_id ? `Phòng ${b.room_id}` : 'Phòng chưa xác định');
        const start = new Date(b.start_time);
        const end = new Date(b.end_time);
        const hasValidDate = !Number.isNaN(start.getTime()) && !Number.isNaN(end.getTime());
        const dateLabel = hasValidDate
            ? start.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
            : 'Chưa có ngày';
        const timeRange = hasValidDate
            ? `${start.toLocaleTimeString('vi-VN', timeOptions)} – ${end.toLocaleTimeString('vi-VN', timeOptions)}`
            : 'Chưa có thời gian';
        const statusKey = String(b.status || '').toLowerCase();
        const status = statusLabels[statusKey] || { label: 'Không xác định', className: 'booking-status-unknown' };

        let equipmentsHTML = '';
        if (b.equipments && b.equipments.length > 0) {
            const eqList = b.equipments.map(eq => {
                const name = escapeHtml(eq.equipment_name || 'Thiết bị');
                return `${name} (x${eq.quantity})`;
            }).join(', ');

            equipmentsHTML = `
                <div class="booking-equipment-summary">
                    Thiết bị: ${eqList}
                </div>
            `;
        }

        return `
            <tr>
                <td class="booking-room-cell">
                    <strong class="booking-room-name">${escapeHtml(roomName)}</strong>
                    <span class="booking-meeting-title">${escapeHtml(b.title || 'Cuộc họp')}</span>
                    ${equipmentsHTML}
                </td>
                <td>
                    <div class="booking-datetime">
                        <span class="booking-date">${dateLabel}</span>
                        <strong class="booking-time">${timeRange}</strong>
                    </div>
                </td>
                <td><span class="booking-status ${status.className}">${status.label}</span></td>
                <td class="booking-action-cell"><button class="booking-cancel-button" type="button" onclick="cancelBooking(${b.id})">Hủy đặt</button></td>
            </tr>
        `;
    }).join('');
}

async function cancelBooking(meetingId) {
    if (!confirm("Bạn có chắc chắn muốn hủy lịch họp này?")) return;

    const token = getAuthToken();
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
    const token = getAuthToken();
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
                "Authorization": `Bearer ${token}`
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

    const token = getAuthToken();

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
    window.location.href = 'login.html';
}

/* ==========================================================================
   EQUIPMENT MANAGEMENT & SELECTION
   ========================================================================== */
function setDefaultEquipmentAvailabilityTimes() {
    const startInput = document.getElementById('equipmentStartTime');
    const endInput = document.getElementById('equipmentEndTime');
    if (!startInput || !endInput) return;

    const now = new Date();
    const end = new Date(now.getTime() + 60 * 60 * 1000);
    startInput.value = formatDateTimeLocal(now);
    endInput.value = formatDateTimeLocal(end);
}

function scheduleEquipmentAvailabilityFetch() {
    clearTimeout(equipmentAvailabilityTimer);
    equipmentAvailabilityTimer = setTimeout(fetchEquipmentAvailability, 250);
}

async function fetchEquipmentAvailability() {
    const tbody = document.getElementById('equipmentAvailabilityTableBody');
    if (!tbody) return;

    const params = new URLSearchParams();
    const startTime = document.getElementById('equipmentStartTime')?.value;
    const endTime = document.getElementById('equipmentEndTime')?.value;
    const category = document.getElementById('equipmentCategoryFilter')?.value.trim();
    const search = document.getElementById('equipmentSearchFilter')?.value.trim();

    if (startTime) params.set('start_time', `${startTime}:00`);
    if (endTime) params.set('end_time', `${endTime}:00`);
    if (category) params.set('category', category);
    if (search) params.set('search', search);

    tbody.innerHTML = '<tr><td colspan="7" class="equipment-table-message">Đang cập nhật...</td></tr>';
    try {
        const token = getAuthToken();
        const res = await fetch(`${API_BASE}/equipments/availability?${params.toString()}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error('Không thể tải trạng thái thiết bị');

        const equipments = await res.json();
        if (!equipments.length) {
            tbody.innerHTML = '<tr><td colspan="7" class="equipment-table-message">Không tìm thấy thiết bị phù hợp.</td></tr>';
            return;
        }

        tbody.innerHTML = equipments.map(item => {
            const isInactive = item.is_active === false;
            const isAvailable = item.available_qty > 0;
            const badgeClass = isInactive ? 'maintenance' : (isAvailable ? 'available' : 'booked-out');
            const badgeText = isInactive ? 'Đang bảo trì' : (isAvailable ? 'Có sẵn' : 'Đã đặt hết');
            return `
                <tr>
                    <td>${escapeHtml(item.code || '—')}</td>
                    <td>${escapeHtml(item.name)}</td>
                    <td>${escapeHtml(item.category || '—')}</td>
                    <td>${item.total_qty}</td>
                    <td>${item.booked_qty}</td>
                    <td>${item.available_qty}</td>
                    <td><span class="equipment-status-badge ${badgeClass}">${badgeText}</span></td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        console.error('Lỗi tải trạng thái thiết bị:', err);
        tbody.innerHTML = '<tr><td colspan="7" class="equipment-table-message error">Không thể tải trạng thái thiết bị.</td></tr>';
    }
}

async function fetchAndRenderEquipments() {
    const container = document.getElementById('equipmentListContainer');
    if (!container) return;

    const token = getAuthToken();
    try {
        const res = await fetch(`${API_BASE}/equipments/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) throw new Error("Không thể lấy danh sách thiết bị");

        const equipments = await res.json();
        const activeEquipments = equipments.filter(eq => eq.is_active !== false);

        if (!activeEquipments || activeEquipments.length === 0) {
            container.innerHTML = '<div class="equipment-empty">📭 Hiện không có thiết bị bổ sung trong kho để mượn thêm.</div>';
            return;
        }

        container.innerHTML = activeEquipments.map(item => `
            <div class="eq-card" id="eq-card-${item.id}">
                <label class="eq-label">
                    <input type="checkbox"
                           class="eq-checkbox"
                           value="${item.id}"
                           onchange="toggleEquipmentQtyInput(this, ${item.id})">
                    <div class="eq-info">
                        <span class="eq-name">${escapeHtml(item.name)}</span>
                        <span class="eq-stock">Kho: ${item.total_qty || '?'} cái</span>
                    </div>
                </label>
                <div class="eq-qty-group">
                    <span class="eq-qty-label">SL</span>
                    <input type="number"
                           id="eq-qty-${item.id}"
                           value="1"
                           min="1"
                           max="${item.total_qty || 99}"
                           disabled
                           class="eq-qty-input">
                </div>
            </div>
        `).join('');

    } catch (err) {
        console.error("Lỗi tải danh sách thiết bị:", err);
        container.innerHTML = '<div class="equipment-empty" style="color:#ef4444;">❌ Lỗi tải danh sách thiết bị!</div>';
    }
}

function toggleEquipmentQtyInput(checkbox, eqId) {
    const qtyInput = document.getElementById(`eq-qty-${eqId}`);
    if (!qtyInput) return;

    if (checkbox.checked) {
        qtyInput.disabled = false;
        qtyInput.focus();
    } else {
        qtyInput.disabled = true;
        qtyInput.value = 1;
    }
}

function getSelectedEquipmentsData() {
    const selected = [];
    const checkboxes = document.querySelectorAll('.eq-checkbox:checked');

    checkboxes.forEach(cb => {
        const eqId = parseInt(cb.value);
        const qtyInput = document.getElementById(`eq-qty-${eqId}`);
        const qty = qtyInput ? (parseInt(qtyInput.value) || 1) : 1;

        selected.push({
            equipment_id: eqId,
            quantity: qty
        });
    });

    return selected;
}

/* ==========================================================================
   ADMIN EQUIPMENT MANAGEMENT (CRUD & TOGGLE)
   ========================================================================== */
let adminEquipmentsCache = [];

async function fetchAdminEquipments() {
    const tbody = document.getElementById('adminEquipmentTableBody');
    if (!tbody) return;

    const token = getAuthToken();
    tbody.innerHTML = '<tr><td colspan="6" class="equipment-table-message">Đang tải danh sách Admin...</td></tr>';
    try {
        const res = await fetch(`${API_BASE}/equipments/?include_inactive=true`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (!res.ok) throw new Error('Không thể tải danh sách thiết bị cho Admin');

        const equipments = await res.json();
        adminEquipmentsCache = equipments;

        if (!equipments.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="equipment-table-message">Chưa có thiết bị nào trong hệ thống.</td></tr>';
            return;
        }

        tbody.innerHTML = equipments.map(item => {
            const isChecked = item.is_active !== false;
            return `
                <tr>
                    <td>${escapeHtml(item.code || '—')}</td>
                    <td>${escapeHtml(item.name)}</td>
                    <td>${escapeHtml(item.category || '—')}</td>
                    <td><strong>${item.total_qty}</strong></td>
                    <td>
                        <label class="switch" title="${isChecked ? 'Đang hoạt động' : 'Tắt / Bảo trì'}">
                            <input type="checkbox" ${isChecked ? 'checked' : ''} onchange="toggleEquipmentActive(${item.id}, this.checked)">
                            <span class="slider"></span>
                        </label>
                    </td>
                    <td>
                        <div style="display: flex; gap: 8px;">
                            <button type="button" class="btn-action edit" onclick="openEditEquipmentModal(${item.id})" style="padding: 4px 10px; font-size: 0.78rem; background: #e0f2fe; color: #0369a1; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">✏️ Sửa</button>
                            <button type="button" class="btn-action delete" onclick="deleteEquipment(${item.id})" style="padding: 4px 10px; font-size: 0.78rem; background: #fee2e2; color: #b91c1c; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">🗑️ Xóa</button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        console.error('Lỗi tải danh sách Admin equipment:', err);
        tbody.innerHTML = '<tr><td colspan="6" class="equipment-table-message error">Không thể tải dữ liệu Admin.</td></tr>';
    }
}

// Khi Admin toggle trạng thái thiết bị thành Inactive, ở phía User tự động API /availability (do team khác phát triển) sẽ đánh dấu là Đang bảo trì
async function toggleEquipmentActive(equipmentId, isActive) {
    const token = getAuthToken();
    try {
        const res = await fetch(`${API_BASE}/equipments/${equipmentId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ is_active: isActive })
        });
        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || 'Không thể cập nhật trạng thái thiết bị');
        }
        await fetchAdminEquipments();
        fetchEquipmentAvailability();
    } catch (err) {
        console.error('Lỗi toggle trạng thái thiết bị:', err);
        alert(`Lỗi: ${err.message}`);
        fetchAdminEquipments();
    }
}

function openEquipmentModal() {
    const editIdInput = document.getElementById('editEquipmentId');
    const nameInput = document.getElementById('equipmentName');
    const codeInput = document.getElementById('equipmentCode');
    const categoryInput = document.getElementById('equipmentCategory');
    const totalQtyInput = document.getElementById('equipmentTotalQty');
    const titleEl = document.getElementById('equipmentModalTitle');

    if (editIdInput) editIdInput.value = '';
    if (nameInput) nameInput.value = '';
    if (codeInput) codeInput.value = '';
    if (categoryInput) categoryInput.value = '';
    if (totalQtyInput) totalQtyInput.value = 1;
    if (titleEl) titleEl.innerText = 'Thêm Thiết Bị Mới';

    const modal = document.getElementById('equipmentModal');
    if (modal) modal.style.display = 'flex';
}

function openEditEquipmentModal(id) {
    const equip = adminEquipmentsCache.find(item => item.id === id);
    if (!equip) return;

    const editIdInput = document.getElementById('editEquipmentId');
    const nameInput = document.getElementById('equipmentName');
    const codeInput = document.getElementById('equipmentCode');
    const categoryInput = document.getElementById('equipmentCategory');
    const totalQtyInput = document.getElementById('equipmentTotalQty');
    const titleEl = document.getElementById('equipmentModalTitle');

    if (editIdInput) editIdInput.value = equip.id;
    if (nameInput) nameInput.value = equip.name || '';
    if (codeInput) codeInput.value = equip.code || '';
    if (categoryInput) categoryInput.value = equip.category || '';
    if (totalQtyInput) totalQtyInput.value = equip.total_qty || 1;
    if (titleEl) titleEl.innerText = 'Sửa Thông Tin Thiết Bị';

    const modal = document.getElementById('equipmentModal');
    if (modal) modal.style.display = 'flex';
}

function closeEquipmentModal() {
    const modal = document.getElementById('equipmentModal');
    if (modal) modal.style.display = 'none';
}

async function handleEquipmentFormSubmit(event) {
    event.preventDefault();
    const token = getAuthToken();
    const editId = document.getElementById('editEquipmentId')?.value;
    const name = document.getElementById('equipmentName')?.value.trim();
    const code = document.getElementById('equipmentCode')?.value.trim() || null;
    const category = document.getElementById('equipmentCategory')?.value.trim() || null;
    const totalQty = parseInt(document.getElementById('equipmentTotalQty')?.value || '1', 10);

    const payload = {
        name,
        code,
        category,
        total_qty: totalQty
    };

    const isEdit = Boolean(editId);
    const url = isEdit ? `${API_BASE}/equipments/${editId}` : `${API_BASE}/equipments/`;
    const method = isEdit ? 'PUT' : 'POST';

    try {
        const res = await fetch(url, {
            method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || 'Thao tác thất bại');
        }

        closeEquipmentModal();
        await fetchAdminEquipments();
        fetchEquipmentAvailability();
        alert(isEdit ? 'Cập nhật thiết bị thành công!' : 'Thêm thiết bị mới thành công!');
    } catch (err) {
        console.error('Lỗi lưu thông tin thiết bị:', err);
        alert(`Lỗi: ${err.message}`);
    }
}

async function deleteEquipment(id) {
    if (!confirm('Bạn có chắc chắn muốn chuyển thiết bị này sang trạng thái ngừng hoạt động / xóa?')) return;
    const token = getAuthToken();
    try {
        const res = await fetch(`${API_BASE}/equipments/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || 'Không thể xóa thiết bị');
        }

        await fetchAdminEquipments();
        fetchEquipmentAvailability();
    } catch (err) {
        console.error('Lỗi khi xóa thiết bị:', err);
        alert(`Lỗi: ${err.message}`);
    }
}

/* ==========================================================================
   GLOBAL EXPORTS (GẮN VÀO WINDOW CHO EVENT HANDLER)
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
window.openBookModal = openBookingModal;
window.closeBookModal = closeBookingModal;
window.openQuickBooking = openQuickBooking;
window.handleBookingSubmit = handleBookingSubmit;
window.handleBookSubmit = handleBookingSubmit;
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
window.fetchAndRenderEquipments = fetchAndRenderEquipments;
window.fetchEquipmentAvailability = fetchEquipmentAvailability;
window.scheduleEquipmentAvailabilityFetch = scheduleEquipmentAvailabilityFetch;
window.toggleEquipmentQtyInput = toggleEquipmentQtyInput;
window.getSelectedEquipmentsData = getSelectedEquipmentsData;
window.fetchAndRenderParticipants = fetchAndRenderParticipants;
window.getSelectedParticipantIds = getSelectedParticipantIds;
window.renderRoomAmenities = renderRoomAmenities;
window.getAmenityIcon = getAmenityIcon;
window.triggerDatePicker = triggerDatePicker;
window.updateDateDisplay = updateDateDisplay;
window.buildViTimeOptions = buildViTimeOptions;
window.formatVietnameseTimeLabel = formatVietnameseTimeLabel;
window.syncHiddenStartTime = syncHiddenStartTime;
window.fetchAdminEquipments = fetchAdminEquipments;
window.toggleEquipmentActive = toggleEquipmentActive;
window.openEquipmentModal = openEquipmentModal;
window.openEditEquipmentModal = openEditEquipmentModal;
window.closeEquipmentModal = closeEquipmentModal;
window.handleEquipmentFormSubmit = handleEquipmentFormSubmit;
window.deleteEquipment = deleteEquipment;