"""Catalogo de skins (patos, armas y fondos) y funciones para dibujarlas."""
import math
import random

import pygame

# ---------------------------------------------------------------- patos
DUCK = [
    "...yyyy.....",
    "..yyyyyy....",
    "..yykyyyoo..",
    "..yyyyyooo..",
    "...yyyyy....",
    ".yyyyyyy....",
    "yyddyyyyyy..",
    "yddddyyyyyy.",
    "yyddyyyyyyy.",
    ".yyyyyyyyy..",
    "..yyyyyyy...",
    "...o..o.....",
]
DUCK_OFFSET = (2, 4)      # el pato va dentro de un lienzo de 16x16 para dejar sitio a accesorios
DUCK_CANVAS = 16

BASE_PAL = {"y": (255, 220, 40), "d": (230, 170, 20), "o": (240, 120, 20), "k": (20, 20, 30)}

# Cada skin: paleta (cambios sobre BASE_PAL) y lista de rectangulos/pixeles (color, x, y, w, h) sobre el lienzo.
DUCK_SKINS = {
    "clasico": {"name": "Clasico", "price": 0, "pal": {}, "over": []},
    "ninja": {
        "name": "Ninja", "price": 120,
        "pal": {"y": (80, 80, 108), "d": (52, 52, 74), "k": (255, 255, 255)},
        "over": [
            ((210, 40, 50), 4, 5, 6, 1),                      # cinta roja
            ((210, 40, 50), 2, 5, 2, 1), ((170, 25, 35), 1, 6, 2, 1),   # colas de la cinta
            ((255, 255, 255), 6, 6, 1, 1),
        ],
    },
    "playero": {
        "name": "Playero", "price": 90,
        "pal": {},
        "over": [
            ((240, 205, 110), 5, 2, 4, 2), ((240, 205, 110), 3, 4, 8, 1),   # sombrero de paja
            ((220, 60, 60), 5, 3, 4, 1),
            ((20, 20, 30), 5, 6, 4, 2), ((120, 200, 255), 5, 6, 1, 1),     # gafas de sol
        ],
    },
    "vaquero": {
        "name": "Vaquero", "price": 150,
        "pal": {},
        "over": [
            ((120, 70, 35), 5, 1, 4, 3), ((140, 85, 40), 3, 4, 9, 1), ((90, 50, 25), 5, 3, 4, 1),
            ((200, 40, 40), 4, 8, 6, 1),                                    # panuelo
        ],
    },
    "rey": {
        "name": "Rey", "price": 250,
        "pal": {"y": (255, 235, 90)},
        "over": [
            ((255, 200, 30), 5, 3, 4, 2), ((255, 200, 30), 5, 2, 1, 1), ((255, 200, 30), 7, 2, 1, 1),
            ((255, 200, 30), 8, 2, 1, 1), ((220, 40, 60), 6, 3, 1, 1),
            ((190, 40, 60), 3, 8, 2, 4),                                    # capa
        ],
    },
}


def build_duck(key):
    spec = DUCK_SKINS[key]
    pal = dict(BASE_PAL, **spec["pal"])
    s = pygame.Surface((DUCK_CANVAS, DUCK_CANVAS), pygame.SRCALPHA)
    ox, oy = DUCK_OFFSET
    for y, row in enumerate(DUCK):
        for x, c in enumerate(row):
            if c != ".":
                s.set_at((x + ox, y + oy), pal[c])
    for col, x, y, w, h in spec["over"]:
        s.fill(col, (x, y, w, h))
    return s


# ---------------------------------------------------------------- armas
# bullet: dot | laser | drop | shuriken | gold
GUN_SKINS = {
    "clasica": {"name": "Clasica", "price": 0, "body": (70, 70, 80), "tip": (150, 150, 160), "grip": (120, 70, 30),
                "len": 12, "thick": 2, "bullet": "dot", "color": (255, 240, 150), "flash": (255, 240, 120)},
    "dorada": {"name": "Dorada", "price": 100, "body": (230, 180, 40), "tip": (255, 235, 130), "grip": (150, 90, 20),
               "len": 12, "thick": 2, "bullet": "gold", "color": (255, 215, 60), "flash": (255, 230, 100)},
    "laser": {"name": "Laser", "price": 160, "body": (50, 60, 110), "tip": (90, 240, 255), "grip": (40, 40, 70),
              "len": 13, "thick": 2, "bullet": "laser", "color": (90, 240, 255), "flash": (160, 255, 255)},
    "agua": {"name": "De agua", "price": 70, "body": (60, 190, 90), "tip": (60, 130, 240), "grip": (240, 120, 40),
             "len": 11, "thick": 3, "bullet": "drop", "color": (80, 170, 255), "flash": (150, 210, 255)},
    "shuriken": {"name": "Shuriken", "price": 200, "body": (35, 35, 45), "tip": (200, 40, 50), "grip": (30, 30, 36),
                 "len": 12, "thick": 2, "bullet": "shuriken", "color": (210, 215, 230), "flash": (255, 120, 120)},
}


