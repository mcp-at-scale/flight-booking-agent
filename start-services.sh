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
echo "→ Starting code-server on port 8180..."
/home/coder/.local/bin/code-server /home/coder/workspace > /tmp/code-server.log 2>&1 &
CODE_SERVER_PID=$!
echo "  code-server started (PID: $CODE_SERVER_PID)"

# Wait a moment for code-server to initialize
sleep 2

cd /home/coder/workspace/examples

# Check if dependencies are installed
if [ ! -d ".venv" ]; then
    echo "  Installing Python dependencies..."
    uv sync
fi

# Start MCPJam Inspector in the background (patched to bind 0.0.0.0:6274)
echo "→ Starting MCPJam Inspector on port 7274..."
DOCKER_CONTAINER=true SERVER_PORT=7274 node /home/coder/workspace/node_modules/@mcpjam/inspector/bin/start.js > /tmp/mcpjam.log 2>&1 &
MCPJAM_PID=$!
echo "  MCPJam Inspector started (PID: $MCPJAM_PID)"

# Start MCP Inspector in the foreground
echo "→ Starting MCP Inspector on port 6274..."

echo ""
echo "=========================================="
echo "  Services ready!"
echo "=========================================="
echo ""
echo "  📝 code-server:      http://localhost:8180"
echo "     Password: mcpatscale"
echo ""
echo "  🔍 MCPJam Inspector: http://localhost:7274"
echo "  🔍 MCP Inspector:    http://localhost:6274"
echo ""
echo "=========================================="
echo ""

# Run MCP Inspector in foreground (keeps container alive)
# Disable auth for local development environment
export DANGEROUSLY_OMIT_AUTH=true
export CLIENT_PORT=6274
export SERVER_PORT=6277
exec npx @modelcontextprotocol/inspector uv run flight-booking-mcp
