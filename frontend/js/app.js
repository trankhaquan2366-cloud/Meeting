/* ==========================================================================
   GLOBAL CONFIGURATION & STATE MANAGEMENT
   ========================================================================== */
const API_BASE = (window.API_URL || 'https://roomsync-app.onrender.com/api').replace(/\/+$/, '');
const API_ORIGIN = new URL(API_BASE).origin;
const ROOM_THUMBNAILS = [
    'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1517502884422-41eaead166d4?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1577412647305-991150c7d163?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1431540015161-0bf868a2d407?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1568992687947-868a62a9f521?auto=format&fit=crop&w=800&q=80',
];
let allRooms = [];
let roomEquipmentCatalog = [];
let roomEquipmentLoaded = false;
let myBookings = [];
let allMeetings = [];
let overviewRoomsLoaded = false;
let overviewMeetingsLoaded = false;
let bookingCalendarView = 'month';
let bookingCalendarDate = new Date();
let bookingSelectedDate = new Date();
let selectedRoomId = null;
let equipmentAvailabilityTimer = null;
let googleCalendarOAuthError = null;
let userNotifications = [];
let notificationFetchVersion = 0;
let notificationMarkAllInProgress = false;
const notificationRsvpOverrides = new Map();
let activeQrScanner = null;
let quickQrScanner = null;
let quickQrSubmissionInProgress = false;
let quickQrResumeTimer = null;
let quickQrCloseTimer = null;
let activeQrMeetingId = null;
let activeQrAction = null;
let qrSubmissionInProgress = false;
let qrToastTimer = null;
let activeRoomQrToken = '';
let activePresenterQrToken = '';
let pendingCancelMeetingId = null;
let userListMountPromise = null;
let userDirectoryLoadPromise = null;

// Trích xuất access_token từ URL hash hoặc query param nếu có (sau khi Google OAuth redirect)
(function initAuthFromUrl() {
    const hashParams = window.location.hash ? new URLSearchParams(window.location.hash.slice(1)) : null;
    const queryParams = window.location.search ? new URLSearchParams(window.location.search) : null;
    const token = hashParams?.get('access_token') || hashParams?.get('token') || queryParams?.get('token') || queryParams?.get('access_token');
    if (token) {
        localStorage.setItem('token', token);
        localStorage.setItem('access_token', token);
        const params = (hashParams && (hashParams.get('access_token') || hashParams.get('token'))) ? hashParams : queryParams;
        if (params) {
            const userFields = {
                role: params.get('role'),
                user_name: params.get('full_name') || params.get('username'),
                user_email: params.get('email'),
                user_id: params.get('user_id'),
                user_picture: params.get('picture'),
            };
            Object.entries(userFields).forEach(([key, val]) => {
                if (val) localStorage.setItem(key, val);
            });
        }
        window.history.replaceState({}, document.title, window.location.pathname);
    }
})();

// Hàm bổ trợ lấy Auth Token
function getAuthToken() {
    return localStorage.getItem('token') || localStorage.getItem('access_token') || '';
}

