"""Diagnostics commands."""
import subprocess
from pathlib import Path

from rich.console import Console
console = Console()

from ..diagnostics import FirewallDiagnostics, NetworkDiagnostics, SystemDiagnostics, WireGuardDiagnostics
from ..wireguard.manager import WireGuardManager
from ..system.network import NetworkManager
from ..system.info import SystemDetector
from ..wireguard.server_config import ServerConfig
from ..wireguard.interfaces import config_path as interface_config_path
from ..cli.common import selected_interface
from ..cli.common import selected_interface, clear_screen, section_banner, pause


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




