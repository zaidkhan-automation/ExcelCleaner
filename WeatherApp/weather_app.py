
# weather_app.py
"""
Simple Weather App (CLI)
Usage:
  python weather_app.py            # interactive prompts
  python weather_app.py -c London  # use env var OWM_API_KEY or you'll be asked
  python weather_app.py -c "New Delhi" -k YOUR_API_KEY

Install requests: pip install requests
Get a free API key at https://openweathermap.org
"""
import argparse
import requests
from datetime import datetime

API_URL = "https://api.openweathermap.org/data/2.5/weather"

def get_weather(city: str, api_key: str, units: str = "metric"):
    params = {"q": city, "appid": api_key, "units": units}
    resp = requests.get(API_URL, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def ts_to_local(t):
    return datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S") if t else "N/A"

def format_weather(data: dict) -> str:
    name = data.get("name", "N/A")
    country = data.get("sys", {}).get("country", "")
    desc = data.get("weather", [{}])[0].get("description", "N/A").title()
    main = data.get("main", {})
    temp = main.get("temp", "N/A")
    feels = main.get("feels_like", "N/A")
    humidity = main.get("humidity", "N/A")
    wind = data.get("wind", {}).get("speed", "N/A")
    sunrise = data.get("sys", {}).get("sunrise")
    sunset = data.get("sys", {}).get("sunset")

    lines = [
        f"Weather for: {name}, {country}",
        f"Condition : {desc}",
        f"Temperature: {temp} °C (feels like {feels} °C)",
        f"Humidity  : {humidity}%",
        f"Wind speed: {wind} m/s",
        f"Sunrise   : {ts_to_local(sunrise)}",
        f"Sunset    : {ts_to_local(sunset)}",
    ]
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Simple Weather App (OpenWeatherMap)")
    parser.add_argument("-c", "--city", help="City name (e.g. Delhi, London)", default=None)
    parser.add_argument("-k", "--key", help="OpenWeatherMap API key (optional if env var OWM_API_KEY set)", default=None)
    parser.add_argument("-u", "--units", help="units: metric or imperial", default="metric")
    args = parser.parse_args()

    city = args.city or input("Enter city name (e.g. Delhi, London): ").strip()
    key = args.key or (__import__("os").environ.get("OWM_API_KEY"))
    if not key:
        key = input("Enter your OpenWeatherMap API key: ").strip()

    if not city or not key:
        print("City and API key are required. Get a free key at https://openweathermap.org")
        return

    try:
        data = get_weather(city, key, units=args.units)
        print(format_weather(data))
    except requests.HTTPError as he:
        code = he.response.status_code if he.response else None
        if code == 401:
            print("Error 401: Unauthorized — check your API key.")
        elif code == 404:
            print("Error 404: City not found — check the city name.")
        else:
            print("HTTP error:", he)
    except requests.RequestException as e:
        print("Network error or timeout:", e)
    except Exception as e:
        print("Unexpected error:", e)

if __name__ == "__main__":
    main()