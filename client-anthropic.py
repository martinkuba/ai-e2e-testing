import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

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

    async def _process_with_tool_calls(self, messages, available_tools, max_iterations=10):
        """Process messages with multiple rounds of tool calls"""
        iteration = 0
        final_text = []
        
        # print("Request messages:")
        # print(messages)

        # Call Claude with current conversation history
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=messages,
            tools=available_tools
        )
        # print("Response messages:")
        # print(response)

        # messages.append({
        #     "role": "assistant",
        #     "content": response.content
        # })

        # go through the response and add to history
        for content in response.content:
            if content.type == 'text':
                messages.append({
                    "role": "assistant",
                    "content": content.text
                })
            elif content.type == 'tool_use':
                tool_name = content.name
                tool_args = content.input
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

        has_tool_call = False
        for content in response.content:
            if content.type == 'text':
                print(f"Text: {content.text}")
                # final_text.append(content.text)

            elif content.type == 'tool_use':
                has_tool_call = True
                tool_name = content.name
                tool_args = content.input

                # Execute tool call
                print(f"[Calling tool {tool_name} with args {tool_args}]")
                tool_result = await self.session.call_tool(tool_name, tool_args)

                print("Tool result:")
                print(tool_result)

                if "Timeout" in tool_result.content[0].text:
                    print("Tool execution timed out, waiting 10 seconds before continuing...")
                    await asyncio.sleep(10)
                    print("Resuming after timeout...")

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
            await self._process_with_tool_calls(messages, available_tools)
        
        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                response = await self.process_query(query)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
        
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()

        # response = await client.process_query("navigate to localhost:8080 and login with username 'admin' and password 'admin'")
        # print("Final response:")
        # print(response)

    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())