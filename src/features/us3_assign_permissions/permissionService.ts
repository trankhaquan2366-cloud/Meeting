import type {
  SystemRole,
  UpdateUserPermissionsDto,
  UserPermissions,
} from './types';

export interface PermissionServiceOptions {
  baseUrl?: string;
  useMock?: boolean;
  fetcher?: typeof fetch;
}

function getDefaultApiBaseUrl(): string {
  const configuredApiUrl = typeof window === 'undefined'
    ? undefined
    : (window as Window & { API_URL?: string }).API_URL;
  return `${(configuredApiUrl ?? '/api').replace(/\/+$/, '')}/v1`;
}
const MOCK_PERMISSIONS = new Map<string, UserPermissions>();

function requireUserId(userId: string): string {
  const normalized = userId.trim();
  if (!normalized) throw new TypeError('userId is required.');
  return normalized;
}

function normalizePermissions(value: unknown, userId: string): UserPermissions {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('Permissions API returned an invalid response.');
  }
  const record = value as Record<string, unknown>;
  const systemRole = record.systemRole ?? record.system_role ?? record.role;
  const role = typeof systemRole === 'string' ? systemRole.toUpperCase() : '';
  const normalizedRole: SystemRole = role === 'ADMIN' ? 'ADMIN'
    : role === 'NHAN_VIEN' || role === 'EMPLOYEE' ? 'NHAN_VIEN'
      : (() => { throw new Error(`Unsupported system role returned by API: ${String(systemRole)}.`); })();
  const canBook = record.canBook ?? record.can_book;
  const canAttend = record.canAttend ?? record.can_attend;

  if (typeof canBook !== 'boolean' || typeof canAttend !== 'boolean') {
    throw new Error('Permissions API response must include canBook and canAttend booleans.');
  }

  return { userId, systemRole: normalizedRole, canBook, canAttend };
}

export class PermissionService {
  private readonly baseUrl: string;
  private readonly useMock: boolean;
  private readonly fetcher: typeof fetch;

  constructor(options: PermissionServiceOptions = {}) {
    this.baseUrl = (options.baseUrl ?? getDefaultApiBaseUrl()).replace(/\/+$/, '');
    this.useMock = options.useMock ?? false;
    this.fetcher = options.fetcher ?? globalThis.fetch.bind(globalThis);
  }

  public async getUserPermissions(
    userId: string,
    fallbackRole: SystemRole = 'NHAN_VIEN',
  ): Promise<UserPermissions> {
    const normalizedUserId = requireUserId(userId);
    if (this.useMock) {
      const current = MOCK_PERMISSIONS.get(normalizedUserId);
      return current
        ? { ...current }
        : {
          userId: normalizedUserId,
          systemRole: fallbackRole,
          canBook: true,
          canAttend: true,
        };
    }

    const response = await this.fetcher(
      this.apiUrl(`/users/${encodeURIComponent(normalizedUserId)}/permissions`),
      { headers: this.headers() },
    );
    if (!response.ok) {
      throw new Error(`Unable to load user permissions (HTTP ${response.status}).`);
    }
    return normalizePermissions(await response.json(), normalizedUserId);
  }

  public async updateUserPermissions(
    userId: string,
    dto: UpdateUserPermissionsDto,
  ): Promise<UserPermissions> {
    const normalizedUserId = requireUserId(userId);
    if (!dto || !['ADMIN', 'NHAN_VIEN'].includes(dto.systemRole)) {
      throw new TypeError('systemRole must be ADMIN or NHAN_VIEN.');
    }
    if (typeof dto.canBook !== 'boolean' || typeof dto.canAttend !== 'boolean') {
      throw new TypeError('canBook and canAttend must be booleans.');
    }

    if (this.useMock) {
      const updated = { userId: normalizedUserId, ...dto };
      MOCK_PERMISSIONS.set(normalizedUserId, updated);
      return { ...updated };
    }

    const response = await this.fetcher(
      this.apiUrl(`/users/${encodeURIComponent(normalizedUserId)}/permissions`),
      {
        method: 'PUT',
        headers: { ...this.headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify(dto),
      },
    );
    if (!response.ok) {
      throw new Error(`Unable to update user permissions (HTTP ${response.status}).`);
    }
    return normalizePermissions(await response.json(), normalizedUserId);
  }

  private apiUrl(path: string): string {
    return new URL(
      `${this.baseUrl}${path}`,
      typeof window === 'undefined' ? 'http://localhost' : window.location.origin,
    ).toString();
  }

  private headers(): HeadersInit {
    const token = typeof localStorage === 'undefined' ? '' : localStorage.getItem('token') ?? '';
    return {
      Accept: 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  }
}

const defaultPermissionService = new PermissionService();

export function getUserPermissions(
  userId: string,
  fallbackRole?: SystemRole,
): Promise<UserPermissions> {
  return defaultPermissionService.getUserPermissions(userId, fallbackRole);
}

export function updateUserPermissions(
  userId: string,
  dto: UpdateUserPermissionsDto,
): Promise<UserPermissions> {
  return defaultPermissionService.updateUserPermissions(userId, dto);
}
