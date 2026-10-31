#!/usr/bin/env python3
"""Refresh headline indices + the Nifty sparkline in data/market.json from Yahoo Finance.

Sector and breadth sections stay on the last exchange end-of-day snapshot (see README).
Fails soft: on any error the existing snapshot is left untouched and exit code is 0.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "market.json"
TICKERS = {"bank": "^NSEBANK", "vix": "^INDIAVIX"}


def hist(sym):
    import yfinance as yf
    h = yf.Ticker(sym).history(period="1mo", auto_adjust=False)["Close"].dropna()
    if len(h) < 2:
        raise ValueError(f"no data for {sym}")
    return h


def main():
    m = json.loads(P.read_text())
    try:
        n = hist("^NSEI")
        last, prev = float(n.iloc[-1]), float(n.iloc[-2])
        m["hero"].update(close=round(last, 2), points=round(last - prev, 2), pct=round((last / prev - 1) * 100, 2))
        m["series"] = [{"d": f"{d.day} {d.strftime('%b')}", "c": round(float(c), 2)} for d, c in n.tail(7).items()]
        d = n.index[-1]
        m["asof"] = d.strftime("%Y-%m-%d")
        m["asof_label"] = d.strftime("%a %d %b %Y")
        m["source"] = "Yahoo Finance via yfinance (delayed); sectors and breadth from NSE end-of-day files"
        for item in m["indices"]:
            sym = TICKERS.get(item["key"])
            if sym:
                try:
                    s = hist(sym)
                    item["close"] = round(float(s.iloc[-1]), 2)
                    item["pct"] = round((float(s.iloc[-1]) / float(s.iloc[-2]) - 1) * 100, 2)
                except Exception as exc:
                    print("kept snapshot for", item["name"], "-", exc)
        P.write_text(json.dumps(m, indent=2, ensure_ascii=False))
        print("updated", m["asof_label"], m["hero"]["close"])
    except Exception as exc:
        print("fetch skipped, snapshot kept:", exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
