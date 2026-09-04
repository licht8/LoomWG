"""Auto-extracted from cli/__init__.py"""
import os
import subprocess
from pathlib import Path

from ..wireguard.manager import WireGuardManager
from ..wireguard.peer_manager import Peer, PeerManager
from ..wireguard.key_manager import KeyManager
from ..wireguard.config_generator import ConfigGenerator
from ..wireguard.client_config import ClientConfigStore
from ..logging_system.logger import LoomLogger
from ..wireguard.server_config import ServerConfig
from ..wireguard.ip_allocator import IPAllocator
from ..wireguard.interfaces import config_path

from ..cli.common import clear_screen, section_banner, pause, confirm, selected_interface, prompt_for_qr_code, display_peer_qr_code

def create_peer() -> None:
    """Create a new peer."""
    clear_screen()

    section_banner("Create peer", f"Create a client on {selected_interface()}")

    try:
        peer_mgr = PeerManager()

        # Get peer name
        name = input("Peer name: ").strip()

        if not name:
            console.print("[red]Name cannot be empty[/red]")
            pause()
            return

        if peer_mgr.peer_exists(name):
            console.print("[red]Peer already exists[/red]")
            pause()
            return

        # Get the selected interface config to allocate IPs
        interface = selected_interface()
        config_path = interface_config_path(interface)

        if not config_path.exists():
            console.print("[red]Server not configured yet[/red]")
            pause()
            return

        config = ServerConfig.from_file(config_path)

        allocator = IPAllocator(config.ipv4_network, config.ipv6_network)

        # Get used IPs
        used_ips = [p.ipv4_address for p in peer_mgr.list_peers()]
        used_ips += [p.ipv6_address for p in peer_mgr.list_peers()]

        # Allocate IPs
        ipv4 = allocator.get_next_ipv4(used_ips)
        ipv6 = allocator.get_next_ipv6(used_ips)

        if not ipv4 or not ipv6:
            console.print("[red]Could not allocate IP addresses[/red]")
            pause()
            return

        console.print(f"\nAllocated IPv4: {ipv4}")
        console.print(f"Allocated IPv6: {ipv6}\n")

        # Generate keys
        console.print("[bold]Generating keys...[/bold]")

        key_mgr = KeyManager()
        keypair = key_mgr.generate_keypair()
        detector = SystemDetector()
        gen = ConfigGenerator()
        wg_manager = WireGuardManager()

        console.print("[green]✓ Keys generated[/green]\n")

        # Create peer
        peer = Peer(
            name=name,
            ipv4_address=ipv4,
            ipv6_address=ipv6,
            public_key=keypair.public_key,
            private_key=keypair.private_key,
        )

        validation_result = peer_mgr.validate_peer_configuration(
            peer,
            vpn_networks=[config.ipv4_network, config.ipv6_network],
            server_addresses=[config.get_ipv4_server_address(), config.get_ipv6_server_address()],
        )
        if not validation_result.valid:
            console.print("[red]Peer validation failed before applying the new configuration:[/red]")
            for issue in validation_result.errors:
                console.print(f"  - {issue}")
            pause()
            return

        logger = LoomLogger()

        peer_result = wg_manager.add_peer_with_result(
            interface,
            peer.public_key,
            peer.ipv4_address,
            client_ipv6=peer.ipv6_address,
            logger=logger,
        )
        runtime_ok = peer_result.success

        if not runtime_ok:
            console.print(f"[red]✗ Failed to add peer to the running WireGuard interface {interface}[/red]")
            if peer_result.interface_present:
                console.print(f"[yellow]{interface} is running, but the peer was not accepted.[/yellow]")
                console.print(f"Return code: {peer_result.return_code}")
                console.print(f"stdout: {peer_result.stdout or '<empty>'}")
                console.print(f"stderr: {peer_result.stderr or '<empty>'}")
            elif peer_result.interface_error:
                console.print("[yellow]WireGuard runtime inspection failed.[/yellow]")
                console.print(f"stderr: {peer_result.stderr or '<empty>'}")
            else:
                console.print(f"[yellow]{interface} is not present in the WireGuard runtime.[/yellow]")
            logger.error(
                "Peer not marked as created because runtime registration failed",
                "peer",
                details=f"peer_name={name}, public_key={peer.public_key}, ipv4={peer.ipv4_address}, interface={interface}, interface_status={'not active' if not wg_manager.is_interface_active(interface) else 'runtime failed'}",
            )
            pause()
            return

        if not peer_mgr.add_peer(peer):
            console.print("[red]✗ Failed to save peer after successful runtime registration[/red]")
            logger.error(
                "Peer runtime registration succeeded but database save failed",
                "peer",
                details=f"peer_name={name}, public_key={peer.public_key}",
            )
            pause()
            return

        console.print(f"[green]✓ Peer '{name}' created[/green]")

        server_config_path = interface_config_path(interface)
        gen.append_peer_to_server_config(
            server_config_path,
            peer.public_key,
            peer.ipv4_address,
            peer.ipv6_address,
        )

        store = ClientConfigStore()
        peer_conf = gen.generate_peer_config(
            peer_ipv4=peer.ipv4_address,
            peer_ipv6=peer.ipv6_address,
            private_key=peer.private_key,
            server_public_key=config.public_key or "",
            server_endpoint=detector.detect().public_ip or "YOUR_SERVER_IP",
            server_port=config.listen_port,
            dns_primary=config.dns_primary,
            dns_secondary=config.dns_secondary,
        )

        config_path = store.save_peer_config(name, peer_conf)
        qr_path = store.save_qr_code(name, peer_conf)

        console.print(f"[green]✓ Client config saved to {config_path}[/green]")
        if qr_path:
            console.print(f"[green]✓ QR code saved to {qr_path}[/green]")
        else:
            console.print("[yellow]Warning: QR image generation is unavailable; install qrcode to save PNG assets.[/yellow]")

        if prompt_for_qr_code(name):
            display_peer_qr_code(name, peer_conf)

        logger.log_peer_created(name, ipv4, ipv6)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()




