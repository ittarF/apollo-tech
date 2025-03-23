# Apollo Tech Setup Guide

This guide provides instructions for setting up and running the Apollo Tech environment, which includes an agent API, tool manager, and Ollama LLM service with GPU acceleration.

## Requirements

- Docker and Docker Compose
- For GPU acceleration:
  - NVIDIA GPU: NVIDIA drivers and [nvidia-docker](https://github.com/NVIDIA/nvidia-docker)
  - AMD GPU: ROCm drivers
- For macOS: Docker Desktop for Mac (will run in CPU mode)

## Directory Structure

The project has the following structure:
```
apollo-tech/
├── Dockerfile           # Agent API Dockerfile
├── docker-compose.yml   # Docker Compose configuration
├── requirements.txt     # Python dependencies
├── main.py              # Agent API entry point
├── build.sh             # Build and run script
├── SETUP.md             # This setup guide
```

Note: The tool-manager service must be built separately and made available as a Docker image.

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/apollo-tech.git
cd apollo-tech
```

### 2. Make the Build Script Executable

```bash
chmod +x build.sh
```

### 3. Prepare the Tool Manager Image

You need to have the tool-manager-api:latest image available before starting the services. You can:

1. Pull it from a registry:
   ```bash
   docker pull your-registry/tool-manager-api:latest
   docker tag your-registry/tool-manager-api:latest tool-manager-api:latest
   ```

2. Build it in a separate directory:
   ```bash
   cd path/to/tool-manager
   docker build -t tool-manager-api:latest .
   ```

3. Alternatively, edit docker-compose.yml to specify a different image name for the tool manager.

### 4. Build the Agent Image

```bash
./build.sh build
```

This will build only the agent API image.

### 5. Start the Environment

This command will automatically detect your environment (NVIDIA GPU, AMD GPU, or CPU-only mode on macOS) and start the appropriate configuration:

```bash
./build.sh start
```

### 6. Access the Services

- Agent API: http://localhost:8080
- Tool Manager: http://localhost:8000
- Ollama: http://localhost:11434

## Managing the Environment

- **Stop all services**:
  ```bash
  ./build.sh stop
  ```

- **Restart services**:
  ```bash
  ./build.sh restart
  ```

## Environment Configuration

The system automatically detects your environment:

- On Linux with NVIDIA GPU: Uses NVIDIA GPU acceleration
- On Linux with AMD GPU: Uses AMD GPU acceleration
- On macOS: Falls back to CPU mode

## Using a Different Tool Manager Image

If you want to use a specific tool manager image instead of the default tool-manager-api:latest, edit the docker-compose.yml file:

```yaml
tool-manager:
  image: your-registry/your-tool-manager:tag
  # rest of configuration remains the same
```

## Troubleshooting

### GPU Not Detected

- For NVIDIA: Ensure `nvidia-smi` command works in your terminal
- For AMD: Ensure `rocminfo` command works in your terminal

### Docker Issues

- Ensure Docker and Docker Compose are properly installed
- On Linux, make sure your user is in the `docker` group:
  ```bash
  sudo usermod -aG docker $USER
  ```
  (Requires logout/login to take effect)

### Tool Manager Image Not Found

If you get an error about the tool-manager image not being found:
1. Pull it from your registry: `docker pull your-registry/tool-manager-api:latest`
2. Tag it as needed: `docker tag your-registry/tool-manager-api:latest tool-manager-api:latest`
3. Or specify the correct image name directly in docker-compose.yml

## Customization

You can modify the `docker-compose.yml` file to adjust port mappings, environment variables, and resource allocations as needed.

## License

[Your License Information] 