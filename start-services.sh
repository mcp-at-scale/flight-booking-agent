#!/bin/bash
# Startup script for Docker container
# Launches both code-server and MCP Inspector

set -e

# Load nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

echo "=========================================="
echo "  Flight Booking Development Environment"
echo "=========================================="
echo ""
echo "Node.js: $(node --version)"
echo "npm: $(npm --version)"
echo ""
echo "Starting services..."
echo ""

# Start code-server in the background
echo "→ Starting code-server on port 8080..."
/home/coder/.local/bin/code-server /home/coder/workspace > /tmp/code-server.log 2>&1 &
CODE_SERVER_PID=$!
echo "  code-server started (PID: $CODE_SERVER_PID)"

# Wait a moment for code-server to initialize
sleep 2

# Start MCP Inspector in the foreground (so container doesn't exit)
echo "→ Starting MCP Inspector on port 8001..."
cd /home/coder/workspace/chapter2

# Check if dependencies are installed
if [ ! -d ".venv" ]; then
    echo "  Installing Python dependencies..."
    uv sync
fi

echo ""
echo "=========================================="
echo "  Services ready!"
echo "=========================================="
echo ""
echo "  📝 code-server:    http://localhost:8080"
echo "     Password: changeme"
echo ""
echo "  🔍 MCP Inspector:  http://localhost:8001"
echo ""
echo "=========================================="
echo ""

# Run MCP Inspector in foreground (keeps container alive)
# Disable auth for local development environment
export DANGEROUSLY_OMIT_AUTH=true
exec npx @modelcontextprotocol/inspector uv run flight-booking-mcp
