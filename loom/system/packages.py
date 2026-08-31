from .command import CommandRunner


class PackageManager:
    """Package management abstraction."""

    def __init__(self, runner: CommandRunner | None = None):
        self.runner = runner or CommandRunner()

    def is_installed(self, package: str) -> bool:
        result = self.runner.run(
            ["rpm", "-q", package],
        )

        return result.success

    def install(self, packages: list[str]) -> bool:
        if not packages:
            return True

        install_command = ["dnf", "install", "-y", *packages]
        result = self.runner.run(
            install_command,
            timeout=300,
        )

        if result.success:
            return True

        if self._needs_epel_retry(result):
            if not self._enable_epel():
                return False

            retry_result = self.runner.run(
                install_command,
                timeout=300,
            )
            return retry_result.success

        return False

    def remove(self, packages: list[str]) -> bool:
        if not packages:
            return True

        result = self.runner.run(
            ["dnf", "remove", "-y", *packages],
            timeout=300,
        )

        return result.success

    def update(self) -> bool:
        result = self.runner.run(
            ["dnf", "makecache", "--refresh"],
            timeout=300,
        )

        return result.success

    @staticmethod
    def _needs_epel_retry(result) -> bool:
        combined_output = f"{result.stdout}\n{result.stderr}".lower()
        missing_markers = (
            "no match for argument",
            "unable to find a match",
            "not available",
            "no package",
            "nothing to do",
        )
        return any(marker in combined_output for marker in missing_markers)

    def _enable_epel(self) -> bool:
        install_epel = self.runner.run(
            ["dnf", "install", "-y", "epel-release"],
            timeout=300,
        )

        if install_epel.success:
            return True

        version_result = self.runner.run(
            ["bash", "-lc", "rpm -E %rhel"],
            timeout=30,
        )

        if not version_result.success:
            return False

        rhel = version_result.stdout.strip()
        url = (
            f"https://dl.fedoraproject.org/pub/epel/epel-release-latest-{rhel}.noarch.rpm"
        )

        direct_install = self.runner.run(
            ["dnf", "install", "-y", url],
            timeout=300,
        )

        return direct_install.success

    def get_version(self, package: str) -> str | None:
        result = self.runner.run(
            ["rpm", "-q", "--qf", "%{VERSION}-%{RELEASE}", package],
        )

        if not result.success:
            return None

        return result.stdout