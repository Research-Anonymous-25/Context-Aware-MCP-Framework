from fastmcp import FastMCP

mcp = FastMCP("Errand MCP")

@mcp.tool(
    name="pickup_gift",
    description="Returns gift pickup readiness and time required to collect"
)
async def pickup_gift(current_time: str):
    # Gift shop opens at 12:00
    if current_time < "12:00":
        return {"status": "unavailable", "message": "Gift shop not open yet."}
    return {"status": "ready", "duration_min": 15}

@mcp.tool(
    name="pickup_clothes",
    description="Returns clothes pickup readiness and time required to collect"
)
async def pickup_clothes(current_time: str):
    # Tailor closes at 14:00
    if current_time > "14:00":
        return {"status": "closed", "message": "Tailor shop is closed."}
    return {"status": "ready", "duration_min": 15}

if __name__ == "__main__":
    mcp.run()
