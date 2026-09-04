"""Auto-extracted from cli/__init__.py"""
import subprocess
from datetime import datetime

from rich.console import Console
from rich.table import Table

from ..wireguard.manager import WireGuardManager
from ..wireguard.interfaces import config_path as interface_config_path

from ..wireguard.server_config import ServerConfig
from ..wireguard.peer_manager import PeerManager
from ..cli.common import clear_screen, section_banner, selected_interface

console = Console()

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




