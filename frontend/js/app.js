/* ==========================================================================
   GLOBAL CONFIGURATION & STATE MANAGEMENT
   ========================================================================== */
const API_BASE = window.API_URL || "http://localhost:8000/api";
let allRooms = [];
let myBookings = [];
let bookingCalendarView = 'month';
let bookingCalendarDate = new Date();
let bookingSelectedDate = new Date();
let selectedRoomId = null;
let equipmentAvailabilityTimer = null;
let googleCalendarOAuthError = null;
let activeQrScanner = null;
let activeQrMeetingId = null;
let activeQrAction = null;
let qrSubmissionInProgress = false;
let qrToastTimer = null;
let activeRoomQrToken = '';
let activePresenterQrToken = '';
let pendingCancelMeetingId = null;

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
document.addEventListener('DOMContentLoaded', async () => {
    const token = getAuthToken();
    const isMeetingPreview = new URLSearchParams(location.search).get('preview') === 'meeting';
    if (!token && !isMeetingPreview) {
        window.location.href = 'index.html';
        return;
    }

    let userName = localStorage.getItem('user_name') || 'Người dùng';
    let userEmail = localStorage.getItem('user_email') || '';
    let role = localStorage.getItem('role') || 'user';

    // Gọi API lấy thông tin chuẩn từ Database trực tiếp
    try {
        const profileRes = await fetch(`${API_BASE}/users/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (profileRes.ok) {
            const userData = await profileRes.json();
            userName = userData.full_name || userName;
            userEmail = userData.email || userEmail;
            localStorage.setItem('user_name', userName);
            localStorage.setItem('user_email', userEmail);
        }
    } catch (e) {
        console.error("Không thể tải thông tin profile từ server", e);
    }

    const isAdmin = role === 'admin';

    // Cập nhật thông tin người dùng trên giao diện
    const nameDisplay = document.getElementById('userNameDisplay');
    if (nameDisplay) nameDisplay.innerText = userName;

    const settingsName = document.getElementById('settingsName');
    if (settingsName) settingsName.innerText = userName;

    const settingsInputName = document.getElementById('settingsInputName');
    if (settingsInputName) settingsInputName.value = userName;

    const settingsInputEmail = document.getElementById('settingsInputEmail');
    if (settingsInputEmail) {
        settingsInputEmail.value = userEmail;
        settingsInputEmail.removeAttribute('readonly'); // Cho phép sửa email
    }
    loadCurrentUserProfile();
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
        const cancellationNav = document.getElementById('navCancellationAnalytics');
        if (btn1) btn1.style.display = 'block';
        if (btn2) btn2.style.display = 'block';
        if (addEqBtn) addEqBtn.style.display = 'block';
        if (adminEqSection) adminEqSection.style.display = 'block';
        if (cancellationNav) cancellationNav.style.display = 'flex';
    } else {
        const navReport = document.getElementById('navReport');
        const cancellationNav = document.getElementById('navCancellationAnalytics');
        if (navReport) navReport.style.display = 'none';
        if (cancellationNav) cancellationNav.style.display = 'none';
    }

    // Tải dữ liệu ban đầu
    fetchRooms(isAdmin).then(() => {
        fetchMyBookings();
        if (isAdmin) populateCancellationRoomFilter();
    });
    setDefaultEquipmentAvailabilityTimes();
    if (isAdmin) {
        fetchAdminEquipments();
    }

    // Khởi tạo thời gian mặc định cho bộ lọc báo cáo
    const reportEnd = document.getElementById("reportEndDate");
    const reportStart = document.getElementById("reportStartDate");
    if (reportEnd && reportStart) {
        const thirtyDaysAgo = new Date(now.getTime() - (30 * 24 * 60 * 60 * 1000));
        reportEnd.value = now.toISOString().slice(0, 16);
        reportStart.value = thirtyDaysAgo.toISOString().slice(0, 16);
        loadRoomsForReportFilter();
    }
    const cancellationStartDate = document.getElementById('cancellationStartDate');
    const cancellationEndDate = document.getElementById('cancellationEndDate');
    if (cancellationStartDate && cancellationEndDate) {
        const localDateValue = value => {
            const year = value.getFullYear();
            const month = String(value.getMonth() + 1).padStart(2, '0');
            const day = String(value.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };
        const monthStart = localDateValue(new Date(now.getFullYear(), now.getMonth(), 1));
        const todayValue = localDateValue(now);
        cancellationStartDate.value = monthStart;
        cancellationEndDate.value = todayValue;
        const executiveStartDate = document.getElementById('executiveStartDate');
        const executiveEndDate = document.getElementById('executiveEndDate');
        if (executiveStartDate) executiveStartDate.value = monthStart;
        if (executiveEndDate) executiveEndDate.value = todayValue;
    }

    const callbackQuery = new URLSearchParams(window.location.search);
    if (callbackQuery.has('calendar_connected') || callbackQuery.has('google_error')) {
        googleCalendarOAuthError = callbackQuery.get('google_error');
        const cleanUrl = new URL(window.location.href);
        cleanUrl.searchParams.delete('calendar_connected');
        cleanUrl.searchParams.delete('google_error');
        window.history.replaceState({}, document.title, `${cleanUrl.pathname}${cleanUrl.search}${cleanUrl.hash}`);
        switchMainTab('settings', document.getElementById('navSettings'));
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
    } else if (tabName === 'report') {
        const view = document.getElementById('viewReport');
        if (view) view.style.display = 'block';
        if (searchContainer) searchContainer.style.display = 'none';
        fetchRoomUsageReport();
    } else if (tabName === 'cancellations') {
        if (String(localStorage.getItem('role') || '').trim().toLowerCase() !== 'admin') return;
        const view = document.getElementById('viewCancellationAnalytics');
        if (view) view.style.display = 'block';
        if (searchContainer) searchContainer.style.display = 'none';
        fetchCancellationAnalytics();
    } else if (tabName === 'settings') {
        const view = document.getElementById('viewSettings');
        if (view) view.style.display = 'block';
        if (searchContainer) searchContainer.style.display = 'none';
        loadCurrentUserProfile();
        loadGoogleCalendarStatus();
    }
}

async function loadGoogleCalendarStatus() {
    const statusElement = document.getElementById('googleCalendarStatus');
    const actionButton = document.getElementById('googleCalendarAction');
    if (!statusElement || !actionButton) return;

    actionButton.disabled = true;
    statusElement.textContent = 'Đang kiểm tra kết nối...';
    try {
        const response = await fetch(`${API_BASE}/auth/google/calendar/status`, {
            headers: { Authorization: `Bearer ${getAuthToken()}` },
        });
        if (!response.ok) throw new Error(`Không thể kiểm tra kết nối Google Calendar (${response.status})`);
        const result = await response.json();
        const connected = result.connected === true;
        const oauthErrorMessages = {
            calendar_permission_denied: 'Bạn chưa cấp quyền Google Calendar. Có thể kết nối lại bất cứ lúc nào.',
            oauth_failed: 'Không thể kết nối Google Calendar. Vui lòng thử lại.',
        };
        statusElement.textContent = connected
            ? 'Tài khoản Google Calendar đã được kết nối.'
            : oauthErrorMessages[googleCalendarOAuthError] || 'Chưa kết nối Google Calendar.';
        googleCalendarOAuthError = null;
        actionButton.textContent = connected ? 'Ngắt kết nối' : 'Kết nối ngay';
        actionButton.dataset.connected = String(connected);
        actionButton.disabled = false;
    } catch (error) {
        console.error('Không thể tải trạng thái Google Calendar:', error);
        statusElement.textContent = 'Không thể tải trạng thái Google Calendar. Vui lòng thử lại.';
    }
}

async function handleGoogleCalendarAction() {
    const statusElement = document.getElementById('googleCalendarStatus');
    const actionButton = document.getElementById('googleCalendarAction');
    if (!statusElement || !actionButton) return;

    actionButton.disabled = true;
    try {
        if (actionButton.dataset.connected === 'true') {
            const response = await fetch(`${API_BASE}/auth/google/calendar/disconnect`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${getAuthToken()}` },
            });
            if (!response.ok) throw new Error(`Không thể ngắt kết nối Google Calendar (${response.status})`);
            await loadGoogleCalendarStatus();
            return;
        }

        const response = await fetch(`${API_BASE}/auth/google/calendar/authorize`, {
            credentials: 'include',
            headers: { Authorization: `Bearer ${getAuthToken()}` },
        });
        if (!response.ok) throw new Error(`Không thể bắt đầu kết nối Google Calendar (${response.status})`);
        const result = await response.json();
        if (!result.authorization_url) throw new Error('Máy chủ không trả về địa chỉ xác thực Google');
        window.location.assign(result.authorization_url);
    } catch (error) {
        console.error('Không thể cập nhật kết nối Google Calendar:', error);
        statusElement.textContent = error.message || 'Không thể cập nhật kết nối Google Calendar.';
        actionButton.disabled = false;
    }
}

