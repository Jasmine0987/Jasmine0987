#!/usr/bin/env python3
"""Generate the profile graphics (light + dark SVGs) with no third-party service.

  GITHUB_TOKEN=xxx python scripts/generate.py     # live data (recommended)
  python scripts/generate.py                       # offline sample data

Outputs to ../assets:
  cartographer-{light,dark}.svg   bio card (parchment, compass, avatar)
  map-{light,dark}.svg            animated project map
  legend-{light,dark}.svg         language chips
  card-N-{light,dark}.svg         one dark repo card per featured project
  expedition-{light,dark}.svg     26-week heatmap + stats
Standard library only.
"""
import base64
import datetime as dt
import json
import math
import os
import random
import urllib.request
from html import escape

USER = "Jasmine0987"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Repos that get a card in the README table (order = card-0 .. card-N)
FEATURED = [
    "AICTCE-Batch-7-AI-Fashion-Design-Generator-STYLESYNC-", "Kavach", "NeuraVapour",
    "ResourceRX", "SafeBite-main", "papercomic", "rl-environment", "supply-chain",
]
FALLBACK_BIO = "Software Engineer. Excited for new projects coming my way!. Working on amazon-ml-challenge right now."
FALLBACK_LANG = {"Kavach": "Python", "NeuraVapour": "Python", "ResourceRX": "JavaScript",
                 "SafeBite-main": "Python", "papercomic": "TypeScript", "rl-environment": "Python",
                 "supply-chain": "JavaScript"}

LANG = {  # name: (badge text, colour, badge text colour)
    "JavaScript": ("JS", "#f1e05a", "#1f2328"), "HTML": ("H5", "#e34c26", "#ffffff"),
    "Python": ("Py", "#3572A5", "#ffffff"), "Jupyter Notebook": ("Jp", "#DA5B0B", "#ffffff"),
    "Java": ("Ja", "#b07219", "#ffffff"), "TypeScript": ("TS", "#3178c6", "#ffffff"),
    "CSS": ("Cs", "#663399", "#ffffff"), "C++": ("C+", "#f34b7d", "#ffffff"),
    "PHP": ("Ph", "#4F5D95", "#ffffff"), "Shell": ("Sh", "#89e051", "#1f2328"),
}
DEFAULT_LANG = ("··", "#8b949e", "#ffffff")

THEMES = {
    "light": dict(text="#1f2a44", sub="#5b6470", green="#1a9850", red="#c8372d",
                  paper="#f5efdd", grid="#e6dec6", dash="#d9cfb2", empty="#ebe3d0",
                  heat=["#c5d4bb", "#9bb99a", "#6f9b7c", "#1e5b45"], link="#1f2328",
                  halo="#ffffff", chip="#4a5160"),
    "dark": dict(text="#e8e4d6", sub="#98a1b3", green="#3fb950", red="#ef6a58",
                 paper="#1c2332", grid="#252e42", dash="#3a4660", empty="#2a3347",
                 heat=["#3b5b4c", "#4f8a68", "#6dbb88", "#a7e8b8"], link="#c9d1d9",
                 halo="#0d1117", chip="#c8ccd6"),
}
SANS = "'Trebuchet MS','Segoe UI',Verdana,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"


# ------------------------------------------------------------------ data ---
def api(url, body=None, raw=False):
    h = {"User-Agent": "profile-svg-generator", "Accept": "application/vnd.github+json"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, headers=h)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read() if raw else json.load(r)


def load_profile():
    p = dict(name="Jasmine", bio=FALLBACK_BIO, location="Hyderabad", followers=4,
             repos=15, avatar=None)
    try:
        u = api(f"https://api.github.com/users/{USER}")
        p.update(name=(u.get("name") or USER).split()[0], bio=(u.get("bio") or "").strip(),
                 location=u.get("location") or "", followers=u.get("followers", 0),
                 repos=u.get("public_repos", 0))
        img = api(u["avatar_url"] + ("&" if "?" in u["avatar_url"] else "?") + "s=240", raw=True)
        p["avatar"] = "data:image/png;base64," + base64.b64encode(img).decode()
    except Exception as e:
        print("  (profile fallback:", e, ")")
    return p


