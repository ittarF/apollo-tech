import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.agent import Agent
from app.services.context_manager import ContextManager

@pytest.fixture
def mock_http_response():
    """Create a mock HTTP response."""
    mock_response = MagicMock()
    # Make raise_for_status return a regular value instead of a coroutine
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock()
    return mock_response

@pytest.fixture
def mock_httpx_client():
    """Create a mock HTTPX client."""
    with patch("httpx.AsyncClient") as mock_client:
        client_instance = AsyncMock()
        mock_client.return_value = client_instance
        client_instance.post = AsyncMock()
        client_instance.aclose = AsyncMock()
        yield client_instance

@pytest.fixture
def mock_llm_connector():
    """Create a mock LLM connector."""
    with patch("app.services.llm_connector.OllamaConnector") as mock_connector:
        connector_instance = AsyncMock()
        mock_connector.return_value = connector_instance
        connector_instance.generate_with_tool_context = AsyncMock()
        connector_instance.close = AsyncMock()
        yield connector_instance

@pytest.mark.asyncio
async def test_fetch_relevant_tools(mock_httpx_client, mock_http_response):
    """Test fetching relevant tools."""
    # Setup
    tools_data = {
        "tools": [
            {
                "name": "format_text",
                "description": "Format text according to specified style",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "format_type": {"type": "string"}
                    },
                    "required": ["text", "format_type"]
                }
            }
        ]
    }
    
    mock_http_response.json.return_value = tools_data
    mock_httpx_client.post.return_value = mock_http_response
    
    agent = Agent(tool_manager_url="http://mock-url")
    agent.http_client = mock_httpx_client
    
    # Execute
    result = await agent._fetch_relevant_tools("Format this text")
    
    # Assert
    mock_httpx_client.post.assert_called_once()
    assert result == tools_data["tools"]

@pytest.mark.asyncio
async def test_execute_tool(mock_httpx_client, mock_http_response):
    """Test executing a tool."""
    # Setup
    tool_result = {
        "result": {"formatted_text": "HELLO WORLD"},
        "error": None
    }
    
    mock_http_response.json.return_value = tool_result
    mock_httpx_client.post.return_value = mock_http_response
    
    agent = Agent(tool_manager_url="http://mock-url")
    agent.http_client = mock_httpx_client
    
    tool_call = {
        "name": "format_text",
        "parameters": {
            "text": "hello world",
            "format_type": "upper"
        }
    }
    
    # Execute
    result = await agent._execute_tool(tool_call)
    
    # Assert
    mock_httpx_client.post.assert_called_once()
    assert result == tool_result

@pytest.mark.asyncio
async def test_parse_llm_response_with_tool_call():
    """Test parsing LLM response with a tool call."""
    # Setup
    agent = Agent(tool_manager_url="http://mock-url")
    
    # Response with a tool call - using valid JSON format
    response = {
        "response": "I'll help you format that text. {\"tool_call\": {\"name\": \"format_text\", \"parameters\": {\"text\": \"hello world\", \"format_type\": \"upper\"}}}"
    }
    
    # Execute
    result = await agent._parse_llm_response(response)
    
    # Assert
    assert "text" in result
    assert "tool_call" in result
    assert result["tool_call"] is not None
    assert result["tool_call"]["name"] == "format_text"
    assert result["tool_call"]["parameters"]["text"] == "hello world"
    assert result["tool_call"]["parameters"]["format_type"] == "upper"

@pytest.mark.asyncio
async def test_parse_llm_response_without_tool_call():
    """Test parsing LLM response without a tool call."""
    # Setup
    agent = Agent(tool_manager_url="http://mock-url")
    
    # Response without a tool call
    response = {
        "response": "The answer to your question is 42."
    }
    
    # Execute
    result = await agent._parse_llm_response(response)
    
    # Assert
    assert result["text"] == "The answer to your question is 42."
    assert result["tool_call"] is None

@pytest.mark.asyncio
async def test_process_input(mock_llm_connector, mock_httpx_client, mock_http_response):
    """Test processing user input."""
    # Setup
    tools_data = {
        "tools": [
            {
                "name": "format_text",
                "description": "Format text according to specified style",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "format_type": {"type": "string"}
                    },
                    "required": ["text", "format_type"]
                }
            }
        ]
    }
    
    tool_result = {
        "result": {"formatted_text": "HELLO WORLD"},
        "error": None
    }
    
    # Mock responses
    mock_http_response.json.side_effect = [
        tools_data,  # For _fetch_relevant_tools
        tool_result  # For _execute_tool
    ]
    mock_httpx_client.post.return_value = mock_http_response
    
    # Mock LLM responses - Use valid JSON in the first response
    mock_llm_connector.generate_with_tool_context.side_effect = [
        {"response": "I'll format that text for you. {\"tool_call\": {\"name\": \"format_text\", \"parameters\": {\"text\": \"hello world\", \"format_type\": \"upper\"}}}"},
        {"response": "The text has been formatted to uppercase: HELLO WORLD"}
    ]
    
    # Create agent with mocks
    agent = Agent(tool_manager_url="http://mock-url")
    agent.http_client = mock_httpx_client
    agent.llm_connector = mock_llm_connector
    
    # Use context manager for testing to avoid dealing with creating mocks for its methods
    agent.context_manager = ContextManager()
    
    # Execute
    result = await agent.process_input("Format 'hello world' to uppercase")
    
    # Assert
    assert "response" in result
    assert result["response"] == "The text has been formatted to uppercase: HELLO WORLD"
    assert result["tool_used"] == "format_text"
    assert result["tool_parameters"]["text"] == "hello world"
    assert result["tool_parameters"]["format_type"] == "upper"
    assert result["tool_result"] == tool_result 