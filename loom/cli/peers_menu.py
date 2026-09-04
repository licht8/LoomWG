"""Peers menu."""
from rich.console import Console
console = Console()

from ..views.peer_views import list_peers, peer_table, show_peer_selection
from ..views.qr_display import show_qr_code
from ..commands.peer_crud import create_peer
from ..commands.peer_lifecycle import disable_peer, enable_peer, revoke_peer, rotate_peer_keys, remove_peer
from ..commands.peer_expiry import set_peer_expiry, enforce_expired_peers, download_peer_config
from ..commands.peer_import import import_server_peers
from ..cli.common import show_header_info

from ..wireguard.manager import WireGuardManager
from ..wireguard.peer_manager import PeerManager
from ..wireguard.client_config import ClientConfigStore
from ..logging_system.logger import LoomLogger
from ..cli.common import clear_screen, section_banner, menu_option, pause, selected_interface, show_header_info

def peers_menu() -> None:
    """Peers management menu."""
    while True:
        clear_screen()
        enforce_expired_peers()
        show_header_info()

        print(f"Peers Menu (selected: {selected_interface()})\n")
        menu_option(1, "Create peer", "Add a new VPN client")
        menu_option(2, "Remove peer", "Delete a VPN client")
        print()
        menu_option(3, "Enable peer", "Add client to config and live interface", "wg set wg0 peer …")
        menu_option(4, "Disable peer", "Remove client from config and live interface", "wg set wg0 peer … remove")
        print()
        menu_option(5, "List peers", "Show all configured clients")
        menu_option(6, "Show peer", "View details for one client")
        print()
        menu_option(7, "Set peer expiry", "Set or clear automatic access expiry")
        menu_option(8, "Revoke peer", "Disable and retain a peer record with audit history")
        menu_option(9, "Rotate peer keys", "Generate a fresh keypair and update the peer config")
        print()
        menu_option(10, "Import peers", "Add peers from the selected interface configuration")
        menu_option(11, "Show QR code", "Display a saved peer config as a terminal QR code")
        print()
        print("  0) Back\n")

        choice = input("Select option: ").strip()

        if choice == "1":
            create_peer()
        elif choice == "2":
            remove_peer()
        elif choice == "3":
            enable_peer()
        elif choice == "4":
            disable_peer()
        elif choice == "5":
            list_peers()
        elif choice == "6":
            show_peer()
        elif choice == "7":
            set_peer_expiry()
        elif choice == "8":
            revoke_peer()
        elif choice == "9":
            rotate_peer_keys()
        elif choice == "10":
            import_server_peers()
        elif choice == "11":
            show_qr_code()
        elif choice == "0":
            break
        else:
            print("Invalid option.")
            pause()




