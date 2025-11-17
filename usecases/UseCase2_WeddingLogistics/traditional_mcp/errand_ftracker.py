from fastmcp import FastMCP

mcp = FastMCP("ErrandMCP")

ERRANDS = [
    {"name": "flowers", "status": "requested"},
    {"name": "cake", "status": "requested"},
    {"name": "decorations", "status": "requested"},
    {"name": "photographer", "status": "requested"},
    {"name": "music", "status": "requested"}
]

@mcp.tool(
    name="list_errands",
    description="Lists all errands with their current status"
)
async def list_errands():
    return {"errands": ERRANDS}

if __name__ == "__main__":
    mcp.run()
