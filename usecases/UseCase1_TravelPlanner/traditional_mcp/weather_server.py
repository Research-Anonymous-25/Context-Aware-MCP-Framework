from fastmcp import FastMCP
from pydantic import BaseModel
from typing import Optional
import requests
from datetime import date
import time

mcp = FastMCP("WeatherServer")

def get_with_retry(url, params=None, headers=None, max_retries=5, base_sleep=10):
    """
    Helper function to make HTTP GET requests with retries and exponential backoff.
    - Retries up to max_retries times if a request fails or gets a 429 (rate limit).
    - Waits longer after each failure (base_sleep * 2^attempt seconds).
    """
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=headers)
            if resp.status_code == 429:
                wait = base_sleep * (2 ** attempt)
                print(f"[Weather API] 429 Too Many Requests. Sleeping for {wait} seconds (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            print(f"[Weather API] Request failed: {e}. Retrying...")
            wait = base_sleep * (2 ** attempt)
            time.sleep(wait)
    raise Exception("Exceeded max retries for Weather API")

@mcp.tool(
    name="get_weather_forecast",
    description="Get weather forecast for given lat/lon. Optionally accepts start_date and end_date in 'YYYY-MM-DD' format for a date range."
)
async def get_weather_forecast(
    lat: float,
    lon: float,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    url = "https://api.open-meteo.com/v1/forecast"
    if not start_date and not end_date:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": True
        }
        resp = get_with_retry(url, params=params)
        if resp.status_code != 200:
            return {"error": "Failed to fetch weather"}
        data = resp.json()
        return {"weather": data.get("current_weather", {})}
    start = start_date or date.today().isoformat()
    end = end_date or start
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
        "timezone": "auto"
    }
    resp = get_with_retry(url, params=params)
    if resp.status_code != 200:
        return {"error": "Failed to fetch weather"}
    data = resp.json()
    return {
        "daily": data.get("daily", {}),
        "location": {"lat": lat, "lon": lon},
        "start_date": start,
        "end_date": end
    }

if __name__ == "__main__":
    mcp.run()