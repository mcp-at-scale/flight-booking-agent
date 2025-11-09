# Use Debian Slim for better compatibility with code-server
FROM debian:12-slim

# Set up environment variables
ENV CODE_SERVER_VERSION=4.100.0
ENV PYTHON_VERSION=3.10
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
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
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m -s /bin/bash coder && \
    echo "coder ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Switch to non-root user
USER coder
WORKDIR /home/coder

# Install code-server (web-based VS Code)
RUN curl -fsSL https://code-server.dev/install.sh | sh -s -- --method=standalone --version=${CODE_SERVER_VERSION}

# Install uv (fast Python package installer)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/home/coder/.local/bin:$PATH"

# Create workspace directory
RUN mkdir -p /home/coder/workspace

# Copy project files
COPY --chown=coder:coder . /home/coder/workspace

# Set working directory to workspace
WORKDIR /home/coder/workspace

# Install project dependencies in chapter2
RUN cd chapter2 && uv sync

# Configure code-server
RUN mkdir -p /home/coder/.config/code-server && \
    echo "bind-addr: 0.0.0.0:8080" > /home/coder/.config/code-server/config.yaml && \
    echo "auth: password" >> /home/coder/.config/code-server/config.yaml && \
    echo "password: changeme" >> /home/coder/.config/code-server/config.yaml && \
    echo "cert: false" >> /home/coder/.config/code-server/config.yaml

# Install useful VS Code extensions
# Note: Some extensions may not be available in code-server's marketplace
RUN ~/.local/bin/code-server --install-extension ms-python.python || true && \
    ~/.local/bin/code-server --install-extension charliermarsh.ruff || true && \
    ~/.local/bin/code-server --install-extension tamasfe.even-better-toml || true

# Expose code-server port
EXPOSE 8080

# Expose MCP server port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/healthz || exit 1

# Start code-server
CMD ["/home/coder/.local/bin/code-server", "/home/coder/workspace"]
