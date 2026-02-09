import requests
from datetime import datetime, timedelta, timezone


CAL_URL = "https://economic-calendar-api.vercel.app/api/events"


def fetch_macro_events():

    try:
        r = requests.get(CAL_URL, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    events = []

    for ev in data:

        try:
            # Example fields from API
            name = ev.get("title", "Unknown Event")
            impact = ev.get("impact", "").upper()
            time_str = ev.get("date")

            if not time_str:
                continue

            # Parse time (UTC)
            t = datetime.fromisoformat(time_str.replace("Z", "")).replace(tzinfo=timezone.utc)

            # Only keep big movers
            if impact not in ("HIGH", "MEDIUM"):
                continue

            events.append({
                "name": name,
                "time": t,
                "impact": impact,
                "note": ev.get("forecast", "Macro volatility expected"),
            })

        except Exception:
            continue

    return events


def upcoming_events(within_hours=72):

    now = datetime.now(timezone.utc)
    horizon = now + timedelta(hours=within_hours)

    upcoming = []

    for ev in fetch_macro_events():
        if now <= ev["time"] <= horizon:
            upcoming.append({
                **ev,
                "countdown": ev["time"] - now
            })

    return sorted(upcoming, key=lambda x: x["time"])
