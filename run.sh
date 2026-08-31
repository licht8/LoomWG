#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log() {
  printf '%b\n' "$1"
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    log "${YELLOW}LoomWG setup requires root privileges. Re-running with sudo...${NC}"
    exec sudo bash "$0" "$@"
  fi
}

detect_os() {
  if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    OS_ID="${ID:-unknown}"
    OS_VERSION="${VERSION_ID:-0}"
    return
  fi

  log "${RED}Unsupported system: /etc/os-release not found.${NC}"
  exit 1
}

ensure_base_tools() {
  case "$OS_ID" in
    rocky|almalinux|centos|rhel|fedora)
      if command -v dnf >/dev/null 2>&1; then
        dnf install -y python3 python3-pip python3-venv firewalld iptables iptables-services qrencode wireguard-tools || true
      else
        yum install -y python3 python3-pip python3-venv firewalld iptables iptables-services qrencode wireguard-tools || true
      fi
      ;;
    ubuntu|debian|raspbian)
      export DEBIAN_FRONTEND=noninteractive
      apt-get update
      apt-get install -y python3 python3-pip python3-venv firewalld iptables qrencode wireguard
      ;;
    *)
      log "${RED}Unsupported OS: ${OS_ID}. LoomWG is designed for Rocky Linux and similar Linux distributions.${NC}"
      exit 1
      ;;
  esac

  if ! command -v python3 >/dev/null 2>&1; then
    log "${RED}Python 3 is required but was not found after installation attempts.${NC}"
    exit 1
  fi
}

ensure_firewall() {
  if command -v systemctl >/dev/null 2>&1; then
    systemctl enable --now firewalld 2>/dev/null || true
  fi
}

ensure_ip_forwarding() {
  cat > /etc/sysctl.d/99-loomwg-forwarding.conf <<'EOF'
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1
EOF

  if command -v sysctl >/dev/null 2>&1; then
    sysctl --system >/dev/null 2>&1 || true
  fi
}

prepare_python_env() {
  PYTHON_BIN="${PYTHON_BIN:-python3}"
  VENV_DIR="$SCRIPT_DIR/.venv"

  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    log "${RED}Python 3 is required but was not found in PATH.${NC}"
    exit 1
  fi

  if [[ ! -d "$VENV_DIR" ]]; then
    log "${GREEN}Creating virtual environment in $VENV_DIR${NC}"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi

  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"

  log "${GREEN}Upgrading pip${NC}"
  python -m pip install --upgrade pip

  log "${GREEN}Installing LoomWG in editable mode${NC}"
  python -m pip install -e .
}

start_app() {
  log "${GREEN}Setup complete. Starting LoomWG...${NC}"
  exec "$SCRIPT_DIR/.venv/bin/python" -m loom
}

main() {
  require_root "$@"
  detect_os
  ensure_base_tools
  ensure_firewall
  ensure_ip_forwarding
  prepare_python_env
  start_app
}

main "$@"
