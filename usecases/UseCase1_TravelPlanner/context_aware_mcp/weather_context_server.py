from context_store import ContextStore
import requests
import time

def get_weather_forecast(lat, lon, start_date=None, end_date=None):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
        "timezone": "auto"
    }
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        return {"error": "Failed to fetch weather"}
    return resp.json()

def main():
    context = ContextStore()
    while True:
        if context.get("location_done") and not context.get("weather_done"):
            location_result = context.get("location_result")
            start_date = context.get("start_date")
            end_date = context.get("end_date")
            weather_results = []
            if not location_result or "places" not in location_result or not location_result["places"]:
                # Fallback: use base city
                lat = context.get("lat")
                lon = context.get("lon")
                if lat and lon:
                    print("[Weather] No places found, using base city for weather.")
                    weather = get_weather_forecast(lat, lon, start_date, end_date)
                    weather_results = [{
                        "place": {"name": context.get("base_city"), "lat": lat, "lon": lon},
                        "weather": weather
                    }]
                    context.set("weather_result", weather_results)
                    context.set("weather_done", True)
                    return
            if location_result and "places" in location_result:
                print("[Weather] Running weather for all places...")
                for place in location_result["places"]:
                    lat, lon = place["lat"], place["lon"]
                    weather = get_weather_forecast(lat, lon, start_date, end_date)
                    weather_results.append({
                        "place": place,
                        "weather": weather
                    })
                context.set("weather_result", weather_results)
                context.set("weather_done", True)
                print("[Weather] Done. Wrote weather_result and set weather_done.")
            else:
                print("[Weather] No places found in location_result.")
        else:
            print("[Weather] Waiting for location_done in context or already done...")
        time.sleep(2)

if __name__ == "__main__":
    main()