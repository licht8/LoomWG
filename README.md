# LoomWG

LoomWG is a professional Python-based CLI application for installing, configuring, managing, monitoring, and troubleshooting WireGuard VPN servers on Rocky Linux.

## Features

- **WireGuard Installation**: Automated, idempotent installation with system verification for Rocky Linux
- **Server Configuration**: Interactive setup with validation and sensible defaults
- **Peer Management**: Create, list, disable, enable, and remove VPN peers
- **IP Allocation**: Automatic private IP assignment with conflict prevention
- **Firewall Integration**: Automatic firewalld configuration with port management
- **Network Configuration**: IPv4/IPv6 forwarding setup and verification
- **Diagnostics**: Comprehensive health checks across all subsystems
- **Backup & Restore**: Full configuration snapshots with recovery capabilities
- **Logging**: Detailed operational logs without exposing secrets
- **CLI Interface**: Interactive menu-driven terminal interface

## Requirements

- **OS**: Rocky Linux 9 or 10 (x86_64)
- **Root privileges**: Required for all operations
- **Python**: 3.12+
- **systemd**: For service management
- **firewalld**: For firewall management
- **WireGuard kernel module**: Included in Rocky Linux

## Installation

```bash
git clone https://github.com/licht8/LoomWG.git
cd LoomWG
chmod +x ./run.sh
```

### CentOS Stream 9 installation

LoomWG requires Python 3.12 or newer. On CentOS Stream 9, the system Python remains Python 3.9 and must not be replaced.

Install the supported Python runtime for the project:

```bash
sudo dnf install -y python3.12 python3.12-pip python3.12-devel
```

Create a dedicated virtual environment using the built-in venv module:

```bash
cd /root/loomwg
python3.12 -m venv .venv
source .venv/bin/activate
```

Verify that the project environment is using Python 3.12:

```bash
python --version
```

Expected output:

```bash
Python 3.12.x
```

Install LoomWG into the virtual environment:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

### Usage

The recommended startup flow is the project script:

```bash
./run.sh
```

## Project Structure

```
loom/
├── system/              # OS operations and detection
│   ├── command.py      # Command execution wrapper
│   ├── info.py         # System detection
│   ├── packages.py     # Package management (dnf)
│   ├── services.py     # systemd service management
│   └── network.py      # Network configuration
├── wireguard/          # WireGuard management
│   ├── installer.py    # Installation automation
│   ├── manager.py      # Interface/service control
│   ├── server_config.py    # Server configuration
│   ├── config_generator.py # Config file generation
│   ├── key_manager.py  # Key generation/management
│   ├── peer_manager.py # Peer CRUD operations
│   ├── ip_allocator.py # IP address allocation
│   └── status.py       # Status parsing
├── firewall/           # firewalld integration
│   └── firewalld.py    # Firewall rules management
├── diagnostics/        # System diagnostics
│   ├── system.py       # System checks
│   ├── network.py      # Network checks
│   ├── wireguard.py    # WireGuard checks
│   └── firewall.py     # Firewall checks
├── backup/             # Backup/restore functionality
│   └── manager.py      # Backup management
├── logging_system/     # Logging subsystem
│   └── logger.py       # Event logging
└── cli.py              # Interactive CLI interface
```

## Configuration

### Server Configuration

WireGuard configuration is stored at `/etc/wireguard/wg0.conf` with secure permissions (600).

Default settings:
- Interface: `wg0`
- IPv4 Network: `10.66.66.0/24`
- IPv6 Network: `fd42:42:42::/64`
- Listen Port: `51820`
- DNS: `1.1.1.1`, `1.0.0.1`

### Peer Database

Peer information is stored in the app directory at `<project-root>/data/peers.json` for tracking and management.

### Client Configs

Exported user/client `.conf` files are stored in `<project-root>/data/clients/`.
Generated QR code images are stored in `<project-root>/data/qr_codes/` and are also printed in the console after peer creation.

### Logs

Operational logs are stored at `<project-root>/logs/loomwg_YYYYMMDD.log`.

### Backups

Configuration backups are stored at `<project-root>/backups/`.

### Testing

Run tests with pytest:

```bash
pytest tests/
```

## Troubleshooting

### WireGuard Installation Fails

Run diagnostics to identify issues:

```bash
# From main menu → Diagnostics → Full health check
```

### Port Already in Use

Check what's using port 51820:

```bash
sudo netstat -tlnp | grep 51820
```

Change the listen port in server configuration if needed.

### Firewall Issues

Verify firewall configuration:

```bash
# From main menu → Firewall → Show status
# Or from Diagnostics → Firewall diagnostics
```

### Peer Cannot Connect

1. Check server is running: `ip link show wg0`
2. Verify peer config has correct server endpoint
3. Check firewall allows UDP 51820
4. Review logs: Main menu → Logs → View recent logs

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or suggestions, please open an issue on the repository.

---