async function loadCurrentUserProfile() {
    const emailInput = document.getElementById('settingsInputEmail');
    if (!emailInput) return;
    emailInput.disabled = false;
    emailInput.readOnly = false;

    let storedUser = {};
    try {
        const parsedUser = JSON.parse(localStorage.getItem('user') || '{}');
        if (parsedUser && typeof parsedUser === 'object') storedUser = parsedUser;
    } catch (error) {
        storedUser = {};
    }

    const getFallbackEmail = user => {
        const cachedEmail = localStorage.getItem('user_email') || storedUser.email || '';
        if (cachedEmail.trim()) return cachedEmail.trim();

        const username = String(
            user?.username || storedUser.username || localStorage.getItem('username') || '',
        ).trim();
        return username ? `${username.toLowerCase()}@congty.com` : '';
    };

    const setEmailValue = email => {
        emailInput.value = email;
        emailInput.defaultValue = email;
    };

    setEmailValue(getFallbackEmail());

    const token = getAuthToken();
    if (!token) return;

    try {
        const response = await fetch(`${API_BASE}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) return;

        const user = await response.json();
        const actualEmail = typeof user.email === 'string' ? user.email.trim() : '';
        const email = actualEmail || getFallbackEmail(user);
        setEmailValue(email);
        if (actualEmail) localStorage.setItem('user_email', actualEmail);

        const fullName = user.full_name || user.username;
        if (fullName) {
            localStorage.setItem('user_name', fullName);
            const nameDisplay = document.getElementById('userNameDisplay');
            const settingsName = document.getElementById('settingsName');
            const settingsInputName = document.getElementById('settingsInputName');
            if (nameDisplay) nameDisplay.innerText = fullName;
            if (settingsName) settingsName.innerText = fullName;
            if (settingsInputName) settingsInputName.value = fullName;
        }
    } catch (error) {
        console.warn('Could not load the current user profile:', error);
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
   UPDATE USER SETTINGS (LƯU THÔNG TIN CÁ NHÂN & EMAIL THẬT)
   ========================================================================== */
async function updateUserSettings() {
    const newName = document.getElementById('settingsInputName')?.value.trim();
    const newEmail = document.getElementById('settingsInputEmail')?.value.trim();
    const token = getAuthToken();

    if (!newEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(newEmail)) {
        alert("Vui lòng nhập địa chỉ email hợp lệ!");
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/users/me`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                full_name: newName,
                email: newEmail
            })
        });

        if (res.ok) {
            const updatedUser = await res.json();

            localStorage.setItem('user_name', updatedUser.full_name || newName);
            localStorage.setItem('user_email', updatedUser.email || newEmail);

            const nameDisplay = document.getElementById('userNameDisplay');
            if (nameDisplay) nameDisplay.innerText = updatedUser.full_name || newName;
            const settingsName = document.getElementById('settingsName');
            if (settingsName) settingsName.innerText = updatedUser.full_name || newName;

            alert("Đã cập nhật thông tin thành công!");
        } else {
            const err = await res.json();
            alert(`Cập nhật thất bại: ${err.detail || 'Lỗi không xác định'}`);
        }
    } catch (error) {
        console.error("Lỗi cập nhật thông tin:", error);
        alert("Không thể kết nối máy chủ để lưu thông tin!");
    }
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

function updateNotificationDot(unreadCount) {
    const dot = document.getElementById('notificationDot');
    if (!dot) return;
    dot.style.display = unreadCount > 0 ? 'block' : 'none';
}

function toggleNotificationPopup() {
    const popup = document.getElementById('notificationPopup');
    if (!popup) return;

    const isHidden = popup.style.display === 'none' || !popup.style.display;
    popup.style.display = isHidden ? 'block' : 'none';

    if (isHidden) {
        updateNotificationDot(0);
        fetchNotifications();
    }
}

document.addEventListener('click', function (e) {
    const wrapper = document.querySelector('.notification-wrapper');
    const popup = document.getElementById('notificationPopup');
    if (!wrapper || !popup) return;
    if (!wrapper.contains(e.target) && popup.style.display !== 'none') {
        popup.style.display = 'none';
    }
});

window.fetchNotifications = fetchNotifications;
window.updateNotificationDot = updateNotificationDot;

/* ==========================================================================
   MANUAL GUEST INVITE
   ========================================================================== */
let _manualGuests = [];

function addManualGuest() {
    const nameInput = document.getElementById('inviteGuestName');
    const emailInput = document.getElementById('inviteGuestEmail');
    if (!nameInput || !emailInput) return;

    const name = nameInput.value.trim();
    const email = emailInput.value.trim();

    if (!name && !email) { nameInput.focus(); return; }
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        emailInput.style.borderColor = '#ef4444';
        emailInput.focus();
        setTimeout(() => emailInput.style.borderColor = '', 1500);
        return;
    }

    if (_manualGuests.find(g => g.email === email)) {
        emailInput.style.borderColor = '#f59e0b';
        setTimeout(() => emailInput.style.borderColor = '', 1500);
        return;
    }

    _manualGuests.push({ name, email });
    nameInput.value = '';
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
    if (_manualGuests.length === 0) { container.innerHTML = ''; return; }
    container.innerHTML = _manualGuests.map(g => `
        <span class="manual-guest-tag" title="${g.email}">
            ${g.name ? `<strong>${escapeHtml(g.name)}</strong>&nbsp;` : ''}
            <span style="opacity:0.75">${escapeHtml(g.email)}</span>
            <button type="button" onclick="removeManualGuest('${g.email}')" title="Xóa">✕</button>
        </span>
    `).join('');
}

function getManualGuests() { return [..._manualGuests]; }
function resetManualGuests() {
    _manualGuests = [];
    renderManualGuestList();
    const nameInput = document.getElementById('inviteGuestName');
    const emailInput = document.getElementById('inviteGuestEmail');
    if (nameInput) nameInput.value = '';
    if (emailInput) emailInput.value = '';
}

window.addManualGuest = addManualGuest;
window.removeManualGuest = removeManualGuest;
window.getManualGuests = getManualGuests;
window.resetManualGuests = resetManualGuests;

