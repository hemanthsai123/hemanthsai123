#!/usr/bin/env python3
"""Render the profile visuals (SVG) from data/*.json. Pure stdlib.

    python scripts/build_visuals.py
"""
import html
import json
import pathlib
import textwrap

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, OUT = ROOT / "data", ROOT / "assets"

# dataviz palette (dark surface): blue = up, red = down, gray midpoint; text stays in ink tokens
S, INK, INK2, MUT, GRID = "#1a1a19", "#f0efec", "#c3c2b7", "#898781", "#2c2c2a"
UP, DN, WARN = "#3987e5", "#e66767", "#fab219"
FONT = 'system-ui,-apple-system,"Segoe UI",Roboto,sans-serif'
CSS = (
    "@keyframes draw{from{stroke-dashoffset:1200}}"
    "@keyframes pulse{50%{opacity:.25}}"
    "@keyframes rise{from{opacity:0;transform:translateY(6px)}}"
    "@keyframes scroll{to{transform:translateX(-50%)}}"
    "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
)


def e(s):
    return html.escape(str(s), quote=True)


def col(x):
    return UP if x >= 0 else DN


def arrow(x):
    return "▲" if x >= 0 else "▼"


def sgn(x, d=2):
    return f"{x:+.{d}f}".replace("-", "−")


def num(x, d=2):
    return f"{x:,.{d}f}"


def inr(n):
    s = str(abs(int(n)))
    if len(s) > 3:
        head, tail, parts = s[:-3], s[-3:], []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return ("−" if n < 0 else "") + s


def T(x, y, s, size=13, fill=INK2, weight=400, anchor="start", extra=""):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'text-anchor="{anchor}" {extra}>{e(s)}</text>')


def bar(x0, y, w, h, r=3):
    """Horizontal bar from baseline x0; square at the baseline, rounded data-end."""
    if abs(w) < 0.5:
        return ""
    a = abs(w)
    r = min(r, a, h / 2)
    if w > 0:
        d = f"M{x0},{y} h{a-r:.1f} a{r},{r} 0 0 1 {r},{r} v{h-2*r:.1f} a{r},{r} 0 0 1 {-r},{r} H{x0} z"
    else:
        d = f"M{x0},{y} h{-(a-r):.1f} a{r},{r} 0 0 0 {-r},{r} v{h-2*r:.1f} a{r},{r} 0 0 0 {r},{r} H{x0} z"
    return d


def wrap(w, h, body, title, desc):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-labelledby="t d"><title id="t">{e(title)}</title><desc id="d">{e(desc)}</desc>'
        f"<style>text{{font-family:{FONT}}}{CSS}</style>"
        f'<rect width="{w}" height="{h}" rx="16" fill="{S}"/>'
        f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="15.5" fill="none" stroke="#fff" stroke-opacity=".10"/>'
        f"{body}</svg>"
    )


def header(label, right, w=900):
    return (T(32, 40, label, 12, MUT, 600, extra='letter-spacing="1.6"')
            + f'<circle cx="{w-32-8}" cy="36" r="4" fill="{UP}" style="animation:pulse 2s infinite"/>'
            + T(w - 52, 40, right, 12, MUT, 400, "end"))


