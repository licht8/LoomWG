# Отчёт: Исправление ошибок после рефакторинга cli.py

## Цель
Исправить все ошибки импортов и неправильные классы, возникшие после декомпозиции `cli.py` в коммит `f9bd1c6`.

## Выполненные исправления

### 1. `loom/cli/common.py` — Критическая ошибка блокировки
**Проблема:** `WireGuardInstaller` вместо `WireGuardManager` в `show_header_info()` → `AttributeError: 'WireGuardInstaller' object has no attribute 'is_installed'`
**Исправление:** Заменён импорт и экземпляр на `WireGuardManager`

### 2. `loom/commands/configure_server.py` — 6 недостающих импортов + 1 мусор
**Добавлено:** `subprocess`, `ip_network`, `Console`, `FirewalldManager`, `NetworkManager`, `LoomLogger`, `console = Console()`
**Удалено:** `WireGuardInstaller` (не используется)

### 3. `loom/commands/install_wireguard.py` — 6 недостающих импортов
**Добавлено:** `WireGuardManager`, `FirewalldManager`, `NetworkManager`, `selected_interface`, `confirm`, `console`

### 4. `loom/commands/key_rotation.py` — 6 недостающих импортов + 1 мусор
**Добавлено:** `re`, `BackupManager`, `LoomLogger`, `console`, импорт `normalize_wireguard_config` и `repair_wireguard_config_file` из `configure_server`
**Удалено:** `WireGuardInstaller` (не используется)

### 5. `loom/commands/lifecycle.py` — 2 неиспользуемых импорта
**Удалено:** `WireGuardManager`, `WireGuardInstaller`
**Добавлено:** `console = Console()` (используется в функциях файла)

## Результат тестирования
```
58 passed in 0.51s
```
Все 58 тестов прошли. Синтаксических ошибок нет.

## Критерии приёмки
| # | Критерий | Статус |
|---|----------|--------|
| 1 | `python -c "from loom.cli import main_menu"` без ошибок | ✅ |
| 2 | `pytest` — 58/58 passed | ✅ |
| 3 | Нет `AttributeError` | ✅ |
| 4 | Нет неиспользуемых импортов | ✅ |
| 5 | Все `console.print()`, `subprocess.run()`, `LoomLogger()` импортированы | ✅ |

## Коммит
```
429fa1c fix: restore imports and correct classes after cli.py refactoring
```

## Изменённые файлы
- `loom/cli/common.py` — 2 строки (WireGuardInstaller → WireGuardManager)
- `loom/commands/configure_server.py` — добавлено ~8 строк импортов, удалён мусор
- `loom/commands/install_wireguard.py` — добавлено ~7 строк импортов
- `loom/commands/key_rotation.py` — добавлено ~9 строк импортов, удалён мусор
- `loom/commands/lifecycle.py` — удалено 2 строки, добавлен console