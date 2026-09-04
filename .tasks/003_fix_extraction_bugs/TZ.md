# ТЗ: Исправление системных ошибок авто-экстракции после рефакторинга cli.py

## 1. Суть проблемы

После предыдущего исправления `WireGuardInstaller` → `WireGuardManager` приложение запускается, но **падает при выборе любого подменю** (1 Servers, 2 Peers, 3 Firewall и т.д.).

### Ошибка №1 (текущая)

```
File "/root/loomwg/loom/cli/server_menu.py", line 19, in server_menu
    print(f"Server Menu (selected: {selected_interface()})\n")
NameError: name 'selected_interface' is not defined
```

### Корень проблемы — системный баг авто-экстракции

Авто-экстрактор разбил `cli.py` на файлы, но сделал 2 ошибки:

#### Ошибка А: Переименовал импорты из `common.py`

При импорте функций из `common.py` к именам добавился суффикс `_as_xxx`:
```python
# ТЕКУЩИЙ КОД (ПЛОХО):
from ..cli.common import selected_interface as selected_wg
from ..cli.common import create_interface as _create_interface
from ..cli.common import pause as _pause
```

Но внутри кода осталось оригинальное имя:
```python
# Внутри функции — оригинальное имя (NameError!):
interface = selected_interface()    # ← не существует!
_pause()                            # ← не существует!
```

**Затронутые файлы:**
| Файл | Что переименовано | Где используется оригинальное имя |
|------|-------------------|----------------------------------|
| `cli/server_menu.py` | `selected_interface as selected_wg` | строки 19, 39 |
| `commands/peer_crud.py` | `selected_interface as selected_wg` | строки 22, 42 (config_path) |
| `commands/peer_lifecycle.py` | `selected_interface as selected_wg` | строки 21, 34 (config_path) |
| `cli/common.py` | `create_interface as _create_interface` | строка 59 |
| `cli/common.py` | `pause as _pause` | строка 82 |
| `cli/common.py` | `set_selected_interface as _set_selected` | строка 142 |

#### Ошибка Б: Не перенёс Rich-импорты

Оригинальный `cli.py` имел в начале файла:
```python
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
```

Но ни один из 30 новых файлов не получил эти импорты. Файлы используют:
- `console.print()` — без `console = Console()` → **NameError**
- `Table.grid()`, `Table.add_column()` — без `from rich.table import Table` → **NameError**
- `Panel()` — без `from rich.panel import Panel` → **NameError**

**Затронутые файлы (все, где есть Rich-вывод):**

| Файл | Что использует |
|------|----------------|
| `cli/router.py` | `console.print()` (строка 53) |
| `cli/server_menu.py` | `console.print()` (строки 48, 51, 57, 60, 66, 69, 77, 80) |
| `cli/system_info_menu.py` | `console.print()`, `Table`, `Panel` (строки 23-29, 36, 45, 55, 74) |
| `commands/peer_crud.py` | `console.print()` |
| `commands/peer_lifecycle.py` | `console.print()` |
| `commands/peer_expiry.py` | `console.print()` |
| `commands/backup_commands.py` | `console.print()` |
| `commands/diagnostics_commands.py` | `console.print()` |
| `commands/firewall_commands.py` | `console.print()` |

#### Ошибка В: Не перенесены импорты вызываемых подфункций

Файлы меню вызывают функции, которые определены в других модулях, но импорты не добавлены:

| Файл меню | Вызывает функцию | Функция должна быть импортирована из |
|-----------|-----------------|-------------------------------------|
| `server_menu.py` | `show_server_status()` | `views/server_status.py` |
| `server_menu.py` | `configure_server()` | `commands/configure_server.py` |
| `server_menu.py` | `show_server_config()` | (нужно найти) |
| `server_menu.py` | `remove_wireguard()` | `commands/lifecycle.py` |
| `server_menu.py` | `reinstall_wireguard()` | `commands/lifecycle.py` |
| `server_menu.py` | `rotate_server_keys()` | `commands/key_rotation.py` |
| `server_menu.py` | `manage_interfaces()` | (нужно найти) |
| `diagnostics_menu.py` | `run_full_diagnostics()` | `views/...` или commands |
| `diagnostics_menu.py` | `show_header_info()` | `cli/common.py` (уже есть, но не импортировано!) |

