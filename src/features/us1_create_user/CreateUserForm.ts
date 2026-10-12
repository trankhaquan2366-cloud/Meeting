import { CreateUserDto, CreateUserResponse, UserRole } from './types';
import { UserService } from './userService';

export interface CreateUserFormOptions {
  containerId?: string;
  userService?: UserService;
  onSuccess?: (response: CreateUserResponse) => void;
  onError?: (error: Error | string, response?: CreateUserResponse) => void;
}

export class CreateUserForm {
  private userService: UserService;
  private container: HTMLElement | null = null;
  private options: CreateUserFormOptions;

  constructor(options: CreateUserFormOptions = {}) {
    this.options = options;
    this.userService = options.userService || new UserService();
    if (options.containerId && typeof document !== 'undefined') {
      this.container = document.getElementById(options.containerId);
    }
  }

  /**
   * Tạo cấu trúc HTML cho Form tạo người dùng
   */
  public renderHtml(): string {
    return `
      <form id="createUserForm" class="create-user-form" novalidate>
        <div class="form-header">
          <h3>Tạo Tài Khoản Người Dùng Mới</h3>
          <p class="subtitle">Nhập thông tin nhân viên để cấp quyền truy cập hệ thống</p>
        </div>

        <div id="formAlert" class="form-alert" style="display: none;"></div>

        <div class="form-group">
          <label for="fullNameInput">Họ và tên <span class="required">*</span></label>
          <input
            type="text"
            id="fullNameInput"
            name="fullName"
            placeholder="Ví dụ: Nguyễn Văn A"
            autocomplete="name"
          />
          <span id="fullNameError" class="field-error" style="display: none;"></span>
        </div>

        <div class="form-group">
          <label for="emailInput">Địa chỉ Email <span class="required">*</span></label>
          <input
            type="email"
            id="emailInput"
            name="email"
            placeholder="example@company.com"
            autocomplete="email"
          />
          <span id="emailError" class="field-error" style="display: none;"></span>
        </div>

        <div class="form-group">
          <label for="roleSelect">Vai trò trong hệ thống <span class="required">*</span></label>
          <select id="roleSelect" name="role">
            <option value="NHAN_VIEN" selected>Nhân viên (NHAN_VIEN)</option>
            <option value="ADMIN">Quản trị viên (ADMIN)</option>
          </select>
          <span id="roleError" class="field-error" style="display: none;"></span>
        </div>

        <div class="form-actions">
          <button type="submit" id="submitBtn" class="btn btn-primary">
            Tạo tài khoản & Gửi mật khẩu tạm
          </button>
        </div>
      </form>
    `;
  }

  /**
   * Gắn form vào container DOM và lắng nghe sự kiện
   */
  public mount(targetElement?: HTMLElement): void {
    const el = targetElement || this.container;
    if (!el) {
      throw new Error('Container element not found for CreateUserForm');
    }
    el.innerHTML = this.renderHtml();
    this.bindEvents(el);
  }

  /**
   * Đăng ký event listeners cho form
   */
  public bindEvents(rootElement: HTMLElement = document.body): void {
    const form = rootElement.querySelector<HTMLFormElement>('#createUserForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      await this.handleSubmit(form);
    });

    const emailInput = rootElement.querySelector<HTMLInputElement>('#emailInput');
    if (emailInput) {
      emailInput.addEventListener('input', () => {
        this.clearFieldError(rootElement, 'email');
      });
    }

