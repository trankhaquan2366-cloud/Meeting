/* ==========================================================================\n   NOTIFICATION MANAGEMENT\n   ========================================================================== */
let activeNotificationCategory = 'all';
let activeNotificationPageCategory = 'all';
let notificationMarkAllInProgress = false;
let notificationUnreadCounts = {
    total: 0,
    by_category: { reminder: 0, response: 0, change: 0, system: 0 },
};

function initializeNotifications() {
    const popup = document.getElementById('notificationPopup');
    if (popup) {
        popup.addEventListener('click', event => {
            const markAllButton = event.target.closest('button[data-mark-all-notifications]');
            if (markAllButton) {
                markAllNotificationsAsRead();
                return;
            }
            const categoryButton = event.target.closest('button[data-notification-category]');
            if (categoryButton) {
                event.stopPropagation();
                activeNotificationCategory = categoryButton.dataset.notificationCategory;
                renderNotifications(userNotifications);
                popup.querySelector(`button[data-notification-category="${activeNotificationCategory}"]`)?.focus();
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
        popup.addEventListener('keydown', event => {
            const tab = event.target.closest('button[data-notification-category]');
            if (!tab || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
            const tabs = Array.from(popup.querySelectorAll('button[data-notification-category]'));
            const currentIndex = tabs.indexOf(tab);
            const nextIndex = event.key === 'Home' ? 0
                : event.key === 'End' ? tabs.length - 1
                    : (currentIndex + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
            event.preventDefault();
            tabs[nextIndex]?.click();
        });
    }
    const pageTabs = document.getElementById('pageNotifTabs');
    pageTabs?.addEventListener('click', event => {
        const categoryButton = event.target.closest('button[data-notification-category]');
        if (!categoryButton) return;
        activeNotificationPageCategory = categoryButton.dataset.notificationCategory;
        renderNotificationCenter();
    });
    pageTabs?.addEventListener('keydown', event => {
        const tab = event.target.closest('button[data-notification-category]');
        if (!tab || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
        const tabs = Array.from(pageTabs.querySelectorAll('button[data-notification-category]'));
        const index = tabs.indexOf(tab);
        const nextIndex = event.key === 'Home' ? 0
            : event.key === 'End' ? tabs.length - 1
                : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
        event.preventDefault();
        tabs[nextIndex]?.click();
        tabs[nextIndex]?.focus();
    });
    const pageList = document.getElementById('pageNotifList');
    pageList?.addEventListener('click', event => {
        const markAllButton = event.target.closest('button[data-mark-all-notifications]');
        if (markAllButton) {
            markAllNotificationsAsRead();
            return;
        }
        const rsvpButton = event.target.closest('button[data-notification-rsvp]');
        if (rsvpButton) {
            event.preventDefault();
            respondToMeeting(
                Number(rsvpButton.dataset.rsvpMeeting),
                rsvpButton.dataset.notificationRsvp,
                Number(rsvpButton.dataset.notificationId),
            );
            return;
        }
        const notificationButton = event.target.closest('button[data-notification-id]');
        if (notificationButton) markNotificationAsRead(Number(notificationButton.dataset.notificationId));
    });
    document.getElementById('pageMarkAllNotifications')?.addEventListener(
        'click',
        markAllNotificationsAsRead,
    );
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
        const [response, countsResponse] = await Promise.all([
            fetchAPI(`${API_BASE}/notifications/?limit=30&offset=0`, {
                headers: { Authorization: `Bearer ${token}` },
            }),
            fetchAPI(`${API_BASE}/notifications/unread-count`, {
                headers: { Authorization: `Bearer ${token}` },
            }),
        ]);
        if (handleUnauthorizedResponse(response) || handleUnauthorizedResponse(countsResponse)) return false;
        if (!response.ok) {
            const message = await apiErrorMessage(response, 'Không thể tải thông báo.');
            if (requestVersion === notificationFetchVersion) {
                notificationUnreadCounts = emptyNotificationCounts();
                renderNotifications(userNotifications);
                renderNotificationCenter();
                renderNotificationError(message);
            }
            return false;
        }

        const notifications = await response.json();
        if (requestVersion !== notificationFetchVersion) return false;
        userNotifications = Array.isArray(notifications) ? notifications.filter(Boolean) : [];
        notificationUnreadCounts = countsResponse.ok
            ? await countsResponse.json().catch(() => null)
            : null;
        if (!notificationUnreadCounts || typeof notificationUnreadCounts !== 'object') {
            notificationUnreadCounts = countUnreadNotifications(userNotifications);
        }
        clearNotificationError();
        renderNotifications(userNotifications);
        renderNotificationCenter();
        return true;
    } catch (error) {
        console.error('Lỗi lấy danh sách thông báo:', error);
        if (requestVersion === notificationFetchVersion) {
            // Không để trang trắng: dựng lại khung + Empty State kèm cảnh báo.
            notificationUnreadCounts = emptyNotificationCounts();
            renderNotifications(userNotifications);
            renderNotificationCenter();
            renderNotificationError('Không thể kết nối máy chủ để tải thông báo.');
        }
        return false;
    }
}

function emptyNotificationCounts() {
    return { total: 0, by_category: { reminder: 0, response: 0, change: 0, system: 0 } };
}

function countUnreadNotifications(notifications) {
    const counts = { total: 0, by_category: { reminder: 0, response: 0, change: 0, system: 0 } };
    notifications.forEach(notification => {
        if (notification.is_read) return;
        counts.total += 1;
        const category = counts.by_category[notification.category] === undefined
            ? 'system' : notification.category;
        counts.by_category[category] += 1;
    });
    return counts;
}

async function markNotificationAsRead(notificationId) {
    const notification = userNotifications.find(item => Number(item.id) === notificationId);
    if (!notification || notification.is_read) return;

    try {
        const response = await fetchAPI(`${API_BASE}/notifications/${notificationId}/read`, {
            method: 'PUT',
            headers: { Authorization: `Bearer ${getAuthToken()}` },
        });
        if (handleUnauthorizedResponse(response)) return;
        if (!response.ok) {
            alert(await apiErrorMessage(response, 'Không thể đánh dấu thông báo đã đọc.'));
            return;
        }
        notification.is_read = true;
        await fetchNotifications();
    } catch (error) {
        console.error('Lỗi cập nhật trạng thái thông báo:', error);
        alert('Không thể kết nối máy chủ để cập nhật thông báo.');
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
            if (parsed.protocol === 'http:' || parsed.protocol === 'https:') safeUrl = parsed.href;
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
            // Look for a supported meeting URL in the message instead.
        }
    }
    const content = String(notification?.content || '');
    const urls = content.match(/https?:\/\/[^\s<>"']+/gi) || [];
    for (const rawUrl of urls) {
        const candidateUrl = rawUrl.replace(/[.,!?;:)\]}]+$/, '');
        try {
            const parsed = new URL(candidateUrl);
            if ((parsed.protocol === 'http:' || parsed.protocol === 'https:')
                && parsed.hostname === 'meet.google.com') return parsed.href;
        } catch (error) {
            continue;
        }
    }
    return '';
}

function renderNotifications(notifications) {
    const popup = document.getElementById('notificationPopup');
    if (!popup) return;

    const items = Array.isArray(notifications) ? notifications.filter(Boolean) : [];
    const unreadCount = Number(notificationUnreadCounts?.total ?? items.filter(item => !item.is_read).length) || 0;
    updateNotificationDot(unreadCount);
    const filtered = activeNotificationCategory === 'all'
        ? items
        : items.filter(item => (item.category || 'system') === activeNotificationCategory);
    popup.innerHTML = `
        ${notificationHeaderHTML(unreadCount)}
        <div class="notification-list">
            ${filtered.length ? filtered.map(notification => {
                const cancelled = ['cancelled', 'canceled'].includes(
                    String(notification.meeting_status || '').trim().toLowerCase()
                );
                const timestampValue = String(notification.created_at || '');
                const utcTimestamp = /(?:Z|[+-]\d{2}:\d{2})$/i.test(timestampValue)
                    ? timestampValue : `${timestampValue}Z`;
                const timestamp = new Date(utcTimestamp);
                const localTimestamp = Number.isNaN(timestamp.getTime())
                    ? 'Thời gian không xác định' : timestamp.toLocaleString();
                const linkedMeeting = cancelled ? null : resolveNotificationMeeting(notification);
                const actions = linkedMeeting ? renderNotificationRsvpActions(notification, linkedMeeting) : '';
                const meetingLink = notificationMeetingLink(notification);
                const joinAction = !cancelled && meetingLink
                    ? `<a class="notification-join-meeting" href="${escapeHtml(meetingLink)}"
                        target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()">Tham gia họp</a>`
                    : '';
                const itemTitle = cancelled ? 'Cuộc họp đã bị hủy' : notification.title;
                const itemContent = cancelled
                    ? `Cuộc họp '${notification.meeting_title || 'này'}' đã bị người tổ chức hủy. Bạn không cần tham gia.`
                    : notification.content;
                return `<article class="notification-entry ${notification.is_read ? '' : 'unread'}">
                    <button type="button" class="notification-item ${notification.is_read ? '' : 'unread'}"
                        data-notification-id="${Number(notification.id)}">
                        <span class="notification-item-title">${escapeHtml(itemTitle)}</span>
                        <span class="notification-item-time">${escapeHtml(localTimestamp)}</span>
                    </button>
                    <div class="notification-item-content">${linkifyNotificationContent(itemContent)}</div>
                    ${joinAction ? `<div class="notification-join-row">${joinAction}</div>` : ''}
                    ${actions}
                </article>`;
            }).join('') : `<div class="notification-empty">${items.length ? 'Không có thông báo trong mục này.' : 'Không có thông báo nào.'}</div>`}
        </div>
    `;
}

function loadNotificationsPage() {
    const list = document.getElementById('pageNotifList');
    if (list) list.setAttribute('aria-busy', 'true');
    renderNotificationCenter();
    const requests = [fetchNotifications()];
    if (typeof fetchMyBookings === 'function') requests.push(fetchMyBookings());
    return Promise.all(requests)
        .catch(error => {
            console.error('Lỗi tải trang thông báo:', error);
            renderNotificationCenter();
            renderNotificationError('Không thể tải thông báo. Vui lòng thử lại.');
            return [];
        })
        .finally(() => {
            const currentList = document.getElementById('pageNotifList');
            if (currentList) currentList.setAttribute('aria-busy', 'false');
        });
}

function renderNotificationCenter() {
    try {
        renderNotificationCenterUnsafe();
    } catch (error) {
        console.error('Lỗi dựng trung tâm thông báo:', error);
        const list = document.getElementById('pageNotifList');
        if (list) {
            list.innerHTML = `<div class="notification-center-empty" role="alert">
                <strong>Không thể hiển thị thông báo.</strong>
                <span>Vui lòng tải lại trang hoặc thử lại sau.</span>
            </div>`;
            list.setAttribute('aria-busy', 'false');
        }
    }
}

function renderNotificationCenterUnsafe() {
    const list = document.getElementById('pageNotifList');
    if (!list) return;

    const items = Array.isArray(userNotifications) ? userNotifications.filter(Boolean) : [];
    const categories = ['all', 'reminder', 'response', 'change'];
    const counts = (notificationUnreadCounts && notificationUnreadCounts.by_category) || {};
    document.querySelectorAll('#pageNotifTabs [data-notification-category]').forEach(tab => {
        const category = tab.dataset.notificationCategory;
        const selected = category === activeNotificationPageCategory;
        tab.classList.toggle('active', selected);
        tab.setAttribute('aria-selected', String(selected));
        tab.tabIndex = selected ? 0 : -1;
        const count = category === 'all'
            ? Number(notificationUnreadCounts.total || 0)
            : Number(counts[category] || 0);
        const badge = tab.querySelector('[data-category-count]');
        if (badge) badge.textContent = count > 99 ? '99+' : String(count);
    });

    const markAllButton = document.getElementById('pageMarkAllNotifications');
    if (markAllButton) markAllButton.disabled = Number(notificationUnreadCounts.total || 0) === 0;
    const filtered = activeNotificationPageCategory === 'all'
        ? items
        : items.filter(notification =>
            (notification.category || 'system') === activeNotificationPageCategory);

    if (!filtered.length) {
        list.innerHTML = `<div class="notification-center-empty">
            <strong>${items.length ? 'Không có thông báo trong mục này.' : 'Chưa có thông báo mới.'}</strong>
            <span>Thông tin cuộc họp sẽ xuất hiện tại đây.</span>
        </div>`;
        list.setAttribute('aria-busy', 'false');
        return;
    }

    list.innerHTML = filtered.map(notification => {
        const cancelled = ['cancelled', 'canceled'].includes(
            String(notification.meeting_status || '').trim().toLowerCase());
        const meeting = cancelled ? null : getNotificationMeeting(notification);
        const timestampValue = String(notification.created_at || '');
        const timestamp = new Date(/(?:Z|[+-]\d{2}:\d{2})$/i.test(timestampValue)
            ? timestampValue : `${timestampValue}Z`);
        const timeLabel = Number.isNaN(timestamp.getTime())
            ? 'Thời gian không xác định'
            : timestamp.toLocaleString('vi-VN', {
                weekday: 'short', day: '2-digit', month: '2-digit',
                hour: '2-digit', minute: '2-digit',
            });
        const itemTitle = cancelled ? 'Cuộc họp đã bị hủy' : notification.title;
        const itemContent = cancelled
            ? `Cuộc họp '${notification.meeting_title || 'này'}' đã bị người tổ chức hủy.`
            : notification.content;
        const category = notification.category || 'system';
        const categoryLabel = {
            reminder: 'Nhắc lịch', response: 'Phản hồi', change: 'Thay đổi', system: 'Hệ thống',
        }[category] || 'Hệ thống';
        const actions = [];

        const isInvitation = /lời mời|mời tham dự|mời tham gia/i.test(
            `${notification.title || ''} ${notification.content || ''}`);
        if (meeting && isInvitation) {
            actions.push(renderNotificationRsvpActions(notification, meeting));
        }
        const joinLink = notificationMeetingLink(notification)
            || (meeting ? bookingSafeLink(meeting.meeting_link || meeting.online_link) : '');
        if (!cancelled && joinLink) {
            actions.push(`<a class="notification-card-action notification-card-action-primary"
                href="${escapeHtml(joinLink)}" target="_blank" rel="noopener noreferrer">Tham gia</a>`);
        } else if (meeting && meeting.room_id && typeof meetingQrActions === 'function') {
            const checkinAction = meetingQrActions(meeting, meeting.is_organizer
                || meeting.my_response_status === 'accepted');
            if (checkinAction) actions.push(checkinAction.replace('Check-in QR', 'Check-in'));
        }

        const sender = meeting?.organizer_name || (category === 'response' ? 'Thành viên cuộc họp' : 'RoomSync');
        return `<article class="notification-center-card ${notification.is_read ? '' : 'unread'}">
            <span class="notification-center-card-mark notification-center-card-mark-${escapeHtml(category)}" aria-hidden="true"></span>
            <div class="notification-center-card-main">
                <div class="notification-center-card-meta">
                    <span class="notification-center-category">${escapeHtml(categoryLabel)}</span>
                    <span>${escapeHtml(sender)}</span>
                    <time datetime="${escapeHtml(timestampValue)}">${escapeHtml(timeLabel)}</time>
                </div>
                <button class="notification-center-title" type="button"
                    data-notification-id="${Number(notification.id)}">
                    ${escapeHtml(itemTitle)}
                    ${notification.is_read ? '' : '<span class="notification-center-unread-dot" aria-label="Chưa đọc"></span>'}
                </button>
                ${notification.meeting_title ? `<p class="notification-center-meeting">${escapeHtml(notification.meeting_title)}</p>` : ''}
                <p class="notification-center-content">${linkifyNotificationContent(itemContent)}</p>
                ${actions.length ? `<div class="notification-center-actions">${actions.join('')}</div>` : ''}
            </div>
        </article>`;
    }).join('');
    list.setAttribute('aria-busy', 'false');
}

function notificationHeaderHTML(unreadCount) {
    const categories = [
        ['all', 'Tất cả', unreadCount],
        ['reminder', 'Nhắc lịch', notificationUnreadCounts.by_category?.reminder || 0],
        ['response', 'Phản hồi', notificationUnreadCounts.by_category?.response || 0],
        ['change', 'Thay đổi & Hủy', notificationUnreadCounts.by_category?.change || 0],
    ];
    return `
        <header class="notification-popup-header">
            <div class="notification-popup-heading">
                <h2>Thông báo</h2>
                <span id="notificationUnreadCount" class="notification-unread-count" aria-live="polite">${unreadCount} chưa đọc</span>
            </div>
            <div class="notification-category-tabs" role="tablist" aria-label="Lọc thông báo">
                ${categories.map(([category, label, count]) => `<button type="button" role="tab"
                    class="notification-category-tab ${activeNotificationCategory === category ? 'active' : ''}"
                    aria-selected="${activeNotificationCategory === category}"
                    tabindex="${activeNotificationCategory === category ? '0' : '-1'}"
                    data-notification-category="${category}">${label}<span>${count}</span></button>`).join('')}
            </div>
            <button class="notification-mark-all" type="button" data-mark-all-notifications
                ${unreadCount === 0 ? 'disabled' : ''}>Đánh dấu tất cả là đã đọc</button>
        </header>
    `;
}

async function markAllNotificationsAsRead() {
    if (notificationMarkAllInProgress) return;
    const unreadNotifications = userNotifications.filter(notification => !notification.is_read);
    if (unreadNotifications.length === 0) {
        updateNotificationDot(0);
        renderNotificationCenter();
        return;
    }

    const previousReadStates = unreadNotifications.map(notification => ({ notification, isRead: notification.is_read }));
    notificationMarkAllInProgress = true;
    unreadNotifications.forEach(notification => { notification.is_read = true; });
    notificationUnreadCounts = { total: 0, by_category: { reminder: 0, response: 0, change: 0, system: 0 } };
    renderNotifications(userNotifications);
    renderNotificationCenter();

    try {
        const token = getAuthToken();
        if (!token) {
            previousReadStates.forEach(({ notification, isRead }) => { notification.is_read = isRead; });
            notificationUnreadCounts = countUnreadNotifications(userNotifications);
            renderNotifications(userNotifications);
            renderNotificationCenter();
            redirectToLogin();
            return;
        }
        const response = await fetchAPI(`${API_BASE}/notifications/read-all`, {
            method: 'PUT',
            headers: { Authorization: `Bearer ${token}` },
        });
        if (handleUnauthorizedResponse(response)) {
            previousReadStates.forEach(({ notification, isRead }) => { notification.is_read = isRead; });
            notificationUnreadCounts = countUnreadNotifications(userNotifications);
            renderNotifications(userNotifications);
            renderNotificationCenter();
            return;
        }
        if (!response.ok) throw new Error(await apiErrorMessage(response, 'Không thể đánh dấu tất cả thông báo đã đọc.'));
        await fetchNotifications();
    } catch (error) {
        previousReadStates.forEach(({ notification, isRead }) => { notification.is_read = isRead; });
        notificationUnreadCounts = countUnreadNotifications(userNotifications);
        renderNotifications(userNotifications);
        renderNotificationCenter();
        renderNotificationError(error.message || 'Không thể đánh dấu tất cả thông báo đã đọc.');
        console.error('Lỗi đánh dấu tất cả thông báo đã đọc:', error);
        showAppToast(error.message || 'Không thể đánh dấu tất cả thông báo đã đọc.', 'error');
    } finally {
        notificationMarkAllInProgress = false;
    }
}

function resolveNotificationMeeting(notification) {
    if (!notification || !String(notification.title || '').toLowerCase().includes('lời mời')) return null;
    const bookings = Array.isArray(myBookings) ? myBookings.filter(Boolean) : [];
    const meetingId = Number(notification.meeting_id);
    if (Number.isInteger(meetingId) && meetingId > 0) {
        return bookings.find(meeting => Number(meeting.id) === meetingId && !meeting.is_organizer)
            || { id: meetingId, is_organizer: false, my_response_status: 'pending' };
    }
    const titleMatch = String(notification.content || '').match(/cuộc họp ['‘](.+?)['’]/i);
    if (!titleMatch) return null;
    const candidates = bookings.filter(meeting => !meeting.is_organizer && String(meeting.title || '') === titleMatch[1]);
    return candidates.length === 1 ? candidates[0] : null;
}

    function getNotificationMeeting(notification) {
        const bookings = Array.isArray(myBookings) ? myBookings.filter(Boolean) : [];
        const meetingId = Number(notification?.meeting_id);
        if (Number.isInteger(meetingId) && meetingId > 0) {
            const meeting = bookings.find(item => Number(item.id) === meetingId);
            if (meeting) return meeting;
        }
        return resolveNotificationMeeting(notification);
    }

function renderNotificationRsvpActions(notification, meeting) {
    const response = getMeetingRsvpStatus(meeting);
    const notificationId = Number(notification.id);
    const meetingId = Number(meeting.id);
    if (response === 'accepted') {
        return `<div class="notification-rsvp-actions"><span class="badge-status accepted">Đã đồng ý</span>
            <button type="button" class="btn-rsvp btn-reject" data-rsvp-meeting="${meetingId}"
                data-notification-id="${notificationId}" data-notification-rsvp="rejected">Từ chối</button></div>`;
    }
    if (response === 'rejected') {
        return `<div class="notification-rsvp-actions"><span class="badge-status rejected">Đã từ chối</span>
            <button type="button" class="btn-rsvp btn-accept" data-rsvp-meeting="${meetingId}"
                data-notification-id="${notificationId}" data-notification-rsvp="accepted">Đồng ý</button></div>`;
    }
    return `<div class="notification-rsvp-actions"><button type="button" class="btn-rsvp btn-accept"
        data-rsvp-meeting="${meetingId}" data-notification-id="${notificationId}" data-notification-rsvp="accepted">Đồng ý</button>
        <button type="button" class="btn-rsvp btn-reject" data-rsvp-meeting="${meetingId}"
        data-notification-id="${notificationId}" data-notification-rsvp="rejected">Từ chối</button></div>`;
}

function renderNotificationError(message) {
    const popup = document.getElementById('notificationPopup');
    if (popup) {
        const previousError = popup.querySelector('[data-notification-error]');
        if (previousError) previousError.remove();
        popup.insertAdjacentHTML('afterbegin', `<div class="notification-empty" role="alert" data-notification-error>${escapeHtml(message)}</div>`);
    }
    const pageList = document.getElementById('pageNotifList');
    if (!pageList) return;
    // Giữ nguyên khung danh sách (Empty State) và chỉ chèn cảnh báo phía trên.
    let alertBox = pageList.previousElementSibling;
    if (!alertBox || !alertBox.hasAttribute('data-notification-error')) {
        alertBox = document.createElement('div');
        alertBox.className = 'notification-center-alert';
        alertBox.setAttribute('role', 'alert');
        alertBox.setAttribute('data-notification-error', '');
        pageList.before(alertBox);
    }
    alertBox.textContent = message;
    pageList.setAttribute('aria-busy', 'false');
}

function clearNotificationError() {
    document.getElementById('notificationPopup')
        ?.querySelector('[data-notification-error]')
        ?.remove();
    const pageList = document.getElementById('pageNotifList');
    const alertBox = pageList?.previousElementSibling;
    if (alertBox && alertBox.hasAttribute('data-notification-error')) alertBox.remove();
}

function updateNotificationDot(unreadCount) {
    const dot = document.getElementById('notifBadge')
        || document.getElementById('notificationDot');
    const sidebarBadge = document.getElementById('sidebarNotifBadge');
    const badgeText = unreadCount > 99 ? '99+' : String(unreadCount);
    if (dot) {
        dot.textContent = badgeText;
        dot.style.display = unreadCount > 0 ? 'block' : 'none';
    }
    if (sidebarBadge) {
        sidebarBadge.textContent = badgeText;
        sidebarBadge.hidden = unreadCount <= 0;
    }
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
    document.getElementById('sidebarNotifLink')?.setAttribute('aria-expanded', String(isHidden));
    if (isHidden) fetchNotifications();
}

document.addEventListener('click', event => {
    const wrapper = document.querySelector('.notification-wrapper');
    const popup = document.getElementById('notificationPopup');
    const sidebarLink = document.getElementById('sidebarNotifLink');
    if (!wrapper || !popup) return;
    if (!wrapper.contains(event.target) && !sidebarLink?.contains(event.target)
        && popup.style.display !== 'none') {
        popup.style.display = 'none';
        document.getElementById('notificationBellBtn')?.setAttribute('aria-expanded', 'false');
        sidebarLink?.setAttribute('aria-expanded', 'false');
    }
});

window.fetchNotifications = fetchNotifications;
window.updateNotificationDot = updateNotificationDot;
window.toggleNotificationPopup = toggleNotificationPopup;
