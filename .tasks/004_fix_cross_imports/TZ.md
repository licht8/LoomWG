# TZ: Fixing Cross-Imports and Missing Imports

## 1. Problem

The application starts, but **crashes when performing any actions** (creating config, creating peer, deleting, etc.) due to `NameError: name 'xxx' is not defined`.

**Root:** Auto-extraction split functions into files, but **did not add cross-imports** — functions call other functions from other files, but did not import them. Also there is a bug: some files import `config_path as interface_config_path`, but the code inside uses `config_path()`.

---

## 2. Full Error List

### 2.1. `commands/configure_server.py`

**Error:** Calls `install_wireguard()` (line 40) — function from `install_wireguard.py`, not imported.

**Additionally:** File imports `config_path as interface_config_path` (line 18), but **never calls** `interface_config_path()` — this is OK (the `config_path` function is not called directly).

**Fix:** Add import `install_wireguard` from `commands/install_wireguard.py`.

### 2.2. `commands/install_wireguard.py`

**Error:** Calls `prompt_server_config()` (line 74) and `validate_server_settings()` (line 76) — functions from `configure_server.py`, not imported.

**Fix:** Add import from `commands/configure_server.py`:
```python
from ..commands.configure_server import prompt_server_config, validate_server_settings
```

### 2.3. `commands/lifecycle.py`

**Error:** `reinstall_wireguard()` calls `install_wireguard()` (line 38) — function from `install_wireguard.py`, not imported.

**Fix:** Add import:
```python
from ..commands.install_wireguard import install_wireguard
```

### 2.4. `commands/peer_crud.py`

**Error:** `config_path` is imported as `from ..wireguard.interfaces import config_path` (line 14), but used as function `interface_config_path()` (lines 42, 144) — **name does not match!**

Code: `config_path = interface_config_path(interface)` → NameError: `interface_config_path` is not defined.

**Fix:** Change import to:
```python
from ..wireguard.interfaces import config_path as interface_config_path
```

**Also:** `SystemDetector` is not imported:
```python
from ..system.info import SystemDetector
```

### 2.5. `commands/peer_lifecycle.py`

**Error:** `config_path` is imported as `from ..wireguard.interfaces import config_path` (line 17), but used as `interface_config_path()` (lines 37, 85, 133, 193).

**Fix:** Change import to:
```python
from ..wireguard.interfaces import config_path as interface_config_path
```

**Also:** `show_peer_selection()` is used (lines 28, 64, 114, 172) — not imported. Must come from `views.peer_views`.

**Fix:** Add import:
```python
from ..views.peer_views import show_peer_selection
```

### 2.6. `commands/peer_expiry.py`

**Double import:** Lines 2-13 and 15-20 — complete content duplicate!

**Error 1:** `show_peer_selection()` is used (lines 46, 68) — not imported.

**Error 2:** `WireGuardManager` is used (line 34) — not imported.

**Error 3:** `ConfigGenerator` is used (lines 25, 36) — not imported.

**Fix:**
```python
from ..wireguard.manager import WireGuardManager
from ..wireguard.config_generator import ConfigGenerator
from ..views.peer_views import show_peer_selection
```

### 2.7. `commands/peer_import.py`

**Error:** `SystemDetector` is used (line 25) — not imported.

**Error:** `Peer` is used (line 81) — not imported.

**Fix:** Add:
```python
from ..system.info import SystemDetector
from ..wireguard.peer_manager import Peer
```

### 2.8. `commands/backup_commands.py`

**Double import:** Lines 2-12 and 14-21 — complete content duplicate!

No critical errors — all imports are in place, just code duplicate.

### 2.9. `commands/diagnostics_commands.py`

**Double import:** Lines 2-15 and 17-27 — complete content duplicate!

No critical errors — just code duplicate.

### 2.10. `commands/firewall_commands.py`

**Double import:** Lines 2-12 and 14-21 — complete content duplicate!

No critical errors — just code duplicate.

### 2.11. `cli/system_info_menu.py`

**Missing imports:**
| Name | Line | Where used |
|------|------|------------|
| `Table` | 36 | `Table.grid()` |
| `ServerConfig` | 45 | `ServerConfig.from_file()` |
| `FirewalldManager` | 53 | `firewall.is_installed()` |
| `NetworkManager` | 53 | `NetworkManager().is_ipv4_forwarding_enabled()` |
| `ServiceManager` | 55 | `ServiceManager().is_active()` |
| `PeerManager` | 57 | `PeerManager().list_peers()` |
| `_wg_runtime_dashboard` | 48 | `_wg_runtime_dashboard()` |
| `Panel` | 55 | `Panel(details, ...)` |