def load_repos():
    try:
        rs = api(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&sort=updated")
        return [dict(name=r["name"], lang=r.get("language"), stars=r["stargazers_count"],
                     topics=r.get("topics", [])) for r in rs if not r["fork"]]
    except Exception as e:
        print("  (repos fallback:", e, ")")
        return [dict(name=n, lang=FALLBACK_LANG.get(n, "Python"), stars=0, topics=[]) for n in FEATURED]


def load_days():
    if TOKEN:
        q = """query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{
        weeks{contributionDays{date contributionCount}}}}}}"""
        try:
            r = api("https://api.github.com/graphql", {"query": q, "variables": {"u": USER}})
            wk = r["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
            return [(d["date"], d["contributionCount"]) for w in wk for d in w["contributionDays"]]
        except Exception as e:
            print("  (contributions failed:", e, ")")
    print("  using SAMPLE contribution data (set GITHUB_TOKEN for real data)")
    today, rnd, out = dt.date.today(), random.Random(3), []
    for i in range(371, -1, -1):
        d = today - dt.timedelta(days=i)
        out.append((d.isoformat(), rnd.choice([0, 0, 0, 0, 1, 1, 2, 3, 5]) if rnd.random() < .45 else 0))
    return out


# --------------------------------------------------------------- helpers ---
def lang_info(l):
    return LANG.get(l, DEFAULT_LANG)


def wrap(text, width):
    lines, cur = [], ""
    for w in text.split():
        if cur and len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return lines + ([cur] if cur else [])


def trunc(s, n):
    return s if len(s) <= n else s[: n - 1] + "…"


def save(name, mode, content):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"{name}-{mode}.svg"), "w", encoding="utf-8") as f:
        f.write(content)


def doc(w, h, body, title, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">'
            f'<title>{escape(title)}</title><defs>{defs}</defs>{body}</svg>')


def compass(x, y, t):
    return (f'<g transform="translate({x},{y})"><circle r="20" fill="none" stroke="{t["sub"]}" stroke-width="1" opacity=".7"/>'
            f'<text y="-25" text-anchor="middle" font-size="9" font-family="{MONO}" fill="{t["sub"]}">N</text>'
            f'<polygon points="0,-14 5,0 0,14 -5,0" fill="{t["red"]}" transform="rotate(8)"/></g>')


def parchment(w, h, t, uid):
    defs = (f'<pattern id="grid{uid}" width="40" height="40" patternUnits="userSpaceOnUse">'
            f'<path d="M40 0H0V40" fill="none" stroke="{t["grid"]}" stroke-width="1"/></pattern>')
    body = (f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="16" fill="{t["paper"]}"/>'
            f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="16" fill="url(#grid{uid})"/>'
            f'<rect x="6" y="6" width="{w - 12}" height="{h - 12}" rx="12" fill="none" stroke="{t["dash"]}" '
            f'stroke-width="1.5" stroke-dasharray="5 4"/>')
    return defs, body


# ---------------------------------------------------------------- panels ---
def cartographer(t, prof, repos):
    W, H = 880, 230
    defs, body = parchment(W, H, t, "c")
    stars = sum(r["stars"] for r in repos)
    body += (f'<text x="36" y="52" font-size="12" letter-spacing="2" font-family="{MONO}" fill="{t["red"]}">◆ THE CARTOGRAPHER</text>'
             f'<text x="36" y="104" font-size="34" font-weight="800" font-family="{SANS}" fill="{t["text"]}">{escape(prof["name"])}</text>')
    for i, line in enumerate(wrap(prof["bio"] or "Building things, one commit at a time.", 54)[:3]):
        body += f'<text x="36" y="{136 + i * 26}" font-size="18" font-family="{SANS}" fill="{t["sub"]}">{escape(line)}</text>'
    bits = [prof["location"], f'{prof["followers"]} followers', f'{prof["repos"]} repositories', f"★ {stars} stars"]
    body += (f'<text x="36" y="205" font-size="13" font-family="{MONO}" fill="{t["sub"]}">'
             f'{escape(" · ".join(b for b in bits if b))}</text>')
    cx, cy, r = 782, 120, 60
    defs += f'<clipPath id="av"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>'
    if prof["avatar"]:
        body += f'<image href="{prof["avatar"]}" x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" clip-path="url(#av)" preserveAspectRatio="xMidYMid slice"/>'
    else:
        body += (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#7a5fc4"/>'
                 f'<text x="{cx}" y="{cy + 20}" text-anchor="middle" font-size="58" font-weight="800" font-family="{SANS}" fill="#fff">{escape(prof["name"][0])}</text>')
    body += f'<circle cx="{cx}" cy="{cy}" r="{r + 3}" fill="none" stroke="{t["red"]}" stroke-width="6"/>'
    body += compass(832, 46, t)
    return doc(W, H, body, f'{prof["name"]} — profile card', defs)


