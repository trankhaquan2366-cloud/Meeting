import type { RestrictionService } from '../us4_room_booking_restriction';
import type { PermissionService, SystemRole } from '../us3_assign_permissions';
import type { UserListItem } from './types';

export interface BulkUserEditChanges {
  mode: BulkEditMode;
  systemRole?: SystemRole;
  restrictedRoomIds?: string[];
}

export interface BulkUserEditModalOptions {
  permissionService: PermissionService;
  restrictionService: RestrictionService;
  onSaved?: (userIds: string[], changes: BulkUserEditChanges) => void;
}

type BulkEditMode = 'role' | 'rooms';

const BULK_STYLES = `
  .us2-bulk-backdrop { position: fixed; inset: 0; z-index: 1200; display: grid; place-items: center; padding: 20px; background: rgb(15 23 42 / 55%); }
  .us2-bulk-backdrop[hidden] { display: none; }
  .us2-bulk-modal { width: min(100%, 620px); max-height: 90vh; overflow-y: auto; border-radius: 16px; background: #fff; color: #172033; box-shadow: 0 24px 70px rgb(15 23 42 / 28%); font: 14px/1.5 system-ui, sans-serif; }
  .us2-bulk-modal * { box-sizing: border-box; }
  .us2-bulk-modal__header, .us2-bulk-modal__body, .us2-bulk-modal__footer { padding: 18px 22px; }
  .us2-bulk-modal__header { display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #e2e8f0; }
  .us2-bulk-modal__header h2 { margin: 0; font-size: 20px; }
  .us2-bulk-modal__summary { color: #475569; }
  .us2-bulk-modal__mode { display: flex; align-items: flex-start; gap: 10px; margin: 12px 0; padding: 12px; border: 1px solid #e2e8f0; border-radius: 9px; cursor: pointer; }
  .us2-bulk-modal__mode input { margin-top: 4px; accent-color: #2563eb; }
  .us2-bulk-modal__section { margin: 12px 0 16px 25px; }
  .us2-bulk-modal__section[hidden] { display: none; }
  .us2-bulk-modal__select { min-height: 40px; width: 100%; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 8px; background: #fff; font: inherit; }
  .us2-bulk-modal__rooms { display: grid; gap: 8px; max-height: 210px; overflow: auto; }
  .us2-bulk-modal__room { display: flex; align-items: center; gap: 9px; }
  .us2-bulk-modal__room input { accent-color: #dc2626; }
  .us2-bulk-modal__error { white-space: pre-line; color: #b91c1c; }
  .us2-bulk-modal__footer { display: flex; justify-content: flex-end; gap: 9px; border-top: 1px solid #e2e8f0; }
  .us2-bulk-modal__button { min-height: 40px; padding: 8px 14px; border: 0; border-radius: 8px; font: inherit; font-weight: 600; cursor: pointer; }
  .us2-bulk-modal__button:disabled { opacity: .6; cursor: wait; }
  .us2-bulk-modal__button--cancel { background: #f1f5f9; color: #334155; }
  .us2-bulk-modal__button--save { background: #2563eb; color: #fff; }
`;

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[character] ?? character);
}

export class BulkUserEditModal {
  private readonly options: BulkUserEditModalOptions;
  private host: HTMLElement | null = null;
  private users: UserListItem[] = [];
  private rooms: Array<{ id: string; name: string }> = [];
  private roomsLoaded = false;
  private mode: BulkEditMode = 'role';
  private systemRole: 'ADMIN' | 'NHAN_VIEN' = 'NHAN_VIEN';
  private restrictedRoomIds = new Set<string>();
  private loading = false;
  private saving = false;
  private error = '';
  private requestId = 0;

  private readonly onClick = (event: MouseEvent): void => {
    if (event.target instanceof Element && event.target.closest('[data-close]')) this.close();
  };
  private readonly onChange = (event: Event): void => {
    const target = event.target;
    if (!(target instanceof HTMLInputElement) && !(target instanceof HTMLSelectElement)) return;
    if (target.matches('[data-mode]') && target instanceof HTMLInputElement) {
      this.mode = target.value as BulkEditMode;
      this.render(true);
    } else if (target.matches('[data-system-role]') && target instanceof HTMLSelectElement) {
      this.systemRole = target.value as 'ADMIN' | 'NHAN_VIEN';
    } else if (target.matches('[data-room-id]') && target instanceof HTMLInputElement) {
      if (target.checked) this.restrictedRoomIds.add(target.value);
      else this.restrictedRoomIds.delete(target.value);
    }
  };
  private readonly onSubmit = (event: Event): void => {
    event.preventDefault();
    void this.save();
  };
  private readonly onKeyDown = (event: KeyboardEvent): void => {
    if (event.key === 'Escape' && this.isOpen() && !this.saving) this.close();
  };

