from fastmcp import FastMCP
from datetime import datetime, timedelta

mcp = FastMCP("Transport MCP")

TRAVEL_TIMES = {
    ("B", "G"): 45,
    ("B", "T"): 30,
    ("B", "W"): 40,
    ("G", "T"): 20,
    ("G", "W"): 25,
    ("T", "W"): 15,
    ("W", "B"): 40,
    ("T", "B"): 30,
    ("G", "B"): 45,
    ("W", "T"): 15,
    ("W", "G"): 25,
    ("T", "G"): 20
}

@mcp.tool(
    name="plan_transport",
    description="Returns travel time and arrival estimate between two locations with optional start time"
)
async def plan_transport(from_location: str, to_location: str, departure_time: str = None):
    key = (from_location, to_location)
    if key not in TRAVEL_TIMES:
        key = (to_location, from_location)
    travel_time = TRAVEL_TIMES.get(key, None)
    if travel_time is None:
        return {"error": f"Unknown route between {from_location} and {to_location}"}

    arrival_time = None
    if departure_time:
        dt = datetime.strptime(departure_time, "%H:%M")
        dt += timedelta(minutes=travel_time)
        arrival_time = dt.strftime("%H:%M")

    return {"travel_time_min": travel_time, "arrival_time": arrival_time}

if __name__ == "__main__":
    mcp.run()