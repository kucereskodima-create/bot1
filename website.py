import json
from aiohttp import web

DATA_FILE = "users.json"

HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Blackline — Топ игроков</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

* {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
  --bg: #070b14;
  --surface: #0e1623;
  --surface2: #131d2e;
  --border: #1a2d45;
  --accent: #3b82f6;
  --accent2: #60a5fa;
  --gold: #f59e0b;
  --silver: #94a3b8;
  --bronze: #b45309;
  --green: #22c55e;
  --pink: #ec4899;
  --blue: #3b82f6;
  --text: #e2e8f0;
  --muted: #475569;
}}

body {{
  background: var(--bg);
  color: var(--text);
  font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
  min-height: 100vh;
  overflow-x: hidden;
}}

/* ── HEADER ── */
header {{
  position: relative;
  padding: 48px 20px 36px;
  text-align: center;
  overflow: hidden;
}}
header::before {{
  content: '';
  position: absolute;
  top: -60px; left: 50%;
  transform: translateX(-50%);
  width: 600px; height: 300px;
  background: radial-gradient(ellipse, rgba(59,130,246,.22) 0%, transparent 70%);
  pointer-events: none;
}}
.logo {{
  display: inline-flex;
  align-items: center;
  gap: 12px;
  font-size: 2rem;
  font-weight: 900;
  letter-spacing: 3px;
  color: #fff;
  text-shadow: 0 0 40px rgba(59,130,246,.5);
  position: relative;
}}
.logo-icon {{
  width: 44px; height: 44px;
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.3rem;
  box-shadow: 0 0 24px rgba(59,130,246,.5);
}}
.subtitle {{
  margin-top: 8px;
  color: var(--muted);
  font-size: .85rem;
  letter-spacing: 2px;
  text-transform: uppercase;
  position: relative;
}}

