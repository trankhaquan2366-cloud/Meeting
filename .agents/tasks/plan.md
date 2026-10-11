# Implementation Plan — Tạo cuộc họp hoàn chỉnh

> Dựa trên: đọc trực tiếp source code hiện tại (tất cả file liên quan)
> Ghi chú: `python-dateutil` **KHÔNG có** trong `requirements.txt` → dùng `calendar` stdlib để xử lý monthly recurrence.

---

## Tổng quan các vấn đề phát hiện khi đọc code

| File | Vấn đề |
|---|---|
| `models/meeting.py` | `room_id` nullable=False + ondelete='CASCADE' — cần đổi cho phép NULL với SET NULL |
| `schemas/meeting.py` | Thiếu `meeting_type`, `meeting_link`; `MeetingCreateResponse` chưa có; `room_id` bắt buộc |
| `services/meeting_service.py` | Monthly dùng `timedelta(days=30)` sai; conflict → reject toàn bộ thay vì skip; không lưu participants; không có alias `suggest_time`; không check `meeting_type` |
| `routers/meetings.py` | GET `""` trả `RoomResponse` thay vì meetings; gọi `suggest_time` nhưng service có method `calculate_suggested_times`; response_model POST `/book` là `List[MeetingResponse]` thay vì `MeetingCreateResponse` |
| `routers/rooms.py` | Có 2 endpoint trùng: `/available` và `/available/`; endpoint `/available/` có `min_capacity` nhưng `/available` thì không |
| `create-meeting.js` | Online meeting → early return trước khi gọi API; mockIds filter loại bỏ IDs hợp lệ; `meeting_type`/`meeting_link` không có trong payload; không auto-search khi switch offline; không hiển thị skipped; không validate min 15 phút |
| `create-meeting.css` | Thiếu style `.cm-skipped-notice` |

---

## STEP 1 — Database Migration + Model Update

- [ ] 1. Tạo file SQL migration `005_add_meeting_type_and_link.sql`.

  Tạo file mới tại `c:\Users\ADMIN\Desktop\Meeting\migrations\005_add_meeting_type_and_link.sql` với nội dung:

  ```sql
  USE meeting_db;
  ALTER TABLE meetings ADD COLUMN IF NOT EXISTS meeting_type VARCHAR(10) NOT NULL DEFAULT 'offline' AFTER description;
  ALTER TABLE meetings ADD COLUMN IF NOT EXISTS meeting_link VARCHAR(500) NULL AFTER meeting_type;
  ALTER TABLE meetings DROP FOREIGN KEY IF EXISTS fk_meetings_room;
  ALTER TABLE meetings MODIFY COLUMN room_id INT NULL;
  ALTER TABLE meetings ADD CONSTRAINT fk_meetings_room FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL ON UPDATE CASCADE;
  ```

  **Files:** `c:\Users\ADMIN\Desktop\Meeting\migrations\005_add_meeting_type_and_link.sql`

- [ ] 2. Cập nhật `app/models/meeting.py` để phản ánh schema mới.

  **Các thay đổi cụ thể trong file (giữ nguyên phần còn lại):**

  - Dòng hiện tại (~line 22): `room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)`
    → Đổi thành: `room_id = Column(Integer, ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True, index=True)`

  - Sau field `description` (line 20), thêm 2 field mới:
    ```python
    meeting_type = Column(String(10), nullable=False, default='offline')
    meeting_link = Column(String(500), nullable=True)
    ```

  **Giữ nguyên:** Tất cả relationships, `__tablename__`, `MeetingParticipant`, các field khác.

  **Files:** `c:\Users\ADMIN\Desktop\Meeting\app\models\meeting.py`

  **Verify:** `python -c "from app.models.meeting import Meeting; print(Meeting.meeting_type, Meeting.meeting_link, Meeting.room_id)"` không raise ImportError. Nếu có DB kết nối: chạy migration SQL và kiểm tra `DESCRIBE meetings;` thấy 2 cột mới + room_id nullable.

---

## STEP 2 — Schemas + Service Logic

