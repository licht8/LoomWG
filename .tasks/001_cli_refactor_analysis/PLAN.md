# План: Декомпозиция `loom/cli.py`

## Этап 1: Подготовка общей базы (`common.py`)

**Цель:** Вынести общие UI-утилиты в отдельный модуль. Это самое безопасное изменение — никаких зависимостей от других новых модулей.

### Шаги:

1. **Создать `loom/cli/common.py`**
   - Вынести функции:
     - `clear_screen()`
     - `pause()`
     - `confirm(prompt)`
     - `section_banner(title, subtitle)`
     - `menu_option(number, title, description, command)`
     - `show_banner()`
   - Экспортировать все через `__all__`.

2. **Обновить `loom/cli/__init__.py`**
   - Добавить импорт из `common`: `from .common import *`.

3. **Обновить `loom/cli.py`**
   - Заменить локальные вызовы на импорт из `loom.cli.common`.
   - Удалить функции, перенесённые в `common.py`.
   - Проверить, что `cli.py` всё ещё работает: запустить `python -c "from loom.cli import main_menu"` (без вызова main).

**Критерий готовности:** `pytest` проходит. `cli.py` стал короче на ~80 строк.

---

## Этап 2: Вынос View-функций (`loom/views/`)

**Цель:** Отделить функции отрисовки от логики. Функции, которые только показывают данные, переезжают в `loom/views/`.

### Шаги:

1. **Создать `loom/views/__init__.py`**

2. **Создать `loom/views/server_status.py`**
   - Вынести: `show_server_status()`, `_wg_runtime_dashboard()`, `_age_text()`, `_format_bytes()`.
   - Зависимости: `subprocess`, `datetime`, `loom.wireguard.*`. Оставить как есть.

3. **Создать `loom/views/peer_views.py`**
   - Вынести: `list_peers()`, `peer_table()`, `show_peer()`, `show_peer_selection()`.
   - Зависимости: `loom.wireguard.peer_manager.Peer`, `loom.cli.common`.

4. **Создать `loom/views/qr_display.py`**
   - Вынести: `prompt_for_qr_code()`, `display_peer_qr_code()`, `show_qr_code()`.
   - Зависимости: `loom.wireguard.client_config`, `loom.views.peer_views`.

5. **Создать `loom/views/backup_views.py`**
   - Вынести: `list_backups()`, `create_backup()`, `restore_backup()`, `delete_backup()`.
   - Зависимости: `loom.backup.manager`, `loom.cli.common`.

6. **Создать `loom/views/log_views.py`**
   - Вынести: `view_logs()`, `clear_logs()`, `export_logs()`.
   - Зависимости: `loom.logging_system.logger`, `loom.cli.common`.

7. **Обновить `loom/cli.py`**
   - Заменить вызовы View-функций на импорт из `loom.views`.
   - Удалить вынесенный код.

**Критерий готовности:** `pytest` проходит. `cli.py` стал короче на ~400 строк.

---

## Этап 3: Вынос бизнес-логики (`loom/commands/`)

**Цель:** Отделить действия, которые что-то меняют, от UI. Функции, которые пишут файлы и вызывают `subprocess.run`, переезжают в `loom/commands/`.

### Шаги:

1. **Создать `loom/commands/__init__.py`**

2. **Создать `loom/commands/configure_server.py`**
   - Вынести: `configure_server()`, `prompt_server_config()`, `validate_server_settings()`.
   - Аргументы: интерфейс, конфиг-файл. Возврат: результат или исключения.

3. **Создать `loom/commands/install_wireguard.py`**
   - Вынести: `install_wireguard()`.
   - Аргументы: имя интерфейса.

4. **Создать `loom/commands/peer_lifecycle.py`**
   - Вынести: `enable_peer()`, `disable_peer()`, `revoke_peer()`, `rotate_peer_keys()`, `remove_peer()`.
   - Эти функции сложные — каждая содержит:
     - `show_peer_selection()` (View)
     - `input()` (UI)
     - бизнес-логику
   - **Важно:** Функции команд НЕ должны вызывать `input()` или `print()`. Для этого создать отдельный слой интерфейса.
   - **Решение:** В `commands/` вынести ТОЛЬКО чистую логику. В `cli/` оставить вызовы `input()` и передачу данных в команды.

