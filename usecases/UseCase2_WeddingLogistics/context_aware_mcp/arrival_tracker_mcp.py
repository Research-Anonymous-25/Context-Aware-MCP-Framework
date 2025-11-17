from fastmcp import FastMCP

mcp = FastMCP("ArrivalTrackerMCP")

@mcp.tool(
    name="track_guest_arrivals",
    description="Tracks guest arrivals from Airport Pickup Data"
)
async def track_guest_arrivals():
    guests = [
        {"name": "Alex", "arrival_time": "11:00", "location": "B", "needs_ride": True},
        {"name": "Jamie", "arrival_time": "12:30", "location": "B", "needs_ride": True},
        {"name": "Pat", "arrival_time": "12:00", "location": "W", "has_car": True}
    ]
    return {"guest_arrivals": guests}

if __name__ == "__main__":
    mcp.run()