# ---------------------------------------------------------------- banner
def banner(m):
    ticks = [f"NIFTY 50 {num(m['hero']['close'])} {arrow(m['hero']['pct'])} {sgn(m['hero']['pct'])}%"]
    ticks += [f"{i['name'].upper()} {num(i['close'])} {arrow(i['pct'])} {sgn(i['pct'])}%" for i in m["indices"]]
    strip = "      ·      ".join(ticks) + "      ·      "
    ser = m["series"]
    lo, hi = min(p["c"] for p in ser), max(p["c"] for p in ser)
    pts = [(560 + i * (310 / (len(ser) - 1)), 150 - (p["c"] - lo) / (hi - lo) * 80) for i, p in enumerate(ser)]
    path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    body = (
        T(40, 84, "Sai", 46, INK, 700, extra='style="animation:rise .8s both"')
        + T(40, 120, "Indian markets · Python · AI agents", 18, INK2,
            extra='style="animation:rise .8s .15s both"')
        + T(40, 150, "Screeners, strategies and an AI market agent for NSE.", 14, MUT,
            extra='style="animation:rise .8s .3s both"')
        + f'<path d="{path}" fill="none" stroke="{UP}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
          f'stroke-dasharray="1200" style="animation:draw 2.4s ease-out"/>'
        + f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="5" fill="{UP}" stroke="{S}" stroke-width="2"/>'
        + f'<line x1="0" x2="900" y1="188" y2="188" stroke="{GRID}"/>'
        + '<clipPath id="c"><rect x="0" y="190" width="900" height="30"/></clipPath>'
        + f'<g clip-path="url(#c)"><g style="animation:scroll 40s linear infinite">'
          f'<text y="209" font-size="12" fill="{MUT}" xml:space="preserve">{e(strip * 4)}</text></g></g>'
    )
    return wrap(900, 220, body, "Sai — Indian markets, Python and AI agents",
                "Animated profile banner with a Nifty 50 sparkline and index ticker")


# ---------------------------------------------------------------- market board
def board(m):
    h = m["hero"]
    ser = m["series"]
    lo, hi = min(p["c"] for p in ser), max(p["c"] for p in ser)
    x0, x1, y0, y1 = 420, 840, 74, 160
    pts = [(x0 + i * (x1 - x0) / (len(ser) - 1), y1 - (p["c"] - lo) / (hi - lo) * (y1 - y0)) for i, p in enumerate(ser)]
    path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    body = header("NSE MARKET BOARD", f"{m['session']} · {m['asof_label']}")
    body += T(32, 82, h["name"], 14, INK2)
    body += T(32, 138, num(h["close"]), 54, INK, 600)
    body += T(32, 168, f"{arrow(h['pct'])} {sgn(h['points'])}  ({sgn(h['pct'])}%)", 16, col(h["pct"]), 600)
    body += T(32 + 190, 168, f"October so far {sgn(h['month_pct'])}%", 13, MUT)
    for gy in (y0, (y0 + y1) / 2, y1):
        body += f'<line x1="{x0}" x2="{x1}" y1="{gy}" y2="{gy}" stroke="{GRID}"/>'
    body += f'<path d="{path}" fill="none" stroke="{UP}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1200" style="animation:draw 2s ease-out"/>'
    ex, ey = pts[-1]
    body += f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="5" fill="{UP}" stroke="{S}" stroke-width="2"/>'
    body += T(ex - 10, ey - 12, num(ser[-1]["c"], 0), 12, INK, 600, "end")
    body += T(x0, y1 + 20, ser[0]["d"], 11, MUT) + T(x1, y1 + 20, ser[-1]["d"], 11, MUT, 400, "end")
    body += T(x0, y0 - 10, f"Last {len(ser)} sessions · closes", 11, MUT)
    tiles = m["indices"][:5]
    tw, gap = 157, 12
    for i, t in enumerate(tiles):
        tx = 32 + i * (tw + gap)
        body += f'<rect x="{tx}" y="206" width="{tw}" height="66" rx="10" fill="#fff" fill-opacity=".04"/>'
        body += T(tx + 14, 228, t["name"], 12, MUT)
        body += T(tx + 14, 250, num(t["close"]), 17, INK, 600)
        body += T(tx + 14, 265, f"{arrow(t['pct'])} {sgn(t['pct'])}%", 12, col(t["pct"]), 600)
    b = m["breadth"]
    tot = b["up"] + b["down"] + b["flat"]
    bw, gx = 836, 2
    wu, wd = (bw - 2 * gx) * b["up"] / tot, (bw - 2 * gx) * b["down"] / tot
    wf = bw - 2 * gx - wu - wd
    body += T(32, 300, f"Breadth · {inr(tot)} NSE stocks", 12, MUT)
    body += T(868, 300, f"{inr(b['up'])} up · {inr(b['down'])} down · {inr(b['flat'])} unchanged", 12, INK2, 400, "end")
    body += (f'<rect x="32" y="308" width="{wu:.1f}" height="8" rx="4" fill="{UP}"/>'
             f'<rect x="{32+wu+gx:.1f}" y="308" width="{wd:.1f}" height="8" rx="4" fill="{DN}"/>'
             f'<rect x="{32+wu+wd+2*gx:.1f}" y="308" width="{max(wf,2):.1f}" height="8" rx="4" fill="{MUT}"/>')
    return wrap(900, 340, body, f"NSE market board, {m['asof_label']}",
                f"Nifty 50 closed {num(h['close'])}, {sgn(h['pct'])} percent. Breadth {b['up']} up, {b['down']} down.")


