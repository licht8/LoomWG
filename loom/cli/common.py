"""Common UI utilities used across all LoomWG menus."""

import os

from rich.console import Console
from rich.panel import Panel

from ..system.info import SystemDetector
from ..wireguard.interfaces import get_selected_interface, set_selected_interface

console = Console()

__all__ = [
    "clear_screen",
    "pause",
    "confirm",
    "menu_option",
    "show_banner",
    "check_root",
    "show_header_info",
    "section_banner",
    "selected_interface",
    "select_interface",
]


def selected_interface() -> str:
    """Return the interface selected for the current CLI workflow."""
    return get_selected_interface()


def select_interface() -> None:
    """Select a configured WireGuard interface for subsequent operations."""
    from ..wireguard.interfaces import configured_interfaces
    from ..wireguard.interfaces import set_selected_interface as _set_selected
    from .common import create_interface as _create_interface, pause as _pause, selected_interface as _selected

    interfaces = configured_interfaces()
    console.print("\n[bold]WireGuard Interfaces[/bold]")
    for index, name in enumerate(interfaces, 1):
        marker = " (selected)" if name == _selected() else ""
        console.print(f"{index}. {name}{marker}")
    console.print(f"{len(interfaces) + 1}. Create Interface")
    console.print(f"{len(interfaces) + 2}. Back")

    choice = input("Select interface: ").strip()
    try:
        index = int(choice)
    except ValueError:
        console.print("[red]Invalid selection.[/red]")
        _pause()
        return

    if 1 <= index <= len(interfaces):
        _set_selected(interfaces[index - 1])
        console.print(f"[green]✓ Selected {_selected()}[/green]")
        _pause()
    elif index == len(interfaces) + 1:
        _create_interface()
    elif index != len(interfaces) + 2:
        console.print("[red]Invalid selection.[/red]")
        _pause()


def create_interface() -> None:
    """Create a new isolated WireGuard interface configuration."""
    import re
    from pathlib import Path

    from ..wireguard.client_config import ConfigGenerator
    from ..wireguard.key_manager import KeyManager
    from ..wireguard.server_config import ServerConfig
    from ..wireguard.interfaces import (
        configured_interfaces,
        validate_interface_name,
        config_path as interface_config_path,
    )

    name = input("Interface name: ").strip()
    if not validate_interface_name(name) or name == "wg0":
        console.print("[red]Invalid or duplicate interface name.[/red]")
        pause()
        return
    path = interface_config_path(name)
    if path.exists():
        console.print("[red]Interface already exists.[/red]")
        pause()
        return

    defaults = ServerConfig.defaults(interface=name)
    match = re.fullmatch(r"wg([1-9][0-9]*)", name)
    if match:
        interface_number = int(match.group(1))
        subnet_octet = 66 + (interface_number * 11)
        if subnet_octet <= 254:
            defaults.listen_port = 51820 + interface_number
            defaults.ipv4_network = f"10.{subnet_octet}.{subnet_octet}.0/24"
            defaults.ipv6_network = f"fd42:{subnet_octet:x}:{subnet_octet:x}::/64"
    console.print("[dim]Press Enter to accept the value in brackets.[/dim]")
    port_text = input(f"Listening UDP port [{defaults.listen_port}]: ").strip()
    ipv4 = input(f"VPN IPv4 network [{defaults.ipv4_network}]: ").strip() or defaults.ipv4_network
    ipv6 = input(f"VPN IPv6 network [{defaults.ipv6_network}]: ").strip() or defaults.ipv6_network
    try:
        port = int(port_text) if port_text else defaults.listen_port
        candidate = ServerConfig(
            wg_interface=name,
            listen_port=port,
            ipv4_network=ipv4,
            ipv6_network=ipv6,
            dns_primary=defaults.dns_primary,
            dns_secondary=defaults.dns_secondary,
            allowed_ips=defaults.allowed_ips,
        )
        valid, errors = candidate.validate()
        for existing in configured_interfaces():
            if existing == name:
                errors.append(f"Interface {name} already exists")
                continue
            existing_path = interface_config_path(existing)
            if not existing_path.exists():
                continue
            existing_cfg = ServerConfig.from_file(existing_path)
            if candidate.get_ipv4_network().overlaps(existing_cfg.get_ipv4_network()):
                errors.append(f"IPv4 network overlaps interface {existing}")
            if candidate.get_ipv6_network().overlaps(existing_cfg.get_ipv6_network()):
                errors.append(f"IPv6 network overlaps interface {existing}")
        if errors:
            console.print("[red]Interface configuration invalid:[/red]")
            for error in errors:
                console.print(f"  - {error}")
            pause()
            return
        keypair = KeyManager.generate_keypair()
        content = ConfigGenerator.generate_server_config(
            candidate.get_ipv4_server_address(),
            candidate.get_ipv6_server_address(),
            candidate.listen_port,
            keypair.private_key,
        )
        if not ConfigGenerator.write_config(path, content):
            raise RuntimeError("Failed to write interface configuration")
        set_selected_interface(name)
        console.print(f"[green]✓ Interface {name} created and selected[/green]")
    except (RuntimeError, ValueError) as exc:
        console.print(f"[red]✗ Failed to create interface: {exc}[/red]")
    pause()


