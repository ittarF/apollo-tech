#!/usr/bin/env python3
"""
Tool Registration Script

This script registers the native tools in the app/tools directory
with the Tool Manager API.
"""

import os
import sys
import json
import argparse
import httpx
import asyncio
import logging
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default Tool Manager URL
DEFAULT_TOOL_MANAGER_URL = "http://localhost:8000"

# Tool definitions
TOOLS = [
    {
        "name": "format_text",
        "description": "Format text according to the specified format type",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to format"
                },
                "format_type": {
                    "type": "string",
                    "description": "Type of formatting to apply (upper, lower, title, capitalize)",
                    "enum": ["upper", "lower", "title", "capitalize"]
                }
            },
            "required": ["text", "format_type"]
        },
        "is_native": True,
        "function_path": "app.tools.text_tools.format_text",
        "endpoint_url": None
    },
    {
        "name": "count_words",
        "description": "Count the number of words in a text and provide statistics",
        "parameters_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to analyze"
                }
            },
            "required": ["text"]
        },
        "is_native": True,
        "function_path": "app.tools.text_tools.count_words",
        "endpoint_url": None
    }
]

async def register_tools(tool_manager_url: str, tools: List[Dict[str, Any]]) -> None:
    """
    Register tools with the Tool Manager API.
    
    Args:
        tool_manager_url: URL of the Tool Manager API
        tools: List of tool definitions to register
    """
    url = f"{tool_manager_url}/tools"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for tool in tools:
            logger.info(f"Registering tool: {tool['name']}")
            
            try:
                # Check if tool already exists by name
                response = await client.get(f"{url}?name={tool['name']}")
                
                if response.status_code == 200 and response.json():
                    # Tool exists, update it
                    existing_tool = response.json()[0]
                    tool_id = existing_tool["id"]
                    logger.info(f"Tool {tool['name']} already exists (ID: {tool_id}). Updating.")
                    
                    response = await client.put(f"{url}/{tool_id}", json=tool)
                    response.raise_for_status()
                    logger.info(f"Updated tool {tool['name']} (ID: {tool_id})")
                else:
                    # Tool doesn't exist, create it
                    response = await client.post(url, json=tool)
                    response.raise_for_status()
                    created_tool = response.json()
                    logger.info(f"Created tool {tool['name']} (ID: {created_tool.get('id')})")
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error registering tool {tool['name']}: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"Error registering tool {tool['name']}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Register tools with the Tool Manager API")
    parser.add_argument(
        "--url", 
        dest="tool_manager_url",
        default=os.environ.get("TOOL_MANAGER_URL", DEFAULT_TOOL_MANAGER_URL),
        help=f"Tool Manager API URL (default: {DEFAULT_TOOL_MANAGER_URL})"
    )
    
    args = parser.parse_args()
    
    try:
        logger.info(f"Registering tools with Tool Manager API at {args.tool_manager_url}")
        asyncio.run(register_tools(args.tool_manager_url, TOOLS))
        logger.info("Tool registration complete")
    except KeyboardInterrupt:
        logger.info("Tool registration interrupted")
    except Exception as e:
        logger.error(f"Error during tool registration: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 