import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .network import NetworkManager


@dataclass
class SystemInfo:
    """Information about the current system."""

    os_id: str
    os_name: str
    os_version: str
    kernel: str
    architecture: str
    hostname: str
    is_root: bool
    init_system: str
    package_manager: str
    firewalld_available: bool
    firewalld_running: bool
    wireguard_available: bool
    public_ip: str | None
    default_interface: str | None


@dataclass
class SystemCheck:
    """Result of a system check."""

    name: str
    passed: bool
    message: str


class SystemDetector:
    """Detect system information and capabilities."""

    def detect(self) -> SystemInfo:
        os_release = self._read_os_release()

        os_id = os_release.get("ID", platform.system().lower())
        os_name = os_release.get("PRETTY_NAME", platform.system())
        os_version = os_release.get("VERSION_ID", platform.release())

        network = NetworkManager()
        default_interface = network.get_default_interface()
        public_ip = self._get_public_ip()

        return SystemInfo(
            os_id=os_id,
            os_name=os_name,
            os_version=os_version,
            kernel=platform.release(),
            architecture=platform.machine(),
            hostname=platform.node(),
            is_root=self._is_root(),
            init_system=self._detect_init_system(),
            package_manager=self._detect_package_manager(),
            firewalld_available=self._command_exists("firewall-cmd"),
            firewalld_running=self._is_firewalld_running(),
            wireguard_available=self._command_exists("wg"),
            public_ip=public_ip,
            default_interface=default_interface,
        )

    def check(self) -> list[SystemCheck]:
        """Run basic LoomWG system checks."""

        info = self.detect()

        return [
            SystemCheck(
                name="Operating system",
                passed=info.os_id == "rocky",
                message=(
                    f"{info.os_name}"
                    if info.os_id == "rocky"
                    else f"Unsupported OS: {info.os_name}"
                ),
            ),
            SystemCheck(
                name="Architecture",
                passed=info.architecture in ("x86_64", "amd64"),
                message=info.architecture,
            ),
            SystemCheck(
                name="Root privileges",
                passed=info.is_root,
                message=(
                    "Running as root"
                    if info.is_root
                    else "LoomWG must be run as root"
                ),
            ),
            SystemCheck(
                name="Init system",
                passed=info.init_system == "systemd",
                message=info.init_system,
            ),
            SystemCheck(
                name="Package manager",
                passed=info.package_manager == "dnf",
                message=info.package_manager,
            ),
            SystemCheck(
                name="firewalld",
                passed=info.firewalld_available,
                message=(
                    "Available"
                    if info.firewalld_available
                    else "Not installed"
                ),
            ),
        ]

    @staticmethod
    def _read_os_release() -> dict[str, str]:
        """Read /etc/os-release."""

        path = Path("/etc/os-release")

        if not path.exists():
            return {}

        result: dict[str, str] = {}

        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()

            if not line or "=" not in line:
                continue

            key, value = line.split("=", 1)
            result[key] = value.strip('"')

        return result

    @staticmethod
    def _is_root() -> bool:
        """Check root privileges."""

        if os.name == "nt":
            return False

        return os.geteuid() == 0

    @staticmethod
    def _command_exists(command: str) -> bool:
        """Check whether a command is available."""

        return shutil.which(command) is not None

    def _detect_init_system(self) -> str:
        """Detect init system."""

        if os.name == "nt":
            return "Windows"

        if self._command_exists("systemctl"):
            return "systemd"

        if self._command_exists("rc-service"):
            return "OpenRC"

        return "Unknown"

    def _detect_package_manager(self) -> str:
        """Detect package manager."""

        package_managers = (
            ("dnf", "dnf"),
            ("yum", "yum"),
            ("apt-get", "apt"),
            ("pacman", "pacman"),
            ("apk", "apk"),
        )

        for command, name in package_managers:
            if self._command_exists(command):
                return name

        if os.name == "nt":
            return "Windows"

        return "Unknown"

    def _is_firewalld_running(self) -> bool:
        """Check whether firewalld is running."""

        if not self._command_exists("firewall-cmd"):
            return False

        try:
            result = subprocess.run(
                ["firewall-cmd", "--state"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            return (
                result.returncode == 0
                and result.stdout.strip() == "running"
            )

        except (OSError, subprocess.SubprocessError):
            return False

    @staticmethod
    def _get_public_ip() -> str | None:
        """Get the public IPv4 address if available."""

        for url in (
            "https://api.ipify.org",
            "https://checkip.amazonaws.com",
            "https://ifconfig.me/ip",
        ):
            try:
                result = subprocess.run(
                    ["curl", "-fsSL", url],
                    capture_output=True,
                    text=True,
                    timeout=8,
                    check=False,
                )
                if result.returncode == 0:
                    ip = result.stdout.strip()
                    if ip:
                        return ip
            except (OSError, subprocess.SubprocessError):
                continue

        return None