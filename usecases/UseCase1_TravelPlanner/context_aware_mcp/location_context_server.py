from context_store import ContextStore
import requests
import time

KEYWORD_MAP = {
    # Nature & Relaxation
    "relaxing": [
        "leisure=park",
        "tourism=beach",
        "natural=wood",
        "natural=water",
        "place=hamlet",
        "place=village"
    ],
    "park": "leisure=park",
    "forest": "natural=wood",
    "lake": "natural=water",
    "hills": "natural=hill",
    "mountain": "natural=peak",
    # Coastal & Oceanfront
    "sunset": "natural=viewpoint",
    "view": "tourism=viewpoint",
    "scenic": "tourism=viewpoint",
    "beach": "tourism=beach",
    "coast": "natural=coastline",
    "oceanfront": "natural=coastline",
    "island": "place=island",
    "sea": "natural=bay",
    # Culture & History
    "museum": "tourism=museum",
    "gallery": "tourism=gallery",
    "historic site": "historic=yes",
    "church": "amenity=place_of_worship",
    "castle": "historic=castle",
    "monument": "historic=monument",
    # Food & Dining
    "vegetarian": "diet:vegetarian=yes",
    "restaurant": "amenity=restaurant",
    "cafe": "amenity=cafe",
    "food court": "amenity=food_court",
    "bakery": "shop=bakery",
    # Adventure & Outdoors
    "hiking": "route=hiking",
    "climbing": "sport=climbing",
    "amusement park": "tourism=theme_park",
    "zoo": "tourism=zoo",
    "aquarium": "tourism=aquarium",
    # Accommodation
    "hotel": "tourism=hotel",
    "hostel": "tourism=hostel",
    "motel": "tourism=motel",
    "camping": "tourism=camp_site",
    "resort": "tourism=resort"
}

def search_locations(base_city, radius_km=50, keyword=None):
    t0 = time.time()
    try:
        geo_resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": base_city, "format": "json", "limit": 1},
            headers={"User-Agent": "MCP-Travel-Agent/1.0"},
            timeout=10
        )
        print("[Location] Nominatim took", round(time.time() - t0, 2), "seconds")
        loc_data = geo_resp.json()
        if not loc_data:
            return {"error": "City not found"}
        lat, lon = float(loc_data[0]["lat"]), float(loc_data[0]["lon"])
    except Exception as e:
        return {"error": f"Geocoding failed: {e}"}

    radius_meters = radius_km * 1000
    overpass_url = "http://overpass-api.de/api/interpreter"

    # Keyword mapping
    overpass_query = ""
    if keyword and keyword.lower() in KEYWORD_MAP:
        tags = KEYWORD_MAP[keyword.lower()]
        if isinstance(tags, list):
            filters = "".join(
                f"node(around:{radius_meters},{lat},{lon})[{tag}];" for tag in tags
            )
            overpass_query = f"[out:json][timeout:25];{filters}out center 20;"
        else:
            key, value = tags.split("=")
            overpass_query = f"""
            [out:json][timeout:25];
            node(around:{radius_meters},{lat},{lon})[{key}={value}];
            out center 20;
            """
    elif keyword:
        # fallback to regex match if keyword is not in the predefined map
        overpass_query = f"""
        [out:json][timeout:25];
        node(around:{radius_meters},{lat},{lon})[tourism~"{keyword}",i];
        out center 20;
        """
    else:
        # no keyword given — return generic places
        overpass_query = f"""
        [out:json][timeout:25];
        node(around:{radius_meters},{lat},{lon})[place];
        out center 20;
        """

    t1 = time.time()
    try:
        overpass_resp = requests.get(overpass_url, params={"data": overpass_query}, timeout=30)
        print("[Location] Overpass took", round(time.time() - t1, 2), "seconds")
        results = overpass_resp.json().get("elements", [])
    except Exception as e:
        return {"error": f"Overpass API failed: {e}"}

    places = [
        {
            "name": el.get("tags", {}).get("name", "Unnamed"),
            "lat": el.get("lat"),
            "lon": el.get("lon")
        }
        for el in results if "tags" in el
    ]
    print(f"[Location] Found {len(places)} places.")

    if not places:
        print("[Location] No places found, using base city as fallback.")
        places = [{
            "name": base_city,
            "lat": lat,
            "lon": lon
        }]
    return {"places": places[:10], "lat": lat, "lon": lon}

def main():
    context = ContextStore()
    while True:
        context._load()  # Always reload context to get latest
        base_city = context.get("base_city")
        radius_km = context.get("radius_km")
        keyword = context.get("keyword")
        if base_city and not context.get("location_done"):
            print("[Location] Running location search...")
            result = search_locations(base_city, radius_km, keyword)
            context.set("location_result", result)
            context.set("location_done", True)
            print("[Location] Done. Wrote location_result and set location_done.")
        else:
            print("[Location] Waiting for base_city in context or already done...")
        time.sleep(2)

if __name__ == "__main__":
    main()