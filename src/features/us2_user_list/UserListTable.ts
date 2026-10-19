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

function getUserListApiBase(): string {
  const configuredApiUrl = typeof window === 'undefined'
    ? undefined
    : (window as Window & { API_URL?: string }).API_URL;
  return (configuredApiUrl ?? 'https://roomsync-app.onrender.com/api').replace(/\/+$/, '');
}

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
    padding: 14px 16px; border-bottom: 1px solid #e2e8f0; white-space: nowrap;
  }
  .us2-user-list__table th { background: #f8fafc; color: #475569; font-weight: 600; }
  .us2-user-list__table tbody tr { transition: background-color 160ms ease; }
  .us2-user-list__table tbody tr:hover { background: rgb(238 242 255 / 30%); }
  .us2-user-list__table tr:last-child td { border-bottom: 0; }
  .us2-user-list__name { color: #0f172a; font-size: 14px; font-weight: 500; }
  .us2-user-list__email { color: #64748b; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }
  .us2-user-list__restriction-count { color: #475569; font-size: 14px; font-weight: 500; text-align: center; }
  .us2-user-list__badge {
    display: inline-flex; align-items: center; gap: 6px; padding: 2px 10px;
    border: 1px solid transparent; border-radius: 999px; font-size: 12px; font-weight: 650;
  }
  .us2-user-list__role-badge { border-radius: 6px; padding: 2px 10px; font-weight: 500; }
  .us2-user-list__role--admin { background: #f5f3ff; border-color: #ddd6fe; color: #6d28d9; font-weight: 650; }
  .us2-user-list__role--manager { background: #eff6ff; border-color: #bfdbfe; color: #1d4ed8; }
  .us2-user-list__role--employee, .us2-user-list__role--booker, .us2-user-list__role--attendee { background: #f1f5f9; border-color: #e2e8f0; color: #334155; }
  .us2-user-list__status--active { background: #ecfdf5; border-color: #a7f3d0; color: #047857; }
  .us2-user-list__status--inactive, .us2-user-list__status--locked { background: #fff1f2; border-color: #fecdd3; color: #be123c; }
  .us2-user-list__status--pending { background: #fffbeb; border-color: #fde68a; color: #b45309; }
  .us2-user-list__status-dot { width: 6px; height: 6px; flex: 0 0 6px; border-radius: 50%; background: currentColor; }
  .us2-user-list__actions { display: flex; gap: 8px; }
  .us2-user-list__menu { position: fixed; z-index: 1300; min-width: 250px; padding: 6px; border: 1px solid rgb(226 232 240 / 80%); border-radius: 12px; background: #fff; box-shadow: 0 20px 25px -5px rgb(148 163 184 / 35%), 0 8px 10px -6px rgb(148 163 184 / 25%); }
  .us2-user-list__menu[hidden] { display: none; }
  .us2-user-list__menu-item { display: block; width: 100%; padding: 8px 10px; border: 0; border-radius: 7px; background: transparent; color: #334155; text-align: left; font: inherit; font-size: 14px; cursor: pointer; transition: color 160ms ease, background-color 160ms ease; }
  .us2-user-list__menu-item:hover:not(:disabled) { background: #f8fafc; color: #4f46e5; }
  .us2-user-list__menu-item--danger { color: #be123c; }
  .us2-user-list__menu-item:disabled { opacity: .5; cursor: not-allowed; }
  .us2-user-list__menu-toggle { min-width: 38px; min-height: 38px; padding: 4px 10px; border: 1px solid #cbd5e1; border-radius: 7px; background: #fff; color: #334155; font-size: 20px; line-height: 1; cursor: pointer; }
  .us2-user-profile-backdrop { position: fixed; inset: 0; z-index: 1400; display: grid; place-items: center; padding: 20px; background: rgb(15 23 42 / 55%); }
  .us2-user-profile-backdrop[hidden] { display: none; }
  .us2-user-profile { width: min(100%, 760px); max-height: min(92vh, 900px); overflow: auto; border-radius: 16px; background: #fff; color: #172033; box-shadow: 0 24px 70px rgb(15 23 42 / 28%); }
  .us2-user-profile__header, .us2-user-profile__body, .us2-user-profile__footer { padding: 18px 22px; }
  .us2-user-profile__header { display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #e2e8f0; }
  .us2-user-profile__header h2 { margin: 0; font-size: 20px; }
  .us2-user-profile__body { display: grid; gap: 18px; }
  .us2-user-profile__section { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
  .us2-user-profile__section h3 { grid-column: 1 / -1; margin: 0; padding-bottom: 7px; border-bottom: 1px solid #e2e8f0; font-size: 15px; }
  .us2-user-profile__field { display: grid; gap: 5px; min-width: 0; color: #475569; font-weight: 600; }
  .us2-user-profile__field input, .us2-user-profile__field select { width: 100%; min-height: 40px; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 8px; background: #fff; color: #172033; font: inherit; font-weight: 400; }
  .us2-user-profile__field input:disabled, .us2-user-profile__field select:disabled { background: #f8fafc; color: #64748b; }
  .us2-user-profile__groups { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px 12px; max-height: 150px; overflow: auto; }
  .us2-user-profile__group { display: flex; align-items: center; gap: 8px; font-weight: 400; }
  .us2-user-profile__toggle { display: flex; align-items: center; gap: 9px; align-self: end; min-height: 40px; color: #334155; }
  .us2-user-profile__error { color: #b91c1c; }
  .us2-user-profile__footer { display: flex; justify-content: flex-end; gap: 9px; border-top: 1px solid #e2e8f0; }
  .us2-user-profile__button { min-height: 40px; padding: 8px 14px; border: 0; border-radius: 8px; background: #f1f5f9; color: #334155; font: inherit; font-weight: 600; cursor: pointer; }
  .us2-user-profile__button--save { background: #2563eb; color: #fff; }
  .us2-user-profile__button:disabled { opacity: .55; cursor: wait; }
  .us2-user-profile__status { color: #64748b; font-weight: 400; }
  .us2-user-profile :focus-visible, .us2-user-list__menu :focus-visible, .us2-user-list__menu-toggle:focus-visible { outline: 2px solid #2563eb; outline-offset: 2px; }
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
    .us2-user-profile__section, .us2-user-profile__groups { grid-template-columns: 1fr; }
    .us2-user-profile-backdrop { padding: 10px; }
    .us2-user-profile__header, .us2-user-profile__body, .us2-user-profile__footer { padding: 15px; }
  }
`;

interface UserProfileRecord {
  id: number;
  full_name: string | null;
  email: string | null;
  username: string;
  external_id: string | null;
  role: string;
  status: string;
  is_active: boolean;
  created_at: string;
  department_id: number | null;
  department: { id: number; name: string } | null;
  position: string | null;
  project_groups: Array<{ id: number; name: string }>;
  daily_booking_hours_limit: number | null;
  can_bypass_room_approval: boolean;
}

interface DirectoryRecord {
  id: number;
  name: string;
}

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
  return ({
    ADMIN: 'Admin',
    EMPLOYEE: 'Nhân viên',
    BOOKER: 'Booker',
    ATTENDEE: 'Attendee',
    MANAGER: 'Quản lý',
  } as Partial<Record<UserListRole, string>>)[role] ?? escapeHtml(role);
}

function roleClass(role: UserListRole): string {
  return `us2-user-list__role--${role.toLowerCase().replace(/[^a-z0-9_-]/g, '-')}`;
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
  private profileHost: HTMLElement | null = null;
  private profileUser: UserProfileRecord | null = null;
  private profileCanEdit = false;
  private profileLoading = false;
  private profileSaving = false;
  private profileError = '';
  private profileTrigger: HTMLElement | null = null;
  private profileRequestId = 0;
  private readonly currentUserId = typeof localStorage === 'undefined'
    ? ''
    : localStorage.getItem('user_id') ?? '';

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
              ${(['ADMIN', 'EMPLOYEE', 'MANAGER'] as UserListRole[]).map(role => `
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
              <th scope="col">Trạng thái</th><th scope="col">Ngày tạo</th><th scope="col">Tùy chọn</th>
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

  public async refreshAfterCreate(): Promise<void> {
    this.selectedUserIds.clear();
    this.selectedUsers.clear();
    await this.loadUsers({ page: 1, limit: this.query.limit ?? 10 });
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
          if (!this.canModifyUser(user)) return;
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

      const menuToggle = target.closest<HTMLButtonElement>('[data-user-menu-toggle]');
      if (menuToggle) {
        const menu = menuToggle.parentElement?.querySelector<HTMLElement>('[data-user-menu]');
        const shouldOpen = Boolean(menu?.hidden);
        root.querySelectorAll<HTMLElement>('[data-user-menu]').forEach(openMenu => {
          openMenu.hidden = true;
          openMenu.parentElement?.querySelector('[data-user-menu-toggle]')?.setAttribute('aria-expanded', 'false');
        });
        if (menu && shouldOpen) {
          const rect = menuToggle.getBoundingClientRect();
          menu.hidden = false;
          menu.style.top = `${Math.min(rect.bottom + 4, window.innerHeight - menu.offsetHeight - 8)}px`;
          menu.style.left = `${Math.max(8, Math.min(rect.right - menu.offsetWidth, window.innerWidth - menu.offsetWidth - 8))}px`;
          menuToggle.setAttribute('aria-expanded', 'true');
        }
        return;
      }

      const actionButton = target.closest<HTMLButtonElement>('[data-user-action]');
      if (actionButton) {
        const user = this.result.items.find(item => item.id === actionButton.dataset.userId);
        if (user?.id) {
          this.closeUserMenus();
          if (actionButton.dataset.userAction === 'details' && !actionButton.disabled) {
            this.profileTrigger = actionButton;
            void this.openUserDetailModal(user.id);
          } else if (actionButton.dataset.userAction === 'permissions' && !actionButton.disabled) {
            void this.getAssignPermissionModal().open({
              id: user.id,
              fullName: user.fullName,
              email: user.email,
              role: user.role,
            });
          } else if (actionButton.dataset.userAction === 'restrictions' && !actionButton.disabled) {
            void this.getRoomRestrictionModal().open({
              id: user.id,
              fullName: user.fullName,
              email: user.email,
            });
          } else if (actionButton.dataset.userAction === 'status' && !actionButton.disabled) {
            void this.updateUserStatus(user);
          } else if (actionButton.dataset.userAction === 'resend-invite' && !actionButton.disabled) {
            void this.resendInvitation(user);
          }
        }
        return;
      }

      const pageButton = target.closest<HTMLButtonElement>('[data-page]');
      if (!pageButton || pageButton.disabled) return;
      const page = this.query.page ?? 1;
      void this.loadUsers({ ...this.query, page: pageButton.dataset.page === 'next' ? page + 1 : page - 1 });
    });

    root.addEventListener('keydown', event => {
      if (event.key === 'Escape') this.closeUserMenus();
    });
    document.addEventListener('click', event => {
      if (event.target instanceof Node && !root.contains(event.target)) this.closeUserMenus();
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
    const protectedAdmin = user.role === 'ADMIN'
      && (!this.currentUserId || user.id !== this.currentUserId);
    const adminActionsDisabled = this.loading || protectedAdmin;
    return `<tr>
      <td><input class="us2-user-list__selection" data-select-user type="checkbox"
        value="${escapeHtml(user.id)}" aria-label="Chọn ${escapeHtml(user.fullName)}"
        ${this.selectedUserIds.has(user.id) ? 'checked' : ''} ${adminActionsDisabled ? 'disabled' : ''}></td>
      <td class="us2-user-list__name">${escapeHtml(user.fullName)}</td>
      <td class="us2-user-list__email">${escapeHtml(user.email)}</td>
      <td><span class="us2-user-list__badge us2-user-list__role-badge ${roleClass(user.role)}">${roleLabel(user.role)}</span></td>
      <td><span class="us2-user-list__badge us2-user-list__status-badge ${statusClass(user.status)}">
        <span class="us2-user-list__status-dot" aria-hidden="true"></span>${escapeHtml(user.status)}
      </span></td>
      <td>${formatDate(user.createdAt)}</td>
      <td><button class="btn btn-sm btn-light border dropdown-toggle-no-caret us2-user-list__menu-toggle"
        data-bs-toggle="dropdown" data-user-menu-toggle type="button" aria-label="Thao tác với ${escapeHtml(user.fullName)}"
        aria-haspopup="menu" aria-expanded="false" ${this.loading ? 'disabled' : ''}>⋮</button>
        <div class="us2-user-list__menu" data-user-menu role="menu" hidden>
          <button class="us2-user-list__menu-item" data-user-action="details" data-user-id="${escapeHtml(user.id)}"
            type="button" role="menuitem">Xem &amp; Chỉnh sửa chi tiết</button>
          <button class="us2-user-list__menu-item" data-user-action="permissions" data-user-id="${escapeHtml(user.id)}"
            type="button" role="menuitem" ${adminActionsDisabled ? 'disabled' : ''}>Sửa nhanh quyền &amp; vai trò</button>
          <button class="us2-user-list__menu-item" data-user-action="restrictions" data-user-id="${escapeHtml(user.id)}"
            type="button" role="menuitem" ${this.loading ? 'disabled' : ''}>Cấu hình giới hạn đặt phòng</button>
          ${user.status === 'PENDING' ? `<button class="us2-user-list__menu-item" data-user-action="resend-invite"
            data-user-id="${escapeHtml(user.id)}" type="button" role="menuitem" ${adminActionsDisabled ? 'disabled' : ''}>
            Gửi lại Email kích hoạt</button>` : ''}
          <button class="us2-user-list__menu-item us2-user-list__menu-item--danger" data-user-action="status"
            data-user-id="${escapeHtml(user.id)}" type="button" role="menuitem" ${adminActionsDisabled ? 'disabled' : ''}>
            ${user.status === 'ACTIVE' ? 'Khóa tài khoản' : 'Mở khóa tài khoản'}
          </button>
        </div>
      </td>
      <td class="us2-user-list__restriction-count">${this.restrictionCountLabel(user.id)}</td>
    </tr>`;
  }

  private restrictionCountLabel(userId: string): string {
    const restrictionCount = this.restrictionCounts.get(userId);
    return restrictionCount === undefined || restrictionCount === null
      ? '—'
      : `${restrictionCount} phòng`;
  }

  private closeUserMenus(): void {
    this.container?.querySelectorAll<HTMLElement>('[data-user-menu]').forEach(menu => {
      menu.hidden = true;
      menu.parentElement?.querySelector('[data-user-menu-toggle]')?.setAttribute('aria-expanded', 'false');
    });
  }

  private getUserProfileHost(): HTMLElement {
    if (!this.profileHost) {
      this.profileHost = document.createElement('div');
      document.body.appendChild(this.profileHost);
      this.profileHost.addEventListener('submit', event => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement) || !form.matches('[data-user-profile-form]')) return;
        event.preventDefault();
        if (this.profileUser) void this.saveUserProfile(String(this.profileUser.id));
      });
      this.profileHost.addEventListener('click', event => {
        if (!(event.target instanceof Element)) return;
        if (event.target.matches('[data-profile-backdrop]') || event.target.closest('[data-close-profile]')) {
          this.closeUserDetailModal();
        }
      });
      document.addEventListener('keydown', event => {
        const dialog = this.profileHost?.querySelector<HTMLElement>(
          '[data-profile-backdrop]:not([hidden]) [data-profile-dialog]',
        );
        if (!dialog) return;
        if (event.key === 'Escape') {
          this.closeUserDetailModal();
          return;
        }
        if (event.key !== 'Tab') return;

        const focusable = Array.from(dialog.querySelectorAll<HTMLElement>(
          'button:not(:disabled), input:not(:disabled), select:not(:disabled), [tabindex]:not([tabindex="-1"])',
        )).filter(element => element.offsetParent !== null);
        if (!focusable.length) {
          event.preventDefault();
          dialog.focus();
          return;
        }
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && (document.activeElement === first || !dialog.contains(document.activeElement))) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && (document.activeElement === last || !dialog.contains(document.activeElement))) {
          event.preventDefault();
          first.focus();
        }
      });
    }
    return this.profileHost;
  }

  private async fetchProfileJson<T>(url: string): Promise<T> {
    const token = localStorage.getItem('token') ?? localStorage.getItem('access_token') ?? '';
    const response = await fetch(url, {
      headers: {
        Accept: 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    const result: unknown = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = result && typeof result === 'object'
        ? (result as Record<string, unknown>).detail
        : undefined;
      throw new Error(typeof detail === 'string'
        ? detail
        : `Không thể tải hồ sơ người dùng (HTTP ${response.status}).`);
    }
    return result as T;
  }

  private async openUserDetailModal(userId: string): Promise<void> {
    const host = this.getUserProfileHost();
    const requestId = ++this.profileRequestId;
    this.profileUser = null;
    this.profileCanEdit = false;
    this.profileLoading = true;
    this.profileSaving = false;
    this.profileError = '';
    this.renderUserProfileModal();
    host.querySelector<HTMLElement>('[data-profile-dialog]')?.focus();

    try {
      const token = localStorage.getItem('token') ?? localStorage.getItem('access_token') ?? '';
      const headers = {
        Accept: 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      };
      const [userResponse, departmentsResponse, groupsResponse] = await Promise.all([
        fetch(`${getUserListApiBase()}/v1/users/${encodeURIComponent(userId)}`, { headers }),
        fetch(`${getUserListApiBase()}/v1/directories/departments`, { headers }),
        fetch(`${getUserListApiBase()}/v1/directories/project-groups`, { headers }),
      ]);
      const parseResponse = async <T,>(response: Response, label: string): Promise<T> => {
        const data: unknown = await response.json().catch(() => ({}));
        if (!response.ok) {
          const detail = data && typeof data === 'object'
            ? (data as Record<string, unknown>).detail
            : undefined;
          throw new Error(typeof detail === 'string'
            ? detail
            : `Không thể tải ${label} (HTTP ${response.status}).`);
        }
        return data as T;
      };
      const [user, departments, projectGroups] = await Promise.all([
        parseResponse<UserProfileRecord>(userResponse, 'hồ sơ người dùng'),
        parseResponse<DirectoryRecord[]>(departmentsResponse, 'danh sách phòng ban'),
        parseResponse<DirectoryRecord[]>(groupsResponse, 'danh sách nhóm dự án'),
      ]);
      if (requestId !== this.profileRequestId) return;
      if (!Array.isArray(departments) || !Array.isArray(projectGroups)) {
        throw new Error('Danh mục phòng ban hoặc nhóm dự án trả về dữ liệu không hợp lệ.');
      }
      this.profileUser = user;
      this.profileCanEdit = !(
        user.role.toUpperCase() === 'ADMIN'
        && (!this.currentUserId || String(user.id) !== this.currentUserId)
      );
      this.profileLoading = false;
      this.renderUserProfileModal(departments, projectGroups);
      host.querySelector<HTMLInputElement>('#profileFullName')?.focus();
    } catch (error) {
      if (requestId !== this.profileRequestId) return;
      this.profileLoading = false;
      this.profileError = error instanceof Error ? error.message : 'Không thể tải hồ sơ người dùng.';
      this.renderUserProfileModal();
    }
  }

  private renderUserProfileModal(
    departments: DirectoryRecord[] = [],
    projectGroups: DirectoryRecord[] = [],
  ): void {
    const host = this.getUserProfileHost();
    const user = this.profileUser;
    const disabled = this.profileLoading || !this.profileCanEdit || this.profileSaving;
    const status = user?.status.toUpperCase() === 'INACTIVE'
      ? 'LOCKED'
      : user?.status.toUpperCase() ?? '—';
    host.innerHTML = `
      <div class="us2-user-profile-backdrop" data-profile-backdrop role="presentation">
        <section class="us2-user-profile" data-profile-dialog role="dialog" aria-modal="true"
          aria-labelledby="userProfileTitle" tabindex="-1">
          <header class="us2-user-profile__header">
            <h2 id="userProfileTitle">Hồ sơ Chi tiết Người dùng</h2>
            <button class="us2-user-profile__button" type="button" data-close-profile aria-label="Đóng hồ sơ">Đóng</button>
          </header>
          <form data-user-profile-form>
            <div class="us2-user-profile__body">
              ${this.profileLoading ? '<p role="status">Đang tải hồ sơ...</p>' : ''}
              ${this.profileError ? `<p class="us2-user-profile__error" role="alert">${escapeHtml(this.profileError)}</p>` : ''}
              ${user ? `
                <section class="us2-user-profile__section" aria-labelledby="profileAccountHeading">
                  <h3 id="profileAccountHeading">Thông tin cá nhân &amp; tài khoản</h3>
                  <label class="us2-user-profile__field">Họ và tên
                    <input id="profileFullName" name="full_name" type="text" minlength="2" maxlength="150"
                      required value="${escapeHtml(user.full_name ?? '')}" ${disabled ? 'disabled' : ''}>
                  </label>
                  <label class="us2-user-profile__field">Email
                    <input name="email" type="email" maxlength="150" required
                      value="${escapeHtml(user.email ?? '')}" ${disabled ? 'disabled' : ''}>
                  </label>
                  <label class="us2-user-profile__field">Tên đăng nhập
                    <input value="${escapeHtml(user.username)}" disabled>
                  </label>
                  <label class="us2-user-profile__field">Mã nhân viên
                    <input value="${escapeHtml(user.external_id ?? '—')}" disabled>
                  </label>
                  <div class="us2-user-profile__field">Trạng thái tài khoản
                    <span class="us2-user-profile__status">${escapeHtml(status)}</span>
                  </div>
                  <div class="us2-user-profile__field">Ngày tạo
                    <span class="us2-user-profile__status">${escapeHtml(formatDate(user.created_at))}</span>
                  </div>
                </section>
                <section class="us2-user-profile__section" aria-labelledby="profileOrganizationHeading">
                  <h3 id="profileOrganizationHeading">Tổ chức &amp; chức danh</h3>
                  <label class="us2-user-profile__field">Phòng ban
                    <select name="department_id" ${disabled ? 'disabled' : ''}>
                      <option value="">Chưa phân phòng ban</option>
                      ${departments.map(department => `<option value="${department.id}"
                        ${Number(user.department_id ?? user.department?.id) === Number(department.id) ? 'selected' : ''}>
                        ${escapeHtml(department.name)}</option>`).join('')}
                    </select>
                  </label>
                  <label class="us2-user-profile__field">Chức vụ / vị trí công việc
                    <input name="position" type="text" maxlength="100"
                      value="${escapeHtml(user.position ?? '')}" placeholder="Ví dụ: Senior Developer"
                      ${disabled ? 'disabled' : ''}>
                  </label>
                  <div class="us2-user-profile__field" style="grid-column:1/-1">Nhóm dự án tham gia
                    <div class="us2-user-profile__groups">
                      ${projectGroups.length ? projectGroups.map(group => `
                        <label class="us2-user-profile__group">
                          <input type="checkbox" name="project_group_ids" value="${group.id}"
                            ${user.project_groups.some(item => Number(item.id) === Number(group.id)) ? 'checked' : ''}
                            ${disabled ? 'disabled' : ''}>
                          ${escapeHtml(group.name)}
                        </label>`).join('') : '<span>Chưa có nhóm dự án.</span>'}
                    </div>
                  </div>
                </section>
                <section class="us2-user-profile__section" aria-labelledby="profilePermissionsHeading">
                  <h3 id="profilePermissionsHeading">Vai trò &amp; quyền hạn hệ thống</h3>
                  <label class="us2-user-profile__field">Vai trò chính
                    <select name="role" required ${disabled ? 'disabled' : ''}>
                      <option value="admin" ${user.role.toLowerCase() === 'admin' ? 'selected' : ''}>Quản trị viên</option>
                      <option value="manager" ${user.role.toLowerCase() === 'manager' ? 'selected' : ''}>Quản lý</option>
                      <option value="employee" ${user.role.toLowerCase() === 'employee' ? 'selected' : ''}>Nhân viên</option>
                    </select>
                  </label>
                  <label class="us2-user-profile__field">Giới hạn giờ đặt phòng / ngày
                    <input name="daily_booking_hours_limit" type="number" min="0.5" max="24" step="0.5"
                      value="${user.daily_booking_hours_limit ?? ''}" placeholder="Không giới hạn"
                      ${disabled ? 'disabled' : ''}>
                  </label>
                  <label class="us2-user-profile__toggle">
                    <input name="can_bypass_room_approval" type="checkbox"
                      ${user.can_bypass_room_approval ? 'checked' : ''} ${disabled ? 'disabled' : ''}>
                    Được bỏ qua bước duyệt phòng đặc biệt
                  </label>
                  ${!this.profileCanEdit ? '<p class="us2-user-profile__status">Không thể chỉnh sửa hồ sơ quản trị viên khác.</p>' : ''}
                </section>
              ` : ''}
            </div>
            <footer class="us2-user-profile__footer">
              <button class="us2-user-profile__button" type="button" data-close-profile>Hủy</button>
              <button class="us2-user-profile__button us2-user-profile__button--save" type="submit"
                ${!user || disabled ? 'disabled' : ''}>${this.profileSaving ? 'Đang lưu...' : 'Lưu thay đổi'}</button>
            </footer>
          </form>
        </section>
      </div>
    `;
  }

  private closeUserDetailModal(): void {
    const userId = this.profileUser ? String(this.profileUser.id) : '';
    this.profileRequestId += 1;
    this.profileHost?.remove();
    this.profileHost = null;
    this.profileUser = null;
    if (this.profileTrigger?.isConnected) {
      this.profileTrigger.focus();
    } else if (this.container) {
      Array.from(this.container.querySelectorAll<HTMLButtonElement>('[data-user-action="details"]'))
        .find(button => button.dataset.userId === userId)?.focus();
    }
    this.profileTrigger = null;
  }

  private async saveUserProfile(userId: string): Promise<void> {
    const host = this.profileHost;
    const form = host?.querySelector<HTMLFormElement>('[data-user-profile-form]');
    const user = this.profileUser;
    if (!host || !form || !user || !this.profileCanEdit || !form.reportValidity()) return;

    const formData = new FormData(form);
    const limitValue = String(formData.get('daily_booking_hours_limit') ?? '').trim();
    const projectGroupIds = formData.getAll('project_group_ids').map(Number);
    const payload = {
      full_name: String(formData.get('full_name') ?? '').trim(),
      email: String(formData.get('email') ?? '').trim(),
      department_id: String(formData.get('department_id') ?? '').trim()
        ? Number(formData.get('department_id'))
        : null,
      position: String(formData.get('position') ?? '').trim() || null,
      project_group_ids: projectGroupIds,
      role: String(formData.get('role') ?? ''),
      daily_booking_hours_limit: limitValue ? Number(limitValue) : null,
      can_bypass_room_approval: formData.get('can_bypass_room_approval') === 'on',
    };
    this.profileSaving = true;
    this.profileError = '';
    const saveButton = host.querySelector<HTMLButtonElement>('[type="submit"]');
    if (saveButton) {
      saveButton.disabled = true;
      saveButton.textContent = 'Đang lưu...';
    }

    try {
      const token = localStorage.getItem('token') ?? localStorage.getItem('access_token') ?? '';
      const response = await fetch(`${getUserListApiBase()}/v1/users/${encodeURIComponent(userId)}`, {
        method: 'PUT',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      });
      const result: unknown = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = result && typeof result === 'object'
          ? (result as Record<string, unknown>).detail
          : undefined;
        throw new Error(typeof detail === 'string'
          ? detail
          : `Không thể lưu hồ sơ người dùng (HTTP ${response.status}).`);
      }
      this.closeUserDetailModal();
      await this.loadUsers(this.query);
    } catch (error) {
      this.profileSaving = false;
      this.profileError = error instanceof Error ? error.message : 'Không thể lưu hồ sơ người dùng.';
      this.renderUserProfileModal();
    }
  }

  private canModifyUser(user: UserListItem): boolean {
    return user.role !== 'ADMIN' || Boolean(this.currentUserId && user.id === this.currentUserId);
  }

  private async updateUserStatus(user: UserListItem): Promise<void> {
    await this.performAdminRequest(
      `${getUserListApiBase()}/v1/users/${encodeURIComponent(user.id)}`,
      'PATCH',
      { status: user.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE' },
    );
  }

  private async resendInvitation(user: UserListItem): Promise<void> {
    await this.performAdminRequest(
      `${getUserListApiBase()}/v1/users/${encodeURIComponent(user.id)}/resend-invite`,
      'POST',
    );
  }

  private async performAdminRequest(
    url: string,
    method: 'PATCH' | 'POST',
    body?: Record<string, unknown>,
  ): Promise<void> {
    this.error = '';
    this.loading = true;
    this.render();
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(url, {
        method,
        headers: {
          Accept: 'application/json',
          ...(body ? { 'Content-Type': 'application/json' } : {}),
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      const result = await response.json();
      if (!response.ok || result.email_sent === false) {
        throw new Error(
          typeof result.detail === 'string'
            ? result.detail
            : result.message || `Không thể cập nhật tài khoản (HTTP ${response.status}).`,
        );
      }
      await this.loadUsers({ ...this.query, page: 1 });
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Không thể cập nhật tài khoản.';
    } finally {
      this.loading = false;
      this.render();
    }
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
        const updatedRole: UserListRole = permissions.systemRole === 'ADMIN' ? 'ADMIN' : 'EMPLOYEE';
        this.service.updateMockUserRole(permissions.userId, updatedRole);
        void this.loadUsers(this.query);
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