**Fix:** Add at top of file:
```python
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..wireguard.server_config import ServerConfig
from ..firewall.firewalld import FirewalldManager
from ..system.network import NetworkManager
from ..system.services import ServiceManager
from ..wireguard.peer_manager import PeerManager
from ..wireguard.manager import WireGuardManager
from ..views.server_status import _wg_runtime_dashboard

console = Console()
```

### 2.12. `cli/peers_menu.py`

**Error:** `show_peer()` is called (line 58) — not imported. Must come from `views.peer_views`.

**Fix:** Add to import:
```python
from ..views.peer_views import list_peers, peer_table, show_peer_selection, show_peer
```

### 2.13. `cli/firewall_menu.py`

**Error:** `show_firewall_status` is imported from `..views.log_views` (line 5), but the name `show_firewall_status` probably lives in `views.backup_views` or another view module. Need to check actual location.

**Fix:** Check where `show_firewall_status()` is defined, and fix import.

### 2.14. `cli/common.py`

**Function `manage_interfaces()`:** Called from `server_menu.py` (line 99), defined in `common.py` (restored from _Trash). Check that imports inside it are correct.

---

## 3. Summary Table of All Fixes

### Critical (NameError, block work):

| File | What to fix | Lines |
|------|--------------|--------|
| `commands/configure_server.py` | Add `from ..commands.install_wireguard import install_wireguard` | ~1 |
| `commands/install_wireguard.py` | Add `from ..commands.configure_server import prompt_server_config, validate_server_settings` | ~1 |
| `commands/lifecycle.py` | Add `from ..commands.install_wireguard import install_wireguard` | ~1 |
| `commands/peer_crud.py` | `config_path` → `config_path as interface_config_path`, add `SystemDetector` | ~2 |
| `commands/peer_lifecycle.py` | `config_path` → `config_path as interface_config_path`, add `show_peer_selection` from views | ~2 |
| `commands/peer_expiry.py` | Remove import duplicate, add `WireGuardManager`, `ConfigGenerator`, `show_peer_selection` | ~5 |
| `commands/peer_import.py` | Add `SystemDetector`, `Peer` | ~2 |
| `cli/system_info_menu.py` | Add 8 missing imports (Table, Panel, ServerConfig, FirewalldManager, NetworkManager, ServiceManager, PeerManager, _wg_runtime_dashboard) | ~8 |
| `cli/peers_menu.py` | Add `show_peer` to import from views | ~1 |
| `cli/firewall_menu.py` | Fix import `show_firewall_status` (probably should be from another module) | ~1 |

### Non-critical (duplicates, but do not block):

| File | Problem | Fix |
|------|---------|-----|
| `commands/backup_commands.py` | Import duplicate (lines 2-12 and 14-21) | Remove duplicate |
| `commands/diagnostics_commands.py` | Import duplicate (lines 2-15 and 17-27) | Remove duplicate |
| `commands/firewall_commands.py` | Import duplicate (lines 2-12 and 14-21) | Remove duplicate |

---

## 4. Fix Order

### Step 1: Cross-imports between commands (blocks config creation)
- `configure_server.py` → add `install_wireguard`
- `install_wireguard.py` → add `prompt_server_config`, `validate_server_settings`
- `lifecycle.py` → add `install_wireguard`

### Step 2: Cross-imports in commands (blocks peer work)
- `peer_crud.py` → fix `config_path`, add `SystemDetector`
- `peer_lifecycle.py` → fix `config_path`, add `show_peer_selection`
- `peer_expiry.py` → remove duplicate, add `WireGuardManager`, `ConfigGenerator`, `show_peer_selection`
- `peer_import.py` → add `SystemDetector`, `Peer`

### Step 3: CLI-menus (blocks menu display)
- `system_info_menu.py` → add 8 imports
- `peers_menu.py` → add `show_peer`
- `firewall_menu.py` → fix import

### Step 4: Remove import duplicates
- `backup_commands.py` — remove lines 14-21
- `diagnostics_commands.py` — remove lines 17-27
- `firewall_commands.py` — remove lines 14-21

### Step 5: `pytest`
Ensure 58/58 pass.

---

## 5. Acceptance Criteria

1. ✅ `configure_server()` works without `NameError`
2. ✅ `install_wireguard()` works without `NameError`
3. ✅ `create_peer()` works without `NameError`
4. ✅ `enable_peer()` / `disable_peer()` work without `NameError`
5. ✅ `system_info_menu()` does not crash
6. ✅ `pytest` — 58/58 passed
7. ✅ No import duplicates