---

## 2. Полный список всех ошибок по файлам

### `cli/router.py`
| # | Проблема | Строка | Исправление |
|---|----------|--------|-------------|
| 1 | `console.print()` без импорта | 53 | Добавить `from rich.console import Console` и `console = Console()` |

### `cli/server_menu.py`
| # | Проблема | Строка | Исправление |
|---|----------|--------|-------------|
| 1 | `selected_interface()` но импортирован как `selected_wg` | 19, 39 | Убрать `as selected_wg`, импортировать как `selected_interface` |
| 2 | `console.print()` без импорта | 48, 51, 57, 60, 66, 69, 77, 80 | Добавить Rich-импорты + `console = Console()` |
| 3 | Подменю функции не импортированы | 41, 43, 45, 84, 86, 88, 90 | Добавить импорты из соответствующих модулей |

### `cli/system_info_menu.py`
| # | Проблема | Строка | Исправление |
|---|----------|--------|-------------|
| 1 | `console.print()`, `Table`, `Panel` без импортов | 23-29, 36, 45, 55, 74 | Добавить Rich-импорты + `console = Console()` |
| 2 | `ServerConfig`, `FirewalldManager`, `ServiceManager`, `NetworkManager`, `PeerManager`, `_wg_runtime_dashboard` без импортов | 32, 33, 35, 40, 41, 42, 43, 44 | Добавить недостающие импорты |

### `cli/diagnostics_menu.py`
| # | Проблема | Строка | Исправление |
|---|----------|--------|-------------|
| 1 | `show_header_info()` не импортирован из common | 13 | Добавить в импорт |
| 2 | Функции диагностики (`run_full_diagnostics` и т.д.) не импортированы | 28-36 | Добавить импорты |

### `commands/peer_crud.py`
| # | Проблема | Строка | Исправление |
|---|----------|--------|-------------|
| 1 | `selected_interface()` но импортирован как `selected_wg` | 22 | Убрать алиас |
| 2 | `config_path()` но импортирован как `interface_config_path` | 42 | Убрать алиас |
| 3 | `console.print()` без импорта | (множество) | Добавить Rich-импорты |

### `commands/peer_lifecycle.py`
| # | Проблема | Строка | Исправление |
|---|----------|--------|-------------|
| 1 | `selected_interface()` но импортирован как `selected_wg` | 21 | Убрать алиас |
| 2 | `config_path()` но импортирован как `interface_config_path` | 34 | Убрать алиас |
| 3 | `console.print()` без импорта | (множество) | Добавить Rich-импорты |

### `commands/peer_expiry.py`
| # | Проблема | Строка | Исправление |
|---|----------|--------|-------------|
| 1 | `console.print()` без импорта | (множество) | Добавить Rich-импорты |

### `commands/backup_commands.py`
| # | Проблема | Строка | Исправление |
|---|----------|--------|-------------|
| 1 | `console.print()` без импорта | (множество) | Добавить Rich-импорты |

### `commands/diagnostics_commands.py`
| # | Проблема | Строка | Исправление |
|---|----------|--------|-------------|
| 1 | `console.print()` без импорта | (множество) | Добавить Rich-импорты |

### `commands/firewall_commands.py`
| # | Проблема | Строка | Исправление |
|---|----------|--------|-------------|
| 1 | `console.print()` без импорта | (множество) | Добавить Rich-импорты |

### `views/server_status.py`
| # | Проблема | Строка | Исправление |
|---|----------|--------|-------------|
| 1 | `config_path()` но импортирован как `interface_config_path` | 116 | Убрать алиас |

---

## 3. Классификация ошибок

### Категория А: `NameError` — aliased imports (шаблонный баг авто-экстрактора)
Импорт: `from ..cli.common import foo as bar`
Код: `foo()` → **NameError: name 'foo' is not defined**

**Файлы:** `server_menu.py`, `peer_crud.py`, `peer_lifecycle.py`, `common.py`, `server_status.py`

### Категория Б: `NameError` — console/Table/Panel без импортов
Код: `console.print()` но `Console` не импортирован