/* ==========================================================================
   DATE & TIME FORMATTING UTILITIES
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

function formatVietnameseTimeLabel(hour, minute) {
    const timeStr = `${String(hour).padStart(2, '0')}:${minute}`;
    let period = 'sáng';
    if (hour === 12) period = 'trưa';
    else if (hour > 12 && hour < 18) period = 'chiều';
    else if (hour >= 18) period = 'tối';

    const minText = minute === '00' ? '' : `${minute}`;
    return `${timeStr} (${hour}h${minText} ${period})`;
}

function buildViTimeOptions(selectEl, defaultTimeStr) {
    if (!selectEl) return;
    selectEl.innerHTML = '';

    for (let h = 7; h <= 21; h++) {
        for (let m of ['00', '30']) {
            if (h === 21 && m === '30') continue;
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
    const gridRooms = document.getElementById('roomGridRooms');
    renderDashboardRooms(rooms, isAdmin);
    if (!rooms || rooms.length === 0) {
        if (gridRooms) gridRooms.innerHTML = emptyRoomsMessage();
        return;
    }
    if (gridRooms) gridRooms.innerHTML = buildRoomCards(rooms, isAdmin);
}

function renderDashboardRooms(rooms, isAdmin) {
    const gridOverview = document.getElementById('roomGridOverview');
    if (!gridOverview) return;
    if (!rooms || rooms.length === 0) {
        gridOverview.innerHTML = emptyRoomsMessage();
        return;
    }
    gridOverview.innerHTML = buildRoomCards(rooms, isAdmin);
}

function emptyRoomsMessage() {
    return '<p class="text-muted" style="padding: 16px;">Chưa có phòng họp nào trong hệ thống.</p>';
}

function buildRoomCards(rooms, isAdmin) {
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
                    <span class="status-badge ${statusClass} ${isAdmin ? 'has-qr-action' : ''}">${statusText}</span>
                    ${isAdmin ? `<button class="room-qr-icon" type="button" onclick="openRoomQrModal(${room.id})" title="Xem mã QR phòng" aria-label="Xem mã QR phòng ${escapeHtml(room.name)}">
                        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                            <path d="M3 3h8v8H3zM5.5 5.5v3h3v-3zM13 3h8v8h-8zM15.5 5.5v3h3v-3zM3 13h8v8H3zM5.5 15.5v3h3v-3zM13 13h3v3h-3zM18 13h3v3h-3zM13 18h3v3h-3zM18 18h3v3h-3z" />
                        </svg>
                    </button>` : ''}
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
    return htmlContent;
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
    if (lower.includes('màn hình') || lower.includes('tv')) return '📺';
    if (lower.includes('wifi') || lower.includes('internet')) return '📶';
    if (lower.includes('video') || lower.includes('camera')) return '🎥';
    if (lower.includes('chiếu') || lower.includes('projector')) return '📽️';
    if (lower.includes('mic') || lower.includes('loa')) return '🎙️';
    if (lower.includes('đồ uống') || lower.includes('nước') || lower.includes('trà') || lower.includes('cà phê')) return '☕';
    return '✨';
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
        `;
    }
    const modal = document.getElementById('scheduleModal');
    if (modal) modal.style.display = 'flex';
}

function closeScheduleModal() {
    const modal = document.getElementById('scheduleModal');
    if (modal) modal.style.display = 'none';
}

/* ==========================================================================
   MY BOOKINGS MANAGEMENT
   ========================================================================== */
function cancelBooking(meetingId) {
    pendingCancelMeetingId = meetingId;
    const reasonInput = document.getElementById('cancellationReasonInput');
    const modal = document.getElementById('cancelMeetingModal');
    if (reasonInput) reasonInput.value = '';
    if (modal) modal.style.display = 'flex';
}

function closeCancelMeetingModal() {
    const modal = document.getElementById('cancelMeetingModal');
    if (modal) modal.style.display = 'none';
    pendingCancelMeetingId = null;
}

async function submitCancelBooking() {
    if (pendingCancelMeetingId === null) return;
    const meetingId = pendingCancelMeetingId;
    const reasonInput = document.getElementById('cancellationReasonInput');
    const submitButton = document.querySelector('.cancellation-confirm-button');
    if (submitButton) submitButton.disabled = true;
    try {
        const res = await fetch(`${API_BASE}/meetings/${meetingId}/cancel`, {
            method: 'PATCH',
            headers: {
                'Authorization': 'Bearer ' + getAuthToken(),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                cancellation_reason: reasonInput ? reasonInput.value.trim() || null : null,
            }),
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Không thể hủy lịch họp!');
        }
        closeCancelMeetingModal();
        alert('Đã hủy lịch họp!');
        await fetchMyBookings();
        fetchRooms(localStorage.getItem('role') === 'admin');
    } catch (err) {
        alert(`Lỗi: ${err.message || 'Không thể hủy lịch họp.'}`);
    } finally {
        if (submitButton) submitButton.disabled = false;
    }
}
async function fetchMyBookings() {
    if (!getAuthToken()) return;
    try {
        const res = await fetch(`${API_BASE}/meetings/mine`, {
            headers: { 'Authorization': 'Bearer ' + getAuthToken() }
        });
        if (!res.ok) throw new Error('Không thể tải danh sách lịch họp.');
        myBookings = await res.json();
        renderMyBookings();
    } catch (err) {
        console.error('Lỗi lấy danh sách lịch họp:', err);
        ['myBookingsTableBody', 'invitedBookingsList', 'bookingCalendarGrid'].forEach(id => {
            const element = document.getElementById(id);
            if (element) element.innerHTML = '<div class="booking-list-empty">Không thể tải lịch họp. Vui lòng thử lại.</div>';
        });
    }
}

function renderMyBookings() {
    renderOrganizerBookings(myBookings.filter(meeting => meeting.is_organizer));
    renderInvitedBookings(myBookings.filter(meeting => !meeting.is_organizer));
    renderBookingCalendar();
}

function bookingRoomName(meeting) {
    if (String(meeting.meeting_type || '').toLowerCase() === 'online') return 'Cuộc họp online';
    return meeting.room_name || allRooms.find(room => room.id === meeting.room_id)?.name
        || (meeting.room_id ? `Phòng ${meeting.room_id}` : 'Phòng chưa xác định');
}

function bookingDate(value) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
}

function bookingTime(date) {
    return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', hour12: false });
}

