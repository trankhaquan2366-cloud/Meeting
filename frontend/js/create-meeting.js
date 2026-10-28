/* Create Meeting flow — meeting-first, resources second */

const CM_WEEKDAYS = ['Chủ nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'];
const CM_PREVIEW = new URLSearchParams(location.search).get('preview') === 'meeting';
const CM_API_V1 = `${API_BASE.replace(/\/$/, '')}/v1`;
const CM_ICONS = {
    file: '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><path d="M14 2v6h6"/>',
    calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
    building: '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4"/>',
    repeat: '<path d="m17 2 4 4-4 4M3 11v-1a4 4 0 0 1 4-4h14M7 22l-4-4 4-4M21 13v1a4 4 0 0 1-4 4H3"/>',
    check: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/>',
    alert: '<circle cx="12" cy="12" r="10"/><path d="M12 8v4m0 4h.01"/>',
    globe: '<circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10Z"/>',
    link: '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
};

const cmState = {
    mode: 'offline',
    attendees: [],
    selectedRoom: null,
    roomsResult: [],
    requiredAmenities: [],
    roomSelectionExpanded: false,
    roomSearchVersion: 0,
    hasRoomSearch: false,
    searching: false,
    borrowQty: {},
    equipment: [],
    equipmentLoadError: '',
    equipmentAvailabilityTimer: null,
    equipmentAvailabilityVersion: 0,
    users: [],
    departments: [],
    projectGroups: [],
    currentUser: null,
    suggestIndex: -1,
    userSearchTimer: null,
    userSearchVersion: 0,
    userSearchController: null,
    selectingAllAttendees: false,
    selectAllVersion: 0,
    selectAllController: null,
    submitting: false,
    organizerParticipates: true,
    apiError: '',
    suggestedRooms: [],
    roomSearchTimer: null,
};

function cmEl(id) {
    return document.getElementById(id);
}

function cmIcon(name, className = '') {
    const paths = CM_ICONS[name];
    if (!paths) throw new Error(`Biểu tượng cuộc họp không hợp lệ: ${name}`);
    const classes = className ? ` class="${className}"` : '';
    return `<svg${classes} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${paths}</svg>`;
}

