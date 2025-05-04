import asyncio
from typing import Optional
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from anthropic import Anthropic
from dotenv import load_dotenv
import sys

load_dotenv()  # load environment variables from .env

def get_size(obj):
    size = sys.getsizeof(obj)
    if isinstance(obj, dict):
        size += sum(get_size(k) + get_size(v) for k, v in obj.items())
    elif isinstance(obj, (list, tuple, set)):
        size += sum(get_size(item) for item in obj)
    return size

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.messages = []

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server
        
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")
            
        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""

        print(f"* User: {query}")

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
        return await self._process_with_tool_calls(messages, available_tools)

    async def _process_with_tool_calls(self, messages, available_tools, iteration=0, max_iterations=10):
        """Process messages with multiple rounds of tool calls"""
        final_text = []
        
        print(f"\nRequest: iteration {iteration}")

        pruned_messages = self._get_messages_for_llm()
        print(f"Size of messages: {get_size(messages)}, size of pruned messages: {get_size(pruned_messages)}")

        # Call Claude with current conversation history
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            messages=pruned_messages,
            tools=available_tools
        )
        # print("Response messages:")
        # print(response)

        has_tool_call = False
        for content in response.content:
            if content.type == 'text':
                # add to memory
                messages.append({
                    "role": "assistant",
                    "content": content.text
                })

                print(f"* Assistant: {content.text}")
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

                print(f"* Tool use: {tool_name} with args {tool_args}")

                # Execute tool call
                # print(f"[Calling tool {tool_name} with args {tool_args}]")
                tool_result = await self.session.call_tool(tool_name, tool_args)

                print(f"* Tool result: {tool_result}")

                result_blocks = []
                for block in tool_result.content:
                    if block.type == 'text':
                        result_blocks.append({
                            "type": "text",
                            "text": block.text
                        })
                    elif block.type == 'image':
                        result_blocks.append(f"Image: {block.image_url}")

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

        # last three messages
        # messages = self.messages[-3:] if len(self.messages) >= 3 else self.messages

        messages = []
        last_tool_included = False
        for message in reversed(self.messages):
            # print(f"role: {message['role']}, size: {get_size(message['content'])}")
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
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            query = input("\nQuery: ").strip()
            
            if query.lower() == 'quit':
                break
                
            response = await self.process_query(query)
            # print("\n" + response)
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
        
    client = MCPClient()
    try:
        # interactive chat
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()

        # non-interactive query
        # response = await client.process_query("navigate to localhost:8080 and login with username 'admin' and password 'admin'")
        # print("Final response:")
        # print(response)

    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())