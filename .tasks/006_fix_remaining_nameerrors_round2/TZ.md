# ТЗ: Полный аудит отсутствующих импортов — раунд 006

## 1. Проблема

Авто-экстрактор разделил `cli.py` (2604 строки) на ~30 файлов, но **не перенёс все импорты** для каждого файла. Функции используют имена из соседних модулей без соответствующих `import`.

---

## 2. Полный аудит — все файлы

Проверено 60+ `.py` файлов. Найденные ошибки:

### 2.1. `cli/common.py` — `delete_interface()` без `interface_config_path`

**Проблема:** Строка 344:
```python
def delete_interface() -> None:
    from ..wireguard.manager import WireGuardManager
    from ..system.services import ServiceManager
    from ..logging_system.logger import LoomLogger
    # ^^^^^^ нет interface_config_path!
    path = interface_config_path(interface)  # ← NameError!
```

`interface_config_path` импортирован внутри `create_interface()` (строка 71-75), но **не в `delete_interface()`**.

**Исправление:** Добавить в начало `delete_interface()` (после строки 336):
```python
from ..wireguard.interfaces import config_path as interface_config_path
```

---

### 2.2. `cli/system_info_menu.py` — отсутствует `import sys`

**Проблема:** Строка 57:
```python
section("LoomWG", [
    ("Version", "0.1.0"),
    ("Python", sys.version.split()[0]),  # ← sys не импортирован
    ("Executable", sys.executable),
    ...
])
```

В начале файла есть `import subprocess` и `from pathlib import Path`, но **нет `import sys`**.

**Исправление:** Добавить после строки 5:
```python
import sys
```

---

### 2.3. `views/qr_display.py` — дубликат файла + пропущенный `show_peer_selection`

**Проблема:** Файл содержит **два полных дубликата** (строки 1-30 и 31-61). `show_peer_selection` вызывается на строке 15, но не импортирована.

**Исправление:** Полностью перезаписать файл:
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

### 2.4. `views/log_views.py` — отсутствуют `FirewalldManager` и `confirm`

**Проблема:** 
- Строка 20: `firewall = FirewalldManager()` — класс не импортирован.
- Строка 88: `if confirm("Clear all logs?"):` — функция не импортирована.

Текущий импорт (строка 9):
```python
from ..cli.common import clear_screen, section_banner, pause
```

**Исправление:** Добавить в начало файла:
```python
from ..firewall.firewalld import FirewalldManager
from ..cli.common import clear_screen, section_banner, pause, confirm
```

**Полный заголовок файла:**
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

### 2.5. `cli/logs_menu.py` — дубликат импорта `show_header_info`

**Проблема:** `show_header_info` импортирован дважды — строка 6 и строка 9.

**Исправление:** Убрать строку 6 (оставить только строку 9):
```python
# Удалить: from ..cli.common import show_header_info
```

---

### 2.6. `commands/key_rotation.py` — дубликат `import re`

**Проблема:** `import re` на строках 3 и 16.

**Исправление:** Удалить один из них (строка 3).

---

### 2.7. `commands/peer_lifecycle.py` — `SystemDetector` не импортирован

**Проблема:** Строка 248:
```python
server_endpoint=SystemDetector().detect().public_ip or "YOUR_SERVER_IP",
```
`SystemDetector` не импортирован в файле.

**Исправление:** Добавить в начало файла (строка 19):
```python
from ..system.info import SystemDetector
```

---

## 3. Сводная таблица

| # | Файл | Проблема | Исправление |
|---|------|----------|-------------|
| 1 | `cli/common.py:344` | `interface_config_path` не импортирован в `delete_interface()` | Добавить `from ..wireguard.interfaces import config_path as interface_config_path` |
| 2 | `cli/system_info_menu.py:57` | `sys` не импортирован | Добавить `import sys` |
| 3 | `views/qr_display.py` | `show_peer_selection` не импортирована + дубликат файла | Добавить импорт + удалить дубликат |
| 4 | `views/log_views.py` | `FirewalldManager` и `confirm` не импортированы | Добавить оба импорта |
| 5 | `cli/logs_menu.py` | `show_header_info` импортирован дважды | Убрать дубликат |
| 6 | `commands/key_rotation.py` | `import re` на строках 3 и 16 | Удалить один |
| 7 | `commands/peer_lifecycle.py:248` | `SystemDetector` не импортирован | Добавить `from ..system.info import SystemDetector` |

---

## 4. Порядок исправления

### Шаг 1: Исправить `cli/common.py`
- Добавить `interface_config_path` в `delete_interface()`

### Шаг 2: Исправить `cli/system_info_menu.py`
- Добавить `import sys`

### Шаг 3: Исправить `views/qr_display.py`
- Полный редизайн (удалить дубликат, добавить импорт)

### Шаг 4: Исправить `views/log_views.py`
- Добавить `FirewalldManager` и `confirm`

### Шаг 5: Убрать дубликаты
- `cli/logs_menu.py:6` — удалить `from ..cli.common import show_header_info`
- `commands/key_rotation.py:3` — удалить `import re`
- `commands/peer_lifecycle.py` — добавить `SystemDetector`

### Шаг 6: `pytest`
Убедиться что 58/58 проходят.

---

## 5. Критерии приёмки

1. ✅ `Delete selected interface` (выбор `di` в manage_interfaces) — не падает на NameError
2. ✅ `System Information` (выбор 5 в main menu) — не падает на NameError sys
3. ✅ `Show QR code` (выбор 11 в peers_menu) — не падает на NameError show_peer_selection
4. ✅ `Firewall status` (выбор 1 в diagnostics_menu) — не падает на NameError FirewalldManager
5. ✅ `Clear logs` (выбор 2 в logs_menu) — не падает на NameError confirm
6. ✅ `Rotate peer keys` — не падает на NameError SystemDetector
7. ✅ `pytest` — 58/58 passed