# TZ: Full Import Audit — Round 006

## 1. Problem

The auto-extractor split `cli.py` (2604 lines) into ~30 files, but **did not carry all imports** for each file. Functions use names from neighboring modules without corresponding `import`.

---

## 2. Full Audit — All Files

Checked 60+ `.py` files. Found errors:

### 2.1. `cli/common.py` — `delete_interface()` without `interface_config_path`

**Problem:** Line 344:
```python
def delete_interface() -> None:
    from ..wireguard.manager import WireGuardManager
    from ..system.services import ServiceManager
    from ..logging_system.logger import LoomLogger
    # ^^^^^^ no interface_config_path!
    path = interface_config_path(interface)  # ← NameError!
```

`interface_config_path` is imported inside `create_interface()` (lines 71-75), but **not in `delete_interface()`**.

**Fix:** Add at top of `delete_interface()` (after line 336):
```python
from ..wireguard.interfaces import config_path as interface_config_path
```

---

### 2.2. `cli/system_info_menu.py` — Missing `import sys`

**Problem:** Line 57:
```python
section("LoomWG", [
    ("Version", "0.1.0"),
    ("Python", sys.version.split()[0]),  # ← sys not imported
    ("Executable", sys.executable),
    ...
])
```

At top of file there is `import subprocess` and `from pathlib import Path`, but **no `import sys`**.

**Fix:** Add after line 5:
```python
import sys
```

---

### 2.3. `views/qr_display.py` — File Duplicate + Missing `show_peer_selection`

**Problem:** File contains **two full duplicates** (lines 1-30 and 31-61). `show_peer_selection` is called on line 15, but not imported.

**Fix:** Completely rewrite file:
```python
"""View functions for QR code display."""
from rich.console import Console

from ..wireguard.client_config import ClientConfigStore
from ..wireguard.peer_manager import PeerManager
from ..wireguard.config_generator import ConfigGenerator
from ..cli.common import clear_screen, display_peer_qr_code, pause, section_banner
from ..views.peer_views import show_peer_selection

console = Console()


def show_qr_code() -> None:
    """Display a saved peer config as a terminal QR code."""
    clear_screen()
    section_banner("Show QR Code", "Display a saved peer configuration as QR code")

    peer_mgr = PeerManager()
    show_peer_selection(peer_mgr)
    name = input("Peer name: ").strip()
    if not name:
        return
    peer = peer_mgr.get_peer(name)
    if not peer:
        console.print("[red]Peer not found[/red]")
        pause()
        return
    config_path = ClientConfigStore().base_dir / f"{name}.conf"
    if not config_path.exists():
        console.print("[yellow]No saved client config exists for this peer.[/yellow]")
        pause()
        return
    display_peer_qr_code(name, config_path.read_text(encoding="utf-8"))
    pause()
```

---

### 2.4. `views/log_views.py` — Missing `FirewalldManager` and `confirm`

**Problem:**
- Line 20: `firewall = FirewalldManager()` — class not imported.
- Line 88: `if confirm("Clear all logs?"):` — function not imported.

Current import (line 9):
```python
from ..cli.common import clear_screen, section_banner, pause
```

**Fix:** Add at top of file:
```python
from ..firewall.firewalld import FirewalldManager
from ..cli.common import clear_screen, section_banner, pause, confirm
```

**Full file header:**
```python
"""Auto-extracted from cli/__init__.py"""
import re
from pathlib import Path

from rich.console import Console
from rich.table import Table

from ..logging_system.logger import LoomLogger
from ..cli.common import clear_screen, section_banner, pause, confirm
from ..wireguard.manager import WireGuardManager
from ..wireguard.server_config import ServerConfig
from ..firewall.firewalld import FirewalldManager

console = Console()
```

---

### 2.5. `cli/logs_menu.py` — Duplicate Import `show_header_info`

**Problem:** `show_header_info` is imported twice — line 6 and line 9.

**Fix:** Remove line 6 (keep only line 9):
```python
# Remove: from ..cli.common import show_header_info
```

---

### 2.6. `commands/key_rotation.py` — Duplicate `import re`

**Problem:** `import re` on lines 3 and 16.

**Fix:** Remove one of them (line 3).

---

### 2.7. `commands/peer_lifecycle.py` — `SystemDetector` Not Imported

**Problem:** Line 248:
```python
server_endpoint=SystemDetector().detect().public_ip or "YOUR_SERVER_IP",
```
`SystemDetector` is not imported in the file.

**Fix:** Add at top of file (line 19):
```python
from ..system.info import SystemDetector
```

---

## 3. Summary Table

| # | File | Problem | Fix |
|---|------|---------|-----|
| 1 | `cli/common.py:344` | `interface_config_path` not imported in `delete_interface()` | Add `from ..wireguard.interfaces import config_path as interface_config_path` |
| 2 | `cli/system_info_menu.py:57` | `sys` not imported | Add `import sys` |
| 3 | `views/qr_display.py` | `show_peer_selection` not imported + file duplicate | Add import + remove duplicate |
| 4 | `views/log_views.py` | `FirewalldManager` and `confirm` not imported | Add both imports |
| 5 | `cli/logs_menu.py` | `show_header_info` imported twice | Remove duplicate |
| 6 | `commands/key_rotation.py` | `import re` on lines 3 and 16 | Remove one |
| 7 | `commands/peer_lifecycle.py:248` | `SystemDetector` not imported | Add `from ..system.info import SystemDetector` |

---

## 4. Fix Order

### Step 1: Fix `cli/common.py`
- Add `interface_config_path` to `delete_interface()`

### Step 2: Fix `cli/system_info_menu.py`
- Add `import sys`

### Step 3: Fix `views/qr_display.py`
- Complete redesign (remove duplicate, add import)

### Step 4: Fix `views/log_views.py`
- Add `FirewalldManager` and `confirm`

### Step 5: Remove duplicates
- `cli/logs_menu.py:6` — remove `from ..cli.common import show_header_info`
- `commands/key_rotation.py:3` — remove `import re`
- `commands/peer_lifecycle.py` — add `SystemDetector`

### Step 6: `pytest`
Ensure 58/58 pass.

---

## 5. Acceptance Criteria

1. ✅ `Delete selected interface` (select `di` in manage_interfaces) — does not crash on NameError
2. ✅ `System Information` (select 5 in main menu) — does not crash on NameError sys
3. ✅ `Show QR code` (select 11 in peers_menu) — does not crash on NameError show_peer_selection
4. ✅ `Firewall status` (select 1 in diagnostics_menu) — does not crash on NameError FirewalldManager
5. ✅ `Clear logs` (select 2 in logs_menu) — does not crash on NameError confirm
6. ✅ `Rotate peer keys` — does not crash on NameError SystemDetector
7. ✅ `pytest` — 58/58 passed