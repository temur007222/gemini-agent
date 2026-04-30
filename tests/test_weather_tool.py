"""Tests for WeatherTool — geocoding, error paths, mocked HTTP."""

from typing import Any
from unittest.mock import MagicMock

import pytest
import requests

from tools import WeatherTool


@pytest.fixture
def wx() -> WeatherTool:
    return WeatherTool()


def test_empty_city(wx: WeatherTool) -> None:
    out = wx.execute(city="")
    assert out["status"] == "error"


def test_city_not_found(wx: WeatherTool, mocker: Any) -> None:
    """Geocoder returns no results -> structured 'City not found' error."""
    fake_geo = MagicMock()
    fake_geo.json.return_value = {"results": []}
    fake_geo.raise_for_status = MagicMock()
    mocker.patch("tools.weather_tool.requests.get", return_value=fake_geo)

    out = wx.execute(city="Atlantis")
    assert out["status"] == "error"
    assert "Atlantis" in out["error"]
    assert "not found" in out["error"]


def test_network_error_on_geocoding(wx: WeatherTool, mocker: Any) -> None:
    mocker.patch(
        "tools.weather_tool.requests.get",
        side_effect=requests.ConnectionError("offline"),
    )
    out = wx.execute(city="Riga")
    assert out["status"] == "error"
    assert "Geocoding failed" in out["error"]


def test_network_error_on_forecast(wx: WeatherTool, mocker: Any) -> None:
    """Geocoding succeeds, forecast call fails — error must surface clearly."""
    fake_geo = MagicMock()
    fake_geo.json.return_value = {
        "results": [{"name": "Riga", "country": "Latvia", "latitude": 56.95, "longitude": 24.1}]
    }
    fake_geo.raise_for_status = MagicMock()

    def side_effect(url: str, **_kwargs: Any) -> MagicMock:
        if "geocoding" in url:
            return fake_geo
        raise requests.ConnectionError("forecast offline")

    mocker.patch("tools.weather_tool.requests.get", side_effect=side_effect)

    out = wx.execute(city="Riga")
    assert out["status"] == "error"
    assert "Weather fetch failed" in out["error"]


def test_successful_weather_mocked(wx: WeatherTool, mocker: Any) -> None:
    fake_geo = MagicMock()
    fake_geo.json.return_value = {
        "results": [{"name": "Riga", "country": "Latvia", "latitude": 56.95, "longitude": 24.1}]
    }
    fake_geo.raise_for_status = MagicMock()

    fake_wx = MagicMock()
    fake_wx.json.return_value = {
        "current_weather": {"temperature": 12.5, "windspeed": 8.0, "weathercode": 3}
    }
    fake_wx.raise_for_status = MagicMock()

    calls = {"i": 0}

    def side_effect(*_args: Any, **_kwargs: Any) -> MagicMock:
        calls["i"] += 1
        return fake_geo if calls["i"] == 1 else fake_wx

    mocker.patch("tools.weather_tool.requests.get", side_effect=side_effect)

    out = wx.execute(city="Riga")
    assert out["status"] == "success"
    assert out["city"] == "Riga"
    assert out["country"] == "Latvia"
    assert out["temperature_c"] == 12.5
    assert out["wind_kmh"] == 8.0
    assert out["condition"] == "Overcast"


def test_unknown_weathercode_falls_back(wx: WeatherTool, mocker: Any) -> None:
    fake_geo = MagicMock()
    fake_geo.json.return_value = {
        "results": [{"name": "X", "country": "Y", "latitude": 0.0, "longitude": 0.0}]
    }
    fake_geo.raise_for_status = MagicMock()
    fake_wx = MagicMock()
    fake_wx.json.return_value = {
        "current_weather": {"temperature": 0, "windspeed": 0, "weathercode": 9999}
    }
    fake_wx.raise_for_status = MagicMock()

    calls = {"i": 0}

    def side_effect(*_args: Any, **_kwargs: Any) -> MagicMock:
        calls["i"] += 1
        return fake_geo if calls["i"] == 1 else fake_wx

    mocker.patch("tools.weather_tool.requests.get", side_effect=side_effect)

    out = wx.execute(city="X")
    assert out["status"] == "success"
    assert out["condition"] == "Unknown"


def test_declaration_shape(wx: WeatherTool) -> None:
    decl = wx.get_declaration()
    assert decl["name"] == "get_weather"
    assert decl["parameters"]["required"] == ["city"]
