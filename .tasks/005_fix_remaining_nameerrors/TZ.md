# ТЗ: Исправление остающихся NameError после рефакторинга

## 1. Проблема

Приложение запускается, но **падает при выполнении конкретных действий**:
- `View configuration` → `NameError: name 'pause' is not defined`
- `Remove WireGuard` → `UnicodeDecodeError` + `NameError: name 'confirm' is not defined`
- `Manage interfaces` → `NameError: name 'configured_interfaces' is not defined`
- `Create peer` → `NameError: name 'console' is not defined`
- `Remove peer` → `NameError: name 'console' is not defined`

**Корень:** Авто-экстрактор разделил функции по файлам, но не перенёс все импорты для каждого файла. Частичные импорты Rich, `pause`, `confirm`, `configured_interfaces`.

---

## 2. Полный список ошибок

### 2.1. `commands/peer_crud.py` — отсутствует `console = Console()`

**Проблема:** Файл использует `console.print()` (строки 32, 36, 62, 66, 70, 78, 95, 113, 115, 117, 119, 123, 133, 142, 167, 169, 171, 179) — но **нигде не определён** `console = Console()`.

Строка 17 импортирует из common: `from ..cli.common import clear_screen, section_banner, pause, confirm, selected_interface, prompt_for_qr_code, display_peer_qr_code` — но **не импортирует Rich**.

**Исправление:** Добавить в начало файла (после строки 1):
```python
from rich.console import Console
console = Console()
```

**Важно:** Не использовать `from ..cli.common import console` — это создаст циклический импорт, так как `common.py` может импортировать функции из `peer_crud.py`.

---

### 2.2. `commands/peer_lifecycle.py` — отсутствует `console = Console()`

**Проблема:** Строка 6 импортирует `from rich.console import Console` и строка 7 `from rich.panel import Panel` — но **нигде нет `console = Console()`**.

Файл использует `console.print()` (строки 43, 47, 50, 73, 77, 81, 91, 98, 101, 118, 122, 127, 148, 156, 159, 176, 180, 184, 259, 271, 274, 298, 304, 309, 312).

**Исправление:** Добавить после строки 8:
```python
console = Console()
```

---

### 2.3. `commands/peer_import.py` — отсутствуют все Rich-импорты

**Проблема:** Строка 94 использует `console.print()` — но файл не импортирует Rich вообще.

**Исправление:** Добавить в начало файла (после строки 1):
```python
from rich.console import Console
console = Console()
```

---

### 2.4. `views/server_status.py` — отсутствует `pause` и `console`

**Проблема:** 
- `show_server_config()` (строка 137, 147) вызывает `pause()` — не импортирована.
- `show_server_config()` использует `console.print()` (строки 136, 142, 145) — `console` не определён.

**Исправление:** Добавить в начало файла:
```python
from rich.console import Console
console = Console()

from ..cli.common import pause
```

---

### 2.5. `cli/common.py` — функция `manage_interfaces()` использует `configured_interfaces()` без импорта

**Проблема:** Строка 280: `interfaces = configured_interfaces()` — но `configured_interfaces` не импортирована в область видимости `manage_interfaces()`.

**Исправление:** Добавить в начало `manage_interfaces()`:
```python
from ..wireguard.interfaces import configured_interfaces
```

ИЛИ добавить в глобальные импорты файла (в начало `common.py`).

---

### 2.6. `commands/lifecycle.py` — `confirm()` не импортирована

**Проблема:** Строка 17 в `remove_wireguard()` вызывает `confirm("Continue with removal?")` — но `confirm` не импортирована.

Строка 6: `from ..cli.common import clear_screen, section_banner, pause, confirm` — **уже импортирована!**

Это значит, что проблема не в `confirm` в этом файле. Проблема в сообщении пользователя: `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd1`. Это баг ввода/вывода терминала — `confirm()` получает байты вместо строк. Но затем возникает `NameError: name 'confirm' is not defined` — это **другой** файл.

Проверяю: ошибка приходит из `lifecycle.py:18`. Импорт в строке 6 есть. Значит проблема не в lifecycle.py.

Перечитываю ошибку: `File "/root/loomwg/loom/commands/lifecycle.py", line 18, in remove_wireguard → if confirm("Continue with removal?"):`. Импорт confirm есть в строке 6. Значит проблема в том, что confirm() вызывается из другого контекста.

Нет — перечитываю: ошибка **после** `UnicodeDecodeError`. Сначала `confirm()` работает, получает некорректный ввод (байт 0xd1), выбрасывает `UnicodeDecodeError`. Затем **при обработке исключения** возникает новый `NameError` — но в каком файле?

Перечитываю traceback:
```
File "lifecycle.py", line 18, in remove_wireguard
    if confirm("Continue with removal?"):
File "common.py", line 169, in confirm
    response = input(...).strip().lower()
UnicodeDecodeError
```

Значит проблема в `confirm()` в `common.py` — он падает на вводе с неверной кодировкой. Это не NameError, это UnicodeDecodeError. Это баг обработки ввода — `confirm()` не должен падать на не-UTF8 вводе.

**Исправление:** Добавить try/except в `confirm()`:
```python
def confirm(prompt: str = "Continue?") -> bool:
    """Ask for confirmation."""
    while True:
        try:
            response = input(f"\n{prompt} (y/n): ").strip().lower()
        except (UnicodeDecodeError, EOFError, OSError):
            print("\nInvalid response.")
            continue
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        print("Invalid response. Please enter 'y' or 'n'.")
```

---

## 3. Сводная таблица

| # | Файл | Проблема | Исправление |
|---|------|----------|-------------|
| 1 | `commands/peer_crud.py` | Нет `console = Console()` | Добавить `from rich.console import Console` + `console = Console()` в начало |
| 2 | `commands/peer_lifecycle.py` | Нет `console = Console()` | Добавить `console = Console()` после строки 8 |
| 3 | `commands/peer_import.py` | Нет Rich-импортов | Добавить `from rich.console import Console` + `console = Console()` в начало |
| 4 | `views/server_status.py` | Нет `pause` и `console` | Добавить `from rich.console import Console` + `console = Console()` + `from ..cli.common import pause` |
| 5 | `cli/common.py` | `manage_interfaces()` без `configured_interfaces` | Добавить `from ..wireguard.interfaces import configured_interfaces` в начало файла |
| 6 | `cli/common.py` | `confirm()` падает на UnicodeDecodeError | Добавить try/except в `confirm()` |

---

## 4. Порядок исправления

### Шаг 1: Добавить `console = Console()` в 3 command-файла
- `commands/peer_crud.py` — добавить Rich-импорт + console
- `commands/peer_lifecycle.py` — добавить `console = Console()`
- `commands/peer_import.py` — добавить Rich-импорт + console

### Шаг 2: Добавить `pause` + `console` в views
- `views/server_status.py` — добавить `pause` и `console`

### Шаг 3: Исправить `common.py`
- Добавить `configured_interfaces` в `manage_interfaces()`
- Добавить `try/except` в `confirm()` для UnicodeDecodeError

### Шаг 4: `pytest`
Убедиться что 58/58 проходят.

---

## 5. Критерии приёмки

1. ✅ `View configuration` (выбор 3 в server_menu) — не падает
2. ✅ `Remove WireGuard` (выбор 8 в server_menu) — не падает на UnicodeDecodeError
3. ✅ `Manage interfaces` (выбор 11 в server_menu) — не падает
4. ✅ `Create peer` — не падает на `console.print`
5. ✅ `Remove peer` — не падает на `console.print`
6. ✅ `pytest` — 58/58 passed