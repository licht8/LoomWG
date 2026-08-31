"""LoomWG CLI interface."""
import os
import re
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from ipaddress import ip_network

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .backup.manager import BackupManager
from .diagnostics import (
    FirewallDiagnostics,
    NetworkDiagnostics,
    SystemDiagnostics,
    WireGuardDiagnostics,
)
from .firewall.firewalld import FirewalldManager
from .logging_system.logger import LoomLogger
from .system.info import SystemDetector
from .system.network import NetworkManager
from .system.packages import PackageManager
from .system.services import ServiceManager
from .wireguard.client_config import ClientConfigStore
from .wireguard.config_generator import ConfigGenerator
from .wireguard.installer import WireGuardInstaller
from .wireguard.lifecycle import WireGuardLifecycle
from .wireguard.ip_allocator import IPAllocator
from .wireguard.key_manager import KeyManager
from .wireguard.manager import WireGuardManager
from .wireguard.peer_manager import Peer, PeerManager
from .wireguard.server_config import ServerConfig
from .wireguard.status import StatusParser
from .wireguard.interfaces import (
    config_path as interface_config_path,
    configured_interfaces,
    get_selected_interface,
    set_selected_interface,
    validate_interface_name,
)

console = Console()


def selected_interface() -> str:
    """Return the interface selected for the current CLI workflow."""
    return get_selected_interface()


def select_interface() -> None:
    """Select a configured WireGuard interface for subsequent operations."""
    interfaces = configured_interfaces()
    console.print("\n[bold]WireGuard Interfaces[/bold]")
    for index, name in enumerate(interfaces, 1):
        marker = " (selected)" if name == selected_interface() else ""
        console.print(f"{index}. {name}{marker}")
    console.print(f"{len(interfaces) + 1}. Create Interface")
    console.print(f"{len(interfaces) + 2}. Back")

    choice = input("Select interface: ").strip()
    try:
        index = int(choice)
    except ValueError:
        console.print("[red]Invalid selection.[/red]")
        pause()
        return

    if 1 <= index <= len(interfaces):
        set_selected_interface(interfaces[index - 1])
        console.print(f"[green]✓ Selected {selected_interface()}[/green]")
        pause()
    elif index == len(interfaces) + 1:
        create_interface()
    elif index != len(interfaces) + 2:
        console.print("[red]Invalid selection.[/red]")
        pause()


def manage_interfaces() -> None:
    """Manage interface selection, creation, and deletion."""
    while True:
        clear_screen()
        interfaces = configured_interfaces()
        console.print(
            Panel(
                "[bold white]Manage WireGuard Interfaces[/bold white]\n"
                "[grey70]Select an interface or manage the available VPN tunnels[/grey70]",
                border_style="purple",
                padding=(1, 2),
            )
        )
        console.print()
        for index, name in enumerate(interfaces, 1):
            marker = " (selected)" if name == selected_interface() else ""
            console.print(
                f"  [purple]{index}.[/purple] "
                f"[bold]Select {name}[/bold]"
                f"[green]{marker}[/green]"
            )
        console.print()
        console.print("  [purple]ci[/purple] [bold]Create Interface[/bold]")
        console.print("  [purple]di[/purple] [bold]Delete selected interface[/bold]")
        console.print()
        console.print("  [purple]0.[/purple] Back")

        choice = input("Select option: ").strip()

        if choice.lower() == "ci":
            create_interface()
        elif choice.lower() == "di":
            delete_interface()
        elif choice == "0":
            return
        else:
            try:
                index = int(choice)
            except ValueError:
                console.print("[red]Invalid selection.[/red]")
                pause()
                continue

            if not 1 <= index <= len(interfaces):
                console.print("[red]Invalid selection.[/red]")
                pause()
                continue
            set_selected_interface(interfaces[index - 1])
            console.print(f"[green]✓ Selected {selected_interface()}[/green]")
            pause()


def delete_interface() -> None:
    """Delete a non-default interface and its isolated state after confirmation."""
    interface = selected_interface()
    if interface == "wg0":
        console.print("[yellow]The default wg0 interface cannot be deleted here.[/yellow]")
        pause()
        return

    path = interface_config_path(interface)
    if not path.exists():
        console.print(f"[red]Interface {interface} does not exist.[/red]")
        pause()
        return

    console.print(f"[bold red]Delete Interface {interface}[/bold red]")
    console.print(f"Configuration: {path}")
    console.print("This removes the interface configuration, peer database, and client configs.")
    if input(f"Type DELETE {interface} to continue: ").strip() != f"DELETE {interface}":
        console.print("[yellow]Interface deletion cancelled.[/yellow]")
        pause()
        return

    manager = WireGuardManager()
    service = ServiceManager()
    if manager.is_interface_active(interface) and not manager.stop(interface):
        console.print(f"[red]Could not stop {interface}; nothing was deleted.[/red]")
        pause()
        return
    if service.is_enabled(f"wg-quick@{interface}") and not service.disable(f"wg-quick@{interface}"):
        console.print(f"[red]Could not disable wg-quick@{interface}; nothing was deleted.[/red]")
        pause()
        return

    project_root = Path(__file__).resolve().parents[1]
    paths = [
        path,
        project_root / "data" / "interfaces" / interface,
    ]
    try:
        for target in paths:
            if target.is_dir():
                import shutil
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
        set_selected_interface("wg0")
        LoomLogger().info(f"WireGuard interface '{interface}' deleted", "server")
        console.print(f"[green]✓ Interface {interface} deleted[/green]")
    except OSError as exc:
        console.print(f"[red]Failed to delete interface {interface}: {exc}[/red]")
    pause()


def create_interface() -> None:
    """Create a new isolated WireGuard interface configuration."""
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


