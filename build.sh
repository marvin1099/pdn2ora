#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

info() { echo -e "${CYAN}▸${NC} $*"; }
ok()   { echo -e "${GREEN}✓${NC} $*"; }
err()  { echo -e "${RED}✗${NC} $*" >&2; }

ACTION="${1:-help}"

usage() {
    cat <<EOF
pdn2ora build script

Usage:
  ./build.sh <command>

Commands:
  setup           Install all deps (runtime + dev + build)
  test            Run pytest test suite
  lint            Check code style with ruff
  linux           Build Linux binary only
  windows         Build Windows binary via Wine only
  all             Build Linux + Windows binaries
  clean           Remove build artifacts (keeps wineprefix)
  prefix          Remove Wine prefix (re-downloads Python on next windows build)
  help            Show this help
EOF
}

cmd_setup() {
    info "Installing dependencies..."
    uv sync --group dev --group build
    ok "Ready."
}

cmd_test() {
    info "Running tests..."
    uv run --group dev pytest tests/ -v
}

cmd_lint() {
    info "Linting..."
    uv run --group dev ruff check pdn2ora/ --select E,F,W
    ok "Clean."
}

cmd_linux() {
    if ! command -v uv &>/dev/null; then
        err "uv not found. Install: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi

    info "Building Linux binary..."
    uv run --group build pyinstaller \
        --onefile \
        --name pdn2ora-linux-x64 \
        --distpath dist \
        --clean \
        pdn2ora/__main__.py

    ok "Linux binary: dist/pdn2ora-linux-x64"
    ./dist/pdn2ora-linux-x64 --version
}

cmd_windows() {
    if ! command -v wine &>/dev/null; then
        err "Wine not found. Install: https://www.winehq.org/"
        exit 1
    fi

    WINEPREFIX="$PWD/wineprefix"

    if [ ! -f "$WINEPREFIX/drive_c/Python3/python.exe" ]; then
        info "Setting up Wine prefix..."
        WINEPREFIX="$WINEPREFIX" wineboot --init

        info "Fetching latest Python for Windows..."
        PYTHON_URL=$(curl -sL --compressed https://www.python.org/downloads/windows/ \
            | grep -oP 'https://www\.python\.org/ftp/python/[0-9.]+/python-[0-9.]+-amd64\.exe' \
            | sort -t/ -k5 -V | tail -1)

        if [ -z "$PYTHON_URL" ]; then
            err "Failed to find Python download URL"
            exit 1
        fi

        info "Downloading: $PYTHON_URL"
        curl -L -o /tmp/python-installer.exe "$PYTHON_URL"

        info "Installing Python in Wine..."
        WINEPREFIX="$WINEPREFIX" wine /tmp/python-installer.exe /quiet \
            InstallAllUsers=1 PrependPath=1 TargetDir=C:\\Python3
        rm /tmp/python-installer.exe

        info "Installing dependencies in Wine Python..."
        WINEPREFIX="$WINEPREFIX" wine python -m pip install --upgrade pip
        WINEPREFIX="$WINEPREFIX" wine python -m pip install pypdn pyora Pillow numpy defusedxml aenum pyinstaller
    fi

    info "Building Windows binary..."
    WINEPREFIX="$WINEPREFIX" wine python -m PyInstaller \
        --onefile \
        --name pdn2ora-win-x64 \
        --distpath dist \
        --clean \
        pdn2ora/__main__.py

    ok "Windows binary: dist/pdn2ora-win-x64.exe"
    WINEPREFIX="$WINEPREFIX" wine dist/pdn2ora-win-x64.exe --version
}

cmd_all() {
    cmd_linux
    cmd_windows
}

cmd_clean() {
    info "Cleaning build artifacts..."
    rm -rf build/ dist/ *.spec __pycache__
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    ok "Clean. (wineprefix kept)"
}

cmd_prefix() {
    if [ -d wineprefix ]; then
        info "Removing Wine prefix..."
        rm -rf wineprefix/
        ok "Wine prefix removed."
    else
        info "No wineprefix to remove."
    fi
}

case "$ACTION" in
    setup)   cmd_setup   ;;
    test)    cmd_test    ;;
    lint)    cmd_lint    ;;
    linux)   cmd_linux   ;;
    windows) cmd_windows ;;
    all)     cmd_all     ;;
    clean)   cmd_clean   ;;
    prefix)  cmd_prefix  ;;
    help|-h|--help) usage ;;
    *) err "Unknown: $ACTION"; usage; exit 1 ;;
esac
