# Use Debian Slim for better compatibility with code-server
FROM debian:12-slim

# Set up environment variables
ENV CODE_SERVER_VERSION=4.100.0
ENV PYTHON_VERSION=3.10
ENV DEBIAN_FRONTEND=noninteractive
ENV HOST=0.0.0.0

# Install system dependencies (without Node.js - will install via nvm)
RUN apt-get update && apt-get install -y \
    bash \
    curl \
    wget \
    git \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
    libffi-dev \
    libssl-dev \
    ca-certificates \
    sudo \
    net-tools \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m -s /bin/bash coder && \
    echo "coder ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Switch to non-root user
USER coder
WORKDIR /home/coder

# Install nvm and Node.js 22 LTS
ENV NVM_DIR=/home/coder/.nvm
ENV NODE_VERSION=22
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash \
    && . "$NVM_DIR/nvm.sh" \
    && nvm install $NODE_VERSION \
    && nvm use $NODE_VERSION \
    && nvm alias default $NODE_VERSION

# Add Node.js to PATH
ENV PATH="$NVM_DIR/versions/node/v$NODE_VERSION/bin:$PATH"

# Install code-server (web-based VS Code)
RUN curl -fsSL https://code-server.dev/install.sh | sh -s -- --method=standalone --version=${CODE_SERVER_VERSION}

# Install uv (fast Python package installer)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/home/coder/.local/bin:$PATH"

# Create workspace directory
RUN mkdir -p /home/coder/workspace

# Copy startup script first
COPY --chown=coder:coder start-services.sh /home/coder/start-services.sh

# Copy project files
COPY --chown=coder:coder . /home/coder/workspace

# Set working directory to workspace
WORKDIR /home/coder/workspace

# Install project dependencies in examples
RUN cd examples && uv sync

# Pre-install MCPJam Inspector
RUN . "$NVM_DIR/nvm.sh" && npm install @mcpjam/inspector@latest

# Configure code-server
RUN mkdir -p /home/coder/.config/code-server && \
    echo "bind-addr: 0.0.0.0:8180" > /home/coder/.config/code-server/config.yaml && \
    echo "auth: password" >> /home/coder/.config/code-server/config.yaml && \
    echo "password: mcpatscale" >> /home/coder/.config/code-server/config.yaml && \
    echo "cert: false" >> /home/coder/.config/code-server/config.yaml

# Install useful VS Code extensions
# Note: Some extensions may not be available in code-server's marketplace
RUN ~/.local/bin/code-server --install-extension ms-python.python || true && \
    ~/.local/bin/code-server --install-extension charliermarsh.ruff || true && \
    ~/.local/bin/code-server --install-extension tamasfe.even-better-toml || true

# Expose ports
EXPOSE 8180
EXPOSE 9000
EXPOSE 7274
EXPOSE 6274
EXPOSE 6277

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8180/healthz || exit 1

# Start both code-server and MCP Inspector
CMD ["/bin/bash", "/home/coder/start-services.sh"]