def build_links(repos):
    links = []
    seen = set()

    def add(a, b, color):
        k = (min(a, b), max(a, b))
        if a != b and k not in seen:
            seen.add(k)
            links.append((a, b, color))
    groups = {}
    for i, r in enumerate(repos):
        if r["lang"]:
            groups.setdefault(r["lang"], []).append(i)
    for lang, idx in groups.items():
        for a, b in zip(idx, idx[1:]):
            add(a, b, lang_info(lang)[1])
        if len(idx) > 2:
            add(idx[-1], idx[0], lang_info(lang)[1])
    tg = {}
    for i, r in enumerate(repos):
        for tp in r["topics"]:
            tg.setdefault(tp, []).append(i)
    for idx in tg.values():
        for a, b in zip(idx, idx[1:]):
            add(a, b, "#8b949e")
    return links


def layout(n, links, cx, cy):
    rnd = random.Random(11)
    pos = [[cx + 170 * math.cos(2 * math.pi * i / n) + rnd.uniform(-15, 15),
            cy + 120 * math.sin(2 * math.pi * i / n) + rnd.uniform(-15, 15)] for i in range(n)]
    for it in range(500):
        cool = 1 - it / 500 + .05
        f = [[0.0, 0.0] for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                dx, dy = pos[i][0] - pos[j][0], pos[i][1] - pos[j][1]
                d = math.hypot(dx, dy) or .1
                k = 5200 / (d * d)
                f[i][0] += dx / d * k; f[i][1] += dy / d * k
                f[j][0] -= dx / d * k; f[j][1] -= dy / d * k
            dx, dy = pos[i][0] - cx, pos[i][1] - cy
            d = math.hypot(dx, dy) or .1
            k = 9000 / (d * d) - 0.002 * (d - 120)
            f[i][0] += dx / d * k; f[i][1] += dy / d * k
        for a, b, _ in links:
            dx, dy = pos[b][0] - pos[a][0], pos[b][1] - pos[a][1]
            d = math.hypot(dx, dy) or .1
            k = (d - 140) * .015
            f[a][0] += dx / d * k; f[a][1] += dy / d * k
            f[b][0] -= dx / d * k; f[b][1] -= dy / d * k
        for i in range(n):
            pos[i][0] = min(800, max(80, pos[i][0] + max(-6, min(6, f[i][0])) * cool))
            pos[i][1] = min(405, max(135, pos[i][1] + max(-6, min(6, f[i][1])) * cool))
    return pos


def project_map(t, prof, repos):
    W, H, cx, cy = 880, 500, 440, 285
    n = len(repos)
    links = build_links(repos)
    pos = layout(n, links, cx, cy)
    rad = [11 + min(14, math.sqrt(r["stars"]) * 3) for r in repos]
    body = (f'<text x="8" y="22" font-size="12" letter-spacing="2" font-family="{MONO}" fill="{t["green"]}">PROJECT MAP</text>'
            f'<text x="8" y="58" font-size="26" font-weight="800" font-family="{SANS}" fill="{t["text"]}">Everything I build, and how it connects</text>'
            f'<text x="8" y="82" font-size="14" font-family="{SANS}" fill="{t["sub"]}">Size is stars. Lines join projects that share a language or topics.</text>')
    for x, y in pos:
        body += f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{t["link"]}" stroke-width="1" opacity=".8"/>'
    for k, (a, b, col) in enumerate(links):
        (x1, y1), (x2, y2) = pos[a], pos[b]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = x2 - x1, y2 - y1
        d = math.hypot(dx, dy) or 1
        s = .3 if k % 2 else -.3
        qx, qy = mx - dy / d * d * s, my + dx / d * d * s
        path = f"M{x1:.1f},{y1:.1f} Q{qx:.1f},{qy:.1f} {x2:.1f},{y2:.1f}"
        body += f'<path d="{path}" fill="none" stroke="{col}" stroke-width="1.6" opacity=".7"/>'
        for j in range(2):  # moving dots travelling along each link
            dur = 5 + (k * 7 % 5)
            body += (f'<circle r="3.4" fill="{col}"><animateMotion dur="{dur}s" begin="-{j * dur / 2:.1f}s" '
                     f'repeatCount="indefinite" path="{path}"/></circle>')
    for i, (r, (x, y)) in enumerate(zip(repos, pos)):
        col = lang_info(r["lang"])[1]
        body += (f'<a href="https://github.com/{USER}/{escape(r["name"])}" target="_blank">'
                 f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad[i] + 6:.1f}" fill="{col}" opacity=".2">'
                 f'<animate attributeName="r" values="{rad[i] + 4:.1f};{rad[i] + 9:.1f};{rad[i] + 4:.1f}" dur="{3 + i % 3}s" repeatCount="indefinite"/></circle>'
                 f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad[i]:.1f}" fill="{col}"/>'
                 f'<text x="{x:.1f}" y="{y + rad[i] + 18:.1f}" text-anchor="middle" font-size="11.5" font-family="{MONO}" fill="{t["chip"]}">{escape(trunc(r["name"], 20))}</text>'
                 f'<text x="{x:.1f}" y="{y + rad[i] + 33:.1f}" text-anchor="middle" font-size="11" font-family="{MONO}" fill="{t["sub"]}">★ {r["stars"]}</text></a>')
    defs = f'<clipPath id="cav"><rect x="{cx - 32}" y="{cy - 32}" width="64" height="64" rx="16"/></clipPath>'
    body += f'<circle cx="{cx}" cy="{cy}" r="40" fill="{t["halo"]}" opacity=".9"/>'
    if prof["avatar"]:
        body += f'<image href="{prof["avatar"]}" x="{cx - 32}" y="{cy - 32}" width="64" height="64" clip-path="url(#cav)"/>'
    else:
        body += (f'<rect x="{cx - 32}" y="{cy - 32}" width="64" height="64" rx="16" fill="#7a5fc4"/>'
                 f'<text x="{cx}" y="{cy + 14}" text-anchor="middle" font-size="40" font-weight="800" font-family="{SANS}" fill="#fff">{escape(prof["name"][0])}</text>')
    return doc(W, H, body, "A map of my projects", defs)


