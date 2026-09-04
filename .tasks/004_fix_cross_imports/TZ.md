# ТЗ: Исправление кросс-импортов и недостающих импортов

## 1. Проблема

Приложение запускается, но **падает при выполнении любых действий** (создание конфига, создание пира, удаление и т.д.) из-за `NameError: name 'xxx' is not defined`.

**Корень:** Авто-экстракция разделила функции по файлам, но **не добавила кросс-импорты** — функции вызывают другие функции из других файлов, но не импортировали их. Также есть баг: часть файлов импортирует `config_path as interface_config_path`, а код внутри использует `config_path()`.

---

## 2. Полный список ошибок

### 2.1. `commands/configure_server.py`

**Ошибка:** Вызывает `install_wireguard()` (строка 40) — функция из `install_wireguard.py`, не импортирована.

**Дополнительно:** Файл импортирует `config_path as interface_config_path` (строка 18), но **нигде не вызывает** `interface_config_path()` — это OK (функция `config_path` не используется напрямую).

**Исправление:** Добавить импорт `install_wireguard` из `commands/install_wireguard.py`.

### 2.2. `commands/install_wireguard.py`

**Ошибка:** Вызывает `prompt_server_config()` (строка 74) и `validate_server_settings()` (строка 76) — функции из `configure_server.py`, не импортированы.

**Исправление:** Добавить импорт из `commands/configure_server.py`:
```python
from ..commands.configure_server import prompt_server_config, validate_server_settings
```

### 2.3. `commands/lifecycle.py`

**Ошибка:** `reinstall_wireguard()` вызывает `install_wireguard()` (строка 38) — функция из `install_wireguard.py`, не импортирована.

**Исправление:** Добавить импорт:
```python
from ..commands.install_wireguard import install_wireguard
```

### 2.4. `commands/peer_crud.py`

**Ошибка:** `config_path` импортирован как `from ..wireguard.interfaces import config_path` (строка 14), но используется как функция `interface_config_path()` (строка 42, 144) — **имя не совпадает!**

Код: `config_path = interface_config_path(interface)` → NameError: `interface_config_path` не определён.

**Исправление:** Изменить импорт на:
```python
from ..wireguard.interfaces import config_path as interface_config_path
```

**Также:** Не импортирована `SystemDetector`:
```python
from ..system.info import SystemDetector
```

### 2.5. `commands/peer_lifecycle.py`

**Ошибка:** `config_path` импортирован как `from ..wireguard.interfaces import config_path` (строка 17), но используется как `interface_config_path()` (строки 37, 85, 133, 193).

**Исправление:** Изменить импорт на:
```python
from ..wireguard.interfaces import config_path as interface_config_path
```

**Также:** `show_peer_selection()` используется (строки 28, 64, 114, 172) — не импортирована. Должна приходить из `views.peer_views`.

**Исправление:** Добавить импорт:
```python
from ..views.peer_views import show_peer_selection
```

### 2.6. `commands/peer_expiry.py`

**Двойной импорт:** Строки 2-13 и 15-20 — полный дубликат содержимого!

**Ошибка 1:** `show_peer_selection()` используется (строки 46, 68) — не импортирована.

**Ошибка 2:** `WireGuardManager` используется (строка 34) — не импортирована.

**Ошибка 3:** `ConfigGenerator` используется (строки 25, 36) — не импортирована.

**Исправление:**
```python
from ..wireguard.manager import WireGuardManager
from ..wireguard.config_generator import ConfigGenerator
from ..views.peer_views import show_peer_selection
```

### 2.7. `commands/peer_import.py`

**Ошибка:** `SystemDetector` используется (строка 25) — не импортирована.

**Ошибка:** `Peer` используется (строка 81) — не импортирована.

**Исправление:** Добавить:
```python
from ..system.info import SystemDetector
from ..wireguard.peer_manager import Peer
```

### 2.8. `commands/backup_commands.py`

**Двойной импорт:** Строки 2-12 и 14-21 — полный дубликат содержимого!

Никаких критических ошибок — все импорты на месте, просто дубликат кода.

### 2.9. `commands/diagnostics_commands.py`

**Двойной импорт:** Строки 2-15 и 17-27 — полный дубликат содержимого!

Никаких критических ошибок — просто дубликат кода.

### 2.10. `commands/firewall_commands.py`

**Двойной импорт:** Строки 2-12 и 14-21 — полный дубликат содержимого!

Никаких критических ошибок — просто дубликат кода.

### 2.11. `cli/system_info_menu.py`

**Не хватает импортов:**
| Имя | Строка | Где используется |
|-----|--------|-----------------|
| `Table` | 36 | `Table.grid()` |
| `ServerConfig` | 45 | `ServerConfig.from_file()` |
| `FirewalldManager` | 53 | `firewall.is_installed()` |
| `NetworkManager` | 53 | `NetworkManager().is_ipv4_forwarding_enabled()` |
| `ServiceManager` | 55 | `ServiceManager().is_active()` |
| `PeerManager` | 57 | `PeerManager().list_peers()` |
| `_wg_runtime_dashboard` | 48 | `_wg_runtime_dashboard()` |
| `Panel` | 55 | `Panel(details, ...)` |

