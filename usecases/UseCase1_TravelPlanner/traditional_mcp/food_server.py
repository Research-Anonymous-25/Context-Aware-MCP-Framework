from fastmcp import FastMCP
from typing import Optional
import requests
import time
mcp = FastMCP("Food Server")

def overpass_get_with_retry(url, params, max_retries=5, base_sleep=10):
    for attempt in range(max_retries):
        resp = requests.get(url, params=params)
        if resp.status_code == 429:
            wait = base_sleep * (2 ** attempt)
            print(f"[Overpass] 429 Too Many Requests. Sleeping for {wait} seconds (attempt {attempt+1}/{max_retries})...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp
    raise Exception("Exceeded max retries for Overpass API")

@mcp.tool(name="find_food_places", description="Get list of restaurants and cafes in an area from OSM")
async def find_food_places(
    lat: float,
    lon: float,
    radius_km: Optional[int] = 5  # default search radius
):
    radius = radius_km * 1000  # meters

    overpass_query = f"""
    [out:json];
    (
      node(around:{radius},{lat},{lon})[amenity=restaurant];
      node(around:{radius},{lat},{lon})[amenity=cafe];
    );
    out center;
    """

    url = "http://overpass-api.de/api/interpreter"
    resp = overpass_get_with_retry(url, {"data": overpass_query})
    try:
        elements = resp.json().get("elements", [])
    except Exception:
        return {"error": "Failed to parse Overpass response"}

    results = [
        {
            "name": el.get("tags", {}).get("name", "Unnamed"),
            "lat": el["lat"],
            "lon": el["lon"],
            "cuisine": el.get("tags", {}).get("cuisine", ""),
            "tags": el.get("tags", {})
        }
        for el in elements if "tags" in el
    ]

    return {"food_places": results[:10]}
if __name__ == "__main__":
    mcp.run()