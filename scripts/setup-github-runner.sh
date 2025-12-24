#!/bin/bash
# =============================================================================
# GitHub Actions Self-Hosted Runner Setup for M4 Max Mac Studio
# =============================================================================
# This script sets up a self-hosted GitHub Actions runner on your Mac Studio
# with M4 Max chip (ARM64/Apple Silicon).
#
# Usage: ./scripts/setup-github-runner.sh
#
# Prerequisites:
#   - Docker Desktop for Mac (running)
#   - Homebrew (for installing dependencies)
#   - GitHub repo admin access
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  GitHub Actions Self-Hosted Runner Setup for M4 Max           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# =============================================================================
# Step 1: Check prerequisites
# =============================================================================
echo -e "${YELLOW}Step 1: Checking prerequisites...${NC}"

# Check if running on ARM64 Mac
if [[ $(uname -m) != "arm64" ]]; then
    echo -e "${RED}Error: This script is designed for Apple Silicon Macs (arm64)${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Apple Silicon Mac detected${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker not found. Please install Docker Desktop for Mac.${NC}"
    exit 1
fi
if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Docker is installed and running${NC}"

# Check for required tools
for tool in curl jq; do
    if ! command -v $tool &> /dev/null; then
        echo -e "${YELLOW}  Installing $tool via Homebrew...${NC}"
        brew install $tool
    fi
done
echo -e "${GREEN}  ✓ Required tools available${NC}"

# =============================================================================
# Step 2: Create runner directory
# =============================================================================
RUNNER_DIR="$HOME/actions-runner"
echo -e "${YELLOW}Step 2: Setting up runner directory at $RUNNER_DIR...${NC}"

if [[ -d "$RUNNER_DIR" ]]; then
    echo -e "${YELLOW}  Runner directory exists. Checking if runner is already configured...${NC}"
    if [[ -f "$RUNNER_DIR/.runner" ]]; then
        echo -e "${GREEN}  ✓ Runner already configured!${NC}"
        echo -e "${BLUE}  To start: cd $RUNNER_DIR && ./run.sh${NC}"
        echo -e "${BLUE}  To reinstall: rm -rf $RUNNER_DIR && $0${NC}"
        exit 0
    fi
else
    mkdir -p "$RUNNER_DIR"
fi
cd "$RUNNER_DIR"
echo -e "${GREEN}  ✓ Runner directory ready${NC}"

# =============================================================================
# Step 3: Download latest runner
# =============================================================================
echo -e "${YELLOW}Step 3: Downloading latest GitHub Actions runner for macOS ARM64...${NC}"

# Get latest runner version
LATEST_VERSION=$(curl -s https://api.github.com/repos/actions/runner/releases/latest | jq -r '.tag_name' | sed 's/v//')
RUNNER_FILE="actions-runner-osx-arm64-${LATEST_VERSION}.tar.gz"
DOWNLOAD_URL="https://github.com/actions/runner/releases/download/v${LATEST_VERSION}/${RUNNER_FILE}"

echo -e "  Downloading version ${LATEST_VERSION}..."
curl -L -o "$RUNNER_FILE" "$DOWNLOAD_URL"
echo -e "${GREEN}  ✓ Downloaded $RUNNER_FILE${NC}"

# Extract
echo -e "  Extracting..."
tar xzf "$RUNNER_FILE"
rm "$RUNNER_FILE"
echo -e "${GREEN}  ✓ Extracted runner files${NC}"

# =============================================================================
# Step 4: Get registration token
# =============================================================================
echo -e "${YELLOW}Step 4: Getting registration token...${NC}"
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  ACTION REQUIRED: Get your registration token from GitHub      ║${NC}"
echo -e "${BLUE}╠════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║                                                                ║${NC}"
echo -e "${BLUE}║  1. Go to: https://github.com/ArieGoldkin/SkillForge/settings  ║${NC}"
echo -e "${BLUE}║           /actions/runners/new                                 ║${NC}"
echo -e "${BLUE}║                                                                ║${NC}"
echo -e "${BLUE}║  2. Under 'Configure', copy the token after --token            ║${NC}"
echo -e "${BLUE}║                                                                ║${NC}"
echo -e "${BLUE}║  3. Paste it below when prompted                               ║${NC}"
echo -e "${BLUE}║                                                                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

read -p "Enter your GitHub runner registration token: " RUNNER_TOKEN

if [[ -z "$RUNNER_TOKEN" ]]; then
    echo -e "${RED}Error: Token is required${NC}"
    exit 1
fi

# =============================================================================
# Step 5: Configure the runner
# =============================================================================
echo -e "${YELLOW}Step 5: Configuring runner...${NC}"

./config.sh \
    --url https://github.com/ArieGoldkin/SkillForge \
    --token "$RUNNER_TOKEN" \
    --name "m4-max-studio" \
    --labels "self-hosted,macOS,ARM64,m4-max" \
    --work "_work" \
    --runasservice

echo -e "${GREEN}  ✓ Runner configured successfully!${NC}"

# =============================================================================
# Step 6: Install as LaunchAgent (auto-start on boot)
# =============================================================================
echo -e "${YELLOW}Step 6: Setting up auto-start on boot...${NC}"

PLIST_FILE="$HOME/Library/LaunchAgents/com.github.actions.runner.plist"

cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.github.actions.runner</string>
    <key>ProgramArguments</key>
    <array>
        <string>$RUNNER_DIR/run.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$RUNNER_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$RUNNER_DIR/runner.log</string>
    <key>StandardErrorPath</key>
    <string>$RUNNER_DIR/runner.error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
EOF

echo -e "${GREEN}  ✓ LaunchAgent created at $PLIST_FILE${NC}"

# =============================================================================
# Step 7: Start the runner
# =============================================================================
echo -e "${YELLOW}Step 7: Starting runner...${NC}"

launchctl load "$PLIST_FILE"
echo -e "${GREEN}  ✓ Runner started and will auto-start on boot${NC}"

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  🎉 SUCCESS! Self-hosted runner is now active!                 ║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}║  Runner Name:    m4-max-studio                                 ║${NC}"
echo -e "${GREEN}║  Labels:         self-hosted, macOS, ARM64, m4-max             ║${NC}"
echo -e "${GREEN}║  Location:       $RUNNER_DIR                         ║${NC}"
echo -e "${GREEN}║  Auto-start:     Enabled (LaunchAgent)                         ║${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Useful commands:                                              ║${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}║  View status:    launchctl list | grep actions                 ║${NC}"
echo -e "${GREEN}║  View logs:      tail -f $RUNNER_DIR/runner.log      ║${NC}"
echo -e "${GREEN}║  Stop runner:    launchctl unload $PLIST_FILE        ║${NC}"
echo -e "${GREEN}║  Start runner:   launchctl load $PLIST_FILE          ║${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Next step: Make your repo private in GitHub settings!${NC}"
echo -e "${BLUE}https://github.com/ArieGoldkin/SkillForge/settings${NC}"
