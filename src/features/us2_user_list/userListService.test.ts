import { describe, expect, it } from 'vitest';
import { UserListService } from './userListService';

describe('UserListService', () => {
  it('returns mock users in pages of ten by default', async () => {
    const service = new UserListService({ useMock: true });
    const firstPage = await service.getUsers();
    const secondPage = await service.getUsers({ page: 2 });

    expect(firstPage.items).toHaveLength(10);
    expect(firstPage.total).toBe(24);
    expect(secondPage.items).toHaveLength(10);
    expect(secondPage.page).toBe(2);
  });

  it('filters mock users by search text and role', async () => {
    const service = new UserListService({ useMock: true });
    const result = await service.getUsers({ search: 'EXAMPLE.COM', role: 'ADMIN' });

    expect(result.items.length).toBeGreaterThan(0);
    expect(result.items.every(user => user.role === 'ADMIN')).toBe(true);
    expect(result.items.every(user => user.email.includes('example.com'))).toBe(true);
  });

  it('sends supported query parameters to the API', async () => {
    let requestedUrl = '';
    const service = new UserListService({
      useMock: false,
      baseUrl: 'https://example.test/api/users',
      fetcher: async input => {
        requestedUrl = String(input);
        return new Response(JSON.stringify({
          items: [{
            id: 42,
            full_name: 'Nguyễn Minh Tuấn',
            email: 'tuan@example.com',
            role: 'ADMIN',
            status: 'ACTIVE',
            created_at: '2025-01-08T09:15:00.000Z',
          }],
          total: 1,
          page: 3,
          limit: 5,
        }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      },
    });

    const result = await service.getUsers({
      page: 3,
      limit: 5,
      search: 'Minh Tuấn',
      role: 'ADMIN',
    });
    const url = new URL(requestedUrl);

    expect(url.searchParams.get('page')).toBe('3');
    expect(url.searchParams.get('limit')).toBe('5');
    expect(url.searchParams.get('search')).toBe('Minh Tuấn');
    expect(url.searchParams.get('role')).toBe('admin');
    expect(result.items[0].id).toBe('42');
    expect(result.items[0].fullName).toBe('Nguyễn Minh Tuấn');
  });

  it('accepts manager and unknown API roles', async () => {
    const service = new UserListService({
      fetcher: async () => new Response(JSON.stringify({
        items: [
          { id: 1, full_name: 'Quản lý', role: 'MANAGER', status: 'ACTIVE', created_at: '2025-01-08T09:15:00.000Z' },
          { id: 2, full_name: 'Kiểm toán', role: 'AUDITOR', status: 'ACTIVE', created_at: '2025-01-08T09:15:00.000Z' },
        ],
        total: 2,
      }), { status: 200 }),
    });

    const result = await service.getUsers();

    expect(result.items.map(user => user.role)).toEqual(['MANAGER', 'AUDITOR']);
  });

  it('accepts locked account status from the API', async () => {
    const service = new UserListService({
      fetcher: async () => new Response(JSON.stringify({
        items: [{
          id: 3,
          full_name: 'Tài khoản bị khóa',
          role: 'EMPLOYEE',
          status: 'LOCKED',
          created_at: '2025-01-08T09:15:00.000Z',
        }],
        total: 1,
      }), { status: 200 }),
    });

    const result = await service.getUsers();

    expect(result.items[0].status).toBe('LOCKED');
  });

  it('rejects invalid pagination instead of silently returning mock results', async () => {
    const service = new UserListService();

    await expect(service.getUsers({ page: 0 })).rejects.toThrow('page must be a positive integer.');
  });
});
