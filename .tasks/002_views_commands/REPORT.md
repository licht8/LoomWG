# Отчёт: Этап 2 — Вынос View-функций в `loom/views/`

## Цель
Отделить функции отрисовки от логики. Функции, которые только показывают данные, переехали в `loom/views/`.

## Выполнено
1. Создана `loom/views/` с модулями:
   - `server_status.py` — `show_server_status`, `_wg_runtime_dashboard`, `_age_text`, `_format_bytes`, `show_server_config`
   - `peer_views.py` — `list_peers`, `peer_table`, `show_peer`, `show_peer_selection`
   - `qr_display.py` — `show_qr_code`
   - `backup_views.py` — `list_backups`
   - `log_views.py` — `view_logs`, `clear_logs`, `export_logs`, `show_firewall_status`
   - `system_dashboard.py` — `system_info_menu` (перенесена в `cli/`)
2. Создана `loom/commands/` с бизнес-логикой:
   - `configure_server.py` — `configure_server`, `normalize_wireguard_config`, `repair_wireguard_config_file`, `prompt_server_config`, `validate_server_settings`
   - `key_rotation.py` — `rotate_server_keys`
   - `lifecycle.py` — `remove_wireguard`, `reinstall_wireguard`
   - `install_wireguard.py` — `install_wireguard`
   - `peer_crud.py` — `create_peer`
   - `peer_lifecycle.py` — `disable_peer`, `enable_peer`, `revoke_peer`, `rotate_peer_keys`, `remove_peer`
   - `firewall_commands.py` — `start_firewall`, `enable_firewall`, `open_wg_port`
   - `diagnostics_commands.py` — `run_full_diagnostics`, `run_system_diagnostics`, `run_network_diagnostics`, `run_wireguard_diagnostics`, `run_firewall_diagnostics`
   - `backup_commands.py` — `create_backup`, `restore_backup`, `delete_backup`
   - `peer_expiry.py` — `enforce_expired_peers`, `download_peer_config`, `set_peer_expiry`
   - `peer_import.py` — `import_server_peers`
3. Созданы меню в `loom/cli/`:
   - `router.py` — `main_menu`
   - `server_menu.py` — `server_menu`
   - `peers_menu.py` — `peers_menu`
   - `firewall_menu.py` — `firewall_menu`
   - `diagnostics_menu.py` — `diagnostics_menu`
   - `backup_menu.py` — `backup_menu`
   - `logs_menu.py` — `logs_menu`
   - `system_info_menu.py` — `system_info_menu`, `version_menu`
4. `cli/__init__.py` теперь содержит только импорты (~106 строк).

## Статистика
- Старый `loom/cli.py`: 2604 строки (удалён)
- Новая структура:
  - `loom/cli/`: 933 строки (11 файлов)
  - `loom/views/`: 490 строк (6 файлов)
  - `loom/commands/`: 1775 строк (13 файлов)
  - Итого: 3003 строк (добавлен boilerplate — импорты, docstrings)

## Результаты тестирования
```
58 passed in 0.70s
```
Все 58 тестов прошли успешно.

## Изменённые файлы
- `loom/cli/__init__.py` — 106 строк (было 2256)
- `loom/cli/common.py` — 275 строк (UI-утилиты)
- `loom/cli/router.py` — 61 строка
- `loom/cli/server_menu.py` — 99 строк
- `loom/cli/peers_menu.py` — 66 строк
- `loom/cli/firewall_menu.py` — 43 строки
- `loom/cli/diagnostics_menu.py` — 45 строк
- `loom/cli/backup_menu.py` — 38 строк
- `loom/cli/logs_menu.py` — 33 строки
- `loom/cli/system_info_menu.py` — 77 строк
- `loom/views/server_status.py` — 134 строки
- `loom/views/peer_views.py` — 119 строк
- `loom/views/qr_display.py` — 61 строка
- `loom/views/backup_views.py` — 40 строк
- `loom/views/log_views.py` — 130 строк
- `loom/commands/configure_server.py` — 249 строк
- `loom/commands/key_rotation.py` — 140 строк
- `loom/commands/lifecycle.py` — 40 строк
- `loom/commands/install_wireguard.py` — 169 строк
- `loom/commands/peer_crud.py` — 185 строк
- `loom/commands/peer_lifecycle.py` — 315 строк
- `loom/commands/firewall_commands.py` — 65 строк
- `loom/commands/diagnostics_commands.py` — 176 строк
- `loom/commands/backup_commands.py` — 145 строк
- `loom/commands/peer_expiry.py` — 72 строки
- `loom/commands/peer_import.py` — 120 строк

## Бэкап оригинала
- `_Trash/2026-09-04_cli.py.bak` — полный бэкап оригинального `loom/cli.py`