"""Auto-extracted from cli/__init__.py"""
from rich.console import Console
from rich.table import Table

from ..wireguard.manager import WireGuardManager
from ..backup.manager import BackupManager
from ..cli.common import clear_screen, section_banner, pause

console = Console()

def list_backups() -> None:
    """List available backups."""
    clear_screen()

    try:
        backup_mgr = BackupManager()
        backups = backup_mgr.list_backups()

        if not backups:
            console.print("[yellow]No backups found[/yellow]")
            pause()
            return

        table = Table(title="Available Backups")

        table.add_column("Filename", style="cyan")
        table.add_column("Created", style="yellow")

        for filename, created in backups:
            table.add_row(filename, created.strftime("%Y-%m-%d %H:%M:%S"))

        console.print(table)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()




