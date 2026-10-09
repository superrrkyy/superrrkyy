"""
Generator dashboard profil GitHub (dijalankan otomatis oleh GitHub Actions).
Menghasilkan out/dashboard.svg berisi:
  - jam analog + digital (WIB) yang terus bergerak lewat animasi SVG
  - tanggal & sapaan sesuai waktu
  - statistik GitHub (repo, bintang, followers, kontribusi) + bahasa terbanyak
"""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

USER = os.getenv("GH_USER", "superrrkyy")
TOKEN = os.getenv("GITHUB_TOKEN", "")
OUT = os.getenv("OUT_DIR", "out")
WIB = timezone(timedelta(hours=7))

HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]
LANG_COLORS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "HTML": "#e34c26",
    "CSS": "#663399", "Python": "#3572A5", "Shell": "#89e051",
}


# ---------------- data ----------------
def api(url, data=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def get_stats():
    s = {"repos": 0, "stars": 0, "followers": 0, "contrib": None, "live": 0, "langs": []}
    try:
        user = api(f"https://api.github.com/users/{USER}")
        repos = api(f"https://api.github.com/users/{USER}/repos?per_page=100")
        own = [r for r in repos if not r["fork"]]
        s["repos"] = user.get("public_repos", len(repos))
        s["followers"] = user.get("followers", 0)
        s["stars"] = sum(r["stargazers_count"] for r in own)
        s["live"] = sum(1 for r in own if r.get("has_pages"))
        totals = {}
        for r in own:
            try:
                for lang, n in api(r["languages_url"]).items():
                    totals[lang] = totals.get(lang, 0) + n
            except Exception:
                pass
        total = sum(totals.values()) or 1
        s["langs"] = [(k, v / total) for k, v in sorted(totals.items(), key=lambda x: -x[1])][:5]
    except Exception as e:
        print("Gagal ambil statistik:", e)
    try:
        q = {"query": "query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{totalContributions}}}}",
             "variables": {"u": USER}}
        d = api("https://api.github.com/graphql", q)
        s["contrib"] = d["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    except Exception as e:
        print("Gagal ambil kontribusi:", e)
    return s


# ---------------- svg helpers ----------------
def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def sapaan(h):
    if 4 <= h < 10:
        return "Selamat Pagi", "☀️"
    if 10 <= h < 15:
        return "Selamat Siang", "🌤️"
    if 15 <= h < 18:
        return "Selamat Sore", "🌇"
    return "Selamat Malam", "🌙"


def build(now, s):
    W, H = 840, 440
    sec0 = now.second
    cx, cy, R = 150, 190, 92

    a_sec = sec0 * 6
    a_min = now.minute * 6 + sec0 * 0.1
    a_hour = (now.hour % 12) * 30 + now.minute * 0.5 + sec0 / 120

    # Digital HH:MM — satu frame per menit untuk 3 jam ke depan
    minute_frames = []
    base = now.replace(second=0, microsecond=0)
    for m in range(180):
        t = base + timedelta(minutes=m)
        begin = 0 if m == 0 else m * 60 - sec0
        dur = 60 - sec0 if m == 0 else 60
        minute_frames.append(
            f'<text x="0" y="0" opacity="0">{t:%H:%M}'
            f'<set attributeName="opacity" to="1" begin="{begin}s" dur="{dur}s"/></text>'
        )

    # Detik — 60 frame yang berputar setiap 60 detik
    sec_frames = []
    for v in range(60):
        start = (v - sec0) % 60
        a, b = start / 60, min((start + 1) / 60, 1)
        keys = f"0;{a:.5f};{b:.5f}" if b < 1 else f"0;{a:.5f};1"
        vals = "0;1;0" if b < 1 else "0;1;1"
        sec_frames.append(
            f'<text x="0" y="0" opacity="0">{v:02d}'
            f'<animate attributeName="opacity" values="{vals}" keyTimes="{keys}" calcMode="discrete" dur="60s" repeatCount="indefinite"/></text>'
        )

    ticks = []
    for i in range(60):
        big = i % 5 == 0
        ticks.append(
            f'<line x1="{cx}" y1="{cy - R + 6}" x2="{cx}" y2="{cy - R + (16 if big else 10)}" '
            f'stroke="{"#c4b5fd" if big else "#4c4670"}" stroke-width="{3 if big else 1.5}" stroke-linecap="round" '
            f'transform="rotate({i * 6} {cx} {cy})"/>'
        )

    greet, icon = sapaan(now.hour)
    tanggal = f"{HARI[now.weekday()]}, {now.day} {BULAN[now.month - 1]} {now.year}"

    def card(x, y, label, value, emoji, color, w=162):
        return f'''
    <g transform="translate({x} {y})">
      <rect width="{w}" height="92" rx="16" fill="#ffffff" fill-opacity=".035" stroke="#ffffff" stroke-opacity=".08"/>
      <rect width="4" height="40" y="26" rx="2" fill="{color}"/>
      <text x="20" y="34" class="lbl">{emoji} {esc(label)}</text>
      <text x="20" y="72" class="val" fill="{color}">{esc(value)}</text>
    </g>'''

    contrib = s["contrib"] if s["contrib"] is not None else "–"
    cards = (
        card(320, 98, "Repositori", s["repos"], "📦", "#a78bfa")
        + card(494, 98, "Bintang", s["stars"], "⭐", "#fbbf24")
        + card(320, 202, "Kontribusi/thn", contrib, "🔥", "#f472b6")
        + card(494, 202, "Website Live", s["live"], "🌐", "#22d3ee")
    )
    side = card(668, 98, "Followers", s["followers"], "👥", "#4ade80", w=140)

    # language bar
    bar, legend, x = [], [], 0
    bw = 488
    for i, (lang, frac) in enumerate(s["langs"]):
        w = max(bw * frac, 4)
        col = LANG_COLORS.get(lang, "#8b8b9e")
        bar.append(f'<rect x="{x:.1f}" y="0" width="{w:.1f}" height="10" fill="{col}"/>')
        x += w
        lx = (i % 3) * 165
        ly = 30 + (i // 3) * 22
        legend.append(f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{col}"/>'
                      f'<text x="{lx + 16}" y="{ly}" class="leg">{esc(lang)} <tspan fill="#8b86a8">{frac * 100:.1f}%</tspan></text>')

    updated = f"{now:%H:%M} WIB"

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0d0b1a"/><stop offset="1" stop-color="#120f24"/>
    </linearGradient>
    <linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#a78bfa"/><stop offset="1" stop-color="#22d3ee"/>
    </linearGradient>
    <linearGradient id="title" x1="0" x2="1">
      <stop offset="0" stop-color="#c4b5fd"/><stop offset="1" stop-color="#67e8f9"/>
    </linearGradient>
    <radialGradient id="glow"><stop offset="0" stop-color="#7c3aed" stop-opacity=".35"/><stop offset="1" stop-color="#7c3aed" stop-opacity="0"/></radialGradient>
    <clipPath id="barclip"><rect width="{bw}" height="10" rx="5"/></clipPath>
    <style>
      .lbl {{ font: 600 13px 'Segoe UI', Helvetica, Arial, sans-serif; fill: #a39fc0; }}
      .val {{ font: 800 30px 'Segoe UI', Helvetica, Arial, sans-serif; }}
      .leg {{ font: 500 13px 'Segoe UI', Helvetica, Arial, sans-serif; fill: #e2e0f0; }}
      .mono {{ font-family: 'Fira Code', Consolas, Menlo, monospace; }}
      .live {{ animation: pulse 1.6s ease-in-out infinite; }}
      @keyframes pulse {{ 50% {{ opacity: .25; }} }}
    </style>
  </defs>

  <rect width="{W}" height="{H}" rx="24" fill="url(#bg)"/>
  <rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="24" fill="none" stroke="#ffffff" stroke-opacity=".08"/>
  <circle cx="{cx}" cy="{cy}" r="190" fill="url(#glow)"/>

  <!-- header -->
  <text x="32" y="50" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="22" font-weight="800" fill="url(#title)">⚡ AXRYZURE DASHBOARD</text>
  <g transform="translate({W - 32} 44)">
    <text x="0" y="0" text-anchor="end" class="mono" font-size="12" fill="#8b86a8">sinkron {updated}</text>
    <circle cx="-{len("sinkron " + updated) * 7.3 + 12:.0f}" cy="-4" r="5" fill="#4ade80" class="live"/>
  </g>
  <line x1="32" y1="70" x2="{W - 32}" y2="70" stroke="#ffffff" stroke-opacity=".07"/>

  <!-- analog clock -->
  <circle cx="{cx}" cy="{cy}" r="{R + 8}" fill="none" stroke="url(#ring)" stroke-width="3" opacity=".9"/>
  <circle cx="{cx}" cy="{cy}" r="{R}" fill="#0a0815"/>
  {''.join(ticks)}
  <line x1="{cx}" y1="{cy + 12}" x2="{cx}" y2="{cy - 50}" stroke="#ffffff" stroke-width="6" stroke-linecap="round">
    <animateTransform attributeName="transform" type="rotate" from="{a_hour:.3f} {cx} {cy}" to="{a_hour + 360:.3f} {cx} {cy}" dur="43200s" repeatCount="indefinite"/>
  </line>
  <line x1="{cx}" y1="{cy + 14}" x2="{cx}" y2="{cy - 72}" stroke="#c4b5fd" stroke-width="4" stroke-linecap="round">
    <animateTransform attributeName="transform" type="rotate" from="{a_min:.3f} {cx} {cy}" to="{a_min + 360:.3f} {cx} {cy}" dur="3600s" repeatCount="indefinite"/>
  </line>
  <g>
    <line x1="{cx}" y1="{cy + 20}" x2="{cx}" y2="{cy - 80}" stroke="#22d3ee" stroke-width="2" stroke-linecap="round"/>
    <circle cx="{cx}" cy="{cy - 80}" r="3" fill="#22d3ee"/>
    <animateTransform attributeName="transform" type="rotate" from="{a_sec} {cx} {cy}" to="{a_sec + 360} {cx} {cy}" dur="60s" repeatCount="indefinite"/>
  </g>
  <circle cx="{cx}" cy="{cy}" r="7" fill="#22d3ee"/><circle cx="{cx}" cy="{cy}" r="3" fill="#0a0815"/>

  <!-- digital clock -->
  <g transform="translate({cx - 62} 338)" class="mono" font-size="34" font-weight="600" fill="#ffffff">
    <g>{''.join(minute_frames)}</g>
    <g transform="translate(100 0)" font-size="20" fill="#22d3ee">{''.join(sec_frames)}</g>
  </g>
  <text x="{cx}" y="366" text-anchor="middle" class="mono" font-size="12" fill="#8b86a8" letter-spacing="2">WIB • JAKARTA</text>
  <text x="{cx}" y="404" text-anchor="middle" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="15" font-weight="700" fill="#e2e0f0">{icon} {greet}!</text>
  <text x="{cx}" y="424" text-anchor="middle" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="12" fill="#a39fc0">{esc(tanggal)}</text>

  <!-- stat cards -->
  {cards}
  {side}
  <g transform="translate(668 202)">
    <rect width="140" height="92" rx="16" fill="#ffffff" fill-opacity=".035" stroke="#ffffff" stroke-opacity=".08"/>
    <text x="70" y="40" text-anchor="middle" font-size="26">🚀</text>
    <text x="70" y="70" text-anchor="middle" class="lbl">Terus Membangun</text>
  </g>

  <!-- languages -->
  <g transform="translate(320 330)">
    <text x="0" y="-10" class="lbl">💻 Bahasa Terbanyak</text>
    <g transform="translate(0 4)" clip-path="url(#barclip)">
      <rect width="{bw}" height="10" fill="#1f1b33"/>
      {''.join(bar)}
    </g>
    <g transform="translate(0 8)">{''.join(legend)}</g>
  </g>
</svg>'''


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    now = datetime.now(WIB)
    svg = build(now, get_stats())
    with open(os.path.join(OUT, "dashboard.svg"), "w", encoding="utf-8") as f:
        f.write(svg)
    print("✅ dashboard.svg dibuat:", now.isoformat())
