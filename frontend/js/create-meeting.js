/* Create Meeting flow — meeting-first, resources second */

const CM_WEEKDAYS = ['Chủ nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'];
const CM_PREVIEW = new URLSearchParams(location.search).get('preview') === 'meeting';

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
    users: [],
    suggestIndex: -1,
    submitting: false,
    apiError: '',
    suggestedRooms: [],
    roomSearchTimer: null,
};

const CM_MOCK_USERS = [
    { id: 101, full_name: 'Nguyễn Văn A', email: 'a.nguyen@congty.com', title: 'Product Owner' },
    { id: 102, full_name: 'Trần Văn B', email: 'b.tran@congty.com', title: 'Tech Lead' },
    { id: 103, full_name: 'Lê Thị C', email: 'c.le@congty.com', title: 'Designer' },
    { id: 104, full_name: 'Phạm Minh D', email: 'd.pham@congty.com', title: 'QA' },
    { id: 105, full_name: 'Hoàng E', email: 'e.hoang@congty.com', title: 'Backend' },
    { id: 106, full_name: 'Đỗ F', email: 'f.do@congty.com', title: 'Frontend' },
    { id: 107, full_name: 'Vũ G', email: 'g.vu@congty.com', title: 'Scrum Master' },
    { id: 108, full_name: 'Bùi H', email: 'h.bui@congty.com', title: 'BA' },
];

const CM_MOCK_EQUIPMENT = [
    { id: 1, name: 'Laptop', available_qty: 5, total_qty: 10, is_active: true },
    { id: 2, name: 'Micro không dây', available_qty: 2, total_qty: 4, is_active: true },
    { id: 3, name: 'Webcam', available_qty: 0, total_qty: 3, is_active: true },
];

function cmEl(id) {
    return document.getElementById(id);
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
    return 1 + cmAttendeeCount();
}