- [ ] 3. Cập nhật `app/schemas/meeting.py` — thêm fields và schema mới.

  **Thay đổi tại `MeetingCreateRequest` (hiện tại dòng 10–18):**
  - Đổi `room_id: int` → `room_id: Optional[int] = None` (bỏ required, vì online meeting không cần)
  - Thêm 2 field sau `description`:
    ```python
    meeting_type: str = 'offline'
    meeting_link: Optional[str] = None
    ```
  - Thêm validator cho `meeting_type`:
    ```python
    @field_validator('meeting_type')
    @classmethod
    def validate_meeting_type(cls, v):
        if v not in ('online', 'offline'):
            raise ValueError("meeting_type phải là 'online' hoặc 'offline'")
        return v
    ```

  **Thay đổi tại `MeetingResponse` (hiện tại dòng 22–35):**
  - Đổi `room_id: int` → `room_id: Optional[int] = None`
  - Thêm 2 field mới:
    ```python
    meeting_type: str = 'offline'
    meeting_link: Optional[str] = None
    ```

  **Thêm class mới `MeetingCreateResponse` sau `MeetingResponse`:**
  ```python
  class MeetingCreateResponse(BaseModel):
      created: List[MeetingResponse]
      skipped: List[dict]
  ```

  **Giữ nguyên:** `FrequentUserResponse`, `NotificationResponse`, `SuggestTimeRequest`, `TimeSlot`, `SuggestTimeResponse`, validator `parse_equipments`.

  **Files:** `c:\Users\ADMIN\Desktop\Meeting\app\schemas\meeting.py`

- [ ] 4. Cập nhật `app/services/meeting_service.py` — 7 fix quan trọng.

  **Import cần thêm ở đầu file:**
  ```python
  import calendar
  from app.models.meeting import MeetingParticipant
  ```

  **Fix A — Validate meeting_type (thêm vào đầu method `create_meeting`, sau kiểm tra `start_time < now`):**
  ```python
  meeting_type = getattr(payload, 'meeting_type', 'offline') or 'offline'
  meeting_link = getattr(payload, 'meeting_link', None)

  if meeting_type == 'online':
      if not meeting_link:
          raise HTTPException(status_code=400, detail="Cuộc họp online cần có meeting_link!")
      room = None  # online không cần phòng
  else:  # offline
      if not payload.room_id:
          raise HTTPException(status_code=400, detail="Cuộc họp offline cần chọn phòng họp!")
      room = db.query(Room).filter(Room.id == payload.room_id, Room.is_active == True).first()
      if not room:
          raise HTTPException(status_code=400, detail="Phòng họp không tồn tại hoặc đã bị ngưng hoạt động!")
  ```
  → **Xóa block kiểm tra phòng hiện tại** (lines ~40–46 kiểm tra room cứng nhắc) vì đã được xử lý trong Fix A.

  **Fix B — Monthly recurrence dùng calendar (thay `timedelta(days=30)` trong vòng lặp):**
  ```python
  elif recurrence_type in ("monthly", "until_changed"):
      # Tính đúng ngày tháng tiếp theo bằng calendar arithmetic
      year = current_start.year
      month = current_start.month + 1
      if month > 12:
          month = 1
          year += 1
      day = min(current_start.day, calendar.monthrange(year, month)[1])
      delta = current_start.replace(year=year, month=month, day=day) - current_start
      current_start += delta
      current_end += delta
  ```

  **Fix C — Skip conflict thay vì reject toàn bộ (thay block `if overlapping_meeting`):**
  - Khai báo `skipped = []` trước vòng lặp `for s_time, e_time in meeting_dates`.
  - Thay đoạn raise HTTPException khi conflict bằng:
    ```python
    if overlapping_meeting:
        date_str = s_time.strftime("%d/%m/%Y lúc %H:%M")
        skipped.append({
            "date": date_str,
            "reason": f"Phòng đã có lịch vào {date_str}"
        })
        continue  # bỏ qua occurrence này, tiếp tục tạo những cái khác
    ```
  - Sau vòng lặp, thêm guard:
    ```python
    if not created_meetings:
        db.rollback()
        raise HTTPException(status_code=400, detail="Tất cả các mốc thời gian đều bị xung đột lịch phòng!")
    ```

  **Fix D — Lưu participants sau `db.flush()` (thêm ngay sau block lưu equipments):**
  ```python
  participant_ids = getattr(payload, 'participant_ids', []) or []
  for pid in participant_ids:
      if pid == organizer_id:
          continue  # không thêm organizer vào participants
      participant = MeetingParticipant(
          meeting_id=new_meeting.id,
          user_id=pid
      )
      db.add(participant)
  ```

  **Fix E — Không check room conflict khi online (trong vòng lặp `for s_time, e_time`):**
  ```python
  # Chỉ kiểm tra conflict phòng khi offline
  if meeting_type == 'offline':
      overlapping_meeting = db.query(Meeting).filter(
          Meeting.room_id == payload.room_id,
          ...
      ).first()
      if overlapping_meeting:
          ...  # skip logic từ Fix C
  ```

  **Fix F — Truyền `meeting_type` và `meeting_link` vào `Meeting(...)` constructor:**
  ```python
  new_meeting = Meeting(
      title=payload.title,
      description=payload.description,
      room_id=payload.room_id if meeting_type == 'offline' else None,
      meeting_type=meeting_type,
      meeting_link=meeting_link,
      organizer_id=organizer_id,
      start_time=s_time,
      end_time=e_time,
      is_recurring=recurrence_type not in (None, "none"),
      recurring_type=recurrence_type if recurrence_type != "none" else None,
      status="scheduled"
  )
  ```

  **Fix G — Return dict thay vì list + thêm alias `suggest_time`:**
  - Đổi `return created_meetings` cuối method thành:
    ```python
    return {'created': created_meetings, 'skipped': skipped}
    ```
  - Thêm alias method sau `calculate_suggested_times`:
    ```python
    @staticmethod
    def suggest_time(db: Session, payload):
        return MeetingService.calculate_suggested_times(
            db=db,
            participant_ids=payload.participant_ids,
            date_str=payload.date,
            duration_minutes=payload.duration_minutes
        )
    ```

  **Files:** `c:\Users\ADMIN\Desktop\Meeting\app\services\meeting_service.py`

  **Verify:** `python -c "from app.services.meeting_service import MeetingService; print('OK')"` không raise ImportError.

