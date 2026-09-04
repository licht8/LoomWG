"""View functions for QR code display."""
from ..wireguard.client_config import ClientConfigStore
from ..wireguard.peer_manager import PeerManager
from ..cli.common import clear_screen, display_peer_qr_code, pause

console = None


def show_qr_code() -> None:
    """Display a saved peer config as a terminal QR code."""
    console = Console()
    
    clear_screen()
    peer_mgr = PeerManager()
    show_peer_selection(peer_mgr)
    name = input("Peer name: ").strip()
    if not name:
        return
    peer = peer_mgr.get_peer(name)
    if not peer:
        console.print("[red]Peer not found[/red]")
        pause()
        return
    config_path = ClientConfigStore().base_dir / f"{name}.conf"
    if not config_path.exists():
        console.print("[yellow]No saved client config exists for this peer.[/yellow]")
        pause()
        return
    display_peer_qr_code(name, config_path.read_text(encoding="utf-8"))
    pause()
"""View functions for QR code display."""

from ..wireguard.client_config import ClientConfigStore
from ..wireguard.peer_manager import PeerManager
from ..cli.common import clear_screen, display_peer_qr_code

console = None  # will be imported where needed


def show_qr_code() -> None:
    """Display a saved peer config as a terminal QR code."""
    from rich.console import Console
    console = Console()
    
    clear_screen()
    peer_mgr = PeerManager()
    show_peer_selection(peer_mgr)
    name = input("Peer name: ").strip()
    if not name:
        return
    peer = peer_mgr.get_peer(name)
    if not peer:
        console.print("[red]Peer not found[/red]")
        pause()
        return
    config_path = ClientConfigStore().base_dir / f"{name}.conf"
    if not config_path.exists():
        console.print("[yellow]No saved client config exists for this peer.[/yellow]")
        pause()
        return
    display_peer_qr_code(name, config_path.read_text(encoding="utf-8"))
    pause()