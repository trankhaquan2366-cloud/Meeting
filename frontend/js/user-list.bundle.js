var RoomSyncUserList = (() => {
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
  var __export = (target, all) => {
    for (var name in all)
      __defProp(target, name, { get: all[name], enumerable: true });
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);
  var __publicField = (obj, key, value) => __defNormalProp(obj, typeof key !== "symbol" ? key + "" : key, value);

  // src/features/us2_user_list/dashboard.ts
  var dashboard_exports = {};
  __export(dashboard_exports, {
    mountUserListTable: () => mountUserListTable
  });

  // src/features/us2_user_list/userListService.ts
  var DEFAULT_API_URL = "http://localhost:8000/api/users/";
  var MOCK_USERS = [
    { id: "USR-001", fullName: "Nguy\u1EC5n Minh Tu\u1EA5n", email: "tuan.nguyen@example.com", role: "ADMIN", status: "ACTIVE", createdAt: "2025-01-08T09:15:00.000Z" },
    { id: "USR-002", fullName: "Tr\u1EA7n Thu H\xE0", email: "ha.tran@example.com", role: "BOOKER", status: "ACTIVE", createdAt: "2025-01-12T03:30:00.000Z" },
    { id: "USR-003", fullName: "L\xEA Ho\xE0ng Nam", email: "nam.le@example.com", role: "ATTENDEE", status: "ACTIVE", createdAt: "2025-01-18T07:00:00.000Z" },
    { id: "USR-004", fullName: "Ph\u1EA1m Ng\u1ECDc Anh", email: "anh.pham@example.com", role: "BOOKER", status: "INACTIVE", createdAt: "2025-01-24T10:20:00.000Z" },
    { id: "USR-005", fullName: "\u0110\u1ED7 Quang Huy", email: "huy.do@example.com", role: "ATTENDEE", status: "ACTIVE", createdAt: "2025-02-02T01:45:00.000Z" },
    { id: "USR-006", fullName: "V\u0169 Th\u1ECB Mai", email: "mai.vu@example.com", role: "ADMIN", status: "ACTIVE", createdAt: "2025-02-07T08:10:00.000Z" },
    { id: "USR-007", fullName: "B\xF9i \u0110\u1EE9c Long", email: "long.bui@example.com", role: "BOOKER", status: "ACTIVE", createdAt: "2025-02-14T04:35:00.000Z" },
    { id: "USR-008", fullName: "Ho\xE0ng Y\u1EBFn Nhi", email: "nhi.hoang@example.com", role: "ATTENDEE", status: "INACTIVE", createdAt: "2025-02-20T06:25:00.000Z" },
    { id: "USR-009", fullName: "D\u01B0\u01A1ng Gia B\u1EA3o", email: "bao.duong@example.com", role: "BOOKER", status: "ACTIVE", createdAt: "2025-03-01T02:55:00.000Z" },
    { id: "USR-010", fullName: "\u0110\u1EB7ng Thanh T\xE2m", email: "tam.dang@example.com", role: "ATTENDEE", status: "ACTIVE", createdAt: "2025-03-05T09:40:00.000Z" },
    { id: "USR-011", fullName: "Ng\xF4 Kh\xE1nh Linh", email: "linh.ngo@example.com", role: "BOOKER", status: "ACTIVE", createdAt: "2025-03-11T05:05:00.000Z" },
    { id: "USR-012", fullName: "Mai Qu\u1ED1c Vi\u1EC7t", email: "viet.mai@example.com", role: "ATTENDEE", status: "ACTIVE", createdAt: "2025-03-15T11:15:00.000Z" },
    { id: "USR-013", fullName: "Phan B\u1EA3o Ch\xE2u", email: "chau.phan@example.com", role: "BOOKER", status: "INACTIVE", createdAt: "2025-03-21T02:20:00.000Z" },
    { id: "USR-014", fullName: "L\xFD Minh Khang", email: "khang.ly@example.com", role: "ATTENDEE", status: "ACTIVE", createdAt: "2025-04-02T06:50:00.000Z" },
    { id: "USR-015", fullName: "Cao Nh\u1EADt Vy", email: "vy.cao@example.com", role: "ADMIN", status: "ACTIVE", createdAt: "2025-04-09T03:05:00.000Z" },
    { id: "USR-016", fullName: "T\u1EA1 Qu\u1ED1c B\u1EA3o", email: "bao.ta@example.com", role: "BOOKER", status: "ACTIVE", createdAt: "2025-04-16T07:35:00.000Z" },
    { id: "USR-017", fullName: "\u0110inh Ph\u01B0\u01A1ng Th\u1EA3o", email: "thao.dinh@example.com", role: "ATTENDEE", status: "ACTIVE", createdAt: "2025-04-22T10:00:00.000Z" },
    { id: "USR-018", fullName: "H\u1ED3 Anh D\u0169ng", email: "dung.ho@example.com", role: "BOOKER", status: "ACTIVE", createdAt: "2025-05-03T01:30:00.000Z" },
    { id: "USR-019", fullName: "Tr\u1ECBnh M\u1EF9 Duy\xEAn", email: "duyen.trinh@example.com", role: "ATTENDEE", status: "INACTIVE", createdAt: "2025-05-12T08:45:00.000Z" },
    { id: "USR-020", fullName: "\u0110\xE0o Th\xE0nh C\xF4ng", email: "cong.dao@example.com", role: "BOOKER", status: "ACTIVE", createdAt: "2025-05-19T04:15:00.000Z" },
    { id: "USR-021", fullName: "Nguy\u1EC5n H\u1EA3i Y\u1EBFn", email: "yen.nguyen@example.com", role: "ATTENDEE", status: "ACTIVE", createdAt: "2025-05-28T09:55:00.000Z" },
    { id: "USR-022", fullName: "L\xE2m Qu\u1ED1c Kh\xE1nh", email: "khanh.lam@example.com", role: "BOOKER", status: "ACTIVE", createdAt: "2025-06-04T03:40:00.000Z" },
    { id: "USR-023", fullName: "Chu Th\u1ECB H\u01B0\u01A1ng", email: "huong.chu@example.com", role: "ATTENDEE", status: "ACTIVE", createdAt: "2025-06-14T06:05:00.000Z" },
    { id: "USR-024", fullName: "V\xF5 Th\xE0nh \u0110\u1EA1t", email: "dat.vo@example.com", role: "BOOKER", status: "INACTIVE", createdAt: "2025-06-23T11:25:00.000Z" }
  ];
  var MOCK_USER_ROLE_OVERRIDES = /* @__PURE__ */ new Map();
  function positiveInteger(value, fallback, name) {
    const result = value ?? fallback;
    if (!Number.isSafeInteger(result) || result < 1) {
      throw new RangeError(`${name} must be a positive integer.`);
    }
    return result;
  }
  function normalizeRole(value) {
    if (typeof value !== "string") {
      throw new Error("User list API returned a user without a valid role.");
    }
    const role = value.toUpperCase();
    if (role === "ADMIN" || role === "BOOKER" || role === "ATTENDEE") return role;
    throw new Error(`User list API returned an unsupported role: ${value}.`);
  }
  function normalizeStatus(value) {
    if (typeof value !== "string") {
      throw new Error("User list API returned a user without a valid status.");
    }
    const status = value.toUpperCase();
    if (status === "ACTIVE" || status === "INACTIVE") return status;
    throw new Error(`User list API returned an unsupported status: ${value}.`);
  }
  function normalizeUser(value) {
    if (!value || typeof value !== "object") {
      throw new Error("User list API returned an invalid user record.");
    }
    const record = value;
    const id = record.id;
    const fullName = record.fullName ?? record.full_name;
    const email = record.email;
    const createdAt = record.createdAt ?? record.created_at;
    if (typeof id !== "string" && typeof id !== "number" || typeof fullName !== "string" || typeof email !== "string" || typeof createdAt !== "string" || Number.isNaN(Date.parse(createdAt))) {
      throw new Error("User list API returned a user with missing or invalid fields.");
    }
    return {
      id: String(id),
      fullName,
      email,
      role: normalizeRole(record.role),
      status: normalizeStatus(record.status),
      createdAt
    };
  }
  function normalizeResult(payload, page, limit) {
    const record = Array.isArray(payload) ? { items: payload } : payload;
    if (!record || typeof record !== "object") {
      throw new Error("User list API returned an invalid response.");
    }
    const response = record;
    const rawItems = response.items ?? response.users;
    if (!Array.isArray(rawItems)) {
      throw new Error("User list API response must contain an items array.");
    }
    const items = rawItems.map(normalizeUser);
    const total = response.total ?? items.length;
    if (typeof total !== "number" || !Number.isSafeInteger(total) || total < 0) {
      throw new Error("User list API returned an invalid total count.");
    }
    return {
      items,
      total,
      page: typeof response.page === "number" ? response.page : page,
      limit: typeof response.limit === "number" ? response.limit : limit
    };
  }
  var UserListService = class {
    constructor(options = {}) {
      __publicField(this, "baseUrl");
      __publicField(this, "useMock");
      __publicField(this, "fetcher");
      this.baseUrl = options.baseUrl ?? DEFAULT_API_URL;
      this.useMock = options.useMock ?? true;
      this.fetcher = options.fetcher ?? globalThis.fetch.bind(globalThis);
    }
    async getUsers(query = {}) {
      const page = positiveInteger(query.page, 1, "page");
      const limit = positiveInteger(query.limit, 10, "limit");
      if (query.role && !["ADMIN", "BOOKER", "ATTENDEE"].includes(query.role)) {
        throw new RangeError(`Unsupported role filter: ${query.role}.`);
      }
      const normalizedQuery = {
        ...query,
        page,
        limit,
        search: query.search?.trim() || void 0
      };
      if (this.useMock) return this.getMockUsers({ ...normalizedQuery, page, limit });
      const url = new URL(this.baseUrl);
      url.searchParams.set("page", String(page));
      url.searchParams.set("limit", String(limit));
      if (normalizedQuery.search) url.searchParams.set("search", normalizedQuery.search);
      if (normalizedQuery.role) url.searchParams.set("role", normalizedQuery.role);
      const response = await this.fetcher(url.toString(), {
        headers: { Accept: "application/json" }
      });
      if (!response.ok) {
        throw new Error(`Unable to load users (HTTP ${response.status}).`);
      }
      return normalizeResult(await response.json(), page, limit);
    }
    updateMockUserRole(userId, role) {
      if (this.useMock) MOCK_USER_ROLE_OVERRIDES.set(userId, role);
    }
    getMockUsers(query) {
      const search = query.search?.toLocaleLowerCase();
      const filtered = MOCK_USERS.map((user) => ({
        ...user,
        role: MOCK_USER_ROLE_OVERRIDES.get(user.id) ?? user.role
      })).filter((user) => {
        const matchesSearch = !search || user.fullName.toLocaleLowerCase().includes(search) || user.email.toLocaleLowerCase().includes(search);
        const matchesRole = !query.role || user.role === query.role;
        return matchesSearch && matchesRole;
      });
      const start = (query.page - 1) * query.limit;
      return {
        items: filtered.slice(start, start + query.limit).map((user) => ({ ...user })),
        total: filtered.length,
        page: query.page,
        limit: query.limit
      };
    }
  };
  var defaultService = new UserListService();

  // src/features/us3_assign_permissions/permissionService.ts
  var DEFAULT_API_BASE_URL = "http://localhost:8000/api";
  var MOCK_PERMISSIONS = /* @__PURE__ */ new Map();
  function requireUserId(userId) {
    const normalized = userId.trim();
    if (!normalized) throw new TypeError("userId is required.");
    return normalized;
  }
  function normalizePermissions(value, userId) {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      throw new Error("Permissions API returned an invalid response.");
    }
    const record = value;
    const systemRole = record.systemRole ?? record.system_role ?? record.role;
    const role = typeof systemRole === "string" ? systemRole.toUpperCase() : "";
    const normalizedRole = role === "ADMIN" ? "ADMIN" : role === "NHAN_VIEN" || role === "EMPLOYEE" ? "NHAN_VIEN" : (() => {
      throw new Error(`Unsupported system role returned by API: ${String(systemRole)}.`);
    })();
    const canBook = record.canBook ?? record.can_book;
    const canAttend = record.canAttend ?? record.can_attend;
    if (typeof canBook !== "boolean" || typeof canAttend !== "boolean") {
      throw new Error("Permissions API response must include canBook and canAttend booleans.");
    }
    return { userId, systemRole: normalizedRole, canBook, canAttend };
  }
  var PermissionService = class {
    constructor(options = {}) {
      __publicField(this, "baseUrl");
      __publicField(this, "useMock");
      __publicField(this, "fetcher");
      this.baseUrl = (options.baseUrl ?? DEFAULT_API_BASE_URL).replace(/\/+$/, "");
      this.useMock = options.useMock ?? true;
      this.fetcher = options.fetcher ?? globalThis.fetch.bind(globalThis);
    }
    async getUserPermissions(userId, fallbackRole = "NHAN_VIEN") {
      const normalizedUserId = requireUserId(userId);
      if (this.useMock) {
        const current = MOCK_PERMISSIONS.get(normalizedUserId);
        return current ? { ...current } : {
          userId: normalizedUserId,
          systemRole: fallbackRole,
          canBook: true,
          canAttend: true
        };
      }
      const response = await this.fetcher(
        `${this.baseUrl}/users/${encodeURIComponent(normalizedUserId)}/permissions`,
        { headers: { Accept: "application/json" } }
      );
      if (!response.ok) {
        throw new Error(`Unable to load user permissions (HTTP ${response.status}).`);
      }
      return normalizePermissions(await response.json(), normalizedUserId);
    }
    async updateUserPermissions(userId, dto) {
      const normalizedUserId = requireUserId(userId);
      if (!dto || !["ADMIN", "NHAN_VIEN"].includes(dto.systemRole)) {
        throw new TypeError("systemRole must be ADMIN or NHAN_VIEN.");
      }
      if (typeof dto.canBook !== "boolean" || typeof dto.canAttend !== "boolean") {
        throw new TypeError("canBook and canAttend must be booleans.");
      }
      if (this.useMock) {
        const updated = { userId: normalizedUserId, ...dto };
        MOCK_PERMISSIONS.set(normalizedUserId, updated);
        return { ...updated };
      }
      const response = await this.fetcher(
        `${this.baseUrl}/users/${encodeURIComponent(normalizedUserId)}/permissions`,
        {
          method: "PUT",
          headers: { Accept: "application/json", "Content-Type": "application/json" },
          body: JSON.stringify(dto)
        }
      );
      if (!response.ok) {
        throw new Error(`Unable to update user permissions (HTTP ${response.status}).`);
      }
      return normalizePermissions(await response.json(), normalizedUserId);
    }
  };
  var defaultPermissionService = new PermissionService();

  // src/features/us3_assign_permissions/AssignPermissionModal.ts
  var MODAL_STYLES = `
  .us3-modal-backdrop { position: fixed; inset: 0; z-index: 1100; display: grid; place-items: center; padding: 20px; background: rgb(15 23 42 / 55%); }
  .us3-modal-backdrop[hidden] { display: none; }
  .us3-modal { width: min(100%, 520px); border-radius: 16px; background: #fff; color: #172033; box-shadow: 0 24px 70px rgb(15 23 42 / 28%); font: 14px/1.5 system-ui, sans-serif; }
  .us3-modal * { box-sizing: border-box; }
  .us3-modal__header, .us3-modal__body, .us3-modal__footer { padding: 18px 22px; }
  .us3-modal__header { display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #e2e8f0; }
  .us3-modal__header h2 { margin: 0; font-size: 20px; }
  .us3-modal__user { display: grid; gap: 3px; margin-bottom: 18px; padding: 12px; border-radius: 9px; background: #f8fafc; }
  .us3-modal__user span { color: #64748b; overflow-wrap: anywhere; }
  .us3-modal__field { display: grid; gap: 7px; margin: 14px 0; }
  .us3-modal__field select { min-height: 40px; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 8px; background: #fff; color: inherit; font: inherit; }
  .us3-modal__permission { display: flex; align-items: flex-start; gap: 9px; padding: 9px 0; }
  .us3-modal__permission input { margin-top: 4px; accent-color: #2563eb; }
  .us3-modal__error { color: #b91c1c; }
  .us3-modal__footer { display: flex; justify-content: flex-end; gap: 9px; border-top: 1px solid #e2e8f0; }
  .us3-modal__button { min-height: 40px; padding: 8px 14px; border: 0; border-radius: 8px; font: inherit; font-weight: 600; cursor: pointer; }
  .us3-modal__button:disabled { opacity: .6; cursor: wait; }
  .us3-modal__button--cancel { background: #f1f5f9; color: #334155; }
  .us3-modal__button--save { background: #2563eb; color: #fff; }
`;
  function escapeHtml(value) {
    return value.replace(/[&<>"']/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    })[character] ?? character);
  }
  var AssignPermissionModal = class {
    constructor(options = {}) {
      __publicField(this, "service");
      __publicField(this, "options");
      __publicField(this, "host", null);
      __publicField(this, "user", null);
      __publicField(this, "systemRole", "NHAN_VIEN");
      __publicField(this, "canBook", true);
      __publicField(this, "canAttend", true);
      __publicField(this, "loading", false);
      __publicField(this, "loadFailed", false);
      __publicField(this, "saving", false);
      __publicField(this, "error", "");
      __publicField(this, "requestId", 0);
      __publicField(this, "onSubmit", (event) => {
        event.preventDefault();
        void this.save();
      });
      __publicField(this, "onChange", (event) => {
        const target = event.target;
        if (target instanceof HTMLSelectElement && target.matches("[data-system-role]")) {
          this.systemRole = target.value;
        } else if (target instanceof HTMLInputElement && target.matches("[data-can-book]")) {
          this.canBook = target.checked;
        } else if (target instanceof HTMLInputElement && target.matches("[data-can-attend]")) {
          this.canAttend = target.checked;
        }
      });
      __publicField(this, "onClick", (event) => {
        if (event.target instanceof Element && event.target.closest("[data-close]")) this.close();
      });
      __publicField(this, "onKeyDown", (event) => {
        if (event.key === "Escape" && this.isOpen()) this.close();
      });
      this.options = options;
      this.service = options.service ?? new PermissionService();
    }
    mount(target = document.body) {
      if (this.host) return;
      this.host = document.createElement("div");
      this.host.innerHTML = `<style>${MODAL_STYLES}</style>${this.renderHtml()}`;
      target.appendChild(this.host);
      this.host.addEventListener("submit", this.onSubmit);
      this.host.addEventListener("change", this.onChange);
      this.host.addEventListener("click", this.onClick);
      document.addEventListener("keydown", this.onKeyDown);
    }
    async open(user) {
      if (!user.id.trim()) throw new TypeError("A user ID is required to assign permissions.");
      if (!this.host) this.mount();
      const requestId = ++this.requestId;
      this.user = { ...user };
      this.systemRole = user.role?.toUpperCase() === "ADMIN" ? "ADMIN" : "NHAN_VIEN";
      this.canBook = true;
      this.canAttend = true;
      this.loading = true;
      this.loadFailed = false;
      this.saving = false;
      this.error = "";
      this.render(true);
      this.getDialog()?.focus();
      try {
        const current = await this.service.getUserPermissions(
          user.id,
          user.role?.toUpperCase() === "ADMIN" ? "ADMIN" : "NHAN_VIEN"
        );
        if (requestId !== this.requestId) return;
        this.systemRole = current.systemRole;
        this.canBook = current.canBook;
        this.canAttend = current.canAttend;
        this.loadFailed = false;
      } catch (error) {
        if (requestId !== this.requestId) return;
        this.loadFailed = true;
        this.error = error instanceof Error ? error.message : "Kh\xF4ng th\u1EC3 t\u1EA3i quy\u1EC1n ng\u01B0\u1EDDi d\xF9ng.";
      } finally {
        if (requestId === this.requestId) {
          this.loading = false;
          this.render(true);
          this.getDialog()?.focus();
        }
      }
    }
    close() {
      if (!this.isOpen()) return;
      this.requestId += 1;
      this.host?.querySelector("[data-backdrop]")?.setAttribute("hidden", "");
      this.options.onCancel?.();
    }
    renderHtml() {
      return `
      <div class="us3-modal-backdrop" data-backdrop hidden>
        <section class="us3-modal" role="dialog" aria-modal="true"
          aria-labelledby="us3-modal-title" tabindex="-1">
          <header class="us3-modal__header">
            <h2 id="us3-modal-title">S\u1EEDa quy\u1EC1n ng\u01B0\u1EDDi d\xF9ng</h2>
            <button class="us3-modal__button us3-modal__button--cancel" type="button" data-close aria-label="\u0110\xF3ng">\xD7</button>
          </header>
          <form data-permission-form>
            <div class="us3-modal__body">
              <div class="us3-modal__user">
                <strong>${escapeHtml(this.user?.fullName ?? "")}</strong>
                <span>${escapeHtml(this.user?.email ?? "")}</span>
              </div>
              <label class="us3-modal__field">Vai tr\xF2 h\u1EC7 th\u1ED1ng
                <select data-system-role ${this.loading || this.saving ? "disabled" : ""}>
                  <option value="ADMIN" ${this.systemRole === "ADMIN" ? "selected" : ""}>ADMIN</option>
                  <option value="NHAN_VIEN" ${this.systemRole === "NHAN_VIEN" ? "selected" : ""}>NHAN_VIEN</option>
                </select>
              </label>
              <p><strong>Quy\u1EC1n thao t\xE1c</strong></p>
              <label class="us3-modal__permission">
                <input type="checkbox" data-can-book ${this.canBook ? "checked" : ""}
                  ${this.loading || this.saving ? "disabled" : ""}>
                <span>Ng\u01B0\u1EDDi \u0111\u1EB7t l\u1ECBch</span>
              </label>
              <label class="us3-modal__permission">
                <input type="checkbox" data-can-attend ${this.canAttend ? "checked" : ""}
                  ${this.loading || this.saving ? "disabled" : ""}>
                <span>Ng\u01B0\u1EDDi tham d\u1EF1</span>
              </label>
              ${this.loading ? '<p role="status">\u0110ang t\u1EA3i quy\u1EC1n...</p>' : ""}
              ${this.error ? `<p class="us3-modal__error" role="alert">${escapeHtml(this.error)}</p>` : ""}
            </div>
            <footer class="us3-modal__footer">
              <button class="us3-modal__button us3-modal__button--cancel" type="button" data-close>H\u1EE7y</button>
              <button class="us3-modal__button us3-modal__button--save" type="submit"
                ${this.loading || this.saving || this.loadFailed ? "disabled" : ""}>${this.saving ? "\u0110ang l\u01B0u..." : "L\u01B0u quy\u1EC1n"}</button>
            </footer>
          </form>
        </section>
      </div>
    `;
    }
    async save() {
      if (!this.user || this.loading || this.saving) return;
      this.saving = true;
      this.error = "";
      this.render(true);
      let saved = false;
      try {
        const dto = {
          systemRole: this.systemRole,
          canBook: this.canBook,
          canAttend: this.canAttend
        };
        const updated = await this.service.updateUserPermissions(this.user.id, dto);
        const user = this.user;
        saved = true;
        this.host?.querySelector("[data-backdrop]")?.setAttribute("hidden", "");
        this.options.onSaved?.(user, updated);
      } catch (error) {
        this.error = error instanceof Error ? error.message : "Kh\xF4ng th\u1EC3 l\u01B0u quy\u1EC1n ng\u01B0\u1EDDi d\xF9ng.";
      } finally {
        this.saving = false;
        this.render(!saved);
      }
    }
    render(open) {
      if (!this.host) return;
      this.host.innerHTML = `<style>${MODAL_STYLES}</style>${this.renderHtml()}`;
      if (open) this.host.querySelector("[data-backdrop]")?.removeAttribute("hidden");
    }
    getDialog() {
      return this.host?.querySelector('[role="dialog"]') ?? null;
    }
    isOpen() {
      return Boolean(this.host?.querySelector("[data-backdrop]:not([hidden])"));
    }
  };

  // src/features/us4_room_booking_restriction/restrictionService.ts
  var DEFAULT_API_BASE_URL2 = "http://localhost:8000/api";
  var MOCK_ROOMS = [
    { id: "room-a1", name: "Ph\xF2ng h\u1ECDp A1", location: "T\u1EA7ng 1" },
    { id: "room-b2", name: "Ph\xF2ng h\u1ECDp B2", location: "T\u1EA7ng 2" },
    { id: "room-vip-1", name: "Ph\xF2ng VIP 1", location: "T\u1EA7ng 5" },
    { id: "room-c3", name: "Ph\xF2ng h\u1ECDp C3", location: "T\u1EA7ng 3" }
  ];
  var MOCK_RESTRICTIONS = /* @__PURE__ */ new Map([
    ["user-002", {
      userId: "user-002",
      restrictedRoomIds: ["room-vip-1"],
      reason: "Ch\u1EC9 d\xE0nh cho cu\u1ED9c h\u1ECDp c\xF3 kh\xE1ch h\xE0ng.",
      updatedAt: "2025-06-01T09:00:00.000Z"
    }]
  ]);
  function requireUserId2(userId) {
    const normalized = userId.trim();
    if (!normalized) throw new TypeError("userId is required.");
    return normalized;
  }
  function asRecord(value, message) {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      throw new Error(message);
    }
    return value;
  }
  function normalizeRoom(value) {
    const record = asRecord(value, "Rooms API returned an invalid room.");
    const id = record.id;
    const name = record.name ?? record.room_name;
    const location = record.location ?? record.building;
    if (typeof id !== "string" && typeof id !== "number" || typeof name !== "string") {
      throw new Error("Rooms API returned a room with missing id or name.");
    }
    return {
      id: String(id),
      name,
      ...typeof location === "string" ? { location } : {}
    };
  }
  function normalizeRestriction(value, userId) {
    const record = asRecord(value, "Restrictions API returned an invalid response.");
    const rawRoomIds = record.restrictedRoomIds ?? record.restricted_room_ids ?? record.blocked_room_ids ?? [];
    const reason = record.reason ?? "";
    const updatedAt = record.updatedAt ?? record.updated_at;
    if (!Array.isArray(rawRoomIds) || !rawRoomIds.every(
      (roomId) => typeof roomId === "string" || typeof roomId === "number"
    )) {
      throw new Error("Restrictions API returned an invalid list of restricted rooms.");
    }
    if (typeof reason !== "string") {
      throw new Error("Restrictions API returned an invalid reason.");
    }
    return {
      userId: typeof record.userId === "string" ? record.userId : typeof record.user_id === "string" ? record.user_id : userId,
      restrictedRoomIds: rawRoomIds.map(String),
      reason,
      ...typeof updatedAt === "string" ? { updatedAt } : {}
    };
  }
  var RestrictionService = class {
    constructor(options = {}) {
      __publicField(this, "baseUrl");
      __publicField(this, "useMock");
      __publicField(this, "fetcher");
      this.baseUrl = (options.baseUrl ?? DEFAULT_API_BASE_URL2).replace(/\/+$/, "");
      this.useMock = options.useMock ?? true;
      this.fetcher = options.fetcher ?? globalThis.fetch.bind(globalThis);
    }
    async getAvailableRooms() {
      if (this.useMock) return MOCK_ROOMS.map((room) => ({ ...room }));
      const response = await this.fetcher(`${this.baseUrl}/rooms/`, {
        headers: { Accept: "application/json" }
      });
      if (!response.ok) {
        throw new Error(`Unable to load meeting rooms (HTTP ${response.status}).`);
      }
      const payload = await response.json();
      const rooms = Array.isArray(payload) ? payload : asRecord(payload, "Rooms API returned an invalid response.").items;
      if (!Array.isArray(rooms)) {
        throw new Error("Rooms API response must contain a room list.");
      }
      return rooms.map(normalizeRoom);
    }
    async getUserRestrictions(userId) {
      const normalizedUserId = requireUserId2(userId);
      if (this.useMock) {
        const existing = MOCK_RESTRICTIONS.get(normalizedUserId);
        return existing ? { ...existing, restrictedRoomIds: [...existing.restrictedRoomIds] } : { userId: normalizedUserId, restrictedRoomIds: [], reason: "" };
      }
      const response = await this.fetcher(
        `${this.baseUrl}/users/${encodeURIComponent(normalizedUserId)}/room-restrictions`,
        { headers: { Accept: "application/json" } }
      );
      if (!response.ok) {
        throw new Error(`Unable to load user room restrictions (HTTP ${response.status}).`);
      }
      return normalizeRestriction(await response.json(), normalizedUserId);
    }
    async updateUserRestrictions(userId, dto) {
      const normalizedUserId = requireUserId2(userId);
      const normalizedDto = this.validateDto(dto);
      if (this.useMock) {
        const detail = {
          userId: normalizedUserId,
          restrictedRoomIds: [...normalizedDto.restrictedRoomIds],
          reason: normalizedDto.reason ?? "",
          updatedAt: (/* @__PURE__ */ new Date()).toISOString()
        };
        MOCK_RESTRICTIONS.set(normalizedUserId, detail);
        return { ...detail, restrictedRoomIds: [...detail.restrictedRoomIds] };
      }
      const response = await this.fetcher(
        `${this.baseUrl}/users/${encodeURIComponent(normalizedUserId)}/room-restrictions`,
        {
          method: "PUT",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json"
          },
          body: JSON.stringify(normalizedDto)
        }
      );
      if (!response.ok) {
        throw new Error(`Unable to update user room restrictions (HTTP ${response.status}).`);
      }
      return normalizeRestriction(await response.json(), normalizedUserId);
    }
    validateDto(dto) {
      if (!dto || !Array.isArray(dto.restrictedRoomIds) || !dto.restrictedRoomIds.every(
        (roomId) => typeof roomId === "string" && roomId.trim().length > 0
      )) {
        throw new TypeError("restrictedRoomIds must be an array of non-empty room IDs.");
      }
      if (dto.reason !== void 0 && typeof dto.reason !== "string") {
        throw new TypeError("reason must be a string when provided.");
      }
      return {
        restrictedRoomIds: [...new Set(dto.restrictedRoomIds.map((roomId) => roomId.trim()))],
        ...dto.reason !== void 0 ? { reason: dto.reason.trim() } : {}
      };
    }
  };
  var defaultRestrictionService = new RestrictionService();

  // src/features/us4_room_booking_restriction/RoomRestrictionModal.ts
  var MODAL_STYLES2 = `
  .us4-modal-backdrop {
    position: fixed; inset: 0; z-index: 1000; display: grid; place-items: center;
    overflow-y: auto; padding: 20px; background: rgb(15 23 42 / 55%);
  }
  .us4-modal-backdrop[hidden] { display: none; }
  .us4-modal {
    width: min(100%, 560px); max-height: min(90vh, 760px); overflow-y: auto;
    border-radius: 16px; background: #fff; color: #172033;
    box-shadow: 0 24px 70px rgb(15 23 42 / 28%);
    font: 14px/1.5 system-ui, sans-serif;
  }
  .us4-modal * { box-sizing: border-box; }
  .us4-modal__header, .us4-modal__footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  .us4-modal__header { padding: 20px 24px 12px; }
  .us4-modal__header h2 { margin: 0; font-size: 20px; }
  .us4-modal__body { padding: 8px 24px 20px; }
  .us4-modal__user { display: grid; gap: 4px; margin-bottom: 18px; padding: 12px 14px; border-radius: 9px; background: #f8fafc; }
  .us4-modal__user span { color: #475569; overflow-wrap: anywhere; }
  .us4-modal__section-title { margin: 0 0 8px; font-weight: 650; }
  .us4-modal__room-list { display: grid; gap: 8px; max-height: 250px; overflow-y: auto; }
  .us4-modal__room { display: flex; align-items: flex-start; gap: 10px; padding: 10px 12px; border: 1px solid #e2e8f0; border-radius: 9px; cursor: pointer; }
  .us4-modal__room input { margin-top: 3px; accent-color: #dc2626; }
  .us4-modal__room small { display: block; color: #64748b; }
  .us4-modal__reason { display: grid; gap: 6px; margin-top: 18px; }
  .us4-modal__reason textarea { width: 100%; resize: vertical; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px 12px; font: inherit; }
  .us4-modal__error { margin: 12px 0 0; color: #b91c1c; }
  .us4-modal__footer { justify-content: flex-end; padding: 14px 24px 20px; }
  .us4-modal__button { min-height: 40px; padding: 8px 14px; border: 0; border-radius: 8px; font: inherit; font-weight: 600; cursor: pointer; }
  .us4-modal__button:disabled { opacity: .6; cursor: wait; }
  .us4-modal__button--cancel { background: #f1f5f9; color: #334155; }
  .us4-modal__button--save { background: #2563eb; color: #fff; }
  .us4-modal__close { border: 0; background: transparent; color: #64748b; font-size: 24px; cursor: pointer; }
`;
  function escapeHtml2(value) {
    return value.replace(/[&<>"']/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    })[character] ?? character);
  }
  var RoomRestrictionModal = class {
    constructor(options = {}) {
      __publicField(this, "service");
      __publicField(this, "options");
      __publicField(this, "host", null);
      __publicField(this, "user", null);
      __publicField(this, "rooms", []);
      __publicField(this, "restrictedRoomIds", /* @__PURE__ */ new Set());
      __publicField(this, "reason", "");
      __publicField(this, "error", "");
      __publicField(this, "loading", false);
      __publicField(this, "restrictionsLoaded", false);
      __publicField(this, "saving", false);
      __publicField(this, "requestId", 0);
      __publicField(this, "onKeyDown", (event) => {
        if (event.key === "Escape" && this.isOpen()) this.close();
      });
      __publicField(this, "onSubmit", (event) => {
        event.preventDefault();
        void this.save();
      });
      __publicField(this, "onClick", (event) => {
        const target = event.target;
        if (!(target instanceof Element)) return;
        if (target.closest("[data-close-modal]")) this.close();
      });
      __publicField(this, "onChange", (event) => {
        const target = event.target;
        if (target instanceof HTMLInputElement && target.matches("[data-room-id]")) {
          if (target.checked) this.restrictedRoomIds.add(target.value);
          else this.restrictedRoomIds.delete(target.value);
        }
        if (target instanceof HTMLTextAreaElement && target.matches("[data-reason]")) {
          this.reason = target.value;
        }
      });
      this.options = options;
      this.service = options.service ?? new RestrictionService();
    }
    mount(target = document.body) {
      if (this.host) return;
      const host = document.createElement("div");
      host.innerHTML = `<style>${MODAL_STYLES2}</style>${this.renderHtml()}`;
      target.appendChild(host);
      this.host = host;
      host.addEventListener("click", this.onClick);
      host.addEventListener("submit", this.onSubmit);
      host.addEventListener("change", this.onChange);
      document.addEventListener("keydown", this.onKeyDown);
    }
    async open(user) {
      if (!user.id.trim()) throw new TypeError("A user ID is required to edit room restrictions.");
      if (typeof user.fullName !== "string" || typeof user.email !== "string") {
        throw new TypeError("The selected user must have a name and email address.");
      }
      if (!this.host) this.mount();
      const requestId = ++this.requestId;
      this.user = { ...user };
      this.rooms = [];
      this.restrictedRoomIds.clear();
      this.reason = "";
      this.error = "";
      this.loading = true;
      this.restrictionsLoaded = false;
      this.saving = false;
      this.render();
      this.host?.querySelector("[data-backdrop]")?.removeAttribute("hidden");
      this.getDialog()?.focus();
      try {
        const [rooms, restrictions] = await Promise.all([
          this.service.getAvailableRooms(),
          this.service.getUserRestrictions(user.id)
        ]);
        if (requestId !== this.requestId) return;
        this.rooms = rooms;
        this.restrictedRoomIds = new Set(restrictions.restrictedRoomIds);
        this.reason = restrictions.reason;
        this.restrictionsLoaded = true;
      } catch (error) {
        if (requestId !== this.requestId) return;
        this.restrictionsLoaded = false;
        this.error = error instanceof Error ? error.message : "Kh\xF4ng th\u1EC3 t\u1EA3i c\u1EA5u h\xECnh h\u1EA1n ch\u1EBF.";
      } finally {
        if (requestId === this.requestId) {
          this.loading = false;
          this.render();
          this.getDialog()?.focus();
        }
      }
    }
    close() {
      if (!this.isOpen()) return;
      this.requestId += 1;
      this.host?.querySelector("[data-backdrop]")?.setAttribute("hidden", "");
      this.options.onCancel?.();
    }
    renderHtml() {
      const roomList = this.loading ? '<p role="status">\u0110ang t\u1EA3i danh s\xE1ch ph\xF2ng...</p>' : this.rooms.length ? this.rooms.map((room) => this.renderRoom(room)).join("") : "<p>Kh\xF4ng c\xF3 ph\xF2ng h\u1ECDp \u0111\u1EC3 c\u1EA5u h\xECnh.</p>";
      return `
      <div class="us4-modal-backdrop" data-backdrop hidden>
        <section class="us4-modal" role="dialog" aria-modal="true"
          aria-labelledby="us4-modal-title" tabindex="-1">
          <header class="us4-modal__header">
            <h2 id="us4-modal-title">Gi\u1EDBi h\u1EA1n quy\u1EC1n \u0111\u1EB7t ph\xF2ng</h2>
            <button class="us4-modal__close" type="button" data-close-modal
              aria-label="\u0110\xF3ng c\u1EEDa s\u1ED5">\xD7</button>
          </header>
          <form data-restriction-form>
            <div class="us4-modal__body">
              <div class="us4-modal__user">
                <strong>${escapeHtml2(this.user?.fullName ?? "")}</strong>
                <span>${escapeHtml2(this.user?.email ?? "")}</span>
              </div>
              <p class="us4-modal__section-title">Ch\u1ECDn ph\xF2ng b\u1ECB c\u1EA5m \u0111\u1EB7t</p>
              <div class="us4-modal__room-list">${roomList}</div>
              <label class="us4-modal__reason">
                <span>L\xFD do h\u1EA1n ch\u1EBF (t\xF9y ch\u1ECDn)</span>
                <textarea data-reason rows="3" maxlength="1000"
                  placeholder="Nh\u1EADp l\xFD do...">${escapeHtml2(this.reason)}</textarea>
              </label>
              ${this.error ? `<p class="us4-modal__error" role="alert">${escapeHtml2(this.error)}</p>` : ""}
            </div>
            <footer class="us4-modal__footer">
              <button class="us4-modal__button us4-modal__button--cancel" type="button"
                data-close-modal>H\u1EE7y</button>
              <button class="us4-modal__button us4-modal__button--save" type="submit"
                ${this.loading || this.saving || !this.restrictionsLoaded ? "disabled" : ""}>
                ${this.saving ? "\u0110ang l\u01B0u..." : "L\u01B0u c\u1EA5u h\xECnh"}
              </button>
            </footer>
          </form>
        </section>
      </div>
    `;
    }
    renderRoom(room) {
      const checked = this.restrictedRoomIds.has(room.id) ? "checked" : "";
      const location = room.location ? `<small>${escapeHtml2(room.location)}</small>` : "";
      return `
      <label class="us4-modal__room">
        <input type="checkbox" data-room-id value="${escapeHtml2(room.id)}" ${checked}
          ${this.loading || this.saving ? "disabled" : ""}>
        <span><strong>${escapeHtml2(room.name)}</strong>${location}</span>
      </label>
    `;
    }
    async save() {
      if (!this.user || this.loading || this.saving || !this.restrictionsLoaded) return;
      this.saving = true;
      this.error = "";
      this.syncFormState();
      const dto = {
        restrictedRoomIds: [...this.restrictedRoomIds],
        reason: this.reason.trim()
      };
      try {
        await this.service.updateUserRestrictions(this.user.id, dto);
        this.host?.querySelector("[data-backdrop]")?.setAttribute("hidden", "");
        this.options.onSaved?.();
      } catch (error) {
        this.error = error instanceof Error ? error.message : "Kh\xF4ng th\u1EC3 l\u01B0u c\u1EA5u h\xECnh h\u1EA1n ch\u1EBF.";
        this.render();
      } finally {
        this.saving = false;
        this.syncFormState();
      }
    }
    syncFormState() {
      const submit = this.host?.querySelector('[type="submit"]');
      if (submit) {
        submit.disabled = this.loading || this.saving;
        submit.textContent = this.saving ? "\u0110ang l\u01B0u..." : "L\u01B0u c\u1EA5u h\xECnh";
      }
      this.host?.querySelectorAll("[data-room-id]").forEach((input) => {
        input.disabled = this.loading || this.saving;
      });
    }
    render() {
      if (!this.host) return;
      const wasOpen = this.isOpen();
      this.host.innerHTML = `<style>${MODAL_STYLES2}</style>${this.renderHtml()}`;
      if (wasOpen) {
        this.host.querySelector("[data-backdrop]")?.removeAttribute("hidden");
        this.getDialog()?.focus();
      }
    }
    getDialog() {
      return this.host?.querySelector('[role="dialog"]') ?? null;
    }
    isOpen() {
      return Boolean(this.host?.querySelector("[data-backdrop]:not([hidden])"));
    }
  };

  // src/features/us2_user_list/BulkUserEditModal.ts
  var BULK_STYLES = `
  .us2-bulk-backdrop { position: fixed; inset: 0; z-index: 1200; display: grid; place-items: center; padding: 20px; background: rgb(15 23 42 / 55%); }
  .us2-bulk-backdrop[hidden] { display: none; }
  .us2-bulk-modal { width: min(100%, 620px); max-height: 90vh; overflow-y: auto; border-radius: 16px; background: #fff; color: #172033; box-shadow: 0 24px 70px rgb(15 23 42 / 28%); font: 14px/1.5 system-ui, sans-serif; }
  .us2-bulk-modal * { box-sizing: border-box; }
  .us2-bulk-modal__header, .us2-bulk-modal__body, .us2-bulk-modal__footer { padding: 18px 22px; }
  .us2-bulk-modal__header { display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #e2e8f0; }
  .us2-bulk-modal__header h2 { margin: 0; font-size: 20px; }
  .us2-bulk-modal__summary { color: #475569; }
  .us2-bulk-modal__mode { display: flex; align-items: flex-start; gap: 10px; margin: 12px 0; padding: 12px; border: 1px solid #e2e8f0; border-radius: 9px; cursor: pointer; }
  .us2-bulk-modal__mode input { margin-top: 4px; accent-color: #2563eb; }
  .us2-bulk-modal__section { margin: 12px 0 16px 25px; }
  .us2-bulk-modal__section[hidden] { display: none; }
  .us2-bulk-modal__select { min-height: 40px; width: 100%; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 8px; background: #fff; font: inherit; }
  .us2-bulk-modal__rooms { display: grid; gap: 8px; max-height: 210px; overflow: auto; }
  .us2-bulk-modal__room { display: flex; align-items: center; gap: 9px; }
  .us2-bulk-modal__room input { accent-color: #dc2626; }
  .us2-bulk-modal__error { white-space: pre-line; color: #b91c1c; }
  .us2-bulk-modal__footer { display: flex; justify-content: flex-end; gap: 9px; border-top: 1px solid #e2e8f0; }
  .us2-bulk-modal__button { min-height: 40px; padding: 8px 14px; border: 0; border-radius: 8px; font: inherit; font-weight: 600; cursor: pointer; }
  .us2-bulk-modal__button:disabled { opacity: .6; cursor: wait; }
  .us2-bulk-modal__button--cancel { background: #f1f5f9; color: #334155; }
  .us2-bulk-modal__button--save { background: #2563eb; color: #fff; }
`;
  function escapeHtml3(value) {
    return value.replace(/[&<>"']/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    })[character] ?? character);
  }
  var BulkUserEditModal = class {
    constructor(options) {
      __publicField(this, "options");
      __publicField(this, "host", null);
      __publicField(this, "users", []);
      __publicField(this, "rooms", []);
      __publicField(this, "roomsLoaded", false);
      __publicField(this, "mode", "role");
      __publicField(this, "systemRole", "NHAN_VIEN");
      __publicField(this, "restrictedRoomIds", /* @__PURE__ */ new Set());
      __publicField(this, "loading", false);
      __publicField(this, "saving", false);
      __publicField(this, "error", "");
      __publicField(this, "requestId", 0);
      __publicField(this, "onClick", (event) => {
        if (event.target instanceof Element && event.target.closest("[data-close]")) this.close();
      });
      __publicField(this, "onChange", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLInputElement) && !(target instanceof HTMLSelectElement)) return;
        if (target.matches("[data-mode]") && target instanceof HTMLInputElement) {
          this.mode = target.value;
          this.render(true);
        } else if (target.matches("[data-system-role]") && target instanceof HTMLSelectElement) {
          this.systemRole = target.value;
        } else if (target.matches("[data-room-id]") && target instanceof HTMLInputElement) {
          if (target.checked) this.restrictedRoomIds.add(target.value);
          else this.restrictedRoomIds.delete(target.value);
        }
      });
      __publicField(this, "onSubmit", (event) => {
        event.preventDefault();
        void this.save();
      });
      __publicField(this, "onKeyDown", (event) => {
        if (event.key === "Escape" && this.isOpen() && !this.saving) this.close();
      });
      this.options = options;
    }
    mount(target = document.body) {
      if (this.host) return;
      this.host = document.createElement("div");
      this.host.innerHTML = `<style>${BULK_STYLES}</style>${this.renderHtml()}`;
      target.appendChild(this.host);
      this.host.addEventListener("click", this.onClick);
      this.host.addEventListener("change", this.onChange);
      this.host.addEventListener("submit", this.onSubmit);
      document.addEventListener("keydown", this.onKeyDown);
    }
    async open(users) {
      if (!users.length) throw new TypeError("Select at least one user for bulk editing.");
      if (!this.host) this.mount();
      const requestId = ++this.requestId;
      this.users = users.map((user) => ({ ...user }));
      this.mode = "role";
      this.systemRole = "NHAN_VIEN";
      this.restrictedRoomIds.clear();
      this.roomsLoaded = false;
      this.loading = true;
      this.saving = false;
      this.error = "";
      this.render(true);
      try {
        this.rooms = await this.options.restrictionService.getAvailableRooms();
        if (requestId !== this.requestId) return;
        this.roomsLoaded = true;
      } catch (error) {
        if (requestId !== this.requestId) return;
        this.error = error instanceof Error ? error.message : "Kh\xF4ng th\u1EC3 t\u1EA3i danh s\xE1ch ph\xF2ng.";
      } finally {
        if (requestId === this.requestId) {
          this.loading = false;
          this.render(true);
          this.getDialog()?.focus();
        }
      }
    }
    close() {
      if (!this.isOpen() || this.saving) return;
      this.requestId += 1;
      this.host?.querySelector("[data-backdrop]")?.setAttribute("hidden", "");
    }
    renderHtml() {
      const roomItems = this.rooms.map((room) => `
      <label class="us2-bulk-modal__room">
        <input type="checkbox" data-room-id value="${escapeHtml3(room.id)}"
          ${this.restrictedRoomIds.has(room.id) ? "checked" : ""}
          ${this.loading || this.saving ? "disabled" : ""}>
        <span>${escapeHtml3(room.name)}</span>
      </label>
    `).join("");
      return `
      <div class="us2-bulk-backdrop" data-backdrop hidden>
        <section class="us2-bulk-modal" role="dialog" aria-modal="true"
          aria-labelledby="us2-bulk-title" tabindex="-1">
          <header class="us2-bulk-modal__header">
            <h2 id="us2-bulk-title">Ch\u1EC9nh s\u1EEDa \u0111\u1ED3ng b\u1ED9</h2>
            <button class="us2-bulk-modal__button us2-bulk-modal__button--cancel"
              type="button" data-close aria-label="\u0110\xF3ng">\xD7</button>
          </header>
          <form data-bulk-form>
            <div class="us2-bulk-modal__body">
              <p class="us2-bulk-modal__summary">\xC1p d\u1EE5ng cho ${this.users.length} ng\u01B0\u1EDDi d\xF9ng \u0111\xE3 ch\u1ECDn.</p>
              <div class="us2-bulk-modal__mode">
                <input id="us2BulkModeRole" type="radio" name="bulkMode" data-mode value="role"
                  ${this.mode === "role" ? "checked" : ""} ${this.saving ? "disabled" : ""}>
                <div>
                  <label for="us2BulkModeRole"><strong>C\u1EADp nh\u1EADt vai tr\xF2 h\u1EC7 th\u1ED1ng</strong></label>
                  <div class="us2-bulk-modal__section" ${this.mode !== "role" ? "hidden" : ""}>
                    <select class="us2-bulk-modal__select" data-system-role
                      ${this.saving ? "disabled" : ""}>
                      <option value="NHAN_VIEN" ${this.systemRole === "NHAN_VIEN" ? "selected" : ""}>NHAN_VIEN</option>
                      <option value="ADMIN" ${this.systemRole === "ADMIN" ? "selected" : ""}>ADMIN</option>
                    </select>
                    <small>Quy\u1EC1n Ng\u01B0\u1EDDi \u0111\u1EB7t l\u1ECBch/Ng\u01B0\u1EDDi tham d\u1EF1 hi\u1EC7n c\xF3 \u0111\u01B0\u1EE3c gi\u1EEF nguy\xEAn.</small>
                  </div>
                </div>
              </div>
              <div class="us2-bulk-modal__mode">
                <input id="us2BulkModeRooms" type="radio" name="bulkMode" data-mode value="rooms"
                  ${this.mode === "rooms" ? "checked" : ""} ${this.saving ? "disabled" : ""}>
                <div>
                  <label for="us2BulkModeRooms"><strong>Thay danh s\xE1ch ph\xF2ng b\u1ECB c\u1EA5m \u0111\u1EB7t</strong></label>
                  <div class="us2-bulk-modal__section" ${this.mode !== "rooms" ? "hidden" : ""}>
                    ${this.loading ? '<span role="status">\u0110ang t\u1EA3i danh s\xE1ch ph\xF2ng...</span>' : `
                      <span class="us2-bulk-modal__rooms">
                        ${roomItems || "<span>Kh\xF4ng c\xF3 ph\xF2ng \u0111\u1EC3 ch\u1ECDn.</span>"}
                      </span>
                    `}
                    <small>S\u1EBD thay th\u1EBF to\xE0n b\u1ED9 danh s\xE1ch hi\u1EC7n t\u1EA1i b\u1EB1ng c\xE1c ph\xF2ng \u0111\xE3 ch\u1ECDn.</small>
                  </div>
                </div>
              </div>
              ${this.error ? `<p class="us2-bulk-modal__error" role="alert">${escapeHtml3(this.error)}</p>` : ""}
            </div>
            <footer class="us2-bulk-modal__footer">
              <button class="us2-bulk-modal__button us2-bulk-modal__button--cancel"
                type="button" data-close ${this.saving ? "disabled" : ""}>H\u1EE7y</button>
              <button class="us2-bulk-modal__button us2-bulk-modal__button--save"
                type="submit" ${this.loading || this.saving || this.mode === "rooms" && !this.roomsLoaded ? "disabled" : ""}>
                ${this.saving ? "\u0110ang l\u01B0u..." : "\xC1p d\u1EE5ng"}
              </button>
            </footer>
          </form>
        </section>
      </div>
    `;
    }
    async save() {
      if (this.loading || this.saving || !this.users.length || this.mode === "rooms" && !this.roomsLoaded) return;
      this.saving = true;
      this.error = "";
      this.render(true);
      const failures = [];
      const updatedIds = [];
      for (const user of this.users) {
        try {
          if (this.mode === "role") {
            const current = await this.options.permissionService.getUserPermissions(
              user.id,
              user.role === "ADMIN" ? "ADMIN" : "NHAN_VIEN"
            );
            await this.options.permissionService.updateUserPermissions(user.id, {
              canBook: current.canBook,
              canAttend: current.canAttend,
              systemRole: this.systemRole
            });
          } else {
            await this.options.restrictionService.updateUserRestrictions(user.id, {
              restrictedRoomIds: [...this.restrictedRoomIds]
            });
          }
          updatedIds.push(user.id);
        } catch (error) {
          const detail = error instanceof Error ? error.message : "L\u1ED7i kh\xF4ng x\xE1c \u0111\u1ECBnh";
          failures.push(`${user.fullName} (${user.email}): ${detail}`);
        }
      }
      this.saving = false;
      const changes = this.mode === "role" ? { mode: "role", systemRole: this.systemRole } : { mode: "rooms", restrictedRoomIds: [...this.restrictedRoomIds] };
      if (failures.length) {
        this.error = `\u0110\xE3 c\u1EADp nh\u1EADt ${updatedIds.length}/${this.users.length} t\xE0i kho\u1EA3n. Kh\xF4ng c\u1EADp nh\u1EADt \u0111\u01B0\u1EE3c:
${failures.join("\n")}`;
        this.options.onSaved?.(updatedIds, changes);
        this.render(true);
        return;
      }
      this.host?.querySelector("[data-backdrop]")?.setAttribute("hidden", "");
      this.options.onSaved?.(updatedIds, changes);
    }
    render(open) {
      if (!this.host) return;
      this.host.innerHTML = `<style>${BULK_STYLES}</style>${this.renderHtml()}`;
      if (open) this.host.querySelector("[data-backdrop]")?.removeAttribute("hidden");
    }
    getDialog() {
      return this.host?.querySelector('[role="dialog"]') ?? null;
    }
    isOpen() {
      return Boolean(this.host?.querySelector("[data-backdrop]:not([hidden])"));
    }
  };

  // src/features/us2_user_list/UserListTable.ts
  var TABLE_STYLES = `
  .us2-user-list { color: #172033; font: 14px/1.5 system-ui, sans-serif; }
  .us2-user-list * { box-sizing: border-box; }
  .us2-user-list__header, .us2-user-list__toolbar, .us2-user-list__pagination {
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
  }
  .us2-user-list__header { margin-bottom: 18px; flex-wrap: wrap; }
  .us2-user-list__header-actions { display: flex; flex-wrap: wrap; gap: 8px; }
  .us2-user-list__title { margin: 0; font-size: 22px; }
  .us2-user-list__toolbar { margin-bottom: 14px; flex-wrap: wrap; }
  .us2-user-list__search, .us2-user-list__filter {
    min-height: 40px; padding: 8px 12px; border: 1px solid #cbd5e1;
    border-radius: 8px; background: #fff; color: inherit;
  }
  .us2-user-list__search { width: min(100%, 360px); }
  .us2-user-list__table-wrap { overflow-x: auto; border: 1px solid #e2e8f0; border-radius: 10px; }
  .us2-user-list__table { width: 100%; border-collapse: collapse; text-align: left; }
  .us2-user-list__table th, .us2-user-list__table td {
    padding: 12px 14px; border-bottom: 1px solid #e2e8f0; white-space: nowrap;
  }
  .us2-user-list__table th { background: #f8fafc; color: #475569; font-weight: 600; }
  .us2-user-list__table tr:last-child td { border-bottom: 0; }
  .us2-user-list__badge {
    display: inline-block; padding: 3px 9px; border-radius: 999px;
    font-size: 12px; font-weight: 650;
  }
  .us2-user-list__role--admin { background: #ede9fe; color: #6d28d9; }
  .us2-user-list__role--booker { background: #dbeafe; color: #1d4ed8; }
  .us2-user-list__role--attendee { background: #cffafe; color: #0e7490; }
  .us2-user-list__status--active { background: #dcfce7; color: #15803d; }
  .us2-user-list__status--inactive { background: #f1f5f9; color: #475569; }
  .us2-user-list__actions { display: flex; gap: 8px; }
  .us2-user-list__action, .us2-user-list__button, .us2-user-list__bulk-button {
    border: 0; border-radius: 7px; padding: 8px 11px; font: inherit;
  }
  .us2-user-list__action { color: #334155; background: #f1f5f9; cursor: pointer; }
  .us2-user-list__action:hover:not(:disabled) { background: #e2e8f0; }
  .us2-user-list__button, .us2-user-list__bulk-button { background: #2563eb; color: #fff; text-decoration: none; cursor: pointer; }
  .us2-user-list__bulk-button { background: #475569; }
  .us2-user-list__action:disabled, .us2-user-list__bulk-button:disabled { opacity: .55; cursor: not-allowed; }
  .us2-user-list__selection { width: 1rem; height: 1rem; accent-color: #2563eb; }
  .us2-user-list__count-error { margin: 8px 0 0; color: #b91c1c; }
  .us2-user-list__pagination { padding: 14px 2px 0; color: #475569; }
  .us2-user-list__page-controls { display: flex; align-items: center; gap: 8px; }
  .us2-user-list__error { margin: 10px 0; color: #b91c1c; }
  .us2-user-list__empty { padding: 28px !important; color: #64748b; text-align: center; }
  @media (max-width: 640px) {
    .us2-user-list__header, .us2-user-list__pagination { align-items: flex-start; flex-direction: column; }
  }
`;
  function escapeHtml4(value) {
    return value.replace(/[&<>"']/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    })[character] ?? character);
  }
  function roleLabel(role) {
    return { ADMIN: "Admin", BOOKER: "Booker", ATTENDEE: "Attendee" }[role];
  }
  function roleClass(role) {
    return `us2-user-list__role--${role.toLowerCase()}`;
  }
  function statusClass(status) {
    return `us2-user-list__status--${status.toLowerCase()}`;
  }
  function formatDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "\u2014";
    return new Intl.DateTimeFormat("vi-VN", { year: "numeric", month: "2-digit", day: "2-digit" }).format(date);
  }
  var UserListTable = class {
    constructor(options = {}) {
      __publicField(this, "service");
      __publicField(this, "options");
      __publicField(this, "permissionService");
      __publicField(this, "restrictionService");
      __publicField(this, "selectedUserIds", /* @__PURE__ */ new Set());
      __publicField(this, "selectedUsers", /* @__PURE__ */ new Map());
      __publicField(this, "restrictionCounts", /* @__PURE__ */ new Map());
      __publicField(this, "container", null);
      __publicField(this, "query", { page: 1, limit: 10 });
      __publicField(this, "result", { items: [], total: 0, page: 1, limit: 10 });
      __publicField(this, "loading", false);
      __publicField(this, "error", "");
      __publicField(this, "restrictionCountError", "");
      __publicField(this, "requestId", 0);
      __publicField(this, "boundContainers", /* @__PURE__ */ new WeakSet());
      __publicField(this, "assignPermissionModal", null);
      __publicField(this, "roomRestrictionModal", null);
      __publicField(this, "bulkEditModal", null);
      this.options = options;
      this.service = options.service ?? new UserListService();
      this.permissionService = options.permissionService ?? new PermissionService();
      this.restrictionService = options.restrictionService ?? new RestrictionService();
      if (options.containerId && typeof document !== "undefined") {
        this.container = document.getElementById(options.containerId);
      }
    }
    renderHtml() {
      const pageCount = Math.max(1, Math.ceil(this.result.total / this.result.limit));
      const currentPageSelected = this.result.items.length > 0 && this.result.items.every((user) => this.selectedUserIds.has(user.id));
      const rows = this.result.items.length ? this.result.items.map((user) => this.renderRow(user)).join("") : `<tr><td class="us2-user-list__empty" colspan="8">${this.loading ? "\u0110ang t\u1EA3i danh s\xE1ch..." : "Kh\xF4ng t\xECm th\u1EA5y ng\u01B0\u1EDDi d\xF9ng."}</td></tr>`;
      return `
      <style>${TABLE_STYLES}</style>
      <section class="us2-user-list" aria-labelledby="us2-user-list-title">
        <header class="us2-user-list__header">
          <div>
            <h2 class="us2-user-list__title" id="us2-user-list-title">Danh s\xE1ch ng\u01B0\u1EDDi d\xF9ng</h2>
            <p>Qu\u1EA3n l\xFD t\xE0i kho\u1EA3n v\xE0 vai tr\xF2 trong h\u1EC7 th\u1ED1ng.</p>
          </div>
          <div class="us2-user-list__header-actions">
            <button class="us2-user-list__bulk-button" data-bulk-edit type="button"
              ${this.selectedUserIds.size === 0 || this.loading ? "disabled" : ""}>
              Ch\u1EC9nh s\u1EEDa \u0111\u1ED3ng b\u1ED9${this.selectedUserIds.size ? ` (${this.selectedUserIds.size})` : ""}
            </button>
            <a class="us2-user-list__button" data-create-user href="${escapeHtml4(this.options.createUserHref ?? "#createUserForm")}">
              + T\u1EA1o ng\u01B0\u1EDDi d\xF9ng m\u1EDBi
            </a>
          </div>
        </header>
        <div class="us2-user-list__toolbar">
          <label>
            <span class="sr-only">T\xECm theo t\xEAn ho\u1EB7c email</span>
            <input class="us2-user-list__search" data-search type="search"
              placeholder="T\xECm theo t\xEAn ho\u1EB7c email..." value="${escapeHtml4(this.query.search ?? "")}"
              autocomplete="off">
          </label>
          <label>
            <span class="sr-only">L\u1ECDc theo vai tr\xF2</span>
            <select class="us2-user-list__filter" data-role-filter aria-label="L\u1ECDc theo vai tr\xF2">
              <option value="">T\u1EA5t c\u1EA3 vai tr\xF2</option>
              ${["ADMIN", "BOOKER", "ATTENDEE"].map((role) => `
                <option value="${role}" ${this.query.role === role ? "selected" : ""}>${roleLabel(role)}</option>
              `).join("")}
            </select>
          </label>
        </div>
        ${this.error ? `<p class="us2-user-list__error" role="alert">${escapeHtml4(this.error)}</p>` : ""}
        ${this.restrictionCountError ? `<p class="us2-user-list__count-error" role="alert">${escapeHtml4(this.restrictionCountError)}</p>` : ""}
        <div class="us2-user-list__table-wrap">
          <table class="us2-user-list__table">
            <thead><tr>
              <th scope="col"><input class="us2-user-list__selection" data-select-page type="checkbox"
                aria-label="Ch\u1ECDn t\u1EA5t c\u1EA3 ng\u01B0\u1EDDi d\xF9ng tr\xEAn trang n\xE0y"
                ${currentPageSelected ? "checked" : ""} ${this.loading ? "disabled" : ""}></th>
              <th scope="col">H\u1ECD v\xE0 t\xEAn</th><th scope="col">Email</th><th scope="col">Vai tr\xF2</th>
              <th scope="col">Tr\u1EA1ng th\xE1i</th><th scope="col">Ng\xE0y t\u1EA1o</th><th scope="col">H\xE0nh \u0111\u1ED9ng</th>
              <th scope="col">Gi\u1EDBi h\u1EA1n \u0111\u1EB7t ph\xF2ng</th>
            </tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
        <footer class="us2-user-list__pagination" aria-label="Ph\xE2n trang">
          <span>Hi\u1EC3n th\u1ECB ${this.result.items.length ? (this.result.page - 1) * this.result.limit + 1 : 0}\u2013${Math.min(this.result.page * this.result.limit, this.result.total)} trong ${this.result.total} ng\u01B0\u1EDDi d\xF9ng</span>
          <div class="us2-user-list__page-controls">
            <button class="us2-user-list__action" data-page="previous" type="button"
              ${this.loading || this.result.page <= 1 ? "disabled" : ""}>Tr\u01B0\u1EDBc</button>
            <span>Trang ${this.result.page} / ${pageCount}</span>
            <button class="us2-user-list__action" data-page="next" type="button"
              ${this.loading || this.result.page >= pageCount ? "disabled" : ""}>Sau</button>
          </div>
        </footer>
      </section>
    `;
    }
    async mount(targetElement) {
      const container = targetElement ?? this.container;
      if (!container) throw new Error("Container element not found for UserListTable.");
      this.container = container;
      this.bindEvents(container);
      this.render();
      await this.loadUsers();
    }
    async loadUsers(query = this.query) {
      this.query = { ...query, page: query.page ?? 1, limit: query.limit ?? 10 };
      this.loading = true;
      this.error = "";
      const requestId = ++this.requestId;
      this.render();
      try {
        const result = await this.service.getUsers(this.query);
        if (requestId !== this.requestId) return;
        this.result = result;
        result.items.forEach((user) => {
          if (this.selectedUserIds.has(user.id)) this.selectedUsers.set(user.id, { ...user });
        });
        await this.loadRestrictionCounts(result.items, requestId);
      } catch (error) {
        if (requestId !== this.requestId) return;
        this.error = error instanceof Error ? error.message : "Kh\xF4ng th\u1EC3 t\u1EA3i danh s\xE1ch ng\u01B0\u1EDDi d\xF9ng.";
        this.result = { ...this.result, items: [], total: 0, page: this.query.page ?? 1 };
        this.restrictionCounts.clear();
      } finally {
        if (requestId === this.requestId) {
          this.loading = false;
          this.render();
        }
      }
    }
    bindEvents(root) {
      if (this.boundContainers.has(root)) return;
      this.boundContainers.add(root);
      root.addEventListener("input", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLInputElement) || !target.matches("[data-search]")) return;
        void this.loadUsers({ ...this.query, search: target.value, page: 1 });
      });
      root.addEventListener("change", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;
        if (target instanceof HTMLSelectElement && target.matches("[data-role-filter]")) {
          const role = target.value;
          void this.loadUsers({ ...this.query, role: role || void 0, page: 1 });
        } else if (target instanceof HTMLInputElement && target.matches("[data-select-page]")) {
          this.result.items.forEach((user) => {
            if (target.checked) {
              this.selectedUserIds.add(user.id);
              this.selectedUsers.set(user.id, { ...user });
            } else {
              this.selectedUserIds.delete(user.id);
              this.selectedUsers.delete(user.id);
            }
          });
          this.render();
        } else if (target instanceof HTMLInputElement && target.matches("[data-select-user]")) {
          const user = this.result.items.find((item) => item.id === target.value);
          if (target.checked && user) {
            this.selectedUserIds.add(user.id);
            this.selectedUsers.set(user.id, { ...user });
          } else {
            this.selectedUserIds.delete(target.value);
            this.selectedUsers.delete(target.value);
          }
          this.render();
        }
      });
      root.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof Element)) return;
        const createLink = target.closest("[data-create-user]");
        if (createLink && this.options.onCreateUser) {
          event.preventDefault();
          this.options.onCreateUser();
          return;
        }
        const bulkButton = target.closest("[data-bulk-edit]");
        if (bulkButton && !bulkButton.disabled) {
          const users = [...this.selectedUsers.values()];
          if (users.length) void this.getBulkEditModal().open(users);
          return;
        }
        const actionButton = target.closest("[data-user-action]");
        if (actionButton) {
          const user = this.result.items.find((item) => item.id === actionButton.dataset.userId);
          if (user?.id) {
            if (actionButton.dataset.userAction === "permissions") {
              void this.getAssignPermissionModal().open({
                id: user.id,
                fullName: user.fullName,
                email: user.email,
                role: user.role
              });
            } else if (actionButton.dataset.userAction === "restrictions") {
              void this.getRoomRestrictionModal().open({
                id: user.id,
                fullName: user.fullName,
                email: user.email
              });
            }
          }
          return;
        }
        const pageButton = target.closest("[data-page]");
        if (!pageButton || pageButton.disabled) return;
        const page = this.query.page ?? 1;
        void this.loadUsers({ ...this.query, page: pageButton.dataset.page === "next" ? page + 1 : page - 1 });
      });
    }
    render() {
      if (!this.container) return;
      const activeElement = document.activeElement;
      const hadSearchFocus = activeElement instanceof HTMLInputElement && activeElement.matches("[data-search]") && this.container.contains(activeElement);
      const selectionStart = hadSearchFocus ? activeElement.selectionStart : null;
      const selectionEnd = hadSearchFocus ? activeElement.selectionEnd : null;
      const hadRoleFilterFocus = activeElement instanceof HTMLSelectElement && activeElement.matches("[data-role-filter]") && this.container.contains(activeElement);
      const hadSelectPageFocus = activeElement instanceof HTMLInputElement && activeElement.matches("[data-select-page]") && this.container.contains(activeElement);
      const focusedUserId = activeElement instanceof HTMLInputElement && activeElement.matches("[data-select-user]") && this.container.contains(activeElement) ? activeElement.value : null;
      this.container.innerHTML = this.renderHtml();
      if (hadSearchFocus) {
        const searchInput = this.container.querySelector("[data-search]");
        searchInput?.focus();
        if (selectionStart !== null && selectionEnd !== null) {
          searchInput?.setSelectionRange(selectionStart, selectionEnd);
        }
      } else if (hadRoleFilterFocus) {
        this.container.querySelector("[data-role-filter]")?.focus();
      } else if (hadSelectPageFocus) {
        this.container.querySelector("[data-select-page]")?.focus();
      } else if (focusedUserId) {
        Array.from(this.container.querySelectorAll("[data-select-user]")).find((input) => input.value === focusedUserId)?.focus();
      }
    }
    renderRow(user) {
      const restrictionCount = this.restrictionCounts.get(user.id);
      return `<tr>
      <td><input class="us2-user-list__selection" data-select-user type="checkbox"
        value="${escapeHtml4(user.id)}" aria-label="Ch\u1ECDn ${escapeHtml4(user.fullName)}"
        ${this.selectedUserIds.has(user.id) ? "checked" : ""} ${this.loading ? "disabled" : ""}></td>
      <td>${escapeHtml4(user.fullName)}</td>
      <td>${escapeHtml4(user.email)}</td>
      <td><span class="us2-user-list__badge ${roleClass(user.role)}">${roleLabel(user.role)}</span></td>
      <td><span class="us2-user-list__badge ${statusClass(user.status)}">${user.status}</span></td>
      <td>${formatDate(user.createdAt)}</td>
      <td><div class="us2-user-list__actions">
        <button class="us2-user-list__action" type="button" data-user-action="permissions"
          data-user-id="${escapeHtml4(user.id)}">S\u1EEDa quy\u1EC1n</button>
        <button class="us2-user-list__action" type="button" data-user-action="restrictions"
          data-user-id="${escapeHtml4(user.id)}">Gi\u1EDBi h\u1EA1n ph\xF2ng</button>
      </div></td>
      <td>${restrictionCount === void 0 || restrictionCount === null ? "\u2014" : `${restrictionCount} ph\xF2ng`}</td>
    </tr>`;
    }
    async loadRestrictionCounts(users, requestId) {
      this.restrictionCounts.clear();
      this.restrictionCountError = "";
      if (!users.length) return;
      const results = await Promise.allSettled(
        users.map((user) => this.restrictionService.getUserRestrictions(user.id))
      );
      if (requestId !== this.requestId) return;
      let failedCount = 0;
      results.forEach((result, index) => {
        const userId = users[index].id;
        if (result.status === "fulfilled") {
          this.restrictionCounts.set(userId, result.value.restrictedRoomIds.length);
        } else {
          this.restrictionCounts.set(userId, null);
          failedCount += 1;
        }
      });
      if (failedCount) {
        this.restrictionCountError = `Kh\xF4ng t\u1EA3i \u0111\u01B0\u1EE3c gi\u1EDBi h\u1EA1n ph\xF2ng c\u1EE7a ${failedCount} ng\u01B0\u1EDDi d\xF9ng; c\xE1c \xF4 ch\u01B0a t\u1EA3i hi\u1EC3n th\u1ECB \u201C\u2014\u201D.`;
      }
    }
    getAssignPermissionModal() {
      this.assignPermissionModal ?? (this.assignPermissionModal = new AssignPermissionModal({
        service: this.permissionService,
        onSaved: (_user, permissions) => {
          const user = this.result.items.find((item) => item.id === permissions.userId);
          const selectedUser = this.selectedUsers.get(permissions.userId);
          const updatedRole = permissions.systemRole === "ADMIN" ? "ADMIN" : permissions.canBook ? "BOOKER" : "ATTENDEE";
          this.service.updateMockUserRole(permissions.userId, updatedRole);
          if (user) user.role = updatedRole;
          if (selectedUser) selectedUser.role = updatedRole;
          this.render();
        }
      }));
      return this.assignPermissionModal;
    }
    getRoomRestrictionModal() {
      this.roomRestrictionModal ?? (this.roomRestrictionModal = new RoomRestrictionModal({
        service: this.restrictionService,
        onSaved: () => void this.loadUsers(this.query)
      }));
      return this.roomRestrictionModal;
    }
    getBulkEditModal() {
      this.bulkEditModal ?? (this.bulkEditModal = new BulkUserEditModal({
        permissionService: this.permissionService,
        restrictionService: this.restrictionService,
        onSaved: (userIds, changes) => {
          if (changes.mode === "role" && changes.systemRole) {
            userIds.forEach((userId) => {
              const user = this.result.items.find((item) => item.id === userId);
              const selectedUser = this.selectedUsers.get(userId);
              const updatedRole = changes.systemRole === "ADMIN" ? "ADMIN" : user?.role === "ATTENDEE" || selectedUser?.role === "ATTENDEE" ? "ATTENDEE" : "BOOKER";
              this.service.updateMockUserRole(userId, updatedRole);
              if (user) user.role = updatedRole;
              if (selectedUser) selectedUser.role = updatedRole;
            });
          } else if (changes.mode === "rooms" && changes.restrictedRoomIds) {
            userIds.forEach((userId) => {
              this.restrictionCounts.set(userId, changes.restrictedRoomIds?.length ?? 0);
            });
          }
          userIds.forEach((userId) => {
            this.selectedUserIds.delete(userId);
            this.selectedUsers.delete(userId);
          });
          this.render();
        }
      }));
      return this.bulkEditModal;
    }
  };

  // src/features/us2_user_list/dashboard.ts
  var userListTable = null;
  function mountUserListTable(containerId, onCreateUser) {
    const container = document.getElementById(containerId);
    if (!container) {
      throw new Error(`User list container "#${containerId}" was not found.`);
    }
    userListTable ?? (userListTable = new UserListTable({
      containerId,
      createUserHref: "#adminCreateUserForm",
      onCreateUser
    }));
    return userListTable.mount(container);
  }
  return __toCommonJS(dashboard_exports);
})();
