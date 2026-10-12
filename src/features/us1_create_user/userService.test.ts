import { describe, it, expect, beforeEach, vi } from 'vitest';
import { UserService, InMemoryUserRepository, EmailSender } from './userService';
import { CreateUserDto } from './types';
import { CreateUserForm } from './CreateUserForm';

describe('US1: Create User Feature - UserService Unit Tests', () => {
  let userRepo: InMemoryUserRepository;
  let mockEmailSender: EmailSender;
  let userService: UserService;

  beforeEach(() => {
    userRepo = new InMemoryUserRepository();
    mockEmailSender = {
      sendTemporaryPassword: vi.fn().mockResolvedValue(true),
    };
    userService = new UserService(userRepo, mockEmailSender);
  });

  describe('1. Random Temporary Password Generation', () => {
    it('should generate a temporary password between 8 and 12 characters', () => {
      for (let i = 0; i < 20; i++) {
        const password = userService.generateTemporaryPassword(8, 12);
        expect(password.length).toBeGreaterThanOrEqual(8);
        expect(password.length).toBeLessThanOrEqual(12);
      }
    });

    it('should contain uppercase, lowercase, numbers and special characters', () => {
      const password = userService.generateTemporaryPassword(8, 12);
      expect(/[A-Z]/.test(password)).toBe(true);
      expect(/[a-z]/.test(password)).toBe(true);
      expect(/[0-9]/.test(password)).toBe(true);
      expect(/[!@#$%^&*]/.test(password)).toBe(true);
    });
  });

  describe('2. Input Validation', () => {
    it('should reject empty or whitespace-only fullName', () => {
      const result = userService.validateInput({
        fullName: '   ',
        email: 'test@example.com',
        role: 'NHAN_VIEN',
      });
      expect(result.isValid).toBe(false);
      expect(result.errors.fullName).toBeDefined();
    });

    it('should reject fullName with fewer than 2 characters', () => {
      const result = userService.validateInput({
        fullName: 'A',
        email: 'test@example.com',
        role: 'NHAN_VIEN',
      });
      expect(result.isValid).toBe(false);
      expect(result.errors.fullName).toContain('ít nhất 2 ký tự');
    });

    it('should reject invalid email formats', () => {
      const invalidEmails = [
        'invalid-email',
        'test@',
        'test@domain',
        '@domain.com',
        'user@domain..com',
        'user name@domain.com',
      ];

      for (const email of invalidEmails) {
        const result = userService.validateInput({
          fullName: 'Nguyễn Văn A',
          email,
          role: 'NHAN_VIEN',
        });
        expect(result.isValid).toBe(false);
        expect(result.errors.email).toBeDefined();
      }
    });

    it('should accept valid email formats', () => {
      const validEmails = [
        'user@example.com',
        'admin.user@domain.vn',
        'staff_123@sub.domain.org',
      ];

      for (const email of validEmails) {
        const result = userService.validateInput({
          fullName: 'Nguyễn Văn A',
          email,
          role: 'NHAN_VIEN',
        });
        expect(result.isValid).toBe(true);
      }
    });

    it('should reject invalid role', () => {
      const result = userService.validateInput({
        fullName: 'Nguyễn Văn A',
        email: 'user@example.com',
        role: 'SUPERADMIN' as any,
      });
      expect(result.isValid).toBe(false);
      expect(result.errors.role).toBeDefined();
    });
  });

  describe('3. Duplicate Email Check & User Creation', () => {
    it('should successfully create a new user with role NHAN_VIEN and send email', async () => {
      const dto: CreateUserDto = {
        fullName: 'Trần Văn Nhân Viên',
        email: 'nhanvien@congty.com',
        role: 'NHAN_VIEN',
      };

      const response = await userService.createUser(dto);

      expect(response.success).toBe(true);
      expect(response.user).toBeDefined();
      expect(response.user?.fullName).toBe('Trần Văn Nhân Viên');
      expect(response.user?.email).toBe('nhanvien@congty.com');
      expect(response.user?.role).toBe('NHAN_VIEN');
      expect(response.temporaryPassword).toBeDefined();
      expect(response.temporaryPassword!.length).toBeGreaterThanOrEqual(8);
      expect(response.temporaryPassword!.length).toBeLessThanOrEqual(12);
      expect(response.emailSent).toBe(true);

      // Verify emailSender was invoked
      expect(mockEmailSender.sendTemporaryPassword).toHaveBeenCalledWith(
        'nhanvien@congty.com',
        'Trần Văn Nhân Viên',
        response.temporaryPassword
      );

      // Verify user is persisted in repository
      const savedUser = userRepo.findByEmail('nhanvien@congty.com');
      expect(savedUser).not.toBeNull();
      expect(savedUser?.id).toBe(response.user?.id);
    });

    it('should successfully create a new user with role ADMIN', async () => {
      const dto: CreateUserDto = {
        fullName: 'Lê Quản Trị',
        email: 'admin@congty.com',
        role: 'ADMIN',
      };

      const response = await userService.createUser(dto);

      expect(response.success).toBe(true);
      expect(response.user?.role).toBe('ADMIN');
      expect(response.emailSent).toBe(true);
    });

    it('should prevent duplicate email registration (case-insensitive)', async () => {
      const dto1: CreateUserDto = {
        fullName: 'Người Dùng 1',
        email: 'user@congty.com',
        role: 'NHAN_VIEN',
      };
      await userService.createUser(dto1);

      // Attempt to register with uppercase email
      const dto2: CreateUserDto = {
        fullName: 'Người Dùng 2',
        email: 'USER@congty.com',
        role: 'ADMIN',
      };
      const response2 = await userService.createUser(dto2);

      expect(response2.success).toBe(false);
      expect(response2.message).toContain('Email đã tồn tại');
      expect(response2.errors?.email).toBeDefined();
      expect(userRepo.getAll().length).toBe(1);
    });

    it('should handle email sending failure gracefully', async () => {
      const failingEmailSender: EmailSender = {
        sendTemporaryPassword: vi.fn().mockRejectedValue(new Error('SMTP connection error')),
      };
      const customService = new UserService(userRepo, failingEmailSender);

      const dto: CreateUserDto = {
        fullName: 'Người Dùng Test Mail Lỗi',
        email: 'failmail@congty.com',
        role: 'NHAN_VIEN',
      };

      const response = await customService.createUser(dto);
      expect(response.success).toBe(true);
      expect(response.emailSent).toBe(false);
      expect(response.user).toBeDefined();
    });
  });

  describe('4. CreateUserForm UI Component', () => {
    it('should render HTML with required fields and NHAN_VIEN default selected', () => {
      const form = new CreateUserForm();
      const html = form.renderHtml();

      expect(html).toContain('id="fullNameInput"');
      expect(html).toContain('id="emailInput"');
      expect(html).toContain('id="roleSelect"');
      expect(html).toContain('value="NHAN_VIEN" selected');
      expect(html).toContain('value="ADMIN"');
      expect(html).toContain('id="createUserForm"');
    });
  });
});
