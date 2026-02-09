import pandas as pd
import numpy as np


def sr_zones(df: pd.DataFrame, lookback: int = 200):
    """
    Build S/R zones and attach strength metrics:
    - touches
    - volume_score
    - age
    - strength (0–100)
    """

    recent = df.tail(lookback).copy()

    highs = recent["high"].nlargest(6).values
    lows  = recent["low"].nsmallest(6).values

    raw_zones = []

    # ---------- Create initial zones ----------

    for h in highs:
        raw_zones.append({
            "type": "resistance",
            "top": float(h),
            "bottom": float(h * 0.998)
        })

    for l in lows:
        raw_zones.append({
            "type": "support",
            "top": float(l * 1.002),
            "bottom": float(l)
        })

    # ---------- Merge overlapping ----------

    zones = merge_zones(raw_zones, overlap_threshold=0.0015)

    # ---------- Strength metrics ----------

    avg_vol = recent["volume"].mean()

    for z in zones:

        touches = 0
        volume_hits = []
        first_touch_idx = None

        for i, row in recent.iterrows():

            price_in_zone = (
                row["low"] <= z["top"] and
                row["high"] >= z["bottom"]
            )

            if price_in_zone:
                touches += 1
                volume_hits.append(row["volume"])

                if first_touch_idx is None:
                    first_touch_idx = i

        # ---- Age (older = stronger) ----
        if first_touch_idx is not None:
            age = len(recent) - recent.index.get_loc(first_touch_idx)
        else:
            age = 0

        # ---- Volume score (normalized) ----
        if volume_hits and avg_vol > 0:
            volume_score = float(np.mean(volume_hits) / avg_vol)
        else:
            volume_score = 0.0

        # ---- Strength synthesis ----
        strength = (
            min(touches, 10) * 5 +      # up to 50 pts
            min(volume_score, 3) * 15 + # up to 45 pts
            min(age / lookback, 1) * 5  # up to 5 pts
        )

        z["touches"] = touches
        z["volume_score"] = round(volume_score, 2)
        z["age"] = int(age)
        z["strength"] = round(min(strength, 100), 1)

    # ---------- Sort by strength (strongest first) ----------

    zones = sorted(zones, key=lambda z: z["strength"], reverse=True)

    return zones


def merge_zones(zones, overlap_threshold=0.0015):

    if not zones:
        return []

    zones = sorted(zones, key=lambda z: z["bottom"])
    merged = [zones[0]]

    for z in zones[1:]:

        last = merged[-1]

        if z["bottom"] <= last["top"] * (1 + overlap_threshold):

            last["top"] = max(last["top"], z["top"])
            last["bottom"] = min(last["bottom"], z["bottom"])

        else:
            merged.append(z)

    return merged