**Исправление:** Добавить в начало файла:
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

**Ошибка:** `show_peer()` вызывается (строка 58) — не импортирована. Должна приходить из `views.peer_views`.

**Исправление:** Добавить в импорт:
```python
from ..views.peer_views import list_peers, peer_table, show_peer_selection, show_peer
```

### 2.13. `cli/firewall_menu.py`

**Ошибка:** `show_firewall_status` импортирован из `..views.log_views` (строка 5), но название `show_firewall_status` скорее всего находится в `views.backup_views` или другом view-модуле. Нужно проверить реальное расположение.

**Исправление:** Проверить, где определена `show_firewall_status()`, и исправить импорт.

### 2.14. `cli/common.py`

**Функция `manage_interfaces()`:** Вызывается из `server_menu.py` (строка 99), определена в `common.py` (восстановлена из _Trash). Проверить, что импорты внутри неё корректны.

---

## 3. Сводная таблица всех исправлений

### Критические (NameError, блокируют работу):

| Файл | Что исправить | Строки |
|------|--------------|--------|
| `commands/configure_server.py` | Добавить `from ..commands.install_wireguard import install_wireguard` | ~1 |
| `commands/install_wireguard.py` | Добавить `from ..commands.configure_server import prompt_server_config, validate_server_settings` | ~1 |
| `commands/lifecycle.py` | Добавить `from ..commands.install_wireguard import install_wireguard` | ~1 |
| `commands/peer_crud.py` | `config_path` → `config_path as interface_config_path`, добавить `SystemDetector` | ~2 |
| `commands/peer_lifecycle.py` | `config_path` → `config_path as interface_config_path`, добавить `show_peer_selection` из views | ~2 |
| `commands/peer_expiry.py` | Убрать дубликат импортов, добавить `WireGuardManager`, `ConfigGenerator`, `show_peer_selection` | ~5 |
| `commands/peer_import.py` | Добавить `SystemDetector`, `Peer` | ~2 |
| `cli/system_info_menu.py` | Добавить 8 недостающих импортов (Table, Panel, ServerConfig, FirewalldManager, NetworkManager, ServiceManager, PeerManager, _wg_runtime_dashboard) | ~8 |
| `cli/peers_menu.py` | Добавить `show_peer` в импорт из views | ~1 |
| `cli/firewall_menu.py` | Исправить импорт `show_firewall_status` (вероятно, должен быть из другого модуля) | ~1 |

### Не критические (дубликаты, но не блокируют):

| Файл | Проблема | Исправление |
|------|----------|-------------|
| `commands/backup_commands.py` | Дубликат импортов (строки 2-12 и 14-21) | Удалить дубликат |
| `commands/diagnostics_commands.py` | Дубликат импортов (строки 2-15 и 17-27) | Удалить дубликат |
| `commands/firewall_commands.py` | Дубликат импортов (строки 2-12 и 14-21) | Удалить дубликат |

---

## 4. Порядок исправления

### Шаг 1: Кросс-импорты между commands (блокирует создание конфига)
- `configure_server.py` → добавить `install_wireguard`
- `install_wireguard.py` → добавить `prompt_server_config`, `validate_server_settings`
- `lifecycle.py` → добавить `install_wireguard`

### Шаг 2: Кросс-импорты в commands (блокирует работу с пирами)
- `peer_crud.py` → исправить `config_path`, добавить `SystemDetector`
- `peer_lifecycle.py` → исправить `config_path`, добавить `show_peer_selection`
- `peer_expiry.py` → убрать дубликат, добавить `WireGuardManager`, `ConfigGenerator`, `show_peer_selection`
- `peer_import.py` → добавить `SystemDetector`, `Peer`

### Шаг 3: CLI-меню (блокирует отображение меню)
- `system_info_menu.py` → добавить 8 импортов
- `peers_menu.py` → добавить `show_peer`
- `firewall_menu.py` → исправить импорт

### Шаг 4: Убрать дубликаты импортов
- `backup_commands.py` — убрать строки 14-21
- `diagnostics_commands.py` — убрать строки 17-27
- `firewall_commands.py` — убрать строки 14-21

### Шаг 5: `pytest`
Убедиться что 58/58 проходят.

---

## 5. Критерии приёмки

1. ✅ `configure_server()` работает без `NameError`
2. ✅ `install_wireguard()` работает без `NameError`
3. ✅ `create_peer()` работает без `NameError`
4. ✅ `enable_peer()` / `disable_peer()` работают без `NameError`
5. ✅ `system_info_menu()` не падает
6. ✅ `pytest` — 58/58 passed
7. ✅ Нет дубликатов импортов