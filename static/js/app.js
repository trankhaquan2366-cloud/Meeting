const API_BASE = "http://localhost:8000/api";
let calendarInstance = null;

document.addEventListener('DOMContentLoaded', function() {
    const token = localStorage.getItem('token');
    if (!token) { window.location.href = '/'; return; }

    const isAdmin = token.includes('admin');
    if (isAdmin) document.getElementById('addRoomBtn').style.display = 'block';

    document.getElementById('bookDate').value = new Date().toISOString().split('T')[0];

    initCalendar();
    fetchRooms(isAdmin);
    fetchBookings();
});

async function fetchRooms(isAdmin) {
    const res = await fetch(`${API_BASE}/rooms`);
    const rooms = await res.json();
    document.getElementById('roomList').innerHTML = rooms.map(r => `
        <div class="room-card">
            <div class="room-image">
                <img src="${r.image_url}" alt="${r.name}">
                <span class="status-badge ${r.is_available ? 'available' : 'booked'}">${r.is_available ? '• Còn trống' : '• Đã đặt'}</span>
            </div>
            <div class="room-info">
                <h3>${r.name}</h3>
                <p style="font-size:13px; color:#64748b;">📍 ${r.floor} | 👥 ${r.capacity}</p>
                <div class="btn-group">
                    <button class="btn-primary" style="padding:8px;" onclick="selectRoom(${r.id})" ${!r.is_available ? 'disabled style="background:#cbd5e1"' : ''}>
                        ${r.is_available ? 'Đặt ngay' : 'Hết chỗ'}
                    </button>
                    ${isAdmin ? `<button class="btn-outline" style="color:red;" onclick="deleteRoom(${r.id})">Xóa</button>` : ''}
                </div>
            </div>
        </div>
    `).join('');

    document.getElementById('bookRoomSelect').innerHTML = '<option value="">-- Chọn phòng --</option>' + rooms.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
}

function selectRoom(id) {
    document.getElementById('bookRoomSelect').value = id;
    document.getElementById('bookingForm').scrollIntoView({ behavior: 'smooth' });
}

document.getElementById('bookingForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const data = {
        title: document.getElementById('bookTitle').value,
        room_id: parseInt(document.getElementById('bookRoomSelect').value),
        date: document.getElementById('bookDate').value,
        start_time: document.getElementById('bookStartTime').value,
        end_time: document.getElementById('bookEndTime').value
    };

    const res = await fetch(`${API_BASE}/bookings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (res.ok) {
        alert('Đặt phòng thành công!');
        fetchBookings();
    }
});

function initCalendar() {
    calendarInstance = new FullCalendar.Calendar(document.getElementById('calendar'), {
        initialView: 'timeGridWeek',
        headerToolbar: { left: 'prev,next today', center: 'title', right: 'timeGridDay,timeGridWeek,dayGridMonth' },
        locale: 'vi',
        height: '600px',
        events: []
    });
    calendarInstance.render();
}

async function fetchBookings() {
    const res = await fetch(`${API_BASE}/bookings`);
    const bookings = await res.json();
    calendarInstance.removeAllEvents();
    calendarInstance.addEventSource(bookings.map(b => ({
        id: b.id, title: b.title, start: b.start_time, end: b.end_time, backgroundColor: '#2563eb'
    })));
}

function openModal() { document.getElementById('addRoomModal').style.display = 'flex'; }
function closeModal() { document.getElementById('addRoomModal').style.display = 'none'; }

document.getElementById('addRoomForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const data = {
        name: document.getElementById('newRoomName').value,
        floor: document.getElementById('newRoomFloor').value,
        capacity: document.getElementById('newRoomCapacity').value
    };
    await fetch(`${API_BASE}/rooms`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    closeModal();
    fetchRooms(true);
});

async function deleteRoom(id) {
    if (confirm('Xóa phòng này?')) {
        await fetch(`${API_BASE}/rooms/${id}`, { method: 'DELETE' });
        fetchRooms(true);
    }
}

function logout() { localStorage.removeItem('token'); window.location.href = '/'; }