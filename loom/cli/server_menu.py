"""Auto-extracted from cli/__init__.py"""
from ..wireguard.manager import WireGuardManager
from ..wireguard.server_config import ServerConfig
from ..wireguard.interfaces import config_path as interface_config_path

from ..system.services import ServiceManager
from ..logging_system.logger import LoomLogger
from ..cli.common import clear_screen, show_header_info, menu_option, pause, confirm, selected_interface as selected_wg

def server_menu() -> None:
    """Server management menu."""
    wg_manager = WireGuardManager()
    logger = LoomLogger()

    while True:
        clear_screen()
        show_header_info()

        print(f"Server Menu (selected: {selected_interface()})\n")
        menu_option(1, "Server status", "Live WireGuard runtime activity")
        menu_option(2, "Configure server", "Create the initial wg0 configuration")
        menu_option(3, "View configuration", "Display the saved wg0.conf file")
        print()
        menu_option(4, "Start WireGuard", "Bring up the VPN interface", "wg-quick up wg0")
        menu_option(5, "Stop WireGuard", "Bring down the VPN interface", "wg-quick down wg0")
        menu_option(6, "Restart WireGuard", "Restart the VPN interface", "wg-quick down/up wg0")
        print()
        menu_option(7, "Enable on boot", "Start WireGuard automatically", "systemctl enable wg-quick@wg0")
        menu_option(8, "Remove WireGuard", "Remove LoomWG-managed WireGuard state", "systemctl disable --now wg-quick@wg0")
        menu_option(9, "Reinstall WireGuard", "Remove and install a fresh setup", "dnf remove/install wireguard-tools")
        print()
        menu_option(10, "Rotate server keys", "Replace the server keypair safely with backup and validation")
        menu_option(11, "Manage interfaces", "Create, select, or delete WireGuard interfaces")
        print()
        print("  0) Back\n")

        choice = input("Select option: ").strip()

        interface = selected_interface()
        if choice == "1":
            show_server_status()
        elif choice == "2":
            configure_server()
        elif choice == "3":
            show_server_config()
        elif choice == "4":
            if wg_manager.start(interface):
                console.print("[green]✓ WireGuard started[/green]")
                logger.info("WireGuard started", "server")
            else:
                console.print("[red]✗ Failed to start WireGuard[/red]")
                logger.error("Failed to start WireGuard", "server")

            pause()
        elif choice == "5":
            if wg_manager.stop(interface):
                console.print("[green]✓ WireGuard stopped[/green]")
                logger.info("WireGuard stopped", "server")
            else:
                console.print("[red]✗ Failed to stop WireGuard[/red]")
                logger.error("Failed to stop WireGuard", "server")

            pause()
        elif choice == "6":
            if wg_manager.restart(interface):
                console.print("[green]✓ WireGuard restarted[/green]")
                logger.info("WireGuard restarted", "server")
            else:
                console.print("[red]✗ Failed to restart WireGuard[/red]")
                logger.error("Failed to restart WireGuard", "server")

            pause()
        elif choice == "7":
            services = ServiceManager()

            if services.enable(f"wg-quick@{interface}"):
                console.print("[green]✓ Enabled on boot[/green]")
                logger.info("WireGuard enabled on boot", "server")
            else:
                console.print("[red]✗ Failed to enable on boot[/red]")

            pause()
        elif choice == "8":
            remove_wireguard()
        elif choice == "9":
            reinstall_wireguard()
        elif choice == "10":
            rotate_server_keys()
        elif choice == "11":
            manage_interfaces()
        elif choice == "0":
            break
        else:
            print("Invalid option.")
            pause()




