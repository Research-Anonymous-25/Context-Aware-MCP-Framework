from context_store import ContextStore
import requests
import time

def find_hotels_nearby(lat, lon, radius=5000):
    query = f"""
    [out:json][timeout:25];
    (
      node["tourism"~"hotel|hostel|guest_house"](around:{radius},{lat},{lon});
      way["tourism"~"hotel|hostel|guest_house"](around:{radius},{lat},{lon});
      relation["tourism"~"hotel|hostel|guest_house"](around:{radius},{lat},{lon});
    );
    out center tags;
    """
    response = requests.get("https://overpass-api.de/api/interpreter", params={'data': query})
    if response.status_code != 200:
        return {"error": "Failed to fetch hotels"}
    data = response.json()
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
    return results[:10]

def main():
    context = ContextStore()
    while True:
        if context.get("weather_done") and not context.get("hotel_done"):
            location_result = context.get("location_result")
            budget = context.get("budget")
            guests = context.get("guests")
            hotel_results = []
            if location_result and "places" in location_result:
                print("[Hotel] Running hotel search for all places...")
                for place in location_result["places"]:
                    lat, lon = place["lat"], place["lon"]
                    hotels = find_hotels_nearby(lat, lon)
                    hotel_results.append({
                        "place": place,
                        "hotels": hotels,
                        "budget": budget,
                        "guests": guests
                    })
                context.set("hotel_result", hotel_results)
                context.set("hotel_done", True)
                print("[Hotel] Done. Wrote hotel_result and set hotel_done.")
            else:
                print("[Hotel] No places found in location_result.")
        else:
            print("[Hotel] Waiting for weather_done in context or already done...")
        time.sleep(2)

if __name__ == "__main__":
    main()