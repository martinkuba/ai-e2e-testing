from mcp_client import MCPClient
import asyncio
import os

# Create an array of strings
# instructions = [
#     "navigate to navigate to http://localhost:8080/now/sow/synthetics-management, if you are presented with login screen, use admin/admin to login",
# ]

# Test: Navigation to Synthetic Monitoring
# instructions = [
#   "navigate to: http://localhost:8080/now/sow/home. if you are presented with login screen, use admin/admin to login",
#   "Click the Synthetics Management button",
#   "Confirm that the page title is: Synthetic monitoring | Service Operations Workspace | ServiceNow",
#   "Ensure that the page heading 'Synthetic monitoring' is visible."
# ]

# Test: Home Page Buttons and Filter Dialog
instructions = [
  "navigate to: http://localhost:8080/now/sow/home. if you are presented with login screen, use admin/admin to login",
  "Go to: http://localhost:8080/now/sow/synthetics-management.",
  "Wait for the page to fully load.",
  "Check that the following buttons are visible: Filter, Refresh, Edit columns, Delete, Edit (exact match), Export, New",
  "Click the Filter button.",
  "Confirm that a dialog opens.",
  "Close the dialog by clicking Close dialog."
]

# instructions = ["""
#   - Navigate to: http://localhost:8080/now/sow/home. if you are presented with login screen, use admin/admin to login.
#   - Go to: http://localhost:8080/now/sow/synthetics-management.
#   - Wait for the page to fully load.
#   - Check that the following buttons are visible: Filter, Refresh, Edit columns, Delete, Edit (exact match), Export, New
#   - Click the Filter button.
#   - Confirm that a dialog opens.
#   - Close the dialog by clicking Close dialog.
# """
# ]

# Test: Creating a New Monitor
# instructions = [
#   "navigate to http://localhost:8080/now/sow/synthetics-new-monitor. if you are presented with login screen, use admin/admin to login",
#   "Enter a short, random name for the monitor (e.g., abcxyz).",
#   "Click in the field labeled 'Look up and select a configuration item': Press the down arrow key, then press enter to select the first item.",
#   "In the Locations drop-down menu, select Current Instance.",
#   "Set the assertion: in the drop-down menu that says 'Select a criteria', select 'Status code'. Then click in the 'Enter status code' field and select '200 OK'.",
#   "Enter the number 5 in the 'Enter a number' field.",
#   "Click the Save button.",
#   "Confirm that a new tab has opened with the name of the monitor you entered.",
#   "Click Synthetic monitoring in the navigation.",
#   "Wait for the page to load, then confirm: The monitor count has increased by one. A table row now lists the new monitor.",
#   "Click on the monitor name in the table to open its details."
# ]

system_prompt = """
You are an expert autonomous agent designed to perform end-to-end (E2E) testing of web applications.
You operate by issuing structured tool calls through the Model Context Protocol (MCP) to interact with a live web browser. These tool calls simulate user actions such as clicking buttons, filling out forms, navigating pages, or verifying page content.

If you encounter a tool error with the message 'Error: Stale aria-ref', this usually indicates the page has updated and a reference is no longer valid. In that case:

- Take a snapshot of the current page.
- Retry the same action once using a fresh reference.

Only attempt one retry. If it still fails, report the issue and continue or abort the test depending on severity.
"""

async def main():
    client = MCPClient()

    path = os.path.abspath("node_modules/@playwright/mcp/cli.js")
    await client.connect_to_server(path)

    # passing config file currently works only with playwright-mcp main branch (needs to be built locally) 
    # await client.connect_to_server("/Users/martin.kuba/dev/playwright-mcp/cli.js", ["--config", "./config.json"])

    for instruction in instructions:
        # print(f"Press enter to run next step:\n Next step: {instruction}")
        # input()
        await client.process_query(instruction, system_prompt)
    
    print("Continuing with interactive chat...")

    await client.chat_loop()
    await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
