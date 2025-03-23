import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)

class Message(BaseModel):
    """Model representing a message in the conversation"""
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

class ToolCall(BaseModel):
    """Model representing a tool call"""
    tool_name: str
    parameters: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

class ConversationContext(BaseModel):
    """Model representing the full conversation context"""
    messages: List[Message] = Field(default_factory=list)
    tool_calls: List[ToolCall] = Field(default_factory=list)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

class ContextManager:
    """
    Manages conversation context and tool integration.
    
    Responsible for:
    1. Maintaining conversation history
    2. Tracking tool usage
    3. Constructing prompts with appropriate context
    4. Managing context window size
    """
    
    def __init__(self, max_history_length: int = 10):
        """
        Initialize the context manager.
        
        Args:
            max_history_length: Maximum number of messages to keep in history
        """
        self.conversations: Dict[str, ConversationContext] = {}
        self.max_history_length = max_history_length
    
    def create_conversation(self, conversation_id: str) -> None:
        """
        Create a new conversation context.
        
        Args:
            conversation_id: Unique ID for the conversation
        """
        if conversation_id in self.conversations:
            logger.warning(f"Conversation {conversation_id} already exists. Overwriting.")
            
        self.conversations[conversation_id] = ConversationContext()
        logger.info(f"Created new conversation with ID: {conversation_id}")
    
    def add_message(self, conversation_id: str, role: str, content: str) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            conversation_id: Conversation ID
            role: Message role (user, assistant, system)
            content: Message content
        """
        if conversation_id not in self.conversations:
            self.create_conversation(conversation_id)
            
        message = Message(role=role, content=content)
        self.conversations[conversation_id].messages.append(message)
        
        # Trim history if it exceeds max length
        if len(self.conversations[conversation_id].messages) > self.max_history_length:
            self.conversations[conversation_id].messages.pop(0)
            
        logger.debug(f"Added {role} message to conversation {conversation_id}")
    
    def add_tool_call(self, 
                    conversation_id: str, 
                    tool_name: str, 
                    parameters: Dict[str, Any],
                    result: Optional[Any] = None,
                    error: Optional[str] = None) -> None:
        """
        Add a tool call to the conversation history.
        
        Args:
            conversation_id: Conversation ID
            tool_name: Name of the tool called
            parameters: Tool parameters
            result: Optional result from the tool
            error: Optional error message if the tool call failed
        """
        if conversation_id not in self.conversations:
            self.create_conversation(conversation_id)
            
        tool_call = ToolCall(
            tool_name=tool_name,
            parameters=parameters,
            result=result,
            error=error
        )
        
        self.conversations[conversation_id].tool_calls.append(tool_call)
        logger.debug(f"Added tool call {tool_name} to conversation {conversation_id}")
    
    def get_formatted_history(self, conversation_id: str, include_system: bool = True) -> str:
        """
        Get formatted conversation history as a string for prompting.
        
        Args:
            conversation_id: Conversation ID
            include_system: Whether to include system messages
            
        Returns:
            Formatted conversation history
        """
        if conversation_id not in self.conversations:
            logger.warning(f"Conversation {conversation_id} not found")
            return ""
            
        history = ""
        for message in self.conversations[conversation_id].messages:
            if not include_system and message.role == "system":
                continue
                
            history += f"{message.role.capitalize()}: {message.content}\n\n"
            
        return history.strip()
    
    def get_tool_context(self, conversation_id: str, recent_only: bool = True, max_tools: int = 5) -> str:
        """
        Get context about recent tool calls.
        
        Args:
            conversation_id: Conversation ID
            recent_only: Whether to include only recent tool calls
            max_tools: Maximum number of tool calls to include
            
        Returns:
            Formatted tool context
        """
        if conversation_id not in self.conversations:
            logger.warning(f"Conversation {conversation_id} not found")
            return ""
            
        tool_calls = self.conversations[conversation_id].tool_calls
        
        if recent_only:
            tool_calls = tool_calls[-max_tools:] if tool_calls else []
            
        context = "Recent tool calls:\n"
        
        if not tool_calls:
            return ""
            
        for call in tool_calls:
            context += f"- Tool: {call.tool_name}\n"
            context += f"  Parameters: {call.parameters}\n"
            
            if call.result is not None:
                context += f"  Result: {call.result}\n"
            elif call.error is not None:
                context += f"  Error: {call.error}\n"
                
            context += "\n"
            
        return context
    
    def clear_conversation(self, conversation_id: str) -> None:
        """
        Clear a conversation's history.
        
        Args:
            conversation_id: Conversation ID to clear
        """
        if conversation_id in self.conversations:
            self.conversations[conversation_id] = ConversationContext()
            logger.info(f"Cleared conversation {conversation_id}")
        else:
            logger.warning(f"Attempted to clear nonexistent conversation {conversation_id}")
    
    def delete_conversation(self, conversation_id: str) -> None:
        """
        Delete a conversation.
        
        Args:
            conversation_id: Conversation ID to delete
        """
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            logger.info(f"Deleted conversation {conversation_id}")
        else:
            logger.warning(f"Attempted to delete nonexistent conversation {conversation_id}")
            
    def get_full_context(self, 
                       conversation_id: str, 
                       user_input: str,
                       tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get the full context for an LLM prompt, including conversation history and available tools.
        
        Args:
            conversation_id: Conversation ID
            user_input: Current user input
            tools: List of available tools
            
        Returns:
            Dictionary with prompt, system_message, and tools context
        """
        # Create conversation if it doesn't exist
        if conversation_id not in self.conversations:
            self.create_conversation(conversation_id)
            
        # Add the current user input to history
        self.add_message(conversation_id, "user", user_input)
        
        # Get conversation history
        history = self.get_formatted_history(conversation_id)
        
        # Get tool context
        tool_context = self.get_tool_context(conversation_id)
        
        # System message that instructs the model
        system_message = ("""You are a helpful AI assistant. 

IMPORTANT: You MUST format ALL your responses as valid JSON objects with this structure:
```json
{
    "response": "your helpful response text here",
    "tool_call": null
}
```

When you need to use a tool, format your response as:
```json
{
    "response": "your explanation of what you're doing",
    "tool_call": {
        "name": "name_of_tool",
        "parameters": {
            "param1": "value1",
            "param2": "value2"
        }
    }
}
```

NEVER respond in plain text. ALWAYS use this JSON format.""")
        
        # If we have tool context, add it to the system message
        if tool_context:
            system_message += f"\n\n{tool_context}"
            
        return {
            "conversation_history": history,
            "system_message": system_message,
            "current_input": user_input,
            "tools": tools or []
        } 