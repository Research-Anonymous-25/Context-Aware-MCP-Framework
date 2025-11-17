import requests
from fastmcp import FastMCP
from typing import Optional
import time

mcp = FastMCP("Hotel Server")

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

def overpass_query(lat, lon, radius):
    query = f"""
    [out:json][timeout:25];
    (
      node["tourism"~"hotel|hostel|guest_house"](around:{radius},{lat},{lon});
      way["tourism"~"hotel|hostel|guest_house"](around:{radius},{lat},{lon});
      relation["tourism"~"hotel|hostel|guest_house"](around:{radius},{lat},{lon});
    );
    out center tags;
    """
    url = "https://overpass-api.de/api/interpreter"
    resp = overpass_get_with_retry(url, {'data': query})
    return resp.json()

@mcp.tool(
    name="find_hotels_nearby",
    description="Find nearby hotels, hostels, or guest houses using OSM based on lat/lon and radius in meters."
)
async def find_hotels_nearby(
    lat: float,
    lon: float,
    radius: Optional[int] = 5000  # meters
):
    data = overpass_query(lat, lon, radius)

    elements = data.get("elements", [])
    results = []

    for el in elements:
        tags = el.get("tags", {})
        results.append({
            "name": tags.get("name", "Unnamed"),
            "lat": el.get("lat") or el.get("center", {}).get("lat"),
            "lon": el.get("lon") or el.get("center", {}).get("lon"),
            "tourism": tags.get("tourism"),
            "stars": tags.get("stars"),
            "phone": tags.get("phone"),
            "website": tags.get("website"),
            "address": {
                "street": tags.get("addr:street"),
                "city": tags.get("addr:city"),
                "postcode": tags.get("addr:postcode"),
                "country": tags.get("addr:country")
            }
        })

    if not results:
        return {"message": "No hotels found nearby."}

    return {"hotels": results[:10]}

if __name__ == "__main__":
    mcp.run()