import asyncio
from typing import Optional, List
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from anthropic import Anthropic
from dotenv import load_dotenv
import sys
from mcp_client import MCPClient

load_dotenv()

def get_size(obj):
    size = sys.getsizeof(obj)
    if isinstance(obj, dict):
        size += sum(get_size(k) + get_size(v) for k, v in obj.items())
    elif isinstance(obj, (list, tuple, set)):
        size += sum(get_size(item) for item in obj)
    return size

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script> [server_args...]")
        sys.exit(1)
        
    client = MCPClient()
    try:
        # Get server script path and any additional arguments
        server_script = sys.argv[1]
        server_args = sys.argv[2:] if len(sys.argv) > 2 else None

        print(server_script)
        print(server_args)
        
        # interactive chat
        await client.connect_to_server(server_script, server_args)
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
