import type {
  RoomOption,
  UpdateUserRestrictionDto,
  UserRoomRestrictionDetail,
} from './types';

export interface RestrictionServiceOptions {
  baseUrl?: string;
  useMock?: boolean;
  fetcher?: typeof fetch;
}

function getDefaultApiBaseUrl(): string {
  if (typeof window === 'undefined') return '/api';
  const configuredApiUrl = (window as Window & { API_URL?: string }).API_URL;
  return configuredApiUrl ?? '/api';
}

const MOCK_ROOMS: RoomOption[] = [
  { id: 'room-a1', name: 'Phòng họp A1', location: 'Tầng 1' },
  { id: 'room-b2', name: 'Phòng họp B2', location: 'Tầng 2' },
  { id: 'room-vip-1', name: 'Phòng VIP 1', location: 'Tầng 5' },
  { id: 'room-c3', name: 'Phòng họp C3', location: 'Tầng 3' },
];

const MOCK_RESTRICTIONS = new Map<string, UserRoomRestrictionDetail>([
  ['user-002', {
    userId: 'user-002',
    restrictedRoomIds: ['room-vip-1'],
    reason: 'Chỉ dành cho cuộc họp có khách hàng.',
    updatedAt: '2025-06-01T09:00:00.000Z',
  }],
]);

function requireUserId(userId: string): string {
  const normalized = userId.trim();
  if (!normalized) throw new TypeError('userId is required.');
  return normalized;
}

function asRecord(value: unknown, message: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(message);
  }
  return value as Record<string, unknown>;
}

function normalizeRoom(value: unknown): RoomOption {
  const record = asRecord(value, 'Rooms API returned an invalid room.');
  const id = record.id;
  const name = record.name ?? record.room_name;
  const location = record.location ?? record.building;

  if ((typeof id !== 'string' && typeof id !== 'number') || typeof name !== 'string') {
    throw new Error('Rooms API returned a room with missing id or name.');
  }

  return {
    id: String(id),
    name,
    ...(typeof location === 'string' ? { location } : {}),
  };
}

function normalizeRestriction(
  value: unknown,
  userId: string,
): UserRoomRestrictionDetail {
  const record = asRecord(value, 'Restrictions API returned an invalid response.');
  const rawRoomIds = record.restrictedRoomIds
    ?? record.restricted_room_ids
    ?? record.blocked_room_ids
    ?? [];
  const reason = record.reason ?? '';
  const updatedAt = record.updatedAt ?? record.updated_at;

  if (!Array.isArray(rawRoomIds) || !rawRoomIds.every(
    roomId => typeof roomId === 'string' || typeof roomId === 'number',
  )) {
    throw new Error('Restrictions API returned an invalid list of restricted rooms.');
  }
  if (typeof reason !== 'string') {
    throw new Error('Restrictions API returned an invalid reason.');
  }

  return {
    userId: typeof record.userId === 'string'
      ? record.userId
      : typeof record.user_id === 'string' ? record.user_id : userId,
    restrictedRoomIds: rawRoomIds.map(String),
    reason,
    ...(typeof updatedAt === 'string' ? { updatedAt } : {}),
  };
}

export class RestrictionService {
  private readonly baseUrl: string;
  private readonly useMock: boolean;
  private readonly fetcher: typeof fetch;

  constructor(options: RestrictionServiceOptions = {}) {
    this.baseUrl = (options.baseUrl ?? getDefaultApiBaseUrl()).replace(/\/+$/, '');
    this.useMock = options.useMock ?? true;
    this.fetcher = options.fetcher ?? globalThis.fetch.bind(globalThis);
  }

  public async getAvailableRooms(): Promise<RoomOption[]> {
    if (this.useMock) return MOCK_ROOMS.map(room => ({ ...room }));

    const response = await this.fetcher(`${this.baseUrl}/rooms/`, {
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Unable to load meeting rooms (HTTP ${response.status}).`);
    }

    const payload: unknown = await response.json();
    const rooms = Array.isArray(payload)
      ? payload
      : asRecord(payload, 'Rooms API returned an invalid response.').items;
    if (!Array.isArray(rooms)) {
      throw new Error('Rooms API response must contain a room list.');
    }
    return rooms.map(normalizeRoom);
  }

  public async getUserRestrictions(userId: string): Promise<UserRoomRestrictionDetail> {
    const normalizedUserId = requireUserId(userId);
    if (this.useMock) {
      const existing = MOCK_RESTRICTIONS.get(normalizedUserId);
      return existing
        ? { ...existing, restrictedRoomIds: [...existing.restrictedRoomIds] }
        : { userId: normalizedUserId, restrictedRoomIds: [], reason: '' };
    }

    const response = await this.fetcher(
      `${this.baseUrl}/users/${encodeURIComponent(normalizedUserId)}/room-restrictions`,
      { headers: { Accept: 'application/json' } },
    );
    if (!response.ok) {
      throw new Error(`Unable to load user room restrictions (HTTP ${response.status}).`);
    }
    return normalizeRestriction(await response.json(), normalizedUserId);
  }

  public async updateUserRestrictions(
    userId: string,
    dto: UpdateUserRestrictionDto,
  ): Promise<UserRoomRestrictionDetail> {
    const normalizedUserId = requireUserId(userId);
    const normalizedDto = this.validateDto(dto);

    if (this.useMock) {
      const detail: UserRoomRestrictionDetail = {
        userId: normalizedUserId,
        restrictedRoomIds: [...normalizedDto.restrictedRoomIds],
        reason: normalizedDto.reason ?? '',
        updatedAt: new Date().toISOString(),
      };
      MOCK_RESTRICTIONS.set(normalizedUserId, detail);
      return { ...detail, restrictedRoomIds: [...detail.restrictedRoomIds] };
    }

    const response = await this.fetcher(
      `${this.baseUrl}/users/${encodeURIComponent(normalizedUserId)}/room-restrictions`,
      {
        method: 'PUT',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(normalizedDto),
      },
    );
    if (!response.ok) {
      throw new Error(`Unable to update user room restrictions (HTTP ${response.status}).`);
    }
    return normalizeRestriction(await response.json(), normalizedUserId);
  }

  private validateDto(dto: UpdateUserRestrictionDto): UpdateUserRestrictionDto {
    if (!dto || !Array.isArray(dto.restrictedRoomIds)
      || !dto.restrictedRoomIds.every(
        roomId => typeof roomId === 'string' && roomId.trim().length > 0,
      )) {
      throw new TypeError('restrictedRoomIds must be an array of non-empty room IDs.');
    }
    if (dto.reason !== undefined && typeof dto.reason !== 'string') {
      throw new TypeError('reason must be a string when provided.');
    }
    return {
      restrictedRoomIds: [...new Set(dto.restrictedRoomIds.map(roomId => roomId.trim()))],
      ...(dto.reason !== undefined ? { reason: dto.reason.trim() } : {}),
    };
  }
}

const defaultRestrictionService = new RestrictionService();

export function getAvailableRooms(): Promise<RoomOption[]> {
  return defaultRestrictionService.getAvailableRooms();
}

export function getUserRestrictions(userId: string): Promise<UserRoomRestrictionDetail> {
  return defaultRestrictionService.getUserRestrictions(userId);
}

export function updateUserRestrictions(
  userId: string,
  dto: UpdateUserRestrictionDto,
): Promise<UserRoomRestrictionDetail> {
  return defaultRestrictionService.updateUserRestrictions(userId, dto);
}

export type { RoomOption, UpdateUserRestrictionDto, UserRoomRestrictionDetail };