function bookingDateKey(date) {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function renderOrganizerBookings(meetings) {
    const container = document.getElementById('myBookingsTableBody');
    if (!container) return;
    if (!meetings.length) {
        container.innerHTML = '<div class="booking-list-empty">Bạn chưa chủ trì cuộc họp nào.</div>';
        return;
    }
    container.innerHTML = meetings.map(meeting => {
        const start = bookingDate(meeting.start_time);
        const end = bookingDate(meeting.end_time);
        const date = start ? start.toLocaleDateString('vi-VN') : 'Chưa có ngày';
        const time = start && end ? `${bookingTime(start)} – ${bookingTime(end)}` : 'Chưa có thời gian';
        const participants = (meeting.participants || []).filter(person => person.user_id !== meeting.organizer_id);
        const attendeeMarkup = participants.length ? participants.map(person => {
            const response = ['accepted', 'declined'].includes(person.response_status) ? person.response_status : 'pending';
            const label = response === 'accepted' ? 'Đã đồng ý' : response === 'declined' ? 'Đã từ chối' : 'Chưa phản hồi';
            return `<div class="booking-guest ${response === 'accepted' ? '' : 'pending'}"><span>${escapeHtml(person.name || person.email || 'Người tham dự')}</span><span class="booking-guest-status ${response}">${response === 'accepted' ? '✓ ' : ''}${label}</span></div>`;
        }).join('') : '<div class="booking-guest pending">Chưa có người được mời.</div>';
        const cancel = `<button class="booking-cancel-button" type="button" onclick="cancelBooking(${meeting.id})">Hủy lịch</button>`;
        const qrActions = meetingPresenterQrAction(meeting);
        let joinLink = '';
        try {
            const url = new URL(String(meeting.meeting_link || meeting.online_link || ''));
            if (url.protocol === 'http:' || url.protocol === 'https:') {
                joinLink = `<a class="booking-rsvp-button" href="${escapeHtml(url.href)}" target="_blank" rel="noopener noreferrer">Tham gia</a>`;
            }
        } catch (error) {
            joinLink = '';
        }
        return `<article class="booking-list-card"><div class="booking-list-row">
            <div class="booking-list-main"><strong>${escapeHtml(meeting.title || 'Cuộc họp')}</strong><span>${escapeHtml(bookingRoomName(meeting))} · ${escapeHtml(date)}</span></div>
            <div class="booking-list-time">${escapeHtml(time)}</div>
            <div class="booking-list-actions"><button class="booking-guest-toggle" type="button" aria-expanded="false" onclick="toggleBookingGuests(${meeting.id}, this)">Người được mời (${participants.length})</button>${joinLink}${qrActions}${cancel}</div>
        </div><div id="bookingGuests${meeting.id}" class="booking-guest-list" hidden>${attendeeMarkup}</div></article>`;
    }).join('');
}

function renderInvitedBookings(meetings) {
    const container = document.getElementById('invitedBookingsList');
    if (!container) return;
    if (!meetings.length) {
        container.innerHTML = '<div class="booking-list-empty">Bạn chưa được mời tham gia cuộc họp nào.</div>';
        return;
    }
    container.innerHTML = meetings.map(meeting => {
        const start = bookingDate(meeting.start_time);
        const end = bookingDate(meeting.end_time);
        const date = start ? start.toLocaleDateString('vi-VN') : 'Chưa có ngày';
        const time = start && end ? `${bookingTime(start)} – ${bookingTime(end)}` : 'Chưa có thời gian';
        const response = meeting.my_response_status || 'pending';
        const status = response === 'accepted' ? 'Đã xác nhận' : response === 'declined' ? 'Đã từ chối' : 'Chưa phản hồi';
        const adminCancel = String(localStorage.getItem('role') || '').trim().toLowerCase() === 'admin'
            ? `<button class="booking-cancel-button" type="button" onclick="cancelBooking(${meeting.id})">Hủy lịch</button>`
            : '';
        const qrActions = meetingQrActions(meeting, response === 'accepted');
        return `<article class="booking-list-card"><div class="booking-list-row">
            <div class="booking-list-main"><strong>${escapeHtml(meeting.title || 'Cuộc họp')}</strong><span>${escapeHtml(bookingRoomName(meeting))} · ${escapeHtml(date)}</span><span>Chủ trì: ${escapeHtml(meeting.organizer_name || 'Người tổ chức')}</span></div>
            <div class="booking-list-time">${escapeHtml(time)}<br>${escapeHtml(status)}</div>
            <div class="booking-list-actions"><button class="booking-rsvp-button" type="button" onclick="respondToMeeting(${meeting.id}, 'accepted')" ${response === 'accepted' ? 'disabled' : ''}>Xác nhận</button><button class="booking-rsvp-button" type="button" onclick="respondToMeeting(${meeting.id}, 'declined')" ${response === 'declined' ? 'disabled' : ''}>Từ chối</button>${qrActions}${adminCancel}</div>
        </div></article>`;
    }).join('');
}

function meetingQrActions(meeting, isEligible) {
    if (!isEligible || !meeting.room_id || String(meeting.meeting_type || 'offline').toLowerCase() === 'online') return '';
    const state = String(meeting.status || '').toUpperCase();
    if (state === 'SCHEDULED') {
        const start = bookingDate(meeting.start_time);
        const now = Date.now();
        if (!start || now < start.getTime() - 15 * 60 * 1000 || now > start.getTime() + 15 * 60 * 1000) return '';
        return `<button class="booking-qr-button" type="button" onclick="openQrCheckModal(${meeting.id}, 'check-in')">Check-in QR</button>`;
    }
    if (state === 'IN_PROGRESS') {
        return `<button class="booking-qr-button" type="button" onclick="openQrCheckModal(${meeting.id}, 'check-out')">Check-out QR</button>`;
    }
    return '';
}

function meetingPresenterQrAction(meeting) {
    if (!meeting.room_id || String(meeting.meeting_type || 'offline').toLowerCase() === 'online') return '';
    const state = String(meeting.status || '').toUpperCase();
    if (!['SCHEDULED', 'IN_PROGRESS'].includes(state)) return '';
    return `<button class="booking-qr-button" type="button" onclick="openPresenterQrModal(${meeting.id})"><span aria-hidden="true">▦</span> Mã QR Check-in</button>`;
}

function showQrToast(message, isError = false) {
    const toast = document.getElementById('qrToast');
    if (!toast) return;
    toast.textContent = message;
    toast.classList.toggle('is-error', isError);
    toast.classList.add('is-visible');
    if (qrToastTimer) clearTimeout(qrToastTimer);
    qrToastTimer = setTimeout(() => toast.classList.remove('is-visible'), 3500);
}

function buildQrCode(container, token, size) {
    if (typeof QRCode === 'undefined') {
        throw new Error('Không tải được thư viện tạo mã QR. Vui lòng tải lại trang.');
    }
    container.replaceChildren();
    new QRCode(container, {
        text: token,
        width: size,
        height: size,
        colorDark: '#0f172a',
        colorLight: '#ffffff',
        correctLevel: QRCode.CorrectLevel.H,
    });
}

async function fetchRoomQrToken(roomId, meetingId = null) {
    const meetingQuery = meetingId ? `?meeting_id=${encodeURIComponent(meetingId)}` : '';
    const response = await fetch(`${API_BASE}/rooms/${roomId}/qr-code${meetingQuery}`, {
        headers: { Authorization: `Bearer ${getAuthToken()}` },
    });
    const result = await response.json();
    if (!response.ok) {
        throw new Error(result.detail || 'Không thể tải mã QR phòng họp.');
    }
    return result;
}

async function openRoomQrModal(roomId) {
    const room = allRooms.find(item => item.id === roomId);
    const modal = document.getElementById('roomQrModal');
    const qrTarget = document.getElementById('roomQrImage');
    if (!room || !modal || !qrTarget) return;

    document.getElementById('roomQrName').textContent = room.name || 'Phòng họp';
    document.getElementById('roomQrLocation').textContent = room.location || 'Chưa cập nhật vị trí';
    qrTarget.replaceChildren();
    modal.style.display = 'flex';
    try {
        const data = await fetchRoomQrToken(roomId);
        activeRoomQrToken = data.qr_token;
        buildQrCode(qrTarget, activeRoomQrToken, 320);
    } catch (error) {
        modal.style.display = 'none';
        showQrToast(error.message || 'Không thể tải mã QR phòng.', true);
    }
}

function closeRoomQrModal() {
    const modal = document.getElementById('roomQrModal');
    if (modal) modal.style.display = 'none';
    activeRoomQrToken = '';
}

async function openPresenterQrModal(meetingId) {
    const meeting = myBookings.find(item => item.id === meetingId);
    const modal = document.getElementById('presenterQRModal');
    const qrTarget = document.getElementById('presenterQRImage');
    if (!meeting || !modal || !qrTarget) return;

    document.getElementById('presenterQRTitle').textContent = meeting.title || 'Cuộc họp';
    document.getElementById('presenterQRRoom').textContent = bookingRoomName(meeting);
    const start = bookingDate(meeting.start_time);
    const end = bookingDate(meeting.end_time);
    document.getElementById('presenterQRTime').textContent = start && end
        ? `${start.toLocaleDateString('vi-VN')} · ${bookingTime(start)} – ${bookingTime(end)}`
        : 'Chưa có thời gian';
    qrTarget.replaceChildren();
    modal.style.display = 'flex';
    try {
        const data = await fetchRoomQrToken(meeting.room_id, meeting.id);
        activePresenterQrToken = data.qr_token;
        buildQrCode(qrTarget, activePresenterQrToken, 560);
    } catch (error) {
        modal.style.display = 'none';
        showQrToast(error.message || 'Không thể tải mã QR check-in.', true);
    }
}

async function closePresenterQrModal() {
    const modal = document.getElementById('presenterQRModal');
    if (document.fullscreenElement === modal) {
        await document.exitFullscreen();
    }
    if (modal) modal.style.display = 'none';
    activePresenterQrToken = '';
}

async function togglePresenterQrFullscreen() {
    const modal = document.getElementById('presenterQRModal');
    if (!modal) return;
    try {
        if (document.fullscreenElement === modal) {
            await document.exitFullscreen();
        } else {
            await modal.requestFullscreen();
        }
    } catch (error) {
        showQrToast('Trình duyệt không cho phép mở chế độ toàn màn hình.', true);
    }
}

function syncPresenterFullscreenButton() {
    const button = document.getElementById('presenterQRFullscreenButton');
    const modal = document.getElementById('presenterQRModal');
    if (button) {
        button.textContent = document.fullscreenElement === modal ? 'Thoát toàn màn hình' : 'Phóng to / Fullscreen';
    }
}

async function copyQrToken(token) {
    if (!token) {
        showQrToast('Không có mã QR để sao chép.', true);
        return;
    }
    try {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(token);
        } else {
            const input = document.createElement('textarea');
            input.value = token;
            input.setAttribute('readonly', '');
            input.style.position = 'fixed';
            input.style.opacity = '0';
            document.body.appendChild(input);
            input.select();
            const copied = document.execCommand('copy');
            input.remove();
            if (!copied) throw new Error('Trình duyệt không thể sao chép mã QR.');
        }
        showQrToast('Đã sao chép token QR.');
    } catch (error) {
        showQrToast(error.message || 'Không thể sao chép token QR.', true);
    }
}