  constructor(options: BulkUserEditModalOptions) {
    this.options = options;
  }

  public mount(target: HTMLElement = document.body): void {
    if (this.host) return;
    this.host = document.createElement('div');
    this.host.innerHTML = `<style>${BULK_STYLES}</style>${this.renderHtml()}`;
    target.appendChild(this.host);
    this.host.addEventListener('click', this.onClick);
    this.host.addEventListener('change', this.onChange);
    this.host.addEventListener('submit', this.onSubmit);
    document.addEventListener('keydown', this.onKeyDown);
  }

  public async open(users: UserListItem[]): Promise<void> {
    if (!users.length) throw new TypeError('Select at least one user for bulk editing.');
    if (!this.host) this.mount();
    const requestId = ++this.requestId;
    this.users = users.map(user => ({ ...user }));
    this.mode = 'role';
    this.systemRole = 'NHAN_VIEN';
    this.restrictedRoomIds.clear();
    this.roomsLoaded = false;
    this.loading = true;
    this.saving = false;
    this.error = '';
    this.render(true);

    try {
      this.rooms = await this.options.restrictionService.getAvailableRooms();
      if (requestId !== this.requestId) return;
      this.roomsLoaded = true;
    } catch (error) {
      if (requestId !== this.requestId) return;
      this.error = error instanceof Error ? error.message : 'Không thể tải danh sách phòng.';
    } finally {
      if (requestId === this.requestId) {
        this.loading = false;
        this.render(true);
        this.getDialog()?.focus();
      }
    }
  }

  public close(): void {
    if (!this.isOpen() || this.saving) return;
    this.requestId += 1;
    this.host?.querySelector<HTMLElement>('[data-backdrop]')?.setAttribute('hidden', '');
  }

  public renderHtml(): string {
    const roomItems = this.rooms.map(room => `
      <label class="us2-bulk-modal__room">
        <input type="checkbox" data-room-id value="${escapeHtml(room.id)}"
          ${this.restrictedRoomIds.has(room.id) ? 'checked' : ''}
          ${this.loading || this.saving ? 'disabled' : ''}>
        <span>${escapeHtml(room.name)}</span>
      </label>
    `).join('');

    return `
      <div class="us2-bulk-backdrop" data-backdrop hidden>
        <section class="us2-bulk-modal" role="dialog" aria-modal="true"
          aria-labelledby="us2-bulk-title" tabindex="-1">
          <header class="us2-bulk-modal__header">
            <h2 id="us2-bulk-title">Chỉnh sửa đồng bộ</h2>
            <button class="us2-bulk-modal__button us2-bulk-modal__button--cancel"
              type="button" data-close aria-label="Đóng">×</button>
          </header>
          <form data-bulk-form>
            <div class="us2-bulk-modal__body">
              <p class="us2-bulk-modal__summary">Áp dụng cho ${this.users.length} người dùng đã chọn.</p>
              <div class="us2-bulk-modal__mode">
                <input id="us2BulkModeRole" type="radio" name="bulkMode" data-mode value="role"
                  ${this.mode === 'role' ? 'checked' : ''} ${this.saving ? 'disabled' : ''}>
                <div>
                  <label for="us2BulkModeRole"><strong>Cập nhật vai trò hệ thống</strong></label>
                  <div class="us2-bulk-modal__section" ${this.mode !== 'role' ? 'hidden' : ''}>
                    <select class="us2-bulk-modal__select" data-system-role
                      ${this.saving ? 'disabled' : ''}>
                      <option value="NHAN_VIEN" ${this.systemRole === 'NHAN_VIEN' ? 'selected' : ''}>NHAN_VIEN</option>
                      <option value="ADMIN" ${this.systemRole === 'ADMIN' ? 'selected' : ''}>ADMIN</option>
                    </select>
                    <small>Quyền Người đặt lịch/Người tham dự hiện có được giữ nguyên.</small>
                  </div>
                </div>
              </div>
              <div class="us2-bulk-modal__mode">
                <input id="us2BulkModeRooms" type="radio" name="bulkMode" data-mode value="rooms"
                  ${this.mode === 'rooms' ? 'checked' : ''} ${this.saving ? 'disabled' : ''}>
                <div>
                  <label for="us2BulkModeRooms"><strong>Thay danh sách phòng bị cấm đặt</strong></label>
                  <div class="us2-bulk-modal__section" ${this.mode !== 'rooms' ? 'hidden' : ''}>
                    ${this.loading ? '<span role="status">Đang tải danh sách phòng...</span>' : `
                      <span class="us2-bulk-modal__rooms">
                        ${roomItems || '<span>Không có phòng để chọn.</span>'}
                      </span>
                    `}
                    <small>Sẽ thay thế toàn bộ danh sách hiện tại bằng các phòng đã chọn.</small>
                  </div>
                </div>
              </div>
              ${this.error ? `<p class="us2-bulk-modal__error" role="alert">${escapeHtml(this.error)}</p>` : ''}
            </div>
            <footer class="us2-bulk-modal__footer">
              <button class="us2-bulk-modal__button us2-bulk-modal__button--cancel"
                type="button" data-close ${this.saving ? 'disabled' : ''}>Hủy</button>
              <button class="us2-bulk-modal__button us2-bulk-modal__button--save"
                type="submit" ${this.loading || this.saving || (this.mode === 'rooms' && !this.roomsLoaded) ? 'disabled' : ''}>
                ${this.saving ? 'Đang lưu...' : 'Áp dụng'}
              </button>
            </footer>
          </form>
        </section>
      </div>
    `;
  }