# ---------------------------------------------------------------- sector heatmap
def heatmap(m):
    rows = sorted(m["sectors"], key=lambda s: -s["d"])
    rh, top = 24, 96
    h = top + len(rows) * rh + 44
    za, sa = 330, 30     # day panel: zero line x, px per %
    zb, sb = 690, 9      # month panel
    body = header("SECTOR ROTATION", f"{m['session']} · {m['asof_label']}")
    body += T(za, 72, "Today (%)", 12, INK2, 600, "middle") + T(zb + 40, 72, "October so far (%)", 12, INK2, 600, "middle")
    body += f'<line x1="{za}" x2="{za}" y1="{top-12}" y2="{h-40}" stroke="#c3c2b7" stroke-opacity=".35"/>'
    body += f'<line x1="{zb}" x2="{zb}" y1="{top-12}" y2="{h-40}" stroke="#c3c2b7" stroke-opacity=".35"/>'
    for i, s in enumerate(rows):
        y = top + i * rh
        if i % 2 == 0:
            body += f'<rect x="20" y="{y-3}" width="860" height="{rh}" rx="6" fill="#fff" fill-opacity=".025"/>'
        body += T(32, y + 13, s["n"], 13, INK)
        for z, sc, v, dec in ((za, sa, s["d"], 2), (zb, sb, s["m"], 1)):
            w = v * sc
            body += f'<path d="{bar(z, y, w, 14)}" fill="{col(v)}"/>'
            tx = z + w + (6 if v >= 0 else -6)
            body += T(tx, y + 12, sgn(v, dec) + "%", 11, INK2, 400, "start" if v >= 0 else "end")
    body += T(32, h - 14, "Blue = up, red = down. Rows sorted by today's move; bars start at zero.", 11, MUT)
    lead = rows[0]
    best_m = max(rows, key=lambda r: r["m"])
    return wrap(900, h, body, f"Sector rotation, {m['asof_label']}",
                f"Today {lead['n']} led with {sgn(lead['d'])} percent. For October, {best_m['n']} leads with {sgn(best_m['m'],1)} percent.")


# ---------------------------------------------------------------- screener board
def card(x, w, title, sub, rows_svg):
    return (f'<rect x="{x}" y="60" width="{w}" height="270" rx="12" fill="#fff" fill-opacity=".04"/>'
            + T(x + 16, 86, title, 13, INK, 600) + T(x + 16, 103, sub, 11, MUT) + rows_svg)


