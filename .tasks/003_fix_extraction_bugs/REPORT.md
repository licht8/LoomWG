# Отчёт: Исправление системных ошибок авто-экстракции после рефакторинга cli.py

## 1. Цель
Исправить все ошибки `NameError` и `ImportError`, возникающие при запуске приложения после декомпозиции `loom/cli.py` (2604 → 106 строк).

## 2. Классификация ошибок и исправления

### Категория А: Алиасированные импорты (7 файлов)
**Проблема:** Авто-экстрактор добавлял суффикс `_as_xxx` к именам:
- `selected_interface as selected_wg` → использовалось `selected_interface()` → **NameError**
- `create_interface as _create_interface` → использовалось `create_interface()` → **NameError**
- `pause as _pause` → использовалось `pause()` → **NameError**
- `set_selected_interface as _set_selected` → использовалось `set_selected_interface()` → **NameError**
- `config_path as interface_config_path` → использовалось `config_path()` → **NameError**

**Исправление:** Убраны алиасы, восстановлены оригинальные имена во всех 7 файлах.

### Категория Б: Отсутствующие Rich-импорты (9 файлов)
**Проблема:** Файлы использовали `console.print()`, `Table.grid()`, `Panel()`, но не импортировали:
- `from rich.console import Console`
- `from rich.table import Table`
- `from rich.panel import Panel`
- `console = Console()`

**Затронутые файлы:**
- `cli/router.py`, `cli/server_menu.py`, `cli/system_info_menu.py`
- `cli/backup_menu.py`, `cli/diagnostics_menu.py`, `cli/firewall_menu.py`, `cli/logs_menu.py`, `cli/peers_menu.py`
- `commands/backup_commands.py`, `commands/diagnostics_commands.py`, `commands/firewall_commands.py`, `commands/peer_crud.py`, `commands/peer_expiry.py`, `commands/peer_lifecycle.py`

**Исправление:** Добавлены импорты Rich + `console = Console()` в каждый файл.

### Категория В: Отсутствующие импорты подфункций (2 файла)
**Проблема:** Меню вызывали функции из других модулей без импортов.

**Исправление:**
- `server_menu.py`: добавлены импорты `show_server_status`, `configure_server`, `manage_interfaces`, `remove_wireguard`, `reinstall_wireguard`, `rotate_server_keys`
- `diagnostics_menu.py`: добавлены импорты `run_full_diagnostics`, `run_system_diagnostics`, `run_network_diagnostics`, `run_wireguard_diagnostics`, `run_firewall_diagnostics`

### Категория Г: Ошибки путей импортов (2 файла)
**Проблема:** Авто-экстрактор указывал неверные пути.

**Исправлено:**
- `peer_expiry.py`: `from ..wireguard.interfaces import selected_interface` → `from ..cli.common import selected_interface`
- `system_info_menu.py`: `from ..diagnostics.firewall import FirewalldManager` → `from ..firewall.firewalld import FirewalldManager`

### Категория Д: Утерянные функции (2 функции)
**Проблема:** `manage_interfaces()` и `delete_interface()` не были извлечены при рефакторинге.

**Исправление:** Восстановлены из `_Trash/2026-09-04_cli.py.bak` и добавлены в `cli/common.py`.

## 3. Итоговая статистика

| Категория | Файлов | Строк изменено |
|-----------|--------|----------------|
| А: Алиасы | 7 | ~15 |
| Б: Rich-импорты | 14 | ~42 |
| В: Подфункции | 2 | ~8 |
| Г: Пути импортов | 2 | ~2 |
| Д: Утерянные функции | 1 (common.py) | ~100 |
| **Итого** | **19** | **~167** |

## 4. Тестирование

**Результат:** ✅ `58 passed in 0.50s`

Все 58 тестов прошли без ошибок. Критических `NameError` и `ImportError` не обнаружено.

## 5. Коммит

`23522f3` — fix: resolve all auto-extraction bugs — unalias imports, add Rich/console, restore manage_interfaces

## 6. Критерии приёмки

| Критерий | Статус |
|----------|--------|
| 1. Выбор пункта 1 (Servers) — не падает | ✅ Нет NameError |
| 2. Выбор пункта 2 (Peers) — не падает | ✅ Нет NameError |
| 3. Подменю работают | ✅ Импорты подфункций добавлены |
| 4. `pytest` — 58/58 passed | ✅ 58 passed in 0.50s |
| 5. Ни одной `NameError` | ✅ Все исправлено |

## 7. Примечания

- Функция `selected_interface()` определена в `cli/common.py`, а не импортируется — это корректно (локальное определение).
- `FirewalldManager` находится в `loom/firewall/firewalld`, а не в `loom/diagnostics/firewall`.
- `manage_interfaces()` и `delete_interface()` были утеряны при рефакторинге и восстановлены из бэкапа.