#!/usr/bin/env python3
"""Compact NSE screener -> data/screens_live.json

Criteria (all computed from daily OHLCV):
  highs     close within 0.5% of the 52-week closing high
  volume    today's volume >= 2x the 20-session average
  momentum  RSI(14, Wilder) in 55-75 and close > EMA20 > EMA50

    python screener/screener.py          # live, needs: pip install yfinance pandas numpy
    python screener/screener.py --demo   # synthetic data, no network
"""
import json
import pathlib
import sys
from datetime import date

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
UNIVERSE = (
    "RELIANCE HDFCBANK ICICIBANK INFY TCS BHARTIARTL ITC SBIN LT KOTAKBANK AXISBANK BAJFINANCE HINDUNILVR "
    "MARUTI SUNPHARMA TITAN ULTRACEMCO ASIANPAINT NTPC POWERGRID ONGC TATASTEEL JSWSTEEL HCLTECH WIPRO TECHM "
    "ADANIENT ADANIPORTS COALINDIA HINDALCO DIVISLAB CIPLA DRREDDY EICHERMOT HEROMOTOCO BAJAJ-AUTO M&M NESTLEIND "
    "BRITANNIA GRASIM APOLLOHOSP INDUSINDBK SBILIFE HDFCLIFE SHRIRAMFIN TRENT BEL ETERNAL TMPV"
).split()


def rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def snap(df):
    c, v = df["Close"], df["Volume"]
    last = c.iloc[-1]
    return {
        "price": float(last),
        "chg": float((last / c.iloc[-2] - 1) * 100),
        "rsi": float(rsi(c).iloc[-1]),
        "ema20": float(ema(c, 20).iloc[-1]),
        "ema50": float(ema(c, 50).iloc[-1]),
        "gap52": float((last / c.tail(252).max() - 1) * 100),
        "vx": float(v.iloc[-1] / v.iloc[-21:-1].mean()) if v.iloc[-21:-1].mean() else 0.0,
    }


def run(frames):
    rows = {}
    for sym, df in frames.items():
        try:
            df = df.dropna()
            if len(df) >= 60:
                rows[sym] = snap(df)
        except Exception as exc:
            print("skip", sym, exc)
    highs = sorted((s for s, r in rows.items() if r["gap52"] >= -0.5), key=lambda s: -rows[s]["chg"])
    vol = sorted((s for s, r in rows.items() if r["vx"] >= 2), key=lambda s: -rows[s]["vx"])
    mom = sorted((s for s, r in rows.items()
                  if 55 <= r["rsi"] <= 75 and r["price"] > r["ema20"] > r["ema50"]), key=lambda s: -rows[s]["rsi"])
    return {
        "highs": [{"sym": s, "price": round(rows[s]["price"], 2), "chg": round(rows[s]["chg"], 2)} for s in highs[:6]],
        "volume": [{"sym": s, "x": round(rows[s]["vx"], 1), "chg": round(rows[s]["chg"], 2)} for s in vol[:6]],
        "momentum": [{"sym": s, "chg": round(rows[s]["chg"], 2), "rsi": round(rows[s]["rsi"], 1)} for s in mom[:6]],
        "scanned": len(rows),
    }


def demo_frames(seed=7):
    rng = np.random.default_rng(seed)
    out = {}
    for i, sym in enumerate(UNIVERSE):
        r = rng.normal(0.0006 + (i % 5) * 0.0002, 0.015, 300)
        close = 100 * np.exp(np.cumsum(r))
        vol = rng.integers(8e5, 2e6, 300).astype(float)
        if i % 9 == 0:
            vol[-1] *= 3.5
        out[sym] = pd.DataFrame({"Close": close, "Volume": vol})
    return out


def live_frames():
    import yfinance as yf  # imported lazily so --demo needs no network libs
    out = {}
    for sym in UNIVERSE:
        try:
            out[sym] = yf.Ticker(sym + ".NS").history(period="14mo", auto_adjust=False)[["Close", "Volume"]]
        except Exception as exc:
            print("fetch failed", sym, exc)
    return out


def main():
    demo = "--demo" in sys.argv
    res = run(demo_frames() if demo else live_frames())
    if not res["scanned"]:
        print("nothing scanned; leaving previous screens in place")
        return 0
    res["asof"] = ("demo data" if demo else date.today().isoformat())
    (ROOT / "data").mkdir(exist_ok=True)
    out = ROOT / "data" / ("screens_demo.json" if demo else "screens_live.json")
    out.write_text(json.dumps(res, indent=2))
    print(f"scanned {res['scanned']} | highs {len(res['highs'])} | volume {len(res['volume'])} | momentum {len(res['momentum'])} -> {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