def legend(t, repos):
    counts = {}
    for r in repos:
        if r["lang"]:
            counts[r["lang"]] = counts.get(r["lang"], 0) + 1
    body, x = "", 8
    for lang, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        txt, col, fg = lang_info(lang)
        label = f"{lang} · {c}"
        body += (f'<rect x="{x}" y="9" width="24" height="24" rx="6" fill="{col}"/>'
                 f'<text x="{x + 12}" y="25.5" text-anchor="middle" font-size="11" font-weight="800" font-family="{SANS}" fill="{fg}">{txt}</text>'
                 f'<text x="{x + 33}" y="26" font-size="13.5" font-weight="700" font-family="{MONO}" fill="{t["chip"]}" opacity=".9">{escape(label)}</text>')
        x += 33 + len(label) * 8.4 + 30
    return doc(880, 42, body, "Languages used across my projects")


def repo_card(t, r):
    W, H = 430, 300
    name = r["name"].replace("-STYLESYNC-", "").replace("_", " ").replace("-", " ").strip()
    words = name.split()
    size, width = 38, 16
    lines = wrap(" ".join(words), width)
    if len(lines) > 3:
        size, width = 30, 21
        lines = wrap(" ".join(words), width)[:3]
    txt, col, fg = lang_info(r["lang"])
    body = (f'<clipPath id="rc"><rect width="{W}" height="{H}" rx="16"/></clipPath><g clip-path="url(#rc)">'
            f'<rect width="{W}" height="{H}" fill="#1e2b39"/><rect y="230" width="{W}" height="70" fill="#16212c"/></g>')
    for i, line in enumerate(lines):
        body += f'<text x="30" y="{72 + i * (size + 10)}" font-size="{size}" font-weight="800" font-family="{SANS}" fill="#ffffff">{escape(line)}</text>'
    body += (f'<rect x="10" y="253" width="24" height="24" rx="6" fill="{col}"/>'
             f'<text x="22" y="270" text-anchor="middle" font-size="11" font-weight="800" font-family="{SANS}" fill="{fg}">{txt}</text>'
             f'<text x="42" y="271" font-size="15" font-weight="700" font-family="{SANS}" fill="#ffffff">{escape(trunc(r["name"], 28))}</text>'
             f'<text x="{W - 16}" y="271" text-anchor="end" font-size="14" font-family="{MONO}" fill="#8b98a8">★ {r["stars"]}</text>')
    return doc(W, H, body, f'{r["name"]} repository card')


