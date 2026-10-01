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

// Chuyển đổi giờ sang nhãn tiếng Việt: 7 giờ sáng, 12 giờ trưa, 14 giờ chiều...
function formatVietnameseHour(h) {
    if (h === 0)  return `0 giờ (nửa đêm)`;
    if (h < 12)  return `${h} giờ sáng`;
    if (h === 12) return `12 giờ trưa`;
    if (h < 18)  return `${h} giờ chiều`;
    return `${h} giờ tối`;
}

// Tạo danh sách giờ theo tiếng Việt từ 6:00 đến 22:00 (bước 1 giờ)
function buildViTimeOptions(selectEl, defaultHour) {
    if (!selectEl) return;
    selectEl.innerHTML = '';
    for (let h = 6; h <= 22; h++) {
        const opt = document.createElement('option');
        opt.value = `${String(h).padStart(2,'0')}:00`;
        opt.textContent = formatVietnameseHour(h);
        if (h === defaultHour) opt.selected = true;
        selectEl.appendChild(opt);
    }
}

// Hiển thị ngày đẹp trên label, đồng bộ với input ẩn
function updateDateDisplay(dateVal) {
    const label = document.getElementById('dateDisplayLabel');
    if (!label || !dateVal) return;
    const [y, m, d] = dateVal.split('-');
    const days = ['CN','Thứ 2','Thứ 3','Thứ 4','Thứ 5','Thứ 6','Thứ 7'];
    const dt = new Date(parseInt(y), parseInt(m)-1, parseInt(d));
    label.textContent = `${days[dt.getDay()]} ${d}/${m}/${y}`;
}

// Kích hoạt native date picker thông qua input ẩn
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
    // Làm tròn lên giờ tiếp theo
    const start = new Date(now);
    if (start.getMinutes() > 0 || start.getSeconds() > 0 || start.getMilliseconds() > 0) {
        start.setHours(start.getHours() + 1, 0, 0, 0);
    }
    const end = new Date(start);
    end.setHours(end.getHours() + 1);

    // Cập nhật ngày
    const dateInp = document.getElementById('meetingDateInput');
    if (dateInp) {
        dateInp.value = formatDateInput(start);
        updateDateDisplay(dateInp.value);
    }

    // Build + chọn giờ bắt đầu
    const startSel = document.getElementById('startTimeSelect');
    buildViTimeOptions(startSel, start.getHours());

    // Build + chọn giờ kết thúc
    const endSel = document.getElementById('endTimeSelect');
    buildViTimeOptions(endSel, end.getHours());
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

/* --- MỞ & ĐÓNG MODAL ĐẶT PHÒNG --- */
function openBookingModal(roomId) {
    const room = allRooms.find(r => r.id === roomId && r.is_active !== false);
    if (!room) return;

    setDefaultBookingTimes();
    selectBookingRoom(room);
    renderRoomOptions();

    const modal = document.getElementById('bookingModal');
    if (modal) modal.style.display = 'flex';
    fetchAndRenderEquipments();
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
        try {
            list = JSON.parse(list);
        } catch (e) {
            list = list.split(',').map(s => s.trim()).filter(Boolean);
        }
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

function selectBookingRoom(room) {
    selectedRoomId = room.id;
    const roomNameEl = document.querySelector('#bookingModal .room-name');
    const roomMetaEl = document.querySelector('#bookingModal .room-meta');
    if (roomNameEl) roomNameEl.innerText = room.name;
    if (roomMetaEl) {
        roomMetaEl.innerHTML = `${room.capacity || 10} người · <span class="status-available">Đang hoạt động</span>`;
    }

    // Hiển thị tiện ích có sẵn của phòng đã chọn
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
                    // Cập nhật ngày
                    const di = document.getElementById('meetingDateInput');
                    if (di) { di.value = slot.date; updateDateDisplay(slot.date); }
                    // Cập nhật giờ bắt đầu
                    const ss = document.getElementById('startTimeSelect');
                    if (ss) ss.value = slot.start;
                    // Cập nhật giờ kết thúc
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
        equipments: getSelectedEquipmentsData()
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
        const res = await fetch(`${API_BASE}/meetings`, {
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

        let equipmentsHTML = '';
        if (b.equipments && b.equipments.length > 0) {
            const eqList = b.equipments.map(eq => {
                const name = escapeHtml(eq.equipment_name || 'Thiết bị');
                return name + ' (x' + eq.quantity + ')';
            }).join(', ');

            equipmentsHTML = `
                <div style="margin-top: 4px; font-size: 0.78rem; color: #475569;">
                    📦 <em>Thiết bị:</em> ${eqList}
                </div>
            `;
        }
        

        return `
            <tr>
                <td>
                    <strong>${escapeHtml(roomName)}</strong>
                    <div style="font-size:0.82rem; color:#64748b;">${escapeHtml(b.title || 'Cuộc họp')}</div>
                    ${equipmentsHTML}
                </td>
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
   XỬ LÝ THIẾT BỊ TRONG FORM ĐẶT PHÒNG
   ========================================================================== */

async function fetchAndRenderEquipments() {
    const container = document.getElementById('equipmentListContainer');
    if (!container) return;

    const token = localStorage.getItem('token') || '';
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
        qtyInput.removeAttribute('style'); // let CSS class handle visuals
        qtyInput.focus();
    } else {
        qtyInput.disabled = true;
        qtyInput.value = 1;
        qtyInput.removeAttribute('style');
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
   GLOBAL EXPORTS (XUẤT TOÀN CỤC CHO HTML CALL)
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
window.openQuickBooking = openQuickBooking;
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
window.fetchAndRenderEquipments = fetchAndRenderEquipments;
window.toggleEquipmentQtyInput = toggleEquipmentQtyInput;
window.getSelectedEquipmentsData = getSelectedEquipmentsData;
window.renderRoomAmenities = renderRoomAmenities;
window.getAmenityIcon = getAmenityIcon;
window.triggerDatePicker = triggerDatePicker;
window.updateDateDisplay = updateDateDisplay;
window.buildViTimeOptions = buildViTimeOptions;
window.formatVietnameseHour = formatVietnameseHour;
// syncHiddenStartTime: không cần thiết nữa nhưng giữ để tương thích HTML
window.syncHiddenStartTime = function() {};