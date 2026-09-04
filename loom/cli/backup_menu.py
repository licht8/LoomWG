"""Backup menu."""
from rich.console import Console
console = Console()

from ..commands.backup_commands import create_backup, restore_backup, delete_backup
from ..views.backup_views import list_backups
from ..cli.common import show_header_info

from ..backup.manager import BackupManager
from ..logging_system.logger import LoomLogger
from ..cli.common import clear_screen, section_banner, menu_option, pause, show_header_info

def backup_menu() -> None:
    """Backup and restore menu."""
    while True:
        clear_screen()
        show_header_info()

        section_banner("Backup & Restore Menu", "Protect or recover LoomWG data")
        menu_option(1, "Create backup", "Save current LoomWG data")
        menu_option(2, "Restore backup", "Recover saved LoomWG data")
        menu_option(3, "Delete backup", "Permanently delete a backup")
        print()
        menu_option(4, "List backups", "Show available backup files")
        print("  0) Back\n")

        choice = input("Select option: ").strip()

        if choice == "1":
            create_backup()
        elif choice == "2":
            restore_backup()
        elif choice == "3":
            delete_backup()
        elif choice == "4":
            list_backups()
        elif choice == "0":
            break
        else:
            print("Invalid option.")
            pause()




