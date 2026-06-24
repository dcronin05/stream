from mcp.server.fastmcp import FastMCP
import db

# Initialize FastMCP Server
mcp = FastMCP("Universal Clipboard")
db.init_db()

@mcp.tool()
def read_clipboard() -> str:
    """Reads the latest clip from the central clipboard."""
    clip = db.get_latest_clip()
    if clip:
        return f"[{clip['timestamp']} - {clip['source']}]\n{clip['content']}"
    return "Clipboard is empty."

@mcp.tool()
def write_clipboard(content: str, source: str = "agent") -> str:
    """Writes a new string to the central clipboard, pushing the old ones into history."""
    db.add_clip(content, source)
    return "Successfully wrote to clipboard."

@mcp.tool()
def clear_clipboard() -> str:
    """Clears the entire clipboard history."""
    db.clear_clips()
    return "Clipboard cleared."

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