def menu_option(
    number: int, title: str, description: str, command: str | None = None
) -> None:
    """Render a selectable menu item with a subdued explanatory label."""
    suffix = f"  [grey35]({command})[/grey35]" if command else ""
    console.print(
        f"  [purple]{number})[/purple] [bold]{title:<25}[/bold]"
        f"[grey35]{description}[/grey35]{suffix}"
    )


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
║        For Rocky Linux VPS/Servers             ║
╚═══════════════════════════════════════════════╝
"""

    print(banner)


def check_root() -> bool:
    """Check if running as root."""
    detector = SystemDetector()
    info = detector.detect()

    if not info.is_root:
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
    detector = SystemDetector()
    info = detector.detect()
    wg_manager = WireGuardManager()

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


def display_peer_qr_code(peer_name: str, config_content: str) -> None:
    """Display terminal QR output using the system qrencode feature when available."""
    qr_text = ClientConfigStore.render_qr_ansi(config_content)
    if qr_text is None:
        console.print("[yellow]Warning: QR generation is unavailable because qrencode is not installed.[/yellow]")
        return
    console.print(f"\n[bold]QR code for {peer_name}[/bold]\n")
    print(qr_text)


def show_qr_code() -> None:
    """Display a saved peer config as a terminal QR code."""
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


def main_menu() -> None:
    """Main menu."""
    if not check_root():
        return

    while True:
        show_banner()
        show_header_info()

        print("Main Menu\n")
        menu_option(1, "Server", "Configure and operate WireGuard")
        print()
        menu_option(2, "Peers", "Create and manage VPN clients")
        print()
        menu_option(3, "Firewall", "Manage firewalld access")
        print()
        menu_option(4, "Diagnostics", "Run health and troubleshooting checks")
        menu_option(5, "Backup & Restore", "Protect or recover LoomWG data")
        menu_option(6, "Logs", "View and export application activity")
        menu_option(7, "System Info", "Read-only server and VPN overview")
        print()
        print("  0) Exit\n")

        choice = input("Select option: ").strip()

        if choice == "1":
            server_menu()
        elif choice == "2":
            peers_menu()
        elif choice == "3":
            firewall_menu()
        elif choice == "4":
            diagnostics_menu()
        elif choice == "5":
            backup_menu()
        elif choice == "6":
            logs_menu()
        elif choice == "7":
            system_info_menu()
        elif choice == "0":
            console.print("[yellow]Goodbye![/yellow]")
            sys.exit(0)
        else:
            print("Invalid option. Please try again.")
            pause()


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


def show_server_status() -> None:
    """Show a runtime-only WireGuard operational dashboard."""
    while True:
        clear_screen()
        wg_manager = WireGuardManager()
        interface = selected_interface()
        config_file = interface_config_path(interface)
        config = ServerConfig.from_file(config_file)
        active = wg_manager.is_interface_active(interface)
        section_banner("Server status", f"Live status for {interface}")
        console.print("[bold]WireGuard Server Status[/bold]\n")
        console.print(f"Status:             {'[green]RUNNING[/green]' if active else '[red]DOWN[/red]'}")
        console.print(f"Interface:          {interface}")
        console.print(f"Listening port:     {config.listen_port}/UDP")
        console.print(f"Server IPv4:        {config.get_ipv4_server_address() if config_file.exists() else 'N/A'}")
        console.print(f"Server IPv6:        {config.get_ipv6_server_address() if config_file.exists() else 'N/A'}")
        if active:
            dashboard = _wg_runtime_dashboard(interface)
            console.print(f"Uptime:             {dashboard['uptime']}")
            console.print(f"Peers:              {dashboard['total']} total / [green]{dashboard['online']} online[/green] / {dashboard['idle']} idle / {dashboard['offline']} offline")
            console.print(f"Traffic:            RX {dashboard['rx']} / TX {dashboard['tx']}")
            console.print(f"Last activity:      {dashboard['last_activity']}")
            if dashboard['rows']:
                table = Table(title="Per-peer Activity")
                table.add_column("Peer")
                table.add_column("Endpoint")
                table.add_column("Last handshake")
                table.add_column("RX")
                table.add_column("TX")
                table.add_column("State")
                for row in dashboard['rows']:
                    table.add_row(*row)
                console.print(table)
        else:
            console.print("Uptime:             N/A")
        choice = input("\n[R]efresh or Enter to go back: ").strip().lower()
        if choice != "r":
            return


def _wg_runtime_dashboard(interface: str | None = None) -> dict[str, object]:
    """Read a WireGuard runtime dump and return presentation-safe live metrics."""
    interface = interface or selected_interface()
    try:
        output = subprocess.run(["wg", "show", interface, "dump"], capture_output=True, text=True, timeout=5, check=False).stdout
        link = subprocess.run(["ip", "-o", "link", "show", interface], capture_output=True, text=True, timeout=5, check=False).stdout
    except OSError:
        output, link = "", ""
    rows, total_rx, total_tx, online, idle, offline, latest = [], 0, 0, 0, 0, 0, None
    peer_store = PeerManager()
    now = datetime.now().timestamp()
    for line in output.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 8:
            continue
        key, endpoint, handshake, rx, tx = parts[0], parts[2] or "N/A", int(parts[4] or 0), int(parts[5] or 0), int(parts[6] or 0)
        age = now - handshake if handshake else None
        state = "OFFLINE" if age is None else "ONLINE" if age < 120 else "IDLE" if age < 86400 else "OFFLINE"
        online += state == "ONLINE"; idle += state == "IDLE"; offline += state == "OFFLINE"
        total_rx += rx; total_tx += tx
        peer_store.record_traffic(key, rx, tx)
        if handshake and (latest is None or handshake > latest): latest = handshake
        rows.append((key[:12] + "…", endpoint, _age_text(age), _format_bytes(rx), _format_bytes(tx), state))
    uptime = "N/A"
    if link:
        # Linux reports link creation time poorly across versions; service uptime is stable.
        result = subprocess.run(["systemctl", "show", f"wg-quick@{interface}", "--property=ActiveEnterTimestamp", "--value"], capture_output=True, text=True, timeout=5, check=False)
        uptime = result.stdout.strip() or "Active"
    return {"uptime": uptime, "total": len(rows), "online": online, "idle": idle, "offline": offline, "rx": _format_bytes(total_rx), "tx": _format_bytes(total_tx), "last_activity": _age_text(now - latest) if latest else "Never", "rows": rows}


def _age_text(age: float | None) -> str:
    if age is None: return "Never"
    if age < 60: return f"{int(age)}s ago"
    if age < 3600: return f"{int(age // 60)}m ago"
    if age < 86400: return f"{int(age // 3600)}h ago"
    return f"{int(age // 86400)}d ago"


def _format_bytes(value: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024: return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"


def show_server_config() -> None:
    """Show server configuration."""
    clear_screen()

    interface = selected_interface()
    config_path = interface_config_path(interface)

    if not config_path.exists():
        console.print("[yellow]No configuration found[/yellow]")
        pause()
        return

    try:
        content = config_path.read_text()
        console.print(f"\n[bold]{config_path}[/bold]\n")
        print(content)
    except Exception as e:
        console.print(f"[red]Error reading config: {e}[/red]")

    pause()


def configure_server() -> None:
    """Configure WireGuard server."""
    clear_screen()

    section_banner("Configure server", "Create or update the WireGuard server configuration")

    # Check if WireGuard is installed
    wg_manager = WireGuardManager()

    if Path("/etc/wireguard/wg0.conf").exists():
        console.print("[yellow]WireGuard server is already configured at /etc/wireguard/wg0.conf.[/yellow]")
        pause()
        return

    if not wg_manager.is_installed():
        console.print("[yellow]WireGuard is not installed. Install first? (y/n)[/yellow]")

        if confirm():
            install_wireguard()
            return
        else:
            return

    config = prompt_server_config()

    # Validate
    valid, errors = config.validate()
    errors.extend(validate_server_settings(config))
    valid = valid and not errors

    if not valid:
        console.print("[red]Configuration invalid:[/red]")

        for error in errors:
            console.print(f"  - {error}")

        pause()
        return

    # Generate keys
    console.print("\n[bold]Generating keys...[/bold]")

    try:
        key_mgr = KeyManager()
        keypair = key_mgr.generate_keypair()

        config.private_key = keypair.private_key
        config.public_key = keypair.public_key

        console.print("[green]✓ Keys generated[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to generate keys: {e}[/red]")
        pause()
        return

    # Generate configuration
    console.print("[bold]Generating configuration...[/bold]")

    try:
        gen = ConfigGenerator()
        server_ipv4 = config.get_ipv4_server_address()
        server_ipv6 = config.get_ipv6_server_address()

        conf_content = gen.generate_server_config(
            server_ipv4=server_ipv4,
            server_ipv6=server_ipv6,
            listen_port=config.listen_port,
            private_key=config.private_key,
        )

        # Validate
        valid, errors = gen.validate_config(conf_content)

        server_valid, server_errors = gen.validate_server_config(conf_content)
        if not server_valid:
            valid = False
            errors.extend(server_errors)

        if not valid:
            console.print("[red]Configuration invalid:[/red]")

            for error in errors:
                console.print(f"  - {error}")

            pause()
            return

        # Write config
        interface = selected_interface()
        config_path = interface_config_path(interface)

        if not gen.write_config(config_path, conf_content):
            console.print("[red]✗ Failed to write configuration[/red]")
            pause()
            return

        console.print("[green]✓ Configuration written[/green]")

        # Log
        logger = LoomLogger()
        logger.log_installation(True, f"Server config: {config_path}")

    except Exception as e:
        console.print(f"[red]✗ Failed: {e}[/red]")
        pause()
        return

    # Enable firewall
    console.print("\n[bold]Configuring firewall...[/bold]")

    try:
        firewall = FirewalldManager()

        if not firewall.is_running():
            console.print("[yellow]Starting firewalld...[/yellow]")
            firewall.start()

        if firewall.open_port(config.listen_port):
            console.print("[green]✓ Port opened[/green]")
        else:
            console.print("[yellow]⚠ Could not open port[/yellow]")

        if firewall.enable_masquerading():
            console.print("[green]✓ Masquerading enabled[/green]")
        else:
            console.print("[yellow]⚠ Could not enable masquerading[/yellow]")
    except Exception as e:
        console.print(f"[yellow]⚠ Firewall configuration failed: {e}[/yellow]")

    # Enable IP forwarding
    console.print("[bold]Enabling IP forwarding...[/bold]")

    try:
        network = NetworkManager()

        if network.enable_ip_forwarding():
            console.print("[green]✓ IPv4 forwarding enabled[/green]")

        if network.enable_ipv6_forwarding():
            console.print("[green]✓ IPv6 forwarding enabled[/green]")
    except Exception as e:
        console.print(f"[yellow]⚠ Could not enable forwarding: {e}[/yellow]")

    console.print("\n[green]✓ Server configured successfully![/green]")
    pause()


def normalize_wireguard_config(content: str) -> str:
    """Normalize WireGuard config lines to the canonical format accepted by wg setconf."""
    normalized_lines: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("["):
            normalized_lines.append(raw_line)
            continue
        if "=" not in line:
            normalized_lines.append(raw_line)
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        value = re.sub(r',(?=\S)', ', ', value)
        normalized_lines.append(f"{key} = {value}")
    return "\n".join(normalized_lines) + ("\n" if content.endswith("\n") else "")


def repair_wireguard_config_file(config_path: Path) -> str:
    """Repair legacy malformed WireGuard config formatting before live apply."""
    original = config_path.read_text(encoding="utf-8")
    normalized = normalize_wireguard_config(original)
    if normalized != original:
        config_path.write_text(normalized, encoding="utf-8")
        config_path.chmod(0o600)
    return normalized


def rotate_server_keys() -> None:
    """Rotate the server keypair with validation, backup, and rollback protection."""
    clear_screen()

    interface = selected_interface()
    config_path = interface_config_path(interface)
    wg_manager = WireGuardManager()

    if not config_path.exists():
        console.print("[yellow]No WireGuard configuration exists for wg0.[/yellow]")
        pause()
        return

    repaired_config = repair_wireguard_config_file(config_path)
    current_cfg = ServerConfig.from_file(config_path)
    peer_mgr = PeerManager()
    configured_peers = len(peer_mgr.list_peers())
    active_peers = len(peer_mgr.list_enabled_peers())
    current_key = current_cfg.public_key or (KeyManager.generate_public_key(current_cfg.private_key) if current_cfg.private_key else "<unknown>")

    section_banner("Rotate Server Keys", "Safely replace the server keypair")
    console.print(f"Interface: {interface}")
    console.print(f"Current server public key: {current_key}")
    console.print(f"Configured peers: {configured_peers}")
    console.print(f"Active peers: {active_peers}")
    console.print(f"Configuration file: {config_path}")
    console.print()
    console.print("[bold red]WARNING:[/bold red] Rotating the server key changes the server public key and makes existing client configurations outdated.")
    confirmation = input("Type ROTATE to continue: ").strip()
    if confirmation != "ROTATE":
        console.print("[yellow]Server key rotation cancelled.[/yellow]")
        pause()
        return

    backup_mgr = BackupManager()
    backup_file = backup_mgr.create_backup(description="Server key rotation pre-checkpoint")
    if backup_file is None:
        console.print("[red]✗ Failed to create a backup before rotating the server key.[/red]")
        pause()
        return

    try:
        new_keypair = KeyManager.generate_keypair()
        if not KeyManager.validate_key(new_keypair.private_key):
            raise RuntimeError("Generated server private key is invalid")
        if not wg_manager.is_interface_active(interface):
            raise RuntimeError(f"WireGuard interface {interface} is not active")

        original_config = normalize_wireguard_config(config_path.read_text(encoding="utf-8"))
        candidate_config = re.sub(
            r"(?m)^PrivateKey\s*=\s*.*$",
            f"PrivateKey = {new_keypair.private_key}",
            original_config,
            count=1,
        )
        candidate_config = normalize_wireguard_config(candidate_config)
        if "PrivateKey = " not in candidate_config:
            raise RuntimeError("The generated server configuration does not contain a private key")

        valid, errors = ConfigGenerator.validate_config(candidate_config)
        server_valid, server_errors = ConfigGenerator.validate_server_config(candidate_config)
        if not valid or not server_valid:
            raise RuntimeError("; ".join(errors + server_errors))

        peer_entries = ConfigGenerator.parse_server_peers(config_path)
        if any(not entry.get("public_key") for entry in peer_entries):
            raise RuntimeError("One or more existing peers cannot be represented in the rotated configuration")

        config_path.write_text(normalize_wireguard_config(candidate_config), encoding="utf-8")
        config_path.chmod(0o600)

        if not wg_manager.sync(interface):
            raise RuntimeError("Failed to apply the new server key to the live interface")

        client_store = ClientConfigStore()
        client_names = [path.stem for path in client_store.base_dir.glob("*.conf") if path.is_file()]
        regenerated, regeneration_failed = client_store.regenerate_after_server_key_rotation(
            new_keypair.public_key,
            client_names,
        )
        if regeneration_failed:
            regen_marker = client_store.mark_server_key_rotation_required(regeneration_failed)
        else:
            regen_marker = None

        current_cfg.private_key = new_keypair.private_key
        current_cfg.public_key = new_keypair.public_key

        logger = LoomLogger()
        logger.log_server_key_rotated(
            interface,
            current_key if current_key != "<unknown>" else "unknown",
            new_keypair.public_key,
            str(backup_file),
            configured_peers,
        )

        console.print("\n[green]✓ Server key rotation completed[/green]")
        console.print(f"New server public key: {new_keypair.public_key}")
        console.print(f"Preserved peers: {configured_peers}")
        console.print(f"Client configs regenerated: {len(regenerated)}")
        if regeneration_failed:
            console.print(f"Client configs requiring manual regeneration: {len(regeneration_failed)}")
        console.print(f"Backup location: {backup_file}")
        console.print(f"Rotation timestamp: {datetime.now().isoformat()}")
        if regen_marker:
            console.print(f"Regeneration marker: {regen_marker}")

    except Exception as exc:
        config_path.write_text(normalize_wireguard_config(original_config), encoding="utf-8")
        config_path.chmod(0o600)
        if wg_manager.is_interface_active(interface):
            try:
                wg_manager.sync(interface)
            except Exception:
                pass
        console.print(f"[red]✗ Server key rotation failed and the previous state was restored: {exc}[/red]")
        LoomLogger().error("Server key rotation failed and was rolled back", "server", details=str(exc))

    pause()


def prompt_server_config() -> ServerConfig:
    """Collect server network settings, using safe defaults on blank input."""
    defaults = ServerConfig.defaults()
    console.print("[dim]Press Enter to accept the value in brackets.[/dim]")

    def value(label: str, default: str) -> str:
        return input(f"{label} [{default}]: ").strip() or default

    port_text = value("Listening UDP port", str(defaults.listen_port))
    try:
        port = int(port_text)
    except ValueError:
        port = 0
    config = ServerConfig(
        wg_interface=defaults.wg_interface,
        listen_port=port,
        ipv4_network=value("VPN IPv4 network", defaults.ipv4_network),
        ipv6_network=value("VPN IPv6 network", defaults.ipv6_network),
        dns_primary=value("Primary DNS", defaults.dns_primary),
        dns_secondary=value("Secondary DNS", defaults.dns_secondary),
        allowed_ips=value("Client Allowed IPs", defaults.allowed_ips),
    )
    return config


def validate_server_settings(config: ServerConfig) -> list[str]:
    """Reject unsafe server settings before touching the configuration file."""
    errors: list[str] = []
    try:
        routes = subprocess.run(["ip", "-o", "route", "show"], capture_output=True, text=True, timeout=5, check=False)
        for line in routes.stdout.splitlines():
            destination = line.split()[0] if line.split() else ""
            if destination in {"default", "broadcast", "local"}:
                continue
            try:
                if config.get_ipv4_network().overlaps(ip_network(destination, strict=False)):
                    errors.append(f"VPN IPv4 network overlaps existing route {destination}")
                    break
            except ValueError:
                continue
    except OSError:
        pass
    try:
        result = subprocess.run(["ss", "-lun"], capture_output=True, text=True, timeout=5, check=False)
        marker = f":{config.listen_port}"
        if result.returncode == 0 and marker in result.stdout:
            errors.append(f"UDP port {config.listen_port} is already in use")
    except OSError:
        pass
    return errors


def remove_wireguard() -> None:
    """Remove LoomWG-managed WireGuard state after explicit confirmation."""
    clear_screen()
    section_banner("Remove WireGuard", "Remove the LoomWG-managed WireGuard installation")
    console.print("This removes wg0, its service, LoomWG forwarding settings, and WireGuard packages.")
    if confirm("Continue with removal?"):
        result = WireGuardLifecycle().remove()
        console.print(f"[green]✓ {result.message}[/green]" if result.success else f"[red]✗ {result.message}[/red]")
    pause()


def reinstall_wireguard() -> None:
    """Perform a complete removal followed by a fresh installation."""
    clear_screen()
    section_banner("Reinstall WireGuard", "Remove and recreate the LoomWG WireGuard installation")
    console.print("This first removes the existing LoomWG WireGuard setup.")
    if not confirm("Continue with reinstall?"):
        return
    result = WireGuardLifecycle().remove()
    if not result.success:
        console.print(f"[red]✗ Reinstall stopped: {result.message}[/red]")
        pause()
        return
    console.print(f"[green]✓ {result.message}[/green]")
    install_wireguard()


def install_wireguard() -> None:
    """Install WireGuard and configure the default server."""
    clear_screen()
    interface = selected_interface()

    console.print("[bold]Installing WireGuard[/bold]\n")

    detector = SystemDetector()
    checks = detector.check()

    console.print("[bold]System Checks:[/bold]\n")

    for check in checks:
        status = "[green]✓[/green]" if check.passed else "[red]✗[/red]"
        console.print(f"{status} {check.name}: {check.message}")

    critical_failed = any(
        not check.passed
        and check.name
        in ("Operating system", "Architecture", "Root privileges", "Init system")
        for check in checks
    )

    if critical_failed:
        console.print("\n[red]System does not meet requirements[/red]")
        pause()
        return

    if not confirm("\nContinue with installation?"):
        return

    installer = WireGuardInstaller()

    console.print("\n[bold]Installing packages...[/bold]\n")
    result = installer.install(interface)

    if not result.success:
        console.print(f"[red]✗ {result.message}[/red]")
        LoomLogger().log_installation(False, result.message)
        pause()
        return

    console.print(f"[green]✓ {result.message}[/green]")

    try:
        console.print("\n[bold]Creating server configuration...[/bold]")
        config = prompt_server_config()
        config_valid, config_errors = config.validate()
        config_errors.extend(validate_server_settings(config))
        if not config_valid or config_errors:
            console.print("[red]Configuration invalid:[/red]")
            for error in config_errors:
                console.print(f"  - {error}")
            pause()
            return
        key_mgr = KeyManager()
        keypair = key_mgr.generate_keypair()
        config.private_key = keypair.private_key
        config.public_key = keypair.public_key

        generator = ConfigGenerator()
        server_conf = generator.generate_server_config(
            server_ipv4=config.get_ipv4_server_address(),
            server_ipv6=config.get_ipv6_server_address(),
            listen_port=config.listen_port,
            private_key=config.private_key,
        )

        valid, errors = generator.validate_config(server_conf)
        server_valid, server_errors = generator.validate_server_config(server_conf)
        if not server_valid:
            valid = False
            errors.extend(server_errors)

        if not valid:
            console.print("[red]Configuration validation failed:[/red]")
            for error in errors:
                console.print(f"  - {error}")
            pause()
            return

        config_path = interface_config_path(selected_interface())
        if not generator.write_config(config_path, server_conf):
            console.print("[red]✗ Failed to write WireGuard configuration[/red]")
            pause()
            return

        console.print("[green]✓ Server configuration created[/green]")

        firewall = FirewalldManager()
        if not firewall.is_running():
            firewall.start()
        firewall.open_port(config.listen_port)
        firewall.enable_masquerading()
        console.print("[green]✓ Firewall rules configured[/green]")

        network = NetworkManager()
        network.enable_ip_forwarding()
        network.enable_ipv6_forwarding()
        console.print("[green]✓ IP forwarding enabled[/green]")

        wg_manager = WireGuardManager()
        start_result = wg_manager.start_with_result(interface)
        runtime_ok = start_result.success

        if runtime_ok:
            if start_result.already_running:
                console.print(f"[green]✓ {interface} is already running[/green]")
            else:
                console.print("[green]✓ WireGuard interface started successfully[/green]")
        else:
            console.print(f"[red]✗ Failed to start WireGuard interface {interface}[/red]")
            console.print(f"Return code: {start_result.return_code}")
            console.print(f"stdout: {start_result.stdout or '<empty>'}")
            console.print(f"stderr: {start_result.stderr or '<empty>'}")
            console.print("\n[bold]Runtime verification:[/bold]")
            console.print(
                f"wg show interfaces: {interface if start_result.wg_interface_exists else f'{interface} not present'}"
            )
            console.print(
                f"ip link show {interface}: {'present' if start_result.link_exists else 'not present'}"
            )
            console.print("\n[yellow]Installation completed with errors.[/yellow]")
            console.print("[yellow]WireGuard is NOT currently running.[/yellow]")
            console.print("Run: wg show interfaces")
            console.print(f"Run: wg show {interface}")
            console.print(f"Run: ip link show {interface}")

        boot_enabled = ServiceManager().enable(f"wg-quick@{interface}")
        if boot_enabled:
            console.print("[green]✓ WireGuard enabled on boot[/green]")
        else:
            console.print("[yellow]⚠ Could not enable WireGuard at boot[/yellow]")

        installation_ok = runtime_ok and boot_enabled
        LoomLogger().log_installation(installation_ok, str(config_path))
        if installation_ok:
            console.print("\n[green]✓ WireGuard installation completed successfully[/green]")
        elif runtime_ok:
            console.print("\n[yellow]Installation completed with errors.[/yellow]")
    except Exception as exc:
        console.print(f"[red]✗ Installation failed: {exc}[/red]")
        LoomLogger().log_installation(False, str(exc))

    pause()


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


def show_peer() -> None:
    """Show peer details."""
    clear_screen()

    try:
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


def disable_peer() -> None:
    """Disable a peer."""
    clear_screen()
    section_banner("Disable peer", f"Disable a client on {selected_interface()}")

    try:
        peer_mgr = PeerManager()
        show_peer_selection(peer_mgr)

        name = input("Peer name: ").strip()

        if not name:
            return

        peer = peer_mgr.get_peer(name)
        interface = selected_interface()
        config_path = interface_config_path(interface)
        generator = ConfigGenerator()
        runtime_ok = WireGuardManager().remove_peer_from_interface(interface, peer.public_key) if peer else False
        config_ok = generator.remove_peer_from_server_config(config_path, peer.public_key) if peer and config_path.exists() else True
        if runtime_ok and config_ok and peer_mgr.disable_peer(name):
            console.print(f"[green]✓ Peer '{name}' disabled[/green]")

            logger = LoomLogger()
            logger.info(f"Peer '{name}' disabled", "peer")
        else:
            console.print("[red]✗ Failed to disable peer[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()


def enable_peer() -> None:
    """Enable a peer."""
    clear_screen()
    section_banner("Enable peer", f"Enable a client on {selected_interface()}")

    try:
        peer_mgr = PeerManager()
        show_peer_selection(peer_mgr)

        name = input("Peer name: ").strip()

        if not name:
            return

        peer = peer_mgr.get_peer(name)
        if not peer:
            console.print("[red]✗ Peer not found[/red]")
            pause()
            return
        if peer.revoked_at:
            console.print("[red]✗ This peer has been revoked and cannot be re-enabled.[/red]")
            pause()
            return
        if peer.expires_at and datetime.fromisoformat(peer.expires_at) <= datetime.now():
            console.print("[red]✗ Peer access has expired. Set a new expiry before enabling it.[/red]")
            pause()
            return
        interface = selected_interface()
        config_path = interface_config_path(interface)
        generator = ConfigGenerator()
        config_ok = generator.append_peer_to_server_config(config_path, peer.public_key, peer.ipv4_address, peer.ipv6_address, peer.preshared_key or None)
        manager = WireGuardManager()
        runtime_ok = (not manager.is_interface_active(interface)) or manager.add_peer_to_interface(interface, peer.public_key, peer.ipv4_address, client_ipv6=peer.ipv6_address)
        if config_ok and runtime_ok and peer_mgr.enable_peer(name):
            console.print(f"[green]✓ Peer '{name}' enabled[/green]")
            if not manager.is_interface_active(interface):
                console.print(f"[yellow]{interface} is down; the peer will be applied when the interface starts.[/yellow]")

            logger = LoomLogger()
            logger.info(f"Peer '{name}' enabled", "peer")
        else:
            console.print("[red]✗ Failed to enable peer[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()


def revoke_peer() -> None:
    """Revoke a peer while preserving its historical metadata and audit trail."""
    clear_screen()

    try:
        peer_mgr = PeerManager()
        show_peer_selection(peer_mgr)
        name = input("Peer name: ").strip()
        peer = peer_mgr.get_peer(name)
        if not peer:
            console.print("[red]Peer not found[/red]")
            pause()
            return
        if peer.revoked_at:
            console.print("[yellow]This peer is already revoked.[/yellow]")
            pause()
            return

        console.print(f"\n[bold]Revoke Peer[/bold]")
        console.print(f"Name: {peer.name}")
        console.print(f"Public Key: {peer.public_key}")
        if not confirm(f"Revoke peer '{name}' and disable its access immediately?"):
            return

        interface = selected_interface()
        config_path = interface_config_path(interface)
        generator = ConfigGenerator()
        manager = WireGuardManager()
        original_config = config_path.read_text(encoding="utf-8") if config_path.exists() else None
        original_peer = Peer(**peer.to_dict())

        try:
            runtime_ok = manager.remove_peer_from_interface(interface, peer.public_key) if manager.is_interface_active(interface) else True
            config_ok = generator.remove_peer_from_server_config(config_path, peer.public_key) if config_path.exists() else True
            if not (runtime_ok and config_ok):
                raise RuntimeError("Failed to remove peer from the live interface or server configuration")
            if not peer_mgr.revoke_peer(name):
                raise RuntimeError("Failed to mark the peer as revoked in the database")
            logger = LoomLogger()
            logger.log_peer_revoked(name, peer.public_key)
            console.print(f"[green]✓ Peer '{name}' revoked[/green]")
        except Exception:
            if config_path.exists() and original_config is not None:
                config_path.write_text(original_config, encoding="utf-8")
                config_path.chmod(0o600)
            peer_mgr.update_peer(name, original_peer)
            if manager.is_interface_active(interface):
                manager.add_peer_to_interface(interface, original_peer.public_key, original_peer.ipv4_address, client_ipv6=original_peer.ipv6_address)
            console.print("[red]✗ Revocation failed and changes were rolled back.[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()


def rotate_peer_keys() -> None:
    """Rotate a peer's WireGuard keys without creating a duplicate peer record."""
    clear_screen()

    try:
        peer_mgr = PeerManager()
        show_peer_selection(peer_mgr)
        name = input("Peer name: ").strip()
        peer = peer_mgr.get_peer(name)
        if not peer:
            console.print("[red]Peer not found[/red]")
            pause()
            return
        if peer.revoked_at:
            console.print("[red]Revoked peers cannot have their keys rotated.[/red]")
            pause()
            return

        console.print(f"\n[bold]Rotate Peer Keys[/bold]")
        console.print(f"Name: {peer.name}")
        console.print(f"Public Key: {peer.public_key}")
        if not confirm(f"Generate and apply a new keypair for '{name}'?"):
            return

        keypair = KeyManager.generate_keypair()
        original_peer = Peer(**peer.to_dict())
        interface = selected_interface()
        config_path = interface_config_path(interface)
        original_config = config_path.read_text(encoding="utf-8") if config_path.exists() else None
        manager = WireGuardManager()
        generator = ConfigGenerator()

        try:
            if config_path.exists():
                temp_path = config_path.with_suffix(".rotate.tmp")
                temp_path.write_text(original_config, encoding="utf-8")
                generator.remove_peer_from_server_config(temp_path, peer.public_key)
                generator.append_peer_to_server_config(temp_path, keypair.public_key, peer.ipv4_address, peer.ipv6_address)
                candidate = temp_path.read_text(encoding="utf-8")
                valid, errors = generator.validate_config(candidate)
                server_valid, server_errors = generator.validate_server_config(candidate)
                if not (valid and server_valid):
                    raise RuntimeError("; ".join(errors + server_errors))
                temp_path.unlink(missing_ok=True)

            if manager.is_interface_active(interface) and not manager.remove_peer_from_interface(interface, peer.public_key):
                raise RuntimeError("Failed to remove the old peer key from the live interface")

            if config_path.exists():
                generator.remove_peer_from_server_config(config_path, peer.public_key)
                generator.append_peer_to_server_config(config_path, keypair.public_key, peer.ipv4_address, peer.ipv6_address)

            updated_peer = Peer(
                name=peer.name,
                ipv4_address=peer.ipv4_address,
                ipv6_address=peer.ipv6_address,
                public_key=keypair.public_key,
                private_key=keypair.private_key,
                preshared_key=peer.preshared_key,
                created_at=peer.created_at,
                enabled=peer.enabled,
                description=peer.description,
                endpoint=peer.endpoint,
                latest_handshake=peer.latest_handshake,
                transfer_rx=peer.transfer_rx,
                transfer_tx=peer.transfer_tx,
                expires_at=peer.expires_at,
                revoked_at=peer.revoked_at,
                traffic_history=list(peer.traffic_history),
            )
            if not peer_mgr.rotate_peer_keys(name, updated_peer):
                raise RuntimeError("Failed to update the peer database with the new public key")

            server_cfg = ServerConfig.from_file(config_path) if config_path.exists() else ServerConfig.defaults()
            client_store = ClientConfigStore()
            peer_conf = ConfigGenerator().generate_peer_config(
                peer_ipv4=peer.ipv4_address,
                peer_ipv6=peer.ipv6_address,
                private_key=keypair.private_key,
                server_public_key=server_cfg.public_key or "",
                server_endpoint=SystemDetector().detect().public_ip or "YOUR_SERVER_IP",
                server_port=server_cfg.listen_port,
                dns_primary=server_cfg.dns_primary,
                dns_secondary=server_cfg.dns_secondary,
            )
            client_store.save_peer_config(name, peer_conf)
            client_store.save_qr_code(name, peer_conf)

            if manager.is_interface_active(interface) and not manager.add_peer_to_interface(interface, keypair.public_key, peer.ipv4_address, client_ipv6=peer.ipv6_address):
                raise RuntimeError("Failed to add the rotated key to the live interface")

            logger = LoomLogger()
            logger.log_peer_key_rotated(name, original_peer.public_key, keypair.public_key)
            console.print(f"[green]✓ Peer '{name}' key rotation completed[/green]")
        except Exception as exc:
            if config_path.exists() and original_config is not None:
                config_path.write_text(original_config, encoding="utf-8")
                config_path.chmod(0o600)
            peer_mgr.update_peer(name, original_peer)
            if manager.is_interface_active(interface):
                try:
                    manager.remove_peer_from_interface(interface, keypair.public_key)
                    manager.add_peer_to_interface(interface, original_peer.public_key, original_peer.ipv4_address, client_ipv6=original_peer.ipv6_address)
                except Exception:
                    pass
            console.print(f"[red]✗ Rotation failed and the prior state was restored: {exc}[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()


def remove_peer() -> None:
    """Remove a peer."""
    clear_screen()
    section_banner("Remove peer", f"Remove a client from {selected_interface()}")

    try:
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

        if confirm(f"Remove peer '{name}'? This cannot be undone."):
            if peer_mgr.remove_peer(name):
                console.print(f"[green]✓ Peer '{name}' removed[/green]")

                logger = LoomLogger()
                logger.log_peer_removed(name)
            else:
                console.print("[red]✗ Failed to remove peer[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()


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


def show_firewall_status() -> None:
    """Show firewall status."""
    clear_screen()
    section_banner("Show status", "View firewalld and WireGuard port status")

    try:
        firewall = FirewalldManager()

        console.print("[bold]Firewall Status[/bold]\n")
        console.print(f"Running: {'[green]Yes[/green]' if firewall.is_running() else '[red]No[/red]'}")
        console.print(f"Enabled: {'[green]Yes[/green]' if firewall.is_enabled() else '[red]No[/red]'}")

        config = ServerConfig.defaults()

        if firewall.is_running():
            port_open = firewall.is_port_open(config.listen_port)
            masq = firewall.is_masquerading_enabled()

            console.print(
                f"Port {config.listen_port}/UDP: {'[green]Open[/green]' if port_open else '[red]Closed[/red]'}"
            )
            console.print(
                f"Masquerading: {'[green]Enabled[/green]' if masq else '[red]Disabled[/red]'}"
            )
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()


def start_firewall() -> None:
    """Start firewall."""
    try:
        firewall = FirewalldManager()

        if firewall.start():
            console.print("[green]✓ Firewall started[/green]")
        else:
            console.print("[red]✗ Failed to start firewall[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()


def enable_firewall() -> None:
    """Enable firewall on boot."""
    try:
        firewall = FirewalldManager()

        if firewall.enable():
            console.print("[green]✓ Firewall enabled on boot[/green]")
        else:
            console.print("[red]✗ Failed to enable firewall[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()


def open_wg_port() -> None:
    """Open WireGuard port in firewall."""
    try:
        firewall = FirewalldManager()
        config = ServerConfig.defaults()

        if firewall.open_port(config.listen_port):
            console.print(f"[green]✓ Port {config.listen_port}/UDP opened[/green]")
        else:
            console.print("[red]✗ Failed to open port[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()


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

        choice = input("Select option: ").strip()

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


def run_full_diagnostics() -> None:
    """Run complete diagnostics."""
    clear_screen()

    console.print("[bold]Running Full Diagnostics...[/bold]\n")

    all_results = []

    # System
    console.print("[bold]System Diagnostics[/bold]\n")

    sys_diag = SystemDiagnostics()
    sys_results = sys_diag.run_all()

    for result in sys_results:
        status = "[green]✓[/green]" if result.level.value == "PASS" else f"[{result.level.name.lower()}]⚠[/{result.level.name.lower()}]"

        console.print(f"{status} {result.name}: {result.message}")
        all_results.append(result)

    # Network
    console.print("\n[bold]Network Diagnostics[/bold]\n")

    net_diag = NetworkDiagnostics()
    net_results = net_diag.run_all()

    for result in net_results:
        status = "[green]✓[/green]" if result.level.value == "PASS" else f"[{result.level.name.lower()}]⚠[/{result.level.name.lower()}]"

        console.print(f"{status} {result.name}: {result.message}")
        all_results.append(result)

    # WireGuard
    console.print("\n[bold]WireGuard Diagnostics[/bold]\n")

    wg_diag = WireGuardDiagnostics()
    wg_results = wg_diag.run_all(selected_interface())

    for result in wg_results:
        status = "[green]✓[/green]" if result.level.value == "PASS" else f"[{result.level.name.lower()}]⚠[/{result.level.name.lower()}]"

        console.print(f"{status} {result.name}: {result.message}")
        all_results.append(result)

    # Firewall
    console.print("\n[bold]Firewall Diagnostics[/bold]\n")

    fw_diag = FirewallDiagnostics()
    fw_results = fw_diag.run_all(51820)

    for result in fw_results:
        status = "[green]✓[/green]" if result.level.value == "PASS" else f"[{result.level.name.lower()}]⚠[/{result.level.name.lower()}]"

        console.print(f"{status} {result.name}: {result.message}")
        all_results.append(result)

    # Overall status
    console.print("\n" + "=" * 50)

    overall = sys_diag.overall_level(all_results)

    if overall.value == "PASS":
        console.print("[green]Overall: HEALTHY ✓[/green]")
    elif overall.value == "WARNING":
        console.print("[yellow]Overall: NEEDS ATTENTION ⚠[/yellow]")
    else:
        console.print("[red]Overall: CRITICAL ✗[/red]")

    print("=" * 50)

    pause()


def run_system_diagnostics() -> None:
    """Run system diagnostics."""
    clear_screen()

    console.print("[bold]System Diagnostics[/bold]\n")

    diag = SystemDiagnostics()
    results = diag.run_all()

    for result in results:
        status = "[green]✓[/green]" if result.level.value == "PASS" else f"[{result.level.name.lower()}]⚠[/{result.level.name.lower()}]"

        console.print(f"{status} {result.name}: {result.message}")

        if result.details:
            console.print(f"   {result.details}")

    pause()


def run_network_diagnostics() -> None:
    """Run network diagnostics."""
    clear_screen()

    console.print("[bold]Network Diagnostics[/bold]\n")

    diag = NetworkDiagnostics()
    results = diag.run_all()

    for result in results:
        status = "[green]✓[/green]" if result.level.value == "PASS" else f"[{result.level.name.lower()}]⚠[/{result.level.name.lower()}]"

        console.print(f"{status} {result.name}: {result.message}")

        if result.details:
            console.print(f"   {result.details}")

    pause()


def run_wireguard_diagnostics() -> None:
    """Run WireGuard diagnostics."""
    clear_screen()

    console.print("[bold]WireGuard Diagnostics[/bold]\n")

    diag = WireGuardDiagnostics()
    results = diag.run_all(selected_interface())

    for result in results:
        status = "[green]✓[/green]" if result.level.value == "PASS" else f"[{result.level.name.lower()}]⚠[/{result.level.name.lower()}]"

        console.print(f"{status} {result.name}: {result.message}")

        if result.details:
            console.print(f"   {result.details}")

    pause()


def run_firewall_diagnostics() -> None:
    """Run firewall diagnostics."""
    clear_screen()

    console.print("[bold]Firewall Diagnostics[/bold]\n")

    diag = FirewallDiagnostics()
    results = diag.run_all(51820)

    for result in results:
        status = "[green]✓[/green]" if result.level.value == "PASS" else f"[{result.level.name.lower()}]⚠[/{result.level.name.lower()}]"

        console.print(f"{status} {result.name}: {result.message}")

        if result.details:
            console.print(f"   {result.details}")

    pause()


def backup_menu() -> None:
    """Backup and restore menu."""
    while True:
        clear_screen()
        show_header_info()

        section_banner("Backup & Restore Menu", "Protect or recover LoomWG data")
        menu_option(1, "Create backup", "Save current LoomWG data")
        menu_option(2, "Restore backup", "Recover saved LoomWG data")
        menu_option(3, "Delete backup", "Permanently delete a backup")
        print()
        menu_option(4, "List backups", "Show available backup files")
        print("  0) Back\n")

        choice = input("Select option: ").strip()

        if choice == "1":
            create_backup()
        elif choice == "2":
            restore_backup()
        elif choice == "3":
            delete_backup()
        elif choice == "4":
            list_backups()
        elif choice == "0":
            break
        else:
            print("Invalid option.")
            pause()


def create_backup() -> None:
    """Create a backup."""
    clear_screen()
    section_banner("Create backup", "Save the current LoomWG and WireGuard state")

    try:
        description = input("Backup description (optional): ").strip()

        console.print("\n[bold]Creating backup...[/bold]")

        backup_mgr = BackupManager()
        backup_file = backup_mgr.create_backup(description)

        if backup_file:
            console.print(f"[green]✓ Backup created: {backup_file}[/green]")

            logger = LoomLogger()
            logger.info(f"Backup created: {backup_file}", "backup")
        else:
            console.print("[red]✗ Failed to create backup[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()


def list_backups() -> None:
    """List available backups."""
    clear_screen()

    try:
        backup_mgr = BackupManager()
        backups = backup_mgr.list_backups()

        if not backups:
            console.print("[yellow]No backups found[/yellow]")
            pause()
            return

        table = Table(title="Available Backups")

        table.add_column("Filename", style="cyan")
        table.add_column("Created", style="yellow")

        for filename, created in backups:
            table.add_row(filename, created.strftime("%Y-%m-%d %H:%M:%S"))

        console.print(table)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()


def restore_backup() -> None:
    """Restore from backup."""
    clear_screen()
    section_banner("Restore backup", "Recover a saved LoomWG state")

    try:
        backup_mgr = BackupManager()
        backups = backup_mgr.list_backups()

        if not backups:
            console.print("[yellow]No backups available[/yellow]")
            pause()
            return

        console.print("[bold]Available Backups[/bold]\n")

        for i, (filename, created) in enumerate(backups, 1):
            print(f"  {i}) {filename} ({created.strftime('%Y-%m-%d %H:%M:%S')})")

        choice = input("\nSelect backup (number): ").strip()

        try:
            idx = int(choice) - 1

            if idx < 0 or idx >= len(backups):
                console.print("[red]Invalid selection[/red]")
                pause()
                return

            backup_filename, _ = backups[idx]
            backup_file = backup_mgr.backup_dir / backup_filename

            if confirm("Restore from this backup? Current configuration will be backed up."):
                console.print("\n[bold]Restoring...[/bold]")

                if backup_mgr.restore_backup(backup_file):
                    console.print("[green]✓ Restore successful[/green]")

                    logger = LoomLogger()
                    logger.info(f"Backup restored: {backup_filename}", "backup")
                else:
                    console.print("[red]✗ Restore failed[/red]")

        except ValueError:
            console.print("[red]Invalid input[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()


def delete_backup() -> None:
    """Delete a backup."""
    clear_screen()
    section_banner("Delete backup", "Permanently remove a saved backup")

    try:
        backup_mgr = BackupManager()
        backups = backup_mgr.list_backups()

        if not backups:
            console.print("[yellow]No backups available[/yellow]")
            pause()
            return

        console.print("[bold]Available Backups[/bold]\n")

        for i, (filename, created) in enumerate(backups, 1):
            print(f"  {i}) {filename} ({created.strftime('%Y-%m-%d %H:%M:%S')})")

        choice = input("\nSelect backup to delete (number): ").strip()

        try:
            idx = int(choice) - 1

            if idx < 0 or idx >= len(backups):
                console.print("[red]Invalid selection[/red]")
                pause()
                return

            backup_filename, _ = backups[idx]
            backup_file = backup_mgr.backup_dir / backup_filename

            if confirm(f"Delete {backup_filename}? This cannot be undone."):
                if backup_mgr.delete_backup(backup_file):
                    console.print("[green]✓ Backup deleted[/green]")

                    logger = LoomLogger()
                    logger.info(f"Backup deleted: {backup_filename}", "backup")
                else:
                    console.print("[red]✗ Failed to delete backup[/red]")

        except ValueError:
            console.print("[red]Invalid input[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()


def logs_menu() -> None:
    """Logs menu."""
    while True:
        clear_screen()
        show_header_info()

        print("Logs Menu\n")
        menu_option(1, "View recent logs", "Show the latest LoomWG activity")
        menu_option(2, "Clear logs", "Permanently remove saved log entries")
        menu_option(3, "Export logs", "Save logs to a JSON file")
        print("  0) Back\n")

        choice = input("Select option: ").strip()

        if choice == "1":
            view_logs()
        elif choice == "2":
            clear_logs()
        elif choice == "3":
            export_logs()
        elif choice == "0":
            break
        else:
            print("Invalid option.")
            pause()


def view_logs() -> None:
    """View recent logs."""
    clear_screen()

    try:
        logger = LoomLogger()
        logs = logger.list_recent(50)

        if not logs:
            console.print("[yellow]No logs found[/yellow]")
            pause()
            return

        console.print("[bold]Recent Logs[/bold]\n")

        for log in logs:
            timestamp = log.get("timestamp", "")
            level = log.get("level", "")
            message = log.get("message", "")
            category = log.get("category", "")

            level_color = {
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red",
            }.get(level, "white")

            console.print(
                f"[{level_color}][{level}][/{level_color}] {timestamp} [{category}] {message}"
            )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()


def clear_logs() -> None:
    """Clear all logs."""
    if confirm("Clear all logs? This cannot be undone."):
        try:
            logger = LoomLogger()

            if logger.clear_logs():
                console.print("[green]✓ Logs cleared[/green]")
            else:
                console.print("[red]✗ Failed to clear logs[/red]")

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    pause()


def export_logs() -> None:
    """Export logs to file."""
    clear_screen()

    try:
        filename = input("Export filename (default: loomwg_logs.json): ").strip()

        if not filename:
            filename = "loomwg_logs.json"

        logger = LoomLogger()
        export_path = Path(filename)

        if logger.export_logs(export_path):
            console.print(f"[green]✓ Logs exported to {filename}[/green]")
        else:
            console.print("[red]✗ Failed to export logs[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    pause()


def system_info_menu() -> None:
    """Display a comprehensive, read-only server and VPN information dashboard."""
    clear_screen()
    detector = SystemDetector()
    info = detector.detect()
    def command(*args: str) -> str:
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=5, check=False)
            return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else "N/A"
        except OSError:
            return "N/A"

    def section(title: str, rows: list[tuple[str, object]]) -> None:
        """Print aligned labels, preserving readable wrapping for long values."""
        table = Table.grid(padding=(0, 1), expand=True)
        table.add_column(style="bold cyan", width=22, no_wrap=True)
        table.add_column()
        for label, value in rows:
            table.add_row(f"{label}:", str(value) if value not in (None, "") else "N/A")
        console.print(f"\n[bold]{title}[/bold]")
        console.print(table)

    config_path = Path("/etc/wireguard/wg0.conf")
    config = ServerConfig.from_file(config_path)
    firewall = FirewalldManager()
    wg = WireGuardManager()
    dashboard = _wg_runtime_dashboard() if wg.is_interface_active("wg0") else None
    console.print("[bold]System Information[/bold]\n" + "═" * 39)
    section("Server", [("Hostname", info.hostname), ("OS", info.os_name), ("Kernel", info.kernel), ("Architecture", info.architecture), ("Init system", info.init_system), ("Package manager", info.package_manager), ("Uptime", command("uptime", "-p")), ("Boot time", command("uptime", "-s")), ("Date / timezone", command("date", "+%F %T %Z"))])
    section("Resources", [("CPU", command("sh", "-c", "lscpu | awk -F: '/Model name/ {print $2; exit}'")), ("CPU usage", command("sh", "-c", "top -bn1 | awk '/Cpu\\(s\\)/ {print $2 \"%\"; exit}'")), ("Memory", command("sh", "-c", "free -h | awk 'NR==2 {print \"total \" $2 \", used \" $3 \", available \" $7}'")), ("Swap", command("sh", "-c", "free -h | awk 'NR==3 {print \"total \" $2 \", used \" $3}'")), ("Disk /", command("sh", "-c", "df -h / | awk 'NR==2 {print \"used \" $3 \" of \" $2 \" (\" $5 \")\"}'")), ("Load average", command("sh", "-c", "cut -d' ' -f1-3 /proc/loadavg"))])
    section("Network", [("Public IPv4", info.public_ip or "N/A"), ("Default interface", info.default_interface or "N/A"), ("IPv4 gateway", command("sh", "-c", "ip route | awk '/default/ {print $3; exit}'")), ("IPv6 gateway", command("sh", "-c", "ip -6 route | awk '/default/ {print $3; exit}'")), ("DNS servers", command("sh", "-c", "awk '/^nameserver/ {print $2}' /etc/resolv.conf | paste -sd, -"))])
    section("Firewall & Security", [("firewalld installed", "YES" if firewall.is_installed() else "NO"), ("firewalld running", "YES" if firewall.is_running() else "NO"), ("Active zone", command("firewall-cmd", "--get-active-zones") if firewall.is_running() else "N/A"), ("IPv4 forwarding", "ENABLED" if NetworkManager().is_ipv4_forwarding_enabled() else "DISABLED"), ("SELinux", command("getenforce")), ("Current user", command("id", "-un")), ("Root privileges", "YES" if info.is_root else "NO")])
    section("WireGuard", [("Installed", "YES" if wg.is_installed() else "NO"), ("Tools version", command("wg", "--version")), ("Interfaces", ", ".join(wg.list_interfaces()) or "None"), ("Status", "RUNNING" if wg.is_interface_active("wg0") else "DOWN"), ("Listening port", config.listen_port if config_path.exists() else "N/A"), ("Server addresses", f"{config.get_ipv4_server_address()} / {config.get_ipv6_server_address()}" if config_path.exists() else "N/A"), ("Peers", dashboard["total"] if dashboard else 0), ("Active peers", dashboard["online"] if dashboard else 0), ("Traffic RX / TX", f"{dashboard['rx']} / {dashboard['tx']}" if dashboard else "0 B / 0 B")])
    section("WireGuard Service", [("Active", "YES" if ServiceManager().is_active("wg-quick@wg0") else "NO"), ("Enabled on boot", "YES" if ServiceManager().is_enabled("wg-quick@wg0") else "NO"), ("Configuration", config_path), ("Config exists", "YES" if config_path.exists() else "NO"), ("Config permissions", oct(config_path.stat().st_mode & 0o777) if config_path.exists() else "N/A")])
    section("VPN Network", [("IPv4 subnet", config.ipv4_network if config_path.exists() else "N/A"), ("IPv6 subnet", config.ipv6_network if config_path.exists() else "N/A"), ("IPv4 forwarding", "ENABLED" if NetworkManager().is_ipv4_forwarding_enabled() else "DISABLED"), ("IPv6 forwarding", "ENABLED" if NetworkManager().is_ipv6_forwarding_enabled() else "DISABLED"), ("NAT", "ENABLED" if firewall.is_masquerading_enabled() else "DISABLED")])
    section("LoomWG", [("Version", "0.1.0"), ("Python", sys.version.split()[0]), ("Executable", sys.executable), ("Working directory", Path.cwd()), ("Stored peers", len(PeerManager().list_peers()))])
    console.print("\n[bold]Runtime detail[/bold]")
    for title, details in [
        ("Interfaces", command("ip", "-brief", "address")),
        ("Routing table", command("ip", "route")),
        ("IPv6 routing table", command("ip", "-6", "route")),
        ("Listening TCP ports", command("ss", "-ltn")),
        ("Listening UDP ports", command("ss", "-lun")),
        ("WireGuard runtime", command("wg", "show", "wg0")),
        ("WireGuard service", command("systemctl", "status", "wg-quick@wg0", "--no-pager")),
    ]:
        console.print(Panel(details, title=title, border_style="dim"))

    pause()


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


def import_server_peers() -> None:
    """Import public peer entries from the selected interface config."""
    clear_screen()
    section_banner("Import peers", f"Import clients from {selected_interface()}")
    peer_mgr = PeerManager()
    interface = selected_interface()
    entries = ConfigGenerator.parse_server_peers(interface_config_path(interface))
    imported = 0
    for index, entry in enumerate(entries, 1):
        if peer_mgr.get_peer_by_public_key(entry["public_key"]):
            continue
        addresses = [item.strip() for item in entry["allowed_ips"].split(",")]
        ipv4 = next((item for item in addresses if "." in item), "")
        ipv6 = next((item for item in addresses if ":" in item), "")
        if not ipv4 or not ipv6:
            continue
        name = f"imported-{index}"
        while peer_mgr.peer_exists(name): name += "-x"
        if peer_mgr.add_peer(Peer(name=name, ipv4_address=ipv4, ipv6_address=ipv6, public_key=entry["public_key"])):
            imported += 1
    console.print(f"[green]✓ Imported {imported} peer(s)[/green]")
    pause()


def version_menu() -> None:
    """Show the installed LoomWG version and the most recent changelog entry."""
    clear_screen()
    version = "0.1.0"
    changelog = Path(__file__).resolve().parents[1] / "CHANGELOG.md"
    latest = "N/A"
    try:
        sections = changelog.read_text(encoding="utf-8").split("## [")
        if len(sections) > 1:
            latest = "## [" + sections[1].split("## [", 1)[0].strip()
    except OSError:
        pass
    console.print(f"[bold]LoomWG {version}[/bold]\n\n[bold]Latest changes[/bold]\n{latest}")
    pause()