function cmInitials(name) {
    const parts = String(name || '?').trim().split(/\s+/);
    return ((parts[0] || '?')[0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();
}

function cmParseAmenities(room) {
    let list = room?.amenities || [];
    if (typeof list === 'string') {
        try { list = JSON.parse(list); }
        catch (e) { list = list.split(',').map(s => s.trim()).filter(Boolean); }
    }
    return Array.isArray(list) ? list : [];
}

function cmNormalizeAmenity(value) {
    return String(value || '').trim().replace(/\s+/g, ' ').toLocaleLowerCase();
}

function cmCapacityNumber(room) {
    const n = parseInt(room?.capacity, 10);
    return Number.isFinite(n) ? n : 8;
}

function cmNormalizeUserKey(user) {
    if (!user) return '';
    const id = user.id ?? user.user_id;
    const email = String(user.email || '').trim().toLowerCase();
    const name = String(user.full_name || user.name || '').trim().toLowerCase();
    if (id !== undefined && id !== null && id !== '') return `id:${String(id)}`;
    if (email) return `email:${email}`;
    if (name) return `name:${name}`;
    return '';
}

function cmCurrentOrganizer() {
    if (cmState.currentUser) return cmState.currentUser;
    const storedName = String(localStorage.getItem('user_name') || '').trim();
    const storedEmail = String(localStorage.getItem('user_email') || '').trim().toLowerCase();
    const storedId = String(localStorage.getItem('user_id') || '').trim();
    const users = Array.isArray(cmState.users) ? cmState.users : [];

    const match = users.find(user => {
        const email = String(user.email || '').trim().toLowerCase();
        const fullName = String(user.full_name || user.name || '').trim().toLowerCase();
        const id = String(user.id ?? user.user_id ?? '').trim();
        return (storedId && id && id === storedId)
            || (storedEmail && email && email === storedEmail)
            || (storedName && fullName && fullName === storedName.trim().toLowerCase());
    });
    if (match) return match;
    if (storedName || storedEmail || storedId) {
        return {
            id: storedId || 'current-user',
            user_id: storedId || 'current-user',
            full_name: storedName || 'Current User',
            email: storedEmail || '',
            name: storedName || 'Current User',
        };
    }

    return null;
}

function cmIsOrganizerUser(user) {
    if (!user) return false;
    const organizer = cmCurrentOrganizer();
    if (!organizer) return false;
    const userId = String(user.id ?? user.user_id ?? '');
    const organizerId = String(organizer.id ?? organizer.user_id ?? '');
    if (userId && organizerId && userId === organizerId) return true;

    const userName = String(user.full_name || user.name || '').trim().toLowerCase();
    const organizerName = String(organizer.full_name || organizer.name || '').trim().toLowerCase();
    const userEmail = String(user.email || '').trim().toLowerCase();
    const organizerEmail = String(organizer.email || '').trim().toLowerCase();
    return (!!userName && !!organizerName && userName === organizerName)
        || (!!userEmail && !!organizerEmail && userEmail === organizerEmail);
}

function cmUniqueValidParticipants() {
    const organizer = cmCurrentOrganizer();
    const seen = new Map();
    const normalized = cmState.attendees.filter(user => {
        const candidateKey = cmNormalizeUserKey(user);
        if (!candidateKey) return false;
        if (organizer && cmIsOrganizerUser(user)) return false;
        if (seen.has(candidateKey)) return false;
        seen.set(candidateKey, true);
        return true;
    });
    cmState.attendees = normalized;
    return normalized;
}

function cmAttendeeCount() {
    return cmUniqueValidParticipants().length;
}

function cmNeededSeats() {
    const externalGuests = Math.max(0, Number.parseInt(cmEl('cmExternalGuestCount')?.value || '0', 10) || 0);
    return cmAttendeeCount() + externalGuests + Number(cmOrganizerParticipates());
}

function cmOrganizerParticipates() {
    return cmEl('cmOrganizerParticipates')?.checked ?? cmState.organizerParticipates;
}

function cmGetTimes() {
    const date = cmEl('cmDate')?.value;
    const start = cmEl('start_time')?.value;
    const end = cmEl('end_time')?.value;
    return { date, start, end };
}

function cmDateTimeValue(date, time) {
    const value = new Date(`${date}T${time}:00`);
    const dateValue = typeof formatDateInput === 'function'
        ? formatDateInput(value)
        : `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`;
    return `${dateValue}T${time}:00`;
}

function cmGetDateTimeRange() {
    const { date, start, end } = cmGetTimes();
    return {
        startTime: cmDateTimeValue(date, start),
        endTime: cmDateTimeValue(date, end),
    };
}

function cmFormatViDate(iso) {
    if (!iso) return 'Chưa chọn ngày';
    const [y, m, d] = iso.split('-');
    return `${d}/${m}/${y}`;
}

function cmRecurrenceLabel() {
    const type = cmEl('cmRecurrence')?.value || 'none';
    if (type === 'none') return 'Không lặp';
    const extra = cmEl('cmRecurrenceNote')?.textContent || '';
    return extra || (type === 'weekly' ? 'Hàng tuần' : 'Hàng tháng');
}

function frequentIds() {
    try {
        return JSON.parse(localStorage.getItem('cm_frequent_ids') || '[]');
    } catch (e) {
        return [];
    }
}

function rememberAttendees(ids) {
    const prev = frequentIds();
    const next = [...ids, ...prev.filter(id => !ids.includes(id))].slice(0, 20);
    localStorage.setItem('cm_frequent_ids', JSON.stringify(next));
}

function openCreateMeeting(options = {}) {
    const overlay = cmEl('createMeetingModal');
    if (!overlay) return;

    resetCreateMeeting();
    const dialog = cmEl('cmDialog');
    dialog?.classList.remove('is-success');
    if (dialog) dialog.scrollTop = 0;
    overlay.classList.add('is-open');
    overlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';

    const title = cmEl('cmTitle');
    if (title) setTimeout(() => title.focus(), 30);

    loadCreateMeetingData().then(async () => {
        if (options.roomId) {
            await searchMatchingRooms();
            const match = cmState.roomsResult.find(item => String(item.room.id) === String(options.roomId));
            if (match) selectCreateMeetingRoom(match.room, { silent: true });
        }
        updateCreateMeetingSummary();
    });
}

function closeCreateMeeting() {
    const overlay = cmEl('createMeetingModal');
    if (!overlay) return;
    overlay.classList.remove('is-open');
    overlay.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    const dialog = cmEl('cmDialog');
    dialog?.classList.remove('is-success');
    cmState.userSearchVersion += 1;
    cmState.userSearchController?.abort();
    if (cmState.userSearchTimer) clearTimeout(cmState.userSearchTimer);
    cmState.userSearchTimer = null;
    cmState.selectAllVersion += 1;
    cmState.selectAllController?.abort();
    cmState.selectAllController = null;
    cmState.selectingAllAttendees = false;
    cmState.equipmentAvailabilityVersion += 1;
    if (cmState.equipmentAvailabilityTimer) {
        clearTimeout(cmState.equipmentAvailabilityTimer);
    }
    cmState.equipmentAvailabilityTimer = null;
    cmSetParticipantSearchDisabled(false);
}

function resetCreateMeeting() {
    cmState.mode = 'offline';
    cmState.attendees = [];
    cmState.selectedRoom = null;
    cmState.roomsResult = [];
    cmState.requiredAmenities = [];
    cmState.roomSelectionExpanded = false;
    cmState.roomSearchVersion += 1;
    cmState.hasRoomSearch = false;
    cmState.searching = false;
    cmState.borrowQty = {};
    cmState.equipmentLoadError = '';
    cmState.equipmentAvailabilityVersion += 1;
    if (cmState.equipmentAvailabilityTimer) {
        clearTimeout(cmState.equipmentAvailabilityTimer);
    }
    cmState.equipmentAvailabilityTimer = null;
    cmState.suggestIndex = -1;
    cmState.submitting = false;
    cmState.organizerParticipates = true;
    cmState.apiError = '';
    cmState.suggestedRooms = [];
    cmState.userSearchVersion += 1;
    cmState.userSearchController?.abort();
    cmState.selectAllVersion += 1;
    cmState.selectAllController?.abort();
    cmState.selectAllController = null;
    cmState.selectingAllAttendees = false;
    cmSetParticipantSearchDisabled(false);
    if (cmState.userSearchTimer) clearTimeout(cmState.userSearchTimer);
    cmState.userSearchTimer = null;
    if (cmState.roomSearchTimer) clearTimeout(cmState.roomSearchTimer);
    cmState.roomSearchTimer = null;
    clearValidationFeedback();

    const formIds = ['cmTitle', 'cmDescription', 'cmMeetingLink', 'cmAttendeeSearch'];
    formIds.forEach(id => {
        const el = cmEl(id);
        if (el) {
            el.value = '';
            el.classList.remove('is-invalid');
        }
    });
    const organizerParticipates = cmEl('cmOrganizerParticipates');
    if (organizerParticipates) organizerParticipates.checked = true;
    const externalGuests = cmEl('cmExternalGuestCount');
    if (externalGuests) externalGuests.value = '0';
    ['cmDepartmentFilter', 'cmProjectGroupFilter', 'cmPositionFilter'].forEach(id => {
        const filter = cmEl(id);
        if (filter) filter.value = '';
    });
    const attendeeStatus = cmEl('cmAttendeeSearchStatus');
    if (attendeeStatus) attendeeStatus.textContent = '';
    const directoryError = cmEl('cmDirectoryError');
    if (directoryError) {
        directoryError.textContent = '';
        directoryError.hidden = true;
        directoryError.classList.remove('is-open');
    }
    const attendeeResults = cmEl('cmAttendeeSuggest');
    if (attendeeResults) {
        attendeeResults.innerHTML = '';
        attendeeResults.classList.remove('is-open');
    }
    setCreateMeetingMode('offline');
    setRecurrence('none');
    setDefaultCreateMeetingTimes();
    renderAttendeeChips();
    renderFixedAmenityOptions();
    renderRoomResults();
    renderEquipment();
    const noticeEl = cmEl('cmSkippedNotice');
    if (noticeEl) {
        noticeEl.style.display = 'none';
        noticeEl.innerHTML = '';
    }
    updateEquipmentSectionVisibility();
    hideCmAlerts();
    updateCreateMeetingSummary();
}

function setDefaultCreateMeetingTimes() {
    const now = new Date();
    const startDate = new Date(now);
    startDate.setSeconds(0, 0);
    if (now.getMinutes() < 30) startDate.setMinutes(30);
    else startDate.setHours(startDate.getHours() + 1, 0, 0, 0);
    const endDate = new Date(startDate);
    endDate.setHours(endDate.getHours() + 1);
    if (startDate.toDateString() !== endDate.toDateString()) {
        startDate.setDate(startDate.getDate() + 1);
        startDate.setHours(0, 0, 0, 0);
        endDate.setTime(startDate.getTime());
        endDate.setHours(endDate.getHours() + 1);
    }
    const dateVal = typeof formatDateInput === 'function'
        ? formatDateInput(startDate)
        : startDate.toISOString().slice(0, 10);
    const startVal = `${String(startDate.getHours()).padStart(2, '0')}:${String(startDate.getMinutes()).padStart(2, '0')}`;
    const endVal = `${String(endDate.getHours()).padStart(2, '0')}:${String(endDate.getMinutes()).padStart(2, '0')}`;

    const dateEl = cmEl('cmDate');
    const startEl = cmEl('start_time');
    const endEl = cmEl('end_time');
    if (dateEl) dateEl.value = dateVal;
    if (startEl) startEl.value = startVal;
    if (endEl) endEl.value = endVal;
}

function populateParticipantFilter(id, options, emptyLabel) {
    const select = cmEl(id);
    if (!select) return;
    select.innerHTML = `<option value="">${escapeHtml(emptyLabel)}</option>` + options
        .filter(option => option.code)
        .map(option =>
        `<option value="${escapeHtml(option.code)}">${escapeHtml(option.name)}</option>`
    ).join('');
}

async function loadParticipantDirectories() {
    const token = typeof getAuthToken === 'function' ? getAuthToken() : '';
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const errors = [];

    try {
        const response = await fetchAPI(`${API_BASE}/users/me`, { headers });
        if (!response.ok) throw new Error(`Thông tin người dùng (${response.status})`);
        cmState.currentUser = await response.json();
        renderQuickInviteChips();
    } catch (error) {
        errors.push(error.message);
    }

    try {
        const response = await fetchAPI(`${CM_API_V1}/departments`, { headers });
        if (!response.ok) throw new Error(`Phòng ban (${response.status})`);
        cmState.departments = await response.json();
        populateParticipantFilter('cmDepartmentFilter', cmState.departments, 'Tất cả phòng ban');
    } catch (error) {
        errors.push(error.message);
    }

    try {
        const response = await fetchAPI(`${CM_API_V1}/project-groups`, { headers });
        if (!response.ok) throw new Error(`Nhóm dự án (${response.status})`);
        cmState.projectGroups = await response.json();
        populateParticipantFilter('cmProjectGroupFilter', cmState.projectGroups, 'Tất cả nhóm dự án');
    } catch (error) {
        errors.push(error.message);
    }

    const errorBox = cmEl('cmDirectoryError');
    if (errorBox) {
        errorBox.hidden = errors.length === 0;
        errorBox.classList.toggle('is-open', errors.length > 0);
        errorBox.textContent = errors.length
            ? `Không tải được danh mục bộ lọc: ${errors.join(', ')}.`
            : '';
    }
}

function renderQuickInviteChips() {
    const container = cmEl('cmQuickInviteChips');
    if (!container) return;

    const department = cmState.currentUser?.department;
    const projectGroups = cmState.currentUser?.project_groups || [];
    const chips = [];
    if (department?.code) {
        chips.push({
            kind: 'department',
            code: department.code,
            label: `+ Mời toàn bộ Phòng ${department.name}`,
        });
    }
    projectGroups.forEach(group => {
        if (group.code) {
            chips.push({
                kind: 'group',
                code: group.code,
                label: `+ Mời Nhóm ${group.name}`,
            });
        }
    });

    container.replaceChildren();
    chips.forEach(chip => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'cm-quick-invite-chip';
        button.textContent = chip.label;
        button.addEventListener('click', () => inviteQuickGroup(chip.kind, chip.code));
        container.appendChild(button);
    });
    container.hidden = chips.length === 0;
}

async function inviteQuickGroup(kind, code) {
    const departmentFilter = cmEl('cmDepartmentFilter');
    const groupFilter = cmEl('cmProjectGroupFilter');
    if (!departmentFilter || !groupFilter) return;

    departmentFilter.value = kind === 'department' ? code : '';
    groupFilter.value = kind === 'group' ? code : '';
    const positionFilter = cmEl('cmPositionFilter');
    if (positionFilter) positionFilter.value = '';
    const search = cmEl('cmAttendeeSearch');
    if (search) search.value = '';
    await selectAllFilteredAttendees();
}

async function loadCreateMeetingData() {
    await loadParticipantDirectories();
    await searchCreateMeetingParticipants();

    try {
        if (typeof allRooms !== 'undefined' && !allRooms.length) {
            const res = await fetchAPI(`${API_BASE}/rooms/`);
            if (!res.ok) throw new Error(`Không tải được phòng (${res.status}).`);
            allRooms = await res.json();
        }
        renderFixedAmenityOptions();
    } catch (e) {
        console.warn('Không tải được tiện nghi phòng', e);
        const options = cmEl('cmFixedAmenityOptions');
        if (options) options.innerHTML = '<p class="cm-help">Không tải được tiện nghi phòng. Vui lòng thử tải lại.</p>';
    }

    updateCapacityHint();
    await refreshEquipmentAvailability();
}

function scheduleEquipmentAvailabilityRefresh() {
    if (cmState.equipmentAvailabilityTimer) {
        clearTimeout(cmState.equipmentAvailabilityTimer);
    }
    cmState.equipmentAvailabilityVersion += 1;
    cmState.equipmentAvailabilityTimer = setTimeout(() => {
        cmState.equipmentAvailabilityTimer = null;
        refreshEquipmentAvailability();
    }, 300);
}

async function refreshEquipmentAvailability() {
    const { date, start, end } = cmGetTimes();
    const box = cmEl('cmBorrowEquipment');
    if (!date || !start || !end || end <= start) {
        cmState.equipmentLoadError = 'Chọn khung thời gian hợp lệ để kiểm tra tồn kho thiết bị.';
        cmState.equipment = [];
        renderEquipment();
        return;
    }

    const version = ++cmState.equipmentAvailabilityVersion;
    const { startTime, endTime } = cmGetDateTimeRange();
    const params = new URLSearchParams({ start_time: startTime, end_time: endTime });
    const token = typeof getAuthToken === 'function' ? getAuthToken() : '';
    try {
        const response = await fetchAPI(`${API_BASE}/equipments/availability?${params}`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!response.ok) {
            throw new Error(`Không thể kiểm tra tồn kho thiết bị (HTTP ${response.status}).`);
        }
        const equipment = await response.json();
        if (version !== cmState.equipmentAvailabilityVersion) return;

        const previous = new Map(cmState.equipment.map(item => [String(item.id), item]));
        const reduced = [];
        cmState.equipment = equipment
            .filter(item => item.is_active !== false)
            .map(item => {
                const available = Number(item.available_quantity ?? item.available_qty ?? 0);
                const total = Number(item.total_quantity ?? item.total_qty ?? 0);
                const normalized = {
                    ...previous.get(String(item.id)),
                    ...item,
                    total_qty: total,
                    total_quantity: total,
                    available_qty: available,
                    available_quantity: available,
                };
                const requested = getBorrowQtyValue(item.id);
                if (requested > available) {
                    setBorrowQtyValue(item.id, available);
                    reduced.push(`${normalized.name}: ${requested} → ${available}`);
                }
                return normalized;
            });
        cmState.equipmentLoadError = '';
        renderEquipment();
        updateCreateMeetingSummary();
        if (reduced.length && typeof showAppToast === 'function') {
            showAppToast(
                `Tồn kho đã thay đổi; số lượng được điều chỉnh: ${reduced.join(', ')}.`,
                'error'
            );
        }
    } catch (error) {
        if (version !== cmState.equipmentAvailabilityVersion) return;
        cmState.equipmentLoadError = error.message || 'Không thể tải tồn kho thiết bị.';
        console.error('Không thể cập nhật tồn kho thiết bị theo khung giờ:', error);
        if (!cmState.equipment.length && box) {
            box.innerHTML = `<p class="cm-alert cm-alert-error is-open">${escapeHtml(cmState.equipmentLoadError)}</p>`;
        } else {
            renderEquipment();
        }
    }
}

function canSearchRoomsForMeeting() {
    if (cmState.mode !== 'offline') return false;
    const { date, start, end } = cmGetTimes();
    if (!date || !start || !end) return false;
    if (end <= start) return false;
    if (cmTimeIsInPast(date, start)) return false;
    return cmNeededSeats() > 0;
}

function invalidateRoomResults() {
    cmState.roomSearchVersion += 1;
    cmState.selectedRoom = null;
    cmState.roomSelectionExpanded = false;
    if (cmState.roomSearchTimer) clearTimeout(cmState.roomSearchTimer);
    cmState.roomSearchTimer = null;
    cmState.searching = false;
    cmState.roomsResult = [];
    cmState.hasRoomSearch = false;
    cmState.suggestedRooms = [];
    clearValidationError('cmRoomError');
    renderRoomResults();
    updateEquipmentSectionVisibility();
    updateCreateMeetingSummary();
}

function setCreateMeetingMode(mode) {
    cmState.mode = mode;
    invalidateRoomResults();
    if (mode === 'online') {
        cmState.requiredAmenities = [];
        renderFixedAmenityOptions();
    }

    const onlineBtn = cmEl('cmModeOnline');
    const offlineBtn = cmEl('cmModeOffline');
    if (onlineBtn) onlineBtn.setAttribute('aria-pressed', String(mode === 'online'));
    if (offlineBtn) offlineBtn.setAttribute('aria-pressed', String(mode === 'offline'));

    const onlineBox = cmEl('cmOnlineBox');
    const roomSection = cmEl('cmResources');
    if (onlineBox) onlineBox.classList.toggle('is-open', mode === 'online');
    if (roomSection) roomSection.classList.toggle('is-open', mode === 'offline');
    onlineBox?.setAttribute('aria-hidden', String(mode !== 'online'));
    roomSection?.setAttribute('aria-hidden', String(mode !== 'offline'));

    const roomSearchBtn = document.getElementById('cmSearchRoomsBtn');
    if (roomSearchBtn) roomSearchBtn.disabled = mode !== 'offline';

    const onlineLink = cmEl('cmMeetingLink');
    if (mode === 'online') {
        if (onlineLink) onlineLink.required = true;
    } else if (onlineLink) {
        onlineLink.value = '';
        onlineLink.required = false;
        clearValidationError('cmMeetingLinkError');
    }

    renderRoomResults();
    updateEquipmentSectionVisibility();
    updateCreateMeetingSummary();
}

function renderFixedAmenityOptions() {
    const box = cmEl('cmFixedAmenityOptions');
    if (!box) return;

    const amenities = new Map();
    (typeof allRooms !== 'undefined' ? allRooms : [])
        .filter(room => room.is_active !== false)
        .forEach(room => cmParseAmenities(room).forEach(amenity => {
            const value = String(amenity || '').trim();
            const key = cmNormalizeAmenity(value);
            if (key && !amenities.has(key)) amenities.set(key, value);
        }));

    if (!amenities.size) {
        box.innerHTML = '<p class="cm-help">Chưa có tiện nghi cố định được khai báo cho phòng.</p>';
        return;
    }

    box.innerHTML = [...amenities.values()].sort((a, b) => a.localeCompare(b, 'vi')).map(amenity => `
        <label class="cm-amenity-choice">
            <input type="checkbox" value="${escapeHtml(amenity)}" ${cmState.requiredAmenities.some(item => cmNormalizeAmenity(item) === cmNormalizeAmenity(amenity)) ? 'checked' : ''}>
            <span>${escapeHtml(amenity)}</span>
        </label>
    `).join('');
}

function updateEquipmentSectionVisibility() {
    const section = cmEl('cmEquipmentSection');
    if (section) section.hidden = cmState.mode !== 'offline' || !cmState.selectedRoom;
}

function setRecurrence(type) {
    const select = cmEl('cmRecurrence');
    if (select && type) select.value = type;
    const value = select?.value || 'none';
    const extra = cmEl('cmRecurringExtra');
    extra?.classList.toggle('is-open', value !== 'none');
    cmEl('cmRecNone')?.setAttribute('aria-pressed', String(value === 'none'));
    cmEl('cmRecWeekly')?.setAttribute('aria-pressed', String(value === 'weekly'));
    cmEl('cmRecMonthly')?.setAttribute('aria-pressed', String(value === 'monthly'));
    updateRecurrenceNote();
    updateCreateMeetingSummary();
    scheduleRoomSearchRefresh();
}

function updateRecurrenceNote() {
    const type = cmEl('cmRecurrence')?.value || 'none';
    const note = cmEl('cmRecurrenceNote');
    const until = cmEl('cmRecurrenceUntil')?.value;
    const { date } = cmGetTimes();
    if (!note) return;
    if (type === 'none') {
        note.textContent = '';
        return;
    }
    const dt = date ? new Date(`${date}T00:00:00`) : new Date();
    const weekday = CM_WEEKDAYS[dt.getDay()];
    const day = dt.getDate();
    const untilText = until ? `, kết thúc ${cmFormatViDate(until)}` : '';
    note.textContent = type === 'weekly'
        ? `Lặp vào ${weekday} hàng tuần${untilText}`
        : `Lặp hàng tháng vào ngày ${day}${untilText}`;
}

function renderAttendeeChips() {
    const normalized = cmUniqueValidParticipants();
    const wrap = cmEl('cmAttendeeChips');
    const count = cmEl('cmAttendeeCount');
    if (count) count.textContent = `${normalized.length} người tham dự`;
    if (!wrap) return;
    if (!normalized.length) {
        wrap.innerHTML = '<p class="cm-help">Chưa có người tham dự. Bạn vẫn có thể tạo cuộc họp với tư cách người tổ chức.</p>';
        updateCapacityHint();
        updateCreateMeetingSummary();
        return;
    }
    wrap.innerHTML = normalized.map(u => `
        <span class="cm-chip">
            <span class="cm-avatar" aria-hidden="true">${escapeHtml(cmInitials(u.full_name || u.email))}</span>
            ${escapeHtml(u.full_name || u.email)}
            <button type="button" aria-label="Xóa ${escapeHtml(u.full_name || u.email)}" onclick="removeCreateMeetingAttendee(${u.id})">×</button>
        </span>
    `).join('');
    updateCapacityHint();
    updateCreateMeetingSummary();
}

function scheduleRoomSearchRefresh() {
    invalidateRoomResults();
    if (!canSearchRoomsForMeeting()) {
        return;
    }

    cmState.roomSearchTimer = setTimeout(() => {
        cmState.roomSearchTimer = null;
        if (canSearchRoomsForMeeting()) {
            searchMatchingRooms();
        }
    }, 250);
}

function onFixedAmenityChange(event) {
    if (!event.target.matches('#cmFixedAmenityOptions input[type="checkbox"]')) return;
    cmState.requiredAmenities = [...cmEl('cmFixedAmenityOptions').querySelectorAll('input:checked')]
        .map(input => input.value);
    scheduleRoomSearchRefresh();
}

function addCreateMeetingAttendee(user) {
    if (!user || cmIsOrganizerUser(user)) return;
    const key = cmNormalizeUserKey(user);
    if (!key || cmState.attendees.some(a => cmNormalizeUserKey(a) === key)) return;
    cmState.attendees.push(user);
    renderAttendeeChips();
    scheduleRoomSearchRefresh();
}

function removeCreateMeetingAttendee(id) {
    cmState.attendees = cmState.attendees.filter(a => String(a.id) !== String(id));
    renderAttendeeChips();
    renderAttendeeResults();
    scheduleRoomSearchRefresh();
}

function renderAttendeeResults() {
    const list = cmEl('cmAttendeeSuggest');
    const status = cmEl('cmAttendeeSearchStatus');
    if (!list) return;
    const organizer = cmCurrentOrganizer();
    const selected = new Set(cmState.attendees.map(a => cmNormalizeUserKey(a)));
    const matches = cmState.users.filter(user => !organizer || !cmIsOrganizerUser(user));
    if (!matches.length) {
        list.innerHTML = '';
        closeAttendeeSuggest();
        if (status && !status.textContent) status.textContent = 'Không tìm thấy người phù hợp.';
        return;
    }
    cmState.suggestIndex = -1;
    list.innerHTML = matches.map((u, i) => `
        <li>
            <button type="button" data-index="${i}" ${selected.has(cmNormalizeUserKey(u)) ? 'disabled aria-disabled="true"' : ''}
                onclick="pickCreateMeetingAttendee(${u.id})">
                <span class="cm-avatar" aria-hidden="true">${escapeHtml(cmInitials(u.full_name || u.email))}</span>
                <span class="cm-suggest-meta">
                    <strong>${escapeHtml(u.full_name || 'Người dùng')}</strong>
                    <span>${escapeHtml(u.email || '')}${u.external_id ? ` · ${escapeHtml(u.external_id)}` : ''}</span>
                    <span>${escapeHtml(u.position || '')}${u.department?.name ? ` · ${escapeHtml(u.department.name)}` : ''}</span>
                </span>
                ${selected.has(cmNormalizeUserKey(u)) ? '<span class="cm-result-selected">Đã chọn</span>' : ''}
            </button>
        </li>
    `).join('');
    list.classList.add('is-open');
    if (status) status.textContent = `${matches.length} kết quả${matches.length === 100 ? ' (tối đa 100 kết quả)' : ''}`;
}

async function searchCreateMeetingParticipants() {
    if (cmState.selectingAllAttendees) return;
    const status = cmEl('cmAttendeeSearchStatus');
    const list = cmEl('cmAttendeeSuggest');
    const version = ++cmState.userSearchVersion;
    cmState.userSearchController?.abort();
    const controller = new AbortController();
    cmState.userSearchController = controller;
    const params = createParticipantSearchParams(100);
    if (status) status.textContent = 'Đang tìm kiếm…';
    if (list) {
        list.innerHTML = '';
        list.classList.remove('is-open');
    }

    try {
        const token = typeof getAuthToken === 'function' ? getAuthToken() : '';
        const response = await fetchAPI(`${CM_API_V1}/users/search?${params}`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            signal: controller.signal,
        });
        if (!response.ok) throw new Error(`Không thể tìm người tham dự (${response.status}).`);
        const users = await response.json();
        if (version !== cmState.userSearchVersion) return;
        cmState.users = Array.isArray(users) ? users : [];
        if (status) status.textContent = '';
        renderAttendeeResults();
    } catch (error) {
        if (error.name === 'AbortError' || version !== cmState.userSearchVersion) return;
        cmState.users = [];
        if (status) status.textContent = error.message || 'Không thể tìm người tham dự.';
        if (list) {
            list.innerHTML = '';
            list.classList.remove('is-open');
        }
    }
}

