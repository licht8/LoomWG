"""Auto-extracted from cli/__init__.py"""
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
console = Console()

import re
import subprocess

from ..wireguard.peer_manager import PeerManager
from ..wireguard.key_manager import KeyManager
from ..wireguard.config_generator import ConfigGenerator
from ..wireguard.client_config import ClientConfigStore
from ..wireguard.server_config import ServerConfig
from ..wireguard.interfaces import config_path as interface_config_path

from ..wireguard.manager import WireGuardManager
from ..system.info import SystemDetector
from ..wireguard.peer_manager import Peer
from ..cli.common import selected_interface, clear_screen, section_banner, pause, confirm

def import_server_peers() -> None:
    """Import peers and create replacement client artifacts."""
    clear_screen()
    section_banner("Import peers", f"Import clients from {selected_interface()}")
    peer_mgr = PeerManager()
    interface = selected_interface()
    config_path = interface_config_path(interface)
    entries = ConfigGenerator.parse_server_peers(config_path)
    server_cfg = ServerConfig.from_file(config_path)
    detector = SystemDetector().detect()
    manager = WireGuardManager()
    generator = ConfigGenerator()
    client_store = ClientConfigStore(interface_name=interface)
    original_config = config_path.read_text(encoding="utf-8") if config_path.exists() else None
    original_peers = dict(peer_mgr.peers)
    changed_live: list[tuple[str, str, str, str]] = []
    created_artifacts: list[tuple[Path, Path | None]] = []
    imported = 0
    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>6.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
    ) as progress:
        task = progress.add_task("[cyan]Importing peers...", total=len(entries))

        for index, entry in enumerate(entries, 1):
            # Skip already imported peers
            if peer_mgr.get_peer_by_public_key(entry["public_key"]):
                progress.advance(task)
                continue
            addresses = [item.strip() for item in entry["allowed_ips"].split(",")]
            ipv4 = next((item for item in addresses if "." in item), "")
            ipv6 = next((item for item in addresses if ":" in item), "")
            if not ipv4 or not ipv6:
                progress.advance(task)
                continue
            name = f"imported-{index}"
            while peer_mgr.peer_exists(name):
                name += "-x"

            # The original client private key cannot be recovered from wg0.conf.
            # Generate a replacement keypair and keep the server/client entries aligned.
            keypair = KeyManager.generate_keypair()
            try:
                if not generator.remove_peer_from_server_config(config_path, entry["public_key"]):
                    raise RuntimeError(f"Could not replace peer '{name}' in the server configuration")
                if not generator.append_peer_to_server_config(
                    config_path, keypair.public_key, ipv4, ipv6
                ):
                    raise RuntimeError(f"Could not add peer '{name}' to the server configuration")

                candidate = config_path.read_text(encoding="utf-8")
                valid, errors = generator.validate_config(candidate)
                server_valid, server_errors = generator.validate_server_config(candidate)
                if not (valid and server_valid):
                    raise RuntimeError("; ".join(errors + server_errors))

                if manager.is_interface_active(interface):
                    if not manager.remove_peer_from_interface(interface, entry["public_key"]):
                        raise RuntimeError(f"Could not remove the old key for '{name}'")
                    if not manager.add_peer_to_interface(
                        interface, keypair.public_key, ipv4, client_ipv6=ipv6
                    ):
                        raise RuntimeError(f"Could not add the replacement key for '{name}'")
                    changed_live.append((entry["public_key"], keypair.public_key, ipv4, ipv6))

                peer_conf = generator.generate_peer_config(
                    peer_ipv4=ipv4,
                    peer_ipv6=ipv6,
                    private_key=keypair.private_key,
                    server_public_key=server_cfg.public_key,
                    server_endpoint=detector.public_ip or "YOUR_SERVER_IP",
                    server_port=server_cfg.listen_port,
                    dns_primary=server_cfg.dns_primary,
                    dns_secondary=server_cfg.dns_secondary,
                )
                peer_mgr.peers[name] = Peer(
                    name=name,
                    ipv4_address=ipv4,
                    ipv6_address=ipv6,
                    public_key=keypair.public_key,
                    private_key=keypair.private_key,
                )
                if not peer_mgr.save():
                    raise RuntimeError(f"Could not save imported peer '{name}'")
                config_artifact = client_store.save_peer_config(name, peer_conf)
                qr_artifact = client_store.save_qr_code(name, peer_conf)
                created_artifacts.append((config_artifact, qr_artifact))
                if qr_artifact is None:
                    progress.update(task, description=f"[yellow]Warning: QR unavailable for '{name}'[/]")
                imported += 1

                progress.update(task, advance=1, description=f"[green]Imported: {name}[/]")
            except Exception as exc:
                progress.update(task, description=f"[red]Error importing '{name}'[/]")
                if original_config is not None:
                    config_path.write_text(original_config, encoding="utf-8")
                    config_path.chmod(0o600)
                peer_mgr.peers = original_peers
                peer_mgr.save()
                for old_key, new_key, old_ipv4, old_ipv6 in reversed(changed_live):
                    manager.remove_peer_from_interface(interface, new_key)
                    manager.add_peer_to_interface(
                        interface, old_key, old_ipv4, client_ipv6=old_ipv6
                    )
                for config_artifact, qr_artifact in created_artifacts:
                    config_artifact.unlink(missing_ok=True)
                    if qr_artifact is not None:
                        qr_artifact.unlink(missing_ok=True)
                console.print(f"[red]Could not import '{name}': {exc}[/red]")
                break

    # Final result
    if imported:
        from rich.panel import Panel
        from rich.text import Text
        console.print(Panel(
            Text.assemble(f"✓ Imported {imported} peer(s) successfully", style="green"),
            border_style="green",
        ))
    else:
        console.print("[yellow]No new peers to import.[/]")
    pause()




