import type {
  GetUsersQuery,
  GetUsersResult,
  UserListItem,
  UserListRole,
  UserListStatus,
} from './types';

export interface UserListServiceOptions {
  baseUrl?: string;
  useMock?: boolean;
  fetcher?: typeof fetch;
}

const DEFAULT_API_URL = '/api/v1/users/';

const MOCK_USERS: UserListItem[] = [
  { id: 'USR-001', fullName: 'Nguyễn Minh Tuấn', email: 'tuan.nguyen@example.com', role: 'ADMIN', status: 'ACTIVE', createdAt: '2025-01-08T09:15:00.000Z' },
  { id: 'USR-002', fullName: 'Trần Thu Hà', email: 'ha.tran@example.com', role: 'BOOKER', status: 'ACTIVE', createdAt: '2025-01-12T03:30:00.000Z' },
  { id: 'USR-003', fullName: 'Lê Hoàng Nam', email: 'nam.le@example.com', role: 'ATTENDEE', status: 'ACTIVE', createdAt: '2025-01-18T07:00:00.000Z' },
  { id: 'USR-004', fullName: 'Phạm Ngọc Anh', email: 'anh.pham@example.com', role: 'BOOKER', status: 'INACTIVE', createdAt: '2025-01-24T10:20:00.000Z' },
  { id: 'USR-005', fullName: 'Đỗ Quang Huy', email: 'huy.do@example.com', role: 'ATTENDEE', status: 'ACTIVE', createdAt: '2025-02-02T01:45:00.000Z' },
  { id: 'USR-006', fullName: 'Vũ Thị Mai', email: 'mai.vu@example.com', role: 'ADMIN', status: 'ACTIVE', createdAt: '2025-02-07T08:10:00.000Z' },
  { id: 'USR-007', fullName: 'Bùi Đức Long', email: 'long.bui@example.com', role: 'BOOKER', status: 'ACTIVE', createdAt: '2025-02-14T04:35:00.000Z' },
  { id: 'USR-008', fullName: 'Hoàng Yến Nhi', email: 'nhi.hoang@example.com', role: 'ATTENDEE', status: 'INACTIVE', createdAt: '2025-02-20T06:25:00.000Z' },
  { id: 'USR-009', fullName: 'Dương Gia Bảo', email: 'bao.duong@example.com', role: 'BOOKER', status: 'ACTIVE', createdAt: '2025-03-01T02:55:00.000Z' },
  { id: 'USR-010', fullName: 'Đặng Thanh Tâm', email: 'tam.dang@example.com', role: 'ATTENDEE', status: 'ACTIVE', createdAt: '2025-03-05T09:40:00.000Z' },
  { id: 'USR-011', fullName: 'Ngô Khánh Linh', email: 'linh.ngo@example.com', role: 'BOOKER', status: 'ACTIVE', createdAt: '2025-03-11T05:05:00.000Z' },
  { id: 'USR-012', fullName: 'Mai Quốc Việt', email: 'viet.mai@example.com', role: 'ATTENDEE', status: 'ACTIVE', createdAt: '2025-03-15T11:15:00.000Z' },
  { id: 'USR-013', fullName: 'Phan Bảo Châu', email: 'chau.phan@example.com', role: 'BOOKER', status: 'INACTIVE', createdAt: '2025-03-21T02:20:00.000Z' },
  { id: 'USR-014', fullName: 'Lý Minh Khang', email: 'khang.ly@example.com', role: 'ATTENDEE', status: 'ACTIVE', createdAt: '2025-04-02T06:50:00.000Z' },
  { id: 'USR-015', fullName: 'Cao Nhật Vy', email: 'vy.cao@example.com', role: 'ADMIN', status: 'ACTIVE', createdAt: '2025-04-09T03:05:00.000Z' },
  { id: 'USR-016', fullName: 'Tạ Quốc Bảo', email: 'bao.ta@example.com', role: 'BOOKER', status: 'ACTIVE', createdAt: '2025-04-16T07:35:00.000Z' },
  { id: 'USR-017', fullName: 'Đinh Phương Thảo', email: 'thao.dinh@example.com', role: 'ATTENDEE', status: 'ACTIVE', createdAt: '2025-04-22T10:00:00.000Z' },
  { id: 'USR-018', fullName: 'Hồ Anh Dũng', email: 'dung.ho@example.com', role: 'BOOKER', status: 'ACTIVE', createdAt: '2025-05-03T01:30:00.000Z' },
  { id: 'USR-019', fullName: 'Trịnh Mỹ Duyên', email: 'duyen.trinh@example.com', role: 'ATTENDEE', status: 'INACTIVE', createdAt: '2025-05-12T08:45:00.000Z' },
  { id: 'USR-020', fullName: 'Đào Thành Công', email: 'cong.dao@example.com', role: 'BOOKER', status: 'ACTIVE', createdAt: '2025-05-19T04:15:00.000Z' },
  { id: 'USR-021', fullName: 'Nguyễn Hải Yến', email: 'yen.nguyen@example.com', role: 'ATTENDEE', status: 'ACTIVE', createdAt: '2025-05-28T09:55:00.000Z' },
  { id: 'USR-022', fullName: 'Lâm Quốc Khánh', email: 'khanh.lam@example.com', role: 'BOOKER', status: 'ACTIVE', createdAt: '2025-06-04T03:40:00.000Z' },
  { id: 'USR-023', fullName: 'Chu Thị Hương', email: 'huong.chu@example.com', role: 'ATTENDEE', status: 'ACTIVE', createdAt: '2025-06-14T06:05:00.000Z' },
  { id: 'USR-024', fullName: 'Võ Thành Đạt', email: 'dat.vo@example.com', role: 'BOOKER', status: 'INACTIVE', createdAt: '2025-06-23T11:25:00.000Z' },
];
const MOCK_USER_ROLE_OVERRIDES = new Map<string, UserListRole>();

