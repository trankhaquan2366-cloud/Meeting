import { UserListTable } from './UserListTable';

let userListTable: UserListTable | null = null;

export function mountUserListTable(
  containerId: string,
  onCreateUser: () => void,
): Promise<void> {
  const container = document.getElementById(containerId);
  if (!container) {
    throw new Error(`User list container "#${containerId}" was not found.`);
  }

  userListTable ??= new UserListTable({
    containerId,
    createUserHref: '#adminCreateUserForm',
    onCreateUser,
  });
  return userListTable.mount(container);
}

export function refreshUserListTable(): Promise<void> {
  if (!userListTable) {
    throw new Error('The user list has not been mounted yet.');
  }
  return userListTable.refreshAfterCreate();
}
