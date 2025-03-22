#!/usr/bin/env python3
import os
import json
import argparse
import httpx
import asyncio
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

# Default API endpoint
DEFAULT_API_URL = "http://localhost:8080"
# File to store conversation ID for persistence between sessions
CONVERSATION_STORE = "conversation_store.json"

console = Console()

async def process_input(api_url, user_input, conversation_id=None):
    """
    Send user input to the agent API and return the response.
    
    Args:
        api_url: API endpoint URL
        user_input: User's input text
        conversation_id: Optional conversation ID for continuing a conversation
        
    Returns:
        Agent's response and conversation ID
    """
    url = f"{api_url}/process"
    payload = {"input": user_input}
    
    if conversation_id:
        payload["conversation_id"] = conversation_id
        
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        console.print(f"[bold red]HTTP Error:[/] {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        console.print(f"[bold red]Error:[/] {str(e)}")
        return None

def load_conversation_id():
    """Load saved conversation ID from file."""
    if os.path.exists(CONVERSATION_STORE):
        try:
            with open(CONVERSATION_STORE, 'r') as f:
                data = json.load(f)
                return data.get('conversation_id')
        except Exception as e:
            console.print(f"[bold yellow]Warning:[/] Could not load conversation: {str(e)}")
    return None

def save_conversation_id(conversation_id):
    """Save conversation ID to file for persistence."""
    try:
        with open(CONVERSATION_STORE, 'w') as f:
            json.dump({'conversation_id': conversation_id}, f)
    except Exception as e:
        console.print(f"[bold yellow]Warning:[/] Could not save conversation: {str(e)}")

async def interactive_session(api_url):
    """
    Start an interactive session with the agent.
    
    Args:
        api_url: API endpoint URL
    """
    # Load existing conversation ID if available
    conversation_id = load_conversation_id()
    
    # Show message if continuing existing conversation
    if conversation_id:
        console.print("[bold yellow]Continuing previous conversation[/]")
    
    console.print(Panel.fit(
        "[bold blue]Apollo Tech Agent[/]",
        subtitle="Type 'exit' to quit, 'new' for new conversation"
    ))
    
    while True:
        user_input = console.input("[bold green]You:[/] ")
        
        if user_input.lower() in ("exit", "quit", "q"):
            console.print("[bold yellow]Exiting session[/]")
            break
            
        # Check if user wants to start a new conversation
        if user_input.lower() == "new":
            conversation_id = None
            save_conversation_id(None)
            console.print("[bold yellow]Starting new conversation[/]")
            continue
            
        # Show processing indicator
        with console.status("[bold blue]Processing...[/]"):
            result = await process_input(api_url, user_input, conversation_id)
            
        if not result:
            continue
            
        # Update conversation ID and save it
        conversation_id = result.get("conversation_id")
        save_conversation_id(conversation_id)
        
        # Display response
        console.print("[bold blue]Agent:[/]", Markdown(result.get("response", "")))
        
        # Display tool usage info if available
        tool_used = result.get("tool_used")
        if tool_used:
            console.print("[bold cyan]Tool used:[/]", tool_used)
            console.print("[bold cyan]Parameters:[/]", json.dumps(result.get("tool_parameters", {}), indent=2))
            
            tool_result = result.get("tool_result", {})
            if tool_result.get("result"):
                console.print("[bold cyan]Tool result:[/]", json.dumps(tool_result.get("result"), indent=2))
            elif tool_result.get("error"):
                console.print("[bold red]Tool error:[/]", tool_result.get("error"))
                
        console.print()

def main():
    parser = argparse.ArgumentParser(description="Apollo Tech Agent Client")
    parser.add_argument(
        "--api", 
        dest="api_url",
        default=os.environ.get("AGENT_API_URL", DEFAULT_API_URL),
        help=f"Agent API URL (default: {DEFAULT_API_URL})"
    )
    parser.add_argument(
        "--new",
        action="store_true",
        help="Start a new conversation (ignore saved conversation ID)"
    )
    
    args = parser.parse_args()
    
    # If --new flag was provided, delete any saved conversation
    if args.new and os.path.exists(CONVERSATION_STORE):
        os.remove(CONVERSATION_STORE)
        console.print("[bold yellow]Starting new conversation[/]")
    
    try:
        asyncio.run(interactive_session(args.api_url))
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Session terminated by user[/]")

if __name__ == "__main__":
    main() 