**Файлы:** `router.py`, `server_menu.py`, `system_info_menu.py`, `peer_crud.py`, `peer_lifecycle.py`, `peer_expiry.py`, `backup_commands.py`, `diagnostics_commands.py`, `firewall_commands.py`

### Категория В: `NameError` — подфункции не импортированы
Файл меню вызывает функцию, которая должна быть импортирована из другого модуля

**Файлы:** `server_menu.py`, `diagnostics_menu.py`

---

## 4. Порядок исправления

### Шаг 1: Зафиксить все алиасы (`selected_interface as selected_wg` → `selected_interface`)

**Файлы:**
- `cli/server_menu.py` — строка 8: убрать `as selected_wg`, заменить 2 использования (строки 19, 39)
- `commands/peer_crud.py` — строка 8: убрать `as selected_wg`, заменить 1 использование (строка 22)
- `commands/peer_crud.py` — строка 9: убрать `as interface_config_path`, заменить 1 использование (строка 42)
- `commands/peer_lifecycle.py` — строка 8: убрать `as selected_wg`, заменить 1 использование (строка 21)
- `commands/peer_lifecycle.py` — строка 9: убрать `as interface_config_path`, заменить 1 использование (строка 34)
- `cli/common.py` — строка 36: убрать `as _create_interface`, заменить 1 использование (строка 59)
- `cli/common.py` — строка 37: убрать `as _pause`, заменить 1 использование (строка 82)
- `cli/common.py` — строка 35: убрать `as _set_selected`, заменить 1 использование (строка 142)
- `views/server_status.py` — строка 5: убрать `as interface_config_path`, заменить 1 использование (строка 116)

### Шаг 2: Добавить Rich-импорты (`Console`, `Table`, `Panel`)

**Файлы (9 штук):**
- `cli/router.py` → добавить `from rich.console import Console` + `console = Console()`
- `cli/server_menu.py` → добавить `from rich.console import Console` + `console = Console()`
- `cli/system_info_menu.py` → добавить `from rich.console import Console` + `from rich.panel import Panel` + `from rich.table import Table` + `console = Console()`
- `commands/peer_crud.py` → добавить Rich-импорты
- `commands/peer_lifecycle.py` → добавить Rich-импорты
- `commands/peer_expiry.py` → добавить Rich-импорты
- `commands/backup_commands.py` → добавить Rich-импорты
- `commands/diagnostics_commands.py` → добавить Rich-импорты
- `commands/firewall_commands.py` → добавить Rich-импорты

### Шаг 3: Добавить импорты подфункций

**`cli/server_menu.py`:**
```python
from ..views.server_status import show_server_status
from ..commands.configure_server import configure_server
from ..commands.lifecycle import remove_wireguard, reinstall_wireguard
from ..commands.key_rotation import rotate_server_keys
from .server_menu import manage_interfaces  # или откуда там
```

**`cli/diagnostics_menu.py`:**
```python
from ..cli.common import show_header_info  # ← уже есть! нужно проверить
from ..views.diagnostic_views import (
    run_full_diagnostics,
    run_system_diagnostics,
    run_network_diagnostics,
    run_wireguard_diagnostics,
    run_firewall_diagnostics,
)
```

### Шаг 4: Добавить недостающие импорты в `system_info_menu.py`

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

### Шаг 5: `pytest`
Убедиться что 58/58 проходят.

---

## 5. Сводная таблица

| Категория | Кол-во файлов | Кол-во строк | Сложность |
|-----------|--------------|--------------|-----------|
| А: Алиасы | 7 файлов | ~15 строк | Низкая |
| Б: Rich-импорты | 9 файлов | ~27 строк | Низкая |
| В: Подфункции | 2 файла | ~10 строк | Средняя |
| Г: system_info_menu | 1 файл | ~15 строк | Средняя |
| **Итого** | **~11 файлов** | **~67 строк** | **Низкая-Средняя** |

## 6. Критерии приёмки

1. ✅ Выбор пункта 1 (Servers) в главном меню — не падает
2. ✅ Выбор пункта 2 (Peers) в главном меню — не падает
3. ✅ Выбор любого подменю — не падает
4. ✅ `pytest` — 58/58 passed
5. ✅ Ни одной `NameError` при любом пути через меню