function positiveInteger(value: number | undefined, fallback: number, name: string): number {
  const result = value ?? fallback;
  if (!Number.isSafeInteger(result) || result < 1) {
    throw new RangeError(`${name} must be a positive integer.`);
  }
  return result;
}

function normalizeRole(value: unknown): UserListRole {
  if (typeof value !== 'string') {
    throw new Error('User list API returned a user without a valid role.');
  }
  const role = value.trim();
  if (!role) throw new Error('User list API returned a user without a valid role.');
  return role.toUpperCase();
}

function normalizeStatus(value: unknown): UserListStatus {
  if (typeof value !== 'string') {
    throw new Error('User list API returned a user without a valid status.');
  }
  const status = value.toUpperCase();
  if (
    status === 'ACTIVE'
    || status === 'INACTIVE'
    || status === 'PENDING'
    || status === 'LOCKED'
  ) {
    return status;
  }
  throw new Error(`User list API returned an unsupported status: ${value}.`);
}

function normalizeUser(value: unknown): UserListItem {
  if (!value || typeof value !== 'object') {
    throw new Error('User list API returned an invalid user record.');
  }

  const record = value as Record<string, unknown>;
  const id = record.id;
  const fullName = record.fullName ?? record.full_name ?? record.username;
  const email = record.email;
  const createdAt = record.createdAt ?? record.created_at;

  if (
    (typeof id !== 'string' && typeof id !== 'number')
    || typeof fullName !== 'string'
    || (email !== null && email !== undefined && typeof email !== 'string')
    || typeof createdAt !== 'string'
    || Number.isNaN(Date.parse(createdAt))
  ) {
    throw new Error('User list API returned a user with missing or invalid fields.');
  }

  return {
    id: String(id),
    fullName,
    email: typeof email === 'string' ? email : '',
    role: normalizeRole(record.role),
    status: normalizeStatus(record.status),
    createdAt,
  };
}