function createParticipantSearchParams(limit, offset = 0) {
    const params = new URLSearchParams({ limit: String(limit) });
    const departmentCode = cmEl('cmDepartmentFilter')?.value;
    const groupCode = cmEl('cmProjectGroupFilter')?.value;
    const position = cmEl('cmPositionFilter')?.value;
    const keyword = cmEl('cmAttendeeSearch')?.value.trim();
    if (departmentCode) params.set('department_code', departmentCode);
    if (groupCode) params.set('group_code', groupCode);
    if (position) params.set('position', position);
    if (keyword) params.set('keyword', keyword);
    if (offset) params.set('offset', String(offset));
    return params;
}

function cmSetParticipantSearchDisabled(disabled) {
    ['cmDepartmentFilter', 'cmProjectGroupFilter', 'cmPositionFilter', 'cmAttendeeSearch', 'cmSelectAllAttendees']
        .forEach(id => {
            const control = cmEl(id);
            if (control) control.disabled = disabled;
        });
    cmEl('cmQuickInviteChips')
        ?.querySelectorAll('button')
        .forEach(button => { button.disabled = disabled; });
}

function scheduleParticipantSearch(delay = 0) {
    if (cmState.userSearchTimer) clearTimeout(cmState.userSearchTimer);
    cmState.userSearchTimer = setTimeout(() => {
        cmState.userSearchTimer = null;
        searchCreateMeetingParticipants();
    }, delay);
}

