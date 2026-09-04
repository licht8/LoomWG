"""Auto-extracted from cli/__init__.py"""
from ..firewall.firewalld import FirewalldManager
from ..wireguard.manager import WireGuardManager
from ..wireguard.server_config import ServerConfig
from ..wireguard.interfaces import config_path as interface_config_path

from ..logging_system.logger import LoomLogger
from ..cli.common import clear_screen, section_banner, menu_option, pause

def firewall_menu() -> None:
    """Firewall management menu."""
    while True:
        clear_screen()
        show_header_info()

        print("Firewall Menu\n")
        menu_option(1, "Show status", "View firewalld state and VPN port")
        print()
        menu_option(2, "Start firewalld", "Start the firewall service", "systemctl start firewalld")
        menu_option(3, "Open WireGuard port", "Allow the configured UDP port", "firewall-cmd --add-port …")
        print()
        menu_option(4, "Enable on boot", "Start firewalld automatically", "systemctl enable firewalld")
        print("  0) Back\n")

        choice = input("Select option: ").strip()

        if choice == "1":
            show_firewall_status()
        elif choice == "2":
            start_firewall()
        elif choice == "3":
            open_wg_port()
        elif choice == "4":
            enable_firewall()
        elif choice == "0":
            break
        else:
            print("Invalid option.")
            pause()




