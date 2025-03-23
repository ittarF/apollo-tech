import os
import json
import logging
import uuid
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agent import Agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Get Tool Manager URL from environment or use default
TOOL_MANAGER_URL = os.environ.get("TOOL_MANAGER_URL", "http://localhost:8000")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "gemma3")

# Initialize a single Agent instance for all requests
agent_instance = Agent(
    tool_manager_url=TOOL_MANAGER_URL,
    ollama_base_url=OLLAMA_BASE_URL,
    model=DEFAULT_MODEL,
)

# Define request and response models
class UserRequest(BaseModel):
    input: str
    conversation_id: Optional[str] = None

class AgentResponse(BaseModel):
    conversation_id: str
    response: str
    tool_used: Optional[str] = None
    tool_parameters: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None

# Initialize FastAPI app
app = FastAPI(
    title="Agent API",
    description="API for interacting with the LLM-powered agent",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a dependency that returns the singleton agent
async def get_agent():
    return agent_instance

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "online", "message": "Agent API is running"}

@app.post("/process", response_model=AgentResponse)
async def process_input(request: UserRequest, agent: Agent = Depends(get_agent)):
    """
    Process user input and return agent response.
    
    This endpoint implements the main interaction flow:
    1. Receive user input
    2. Process through agent (which handles tools, LLM, etc.)
    3. Return response
    """
    try:
        logger.info(f"Received request: {request.input[:50]}...")
        
        # Process the input through the agent
        result = await agent.process_input(
            user_input=request.input,
            conversation_id=request.conversation_id
        )
        
        return AgentResponse(**result)
        
    except Exception as e:
        logger.error(f"Error processing input: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing input: {str(e)}")

@app.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str, agent: Agent = Depends(get_agent)):
    """Delete a conversation by ID."""
    try:
        agent.context_manager.delete_conversation(conversation_id)
        return {"status": "success", "message": f"Conversation {conversation_id} deleted"}
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting conversation: {str(e)}")

@app.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str, agent: Agent = Depends(get_agent)):
    """Get conversation history by ID."""
    try:
        if conversation_id not in agent.context_manager.conversations:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
            
        # Get conversation data
        conv = agent.context_manager.conversations[conversation_id]
        
        # Convert to serializable format
        messages = [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in conv.messages
        ]
        
        tool_calls = [
            {
                "tool_name": tc.tool_name,
                "parameters": tc.parameters,
                "result": tc.result,
                "error": tc.error,
                "timestamp": tc.timestamp.isoformat()
            }
            for tc in conv.tool_calls
        ]
        
        return {
            "conversation_id": conversation_id,
            "messages": messages,
            "tool_calls": tool_calls
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting conversation: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Close resources when application shuts down."""
    logger.info("Shutting down API server, closing resources...")
    await agent_instance.close()
    logger.info("Resources closed successfully") 