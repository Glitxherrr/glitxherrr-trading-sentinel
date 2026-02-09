import json
from pathlib import Path
from datetime import datetime
import pytz

SNAPSHOT_FILE = Path("snapshot_memory.json")

IST = pytz.timezone("Asia/Kolkata")


# -------- LOAD SNAPSHOT --------

def load_snapshot():
    if SNAPSHOT_FILE.exists():
        try:
            return json.loads(SNAPSHOT_FILE.read_text())
        except Exception:
            return None
    return None


# -------- SAVE SNAPSHOT (IST TIME) --------

def save_snapshot(state: dict):
    payload = {
        "timestamp": datetime.now(IST).isoformat(),
        "state": state
    }

    try:
        SNAPSHOT_FILE.write_text(json.dumps(payload, indent=2))
    except Exception:
        pass


# -------- PRETTY TIME FOR UI --------

def format_ist_time(iso_time: str):
    if not iso_time:
        return None

    try:
        dt = datetime.fromisoformat(iso_time)

        if dt.tzinfo is None:
            dt = IST.localize(dt)

        dt_ist = dt.astimezone(IST)

        return dt_ist.strftime("%d %b %Y, %I:%M %p IST")

    except Exception:
        return iso_time
