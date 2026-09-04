# ТЗ: Этап 1 — Вынос common.py

## Цель
Разбить файл `loom/cli.py` (2604 строки) на модульную структуру.
Этап 1: Вынести общие UI-утилиты в `loom/cli/common.py`.

## Выполнено
1. Создана директория `loom/cli/` (переместив `loom/cli.py` в `_Trash/`).
2. Создан `loom/cli/common.py` с UI-утилитами:
   - `selected_interface()`, `select_interface()`, `create_interface()`
   - `clear_screen()`, `pause()`, `confirm()`
   - `section_banner()`, `menu_option()`, `show_banner()`
   - `check_root()`, `show_header_info()`
3. `loom/cli/__init__.py` — оставшийся код cli.py (~2256 строк) с исправленными импортами.
4. Все 58 pytest прошли успешно.

## Статус файлов
- `loom/cli/common.py` — 248 строк
- `loom/cli/__init__.py` — 2256 строк
- `_Trash/2026-09-04_cli.py.bak` — бэкап оригинала
