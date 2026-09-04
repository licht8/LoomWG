# TZ: Phase 1 — Extracting common.py

## Goal
Break the file `loom/cli.py` (2604 lines) into a modular structure.
Phase 1: Extract common UI utilities to `loom/cli/common.py`.

## Completed
1. Created directory `loom/cli/` (moved `loom/cli.py` to `_Trash/`).
2. Created `loom/cli/common.py` with UI utilities:
   - `selected_interface()`, `select_interface()`, `create_interface()`
   - `clear_screen()`, `pause()`, `confirm()`
   - `section_banner()`, `menu_option()`, `show_banner()`
   - `check_root()`, `show_header_info()`
3. `loom/cli/__init__.py` — remaining cli.py code (~2256 lines) with fixed imports.
4. All 58 pytest tests passed successfully.

## File Status
- `loom/cli/common.py` — 248 lines
- `loom/cli/__init__.py` — 2256 lines
- `_Trash/2026-09-04_cli.py.bak` — original backup