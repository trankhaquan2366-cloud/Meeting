export interface RoomOption {
  id: string;
  name: string;
  location?: string;
}

export interface UserRoomRestrictionDetail {
  userId: string;
  restrictedRoomIds: string[];
  reason: string;
  updatedAt?: string;
}

export interface UpdateUserRestrictionDto {
  restrictedRoomIds: string[];
  reason?: string;
}

export interface RestrictionUser {
  id: string;
  fullName: string;
  email: string;
}