function downloadQrImage(containerId, fileName) {
    const canvas = document.querySelector(`#${containerId} canvas`);
    if (!canvas) {
        showQrToast('Ảnh QR chưa sẵn sàng để tải.', true);
        return;
    }
    try {
        const link = document.createElement('a');
        link.href = canvas.toDataURL('image/png');
        link.download = fileName;
        link.click();
        showQrToast('Đã tải ảnh QR PNG.');
    } catch (error) {
        showQrToast(error.message || 'Không thể tải ảnh QR.', true);
    }
}

function copyRoomQrToken() {
    return copyQrToken(activeRoomQrToken);
}

function downloadRoomQrImage() {
    const roomName = document.getElementById('roomQrName')?.textContent || 'phong-hop';
    const safeName = roomName.replace(/[^\w-]+/g, '-').replace(/^-|-$/g, '') || 'phong-hop';
    downloadQrImage('roomQrImage', `QR-${safeName}.png`);
}

function copyPresenterQrToken() {
    return copyQrToken(activePresenterQrToken);
}

document.addEventListener('fullscreenchange', syncPresenterFullscreenButton);

async function openQrCheckModal(meetingId, action) {
    activeQrMeetingId = meetingId;
    activeQrAction = action;
    qrSubmissionInProgress = false;
    const modal = document.getElementById('qrCheckModal');
    const input = document.getElementById('qrTokenInput');
    const description = document.getElementById('qrCheckDescription');
    if (!modal || !input) return;
    input.value = '';
    if (description) {
        description.textContent = action === 'check-in'
            ? 'Quét mã QR của phòng họp để check-in.'
            : 'Quét mã QR của phòng họp để check-out.';
    }
    modal.style.display = 'flex';
    if (typeof Html5Qrcode === 'undefined') {
        showQrToast('Không tải được trình quét QR. Bạn có thể nhập mã thủ công.', true);
        return;
    }
    try {
        activeQrScanner = new Html5Qrcode('qrReader');
        await activeQrScanner.start(
            { facingMode: 'environment' },
            { fps: 10, qrbox: { width: 240, height: 240 } },
            async (decodedText) => {
                input.value = decodedText;
                await stopQrScanner();
                await submitQrCheck();
            },
            () => {}
        );
    } catch (error) {
        console.warn('Không thể khởi động camera quét QR:', error);
        showQrToast('Không thể mở camera. Hãy nhập mã QR thủ công.', true);
    }
}

async function stopQrScanner() {
    if (!activeQrScanner) return;
    const scanner = activeQrScanner;
    activeQrScanner = null;
    try {
        if (scanner.isScanning) await scanner.stop();
        scanner.clear();
    } catch (error) {
        console.warn('Không thể dừng trình quét QR:', error);
    }
}

async function closeQrCheckModal() {
    await stopQrScanner();
    const modal = document.getElementById('qrCheckModal');
    if (modal) modal.style.display = 'none';
    activeQrMeetingId = null;
    activeQrAction = null;
    qrSubmissionInProgress = false;
}

async function submitQrCheck() {
    if (qrSubmissionInProgress || !activeQrMeetingId || !activeQrAction) return;
    const input = document.getElementById('qrTokenInput');
    const scannedValue = (input?.value || '').trim();
    if (!scannedValue) {
        showQrToast('Vui lòng quét hoặc nhập mã QR phòng họp.', true);
        return;
    }
    let qrToken = scannedValue;
    try {
        const parsed = JSON.parse(scannedValue);
        qrToken = parsed.qr_token || scannedValue;
    } catch (error) {
        // QR labels generated by RoomSync contain the token as plain text.
    }
    qrSubmissionInProgress = true;
    try {
        const response = await fetch(
            `${API_BASE}/v1/meetings/${activeQrMeetingId}/${activeQrAction}`,
            {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${getAuthToken()}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ qr_token: qrToken }),
            }
        );
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Không thể cập nhật trạng thái check-in.');
        const successMessage = activeQrAction === 'check-in'
            ? 'Check-in thành công.'
            : 'Check-out thành công.';
        await closeQrCheckModal();
        showQrToast(successMessage);
        await fetchMyBookings();
    } catch (error) {
        qrSubmissionInProgress = false;
        showQrToast(error.message || 'Không thể gửi mã QR.', true);
    }
}

function toggleBookingGuests(meetingId, button) {
    const list = document.getElementById(`bookingGuests${meetingId}`);
    if (!list) return;
    list.hidden = !list.hidden;
    button.setAttribute('aria-expanded', String(!list.hidden));
}

function switchBookingTab(tab) {
    const tabs = { calendar: ['bookingTabCalendar', 'bookingPanelCalendar'], mine: ['bookingTabMine', 'bookingPanelMine'], invited: ['bookingTabInvited', 'bookingPanelInvited'] };
    Object.entries(tabs).forEach(([name, ids]) => {
        const active = name === tab;
        const button = document.getElementById(ids[0]);
        const panel = document.getElementById(ids[1]);
        if (button) {
            button.classList.toggle('active', active);
            button.setAttribute('aria-selected', String(active));
        }
        if (panel) panel.hidden = !active;
    });
    if (tab === 'calendar') renderBookingCalendar();
}

function shiftBookingCalendar(amount) {
    bookingCalendarDate = new Date(bookingCalendarDate);
    if (bookingCalendarView === 'month') bookingCalendarDate.setMonth(bookingCalendarDate.getMonth() + amount, 1);
    else bookingCalendarDate.setDate(bookingCalendarDate.getDate() + amount * (bookingCalendarView === 'week' ? 7 : 1));
    bookingSelectedDate = new Date(bookingCalendarDate);
    renderBookingCalendar();
}

function goToBookingCalendarToday() {
    bookingCalendarDate = new Date();
    bookingSelectedDate = new Date();
    renderBookingCalendar();
}

function setBookingCalendarView(view) {
    if (!['month', 'week', 'day'].includes(view)) return;
    bookingCalendarView = view;
    document.querySelectorAll('[data-calendar-view]').forEach(button => button.classList.toggle('active', button.dataset.calendarView === view));
    renderBookingCalendar();
}

