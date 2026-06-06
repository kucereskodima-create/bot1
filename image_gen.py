import io
from PIL import Image, ImageDraw, ImageFont

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _f(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)
    except Exception:
        return ImageFont.load_default()


def _grad(w: int, h: int, c1: tuple, c2: tuple, horiz: bool = False) -> Image.Image:
    img  = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    n    = w if horiz else h
    for i in range(n):
        t = i / max(n - 1, 1)
        col = tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3))
        if horiz:
            draw.line([(i, 0), (i, h)], fill=col)
        else:
            draw.line([(0, i), (w, i)], fill=col)
    return img


def _to_buf(img: Image.Image) -> io.BytesIO:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ─── Компактная карточка профиля ─────────────────────────────────────────────
# Размер 680 × 370 — маленькая, но красивая

def gen_profile_card(d: dict) -> io.BytesIO:
    W, H = 680, 370
    # Тёмно-синий градиент — снизу чуть теплее
    img  = _grad(W, H, (10, 8, 30), (18, 24, 52))
    draw = ImageDraw.Draw(img)

    GOLD   = (212, 175, 55)
    WHITE  = (240, 240, 255)
    MUTED  = (110, 120, 160)
    GREEN  = (60,  210, 100)
    CYAN   = (60,  190, 230)
    ORANGE = (255, 160,  20)
    PURPLE = (160, 90,  240)
    DIM    = (28,  26,  58)
    BORDER = (38,  36,  78)

    # ── Золотая левая полоса ──
    draw.rectangle([(0, 0), (5, H)], fill=GOLD)

    # ── Шапка ──────────────────────────────────────────────────────────────
    draw.rectangle([(5, 0), (W, 58)], fill=(14, 12, 38))
    # Имя
    name = str(d.get("name", "Игрок"))[:22]
    draw.text((20, 10), name, font=_f(26), fill=WHITE)
    # VIP бейдж
    if d.get("vip"):
        draw.rounded_rectangle([(20 + _f(26).getlength(name) + 12, 12),
                                 (20 + _f(26).getlength(name) + 72, 40)],
                                radius=6, fill=(180, 130, 0))
        draw.text((20 + _f(26).getlength(name) + 18, 13), "VIP", font=_f(16), fill=(255, 235, 150))
    # ID + регистрация
    draw.text((20, 40), f"ID: {d.get('game_id','—')}   •   Рег.: {d.get('reg_date','—')}",
              font=_f(13, False), fill=MUTED)
    # Место в топе — правый угол
    rank_txt = f"#{d.get('rank','—')} в топе"
    rw = int(_f(14).getlength(rank_txt))
    draw.rounded_rectangle([(W - rw - 28, 14), (W - 10, 46)], radius=7, fill=DIM)
    draw.text((W - rw - 18, 18), rank_txt, font=_f(14), fill=GOLD)

    # ── Финансовый блок ─────────────────────────────────────────────────────
    y0 = 70
    draw.rounded_rectangle([(10, y0), (W - 10, y0 + 82)], radius=10, fill=DIM, outline=BORDER)
    draw.text((22, y0 + 8), "ФИНАНСЫ", font=_f(11, False), fill=MUTED)

    def kv(x, y, label, val, col):
        draw.text((x, y),      label, font=_f(12, False), fill=MUTED)
        draw.text((x, y + 16), val,   font=_f(18),        fill=col)

    kv(22,        y0 + 24, "Баланс",  f"{d.get('balance_fmt','0')}$",        GREEN)
    kv(220,       y0 + 24, "Банк",    f"{d.get('bank_fmt','0')}$",           CYAN)
    kv(420,       y0 + 24, "DC",      str(d.get("dc", 0)),                   PURPLE)
    kv(22,        y0 + 52, "BTC",     f"{d.get('btc_bal','0')} BTC",         ORANGE)
    draw.text((160, y0 + 66), f"~{d.get('btc_usd','0')}$", font=_f(13, False), fill=MUTED)

    # ── Прогресс ────────────────────────────────────────────────────────────
    y0 = 164
    draw.rounded_rectangle([(10, y0), (W - 10, y0 + 50)], radius=10, fill=DIM, outline=BORDER)
    draw.text((22, y0 + 6), f"УР. {d.get('level',1)}", font=_f(16), fill=WHITE)
    draw.text((100, y0 + 8), f"Опыт: {d.get('exp',0)} / {d.get('next_exp',100)}",
              font=_f(13, False), fill=MUTED)
    # Полоса опыта
    bx, by = 22, y0 + 30
    bw = W - 44
    ratio = min(d.get("exp", 0) / max(d.get("next_exp", 100), 1), 1.0)
    draw.rounded_rectangle([(bx, by), (bx + bw, by + 10)], radius=5, fill=(30, 28, 60))
    filled = max(int(bw * ratio), 0)
    if filled:
        # Градиентная полоска опыта
        for px in range(filled):
            t   = px / max(filled - 1, 1)
            col = (int(40 + 40 * t), int(160 + 50 * t), int(80 + 20 * t))
            draw.line([(bx + px, by), (bx + px, by + 10)], fill=col)

    # ── Нижний блок: Имущество | Ферма ──────────────────────────────────────
    y0   = 226
    half = (W - 26) // 2

    # Имущество
    draw.rounded_rectangle([(10, y0), (10 + half, y0 + 118)], radius=10, fill=DIM, outline=BORDER)
    draw.text((24, y0 + 8), "ИМУЩЕСТВО", font=_f(11, False), fill=MUTED)

    def prop(x, y, label, val, col=(200, 200, 220)):
        draw.text((x, y),      label, font=_f(11, False), fill=MUTED)
        draw.text((x, y + 14), str(val)[:22], font=_f(14), fill=col)

    prop(24, y0 + 26, "Авто",    d.get("car", "Нет"))
    prop(24, y0 + 60, "Дом",     d.get("house", "Нет"))
    prop(24, y0 + 94, "Работа",  d.get("work", "—"), MUTED)

    # Ферма & Гонки
    fx = 16 + half
    draw.rounded_rectangle([(fx, y0), (W - 10, y0 + 118)], radius=10, fill=DIM, outline=BORDER)
    draw.text((fx + 14, y0 + 8), "ФЕРМА & ГОНКИ", font=_f(11, False), fill=MUTED)
    farm_col = GREEN if "Актив" in str(d.get("farm_status", "")) else (180, 80, 80)
    prop(fx + 14, y0 + 26, "Ферма", f"{d.get('farm_name','—')} ур.{d.get('farm_lvl',0)}", farm_col)
    prop(fx + 14, y0 + 60, "Статус", d.get("farm_status", "—"), farm_col)
    prop(fx + 14, y0 + 94, "Авто",  d.get("race_car", "Нет")[:20], (220, 170, 70))

    # ── Нижняя золотая линия ─────────────────────────────────────────────────
    draw.rectangle([(5, H - 3), (W, H)], fill=GOLD)

    return _to_buf(img)


