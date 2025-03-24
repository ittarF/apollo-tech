import json
import logging
import uuid
from typing import Dict, List, Any, Optional
import httpx
import re

from app.services.llm_connector import OllamaConnector
from app.services.context_manager import ContextManager

logger = logging.getLogger(__name__)

class Agent:
    """
    Main agent class that orchestrates the interaction between user input,
    LLM engine, context manager, and tool services.
    
    This agent follows the architecture in the diagram, handling the flow from
    user input to generating responses with tool usage when appropriate.
    """
    
    def __init__(self, 
                 tool_manager_url: str,
                 ollama_base_url: str = "http://localhost:11434",
                 model: str = "gemma3"):
        """
        Initialize the agent with necessary services.
        
        Args:
            tool_manager_url: URL of the Tool Manager API
            ollama_base_url: Base URL for Ollama API
            model: Default LLM model to use
        """
        self.tool_manager_url = tool_manager_url
        self.llm_connector = OllamaConnector(base_url=ollama_base_url, model=model)
        self.context_manager = ContextManager()
        self.http_client = httpx.AsyncClient(timeout=60.0)
        
    async def _fetch_relevant_tools(self, prompt: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Fetch tools relevant to the user prompt from the Tool Manager API.
        
        Args:
            prompt: User prompt
            top_k: Number of most relevant tools to return
            
        Returns:
            List of tool definitions
        """
        try:
            logger.debug(f"Fetching relevant tools for prompt: {prompt}")
            url = f"{self.tool_manager_url}/tool_lookup"
            
            response = await self.http_client.post(
                url,
                json={"prompt": prompt, "top_k": top_k}
            )
            response.raise_for_status()
            
            result = response.json()
            logger.debug(f"Found {len(result.get('tools', []))} relevant tools")
            return result.get("tools", [])
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during tool lookup: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Error fetching relevant tools: {str(e)}")
            return []
    
    async def _execute_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool call using the Tool Manager API.
        
        Args:
            tool_call: Tool call definition with name and parameters
            
        Returns:
            Tool execution result
        """
        try:
            logger.debug(f"Executing tool call: {tool_call}")
            url = f"{self.tool_manager_url}/tool_usage"
            
            response = await self.http_client.post(
                url,
                json={"tool_call": tool_call}
            )
            response.raise_for_status()
            
            result = response.json()
            logger.debug(f"Tool execution result: {result}")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during tool execution: {e.response.status_code} - {e.response.text}")
            return {"result": None, "error": f"HTTP error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Error executing tool: {str(e)}")
            return {"result": None, "error": str(e)}
    
    async def _parse_llm_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse the LLM response to extract potential tool calls.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Parsed response with text and potential tool_call
        """
        text = response.get("response", "")
        tool_call = None
        
        # First try to parse directly as JSON #1
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                # Extract the response text and tool call if available
                text = parsed.get("response", text)
                tool_call = parsed.get("tool_call")
                return {
                    "text": text.strip(),
                    "tool_call": tool_call
                }
        except json.JSONDecodeError as e:
            pass
            # logger.warning(f"Failed to parse response as JSON: {str(e)}")
        
        # Try to extract JSON from markdown code blocks #2
        try:
            # Match both ```json and ``` code blocks
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                return dict(**data) # TODO: use pydantic models
            
        except (json.JSONDecodeError, AttributeError, IndexError):
            pass
        
        # Fall back to regex patterns if direct parsing fails #3
        try:
            # Look for a JSON object that might contain a tool call
            json_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
            matches = re.finditer(json_pattern, text)
            
            for match in matches:
                potential_json = match.group(0)
                try:
                    parsed_json = json.loads(potential_json)
                    if "tool_call" in parsed_json:
                        tool_call = parsed_json["tool_call"]
                        # Use the response text if available
                        if "response" in parsed_json:
                            text = parsed_json["response"]
                        else:
                            # Remove the JSON from the text
                            text = text.replace(potential_json, "")
                        break
                except json.JSONDecodeError:
                    continue
            
        except Exception as e:
            logger.error(f"Error parsing LLM response with regex: {str(e)}")
        
        # If all else fails, try the basic approach as a last resort #4
        if not tool_call and "{" in text and "}" in text:
            try:
                # Simple approach: find outermost { and }
                json_start = text.find("{")
                json_end = text.rfind("}") + 1
                
                potential_json = text[json_start:json_end]
                
                # Replace single quotes with double quotes for valid JSON
                potential_json = potential_json.replace("'", '"')
                
                try:
                    parsed_json = json.loads(potential_json)
                    if "tool_call" in parsed_json:
                        tool_call = parsed_json["tool_call"]
                        # Use the response text if available
                        if "response" in parsed_json:
                            text = parsed_json["response"]
                        else:
                            # Remove the JSON from the text
                            text = text[:json_start] + text[json_end:]
                except json.JSONDecodeError:
                    logger.debug(f"Failed to parse JSON: {potential_json}")
            except Exception as e:
                logger.error(f"Error in basic JSON parsing approach: {str(e)}")
        
        return {
            "text": text.strip(),
            "tool_call": tool_call
        }
    
    async def process_input(self, 
                         user_input: str, 
                         conversation_id: Optional[str] = None,
                         debug_mode: bool = False) -> Dict[str, Any]:
        """
        Process user input and generate a response, potentially using tools.
        
        This method implements the complete flow from the architecture diagram:
        1. Receive user input
        2. Fetch relevant tools
        3. Send prompt to LLM with context
        4. Parse response and execute tools if needed
        5. Send final response to user
        
        Args:
            user_input: User's input text
            conversation_id: Optional conversation ID (generates new ID if None)
            debug_mode: Whether to include debug information in the response
            
        Returns:
            Response with assistant text and any tool usage information
        """
        # Generate a conversation ID if not provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            
        logger.info(f"Processing input for conversation {conversation_id}: {user_input}")
        
        # Step 1: Fetch relevant tools based on user input
        relevant_tools = await self._fetch_relevant_tools(user_input)
        
        # Step 2: Get the full context for the prompt
        context = self.context_manager.get_full_context(
            conversation_id=conversation_id,
            user_input=user_input,
            tools=relevant_tools
        )
        
        # Create the debug info dictionary if debug mode is enabled
        debug_info = {}
        if debug_mode:
            debug_info = {
                "system_message": context.get("system_message", ""),
                "conversation_history": context.get("conversation_history", ""),
                "tools": [tool.get("name", "") for tool in relevant_tools],
                "full_tools_info": relevant_tools
            }
        
        # Step 3: Generate initial response with LLM
        llm_response = await self.llm_connector.generate_with_tool_context(
            prompt=user_input,
            tools=relevant_tools,
            conversation_context=context.get("conversation_history"),
            system_message=context.get("system_message")
        )
        
        if debug_mode:
            debug_info["raw_llm_response"] = llm_response
        
        # Step 4: Parse the LLM response to check for tool calls
        parsed_response = await self._parse_llm_response(llm_response)
        response_text = parsed_response.get("response", "")
        tool_call = parsed_response.get("tool_call")
        
        # Step 5: Execute tool if a tool call was detected
        tool_result = None
        if tool_call:
            logger.info(f"Tool call detected: {tool_call}")
            
            # Record the tool call in context
            self.context_manager.add_tool_call(
                conversation_id=conversation_id,
                tool_name=tool_call.get("name", "unknown"),
                parameters=tool_call.get("parameters", {})
            )
            
            # Execute the tool
            tool_result = await self._execute_tool(tool_call)
            
            # Update the tool call with the result
            # TODO: fix to exclude useless tokens
            self.context_manager.add_tool_call(
                conversation_id=conversation_id,
                tool_name=tool_call.get("name", "unknown"),
                parameters=tool_call.get("parameters", {}),
                result=tool_result.get("result"),
                error=tool_result.get("error")
            )
            
            # If tool execution was successful, generate a follow-up response
            if tool_result.get("result") is not None:
                # Get updated context with tool result
                updated_context = self.context_manager.get_full_context(
                    conversation_id=conversation_id,
                    user_input=user_input,
                    tools=relevant_tools
                )
                
                # Generate follow-up response with tool result context
                follow_up_prompt = (
                    f"I executed the tool {tool_call.get('name')} with parameters "
                    f"{json.dumps(tool_call.get('parameters'))} and got the result: "
                    f"{json.dumps(tool_result.get('result'))}. Please provide a helpful "
                    f"response based on this result."
                )
                
                follow_up_response = await self.llm_connector.generate_with_tool_context(
                    prompt=follow_up_prompt,
                    tools=relevant_tools,
                    conversation_context=updated_context.get("conversation_history")
                )
                
                if debug_mode:
                    debug_info["follow_up_prompt"] = follow_up_prompt
                    debug_info["raw_follow_up_response"] = follow_up_response
                
                parsed_follow_up = await self._parse_llm_response(follow_up_response)
                response_text = parsed_follow_up.get("response", "")
        
        # Step 6: Record the assistant's response in the context
        self.context_manager.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=response_text
        )
        
        # Return the final response with any tool usage information
        response = {
            "conversation_id": conversation_id,
            "response": response_text,
            "tool_used": tool_call.get("name") if tool_call else None,
            "tool_parameters": tool_call.get("parameters") if tool_call else None,
            "tool_result": tool_result
        }
        
        # Add debug info if debug mode is enabled
        if debug_mode:
            debug_info["raw_llm_response"] = llm_response
            response["debug_info"] = debug_info
            
        # Log a warning if we didn't get a proper JSON response
        if debug_mode and not tool_call and ("raw_llm_response" in debug_info):
            raw_response = debug_info.get("raw_llm_response", {}).get("response", "")
            try:
                # Check if the raw response is valid JSON
                json.loads(raw_response)
            except json.JSONDecodeError:
                logger.warning("LLM failed to respond with proper JSON formatting")

        return response
    
    async def close(self):
        """Close the HTTP client and resources."""
        await self.http_client.aclose()
        await self.llm_connector.close()
        logger.info("Agent resources closed") 