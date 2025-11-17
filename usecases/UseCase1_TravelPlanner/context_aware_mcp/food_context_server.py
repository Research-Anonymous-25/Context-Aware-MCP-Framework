from context_store import ContextStore
import requests
import time

def find_food_places(lat, lon, radius_km=5, dietary_preference=None):
    radius = radius_km * 1000
    overpass_query = f"""
    [out:json];
    (
      node(around:{radius},{lat},{lon})[amenity=restaurant];
      node(around:{radius},{lat},{lon})[amenity=cafe];
    );
    out center;
    """
    url = "http://overpass-api.de/api/interpreter"
    resp = requests.get(url, params={"data": overpass_query})
    if resp.status_code != 200:
        return {"error": "Failed to fetch food places"}
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
    # Optionally filter by dietary_preference if needed
    if dietary_preference:
        filtered = []
        for r in results:
            cuisine = r.get("cuisine", "").lower()
            if dietary_preference.lower() in cuisine or dietary_preference.lower() in str(r["tags"]).lower():
                filtered.append(r)
        results = filtered
    return results[:10]

def main():
    context = ContextStore()
    while True:
        if context.get("hotel_done") and not context.get("food_done"):
            location_result = context.get("location_result")
            dietary_preference = context.get("dietary_preference")
            radius_km = context.get("radius_km", 5)
            food_results = []
            if location_result and "places" in location_result:
                print("[Food] Running food search for all places...")
                for place in location_result["places"]:
                    lat, lon = place["lat"], place["lon"]
                    foods = find_food_places(lat, lon, radius_km, dietary_preference)
                    food_results.append({
                        "place": place,
                        "food_places": foods
                    })
                context.set("food_result", food_results)
                context.set("food_done", True)
                print("[Food] Done.")
            else:
                print("[Food] No places found in location_result.")
        else:
            print("[Food] Waiting for hotel_done or already done...")
        time.sleep(2)

if __name__ == "__main__":
    main()