# ─── Карточка фермы ──────────────────────────────────────────────────────────

def gen_farm_card(d: dict) -> io.BytesIO:
    W, H = 720, 380
    img  = _grad(W, H, (4, 16, 8), (10, 32, 16))
    draw = ImageDraw.Draw(img)

    NEON  = (0,  210, 80)
    WHITE = (235, 255, 235)
    MUTED = (70,  140, 80)
    GOLD  = (255, 190,  0)
    CYAN  = (50,  210, 255)
    DIM   = (8,   30, 14)
    BDR   = (0,   65, 28)

    draw.rectangle([(0, 0), (6, H)], fill=NEON)
    draw.rectangle([(6, 0), (W, 62)], fill=(6, 22, 10))
    draw.text((22, 14), "BTC ФЕРМА  //  BLACKLINE", font=_f(26), fill=NEON)

    badge = f"Ур.{d.get('farm_lvl',0)}: {d.get('farm_name','—')}"
    bw    = int(_f(16).getlength(badge)) + 28
    draw.rounded_rectangle([(W - bw - 12, 14), (W - 12, 50)], radius=8, fill=(0, 65, 26))
    draw.text((W - bw - 2, 22), badge, font=_f(16), fill=NEON)

    # Статус
    status   = d.get("status", "Нет фермы")
    s_col    = (0, 255, 90) if "Актив" in status else (210, 70, 70)
    draw.text((22, 76), f"Статус: {status}", font=_f(20), fill=s_col)

    def box(x, y, lbl, val, col):
        draw.rounded_rectangle([(x, y), (x + 212, y + 88)], radius=10, fill=DIM, outline=BDR)
        draw.text((x + 14, y + 10), lbl, font=_f(12, False), fill=MUTED)
        draw.text((x + 14, y + 34), val, font=_f(22),        fill=col)

    box(12,  120, "BTC БАЛАНС",   f"{d.get('btc_bal','0')} BTC",  (0, 220, 110))
    box(236, 120, "В ДОЛЛАРАХ",   f"~{d.get('btc_usd','0')}$",    CYAN)
    box(460, 120, "ДОБЫЧА / ЧАС", f"{d.get('btc_per_hour',0)} BTC", GOLD)

    box(12,  224, "КУРС BTC",
        f"${d.get('btc_price',0):,}".replace(",", "."),            (200, 200, 200))
    box(236, 224, "УРОВЕНЬ",      f"{d.get('farm_lvl',0)} / 5",   (170, 90, 240))
    box(460, 224, "РЕЖИМ",        "Пассивный",                     (180, 220, 100))

    draw.rectangle([(6, H - 36), (W, H - 36)], fill=BDR)
    draw.text((22, H - 26), "Blackline Economy Bot  •  BTC Passive Mining",
              font=_f(13, False), fill=MUTED)
    draw.rectangle([(6, H - 3), (W, H)], fill=NEON, width=3)

    return _to_buf(img)


# ─── Карточка авто (гонки) ───────────────────────────────────────────────────