def clear_screen() -> None:
    """Clear terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


def section_banner(title: str, subtitle: str | None = None) -> None:
    """Display a consistent purple banner for a CLI section."""
    text = f"[bold white]{title}[/bold white]"
    if subtitle:
        text += f"\n[grey70]{subtitle}[/grey70]"
    console.print(Panel(text, border_style="purple", padding=(1, 2)))
    console.print()


def pause() -> None:
    """Pause and wait for user input."""
    input("\nPress Enter to continue...")


def confirm(prompt: str = "Continue?") -> bool:
    """Ask for confirmation."""
    while True:
        response = input(f"\n{prompt} (y/n): ").strip().lower()

        if response in ("y", "yes"):
            return True

        if response in ("n", "no"):
            return False

        print("Invalid response. Please enter 'y' or 'n'.")


def show_banner() -> None:
    """Display LoomWG banner."""
    clear_screen()

    banner = """
╔═══════════════════════════════════════════════╗
║                  LoomWG                        ║
║         WireGuard Administration Tool          ║
║                                                ║
║            For Linux VPS/Servers               ║
╚═══════════════════════════════════════════════╝
"""

    print(banner)




def display_peer_qr_code(peer_name: str, config_content: str) -> None:
    """Display terminal QR output using the system qrencode feature when available."""
    from ..wireguard.client_config import ClientConfigStore
    qr_text = ClientConfigStore.render_qr_ansi(config_content)
    if qr_text is None:
        console.print("[yellow]Warning: QR generation is unavailable because qrencode is not installed.[/yellow]")
        return
    console.print(f"\n[bold]QR code for {peer_name}[/bold]\n")
    print(qr_text)




def prompt_for_qr_code(peer_name: str | None = None) -> bool:
    """Prompt the user to show a QR code for a generated client config."""
    prompt = "Show QR code for this peer? (Y/n): "
    while True:
        response = input(prompt).strip().lower()
        if response in ("", "y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        print("Invalid response. Please enter 'y' or 'n'.")

def check_root() -> bool:
    """Check if running as root."""
    from ..system.info import SystemDetector
    if not SystemDetector().detect().is_root:
        console.print(
            Panel(
                "[red]ERROR[/red]\n\n"
                "LoomWG must be run as root.\n"
                "Please run again with sudo.",
                title="[bold]Permission Denied[/bold]"
            )
        )
        return False
    return True


def show_header_info() -> None:
    """Show system header information."""
    from ..system.info import SystemDetector as InfoDetector
    from ..wireguard.installer import WireGuardInstaller

    detector = InfoDetector()
    info = detector.detect()
    wg_manager = WireGuardInstaller()

    print("\n" + "=" * 50)
    print(f"Server: {info.hostname}")
    print(f"OS: {info.os_name} {info.os_version}")
    print(f"Kernel: {info.kernel}")

    if wg_manager.is_installed():
        interfaces = wg_manager.get_interfaces()

        if interfaces:
            print(f"WireGuard: Installed ({len(interfaces)} interface(s))")

        else:
            print("WireGuard: Installed")
    else:
        print("WireGuard: Not installed")

    print("=" * 50 + "\n")


def menu_option(
    number: int, title: str, description: str, command: str | None = None
) -> None:
    """Render a selectable menu item with a subdued explanatory label."""
    suffix = f"  [grey35]({command})[/grey35]" if command else ""
    console.print(
        f"  [purple]{number})[/purple] [bold]{title:<25}[/bold]"
        f"[grey35]{description}[/grey35]{suffix}"
    )