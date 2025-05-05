from mcp_client import MCPClient
import asyncio

# Create an array of strings
instructions = [
    "navigate to navigate to http://localhost:8080/now/sow/synthetics-management, if you are presented with login screen, use admin/admin to login",
]

# Test: Navigation to Synthetic Monitoring
# instructions = [
#   "navigate to: http://localhost:8080/now/sow/home. if you are presented with login screen, use admin/admin to login",
#   "Click the Synthetics Management button",
#   "Confirm that the page title is: Synthetic monitoring | Service Operations Workspace | ServiceNow",
#   "Ensure that the page heading 'Synthetic monitoring' is visible."
# ]

# instructions = [
#   "navigate to: http://localhost:8080/now/sow/home. if you are presented with login screen, use admin/admin to login",
#   "Click the Synthetics Management button",
#   "Confirm that the page title is: Synthetic monitoring | Service Operations Workspace | ServiceNow",
#   "Ensure that the page heading 'Synthetic monitoring' is visible."
# ]

async def main():
    client = MCPClient()
    await client.connect_to_server("/Users/martin.kuba/dev/playwright-mcp/cli.js", ["--config", "./config.json"])

    for instruction in instructions:
        await client.process_query(instruction)

    await client.chat_loop()
    await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