function cmGetTimes() {
    const date = cmEl('cmDate')?.value;
    const start = cmEl('cmStart')?.value;
    const end = cmEl('cmEnd')?.value;
    return { date, start, end };
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

function rankUsers(users, query) {
    const q = query.trim().toLowerCase();
    const freq = new Set(frequentIds());
    return users
        .filter(u => {
            if (!q) return true;
            const blob = `${u.full_name || ''} ${u.email || ''} ${u.title || ''}`.toLowerCase();
            return blob.includes(q);
        })
        .sort((a, b) => {
            const aRel = q && String(a.full_name || '').toLowerCase().startsWith(q) ? 0 : 1;
            const bRel = q && String(b.full_name || '').toLowerCase().startsWith(q) ? 0 : 1;
            if (aRel !== bRel) return aRel - bRel;
            const aF = freq.has(a.id) ? 0 : 1;
            const bF = freq.has(b.id) ? 0 : 1;
            return aF - bF;
        })
        .slice(0, 8);
}

function openCreateMeeting(options = {}) {
    const overlay = cmEl('createMeetingModal');
    if (!overlay) return;

    resetCreateMeeting();
    cmEl('cmDialog')?.classList.remove('is-success');
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
    if (dialog) dialog.classList.remove('is-success');
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
    cmState.suggestIndex = -1;
    cmState.submitting = false;
    cmState.apiError = '';
    cmState.suggestedRooms = [];
    if (cmState.roomSearchTimer) clearTimeout(cmState.roomSearchTimer);
    cmState.roomSearchTimer = null;

    const formIds = ['cmTitle', 'cmDescription', 'cmMeetingLink', 'cmAttendeeSearch'];
    formIds.forEach(id => {
        const el = cmEl(id);
        if (el) {
            el.value = '';
            el.classList.remove('is-invalid');
        }
    });
    setCreateMeetingMode('offline');
    setRecurrence('none');
    setDefaultCreateMeetingTimes();
    renderAttendeeChips();
    renderFixedAmenityOptions();
    renderRoomResults();
    renderEquipment();
    updateEquipmentSectionVisibility();
    hideCmAlerts();
    updateCreateMeetingSummary();
}

function setDefaultCreateMeetingTimes() {
    const now = new Date();
    let startHour = now.getHours();
    let startMin = now.getMinutes() < 30 ? '30' : '00';
    if (now.getMinutes() >= 30) startHour += 1;
    if (startHour < 7) startHour = 9;
    if (startHour > 20) startHour = 9;
    const endHour = Math.min(startHour + 1, 21);
    const dateVal = typeof formatDateInput === 'function' ? formatDateInput(now) : now.toISOString().slice(0, 10);
    const startVal = `${String(startHour).padStart(2, '0')}:${startMin}`;
    const endVal = `${String(endHour).padStart(2, '0')}:${startMin}`;

    const dateEl = cmEl('cmDate');
    const startEl = cmEl('cmStart');
    const endEl = cmEl('cmEnd');
    if (dateEl) dateEl.value = dateVal;
    if (typeof buildViTimeOptions === 'function') {
        buildViTimeOptions(startEl, startVal);
        buildViTimeOptions(endEl, endVal);
    } else {
        if (startEl) startEl.value = startVal;
        if (endEl) endEl.value = endVal;
    }
}

async function loadCreateMeetingData() {
    const token = typeof getAuthToken === 'function' ? getAuthToken() : '';
    try {
        if (typeof _allUsers !== 'undefined' && _allUsers.length) {
            cmState.users = _allUsers;
        } else if (token) {
            const res = await fetch(`${API_BASE}/users/`, { headers: { Authorization: `Bearer ${token}` } });
            if (res.ok) cmState.users = await res.json();
        }
    } catch (e) {
        console.warn('Không tải được người dùng', e);
    }
    if (!cmState.users.length) cmState.users = CM_MOCK_USERS;

    try {
        if (typeof allRooms !== 'undefined' && !allRooms.length) {
            const res = await fetch(`${API_BASE}/rooms/`);
            if (!res.ok) throw new Error(`Không tải được phòng (${res.status}).`);
            allRooms = await res.json();
        }
        renderFixedAmenityOptions();
    } catch (e) {
        console.warn('Không tải được tiện nghi phòng', e);
        const options = cmEl('cmFixedAmenityOptions');
        if (options) options.innerHTML = '<p class="cm-help">Không tải được tiện nghi phòng. Vui lòng thử tải lại.</p>';
    }

    try {
        const { date, start, end } = cmGetTimes();
        const params = new URLSearchParams();
        if (date && start && end) {
            params.set('start_time', `${date}T${start}:00`);
            params.set('end_time', `${date}T${end}:00`);
        }
        if (token) {
            const res = await fetch(`${API_BASE}/equipments/availability?${params}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (res.ok) cmState.equipment = (await res.json()).filter(eq => eq.is_active !== false);
        }
    } catch (e) {
        console.warn('Không tải được thiết bị', e);
    }
    if (!cmState.equipment.length) cmState.equipment = CM_MOCK_EQUIPMENT;
    renderEquipment();
    updateCapacityHint();
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
        onlineLink.classList.remove('is-invalid');
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
    scheduleRoomSearchRefresh();
}

function addAllTeamMembers() {
    const organizer = cmCurrentOrganizer();
    const domain = (localStorage.getItem('user_email') || organizer?.email || cmState.users[0]?.email || '').split('@')[1];
    cmState.users
        .filter(u => {
            if (organizer && cmIsOrganizerUser(u)) return false;
            if (!domain) return true;
            return String(u.email || '').endsWith(`@${domain}`);
        })
        .forEach(addCreateMeetingAttendee);
    closeAttendeeSuggest();
}

function onAttendeeSearchInput() {
    const input = cmEl('cmAttendeeSearch');
    const list = cmEl('cmAttendeeSuggest');
    if (!input || !list) return;
    const query = input.value;
    const organizer = cmCurrentOrganizer();
    const selected = new Set(cmState.attendees.map(a => cmNormalizeUserKey(a)));
    const matches = rankUsers(
        cmState.users.filter(u => {
            if (organizer && cmIsOrganizerUser(u)) return false;
            return !selected.has(cmNormalizeUserKey(u));
        }),
        query
    );
    if (!query.trim() || !matches.length) {
        closeAttendeeSuggest();
        return;
    }
    cmState.suggestIndex = -1;
    list.innerHTML = matches.map((u, i) => `
        <li>
            <button type="button" data-index="${i}" onclick="pickCreateMeetingAttendee(${u.id})">
                <span class="cm-avatar">${escapeHtml(cmInitials(u.full_name || u.email))}</span>
                <span class="cm-suggest-meta">
                    <strong>${escapeHtml(u.full_name || 'Người dùng')}</strong>
                    <span>${escapeHtml(u.email || '')}${u.title ? ' · ' + escapeHtml(u.title) : ''}</span>
                </span>
            </button>
        </li>
    `).join('');
    list.classList.add('is-open');
    list.dataset.ids = matches.map(u => u.id).join(',');
}

function pickCreateMeetingAttendee(id) {
    const user = cmState.users.find(u => String(u.id) === String(id));
    if (user) addCreateMeetingAttendee(user);
    const input = cmEl('cmAttendeeSearch');
    if (input) input.value = '';
    closeAttendeeSuggest();
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
        const params = new URLSearchParams({
            start_time: `${date}T${start}:00`,
            end_time: `${date}T${end}:00`,
        });
        const res = await fetch(`${API_BASE}/rooms/available?${params}`, {
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
        if (!item.available || !item.fit) return false;
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
                    <h3>✓ ${escapeHtml(selected.room.name)}</h3>
                    <span class="cm-badge cm-badge-ok">Đã chọn · Trống</span>
                </div>
                <p class="cm-room-meta">${escapeHtml(selected.room.location || 'Chưa có vị trí')} · ${selected.capacity} chỗ · ${escapeHtml(cmGetTimes().start || '')}–${escapeHtml(cmGetTimes().end || '')}</p>
                <p class="cm-room-amenities">${amenities.length ? amenities.map(item => `✓ ${escapeHtml(item)}`).join(' · ') : 'Chưa khai báo tiện nghi cố định'}</p>
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
            ? cmState.requiredAmenities.map(item => `✓ ${escapeHtml(item)}`)
            : amenities.map(item => `✓ ${escapeHtml(item)}`);
        const action = isSelected
            ? '<button type="button" class="cm-btn cm-btn-ghost" disabled>Đã chọn</button>'
            : `<button type="button" class="cm-btn cm-btn-ghost" onclick="selectCreateMeetingRoomById('${room.id}')">Chọn phòng</button>`;
        return `
            <article class="cm-room-card ${isSelected ? 'is-selected' : ''}">
                <div class="cm-room-top">
                    <h3>${escapeHtml(room.name)}</h3>
                    <span class="cm-badge cm-badge-ok">Trống</span>
                </div>
                <p class="cm-room-meta">${escapeHtml(room.location || 'Chưa có vị trí')} · ${item.capacity} chỗ</p>
                <p class="cm-room-amenities">${displayedAmenities.length ? displayedAmenities.join(' · ') : 'Không yêu cầu tiện nghi cố định'}</p>
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
        String(item.room.id) === String(room.id) && item.available && item.fit
    );
    if (!match) return;
    cmState.selectedRoom = match.room;
    cmState.roomSelectionExpanded = false;
    renderRoomResults();
    updateEquipmentSectionVisibility();
    if (!silent) updateCreateMeetingSummary();
}

function changeCreateMeetingRoom() {
    if (!cmState.selectedRoom) return;
    cmState.roomSelectionExpanded = true;
    renderRoomResults();
}

function renderEquipment() {
    const box = cmEl('cmBorrowEquipment');
    if (!box) return;
    if (!cmState.equipment.length) {
        box.innerHTML = '<p class="cm-help">Không có thiết bị để mượn thêm.</p>';
        return;
    }
    box.innerHTML = cmState.equipment.map(eq => {
        const qty = cmState.borrowQty[eq.id] || 0;
        const available = eq.available_qty ?? eq.total_qty ?? 0;
        const empty = available <= 0;
        return `
            <div class="cm-eq-row ${empty ? 'is-empty' : ''}">
                <div>
                    <strong>${escapeHtml(eq.name)}</strong>
                    <div class="cm-help">Available: ${available} / ${eq.total_qty ?? available}</div>
                </div>
                ${empty
                    ? '<span class="cm-badge cm-badge-busy">Hết thiết bị</span>'
                    : `<div class="cm-stepper">
                        <button type="button" aria-label="Giảm ${escapeHtml(eq.name)}" onclick="changeBorrowQty(${eq.id}, -1)">−</button>
                        <span>${qty}</span>
                        <button type="button" aria-label="Tăng ${escapeHtml(eq.name)}" onclick="changeBorrowQty(${eq.id}, 1)">+</button>
                       </div>`}
            </div>
        `;
    }).join('');
    updateEquipmentConflict();
}

function changeBorrowQty(id, delta) {
    const eq = cmState.equipment.find(item => item.id === id);
    if (!eq) return;
    const available = eq.available_qty ?? eq.total_qty ?? 0;
    const next = Math.max(0, (cmState.borrowQty[id] || 0) + delta);
    cmState.borrowQty[id] = Math.min(next, available);
    renderEquipment();
    updateCreateMeetingSummary();
}

function reduceEquipmentToAvailable(id) {
    const eq = cmState.equipment.find(item => item.id === id);
    if (!eq) return;
    cmState.borrowQty[id] = eq.available_qty ?? 0;
    renderEquipment();
    updateCreateMeetingSummary();
}

function clearBorrowQty(id) {
    cmState.borrowQty[id] = 0;
    renderEquipment();
    updateCreateMeetingSummary();
}

function updateEquipmentConflict() {
    const alert = cmEl('cmEquipConflict');
    if (!alert) return;
    const issues = cmState.equipment.filter(eq => (cmState.borrowQty[eq.id] || 0) > (eq.available_qty ?? eq.total_qty ?? 0));
    if (!issues.length) {
        alert.classList.remove('is-open');
        alert.innerHTML = '';
        return;
    }
    const eq = issues[0];
    alert.classList.add('is-open');
    alert.innerHTML = `
        <strong>⚠ ${escapeHtml(eq.name)} không đủ số lượng</strong>
        <span>Available: ${eq.available_qty} · Yêu cầu: ${cmState.borrowQty[eq.id]}</span>
        <span>
            <button type="button" class="cm-link-btn" onclick="reduceEquipmentToAvailable(${eq.id})">Giảm số lượng</button>
            ·
            <button type="button" class="cm-link-btn" onclick="clearBorrowQty(${eq.id})">Chọn thiết bị khác</button>
        </span>
    `;
}

function generateMeetingLink() {
    const input = cmEl('cmMeetingLink');
    if (!input) return;
    const slug = Math.random().toString(36).slice(2, 8);
    input.value = `https://meet.roomsync.vn/${slug}`;
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
        const qty = cmState.borrowQty[eq.id] || 0;
        const available = eq.available_qty ?? 0;
        if (qty > available) conflicts.push(`${eq.name} không đủ số lượng.`);
    });
    return conflicts;
}

function updateCreateMeetingSummary() {
    const title = cmEl('cmTitle')?.value.trim() || 'Chưa đặt tên cuộc họp';
    const { date, start, end } = cmGetTimes();
    const borrowed = cmState.equipment.filter(eq => (cmState.borrowQty[eq.id] || 0) > 0);
    const conflicts = collectConflicts();
    const roomConflict = cmEl('cmRoomConflict');
    if (roomConflict) {
        if (conflicts.some(c => c.startsWith('Phòng'))) {
            const suggestions = cmState.suggestedRooms.map(r => escapeHtml(r.name)).join(', ');
            roomConflict.classList.add('is-open');
            roomConflict.innerHTML = `
                <strong>⚠ Phòng ${escapeHtml(cmState.selectedRoom.name)} không khả dụng</strong>
                <span>${escapeHtml(start || '')} – ${escapeHtml(end || '')} đã có cuộc họp.</span>
                ${suggestions ? `<span>Đề xuất: ${suggestions}</span>` : ''}
            `;
        } else {
            roomConflict.classList.remove('is-open');
        }
    }

    const list = cmEl('cmSummaryList');
    if (list) {
        const items = [
            `📌 ${title}`,
            `📅 ${cmFormatViDate(date)}`,
            `🕐 ${start || '--:--'} – ${end || '--:--'}`,
            `👥 ${cmAttendeeCount()} người`,
            cmState.mode === 'online' ? '🌐 Online' : `🏢 ${cmState.selectedRoom ? cmState.selectedRoom.name : 'Chưa chọn phòng'}`,
            cmState.mode === 'online' ? `🔗 ${cmEl('cmMeetingLink')?.value || 'Chưa có link'}` : null,
            ...borrowed.map(eq => `🎤 ${eq.name} x${cmState.borrowQty[eq.id]}`),
            `🔁 ${cmRecurrenceLabel()}`,
        ].filter(Boolean);
        list.innerHTML = items.map(item => `<li>${escapeHtml(item)}</li>`).join('');
    }

    const status = cmEl('cmSummaryStatus');
    if (status) {
        status.className = `cm-status ${conflicts.length ? 'is-warn' : 'is-ok'}`;
        status.textContent = conflicts.length ? '⚠ Có vấn đề cần xử lý' : '✓ Không có xung đột';
    }

    const submit = cmEl('cmSubmit');
    if (submit) {
        submit.disabled = cmState.submitting || Boolean(conflicts.length);
        submit.textContent = cmState.submitting ? 'Đang tạo...' : 'TẠO CUỘC HỌP';
    }
}

function showFormError(message) {
    const box = cmEl('cmFormError');
    if (!box) return;
    box.classList.add('is-open');
    box.textContent = message;
}

function cmTimeIsInPast(date, start) {
    if (!date || !start) return false;
    const startDate = new Date(`${date}T${start}:00`);
    if (Number.isNaN(startDate.getTime())) return false;
    return startDate.getTime() < Date.now();
}

function validateCreateMeeting() {
    hideCmAlerts();
    const title = cmEl('cmTitle');
    const dateInput = cmEl('cmDate');
    const startInput = cmEl('cmStart');
    const endInput = cmEl('cmEnd');
    const onlineLink = cmEl('cmMeetingLink');
    const { date, start, end } = cmGetTimes();
    let ok = true;

    [title, dateInput, startInput, endInput, onlineLink].forEach(el => el?.classList.remove('is-invalid'));

    if (!title?.value.trim()) {
        title.classList.add('is-invalid');
        cmEl('cmTitleError')?.classList.add('is-visible');
        ok = false;
    } else {
        cmEl('cmTitleError')?.classList.remove('is-visible');
    }

    if (!date || !start || !end) {
        [dateInput, startInput, endInput].forEach(el => {
            if (el) el.classList.add('is-invalid');
        });
        showFormError('Chọn ngày, giờ bắt đầu và giờ kết thúc hợp lệ.');
        ok = false;
    }

    if (date && start && cmTimeIsInPast(date, start)) {
        startInput?.classList.add('is-invalid');
        showFormError('Thời gian bắt đầu không được ở quá khứ.');
        ok = false;
    }

    if (date && start && end && end <= start) {
        [startInput, endInput].forEach(el => {
            if (el) el.classList.add('is-invalid');
        });
        showFormError('Giờ kết thúc phải sau giờ bắt đầu.');
        ok = false;
    }

    if (cmState.mode === 'online') {
        const linkValue = onlineLink?.value.trim() || '';
        if (!linkValue) {
            onlineLink?.classList.add('is-invalid');
            showFormError('Cuộc họp online cần link. Bấm Tạo link nếu chưa có.');
            ok = false;
        } else if (!/^https?:\/\//i.test(linkValue)) {
            onlineLink?.classList.add('is-invalid');
            showFormError('Link cuộc họp online không hợp lệ. Vui lòng nhập URL đầy đủ bắt đầu bằng http:// hoặc https://');
            ok = false;
        }
    }

    if (cmState.mode === 'offline' && !cmState.selectedRoom) {
        showFormError('Vui lòng chọn phòng họp.');
        ok = false;
    }

    if (collectConflicts().length && !(cmState.mode === 'offline' && !cmState.selectedRoom)) {
        showFormError('Hãy xử lý xung đột trước khi tạo cuộc họp.');
        ok = false;
    }
    return ok;
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
    if (recurrenceType !== 'none') {
        if (until) recurrenceEndDate = `${until}T${end}:00`;
        else {
            const d = new Date(`${date}T${end}:00`);
            d.setMonth(d.getMonth() + (recurrenceType === 'weekly' ? 2 : 1));
            recurrenceEndDate = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}T${end}:00`;
        }
    }

    const realParticipantIds = [...new Set(
        cmState.attendees
            .map(a => a.id)
            .filter(id => Number.isInteger(id))
    )];

    const payload = {
        title,
        description: descriptionParts.join('\n') || null,
        meeting_type: cmState.mode,
        meeting_link: cmState.mode === 'online'
            ? (cmEl('cmMeetingLink')?.value.trim() || null)
            : null,
        room_id: cmState.mode === 'offline'
            ? (cmState.selectedRoom ? parseInt(cmState.selectedRoom.id, 10) : null)
            : null,
        start_time: `${date}T${start}:00`,
        end_time:   `${date}T${end}:00`,
        is_recurring: recurrenceType !== 'none',
        recurrence_type: recurrenceType,
        recurrence_end_date: recurrenceEndDate,
        equipments: cmState.mode === 'offline'
            ? Object.entries(cmState.borrowQty)
                .filter(([, qty]) => qty > 0)
                .map(([eid, qty]) => ({
                    equipment_id: parseInt(eid, 10),
                    quantity: qty
                }))
            : [],
        participant_ids: realParticipantIds,
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
        const res = await fetch(`${API_BASE}/meetings/book`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(payload),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Không thể tạo cuộc họp.');
        }
        rememberAttendees(realParticipantIds);
        showCreateMeetingSuccess();
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

function showCreateMeetingSuccess() {
    cmEl('cmDialog')?.classList.add('is-success');
}

function showOnlineLocalSuccess() {
    showCreateMeetingSuccess();
}

function bindCreateMeetingEvents() {
    const overlay = cmEl('createMeetingModal');
    if (!overlay) return;

    ['cmTitle', 'cmDescription', 'cmDate', 'cmStart', 'cmEnd', 'cmMeetingLink', 'cmRecurrenceUntil'].forEach(id => {
        cmEl(id)?.addEventListener('input', () => {
            updateCreateMeetingSummary();
            if (['cmDate', 'cmStart', 'cmEnd', 'cmRecurrenceUntil'].includes(id)) {
                scheduleRoomSearchRefresh();
            }
        });
        cmEl(id)?.addEventListener('change', () => {
            updateRecurrenceNote();
            updateCreateMeetingSummary();
            if (['cmDate', 'cmStart', 'cmEnd', 'cmRecurrenceUntil'].includes(id)) {
                scheduleRoomSearchRefresh();
            }
        });
    });

    cmEl('cmRecurrence')?.addEventListener('change', () => setRecurrence());
    cmEl('cmAttendeeSearch')?.addEventListener('input', onAttendeeSearchInput);
    cmEl('cmAttendeeSearch')?.addEventListener('keydown', handleAttendeeKeydown);
    cmEl('cmFixedAmenityOptions')?.addEventListener('change', onFixedAmenityChange);
    cmEl('createMeetingForm')?.addEventListener('submit', handleCreateMeetingSubmit);

    document.addEventListener('click', event => {
        const wrap = document.querySelector('.cm-attendee-search');
        if (wrap && !wrap.contains(event.target)) closeAttendeeSuggest();
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
window.addAllTeamMembers = addAllTeamMembers;
window.pickCreateMeetingAttendee = pickCreateMeetingAttendee;
window.searchMatchingRooms = searchMatchingRooms;
window.selectCreateMeetingRoomById = selectCreateMeetingRoomById;
window.changeCreateMeetingRoom = changeCreateMeetingRoom;
window.changeBorrowQty = changeBorrowQty;
window.reduceEquipmentToAvailable = reduceEquipmentToAvailable;
window.clearBorrowQty = clearBorrowQty;
window.generateMeetingLink = generateMeetingLink;
window.handleCreateMeetingSubmit = handleCreateMeetingSubmit;
window.showCreateMeetingSuccess = showCreateMeetingSuccess;
