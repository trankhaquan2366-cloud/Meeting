import type {
  SystemRole,
  UpdateUserPermissionsDto,
  UserPermissionTarget,
  UserPermissions,
} from './types';
import { PermissionService } from './permissionService';

export interface AssignPermissionModalOptions {
  service?: PermissionService;
  onSaved?: (user: UserPermissionTarget, permissions: UserPermissions) => void;
  onCancel?: () => void;
}

const MODAL_STYLES = `
  .us3-modal-backdrop { position: fixed; inset: 0; z-index: 1100; display: grid; place-items: center; padding: 20px; background: rgb(15 23 42 / 55%); }
  .us3-modal-backdrop[hidden] { display: none; }
  .us3-modal { width: min(100%, 520px); border-radius: 16px; background: #fff; color: #172033; box-shadow: 0 24px 70px rgb(15 23 42 / 28%); font: 14px/1.5 system-ui, sans-serif; }
  .us3-modal * { box-sizing: border-box; }
  .us3-modal__header, .us3-modal__body, .us3-modal__footer { padding: 18px 22px; }
  .us3-modal__header { display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #e2e8f0; }
  .us3-modal__header h2 { margin: 0; font-size: 20px; }
  .us3-modal__user { display: grid; gap: 3px; margin-bottom: 18px; padding: 12px; border-radius: 9px; background: #f8fafc; }
  .us3-modal__user span { color: #64748b; overflow-wrap: anywhere; }
  .us3-modal__field { display: grid; gap: 7px; margin: 14px 0; }
  .us3-modal__field select { min-height: 40px; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 8px; background: #fff; color: inherit; font: inherit; }
  .us3-modal__permission { display: flex; align-items: flex-start; gap: 9px; padding: 9px 0; }
  .us3-modal__permission input { margin-top: 4px; accent-color: #2563eb; }
  .us3-modal__error { color: #b91c1c; }
  .us3-modal__footer { display: flex; justify-content: flex-end; gap: 9px; border-top: 1px solid #e2e8f0; }
  .us3-modal__button { min-height: 40px; padding: 8px 14px; border: 0; border-radius: 8px; font: inherit; font-weight: 600; cursor: pointer; }
  .us3-modal__button:disabled { opacity: .6; cursor: wait; }
  .us3-modal__button--cancel { background: #f1f5f9; color: #334155; }
  .us3-modal__button--save { background: #2563eb; color: #fff; }
`;

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[character] ?? character);
}

export class AssignPermissionModal {
  private readonly service: PermissionService;
  private readonly options: AssignPermissionModalOptions;
  private host: HTMLElement | null = null;
  private user: UserPermissionTarget | null = null;
  private systemRole: SystemRole = 'NHAN_VIEN';
  private canBook = true;
  private canAttend = true;
  private loading = false;
  private loadFailed = false;
  private saving = false;
  private error = '';
  private requestId = 0;

  private readonly onSubmit = (event: Event): void => {
    event.preventDefault();
    void this.save();
  };
  private readonly onChange = (event: Event): void => {
    const target = event.target;
    if (target instanceof HTMLSelectElement && target.matches('[data-system-role]')) {
      this.systemRole = target.value as SystemRole;
    } else if (target instanceof HTMLInputElement && target.matches('[data-can-book]')) {
      this.canBook = target.checked;
    } else if (target instanceof HTMLInputElement && target.matches('[data-can-attend]')) {
      this.canAttend = target.checked;
    }
  };
  private readonly onClick = (event: MouseEvent): void => {
    if (event.target instanceof Element && event.target.closest('[data-close]')) this.close();
  };
  private readonly onKeyDown = (event: KeyboardEvent): void => {
    if (event.key === 'Escape' && this.isOpen()) this.close();
  };

  constructor(options: AssignPermissionModalOptions = {}) {
    this.options = options;
    this.service = options.service ?? new PermissionService();
  }

  public mount(target: HTMLElement = document.body): void {
    if (this.host) return;
    this.host = document.createElement('div');
    this.host.innerHTML = `<style>${MODAL_STYLES}</style>${this.renderHtml()}`;
    target.appendChild(this.host);
    this.host.addEventListener('submit', this.onSubmit);
    this.host.addEventListener('change', this.onChange);
    this.host.addEventListener('click', this.onClick);
    document.addEventListener('keydown', this.onKeyDown);
  }