function onAttendeeSearchInput() {
    scheduleParticipantSearch(300);
}

async function selectAllFilteredAttendees() {
    const status = cmEl('cmAttendeeSearchStatus');
    const runVersion = ++cmState.selectAllVersion;
    const controller = new AbortController();
    cmState.selectAllController = controller;
    cmState.userSearchVersion += 1;
    cmState.userSearchController?.abort();
    if (cmState.userSearchTimer) clearTimeout(cmState.userSearchTimer);
    cmState.userSearchTimer = null;
    cmState.selectingAllAttendees = true;
    cmSetParticipantSearchDisabled(true);
    if (status) status.textContent = 'Đang lấy tất cả người phù hợp…';

    try {
        const token = typeof getAuthToken === 'function' ? getAuthToken() : '';
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        const allMatches = [];
        const pageSize = 500;
        for (let offset = 0; ; offset += pageSize) {
            const params = createParticipantSearchParams(pageSize, offset);
            const response = await fetchAPI(`${CM_API_V1}/users/search?${params}`, {
                headers,
                signal: controller.signal,
            });
            if (!response.ok) throw new Error(`Không thể tải toàn bộ kết quả (${response.status}).`);
            const page = await response.json();
            if (!Array.isArray(page)) throw new Error('API tìm người tham dự trả về dữ liệu không hợp lệ.');
            allMatches.push(...page);
            if (page.length < pageSize) break;
        }
        if (runVersion !== cmState.selectAllVersion) return;

        const organizer = cmCurrentOrganizer();
        const seen = new Set(cmState.attendees.map(user => cmNormalizeUserKey(user)));
        let added = 0;
        allMatches.forEach(user => {
            const key = cmNormalizeUserKey(user);
            if (!key || (organizer && cmIsOrganizerUser(user)) || seen.has(key)) return;
            seen.add(key);
            cmState.attendees.push(user);
            added += 1;
        });
        renderAttendeeChips();
        renderAttendeeResults();
        if (status) status.textContent = `Đã chọn thêm ${added} người trong toàn bộ kết quả lọc.`;
        scheduleRoomSearchRefresh();
    } catch (error) {
        if (error.name !== 'AbortError' && runVersion === cmState.selectAllVersion && status) {
            status.textContent = error.message || 'Không thể chọn tất cả người phù hợp.';
        }
    } finally {
        if (runVersion === cmState.selectAllVersion) {
            cmState.selectingAllAttendees = false;
            cmState.selectAllController = null;
            cmSetParticipantSearchDisabled(false);
        }
    }
}

function pickCreateMeetingAttendee(id) {
    const user = cmState.users.find(u => String(u.id) === String(id));
    if (user) addCreateMeetingAttendee(user);
    const input = cmEl('cmAttendeeSearch');
    if (input) input.value = '';
    closeAttendeeSuggest();
    scheduleParticipantSearch();
}

function closeAttendeeSuggest() {
    cmEl('cmAttendeeSuggest')?.classList.remove('is-open');
    cmState.suggestIndex = -1;
}

function handleAttendeeKeydown(event) {
    const list = cmEl('cmAttendeeSuggest');
    if (!list?.classList.contains('is-open')) return;
    const buttons = [...list.querySelectorAll('button')];
    if (event.key === 'ArrowDown') {
        event.preventDefault();
        cmState.suggestIndex = Math.min(cmState.suggestIndex + 1, buttons.length - 1);
    } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        cmState.suggestIndex = Math.max(cmState.suggestIndex - 1, 0);
    } else if (event.key === 'Enter' && cmState.suggestIndex >= 0) {
        event.preventDefault();
        buttons[cmState.suggestIndex]?.click();
        return;
    } else if (event.key === 'Escape') {
        closeAttendeeSuggest();
        return;
    }
    buttons.forEach((btn, i) => btn.classList.toggle('is-active', i === cmState.suggestIndex));
}

function updateCapacityHint() {
    const needed = cmNeededSeats();
    const label = cmEl('cmCapacityValue');
    if (label) label.textContent = `${needed} người`;
    const min = cmEl('cmCapacityMin');
    if (min) min.textContent = `Phòng tối thiểu: ${needed} chỗ`;
    const warning = cmEl('cmCapacityWarning');
    const capacity = cmState.selectedRoom ? cmCapacityNumber(cmState.selectedRoom) : null;
    const attendees = needed;
    if (warning) {
        const overCapacity = capacity !== null && attendees > capacity;
        warning.hidden = !overCapacity;
        warning.classList.toggle('is-open', overCapacity);
        warning.textContent = overCapacity
            ? `Đã chọn ${attendees} người tham dự, vượt sức chứa ${capacity} chỗ của phòng đang chọn.`
            : '';
    }
}

function hideCmAlerts() {
    ['cmRoomConflict', 'cmEquipConflict', 'cmFormError', 'cmApiError'].forEach(id => {
        cmEl(id)?.classList.remove('is-open');
    });
}

async function searchMatchingRooms() {
    if (cmState.mode !== 'offline') return;

    const results = cmEl('cmRoomResults');
    const { date, start, end } = cmGetTimes();
    if (!canSearchRoomsForMeeting()) {
        showFormError('Chọn ngày và khung giờ hợp lệ trước khi tìm phòng.');
        return;
    }
    const searchVersion = ++cmState.roomSearchVersion;
    const requiredAmenities = cmState.requiredAmenities.map(cmNormalizeAmenity);
    cmState.selectedRoom = null;
    cmState.roomSelectionExpanded = false;
    cmState.roomsResult = [];
    cmState.hasRoomSearch = true;
    cmState.searching = true;
    updateEquipmentSectionVisibility();
    if (results) {
        results.innerHTML = '<div class="cm-skeleton"></div><div class="cm-skeleton"></div>';
    }
    hideCmAlerts();

    const token = typeof getAuthToken === 'function' ? getAuthToken() : '';
    let availableRooms = [];
    try {
        const { startTime, endTime } = cmGetDateTimeRange();
        const params = new URLSearchParams({ start_time: startTime, end_time: endTime });
        const res = await fetchAPI(`${API_BASE}/rooms/available?${params}`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {}
        });
        if (!res.ok) throw new Error(`Room availability returned ${res.status}.`);
        availableRooms = await res.json();
    } catch (e) {
        console.warn('Không kiểm tra được phòng trống', e);
        showFormError('Không thể kiểm tra phòng trống lúc này. Vui lòng thử lại.');
    }
    if (searchVersion !== cmState.roomSearchVersion) return;

    const needed = cmNeededSeats();
    const mapped = availableRooms
        .filter(r => r.is_active !== false)
        .map(room => {
            const capacity = cmCapacityNumber(room);
            const available = room.is_available !== false;
            const fit = capacity >= needed;
            return { room, capacity, available, fit, score: available && fit ? capacity - needed : 999 };
        })
        .sort((a, b) => {
            if (a.available !== b.available) return a.available ? -1 : 1;
            if (a.fit !== b.fit) return a.fit ? -1 : 1;
            return a.score - b.score;
        });

    cmState.roomsResult = mapped.filter(item => {
        if (!item.available) return false;
        const roomAmenities = new Set(cmParseAmenities(item.room).map(cmNormalizeAmenity));
        return requiredAmenities.every(amenity => roomAmenities.has(amenity));
    });

    cmState.searching = false;
    renderRoomResults();
    updateCreateMeetingSummary();
}

