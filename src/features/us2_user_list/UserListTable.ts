import type {
  GetUsersQuery,
  GetUsersResult,
  UserListItem,
  UserListRole,
  UserListStatus,
} from './types';
import { UserListService } from './userListService';
import { AssignPermissionModal, PermissionService } from '../us3_assign_permissions';
import { RestrictionService, RoomRestrictionModal } from '../us4_room_booking_restriction';
import { BulkUserEditModal } from './BulkUserEditModal';

export interface UserListTableOptions {
  containerId?: string;
  service?: UserListService;
  permissionService?: PermissionService;
  restrictionService?: RestrictionService;
  createUserHref?: string;
  onCreateUser?: () => void;
}

const TABLE_STYLES = `
  .us2-user-list { color: #172033; font: 14px/1.5 system-ui, sans-serif; }
  .us2-user-list * { box-sizing: border-box; }
  .us2-user-list__header, .us2-user-list__toolbar, .us2-user-list__pagination {
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
  }
  .us2-user-list__header { margin-bottom: 18px; flex-wrap: wrap; }
  .us2-user-list__header-actions { display: flex; flex-wrap: wrap; gap: 8px; }
  .us2-user-list__title { margin: 0; font-size: 22px; }
  .us2-user-list__toolbar { margin-bottom: 14px; flex-wrap: wrap; }
  .us2-user-list__search, .us2-user-list__filter {
    min-height: 40px; padding: 8px 12px; border: 1px solid #cbd5e1;
    border-radius: 8px; background: #fff; color: inherit;
  }
  .us2-user-list__search { width: min(100%, 360px); }
  .us2-user-list__table-wrap { overflow-x: auto; border: 1px solid #e2e8f0; border-radius: 10px; }
  .us2-user-list__table { width: 100%; border-collapse: collapse; text-align: left; }
  .us2-user-list__table th, .us2-user-list__table td {
    padding: 12px 14px; border-bottom: 1px solid #e2e8f0; white-space: nowrap;
  }
  .us2-user-list__table th { background: #f8fafc; color: #475569; font-weight: 600; }
  .us2-user-list__table tr:last-child td { border-bottom: 0; }
  .us2-user-list__badge {
    display: inline-block; padding: 3px 9px; border-radius: 999px;
    font-size: 12px; font-weight: 650;
  }
  .us2-user-list__role--admin { background: #ede9fe; color: #6d28d9; }
  .us2-user-list__role--booker { background: #dbeafe; color: #1d4ed8; }
  .us2-user-list__role--attendee { background: #cffafe; color: #0e7490; }
  .us2-user-list__status--active { background: #dcfce7; color: #15803d; }
  .us2-user-list__status--inactive { background: #f1f5f9; color: #475569; }
  .us2-user-list__actions { display: flex; gap: 8px; }
  .us2-user-list__action, .us2-user-list__button, .us2-user-list__bulk-button {
    border: 0; border-radius: 7px; padding: 8px 11px; font: inherit;
  }
  .us2-user-list__action { color: #334155; background: #f1f5f9; cursor: pointer; }
  .us2-user-list__action:hover:not(:disabled) { background: #e2e8f0; }
  .us2-user-list__button, .us2-user-list__bulk-button { background: #2563eb; color: #fff; text-decoration: none; cursor: pointer; }
  .us2-user-list__bulk-button { background: #475569; }
  .us2-user-list__action:disabled, .us2-user-list__bulk-button:disabled { opacity: .55; cursor: not-allowed; }
  .us2-user-list__selection { width: 1rem; height: 1rem; accent-color: #2563eb; }
  .us2-user-list__count-error { margin: 8px 0 0; color: #b91c1c; }
  .us2-user-list__pagination { padding: 14px 2px 0; color: #475569; }
  .us2-user-list__page-controls { display: flex; align-items: center; gap: 8px; }
  .us2-user-list__error { margin: 10px 0; color: #b91c1c; }
  .us2-user-list__empty { padding: 28px !important; color: #64748b; text-align: center; }
  @media (max-width: 640px) {
    .us2-user-list__header, .us2-user-list__pagination { align-items: flex-start; flex-direction: column; }
  }
`;

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, character => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[character] ?? character);
}