    const fullNameInput = rootElement.querySelector<HTMLInputElement>('#fullNameInput');
    if (fullNameInput) {
      fullNameInput.addEventListener('input', () => {
        this.clearFieldError(rootElement, 'fullName');
      });
    }
  }

  public getFormData(form: HTMLFormElement): CreateUserDto {
    const fullNameInput = form.querySelector<HTMLInputElement>('#fullNameInput');
    const emailInput = form.querySelector<HTMLInputElement>('#emailInput');
    const roleSelect = form.querySelector<HTMLSelectElement>('#roleSelect');

    return {
      fullName: fullNameInput?.value || '',
      email: emailInput?.value || '',
      role: (roleSelect?.value as UserRole) || 'NHAN_VIEN',
    };
  }

  public async handleSubmit(form: HTMLFormElement): Promise<CreateUserResponse> {
    const data = this.getFormData(form);
    const submitBtn = form.querySelector<HTMLButtonElement>('#submitBtn');
    const alertBox = form.querySelector<HTMLElement>('#formAlert');

    // Reset errors
    this.clearAllErrors(form);

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerText = 'Đang xử lý...';
    }

    try {
      const response = await this.userService.createUser(data);

      if (!response.success) {
        if (response.errors) {
          for (const [field, message] of Object.entries(response.errors)) {
            this.showFieldError(form, field, message);
          }
        }
        if (alertBox) {
          alertBox.className = 'form-alert alert-danger';
          alertBox.innerText = response.message;
          alertBox.style.display = 'block';
        }
        if (this.options.onError) {
          this.options.onError(response.message, response);
        }
        return response;
      }

      // Success
      if (alertBox) {
        alertBox.className = 'form-alert alert-success';
        alertBox.innerHTML = `
          <strong>${response.message}!</strong><br/>
          Tài khoản: ${response.user?.email}<br/>
          Mật khẩu tạm: <code>${response.temporaryPassword}</code><br/>
          ${response.emailSent ? 'Đã gửi email thông tin đăng nhập tới người dùng.' : 'Chưa gửi được email, vui lòng bàn giao trực tiếp.'}
        `;
        alertBox.style.display = 'block';
      }

      form.reset();
      const roleSelect = form.querySelector<HTMLSelectElement>('#roleSelect');
      if (roleSelect) {
        roleSelect.value = 'NHAN_VIEN';
      }

      if (this.options.onSuccess) {
        this.options.onSuccess(response);
      }
      return response;
    } catch (err: any) {
      const errorMsg = err.message || 'Lỗi không xác định khi tạo tài khoản';
      if (alertBox) {
        alertBox.className = 'form-alert alert-danger';
        alertBox.innerText = errorMsg;
        alertBox.style.display = 'block';
      }
      if (this.options.onError) {
        this.options.onError(errorMsg);
      }
      return {
        success: false,
        message: errorMsg,
      };
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerText = 'Tạo tài khoản & Gửi mật khẩu tạm';
      }
    }
  }

  private showFieldError(root: HTMLElement, fieldName: string, message: string): void {
    const errorEl = root.querySelector<HTMLElement>(`#${fieldName}Error`);
    const inputEl = root.querySelector<HTMLElement>(`#${fieldName}Input`);
    if (errorEl) {
      errorEl.innerText = message;
      errorEl.style.display = 'block';
    }
    if (inputEl) {
      inputEl.classList.add('input-invalid');
    }
  }

  private clearFieldError(root: HTMLElement, fieldName: string): void {
    const errorEl = root.querySelector<HTMLElement>(`#${fieldName}Error`);
    const inputEl = root.querySelector<HTMLElement>(`#${fieldName}Input`);
    if (errorEl) {
      errorEl.style.display = 'none';
      errorEl.innerText = '';
    }
    if (inputEl) {
      inputEl.classList.remove('input-invalid');
    }
  }

  private clearAllErrors(root: HTMLElement): void {
    const errors = root.querySelectorAll<HTMLElement>('.field-error');
    errors.forEach((el) => {
      el.style.display = 'none';
      el.innerText = '';
    });
    const inputs = root.querySelectorAll<HTMLElement>('.input-invalid');
    inputs.forEach((el) => el.classList.remove('input-invalid'));
    const alertBox = root.querySelector<HTMLElement>('#formAlert');
    if (alertBox) {
      alertBox.style.display = 'none';
      alertBox.innerText = '';
    }
  }
}
