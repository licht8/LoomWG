"""Auto-extracted from cli/__init__.py"""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..wireguard.peer_manager import Peer, PeerManager
from ..wireguard.client_config import ClientConfigStore
from ..cli.common import clear_screen, pause, menu_option, selected_interface, confirm

console = Console()

def list_peers() -> None:
    """List all peers."""
    clear_screen()

    try:
        peer_mgr = PeerManager()
        peers = peer_mgr.list_peers()

        if not peers:
            console.print("[yellow]No peers configured[/yellow]")
            pause()
            return

        console.print(peer_table(peers))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()




def peer_table(peers: list[Peer]) -> Table:
    """Build a concise peer table used before peer selection actions."""
    table = Table(title="WireGuard Peers")

    table.add_column("Name", style="cyan")
    table.add_column("IPv4", style="magenta")
    table.add_column("IPv6", style="magenta")
    table.add_column("RX", style="green")
    table.add_column("TX", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Created", style="cyan")

    for peer in peers:
        status = "[green]Enabled[/green]" if peer.enabled else "[yellow]Disabled[/yellow]"
        created = peer.created_at.split("T")[0]
        rx = f"{peer.transfer_rx} B"
        tx = f"{peer.transfer_tx} B"

        table.add_row(peer.name, peer.ipv4_address, peer.ipv6_address, rx, tx, status, created)
    return table




def show_peer_selection(peer_mgr: PeerManager) -> None:
    """Display all peers before prompting for a peer name."""
    peers = peer_mgr.list_peers()
    if peers:
        console.print(peer_table(peers))
        console.print()
    else:
        console.print("[yellow]No peers configured[/yellow]")




def show_peer() -> None:
    """Show peer details."""
    clear_screen()

    try:
        peer_mgr = PeerManager()
        show_peer_selection(peer_mgr)

        try:
            name = input("Peer name: ").strip()

        except (EOFError, KeyboardInterrupt, OSError):
            console.print("[red]Input interrupted.[/red]")
            pause()
            return


        if not name:
            return

        peer = peer_mgr.get_peer(name)

        if not peer:
            console.print("[red]Peer not found[/red]")
            pause()
            return

        console.print(f"\n[bold]Peer: {peer.name}[/bold]\n")
        console.print(f"IPv4: {peer.ipv4_address}")
        console.print(f"IPv6: {peer.ipv6_address}")
        console.print(f"Public Key: {peer.public_key}")
        console.print(f"Status: {'Enabled' if peer.enabled else 'Disabled'}")
        console.print(f"Created: {peer.created_at}")

        if peer.endpoint:
            console.print(f"Endpoint: {peer.endpoint}")

        if peer.latest_handshake:
            console.print(f"Latest Handshake: {peer.latest_handshake}")

        console.print(f"Transfer RX: {peer.transfer_rx}")
        console.print(f"Transfer TX: {peer.transfer_tx}")
        console.print(f"Expiry: {peer.expires_at or 'Never'}")
        console.print(f"Revoked: {peer.revoked_at or 'No'}")
        console.print(f"Traffic samples: {len(peer.traffic_history)}")
        if peer.traffic_history:
            console.print("\n[bold]Recent traffic samples[/bold]")
            for sample in peer.traffic_history[-5:]:
                console.print(f"  {sample['timestamp']}: RX {sample['rx']} B / TX {sample['tx']} B")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()