def expedition(t, days):
    W, H = 880, 264
    defs, body = parchment(W, H, t, "e")
    first = dt.date.fromisoformat(days[0][0])
    cells = [None] * ((first.weekday() + 1) % 7) + days
    weeks = [cells[i:i + 7] for i in range(0, len(cells), 7)][-26:]
    window = [c for wk in weeks for c in wk if c]
    mx = max((c for _, c in window), default=1) or 1
    body += f'<text x="36" y="50" font-size="12" letter-spacing="2" font-family="{MONO}" fill="{t["red"]}">◆ EXPEDITION LOG · 26 WEEKS</text>'
    for wi, wk in enumerate(weeks):
        for di, c in enumerate(wk):
            if not c:
                continue
            col = t["empty"] if c[1] == 0 else t["heat"][min(3, int(4 * c[1] / (mx + .001)))]
            body += (f'<rect x="{36 + wi * 16}" y="{84 + di * 16}" width="13" height="13" rx="3" fill="{col}">'
                     f'<title>{c[0]}: {c[1]}</title></rect>')
    active = sum(1 for _, c in window if c > 0)
    best = run = 0
    for _, c in window:
        run = run + 1 if c > 0 else 0
        best = max(best, run)
    year = str(dt.date.today().year)
    steps = sum(c for d, c in days if d.startswith(year))
    stats = [("DAYS TRAVELLING", f"{active} days"), ("LONGEST JOURNEY", f"{best} days"), ("CONTRIBUTIONS THIS YEAR", f"{steps:,}")]
    for i, (lab, val) in enumerate(stats):
        y = 92 + i * 56
        body += (f'<text x="520" y="{y}" font-size="12" letter-spacing="1" font-family="{MONO}" fill="{t["sub"]}">{lab}</text>'
                 f'<text x="520" y="{y + 30}" font-size="28" font-weight="800" font-family="{SANS}" fill="{t["text"]}">{val}</text>')
    body += compass(832, 46, t)
    return doc(W, H, body, "Contribution expedition log", defs)


# ------------------------------------------------------------------ main ---
def main():
    print("Fetching data…")
    prof, repos, days = load_profile(), load_repos(), load_days()
    by_name = {r["name"]: r for r in repos}
    print(f"  {len(repos)} repos, {len(days)} days")
    print("  total contributions:", sum(c for _, c in days))
    print("Rendering…")
    for mode, t in THEMES.items():
        save("cartographer", mode, cartographer(t, prof, repos))
        save("map", mode, project_map(t, prof, repos))
        save("legend", mode, legend(t, repos))
        save("expedition", mode, expedition(t, days))
        for i, n in enumerate(FEATURED):
            save(f"card-{i}", mode, repo_card(t, by_name.get(n, dict(name=n, lang=None, stars=0))))
    print("Done ->", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
