"""Peer expiry management."""
from datetime import datetime
from pathlib import Path

from rich.console import Console
console = Console()

from ..wireguard.peer_manager import PeerManager
from ..wireguard.client_config import ClientConfigStore
from ..wireguard.config_generator import ConfigGenerator
from ..wireguard.interfaces import config_path as interface_config_path
from ..cli.common import selected_interface
from ..cli.common import clear_screen, section_banner, pause, confirm

from datetime import datetime
from pathlib import Path

from ..wireguard.peer_manager import PeerManager
from ..wireguard.client_config import ClientConfigStore
from ..cli.common import clear_screen, section_banner, pause, confirm

def enforce_expired_peers() -> None:
    """Revoke expired peers from persistent config and the running interface."""
    peer_mgr = PeerManager()
    generator = ConfigGenerator()
    interface = selected_interface()
    config_path = interface_config_path(interface)
    for peer in peer_mgr.list_enabled_peers():
        try:
            expired = peer.expires_at and datetime.fromisoformat(peer.expires_at) <= datetime.now()
        except ValueError:
            expired = False
        if expired:
            WireGuardManager().remove_peer_from_interface(interface, peer.public_key)
            if config_path.exists():
                generator.remove_peer_from_server_config(config_path, peer.public_key)
            peer_mgr.disable_peer(peer.name)




def download_peer_config() -> None:
    """Make an existing client config and a fresh QR image available again."""
    clear_screen()
    peer_mgr = PeerManager()
    show_peer_selection(peer_mgr)
    name = input("Peer name: ").strip()
    path = ClientConfigStore().base_dir / f"{name}.conf"
    if not peer_mgr.get_peer(name):
        console.print("[red]Peer not found[/red]")
    elif not path.exists():
        console.print("[yellow]No saved client config exists. Private keys are not stored after creation, so create a replacement peer instead.[/yellow]")
    else:
        content = path.read_text(encoding="utf-8")
        qr_path = ClientConfigStore().save_qr_code(name, content)
        console.print(f"[green]✓ Client configuration: {path}[/green]")
        if qr_path: console.print(f"[green]✓ QR code regenerated: {qr_path}[/green]")
    pause()




def set_peer_expiry() -> None:
    """Set an ISO date expiry for a peer, or clear it."""
    clear_screen()
    section_banner("Set peer expiry", f"Manage client access expiry on {selected_interface()}")
    peer_mgr = PeerManager()
    show_peer_selection(peer_mgr)
    name = input("Peer name: ").strip()
    peer = peer_mgr.get_peer(name)
    if not peer:
        console.print("[red]Peer not found[/red]")
    else:
        raw = input("Expiry (YYYY-MM-DD, blank to clear): ").strip()
        try:
            expiry = datetime.fromisoformat(raw).replace(hour=23, minute=59, second=59).isoformat() if raw else None
            peer_mgr.set_expiry(name, expiry)
            console.print(f"[green]✓ Expiry {'cleared' if not expiry else 'set to ' + expiry}[/green]")
        except ValueError:
            console.print("[red]Use YYYY-MM-DD.[/red]")
    pause()




