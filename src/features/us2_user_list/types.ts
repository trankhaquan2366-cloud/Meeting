export type UserListRole = 'ADMIN' | 'EMPLOYEE' | 'BOOKER' | 'ATTENDEE' | 'MANAGER' | (string & {});
export type UserListStatus = 'ACTIVE' | 'PENDING' | 'INACTIVE' | 'LOCKED';

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
