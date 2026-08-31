"""Tests for WireGuard installer prerequisites."""

from loom.wireguard.installer import WireGuardInstaller


class TestWireGuardInstaller:
    """Validate installation prerequisites."""

    def test_required_packages_do_not_require_resolvconf(self):
        """Rocky 10 does not ship the `resolvconf` package, so we must not require it."""
        assert "resolvconf" not in WireGuardInstaller.REQUIRED_PACKAGES