def screener(m, live=None):
    sc = dict(m["screens"])
    asof_note = f"{m['session']} · {m['asof_label']}"
    if live:
        for k in ("highs", "volume"):
            if live.get(k):
                sc[k] = live[k]
        if live.get("momentum"):
            sc["third"] = {"title": "Momentum", "sub": "RSI 55–75 · close > EMA20 > EMA50",
                           "items": [{"sym": i["sym"], "chg": i["chg"], "rsi": i["rsi"], "dir": "long"} for i in live["momentum"]]}
        asof_note = f"screener run · {live.get('asof', '')}"
    cw, gap = 272, 10
    xs = [32 + i * (cw + gap) for i in range(3)]
    # card 1: highs
    r1 = ""
    for i, it in enumerate(sc["highs"][:6]):
        y = 130 + i * 32
        r1 += T(xs[0] + 16, y, it["sym"], 13, INK, 600)
        r1 += T(xs[0] + cw - 16, y, ("₹" + num(it["price"])) if it.get("chg") is None else f"₹{num(it['price'])}  {sgn(it['chg'])}%", 12, INK2, 400, "end")
        r1 += f'<line x1="{xs[0]+16}" x2="{xs[0]+cw-16}" y1="{y+10}" y2="{y+10}" stroke="{GRID}"/>'
    # card 2: volume
    r2, mx = "", max(v["x"] for v in sc["volume"][:6])
    for i, it in enumerate(sc["volume"][:6]):
        y = 130 + i * 32
        r2 += T(xs[1] + 16, y, it["sym"], 13, INK, 600)
        r2 += T(xs[1] + cw - 16, y, f"{sgn(it['chg'])}%", 12, col(it["chg"]), 600, "end")
        w = 150 * it["x"] / mx
        r2 += f'<path d="{bar(xs[1]+16, y+6, w, 6, 3)}" fill="{UP}" opacity=".85"/>'
        r2 += T(xs[1] + 16 + w + 6, y + 12, f"{it['x']:g}×", 10, INK2)
    # card 3: third
    th = sc["third"]
    r3 = ""
    for i, it in enumerate(th["items"][:6]):
        y = 130 + i * 32
        up = it["dir"] == "long"
        r3 += f'<text x="{xs[2]+16}" y="{y}" font-size="12" fill="{UP if up else DN}">{"▲" if up else "▼"}</text>'
        r3 += T(xs[2] + 34, y, it["sym"], 13, INK, 600)
        extra = f"OI {sgn(it['oi'])}%" if "oi" in it else f"RSI {it['rsi']:.0f}"
        r3 += T(xs[2] + cw - 16, y, f"{sgn(it['chg'])}%  ·  {extra}", 12, INK2, 400, "end")
        r3 += f'<line x1="{xs[2]+16}" x2="{xs[2]+cw-16}" y1="{y+10}" y2="{y+10}" stroke="{GRID}"/>'
    body = header("SCREENER BOARD", asof_note)
    body += card(xs[0], cw, "52-week closing highs", "Nifty 500 · price, day move", r1)
    body += card(xs[1], cw, "Volume shockers", "≥ 2× own 20-session average", r2)
    body += card(xs[2], cw, th["title"], th["sub"], r3)
    body += T(32, 352, "▲ long build-up / momentum   ▼ short build-up. Facts from exchange data, not recommendations.", 11, MUT)
    return wrap(900, 372, body, "Screener board",
                "Three screens: 52-week closing highs, volume shockers and F&O build-up or momentum.")


# ---------------------------------------------------------------- AI brief
def brief(b):
    lines = []
    for bl in b["bullets"]:
        lines.append(textwrap.wrap(bl, 108))
    h = 124 + sum(len(l) for l in lines) * 20 + len(lines) * 10 + 36
    body = header("AI MARKET BRIEF", b["asof_label"])
    body += f'<rect x="32" y="56" width="{26+len(b["engine"])*7}" height="22" rx="11" fill="#fff" fill-opacity=".07"/>'
    body += T(45, 71, b["engine"], 11, INK2)
    body += T(32, 108, b["headline"], 18, INK, 600)
    y = 138
    for l in lines:
        body += f'<circle cx="38" cy="{y-4}" r="3" fill="{UP}"/>'
        for j, part in enumerate(l):
            body += T(52, y, part, 13.5, INK2)
            y += 20
        y += 10
    body += T(32, h - 14, "Generated by agent/market_agent.py from the data on this page. Commentary, not advice.", 11, MUT)
    return wrap(900, h, body, "AI market brief", b["headline"])


def main():
    OUT.mkdir(exist_ok=True)
    m = json.loads((DATA / "market.json").read_text())
    live_p = DATA / "screens_live.json"
    live = json.loads(live_p.read_text()) if live_p.exists() else None
    brief_p = DATA / "brief.json"
    files = {"banner.svg": banner(m), "market-board.svg": board(m),
             "sector-heatmap.svg": heatmap(m), "screener-board.svg": screener(m, live)}
    if brief_p.exists():
        files["ai-brief.svg"] = brief(json.loads(brief_p.read_text()))
    for name, svg in files.items():
        (OUT / name).write_text(svg, encoding="utf-8")
        print("wrote", OUT / name)


if __name__ == "__main__":
    main()