def draw_gun(surf, key, px, py, angle, recoil=0.0, flash=False):
    g = GUN_SKINS[key]
    ca, sa = math.cos(angle), math.sin(angle)
    t = g["thick"]
    for i in range(2, g["len"] + 1):
        col = g["tip"] if i >= g["len"] - 1 else g["body"]
        d = i - recoil
        surf.fill(col, (int(px + ca * d), int(py + sa * d), t, t))
    surf.fill(g["grip"], (int(px + ca * 3), int(py + sa * 3 + 2), 2, 3))      # empunadura
    if flash:
        m = g["len"] + 3
        surf.fill(g["flash"], (int(px + ca * m), int(py + sa * m), 3, 3))


def draw_bullet(surf, key, x, y, vx, vy, ticks):
    g = GUN_SKINS[key]
    style, col = g["bullet"], g["color"]
    x, y = int(x), int(y)
    if style == "laser":
        n = math.hypot(vx, vy) or 1
        ex, ey = x - vx / n * 7, y - vy / n * 7
        pygame.draw.line(surf, (40, 150, 200), (x, y), (int(ex), int(ey)), 3)
        pygame.draw.line(surf, col, (x, y), (int(ex), int(ey)), 1)
    elif style == "drop":
        pygame.draw.circle(surf, col, (x, y), 2)
        surf.set_at((x - 1, y - 1), (230, 245, 255))
    elif style == "shuriken":
        pts = ((0, -2), (0, 2), (-2, 0), (2, 0)) if (ticks // 60) % 2 else ((-2, -2), (2, 2), (-2, 2), (2, -2))
        for dx, dy in pts:
            surf.set_at((x + dx, y + dy), col)
        surf.set_at((x, y), (120, 125, 140))
        surf.set_at((x + 1, y), (120, 125, 140))
    elif style == "gold":
        surf.fill(col, (x - 1, y - 1, 3, 3))
        surf.set_at((x - 1, y - 1), (255, 255, 255))
    else:
        surf.fill(col, (x - 1, y - 1, 3, 3))


# ---------------------------------------------------------------- fondos
BG_SKINS = {
    "pradera": {"name": "Pradera", "price": 0, "clouds": True, "dark": False},
    "playa": {"name": "Playa", "price": 130, "clouds": True, "dark": False},
    "noche": {"name": "Noche", "price": 110, "clouds": False, "dark": True},
    "espacio": {"name": "Espacio", "price": 220, "clouds": False, "dark": True},
}


def _gradient(bg, w, y0, y1, top, bottom):
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0 - 1)
        bg.fill(tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)), (0, y, w, 1))


def _hills(bg, w, h, layers):
    for base, col, amp, freq in layers:
        for x in range(w):
            top = int(base - amp - amp * math.sin(x * freq + base))
            bg.fill(col, (x, top, 1, h - top))


def _ground(bg, w, h, gy, col, edge, speck):
    bg.fill(col, (0, gy + 8, w, h - gy - 8))
    bg.fill(edge, (0, gy + 8, w, 2))
    for _ in range(60):
        bg.set_at((random.randint(0, w - 1), random.randint(gy + 11, h - 1)), speck)


