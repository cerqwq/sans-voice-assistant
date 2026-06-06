"""
Weather Tool - Get weather data using wttr.in (free, no API key).
Optional: OpenWeatherMap API support.
"""

import requests
from typing import Optional

# Optional: OpenWeatherMap API key (set to use OWM instead of wttr.in)
OPENWEATHER_API_KEY = None  # Set your key here or via environment variable


def get_weather(city: str, days: int = 1) -> str:
    """
    Get weather information for a city using wttr.in (free, no API key).

    Args:
        city: City name (e.g., 'Beijing', 'New York', 'Tokyo')
        days: Number of forecast days (1-3)

    Returns:
        Human-readable weather summary string
    """
    try:
        headers = {"User-Agent": "curl/8.0"}

        # Get JSON data
        url = f"https://wttr.in/{requests.utils.quote(city)}?format=j1"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Current conditions
        current = data["current_condition"][0]
        temp_c = current["temp_C"]
        temp_f = current["temp_F"]
        humidity = current["humidity"]
        wind_kmph = current["windspeedKmph"]
        desc = current["weatherDesc"][0]["value"]
        feels_c = current["FeelsLikeC"]

        result = (
            f"Weather in {city}:\n"
            f"  Condition: {desc}\n"
            f"  Temperature: {temp_c}C ({temp_f}F), feels like {feels_c}C\n"
            f"  Humidity: {humidity}%\n"
            f"  Wind: {wind_kmph} km/h"
        )

        # Forecast
        if days > 1:
            result += "\n\nForecast:\n"
            for day in data["weather"][:days]:
                date = day["date"]
                max_t = day["maxtempC"]
                min_t = day["mintempC"]
                day_desc = day["hourly"][4]["weatherDesc"][0]["value"]
                result += f"  {date}: {min_t}C - {max_t}C, {day_desc}\n"

        return result.strip()

    except requests.RequestException as e:
        return f"Weather service error: {e}"
    except (KeyError, IndexError) as e:
        return f"Failed to parse weather data: {e}"


def get_weather_compact(city: str) -> str:
    """Get a one-line weather summary."""
    try:
        headers = {"User-Agent": "curl/8.0"}
        resp = requests.get(
            f"https://wttr.in/{requests.utils.quote(city)}?format=3",
            headers=headers,
            timeout=10,
        )
        return resp.text.strip()
    except Exception as e:
        return f"Weather error: {e}"


def get_weather_owm(city: str, units: str = "metric") -> str:
    """
    Get weather from OpenWeatherMap (requires free API key).
    Set OPENWEATHER_API_KEY at the top of this file.
    """
    if not OPENWEATHER_API_KEY:
        return "OpenWeatherMap API key not configured. Using wttr.in instead."

    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": units,
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        temp = data["main"]["temp"]
        feels = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        desc = data["weather"][0]["description"]
        wind = data["wind"]["speed"]
        unit_sym = "C" if units == "metric" else "F"

        return (
            f"Weather in {city}: {desc}\n"
            f"Temperature: {temp}{unit_sym} (feels like {feels}{unit_sym})\n"
            f"Humidity: {humidity}%, Wind: {wind} m/s"
        )
    except Exception as e:
        return f"Weather error: {e}"


# Claude API tool definition
WEATHER_TOOL = {
    "name": "get_weather",
    "description": (
        "Get current weather and forecast for a city. Use when the user asks "
        "about weather, temperature, rain, forecast, or 'should I bring an umbrella'. "
        "Uses wttr.in service (free, no API key). Supports any city worldwide."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "City name, e.g. 'Beijing', 'New York', 'Tokyo'",
            },
            "days": {
                "type": "integer",
                "description": "Forecast days (1-3, default 1)",
                "default": 1,
            },
        },
        "required": ["city"],
    },
}