function renderRoomResults() {
    const results = cmEl('cmRoomResults');
    if (!results) return;
    if (cmState.mode === 'online') {
        results.innerHTML = '<div class="cm-empty">Cuộc họp online không cần chọn phòng.</div>';
        return;
    }
    if (cmState.searching) return;
    if (!cmState.roomsResult.length) {
        results.innerHTML = `<div class="cm-empty">${cmState.hasRoomSearch ? 'Không tìm thấy phòng phù hợp với thời gian, sức chứa và tiện nghi đã chọn.' : 'Chọn điều kiện phòng rồi bấm “Tìm phòng phù hợp”.'}</div>`;
        return;
    }

    const selected = cmState.selectedRoom
        ? cmState.roomsResult.find(item => String(item.room.id) === String(cmState.selectedRoom.id))
        : null;
    if (selected && !cmState.roomSelectionExpanded) {
        const amenities = cmParseAmenities(selected.room);
        results.innerHTML = `
            <article class="cm-room-card cm-room-selected">
                <div class="cm-room-top">
                    <h3>${cmIcon('check', 'cm-inline-icon cm-room-check')} ${escapeHtml(selected.room.name)}</h3>
                    <span class="cm-badge ${selected.fit ? 'cm-badge-ok' : 'cm-badge-busy'}">
                        ${selected.fit ? 'Đã chọn · Trống' : 'Đã chọn · Quá sức chứa'}
                    </span>
                </div>
                <p class="cm-room-meta">${escapeHtml(selected.room.location || 'Chưa có vị trí')} · ${selected.capacity} chỗ · ${escapeHtml(cmGetTimes().start || '')}–${escapeHtml(cmGetTimes().end || '')}</p>
                <p class="cm-room-amenities">${amenities.length ? amenities.map(item => `<span class="cm-amenity-label">${cmIcon('check', 'cm-inline-icon')} ${escapeHtml(item)}</span>`).join('') : 'Chưa khai báo tiện nghi cố định'}</p>
                <div class="cm-room-actions"><button type="button" class="cm-btn cm-btn-secondary" onclick="changeCreateMeetingRoom()">Đổi phòng</button></div>
            </article>
        `;
        return;
    }

    results.innerHTML = cmState.roomsResult.map(item => {
        const room = item.room;
        const isSelected = cmState.selectedRoom && String(cmState.selectedRoom.id) === String(room.id);
        const amenities = cmParseAmenities(room);
        const displayedAmenities = cmState.requiredAmenities.length
            ? cmState.requiredAmenities
            : amenities;
        const action = isSelected
            ? '<button type="button" class="cm-btn cm-btn-ghost" disabled>Đã chọn</button>'
            : `<button type="button" class="cm-btn cm-btn-ghost" onclick="selectCreateMeetingRoomById('${room.id}')">Chọn phòng</button>`;
        return `
            <article class="cm-room-card ${isSelected ? 'is-selected' : ''}">
                <div class="cm-room-top">
                    <h3>${escapeHtml(room.name)}</h3>
                    <span class="cm-badge ${item.fit ? 'cm-badge-ok' : 'cm-badge-busy'}">
                        ${item.fit ? 'Trống' : 'Trống · Sức chứa thấp'}
                    </span>
                </div>
                <p class="cm-room-meta">${escapeHtml(room.location || 'Chưa có vị trí')} · ${item.capacity} chỗ</p>
                <p class="cm-room-amenities">${displayedAmenities.length ? displayedAmenities.map(amenity => `<span class="cm-amenity-label">${cmIcon('check', 'cm-inline-icon')} ${escapeHtml(amenity)}</span>`).join('') : 'Không yêu cầu tiện nghi cố định'}</p>
                <div class="cm-room-actions">${action}</div>
            </article>
        `;
    }).join('');
}

function selectCreateMeetingRoomById(id) {
    const found = cmState.roomsResult.find(item => String(item.room.id) === String(id));
    if (found) selectCreateMeetingRoom(found.room);
}

function selectCreateMeetingRoom(room, { silent } = {}) {
    if (!room) return;
    const match = cmState.roomsResult.find(item =>
        String(item.room.id) === String(room.id) && item.available
    );
    if (!match) return;
    cmState.selectedRoom = match.room;
    cmState.roomSelectionExpanded = false;
    clearValidationError('cmRoomError');
    renderRoomResults();
    updateEquipmentSectionVisibility();
    updateCapacityHint();
    if (!silent) updateCreateMeetingSummary();
}

function changeCreateMeetingRoom() {
    if (!cmState.selectedRoom) return;
    cmState.roomSelectionExpanded = true;
    renderRoomResults();
}

function getEquipmentAvailableQty(eq) {
    const value = Number(eq?.available_qty ?? eq?.total_qty ?? 0);
    return Number.isFinite(value) ? Math.max(0, value) : 0;
}

function getBorrowQtyValue(id) {
    const key = String(id);
    const value = Number(cmState.borrowQty[key] ?? cmState.borrowQty[id] ?? 0);
    return Number.isFinite(value) ? Math.max(0, Math.trunc(value)) : 0;
}

function setBorrowQtyValue(id, nextQty) {
    const key = String(id);
    const value = Number(nextQty);
    const safe = Number.isFinite(value) ? Math.max(0, Math.trunc(value)) : 0;
    if (safe <= 0) {
        delete cmState.borrowQty[key];
        return 0;
    }
    cmState.borrowQty[key] = safe;
    return safe;
}

function renderEquipment() {
    const box = cmEl('cmBorrowEquipment');
    if (!box) return;
    if (!cmState.equipment.length) {
        box.innerHTML = cmState.equipmentLoadError
            ? `<p class="cm-alert cm-alert-error is-open">${escapeHtml(cmState.equipmentLoadError)}</p>`
            : '<p class="cm-help">Không có thiết bị khả dụng trong khung giờ này.</p>';
        return;
    }
    const loadError = cmState.equipmentLoadError;
    box.innerHTML = `${loadError
        ? `<p class="cm-alert cm-alert-error is-open">${escapeHtml(loadError)}</p>`
        : ''}${cmState.equipment.map(eq => {
        const qty = getBorrowQtyValue(eq.id);
        const available = getEquipmentAvailableQty(eq);
        const total = Number(eq.total_quantity ?? eq.total_qty ?? 0);
        const unavailable = available <= 0 || Boolean(loadError);
        return `
            <div class="cm-eq-row ${available <= 0 ? 'is-unavailable' : ''} ${loadError ? 'is-stale' : ''}">
                <div>
                    <strong>${escapeHtml(eq.name)}</strong>
                    <div class="cm-help">Còn ${available}/${total}</div>
                </div>
                <div class="cm-eq-controls">
                    <input class="cm-equipment-quantity" type="number" min="0" max="${available}"
                        step="1" value="${qty}" aria-label="Số lượng ${escapeHtml(eq.name)}"
                        ${unavailable ? 'disabled' : ''}
                        onchange="setEquipmentQuantity(${Number(eq.id)}, this.value)" />
                    <span class="cm-badge ${unavailable ? 'cm-badge-busy' : 'cm-badge-ok'}">
                        ${loadError ? 'Chưa xác minh tồn kho' : unavailable ? 'Hết hàng trong khung giờ này' : `Còn ${available}/${total}`}
                    </span>
                </div>
            </div>
        `;
    }).join('')}`;
    updateEquipmentConflict();
}

function setEquipmentQuantity(id, value) {
    const equipment = cmState.equipment.find(item => Number(item.id) === Number(id));
    if (!equipment) return;
    const available = getEquipmentAvailableQty(equipment);
    const requested = Number.parseInt(value, 10);
    const quantity = Number.isFinite(requested)
        ? Math.max(0, Math.min(requested, available))
        : 0;
    setBorrowQtyValue(id, quantity);
    renderEquipment();
    updateCreateMeetingSummary();
}

function showEquipmentAvailabilityError(eq, requestedQty) {
    const alert = cmEl('cmEquipConflict');
    if (!alert || !eq) return;
    const available = getEquipmentAvailableQty(eq);
    const message = available <= 0
        ? `Thiết bị "${eq.name}" hiện đã hết hàng. Bạn đang yêu cầu ${requestedQty}.`
        : `Thiết bị "${eq.name}" chỉ còn ${available} chiếc khả dụng, bạn đang yêu cầu ${requestedQty}.`;
    alert.classList.add('is-open');
    alert.innerHTML = `
        ${cmIcon('alert', 'cm-alert-icon')}
        <div class="cm-conflict-copy">
            <strong>${escapeHtml(eq.name)}</strong>
            <span>${escapeHtml(message)}</span>
            <span>
                <button type="button" class="cm-link-btn" onclick="reduceEquipmentToAvailable(${eq.id})">Giảm xuống còn ${available}</button>
                ·
                <button type="button" class="cm-link-btn" onclick="clearBorrowQty(${eq.id})">Xóa lựa chọn</button>
            </span>
        </div>
    `;
}

