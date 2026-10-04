"""KRT Terminal — Phase 1 CLI scanner.
Usage: python main.py --at "2026-10-01 11:15"
"""
import argparse
import pandas as pd
from krt.config import load_settings, ROOT
from krt.data.csv_provider import CSVProvider
from krt.scanner import scan
from krt.signals import SignalLog


def fmt(r):
    t = "/".join(str(x) for x in r["targets"]) or "-"
    return (f"  {r['symbol']:<11}{r['level_name']:<5}{r['level']:>10}  px {r['price']:>9}  "
            f"RVOL {r['rvol'] or '-':>5}  score {r['score']:>3}  SL {r['sl']:>9}  T {t:<26} {r['status']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", required=True, help="scan time, e.g. '2026-10-01 11:15'")
    a = ap.parse_args()
    cfg = load_settings()
    now = pd.Timestamp(a.at)
    res = scan(CSVProvider(ROOT / "data" / "sample"), cfg, now)
    log = SignalLog(ROOT / "logs" / "signals.jsonl")

    print(f"\n KRT TERMINAL  |  {now}  |  MARKET: {res['market']}")
    print(" " + "━" * 100)
    for side, label in (("ce", "🟢 TOP CE CANDIDATES"), ("pe", "🔴 TOP PE CANDIDATES")):
        print(f"\n {label}")
        print("\n".join(fmt(r) for r in res[side]) or "  NO CONFIRMED SETUP")
    for b in res["blocked"]:
        print(f"  ⚠ {b['symbol']}: {b['status']}")
    new = [s for s in res["signals"] if log.add(s)]
    print(f"\n New signals logged: {len(new)}  →  logs/signals.jsonl")
    if not res["signals"]:
        print(" WAIT — நல்ல setup இல்லை.")
    print("\n ⚠ Rule-based scanner. Profit / accuracy guarantee இல்லை. Not investment advice.\n")


if __name__ == "__main__":
    main()
