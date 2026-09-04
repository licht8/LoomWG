# TZ: Fixing Remaining NameError and Similar Errors (Round 008)

## 1. Goal
Eliminate `NameError` and `ImportError` occurring during specific actions in CLI after `cli.py` refactoring. Errors are caused by the auto-extractor splitting the file into modules but not carrying necessary imports into each specific file/function.

---

## 2. Critical Errors from Report (2 files)

### 2.1. `cli/common.py` — `delete_interface()` without `interface_config_path`

**Traceback:**
```
File "loom/cli/common.py", line 344, in delete_interface
    path = interface_config_path(interface)
NameError: name 'interface_config_path' is not defined
```

**Problem:**
The function `delete_interface()` (starts ~line 332) locally imports only `WireGuardManager`, `ServiceManager`, `LoomLogger`. The call `interface_config_path(interface)` happens without import.

**Fix:**
Add to the local imports block of function `delete_interface()` (after line with `from ..logging_system.logger import LoomLogger`):
```python
from ..wireguard.interfaces import config_path as interface_config_path
```

---

### 2.2. `cli/system_info_menu.py` — Missing `import sys`

**Traceback:**
```
File "loom/cli/system_info_menu.py", line 57, in system_info_menu
    section("LoomWG", [("Version", "0.1.0"), ("Python", sys.version.split()[0]), ("Executable", sys.executable), ...])
NameError: name 'sys' is not defined
```

**Problem:**
At top of file there is `import subprocess` and `from pathlib import Path`, but `sys` is not connected. Used on line 57.

**Fix:**
Add at very top of file (after docstring):
```python
import sys
```

---

## 3. Similar Errors (Found by Codebase Analysis)

Scanning showed **5 similar cases** — used names without import in other files.

### 3.1. `views/qr_display.py` — `show_peer_selection` Not Imported
**Problem:** `show_peer_selection(peer_mgr)` is called (~line 19), but import is missing.
**Fix:** Add to imports: `from ..views.peer_views import show_peer_selection`

### 3.2. `views/log_views.py` — `FirewalldManager` and `confirm` Not Imported
**Problem:**
- Line 23: `firewall = FirewalldManager()` — class not connected.
- Line 89: `if confirm("Clear all logs?"):` — function not connected.
**Fix:** Add at top of file:
```python
from ..firewall.firewalld import FirewalldManager
from ..cli.common import clear_screen, section_banner, pause, confirm
```

### 3.3. `commands/peer_lifecycle.py` — `SystemDetector` Not Imported
**Problem:** Line ~249: `SystemDetector().detect().public_ip` — class not connected.
**Fix:** Add to global imports: `from ..system.info import SystemDetector`

### 3.4. `commands/key_rotation.py` — Duplicate `import re`
**Problem:** Line 2: `import re` and line 15: `import re`.
**Fix:** Remove one duplicate (line 15).

### 3.5. `cli/logs_menu.py` — Duplicate `show_header_info`
**Problem:** `from ..cli.common import show_header_info` on line 6 and line 9.
**Fix:** Remove line 6.

---

## 4. Summary Table

| # | File | Error | Fix |
|---|------|-------|-----|
| 1 | `cli/common.py` | `delete_interface()` without `interface_config_path` | Add import `config_path as interface_config_path` inside function |
| 2 | `cli/system_info_menu.py` | `sys` not imported | Add `import sys` at top of file |
| 3 | `views/qr_display.py` | `show_peer_selection` not imported | Add to imports from `..views.peer_views` |
| 4 | `views/log_views.py` | `FirewalldManager` + `confirm` not imported | Add both imports at top of file |
| 5 | `commands/peer_lifecycle.py` | `SystemDetector` not imported | Add to global imports |
| 6 | `commands/key_rotation.py` | Duplicate `import re` | Remove line 15 |
| 7 | `cli/logs_menu.py` | Duplicate `show_header_info` | Remove line 6 |

---

## 5. Fix Order (max 3 steps per task)

### Step 1: Fix `cli/common.py`
- In `delete_interface()` add `from ..wireguard.interfaces import config_path as interface_config_path`

### Step 2: Fix `cli/system_info_menu.py`
- Add `import sys` at top of file

### Step 3: Fix remaining 5 files
- `views/qr_display.py` → add `show_peer_selection`
- `views/log_views.py` → add `FirewalldManager` and `confirm`
- `commands/peer_lifecycle.py` → add `SystemDetector`
- `commands/key_rotation.py` → remove duplicate `import re`
- `cli/logs_menu.py` → remove duplicate `show_header_info`

---

## 6. Acceptance Criteria

1. ✅ `Delete selected interface` (select `di` in manage interfaces) — does not crash
2. ✅ `System Information` (select 5 in main menu) — does not crash
3. ✅ `Show QR code` (select 11 in peers menu) — does not crash
4. ✅ `Firewall status` (select 1 in diagnostics) — does not crash
5. ✅ `Clear logs` (select 2 in logs menu) — does not crash
6. ✅ `pytest` — 58/58 passed without errors