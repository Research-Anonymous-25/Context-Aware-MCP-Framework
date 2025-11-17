from fastmcp import FastMCP

mcp = FastMCP("ArrivalTrackerMCP")

GUESTS = [
    {
        "name": "family1",
        "arrival_location": "airport",
        "arrival_time": "14:00",
        "needs_ride": True
    },
    {
        "name": "family2",
        "arrival_location": "hotel",
        "arrival_time": "15:00",
        "needs_ride": True
    }
]

@mcp.tool(
    name="track_guest_arrivals",
    description="Provides details of expected guest arrivals"
)
async def track_guest_arrivals():
    return {"guest_arrivals": GUESTS}

if __name__ == "__main__":
    mcp.run()
