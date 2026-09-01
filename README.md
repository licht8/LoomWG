# LoomWG

LoomWG is a professional Python-based CLI application for installing, configuring, managing, monitoring, and troubleshooting WireGuard VPN servers on CentOS, Rocky Linux, AlmaLinux, and other RHEL-family Linux distributions.

## Features

- **WireGuard Installation**: Automated, idempotent installation with system verification for CentOS/RHEL-family servers
- **Server Configuration**: Interactive setup with validation and sensible defaults
- **Peer Management**: Create, list, disable, enable, revoke, rotate keys, and remove VPN peers
- **IP Allocation**: Automatic private IP assignment with conflict prevention
- **Firewall Integration**: Automatic firewalld configuration with port management
- **Network Configuration**: IPv4/IPv6 forwarding setup and verification
- **Diagnostics**: Comprehensive health checks across all subsystems
- **Backup & Restore**: Full configuration snapshots with recovery capabilities
- **Logging**: Detailed operational logs without exposing secrets
- **CLI Interface**: Interactive menu-driven terminal interface

## Requirements

- **OS**: CentOS Stream 8/9/10, Rocky Linux 8/9/10, AlmaLinux 8/9/10, or other RHEL-family Linux distributions
- **Root privileges**: Required for all operations
- **Python**: 3.12+
- **systemd**: For service management
- **firewalld**: For firewall management
- **WireGuard kernel module**: Provided by the OS package set or ELRepo on supported distributions

## Installation

```bash
git clone https://github.com/licht8/LoomWG.git
cd LoomWG
chmod +x ./run.sh
```

The project script will bootstrap the environment as needed and can be used as the recommended startup flow:

```bash
./run.sh
```

### Supported RHEL-family install flow

LoomWG requires Python 3.12 or newer. The system Python may remain 3.9/3.8 on CentOS/Alma/Rocky, so the project uses a dedicated virtual environment rather than replacing the system interpreter.

Install the supported Python runtime for the project:

```bash
sudo dnf install -y python3.12 python3.12-pip python3.12-devel
```

Create a dedicated virtual environment:

```bash
cd /root/loomwg
python3.12 -m venv .venv
source .venv/bin/activate
```

Verify the environment is using Python 3.12:

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

Then start the app:

```bash
./run.sh
```

### CentOS Stream

For CentOS Stream 9 or 10, the installer handles the required package bootstrap automatically. If the DNF metadata is stale or broken, LoomWG will repair the CentOS repository configuration during installation setup.

### Rocky Linux

Rocky Linux 9 and 10 are supported directly. The project uses the same Python 3.12 virtualenv flow and RHEL-family package setup.

### AlmaLinux

AlmaLinux 9 and 10 are supported directly, including the same Python 3.12 virtual environment and package installation flow.

### Usage

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