/* ── TABS ── */
.tabs {{
  display: flex;
  justify-content: center;
  gap: 8px;
  padding: 0 16px 32px;
  flex-wrap: wrap;
}}
.tab-btn {{
  background: var(--surface);
  border: 1.5px solid var(--border);
  color: var(--muted);
  padding: 9px 24px;
  border-radius: 100px;
  font-size: .9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all .2s;
  font-family: inherit;
}}
.tab-btn:hover {{ color: var(--accent2); border-color: var(--accent); }}
.tab-btn.active {{
  background: linear-gradient(135deg, #1e3a5f 0%, #1e40af 100%);
  border-color: var(--accent);
  color: #fff;
  box-shadow: 0 0 20px rgba(59,130,246,.3);
}}

/* ── LAYOUT ── */
.container {{
  max-width: 720px;
  margin: 0 auto;
  padding: 0 16px 80px;
}}
.panel {{ display: none; }}
.panel.active {{ display: block; animation: fadeIn .25s ease; }}
@keyframes fadeIn {{ from {{ opacity:0; transform:translateY(6px); }} to {{ opacity:1; transform:translateY(0); }} }}

/* ── PODIUM ── */
.podium {{
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 12px;
  margin-bottom: 28px;
  padding: 0 4px;
}}
.pod {{
  flex: 1;
  max-width: 200px;
  border-radius: 16px;
  padding: 20px 12px 16px;
  text-align: center;
  border: 1.5px solid var(--border);
  background: var(--surface);
  position: relative;
  transition: transform .2s;
}}
.pod:hover {{ transform: translateY(-4px); }}
.pod-1 {{
  order: 2;
  background: linear-gradient(160deg, #1c2d4a 0%, #0f1f38 100%);
  border-color: var(--gold);
  box-shadow: 0 0 28px rgba(245,158,11,.18);
  padding-top: 28px;
}}
.pod-2 {{ order: 1; background: linear-gradient(160deg, #171f2e 0%, #0e1623 100%); border-color: #334155; }}
.pod-3 {{ order: 3; background: linear-gradient(160deg, #1a1710 0%, #0e1110 100%); border-color: #44290e; }}

.pod-crown {{
  font-size: 1.6rem;
  line-height: 1;
  margin-bottom: 6px;
}}
.pod-avatar {{
  width: 52px; height: 52px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.3rem; font-weight: 800;
  margin: 0 auto 8px;
  border: 2px solid var(--border);
}}
.pod-1 .pod-avatar {{ background: linear-gradient(135deg,#78350f,#d97706); border-color: var(--gold); color: #fef3c7; }}
.pod-2 .pod-avatar {{ background: linear-gradient(135deg,#1e293b,#334155); border-color: #64748b; color: #cbd5e1; }}
.pod-3 .pod-avatar {{ background: linear-gradient(135deg,#292524,#57534e); border-color: #78716c; color: #e7e5e4; }}

.pod-name {{
  font-size: .82rem;
  font-weight: 700;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  margin-bottom: 6px;
}}
.pod-val {{
  font-size: .78rem;
  font-weight: 700;
}}
.pod-1 .pod-val {{ color: var(--gold); }}
.pod-2 .pod-val {{ color: var(--silver); }}
.pod-3 .pod-val {{ color: #cd7c2e; }}

.pod-rank {{
  position: absolute;
  top: -12px; left: 50%;
  transform: translateX(-50%);
  background: var(--surface2);
  border: 1.5px solid var(--border);
  border-radius: 20px;
  padding: 2px 10px;
  font-size: .7rem;
  font-weight: 800;
  color: var(--muted);
  white-space: nowrap;
}}
.pod-1 .pod-rank {{ color: var(--gold); border-color: var(--gold); }}

/* ── LIST ── */
.list {{ display: flex; flex-direction: column; gap: 6px; }}
.item {{
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 16px;
  transition: all .15s;
}}
.item:hover {{ background: var(--surface2); border-color: #243656; transform: translateX(3px); }}

.item-rank {{
  width: 28px;
  text-align: center;
  font-size: .85rem;
  font-weight: 800;
  flex-shrink: 0;
  color: var(--muted);
}}
.item-avatar {{
  width: 36px; height: 36px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: .95rem; font-weight: 700;
  flex-shrink: 0;
  background: linear-gradient(135deg, #1e3a5f, #0f3460);
  color: var(--accent2);
  border: 1.5px solid var(--border);
}}
.item-name {{
  flex: 1;
  font-size: .9rem;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.item-val {{
  font-size: .92rem;
  font-weight: 800;
  flex-shrink: 0;
  white-space: nowrap;
}}
.val-balance {{ color: var(--green); }}
.val-level   {{ color: var(--blue); }}
.val-ref     {{ color: var(--pink); }}

.empty {{
  text-align: center;
  padding: 60px 16px;
  color: var(--muted);
  font-size: .95rem;
}}

/* ── FOOTER ── */
footer {{
  text-align: center;
  color: #1e3a5f;
  font-size: .75rem;
  padding: 20px;
  letter-spacing: 1px;
}}
</style>
</head>
<body>

<header>
  <div class="logo">
    <div class="logo-icon">&#9889;</div>
    BLACKLINE
  </div>
  <div class="subtitle">Таблица лидеров</div>
</header>

<div class="tabs">
  <button class="tab-btn active" onclick="sw('balance',this)">&#128176; Баланс</button>
  <button class="tab-btn" onclick="sw('level',this)">&#11088; Уровень</button>
  <button class="tab-btn" onclick="sw('ref',this)">&#128101; Рефералы</button>
</div>

<div class="container">

  <div class="panel active" id="p-balance">
    {podium_balance}
    <div class="list">{list_balance}</div>
  </div>

  <div class="panel" id="p-level">
    {podium_level}
    <div class="list">{list_level}</div>
  </div>

  <div class="panel" id="p-ref">
    {podium_ref}
    <div class="list">{list_ref}</div>
  </div>

</div>

<footer>BLACKLINE &copy; 2025</footer>

<script>
function sw(name, btn) {{
  document.querySelectorAll('.panel').forEach(function(p){{ p.classList.remove('active'); }});
  document.querySelectorAll('.tab-btn').forEach(function(b){{ b.classList.remove('active'); }});
  document.getElementById('p-' + name).classList.add('active');
  btn.classList.add('active');
}}
</script>
</body>
</html>
"""


def fmt(n):
    n = float(n)
    if n >= 1_000_000_000_000:
        return f"{n/1_000_000_000_000:.1f}трлн"
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.1f}млрд"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}м"
    if n >= 1_000:
        return f"{n/1_000:.1f}к"
    return str(int(n))


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def letter(name):
    name = (name or "?").strip()
    return name[0].upper() if name else "?"


CROWN = {1: "&#128081;", 2: "&#129352;", 3: "&#129353;"}
POD_ORDER = {1: "pod-1", 2: "pod-2", 3: "pod-3"}


def build_podium(top3, val_fn):
    if not top3:
        return ""
    pods = []
    for rank in [1, 2, 3]:
        if rank > len(top3):
            pods.append(f'<div class="pod {POD_ORDER[rank]}"><div class="pod-rank">—</div><div class="pod-crown">&#8203;</div><div class="pod-avatar">?</div><div class="pod-name">—</div><div class="pod-val">—</div></div>')
            continue
        _, data = top3[rank - 1]
        name = esc(data.get("name") or "Без имени")
        val = val_fn(data)
        pods.append(
            f'<div class="pod {POD_ORDER[rank]}">'
            f'<div class="pod-rank"># {rank}</div>'
            f'<div class="pod-crown">{CROWN[rank]}</div>'
            f'<div class="pod-avatar">{letter(data.get("name","?"))}</div>'
            f'<div class="pod-name">{name}</div>'
            f'<div class="pod-val">{val}</div>'
            f'</div>'
        )
    return f'<div class="podium">{"".join(pods)}</div>'


def build_list(entries, val_fn, val_class):
    if not entries:
        return '<div class="empty">Нет данных</div>'
    rows = []
    for i, (_, data) in enumerate(entries[3:], 4):
        name = esc(data.get("name") or "Без имени")
        val = val_fn(data)
        av = letter(data.get("name", "?"))
        rows.append(
            f'<div class="item">'
            f'<div class="item-rank">{i}</div>'
            f'<div class="item-avatar">{av}</div>'
            f'<div class="item-name">{name}</div>'
            f'<div class="item-val {val_class}">{val}</div>'
            f'</div>'
        )
    return "".join(rows) if rows else ""


async def index(request):
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except Exception:
        users = {}

    items = list(users.items())

    top_balance = sorted(items, key=lambda x: x[1].get("balance", 0), reverse=True)[:18]
    top_level   = sorted(items, key=lambda x: (x[1].get("level", 1), x[1].get("experience", 0)), reverse=True)[:18]
    top_ref     = sorted(items, key=lambda x: len(x[1].get("referrals", [])), reverse=True)[:18]

    def bal_fn(d): return fmt(d.get("balance", 0)) + "$"
    def lvl_fn(d): return f"Lvl {d.get('level', 1)} · {fmt(d.get('experience', 0))} xp"
    def ref_fn(d): return str(len(d.get("referrals", []))) + " реф"

    html = HTML.format(
        podium_balance=build_podium(top_balance[:3], bal_fn),
        list_balance=build_list(top_balance, bal_fn, "val-balance"),
        podium_level=build_podium(top_level[:3], lvl_fn),
        list_level=build_list(top_level, lvl_fn, "val-level"),
        podium_ref=build_podium(top_ref[:3], ref_fn),
        list_ref=build_list(top_ref, ref_fn, "val-ref"),
    )
    return web.Response(text=html, content_type="text/html", charset="utf-8")


def make_app() -> web.Application:
    application = web.Application()
    application.router.add_get("/", index)
    return application
