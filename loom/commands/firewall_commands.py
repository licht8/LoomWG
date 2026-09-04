"""Firewall commands."""
import subprocess

from rich.console import Console
console = Console()

from ..firewall.firewalld import FirewalldManager
from ..wireguard.server_config import ServerConfig
from ..wireguard.interfaces import config_path as interface_config_path
from ..cli.common import selected_interface
from ..logging_system.logger import LoomLogger
from ..cli.common import clear_screen, section_banner, pause

import subprocess

from ..firewall.firewalld import FirewalldManager
from ..wireguard.server_config import ServerConfig
from ..wireguard.interfaces import config_path

from ..logging_system.logger import LoomLogger
from ..cli.common import clear_screen, section_banner, pause

def start_firewall() -> None:
    """Start firewall."""
    try:
        firewall = FirewalldManager()

        if firewall.start():
            console.print("[green]✓ Firewall started[/green]")
        else:
            console.print("[red]✗ Failed to start firewall[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()




def enable_firewall() -> None:
    """Enable firewall on boot."""
    try:
        firewall = FirewalldManager()

        if firewall.enable():
            console.print("[green]✓ Firewall enabled on boot[/green]")
        else:
            console.print("[red]✗ Failed to enable firewall[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()




def open_wg_port() -> None:
    """Open WireGuard port in firewall."""
    try:
        firewall = FirewalldManager()
        config = ServerConfig.defaults()

        if firewall.open_port(config.listen_port):
            console.print(f"[green]✓ Port {config.listen_port}/UDP opened[/green]")
        else:
            console.print("[red]✗ Failed to open port[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()




