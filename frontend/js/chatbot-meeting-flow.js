(() => {
    const normalize = value => String(value || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/đ/g, 'd')
        .toLocaleLowerCase('vi');

    const localDateValue = date => [
        date.getFullYear(),
        String(date.getMonth() + 1).padStart(2, '0'),
        String(date.getDate()).padStart(2, '0'),
    ].join('-');

    const localTimeValue = date => [
        String(date.getHours()).padStart(2, '0'),
        String(date.getMinutes()).padStart(2, '0'),
    ].join(':');

    function defaultSchedule() {
        const start = new Date();
        start.setSeconds(0, 0);
        start.setMinutes(start.getMinutes() < 30 ? 30 : 0);
        if (start.getMinutes() === 0) start.setHours(start.getHours() + 1);
        if (start.getHours() < 8) start.setHours(9, 0);
        if (start.getHours() >= 17) {
            start.setDate(start.getDate() + 1);
            start.setHours(9, 0);
        }
        const end = new Date(start.getTime() + 60 * 60 * 1000);
        return { date: localDateValue(start), start: localTimeValue(start), end: localTimeValue(end) };
    }

    function extractPromptValues(content) {
        const normalized = normalize(content);
        const schedule = defaultSchedule();
        const timeMatch = normalized.match(/\b([01]?\d|2[0-3])\s*(?:h|gio)(?:\s*([0-5]\d))?\b/);
        if (timeMatch) {
            const requestedStart = new Date();
            requestedStart.setHours(Number(timeMatch[1]), Number(timeMatch[2] || 0), 0, 0);
            if (requestedStart <= new Date()) requestedStart.setDate(requestedStart.getDate() + 1);
            schedule.date = localDateValue(requestedStart);
            schedule.start = localTimeValue(requestedStart);
            const requestedEnd = new Date(requestedStart.getTime() + 60 * 60 * 1000);
            schedule.end = localTimeValue(requestedEnd);
            if (localDateValue(requestedEnd) !== schedule.date) {
                schedule.end = '23:59';
            }
        }

        const isoDate = normalized.match(/\b(20\d{2})-(\d{2})-(\d{2})\b/);
        const localDate = normalized.match(/\bngay\s+(\d{1,2})[/-](\d{1,2})(?:[/-](20\d{2}))?\b/);
        if (normalized.includes('hom nay')) schedule.date = localDateValue(new Date());
        if (normalized.includes('ngay mai') || normalized.includes('mai')) {
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            schedule.date = localDateValue(tomorrow);
        }
        if (isoDate) schedule.date = `${isoDate[1]}-${isoDate[2]}-${isoDate[3]}`;
        if (localDate) {
            const year = localDate[3] || String(new Date().getFullYear());
            schedule.date = `${year}-${String(localDate[2]).padStart(2, '0')}-${String(localDate[1]).padStart(2, '0')}`;
        }

        const equipmentKeys = [];
        if (/\b(tv|tivi|television)\b/.test(normalized)) equipmentKeys.push('tv');
        if (/\b(projector|may chieu)\b/.test(normalized)) equipmentKeys.push('projector');
        if (/\b(mic|micro|microphone)\b/.test(normalized)) equipmentKeys.push('mic');
        if (/\b(whiteboard|bang trang)\b/.test(normalized)) equipmentKeys.push('whiteboard');

        const isOnline = /\b(online|truc tuyen|hop truc tuyen)\b/.test(normalized);
        return { ...schedule, equipmentKeys, isOnline };
    }

    function addThinkingMessage(content) {
        appendAiChatMessage({ sender: 'user', content });
        const thinking = appendAiChatMessage({
            sender: 'bot',
            content: 'AI đang đọc yêu cầu',
        });
        thinking.row.classList.add('is-thinking');
        thinking.text.setAttribute('aria-live', 'polite');
        return thinking;
    }

    async function ensureChatReady() {
        if (document.getElementById('ai-chat-drawer')?.hidden) {
            await window.openAiChatDrawer?.();
        }
        if (!activeChatSessionId && typeof createAiChatSession === 'function') {
            await createAiChatSession();
        }
        if (!activeChatSessionId) {
            throw new Error('Không thể mở phiên trò chuyện. Vui lòng thử lại.');
        }
    }

    async function showMeetingForm(content, flowType = null) {
        let thinking = addThinkingMessage(content);
        try {
            await ensureChatReady();
            if (!thinking.row.isConnected) thinking = addThinkingMessage(content);
            const options = await chatApiRequest('/meeting-form-options');
            thinking.text.textContent = 'Hoàn tất. Chọn nhóm và thời gian để tiếp tục.';
            thinking.row.classList.remove('is-thinking');
            thinking.interactivePreview = createFormCard(options, content, flowType);
            thinking.bubble.appendChild(thinking.interactivePreview);
            scrollAiChatToLatest();
        } catch (error) {
            thinking.text.textContent = error.message || 'Không thể tải dữ liệu biểu mẫu.';
            thinking.row.classList.remove('is-thinking');
        }
    }

    function createLabel(text, control) {
        const label = document.createElement('label');
        label.className = 'ai-meeting-field';
        const title = document.createElement('span');
        title.textContent = text;
        label.append(title, control);
        return label;
    }

    function createFormCard(options, prompt, flowType) {
        const card = document.createElement('form');
        card.className = 'ai-chat-preview ai-chat-meeting-form';
        const heading = document.createElement('h3');
        heading.textContent = 'Tạo cuộc họp';
        const summary = document.createElement('p');
        summary.className = 'ai-meeting-intro';
        summary.textContent = 'Thông tin bạn đã nêu được điền sẵn. Kiểm tra lại trước khi tạo.';

        const normalized = normalize(prompt);
        const scopeType = document.createElement('select');
        scopeType.name = 'group_type';
        scopeType.setAttribute('aria-label', 'Loại nhóm');
        [
            ['department', 'Phòng ban'],
            ['project', 'Nhóm dự án'],
        ].forEach(([value, label]) => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = label;
            scopeType.appendChild(option);
        });
        if (flowType === 'project' || normalized.includes('nhom du an') || normalized.includes('du an')) {
            scopeType.value = 'project';
        }
        if (flowType === 'department' || normalized.includes('phong ban')) {
            scopeType.value = 'department';
        }

        const group = document.createElement('select');
        group.name = 'group_id';
        group.required = true;
        group.setAttribute('aria-label', 'Phòng ban hoặc nhóm dự án');
        const fillGroups = () => {
            const groups = scopeType.value === 'department'
                ? options.departments || []
                : options.projects || [];
            group.replaceChildren();
            const placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.textContent = groups.length ? 'Chọn một nhóm' : 'Chưa có nhóm nào';
            group.appendChild(placeholder);
            groups.forEach(item => {
                const option = document.createElement('option');
                option.value = String(item.id);
                option.textContent = item.name;
                option.dataset.code = item.code || '';
                group.appendChild(option);
            });
            const match = groups.find(item => {
                const searchable = normalize(`${item.name} ${item.code || ''}`);
                return searchable.length > 1 && normalized.includes(searchable);
            });
            if (match) group.value = String(match.id);
        };
        fillGroups();
        scopeType.addEventListener('change', fillGroups);

        const groupControls = document.createElement('div');
        groupControls.className = 'ai-meeting-group-controls';
        groupControls.append(
            createLabel('Loại nhóm', scopeType),
            createLabel('Phòng ban / nhóm dự án', group),
        );

        const titleInput = document.createElement('input');
        titleInput.name = 'title';
        titleInput.type = 'text';
        titleInput.maxLength = 200;
        titleInput.required = true;
        titleInput.value = scopeType.value === 'project'
            ? 'Họp nhóm dự án'
            : 'Họp phòng ban';
        scopeType.addEventListener('change', () => {
            if (titleInput.value === 'Họp phòng ban' || titleInput.value === 'Họp nhóm dự án') {
                titleInput.value = scopeType.value === 'project'
                    ? 'Họp nhóm dự án'
                    : 'Họp phòng ban';
            }
        });

        const schedule = extractPromptValues(prompt);
        const dateInput = document.createElement('input');
        dateInput.name = 'date';
        dateInput.type = 'date';
        dateInput.required = true;
        dateInput.value = schedule.date;
        const startInput = document.createElement('input');
        startInput.name = 'start_time';
        startInput.type = 'time';
        startInput.required = true;
        startInput.value = schedule.start;
        const endInput = document.createElement('input');
        endInput.name = 'end_time';
        endInput.type = 'time';
        endInput.required = true;
        endInput.value = schedule.end;

        const scheduleControls = document.createElement('div');
        scheduleControls.className = 'ai-meeting-time-controls';
        scheduleControls.append(
            createLabel('Ngày họp', dateInput),
            createLabel('Bắt đầu', startInput),
            createLabel('Kết thúc', endInput),
        );

        const equipmentSection = document.createElement('fieldset');
        equipmentSection.className = 'ai-meeting-equipment';
        const equipmentLegend = document.createElement('legend');
        equipmentLegend.textContent = 'Thiết bị cần dùng';
        const equipmentInputs = [];
        (options.equipment || []).forEach(item => {
            const label = document.createElement('label');
            label.className = 'ai-meeting-check';
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = item.id ? String(item.id) : '';
            checkbox.dataset.key = item.key;
            checkbox.checked = schedule.equipmentKeys.includes(item.key);
            checkbox.disabled = !item.available;
            const text = document.createElement('span');
            text.textContent = item.available ? item.label : `${item.label} (chưa có trong kho)`;
            label.append(checkbox, text);
            equipmentSection.appendChild(label);
            equipmentInputs.push(checkbox);
        });
        equipmentSection.prepend(equipmentLegend);

        const onlineLabel = document.createElement('label');
        onlineLabel.className = 'ai-meeting-online-toggle';
        const onlineInput = document.createElement('input');
        onlineInput.type = 'checkbox';
        onlineInput.name = 'online_meeting';
        onlineInput.checked = schedule.isOnline;
        const onlineText = document.createElement('span');
        onlineText.textContent = 'Tạo cuộc họp trực tuyến và gửi link tham gia';
        onlineLabel.append(onlineInput, onlineText);
        onlineInput.addEventListener('change', () => {
            equipmentInputs.forEach(input => {
                input.disabled = onlineInput.checked || !input.value;
            });
        });
        if (onlineInput.checked) {
            equipmentInputs.forEach(input => { input.disabled = true; });
        }

        const status = document.createElement('p');
        status.className = 'ai-chat-confirm-result';
        status.setAttribute('role', 'status');
        const suggestions = document.createElement('div');
        suggestions.className = 'ai-meeting-suggestions';
        suggestions.hidden = true;

        const submit = document.createElement('button');
        submit.type = 'submit';
        submit.className = 'ai-chat-confirm-button';
        submit.textContent = 'Tạo cuộc họp';

        card.append(
            heading,
            summary,
            groupControls,
            createLabel('Tên cuộc họp', titleInput),
            scheduleControls,
            equipmentSection,
            onlineLabel,
            status,
            suggestions,
            submit,
        );

        card.addEventListener('submit', async event => {
            event.preventDefault();
            if (!card.reportValidity() || submit.disabled) return;
            const [year, month, day] = dateInput.value.split('-').map(Number);
            const toLocalDateTime = (dateValue, timeValue) => `${dateValue}T${timeValue}:00`;
            const selectedEquipment = equipmentInputs
                .filter(input => input.checked && input.value)
                .map(input => Number(input.value));
            submit.disabled = true;
            submit.textContent = 'Đang kiểm tra phòng và lịch...';
            status.textContent = 'Đang đọc dữ liệu phòng ban và kiểm tra lịch...';
            status.classList.remove('is-error');
            suggestions.replaceChildren();
            suggestions.hidden = true;
            try {
                const result = await submitMeetingForm({
                    session_id: activeChatSessionId,
                    source_prompt: prompt,
                    group_type: scopeType.value,
                    group_id: Number(group.value),
                    title: titleInput.value.trim(),
                    start_time: toLocalDateTime(
                        `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`,
                        startInput.value,
                    ),
                    end_time: toLocalDateTime(
                        `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`,
                        endInput.value,
                    ),
                    equipment_ids: onlineInput.checked ? [] : selectedEquipment,
                    online_meeting: onlineInput.checked,
                });
                const meeting = Array.isArray(result) ? result[0] : null;
                status.classList.remove('is-error');
                status.textContent = meeting
                    ? `Đã tạo cuộc họp${meeting.room_id ? ` tại ${meeting.room_name || 'phòng đã chọn'}` : ''} và gửi lời mời đến ${selectedGroupName(scopeType, group, options)}.`
                    : 'Đã tạo cuộc họp và gửi lời mời.';
                if (meeting?.meeting_link || meeting?.online_link) {
                    const link = document.createElement('a');
                    link.className = 'ai-meeting-link';
                    link.href = meeting.meeting_link || meeting.online_link;
                    link.target = '_blank';
                    link.rel = 'noopener noreferrer';
                    link.textContent = `Tham gia cuộc họp: ${link.href}`;
                    card.appendChild(link);
                }
                submit.textContent = 'Đã tạo cuộc họp';
            } catch (error) {
                status.classList.add('is-error');
                status.textContent = error.message || 'Không thể tạo cuộc họp.';
                if (Array.isArray(error.suggestions) && error.suggestions.length) {
                    suggestions.hidden = false;
                    const label = document.createElement('p');
                    label.textContent = 'Khung giờ / phòng gần nhất còn trống:';
                    suggestions.appendChild(label);
                    error.suggestions.forEach(item => {
                        const button = document.createElement('button');
                        button.type = 'button';
                        button.className = 'ai-meeting-suggestion';
                        const suggestionStart = new Date(item.start_time);
                        const suggestionEnd = new Date(item.end_time);
                        button.textContent = `${item.room_name} · ${suggestionStart.toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}–${suggestionEnd.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}`;
                        button.addEventListener('click', () => {
                            const localStart = new Date(item.start_time);
                            const localEnd = new Date(item.end_time);
                            dateInput.value = localDateValue(localStart);
                            startInput.value = localTimeValue(localStart);
                            endInput.value = localTimeValue(localEnd);
                            status.textContent = 'Đã cập nhật khung giờ gợi ý. Chọn “Tạo cuộc họp” để xác nhận.';
                            status.classList.remove('is-error');
                            suggestions.hidden = true;
                        });
                        suggestions.appendChild(button);
                    });
                }
                submit.textContent = 'Thử lại';
                submit.disabled = false;
            }
        });

        return card;
    }

    function selectedGroupName(typeControl, groupControl, options) {
        const items = typeControl.value === 'department'
            ? options.departments || []
            : options.projects || [];
        return items.find(item => String(item.id) === groupControl.value)?.name || 'nhóm đã chọn';
    }

    async function submitMeetingForm(payload) {
        const response = await fetchAPI(`${API_BASE}/v1/chatbot/meetings`, {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${localStorage.getItem('token') || localStorage.getItem('access_token') || ''}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok) {
            const detail = result?.detail;
            const error = new Error(
                typeof detail === 'string'
                    ? detail
                    : detail?.message || result?.message || `Yêu cầu thất bại (${response.status}).`,
            );
            error.suggestions = detail?.suggestions;
            throw error;
        }
        return result;
    }

    function isNaturalMeetingPrompt(content) {
        const normalized = normalize(content);
        return /\b(tao|lap|to chuc|dat)\b/.test(normalized)
            && /\b(hop|cuoc hop|meeting)\b/.test(normalized);
    }

    document.addEventListener('click', event => {
        const button = event.target.closest('[data-ai-chat-flow]');
        if (!button) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        const prompt = button.dataset.aiChatPrompt || 'Tạo cuộc họp nhóm';
        showMeetingForm(prompt, button.dataset.aiChatFlow);
    }, true);

    document.addEventListener('submit', event => {
        if (event.target.id !== 'ai-chat-form') return;
        const input = document.getElementById('ai-chat-input');
        const content = input?.value.trim() || '';
        if (!content || !isNaturalMeetingPrompt(content)) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        input.value = '';
        showMeetingForm(content);
    }, true);
})();
