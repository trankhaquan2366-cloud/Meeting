export type UserListRole = 'ADMIN' | 'BOOKER' | 'ATTENDEE';
export type UserListStatus = 'ACTIVE' | 'INACTIVE';

export interface UserListItem {
  id: string;
  fullName: string;
  email: string;
  role: UserListRole;
  status: UserListStatus;
  createdAt: string;
}

export interface GetUsersQuery {
  page?: number;
  limit?: number;
  search?: string;
  role?: UserListRole;
}

export interface GetUsersResult {
  items: UserListItem[];
  total: number;
  page: number;
  limit: number;
}
