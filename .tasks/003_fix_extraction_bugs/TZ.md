# TZ: Fixing System Auto-Extraction Errors After cli.py Refactoring

## 1. Problem

After the previous fix `WireGuardInstaller` → `WireGuardManager` the application starts, but **crashes when selecting any submenu** (1 Servers, 2 Peers, 3 Firewall, etc.).

### Error #1 (current)

```
File "/root/loomwg/loom/cli/server_menu.py", line 19, in server_menu
    print(f"Server Menu (selected: {selected_interface()})\n")
NameError: name 'selected_interface' is not defined
```

### Root cause — auto-extractor system bug

The auto-extractor split `cli.py` into files, but made 2 mistakes:

#### Mistake A: Renamed imports from `common.py`

When importing functions from `common.py`, names got a `_as_xxx` suffix:
```python
# CURRENT CODE (BAD):
from ..cli.common import selected_interface as selected_wg
from ..cli.common import create_interface as _create_interface
from ..cli.common import pause as _pause
```

But inside the code the original name remains:
```python
# Inside function — original name (NameError!):
interface = selected_interface()    # ← does not exist!
_pause()                            # ← does not exist!
```

**Affected files:**
| File | What renamed | Where original name is used |
|------|--------------|----------------------------|
| `cli/server_menu.py` | `selected_interface as selected_wg` | lines 19, 39 |
| `commands/peer_crud.py` | `selected_interface as selected_wg` | lines 22, 42 (config_path) |
| `commands/peer_lifecycle.py` | `selected_interface as selected_wg` | lines 21, 34 (config_path) |
| `cli/common.py` | `create_interface as _create_interface` | line 59 |
| `cli/common.py` | `pause as _pause` | line 82 |
| `cli/common.py` | `set_selected_interface as _set_selected` | line 142 |

#### Mistake B: Did not carry Rich imports

The original `cli.py` had at the top of the file:
```python
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
```

But none of the 30 new files got these imports. Files use:
- `console.print()` — without `console = Console()` → **NameError**
- `Table.grid()`, `Table.add_column()` — without `from rich.table import Table` → **NameError**
- `Panel()` — without `from rich.panel import Panel` → **NameError**

**Affected files (all where Rich output exists):**

| File | What uses |
|------|-----------|
| `cli/router.py` | `console.print()` (line 53) |
| `cli/server_menu.py` | `console.print()` (lines 48, 51, 57, 60, 66, 69, 77, 80) |
| `cli/system_info_menu.py` | `console.print()`, `Table`, `Panel` (lines 23-29, 36, 45, 55, 74) |
| `commands/peer_crud.py` | `console.print()` |
| `commands/peer_lifecycle.py` | `console.print()` |
| `commands/peer_expiry.py` | `console.print()` |
| `commands/backup_commands.py` | `console.print()` |
| `commands/diagnostics_commands.py` | `console.print()` |
| `commands/firewall_commands.py` | `console.print()` |

#### Mistake C: Did not carry imports of called sub-functions

Menu files call functions defined in other modules, but imports were not added:

| Menu File | Calls function | Function must be imported from |
|-----------|---------------|--------------------------------|
| `server_menu.py` | `show_server_status()` | `views/server_status.py` |
| `server_menu.py` | `configure_server()` | `commands/configure_server.py` |
| `server_menu.py` | `show_server_config()` | (need to find) |
| `server_menu.py` | `remove_wireguard()` | `commands/lifecycle.py` |
| `server_menu.py` | `reinstall_wireguard()` | `commands/lifecycle.py` |
| `server_menu.py` | `rotate_server_keys()` | `commands/key_rotation.py` |
| `server_menu.py` | `manage_interfaces()` | (need to find) |
| `diagnostics_menu.py` | `run_full_diagnostics()` | `views/...` or commands |
| `diagnostics_menu.py` | `show_header_info()` | `cli/common.py` (already exists, but not imported!) |

