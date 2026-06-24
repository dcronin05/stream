from mcp.server.fastmcp import FastMCP
import db

# Initialize FastMCP Server
mcp = FastMCP("Universal AI Stream")
db.init_db()

@mcp.tool()
def read_stream() -> str:
    """Reads the latest post from the central AI Stream timeline."""
    clip = db.get_latest_clip()
    if clip:
        return f"[{clip['timestamp']} - {clip['source']}]\n{clip['content']}"
    return "Stream is empty."

@mcp.tool()
def post_to_stream(content: str, source: str = "agent") -> str:
    """Publishes a new update or string to the central AI Stream timeline."""
    db.add_clip(content, source)
    return "Successfully posted to Stream."

@mcp.tool()
def clear_stream() -> str:
    """Clears the entire Stream timeline history."""
    db.clear_clips()
    return "Stream cleared."

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--sse":
        # Start the SSE server on port 8001
        mcp.settings.host = "0.0.0.0"
        mcp.settings.port = 8001
        mcp.run(transport="sse")
    else:
        # Default to stdio for local agent integrations
        mcp.run(transport="stdio")
