import pandas as pd
from .levels import completed_levels, swing_levels, confluence
from .volume import same_time_rvol, participation_tag
from .market import classify, relative_strength
from .scoring import score
from .setups import level_break
from .signals import Signal


def scan(provider, cfg: dict, now: pd.Timestamp) -> dict:
    idx_daily = provider.daily(cfg["index_symbol"])
    market = classify(idx_daily, now)
    rows, signals = [], []
    for sym in cfg["universe"]:
        if provider.is_stale(sym, now):
            rows.append({"symbol": sym, "status": "STALE DATA — BLOCKED"})
            continue
        daily, intra = provider.daily(sym), provider.intraday(sym)
        lv = completed_levels(daily, now)
        pool = sorted({round(x, 2) for x in swing_levels(daily, now) + list(lv.values())})
        rvol = same_time_rvol(intra, now, cfg["volume"]["lookback_days"])
        rs = relative_strength(daily, idx_daily, now)
        for c in level_break.detect(intra, lv, now, cfg["timeframe_minutes"], pool, cfg):
            if c["status"] == "INVALIDATED":
                continue  # failed CE ≠ auto PE; PE தனியாக confirm ஆக வேண்டும்
            vol_ok = rvol is not None and rvol >= cfg["volume"]["rvol_pass"]
            if c["status"] == "CONFIRMED" and not vol_ok:
                c["status"] = "WATCH"
            sc = score(c, rvol, rs, market, cfg["score_weights"])
            tags = []
            if len(confluence(lv, c["level"])) > 1:
                tags.append("LEVEL CONFLUENCE")
            tags.append(participation_tag(rvol, cfg["volume"]))
            rows.append({"symbol": sym, **c, "rvol": rvol, "rs": rs, "score": sc, "tags": tags})
            if c["status"] == "CONFIRMED":
                signals.append(Signal(sym, c["direction"], c["setup"], c["level_name"],
                                      c["entry_zone"], c["sl"], tuple(c["targets"]),
                                      str(c["break_time"]), str(now), c["price"], sc,
                                      tuple([f"{c['level_name']} break", *tags])))
    ranked = sorted([r for r in rows if "score" in r], key=lambda r: -r["score"])
    return {
        "market": market, "time": now,
        "ce": [r for r in ranked if r["direction"] == "CE"][:5],
        "pe": [r for r in ranked if r["direction"] == "PE"][:5],
        "blocked": [r for r in rows if "score" not in r],
        "signals": signals,
    }
