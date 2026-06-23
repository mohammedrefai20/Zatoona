from mcp.server.fastmcp import FastMCP

from config import settings
from vector_db import chroma_client
from mcp_server.tools import retrieval_tool

mcp = FastMCP("leo-notes")
retrieval_tool.register(mcp)


def init_collection():
    if settings.SESSION_RESET:
        return chroma_client.reset_collection()
    return chroma_client.get_collection()


def start_mcp_server(host=settings.MCP_HOST, port=settings.MCP_PORT, transport="streamable-http"):
    init_collection()
    mcp.settings.host = host
    mcp.settings.port = port
    mcp.run(transport=transport)


if __name__ == "__main__":
    start_mcp_server()
