export type SystemRole = 'ADMIN' | 'NHAN_VIEN';

export interface UserPermissionTarget {
  id: string;
  fullName: string;
  email: string;
  role?: string;
}

export interface UserPermissions {
  userId: string;
  systemRole: SystemRole;
  canBook: boolean;
  canAttend: boolean;
}

export interface UpdateUserPermissionsDto {
  systemRole: SystemRole;
  canBook: boolean;
  canAttend: boolean;
}