function roleLabel(role: UserListRole): string {
  return { ADMIN: 'Admin', BOOKER: 'Booker', ATTENDEE: 'Attendee' }[role];
}

function roleClass(role: UserListRole): string {
  return `us2-user-list__role--${role.toLowerCase()}`;
}

function statusClass(status: UserListStatus): string {
  return `us2-user-list__status--${status.toLowerCase()}`;
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('vi-VN', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(date);
}

export class UserListTable {
  private readonly service: UserListService;
  private readonly options: UserListTableOptions;
  private readonly permissionService: PermissionService;
  private readonly restrictionService: RestrictionService;
  private readonly selectedUserIds = new Set<string>();
  private readonly selectedUsers = new Map<string, UserListItem>();
  private readonly restrictionCounts = new Map<string, number | null>();
  private container: HTMLElement | null = null;
  private query: GetUsersQuery = { page: 1, limit: 10 };
  private result: GetUsersResult = { items: [], total: 0, page: 1, limit: 10 };
  private loading = false;
  private error = '';
  private restrictionCountError = '';
  private requestId = 0;
  private readonly boundContainers = new WeakSet<HTMLElement>();
  private assignPermissionModal: AssignPermissionModal | null = null;
  private roomRestrictionModal: RoomRestrictionModal | null = null;
  private bulkEditModal: BulkUserEditModal | null = null;

  constructor(options: UserListTableOptions = {}) {
    this.options = options;
    this.service = options.service ?? new UserListService();
    this.permissionService = options.permissionService ?? new PermissionService();
    this.restrictionService = options.restrictionService ?? new RestrictionService();
    if (options.containerId && typeof document !== 'undefined') {
      this.container = document.getElementById(options.containerId);
    }
  }

  public renderHtml(): string {
    const pageCount = Math.max(1, Math.ceil(this.result.total / this.result.limit));
    const currentPageSelected = this.result.items.length > 0
      && this.result.items.every(user => this.selectedUserIds.has(user.id));
    const rows = this.result.items.length
      ? this.result.items.map(user => this.renderRow(user)).join('')
      : `<tr><td class="us2-user-list__empty" colspan="8">${this.loading ? 'Đang tải danh sách...' : 'Không tìm thấy người dùng.'}</td></tr>`;

    return `
      <style>${TABLE_STYLES}</style>
      <section class="us2-user-list" aria-labelledby="us2-user-list-title">
        <header class="us2-user-list__header">
          <div>
            <h2 class="us2-user-list__title" id="us2-user-list-title">Danh sách người dùng</h2>
            <p>Quản lý tài khoản và vai trò trong hệ thống.</p>
          </div>
          <div class="us2-user-list__header-actions">
            <button class="us2-user-list__bulk-button" data-bulk-edit type="button"
              ${this.selectedUserIds.size === 0 || this.loading ? 'disabled' : ''}>
              Chỉnh sửa đồng bộ${this.selectedUserIds.size ? ` (${this.selectedUserIds.size})` : ''}
            </button>
            <a class="us2-user-list__button" data-create-user href="${escapeHtml(this.options.createUserHref ?? '#createUserForm')}">
              + Tạo người dùng mới
            </a>
          </div>
        </header>
        <div class="us2-user-list__toolbar">
          <label>
            <span class="sr-only">Tìm theo tên hoặc email</span>
            <input class="us2-user-list__search" data-search type="search"
              placeholder="Tìm theo tên hoặc email..." value="${escapeHtml(this.query.search ?? '')}"
              autocomplete="off">
          </label>
          <label>
            <span class="sr-only">Lọc theo vai trò</span>
            <select class="us2-user-list__filter" data-role-filter aria-label="Lọc theo vai trò">
              <option value="">Tất cả vai trò</option>
              ${(['ADMIN', 'BOOKER', 'ATTENDEE'] as UserListRole[]).map(role => `
                <option value="${role}" ${this.query.role === role ? 'selected' : ''}>${roleLabel(role)}</option>
              `).join('')}
            </select>
          </label>
        </div>
        ${this.error ? `<p class="us2-user-list__error" role="alert">${escapeHtml(this.error)}</p>` : ''}
        ${this.restrictionCountError ? `<p class="us2-user-list__count-error" role="alert">${escapeHtml(this.restrictionCountError)}</p>` : ''}
        <div class="us2-user-list__table-wrap">
          <table class="us2-user-list__table">
            <thead><tr>
              <th scope="col"><input class="us2-user-list__selection" data-select-page type="checkbox"
                aria-label="Chọn tất cả người dùng trên trang này"
                ${currentPageSelected ? 'checked' : ''} ${this.loading ? 'disabled' : ''}></th>
              <th scope="col">Họ và tên</th><th scope="col">Email</th><th scope="col">Vai trò</th>
              <th scope="col">Trạng thái</th><th scope="col">Ngày tạo</th><th scope="col">Hành động</th>
              <th scope="col">Giới hạn đặt phòng</th>
            </tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
        <footer class="us2-user-list__pagination" aria-label="Phân trang">
          <span>Hiển thị ${this.result.items.length ? (this.result.page - 1) * this.result.limit + 1 : 0}–${Math.min(this.result.page * this.result.limit, this.result.total)} trong ${this.result.total} người dùng</span>
          <div class="us2-user-list__page-controls">
            <button class="us2-user-list__action" data-page="previous" type="button"
              ${this.loading || this.result.page <= 1 ? 'disabled' : ''}>Trước</button>
            <span>Trang ${this.result.page} / ${pageCount}</span>
            <button class="us2-user-list__action" data-page="next" type="button"
              ${this.loading || this.result.page >= pageCount ? 'disabled' : ''}>Sau</button>
          </div>
        </footer>
      </section>
    `;
  }

  public async mount(targetElement?: HTMLElement): Promise<void> {
    const container = targetElement ?? this.container;
    if (!container) throw new Error('Container element not found for UserListTable.');

    this.container = container;
    this.bindEvents(container);
    this.render();
    await this.loadUsers();
  }

  public async loadUsers(query: GetUsersQuery = this.query): Promise<void> {
    this.query = { ...query, page: query.page ?? 1, limit: query.limit ?? 10 };
    this.loading = true;
    this.error = '';
    const requestId = ++this.requestId;
    this.render();

    try {
      const result = await this.service.getUsers(this.query);
      if (requestId !== this.requestId) return;
      this.result = result;
      result.items.forEach(user => {
        if (this.selectedUserIds.has(user.id)) this.selectedUsers.set(user.id, { ...user });
      });
      await this.loadRestrictionCounts(result.items, requestId);
    } catch (error) {
      if (requestId !== this.requestId) return;
      this.error = error instanceof Error ? error.message : 'Không thể tải danh sách người dùng.';
      this.result = { ...this.result, items: [], total: 0, page: this.query.page ?? 1 };
      this.restrictionCounts.clear();
    } finally {
      if (requestId === this.requestId) {
        this.loading = false;
        this.render();
      }
    }
  }

  private bindEvents(root: HTMLElement): void {
    if (this.boundContainers.has(root)) return;
    this.boundContainers.add(root);

    root.addEventListener('input', event => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement) || !target.matches('[data-search]')) return;
      void this.loadUsers({ ...this.query, search: target.value, page: 1 });
    });

    root.addEventListener('change', event => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      if (target instanceof HTMLSelectElement && target.matches('[data-role-filter]')) {
        const role = target.value as UserListRole | '';
        void this.loadUsers({ ...this.query, role: role || undefined, page: 1 });
      } else if (target instanceof HTMLInputElement && target.matches('[data-select-page]')) {
        this.result.items.forEach(user => {
          if (target.checked) {
            this.selectedUserIds.add(user.id);
            this.selectedUsers.set(user.id, { ...user });
          } else {
            this.selectedUserIds.delete(user.id);
            this.selectedUsers.delete(user.id);
          }
        });
        this.render();
      } else if (target instanceof HTMLInputElement && target.matches('[data-select-user]')) {
        const user = this.result.items.find(item => item.id === target.value);
        if (target.checked && user) {
          this.selectedUserIds.add(user.id);
          this.selectedUsers.set(user.id, { ...user });
        } else {
          this.selectedUserIds.delete(target.value);
          this.selectedUsers.delete(target.value);
        }
        this.render();
      }
    });

    root.addEventListener('click', event => {
      const target = event.target;
      if (!(target instanceof Element)) return;

      const createLink = target.closest<HTMLAnchorElement>('[data-create-user]');
      if (createLink && this.options.onCreateUser) {
        event.preventDefault();
        this.options.onCreateUser();
        return;
      }

      const bulkButton = target.closest<HTMLButtonElement>('[data-bulk-edit]');
      if (bulkButton && !bulkButton.disabled) {
        const users = [...this.selectedUsers.values()];
        if (users.length) void this.getBulkEditModal().open(users);
        return;
      }

      const actionButton = target.closest<HTMLButtonElement>('[data-user-action]');
      if (actionButton) {
        const user = this.result.items.find(item => item.id === actionButton.dataset.userId);
        if (user?.id) {
          if (actionButton.dataset.userAction === 'permissions') {
            void this.getAssignPermissionModal().open({
              id: user.id,
              fullName: user.fullName,
              email: user.email,
              role: user.role,
            });
          } else if (actionButton.dataset.userAction === 'restrictions') {
            void this.getRoomRestrictionModal().open({
              id: user.id,
              fullName: user.fullName,
              email: user.email,
            });
          }
        }
        return;
      }

      const pageButton = target.closest<HTMLButtonElement>('[data-page]');
      if (!pageButton || pageButton.disabled) return;
      const page = this.query.page ?? 1;
      void this.loadUsers({ ...this.query, page: pageButton.dataset.page === 'next' ? page + 1 : page - 1 });
    });
  }

  private render(): void {
    if (!this.container) return;

    const activeElement = document.activeElement;
    const hadSearchFocus = activeElement instanceof HTMLInputElement
      && activeElement.matches('[data-search]')
      && this.container.contains(activeElement);
    const selectionStart = hadSearchFocus ? activeElement.selectionStart : null;
    const selectionEnd = hadSearchFocus ? activeElement.selectionEnd : null;
    const hadRoleFilterFocus = activeElement instanceof HTMLSelectElement
      && activeElement.matches('[data-role-filter]')
      && this.container.contains(activeElement);
    const hadSelectPageFocus = activeElement instanceof HTMLInputElement
      && activeElement.matches('[data-select-page]')
      && this.container.contains(activeElement);
    const focusedUserId = activeElement instanceof HTMLInputElement
      && activeElement.matches('[data-select-user]')
      && this.container.contains(activeElement)
      ? activeElement.value
      : null;

    this.container.innerHTML = this.renderHtml();

    if (hadSearchFocus) {
      const searchInput = this.container.querySelector<HTMLInputElement>('[data-search]');
      searchInput?.focus();
      if (selectionStart !== null && selectionEnd !== null) {
        searchInput?.setSelectionRange(selectionStart, selectionEnd);
      }
    } else if (hadRoleFilterFocus) {
      this.container.querySelector<HTMLSelectElement>('[data-role-filter]')?.focus();
    } else if (hadSelectPageFocus) {
      this.container.querySelector<HTMLInputElement>('[data-select-page]')?.focus();
    } else if (focusedUserId) {
      Array.from(this.container.querySelectorAll<HTMLInputElement>('[data-select-user]'))
        .find(input => input.value === focusedUserId)?.focus();
    }
  }

  private renderRow(user: UserListItem): string {
    const restrictionCount = this.restrictionCounts.get(user.id);
    return `<tr>
      <td><input class="us2-user-list__selection" data-select-user type="checkbox"
        value="${escapeHtml(user.id)}" aria-label="Chọn ${escapeHtml(user.fullName)}"
        ${this.selectedUserIds.has(user.id) ? 'checked' : ''} ${this.loading ? 'disabled' : ''}></td>
      <td>${escapeHtml(user.fullName)}</td>
      <td>${escapeHtml(user.email)}</td>
      <td><span class="us2-user-list__badge ${roleClass(user.role)}">${roleLabel(user.role)}</span></td>
      <td><span class="us2-user-list__badge ${statusClass(user.status)}">${user.status}</span></td>
      <td>${formatDate(user.createdAt)}</td>
      <td><div class="us2-user-list__actions">
        <button class="us2-user-list__action" type="button" data-user-action="permissions"
          data-user-id="${escapeHtml(user.id)}">Sửa quyền</button>
        <button class="us2-user-list__action" type="button" data-user-action="restrictions"
          data-user-id="${escapeHtml(user.id)}">Giới hạn phòng</button>
      </div></td>
      <td>${restrictionCount === undefined || restrictionCount === null ? '—' : `${restrictionCount} phòng`}</td>
    </tr>`;
  }

  private async loadRestrictionCounts(users: UserListItem[], requestId: number): Promise<void> {
    this.restrictionCounts.clear();
    this.restrictionCountError = '';
    if (!users.length) return;

    const results = await Promise.allSettled(
      users.map(user => this.restrictionService.getUserRestrictions(user.id)),
    );
    if (requestId !== this.requestId) return;

    let failedCount = 0;
    results.forEach((result, index) => {
      const userId = users[index].id;
      if (result.status === 'fulfilled') {
        this.restrictionCounts.set(userId, result.value.restrictedRoomIds.length);
      } else {
        this.restrictionCounts.set(userId, null);
        failedCount += 1;
      }
    });
    if (failedCount) {
      this.restrictionCountError = `Không tải được giới hạn phòng của ${failedCount} người dùng; các ô chưa tải hiển thị “—”.`;
    }
  }

  private getAssignPermissionModal(): AssignPermissionModal {
    this.assignPermissionModal ??= new AssignPermissionModal({
      service: this.permissionService,
      onSaved: (_user, permissions) => {
        const user = this.result.items.find(item => item.id === permissions.userId);
        const selectedUser = this.selectedUsers.get(permissions.userId);
        const updatedRole: UserListRole = permissions.systemRole === 'ADMIN'
          ? 'ADMIN'
          : permissions.canBook ? 'BOOKER' : 'ATTENDEE';
        this.service.updateMockUserRole(permissions.userId, updatedRole);
        if (user) user.role = updatedRole;
        if (selectedUser) selectedUser.role = updatedRole;
        this.render();
      },
    });
    return this.assignPermissionModal;
  }

  private getRoomRestrictionModal(): RoomRestrictionModal {
    this.roomRestrictionModal ??= new RoomRestrictionModal({
      service: this.restrictionService,
      onSaved: () => void this.loadUsers(this.query),
    });
    return this.roomRestrictionModal;
  }

  private getBulkEditModal(): BulkUserEditModal {
    this.bulkEditModal ??= new BulkUserEditModal({
      permissionService: this.permissionService,
      restrictionService: this.restrictionService,
      onSaved: (userIds, changes) => {
        if (changes.mode === 'role' && changes.systemRole) {
          userIds.forEach(userId => {
            const user = this.result.items.find(item => item.id === userId);
            const selectedUser = this.selectedUsers.get(userId);
            const updatedRole: UserListRole = changes.systemRole === 'ADMIN'
              ? 'ADMIN'
              : user?.role === 'ATTENDEE' || selectedUser?.role === 'ATTENDEE'
                ? 'ATTENDEE' : 'BOOKER';
            this.service.updateMockUserRole(userId, updatedRole);
            if (user) user.role = updatedRole;
            if (selectedUser) selectedUser.role = updatedRole;
          });
        } else if (changes.mode === 'rooms' && changes.restrictedRoomIds) {
          userIds.forEach(userId => {
            this.restrictionCounts.set(userId, changes.restrictedRoomIds?.length ?? 0);
          });
        }
        userIds.forEach(userId => {
          this.selectedUserIds.delete(userId);
          this.selectedUsers.delete(userId);
        });
        this.render();
      },
    });
    return this.bulkEditModal;
  }
}