  public async open(user: UserPermissionTarget): Promise<void> {
    if (!user.id.trim()) throw new TypeError('A user ID is required to assign permissions.');
    if (!this.host) this.mount();
    const requestId = ++this.requestId;
    this.user = { ...user };
    this.systemRole = user.role?.toUpperCase() === 'ADMIN' ? 'ADMIN' : 'NHAN_VIEN';
    this.canBook = true;
    this.canAttend = true;
    this.loading = true;
    this.loadFailed = false;
    this.saving = false;
    this.error = '';
    this.render(true);
    this.getDialog()?.focus();

    try {
      const current = await this.service.getUserPermissions(
        user.id,
        user.role?.toUpperCase() === 'ADMIN' ? 'ADMIN' : 'NHAN_VIEN',
      );
      if (requestId !== this.requestId) return;
      this.systemRole = current.systemRole;
      this.canBook = current.canBook;
      this.canAttend = current.canAttend;
      this.loadFailed = false;
    } catch (error) {
      if (requestId !== this.requestId) return;
      this.loadFailed = true;
      this.error = error instanceof Error ? error.message : 'Không thể tải quyền người dùng.';
    } finally {
      if (requestId === this.requestId) {
        this.loading = false;
        this.render(true);
        this.getDialog()?.focus();
      }
    }
  }

  public close(): void {
    if (!this.isOpen()) return;
    this.requestId += 1;
    this.host?.querySelector<HTMLElement>('[data-backdrop]')?.setAttribute('hidden', '');
    this.options.onCancel?.();
  }

  public renderHtml(): string {
    return `
      <div class="us3-modal-backdrop" data-backdrop hidden>
        <section class="us3-modal" role="dialog" aria-modal="true"
          aria-labelledby="us3-modal-title" tabindex="-1">
          <header class="us3-modal__header">
            <h2 id="us3-modal-title">Sửa quyền người dùng</h2>
            <button class="us3-modal__button us3-modal__button--cancel" type="button" data-close aria-label="Đóng">×</button>
          </header>
          <form data-permission-form>
            <div class="us3-modal__body">
              <div class="us3-modal__user">
                <strong>${escapeHtml(this.user?.fullName ?? '')}</strong>
                <span>${escapeHtml(this.user?.email ?? '')}</span>
              </div>
              <label class="us3-modal__field">Vai trò hệ thống
                <select data-system-role ${this.loading || this.saving ? 'disabled' : ''}>
                  <option value="ADMIN" ${this.systemRole === 'ADMIN' ? 'selected' : ''}>ADMIN</option>
                  <option value="NHAN_VIEN" ${this.systemRole === 'NHAN_VIEN' ? 'selected' : ''}>NHAN_VIEN</option>
                </select>
              </label>
              <p><strong>Quyền thao tác</strong></p>
              <label class="us3-modal__permission">
                <input type="checkbox" data-can-book ${this.canBook ? 'checked' : ''}
                  ${this.loading || this.saving ? 'disabled' : ''}>
                <span>Người đặt lịch</span>
              </label>
              <label class="us3-modal__permission">
                <input type="checkbox" data-can-attend ${this.canAttend ? 'checked' : ''}
                  ${this.loading || this.saving ? 'disabled' : ''}>
                <span>Người tham dự</span>
              </label>
              ${this.loading ? '<p role="status">Đang tải quyền...</p>' : ''}
              ${this.error ? `<p class="us3-modal__error" role="alert">${escapeHtml(this.error)}</p>` : ''}
            </div>
            <footer class="us3-modal__footer">
              <button class="us3-modal__button us3-modal__button--cancel" type="button" data-close>Hủy</button>
              <button class="us3-modal__button us3-modal__button--save" type="submit"
                ${this.loading || this.saving || this.loadFailed ? 'disabled' : ''}>${this.saving ? 'Đang lưu...' : 'Lưu quyền'}</button>
            </footer>
          </form>
        </section>
      </div>
    `;
  }

  private async save(): Promise<void> {
    if (!this.user || this.loading || this.saving) return;
    this.saving = true;
    this.error = '';
    this.render(true);
    let saved = false;
    try {
      const dto: UpdateUserPermissionsDto = {
        systemRole: this.systemRole,
        canBook: this.canBook,
        canAttend: this.canAttend,
      };
      const updated = await this.service.updateUserPermissions(this.user.id, dto);
      const user = this.user;
      saved = true;
      this.host?.querySelector<HTMLElement>('[data-backdrop]')?.setAttribute('hidden', '');
      this.options.onSaved?.(user, updated);
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Không thể lưu quyền người dùng.';
    } finally {
      this.saving = false;
      this.render(!saved);
    }
  }

  private render(open: boolean): void {
    if (!this.host) return;
    this.host.innerHTML = `<style>${MODAL_STYLES}</style>${this.renderHtml()}`;
    if (open) this.host.querySelector<HTMLElement>('[data-backdrop]')?.removeAttribute('hidden');
  }

  private getDialog(): HTMLElement | null {
    return this.host?.querySelector<HTMLElement>('[role="dialog"]') ?? null;
  }

  private isOpen(): boolean {
    return Boolean(this.host?.querySelector('[data-backdrop]:not([hidden])'));
  }
}
