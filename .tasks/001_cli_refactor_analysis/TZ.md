# ТЗ: Декомпозиция `loom/cli.py` (Рефакторинг God File)

## 1. Контекст и Цель
**Задача:** Разбить файл `loom/cli.py` (2604 строки) на модульную структуру.
**Цель:** Разделить ответственность между навигацией (UI), бизнес-логикой (Commands) и отрисовкой (Views).
**Правила:**
- Не удалять старый код, переносить в `_Trash/`.
- Запускать `pytest` после каждого этапа.
- Соблюдать принцип единой ответственности (SRP).

---

## 2. Новая Архитектура

```text
loom/
├── cli/                      # СЛОЙ 1: Навигация и Ввод
│   ├── __init__.py           # Импорты меню
│   ├── router.py             # Главный роутер (main)
│   ├── common.py             # Утилиты: clear_screen, pause, confirm, banner
│   ├── main_menu.py          # main_menu
│   ├── server_menu.py        # server_menu + sub-actions
│   ├── peers_menu.py         # peers_menu + sub-actions
│   ├── firewall_menu.py      # firewall_menu
│   ├── diagnostics_menu.py   # diagnostics_menu
│   ├── backup_menu.py        # backup_menu
│   ├── logs_menu.py          # logs_menu
│   └── system_info_menu.py   # system_info_menu + version
│
├── commands/                 # СЛОЙ 2: Бизнес-логика (Действия)
│   ├── __init__.py           # Импорты команд
│   ├── configure_server.py   # configure_server (чистая логика)
│   ├── install_wireguard.py  # install_wireguard
│   ├── create_peer.py        # create_peer (логика IP, ключей)
│   ├── peer_lifecycle.py     # enable_peer, disable_peer, revoke_peer, rotate_peer_keys, remove_peer
│   ├── key_rotation.py       # rotate_server_keys (сложная логика с rollback)
│   ├── interface_manager.py  # manage_interfaces, create_interface, delete_interface
│   ├── peer_expiry.py        # set_peer_expiry, enforce_expired_peers
│   ├── peer_import.py        # import_server_peers
│   └── lifecycle.py          # remove_wireguard, reinstall_wireguard
│
├── views/                    # СЛОЙ 3: Отрисовка (UI)
│   ├── __init__.py           # Импорты view
│   ├── server_status.py      # show_server_status, _wg_runtime_dashboard
│   ├── peer_views.py         # peer_table, show_peer, show_peer_selection
│   ├── qr_display.py         # display_peer_qr_code, show_qr_code
│   ├── backup_views.py       # table creation for backups
│   ├── log_views.py          # view_logs (форматирование)
│   └── system_dashboard.py   # system_info_menu (рендеринг панелей)
│
└── cli.py                    # ТОЛЬКО Точка входа (40-50 строк)
```

---

## 3. Детальные Требования к Модулям

### 3.1. `loom/cli/common.py`
**Содержимое:** Вынести общие функции, используемые в каждом меню.
- `clear_screen()`
- `pause()`
- `confirm(prompt)`
- `section_banner(title, subtitle)`
- `menu_option(number, title, description, command)`
- `check_root()`
- `show_header_info()`
- `selected_interface()`, `select_interface()`
- `prompt_for_qr_code()`

**Ограничение:** Никакой бизнес-логики, только UI-хелперы.

### 3.2. `loom/commands/...`
**Содержимое:** Извлечь функции, которые что-то меняют (запись на диск, выполнение команд `wg`, `dnf`).
- **Пример `create_peer`:** Функция должна принимать имя, IP и ключи как аргументы, выполнять логику добавления пира и возвращать результат или объект `Peer`. Она **НЕ должна** вызывать `input()` или `console.print()`.
- **Пример `rotate_server_keys`:** Должна принимать текущий конфиг и возвращать новый (с проверками), без `clear_screen`.

**Список файлов и что в них класть:**
1.  **`configure_server.py`**: Логика `configure_server`.
2.  **`install_wireguard.py`**: Логика `install_wireguard`.
3.  **`create_peer.py`**: Логика `create_peer`.
4.  **`peer_lifecycle.py`**: `enable_peer`, `disable_peer`, `revoke_peer`, `rotate_peer_keys`, `remove_peer`.
5.  **`key_rotation.py`**: `rotate_server_keys` (самая сложная, требует тестов на rollback).
6.  **`interface_manager.py`**: `manage_interfaces`, `create_interface`, `delete_interface`.
7.  **`peer_expiry.py`**: `set_peer_expiry`, `enforce_expired_peers`.
8.  **`peer_import.py`**: `import_server_peers`.
9.  **`lifecycle.py`**: `remove_wireguard`, `reinstall_wireguard`.

### 3.3. `loom/views/...`
**Содержимое:** Извлечь функции, которые только читают данные и выводят их (Rich Console).
1.  **`server_status.py`**: `show_server_status`, `_wg_runtime_dashboard` (можно оставить здесь или в commands, если это чистая обработка данных).
2.  **`peer_views.py`**: `peer_table`, `show_peer`, `show_peer_selection`.
3.  **`qr_display.py`**: `display_peer_qr_code`, `show_qr_code`.
4.  **`backup_views.py`**: Вывод списков бэкапов (форматирование таблиц).
5.  **`log_views.py`**: `view_logs`.
6.  **`system_dashboard.py`**: `system_info_menu`.

### 3.4. `loom/cli/router.py`
**Содержимое:** Главный контроллер.
- `main_menu()`: Отображает меню, получает выбор `input()`, вызывает соответствующую функцию из `commands` или вложенное меню.
- Использовать паттерн "Входящая функция вызывает View + Command".

---

## 4. Правила Рефакторинга

1.  **Разделение логики и UI:**
    - `commands` НЕ делают `print`, `input`, `console.print`, `clear_screen`.
    - `views` НЕ делают `subprocess.run`, `open('w')`, `peer_mgr.add_peer()`.
    - `cli` управляет потоком: "Спросить ввод -> Передать в Command -> Взять результат -> Передать в View".

2.  **Работа с импортами:**
    - Не создавать циклических импортов.
    - Старые импорты в `cli.py` аккуратно перераспределить по новым файлам.

3.  **Поэтапность:**
    - Сначала вынести `common.py` (самое безопасное).
    - Затем вынести View-функции (просто перемещение кода).
    - Затем вынести команды (требует адаптации передачи аргументов).
    - В конце обновить `cli.py` (вставить вызовы новых модулей).

4.  **Тестирование:**
    - После каждого переноса функции (например, `create_peer`) убедиться, что `pytest` проходит или функция изолирована и протестирована отдельно.

## 5. Критерии Приемки
1.  `loom/cli.py` содержит не более 50-60 строк (точка входа и роутер).
2.  Нет дублирования `clear_screen()`, `pause()`, `confirm()`.
3.  Нет бизнес-логики в файлах с суффиксом `_menu.py`.
4.  `pytest` проходит успешно.