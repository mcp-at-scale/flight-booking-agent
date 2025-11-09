# Docker Development Environment

This repository includes a Dockerfile that provides a web-based VS Code environment (code-server) with all necessary tools for development and testing.

## Features

- 🌐 **Web-based VS Code**: Access via browser at `http://localhost:8080`
- 🐍 **Python 3.11+**: Pre-configured Python environment
- ⚡ **uv package manager**: Fast Python package installation
- 🧪 **Testing ready**: pytest and all dev dependencies installed
- 🎨 **VS Code extensions**: Python, Ruff, TOML support pre-installed
- 🔒 **Non-root user**: Runs as `coder` user for security
- 🚀 **MCP**: Port 8000 exposed for MCP server 
- 📦 **Debian-based**: Stable and compatible (~1.3GB)

## Quick Start

### Build the image

```bash
docker build -t flight-booking-dev .
```

### Run the container

```bash
docker run -d \
  --name flight-booking-dev \
  -p 8080:8080 \
  -p 8000:8000 \
  -v $(pwd):/home/coder/workspace \
  flight-booking-dev
```

**Note:** Port 8000 is for the MCP server.

### Access the environment

Open your browser and navigate to:
```
http://localhost:8080
```

**Default password:** `changeme`

## Custom Configuration

### Change the password

Create a custom config before running:

```bash
docker run -d \
  --name flight-booking-dev \
  -p 8080:8080 \
  -p 8000:8000 \
  -e PASSWORD=your-secure-password \
  -v $(pwd):/home/coder/workspace \
  flight-booking-dev
```

Or modify the Dockerfile before building:
```yaml
# In Dockerfile, change this line:
echo "password: changeme" >> /home/coder/.config/code-server/config.yaml
```

### Use a different port

```bash
docker run -d \
  --name flight-booking-dev \
  -p 3000:8080 \
  -v $(pwd):/home/coder/workspace \
  flight-booking-dev
```

Access at: `http://localhost:3000`

## Development Workflow

### Run tests

Open the integrated terminal in code-server and run:

```bash
cd chapter2
uv run pytest
```

### Install new dependencies

```bash
cd chapter2
uv add package-name
```

### Run Python scripts

```bash
cd chapter2
uv run python -m chapter2.main
```

## Docker Compose (Optional)

Create a `docker-compose.yml` for easier management:

```yaml
services:
  dev:
    build: .
    ports:
      - "8080:8080"
      - "8000:8000"
    volumes:
      - .:/home/coder/workspace
    environment:
      - PASSWORD=changeme
    restart: unless-stopped
```

Start with:
```bash
docker-compose up -d
```

## Useful Commands

### View logs
```bash
docker logs flight-booking-dev
```

### Access shell
```bash
docker exec -it flight-booking-dev bash
```

### Stop container
```bash
docker stop flight-booking-dev
```

### Remove container
```bash
docker rm flight-booking-dev
```

### Rebuild after changes
```bash
docker build --no-cache -t flight-booking-dev .
```

## Troubleshooting

### Port already in use
If port 8080 is already in use, change the port mapping:
```bash
docker run -d -p 8081:8080 -v $(pwd):/home/coder/workspace flight-booking-dev
```

### Permission issues
The container runs as user `coder` (UID 1000). If you have permission issues with mounted volumes, ensure your local files are readable by this user.

### Extensions not loading
If VS Code extensions don't load, try rebuilding the image:
```bash
docker build --no-cache -t flight-booking-dev .
```

## Security Notes

⚠️ **Important**: Change the default password before exposing to a network!

For production use, consider:
- Using HTTPS with proper certificates
- Implementing stronger authentication
- Using environment variables for secrets
- Restricting network access

## Image Size

The Debian Slim-based image is approximately **~1.3GB**. While larger than Alpine-based alternatives, it provides better compatibility with code-server and development tools.

To check your image size:
```bash
docker images flight-booking-dev
```

## Ports

- **8080**: code-server (web-based VS Code)
- **8000**: MCP server