function normalizeResult(
  payload: unknown,
  page: number,
  limit: number,
  roleForApi?: string,
): GetUsersResult {
  const record = Array.isArray(payload) ? { items: payload } : payload;
  if (!record || typeof record !== 'object') {
    throw new Error('User list API returned an invalid response.');
  }

  const response = record as Record<string, unknown>;
  const rawItems = response.items ?? response.users;
  if (!Array.isArray(rawItems)) {
    throw new Error('User list API response must contain an items array.');
  }

  const items = rawItems.map(normalizeUser);
  if (Array.isArray(payload)) {
    const filtered = items.filter(
      user => !roleForApi || user.role === roleForApi.toUpperCase(),
    );
    const start = (page - 1) * limit;
    return {
      items: filtered.slice(start, start + limit),
      total: filtered.length,
      page,
      limit,
    };
  }
  const total = response.total ?? items.length;
  if (typeof total !== 'number' || !Number.isSafeInteger(total) || total < 0) {
    throw new Error('User list API returned an invalid total count.');
  }

  return {
    items,
    total,
    page: typeof response.page === 'number' ? response.page : page,
    limit: typeof response.limit === 'number' ? response.limit : limit,
  };
}

export class UserListService {
  private readonly baseUrl: string;
  private readonly useMock: boolean;
  private readonly fetcher: typeof fetch;

  constructor(options: UserListServiceOptions = {}) {
    this.baseUrl = options.baseUrl ?? DEFAULT_API_URL;
    this.useMock = options.useMock ?? false;
    this.fetcher = options.fetcher ?? globalThis.fetch.bind(globalThis);
  }

  public async getUsers(query: GetUsersQuery = {}): Promise<GetUsersResult> {
    const page = positiveInteger(query.page, 1, 'page');
    const limit = positiveInteger(query.limit, 10, 'limit');

    if (query.role && !(['ADMIN', 'EMPLOYEE', 'BOOKER', 'ATTENDEE', 'MANAGER'] as UserListRole[]).includes(query.role)) {
      throw new RangeError(`Unsupported role filter: ${query.role}.`);
    }

    const normalizedQuery: GetUsersQuery = {
      ...query,
      page,
      limit,
      search: query.search?.trim() || undefined,
    };

    if (this.useMock) return this.getMockUsers({ ...normalizedQuery, page, limit });

    const url = new URL(
      this.baseUrl,
      typeof window === 'undefined' ? 'http://localhost' : window.location.origin,
    );
    url.searchParams.set('page', String(page));
    url.searchParams.set('limit', String(limit));
    if (normalizedQuery.search) url.searchParams.set('search', normalizedQuery.search);
    const roleForApi = normalizedQuery.role === 'BOOKER' || normalizedQuery.role === 'ATTENDEE'
      ? 'employee'
      : normalizedQuery.role?.toLowerCase();
    if (roleForApi) url.searchParams.set('role', roleForApi);

    const token = typeof localStorage === 'undefined' ? '' : localStorage.getItem('token') ?? '';

    const response = await this.fetcher(url.toString(), {
      headers: {
        Accept: 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!response.ok) {
      throw new Error(`Unable to load users (HTTP ${response.status}).`);
    }

    return normalizeResult(await response.json(), page, limit, roleForApi);
  }

  public updateMockUserRole(userId: string, role: UserListRole): void {
    if (this.useMock) MOCK_USER_ROLE_OVERRIDES.set(userId, role);
  }

  private getMockUsers(query: GetUsersQuery & { page: number; limit: number }): GetUsersResult {
    const search = query.search?.toLocaleLowerCase();
    const filtered = MOCK_USERS.map(user => ({
      ...user,
      role: MOCK_USER_ROLE_OVERRIDES.get(user.id) ?? user.role,
    })).filter(user => {
      const matchesSearch = !search
        || user.fullName.toLocaleLowerCase().includes(search)
        || user.email.toLocaleLowerCase().includes(search);
      const matchesRole = !query.role || user.role === query.role;
      return matchesSearch && matchesRole;
    });
    const start = (query.page - 1) * query.limit;

    return {
      items: filtered.slice(start, start + query.limit).map(user => ({ ...user })),
      total: filtered.length,
      page: query.page,
      limit: query.limit,
    };
  }
}

const defaultService = new UserListService();

export function getUsers(query: GetUsersQuery = {}): Promise<GetUsersResult> {
  return defaultService.getUsers(query);
}

export type { GetUsersQuery, GetUsersResult, UserListItem, UserListRole, UserListStatus };