async function fetchAPI(...args) {
    const [input, init = {}] = args;
    const headers = new Headers(input instanceof Request ? input.headers : undefined);
    new Headers(init.headers || {}).forEach((value, name) => headers.set(name, value));
    const token = getAuthToken();
    if (token && !headers.has('Authorization')) {
        headers.set('Authorization', `Bearer ${token}`);
    }
    const requestInput = typeof input === 'string' && input.startsWith('/')
        ? new URL(input, `${API_ORIGIN}/`).href
        : input;
    const response = await window.fetch(requestInput, { ...init, headers });
    if (response.status === 401 && getAuthToken()) {
        localStorage.removeItem('token');
        localStorage.removeItem('access_token');

        const pathname = window.location.pathname;
        const loginPath = pathname.endsWith('/dashboard.html')
            ? pathname.replace(/dashboard\.html$/, 'index.html')
            : pathname === '/dashboard'
                ? '/app'
                : 'index.html';
        window.location.replace(loginPath);
    }
    return response;
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
    initializeDirectoryManagement();
    document.getElementById('adminUserProjectGroups')?.addEventListener('change', event => {
        const select = event.currentTarget;
        if (!(select instanceof HTMLSelectElement)) return;
        const hasGroups = Array.from(select.selectedOptions).some(option => option.value !== '');
        select.options[0].selected = !hasGroups;
    });
    document.getElementById('btnRunUsageReport')?.addEventListener('click', loadUsageReportData);
    document.getElementById('btnFilterCancellation')?.addEventListener('click', loadCancelReportData);
    document.getElementById('btn-open-executive-modal')?.addEventListener('click', openExecutiveReportModal);
    document.getElementById('btn-close-executive-modal')?.addEventListener('click', closeExecutiveReportModal);
    document.getElementById('btn-export-executive-excel')?.addEventListener(
        'click',
        () => exportExecutiveReport('excel'),
    );
    document.getElementById('btn-export-executive-pdf')?.addEventListener(
        'click',
        () => exportExecutiveReport('pdf'),
    );
    document.getElementById('executiveReportModal')?.addEventListener('click', event => {
        if (event.target === event.currentTarget) closeExecutiveReportModal();
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape'
            && document.getElementById('executiveReportModal')?.getAttribute('aria-hidden') === 'false') {
            closeExecutiveReportModal();
        }
    });
    if (!token && !isMeetingPreview) {
        window.location.href = 'index.html';
        return;
    }

    let userName = localStorage.getItem('user_name') || 'Người dùng';
    let userEmail = localStorage.getItem('user_email') || '';
    let role = localStorage.getItem('role') || 'user';

    // Gọi API lấy thông tin chuẩn từ Database trực tiếp
    try {
        const profileRes = await fetchAPI(`${API_BASE}/users/me`, {
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

    const isAdmin = String(role).trim().toLowerCase() === 'admin';

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
        const userManagementNav = document.getElementById('navUserManagement');
        if (btn1) btn1.style.display = 'block';
        if (btn2) btn2.style.display = 'block';
        if (addEqBtn) addEqBtn.style.display = 'block';
        if (adminEqSection) adminEqSection.style.display = 'block';
        if (userManagementNav) userManagementNav.style.display = 'flex';
    } else {
        const navReport = document.getElementById('navReport');
        const cancellationTab = document.getElementById('report-tab-cancel');
        const userManagementNav = document.getElementById('navUserManagement');
        if (navReport) navReport.style.display = 'none';
        if (cancellationTab) cancellationTab.hidden = true;
        if (userManagementNav) userManagementNav.style.display = 'none';
    }

    // Tải dữ liệu ban đầu
    fetchRooms(isAdmin).then(() => {
        fetchMyBookings();
        if (isAdmin) populateCancellationRoomFilter();
    });
    window.setInterval(() => {
        updateOverviewKPICards(
            overviewRoomsLoaded ? allRooms : null,
            overviewMeetingsLoaded ? allMeetings : null,
        );
    }, 60_000);
    initializeNotifications();
    initializeRsvpActions();
    setDefaultEquipmentAvailabilityTimes();
    if (isAdmin) {
        fetchAdminEquipments();
    }

    // Khởi tạo thời gian mặc định cho bộ lọc báo cáo
    const reportEnd = document.getElementById("reportEndDate");
    const reportStart = document.getElementById("reportStartDate");
    if (reportEnd && reportStart) {
        const thirtyDaysAgo = new Date(now.getTime() - (30 * 24 * 60 * 60 * 1000));
        const localDate = value => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`;
        reportEnd.value = localDate(now);
        reportStart.value = localDate(thirtyDaysAgo);
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
    toggleMobileMenu();
}

function toggleMobileMenu() {
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('mobileMenuBackdrop');
    const menuButton = document.querySelector('.btn-toggle-menu');
    if (!sidebar || !backdrop) return;

    const isOpen = sidebar.classList.contains('translate-x-0');
    if (isOpen) {
        closeMobileMenu();
        return;
    }

    sidebar.classList.remove('-translate-x-full');
    sidebar.classList.add('translate-x-0');
    backdrop.classList.remove('hidden');
    document.body.classList.add('mobile-menu-open');
    if (menuButton) menuButton.setAttribute('aria-expanded', 'true');
}

function closeMobileMenu() {
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('mobileMenuBackdrop');
    const menuButton = document.querySelector('.btn-toggle-menu');

    if (sidebar) {
        sidebar.classList.remove('translate-x-0');
        sidebar.classList.add('-translate-x-full');
    }
    if (backdrop) backdrop.classList.add('hidden');
    document.body.classList.remove('mobile-menu-open');
    if (menuButton) menuButton.setAttribute('aria-expanded', 'false');
}

function switchToOverview() {
    const overviewTab = document.getElementById('navOverview');
    switchMainTab('overview', overviewTab);
}

function switchMainTab(tabName, el) {
    if (tabName === 'users' && !isCurrentUserAdmin()) {
        showAppToast('Bạn không có quyền truy cập mục quản trị này.', 'error');
        return;
    }

    closeMobileMenu();
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    if (el) el.classList.add('active');
    document.querySelectorAll('.mobile-nav-item[data-tab]').forEach(item => {
        const isActive = item.dataset.tab === tabName;
        item.classList.toggle('active', isActive);
        item.setAttribute('aria-current', isActive ? 'page' : 'false');
    });

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
        switchReportTab('usage');
    } else if (tabName === 'settings') {
        const view = document.getElementById('viewSettings');
        if (view) view.style.display = 'block';
        if (searchContainer) searchContainer.style.display = 'none';
        loadCurrentUserProfile();
        loadGoogleCalendarStatus();
    } else if (tabName === 'users') {
        const view = document.getElementById('viewUserManagement');
        if (view) view.style.display = 'block';
        if (searchContainer) searchContainer.style.display = 'none';
        showUserManagementSection('list');
    }
}

function showUserManagementSection(section) {
    if (!isCurrentUserAdmin()) {
        showAppToast('Bạn không có quyền truy cập mục quản trị này.', 'error');
        return;
    }

    const selectedSection = ['create', 'directories'].includes(section) ? section : 'list';
    const showList = selectedSection === 'list';
    const showCreate = selectedSection === 'create';
    const showDirectories = selectedSection === 'directories';
    const listPanel = document.getElementById('userListModePanel');
    const createPanel = document.getElementById('userCreateModePanel');
    const directoriesPanel = document.getElementById('userDirectoriesModePanel');
    const listTab = document.getElementById('userListModeTab');
    const createTab = document.getElementById('userCreateModeTab');
    const directoriesTab = document.getElementById('userDirectoriesModeTab');

    if (listPanel) listPanel.hidden = !showList;
    if (createPanel) createPanel.hidden = !showCreate;
    if (directoriesPanel) directoriesPanel.hidden = !showDirectories;
    [
        [listTab, showList],
        [createTab, showCreate],
        [directoriesTab, showDirectories],
    ].forEach(([tab, selected]) => {
        if (!tab) return;
        tab.setAttribute('aria-selected', String(selected));
        tab.classList.toggle('border-blue-600', selected);
        tab.classList.toggle('text-blue-700', selected);
        tab.classList.toggle('border-transparent', !selected);
        tab.classList.toggle('text-slate-500', !selected);
    });

    if (showList) {
        const userList = window.RoomSyncUserList;
        if (!userList || typeof userList.mountUserListTable !== 'function') {
            showAppToast('Không tải được giao diện danh sách người dùng. Vui lòng tải lại trang.', 'error');
            return;
        }

        if (!userListMountPromise) {
            userListMountPromise = userList.mountUserListTable(
                'userListTableContainer',
                () => showUserManagementSection('create'),
            ).catch(error => {
                userListMountPromise = null;
                console.error('Không thể khởi tạo danh sách người dùng:', error);
                showAppToast('Không thể khởi tạo danh sách người dùng. Vui lòng thử lại.', 'error');
            });
        }
    } else if (showCreate) {
        void loadAdminUserDirectories();
        document.getElementById('adminUserFullName')?.focus();
    } else {
        void loadAdminUserDirectories();
    }
}

async function fetchAdminUserDirectory(path, label) {
    const token = getAuthToken();
    const response = await fetchAPI(path, {
        headers: {
            Accept: 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
    });
    if (!response.ok) {
        throw new Error(`Không thể tải danh sách ${label} (HTTP ${response.status}).`);
    }

    const records = await response.json();
    if (!Array.isArray(records)) {
        throw new Error(`Danh sách ${label} trả về dữ liệu không hợp lệ.`);
    }
    return records;
}

function populateAdminUserSelect(selectId, records, label) {
    const select = document.getElementById(selectId);
    if (!(select instanceof HTMLSelectElement)) return;

    const selectedValues = new Set(Array.from(select.selectedOptions, option => option.value));
    while (select.options.length > 1) select.remove(1);
    for (const record of records) {
        const id = Number(record?.id);
        const name = typeof record?.name === 'string' ? record.name.trim() : '';
        if (!Number.isSafeInteger(id) || id < 1 || !name) {
            throw new Error(`Danh sách ${label} chứa mục không hợp lệ.`);
        }

        const option = document.createElement('option');
        option.value = String(id);
        option.textContent = name;
        option.selected = selectedValues.has(option.value);
        select.add(option);
    }
}

const directoryManagementState = {
    departments: [],
    projectGroups: [],
    editing: null,
};

function renderManagedDirectory(type) {
    const isDepartment = type === 'department';
    const records = isDepartment
        ? directoryManagementState.departments
        : directoryManagementState.projectGroups;
    const container = document.getElementById(isDepartment ? 'departmentsList' : 'projectGroupsList');
    if (!container) return;
    const editing = directoryManagementState.editing;

    if (!records.length) {
        container.innerHTML = `<li class="py-3 text-sm text-slate-500">Chưa có ${isDepartment ? 'phòng ban' : 'nhóm dự án'} nào. Hãy thêm mục đầu tiên.</li>`;
        return;
    }

    container.innerHTML = records.map(record => {
        const isEditing = editing?.type === type && editing.id === record.id;
        const safeName = escapeHtml(record.name);
        const accessibleType = isDepartment ? 'phòng ban' : 'nhóm dự án';
        return `<li class="flex items-center justify-between gap-3 py-3" data-directory-row="${record.id}">
            ${isEditing
                ? `<form class="flex min-w-0 flex-1 items-center gap-2" data-directory-edit-form data-directory-type="${type}" data-directory-id="${record.id}">
                    <label class="sr-only" for="edit-${type}-${record.id}">Tên ${accessibleType}</label>
                    <input id="edit-${type}-${record.id}" name="name" value="${safeName}" maxlength="120" required
                        class="min-w-0 flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20">
                    <button type="submit" class="rounded-lg px-3 py-2 text-sm font-semibold text-blue-700 hover:bg-blue-50">Lưu</button>
                    <button type="button" data-directory-action="cancel" data-directory-type="${type}" class="rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100">Hủy</button>
                </form>`
                : `<span class="min-w-0 flex-1 text-sm font-medium text-slate-800">${safeName}</span>
                    <div class="flex shrink-0 gap-1">
                        <button type="button" data-directory-action="edit" data-directory-type="${type}" data-directory-id="${record.id}"
                            class="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500">Sửa</button>
                        <button type="button" data-directory-action="delete" data-directory-type="${type}" data-directory-id="${record.id}"
                            class="rounded-lg px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500">Xóa</button>
                    </div>`}
        </li>`;
    }).join('');

    if (editing?.type === type) {
        container.querySelector('input')?.focus();
    }
}

function setDirectoryMessage(type, message, isError = false) {
    const messageId = type === 'department' ? 'departmentsMessage' : 'projectGroupsMessage';
    const element = document.getElementById(messageId);
    if (!element) return;
    element.textContent = message;
    element.classList.toggle('text-red-700', isError);
    element.classList.toggle('text-emerald-700', !isError && Boolean(message));
}

async function refreshAdminUserDirectories() {
    const [departments, projectGroups] = await Promise.all([
        fetchAdminUserDirectory(`${API_BASE}/departments`, 'phòng ban'),
        fetchAdminUserDirectory(`${API_BASE}/teams`, 'nhóm dự án'),
    ]);
    directoryManagementState.departments = departments;
    directoryManagementState.projectGroups = projectGroups;
    populateAdminUserSelect('adminUserDepartment', departments, 'phòng ban');
    populateAdminUserSelect('adminUserProjectGroups', projectGroups, 'nhóm dự án');
    renderManagedDirectory('department');
    renderManagedDirectory('project-group');
}

function loadAdminUserDirectories() {
    if (userDirectoryLoadPromise) return userDirectoryLoadPromise;

    userDirectoryLoadPromise = refreshAdminUserDirectories().catch(error => {
        console.error('Không thể tải danh mục phòng ban và nhóm dự án:', error);
        showAppToast(
            error instanceof Error ? error.message : 'Không thể tải danh sách phòng ban và nhóm dự án.',
            'error',
        );
    }).finally(() => {
        userDirectoryLoadPromise = null;
    });
    return userDirectoryLoadPromise;
}

function initializeDirectoryManagement() {
    document.querySelectorAll('form[data-directory-type]:not([data-directory-edit-form])').forEach(form => {
        form.addEventListener('submit', async event => {
            event.preventDefault();
            if (!isCurrentUserAdmin()) {
                showAppToast('Chỉ quản trị viên mới được quản lý phòng ban và nhóm dự án.', 'error');
                return;
            }
            const type = form.dataset.directoryType;
            const isDepartment = type === 'department';
            const input = form.elements.namedItem('name');
            if (!(input instanceof HTMLInputElement) || !form.reportValidity()) return;
            const button = form.querySelector('button[type="submit"]');
            if (button) button.disabled = true;
            setDirectoryMessage(type, '');
            try {
                const response = await fetchAPI(
                    `${API_BASE}/${isDepartment ? 'departments' : 'teams'}`,
                    {
                        method: 'POST',
                        headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: input.value.trim() }),
                    },
                );
                const result = await response.json();
                if (!response.ok) throw new Error(result.detail || `Không thể thêm mục (HTTP ${response.status}).`);
                form.reset();
                await refreshAdminUserDirectories();
                setDirectoryMessage(type, `Đã thêm ${isDepartment ? 'phòng ban' : 'nhóm dự án'} "${result.name}".`);
            } catch (error) {
                setDirectoryMessage(
                    type,
                    error instanceof Error ? error.message : 'Không thể thêm mục. Vui lòng thử lại.',
                    true,
                );
            } finally {
                if (button) button.disabled = false;
            }
        });
    });

    document.addEventListener('submit', async event => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement) || !form.matches('[data-directory-edit-form]')) return;
        event.preventDefault();
        if (!isCurrentUserAdmin()) {
            showAppToast('Chỉ quản trị viên mới được quản lý phòng ban và nhóm dự án.', 'error');
            return;
        }
        const type = form.dataset.directoryType;
        const isDepartment = type === 'department';
        const input = form.elements.namedItem('name');
        if (!(input instanceof HTMLInputElement) || !form.reportValidity()) return;
        const button = form.querySelector('button[type="submit"]');
        if (button) button.disabled = true;
        try {
            const response = await fetchAPI(
                `${API_BASE}/${isDepartment ? 'departments' : 'teams'}/${form.dataset.directoryId}`,
                {
                    method: 'PUT',
                    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: input.value.trim() }),
                },
            );
            const result = await response.json();
            if (!response.ok) throw new Error(result.detail || `Không thể cập nhật mục (HTTP ${response.status}).`);
            directoryManagementState.editing = null;
            await refreshAdminUserDirectories();
            setDirectoryMessage(type, `Đã cập nhật tên thành "${result.name}".`);
        } catch (error) {
            setDirectoryMessage(
                type,
                error instanceof Error ? error.message : 'Không thể cập nhật mục. Vui lòng thử lại.',
                true,
            );
        } finally {
            if (button) button.disabled = false;
        }
    });

    document.addEventListener('click', async event => {
        if (!(event.target instanceof Element)) return;
        const button = event.target.closest('button[data-directory-action]');
        if (!button) return;
        const { directoryAction: action, directoryType: type, directoryId } = button.dataset;
        if (action === 'cancel') {
            directoryManagementState.editing = null;
            renderManagedDirectory(type);
            return;
        }
        if (action === 'edit') {
            directoryManagementState.editing = { type, id: Number(directoryId) };
            renderManagedDirectory(type);
            return;
        }
        if (action !== 'delete' || !isCurrentUserAdmin()) return;
        const isDepartment = type === 'department';
        const noun = isDepartment ? 'phòng ban' : 'nhóm dự án';
        const impact = isDepartment
            ? 'Người dùng đang thuộc phòng ban này sẽ không còn được gán phòng ban.'
            : 'Liên kết giữa nhóm này và người dùng sẽ bị gỡ.';
        if (!window.confirm(`Xóa ${noun} này? ${impact}`)) return;
        button.disabled = true;
        setDirectoryMessage(type, '');
        try {
            const response = await fetchAPI(
                `${API_BASE}/${isDepartment ? 'departments' : 'teams'}/${directoryId}`,
                { method: 'DELETE', headers: { Accept: 'application/json' } },
            );
            if (!response.ok) {
                const result = await response.json();
                throw new Error(result.detail || `Không thể xóa mục (HTTP ${response.status}).`);
            }
            directoryManagementState.editing = null;
            await refreshAdminUserDirectories();
            setDirectoryMessage(type, `Đã xóa ${noun}.`);
        } catch (error) {
            setDirectoryMessage(
                type,
                error instanceof Error ? error.message : 'Không thể xóa mục. Vui lòng thử lại.',
                true,
            );
        } finally {
            button.disabled = false;
        }
    });
}

function isCurrentUserAdmin() {
    return String(localStorage.getItem('role') || '').trim().toLowerCase() === 'admin';
}

document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
        const openMenus = document.querySelectorAll('.room-actions-menu[open]');
        openMenus.forEach(menu => {
            const restoreFocus = menu.contains(event.target);
            menu.open = false;
            if (restoreFocus) menu.querySelector('summary')?.focus();
        });
        closeMobileMenu();
    }
});

document.addEventListener('click', event => {
    if (!(event.target instanceof Element)) return;
    document.querySelectorAll('.room-actions-menu[open]').forEach(menu => {
        if (!menu.contains(event.target)) menu.open = false;
    });
});

window.addEventListener('resize', () => {
    if (window.innerWidth >= 1024) closeMobileMenu();
});

async function loadGoogleCalendarStatus() {
    const statusElement = document.getElementById('googleCalendarStatus');
    const actionButton = document.getElementById('googleCalendarAction');
    if (!statusElement || !actionButton) return;

    actionButton.disabled = true;
    statusElement.textContent = 'Đang kiểm tra kết nối...';
    try {
        const response = await fetchAPI(`${API_BASE}/auth/google/calendar/status`, {
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
            const response = await fetchAPI(`${API_BASE}/auth/google/calendar/disconnect`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${getAuthToken()}` },
            });
            if (!response.ok) throw new Error(`Không thể ngắt kết nối Google Calendar (${response.status})`);
            await loadGoogleCalendarStatus();
            return;
        }

        const response = await fetchAPI(`${API_BASE}/auth/google/calendar/authorize`, {
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
        const response = await fetchAPI(`${API_BASE}/auth/me`, {
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
        const res = await fetchAPI(`${API_BASE}/users/me`, {
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
function initializeNotifications() {
    const popup = document.getElementById('notificationPopup');
    if (popup) {
        popup.addEventListener('click', event => {
            const markAllButton = event.target.closest('button[data-mark-all-notifications]');
            if (markAllButton) {
                markAllNotificationsAsRead();
                return;
            }
            const action = event.target.closest('button[data-notification-rsvp]');
            if (action) {
                event.preventDefault();
                event.stopPropagation();
                if (action.disabled) return;
                respondToMeeting(
                    Number(action.dataset.rsvpMeeting),
                    action.dataset.notificationRsvp,
                    Number(action.dataset.notificationId)
                );
                return;
            }
            const item = event.target.closest('button[data-notification-id]');
            if (item) markNotificationAsRead(Number(item.dataset.notificationId));
        });
    }
    fetchNotifications();
    window.setInterval(fetchNotifications, 30000);
}

async function fetchNotifications() {
    const requestVersion = ++notificationFetchVersion;
    const token = getAuthToken();
    if (!token) {
        redirectToLogin();
        return false;
    }

    try {
        const res = await fetchAPI(`${API_BASE}/notifications/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (handleUnauthorizedResponse(res)) return false;
        if (res.ok) {
            const notifications = await res.json();
            if (requestVersion !== notificationFetchVersion) return false;
            userNotifications = notifications;
            renderNotifications(userNotifications);
            return true;
        } else {
            const message = await apiErrorMessage(res, 'Không thể tải thông báo.');
            if (requestVersion === notificationFetchVersion) renderNotificationError(message);
        }
    } catch (err) {
        console.error("Lỗi lấy danh sách thông báo:", err);
        if (requestVersion === notificationFetchVersion) {
            renderNotificationError('Không thể kết nối máy chủ để tải thông báo.');
        }
    }
    return false;
}

async function markNotificationAsRead(notificationId) {
    const notification = userNotifications.find(item => Number(item.id) === notificationId);
    if (!notification || notification.is_read) return;

    try {
        const res = await fetch(`${API_BASE}/notifications/${notificationId}/read`, {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });
        if (handleUnauthorizedResponse(res)) return;
        if (!res.ok) {
            alert(await apiErrorMessage(res, 'Không thể đánh dấu thông báo đã đọc.'));
            return;
        }
        notification.is_read = true;
        renderNotifications(userNotifications);
    } catch (err) {
        console.error('Lỗi cập nhật trạng thái thông báo:', err);
        alert('Không thể kết nối máy chủ để cập nhật thông báo.');
    }
}

function handleUnauthorizedResponse(response) {
    if (response.status !== 401) return false;
    redirectToLogin();
    return true;
}

function redirectToLogin() {
    alert('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
    window.location.href = 'index.html';
}

async function apiErrorMessage(response, fallback) {
    if (response.status === 401) return 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.';
    if (response.status === 403) return 'Bạn không được mời tham gia cuộc họp này.';
    try {
        const result = await response.json();
        if (response.status === 400 && result.detail === 'Organizer cannot respond to their own meeting') {
            return 'Người tổ chức không thể phản hồi cuộc họp của chính mình.';
        }
        return result.detail || fallback;
    } catch (err) {
        return response.status === 400
            ? 'Yêu cầu không hợp lệ. Vui lòng kiểm tra lại thao tác.'
            : fallback;
    }
}

function linkifyNotificationContent(content) {
    const text = String(content || '');
    const urlPattern = /https?:\/\/[^\s<>"']+/gi;
    const trailingPunctuationPattern = /[.,!?;:)\]}]+$/;
    let html = '';
    let cursor = 0;
    let match;

    while ((match = urlPattern.exec(text)) !== null) {
        const rawUrl = match[0];
        const trailingPunctuation = rawUrl.match(trailingPunctuationPattern)?.[0] || '';
        const candidate = rawUrl.slice(0, rawUrl.length - trailingPunctuation.length);
        let safeUrl = '';
        try {
            const parsed = new URL(candidate);
            if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
                safeUrl = parsed.href;
            }
        } catch (error) {
            safeUrl = '';
        }
        if (!safeUrl) continue;

        html += escapeHtml(text.slice(cursor, match.index));
        html += `<a href="${escapeHtml(safeUrl)}" target="_blank" rel="noopener noreferrer"
            class="text-blue-600 underline hover:text-blue-800"
            onclick="event.stopPropagation()">${escapeHtml(candidate)}</a>${escapeHtml(trailingPunctuation)}`;
        cursor = match.index + rawUrl.length;
    }
    return html + escapeHtml(text.slice(cursor));
}

function notificationMeetingLink(notification) {
    const candidate = notification?.meeting_link;
    if (candidate) {
        try {
            const parsed = new URL(candidate);
            if (parsed.protocol === 'http:' || parsed.protocol === 'https:') return parsed.href;
        } catch (error) {
            // Fall through and look for a Google Meet URL in the message.
        }
    }
    const content = String(notification?.content || '');
    const urls = content.match(/https?:\/\/[^\s<>"']+/gi) || [];
    for (const rawUrl of urls) {
        const candidateUrl = rawUrl.replace(/[.,!?;:)\]}]+$/, '');
        try {
            const parsed = new URL(candidateUrl);
            if (parsed.protocol === 'http:' && parsed.hostname === 'meet.google.com'
                || parsed.protocol === 'https:' && parsed.hostname === 'meet.google.com') {
                return parsed.href;
            }
        } catch (error) {
            continue;
        }
    }
    return '';
}

function renderNotifications(notifications) {
    const popup = document.getElementById('notificationPopup');
    if (!popup) return;

    if (!notifications || notifications.length === 0) {
        updateNotificationDot(0);
        popup.innerHTML = `
            ${notificationHeaderHTML(0)}
            <div class="notification-list">
                <div class="notification-empty">Không có thông báo nào.</div>
            </div>
        `;
        return;
    }

    const unreadCount = notifications.filter(n => !n.is_read).length;
    updateNotificationDot(unreadCount);

    popup.innerHTML = `
        ${notificationHeaderHTML(unreadCount)}
        <div class="notification-list">
            ${notifications.map(n => {
                const cancelled = ['cancelled', 'canceled'].includes(
                    String(n.meeting_status || '').trim().toLowerCase()
                );
                const timestampValue = String(n.created_at || '');
                const utcTimestamp = /(?:Z|[+-]\d{2}:\d{2})$/i.test(timestampValue)
                    ? timestampValue
                    : `${timestampValue}Z`;
                const timestamp = new Date(utcTimestamp);
                const localTimestamp = Number.isNaN(timestamp.getTime())
                    ? 'Thời gian không xác định'
                    : timestamp.toLocaleString();
                const linkedMeeting = cancelled ? null : resolveNotificationMeeting(n);
                const actions = linkedMeeting ? renderNotificationRsvpActions(n, linkedMeeting) : '';
                const meetingLink = notificationMeetingLink(n);
                const joinAction = !cancelled && meetingLink
                    ? `<a class="notification-join-meeting" href="${escapeHtml(meetingLink)}"
                        target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()">
                        📹 Tham gia họp
                    </a>`
                    : '';
                const itemTitle = cancelled ? 'Cuộc họp đã bị hủy' : n.title;
                const itemContent = cancelled
                    ? `Cuộc họp '${n.meeting_title || 'này'}' đã bị người tổ chức hủy. Bạn không cần tham gia.`
                    : n.content;
                return `<article class="notification-entry ${n.is_read ? '' : 'unread'}">
                    <button type="button" class="notification-item ${n.is_read ? '' : 'unread'}"
                        data-notification-id="${Number(n.id)}">
                        <span class="notification-item-title">${escapeHtml(itemTitle)}</span>
                        <span class="notification-item-time">${escapeHtml(localTimestamp)}</span>
                    </button>
                    <div class="notification-item-content">${linkifyNotificationContent(itemContent)}</div>
                    ${joinAction ? `<div class="notification-join-row">${joinAction}</div>` : ''}
                    ${actions}
                </article>`;
            }).join('')}
        </div>
    `;
}

function notificationHeaderHTML(unreadCount) {
    return `
        <header class="notification-popup-header">
            <div class="notification-popup-heading">
                <h2>Thông báo</h2>
                <span id="notificationUnreadCount" class="notification-unread-count"
                    aria-live="polite">${unreadCount} chưa đọc</span>
            </div>
            <button class="notification-mark-all" type="button" data-mark-all-notifications
                ${unreadCount === 0 ? 'disabled' : ''}>
                Đánh dấu tất cả là đã đọc
            </button>
        </header>
    `;
}

async function markAllNotificationsAsRead() {
    if (notificationMarkAllInProgress) return;

    const unreadNotifications = userNotifications.filter(notification => !notification.is_read);
    if (unreadNotifications.length === 0) {
        updateNotificationDot(0);
        return;
    }

    const previousReadStates = unreadNotifications.map(notification => ({
        notification,
        isRead: notification.is_read,
    }));
    notificationMarkAllInProgress = true;
    unreadNotifications.forEach(notification => { notification.is_read = true; });
    renderNotifications(userNotifications);

    try {
        const token = getAuthToken();
        if (!token) {
            previousReadStates.forEach(({ notification, isRead }) => { notification.is_read = isRead; });
            renderNotifications(userNotifications);
            redirectToLogin();
            return;
        }

        const res = await fetch(`${API_BASE}/notifications/read-all`, {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (handleUnauthorizedResponse(res)) {
            previousReadStates.forEach(({ notification, isRead }) => { notification.is_read = isRead; });
            renderNotifications(userNotifications);
            return;
        }
        if (!res.ok) {
            throw new Error(await apiErrorMessage(res, 'Không thể đánh dấu tất cả thông báo đã đọc.'));
        }

        await fetchNotifications();
    } catch (error) {
        previousReadStates.forEach(({ notification, isRead }) => { notification.is_read = isRead; });
        renderNotifications(userNotifications);
        renderNotificationError(error.message || 'Không thể đánh dấu tất cả thông báo đã đọc.');
        console.error('Lỗi đánh dấu tất cả thông báo đã đọc:', error);
        showAppToast(error.message || 'Không thể đánh dấu tất cả thông báo đã đọc.', 'error');
    } finally {
        notificationMarkAllInProgress = false;
    }
}

function resolveNotificationMeeting(notification) {
    if (!notification || !String(notification.title || '').toLowerCase().includes('lời mời')) return null;
    const meetingId = Number(notification.meeting_id);
    if (Number.isInteger(meetingId) && meetingId > 0) {
        return myBookings.find(meeting => Number(meeting.id) === meetingId && !meeting.is_organizer)
            || { id: meetingId, is_organizer: false, my_response_status: 'pending' };
    }

    const titleMatch = String(notification.content || '').match(/cuộc họp ['‘](.+?)['’]/i);
    if (!titleMatch) return null;
    const candidates = myBookings.filter(meeting =>
        !meeting.is_organizer && String(meeting.title || '') === titleMatch[1]
    );
    return candidates.length === 1 ? candidates[0] : null;
}

function renderNotificationRsvpActions(notification, meeting) {
    const normalizedResponse = getMeetingRsvpStatus(meeting);
    const notificationId = Number(notification.id);
    const meetingId = Number(meeting.id);
    if (normalizedResponse === 'accepted') {
        return `<div class="notification-rsvp-actions">
            <span class="badge-status accepted">Đã đồng ý</span>
            <button type="button" class="btn-rsvp btn-reject" data-rsvp-meeting="${meetingId}"
                data-notification-id="${notificationId}" data-notification-rsvp="rejected">Đổi sang từ chối</button>
        </div>`;
    }
    if (normalizedResponse === 'rejected') {
        return `<div class="notification-rsvp-actions">
            <span class="badge-status rejected">Đã từ chối</span>
            <button type="button" class="btn-rsvp btn-accept" data-rsvp-meeting="${meetingId}"
                data-notification-id="${notificationId}" data-notification-rsvp="accepted">Đổi sang chấp nhận</button>
        </div>`;
    }
    return `<div class="notification-rsvp-actions">
        <button type="button" class="btn-rsvp btn-accept" data-rsvp-meeting="${meetingId}"
            data-notification-id="${notificationId}" data-notification-rsvp="accepted">Chấp nhận</button>
        <button type="button" class="btn-rsvp btn-reject" data-rsvp-meeting="${meetingId}"
            data-notification-id="${notificationId}" data-notification-rsvp="rejected">Từ chối</button>
    </div>`;
}

function renderNotificationError(message) {
    const popup = document.getElementById('notificationPopup');
    if (!popup) return;
    if (userNotifications.length === 0) {
        popup.innerHTML = `<div class="notification-empty" role="alert">${escapeHtml(message)}</div>`;
        return;
    }
    const previousError = popup.querySelector('[data-notification-error]');
    if (previousError) previousError.remove();
    popup.insertAdjacentHTML(
        'afterbegin',
        `<div class="notification-empty" role="alert" data-notification-error>${escapeHtml(message)}</div>`
    );
}

function updateNotificationDot(unreadCount) {
    const dot = document.getElementById('notificationDot');
    if (!dot) return;
    dot.textContent = unreadCount > 99 ? '99+' : String(unreadCount);
    dot.style.display = unreadCount > 0 ? 'block' : 'none';
    const bell = document.getElementById('notificationBellBtn');
    if (bell) bell.setAttribute('aria-label', unreadCount > 0 ? `Thông báo, ${unreadCount} chưa đọc` : 'Thông báo');
}

function toggleNotificationPopup() {
    const popup = document.getElementById('notificationPopup');
    if (!popup) return;

    const isHidden = popup.style.display === 'none' || !popup.style.display;
    popup.style.display = isHidden ? 'flex' : 'none';
    const bell = document.getElementById('notificationBellBtn');
    if (bell) bell.setAttribute('aria-expanded', String(isHidden));

    if (isHidden) {
        fetchNotifications().then(loaded => {
            if (loaded) markAllNotificationsAsRead();
        });
    }
}

document.addEventListener('click', function (e) {
    const wrapper = document.querySelector('.notification-wrapper');
    const popup = document.getElementById('notificationPopup');
    if (!wrapper || !popup) return;
    if (!wrapper.contains(e.target) && popup.style.display !== 'none') {
        popup.style.display = 'none';
        const bell = document.getElementById('notificationBellBtn');
        if (bell) bell.setAttribute('aria-expanded', 'false');
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

    for (let h = 0; h <= 23; h++) {
        for (let m of ['00', '30']) {
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
async function fetchMeetings() {
    try {
        const response = await fetchAPI(`${API_BASE}/meetings/`, {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` },
        });
        if (handleUnauthorizedResponse(response)) return;
        if (!response.ok) throw new Error(`Không thể tải danh sách cuộc họp (HTTP ${response.status}).`);
        const meetings = await response.json();
        if (!Array.isArray(meetings)) throw new Error('Dữ liệu danh sách cuộc họp không hợp lệ.');
        allMeetings = meetings;
        overviewMeetingsLoaded = true;
        updateOverviewKPICards(overviewRoomsLoaded ? allRooms : null, allMeetings);
        if (overviewRoomsLoaded) {
            applyFilters();
        }
    } catch (error) {
        console.error('Lỗi lấy dữ liệu KPI cuộc họp:', error);
        updateOverviewKPICards(overviewRoomsLoaded ? allRooms : null, null);
    }
}

async function fetchRooms(isAdmin) {
    try {
        const token = getAuthToken();
        const roomsEndpoint = isAdmin ? `${API_BASE}/rooms/all-status/` : `${API_BASE}/rooms/`;
        const res = await fetchAPI(roomsEndpoint, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
            const rooms = await res.json();
            if (!Array.isArray(rooms)) throw new Error('Dữ liệu danh sách phòng họp không hợp lệ.');
            allRooms = rooms;
            overviewRoomsLoaded = true;
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
    if (!gridRooms) return;
    if (!Array.isArray(rooms) || rooms.length === 0) {
        gridRooms.innerHTML = emptyRoomsMessage();
        return;
    }
    gridRooms.innerHTML = buildRoomCards(rooms, isAdmin);
}

function renderDashboardRooms(rooms, isAdmin) {
    const gridOverview = document.getElementById('roomGridOverview');
    if (!gridOverview) return;
    if (!overviewMeetingsLoaded) {
        gridOverview.innerHTML = '<p class="text-muted room-grid-empty" role="status">Đang xác minh tình trạng phòng họp...</p>';
        return;
    }
    if (!Array.isArray(rooms) || rooms.length === 0) {
        gridOverview.innerHTML = emptyRoomsMessage();
        return;
    }
    const availableRooms = rooms.filter(room => getRoomCardState(room).available);
    gridOverview.innerHTML = availableRooms.length
        ? buildRoomCards(availableRooms, isAdmin)
        : '<p class="text-muted room-grid-empty">Hiện không có phòng họp nào đang trống.</p>';
}

function emptyRoomsMessage() {
    return '<p class="text-muted" style="padding: 16px;">Chưa có phòng họp nào trong hệ thống.</p>';
}

function getRoomCardState(room) {
    const operationalStatus = String(room.room_status || '').trim().toLowerCase();
    if (operationalStatus === 'maintenance') {
        return { available: false, statusClass: 'status-amber', statusText: 'Đang bảo trì' };
    }
    if (operationalStatus === 'locked') {
        return { available: false, statusClass: 'status-red', statusText: 'Tạm khóa' };
    }
    if (room.is_active === false) {
        return { available: false, statusClass: 'status-amber', statusText: 'Ngưng hoạt động' };
    }

    const roomStatus = String(room.status || '').trim().toUpperCase();
    const now = Date.now();
    const isMeetingInProgress = Array.isArray(allMeetings) && allMeetings.some(meeting => {
        if (String(meeting.room_id) !== String(room.id)) return false;
        const meetingStatus = String(meeting.status || '').trim().toUpperCase();
        if (['CANCELLED', 'CANCELED', 'CANCELLED_NO_SHOW', 'COMPLETED', 'COMPLETE', 'FINISHED', 'DONE'].includes(meetingStatus)) {
            return false;
        }
        const start = Date.parse(meeting.start_time);
        const end = Date.parse(meeting.end_time);
        return Number.isFinite(start) && Number.isFinite(end) && now >= start && now < end;
    });
    if (isMeetingInProgress || ['IN_USE', 'IN_PROGRESS', 'OCCUPIED'].includes(roomStatus)) {
        return { available: false, statusClass: 'status-red', statusText: 'Đang sử dụng' };
    }

    const isExplicitlyAvailable = roomStatus === 'AVAILABLE' || room.is_available === true;
    const hasExplicitUnavailableStatus = room.is_available === false
        || ['BOOKED', 'RESERVED', 'UNAVAILABLE', 'BUSY'].includes(roomStatus);
    const available = !hasExplicitUnavailableStatus
        && (isExplicitlyAvailable || (!roomStatus && room.is_available == null));
    return available
        ? { available: true, statusClass: 'status-green', statusText: 'Còn trống' }
        : { available: false, statusClass: 'status-red', statusText: 'Đã đặt' };
}

function buildRoomCards(rooms, isAdmin) {
    const htmlContent = rooms.map((room, index) => {
        const roomState = getRoomCardState(room);
        const roomImg = room.room_image || room.image_url || ROOM_THUMBNAILS[(Number(room.id) || index) % ROOM_THUMBNAILS.length];

        let amenitiesHTML = '';
        const amenities = parseRoomAmenities(room.amenities);
        amenitiesHTML = amenities.map(amenity =>
            `<span class="tag room-amenity-tag">${getAmenityIcon(amenity)}<span>${escapeHtml(amenity)}</span></span>`
        ).join('');

        const capacity = Number(room.capacity);
        const capacityLabel = Number.isFinite(capacity) && capacity > 0 ? capacity : 10;

        const menuActions = `
            <button class="room-action-item" type="button" onclick="openScheduleModal(${room.id})">Xem lịch</button>
            ${isAdmin ? `
                <button class="room-action-item" type="button" onclick="openRoomQrModal(${room.id})">Xem mã QR</button>
                <button class="room-action-item" type="button" onclick="openEditModal(${room.id})">Sửa thông tin</button>
                <button class="room-action-item room-action-item--danger" type="button" onclick="deleteRoom(${room.id})">Xóa phòng</button>
            ` : ''}
        `;

        return `
            <div class="room-card">
                <div class="card-image room-card-img-wrapper">
                    <img class="room-card-img" src="${escapeHtml(roomImg)}" alt="Không gian ${escapeHtml(room.name)}"
                        loading="lazy" decoding="async">
                    <span class="status-badge ${roomState.statusClass}">${roomState.statusText}</span>
                </div>
                <div class="card-body">
                    <h3>${escapeHtml(room.name)}</h3>
                    <p class="location">
                        <span class="room-meta-item">${getRoomMetaIcon('location')}<span>${escapeHtml(room.location || 'Tầng 1')}</span></span>
                        <span class="room-meta-divider" aria-hidden="true"></span>
                        <span class="room-meta-item">${getRoomMetaIcon('capacity')}<span>${capacityLabel} người</span></span>
                    </p>
                    <div class="amenities-tags">${amenitiesHTML}</div>
                    <div class="card-actions room-card-actions">
                        <button class="btn-book room-primary-action" type="button" ${roomState.available ? `onclick="openCreateMeeting({ roomId: ${room.id} })"` : 'disabled'}>
                            ${roomState.available ? 'Tạo cuộc họp' : roomState.statusText}
                        </button>
                        <details class="room-actions-menu">
                            <summary aria-label="Thao tác với phòng ${escapeHtml(room.name)}">
                                <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                                    <circle cx="5" cy="12" r="1.5" />
                                    <circle cx="12" cy="12" r="1.5" />
                                    <circle cx="19" cy="12" r="1.5" />
                                </svg>
                            </summary>
                            <div class="room-actions-popover">${menuActions}</div>
                        </details>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    return htmlContent;
}

function parseRoomAmenities(value) {
    if (Array.isArray(value)) return value.map(item => String(item || '').trim()).filter(Boolean);
    if (typeof value !== 'string' || !value.trim()) return [];
    try {
        const parsed = JSON.parse(value);
        if (Array.isArray(parsed)) return parsed.map(item => String(item || '').trim()).filter(Boolean);
    } catch {
        return value.split(',').map(item => item.trim()).filter(Boolean);
    }
    return value.split(',').map(item => item.trim()).filter(Boolean);
}

function getRoomMetaIcon(type) {
    const paths = type === 'location'
        ? '<path d="M12 2a8 8 0 0 0-8 8c0 5.25 8 12 8 12s8-6.75 8-12a8 8 0 0 0-8-8z"/><circle cx="12" cy="10" r="3"/>'
        : '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>';
    return `<svg class="room-meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${paths}</svg>`;
}

function updateStats(rooms) {
    updateOverviewKPICards(rooms, overviewMeetingsLoaded ? allMeetings : null);
}

function updateOverviewKPICards(rooms, meetings) {
    const setText = (id, value) => {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    };

    if (!Array.isArray(rooms)) {
        ['statTotalRooms', 'statTotalRoomsSub', 'statInUseRooms', 'statOccupancyRate',
            'statAvailableRooms', 'statAvailableRoomsSub', 'statWeeklyBookings',
            'statWeeklyBookingsSub'].forEach(id => setText(id, '-'));
        setText('summaryAvailable', '-');
        setText('summaryInUse', '-');
        return;
    }

    const totalRooms = rooms.length;
    const totalCapacity = rooms.reduce((total, room) => {
        const capacity = Number(room.capacity);
        return total + (Number.isFinite(capacity) && capacity > 0 ? capacity : 0);
    }, 0);
    setText('statTotalRooms', String(totalRooms));
    setText('statTotalRoomsSub', `Tổng sức chứa ${totalCapacity} người`);

    if (!Array.isArray(meetings)) {
        ['statInUseRooms', 'statOccupancyRate', 'statAvailableRooms',
            'statAvailableRoomsSub', 'statWeeklyBookings', 'statWeeklyBookingsSub']
            .forEach(id => setText(id, '-'));
        setText('summaryAvailable', '-');
        setText('summaryInUse', '-');
        return;
    }

    const now = Date.now();
    const occupiedRoomIds = new Set();
    const roomIds = new Set(rooms.map(room => String(room.id)));
    const isCancelled = meeting =>
        ['CANCELLED', 'CANCELED', 'CANCELLED_NO_SHOW'].includes(
            String(meeting.status || '').trim().toUpperCase(),
        );
    for (const meeting of meetings) {
        if (isCancelled(meeting)) continue;
        const start = Date.parse(meeting.start_time);
        const end = Date.parse(meeting.end_time);
        if (Number.isFinite(start) && Number.isFinite(end)
            && now >= start && now < end && meeting.room_id != null
            && roomIds.has(String(meeting.room_id))) {
            occupiedRoomIds.add(String(meeting.room_id));
        }
    }

    const inUseCount = occupiedRoomIds.size;
    const availableCount = totalRooms - inUseCount;
    const occupancyRate = totalRooms > 0 ? Math.round((inUseCount / totalRooms) * 100) : 0;
    setText('statInUseRooms', String(inUseCount));
    setText('statOccupancyRate', `${occupancyRate}% công suất`);
    setText('statAvailableRooms', String(availableCount));
    setText('statAvailableRoomsSub', `trong ${totalRooms} phòng`);
    setText('summaryAvailable', String(availableCount));
    setText('summaryInUse', String(inUseCount));

    const currentDate = new Date();
    const weekStart = new Date(
        currentDate.getFullYear(),
        currentDate.getMonth(),
        currentDate.getDate() - ((currentDate.getDay() + 6) % 7),
    );
    const nextWeekStart = new Date(weekStart);
    nextWeekStart.setDate(nextWeekStart.getDate() + 7);
    const weeklyMeetings = meetings.filter(meeting => {
        if (isCancelled(meeting)) return false;
        const start = Date.parse(meeting.start_time);
        return Number.isFinite(start) && start >= weekStart.getTime() && start < nextWeekStart.getTime();
    });
    const completedCount = weeklyMeetings.filter(meeting =>
        ['COMPLETED', 'COMPLETE', 'FINISHED', 'DONE'].includes(
            String(meeting.status || '').trim().toUpperCase(),
        ),
    ).length;

    setText('statWeeklyBookings', String(weeklyMeetings.length));
    setText(
        'statWeeklyBookingsSub',
        weeklyMeetings.length
            ? `${completedCount} cuộc họp đã hoàn thành`
            : 'Không có cuộc họp tuần này',
    );
}

function getAmenityIcon(name) {
    const lower = String(name || '').toLocaleLowerCase();
    let paths = '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4"/>';
    if (lower.includes('wifi') || lower.includes('internet')) {
        paths = '<path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><path d="M12 20h.01"/>';
    } else if (lower.includes('video') || lower.includes('camera')) {
        paths = '<rect x="3" y="6" width="13" height="12" rx="2"/><path d="m16 10 5-3v10l-5-3z"/>';
    } else if (lower.includes('chiếu') || lower.includes('projector')) {
        paths = '<rect x="3" y="5" width="18" height="12" rx="2"/><path d="M8 21h8M12 17v4"/><path d="m9 9 6 2-6 2z"/>';
    } else if (lower.includes('mic') || lower.includes('loa')) {
        paths = '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8"/>';
    } else if (lower.includes('bảng') || lower.includes('whiteboard')) {
        paths = '<rect x="3" y="3" width="18" height="15" rx="1"/><path d="M7 22l3-4m7 4-3-4M7 8h10"/>';
    }
    return `<svg class="room-amenity-icon text-indigo-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${paths}</svg>`;
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
        const res = await fetchAPI(`${API_BASE}/meetings/${meetingId}/cancel`, {
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
    if (!getAuthToken()) {
        redirectToLogin();
        return;
    }
    try {
        const res = await fetchAPI(`${API_BASE}/meetings/mine`, {
            headers: { 'Authorization': 'Bearer ' + getAuthToken() }
        });
        if (handleUnauthorizedResponse(res)) return;
        if (!res.ok) throw new Error('Không thể tải danh sách lịch họp.');
        const meetings = await res.json();
        if (!Array.isArray(meetings)) throw new Error('Dữ liệu danh sách lịch họp không hợp lệ.');
        myBookings = meetings;
        await fetchMeetings();
        renderMyBookings();
        if (userNotifications.length) renderNotifications(userNotifications);
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
    if (isOnlineMeeting(meeting)) return 'Cuộc họp online';
    return meeting.room_details?.name || meeting.room_name
        || allRooms.find(room => room.id === meeting.room_id)?.name
        || (meeting.room_id ? `Phòng ${meeting.room_id}` : 'Phòng chưa xác định');
}

function isOnlineMeeting(meeting) {
    return meeting.is_online === true
        || String(meeting.meeting_type || '').trim().toLowerCase() === 'online';
}

function bookingSafeLink(value) {
    try {
        const url = new URL(String(value || ''));
        return ['http:', 'https:'].includes(url.protocol) ? url.href : '';
    } catch (error) {
        return '';
    }
}

function bookingList(value) {
    if (Array.isArray(value)) return value.filter(item => item != null && String(item).trim());
    if (typeof value !== 'string' || !value.trim()) return [];
    try {
        const parsed = JSON.parse(value);
        if (Array.isArray(parsed)) return parsed.filter(item => item != null && String(item).trim());
    } catch (error) {
        return value.split(',').map(item => item.trim()).filter(Boolean);
    }
    return [];
}

function bookingEquipmentLabel(equipment) {
    if (typeof equipment === 'string') return equipment;
    if (!equipment || typeof equipment !== 'object') return '';
    const name = equipment.equipment_name || equipment.name;
    if (!name) return '';
    const quantity = Number(equipment.quantity);
    return Number.isFinite(quantity) && quantity > 1 ? `${name} × ${quantity}` : String(name);
}

function bookingMeetingDetailsMarkup(meeting) {
    if (isOnlineMeeting(meeting)) {
        const link = bookingSafeLink(meeting.meeting_link || meeting.online_link);
        if (!link) return '<span>Link cuộc họp chưa được cung cấp.</span>';
        return `<div class="booking-online-link-row">
            <a class="booking-meeting-link" href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer">${escapeHtml(link)}</a>
            <button class="booking-copy-link-button" type="button" data-meeting-link="${escapeHtml(link)}"
                onclick="copyMeetingLink(this)" aria-label="Sao chép link cuộc họp">Sao chép link</button>
        </div>`;
    }

    const room = meeting.room_details
        || allRooms.find(item => Number(item.id) === Number(meeting.room_id))
        || null;
    const roomName = room?.name || meeting.room_name
        || (meeting.room_id ? `Phòng ${meeting.room_id}` : 'Phòng chưa xác định');
    const capacity = room?.capacity ?? meeting.room_capacity;
    const location = room?.location || meeting.room_location || '';
    const locationParts = [roomName];
    if (capacity != null && capacity !== '') locationParts.push(`${capacity} người`);
    if (location) locationParts.push(location);

    const amenities = bookingList(room?.amenities || meeting.room_amenities);
    const roomEquipment = bookingList(room?.equipment || room?.default_equipments)
        .map(bookingEquipmentLabel).filter(Boolean);
    const meetingEquipment = bookingList(meeting.equipments)
        .map(bookingEquipmentLabel).filter(Boolean);
    const allEquipment = [...new Set([...amenities, ...roomEquipment, ...meetingEquipment])];
    const equipmentMarkup = allEquipment.length
        ? `<ul class="booking-equipment-list">${allEquipment.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`
        : '<p class="booking-room-empty">Chưa có tiện nghi hoặc thiết bị được ghi nhận.</p>';
    const description = room?.description
        ? `<p class="booking-room-description">${escapeHtml(room.description)}</p>`
        : '';

    return `<span class="booking-room-location">${escapeHtml(locationParts.join(' · '))}</span>
        <details class="booking-room-details">
            <summary>Xem chi tiết phòng</summary>
            <div class="booking-room-details-content">
                ${description}
                <span class="booking-room-details-heading">Tiện nghi và thiết bị</span>
                ${equipmentMarkup}
            </div>
        </details>`;
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
        const summary = isOnlineMeeting(meeting)
            ? `${bookingRoomName(meeting)} · ${date}`
            : date;
        const time = start && end ? `${bookingTime(start)} – ${bookingTime(end)}` : 'Chưa có thời gian';
        const participants = (meeting.participants || []).filter(person => person.user_id !== meeting.organizer_id);
        const attendeeMarkup = participants.length ? participants.map(person => {
            const response = person.response_status === 'declined' ? 'rejected'
                : ['accepted', 'rejected'].includes(person.response_status) ? person.response_status : 'pending';
            const label = response === 'accepted' ? 'Đã đồng ý' : response === 'rejected' ? 'Đã từ chối' : 'Chưa phản hồi';
            return `<div class="booking-guest ${response === 'accepted' ? '' : 'pending'}"><span>${escapeHtml(person.name || person.email || 'Người tham dự')}</span><span class="booking-guest-status ${response}">${response === 'accepted' ? '✓ ' : ''}${label}</span></div>`;
        }).join('') : '<div class="booking-guest pending">Chưa có người được mời.</div>';
        const cancel = `<button class="booking-cancel-button" type="button" onclick="cancelBooking(${meeting.id})">Hủy lịch</button>`;
        const qrActions = meetingPresenterQrAction(meeting);
        const meetingLink = isOnlineMeeting(meeting)
            ? bookingSafeLink(meeting.meeting_link || meeting.online_link)
            : '';
        const joinLink = meetingLink
            ? `<a class="booking-rsvp-button" href="${escapeHtml(meetingLink)}" target="_blank" rel="noopener noreferrer">Tham gia</a>`
            : '';
        const extendActions = String(meeting.status || '').trim().toUpperCase() === 'IN_PROGRESS'
            ? `<button class="booking-extend-button" type="button" onclick="extendMeeting(${Number(meeting.id)}, 15, this)">+ Gia hạn 15p</button>
                <button class="booking-extend-button" type="button" onclick="extendMeeting(${Number(meeting.id)}, 30, this)">+ Gia hạn 30p</button>`
            : '';
        return `<article class="booking-list-card"><div class="booking-list-row">
            <div class="booking-list-main">
                <strong>${escapeHtml(meeting.title || 'Cuộc họp')}</strong>
                <span>${escapeHtml(summary)}</span>
                ${bookingMeetingDetailsMarkup(meeting)}
            </div>
            <div class="booking-list-time">${escapeHtml(time)}</div>
            <div class="booking-list-actions"><button class="booking-guest-toggle" type="button" aria-expanded="false" onclick="toggleBookingGuests(${meeting.id}, this)">Người được mời (${participants.length})</button>${joinLink}${qrActions}${extendActions}${cancel}</div>
        </div><div id="bookingGuests${meeting.id}" class="booking-guest-list" hidden>${attendeeMarkup}</div></article>`;
    }).join('');
}

async function copyMeetingLink(button) {
    const link = bookingSafeLink(button?.dataset.meetingLink);
    if (!link) {
        showAppToast('Link cuộc họp không hợp lệ.', 'error');
        return;
    }
    try {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(link);
        } else {
            const input = document.createElement('textarea');
            input.value = link;
            input.setAttribute('readonly', '');
            input.style.position = 'fixed';
            input.style.opacity = '0';
            document.body.appendChild(input);
            let copied = false;
            try {
                input.select();
                copied = document.execCommand('copy');
            } finally {
                input.remove();
            }
            if (!copied) throw new Error('Trình duyệt không thể sao chép link.');
        }
        showAppToast('Đã sao chép link cuộc họp.');
    } catch (error) {
        showAppToast(error.message || 'Không thể sao chép link cuộc họp.', 'error');
    }
}

async function extendMeeting(meetingId, extendMinutes, button) {
    if (![15, 30].includes(extendMinutes) || button?.disabled) return;
    if (button) {
        button.disabled = true;
        button.textContent = 'Đang gia hạn…';
    }

    try {
        const response = await fetchAPI(`${API_BASE}/meetings/${meetingId}/extend`, {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${getAuthToken()}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ extend_minutes: extendMinutes }),
        });
        const result = await response.json().catch(() => ({}));
        if (handleUnauthorizedResponse(response)) return;
        if (response.status === 409 && result.detail?.available_rooms) {
            const roomNames = result.detail.available_rooms
                .map(room => room.name)
                .filter(Boolean);
            const suggestions = roomNames.length
                ? ` Phòng thay thế đang trống: ${roomNames.join(', ')}.`
                : ' Hiện không tìm thấy phòng thay thế phù hợp.';
            showAppToast(`${result.detail.message || 'Không thể gia hạn.'}${suggestions}`, 'error');
            return;
        }
        if (!response.ok) {
            const message = typeof result.detail === 'string'
                ? result.detail
                : 'Không thể gia hạn cuộc họp. Vui lòng thử lại.';
            throw new Error(message);
        }

        showAppToast(`Đã gia hạn cuộc họp thêm ${extendMinutes} phút.`);
        await fetchMyBookings();
    } catch (error) {
        console.error('Không thể gia hạn cuộc họp:', error);
        showAppToast(error.message || 'Không thể gia hạn cuộc họp. Vui lòng thử lại.', 'error');
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = `+ Gia hạn ${extendMinutes}p`;
        }
    }
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
        const response = getMeetingRsvpStatus(meeting);
        const statusLabel = response === 'accepted' ? 'Đã đồng ý'
            : response === 'rejected' ? 'Đã từ chối' : 'Chưa phản hồi';
        const acceptButton = `<button class="btn-rsvp btn-accept" type="button" data-meeting-id="${meeting.id}" data-rsvp-meeting="${meeting.id}" data-rsvp-status="accepted">${response === 'rejected' ? 'Đổi sang chấp nhận' : 'Chấp nhận'}</button>`;
        const rejectButton = `<button class="btn-rsvp btn-reject" type="button" data-meeting-id="${meeting.id}" data-rsvp-meeting="${meeting.id}" data-rsvp-status="rejected">${response === 'accepted' ? 'Đổi sang từ chối' : 'Từ chối'}</button>`;
        const rsvpActions = response === 'accepted' ? rejectButton
            : response === 'rejected' ? acceptButton
                : `${acceptButton}${rejectButton}`;
        const adminCancel = String(localStorage.getItem('role') || '').trim().toLowerCase() === 'admin'
            ? `<button class="booking-cancel-button" type="button" onclick="cancelBooking(${meeting.id})">Hủy lịch</button>`
            : '';
        const qrActions = meetingQrActions(meeting, response === 'accepted');
        return `<article class="booking-list-card"><div class="booking-list-row invited-booking-row">
            <div class="booking-list-main"><strong>${escapeHtml(meeting.title || 'Cuộc họp')}</strong><span>${escapeHtml(bookingRoomName(meeting))} · ${escapeHtml(date)}</span><span>Chủ trì: ${escapeHtml(meeting.organizer_name || 'Người tổ chức')}</span></div>
            <div class="booking-list-time">${escapeHtml(time)}<br><span class="badge-status ${escapeHtml(response)}">${escapeHtml(statusLabel)}</span></div>
            <div class="booking-list-actions rsvp-actions">
                ${rsvpActions}${qrActions}${adminCancel}
            </div>
        </div></article>`;
    }).join('');
}

function getMeetingRsvpStatus(meeting) {
    const response = notificationRsvpOverrides.get(Number(meeting.id))
        || meeting.my_response_status
        || meeting.response_status
        || meeting.participant_response_status
        || meeting.rsvp_status
        || meeting.status;
    const normalized = String(response || '').trim().toLowerCase();
    if (normalized === 'declined' || normalized === 'decline') return 'rejected';
    return ['pending', 'accepted', 'rejected'].includes(normalized) ? normalized : 'pending';
}

function initializeRsvpActions() {
    const container = document.getElementById('invitedBookingsList');
    if (!container || container.dataset.rsvpBound === 'true') return;
    container.dataset.rsvpBound = 'true';
    container.addEventListener('click', event => {
        const button = event.target.closest('button[data-rsvp-meeting][data-rsvp-status]');
        if (!button || button.disabled) return;
        respondToMeeting(Number(button.dataset.rsvpMeeting), button.dataset.rsvpStatus);
    });
}

async function handleAdminCreateUser(event) {
    event.preventDefault();
    if (!isCurrentUserAdmin()) {
        showAppToast('Chỉ quản trị viên mới được tạo tài khoản.', 'error');
        return;
    }

    const form = event.currentTarget;
    if (!(form instanceof HTMLFormElement) || !form.reportValidity()) return;

    const formData = new FormData(form);
    const payload = {
        full_name: String(formData.get('full_name') || '').trim(),
        email: String(formData.get('email') || '').trim(),
        role: String(formData.get('role') || 'employee'),
    };
    const username = String(formData.get('username') || '').trim();
    if (username) payload.username = username;
    const departmentId = String(formData.get('department_id') || '').trim();
    if (departmentId) payload.department_id = Number(departmentId);
    const projectGroupIds = formData.getAll('project_group_ids')
        .map(value => String(value).trim())
        .filter(value => value !== '')
        .map(Number);
    if (projectGroupIds.length) payload.project_group_ids = projectGroupIds;

    const submitButton = document.getElementById('adminCreateUserSubmit');
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = 'Đang tạo tài khoản...';
    }

    try {
        const response = await fetchAPI(`${API_BASE}/v1/users/`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
        });

        let result = {};
        try {
            result = await response.json();
        } catch {
            result = {};
        }

        if (!response.ok) {
            const detail = result.detail;
            const message = Array.isArray(detail)
                ? detail.map(error => error.msg || 'Dữ liệu không hợp lệ').join(' ')
                : (detail || result.message || `Không thể tạo tài khoản (HTTP ${response.status}).`);
            showAppToast(String(message), 'error');
            return;
        }

        form.reset();
        const accountName = result.full_name || payload.full_name;
        if (result.email_sent) {
            showAppToast(`Đã tạo tài khoản ${accountName} và gửi email hướng dẫn kích hoạt.`);
        } else {
            showAppToast(
                `Đã tạo tài khoản ${accountName} ở trạng thái chờ kích hoạt nhưng không gửi được email. Kiểm tra Gmail/SMTP rồi dùng nút Gửi lại Mail.`,
                'error',
            );
        }
        showUserManagementSection('list');
        try {
            await window.RoomSyncUserList?.refreshUserListTable();
        } catch (error) {
            console.error('Tài khoản đã tạo nhưng không tải lại được danh sách:', error);
            showAppToast('Tài khoản đã tạo; không tải lại được danh sách người dùng.', 'error');
        }
    } catch (error) {
        console.error('Không thể tạo tài khoản người dùng', error);
        showAppToast('Không thể kết nối máy chủ để tạo tài khoản. Vui lòng thử lại.', 'error');
    } finally {
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.textContent = 'Tạo tài khoản';
        }
    }
}

