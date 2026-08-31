# LoomWG Quick Start Guide

This guide gets you up and running with LoomWG on a Rocky Linux VPS.

## Prerequisites

- Rocky Linux 9 or 10 (x86_64)
- sudo/root access
- Internet connection
- At least 100 MB free disk space

## Installation

### Step 1: Clone or Download

```bash
cd /opt
sudo git clone <repository-url> loomwg
cd loomwg
```

Or download as zip and extract.

### Step 2: Install and Launch with the Project Script

From the project root:

```bash
sudo bash ./run.sh
```

The script will:
- verify root privileges
- install the required Rocky Linux packages
- create the virtual environment
- install the package in editable mode
- enable basic Linux routing/firewall prerequisites
- start LoomWG

You can also run it directly after making it executable:

```bash
chmod +x ./run.sh
sudo ./run.sh
```

## First Run Walkthrough

When you first run LoomWG:

1. **System Check**
   - LoomWG verifies your system meets requirements
   - If WireGuard is not installed, you'll be prompted to install it

2. **Server Configuration**
   - Choose to configure the server
   - LoomWG generates keys automatically
   - Default settings are applied
   - Configuration is written to `/etc/wireguard/wg0.conf`

3. **Firewall Setup**
   - Port 51820/UDP is opened
   - Masquerading is enabled for NAT
   - firewalld is started and enabled

4. **Network Setup**
   - IP forwarding is enabled for IPv4 and IPv6
   - Server is ready for peer connections

5. **Create First Peer**
   - Go to Peers menu
   - Create a new peer (e.g., "laptop")
   - Export the configuration
   - Install on your client device

## Common Tasks

### Check Server Status

```
Main Menu → Server → Server status
```

Shows:
- WireGuard interface status
- Listening port
- Connected peers
- Traffic statistics

### Create a New Peer (Client)

```
Main Menu → Peers → Create peer
```

1. Enter a name (e.g., "phone", "laptop")
2. LoomWG allocates IP automatically
3. Keys are generated
4. Export configuration

### Export Peer Configuration

```
Main Menu → Peers → Export peer
```

This gives you a `.conf` file to use on the client device and saves it in the app-local client config directory:

```
<project-root>/data/clients/
```

Each exported peer includes:
- `peer-name.conf` for use with the WireGuard app
- `peer-name.png` QR code for phone-based setup when the QR library is available

### Add to Client Device

**Linux:**
```bash
sudo wg-quick up peer-name.conf
```

**macOS/Windows:**
- Use WireGuard official app
- Import the .conf file

**Android/iOS:**
- Scan QR code (future feature)
- Or import configuration file

### Monitor Server

```
Main Menu → Diagnostics → Full health check
```

Shows:
- System health
- Network connectivity
- WireGuard status
- Firewall rules
- Overall health status

### View Logs

```
Main Menu → Logs → View recent logs
```

Shows recent events:
- Installation
- Peer creation/removal
- Configuration changes
- Errors and warnings

### Backup Configuration

```
Main Menu → Backup & Restore → Create backup
```

Creates timestamped backup at:
```
/var/lib/loomwg/backups/wireguard_backup_YYYYMMDD_HHMMSS.tar.gz
```

### Restore from Backup

```
Main Menu → Backup & Restore → Restore backup
```

Automatically creates pre-restore backup.

## File Locations

Important directories and files:

```
/etc/wireguard/          # WireGuard configuration
/etc/wireguard/wg0.conf  # Server config

<project-root>/data/clients/  # exported user/client .conf files
<project-root>/data/qr_codes/<peer-name>.png  # generated QR codes
<project-root>/data/peers.json  # peer database
<project-root>/logs/     # log files
<project-root>/backups/  # backup files
```

## Troubleshooting

### "WireGuard is not installed"

```
Main Menu → Server → Configure server
# Choose to install when prompted
```

### Cannot connect as client

1. Check server is running:
   ```bash
   sudo wg show
   ```

2. Check firewall port:
   ```bash
   Main Menu → Diagnostics → Firewall diagnostics
   ```

3. Check client config has correct server endpoint:
   ```bash
   grep Endpoint peer.conf
   ```

4. View logs for details:
   ```bash
   Main Menu → Logs → View recent logs
   ```

### Peer not online

1. Check peer configuration is correct
2. Verify peer endpoint has internet access
3. Check firewall rules
4. Verify IP forwarding is enabled:
   ```
   Main Menu → Diagnostics → Network diagnostics
   ```

### Lost Configuration

1. Restore from backup:
   ```
   Main Menu → Backup & Restore → Restore backup
   ```

2. If no backup available, reconfigure:
   ```
   Main Menu → Server → Configure server
   ```

## Security Notes

- **Root Access**: LoomWG requires root. Always run with appropriate trust.
- **Private Keys**: Never share .conf files containing private keys
- **Backups**: Store backups securely
- **Firewall**: Only allow port 51820/UDP from trusted networks if needed
- **DNS**: Uses Cloudflare (1.1.1.1) by default - change in server config if needed

## Next Steps

1. **Multiple Peers**: Create more peers for each client device
2. **Monitoring**: Regularly check server status and logs
3. **Backups**: Create backups periodically
4. **Updates**: Check for LoomWG updates
5. **Diagnostics**: Run health checks regularly

## Advanced Configuration

For advanced changes:

1. Server config: Edit `/etc/wireguard/wg0.conf` directly
2. Peer database: JSON at `<project-root>/data/peers.json`
3. Firewall: Use firewall-cmd directly
4. Logs: Stored in `/var/lib/loomwg/logs/`

**Warning**: Manual edits bypass validation. Use LoomWG menus when possible.

## Getting Help

- Check logs: `Main Menu → Logs`
- Run diagnostics: `Main Menu → Diagnostics`
- Review README.md for detailed documentation
- Check DEVELOPMENT.md for developer info

## Uninstall

```bash
# Remove LoomWG
sudo rm -rf /opt/loomwg

# Keep WireGuard config (recommended for backup)
# Or remove everything:
sudo rm -rf /etc/wireguard
sudo rm -rf /var/lib/loomwg
```

---

**Happy VPNing! 🚀**

For detailed documentation, see [README.md](README.md)
