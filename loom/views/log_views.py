"""Auto-extracted from cli/__init__.py"""
import re
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.rule import Rule
from rich.text import Text

from ..logging_system.logger import LoomLogger
from ..cli.common import clear_screen, section_banner, pause, confirm
from ..wireguard.manager import WireGuardManager
from ..wireguard.server_config import ServerConfig
from ..firewall.firewalld import FirewalldManager

console = Console()


def show_firewall_status() -> None:
    """Show firewall status."""
    clear_screen()
    section_banner("Show status", "View firewalld and WireGuard port status")

    try:
        firewall = FirewalldManager()

        console.print("[bold]Firewall Status[/bold]\n")
        console.print(f"Running: {'[green]Yes[/green]' if firewall.is_running() else '[red]No[/red]'}")
        console.print(f"Enabled: {'[green]Yes[/green]' if firewall.is_enabled() else '[red]No[/red]'}")

        config = ServerConfig.defaults()

        if firewall.is_running():
            port_open = firewall.is_port_open(config.listen_port)
            masq = firewall.is_masquerading_enabled()

            console.print(
                f"Port {config.listen_port}/UDP: {'[green]Open[/green]' if port_open else '[red]Closed[/red]'}"
            )
            console.print(
                f"Masquerading: {'[green]Enabled[/green]' if masq else '[red]Disabled[/red]'}"
            )
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()



def view_logs() -> None:
    """View recent logs grouped by severity."""
    clear_screen()

    try:
        logger = LoomLogger()
        logs = logger.list_recent(50)

        if not logs:
            console.print("[yellow]No logs found[/yellow]")
            pause()
            return

        # Group logs by level
        by_level = {"ERROR": [], "WARNING": [], "INFO": []}
        for log in logs:
            level = log.get("level", "INFO")
            if level in by_level:
                by_level[level].append(log)

        # Print each group in a styled panel
        for level, level_logs in by_level.items():
            if not level_logs:
                continue

            color = {"ERROR": "red", "WARNING": "yellow", "INFO": "green"}.get(level, "white")
            icon = {"ERROR": "[red]\u2717[/red]", "WARNING": "[yellow]\u26a0[/yellow]", "INFO": "[green]\u2713[/green]"}.get(level, "[dim]\u2022[/dim]")

            panel_title = Text.assemble(
                Text(icon), f" {level} ({len(level_logs)})",
                style=f"bold {color}",
            )

            lines = []
            for log in level_logs[-10:]:  # Show last 10 per level
                ts = log.get("timestamp", "")[:19]
                msg = log.get("message", "")
                cat = log.get("category", "")
                lines.append(f"[dim]{ts}[/] [{cat}] {msg}")

            console.print(Panel(
                "\n".join(lines),
                title=panel_title,
                border_style=color,
                padding=(0, 1),
            ))
            console.print()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()



def clear_logs() -> None:
    """Clear all logs."""
    if confirm("Clear all logs? This cannot be undone."):
        try:
            logger = LoomLogger()

            if logger.clear_logs():
                console.print("[green]✓ Logs cleared[/green]")
            else:
                console.print("[red]✗ Failed to export logs[/red]")

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    pause()



def export_logs() -> None:
    """Export logs to file."""
    clear_screen()

    try:
        try:
            filename = input("Export filename (default: loomwg_logs.json): ").strip()

        except (EOFError, KeyboardInterrupt, OSError):
            console.print("[red]Input interrupted.[/red]")
            pause()
            return


        if not filename:
            filename = "loomwg_logs.json"

        logger = LoomLogger()
        export_path = Path(filename)

        if logger.export_logs(export_path):
            console.print(f"[green]✓ Logs exported to {filename}[/green]")
        else:
            console.print("[red]✗ Failed to export logs[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()