function showAppToast(message, type = 'success') {
    const container = document.getElementById('appToastContainer');
    if (!container) {
        alert(message);
        return;
    }
    const toast = document.createElement('div');
    toast.className = `app-toast ${type === 'error' ? 'error' : 'success'}`;
    toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
    toast.textContent = message;
    container.appendChild(toast);
    window.setTimeout(() => toast.remove(), 4000);
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
    const response = await fetchAPI(`${API_BASE}/rooms/${roomId}/qr-code${meetingQuery}`, {
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

async function openQuickQrScanner() {
    const modal = document.getElementById('qrScannerModal');
    const feedback = document.getElementById('quickQrFeedback');
    if (!modal) return;
    if (quickQrCloseTimer) clearTimeout(quickQrCloseTimer);
    if (quickQrResumeTimer) clearTimeout(quickQrResumeTimer);
    if (quickQrScanner) await closeQuickQrScanner();
    if (feedback) feedback.textContent = '';
    modal.style.display = 'flex';
    if (typeof Html5Qrcode === 'undefined') {
        if (feedback) feedback.textContent = 'Không tải được trình quét QR. Vui lòng tải lại trang.';
        return;
    }

    try {
        quickQrScanner = new Html5Qrcode('quickQrReader');
        await quickQrScanner.start(
            { facingMode: 'environment' },
            { fps: 10, qrbox: { width: 240, height: 240 } },
            handleSmartQrResult,
            () => {}
        );
    } catch (error) {
        console.warn('Không thể khởi động camera quét QR nhanh:', error);
        if (feedback) {
            feedback.textContent = 'Không thể mở camera. Hãy kiểm tra quyền truy cập camera của trình duyệt.';
        }
    }
}

async function handleSmartQrResult(decodedText) {
    if (!quickQrScanner || quickQrSubmissionInProgress) return;
    quickQrSubmissionInProgress = true;
    const scanner = quickQrScanner;
    const feedback = document.getElementById('quickQrFeedback');
    if (feedback) feedback.textContent = '';

    try {
        scanner.pause();
        const response = await fetchAPI(`${API_BASE}/v1/meetings/smart-qr-action`, {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${getAuthToken()}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ qr_payload: decodedText }),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Không thể xử lý mã QR.');

        const actionLabel = result.action === 'CHECK_OUT' ? 'CHECK-OUT' : 'CHECK-IN';
        await stopQuickQrScanner();
        showQrToast(`✅ [${actionLabel} THÀNH CÔNG] - ${result.message || 'Đã cập nhật cuộc họp.'}`);
        await fetchMyBookings();
        quickQrCloseTimer = setTimeout(() => {
            closeQuickQrScanner();
        }, 1500);
    } catch (error) {
        if (feedback) feedback.textContent = `❌ ${error.message || 'Không thể xử lý mã QR.'}`;
        quickQrSubmissionInProgress = false;
        if (quickQrResumeTimer) clearTimeout(quickQrResumeTimer);
        quickQrResumeTimer = setTimeout(() => {
            if (quickQrScanner !== scanner) return;
            try {
                scanner.resume();
            } catch (resumeError) {
                console.warn('Không thể tiếp tục trình quét QR:', resumeError);
                if (feedback) feedback.textContent = 'Không thể tiếp tục camera. Hãy đóng và mở lại trình quét.';
                return;
            }
            if (feedback) feedback.textContent = '';
        }, 2500);
    }
}

async function stopQuickQrScanner() {
    if (!quickQrScanner) return;
    const scanner = quickQrScanner;
    quickQrScanner = null;
    try {
        if (scanner.isScanning) await scanner.stop();
        scanner.clear();
    } catch (error) {
        console.warn('Không thể dừng trình quét QR nhanh:', error);
    }
}

async function closeQuickQrScanner() {
    if (quickQrResumeTimer) clearTimeout(quickQrResumeTimer);
    if (quickQrCloseTimer) clearTimeout(quickQrCloseTimer);
    quickQrResumeTimer = null;
    quickQrCloseTimer = null;
    quickQrSubmissionInProgress = false;
    await stopQuickQrScanner();
    const modal = document.getElementById('qrScannerModal');
    if (modal) modal.style.display = 'none';
}

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
        const response = await fetchAPI(
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

async function respondToMeeting(meetingId, responseStatus, notificationId = null) {
    const buttons = document.querySelectorAll(`[data-rsvp-meeting="${Number(meetingId)}"]`);
    buttons.forEach(button => { button.disabled = true; });
    try {
const token = getAuthToken();
    if (!token) {
        redirectToLogin();
        return;
    }
    const res = await fetchAPI(`${API_BASE}/meetings/${meetingId}/respond`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ status: responseStatus }),
    });
    if (handleUnauthorizedResponse(res)) return;
    if (!res.ok) throw new Error(await apiErrorMessage(res, 'Không thể cập nhật phản hồi.'));

    const meeting = myBookings.find(item => Number(item.id) === Number(meetingId));
    notificationRsvpOverrides.set(Number(meetingId), responseStatus);
    if (meeting) {
        meeting.my_response_status = responseStatus;
        renderInvitedBookings(myBookings.filter(item => !item.is_organizer));
    }
    if (userNotifications.length) renderNotifications(userNotifications);
    if (notificationId) await markNotificationAsRead(notificationId);
    showAppToast(responseStatus === 'accepted'
        ? 'Bạn đã chấp nhận tham gia cuộc họp.'
        : 'Bạn đã từ chối lời mời họp.');
    } catch (error) {
        buttons.forEach(button => { button.disabled = false; });
        showAppToast(error.message || 'Không thể cập nhật phản hồi.', 'error');
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
    const query = searchInput ? searchInput.value.trim().toLocaleLowerCase() : '';
    const cap = capSelect ? capSelect.value : 'all';
    const activeFilter = document.querySelector('.filter-chips .chip.active');
    const amenity = activeFilter && activeFilter.textContent.trim() !== 'Tất cả'
        ? activeFilter.textContent.trim()
        : '';

    const filtered = allRooms.filter(room => {
        const matchesSearch = `${room.name || ''} ${room.location || ''}`.toLocaleLowerCase().includes(query);
        const capacity = Number.parseInt(room.capacity, 10) || 10;
        const matchesCapacity = cap === 'all'
            || (cap === 'small' && capacity <= 5)
            || (cap === 'medium' && capacity > 5 && capacity <= 12)
            || (cap === 'large' && capacity > 12);
        const matchesAmenity = !amenity || parseRoomAmenities(room.amenities)
            .some(item => item.toLocaleLowerCase().includes(amenity.toLocaleLowerCase()));
        return matchesSearch && matchesCapacity && matchesAmenity;
    });

    renderRooms(filtered, localStorage.getItem('role') === 'admin');
}

function setFilter(amenity, btn) {
    document.querySelectorAll('.filter-chips .chip').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    applyFilters();
}

/* ==========================================================================
   ADMIN ACTIONS (ADD / EDIT / DELETE ROOMS)
   ========================================================================== */
function openRoomModal() {
    const modalTitle = document.getElementById('modalTitle');
    if (modalTitle) modalTitle.innerText = 'Thêm Phòng Họp Mới';
    document.getElementById('editRoomId').value = '';
    document.getElementById('roomForm').reset();
    previewRoomImage('');
    document.getElementById('roomModal').style.display = 'flex';
    loadRoomEquipmentOptions();
}

function openEditModal(roomId) {
    const room = allRooms.find(r => r.id === roomId);
    if (!room) return;

    document.getElementById('modalTitle').innerText = 'Sửa Thông Tin Phòng Họp';
    document.getElementById('editRoomId').value = room.id;
    document.getElementById('roomName').value = room.name;
    document.getElementById('roomLocation').value = room.location || '';
    document.getElementById('roomCapacity').value = room.capacity || '';
    document.getElementById('roomStatus').value = room.room_status || (room.is_active === false ? 'maintenance' : 'active');
    document.getElementById('roomLayoutType').value = room.layout_type || '';
    document.getElementById('roomImageUrl').value = room.room_image || room.image_url || '';
    previewRoomImage(document.getElementById('roomImageUrl').value);
    document.getElementById('roomModal').style.display = 'flex';
    loadRoomEquipmentOptions(room.equipment_ids || []);
}

async function loadRoomEquipmentOptions(selectedIds = []) {
    const container = document.getElementById('roomEquipmentOptions');
    if (!container) return;
    roomEquipmentLoaded = false;
    container.innerHTML = '<span class="room-equipment-message">Đang tải danh mục thiết bị...</span>';
    try {
        const response = await fetchAPI(`${API_BASE}/equipments/`, {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });
        if (!response.ok) throw new Error(`Không thể tải danh mục thiết bị (HTTP ${response.status}).`);
        const equipment = await response.json();
        if (!Array.isArray(equipment)) throw new Error('Dữ liệu danh mục thiết bị không hợp lệ.');
        roomEquipmentCatalog = equipment.filter(item => item.is_active !== false);
        const selected = new Set(selectedIds.map(Number));
        container.innerHTML = roomEquipmentCatalog.length
            ? roomEquipmentCatalog.map(item => `
                <label class="room-equipment-option">
                    <input type="checkbox" name="roomEquipmentIds" value="${Number(item.id)}"
                        ${selected.has(Number(item.id)) ? 'checked' : ''}>
                    <span>${escapeHtml(item.name)}</span>
                </label>
            `).join('')
            : '<span class="room-equipment-message">Chưa có thiết bị đang hoạt động.</span>';
        roomEquipmentLoaded = true;
    } catch (error) {
        console.error('Lỗi tải danh mục thiết bị cho phòng:', error);
        container.innerHTML = '<span class="room-equipment-message room-equipment-error" role="alert">Không thể tải danh mục thiết bị. Vui lòng đóng và mở lại biểu mẫu.</span>';
    }
}

function previewRoomImage(value) {
    const preview = document.getElementById('roomImagePreview');
    if (!preview) return;
    try {
        const imageUrl = new URL(String(value || '').trim());
        if (!['http:', 'https:'].includes(imageUrl.protocol)) throw new Error('Unsupported image URL scheme.');
        preview.src = imageUrl.href;
        preview.hidden = false;
    } catch {
        preview.removeAttribute('src');
        preview.hidden = true;
    }
}

function closeRoomModal() {
    document.getElementById('roomModal').style.display = 'none';
}

async function handleFormSubmit(e) {
    e.preventDefault();
    const token = getAuthToken();
    const editId = document.getElementById('editRoomId').value;

    if (!roomEquipmentLoaded) {
        alert('Danh mục thiết bị chưa sẵn sàng. Vui lòng thử lại.');
        return;
    }

    const payload = {
        name: document.getElementById('roomName').value,
        location: document.getElementById('roomLocation').value,
        capacity: parseInt(document.getElementById('roomCapacity').value) || 0,
        room_status: document.getElementById('roomStatus').value,
        equipment_ids: [...document.querySelectorAll('input[name="roomEquipmentIds"]:checked')]
            .map(input => Number(input.value)),
        room_image: document.getElementById('roomImageUrl').value.trim() || null,
        layout_type: document.getElementById('roomLayoutType').value || null
    };

    const method = editId ? 'PUT' : 'POST';
    const url = editId ? `${API_BASE}/rooms/${editId}/` : `${API_BASE}/rooms/`;

    try {
        const res = await fetchAPI(url, {
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
        const res = await fetchAPI(`${API_BASE}/rooms/${roomId}/`, {
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
        const res = await fetchAPI(`${API_BASE}/equipments/availability?${params.toString()}`, {
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
        const res = await fetchAPI(`${API_BASE}/equipments/?include_inactive=true`, {
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
        await fetchAPI(`${API_BASE}/equipments/${equipmentId}`, {
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
        const res = await fetchAPI(url, {
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
        await fetchAPI(`${API_BASE}/equipments/${id}`, {
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
const reportCharts = new Map();
const REPORT_CHART_COLORS = [
    '#4F46E5', '#10B981', '#F59E0B', '#8B5CF6',
    '#06B6D4', '#EC4899', '#3B82F6', '#64748B',
];

function setReportButtonLoading(button, isLoading) {
    if (!button) return;
    button.disabled = isLoading;
    button.classList.toggle('is-loading', isLoading);
    const label = button.querySelector('.report-submit-label');
    if (label) label.textContent = isLoading ? 'Đang tải...' : 'Cập nhật';
}

function updateReportChart(elementId, options) {
    const element = document.getElementById(elementId);
    if (!element) return;
    if (!window.ApexCharts) throw new Error('Không tải được thư viện biểu đồ ApexCharts.');

    const existingChart = reportCharts.get(elementId);
    if (existingChart) {
        existingChart.destroy();
        reportCharts.delete(elementId);
    }

    const chart = new window.ApexCharts(element, options);
    reportCharts.set(elementId, chart);
    chart.render();
}

function requestReportPath(path, params) {
    const token = getAuthToken();
    return fetchAPI(`${API_BASE}${path}?${params.toString()}`, {
        headers: {
            Accept: 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
    });
}

async function loadRoomsForReportFilter() {
    try {
        const response = await fetchAPI(`${API_BASE}/rooms/`);
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

async function loadUsageReportData(event) {
    event?.preventDefault();
    const startDateVal = document.getElementById('reportStartDate')?.value;
    const endDateVal = document.getElementById('reportEndDate')?.value;
    const roomIdVal = document.getElementById('reportRoomIdSelect')?.value;
    const button = document.getElementById('btnRunUsageReport');
    const message = document.getElementById('roomUsageReportMessage');
    if (message) {
        message.textContent = '';
        message.hidden = true;
    }
    if (startDateVal && endDateVal && startDateVal > endDateVal) {
        if (message) {
            message.textContent = 'Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.';
            message.hidden = false;
        }
        return;
    }
    const params = new URLSearchParams();
    if (startDateVal) params.set('start_date', `${startDateVal}T00:00:00`);
    if (endDateVal) params.set('end_date', `${endDateVal}T23:59:59.999999`);
    if (roomIdVal) params.set('room_id', roomIdVal);
    setReportButtonLoading(button, true);

    try {
        let response = await requestReportPath('/v1/reports/usage', params);
        if (response.status === 404) {
            response = await requestReportPath('/v1/reports/room-usage', params);
        }
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Không thể tải dữ liệu báo cáo.');
        }
        const data = await response.json();
        renderReportDataToDashboard(data);
    } catch (error) {
        console.error('Lỗi gọi API báo cáo:', error);
        if (message) {
            message.textContent = error instanceof Error ? error.message : 'Đã xảy ra lỗi khi tải báo cáo.';
            message.hidden = false;
        }
    } finally {
        setReportButtonLoading(button, false);
    }
}

function fetchRoomUsageReport(event) {
    return loadUsageReportData(event);
}

function renderReportDataToDashboard(data) {
    const summary = data?.summary || {};
    const setValue = (id, value) => {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    };
    setValue('kpiTotalRooms', String(summary.total_rooms ?? 0));
    setValue('kpiTotalMeetings', String(summary.total_meetings ?? 0));
    setValue('kpiTotalHours', `${Number(summary.total_hours ?? 0).toFixed(1)} h`);
    setValue('kpiOccupancyRate', `${Number(summary.average_occupancy_rate ?? 0).toFixed(1)}%`);

    const roomDetails = Array.isArray(data?.room_details) ? data.room_details : [];
    const roomUsageByName = new Map();
    roomDetails.forEach(room => {
        const name = String(room.room_name ?? '').replace(/^(?:DEMO|SEED)\s*-\s*/i, '').trim() || 'Phòng họp';
        const key = name.toLocaleLowerCase();
        const aggregate = roomUsageByName.get(key);
        if (aggregate) {
            aggregate.totalHours += Math.max(0, Number(room.total_hours ?? 0));
            return;
        }
        roomUsageByName.set(key, {
            name,
            totalHours: Math.max(0, Number(room.total_hours ?? 0)),
        });
    });
    const groupedRoomUsage = Array.from(roomUsageByName.values());
    updateReportChart('chartUsageBar', {
        chart: { type: 'bar', height: 288, toolbar: { show: false } },
        series: [{
            name: 'Tổng số giờ họp',
            data: roomDetails.map(room => Number(room.total_hours ?? 0)),
        }],
        colors: ['#4F46E5'],
        plotOptions: { bar: { columnWidth: '52%', borderRadius: 6 } },
        dataLabels: { enabled: false },
        xaxis: {
            categories: roomDetails.map(room => String(room.room_name ?? '').replace(/^(?:DEMO|SEED)\s*-\s*/i, '')),
            labels: {
                rotate: -45,
                rotateAlways: true,
                hideOverlappingLabels: true,
                trim: true,
                maxHeight: 60,
                style: { fontSize: '11px', colors: '#64748B' },
                formatter: value => {
                    const name = String(value ?? '');
                    return name.length > 20 ? `${name.slice(0, 17)}...` : name;
                },
            },
            tooltip: { enabled: false },
        },
        yaxis: {
            min: 0,
            title: {
                text: 'Giờ họp (giờ)',
                rotate: -90,
                offsetX: -5,
                style: { fontSize: '12px', fontWeight: '600', color: '#475569' },
            },
            labels: { minWidth: 35, style: { colors: '#64748B' } },
        },
        noData: { text: 'Không có dữ liệu' },
        grid: { borderColor: '#e2e8f0', padding: { left: 25, right: 15 } },
    });
    updateReportChart('chartUsageDonut', {
        chart: { type: 'donut', height: 288 },
        series: groupedRoomUsage.map(room => room.totalHours),
        labels: groupedRoomUsage.map(room => room.name),
        colors: REPORT_CHART_COLORS,
        legend: {
            show: true,
            position: 'bottom',
            horizontalAlign: 'center',
            fontSize: '12px',
            fontFamily: 'Inter, sans-serif',
            onItemHover: { highlightDataSeries: true },
            itemMargin: { horizontal: 8, vertical: 2 },
        },
        dataLabels: {
            enabled: true,
            formatter: value => `${Number(value).toFixed(1)}%`,
            style: {
                fontSize: '11px',
                fontFamily: 'Inter, sans-serif',
                fontWeight: '700',
                colors: ['#FFFFFF'],
            },
            dropShadow: { enabled: false },
            background: { enabled: false },
        },
        states: {
            normal: { filter: { type: 'none', value: 0 } },
            hover: { filter: { type: 'none', value: 0 } },
            inactive: { filter: { type: 'opacityFilter', value: 0.18 } },
        },
        plotOptions: { pie: { donut: { size: '62%' } } },
        noData: { text: 'Không có dữ liệu' },
    });

    const tbody = document.getElementById('roomDetailsTableBody');
    if (!tbody) return;
    tbody.replaceChildren();
    if (roomDetails.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="table-empty-state">Không có dữ liệu cuộc họp trong khoảng thời gian này.</td></tr>';
        return;
    }
    roomDetails.forEach(room => {
        const tr = document.createElement('tr');
        const occupancy = Number(room.occupancy_rate ?? 0);
        tr.innerHTML = `
            <td>${escapeHtml(String(room.room_id ?? '—'))}</td>
            <td><strong>${escapeHtml(String(room.room_name ?? ''))}</strong></td>
            <td>${Number(room.total_meetings ?? 0)}</td>
            <td>${Number(room.total_hours ?? 0).toFixed(1)} h</td>
            <td>${occupancy.toFixed(1)}%</td>
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

async function loadCancelReportData(e) {
    if (e && typeof e.preventDefault === 'function') e.preventDefault();
    const msgDiv = document.getElementById('cancellationAnalyticsMessage');
    const button = document.getElementById('btnFilterCancellation');
    const startDate = document.getElementById('cancellationStartDate')?.value;
    const endDate = document.getElementById('cancellationEndDate')?.value;
    const roomId = document.getElementById('cancellationRoomId')?.value;
    msgDiv?.classList.add('hidden');
    if (msgDiv) msgDiv.textContent = '';
    if (startDate && endDate && startDate > endDate) {
        if (msgDiv) {
            msgDiv.textContent = 'Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.';
            msgDiv.classList.remove('hidden');
        }
        return;
    }
    setReportButtonLoading(button, true);

    const params = new URLSearchParams();
    if (startDate) params.set('start_date', startDate.slice(0, 10));
    if (endDate) params.set('end_date', endDate.slice(0, 10));
    if (roomId) params.set('room_id', roomId);
    const usageParams = new URLSearchParams();
    if (startDate) usageParams.set('start_date', `${startDate.slice(0, 10)}T00:00:00`);
    if (endDate) usageParams.set('end_date', `${endDate.slice(0, 10)}T23:59:59.999999`);
    if (roomId) usageParams.set('room_id', roomId);

    try {
        let response = await requestReportPath('/v1/reports/cancellations', params);
        if (response.status === 404) {
            response = await requestReportPath('/v1/admin/analytics/cancellations', params);
        }
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
        let usageResponse = await requestReportPath('/v1/reports/usage', usageParams);
        if (usageResponse.status === 404) {
            usageResponse = await requestReportPath('/v1/reports/room-usage', usageParams);
        }
        if (!usageResponse.ok) {
            throw new Error(`Không thể tải dữ liệu cuộc họp thành công (${usageResponse.status}).`);
        }
        const [data, usageData] = await Promise.all([response.json(), usageResponse.json()]);
        renderCancellationAnalytics({
            ...data,
            successful_meetings: Number(usageData?.summary?.total_meetings ?? 0),
        });
    } catch (err) {
        console.error('Cancellation Analytics Error:', err);
        if (msgDiv) {
            msgDiv.textContent = `Lỗi tải thống kê: ${err instanceof Error ? err.message : String(err)}`;
            msgDiv.classList.remove('hidden');
        }
    } finally {
        setReportButtonLoading(button, false);
    }
}

function fetchCancellationAnalytics(event) {
    return loadCancelReportData(event);
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
        const response = await fetchAPI(
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
    if (format !== 'excel' && format !== 'pdf') {
        throw new RangeError(`Định dạng báo cáo không hợp lệ: ${format}.`);
    }
    const message = document.getElementById('executiveReportMessage');
    if (message) {
        message.hidden = true;
        message.textContent = '';
    }
    const startDate = document.getElementById('executiveStartDate')?.value;
    const endDate = document.getElementById('executiveEndDate')?.value;
    const departmentId = document.getElementById('executiveDepartmentId')?.value;
    if (startDate && endDate && startDate > endDate) {
        if (message) {
            message.textContent = 'Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.';
            message.hidden = false;
        }
        return;
    }

    const params = new URLSearchParams({ format });
    if (startDate) params.set('start_date', startDate.slice(0, 10));
    if (endDate) params.set('end_date', endDate.slice(0, 10));
    if (departmentId) params.set('department_id', departmentId);
    const excelButton = document.getElementById('btn-export-executive-excel');
    const pdfButton = document.getElementById('btn-export-executive-pdf');
    [excelButton, pdfButton].forEach(button => {
        if (button) button.disabled = true;
    });
    const activeButton = format === 'excel' ? excelButton : pdfButton;
    const activeLabel = activeButton?.querySelector('.executive-export-label');
    if (activeLabel) activeLabel.textContent = 'Đang tạo báo cáo...';
    const reportWindow = window.open('', '_blank');

    try {
        if (!reportWindow) {
            throw new Error('Trình duyệt đã chặn cửa sổ báo cáo. Hãy cho phép cửa sổ bật lên rồi thử lại.');
        }
        const response = await fetchAPI(
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
        reportWindow.location.href = url;
        window.setTimeout(() => window.URL.revokeObjectURL(url), 60000);
    } catch (err) {
        reportWindow?.close();
        console.error('Executive Report Export Error:', err);
        if (message) {
            message.textContent = `Lỗi xuất báo cáo: ${err instanceof Error ? err.message : String(err)}`;
            message.hidden = false;
        }
    } finally {
        [excelButton, pdfButton].forEach(button => {
            if (button) button.disabled = false;
        });
        const excelLabel = excelButton?.querySelector('.executive-export-label');
        const pdfLabel = pdfButton?.querySelector('.executive-export-label');
        if (excelLabel) excelLabel.textContent = 'Xuất Excel (.xlsx)';
        if (pdfLabel) pdfLabel.textContent = 'Xuất PDF (.pdf)';
    }
}

async function loadExecutiveDepartments() {
    const select = document.getElementById('executiveDepartmentId');
    if (!select || select.options.length > 1) return;
    const headers = { Authorization: `Bearer ${getAuthToken()}` };
    let response = await fetchAPI(`${API_BASE}/v1/directories/departments`, { headers });
    if (response.status === 404) {
        response = await fetchAPI(`${API_BASE}/v1/departments`, { headers });
    }
    if (!response.ok) {
        throw new Error(`Không thể tải danh sách phòng ban (HTTP ${response.status}).`);
    }
    const departments = await response.json();
    if (!Array.isArray(departments)) {
        throw new Error('Dữ liệu danh sách phòng ban không hợp lệ.');
    }
    departments.forEach(department => {
        if (department?.id == null || !department.name) return;
        select.add(new Option(String(department.name), String(department.id)));
    });
}

async function openExecutiveReportModal() {
    const modal = document.getElementById('executiveReportModal');
    if (!modal) return;
    modal.style.display = 'flex';
    modal.setAttribute('aria-hidden', 'false');
    const message = document.getElementById('executiveReportMessage');
    if (message) {
        message.hidden = true;
        message.textContent = '';
    }
    try {
        await loadExecutiveDepartments();
    } catch (error) {
        if (message) {
            message.textContent = error instanceof Error ? error.message : 'Không thể tải phòng ban.';
            message.hidden = false;
        }
    }
    document.getElementById('executiveStartDate')?.focus();
}

function closeExecutiveReportModal() {
    const modal = document.getElementById('executiveReportModal');
    if (!modal) return;
    modal.style.display = 'none';
    modal.setAttribute('aria-hidden', 'true');
    document.getElementById('btn-open-executive-modal')?.focus();
}

function renderCancellationAnalytics(data) {
    const summary = data?.summary ?? {};
    const parsedTotal = Number(summary.total_cancelled ?? 0);
    const totalCancelled = Number.isFinite(parsedTotal) ? parsedTotal : 0;
    const totalElement = document.getElementById('kpiTotalCancels');
    const hoursElement = document.getElementById('cancelledWastedHours');
    const rateElement = document.getElementById('kpiCancelRate');
    const reasonElement = document.getElementById('cancellationPopularReason');
    if (totalElement) totalElement.textContent = String(totalCancelled);
    const wastedHours = Number(summary.total_wasted_hours ?? 0);
    if (hoursElement) {
        hoursElement.textContent = `${(Number.isFinite(wastedHours) ? wastedHours : 0).toFixed(2)} giờ`;
    }
    const cancellationRate = Number(data?.cancellation_rate ?? 0);
    if (rateElement) rateElement.textContent = `${Number.isFinite(cancellationRate) ? cancellationRate.toFixed(1) : '0.0'}%`;
    if (reasonElement) reasonElement.textContent = data?.breakdown_by_reason?.[0]?.reason || 'Chưa có dữ liệu';

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

    const meetingsBody = document.getElementById('cancellationMeetingsBody');
    if (meetingsBody) {
        meetingsBody.replaceChildren();
        const records = Array.isArray(data?.cancellation_records) ? data.cancellation_records : [];
        if (!records.length) {
            meetingsBody.innerHTML = '<tr><td colspan="6" class="cancellation-empty">Không có dữ liệu trong khoảng thời gian này</td></tr>';
        } else {
            records.forEach(record => {
                const row = document.createElement('tr');
                const startTime = record.start_time ? new Date(record.start_time).toLocaleString('vi-VN') : '—';
                [record.meeting_id, record.title, record.room_name, record.organizer_name, startTime, record.cancellation_reason]
                    .forEach(value => {
                        const cell = document.createElement('td');
                        cell.textContent = value == null ? '—' : String(value);
                        row.appendChild(cell);
                    });
                meetingsBody.appendChild(row);
            });
        }
    }

    const reasons = Array.isArray(data?.breakdown_by_reason) ? data.breakdown_by_reason : [];
    updateReportChart('chartCancelReasons', {
        chart: { type: 'donut', height: 288 },
        series: reasons.map(item => Number(item.cancel_count ?? 0)),
        labels: reasons.map(item => String(item.reason ?? 'Không xác định')),
        colors: REPORT_CHART_COLORS,
        legend: {
            position: 'bottom',
            horizontalAlign: 'center',
            fontSize: '12px',
            itemMargin: { horizontal: 8, vertical: 2 },
        },
        dataLabels: {
            enabled: true,
            formatter: value => `${Number(value).toFixed(1)}%`,
            style: {
                fontSize: '11px',
                fontFamily: 'Inter, sans-serif',
                fontWeight: '700',
                colors: ['#FFFFFF'],
            },
            dropShadow: { enabled: false },
            background: { enabled: false },
        },
        states: {
            hover: { filter: { type: 'darken', value: 0.88 } },
            active: { allowMultipleDataPointsSelection: false, filter: { type: 'none' } },
        },
        plotOptions: { pie: { donut: { size: '58%' } } },
        noData: { text: 'Không có dữ liệu' },
    });
    const successfulMeetings = Math.max(0, Number(data?.successful_meetings ?? 0));
    updateReportChart('chartCancelvsSuccess', {
        chart: { type: 'bar', height: 288, stacked: true, toolbar: { show: false } },
        series: [
            { name: 'Thành công', data: [successfulMeetings] },
            { name: 'Bị hủy', data: [totalCancelled] },
        ],
        colors: ['#10B981', '#E11D48'],
        plotOptions: { bar: { horizontal: false, columnWidth: '42%', borderRadius: 6 } },
        dataLabels: { enabled: false },
        xaxis: { categories: ['Thống kê cuộc họp'] },
        yaxis: {
            min: 0,
            title: {
                text: 'Số cuộc họp',
                offsetX: -8,
                style: { fontSize: '12px', fontWeight: 600, color: '#475569' },
            },
        },
        legend: { position: 'bottom' },
        noData: { text: 'Không có dữ liệu' },
        grid: { borderColor: '#e2e8f0' },
    });
}

/* GLOBAL EXPORTS (GẮN VÀO WINDOW CHO EVENT HANDLER) */
window.toggleSidebar = toggleSidebar;
window.toggleMobileMenu = toggleMobileMenu;
window.closeMobileMenu = closeMobileMenu;
window.switchToOverview = switchToOverview;
window.switchMainTab = switchMainTab;
window.switchReportTab = switchReportTab;
window.showUserManagementSection = showUserManagementSection;
window.navigateToSettings = navigateToSettings;
window.handleAdminCreateUser = handleAdminCreateUser;
window.scrollToRooms = scrollToRooms;
window.toggleNotificationPopup = toggleNotificationPopup;
window.openScheduleModal = openScheduleModal;
window.closeScheduleModal = closeScheduleModal;
window.openQrCheckModal = openQrCheckModal;
window.closeQrCheckModal = closeQrCheckModal;
window.submitQrCheck = submitQrCheck;
window.openQuickQrScanner = openQuickQrScanner;
window.handleSmartQrResult = handleSmartQrResult;
window.closeQuickQrScanner = closeQuickQrScanner;
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
window.previewRoomImage = previewRoomImage;
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
window.loadUsageReportData = loadUsageReportData;
window.loadCancelReportData = loadCancelReportData;
window.loadRoomsForReportFilter = loadRoomsForReportFilter;
window.updateUserSettings = updateUserSettings;

/* ==========================================================================
   AI CHAT DRAWER
   ========================================================================== */
const CHATBOT_API_BASE = `${API_BASE}/v1/chatbot`;
let activeChatSessionId = null;
let chatSessions = [];
let chatHistoryRequestId = 0;
let chatMessageRequestPending = false;
let chatMinimizeTimer = null;

document.addEventListener('DOMContentLoaded', initializeAiChat);

function initializeAiChat() {
    const launcher = document.getElementById('ai-chat-launcher');
    const drawer = document.getElementById('ai-chat-drawer');
    const form = document.getElementById('ai-chat-form');
    if (!launcher || !drawer || !form) return;

    launcher.addEventListener('click', openAiChatDrawer);
    document.getElementById('ai-chat-close')?.addEventListener('click', closeAiChatDrawer);
    document.getElementById('ai-chat-minimize')?.addEventListener('click', closeAiChatDrawer);
    document.getElementById('ai-chat-new-session')?.addEventListener('click', createAiChatSession);
    document.getElementById('ai-chat-history-refresh')?.addEventListener('click', loadAiChatSessions);
    document.addEventListener('click', event => {
        if (!drawer.hidden && !drawer.contains(event.target) && !launcher.contains(event.target)) {
            closeAiChatDrawer(false);
        }
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && !drawer.hidden) closeAiChatDrawer();
    });
    drawer.querySelectorAll('[data-ai-chat-prompt]').forEach(button => {
        button.addEventListener('click', () => {
            const input = document.getElementById('ai-chat-input');
            if (!input || chatMessageRequestPending) return;
            input.value = button.dataset.aiChatPrompt || '';
            form.requestSubmit();
        });
    });
    form.addEventListener('submit', sendAiChatMessage);
}

async function openAiChatDrawer() {
    const drawer = document.getElementById('ai-chat-drawer');
    const launcher = document.getElementById('ai-chat-launcher');
    if (!drawer || !launcher) return;

    clearTimeout(chatMinimizeTimer);
    drawer.classList.remove('is-minimizing');
    drawer.hidden = false;
    drawer.setAttribute('aria-hidden', 'false');
    launcher.setAttribute('aria-expanded', 'true');
    document.getElementById('ai-chat-input')?.focus();
    await loadAiChatSessions();
}

function closeAiChatDrawer(restoreFocus = true) {
    const drawer = document.getElementById('ai-chat-drawer');
    const launcher = document.getElementById('ai-chat-launcher');
    if (!drawer || !launcher) return;

    drawer.classList.add('is-minimizing');
    launcher.setAttribute('aria-expanded', 'false');
    clearTimeout(chatMinimizeTimer);
    chatMinimizeTimer = setTimeout(() => {
        if (drawer.classList.contains('is-minimizing')) {
            drawer.hidden = true;
            drawer.setAttribute('aria-hidden', 'true');
            drawer.classList.remove('is-minimizing');
            if (restoreFocus) launcher.focus();
        }
    }, 180);
}

function chatAuthHeaders(json = false) {
    const headers = { Authorization: `Bearer ${getAuthToken()}` };
    if (json) headers['Content-Type'] = 'application/json';
    return headers;
}

async function chatApiRequest(path, options = {}) {
    const response = await fetchAPI(`${CHATBOT_API_BASE}${path}`, {
        ...options,
        headers: { ...chatAuthHeaders(Boolean(options.body)), ...(options.headers || {}) },
    });
    if (!response.ok) {
        let detail = `Yêu cầu thất bại (${response.status}).`;
        try {
            const payload = await response.json();
            const responseDetail = payload?.detail;
            detail = typeof responseDetail === 'string'
                ? responseDetail
                : responseDetail?.message || payload?.message || detail;
        } catch {
            // Keep the HTTP status message when the server response is not JSON.
        }
        throw new Error(detail);
    }
    return response.status === 204 ? null : response.json();
}

async function loadAiChatSessions() {
    const list = document.getElementById('ai-chat-history-list');
    if (!list) return;
    list.innerHTML = '<p class="ai-chat-muted">Đang tải lịch sử...</p>';

    try {
        const result = await chatApiRequest('/sessions?limit=100');
        chatSessions = Array.isArray(result) ? result : [];
        renderAiChatSessionList();

        if (activeChatSessionId && chatSessions.some(session => session.id === activeChatSessionId)) {
            return;
        }
        if (chatSessions.length) {
            await selectAiChatSession(chatSessions[0].id);
        } else {
            await createAiChatSession();
        }
    } catch (error) {
        list.innerHTML = `<p class="ai-chat-muted">${escapeHtml(error.message || 'Không thể tải lịch sử chat.')}</p>`;
        setAiChatStatus(error.message || 'Không thể tải lịch sử chat.');
    }
}

function renderAiChatSessionList() {
    const list = document.getElementById('ai-chat-history-list');
    if (!list) return;
    if (!chatSessions.length) {
        list.innerHTML = '<p class="ai-chat-muted">Chưa có cuộc trò chuyện nào.</p>';
        return;
    }

    list.replaceChildren(...chatSessions.map(session => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `ai-chat-history-item${session.id === activeChatSessionId ? ' is-active' : ''}`;
        button.setAttribute('aria-current', session.id === activeChatSessionId ? 'true' : 'false');
        const title = document.createElement('strong');
        title.textContent = session.title || 'Cuộc trò chuyện';
        const updated = document.createElement('span');
        updated.textContent = formatChatTimestamp(session.updated_at || session.created_at);
        button.append(title, updated);
        button.addEventListener('click', () => selectAiChatSession(session.id));
        return button;
    }));
}

async function createAiChatSession() {
    setAiChatStatus('');
    const button = document.getElementById('ai-chat-new-session');
    if (button) button.disabled = true;
    try {
        const session = await chatApiRequest('/sessions', {
            method: 'POST',
            body: JSON.stringify({ title: 'Cuộc trò chuyện mới' }),
        });
        chatSessions = [session, ...chatSessions.filter(item => item.id !== session.id)];
        activeChatSessionId = session.id;
        renderAiChatSessionList();
        renderAiChatMessages([]);
        document.getElementById('ai-chat-input')?.focus();
    } catch (error) {
        setAiChatStatus(error.message || 'Không thể tạo cuộc trò chuyện mới.');
    } finally {
        if (button) button.disabled = false;
    }
}

async function selectAiChatSession(sessionId) {
    const requestId = ++chatHistoryRequestId;
    activeChatSessionId = sessionId;
    renderAiChatSessionList();
    setAiChatStatus('');
    const messages = document.getElementById('ai-chat-messages');
    if (messages) messages.innerHTML = '<p class="ai-chat-muted">Đang tải tin nhắn...</p>';

    try {
        const history = await chatApiRequest(`/sessions/${encodeURIComponent(sessionId)}/messages?limit=500`);
        if (requestId !== chatHistoryRequestId || sessionId !== activeChatSessionId) return;
        renderAiChatMessages(Array.isArray(history) ? history : []);
    } catch (error) {
        if (requestId !== chatHistoryRequestId) return;
        renderAiChatMessages([]);
        setAiChatStatus(error.message || 'Không thể tải tin nhắn.');
    }
}

async function sendAiChatMessage(event) {
    event.preventDefault();
    const input = document.getElementById('ai-chat-input');
    const sendButton = document.getElementById('ai-chat-send');
    const content = input?.value.trim();
    if (!input || !content || chatMessageRequestPending) return;

    let botMessage = null;
    chatMessageRequestPending = true;
    if (sendButton) sendButton.disabled = true;
    document.querySelectorAll('[data-ai-chat-prompt]').forEach(button => {
        button.disabled = true;
    });
    input.disabled = true;
    input.value = '';
    setAiChatStatus('');
    appendAiChatMessage({ sender: 'user', content });
    botMessage = appendAiChatMessage({ sender: 'bot', content: 'AI đang đọc yêu cầu' });
    botMessage.row.classList.add('is-thinking');
    botMessage.text.setAttribute('aria-live', 'polite');
    try {
        if (!activeChatSessionId) {
            await createAiChatSession();
        }
        if (!activeChatSessionId) {
            throw new Error('Không thể tạo phiên trò chuyện. Vui lòng thử lại.');
        }
        if (!botMessage.row.isConnected) {
            appendAiChatMessage({ sender: 'user', content });
            botMessage = appendAiChatMessage({ sender: 'bot', content: 'AI đang đọc yêu cầu' });
            botMessage.row.classList.add('is-thinking');
            botMessage.text.setAttribute('aria-live', 'polite');
        }

        const sessionId = activeChatSessionId;
        const response = await fetchAPI(
            `${CHATBOT_API_BASE}/sessions/${encodeURIComponent(sessionId)}/message/stream`,
            {
                method: 'POST',
                headers: chatAuthHeaders(true),
                body: JSON.stringify({ content }),
            },
        );
        if (!response.ok) {
            let detail = `Yêu cầu thất bại (${response.status}).`;
            try {
                const payload = await response.json();
                const responseDetail = payload?.detail;
                detail = typeof responseDetail === 'string'
                    ? responseDetail
                    : responseDetail?.message || payload?.message || detail;
            } catch {
                // Keep the HTTP status message when the server response is not JSON.
            }
            throw new Error(detail);
        }
        if (!response.body) throw new Error('Không thể đọc phản hồi từ trợ lý.');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let completedResponse = null;
        const handleSseEvent = (block) => {
            if (!block.trim()) return;
            let eventType = 'message';
            const dataLines = [];
            block.split(/\r?\n/).forEach(line => {
                if (line.startsWith('event:')) eventType = line.slice(6).trim();
                else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart());
            });
            if (!dataLines.length) return;
            const payload = JSON.parse(dataLines.join('\n'));
            if (eventType === 'error') {
                throw new Error(payload.message || 'Trợ lý không thể xử lý tin nhắn.');
            }
            if (eventType === 'chunk') {
                if (sessionId !== activeChatSessionId) return;
                if (!botMessage) botMessage = appendAiChatMessage({ sender: 'bot', content: '' });
                botMessage.row.classList.remove('is-thinking');
                botMessage.text.textContent += payload.text || '';
                scrollAiChatToLatest();
            } else if (eventType === 'preview_card') {
                if (sessionId !== activeChatSessionId) return;
                if (!botMessage) botMessage = appendAiChatMessage({ sender: 'bot', content: '' });
                botMessage.row.classList.remove('is-thinking');
                botMessage.interactivePreview = createAiChatInvitePreview(payload);
                botMessage.bubble.appendChild(botMessage.interactivePreview);
                scrollAiChatToLatest();
            } else if (eventType === 'room_widget') {
                if (sessionId !== activeChatSessionId) return;
                if (!botMessage) botMessage = appendAiChatMessage({ sender: 'bot', content: '' });
                botMessage.row.classList.remove('is-thinking');
                botMessage.interactivePreview = createAiChatRoomWidget(payload);
                botMessage.bubble.appendChild(botMessage.interactivePreview);
                scrollAiChatToLatest();
            } else if (eventType === 'complete') {
                completedResponse = payload.response;
                if (sessionId === activeChatSessionId) {
                    if (!botMessage) botMessage = appendAiChatMessage({ sender: 'bot', content: '' });
                    completeAiChatMessage(botMessage, completedResponse);
                }
            }
        };

        try {
            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const blocks = buffer.split(/\r?\n\r?\n/);
                buffer = blocks.pop() || '';
                blocks.forEach(handleSseEvent);
            }
            buffer += decoder.decode();
            if (buffer.trim()) handleSseEvent(buffer);
        } finally {
            reader.releaseLock();
        }
        if (!completedResponse) throw new Error('Luồng phản hồi đã kết thúc bất thường.');
        await refreshAiChatSessionsAfterMessage(sessionId);
    } catch (error) {
        if (botMessage) {
            botMessage.row.classList.remove('is-thinking');
            botMessage.text.textContent = error.message || 'Không thể gửi tin nhắn. Vui lòng thử lại.';
        }
        setAiChatStatus(error.message || 'Không thể gửi tin nhắn. Vui lòng thử lại.');
    } finally {
        chatMessageRequestPending = false;
        if (sendButton) sendButton.disabled = false;
        document.querySelectorAll('[data-ai-chat-prompt]').forEach(button => {
            button.disabled = false;
        });
        input.disabled = false;
        if (!document.getElementById('ai-chat-drawer')?.hidden) input.focus();
    }
}

async function refreshAiChatSessionsAfterMessage(sessionId) {
    try {
        const result = await chatApiRequest('/sessions?limit=100');
        chatSessions = Array.isArray(result) ? result : [];
        if (!chatSessions.some(session => session.id === sessionId)) {
            chatSessions.unshift({ id: sessionId, title: 'Cuộc trò chuyện', updated_at: new Date().toISOString() });
        }
        renderAiChatSessionList();
    } catch (error) {
        setAiChatStatus(error.message || 'Tin nhắn đã gửi nhưng không thể cập nhật lịch sử.');
    }
}

function renderAiChatMessages(messages) {
    const container = document.getElementById('ai-chat-messages');
    if (!container) return;
    container.replaceChildren();
    if (!messages.length) {
        const welcome = document.createElement('div');
        welcome.className = 'ai-chat-welcome';
        welcome.innerHTML = '<svg class="ai-chat-welcome-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z"></path></svg><strong>Xin chào! Tôi có thể giúp bạn đặt phòng họp.</strong><p>Hãy cho tôi biết ngày, giờ, thời lượng và số người tham dự.</p>';
        container.appendChild(welcome);
        return;
    }
    messages.forEach(message => appendAiChatMessage(message));
    scrollAiChatToLatest();
}

function appendAiChatMessage(message) {
    const container = document.getElementById('ai-chat-messages');
    if (!container) return;
    container.querySelector('.ai-chat-welcome')?.remove();

    const isUser = message.sender === 'user';
    const row = document.createElement('div');
    row.className = `ai-chat-message-row ${isUser ? 'is-user' : 'is-bot'}`;
    const bubble = document.createElement('div');
    bubble.className = 'ai-chat-bubble';
    const text = document.createElement('div');
    text.textContent = message.content || '';
    bubble.appendChild(text);

    const completeBooking = message.intent === 'BOOK_ROOM'
        && hasCompleteChatBookingSlots(message.slots);
    if (!isUser && (message.is_ready_for_preview === true || completeBooking)) {
        bubble.appendChild(createAiChatPreview(message.slots, message.ui_widget));
    }

    const timestamp = document.createElement('div');
    timestamp.className = 'ai-chat-message-time';
    timestamp.textContent = formatChatTimestamp(message.created_at || new Date().toISOString(), true);
    bubble.appendChild(timestamp);
    row.appendChild(bubble);
    container.appendChild(row);
    scrollAiChatToLatest();
    return { row, bubble, text, interactivePreview: null };
}

function completeAiChatMessage(messageElement, response) {
    const message = response || {};
    messageElement.row.classList.remove('is-thinking');
    messageElement.text.textContent = message.message || message.bot_message || messageElement.text.textContent;
    const slots = message.preview_card || message.slots;
    const completeBooking = message.intent === 'BOOK_ROOM'
        && hasCompleteChatBookingSlots(slots);
    if (!messageElement.interactivePreview
        && (message.is_ready_for_preview === true || completeBooking)) {
        messageElement.bubble.appendChild(createAiChatPreview(slots, message.ui_widget));
    }
    scrollAiChatToLatest();
}

function hasCompleteChatBookingSlots(slots) {
    return Boolean(
        slots
        && slots.title
        && slots.booking_date
        && slots.start_time
        && Number(slots.duration_minutes) > 0
        && Number(slots.capacity) > 0
        && slots.room_id,
    );
}

function createAiChatPreview(slots, widget) {
    const card = document.createElement('section');
    card.className = 'ai-chat-preview';
    const heading = document.createElement('h3');
    heading.textContent = 'Xem trước cuộc họp';
    const details = document.createElement('dl');
    const entries = [
        ['Tiêu đề', slots.title],
        ['Ngày', formatChatDate(slots.booking_date)],
        ['Giờ bắt đầu', slots.start_time],
        ['Thời lượng', `${slots.duration_minutes} phút`],
        ['Số người', `${slots.capacity} người`],
        ['Phòng gợi ý', slots.room_name || 'Phòng đã chọn'],
    ];
    entries.forEach(([label, value]) => {
        const term = document.createElement('dt');
        term.textContent = label;
        const description = document.createElement('dd');
        description.textContent = String(value ?? '—');
        details.append(term, description);
    });

    const confirmButton = document.createElement('button');
    confirmButton.type = 'button';
    confirmButton.className = 'ai-chat-confirm-button';
    confirmButton.textContent = widget?.actions?.[0]?.label || 'Xác nhận đặt phòng';
    confirmButton.addEventListener('click', () => confirmAiChatBooking(slots, confirmButton));
    card.append(heading, details, confirmButton);
    return card;
}

function createAiChatRoomWidget(payload) {
    const widget = payload.widget || {};
    if (widget.type === 'ROOM_CONFIRMATION_WIDGET') {
        return createAiChatRoomConfirmationWidget(widget);
    }
    if (widget.type === 'CANCEL_CONFIRM_WIDGET') {
        return createAiChatCancellationWidget(widget);
    }
    if (widget.type === 'MY_SCHEDULE_WIDGET' || widget.type === 'ROOM_LIST_WIDGET') {
        return createAiChatListWidget(widget);
    }

    const room = widget.data || {};
    const meeting = payload.meeting || {};
    const card = document.createElement('section');
    card.className = 'ai-chat-preview ai-chat-room-widget';

    const heading = document.createElement('h3');
    heading.textContent = widget.title || 'Phòng họp phù hợp';
    const details = document.createElement('dl');
    [
        ['Phòng', room.name || 'Phòng họp'],
        ['Sức chứa', room.capacity ? `${room.capacity} người` : '—'],
        ['Vị trí', room.location || '—'],
    ].forEach(([label, value]) => {
        const term = document.createElement('dt');
        term.textContent = label;
        const description = document.createElement('dd');
        description.textContent = String(value);
        details.append(term, description);
    });

    const slots = {
        ...meeting,
        room_id: room.id ?? meeting.room_id,
        room_name: room.name || meeting.room_name,
    };
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'ai-chat-confirm-button';
    button.textContent = widget.actions?.[0]?.label || 'Đặt ngay';
    button.addEventListener('click', () => {
        if (hasCompleteChatBookingSlots(slots)) {
            confirmAiChatBooking(slots, button);
        } else if (room.id && typeof window.openCreateMeeting === 'function') {
            window.openCreateMeeting({ roomId: room.id });
        } else {
            setAiChatStatus('Không thể mở biểu mẫu đặt phòng. Vui lòng thử lại.');
        }
    });
    card.append(heading, details, button);
    return card;
}

function createAiChatRoomConfirmationWidget(widget) {
    const meeting = widget.meeting || {};
    const room = widget.data || {};
    const participants = Array.isArray(widget.participants) ? widget.participants : [];
    const card = document.createElement('section');
    card.className = 'ai-chat-preview ai-chat-room-widget';
    const heading = document.createElement('h3');
    heading.textContent = widget.title || 'Xác nhận cuộc họp';

    const details = document.createElement('dl');
    [
        ['Cuộc họp', meeting.title],
        ['Ngày', formatChatDate(meeting.booking_date)],
        ['Thời gian', `${meeting.start_time || '—'} · ${meeting.duration_minutes || '—'} phút`],
        ['Phòng', room.name || meeting.room_name || '—'],
        ['Sức chứa', meeting.capacity ? `${meeting.capacity} người` : '—'],
    ].forEach(([label, value]) => {
        const term = document.createElement('dt');
        term.textContent = label;
        const description = document.createElement('dd');
        description.textContent = String(value ?? '—');
        details.append(term, description);
    });
    card.append(heading, details);

    const participantIds = new Set();
    if (participants.length) {
        const participantsHeading = document.createElement('h4');
        participantsHeading.textContent = `Người tham dự (${participants.length})`;
        const participantList = document.createElement('div');
        participantList.className = 'ai-chat-attendee-list ai-chat-participant-list';
        participants.forEach(participant => {
            const label = document.createElement('label');
            label.className = 'ai-chat-attendee';
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = String(participant.id);
            checkbox.checked = true;
            participantIds.add(participant.id);
            const identity = document.createElement('span');
            identity.textContent = participant.full_name || participant.email || 'Người tham dự';
            label.append(checkbox, identity);
            participantList.appendChild(label);
        });
        card.append(participantsHeading, participantList);
    }

    const equipmentOptions = Array.isArray(widget.equipment_options)
        ? widget.equipment_options
        : [];
    const selectedEquipmentIds = new Set();
    if (equipmentOptions.length) {
        const equipmentDetails = document.createElement('details');
        equipmentDetails.className = 'ai-chat-equipment-options';
        const summary = document.createElement('summary');
        summary.textContent = 'Chọn thêm thiết bị';
        const equipmentList = document.createElement('div');
        equipmentList.className = 'ai-chat-equipment-list';
        const requiredNames = (widget.equipments_required || []).map(name => String(name).toLocaleLowerCase());
        equipmentOptions.forEach(equipment => {
            const label = document.createElement('label');
            label.className = 'ai-chat-attendee';
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = String(equipment.id);
            const equipmentName = String(equipment.name).toLocaleLowerCase();
            checkbox.checked = Number(equipment.available_quantity) > 0
                && requiredNames.some(name => name.includes(equipmentName) || equipmentName.includes(name));
            checkbox.disabled = Number(equipment.available_quantity) <= 0;
            if (checkbox.checked) selectedEquipmentIds.add(equipment.id);
            checkbox.addEventListener('change', () => {
                if (checkbox.checked) selectedEquipmentIds.add(equipment.id);
                else selectedEquipmentIds.delete(equipment.id);
            });
            const identity = document.createElement('span');
            identity.textContent = `${equipment.name} (${equipment.available_quantity ?? 0} còn)`;
            label.append(checkbox, identity);
            equipmentList.appendChild(label);
        });
        equipmentDetails.append(summary, equipmentList);
        card.appendChild(equipmentDetails);
    }

    const confirmButton = document.createElement('button');
    confirmButton.type = 'button';
    confirmButton.className = 'ai-chat-confirm-button';
    confirmButton.textContent = widget.actions?.[0]?.label || 'Đồng ý tạo cuộc họp';
    confirmButton.addEventListener('click', () => {
        const selectedParticipants = [...card.querySelectorAll('.ai-chat-participant-list input[type="checkbox"]')]
            .filter(input => participantIds.has(Number(input.value)) && input.checked)
            .map(input => Number(input.value));
        const equipments = [...selectedEquipmentIds].map(equipmentId => ({
            equipment_id: equipmentId,
            quantity: 1,
        }));
        confirmAiChatMeeting(
            { ...meeting, room_id: room.id ?? meeting.room_id, room_name: room.name || meeting.room_name },
            selectedParticipants,
            confirmButton,
            equipments,
        );
    });
    card.appendChild(confirmButton);
    return card;
}

function createAiChatCancellationWidget(widget) {
    const meeting = widget.data || {};
    const card = document.createElement('section');
    card.className = 'ai-chat-preview ai-chat-room-widget';
    const heading = document.createElement('h3');
    heading.textContent = widget.title || 'Xác nhận hủy cuộc họp';
    const details = document.createElement('p');
    details.textContent = `${meeting.title || 'Cuộc họp'} · ${formatChatTimestamp(meeting.start_time, true)} · ${meeting.room_name || 'Trực tuyến'}`;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'ai-chat-confirm-button';
    button.textContent = widget.actions?.[0]?.label || 'Xác nhận hủy';
    button.addEventListener('click', async () => {
        if (button.disabled) return;
        button.disabled = true;
        button.textContent = 'Đang hủy...';
        const status = document.createElement('p');
        status.className = 'ai-chat-confirm-result';
        status.setAttribute('role', 'status');
        card.appendChild(status);
        try {
            const response = await fetchAPI(`${API_BASE}/v1/meetings/${encodeURIComponent(meeting.id)}/cancel`, {
                method: 'PATCH',
                headers: chatAuthHeaders(true),
                body: JSON.stringify({ cancellation_reason: 'Người dùng xác nhận hủy qua trợ lý RoomSync.' }),
            });
            const result = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(result?.detail || 'Không thể hủy cuộc họp.');
            status.textContent = 'Đã hủy cuộc họp.';
            button.textContent = 'Đã hủy';
        } catch (error) {
            status.classList.add('is-error');
            status.textContent = error.message || 'Không thể hủy cuộc họp.';
            button.textContent = 'Thử lại';
            button.disabled = false;
        }
    });
    card.append(heading, details, button);
    return card;
}

function createAiChatListWidget(widget) {
    const card = document.createElement('section');
    card.className = 'ai-chat-preview ai-chat-room-widget';
    const heading = document.createElement('h3');
    heading.textContent = widget.title || 'Kết quả';
    card.appendChild(heading);
    const list = document.createElement('ul');
    list.className = 'ai-chat-widget-list';
    const entries = Array.isArray(widget.data) ? widget.data : [];
    if (!entries.length) {
        const empty = document.createElement('li');
        empty.textContent = 'Chưa có dữ liệu phù hợp.';
        list.appendChild(empty);
    }
    entries.forEach(item => {
        const entry = document.createElement('li');
        if (widget.type === 'ROOM_LIST_WIDGET') {
            entry.textContent = `${item.name || 'Phòng họp'} · ${item.capacity ?? '—'} chỗ · ${item.location || 'Vị trí chưa cập nhật'}`;
        } else {
            entry.textContent = `${item.title || 'Cuộc họp'} · ${formatChatTimestamp(item.start_time, true)}–${formatChatTimestamp(item.end_time, true)} · ${item.room_name || 'Trực tuyến'}`;
        }
        list.appendChild(entry);
    });
    card.appendChild(list);
    return card;
}

function createAiChatInvitePreview(preview) {
    const meeting = preview.meeting || {};
    const participants = Array.isArray(preview.participants) ? preview.participants : [];
    const card = document.createElement('section');
    card.className = 'ai-chat-preview ai-chat-invite-preview';
    const heading = document.createElement('h3');
    heading.textContent = 'Xem trước cuộc họp và người tham dự';

    const details = document.createElement('dl');
    [
        ['Tiêu đề', meeting.title],
        ['Ngày', formatChatDate(meeting.booking_date)],
        ['Thời gian', `${meeting.start_time || '—'} · ${meeting.duration_minutes || '—'} phút`],
        ['Phòng', meeting.room_name || (meeting.room_id ? `Phòng ${meeting.room_id}` : '—')],
        ['Sức chứa', meeting.room_capacity ?? '—'],
    ].forEach(([label, value]) => {
        const term = document.createElement('dt');
        term.textContent = label;
        const description = document.createElement('dd');
        description.textContent = String(value ?? '—');
        details.append(term, description);
    });

    const attendeesHeading = document.createElement('h4');
    attendeesHeading.className = 'ai-chat-attendees-heading';
    attendeesHeading.textContent = `Người được mời (${participants.length})`;
    const attendeeList = document.createElement('div');
    attendeeList.className = 'ai-chat-attendee-list';
    if (!participants.length) {
        const empty = document.createElement('p');
        empty.className = 'ai-chat-muted';
        empty.textContent = 'Không tìm thấy người phù hợp với tiêu chí.';
        attendeeList.appendChild(empty);
    }
    participants.forEach(participant => {
        const label = document.createElement('label');
        label.className = 'ai-chat-attendee';
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = String(participant.id);
        checkbox.checked = true;
        checkbox.setAttribute('aria-label', `Mời ${participant.full_name || 'người tham dự'}`);
        const identity = document.createElement('span');
        const name = document.createElement('strong');
        name.textContent = participant.full_name || 'Chưa có tên';
        const meta = document.createElement('small');
        const department = participant.department?.name || 'Chưa có phòng ban';
        meta.textContent = [
            participant.email,
            participant.position,
            department,
        ].filter(Boolean).join(' · ');
        identity.append(name, meta);
        label.append(checkbox, identity);
        attendeeList.appendChild(label);
    });

    const warning = document.createElement('p');
    warning.className = 'ai-chat-capacity-warning';
    warning.setAttribute('role', 'alert');
    const updateCapacityWarning = () => {
        const selectedCount = attendeeList.querySelectorAll('input[type="checkbox"]:checked').length;
        const roomCapacity = Number(meeting.room_capacity);
        const overCapacity = Number.isFinite(roomCapacity) && selectedCount > roomCapacity;
        warning.hidden = !overCapacity;
        warning.textContent = overCapacity
            ? `Cảnh báo: ${selectedCount} người được mời vượt sức chứa ${roomCapacity} người của phòng.`
            : '';
    };
    attendeeList.addEventListener('change', updateCapacityWarning);
    card.append(heading, details, attendeesHeading, attendeeList, warning);
    updateCapacityWarning();

    const actions = document.createElement('div');
    actions.className = 'ai-chat-preview-actions';
    const confirmButton = document.createElement('button');
    confirmButton.type = 'button';
    confirmButton.className = 'ai-chat-confirm-button';
    confirmButton.textContent = preview.widget?.actions?.[0]?.label
        || '🚀 Xác nhận tạo cuộc họp';
    confirmButton.disabled = participants.length === 0;
    confirmButton.addEventListener('click', () => {
        const selectedIds = [...attendeeList.querySelectorAll('input[type="checkbox"]:checked')]
            .map(input => Number(input.value));
        confirmAiChatMeeting(meeting, selectedIds, confirmButton);
    });
    const editButton = document.createElement('button');
    editButton.type = 'button';
    editButton.className = 'ai-chat-edit-button';
    editButton.textContent = '⚙ Chỉnh sửa';
    editButton.addEventListener('click', () => {
        const input = document.getElementById('ai-chat-input');
        if (!input) return;
        input.value = 'Chỉnh sửa cuộc họp này: ';
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
    });
    actions.append(confirmButton, editButton);
    card.appendChild(actions);
    return card;
}

async function confirmAiChatMeeting(meeting, participantIds, button, equipments = []) {
    const card = button.closest('.ai-chat-preview');
    if (!card || button.disabled) return;
    button.disabled = true;
    button.textContent = 'Đang tạo cuộc họp...';
    const status = document.createElement('p');
    status.className = 'ai-chat-confirm-result';
    status.setAttribute('role', 'status');
    card.appendChild(status);

    try {
        const [year, month, day] = String(meeting.booking_date).split('-').map(Number);
        const [hour, minute] = String(meeting.start_time).split(':').map(Number);
        const start = new Date(year, month - 1, day, hour, minute);
        const end = new Date(start.getTime() + Number(meeting.duration_minutes) * 60000);
        const toLocalDateTime = value => [
            `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`,
            `${String(value.getHours()).padStart(2, '0')}:${String(value.getMinutes()).padStart(2, '0')}:00`,
        ].join('T');
        const response = await fetchAPI(`${API_BASE}/v1/meetings/book`, {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${getAuthToken()}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                title: meeting.title,
                meeting_type: 'offline',
                room_id: meeting.room_id,
                start_time: toLocalDateTime(start),
                end_time: toLocalDateTime(end),
                participant_ids: participantIds,
                equipments,
            }),
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(result?.detail || 'Không thể tạo cuộc họp.');
        }
        status.textContent = participantIds.length
            ? 'Đã tạo cuộc họp và gửi lời mời tham dự.'
            : 'Đã tạo cuộc họp.';
        button.textContent = 'Đã tạo cuộc họp';
    } catch (error) {
        status.classList.add('is-error');
        status.textContent = error.message || 'Không thể tạo cuộc họp.';
        button.textContent = 'Thử tạo lại';
        button.disabled = false;
    }
}

async function confirmAiChatBooking(slots, button) {
    const card = button.closest('.ai-chat-preview');
    if (!card || button.disabled) return;
    button.disabled = true;
    button.textContent = 'Đang xác nhận...';
    const status = document.createElement('p');
    status.className = 'ai-chat-confirm-result';
    status.setAttribute('role', 'status');
    card.appendChild(status);

    try {
        const meetings = await chatApiRequest('/confirm-booking', {
            method: 'POST',
            body: JSON.stringify({ slots, participant_ids: [] }),
        });
        const meetingCount = Array.isArray(meetings) ? meetings.length : 0;
        status.textContent = meetingCount
            ? `Đã xác nhận và tạo ${meetingCount} cuộc họp.`
            : 'Đã xác nhận đặt phòng.';
        button.textContent = 'Đã xác nhận';
    } catch (error) {
        status.classList.add('is-error');
        status.textContent = error.message || 'Không thể xác nhận đặt phòng.';
        button.textContent = 'Thử xác nhận lại';
        button.disabled = false;
    }
}

function formatChatDate(value) {
    if (!value) return '—';
    const date = new Date(`${value}T00:00:00`);
    return Number.isNaN(date.getTime())
        ? value
        : date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function formatChatTimestamp(value, includeTime = false) {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleString('vi-VN', includeTime
        ? { hour: '2-digit', minute: '2-digit' }
        : { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
}

function scrollAiChatToLatest() {
    const container = document.getElementById('ai-chat-messages');
    if (container) container.scrollTop = container.scrollHeight;
}

function setAiChatStatus(message) {
    const status = document.getElementById('ai-chat-status');
    if (status) status.textContent = message || '';
}

function switchReportTab(tabName, trigger) {
    const isCancellationTab = tabName === 'cancellations';
    if (isCancellationTab && !isCurrentUserAdmin()) return;

    const usageTab = document.getElementById('report-tab-usage');
    const cancellationTab = document.getElementById('report-tab-cancel');
    const usagePanel = document.getElementById('reportUsagePanel');
    const cancellationPanel = document.getElementById('reportCancellationPanel');
    const activeTab = trigger || (isCancellationTab ? cancellationTab : usageTab);
    [usageTab, cancellationTab].forEach(tab => {
        if (tab) {
            const isActive = tab === activeTab;
            tab.setAttribute('aria-selected', String(isActive));
            tab.classList.toggle('active', isActive);
        }
    });
    if (usagePanel) {
        usagePanel.hidden = isCancellationTab;
        usagePanel.classList.toggle('d-none', isCancellationTab);
        usagePanel.classList.toggle('active', !isCancellationTab);
    }
    if (cancellationPanel) {
        cancellationPanel.hidden = !isCancellationTab;
        cancellationPanel.classList.toggle('d-none', !isCancellationTab);
        cancellationPanel.classList.toggle('active', isCancellationTab);
    }

    if (isCancellationTab) loadCancelReportData();
    else loadUsageReportData();
}