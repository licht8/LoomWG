"""Diagnostics menu."""
from rich.console import Console
console = Console()

from ..diagnostics import FirewallDiagnostics, NetworkDiagnostics, SystemDiagnostics, WireGuardDiagnostics
from ..wireguard.manager import WireGuardManager
from ..wireguard.server_config import ServerConfig
from ..wireguard.interfaces import config_path

from ..commands.diagnostics_commands import (
    run_full_diagnostics,
    run_system_diagnostics,
    run_network_diagnostics,
    run_wireguard_diagnostics,
    run_firewall_diagnostics,
)

from ..cli.common import clear_screen, section_banner, menu_option, pause, show_header_info

def diagnostics_menu() -> None:
    """Diagnostics menu."""
    while True:
        clear_screen()
        show_header_info()

        print("Diagnostics Menu\n")
        menu_option(1, "Full health check", "Run every diagnostic check")
        print()
        menu_option(2, "System diagnostics", "Check OS and service prerequisites")
        menu_option(3, "Network diagnostics", "Check routes and connectivity")
        menu_option(4, "WireGuard diagnostics", "Check the VPN interface")
        menu_option(5, "Firewall diagnostics", "Check firewall access and NAT")
        print()
        print("  0) Back\n")

        try:
            choice = input("Select option: ").strip()
        except (EOFError, KeyboardInterrupt, OSError):
            console.print("[red]Input interrupted.[/red]")
            pause()
            return


        if choice == "1":
            run_full_diagnostics()
        elif choice == "2":
            run_system_diagnostics()
        elif choice == "3":
            run_network_diagnostics()
        elif choice == "4":
            run_wireguard_diagnostics()
        elif choice == "5":
            run_firewall_diagnostics()
        elif choice == "0":
            break
        else:
            print("Invalid option.")
            pause()




