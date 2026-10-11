export type UserRole = 'NHAN_VIEN' | 'ADMIN';

export interface CreateUserDto {
  fullName: string;
  email: string;
  role: UserRole;
}

export interface User {
  id: string;
  fullName: string;
  email: string;
  role: UserRole;
  createdAt: string;
}

export interface CreateUserResponse {
  success: boolean;
  message: string;
  user?: User;
  temporaryPassword?: string;
  emailSent?: boolean;
  errors?: Record<string, string>;
}
