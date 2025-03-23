import os
import uvicorn
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Get host and port from environment, or use defaults
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    
    # Set the correct model name
    os.environ["DEFAULT_MODEL"] = "gemma3"
    
    logger.info(f"Starting Agent API server on {host}:{port}")
    logger.info(f"Tool Manager URL: {os.environ.get('TOOL_MANAGER_URL', 'http://localhost:8000')}")
    logger.info(f"Ollama Base URL: {os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')}")
    logger.info(f"Default LLM Model: {os.environ.get('DEFAULT_MODEL', 'gemma3')}")
    
    # Start the server
    uvicorn.run(
        "app.api.server:app",
        host=host,
        port=port,
        reload=os.environ.get("ENVIRONMENT", "development") == "development",
    ) 