---

## STEP 3 — Router Update

- [ ] 5. Cập nhật `app/routers/meetings.py` — 3 fix.

  **Fix A — Import `MeetingCreateResponse`:**
  Thêm `MeetingCreateResponse` vào import block từ `app.schemas.meeting`:
  ```python
  from app.schemas.meeting import (
      MeetingCreateRequest,
      MeetingCreateResponse,
      MeetingResponse,
      SuggestTimeRequest,
      SuggestTimeResponse,
  )
  ```

  **Fix B — Endpoint GET `""` (dòng ~20–29) trả sai kiểu:**
  Hiện tại: `response_model=List[RoomResponse]` và gọi `MeetingService.get_all_active_rooms(db)`.
  → Đổi thành trả meetings, hoặc xóa endpoint này vì đã có GET `/` bên dưới. **Quyết định: xóa endpoint GET `""` vì GET `/` đã cover đúng chức năng.**
  
  Xóa toàn bộ block:
  ```python
  @router.get(
      "",
      response_model=List[RoomResponse],
      ...
  )
  def list_rooms(db: Session = Depends(get_db)):
      return MeetingService.get_all_active_rooms(db)
  ```
  Đồng thời xóa import `RoomResponse` từ `app.schemas.room` nếu không dùng ở đâu khác.

  **Fix C — Endpoint POST `/book` đổi response_model:**
  ```python
  @router.post(
      "/book",
      response_model=MeetingCreateResponse,   # ← đổi từ List[MeetingResponse]
      status_code=status.HTTP_201_CREATED,
      ...
  )
  def create_meeting(...):
      result = MeetingService.create_meeting(...)   # giờ trả dict
      
      # Gửi notification dùng result['created'] thay vì created_meetings
      if payload.participant_ids and result['created']:
          first_meeting = result['created'][0]
          start_str = first_meeting.start_time.strftime("%H:%M %d/%m/%Y")
          background_tasks.add_task(
              send_meeting_invitation_notifications,
              db=db,
              participant_ids=payload.participant_ids,
              meeting_title=first_meeting.title,
              start_time_str=start_str,
          )
      
      return result   # dict {'created': [...], 'skipped': [...]}
  ```

  **Giữ nguyên:** Tất cả endpoint khác (`/suggest-time`, `/`, `/history`, `/{meeting_id}/cancel`, `/{meeting_id}`).

  **Files:** `c:\Users\ADMIN\Desktop\Meeting\app\routers\meetings.py`

