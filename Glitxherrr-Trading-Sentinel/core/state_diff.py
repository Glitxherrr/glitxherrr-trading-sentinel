def diff_market_state(prev: dict | None, curr: dict) -> dict:

    if not prev:
        return {"note": "No previous snapshot"}

    diffs = {}

    def compare(path, label):
        p = prev
        c = curr

        for k in path:
            if not isinstance(p, dict) or not isinstance(c, dict):
                return
            p = p.get(k)
            c = c.get(k)

        if p != c:
            diffs[label] = {"before": p, "now": c}

    # ================= BTC =================

    compare(["btc", "structure", "trend"], "BTC structure trend")
    compare(["btc", "structure", "state"], "BTC structure state")
    compare(["btc", "structure", "liquidity_sweep"], "BTC sweep")
    compare(["btc", "structure", "break_of_structure"], "BTC BOS")

    compare(["btc", "bias", "htf"], "BTC HTF bias")
    compare(["btc", "bias", "ltf"], "BTC LTF bias")

    compare(["btc", "momentum", "bb_squeeze"], "BTC compression")
    compare(["btc", "momentum", "vol_spike"], "BTC volume spike")

    # ================= PAXG =================

    compare(["paxg", "structure", "trend"], "Gold structure trend")
    compare(["paxg", "structure", "state"], "Gold structure state")
    compare(["paxg", "structure", "liquidity_sweep"], "Gold sweep")
    compare(["paxg", "structure", "break_of_structure"], "Gold BOS")

    # ================= DXY =================

    compare(["dxy", "structure", "trend"], "DXY structure trend")
    compare(["dxy", "structure", "state"], "DXY structure state")
    compare(["dxy", "structure", "liquidity_sweep"], "DXY sweep")
    compare(["dxy", "structure", "break_of_structure"], "DXY BOS")

    compare(["dxy", "trend"], "DXY trend")
    compare(["dxy", "strength"], "DXY strength")

    return diffs
