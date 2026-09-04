# Отчёт: Исправление системных ошибок авто-экстракции после рефакторинга cli.py

## Цель
Исправить все ошибки `NameError`, возникающие при запуске приложения после рефакторинга `cli.py` (декомпозиция на 30 модулей).

## Корень проблем — системные баги авто-экстрактора

Когда код `cli.py` (2604 строки) автоматически разрезался на файлы, экстрактор допустил 3 системных ошибки:

### Баг А: Переименовал импорты из `common.py` с суффиксом `_as_xxx`

Экстрактор добавил алиасы к импортам из `common.py`:
```python
from ..cli.common import selected_interface as selected_wg
from ..cli.common import pause as _pause
```

Но внутри кода осталось оригинальное имя:
```python
interface = selected_interface()  # ← NameError! selected_wg не используется
_pause()  # ← NameError!
```

**Фикс:** Убраны все алиасы (`as selected_wg`, `as _pause`, `as _set_selected`, `as interface_config_path`), заменены на прямые импорты и использования.

### Баг Б: Не перенёс Rich-импорты

Оригинальный `cli.py` имел в начале:
```python
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
```

Но ни один из 30 новых файлов не получил этих импортов. Все файлы с `console.print()` падали с `NameError: name 'console' is not defined`.

**Фикс:** В каждый файл, использующий Rich, добавлены:
- `from rich.console import Console`
- `console = Console()`
- `from rich.panel import Panel` / `from rich.table import Table` (где нужно)

### Баг В: Не перенесены импорты подфункций

Меню-файлы вызывали функции из других модулей, но импорты не добавлены:
- `server_menu.py` → `show_server_status`, `configure_server`, `remove_wireguard`, `reinstall_wireguard`, `rotate_server_keys`
- `peers_menu.py` → `create_peer`, `disable_peer`, `enable_peer`, `revoke_peer`, `rotate_peer_keys`, `remove_peer`, `set_peer_expiry`, `enforce_expired_peers`, `download_peer_config`, `import_server_peers`, `list_peers`, `show_qr_code`
- `diagnostics_menu.py` → `run_full_diagnostics`, `run_system_diagnostics` и т.д.
- `logs_menu.py` → `view_logs`, `clear_logs`, `export_logs`
- `backup_menu.py` → `create_backup`, `restore_backup`, `delete_backup`, `list_backups`
- `firewall_menu.py` → `start_firewall`, `enable_firewall`, `open_wg_port`, `show_firewall_status`

## Выполненные исправления

### Файлы (12 штук)

| Файл | Алиасы | Rich-импорты | Подфункции | Итого строк |
|------|--------|-------------|-----------|------------|
| `cli/server_menu.py` | ✅ | ✅ | ✅ | ~20 |
| `cli/system_info_menu.py` | — | ✅ | ✅ | ~15 |
| `cli/diagnostics_menu.py` | ✅ | ✅ | ✅ | ~15 |
| `cli/router.py` | — | ✅ | — | ~5 |
| `cli/logs_menu.py` | — | ✅ | ✅ | ~10 |
| `cli/backup_menu.py` | — | ✅ | ✅ | ~10 |
| `cli/peers_menu.py` | — | ✅ | ✅ | ~15 |
| `cli/firewall_menu.py` | ✅ | ✅ | ✅ | ~10 |
| `cli/common.py` | ✅ | — | — | ~5 |
| `commands/peer_crud.py` | ✅ | ✅ | — | ~15 |
| `commands/peer_lifecycle.py` | ✅ | ✅ | — | ~15 |
| `commands/peer_expiry.py` | — | ✅ | — | ~8 |
| `commands/backup_commands.py` | — | ✅ | — | ~5 |
| `commands/diagnostics_commands.py` | ✅ | ✅ | — | ~8 |
| `commands/firewall_commands.py` | ✅ | ✅ | — | ~8 |
| `views/server_status.py` | ✅ | — | — | ~2 |

## Результат тестирования
```
58 passed in 0.52s
```
Все 58 тестов прошли успешно.

## Критерии приёмки
| # | Критерий | Статус |
|---|----------|--------|
| 1 | Выбор пункта 1 (Servers) — не падает | ✅ |
| 2 | Выбор пункта 2 (Peers) — не падает | ✅ |
| 3 | Выбор любого подменю — не падает | ✅ |
| 4 | `pytest` — 58/58 passed | ✅ |
| 5 | Ни одной `NameError` | ✅ |

## Коммит
```
004b5a8 fix: resolve all auto-extraction bugs (aliased imports, missing Rich, missing sub-function imports)
```

## Сводка по всем этапам рефакторинга

| Этап | Действие | Результат |
|------|----------|-----------|
| 1 | Декомпозиция cli.py (2604→106 строк) | 30 файлов, 58/58 ✅ |
| 2 | Fix: WireGuardInstaller → WireGuardManager | 58/58 ✅ |
| 3 | Fix: системные баги авто-экстракции | 58/58 ✅ |