- [ ] 6. Cập nhật `app/routers/rooms.py` — gộp 2 endpoint `/available`.

  **Vấn đề:** Có 2 endpoint:
  - `GET /available` (line ~25) — không có `min_capacity`
  - `GET /available/` (line ~120) — có `min_capacity`, dùng `room_service.get_available_rooms()`

  **Quyết định:** Gộp thành 1 endpoint duy nhất `GET /available`, dùng logic từ `room_service.get_available_rooms()` (đầy đủ hơn).

  Xóa endpoint `GET /available` cũ (không có min_capacity) và **đổi tên** endpoint `GET /available/` (trailing slash) thành `GET /available`:
  ```python
  @router.get("/available", response_model=List[RoomResponse], summary="Tìm phòng trống")
  def read_available_rooms(
      start_time: datetime = Query(...),
      end_time: datetime = Query(...),
      min_capacity: Optional[int] = Query(0),
      db: Session = Depends(get_db),
  ):
      if start_time >= end_time:
          raise HTTPException(status_code=400, detail="Thời gian bắt đầu phải nhỏ hơn thời gian kết thúc!")
      return room_service.get_available_rooms(db=db, start_time=start_time, end_time=end_time, min_capacity=min_capacity)
  ```

  **Giữ nguyên:** Tất cả endpoint khác (`GET /`, `POST /`, `PUT /{room_id}`, `DELETE /{room_id}`).

  **Files:** `c:\Users\ADMIN\Desktop\Meeting\app\routers\rooms.py`

  **Verify:** `python -c "from app.routers.meetings import router; from app.routers.rooms import router as rr; print('Routers OK')"` không raise ImportError.

---

## STEP 4 — Frontend JS Fix

