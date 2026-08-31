"""Tests for saved client config artifacts."""

from pathlib import Path

from loom.wireguard.client_config import ClientConfigStore


class TestClientConfigStore:
    """Validate client config storage."""

    def test_save_peer_config_creates_directory(self, tmp_path):
        """Saving a peer config should create the client directory and config file."""
        store = ClientConfigStore(base_dir=tmp_path)

        config_file = store.save_peer_config("phone", "[Interface]\nPrivateKey = test\n")

        assert config_file.exists()
        assert config_file.parent == tmp_path
        assert config_file.name == "phone.conf"

    def test_save_qr_code_uses_data_directory(self, tmp_path):
        """QR images should be saved separately from client config files."""
        store = ClientConfigStore(base_dir=tmp_path / "clients", qr_dir=tmp_path / "data")

        qr_file = store.save_qr_code("phone", "[Interface]\nPrivateKey = test\n")

        if qr_file is None:
            pytest.skip("qrcode dependency is not installed")

        assert qr_file.exists()
        assert qr_file.parent == tmp_path / "data"
        assert qr_file.name == "phone.png"

    def test_regenerate_after_server_key_rotation_preserves_client_private_key(self, tmp_path):
        """Rotation should update only the server key and regenerate the QR artifact."""
        store = ClientConfigStore(base_dir=tmp_path / "clients", qr_dir=tmp_path / "data")
        old_config = (
            "[Interface]\n"
            "Address = 10.66.66.2/32, fd42:42:42::2/128\n"
            "PrivateKey = client-private-key\n"
            "\n"
            "[Peer]\n"
            "PublicKey = old-server-key\n"
            "Endpoint = 203.0.113.10:51820\n"
        )
        store.save_peer_config("phone", old_config)

        regenerated, failed = store.regenerate_after_server_key_rotation(
            "new-server-key",
            ["phone"],
        )

        assert regenerated == ["phone"]
        assert failed == []
        updated = (tmp_path / "clients" / "phone.conf").read_text()
        assert "PrivateKey = client-private-key" in updated
        assert "PublicKey = new-server-key" in updated
        assert (tmp_path / "data" / "phone.png").exists()
