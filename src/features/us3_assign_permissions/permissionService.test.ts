import { describe, expect, it } from 'vitest';
import { PermissionService } from './permissionService';

describe('PermissionService', () => {
  it('persists system roles and operation permissions in mock mode', async () => {
    const service = new PermissionService();

    const updated = await service.updateUserPermissions('permission-test-user', {
      systemRole: 'ADMIN',
      canBook: false,
      canAttend: true,
    });
    const loaded = await service.getUserPermissions('permission-test-user');

    expect(updated).toEqual({
      userId: 'permission-test-user',
      systemRole: 'ADMIN',
      canBook: false,
      canAttend: true,
    });
    expect(loaded).toEqual(updated);
  });

  it('rejects unsupported role values', async () => {
    const service = new PermissionService();

    await expect(service.updateUserPermissions('permission-invalid-role', {
      systemRole: 'BOOKER' as 'ADMIN',
      canBook: true,
      canAttend: true,
    })).rejects.toThrow('systemRole must be ADMIN or NHAN_VIEN.');
  });
});