function renderBookingCalendar() {
    const grid = document.getElementById('bookingCalendarGrid');
    if (!grid) return;
    const title = document.getElementById('bookingCalendarTitle');
    const selectedKey = bookingDateKey(bookingSelectedDate);
    let dates;
    if (bookingCalendarView === 'month') {
        const first = new Date(bookingCalendarDate.getFullYear(), bookingCalendarDate.getMonth(), 1);
        const start = new Date(first);
        start.setDate(1 - first.getDay());
        dates = Array.from({ length: 42 }, (_, index) => {
            const date = new Date(start);
            date.setDate(start.getDate() + index);
            return date;
        });
        if (title) title.textContent = bookingCalendarDate.toLocaleDateString('vi-VN', { month: 'long', year: 'numeric' });
    } else if (bookingCalendarView === 'week') {
        const start = new Date(bookingCalendarDate);
        start.setDate(start.getDate() - start.getDay());
        dates = Array.from({ length: 7 }, (_, index) => {
            const date = new Date(start);
            date.setDate(start.getDate() + index);
            return date;
        });
        if (title) title.textContent = `${dates[0].toLocaleDateString('vi-VN')} – ${dates[6].toLocaleDateString('vi-VN')}`;
    } else {
        dates = [new Date(bookingCalendarDate)];
        if (title) title.textContent = bookingCalendarDate.toLocaleDateString('vi-VN', { day: 'numeric', month: 'long', year: 'numeric' });
    }
    const weekdays = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'];
    const columns = bookingCalendarView === 'day' ? 1 : 7;
    grid.style.gridTemplateColumns = `repeat(${columns}, minmax(0, 1fr))`;
    grid.innerHTML = (bookingCalendarView === 'day' ? '' : weekdays.map(day => `<div class="booking-calendar-weekday">${day}</div>`).join(''))
        + dates.map(date => {
            const key = bookingDateKey(date);
            const events = myBookings.filter(meeting => {
                const start = bookingDate(meeting.start_time);
                return start && bookingDateKey(start) === key;
            }).sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
            const classes = [
                bookingCalendarView === 'month' && date.getMonth() !== bookingCalendarDate.getMonth() ? 'outside' : '',
                key === bookingDateKey(new Date()) ? 'today' : '',
                key === selectedKey ? 'selected' : '',
            ].filter(Boolean).join(' ');
            const preview = events.slice(0, bookingCalendarView === 'day' ? events.length : 3).map(meeting => {
                const start = bookingDate(meeting.start_time);
                return `<span class="booking-calendar-event">${start ? `${bookingTime(start)} ` : ''}${escapeHtml(meeting.title || 'Cuộc họp')}</span>`;
            }).join('');
            const more = events.length > 3 && bookingCalendarView !== 'day' ? `<div class="booking-calendar-more">+${events.length - 3} cuộc họp</div>` : '';
            return `<div class="booking-calendar-day ${classes}" role="button" tabindex="0" aria-label="${escapeHtml(date.toLocaleDateString('vi-VN'))}, ${events.length} cuộc họp" onclick="selectBookingCalendarDate('${key}')" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();selectBookingCalendarDate('${key}')}"><span class="booking-calendar-day-number">${date.getDate()}</span>${preview}${more}</div>`;
        }).join('');
    renderBookingAgenda();
}

function selectBookingCalendarDate(key) {
    const [year, month, day] = key.split('-').map(Number);
    bookingSelectedDate = new Date(year, month - 1, day);
    bookingCalendarDate = new Date(bookingSelectedDate);
    renderBookingCalendar();
}

function renderBookingAgenda() {
    const container = document.getElementById('bookingDayAgenda');
    const title = document.getElementById('bookingAgendaTitle');
    if (!container) return;
    if (title) title.textContent = `Lịch ngày ${bookingSelectedDate.toLocaleDateString('vi-VN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}`;
    const key = bookingDateKey(bookingSelectedDate);
    const events = myBookings.filter(meeting => {
        const start = bookingDate(meeting.start_time);
        return start && bookingDateKey(start) === key;
    }).sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
    container.innerHTML = events.length ? events.map(meeting => {
        const start = bookingDate(meeting.start_time);
        const end = bookingDate(meeting.end_time);
        const time = start && end ? `${bookingTime(start)} – ${bookingTime(end)}` : 'Chưa có thời gian';
        return `<div class="booking-agenda-item"><div class="booking-agenda-time">${escapeHtml(time)}</div><div class="booking-agenda-details"><strong>${escapeHtml(meeting.title || 'Cuộc họp')}</strong><span>${escapeHtml(bookingRoomName(meeting))}${meeting.organizer_name ? ` · ${escapeHtml(meeting.organizer_name)}` : ''}</span></div></div>`;
    }).join('') : '<div class="booking-list-empty">Không có cuộc họp trong ngày này.</div>';
}

async function respondToMeeting(meetingId, responseStatus) {
    try {
const res = await fetch(`${API_BASE}/meetings/${meetingId}/response`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getAuthToken() },
    body: JSON.stringify({ response_status: responseStatus }),
});
if (!res.ok) {
    const result = await res.json();
    throw new Error(result.detail || 'Không thể cập nhật phản hồi.');
}
await fetchMyBookings();
    } catch (error) {
alert(`Lỗi: ${error.message}`);
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

    let amenitiesStr = '';
    if (room.amenities) {
        if (typeof room.amenities === 'string') {
            try {
                let parsed = JSON.parse(room.amenities);
                amenitiesStr = Array.isArray(parsed) ? parsed.join(', ') : room.amenities;
            } catch (e) { amenitiesStr = room.amenities; }
        } else if (Array.isArray(room.amenities)) {
            amenitiesStr = room.amenities.join(', ');
        }
    }
    document.getElementById('roomAmenities').value = amenitiesStr;
    document.getElementById('roomModal').style.display = 'flex';
}

function closeRoomModal() {
    document.getElementById('roomModal').style.display = 'none';
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
        is_active: true
    };

    const method = editId ? 'PUT' : 'POST';
    const url = editId ? `${API_BASE}/rooms/${editId}/` : `${API_BASE}/rooms/`;

    try {
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json', "Authorization": `Bearer ${token}` },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            closeRoomModal();
            fetchRooms(localStorage.getItem('role') === 'admin');
            alert(editId ? "Cập nhật phòng thành công!" : "Thêm phòng thành công!");
        } else {
            const err = await res.json();
            alert(err.detail || "Thao tác thất bại!");
        }
    } catch (err) { alert("Lỗi kết nối máy chủ!"); }
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
            renderRooms(allRooms, localStorage.getItem('role') === 'admin');
            updateStats(allRooms);
            alert("Xóa phòng thành công!");
        } else {
            const err = await res.json();
            alert(err.detail || "Thao tác thất bại!");
        }
    } catch (err) { alert("Lỗi máy chủ!"); }
}

function logout() {
    localStorage.clear();
    window.location.href = 'index.html';
}

