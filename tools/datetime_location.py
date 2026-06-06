"""
Datetime & Location Tool - Get current date, time, and user location.
Uses IP geolocation for location (no API key needed).
"""

import datetime
import requests


def get_datetime_location() -> str:
    """Get current date, time, and approximate location."""
    now = datetime.datetime.now()

    # Format date and time
    date_str = now.strftime("%Y年%m月%d日")
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekdays[now.weekday()]
    time_str = now.strftime("%H:%M:%S")

    result = f"当前时间：{date_str} {weekday} {time_str}"

    # Try to get location via IP geolocation
    try:
        resp = requests.get("http://ip-api.com/json/?lang=zh-CN", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                city = data.get("city", "")
                region = data.get("regionName", "")
                country = data.get("country", "")
                location_parts = [p for p in [region, city] if p]
                location = " ".join(location_parts) if location_parts else country
                result += f"\n所在地区：{location}"
    except Exception:
        pass

    return result


# Tool definition for Claude API
DATETIME_LOCATION_TOOL = {
    "name": "get_datetime_location",
    "description": "Get the current date, time, and user's location. Use when user asks about time, date, day, or where they are.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}
