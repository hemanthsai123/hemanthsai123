#!/usr/bin/env python3
"""Market agent: observe -> reason -> brief.

Tools read the same JSON the visuals use. A rules engine always produces a brief;
if USE_LLM=1 and an Ollama server is reachable, llama3.2 rewrites it, constrained
to the computed facts (it may not add numbers). Output: data/brief.json

    python agent/market_agent.py
    USE_LLM=1 OLLAMA_MODEL=llama3.2 python agent/market_agent.py
"""
import json
import os
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT / "scripts"))
from build_visuals import inr, sgn  # noqa: E402


def load(name):
    p = DATA / name
    return json.loads(p.read_text()) if p.exists() else None


# ------------------------------------------------------------------ tools
def tool_breadth(m):
    b = m["breadth"]
    tot = b["up"] + b["down"]
    return {"up": b["up"], "down": b["down"], "ratio": b["up"] / tot if tot else 0.5}


def tool_sectors(m):
    s = sorted(m["sectors"], key=lambda x: -x["d"])
    return {"leaders": s[:3], "laggards": s[-2:][::-1],
            "month_best": max(m["sectors"], key=lambda x: x["m"]),
            "month_worst": min(m["sectors"], key=lambda x: x["m"])}


def tool_breadth_of_trend(m):
    idx = {i["key"]: i for i in m["indices"]}
    return {"nifty_m": m["hero"]["month_pct"], "mid_m": idx["mid"]["month_pct"], "small_m": idx["small"]["month_pct"]}


def tool_derivs(m):
    return m["derivs"]


# ------------------------------------------------------------------ rules engine
def rules(m):
    h, br, sec = m["hero"], tool_breadth(m), tool_sectors(m)
    tr, dv = tool_breadth_of_trend(m), tool_derivs(m)
    vix = next(i for i in m["indices"] if i["key"] == "vix")
    tone = "broad rally" if br["ratio"] > 0.55 else "broad sell-off" if br["ratio"] < 0.45 else "mixed session"
    lead = ", ".join(s["n"] for s in sec["leaders"])
    headline = f"Nifty {sgn(h['pct'])}% to {h['close']:,.2f}: {tone}, led by {lead}"
    bullets = [
        f"Breadth: {inr(br['up'])} stocks up vs {inr(br['down'])} down; India VIX {vix['close']:.2f} ({sgn(vix['pct'])}%).",
        "Leaders: " + ", ".join(f"{s['n']} {sgn(s['d'])}%" for s in sec["leaders"])
        + ". Laggards: " + ", ".join(f"{s['n']} {sgn(s['d'])}%" for s in sec["laggards"]) + ".",
    ]
    if tr["nifty_m"] > 0 and (tr["mid_m"] < 0 or tr["small_m"] < 0):
        bullets.append(
            f"Narrow month: Nifty {sgn(tr['nifty_m'])}% but Midcap 100 {sgn(tr['mid_m'])}% and Smallcap 100 {sgn(tr['small_m'])}%; "
            f"{sec['month_best']['n']} {sgn(sec['month_best']['m'], 1)}% is doing the lifting, {sec['month_worst']['n']} {sgn(sec['month_worst']['m'], 1)}% lags.")
    else:
        bullets.append(f"Month so far: Nifty {sgn(tr['nifty_m'])}%, Midcap 100 {sgn(tr['mid_m'])}%, Smallcap 100 {sgn(tr['small_m'])}%.")
    bullets.append(
        f"Derivatives: FIIs net short {inr(abs(dv['fii_net_fut']))} index futures ({dv['fii_short_pct']}% short). "
        f"Nifty PCR {dv['pcr']} for {dv['expiry']} expiry; heaviest OI at {inr(dv['max_put'])} puts / {inr(dv['max_call'])} calls. "
        f"F&O ban: {', '.join(dv['ban']) or 'none'}.")
    return headline, bullets


# ------------------------------------------------------------------ optional LLM pass
def llm_rewrite(headline, bullets):
    url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    prompt = ("Rewrite this Indian market brief as one headline line and exactly 4 bullet lines, plain text, "
              "each under 160 characters. Use ONLY the numbers given. No advice, no predictions.\n\n"
              f"HEADLINE: {headline}\n" + "\n".join(f"- {b}" for b in bullets))
    req = urllib.request.Request(url + "/api/generate", method="POST",
                                 data=json.dumps({"model": model, "prompt": prompt, "stream": False}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        text = json.loads(r.read())["response"]
    lines = [ln.strip(" -鈥�*\t") for ln in text.splitlines() if ln.strip()]
    if len(lines) != 5 or any(len(ln) > 170 for ln in lines):
        raise ValueError("unexpected LLM shape")
    allowed = set("".join(c for c in (headline + " ".join(bullets)) if c.isdigit() or c in ".,"))
    if not set("".join(c for c in " ".join(lines) if c.isdigit())) <= allowed:
        raise ValueError("LLM introduced digits")
    return lines[0], lines[1:], f"Ollama 路 {model}"


def main():
    m = load("market.json")
    headline, bullets = rules(m)
    engine = "Rules engine"
    if os.getenv("USE_LLM") == "1":
        try:
            headline, bullets, engine = llm_rewrite(headline, bullets)
        except Exception as exc:  # fall back silently to the deterministic brief
            print("LLM skipped:", exc)
    out = {"asof": m["asof"], "asof_label": m["asof_label"], "engine": engine,
           "headline": headline, "bullets": bullets}
    (DATA / "brief.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(headline)
    for b in bullets:
        print(" -", b)


if __name__ == "__main__":
    main()
