document.addEventListener('DOMContentLoaded', function () {
    // 1. Giả lập danh sách phòng họp (Dựa trên thiết kế Figma hình 3)[cite: 3]
    const rooms = [
        { id: 1, name: "Phòng Họp Hội Đồng", floor: "Tầng 5", capacity: "16-20 người", available: true, img: "https://images.unsplash.com/photo-1497366216548-37526070297c?w=500" },
        { id: 2, name: "Phòng Họp Sáng Tạo", floor: "Tầng 3", capacity: "6-8 người", available: false, img: "https://images.unsplash.com/photo-1517502884422-41eaead166d4?w=500" },
        { id: 3, name: "Phòng Hội Nghị A", floor: "Tầng 2", capacity: "10-12 người", available: true, img: "https://images.unsplash.com/photo-1431540015161-0bf868a2d407?w=500" }
    ];

    renderRooms(rooms);
    populateRoomDropdown(rooms);
    initCalendar();
});

// Render danh sách phòng ra HTML
function renderRooms(rooms) {
    const container = document.getElementById('roomList');
    container.innerHTML = rooms.map(room => `
        <div class="room-card">
            <div class="room-image">
                <img src="${room.img}" alt="${room.name}">
                <span class="status-badge ${room.available ? 'available' : 'booked'}">
                    ${room.available ? '• Còn trống' : '• Đã đặt'}
                </span>
            </div>
            <div class="room-info">
                <h3>${room.name}</h3>
                <p style="font-size: 13px; color: #64748b; margin-top: 4px;">📍 ${room.floor} | 👥 ${room.capacity}</p>
                <div class="amenities">
                    <span class="tag">Màn hình</span>
                    <span class="tag">Wifi</span>
                    <span class="tag">Video</span>
                </div>
                <div class="btn-group">
                    <button class="btn-outline">Xem lịch</button>
                    <button class="btn-primary" style="padding: 8px;" ${!room.available ? 'disabled style="background:#cbd5e1"' : ''}>
                        ${room.available ? 'Đặt ngay' : 'Hết chỗ'}
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

// Đưa danh sách phòng vào dropdown form
function populateRoomDropdown(rooms) {
    const select = document.getElementById('bookRoom');
    select.innerHTML = rooms.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
}

// Khởi tạo giao diện Tờ lịch (FullCalendar)
function initCalendar() {
    const calendarEl = document.getElementById('calendar');
    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridWeek', // Hiển thị dạng tờ lịch theo TUẦN
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'timeGridDay,timeGridWeek,dayGridMonth' // Chuyển đổi Ngày / Tuần / Tháng
        },
        locale: 'vi', // Ngôn ngữ Tiếng Việt
        events: [
            {
                title: 'Họp Hội Đồng - Phòng 1',
                start: '2026-09-24T09:00:00',
                end: '2026-09-24T10:30:00',
                color: '#2563eb'
            },
            {
                title: 'Sprint Review - Phòng 2',
                start: '2026-09-25T14:00:00',
                end: '2026-09-25T15:30:00',
                color: '#16a34a'
            }
        ]
    });
    calendar.render();
}