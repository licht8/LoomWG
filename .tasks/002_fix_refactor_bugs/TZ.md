# TZ: Fixing Errors After cli.py Refactoring

## 1. Problem

After refactoring `cli.py` (2604 → 106 lines) the application crashes on startup.

### Error #1 (critical, blocking startup)

```
File "/root/loomwg/loom/cli/common.py", line 254, in show_header_info
    if wg_manager.is_installed():
AttributeError: 'WireGuardInstaller' object has no attribute 'is_installed'
```

**Root:** In `show_header_info()` an object `WireGuardInstaller` was created instead of `WireGuardManager`.
- `WireGuardInstaller` — class for INSTALLING the WireGuard package (methods: `install()`, `_install_packages()`, etc.)
- `WireGuardManager` — class for MANAGING the interface (methods: `is_installed()`, `get_interfaces()`, `start()`, `stop()`)

**Where:** `loom/cli/common.py`, lines 243, 247

---

## 2. Full List of Errors in Files After Refactoring

### 2.1. `loom/cli/common.py`

**Error:** `WireGuardInstaller` instead of `WireGuardManager` in `show_header_info()` (lines 243, 247)

```python
# CURRENT CODE (BAD):
from ..wireguard.installer import WireGuardInstaller
...
wg_manager = WireGuardInstaller()
if wg_manager.is_installed():       # ← AttributeError!
    interfaces = wg_manager.get_interfaces()
```

```python
# CORRECT:
from ..wireguard.manager import WireGuardManager
...
wg_manager = WireGuardManager()
if wg_manager.is_installed():
    interfaces = wg_manager.get_interfaces()
```

---

### 2.2. `loom/commands/configure_server.py`

**Error:** Missing imports. File uses `console.print()`, `LoomLogger`, `FirewalldManager`, `NetworkManager`, `subprocess.run`, `ip_network`, but they are not imported.

**Not imported:**
| Name | Required for |
|------|--------------|
| `console` | `console.print()` — lines 24, 34, 40, 54, 65, 70, 73, 93, 96, 106, 110, 117, 122, 132, 134, 137, 141, 148, 155, 157 |
| `LoomLogger` | `LoomLogger()` — line 113 |
| `FirewalldManager` | `FirewalldManager()` — line 125 |
| `NetworkManager` | `NetworkManager()` — line 147 |
| `subprocess` | `subprocess.run()` — lines 225, 239 |
| `ip_network` | `ip_network()` — line 231 |

**Garbage:** Import `WireGuardInstaller` (line 9) — UNNECESSARY, class is not used in the file.

---

### 2.3. `loom/commands/install_wireguard.py`

**Error:** Missing imports.

**Not imported:**
| Name | Required for |
|------|--------------|
| `selected_interface` | Line 21 — used in `install_wireguard()` |
| `confirm` | Line 46 — used for installation confirmation |
| `console` | `console.print()` — many lines |
| `WireGuardManager` | Line 122 — needed for `start_with_result()` |
| `FirewalldManager` | Line 110 — needed for firewall |
| `NetworkManager` | Line 117 — needed for IP forwarding |

---

### 2.4. `loom/commands/key_rotation.py`

**Error:** Missing imports. File uses many functions and classes without import.

**Not imported:**
| Name | Required for |
|------|--------------|
| `re` | `re.sub()` — line 66 |
| `BackupManager` | `BackupManager()` — line 51 |
| `LoomLogger` | `LoomLogger()` — lines 105, 134 |
| `console` | `console.print()` — many lines |
| `normalize_wireguard_config` | Lines 30, 65, 72, 85, 126 |
| `repair_wireguard_config_file` | Line 30 |

**Garbage:** Import `WireGuardInstaller` (line 12) — UNNECESSARY, class is not used in the file.

---

### 2.5. `loom/commands/lifecycle.py`

**Error:** Garbage imports (not used).

```python
from ..wireguard.manager import WireGuardManager  # ← NOT used
from ..wireguard.installer import WireGuardInstaller  # ← NOT used
```

Classes `WireGuardManager` and `WireGuardInstaller` are not called in this file — these are extra imports from auto-extraction.

---

## 3. Table of All Fixes

| File | What to fix | Lines |
|------|--------------|--------|
| `cli/common.py` | `WireGuardInstaller` → `WireGuardManager` in `show_header_info()` | 2 |
| `commands/configure_server.py` | Add 6 missing imports, remove `WireGuardInstaller` | 7 |
| `commands/install_wireguard.py` | Add 6 missing imports | 6 |
| `commands/key_rotation.py` | Add 6 missing imports, remove `WireGuardInstaller` | 7 |
| `commands/lifecycle.py` | Remove 2 unused imports | 2 |

---

## 4. Fix Order

### Step 1: Fix the blocking startup error
- `cli/common.py` — replace `WireGuardInstaller` with `WireGuardManager`
- Run `python -c "from loom.cli import main_menu"` — application should start

### Step 2: Add missing imports
- `commands/configure_server.py` — add `console`, `LoomLogger`, `FirewalldManager`, `NetworkManager`, `subprocess`, `ip_network`
- `commands/install_wireguard.py` — add `selected_interface`, `confirm`, `console`, `WireGuardManager`, `FirewalldManager`, `NetworkManager`
- `commands/key_rotation.py` — add `re`, `BackupManager`, `LoomLogger`, `console`, `normalize_wireguard_config`, `repair_wireguard_config_file`

### Step 3: Remove garbage imports
- `commands/configure_server.py` — remove `WireGuardInstaller`
- `commands/key_rotation.py` — remove `WireGuardInstaller`
- `commands/lifecycle.py` — remove `WireGuardManager` and `WireGuardInstaller`

### Step 4: Run `pytest`
- Ensure 58/58 tests pass

---

## 5. Acceptance Criteria

1. ✅ `python -c "from loom.cli import main_menu"` — without errors
2. ✅ `pytest` — 58/58 passed
3. ✅ No `AttributeError` on application startup
4. ✅ No unused imports
5. ✅ All `console.print()`, `subprocess.run()`, `LoomLogger()` correctly imported