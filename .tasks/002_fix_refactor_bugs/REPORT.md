# Report: Fixing Errors After cli.py Refactoring

## Goal
Fix all import errors and incorrect classes that arose after decomposing `cli.py` in commit `f9bd1c6`.

## Completed Fixes

### 1. `loom/cli/common.py` — Critical Blocking Error
**Problem:** `WireGuardInstaller` instead of `WireGuardManager` in `show_header_info()` → `AttributeError: 'WireGuardInstaller' object has no attribute 'is_installed'`
**Fix:** Replaced import and instance with `WireGuardManager`

### 2. `loom/commands/configure_server.py` — 6 Missing Imports + 1 Garbage
**Added:** `subprocess`, `ip_network`, `Console`, `FirewalldManager`, `NetworkManager`, `LoomLogger`, `console = Console()`
**Removed:** `WireGuardInstaller` (unused)

### 3. `loom/commands/install_wireguard.py` — 6 Missing Imports
**Added:** `WireGuardManager`, `FirewalldManager`, `NetworkManager`, `selected_interface`, `confirm`, `console`

### 4. `loom/commands/key_rotation.py` — 6 Missing Imports + 1 Garbage
**Added:** `re`, `BackupManager`, `LoomLogger`, `console`, import `normalize_wireguard_config` and `repair_wireguard_config_file` from `configure_server`
**Removed:** `WireGuardInstaller` (unused)

### 5. `loom/commands/lifecycle.py` — 2 Unused Imports
**Removed:** `WireGuardManager`, `WireGuardInstaller`
**Added:** `console = Console()` (used in file functions)

## Test Results
```
58 passed in 0.51s
```
All 58 tests passed. No syntax errors.

## Acceptance Criteria
| # | Criterion | Status |
|---|-----------|--------|
| 1 | `python -c "from loom.cli import main_menu"` without errors | ✅ |
| 2 | `pytest` — 58/58 passed | ✅ |
| 3 | No `AttributeError` | ✅ |
| 4 | No unused imports | ✅ |
| 5 | All `console.print()`, `subprocess.run()`, `LoomLogger()` imported | ✅ |

## Commit
```
429fa1c fix: restore imports and correct classes after cli.py refactoring
```

## Modified Files
- `loom/cli/common.py` — 2 lines (WireGuardInstaller → WireGuardManager)
- `loom/commands/configure_server.py` — added ~8 import lines, removed garbage
- `loom/commands/install_wireguard.py` — added ~7 import lines
- `loom/commands/key_rotation.py` — added ~9 import lines, removed garbage
- `loom/commands/lifecycle.py` — removed 2 lines, added console