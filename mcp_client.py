import asyncio
from typing import Optional, List
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from anthropic import Anthropic
from dotenv import load_dotenv
import sys
from colorama import Fore, Style
import colorama
import base64
import os
from datetime import datetime

load_dotenv()
colorama.init()

def get_size(obj):
    size = sys.getsizeof(obj)
    if isinstance(obj, dict):
        size += sum(get_size(k) + get_size(v) for k, v in obj.items())
    elif isinstance(obj, (list, tuple, set)):
        size += sum(get_size(item) for item in obj)
    return size

def log_message(message: str, color: str = Fore.LIGHTBLUE_EX):
    print(color + f"\n{message}" + Style.RESET_ALL)

def log_debug(message: str):
    print(Fore.LIGHTBLACK_EX + f"DEBUG: {message}" + Style.RESET_ALL)

def log_error(message: str):
    print(Fore.RED + f"ERROR: {message}" + Style.RESET_ALL)

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.messages = []

    async def connect_to_server(self, server_script_path: str, server_args: List[str] = None):
        """Connect to an MCP server
        
        Args:
            server_script_path: Path to the server script (.py or .js)
            server_args: Additional arguments to pass to the server script
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")
            
        command = "python" if is_python else "node"
        args = [server_script_path]
        if server_args:
            args.extend(server_args)
            
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        # print("\nConnected to server with tools:", [tool.name for tool in tools])
        # log_debug("MCP Client Started!")

    async def process_query(self, query: str, system_prompt: str = None) -> str:
        """Process a query using Claude and available tools"""

        log_message(f"* User: {query}", Fore.LIGHTBLUE_EX)

        messages = self.messages
        messages.append({
            "role": "user",
            "content": query
        })

        response = await self.session.list_tools()
        available_tools = [{ 
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        # Add a helper function to process recursive tool calls
        return await self._process_with_tool_calls(messages, available_tools, system_prompt=system_prompt)

    async def _process_with_tool_calls(self, messages, available_tools, iteration=0, max_iterations=10, system_prompt: str = None):
        """Process messages with multiple rounds of tool calls"""
        final_text = []
        
        log_debug(f"Request: iteration {iteration}")

        # prune messages to get around rate limit (40000 tokens per minute) in Anthropic
        pruned_messages = self._get_messages_for_llm()
        # print(f"Size of messages: {get_size(messages)}, size of pruned messages: {get_size(pruned_messages)}")

        system_prompt = "" if not system_prompt else system_prompt

        # Call Claude with current conversation history
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=4000,
            messages=pruned_messages,
            tools=available_tools,
            temperature=0.4,
            system=system_prompt
        )
        log_debug(f"Response: {len(response.content)} blocks")
        # print(response)

        has_tool_call = False
        for content in response.content:
            if content.type == 'text':
                # add to memory
                messages.append({
                    "role": "assistant",
                    "content": content.text
                })

                log_message(f"* Assistant: {content.text}", Fore.CYAN)
                # final_text.append(content.text)

            elif content.type == 'tool_use':
                has_tool_call = True
                tool_name = content.name
                tool_args = content.input

                # add to memory
                messages.append({
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": content.id,
                            "name": tool_name,
                            "input": tool_args
                        }
                    ]
                })

                log_message(f"* Tool use: {tool_name} with args {tool_args}", Fore.LIGHTYELLOW_EX)

                # Execute tool call
                # print(f"[Calling tool {tool_name} with args {tool_args}]")
                tool_result = await self.session.call_tool(tool_name, tool_args)

                log_debug(f"* Tool result: {tool_result}")

                result_blocks = []
                for block in tool_result.content:
                    if block.type == 'text':
                        result_blocks.append({
                            "type": "text",
                            "text": block.text
                        })
                    elif block.type == 'image':
                        # Extract base64 encoded image data
                        data = block.data
                        mime_type = block.mimeType
                        
                        # Save the image to a file
                        try:
                            # Create output directory if it doesn't exist
                            output_dir = "screenshots"
                            os.makedirs(output_dir, exist_ok=True)
                            
                            # Generate a filename based on timestamp
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            extension = mime_type.split('/')[-1]
                            filename = f"{output_dir}/screenshot_{timestamp}.{extension}"
                            
                            # Decode and write to file
                            image_data = base64.b64decode(data)
                            with open(filename, "wb") as f:
                                f.write(image_data)
                            
                            log_message(f"* Saved image to {filename}", Fore.GREEN)
                            
                            # Add image info to result blocks
                            result_blocks.append({
                                "type": "text",
                                "text": f"Image saved to: {filename}"
                            })
                        except Exception as e:
                            log_error(f"Failed to save image: {e}")
                            result_blocks.append({
                                "type": "text",
                                "text": f"Error saving image: {str(e)}"
                            })

                # Add tool result to conversation history
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": content.id,
                            "content": result_blocks,
                        }
                    ],
                })

        if has_tool_call:
            await self._process_with_tool_calls(messages, available_tools, iteration + 1, max_iterations)
        
        return "\n".join(final_text)

    def _get_messages_for_llm(self):
        """Remove old messages to get around rate limit (40000 tokens per minute) in Anthropic
        The current strategy is to remove all tool calls and their results, and only keep the last one.
        """
        # last three messages
        # messages = self.messages[-3:] if len(self.messages) >= 3 else self.messages

        messages = []
        last_tool_included = False
        for message in reversed(self.messages):
            if (message['role'] == 'assistant' and 
                isinstance(message['content'], list) and 
                len(message['content']) > 0 and 
                message['content'][0]['type'] == 'tool_use'): 
                if last_tool_included:
                   continue 
                else:
                    last_tool_included = True

            if (message['role'] == 'user' and
                isinstance(message['content'], list) and 
                len(message['content']) > 0 and 
                message['content'][0].get('type') == 'tool_result' and 
                last_tool_included):
                continue

            messages.insert(0, message)

        return messages

    async def chat_loop(self):
        """Run an interactive chat loop"""
        log_message("Type your queries or 'quit' to exit.", Fore.WHITE)
        
        while True:
            query = input("\nQuery: ").strip()
            
            if query.lower() == 'quit':
                break
                
            response = await self.process_query(query)
            # print("\n" + response)
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose() 