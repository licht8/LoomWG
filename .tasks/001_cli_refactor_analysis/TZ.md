# TZ: Decomposition of `loom/cli.py` (Refactoring God File)

## 1. Context and Goal
**Task:** Break the file `loom/cli.py` (2604 lines) into a modular structure.
**Goal:** Separate responsibility between navigation (UI), business logic (Commands), and rendering (Views).
**Rules:**
- Do not delete old code, move it to `_Trash/`.
- Run `pytest` after each phase.
- Follow the Single Responsibility Principle (SRP).

---

## 2. New Architecture

```text
loom/
├── cli/                      # LAYER 1: Navigation and Input
│   ├── __init__.py           # Menu imports
│   ├── router.py             # Main router (main)
│   ├── common.py             # Utilities: clear_screen, pause, confirm, banner
│   ├── main_menu.py          # main_menu
│   ├── server_menu.py        # server_menu + sub-actions
│   ├── peers_menu.py         # peers_menu + sub-actions
│   ├── firewall_menu.py      # firewall_menu
│   ├── diagnostics_menu.py   # diagnostics_menu
│   ├── backup_menu.py        # backup_menu
│   ├── logs_menu.py          # logs_menu
│   └── system_info_menu.py   # system_info_menu + version
│
├── commands/                 # LAYER 2: Business Logic (Actions)
│   ├── __init__.py           # Command imports
│   ├── configure_server.py   # configure_server (pure logic)
│   ├── install_wireguard.py  # install_wireguard
│   ├── create_peer.py        # create_peer (IP logic, keys)
│   ├── peer_lifecycle.py     # enable_peer, disable_peer, revoke_peer, rotate_peer_keys, remove_peer
│   ├── key_rotation.py       # rotate_server_keys (complex logic with rollback)
│   ├── interface_manager.py  # manage_interfaces, create_interface, delete_interface
│   ├── peer_expiry.py        # set_peer_expiry, enforce_expired_peers
│   ├── peer_import.py        # import_server_peers
│   └── lifecycle.py          # remove_wireguard, reinstall_wireguard
│
├── views/                    # LAYER 3: Rendering (UI)
│   ├── __init__.py           # View imports
│   ├── server_status.py      # show_server_status, _wg_runtime_dashboard
│   ├── peer_views.py         # peer_table, show_peer, show_peer_selection
│   ├── qr_display.py         # display_peer_qr_code, show_qr_code
│   ├── backup_views.py       # table creation for backups
│   ├── log_views.py          # view_logs (formatting)
│   └── system_dashboard.py   # system_info_menu (panel rendering)
│
└── cli.py                    # ONLY Entry Point (40-50 lines)
```

---

## 3. Detailed Module Requirements

### 3.1. `loom/cli/common.py`
**Contents:** Extract common functions used in every menu.
- `clear_screen()`
- `pause()`
- `confirm(prompt)`
- `section_banner(title, subtitle)`
- `menu_option(number, title, description, command)`
- `check_root()`
- `show_header_info()`
- `selected_interface()`, `select_interface()`
- `prompt_for_qr_code()`

**Constraint:** No business logic, only UI helpers.

### 3.2. `loom/commands/...`
**Contents:** Extract functions that change something (disk writes, executing `wg`, `dnf` commands).
- **Example `create_peer`:** The function must accept name, IP, and keys as arguments, perform peer addition logic, and return a result or `Peer` object. It **MUST NOT** call `input()` or `console.print()`.
- **Example `rotate_server_keys`:** Must accept the current config and return a new one (with checks), without `clear_screen`.

**File list and what to put in them:**
1.  **`configure_server.py`**: Logic of `configure_server`.
2.  **`install_wireguard.py`**: Logic of `install_wireguard`.
3.  **`create_peer.py`**: Logic of `create_peer`.
4.  **`peer_lifecycle.py`**: `enable_peer`, `disable_peer`, `revoke_peer`, `rotate_peer_keys`, `remove_peer`.
5.  **`key_rotation.py`**: `rotate_server_keys` (the most complex, requires rollback tests).
6.  **`interface_manager.py`**: `manage_interfaces`, `create_interface`, `delete_interface`.
7.  **`peer_expiry.py`**: `set_peer_expiry`, `enforce_expired_peers`.
8.  **`peer_import.py`**: `import_server_peers`.
9.  **`lifecycle.py`**: `remove_wireguard`, `reinstall_wireguard`.

### 3.3. `loom/views/...`
**Contents:** Extract functions that only read data and output it (Rich Console).
1.  **`server_status.py`**: `show_server_status`, `_wg_runtime_dashboard` (can stay here or in commands if it's pure data processing).
2.  **`peer_views.py`**: `peer_table`, `show_peer`, `show_peer_selection`.
3.  **`qr_display.py`**: `display_peer_qr_code`, `show_qr_code`.
4.  **`backup_views.py`**: Backup list output (table formatting).
5.  **`log_views.py`**: `view_logs`.
6.  **`system_dashboard.py`**: `system_info_menu`.

### 3.4. `loom/cli/router.py`
**Contents:** Main controller.
- `main_menu()`: Displays the menu, receives `input()` choice, calls the corresponding function from `commands` or a nested menu.
- Use the "Incoming function calls View + Command" pattern.

---

## 4. Refactoring Rules

1.  **Separation of logic and UI:**
    - `commands` MUST NOT do `print`, `input`, `console.print`, `clear_screen`.
    - `views` MUST NOT do `subprocess.run`, `open('w')`, `peer_mgr.add_peer()`.
    - `cli` manages the flow: "Ask for input -> Pass to Command -> Get result -> Pass to View".

2.  **Import management:**
    - Do not create circular imports.
    - Carefully redistribute old imports in `cli.py` across new files.

3.  **Phased approach:**
    - First extract `common.py` (the safest).
    - Then extract View functions (just moving code).
    - Then extract commands (requires adapting argument passing).
    - Finally update `cli.py` (insert calls to new modules).

4.  **Testing:**
    - After each function move (e.g., `create_peer`) ensure `pytest` passes or the function is isolated and tested separately.

## 5. Acceptance Criteria
1.  `loom/cli.py` contains no more than 50-60 lines (entry point and router).
2.  No duplication of `clear_screen()`, `pause()`, `confirm()`.
3.  No business logic in files with the `_menu.py` suffix.
4.  `pytest` passes successfully.