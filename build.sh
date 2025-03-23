#!/bin/bash

# Exit on error
set -e

# Function to detect GPU and OS
detect_environment() {
  OS=$(uname -s)
  GPU_TYPE="cpu"  # Default to CPU

  if [ "$OS" = "Linux" ]; then
    # Check for NVIDIA GPU
    if command -v nvidia-smi &> /dev/null; then
      GPU_TYPE="nvidia"
    # Check for AMD GPU
    elif command -v rocminfo &> /dev/null; then
      GPU_TYPE="amd"
    fi
  elif [ "$OS" = "Darwin" ]; then
    echo "macOS detected. Running in CPU mode as fallback."
  fi

  echo "Detected environment: OS=$OS, GPU=$GPU_TYPE"
  return 0
}

# Build agent image
build_agent() {
  echo "Building agent image..."
  docker build -t agent-api:latest .
}

# Run the appropriate docker-compose configuration
run_environment() {
  detect_environment

  echo "Starting services with $GPU_TYPE profile..."
  docker-compose --profile $GPU_TYPE up -d
}

# Main execution
echo "=== Apollo Tech Environment Setup ==="

case "$1" in
  build)
    build_agent
    ;;
  start)
    run_environment
    ;;
  stop)
    docker-compose down
    ;;
  restart)
    docker-compose down
    run_environment
    ;;
  *)
    echo "Usage: $0 {build|start|stop|restart}"
    echo "  build   - Build only the agent image"
    echo "  start   - Start the environment with appropriate GPU support"
    echo "  stop    - Stop all services"
    echo "  restart - Restart all services"
    exit 1
    ;;
esac

echo "Done!" 