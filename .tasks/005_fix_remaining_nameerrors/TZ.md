# TZ: Fixing Remaining NameError After Refactoring

## 1. Problem

The application starts, but **crashes when performing specific actions**:
- `View configuration` → `NameError: name 'pause' is not defined`
- `Remove WireGuard` → `UnicodeDecodeError` + `NameError: name 'confirm' is not defined`
- `Manage interfaces` → `NameError: name 'configured_interfaces' is not defined`
- `Create peer` → `NameError: name 'console' is not defined`
- `Remove peer` → `NameError: name 'console' is not defined`

**Root:** The auto-extractor split functions into files, but did not carry all imports for each file. Partial imports of Rich, `pause`, `confirm`, `configured_interfaces`.

---

## 2. Full Error List

### 2.1. `commands/peer_crud.py` — Missing `console = Console()`

**Problem:** File uses `console.print()` (lines 32, 36, 62, 66, 70, 78, 95, 113, 115, 117, 119, 123, 133, 142, 167, 169, 171, 179) — but **never defined** `console = Console()`.

Line 17 imports from common: `from ..cli.common import clear_screen, section_banner, pause, confirm, selected_interface, prompt_for_qr_code, display_peer_qr_code` — but **does not import Rich**.

**Fix:** Add at top of file (after line 1):
```python
from rich.console import Console
console = Console()
```

**Important:** Do not use `from ..cli.common import console` — this would create a circular import, since `common.py` may import functions from `peer_crud.py`.

---

### 2.2. `commands/peer_lifecycle.py` — Missing `console = Console()`

**Problem:** Line 6 imports `from rich.console import Console` and line 7 `from rich.panel import Panel` — but **nowhere is `console = Console()`**.

File uses `console.print()` (lines 43, 47, 50, 73, 77, 81, 91, 98, 101, 118, 122, 127, 148, 156, 159, 176, 180, 184, 259, 271, 274, 298, 304, 309, 312).

**Fix:** Add after line 8:
```python
console = Console()
```

---

### 2.3. `commands/peer_import.py` — All Rich Imports Missing

**Problem:** Line 94 uses `console.print()` — but file does not import Rich at all.

**Fix:** Add at top of file (after line 1):
```python
from rich.console import Console
console = Console()
```

---

### 2.4. `views/server_status.py` — Missing `pause` and `console`

**Problem:**
- `show_server_config()` (lines 137, 147) calls `pause()` — not imported.
- `show_server_config()` uses `console.print()` (lines 136, 142, 145) — `console` not defined.

**Fix:** Add at top of file:
```python
from rich.console import Console
console = Console()

from ..cli.common import pause
```

---

### 2.5. `cli/common.py` — Function `manage_interfaces()` Uses `configured_interfaces()` Without Import

**Problem:** Line 280: `interfaces = configured_interfaces()` — but `configured_interfaces` is not imported into `manage_interfaces()` scope.

**Fix:** Add at top of `manage_interfaces()`:
```python
from ..wireguard.interfaces import configured_interfaces
```

OR add to global imports of file (at top of `common.py`).

---

### 2.6. `commands/lifecycle.py` — `confirm()` Not Imported

**Problem:** Line 17 in `remove_wireguard()` calls `confirm("Continue with removal?")` — but `confirm` is not imported.

Line 6: `from ..cli.common import clear_screen, section_banner, pause, confirm` — **already imported!**

This means the problem is not `confirm` in this file. The problem is the user's message: `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd1`. This is a terminal I/O bug — `confirm()` receives bytes instead of strings. But then a `NameError: name 'confirm' is not defined` occurs — this is **another** file.

Checking: error comes from `lifecycle.py:18`. Import at line 6 exists. So the problem is not in lifecycle.py.

Re-reading error: `File "/root/loomwg/loom/commands/lifecycle.py", line 18, in remove_wireguard → if confirm("Continue with removal?"):`. Confirm import exists at line 6. So the problem is that confirm() is called from another context.

No — re-reading: error **after** `UnicodeDecodeError`. First `confirm()` works, receives incorrect input (byte 0xd1), throws `UnicodeDecodeError`. Then **during exception handling** a new `NameError` occurs — but in which file?

Re-reading traceback:
```
File "lifecycle.py", line 18, in remove_wireguard
    if confirm("Continue with removal?"):
File "common.py", line 169, in confirm
    response = input(...).strip().lower()
UnicodeDecodeError
```

So the problem is in `confirm()` in `common.py` — it crashes on input with wrong encoding. This is not a NameError, it's a UnicodeDecodeError. This is an input processing bug — `confirm()` should not crash on non-UTF8 input.

**Fix:** Add try/except to `confirm()`:
```python
def confirm(prompt: str = "Continue?") -> bool:
    """Ask for confirmation."""
    while True:
        try:
            response = input(f"\n{prompt} (y/n): ").strip().lower()
        except (UnicodeDecodeError, EOFError, OSError):
            print("\nInvalid response.")
            continue
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        print("Invalid response. Please enter 'y' or 'n'.")
```

---

## 3. Summary Table

| # | File | Problem | Fix |
|---|------|---------|-----|
| 1 | `commands/peer_crud.py` | No `console = Console()` | Add `from rich.console import Console` + `console = Console()` at top |
| 2 | `commands/peer_lifecycle.py` | No `console = Console()` | Add `console = Console()` after line 8 |
| 3 | `commands/peer_import.py` | No Rich imports | Add `from rich.console import Console` + `console = Console()` at top |
| 4 | `views/server_status.py` | No `pause` and `console` | Add `from rich.console import Console` + `console = Console()` + `from ..cli.common import pause` |
| 5 | `cli/common.py` | `manage_interfaces()` without `configured_interfaces` | Add `from ..wireguard.interfaces import configured_interfaces` at top of file |
| 6 | `cli/common.py` | `confirm()` crashes on UnicodeDecodeError | Add try/except in `confirm()` |

---

## 4. Fix Order

### Step 1: Add `console = Console()` to 3 command files
- `commands/peer_crud.py` — add Rich import + console
- `commands/peer_lifecycle.py` — add `console = Console()`
- `commands/peer_import.py` — add Rich import + console

### Step 2: Add `pause` + `console` to views
- `views/server_status.py` — add `pause` and `console`

### Step 3: Fix `common.py`
- Add `configured_interfaces` to `manage_interfaces()`
- Add `try/except` in `confirm()` for UnicodeDecodeError

### Step 4: `pytest`
Ensure 58/58 pass.

---

## 5. Acceptance Criteria

1. ✅ `View configuration` (select 3 in server_menu) — does not crash
2. ✅ `Remove WireGuard` (select 8 in server_menu) — does not crash on UnicodeDecodeError
3. ✅ `Manage interfaces` (select 11 in server_menu) — does not crash
4. ✅ `Create peer` — does not crash on `console.print`
5. ✅ `Remove peer` — does not crash on `console.print`
6. ✅ `pytest` — 58/58 passed