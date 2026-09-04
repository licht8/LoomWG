# Plan: Decomposition of `loom/cli.py`

## Phase 1: Preparing the Common Base (`common.py`)

**Goal:** Extract common UI utilities into a separate module. This is the safest change — no dependencies on other new modules.

### Steps:

1. **Create `loom/cli/common.py`**
   - Extract functions:
     - `clear_screen()`
     - `pause()`
     - `confirm(prompt)`
     - `section_banner(title, subtitle)`
     - `menu_option(number, title, description, command)`
     - `show_banner()`
   - Export all via `__all__`.

2. **Update `loom/cli/__init__.py`**
   - Add import from `common`: `from .common import *`.

3. **Update `loom/cli.py`**
   - Replace local calls with import from `loom.cli.common`.
   - Remove functions moved to `common.py`.
   - Verify `cli.py` still works: run `python -c "from loom.cli import main_menu"` (without calling main).

**Completion Criteria:** `pytest` passes. `cli.py` is shorter by ~80 lines.

---

## Phase 2: Extracting View Functions (`loom/views/`)

**Goal:** Separate rendering functions from logic. Functions that only display data move to `loom/views/`.

### Steps:

1. **Create `loom/views/__init__.py`**

2. **Create `loom/views/server_status.py`**
   - Extract: `show_server_status()`, `_wg_runtime_dashboard()`, `_age_text()`, `_format_bytes()`.
   - Dependencies: `subprocess`, `datetime`, `loom.wireguard.*`. Keep as is.

3. **Create `loom/views/peer_views.py`**
   - Extract: `list_peers()`, `peer_table()`, `show_peer()`, `show_peer_selection()`.
   - Dependencies: `loom.wireguard.peer_manager.Peer`, `loom.cli.common`.

4. **Create `loom/views/qr_display.py`**
   - Extract: `prompt_for_qr_code()`, `display_peer_qr_code()`, `show_qr_code()`.
   - Dependencies: `loom.wireguard.client_config`, `loom.views.peer_views`.

5. **Create `loom/views/backup_views.py`**
   - Extract: `list_backups()`, `create_backup()`, `restore_backup()`, `delete_backup()`.
   - Dependencies: `loom.backup.manager`, `loom.cli.common`.

6. **Create `loom/views/log_views.py`**
   - Extract: `view_logs()`, `clear_logs()`, `export_logs()`.
   - Dependencies: `loom.logging_system.logger`, `loom.cli.common`.

7. **Update `loom/cli.py`**
   - Replace View function calls with import from `loom.views`.
   - Remove extracted code.

**Completion Criteria:** `pytest` passes. `cli.py` is shorter by ~400 lines.

---

## Phase 3: Extracting Business Logic (`loom/commands/`)

**Goal:** Separate actions that change something from UI. Functions that write files and call `subprocess.run` move to `loom/commands/`.

### Steps:

1. **Create `loom/commands/__init__.py`**

2. **Create `loom/commands/configure_server.py`**
   - Extract: `configure_server()`, `prompt_server_config()`, `validate_server_settings()`.
   - Arguments: interface, config file. Return: result or exceptions.

3. **Create `loom/commands/install_wireguard.py`**
   - Extract: `install_wireguard()`.
   - Arguments: interface name.

4. **Create `loom/commands/peer_lifecycle.py`**
   - Extract: `enable_peer()`, `disable_peer()`, `revoke_peer()`, `rotate_peer_keys()`, `remove_peer()`.
   - These functions are complex — each contains:
     - `show_peer_selection()` (View)
     - `input()` (UI)
     - business logic
   - **Important:** Command functions MUST NOT call `input()` or `print()`. Create a separate interface layer for this.
   - **Decision:** In `commands/` extract ONLY pure logic. In `cli/` keep `input()` calls and pass data to commands.

5. **Create `loom/commands/key_rotation.py`**
   - Extract: `rotate_server_keys()`.
   - The most complex function: contains rollback logic, backups, client config regeneration.

6. **Create `loom/commands/interface_manager.py`**
   - Extract: `manage_interfaces()`, `create_interface()`, `delete_interface()`.

7. **Create `loom/commands/peer_expiry.py`**
   - Extract: `set_peer_expiry()`, `enforce_expired_peers()`.

8. **Create `loom/commands/peer_import.py`**
   - Extract: `import_server_peers()`.

9. **Create `loom/commands/lifecycle.py`**
   - Extract: `remove_wireguard()`, `reinstall_wireguard()`.

10. **Update `loom/cli.py`**
    - Replace calls with import from `loom.commands`.
    - Remove extracted code.

**Completion Criteria:** `pytest` passes. `cli.py` is shorter by ~800 lines.

---

## Phase 4: Creating Router and Menus

**Goal:** Create structured menus in `loom/cli/` and a router for navigation.

### Steps:

1. **Create `loom/cli/router.py`**
   - `main_menu()` — main menu, uses a routes dictionary:
     ```python
     ROUTES = {
         '1': ('server', server_menu.server_menu),
         '2': ('peers', peers_menu.peers_menu),
         # ...
     }
     ```

2. **Create `loom/cli/server_menu.py`**
   - `server_menu()` — server menu.
   - Calls functions from `loom.commands` and `loom.views`.

3. **Create `loom/cli/peers_menu.py`**
   - `peers_menu()` — peers menu.

4. **Create `loom/cli/firewall_menu.py`**
   - `firewall_menu()` — firewall menu.

5. **Create `loom/cli/diagnostics_menu.py`**
   - `diagnostics_menu()` — diagnostics menu.

6. **Create `loom/cli/backup_menu.py`**
   - `backup_menu()` — backups menu.

7. **Create `loom/cli/logs_menu.py`**
   - `logs_menu()` — logs menu.

8. **Create `loom/cli/system_info_menu.py`**
   - `system_info_menu()` — system information menu.
   - `version_menu()` — version display.

9. **Update `loom/cli.py`**
   - Keep ONLY `if __name__ == '__main__': main_menu()`.
   - Remove all menu code and business logic.

**Completion Criteria:** `pytest` passes. `cli.py` ~40 lines. All new files work.

---

## Phase 5: Final Cleanup

**Goal:** Remove old dependencies, check all imports, update `__init__.py`.

### Steps:

1. **Check all imports**
   - Ensure no module imports anything from `loom.cli.py` (except entry point).
   - Ensure no circular imports.

2. **Update `loom/__init__.py`**
   - Add public imports of new modules.

3. **Update `pyproject.toml`**
   - If needed, add new packages.

4. **Run full `pytest`**
   - Ensure all tests pass.
   - If any tests reference functions from `cli.py` — update their imports.

5. **Prepare `_Trash/` folder**
   - If any parts of old `cli.py` were deleted, move them to `_Trash/`.

**Completion Criteria:** Clean code, all tests green, `cli.py` < 60 lines.

---

## Summary Estimate

| Phase | Action | Expected Result |
|-------|--------|-----------------|
| 1 | `common.py` | ~80 lines extracted |
| 2 | `views/` | ~400 lines extracted |
| 3 | `commands/` | ~800 lines extracted |
| 4 | `cli/` menus | ~600 lines extracted |
| 5 | Cleanup | `cli.py` < 60 lines |

**Total:** cli.py will shrink from 2604 to ~50 lines. ~12 new files of 100-300 lines each will be created.