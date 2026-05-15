"""Consulta del tiempo usando la API pública wttr.in."""

from __future__ import annotations

import aiohttp


async def get_weather(city: str) -> str:
    url = f"https://wttr.in/{city}?format=j1&lang=es"
    async with (
        aiohttp.ClientSession() as session,
        session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp,
    ):
        if resp.status == 404:
            return f"❌ Ciudad *{city}* no encontrada"
        if resp.status != 200:
            return f"❌ Error {resp.status} consultando el tiempo"
        data = await resp.json(content_type=None)

    cur = data["current_condition"][0]

    area = data.get("nearest_area", [{}])[0]
    area_name = area.get("areaName", [{"value": city}])[0].get("value", city)
    country = area.get("country", [{"value": ""}])[0].get("value", "")
    location = f"{area_name}, {country}" if country else area_name

    desc_list = cur.get("lang_es") or cur.get("weatherDesc") or [{"value": ""}]
    desc = desc_list[0].get("value", "")
    temp_c = cur.get("temp_C", "?")
    feels_c = cur.get("FeelsLikeC", "?")
    humidity = cur.get("humidity", "?")
    wind_kmh = cur.get("windspeedKmph", "?")

    lines = [
        f"🌤️ *{location}*",
        desc,
        f"🌡️ {temp_c}°C (sensación {feels_c}°C)",
        f"💧 Humedad: {humidity}%  |  🌬️ Viento: {wind_kmh} km/h",
    ]

    forecast = data.get("weather", [])[:3]
    if forecast:
        lines.append("\n📅 *Previsión (3 días):*")
        for day in forecast:
            date = day.get("date", "")
            max_c = day.get("maxtempC", "?")
            min_c = day.get("mintempC", "?")
            hourly = day.get("hourly", [])
            midday = next(
                (h for h in hourly if h.get("time") == "1200"), hourly[0] if hourly else {}
            )
            day_desc_list = midday.get("lang_es") or midday.get("weatherDesc") or [{"value": ""}]
            day_desc = day_desc_list[0].get("value", "")
            lines.append(f"`{date}` {day_desc}  {min_c}°C → {max_c}°C")

    return "\n".join(lines)
