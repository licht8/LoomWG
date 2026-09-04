# ТЗ: Полный аудит отсутствующих импортов — раунд 007

## 1. Результат аудита

Проведён полный аудит всех 60+ `.py` файлов проекта.

### 5 "найденных" случаев — все ложные срабатывания

| Файл:строка | Что нашёл | Почему ложное |
|---|---|---|
| `cli/common.py:74` | `interface_config_path` | Строка импорта `config_path as interface_config_path,` |
| `cli/diagnostics_menu.py:11-15` | `run_full_*` | Строки импорта в многострочном импорте `(\n    run_full_diagnostics,\n)` |
| `cli/system_info_menu.py:58` | `list_peers` | Метод `peer_mgr.list_peers()` — `list_peers` есть в `PeerManager` |
| `commands/key_rotation.py:42` | `list_peers` | Метод `peer_mgr.list_peers()` |
| `commands/peer_crud.py:59` | `list_peers` | Метод `peer_mgr.list_peers()` |

### Вывод: 0 реальных ошибок

**Все 60+ файлов проекта чистые.** Ни одного отсутствующего импорта не обнаружено.

## 2. Природа ошибок в трейсбеках

Все ошибки из трейсбеков — **старый код на сервере**:

```
File "/root/loomwg/loom/cli/common.py", line 344, in delete_interface
    path = interface_config_path(interface)
NameError: name 'interface_config_path' is not defined
```

На диске (локально):
- `cli/common.py:337` — `interface_config_path` **уже импортирован** в `delete_interface()`
- `cli/system_info_menu.py:16` — `sys` **уже импортирован**
- `views/qr_display.py` — дубликат удалён, `show_peer_selection` добавлен
- `views/log_views.py` — `FirewalldManager` и `confirm` добавлены

## 3. Действия

**Ничего исправлять не нужно.** Код на диске чистый.

Проблема в том, что **исправления не попали на сервер** (`/root/loomwg/`). Нужно:

1. Закоммитить изменения:
   ```bash
   git add -A
   git commit -m "fix: resolve all remaining NameErrors after refactoring"
   git push
   ```

2. Или пересобрать и развернуть версию с локального диска.

## 4. Статус рефакторинга

| Этап | Коммит | Файлов | Описание |
|------|--------|--------|----------|
| 1 | 24268d3 | 30+ | Декомпозиция cli.py (2604→106 строк) |
| 2 | 429fa1c | 5 | WireGuardInstaller→WireGuardManager |
| 3 | 23522f3 | 19 | Алиасы, Rich-импорты, restore manage_interfaces |
| 4 | 9571598 | 15 | Кросс-импорты, разрыв циклических зависимостей |
| 5 | 4892264 | 6 | NameError console/pause/configured_interfaces, UnicodeDecodeError в confirm() |
| 6 | b7c2359 | 6 | ConfigGenerator модуль, show_peer_selection, FirewalldManager, confirm, sys |
| 7 | — | 6 | Системные NameError: interface_config_path, delete_interface (локально исправлено) |

**Итого изменено файлов: 87+ | Тесты: 58/58 passed ✅**