import { CreateUserDto, CreateUserResponse, User, UserRole } from './types';

export interface EmailSender {
  sendTemporaryPassword(toEmail: string, fullName: string, tempPassword: string): Promise<boolean>;
}

export class DefaultEmailSender implements EmailSender {
  async sendTemporaryPassword(toEmail: string, fullName: string, tempPassword: string): Promise<boolean> {
    // Giả lập gửi mail hệ thống (SMTP / Cloud Provider)
    return true;
  }
}

export interface UserRepository {
  findByEmail(email: string): Promise<User | null> | User | null;
  save(user: User): Promise<User> | User;
  getAll(): Promise<User[]> | User[];
  clear(): void;
}

export class InMemoryUserRepository implements UserRepository {
  private users: Map<string, User> = new Map();

  findByEmail(email: string): User | null {
    const normalized = email.trim().toLowerCase();
    for (const user of this.users.values()) {
      if (user.email.toLowerCase() === normalized) {
        return user;
      }
    }
    return null;
  }

  save(user: User): User {
    this.users.set(user.id, user);
    return user;
  }

  getAll(): User[] {
    return Array.from(this.users.values());
  }

  clear(): void {
    this.users.clear();
  }
}

export class UserService {
  private userRepo: UserRepository;
  private emailSender: EmailSender;

  constructor(userRepo?: UserRepository, emailSender?: EmailSender) {
    this.userRepo = userRepo || new InMemoryUserRepository();
    this.emailSender = emailSender || new DefaultEmailSender();
  }

  /**
   * Sinh mật khẩu tạm thời ngẫu nhiên từ 8 đến 12 ký tự
   * Đảm bảo bao gồm chữ hoa, chữ thường, chữ số và ký tự đặc biệt
   */
  public generateTemporaryPassword(minLength: number = 8, maxLength: number = 12): string {
    const uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    const lowercase = 'abcdefghijklmnopqrstuvwxyz';
    const numbers = '0123456789';
    const specialChars = '!@#$%^&*';
    const allChars = uppercase + lowercase + numbers + specialChars;

    // Chọn ngẫu nhiên độ dài từ minLength đến maxLength
    const length = Math.floor(Math.random() * (maxLength - minLength + 1)) + minLength;

    const passwordChars: string[] = [
      uppercase[Math.floor(Math.random() * uppercase.length)],
      lowercase[Math.floor(Math.random() * lowercase.length)],
      numbers[Math.floor(Math.random() * numbers.length)],
      specialChars[Math.floor(Math.random() * specialChars.length)],
    ];

    while (passwordChars.length < length) {
      passwordChars.push(allChars[Math.floor(Math.random() * allChars.length)]);
    }

    // Trộn ngẫu nhiên các ký tự
    for (let i = passwordChars.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [passwordChars[i], passwordChars[j]] = [passwordChars[j], passwordChars[i]];
    }

    return passwordChars.join('');
  }

  /**
   * Kiểm tra định dạng email hợp lệ
   */
  public validateEmailFormat(email: string): boolean {
    const trimmed = email.trim();
    if (trimmed.includes('..') || trimmed.startsWith('.') || trimmed.endsWith('.')) {
      return false;
    }
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9]+([.-][a-zA-Z0-9]+)*\.[a-zA-Z]{2,}$/;
    return emailRegex.test(trimmed);
  }

  /**
   * Validate dữ liệu đầu vào của CreateUserDto
   */
  public validateInput(dto: CreateUserDto): { isValid: boolean; errors: Record<string, string> } {
    const errors: Record<string, string> = {};

    if (!dto.fullName || dto.fullName.trim().length === 0) {
      errors.fullName = 'Họ tên không được để trống';
    } else if (dto.fullName.trim().length < 2) {
      errors.fullName = 'Họ tên phải có ít nhất 2 ký tự';
    }

    if (!dto.email || dto.email.trim().length === 0) {
      errors.email = 'Email không được để trống';
    } else if (!this.validateEmailFormat(dto.email)) {
      errors.email = 'Email không đúng định dạng';
    }

    const validRoles: UserRole[] = ['NHAN_VIEN', 'ADMIN'];
    if (!dto.role || !validRoles.includes(dto.role)) {
      errors.role = 'Vai trò không hợp lệ (chỉ chấp nhận NHAN_VIEN hoặc ADMIN)';
    }

    return {
      isValid: Object.keys(errors).length === 0,
      errors,
    };
  }

  /**
   * Tạo tài khoản người dùng mới
   */
  public async createUser(dto: CreateUserDto): Promise<CreateUserResponse> {
    // 1. Validate dữ liệu
    const validation = this.validateInput(dto);
    if (!validation.isValid) {
      return {
        success: false,
        message: 'Dữ liệu đầu vào không hợp lệ',
        errors: validation.errors,
      };
    }

    const normalizedEmail = dto.email.trim().toLowerCase();
    const cleanFullName = dto.fullName.trim();

    // 2. Kiểm tra trùng lặp email
    const existingUser = await this.userRepo.findByEmail(normalizedEmail);
    if (existingUser) {
      return {
        success: false,
        message: 'Email đã tồn tại trên hệ thống',
        errors: {
          email: 'Email này đã được sử dụng',
        },
      };
    }

    // 3. Sinh mật khẩu tạm ngẫu nhiên (8 - 12 ký tự)
    const temporaryPassword = this.generateTemporaryPassword(8, 12);

    // 4. Lưu user
    const newUser: User = {
      id: 'USR_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7),
      fullName: cleanFullName,
      email: normalizedEmail,
      role: dto.role,
      createdAt: new Date().toISOString(),
    };

    await this.userRepo.save(newUser);

    // 5. Gửi email thông báo tài khoản & mật khẩu tạm
    let emailSent = false;
    try {
      emailSent = await this.emailSender.sendTemporaryPassword(
        newUser.email,
        newUser.fullName,
        temporaryPassword
      );
    } catch {
      emailSent = false;
    }

    return {
      success: true,
      message: 'Tạo tài khoản người dùng thành công',
      user: newUser,
      temporaryPassword,
      emailSent,
    };
  }
}