def _stars(bg, w, gy, n, seed):
    rnd = random.Random(seed)
    for _ in range(n):
        x, y = rnd.randint(0, w - 1), rnd.randint(0, gy - 20)
        c = rnd.choice(((255, 255, 255), (200, 210, 255), (255, 240, 180)))
        bg.set_at((x, y), c)
        if rnd.random() < 0.15:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                bg.set_at((x + dx, y + dy), tuple(v // 2 for v in c))


def build_background(key, w, h, gy):
    bg = pygame.Surface((w, h))
    if key == "playa":
        _gradient(bg, w, 0, gy, (90, 200, 255), (200, 240, 255))
        pygame.draw.circle(bg, (255, 235, 120), (60, 30), 15)
        pygame.draw.circle(bg, (255, 250, 200), (60, 30), 11)
        sea = gy - 38
        _gradient(bg, w, sea, gy + 8, (40, 150, 220), (70, 200, 230))
        for y in range(sea + 4, gy, 7):                              # olitas
            for x in range(random.randint(0, 10), w, 18):
                bg.fill((200, 240, 255), (x, y, 5, 1))
        bg.fill((255, 255, 255), (0, sea, w, 1))
        _ground(bg, w, h, gy, (240, 215, 140), (255, 235, 170), (215, 185, 110))
        # palmera
        for i in range(36):
            bg.fill((120, 80, 40), (268 + int(math.sin(i / 14) * 5), gy + 8 - i, 3, 1))
        tx, ty = 268 + int(math.sin(36 / 14) * 5), gy + 8 - 36
        for ang in (-2.6, -2.0, -1.3, -0.6, 0.1):
            for r in range(1, 17):
                px, py = tx + math.cos(ang) * r, ty + math.sin(ang) * r * 0.6 + (r * r) / 40
                bg.fill((40, 160, 70), (int(px), int(py), 2, 2))
    elif key == "noche":
        _gradient(bg, w, 0, gy, (10, 12, 40), (50, 40, 90))
        _stars(bg, w, gy, 70, 1)
        pygame.draw.circle(bg, (240, 240, 220), (255, 34), 14)
        pygame.draw.circle(bg, (10, 12, 40), (261, 30), 12)          # luna creciente
        _hills(bg, w, h, ((gy - 6, (30, 30, 62), 18, 0.02), (gy, (20, 20, 44), 10, 0.035)))
        # pagoda en silueta
        for lvl in range(3):
            y = gy - 6 - lvl * 11
            bg.fill((12, 12, 28), (60 + lvl * 3, y, 24 - lvl * 6, 8))
            pygame.draw.polygon(bg, (12, 12, 28), [(54 + lvl * 3, y), (90 - lvl * 3, y), (84 - lvl * 3, y - 4), (60 + lvl * 3, y - 4)])
        _ground(bg, w, h, gy, (22, 24, 40), (45, 50, 80), (35, 38, 62))
    elif key == "espacio":
        bg.fill((6, 4, 20))
        _gradient(bg, w, 0, gy, (6, 4, 20), (40, 20, 70))
        _stars(bg, w, gy, 120, 2)
        pygame.draw.circle(bg, (200, 110, 60), (250, 45), 20)         # planeta con anillo
        pygame.draw.circle(bg, (230, 150, 90), (245, 40), 13)
        pygame.draw.ellipse(bg, (230, 210, 170), (222, 40, 56, 10), 1)
        pygame.draw.circle(bg, (150, 160, 190), (60, 40), 8)
        _hills(bg, w, h, ((gy - 2, (70, 70, 95), 8, 0.05), (gy + 3, (55, 55, 78), 5, 0.08)))
        _ground(bg, w, h, gy, (80, 80, 105), (120, 120, 150), (60, 60, 85))
        for cx in (90, 200):                                           # crateres
            pygame.draw.ellipse(bg, (60, 60, 85), (cx, gy + 18, 22, 6))
    else:  # pradera
        _gradient(bg, w, 0, gy, (110, 190, 255), (200, 230, 255))
        pygame.draw.circle(bg, (255, 240, 130), (270, 32), 14)
        pygame.draw.circle(bg, (255, 255, 200), (270, 32), 10)
        _hills(bg, w, h, ((gy - 6, (90, 170, 110), 18, 0.02), (gy, (60, 140, 70), 10, 0.035)))
        _ground(bg, w, h, gy, (70, 170, 60), (100, 200, 80), (50, 140, 45))
    return bg


# ---------------------------------------------------------------- tienda
CATEGORIES = [("duck", "PATOS", DUCK_SKINS), ("gun", "ARMAS", GUN_SKINS), ("bg", "FONDOS", BG_SKINS)]
DEFAULT_EQUIPPED = {"duck": "clasico", "gun": "clasica", "bg": "pradera"}