5. **Создать `loom/commands/key_rotation.py`**
   - Вынести: `rotate_server_keys()`.
   - Самая сложная функция: содержит rollback-логику, бэкапы, регенерацию клиентских конфигов.

6. **Создать `loom/commands/interface_manager.py`**
   - Вынести: `manage_interfaces()`, `create_interface()`, `delete_interface()`.

7. **Создать `loom/commands/peer_expiry.py`**
   - Вынести: `set_peer_expiry()`, `enforce_expired_peers()`.

8. **Создать `loom/commands/peer_import.py`**
   - Вынести: `import_server_peers()`.

9. **Создать `loom/commands/lifecycle.py`**
   - Вынести: `remove_wireguard()`, `reinstall_wireguard()`.

10. **Обновить `loom/cli.py`**
    - Заменить вызовы на импорт из `loom.commands`.
    - Удалить вынесенный код.

**Критерий готовности:** `pytest` проходит. `cli.py` стал короче на ~800 строк.

---

## Этап 4: Создание роутера и меню

**Цель:** Создать структурированные меню в `loom/cli/` и роутер для навигации.

### Шаги:

1. **Создать `loom/cli/router.py`**
   - `main_menu()` — главное меню, использует словарь маршрутов:
     ```python
     ROUTES = {
         '1': ('server', server_menu.server_menu),
         '2': ('peers', peers_menu.peers_menu),
         # ...
     }
     ```

2. **Создать `loom/cli/server_menu.py`**
   - `server_menu()` — меню сервера.
   - Вызывает функции из `loom.commands` и `loom.views`.

3. **Создать `loom/cli/peers_menu.py`**
   - `peers_menu()` — меню пиров.

4. **Создать `loom/cli/firewall_menu.py`**
   - `firewall_menu()` — меню firewall.

5. **Создать `loom/cli/diagnostics_menu.py`**
   - `diagnostics_menu()` — меню диагностики.

6. **Создать `loom/cli/backup_menu.py`**
   - `backup_menu()` — меню бэкапов.

7. **Создать `loom/cli/logs_menu.py`**
   - `logs_menu()` — меню логов.

8. **Создать `loom/cli/system_info_menu.py`**
   - `system_info_menu()` — меню информации о системе.
   - `version_menu()` — показ версии.

9. **Обновить `loom/cli.py`**
   - Оставить ТОЛЬКО `if __name__ == '__main__': main_menu()`.
   - Удалить весь код меню и бизнес-логики.

**Критерий готовности:** `pytest` проходит. `cli.py` ~40 строк. Все новые файлы работают.

---

## Этап 5: Финальная очистка

**Цель:** Убрать старые зависимости, проверить все импорты, обновить `__init__.py`.

### Шаги:

1. **Проверить все импорты**
   - Убедиться, что ни один модуль не импортирует что-то из `loom.cli.py` (кроме entry point).
   - Убедиться, что нет циклических импортов.

2. **Обновить `loom/__init__.py`**
   - Добавить публичные импорты новых модулей.

3. **Обновить `pyproject.toml`**
   - Если нужно, добавить новые пакеты.

4. **Запустить полный `pytest`**
   - Убедиться, что все тесты проходят.
   - Если какие-то тесты ссылаются на функции из `cli.py` — обновить их импорты.

5. **Подготовить `_Trash/` папку**
   - Если были удалённые части старого `cli.py`, перенести их в `_Trash/`.

**Критерий готовности:** Чистый код, все тесты зелёные, `cli.py` < 60 строк.

---

## Сводная оценка

| Этап | Действие | Ожидаемый результат |
|------|----------|---------------------|
| 1 | `common.py` | ~80 строк вынесено |
| 2 | `views/` | ~400 строк вынесено |
| 3 | `commands/` | ~800 строк вынесено |
| 4 | `cli/` меню | ~600 строк вынесено |
| 5 | Очистка | `cli.py` < 60 строк |

**Итого:** cli.py сократится с 2604 до ~50 строк. Создастся ~12 новых файлов по 100-300 строк.