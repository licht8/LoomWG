# ТЗ: Исправление ошибок после рефакторинга cli.py

## 1. Суть проблемы

После рефакторинга `cli.py` (2604 → 106 строк) приложение падает при запуске.

### Ошибка №1 (критическая, блокирующая запуск)

```
File "/root/loomwg/loom/cli/common.py", line 254, in show_header_info
    if wg_manager.is_installed():
AttributeError: 'WireGuardInstaller' object has no attribute 'is_installed'
```

**Корень:** В `show_header_info()` создан объект `WireGuardInstaller` вместо `WireGuardManager`.
- `WireGuardInstaller` — класс для УСТАНОВКИ пакета WireGuard (методы: `install()`, `_install_packages()` и т.д.)
- `WireGuardManager` — класс для УПРАВЛЕНИЯ интерфейсом (методы: `is_installed()`, `get_interfaces()`, `start()`, `stop()`)

**Где:** `loom/cli/common.py`, строки 243, 247

---

## 2. Полный список ошибок в файлах после рефакторинга

### 2.1. `loom/cli/common.py`

**Ошибка:** `WireGuardInstaller` вместо `WireGuardManager` в `show_header_info()` (строки 243, 247)

```python
# ТЕКУЩИЙ КОД (ПЛОХО):
from ..wireguard.installer import WireGuardInstaller
...
wg_manager = WireGuardInstaller()
if wg_manager.is_installed():       # ← AttributeError!
    interfaces = wg_manager.get_interfaces()
```

```python
# ПРАВИЛЬНО:
from ..wireguard.manager import WireGuardManager
...
wg_manager = WireGuardManager()
if wg_manager.is_installed():
    interfaces = wg_manager.get_interfaces()
```

---

### 2.2. `loom/commands/configure_server.py`

**Ошибка:** Не хватает импортов. Файл использует `console.print()`, `LoomLogger`, `FirewalldManager`, `NetworkManager`, `subprocess.run`, `ip_network`, но они не импортированы.

**Неимпортированные:**
| Имя | Требуется для |
|-----|---------------|
| `console` | `console.print()` — строки 24, 34, 40, 54, 65, 70, 73, 93, 96, 106, 110, 117, 122, 132, 134, 137, 141, 148, 155, 157 |
| `LoomLogger` | `LoomLogger()` — строка 113 |
| `FirewalldManager` | `FirewalldManager()` — строка 125 |
| `NetworkManager` | `NetworkManager()` — строка 147 |
| `subprocess` | `subprocess.run()` — строки 225, 239 |
| `ip_network` | `ip_network()` — строка 231 |

**Мусор:** Импорт `WireGuardInstaller` (строка 9) — НЕНУЖНЫЙ, класс не используется в файле.

---

### 2.3. `loom/commands/install_wireguard.py`

**Ошибка:** Не хватает импортов.

**Неимпортированные:**
| Имя | Требуется для |
|-----|---------------|
| `selected_interface` | Строка 21 — используется в `install_wireguard()` |
| `confirm` | Строка 46 — используется для подтверждения установки |
| `console` | `console.print()` — множество строк |
| `WireGuardManager` | Строка 122 — нужен для `start_with_result()` |
| `FirewalldManager` | Строка 110 — нужен для firewall |
| `NetworkManager` | Строка 117 — нужен для IP forwarding |

---

### 2.4. `loom/commands/key_rotation.py`

**Ошибка:** Не хватает импортов. Файл использует множество функций и классов без импорта.

**Неимпортированные:**
| Имя | Требуется для |
|-----|---------------|
| `re` | `re.sub()` — строка 66 |
| `BackupManager` | `BackupManager()` — строка 51 |
| `LoomLogger` | `LoomLogger()` — строки 105, 134 |
| `console` | `console.print()` — множество строк |
| `normalize_wireguard_config` | Строки 30, 65, 72, 85, 126 |
| `repair_wireguard_config_file` | Строка 30 |

**Мусор:** Импорт `WireGuardInstaller` (строка 12) — НЕНУЖНЫЙ, класс не используется в файле.

---

### 2.5. `loom/commands/lifecycle.py`

**Ошибка:** Мусорные импорты (не используются).

```python
from ..wireguard.manager import WireGuardManager  # ← НЕ используется
from ..wireguard.installer import WireGuardInstaller  # ← НЕ используется
```

Классы `WireGuardManager` и `WireGuardInstaller` не вызываются в этом файле — это лишние импорты от авто-экстракции.

---

## 3. Таблица всех исправлений

| Файл | Что исправить | Кол-во строк |
|------|--------------|--------------|
| `cli/common.py` | `WireGuardInstaller` → `WireGuardManager` в `show_header_info()` | 2 |
| `commands/configure_server.py` | Добавить 6 отсутствующих импортов, убрать `WireGuardInstaller` | 7 |
| `commands/install_wireguard.py` | Добавить 6 отсутствующих импортов | 6 |
| `commands/key_rotation.py` | Добавить 6 отсутствующих импортов, убрать `WireGuardInstaller` | 7 |
| `commands/lifecycle.py` | Убрать 2 неиспользуемых импорта | 2 |

---

## 4. Порядок исправления

### Шаг 1: Исправить блокирующую ошибку запуска
- `cli/common.py` — заменить `WireGuardInstaller` на `WireGuardManager`
- Запустить `python -c "from loom.cli import main_menu"` — приложение должно стартовать

### Шаг 2: Добавить недостающие импорты
- `commands/configure_server.py` — добавить `console`, `LoomLogger`, `FirewalldManager`, `NetworkManager`, `subprocess`, `ip_network`
- `commands/install_wireguard.py` — добавить `selected_interface`, `confirm`, `console`, `WireGuardManager`, `FirewalldManager`, `NetworkManager`
- `commands/key_rotation.py` — добавить `re`, `BackupManager`, `LoomLogger`, `console`, `normalize_wireguard_config`, `repair_wireguard_config_file`

### Шаг 3: Убрать мусорные импорты
- `commands/configure_server.py` — убрать `WireGuardInstaller`
- `commands/key_rotation.py` — убрать `WireGuardInstaller`
- `commands/lifecycle.py` — убрать `WireGuardManager` и `WireGuardInstaller`

### Шаг 4: Запустить `pytest`
- Убедиться что 58/58 тестов проходят

---

## 5. Критерии приёмки

1. ✅ `python -c "from loom.cli import main_menu"` — без ошибок
2. ✅ `pytest` — 58/58 passed
3. ✅ Нет `AttributeError` при запуске приложения
4. ✅ Нет неиспользуемых импортов
5. ✅ Все `console.print()`, `subprocess.run()`, `LoomLogger()` корректно импортированы