function changeBorrowQty(id, delta) {
    const eq = cmState.equipment.find(item => Number(item.id) === Number(id));
    if (!eq) return;

    const available = getEquipmentAvailableQty(eq);
    const current = getBorrowQtyValue(id);
    const next = Math.max(0, current + delta);

    setBorrowQtyValue(id, next);
    renderEquipment();
    if (next > available) showEquipmentAvailabilityError(eq, next);
    updateCreateMeetingSummary();
}

function reduceEquipmentToAvailable(id) {
    const eq = cmState.equipment.find(item => Number(item.id) === Number(id));
    if (!eq) return;
    setBorrowQtyValue(id, getEquipmentAvailableQty(eq));
    renderEquipment();
    updateCreateMeetingSummary();
}

function clearBorrowQty(id) {
    setBorrowQtyValue(id, 0);
    renderEquipment();
    updateCreateMeetingSummary();
}

function updateEquipmentConflict() {
    const alert = cmEl('cmEquipConflict');
    if (!alert) return;
    const issues = cmState.equipment.filter(eq => {
        const qty = getBorrowQtyValue(eq.id);
        const available = getEquipmentAvailableQty(eq);
        return qty > available || (available <= 0 && qty > 0);
    });
    if (!issues.length) {
        alert.classList.remove('is-open');
        alert.innerHTML = '';
        cmEl('cmBorrowEquipment')?.classList.remove('is-invalid');
        clearValidationError('cmEquipmentError');
        return;
    }
    const eq = issues[0];
    const requested = getBorrowQtyValue(eq.id);
    showEquipmentAvailabilityError(eq, requested);
    cmEl('cmBorrowEquipment')?.classList.remove('is-invalid');
    clearValidationError('cmEquipmentError');
}

function generateMeetingLink() {
    const input = cmEl('cmMeetingLink');
    if (!input) return;
    const roomCode = window.crypto.randomUUID().replace(/-/g, '');
    input.value = `https://meet.jit.si/RoomSync-${roomCode}`;
    clearValidationError('cmMeetingLinkError');
    updateCreateMeetingSummary();
}

function collectConflicts() {
    const conflicts = [];
    if (cmState.mode === 'offline' && cmState.selectedRoom) {
        const match = cmState.roomsResult.find(item => String(item.room.id) === String(cmState.selectedRoom.id));
        if (match && match.available === false) {
            conflicts.push(`Phòng ${cmState.selectedRoom.name} không khả dụng trong khung giờ đã chọn.`);
            cmState.suggestedRooms = cmState.roomsResult.filter(item => item.available).slice(0, 2).map(item => item.room);
        }
    }
    cmState.equipment.forEach(eq => {
        const qty = getBorrowQtyValue(eq.id);
        const available = getEquipmentAvailableQty(eq);
        if (qty > available) {
            conflicts.push(`${eq.name} chỉ còn ${available} chiếc khả dụng.`);
        } else if (qty > 0 && available <= 0) {
            conflicts.push(`${eq.name} đã hết hàng.`);
        }
    });
    return conflicts;
}

function updateCreateMeetingSummary() {
    const title = cmEl('cmTitle')?.value.trim() || 'Chưa đặt tên cuộc họp';
    const { date, start, end } = cmGetTimes();
    const borrowed = cmState.equipment.filter(eq => getBorrowQtyValue(eq.id) > 0);
    const conflicts = collectConflicts();
    const roomConflict = cmEl('cmRoomConflict');
    if (roomConflict) {
        const selectedRoomResult = cmState.selectedRoom
            ? cmState.roomsResult.find(item => String(item.room.id) === String(cmState.selectedRoom.id))
            : null;
        if (cmState.mode === 'offline' && selectedRoomResult?.available === false) {
            const suggestions = cmState.suggestedRooms.map(r => escapeHtml(r.name)).join(', ');
            roomConflict.classList.add('is-open');
            roomConflict.classList.add('is-conflict');
            roomConflict.innerHTML = `
                ${cmIcon('alert', 'cm-alert-icon')}
                <div class="cm-conflict-copy">
                    <strong>Phòng ${escapeHtml(cmState.selectedRoom.name)} không khả dụng</strong>
                    <span>${escapeHtml(start || '')} – ${escapeHtml(end || '')} đã có cuộc họp.</span>
                    ${suggestions ? `<span>Đề xuất: ${suggestions}</span>` : ''}
                </div>
            `;
        } else if (cmState.mode === 'offline' && selectedRoomResult?.available === true) {
            roomConflict.classList.add('is-open');
            roomConflict.classList.remove('is-conflict');
            roomConflict.innerHTML = `
                ${cmIcon('check', 'cm-alert-icon')}
                <div class="cm-conflict-copy">
                    <strong>Phòng ${escapeHtml(cmState.selectedRoom.name)} đang khả dụng</strong>
                    <span>Không có cuộc họp trùng trong khung giờ đã chọn.</span>
                </div>
            `;
        } else {
            roomConflict.classList.remove('is-open');
            roomConflict.classList.remove('is-conflict');
            roomConflict.innerHTML = '';
        }
    }

    const list = cmEl('cmSummaryList');
    const organizer = cmCurrentOrganizer();
    const externalGuests = Math.max(
        0,
        Number.parseInt(cmEl('cmExternalGuestCount')?.value || '0', 10) || 0
    );
    const internalUsers = cmAttendeeCount();
    const organizerCount = Number(cmOrganizerParticipates());
    const totalAttendees = internalUsers + externalGuests + organizerCount;
    const organizerName = organizer?.full_name || organizer?.name || 'Chưa xác định';
    const organizerNameElement = cmEl('cmOrganizerName');
    if (organizerNameElement) organizerNameElement.textContent = organizerName;
    const attendeeTotalElement = cmEl('cmTotalAttendees');
    if (attendeeTotalElement) {
        attendeeTotalElement.textContent =
            `${totalAttendees} người (${organizerCount} người tổ chức + ${externalGuests} khách ngoài + ${internalUsers} nhân viên)`;
    }

    if (list) {
        const items = [
            { icon: 'file', label: 'Cuộc họp', value: title },
            { icon: 'calendar', label: 'Ngày', value: cmFormatViDate(date) },
            { icon: 'clock', label: 'Thời gian', value: `${start || '--:--'} – ${end || '--:--'}` },
            { icon: 'users', label: 'Thành phần', value: `Tổng tham dự: ${totalAttendees} người` },
            cmState.mode === 'online'
                ? { icon: 'globe', label: 'Hình thức', value: 'Online' }
                : { icon: 'building', label: 'Phòng họp', value: cmState.selectedRoom ? cmState.selectedRoom.name : 'Chưa chọn phòng' },
            cmState.mode === 'online'
                ? { icon: 'link', label: 'Đường dẫn', value: cmEl('cmMeetingLink')?.value || 'Chưa có link' }
                : null,
            { icon: 'repeat', label: 'Lặp lại', value: cmRecurrenceLabel() },
        ].filter(Boolean);
        list.innerHTML = items.map(item => `
            <li class="cm-summary-item">
                <span class="cm-summary-icon">${cmIcon(item.icon)}</span>
                <span class="cm-summary-copy">
                    <strong>${escapeHtml(item.label)}</strong>
                    <span>${escapeHtml(item.value)}</span>
                </span>
            </li>
        `).join('');
    }
    const equipmentSummary = cmEl('cmEquipmentSummary');
    if (equipmentSummary) {
        equipmentSummary.innerHTML = borrowed.length
            ? borrowed.map(eq => {
                const requested = getBorrowQtyValue(eq.id);
                const available = getEquipmentAvailableQty(eq);
                const isEnough = requested <= available;
                return `<li class="${isEnough ? 'is-ready' : 'is-shortage'}">
                    <span>${escapeHtml(eq.name)} × ${requested}</span>
                    <strong>${isEnough ? 'Đủ hàng' : `Thiếu ${requested - available}`}</strong>
                </li>`;
            }).join('')
            : '<li class="cm-help">Chưa đăng ký thiết bị.</li>';
    }

    const status = cmEl('cmSummaryStatus');
    if (status) {
        const invalidEquipment = cmState.equipment.some(eq => {
            const qty = getBorrowQtyValue(eq.id);
            return qty > getEquipmentAvailableQty(eq)
                || (qty > 0 && getEquipmentAvailableQty(eq) <= 0);
        });
        const hasConflict = conflicts.length || invalidEquipment;
        status.className = `cm-status ${hasConflict ? 'is-warn' : 'is-ok'}`;
        status.innerHTML = `${cmIcon(hasConflict ? 'alert' : 'check', 'cm-status-icon')}<span>${hasConflict ? 'Có vấn đề cần xử lý' : 'Không có xung đột'}</span>`;
    }

    const submit = cmEl('cmSubmit');
    if (submit) {
        const hardRoomConflict = conflicts.some(conflict => conflict.startsWith('Phòng'));
        submit.disabled = cmState.submitting || hardRoomConflict;
        submit.textContent = cmState.submitting ? 'Đang kiểm tra...' : 'TẠO CUỘC HỌP';
    }
}

function showFormError(message) {
    const box = cmEl('cmFormError');
    if (!box) return;
    box.classList.add('is-open');
    box.textContent = message;
}

