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

cd /home/coder/workspace/chapter2

# Check if dependencies are installed
if [ ! -d ".venv" ]; then
    echo "  Installing Python dependencies..."
    uv sync
fi

# Start MCPJam Inspector in the background (default ports 6274/6277)
echo "→ Starting MCPJam Inspector on port 6274..."
npx @mcpjam/inspector@latest > /tmp/mcpjam.log 2>&1 &
MCPJAM_PID=$!
echo "  MCPJam Inspector started (PID: $MCPJAM_PID)"

# MCPJam binds to 127.0.0.1 only — forward 0.0.0.0:6274 -> 127.0.0.1:6274
sleep 5
socat TCP-LISTEN:16274,fork,reuseaddr,bind=0.0.0.0 TCP:127.0.0.1:6274 > /tmp/socat-mcpjam.log 2>&1 &
echo "  socat forward for MCPJam started"

# Start MCP Inspector in the foreground
echo "→ Starting MCP Inspector on port 7274..."

echo ""
echo "=========================================="
echo "  Services ready!"
echo "=========================================="
echo ""
echo "  📝 code-server:      http://localhost:8080"
echo "     Password: mcpatscale"
echo ""
echo "  🔍 MCP Inspector:    http://localhost:7274"
echo "  🔍 MCPJam Inspector: http://localhost:6274"
echo ""
echo "=========================================="
echo ""

# Run MCP Inspector in foreground (keeps container alive)
# Disable auth for local development environment
export DANGEROUSLY_OMIT_AUTH=true
export CLIENT_PORT=7274
export SERVER_PORT=7277
exec npx @modelcontextprotocol/inspector uv run flight-booking-mcp