  private async save(): Promise<void> {
    if (this.loading || this.saving || !this.users.length
      || (this.mode === 'rooms' && !this.roomsLoaded)) return;
    this.saving = true;
    this.error = '';
    this.render(true);
    const failures: string[] = [];
    const updatedIds: string[] = [];

    for (const user of this.users) {
      try {
        if (this.mode === 'role') {
          const current = await this.options.permissionService.getUserPermissions(
            user.id,
            user.role === 'ADMIN' ? 'ADMIN' : 'NHAN_VIEN',
          );
          await this.options.permissionService.updateUserPermissions(user.id, {
            canBook: current.canBook,
            canAttend: current.canAttend,
            systemRole: this.systemRole,
          });
        } else {
          await this.options.restrictionService.updateUserRestrictions(user.id, {
            restrictedRoomIds: [...this.restrictedRoomIds],
          });
        }
        updatedIds.push(user.id);
      } catch (error) {
        const detail = error instanceof Error ? error.message : 'Lỗi không xác định';
        failures.push(`${user.fullName} (${user.email}): ${detail}`);
      }
    }

    this.saving = false;
    const changes: BulkUserEditChanges = this.mode === 'role'
      ? { mode: 'role', systemRole: this.systemRole }
      : { mode: 'rooms', restrictedRoomIds: [...this.restrictedRoomIds] };
    if (failures.length) {
      this.error = `Đã cập nhật ${updatedIds.length}/${this.users.length} tài khoản. Không cập nhật được:\n${failures.join('\n')}`;
      this.options.onSaved?.(updatedIds, changes);
      this.render(true);
      return;
    }

    this.host?.querySelector<HTMLElement>('[data-backdrop]')?.setAttribute('hidden', '');
    this.options.onSaved?.(updatedIds, changes);
  }

  private render(open: boolean): void {
    if (!this.host) return;
    this.host.innerHTML = `<style>${BULK_STYLES}</style>${this.renderHtml()}`;
    if (open) this.host.querySelector<HTMLElement>('[data-backdrop]')?.removeAttribute('hidden');
  }

  private getDialog(): HTMLElement | null {
    return this.host?.querySelector<HTMLElement>('[role="dialog"]') ?? null;
  }

  private isOpen(): boolean {
    return Boolean(this.host?.querySelector('[data-backdrop]:not([hidden])'));
  }
}
