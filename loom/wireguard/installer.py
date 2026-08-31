from dataclasses import dataclass
from pathlib import Path

from ..system.command import CommandRunner
from ..system.info import SystemDetector
from ..system.packages import PackageManager
from .manager import WireGuardManager


@dataclass
class InstallResult:
    """Result of WireGuard installation."""

    success: bool
    message: str


class WireGuardInstaller:
    """Install and configure WireGuard on Rocky Linux."""

    REQUIRED_PACKAGES = [
        "wireguard-tools",
        "qrencode",
        "firewalld",
    ]

    ROCKY_EXTRA_PACKAGES = [
        "elrepo-release",
    ]

    ROCKY_KERNEL_MODULE_CANDIDATES = [
        "kmod-wireguard",
        "wireguard-dkms",
        "wireguard-kmod",
        "wireguard",
    ]

    def __init__(
        self,
        runner: CommandRunner | None = None,
        detector: SystemDetector | None = None,
        package_manager: PackageManager | None = None,
        wireguard: WireGuardManager | None = None,
        interface_name: str = "wg0",
    ):
        self.runner = runner or CommandRunner()
        self.detector = detector or SystemDetector()
        self.package_manager = package_manager or PackageManager(
            self.runner
        )
        self.wireguard = wireguard or WireGuardManager(
            self.runner
        )

        self.interface_name = interface_name
        self.config_dir = Path("/etc/wireguard")

    def install(self, interface: str | None = None) -> InstallResult:
        """Run the complete WireGuard installation for a chosen interface."""
        if interface:
            self.interface_name = interface

        checks = self.detector.check()

        failed_checks = [
            check for check in checks
            if not check.passed
        ]

        if failed_checks:
            messages = "\n".join(
                f"- {check.name}: {check.message}"
                for check in failed_checks
            )

            return InstallResult(
                success=False,
                message=(
                    "System requirements are not satisfied:\n"
                    f"{messages}"
                ),
            )

        if not self._install_packages():
            return InstallResult(
                success=False,
                message="Failed to install required packages.",
            )

        if not self._install_rocky_kernel_module():
            return InstallResult(
                success=False,
                message=(
                    "WireGuard kernel support is not available. "
                    "Install ELRepo and kmod-wireguard, then reboot the server."
                ),
            )

        if not self._create_config_directory():
            return InstallResult(
                success=False,
                message="Failed to create /etc/wireguard.",
            )

        if not self._enable_ip_forwarding():
            return InstallResult(
                success=False,
                message="Failed to enable IP forwarding.",
            )

        return InstallResult(
            success=True,
            message="WireGuard packages installed successfully.",
        )

    def _install_packages(self) -> bool:
        """Install required system packages."""

        if not self.package_manager.update():
            return False

        missing_packages = [
            package
            for package in self.REQUIRED_PACKAGES
            if not self.package_manager.is_installed(package)
        ]

        if not missing_packages:
            return True

        return self.package_manager.install(
            missing_packages
        )

    def _install_rocky_kernel_module(self) -> bool:
        """Install the Rocky kernel module package required for wg-quick to work."""
        info = self.detector.detect()
        if info.os_id not in {"rocky", "almalinux", "centos", "rhel"}:
            return True

        if self._wireguard_module_available():
            return True

        for package in self.ROCKY_EXTRA_PACKAGES:
            if not self.package_manager.is_installed(package):
                if not self.package_manager.install([package]):
                    return False

        for package in self.ROCKY_KERNEL_MODULE_CANDIDATES:
            if self.package_manager.is_installed(package):
                return True

            if self.package_manager.install([package]):
                return True

        return self._wireguard_module_available()

    def _wireguard_module_available(self) -> bool:
        """Check whether the kernel WireGuard module is present or loadable."""
        checks = [
            ["modprobe", "wireguard"],
            ["bash", "-lc", "ls /lib/modules/$(uname -r)/kernel/net/wireguard 2>/dev/null"],
            ["bash", "-lc", "ls /lib/modules/$(uname -r)/extra/wireguard 2>/dev/null"],
        ]

        for command in checks:
            result = self.runner.run(command, timeout=30)
            if result.success:
                return True

        return False

    def _create_config_directory(self) -> bool:
        """Create WireGuard configuration directory."""

        try:
            self.config_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            self.config_dir.chmod(0o700)

            return True

        except OSError:
            return False

    def _enable_ip_forwarding(self) -> bool:
        """Enable IPv4 and IPv6 forwarding."""

        sysctl_file = Path(
            "/etc/sysctl.d/99-loomwg.conf"
        )

        configuration = (
            "net.ipv4.ip_forward = 1\n"
            "net.ipv6.conf.all.forwarding = 1\n"
        )

        try:
            sysctl_file.write_text(
                configuration,
                encoding="utf-8",
            )

        except OSError:
            return False

        result = self.runner.run(
            ["sysctl", "--system"],
            timeout=30,
        )

        return result.success