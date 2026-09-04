# ТЗ: Исправление остающихся NameError и подобных ошибок (Раунд 008)

## 1. Цель
Устранить `NameError` и `ImportError`, возникающие при конкретных действиях в CLI после рефакторинга `cli.py`. Ошибки вызваны тем, что авто-экстрактор разделил файл на модули, но не перенёс необходимые импорты в каждый конкретный файл/функцию.

---

## 2. Критические ошибки из отчёта (2 файла)

### 2.1. `cli/common.py` — `delete_interface()` без `interface_config_path`

**Трейсбек:**
```
File "loom/cli/common.py", line 344, in delete_interface
    path = interface_config_path(interface)
NameError: name 'interface_config_path' is not defined
```

**Проблема:**
Функция `delete_interface()` (начинается ~строка 332) импортирует локально только `WireGuardManager`, `ServiceManager`, `LoomLogger`. Вызов `interface_config_path(interface)` происходит без импорта.

**Исправление:**
Добавить в блок локальных импортов функции `delete_interface()` (после строки с `from ..logging_system.logger import LoomLogger`):
```python
from ..wireguard.interfaces import config_path as interface_config_path
```

---

### 2.2. `cli/system_info_menu.py` — отсутствует `import sys`

**Трейсбек:**
```
File "loom/cli/system_info_menu.py", line 57, in system_info_menu
    section("LoomWG", [("Version", "0.1.0"), ("Python", sys.version.split()[0]), ("Executable", sys.executable), ...])
NameError: name 'sys' is not defined
```

**Проблема:**
В начале файла есть `import subprocess` и `from pathlib import Path`, но `sys` не подключён. Используется на строке 57.

**Исправление:**
Добавить в самое начало файла (после docstring):
```python
import sys
```

---

## 3. Подобные ошибки (найдены анализом кодовой базы)

Сканирование показало **5 аналогичных случаев** — использованные имена без импорта в других файлах.

### 3.1. `views/qr_display.py` — `show_peer_selection` не импортирован
**Проблема:** Вызывается `show_peer_selection(peer_mgr)` (~строка 19), но импорт отсутствует.
**Исправление:** Добавить в импорты: `from ..views.peer_views import show_peer_selection`

### 3.2. `views/log_views.py` — `FirewalldManager` и `confirm` не импортированы
**Проблема:** 
- Строка 23: `firewall = FirewalldManager()` — класс не подключён.
- Строка 89: `if confirm("Clear all logs?"):` — функция не подключена.
**Исправление:** Добавить в начало файла:
```python
from ..firewall.firewalld import FirewalldManager
from ..cli.common import clear_screen, section_banner, pause, confirm
```

### 3.3. `commands/peer_lifecycle.py` — `SystemDetector` не импортирован
**Проблема:** Строка ~249: `SystemDetector().detect().public_ip` — класс не подключён.
**Исправление:** Добавить в глобальные импорты: `from ..system.info import SystemDetector`

### 3.4. `commands/key_rotation.py` — дубликат `import re`
**Проблема:** Строка 2: `import re` и строка 15: `import re`.
**Исправление:** Удалить один из дубликатов (строку 15).

### 3.5. `cli/logs_menu.py` — дубликат `show_header_info`
**Проблема:** `from ..cli.common import show_header_info` на строке 6 и строке 9.
**Исправление:** Убрать строку 6.

---

## 4. Сводная таблица

| # | Файл | Ошибка | Исправление |
|---|------|--------|-------------|
| 1 | `cli/common.py` | `delete_interface()` без `interface_config_path` | Добавить импорт `config_path as interface_config_path` внутри функции |
| 2 | `cli/system_info_menu.py` | `sys` не импортирован | Добавить `import sys` в начало файла |
| 3 | `views/qr_display.py` | `show_peer_selection` не импортирован | Добавить в импорты из `..views.peer_views` |
| 4 | `views/log_views.py` | `FirewalldManager` + `confirm` не импортированы | Добавить оба импорта в начало файла |
| 5 | `commands/peer_lifecycle.py` | `SystemDetector` не импортирован | Добавить в глобальные импорты |
| 6 | `commands/key_rotation.py` | Дубликат `import re` | Удалить строку 15 |
| 7 | `cli/logs_menu.py` | Дубликат `show_header_info` | Убрать строку 6 |

---

## 5. Порядок исправления (максимум 3 шага на задачу)

### Шаг 1: Исправить `cli/common.py`
- В `delete_interface()` добавить `from ..wireguard.interfaces import config_path as interface_config_path`

### Шаг 2: Исправить `cli/system_info_menu.py`
- Добавить `import sys` в начало файла

### Шаг 3: Исправить остальные 5 файлов
- `views/qr_display.py` → добавить `show_peer_selection`
- `views/log_views.py` → добавить `FirewalldManager` и `confirm`
- `commands/peer_lifecycle.py` → добавить `SystemDetector`
- `commands/key_rotation.py` → убрать дубликат `import re`
- `cli/logs_menu.py` → убрать дубликат `show_header_info`

---

## 6. Критерии приёмки

1. ✅ `Delete selected interface` (выбор `di` в manage interfaces) — не падает
2. ✅ `System Information` (выбор 5 в main menu) — не падает
3. ✅ `Show QR code` (выбор 11 в peers menu) — не падает
4. ✅ `Firewall status` (выбор 1 в diagnostics) — не падает
5. ✅ `Clear logs` (выбор 2 в logs menu) — не падает
6. ✅ `pytest` — 58/58 passed без ошибок