---

## 2. Full List of All Errors by Files

### `cli/router.py`
| # | Problem | Line | Fix |
|---|---------|------|-----|
| 1 | `console.print()` without import | 53 | Add `from rich.console import Console` and `console = Console()` |

### `cli/server_menu.py`
| # | Problem | Line | Fix |
|---|---------|------|-----|
| 1 | `selected_interface()` but imported as `selected_wg` | 19, 39 | Remove `as selected_wg`, import as `selected_interface` |
| 2 | `console.print()` without import | 48, 51, 57, 60, 66, 69, 77, 80 | Add Rich imports + `console = Console()` |
| 3 | Submenu functions not imported | 41, 43, 45, 84, 86, 88, 90 | Add imports from respective modules |

### `cli/system_info_menu.py`
| # | Problem | Line | Fix |
|---|---------|------|-----|
| 1 | `console.print()`, `Table`, `Panel` without imports | 23-29, 36, 45, 55, 74 | Add Rich imports + `console = Console()` |
| 2 | `ServerConfig`, `FirewalldManager`, `ServiceManager`, `NetworkManager`, `PeerManager`, `_wg_runtime_dashboard` without imports | 32, 33, 35, 40, 41, 42, 43, 44 | Add missing imports |

### `cli/diagnostics_menu.py`
| # | Problem | Line | Fix |
|---|---------|------|-----|
| 1 | `show_header_info()` not imported from common | 13 | Add to import |
| 2 | Diagnostics functions (`run_full_diagnostics` etc.) not imported | 28-36 | Add imports |

### `commands/peer_crud.py`
| # | Problem | Line | Fix |
|---|---------|------|-----|
| 1 | `selected_interface()` but imported as `selected_wg` | 22 | Remove alias |
| 2 | `config_path()` but imported as `interface_config_path` | 42 | Remove alias |
| 3 | `console.print()` without import | (many) | Add Rich imports |

### `commands/peer_lifecycle.py`
| # | Problem | Line | Fix |
|---|---------|------|-----|
| 1 | `selected_interface()` but imported as `selected_wg` | 21 | Remove alias |
| 2 | `config_path()` but imported as `interface_config_path` | 34 | Remove alias |
| 3 | `console.print()` without import | (many) | Add Rich imports |

### `commands/peer_expiry.py`
| # | Problem | Line | Fix |
|---|---------|------|-----|
| 1 | `console.print()` without import | (many) | Add Rich imports |

### `commands/backup_commands.py`
| # | Problem | Line | Fix |
|---|---------|------|-----|
| 1 | `console.print()` without import | (many) | Add Rich imports |

### `commands/diagnostics_commands.py`
| # | Problem | Line | Fix |
|---|---------|------|-----|
| 1 | `console.print()` without import | (many) | Add Rich imports |

### `commands/firewall_commands.py`
| # | Problem | Line | Fix |
|---|---------|------|-----|
| 1 | `console.print()` without import | (many) | Add Rich imports |

### `views/server_status.py`
| # | Problem | Line | Fix |
|---|---------|------|-----|
| 1 | `config_path()` but imported as `interface_config_path` | 116 | Remove alias |

---

## 3. Error Classification

### Category A: `NameError` — aliased imports (template bug of auto-extractor)
Import: `from ..cli.common import foo as bar`
Code: `foo()` → **NameError: name 'foo' is not defined**

**Files:** `server_menu.py`, `peer_crud.py`, `peer_lifecycle.py`, `common.py`, `server_status.py`

### Category B: `NameError` — console/Table/Panel without imports
Code: `console.print()` but `Console` not imported

**Files:** `router.py`, `server_menu.py`, `system_info_menu.py`, `peer_crud.py`, `peer_lifecycle.py`, `peer_expiry.py`, `backup_commands.py`, `diagnostics_commands.py`, `firewall_commands.py`

