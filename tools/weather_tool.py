"""WeatherTool - current weather via Open-Meteo (free, no API key)."""

from typing import Any, Dict

import requests

from .base_tool import BaseTool


_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

_WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Rain showers", 81: "Heavy rain showers", 82: "Violent rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm",
}


class WeatherTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_weather"

    @property
    def description(self) -> str:
        return "Get current weather (temperature, conditions, wind) for a city."

    def execute(self, city: str) -> Dict[str, Any]:  # type: ignore[override]
        if not isinstance(city, str) or not city.strip():
            return {"status": "error", "error": "city must be a non-empty string"}

        # 1) Geocode
        try:
            geo_params: Dict[str, Any] = {
                "name": city, "count": 1, "language": "en", "format": "json",
            }
            geo = requests.get(_GEOCODE_URL, params=geo_params, timeout=10)
            geo.raise_for_status()
            geo_data = geo.json()
        except requests.RequestException as e:
            return {"status": "error", "error": f"Geocoding failed: {e}"}

        results = geo_data.get("results") or []
        if not results:
            return {"status": "error", "error": f"City '{city}' not found"}
        loc = results[0]
        lat, lon = loc["latitude"], loc["longitude"]

        # 2) Forecast
        try:
            wx = requests.get(
                _FORECAST_URL,
                params={"latitude": lat, "longitude": lon, "current_weather": "true"},
                timeout=10,
            )
            wx.raise_for_status()
            current = wx.json().get("current_weather", {})
        except requests.RequestException as e:
            return {"status": "error", "error": f"Weather fetch failed: {e}"}

        return {
            "status": "success",
            "city": loc.get("name"),
            "country": loc.get("country"),
            "temperature_c": current.get("temperature"),
            "wind_kmh": current.get("windspeed"),
            "condition": _WEATHER_CODES.get(current.get("weathercode"), "Unknown"),
        }

    def get_declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, e.g. 'Riga' or 'Tashkent'",
                    }
                },
                "required": ["city"],
            },
        }