function clearValidationError(errorId) {
    const error = cmEl(errorId);
    error?.classList.remove('is-visible');

    const fieldIds = {
        cmTitleError: 'cmTitle',
        cmDateError: 'cmDate',
        cmStartError: 'start_time',
        cmEndError: 'end_time',
        cmMeetingLinkError: 'cmMeetingLink',
    };
    const field = fieldIds[errorId] ? cmEl(fieldIds[errorId]) : null;
    field?.classList.remove('is-invalid');
    field?.removeAttribute('aria-invalid');

    if (errorId === 'cmRoomError') {
        cmEl('cmRoomResults')?.classList.remove('is-invalid');
        cmEl('cmSearchRoomsBtn')?.classList.remove('is-invalid');
        cmEl('cmSearchRoomsBtn')?.removeAttribute('aria-invalid');
    } else if (errorId === 'cmEquipmentError') {
        cmEl('cmBorrowEquipment')?.classList.remove('is-invalid');
    }
}

function clearValidationFeedback() {
    [
        'cmTitleError',
        'cmDateError',
        'cmStartError',
        'cmEndError',
        'cmMeetingLinkError',
        'cmRoomError',
        'cmEquipmentError',
    ].forEach(clearValidationError);
}

function setValidationError(field, errorId, message) {
    if (field) {
        field.classList.add('is-invalid');
        field.setAttribute('aria-invalid', 'true');
    }
    const error = cmEl(errorId);
    if (error) {
        error.textContent = message;
        error.classList.add('is-visible');
    }
}

function focusFirstInvalidField(field) {
    if (!field) return;
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    field.scrollIntoView({
        behavior: reduceMotion ? 'auto' : 'smooth',
        block: 'center',
    });
    window.setTimeout(() => {
        if (field.isConnected) field.focus({ preventScroll: true });
    }, reduceMotion ? 0 : 350);
}

function clearValidationErrorForField(field) {
    const errorByFieldId = {
        cmTitle: 'cmTitleError',
        cmDate: 'cmDateError',
        start_time: 'cmStartError',
        end_time: 'cmEndError',
        cmMeetingLink: 'cmMeetingLinkError',
    };
    const errorId = errorByFieldId[field.id];
    if (errorId) clearValidationError(errorId);
}

function cmTimeIsInPast(date, start) {
    if (!date || !start) return false;
    const startDate = new Date(`${date}T${start}:00`);
    if (Number.isNaN(startDate.getTime())) return false;
    return startDate.getTime() < Date.now();
}

function validateCreateMeeting() {
    hideCmAlerts();
    clearValidationFeedback();
    const title = cmEl('cmTitle');
    const dateInput = cmEl('cmDate');
    const startInput = cmEl('start_time');
    const endInput = cmEl('end_time');
    const onlineLink = cmEl('cmMeetingLink');
    const { date, start, end } = cmGetTimes();
    const invalidFields = [];
    let ok = true;

    [title, dateInput, startInput, endInput, onlineLink].forEach(el => el?.classList.remove('is-invalid'));

    if (!title?.value.trim()) {
        setValidationError(title, 'cmTitleError', 'Nhập tên cuộc họp trước khi tạo.');
        invalidFields.push(title);
        ok = false;
    }

    const hasValidDate = /^\d{4}-\d{2}-\d{2}$/.test(date || '');
    const hasValidStart = /^\d{2}:\d{2}$/.test(start || '');
    const hasValidEnd = /^\d{2}:\d{2}$/.test(end || '');
    if (!hasValidDate || !hasValidStart || !hasValidEnd) {
        if (!hasValidDate) {
            setValidationError(dateInput, 'cmDateError', 'Chọn ngày hợp lệ.');
            invalidFields.push(dateInput);
        }
        if (!hasValidStart) {
            setValidationError(startInput, 'cmStartError', 'Chọn giờ bắt đầu hợp lệ.');
            invalidFields.push(startInput);
        }
        if (!hasValidEnd) {
            setValidationError(endInput, 'cmEndError', 'Chọn giờ kết thúc hợp lệ.');
            invalidFields.push(endInput);
        }
        showFormError('Chọn ngày, giờ bắt đầu và giờ kết thúc hợp lệ.');
        ok = false;
    }

    if (date && start && cmTimeIsInPast(date, start)) {
        setValidationError(startInput, 'cmStartError', 'Thời gian bắt đầu không được ở quá khứ.');
        invalidFields.push(startInput);
        showFormError('Thời gian bắt đầu không được ở quá khứ.');
        ok = false;
    }

    if (date && start && end && end <= start) {
        setValidationError(endInput, 'cmEndError', 'Giờ kết thúc phải sau giờ bắt đầu.');
        invalidFields.push(endInput);
        showFormError('Giờ kết thúc phải sau giờ bắt đầu.');
        ok = false;
    } else if (date && start && end) {
        const startDt = new Date(`${date}T${start}:00`);
        const endDt = new Date(`${date}T${end}:00`);
        const diffMinutes = (endDt.getTime() - startDt.getTime()) / (1000 * 60);
        if (diffMinutes < 15) {
            setValidationError(endInput, 'cmEndError', 'Thời lượng cuộc họp tối thiểu là 15 phút.');
            invalidFields.push(endInput);
            showFormError('Thời lượng cuộc họp tối thiểu là 15 phút.');
            ok = false;
        }
    }

    if (cmState.mode === 'online') {
        const linkValue = onlineLink?.value.trim() || '';
        if (!linkValue) {
            setValidationError(onlineLink, 'cmMeetingLinkError', 'Cuộc họp online cần link. Bấm Tạo link nếu chưa có.');
            invalidFields.push(onlineLink);
            showFormError('Cuộc họp online cần link. Bấm Tạo link nếu chưa có.');
            ok = false;
        } else if (!/^https?:\/\//i.test(linkValue)) {
            setValidationError(onlineLink, 'cmMeetingLinkError', 'Nhập URL đầy đủ bắt đầu bằng http:// hoặc https://.');
            invalidFields.push(onlineLink);
            showFormError('Link cuộc họp online không hợp lệ. Vui lòng nhập URL đầy đủ bắt đầu bằng http:// hoặc https://');
            ok = false;
        }
    }

    if (cmState.mode === 'offline') {
        const roomId = Number.parseInt(String(cmState.selectedRoom?.id ?? ''), 10);
        if (!Number.isSafeInteger(roomId) || roomId <= 0) {
            const results = cmEl('cmRoomResults');
            const searchButton = cmEl('cmSearchRoomsBtn');
            results?.classList.add('is-invalid');
            searchButton?.classList.add('is-invalid');
            searchButton?.setAttribute('aria-invalid', 'true');
            const roomError = cmEl('cmRoomError');
            if (roomError) {
                roomError.textContent = 'Tìm phòng phù hợp rồi chọn một phòng trước khi tạo cuộc họp.';
                roomError.classList.add('is-visible');
            }
            invalidFields.push(searchButton || results);
            showFormError('Vui lòng chọn phòng họp hợp lệ.');
            ok = false;
        }
    }

    const roomHasConflict = collectConflicts().some(conflict => conflict.startsWith('Phòng'));
    if (roomHasConflict) {
        if (cmState.mode === 'offline' && cmState.selectedRoom) {
            const roomResults = cmEl('cmRoomResults');
            const searchButton = cmEl('cmSearchRoomsBtn');
            roomResults?.classList.add('is-invalid');
            searchButton?.classList.add('is-invalid');
            searchButton?.setAttribute('aria-invalid', 'true');
            const roomError = cmEl('cmRoomError');
            if (roomError) {
                roomError.textContent = 'Phòng đã chọn có xung đột. Hãy tìm và chọn phòng khác.';
                roomError.classList.add('is-visible');
            }
            invalidFields.push(searchButton || roomResults);
        }
        showFormError('Hãy xử lý xung đột trước khi tạo cuộc họp.');
        ok = false;
    }
    if (!ok) {
        const firstInvalidField = invalidFields.find(field => field?.isConnected && !field.disabled);
        focusFirstInvalidField(firstInvalidField);
    }
    return ok;
}

async function showMeetingWarnings(warnings) {
    const dialog = cmEl('cmWarningDialog');
    const list = cmEl('cmWarningList');
    if (!dialog || !list || typeof dialog.showModal !== 'function') {
        return window.confirm(
            `Có ${warnings.length} cảnh báo về sức chứa, thiết bị hoặc lịch người tham dự. Bạn vẫn muốn đặt phòng?`
        );
    }

    list.replaceChildren();
    warnings.forEach(warning => {
        const item = document.createElement('li');
        item.textContent = warning.message || warning.type || 'Có cảnh báo cần xem xét.';
        list.appendChild(item);
    });
    return new Promise(resolve => {
        dialog.addEventListener(
            'close',
            () => resolve(dialog.returnValue === 'force'),
            { once: true }
        );
        dialog.showModal();
    });
}

function meetingResponseMessage(responseData, fallback) {
    const detail = responseData?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail?.blocking_errors) && detail.blocking_errors.length) {
        return detail.blocking_errors.map(error => error.message).join(' ');
    }
    return responseData?.message || fallback;
}