- [ ] 7. Sửa `frontend/js/create-meeting.js` — 7 fix.

  **Fix 1 — Thêm `meeting_type` và `meeting_link` vào payload** (trong `handleCreateMeetingSubmit`, khu vực build `payload` object, hiện tại từ line ~764):

  Sau dòng `room_id: ...`, thêm:
  ```js
  meeting_type: cmState.mode,  // 'online' hoặc 'offline'
  meeting_link: cmState.mode === 'online' ? (cmEl('cmMeetingLink')?.value.trim() || null) : null,
  ```

  **Fix 2 — Xóa early return cho online meeting** (lines ~779–783):
  Xóa block:
  ```js
  if (cmState.mode === 'online') {
      payload.equipments = [];
      rememberAttendees(realParticipantIds);
      showCreateMeetingSuccess();
      return;
  }
  ```
  → Online meeting phải gọi API thật như offline. Giữ `payload.equipments = []` nếu mode === 'online' bằng cách thay vào logic build equipments:
  ```js
  equipments: cmState.mode === 'online' ? [] : Object.entries(cmState.borrowQty)
      .filter(([, qty]) => qty > 0)
      .map(([equipment_id, quantity]) => ({ equipment_id: parseInt(equipment_id, 10), quantity })),
  ```

  **Fix 3 — Xóa `mockIds` filter** (lines ~771–774), gửi tất cả integer IDs:
  Xóa:
  ```js
  const mockIds = new Set(CM_MOCK_USERS.map(u => u.id));
  const realParticipantIds = cmState.attendees
      .map(a => a.id)
      .filter(id => Number.isInteger(id) && !mockIds.has(id));
  ```
  Thay bằng:
  ```js
  const realParticipantIds = cmState.attendees
      .map(a => a.id)
      .filter(id => Number.isInteger(id));
  ```

  **Fix 4 — Auto-search phòng khi `setCreateMeetingMode('offline')`:**
  Trong function `setCreateMeetingMode(mode)`, sau dòng `updateCreateMeetingSummary()`, thêm:
  ```js
  if (mode === 'offline') {
      const { date, start, end } = cmGetTimes();
      if (date && start && end) {
          searchMatchingRooms();
      }
  }
  ```

  **Fix 5 — Room search thêm `min_capacity` vào query params** (trong `searchMatchingRooms()`, khu vực build `params`):
  ```js
  const params = new URLSearchParams({
      start_time: `${date}T${start}:00`,
      end_time: `${date}T${end}:00`,
      min_capacity: String(cmNeededSeats()),   // ← thêm dòng này
  });
  ```

  **Fix 6 — Hiển thị `skipped` occurrences sau tạo thành công** (trong `handleCreateMeetingSubmit`, sau `if (!res.ok)` block, trong try block):
  Thay:
  ```js
  rememberAttendees(realParticipantIds);
  showCreateMeetingSuccess();
  ```
  Bằng:
  ```js
  const result = await res.json();
  rememberAttendees(realParticipantIds);
  showCreateMeetingSuccess();

  // Hiển thị skipped nếu có
  if (result.skipped && result.skipped.length > 0) {
      const skipDates = result.skipped.map(s => s.date || s.reason || JSON.stringify(s)).join(', ');
      const noticeEl = document.createElement('div');
      noticeEl.className = 'cm-skipped-notice';
      noticeEl.textContent = `⚠ ${result.skipped.length} khung giờ bị bỏ qua do xung đột: ${skipDates}`;
      cmEl('cmDialog')?.appendChild(noticeEl);
  }
  ```

  **Fix 7 — Validate min 15 phút duration** (trong `validateCreateMeeting()`):
  Sau block kiểm tra `end <= start`, thêm:
  ```js
  if (date && start && end) {
      const startMs = new Date(`${date}T${start}:00`).getTime();
      const endMs = new Date(`${date}T${end}:00`).getTime();
      if (endMs - startMs < 15 * 60 * 1000) {
          showFormError('Cuộc họp phải có thời lượng tối thiểu 15 phút.');
          ok = false;
      }
  }
  ```

  **Files:** `c:\Users\ADMIN\Desktop\Meeting\frontend\js\create-meeting.js`

  **Verify:** Mở browser console, gọi `openCreateMeeting()`, kiểm tra không có JS errors. Test flow: chọn mode online → không early return → gọi API. Test validate duration < 15 phút → hiển thị error.

---

## STEP 5 — CSS Minor Update

- [ ] 8. Thêm style `.cm-skipped-notice` vào `frontend/css/create-meeting.css`.

  Append vào cuối file (sau CSS rule cuối cùng):
  ```css
  /* Thông báo các lịch bị bỏ qua (skipped occurrences) */
  .cm-skipped-notice {
      background: var(--cm-warning-soft);
      border: 1px solid #fde68a;
      border-radius: var(--cm-radius);
      padding: 12px 16px;
      font-size: 13px;
      color: var(--cm-warning);
      margin-top: 12px;
  }
  ```

  CSS sử dụng các biến đã khai báo trong `:root` (`--cm-warning-soft: #fffbeb`, `--cm-warning: #b45309`, `--cm-radius: 10px`) — không cần thêm biến mới.

  **Files:** `c:\Users\ADMIN\Desktop\Meeting\frontend\css\create-meeting.css`

  **Verify:** Mở file HTML của create-meeting trong browser, tạo element `<div class="cm-skipped-notice">Test</div>` qua DevTools console, kiểm tra style áp dụng đúng (nền vàng nhạt, chữ vàng đậm, border vàng).

---

## Ghi chú thứ tự dependency

- STEP 1 phải hoàn thành trước STEP 2 (model phải có field mới trước khi service dùng chúng).
- STEP 2 phải hoàn thành trước STEP 3 (schema `MeetingCreateResponse` phải tồn tại trước khi router import).
- STEP 3 và STEP 4 có thể làm song song (backend router độc lập với frontend JS).
- STEP 5 độc lập hoàn toàn, có thể làm bất kỳ lúc nào.
- Không cần cài thêm dependency: `calendar` là stdlib Python, `python-dateutil` không có trong `requirements.txt` và không cần thiết.