/* ==========================================================================
   EQUIPMENT MANAGEMENT
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
        tbody.innerHTML = '<tr><td colspan="7" class="equipment-table-message error">Không thể tải trạng thái thiết bị.</td></tr>';
    }
}

let adminEquipmentsCache = [];

async function fetchAdminEquipments() {
    const tbody = document.getElementById('adminEquipmentTableBody');
    if (!tbody) return;

    const token = getAuthToken();
    tbody.innerHTML = '<tr><td colspan="6" class="equipment-table-message">Đang tải danh sách Admin...</td></tr>';
    try {
        const res = await fetch(`${API_BASE}/equipments/?include_inactive=true`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error();

        const equipments = await res.json();
        adminEquipmentsCache = equipments;

        if (!equipments.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="equipment-table-message">Chưa có thiết bị nào.</td></tr>';
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
                        <label class="switch">
                            <input type="checkbox" ${isChecked ? 'checked' : ''} onchange="toggleEquipmentActive(${item.id}, this.checked)">
                            <span class="slider"></span>
                        </label>
                    </td>
                    <td>
                        <div style="display: flex; gap: 8px;">
                            <button type="button" onclick="openEditEquipmentModal(${item.id})" style="padding: 4px 10px; font-size: 0.78rem; background: #e0f2fe; color: #0369a1; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">Sửa</button>
                            <button type="button" onclick="deleteEquipment(${item.id})" style="padding: 4px 10px; font-size: 0.78rem; background: #fee2e2; color: #b91c1c; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">Xóa</button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="6" class="equipment-table-message error">Không thể tải dữ liệu Admin.</td></tr>';
    }
}

async function toggleEquipmentActive(equipmentId, isActive) {
    const token = getAuthToken();
    try {
        await fetch(`${API_BASE}/equipments/${equipmentId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ is_active: isActive })
        });
        fetchAdminEquipments();
        fetchEquipmentAvailability();
    } catch (err) { alert(`Lỗi: ${err.message}`); }
}

function openEquipmentModal() {
    document.getElementById('editEquipmentId').value = '';
    document.getElementById('equipmentForm').reset();
    document.getElementById('equipmentModalTitle').innerText = 'Thêm Thiết Bị Mới';
    document.getElementById('equipmentModal').style.display = 'flex';
}

function openEditEquipmentModal(id) {
    const equip = adminEquipmentsCache.find(item => item.id === id);
    if (!equip) return;
    document.getElementById('editEquipmentId').value = equip.id;
    document.getElementById('equipmentName').value = equip.name || '';
    document.getElementById('equipmentCode').value = equip.code || '';
    document.getElementById('equipmentCategory').value = equip.category || '';
    document.getElementById('equipmentTotalQty').value = equip.total_qty || 1;
    document.getElementById('equipmentModalTitle').innerText = 'Sửa Thông Tin Thiết Bị';
    document.getElementById('equipmentModal').style.display = 'flex';
}

function closeEquipmentModal() {
    document.getElementById('equipmentModal').style.display = 'none';
}

async function handleEquipmentFormSubmit(event) {
    event.preventDefault();
    const token = getAuthToken();
    const editId = document.getElementById('editEquipmentId')?.value;
    const payload = {
        name: document.getElementById('equipmentName')?.value.trim(),
        code: document.getElementById('equipmentCode')?.value.trim() || null,
        category: document.getElementById('equipmentCategory')?.value.trim() || null,
        total_qty: parseInt(document.getElementById('equipmentTotalQty')?.value || '1', 10)
    };

    const isEdit = Boolean(editId);
    const url = isEdit ? `${API_BASE}/equipments/${editId}` : `${API_BASE}/equipments/`;

    try {
        const res = await fetch(url, {
            method: isEdit ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error('Thao tác thất bại');
        closeEquipmentModal();
        fetchAdminEquipments();
        fetchEquipmentAvailability();
        alert(isEdit ? 'Cập nhật thiết bị thành công!' : 'Thêm thiết bị mới thành công!');
    } catch (err) { alert(`Lỗi: ${err.message}`); }
}

async function deleteEquipment(id) {
    if (!confirm('Bạn có chắc chắn muốn xóa thiết bị này?')) return;
    const token = getAuthToken();
    try {
        await fetch(`${API_BASE}/equipments/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        fetchAdminEquipments();
        fetchEquipmentAvailability();
    } catch (err) { alert(`Lỗi: ${err.message}`); }
}

/* ==========================================================================
   ROOM USAGE REPORT LOGIC
   ========================================================================== */
