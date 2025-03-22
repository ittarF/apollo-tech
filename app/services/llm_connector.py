import json
import logging
import httpx
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class OllamaConnector:
    """
    Connector for the Ollama LLM service.
    Handles communication with local Ollama instance.
    """
    
    def __init__(self, 
                 base_url: str = "http://localhost:11434",
                 model: str = "gemma3",
                 timeout: int = 120):
        """
        Initialize the Ollama connector.
        
        Args:
            base_url: Base URL for the Ollama API
            model: Default model to use (gemma3 by default)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
    
    async def generate_response(self, 
                          prompt: str,
                          system_prompt: Optional[str] = None,
                          temperature: float = 0.7,
                          max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate a response using the Ollama API.
        
        Args:
            prompt: The user prompt to send to the model
            system_prompt: Optional system prompt to guide the model's behavior
            temperature: Controls randomness (0 = deterministic, 1 = creative)
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Dictionary containing the model's response
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": False,  # Ensure streaming is disabled to get a complete response
        }
        
        if system_prompt:
            payload["system"] = system_prompt
            
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        try:
            logger.debug(f"Sending request to Ollama API: {payload}")
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            # Parse the response safely
            try:
                result = response.json()
                logger.debug(f"Received response from Ollama API: {result}")
                return result
            except json.JSONDecodeError as e:
                # Handle malformed JSON
                logger.error(f"Error parsing JSON from Ollama API: {str(e)}")
                logger.debug(f"Raw response content: {response.content}")
                
                # Try to extract only the first valid JSON object if there are multiple
                content = response.content.decode('utf-8')
                if '{' in content and '}' in content:
                    try:
                        # Find the first complete JSON object
                        start = content.find('{')
                        # Find the matching closing brace
                        depth = 0
                        for i, char in enumerate(content[start:], start):
                            if char == '{':
                                depth += 1
                            elif char == '}':
                                depth -= 1
                                if depth == 0:
                                    end = i + 1
                                    break
                        
                        # Extract and parse the first JSON object
                        json_str = content[start:end]
                        result = json.loads(json_str)
                        logger.debug(f"Successfully extracted JSON: {result}")
                        return result
                    except Exception as inner_e:
                        logger.error(f"Failed to extract valid JSON: {str(inner_e)}")
                
                # If all parsing attempts fail, return a basic response
                return {
                    "response": "I'm sorry, I encountered an error processing your request.",
                    "error": str(e)
                }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during Ollama API call: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error during Ollama API call: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during Ollama API call: {str(e)}")
            raise
    
    async def generate_with_tool_context(self, 
                                   prompt: str, 
                                   tools: List[Dict[str, Any]],
                                   conversation_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a response with tool definitions included in the context.
        
        Args:
            prompt: The user prompt to send to the model
            tools: List of tool definitions to include in the context
            conversation_context: Additional conversation context
            
        Returns:
            Dictionary containing the model's response
        """
        # Format the tool descriptions for the model
        tools_context = "Available tools:\n"
        for tool in tools:
            tools_context += f"- {tool['name']}: {tool['description']}\n"
            tools_context += f"  Parameters: {json.dumps(tool['parameters'])}\n\n"
        
        # Combine context components
        system_prompt = (
            "You are an AI assistant with access to tools. "
            "When appropriate, use tools to fulfill user requests. "
            "To use a tool, respond with JSON in the format: "
            "{'tool_call': {'name': 'tool_name', 'parameters': {...}}}"
            f"\n\n{tools_context}"
        )
        
        if conversation_context:
            prompt = f"Previous conversation:\n{conversation_context}\n\nUser: {prompt}"
        
        return await self.generate_response(prompt=prompt, system_prompt=system_prompt)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose() 