async function handleCreateMeetingSubmit(event) {
    event.preventDefault();
    if (!validateCreateMeeting()) return;

    const title = cmEl('cmTitle').value.trim();
    const { date, start, end } = cmGetTimes();
    const descriptionParts = [];
    const desc = cmEl('cmDescription')?.value.trim();
    if (desc) descriptionParts.push(desc);

    const recurrenceType = cmEl('cmRecurrence')?.value || 'none';
    const until = cmEl('cmRecurrenceUntil')?.value;
    let recurrenceEndDate = null;
    const { endTime } = cmGetDateTimeRange();
    if (recurrenceType !== 'none') {
        if (until) recurrenceEndDate = cmDateTimeValue(until, end);
        else {
            const d = new Date(endTime);
            d.setMonth(d.getMonth() + (recurrenceType === 'weekly' ? 2 : 1));
            recurrenceEndDate = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}T${end}:00`;
        }
    }

    const realParticipantIds = [...new Set(
        cmState.attendees
            .map(a => a.id)
            .filter(id => Number.isInteger(id))
    )];
    const roomId = cmState.mode === 'offline'
        ? Number.parseInt(String(cmState.selectedRoom.id), 10)
        : null;
    const { startTime } = cmGetDateTimeRange();

    const payload = {
        title,
        description: descriptionParts.join('\n') || null,
        meeting_type: cmState.mode,
        meeting_link: cmState.mode === 'online'
            ? (cmEl('cmMeetingLink')?.value.trim() || null)
            : null,
        room_id: roomId,
        start_time: startTime,
        end_time: endTime,
        is_recurring: recurrenceType !== 'none',
        recurrence_type: recurrenceType,
        recurrence_end_date: recurrenceEndDate,
        organizer_participates: cmOrganizerParticipates(),
        external_guest_count: Math.max(
            0,
            Number.parseInt(cmEl('cmExternalGuestCount')?.value || '0', 10) || 0
        ),
        equipments: cmState.mode === 'offline'
            ? cmState.equipment
                .map(eq => ({
                    equipment_id: Number(eq.id),
                    quantity: getBorrowQtyValue(eq.id),
                }))
                .filter(item => item.quantity > 0)
            : [],
        participant_ids: realParticipantIds,
        force_book: false,
    };

    const token = typeof getAuthToken === 'function' ? getAuthToken() : '';
    if (!token) {
        const box = cmEl('cmApiError');
        if (box) {
            box.classList.add('is-open');
            box.textContent = 'Vui lòng đăng nhập để tạo cuộc họp.';
        }
        return;
    }

    cmState.submitting = true;
    updateCreateMeetingSummary();
    try {
        const validationResponse = await fetchAPI(`${API_BASE}/meetings/validate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(payload),
        });
        const validation = await validationResponse.json().catch(() => ({}));
        if (!validationResponse.ok) {
            throw new Error(meetingResponseMessage(validation, 'Không thể kiểm tra khả dụng.'));
        }
        if (!validation.is_valid) {
            const blockingErrors = validation.blocking_errors || [];
            throw new Error(
                blockingErrors.map(error => error.message).join(' ')
                || 'Cuộc họp không khả dụng.'
            );
        }
        if (validation.warnings?.length) {
            cmState.submitting = false;
            updateCreateMeetingSummary();
            const confirmed = await showMeetingWarnings(validation.warnings);
            if (!confirmed) return;
            payload.force_book = true;
            cmState.submitting = true;
            updateCreateMeetingSummary();
        }

        const res = await fetchAPI(`${API_BASE}/meetings/book`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(payload),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            const warnings = err.detail?.warnings;
            if (res.status === 409 && Array.isArray(warnings) && warnings.length) {
                cmState.submitting = false;
                updateCreateMeetingSummary();
                if (await showMeetingWarnings(warnings)) {
                    payload.force_book = true;
                    cmState.submitting = true;
                    updateCreateMeetingSummary();
                    const confirmedResponse = await fetchAPI(`${API_BASE}/meetings/book`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            Authorization: `Bearer ${token}`,
                        },
                        body: JSON.stringify(payload),
                    });
                    if (confirmedResponse.ok) {
                        const confirmedData = await confirmedResponse.json().catch(() => ({}));
                        const skipped = confirmedData?.skipped || [];
                        rememberAttendees(realParticipantIds);
                        showCreateMeetingSuccess(skipped);
                        if (typeof fetchRooms === 'function') fetchRooms(localStorage.getItem('role') === 'admin');
                        if (typeof fetchMyBookings === 'function') fetchMyBookings();
                        return;
                    }
                    const confirmedError = await confirmedResponse.json().catch(() => ({}));
                    throw new Error(meetingResponseMessage(confirmedError, 'Không thể tạo cuộc họp.'));
                }
                return;
            }
            throw new Error(meetingResponseMessage(err, 'Không thể tạo cuộc họp.'));
        }
        const resData = await res.json().catch(() => ({}));
        const skipped = resData?.skipped || [];
        rememberAttendees(realParticipantIds);
        showCreateMeetingSuccess(skipped);
        if (typeof fetchRooms === 'function') fetchRooms(localStorage.getItem('role') === 'admin');
        if (typeof fetchMyBookings === 'function') fetchMyBookings();
    } catch (error) {
        const box = cmEl('cmApiError');
        if (box) {
            box.classList.add('is-open');
            box.textContent = `Không tạo được cuộc họp. ${error.message}`;
        }
    } finally {
        cmState.submitting = false;
        updateCreateMeetingSummary();
    }
}

function findFallbackRoomId() {
    const rooms = typeof allRooms !== 'undefined' ? allRooms : [];
    const room = rooms.find(r => r.is_active !== false);
    return room ? room.id : NaN;
}

function showCreateMeetingSuccess(skipped = []) {
    const dialog = cmEl('cmDialog');
    if (!dialog) return;
    dialog.classList.add('is-success');
    dialog.scrollTop = 0;

    let noticeEl = cmEl('cmSkippedNotice');
    if (skipped && skipped.length > 0) {
        if (!noticeEl) {
            noticeEl = document.createElement('div');
            noticeEl.id = 'cmSkippedNotice';
            noticeEl.className = 'cm-skipped-notice';
            const successView = cmEl('cmSuccessView');
            const helpText = successView?.querySelector('.cm-help');
            if (helpText && helpText.parentNode) {
                helpText.parentNode.insertBefore(noticeEl, helpText.nextSibling);
            } else if (successView) {
                successView.appendChild(noticeEl);
            }
        }
        noticeEl.innerHTML = `<strong>Lưu ý:</strong> Một số mốc thời gian bị bỏ qua do trùng lịch:
            <ul>
                ${skipped.map(s => `<li>${escapeHtml(s.reason || `${s.start_time}: Trùng phòng`)}</li>`).join('')}
            </ul>`;
        noticeEl.style.display = 'block';
    } else if (noticeEl) {
        noticeEl.style.display = 'none';
        noticeEl.innerHTML = '';
    }
}

function showOnlineLocalSuccess() {
    showCreateMeetingSuccess();
}

function bindCreateMeetingEvents() {
    const overlay = cmEl('createMeetingModal');
    if (!overlay) return;

    ['cmTitle', 'cmDescription', 'cmDate', 'start_time', 'end_time', 'cmMeetingLink', 'cmRecurrenceUntil'].forEach(id => {
        cmEl(id)?.addEventListener('input', () => {
            clearValidationErrorForField(cmEl(id));
            updateCreateMeetingSummary();
            if (['cmDate', 'start_time', 'end_time', 'cmRecurrenceUntil'].includes(id)) {
                scheduleRoomSearchRefresh();
            }
            if (['cmDate', 'start_time', 'end_time'].includes(id)) {
                scheduleEquipmentAvailabilityRefresh();
            }
        });
        cmEl(id)?.addEventListener('change', () => {
            clearValidationErrorForField(cmEl(id));
            updateRecurrenceNote();
            updateCreateMeetingSummary();
            if (['cmDate', 'start_time', 'end_time', 'cmRecurrenceUntil'].includes(id)) {
                scheduleRoomSearchRefresh();
            }
            if (['cmDate', 'start_time', 'end_time'].includes(id)) {
                scheduleEquipmentAvailabilityRefresh();
            }
        });
    });

    cmEl('cmRecurrence')?.addEventListener('change', () => setRecurrence());
    ['cmExternalGuestCount', 'cmOrganizerParticipates'].forEach(id => {
        cmEl(id)?.addEventListener('input', () => {
            updateCapacityHint();
            updateCreateMeetingSummary();
            scheduleRoomSearchRefresh();
        });
        cmEl(id)?.addEventListener('change', () => {
            updateCapacityHint();
            updateCreateMeetingSummary();
            scheduleRoomSearchRefresh();
        });
    });
    cmEl('cmAttendeeSearch')?.addEventListener('input', onAttendeeSearchInput);
    cmEl('cmAttendeeSearch')?.addEventListener('keydown', handleAttendeeKeydown);
    ['cmDepartmentFilter', 'cmProjectGroupFilter', 'cmPositionFilter'].forEach(id => {
        cmEl(id)?.addEventListener('change', () => scheduleParticipantSearch());
    });
    cmEl('cmFixedAmenityOptions')?.addEventListener('change', onFixedAmenityChange);
    cmEl('createMeetingForm')?.addEventListener('submit', handleCreateMeetingSubmit);

    document.addEventListener('click', event => {
        const input = cmEl('cmAttendeeSearch');
        const results = cmEl('cmAttendeeSuggest');
        if (input && results && !input.contains(event.target) && !results.contains(event.target)) {
            closeAttendeeSuggest();
        }
    });

    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && overlay.classList.contains('is-open')) closeCreateMeeting();
    });

    if (CM_PREVIEW) openCreateMeeting();
}

document.addEventListener('DOMContentLoaded', bindCreateMeetingEvents);

window.openCreateMeeting = openCreateMeeting;
window.closeCreateMeeting = closeCreateMeeting;
window.setCreateMeetingMode = setCreateMeetingMode;
window.setRecurrence = setRecurrence;
window.removeCreateMeetingAttendee = removeCreateMeetingAttendee;
window.pickCreateMeetingAttendee = pickCreateMeetingAttendee;
window.selectAllFilteredAttendees = selectAllFilteredAttendees;
window.searchMatchingRooms = searchMatchingRooms;
window.selectCreateMeetingRoomById = selectCreateMeetingRoomById;
window.changeCreateMeetingRoom = changeCreateMeetingRoom;
window.changeBorrowQty = changeBorrowQty;
window.reduceEquipmentToAvailable = reduceEquipmentToAvailable;
window.clearBorrowQty = clearBorrowQty;
window.setEquipmentQuantity = setEquipmentQuantity;
window.generateMeetingLink = generateMeetingLink;
window.handleCreateMeetingSubmit = handleCreateMeetingSubmit;
window.showCreateMeetingSuccess = showCreateMeetingSuccess;
