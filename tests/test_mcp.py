import asyncio
import json
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from test_properties import REF, lead, read, service  # noqa: F401 (service is a fixture)

ROOT = Path(__file__).resolve().parent.parent
# The contract the assistants rely on: the same 6 tools, with the same annotations.
TOOLS = {
    "read_emails": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    "list_pending": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    "save_replies": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
    "preview_send": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
    "send_replies": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": True},
    "dismiss_emails": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False},
}


def test_local_mcp_over_stdio_keeps_the_six_tools(service):
    read(service, [lead("1")])

    async def session():
        # Started the way an assistant starts it: a process that speaks MCP on stdin and stdout.
        server = StdioServerParameters(command=sys.executable, cwd=ROOT,
                                       args=["-m", "backend.cli", "--instance", str(service.folder), "stdio"])
        async with stdio_client(server) as streams, ClientSession(*streams) as client:
            await client.initialize()
            return (await client.list_tools()).tools, await client.call_tool("list_pending", {})

    tools, pending = asyncio.run(session())
    assert {tool.name: tool.annotations.model_dump(exclude_none=True) for tool in tools} == TOOLS
    assert {tool.name for tool in tools if "property_ref" in tool.inputSchema["properties"]} == set(TOOLS) - {"read_emails"}
    assert not pending.isError
    [queue] = json.loads(pending.content[0].text)["properties"]
    assert queue["property_ref"] == REF and [email["id"] for email in queue["emails"]] == ["1"]
