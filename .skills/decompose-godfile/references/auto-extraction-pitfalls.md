# Auto-Extraction Pitfalls: Real Error Transcripts

## Pattern 1: Aliased Imports

**Symptom:** `NameError: name 'selected_interface' is not defined`

**Cause:** Auto-extractor added `as xxx` aliases:
```python
# BROKEN (what extractor produced):
from ..cli.common import selected_interface as selected_wg
from ..cli.common import pause as _pause
from ..cli.common import create_interface as _create_interface
```

But code body still uses original names:
```python
interface = selected_interface()  # ← NameError! selected_wg exists, not selected_interface
_pause()  # ← NameError!
```

**Fix:** Remove all aliases, verify every usage matches import.
```python
# CORRECT:
from ..cli.common import selected_interface, pause, create_interface
```

**Files affected:** `server_menu.py`, `peer_crud.py`, `peer_lifecycle.py`, `common.py`

---

## Pattern 2: Missing Rich Imports

**Symptom:** `NameError: name 'console' is not defined` or `NameError: name 'Table' is not defined`

**Cause:** Original `cli.py` had module-level imports:
```python
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
console = Console()
```

Auto-extractor did NOT propagate these to new files.

**Fix:** Add to every file using Rich:
```python
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
console = Console()
```

**Files affected:** `router.py`, `server_menu.py`, `system_info_menu.py`, all menu files, all command files that print.

---

## Pattern 3: Wrong Import Paths

**Symptom:** `ImportError: cannot import name 'FirewalldManager' from 'loom.diagnostics.firewall'`

**Cause:** Auto-extractor guessed wrong module paths.

**Examples:**
```python
# WRONG:
from ..diagnostics.firewall import FirewalldManager
from ..wireguard.interfaces import selected_interface

# CORRECT:
from ..firewall.firewalld import FirewalldManager
from ..cli.common import selected_interface
```

**Fix:** Always search for class/function definitions:
```bash
grep -rn "class FirewalldManager" loom/
grep -rn "def selected_interface" loom/
```

---

## Pattern 4: Lost Functions

**Symptom:** `NameError: name 'manage_interfaces' is not defined`

**Cause:** Functions with complex bodies (>50 lines) or nested structures may be skipped by auto-extraction scripts.

**Fix:** Compare file count in backup vs new structure. If a function is called but not defined, extract it from backup manually.

---

## Pattern 5: Circular Self-Imports

**Symptom:** `ImportError: cannot import name 'create_interface' from 'loom.cli.common'` (importing from itself)

**Cause:** Function body imports another function from the same module:
```python
def select_interface():
    from ..cli.common import create_interface  # ← Self-import!
```

**Fix:** Define functions at module top-level, use direct calls or move related functions to separate module.

---

## Quick Diagnostic Checklist

When refactoring fails after extraction, run this sequence:

1. **Check aliased imports:**
   ```bash
   grep -rn "import.*as " loom/cli/ loom/commands/ loom/views/
   ```
   Remove all aliases, verify usage.

2. **Check Rich imports:**
   ```bash
   grep -rn "console\." loom/ | grep -v "from rich"
   ```
   Every file in this output needs `from rich.console import Console` + `console = Console()`.

3. **Check wrong paths:**
   ```bash
   grep -rn "class FirewalldManager" loom/
   grep -rn "def selected_interface" loom/
   ```
   Compare import paths against actual definitions.

4. **Check lost functions:**
   ```bash
   # From backup, grep for all def statements
   grep -rn "^def " _Trash/2026-09-04_cli.py.bak > /tmp/backup_defs.txt
   grep -rn "^def " loom/ > /tmp/new_defs.txt
   diff /tmp/backup_defs.txt /tmp/new_defs.txt
   ```

5. **Check circular imports:**
   ```bash
   python -c "import loom" 2>&1 | grep -i circular
   ```