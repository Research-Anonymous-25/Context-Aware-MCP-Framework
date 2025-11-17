# schedule_validator_mcp.py

from fastmcp import FastMCP
from datetime import datetime

mcp = FastMCP("Schedule Validator MCP")

PHOTO_TIME = datetime.strptime("15:00", "%H:%M")

@mcp.tool(
    name="validate_schedule_feasibility",
    description="Validates if all guests and errands can be completed before 3 PM photo time"
)
async def validate_schedule_feasibility(data: dict):
    """
    Expects data to contain:
    - 'guest_arrivals': list of guest dicts with 'arrival_time' keys
    - 'errand_plan': list of errands with 'pickup_time' keys
    - 'transport_time_minutes': dict with keys 'B->W', etc.
    """
    issues = []

    # Check guests
    for guest in data.get("guest_arrivals", []):
        time_str = guest.get("arrival_time", "15:01")
        arrival_time = datetime.strptime(time_str, "%H:%M")
        if arrival_time > PHOTO_TIME:
            issues.append(f"{guest['name']} is arriving after photo time: {time_str}")

    # Check errands
    for errand in data.get("errand_plan", []):
        pickup_time_str = errand.get("pickup_time", "15:01")
        pickup_time = datetime.strptime(pickup_time_str, "%H:%M")
        if pickup_time > PHOTO_TIME:
            issues.append(f"{errand['item']} pickup is after photo time: {pickup_time_str}")

    if issues:
        return {
            "valid": False,
            "issues": issues
        }
    return {
        "valid": True,
        "message": "All tasks complete before photo time"
    }

if __name__ == "__main__":
    mcp.run()