async function loadRoomsForReportFilter() {
    try {
        const response = await fetch(`${API_BASE}/rooms/`);
        if (response.ok) {
            const rooms = await response.json();
            const select = document.getElementById("reportRoomIdSelect");
            if (select) {
                select.innerHTML = '<option value="">Tất cả các phòng</option>';
                rooms.forEach(room => {
                    const option = document.createElement("option");
                    option.value = room.id;
                    option.textContent = room.name;
                    select.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error("Lỗi tải danh sách phòng cho bộ lọc báo cáo:", error);
    }
}

async function fetchRoomUsageReport() {
    const startDateVal = document.getElementById("reportStartDate").value;
    const endDateVal = document.getElementById("reportEndDate").value;
    const roomIdVal = document.getElementById("reportRoomIdSelect").value;
    const token = getAuthToken();

    let url = `${API_BASE}/v1/reports/room-usage?`;
    const params = new URLSearchParams();

    if (startDateVal) params.append("start_date", new Date(startDateVal).toISOString());
    if (endDateVal) params.append("end_date", new Date(endDateVal).toISOString());
    if (roomIdVal) params.append("room_id", roomIdVal);

    try {
        const response = await fetch(url + params.toString(), {
            method: "GET",
            headers: {
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json"
            }
        });

        if (response.status === 401) {
            alert("Phiên đăng nhập hết hạn hoặc bạn không có quyền Quản trị viên (Admin)!");
            return;
        }

        if (response.status === 400) {
            const errData = await response.json();
            alert(`Lỗi tham số: ${errData.detail || "Khoảng thời gian không hợp lệ"}`);
            return;
        }

        if (!response.ok) {
            throw new Error("Không thể kết nối lấy dữ liệu báo cáo.");
        }

        const data = await response.json();
        renderReportDataToDashboard(data);

    } catch (error) {
        console.error("Lỗi gọi API báo cáo:", error);
        alert("Đã xảy ra lỗi khi tải dữ liệu báo cáo từ máy chủ.");
    }
}

function renderReportDataToDashboard(data) {
    document.getElementById("sumTotalRooms").textContent = data.summary.total_rooms;
    document.getElementById("sumTotalMeetings").textContent = data.summary.total_meetings;
    document.getElementById("sumTotalHours").textContent = `${data.summary.total_hours.toFixed(1)} h`;
    document.getElementById("sumAvgOccupancy").textContent = `${data.summary.average_occupancy_rate.toFixed(1)}%`;

    const tbody = document.getElementById("roomDetailsTableBody");
    tbody.innerHTML = "";

    if (!data.room_details || data.room_details.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: #94a3b8; padding: 24px;">Không có dữ liệu cuộc họp trong khoảng thời gian này.</td></tr>`;
        return;
    }

    data.room_details.forEach(room => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${room.room_id}</td>
            <td><strong>${escapeHtml(room.room_name)}</strong></td>
            <td>${room.total_meetings}</td>
            <td>${room.total_hours.toFixed(1)} h</td>
            <td>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-weight: 600;">${room.occupancy_rate.toFixed(1)}%</span>
                    <div style="width: 100px; background: #e2e8f0; border-radius: 9999px; height: 8px; overflow: hidden;">
                        <div style="background: #2563eb; height: 100%; width: ${Math.min(room.occupancy_rate, 100)}%;"></div>
                    </div>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function populateCancellationRoomFilter() {
    const select = document.getElementById('cancellationRoomId');
    if (!select) return;
    const selectedRoomId = select.value;
    select.replaceChildren(new Option('Tất cả phòng', ''));
    allRooms.forEach(room => {
        select.add(new Option(room.name, String(room.id)));
    });
    if (selectedRoomId) select.value = selectedRoomId;
}

async function fetchCancellationAnalytics(e) {
    if (e && typeof e.preventDefault === 'function') e.preventDefault();
    const msgDiv = document.getElementById('cancellationAnalyticsMessage');
    const button = document.getElementById('btnFilterCancellation');
    const startDate = document.getElementById('cancellationStartDate')?.value;
    const endDate = document.getElementById('cancellationEndDate')?.value;
    const roomId = document.getElementById('cancellationRoomId')?.value;
    msgDiv?.classList.add('hidden');
    if (msgDiv) msgDiv.textContent = '';
    if (button) {
        button.disabled = true;
        button.textContent = 'Đang tải...';
    }

    const params = new URLSearchParams();
    if (startDate) params.set('start_date', startDate.slice(0, 10));
    if (endDate) params.set('end_date', endDate.slice(0, 10));
    if (roomId) params.set('room_id', roomId);

    try {
        const response = await fetch(
            `${API_BASE}/v1/admin/analytics/cancellations?${params.toString()}`,
            { headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` } },
        );
        if (!response.ok) {
            let detail = response.statusText;
            try {
                const error = await response.json();
                detail = error?.detail || error?.message || detail;
            } catch {
                // Fall back to the HTTP status text when the error response is not JSON.
            }
            throw new Error(`Lỗi server (${response.status}): ${detail || 'Không rõ lỗi'}`);
        }
        const data = await response.json();
        renderCancellationAnalytics(data);
    } catch (err) {
        console.error('Cancellation Analytics Error:', err);
        if (msgDiv) {
            msgDiv.textContent = `Lỗi tải thống kê: ${err instanceof Error ? err.message : String(err)}`;
            msgDiv.classList.remove('hidden');
        }
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = 'Xem thống kê';
        }
    }
}

async function exportCancellationAnalytics(format) {
    const msgDiv = document.getElementById('cancellationAnalyticsMessage');
    msgDiv?.classList.add('hidden');
    if (msgDiv) msgDiv.textContent = '';

    const params = new URLSearchParams({ format });
    const startDate = document.getElementById('cancellationStartDate')?.value;
    const endDate = document.getElementById('cancellationEndDate')?.value;
    const roomId = document.getElementById('cancellationRoomId')?.value;
    if (startDate) params.set('start_date', startDate.slice(0, 10));
    if (endDate) params.set('end_date', endDate.slice(0, 10));
    if (roomId) params.set('room_id', roomId);

    try {
        const response = await fetch(
            `${API_BASE}/v1/admin/analytics/cancellations/export?${params.toString()}`,
            { headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` } },
        );
        if (!response.ok) {
            let detail = response.statusText;
            try {
                const error = await response.json();
                detail = error?.detail || error?.message || detail;
            } catch {
                // Use the HTTP status text if the error body is not JSON.
            }
            throw new Error(`Lỗi server (${response.status}): ${detail || 'Không rõ lỗi'}`);
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        const extension = format === 'excel' ? 'xlsx' : 'pdf';
        link.href = url;
        link.download = `Bao_Cao_Huy_Phong_${new Date().toISOString().slice(0, 10)}.${extension}`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(() => window.URL.revokeObjectURL(url), 0);
    } catch (err) {
        console.error('Cancellation Analytics Export Error:', err);
        if (msgDiv) {
            msgDiv.textContent = `Lỗi xuất báo cáo: ${err instanceof Error ? err.message : String(err)}`;
            msgDiv.classList.remove('hidden');
        }
    }
}

async function exportExecutiveReport(format) {
    const message = document.getElementById('cancellationAnalyticsMessage');
    message?.classList.add('hidden');
    if (message) message.textContent = '';

    const params = new URLSearchParams({ format });
    const startDate = document.getElementById('executiveStartDate')?.value;
    const endDate = document.getElementById('executiveEndDate')?.value;
    const departmentId = document.getElementById('executiveDepartmentId')?.value;
    if (startDate) params.set('start_date', startDate.slice(0, 10));
    if (endDate) params.set('end_date', endDate.slice(0, 10));
    if (departmentId) params.set('department_id', departmentId);

    try {
        const response = await fetch(
            `${API_BASE}/v1/admin/analytics/executive-report/export?${params.toString()}`,
            { headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` } },
        );
        if (!response.ok) {
            let detail = response.statusText;
            try {
                const error = await response.json();
                detail = error?.detail || error?.message || detail;
            } catch {
                // Fall back to the HTTP status text for non-JSON error bodies.
            }
            throw new Error(`Lỗi server (${response.status}): ${detail || 'Không rõ lỗi'}`);
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `RoomSync_Executive_Report_${new Date().toISOString().slice(0, 10)}.${format === 'excel' ? 'xlsx' : 'pdf'}`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(() => window.URL.revokeObjectURL(url), 0);
    } catch (err) {
        console.error('Executive Report Export Error:', err);
        if (message) {
            message.textContent = `Lỗi xuất báo cáo: ${err instanceof Error ? err.message : String(err)}`;
            message.classList.remove('hidden');
        }
    }
}

function renderCancellationAnalytics(data) {
    const summary = data?.summary ?? {};
    const parsedTotal = Number(summary.total_cancelled ?? 0);
    const totalCancelled = Number.isFinite(parsedTotal) ? parsedTotal : 0;
    const parsedNoShow = Number(summary.cancelled_no_show ?? 0);
    const noShow = Number.isFinite(parsedNoShow) ? parsedNoShow : 0;
    const totalElement = document.getElementById('cancelledTotal');
    const hoursElement = document.getElementById('cancelledWastedHours');
    const noShowElement = document.getElementById('cancelledNoShowRate');
    if (totalElement) totalElement.textContent = String(totalCancelled);
    const wastedHours = Number(summary.total_wasted_hours ?? 0);
    if (hoursElement) {
        hoursElement.textContent = `${(Number.isFinite(wastedHours) ? wastedHours : 0).toFixed(2)} giờ`;
    }
    if (noShowElement) noShowElement.textContent =
        `${totalCancelled > 0 ? ((noShow / totalCancelled) * 100).toFixed(1) : '0.0'}%`;

    const renderRows = (elementId, rows, emptyMessage, valueKeys) => {
        const tbody = document.getElementById(elementId);
        if (!tbody) return;
        tbody.replaceChildren();
        if (!Array.isArray(rows) || rows.length === 0) {
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = valueKeys.length + 1;
            cell.className = 'cancellation-empty';
            cell.textContent = emptyMessage;
            row.appendChild(cell);
            tbody.appendChild(row);
            return;
        }
        rows.forEach(item => {
            const row = document.createElement('tr');
            valueKeys.forEach(key => {
                const cell = document.createElement('td');
                const value = item?.[key];
                cell.textContent = value == null ? '—' : String(value);
                row.appendChild(cell);
            });
            const countCell = document.createElement('td');
            countCell.textContent = String(Number(item?.cancel_count ?? 0));
            row.appendChild(countCell);
            tbody.appendChild(row);
        });
    };

    renderRows(
        'cancellationRoomsBody',
        data?.top_cancelled_rooms,
        'Không có dữ liệu trong khoảng thời gian này',
        ['room_name'],
    );
    renderRows(
        'cancellationReasonsBody',
        data?.breakdown_by_reason,
        'Không có dữ liệu trong khoảng thời gian này',
        ['reason'],
    );
    renderRows(
        'cancellationOffendersBody',
        data?.top_offenders,
        'Không có dữ liệu trong khoảng thời gian này',
        ['user_name'],
    );
}

/* GLOBAL EXPORTS (GẮN VÀO WINDOW CHO EVENT HANDLER) */
window.toggleSidebar = toggleSidebar;
window.switchToOverview = switchToOverview;
window.switchMainTab = switchMainTab;
window.navigateToSettings = navigateToSettings;
window.scrollToRooms = scrollToRooms;
window.toggleNotificationPopup = toggleNotificationPopup;
window.openScheduleModal = openScheduleModal;
window.closeScheduleModal = closeScheduleModal;
window.openQrCheckModal = openQrCheckModal;
window.closeQrCheckModal = closeQrCheckModal;
window.submitQrCheck = submitQrCheck;
window.openRoomQrModal = openRoomQrModal;
window.closeRoomQrModal = closeRoomQrModal;
window.copyRoomQrToken = copyRoomQrToken;
window.downloadRoomQrImage = downloadRoomQrImage;
window.openPresenterQrModal = openPresenterQrModal;
window.closePresenterQrModal = closePresenterQrModal;
window.togglePresenterQrFullscreen = togglePresenterQrFullscreen;
window.copyPresenterQrToken = copyPresenterQrToken;
window.cancelBooking = cancelBooking;
window.closeCancelMeetingModal = closeCancelMeetingModal;
window.submitCancelBooking = submitCancelBooking;
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
window.fetchEquipmentAvailability = fetchEquipmentAvailability;
window.scheduleEquipmentAvailabilityFetch = scheduleEquipmentAvailabilityFetch;
window.fetchAdminEquipments = fetchAdminEquipments;
window.toggleEquipmentActive = toggleEquipmentActive;
window.openEquipmentModal = openEquipmentModal;
window.openEditEquipmentModal = openEditEquipmentModal;
window.closeEquipmentModal = closeEquipmentModal;
window.handleEquipmentFormSubmit = handleEquipmentFormSubmit;
window.deleteEquipment = deleteEquipment;
window.fetchRoomUsageReport = fetchRoomUsageReport;
window.fetchCancellationAnalytics = fetchCancellationAnalytics;
window.loadRoomsForReportFilter = loadRoomsForReportFilter;
window.updateUserSettings = updateUserSettings;