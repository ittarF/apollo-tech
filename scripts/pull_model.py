#!/usr/bin/env python3
"""
Ollama Model Puller

This script pulls the specified model from Ollama's model repository.
"""

import os
import sys
import argparse
import httpx
import asyncio
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default values
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma3"

async def pull_model(ollama_url: str, model_name: str) -> None:
    """
    Pull a model from Ollama.
    
    Args:
        ollama_url: URL of the Ollama API
        model_name: Name of the model to pull
    """
    url = f"{ollama_url}/api/pull"
    
    logger.info(f"Pulling model '{model_name}' from Ollama...")
    
    payload = {
        "name": model_name,
        "stream": False
    }
    
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            
            logger.info(f"Successfully pulled model '{model_name}'")
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error pulling model: {e.response.status_code} - {e.response.text}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error pulling model: {str(e)}")
        sys.exit(1)

async def check_model_exists(ollama_url: str, model_name: str) -> bool:
    """
    Check if a model already exists in Ollama.
    
    Args:
        ollama_url: URL of the Ollama API
        model_name: Name of the model to check
        
    Returns:
        True if the model exists, False otherwise
    """
    url = f"{ollama_url}/api/tags"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            models = response.json().get("models", [])
            return any(model.get("name") == model_name for model in models)
            
    except Exception as e:
        logger.error(f"Error checking if model exists: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Pull a model from Ollama")
    parser.add_argument(
        "--url", 
        dest="ollama_url",
        default=os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL),
        help=f"Ollama API URL (default: {DEFAULT_OLLAMA_URL})"
    )
    parser.add_argument(
        "--model", 
        dest="model_name",
        default=os.environ.get("DEFAULT_MODEL", DEFAULT_MODEL),
        help=f"Name of the model to pull (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--force", 
        action="store_true",
        help="Force pull even if the model already exists"
    )
    
    args = parser.parse_args()
    
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        logger.info("Model pull interrupted")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

async def async_main(args):
    # Check if model already exists
    if not args.force and await check_model_exists(args.ollama_url, args.model_name):
        logger.info(f"Model '{args.model_name}' already exists. Use --force to pull again.")
        return
        
    # Pull the model
    await pull_model(args.ollama_url, args.model_name)

if __name__ == "__main__":
    main() 