def gen_car_card(d: dict) -> io.BytesIO:
    W, H = 720, 360
    img  = _grad(W, H, (20, 12, 12), (38, 18, 18))
    draw = ImageDraw.Draw(img)

    RED   = (220, 40, 40)
    WHITE = (255, 250, 250)
    MUTED = (160, 90, 90)
    GOLD  = (255, 200, 50)
    DIM   = (30, 16, 16)
    BDR   = (72, 28, 28)

    draw.rectangle([(0, 0), (6, H)], fill=RED)
    draw.rectangle([(6, 0), (W, 60)], fill=(26, 14, 14))

    idx   = d.get("idx", 0)
    total = d.get("total", 20)
    draw.text((22, 14), f"ГОНОЧНЫЙ МАГАЗИН  //  {idx + 1} / {total}", font=_f(24), fill=RED)
    if d.get("is_dc"):
        draw.rounded_rectangle([(W - 112, 14), (W - 12, 48)], radius=7, fill=(70, 0, 140))
        draw.text((W - 100, 20), "ДОНАТ", font=_f(17), fill=(200, 110, 255))

    # Название авто
    draw.text((22, 74), str(d.get("name", "Авто"))[:36], font=_f(26), fill=WHITE)

    # Полоса скорости
    speed = d.get("speed", 0)
    bw    = W - 46
    ratio = min(speed / 420, 1.0)
    draw.rounded_rectangle([(22, 118), (22 + bw, 132)], radius=5, fill=(40, 18, 18))
    for px in range(int(bw * ratio)):
        t   = px / max(int(bw * ratio) - 1, 1)
        col = (int(180 + 40 * t), int(30 + 10 * t), int(20 + 10 * t))
        draw.line([(22 + px, 118), (22 + px, 132)], fill=col)
    draw.text((26, 136), f"СКОРОСТЬ: {speed} КМ/Ч", font=_f(14, False), fill=(255, 90, 90))

    def rbox(x, y, lbl, val, col):
        draw.rounded_rectangle([(x, y), (x + 212, y + 84)], radius=10, fill=DIM, outline=BDR)
        draw.text((x + 14, y + 10), lbl, font=_f(12, False), fill=MUTED)
        draw.text((x + 14, y + 34), val, font=_f(20),        fill=col)

    rbox(12,  170, "СТОИМОСТЬ", str(d.get("price_str", "—")), GOLD)
    rbox(236, 170, "СКОРОСТЬ",  f"{speed} КМ/Ч",              RED)
    rbox(460, 170, "СЛОТ",      "1 / 1",                      (140, 140, 200))

    owned    = str(d.get("owned_name", "Нет"))
    is_owned = d.get("is_owned", False)
    o_col    = (0, 200, 80) if is_owned else (150, 150, 150)
    draw.text((22, H - 50), f"Ваше авто: {owned[:30]}", font=_f(16), fill=o_col)
    if is_owned:
        draw.rounded_rectangle([(W - 188, H - 56), (W - 12, H - 22)], radius=8, fill=(0, 70, 26))
        draw.text((W - 176, H - 50), "УЖЕ КУПЛЕНО", font=_f(15), fill=(0, 200, 80))

    draw.rectangle([(6, H - 3), (W, H)], fill=RED)
    return _to_buf(img)


# ─── Воблер (бонус) ──────────────────────────────────────────────────────────

def gen_wobbler(amount_str: str, name: str, is_vip: bool = False) -> io.BytesIO:
    W, H = 720, 270
    c1   = (20, 5, 48)  if not is_vip else (55, 25, 0)
    c2   = (55, 10, 115) if not is_vip else (120, 56, 0)
    img  = _grad(W, H, c1, c2, horiz=True)
    draw = ImageDraw.Draw(img)

    ACC  = (255, 195, 0) if is_vip else (170, 55, 255)
    draw.rectangle([(0, 0), (W, 5)], fill=ACC)
    draw.rectangle([(0, H - 5), (W, H)], fill=ACC)
    draw.rectangle([(0, 0), (5, H)], fill=ACC)
    draw.rectangle([(W - 5, 0), (W, H)], fill=ACC)

    # Полукруги декора
    for cx, cy, r in [(640, 30, 90), (80, 200, 60)]:
        for dr in range(r, r + 45, 12):
            draw.ellipse([(cx - dr, cy - dr), (cx + dr, cy + dr)],
                         outline=(*ACC, 20), width=2)

    y0 = 18
    if is_vip:
        draw.rounded_rectangle([(18, y0), (100, y0 + 34)], radius=6, fill=(255, 155, 0))
        draw.text((28, y0 + 6), "VIP", font=_f(20), fill=(40, 14, 0))
        y0 += 42

    draw.text((18, y0),      "ЕЖЕДНЕВНЫЙ БОНУС", font=_f(36), fill=(255, 255, 255))
    draw.text((18, y0 + 48), f"+{amount_str}$",  font=_f(58), fill=ACC)
    draw.text((18, H - 46),  f"Получил: {name[:30]}", font=_f(19), fill=(190, 190, 200))
    draw.text((W - 180, H - 26), "BLACKLINE BOT", font=_f(13, False), fill=(100, 100, 155))

    return _to_buf(img)
