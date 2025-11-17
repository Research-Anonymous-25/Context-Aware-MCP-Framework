from fastmcp import FastMCP

mcp = FastMCP("TransportMCP")

VEHICLES = [
    {"name": "car1", "capacity": 4, "location": "reception_venue"},
    {"name": "car2", "capacity": 4, "location": "reception_venue"},
    {"name": "van", "capacity": 8, "location": "reception_venue"}
]

@mcp.tool(
    name="list_vehicles",
    description="Lists vehicles with capacity and current location"
)
async def list_vehicles():
    return {"vehicles": VEHICLES}

if __name__ == "__main__":
    mcp.run()