### Category C: `NameError` — sub-functions not imported
Menu file calls a function that must be imported from another module

**Files:** `server_menu.py`, `diagnostics_menu.py`

---

## 4. Fix Order

### Step 1: Fix all aliases (`selected_interface as selected_wg` → `selected_interface`)

**Files:**
- `cli/server_menu.py` — line 8: remove `as selected_wg`, replace 2 uses (lines 19, 39)
- `commands/peer_crud.py` — line 8: remove `as selected_wg`, replace 1 use (line 22)
- `commands/peer_crud.py` — line 9: remove `as interface_config_path`, replace 1 use (line 42)
- `commands/peer_lifecycle.py` — line 8: remove `as selected_wg`, replace 1 use (line 21)
- `commands/peer_lifecycle.py` — line 9: remove `as interface_config_path`, replace 1 use (line 34)
- `cli/common.py` — line 36: remove `as _create_interface`, replace 1 use (line 59)
- `cli/common.py` — line 37: remove `as _pause`, replace 1 use (line 82)
- `cli/common.py` — line 35: remove `as _set_selected`, replace 1 use (line 142)
- `views/server_status.py` — line 5: remove `as interface_config_path`, replace 1 use (line 116)

### Step 2: Add Rich imports (`Console`, `Table`, `Panel`)

**Files (9 files):**
- `cli/router.py` → add `from rich.console import Console` + `console = Console()`
- `cli/server_menu.py` → add `from rich.console import Console` + `console = Console()`
- `cli/system_info_menu.py` → add `from rich.console import Console` + `from rich.panel import Panel` + `from rich.table import Table` + `console = Console()`
- `commands/peer_crud.py` → add Rich imports
- `commands/peer_lifecycle.py` → add Rich imports
- `commands/peer_expiry.py` → add Rich imports
- `commands/backup_commands.py` → add Rich imports
- `commands/diagnostics_commands.py` → add Rich imports
- `commands/firewall_commands.py` → add Rich imports

### Step 3: Add sub-function imports

**`cli/server_menu.py`:**
```python
from ..views.server_status import show_server_status
from ..commands.configure_server import configure_server
from ..commands.lifecycle import remove_wireguard, reinstall_wireguard
from ..commands.key_rotation import rotate_server_keys
from .server_menu import manage_interfaces  # or wherever
```

**`cli/diagnostics_menu.py`:**
```python
from ..cli.common import show_header_info  # ← already exists! need to check
from ..views.diagnostic_views import (
    run_full_diagnostics,
    run_system_diagnostics,
    run_network_diagnostics,
    run_wireguard_diagnostics,
    run_firewall_diagnostics,
)
```

### Step 4: Add missing imports to `system_info_menu.py`

```python
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..wireguard.server_config import ServerConfig
from ..wireguard.interfaces import config_path as interface_config_path
from ..diagnostics.firewall import FirewalldManager
from ..system.network import NetworkManager
from ..system.services import ServiceManager
from ..wireguard.peer_manager import PeerManager
from ..views.server_status import _wg_runtime_dashboard
```

### Step 5: `pytest`
Ensure 58/58 pass.

---

## 5. Summary Table

| Category | File Count | Lines | Complexity |
|----------|-----------|-------|------------|
| A: Aliases | 7 files | ~15 lines | Low |
| B: Rich Imports | 9 files | ~27 lines | Low |
| C: Sub-functions | 2 files | ~10 lines | Medium |
| D: system_info_menu | 1 file | ~15 lines | Medium |
| **Total** | **~11 files** | **~67 lines** | **Low-Medium** |

## 6. Acceptance Criteria

1. ✅ Selecting option 1 (Servers) in main menu — does not crash
2. ✅ Selecting option 2 (Peers) in main menu — does not crash
3. ✅ Any submenu — does not crash
4. ✅ `pytest` — 58/58 passed
5. ✅ No `NameError` on any path through menu