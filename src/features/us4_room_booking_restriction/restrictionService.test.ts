import { beforeEach, describe, expect, it } from 'vitest';
import { RestrictionService } from './restrictionService';
import { RoomRestrictionModal } from './RoomRestrictionModal';

describe('RestrictionService mock', () => {
  let service: RestrictionService;

  beforeEach(() => {
    service = new RestrictionService();
  });

  it('provides sample meeting rooms', async () => {
    const rooms = await service.getAvailableRooms();

    expect(rooms.map(room => room.name)).toContain('Phòng họp A1');
    expect(rooms.map(room => room.name)).toContain('Phòng họp B2');
    expect(rooms.map(room => room.name)).toContain('Phòng VIP 1');
  });

  it('loads, updates, and returns a user room restriction', async () => {
    const initial = await service.getUserRestrictions('mock-test-user');
    expect(initial.restrictedRoomIds).toEqual([]);

    await service.updateUserRestrictions('mock-test-user', {
      restrictedRoomIds: ['room-a1', 'room-a1', 'room-vip-1'],
      reason: 'Temporary restriction',
    });
    const updated = await service.getUserRestrictions('mock-test-user');

    expect(updated.restrictedRoomIds).toEqual(['room-a1', 'room-vip-1']);
    expect(updated.reason).toBe('Temporary restriction');
    expect(updated.userId).toBe('mock-test-user');
  });

  it('rejects missing user IDs and invalid room IDs', async () => {
    await expect(service.getUserRestrictions(' ')).rejects.toThrow('userId is required.');
    await expect(service.updateUserRestrictions('user-1', {
      restrictedRoomIds: [' '],
    })).rejects.toThrow('restrictedRoomIds must be an array of non-empty room IDs.');
  });
});

describe('RoomRestrictionModal', () => {
  it('renders the dialog, restriction controls, and modal actions', () => {
    const modal = new RoomRestrictionModal();
    const html = modal.renderHtml();

    expect(html).toContain('role="dialog"');
    expect(html).toContain('aria-modal="true"');
    expect(html).toContain('Chọn phòng bị cấm đặt');
    expect(html).toContain('data-reason');
    expect(html).toContain('Lưu cấu hình');
    expect(html).toContain('Hủy');
  });
});
