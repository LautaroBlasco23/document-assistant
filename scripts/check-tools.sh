#!/usr/bin/env bash
set -uo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Tool definitions
REQUIRED_TOOLS=("docker" "npm")
OPTIONAL_TOOLS=("ollama")
INSTALLABLE_TOOLS=("uv") # Tools we can auto-install

check_command() {
    command -v "$1" >/dev/null 2>&1
}

get_version() {
    local cmd="$1"
    local version_flag="${2:---version}"
    local version
    version=$($cmd $version_flag 2>&1 | head -1) || version="unknown"
    echo "$version"
}

print_status() {
    local name="$1"
    local status="$2"
    local version="${3:-}"
    
    if [ "$status" = "installed" ]; then
        printf "  ${GREEN}✓${NC} %-12s installed" "$name"
        [ -n "$version" ] && printf " (%s)" "$version"
        echo ""
    elif [ "$status" = "missing" ]; then
        printf "  ${RED}✗${NC} %-12s ${RED}missing${NC}\n" "$name"
    elif [ "$status" = "optional" ]; then
        printf "  ${YELLOW}○${NC} %-12s optional" "$name"
        [ -n "$version" ] && printf " (%s)" "$version"
        echo ""
    fi
}

install_uv() {
    echo ""
    echo -e "${BLUE}Installing uv (Python package manager)...${NC}"
    
    if check_command curl; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        
        # Add to PATH for current session if installed to default location
        if [ -f "$HOME/.local/bin/uv" ]; then
            export PATH="$HOME/.local/bin:$PATH"
        fi
        
        if check_command uv; then
            echo -e "${GREEN}✓ uv installed successfully${NC}"
            return 0
        else
            echo -e "${RED}✗ Failed to install uv${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ curl is required to install uv${NC}"
        return 1
    fi
}

show_install_help() {
    local tool="$1"
    
    case "$tool" in
        docker)
            echo ""
            echo "Docker is required but not installed. Install options:"
            echo "  • Ubuntu/Debian:  sudo apt-get install docker.io docker-compose-plugin"
            echo "  • macOS:          https://docs.docker.com/desktop/install/mac-install/"
            echo "  • Windows:        https://docs.docker.com/desktop/install/windows-install/"
            echo "  • Other:          https://docs.docker.com/get-docker/"
            ;;
        npm)
            echo ""
            echo "Node.js/npm is required but not installed. Install options:"
            echo "  • Via nvm:        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.0/install.sh | bash"
            echo "                    Then: nvm install node"
            echo "  • Ubuntu/Debian:  sudo apt-get install nodejs npm"
            echo "  • macOS:          brew install node"
            echo "  • Other:          https://nodejs.org/en/download/"
            ;;
        uv)
            echo ""
            echo "uv is required but not installed. Install options:"
            echo "  • Via install script: curl -LsSf https://astral.sh/uv/install.sh | sh"
            echo "  • Via pip:            pip install uv"
            echo "  • Other:              https://docs.astral.sh/uv/getting-started/installation/"
            ;;
        ollama)
            echo ""
            echo "Ollama is optional (only needed for local LLM). Install options:"
            echo "  • macOS/Linux:  curl -fsSL https://ollama.com/install.sh | sh"
            echo "  • Other:        https://ollama.com/download"
            ;;
    esac
}

check_all_tools() {
    local missing_required=0
    local missing_optional=0
    local missing_installable=0
    
    echo ""
    echo -e "${BLUE}Checking required tools:${NC}"
    
    # Check Docker
    if check_command docker; then
        print_status "docker" "installed" "$(docker --version 2>/dev/null | cut -d' ' -f3 | tr -d ',')"
    else
        print_status "docker" "missing"
        missing_required=1
    fi
    
    # Check npm/node
    if check_command npm; then
        print_status "npm" "installed" "$(npm --version 2>/dev/null)"
    else
        print_status "npm" "missing"
        missing_required=1
    fi
    
    # Check uv
    if check_command uv; then
        print_status "uv" "installed" "$(uv --version 2>/dev/null | cut -d' ' -f2)"
    else
        print_status "uv" "missing"
        missing_installable=1
    fi
    
    echo ""
    echo -e "${BLUE}Checking optional tools:${NC}"
    
    # Check ollama
    if check_command ollama; then
        print_status "ollama" "optional" "$(ollama --version 2>/dev/null | head -1 | cut -d' ' -f3)"
    else
        print_status "ollama" "optional"
        missing_optional=1
    fi
    
    # Return summary
    if [ $missing_required -eq 1 ] || [ $missing_installable -eq 1 ]; then
        return 1
    fi
    return 0
}

# ── Main ───────────────────────────────────────────────────────────────────────

cd "$PROJECT_ROOT"

MODE="${1:-check}"  # check, install, or help

if [ "$MODE" = "check" ]; then
    if check_all_tools; then
        echo ""
        echo -e "${GREEN}All required tools are installed!${NC}"
        echo "Run 'make start' to begin development."
        exit 0
    else
        echo ""
        echo -e "${YELLOW}Some tools are missing.${NC}"
        echo "Run 'make tools' to install missing tools."
        exit 1
    fi
    
elif [ "$MODE" = "install" ]; then
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Document Assistant - Tool Setup      ${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    check_all_tools
    
    # Check what we can auto-install
    if ! check_command uv; then
        if [ -t 0 ]; then  # Only interactive if stdin is a terminal
            echo ""
            printf "Install uv (Python package manager)? [Y/n]: "
            read -r response
            if [[ ! "$response" =~ ^[Nn]$ ]]; then
                install_uv || true
            fi
        else
            # Non-interactive: auto-install
            install_uv || true
        fi
    fi
    
    # Show help for tools we can't auto-install
    if ! check_command docker; then
        show_install_help "docker"
    fi
    
    if ! check_command npm; then
        show_install_help "npm"
    fi
    
    if ! check_command ollama; then
        show_install_help "ollama"
    fi
    
    # Final status check
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Setup Status                          ${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    if check_all_tools 2>/dev/null; then
        echo ""
        echo -e "${GREEN}✓ All required tools are now installed!${NC}"
        echo ""
        echo "You can now run:"
        echo "  make start    - Start development server"
        exit 0
    else
        echo ""
        echo -e "${YELLOW}⚠ Some tools still need manual installation.${NC}"
        echo "Please install the missing tools listed above, then run 'make start'."
        exit 1
    fi
    
elif [ "$MODE" = "help" ]; then
    echo "Usage: make tools [install|check|help]"
    echo ""
    echo "Commands:"
    echo "  (default)  Check if all required tools are installed"
    echo "  install    Check and install missing tools where possible"
    echo "  help       Show this help message"
    echo ""
    echo "Required tools:"
    echo "  • docker   - Container runtime (manual install required)"
    echo "  • npm      - Node.js package manager (manual install required)"
    echo "  • uv       - Python package manager (can auto-install)"
    echo ""
    echo "Optional tools:"
    echo "  • ollama   - Local LLM runner (only needed for ollama provider)"
    
else
    echo "Unknown mode: $MODE"
    echo "Usage: make tools [install|check|help]"
    exit 1
fi
