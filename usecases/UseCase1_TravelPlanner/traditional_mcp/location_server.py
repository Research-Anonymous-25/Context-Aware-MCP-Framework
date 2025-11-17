from fastmcp import FastMCP
from typing import Optional
import requests
import time

mcp = FastMCP("Location Server")

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

@mcp.tool(name="search_locations", description="Search locations near a city, optional OSM tag filter")
async def search_locations(
    base_city: str,
    radius_km: Optional[int] = 200,
    keyword: Optional[str] = None
):
    city = base_city
    radius = radius_km
    keyword = keyword

    # Step 1: Get city coordinates
    geo_resp = requests.get("https://nominatim.openstreetmap.org/search", params={
        "q": city,
        "format": "json",
        "limit": 1
    }, headers={"User-Agent": "MCP-Travel-Agent/1.0"})
    
    loc_data = geo_resp.json()
    if not loc_data:
        return {"error": "City not found"}
    
    lat, lon = loc_data[0]["lat"], loc_data[0]["lon"]
    radius_meters = radius * 1000
    overpass_url = "http://overpass-api.de/api/interpreter"

    # Step 2: Form Overpass query
    if keyword and "=" in keyword:
        key, value = keyword.split("=")
        overpass_query = f"""
        [out:json];
        node(around:{radius_meters},{lat},{lon})[{key}={value}];
        out center;
        """
    elif keyword:
        overpass_query = f"""
        [out:json];
        node(around:{radius_meters},{lat},{lon})[name~"{keyword}",i];
        out center;
        """
    else:
        overpass_query = f"""
        [out:json];
        node(around:{radius_meters},{lat},{lon})[place];
        out center;
        """

    # Step 3: Query Overpass API
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_resp = overpass_get_with_retry(overpass_url, {"data": overpass_query})
    try:
        results = overpass_resp.json().get("elements", [])
    except Exception:
        return {"error": "Error parsing Overpass response"}

    # Step 4: Extract place data
    places = [
        {
            "name": el.get("tags", {}).get("name", "Unnamed"),
            "lat": el.get("lat"),
            "lon": el.get("lon")
        }
        for el in results if "tags" in el
    ]

    return {"locations": places[:10]}

if __name__ == "__main__":
    mcp.run()