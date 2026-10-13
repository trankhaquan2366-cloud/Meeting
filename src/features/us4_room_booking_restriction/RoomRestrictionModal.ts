import type {
  RestrictionUser,
  RoomOption,
  UpdateUserRestrictionDto,
} from './types';
import { RestrictionService } from './restrictionService';

export interface RoomRestrictionModalOptions {
  service?: RestrictionService;
  onSaved?: () => void;
  onCancel?: () => void;
}

const MODAL_STYLES = `
  .us4-modal-backdrop {
    position: fixed; inset: 0; z-index: 1000; display: grid; place-items: center;
    overflow-y: auto; padding: 20px; background: rgb(15 23 42 / 55%);
  }
  .us4-modal-backdrop[hidden] { display: none; }
  .us4-modal {
    width: min(100%, 560px); max-height: min(90vh, 760px); overflow-y: auto;
    border-radius: 16px; background: #fff; color: #172033;
    box-shadow: 0 24px 70px rgb(15 23 42 / 28%);
    font: 14px/1.5 system-ui, sans-serif;
  }
  .us4-modal * { box-sizing: border-box; }
  .us4-modal__header, .us4-modal__footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  .us4-modal__header { padding: 20px 24px 12px; }
  .us4-modal__header h2 { margin: 0; font-size: 20px; }
  .us4-modal__body { padding: 8px 24px 20px; }
  .us4-modal__user { display: grid; gap: 4px; margin-bottom: 18px; padding: 12px 14px; border-radius: 9px; background: #f8fafc; }
  .us4-modal__user span { color: #475569; overflow-wrap: anywhere; }
  .us4-modal__section-title { margin: 0 0 8px; font-weight: 650; }
  .us4-modal__room-list { display: grid; gap: 8px; max-height: 250px; overflow-y: auto; }
  .us4-modal__room { display: flex; align-items: flex-start; gap: 10px; padding: 10px 12px; border: 1px solid #e2e8f0; border-radius: 9px; cursor: pointer; }
  .us4-modal__room input { margin-top: 3px; accent-color: #dc2626; }
  .us4-modal__room small { display: block; color: #64748b; }
  .us4-modal__reason { display: grid; gap: 6px; margin-top: 18px; }
  .us4-modal__reason textarea { width: 100%; resize: vertical; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px 12px; font: inherit; }
  .us4-modal__error { margin: 12px 0 0; color: #b91c1c; }
  .us4-modal__footer { justify-content: flex-end; padding: 14px 24px 20px; }
  .us4-modal__button { min-height: 40px; padding: 8px 14px; border: 0; border-radius: 8px; font: inherit; font-weight: 600; cursor: pointer; }
  .us4-modal__button:disabled { opacity: .6; cursor: wait; }
  .us4-modal__button--cancel { background: #f1f5f9; color: #334155; }
  .us4-modal__button--save { background: #2563eb; color: #fff; }
  .us4-modal__close { border: 0; background: transparent; color: #64748b; font-size: 24px; cursor: pointer; }
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

export class RoomRestrictionModal {
  private readonly service: RestrictionService;
  private readonly options: RoomRestrictionModalOptions;
  private host: HTMLElement | null = null;
  private user: RestrictionUser | null = null;
  private rooms: RoomOption[] = [];
  private restrictedRoomIds = new Set<string>();
  private reason = '';
  private error = '';
  private loading = false;
  private restrictionsLoaded = false;
  private saving = false;
  private requestId = 0;
  private readonly onKeyDown = (event: KeyboardEvent): void => {
    if (event.key === 'Escape' && this.isOpen()) this.close();
  };
  private readonly onSubmit = (event: Event): void => {
    event.preventDefault();
    void this.save();
  };
  private readonly onClick = (event: MouseEvent): void => {
    const target = event.target;
    if (!(target instanceof Element)) return;
    if (target.closest('[data-close-modal]')) this.close();
  };
  private readonly onChange = (event: Event): void => {
    const target = event.target;
    if (target instanceof HTMLInputElement && target.matches('[data-room-id]')) {
      if (target.checked) this.restrictedRoomIds.add(target.value);
      else this.restrictedRoomIds.delete(target.value);
    }
    if (target instanceof HTMLTextAreaElement && target.matches('[data-reason]')) {
      this.reason = target.value;
    }
  };

  constructor(options: RoomRestrictionModalOptions = {}) {
    this.options = options;
    this.service = options.service ?? new RestrictionService();
  }

  public mount(target: HTMLElement = document.body): void {
    if (this.host) return;

    const host = document.createElement('div');
    host.innerHTML = `<style>${MODAL_STYLES}</style>${this.renderHtml()}`;
    target.appendChild(host);
    this.host = host;
    host.addEventListener('click', this.onClick);
    host.addEventListener('submit', this.onSubmit);
    host.addEventListener('change', this.onChange);
    document.addEventListener('keydown', this.onKeyDown);
  }

  public async open(user: RestrictionUser): Promise<void> {
    if (!user.id.trim()) throw new TypeError('A user ID is required to edit room restrictions.');
    if (typeof user.fullName !== 'string' || typeof user.email !== 'string') {
      throw new TypeError('The selected user must have a name and email address.');
    }
    if (!this.host) this.mount();

    const requestId = ++this.requestId;
    this.user = { ...user };
    this.rooms = [];
    this.restrictedRoomIds.clear();
    this.reason = '';
    this.error = '';
    this.loading = true;
    this.restrictionsLoaded = false;
    this.saving = false;
    this.render();
    this.host?.querySelector<HTMLElement>('[data-backdrop]')?.removeAttribute('hidden');
    this.getDialog()?.focus();

    try {
      const [rooms, restrictions] = await Promise.all([
        this.service.getAvailableRooms(),
        this.service.getUserRestrictions(user.id),
      ]);
      if (requestId !== this.requestId) return;
      this.rooms = rooms;
      this.restrictedRoomIds = new Set(restrictions.restrictedRoomIds);
      this.reason = restrictions.reason;
      this.restrictionsLoaded = true;
    } catch (error) {
      if (requestId !== this.requestId) return;
      this.restrictionsLoaded = false;
      this.error = error instanceof Error ? error.message : 'Không thể tải cấu hình hạn chế.';
    } finally {
      if (requestId === this.requestId) {
        this.loading = false;
        this.render();
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
    const roomList = this.loading
      ? '<p role="status">Đang tải danh sách phòng...</p>'
      : this.rooms.length
        ? this.rooms.map(room => this.renderRoom(room)).join('')
        : '<p>Không có phòng họp để cấu hình.</p>';

    return `
      <div class="us4-modal-backdrop" data-backdrop hidden>
        <section class="us4-modal" role="dialog" aria-modal="true"
          aria-labelledby="us4-modal-title" tabindex="-1">
          <header class="us4-modal__header">
            <h2 id="us4-modal-title">Giới hạn quyền đặt phòng</h2>
            <button class="us4-modal__close" type="button" data-close-modal
              aria-label="Đóng cửa sổ">×</button>
          </header>
          <form data-restriction-form>
            <div class="us4-modal__body">
              <div class="us4-modal__user">
                <strong>${escapeHtml(this.user?.fullName ?? '')}</strong>
                <span>${escapeHtml(this.user?.email ?? '')}</span>
              </div>
              <p class="us4-modal__section-title">Chọn phòng bị cấm đặt</p>
              <div class="us4-modal__room-list">${roomList}</div>
              <label class="us4-modal__reason">
                <span>Lý do hạn chế (tùy chọn)</span>
                <textarea data-reason rows="3" maxlength="1000"
                  placeholder="Nhập lý do...">${escapeHtml(this.reason)}</textarea>
              </label>
              ${this.error ? `<p class="us4-modal__error" role="alert">${escapeHtml(this.error)}</p>` : ''}
            </div>
            <footer class="us4-modal__footer">
              <button class="us4-modal__button us4-modal__button--cancel" type="button"
                data-close-modal>Hủy</button>
              <button class="us4-modal__button us4-modal__button--save" type="submit"
                ${this.loading || this.saving || !this.restrictionsLoaded ? 'disabled' : ''}>
                ${this.saving ? 'Đang lưu...' : 'Lưu cấu hình'}
              </button>
            </footer>
          </form>
        </section>
      </div>
    `;
  }

  private renderRoom(room: RoomOption): string {
    const checked = this.restrictedRoomIds.has(room.id) ? 'checked' : '';
    const location = room.location ? `<small>${escapeHtml(room.location)}</small>` : '';
    return `
      <label class="us4-modal__room">
        <input type="checkbox" data-room-id value="${escapeHtml(room.id)}" ${checked}
          ${this.loading || this.saving ? 'disabled' : ''}>
        <span><strong>${escapeHtml(room.name)}</strong>${location}</span>
      </label>
    `;
  }

  private async save(): Promise<void> {
    if (!this.user || this.loading || this.saving || !this.restrictionsLoaded) return;
    this.saving = true;
    this.error = '';
    this.syncFormState();

    const dto: UpdateUserRestrictionDto = {
      restrictedRoomIds: [...this.restrictedRoomIds],
      reason: this.reason.trim(),
    };

    try {
      await this.service.updateUserRestrictions(this.user.id, dto);
      this.host?.querySelector<HTMLElement>('[data-backdrop]')?.setAttribute('hidden', '');
      this.options.onSaved?.();
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Không thể lưu cấu hình hạn chế.';
      this.render();
    } finally {
      this.saving = false;
      this.syncFormState();
    }
  }

  private syncFormState(): void {
    const submit = this.host?.querySelector<HTMLButtonElement>('[type="submit"]');
    if (submit) {
      submit.disabled = this.loading || this.saving;
      submit.textContent = this.saving ? 'Đang lưu...' : 'Lưu cấu hình';
    }
    this.host?.querySelectorAll<HTMLInputElement>('[data-room-id]').forEach(input => {
      input.disabled = this.loading || this.saving;
    });
  }

  private render(): void {
    if (!this.host) return;
    const wasOpen = this.isOpen();
    this.host.innerHTML = `<style>${MODAL_STYLES}</style>${this.renderHtml()}`;
    if (wasOpen) {
      this.host.querySelector<HTMLElement>('[data-backdrop]')?.removeAttribute('hidden');
      this.getDialog()?.focus();
    }
  }

  private getDialog(): HTMLElement | null {
    return this.host?.querySelector<HTMLElement>('[role="dialog"]') ?? null;
  }

  private isOpen(): boolean {
    return Boolean(this.host?.querySelector('[data-backdrop]:not([hidden])'));
  }
}
