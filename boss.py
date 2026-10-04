"""Jefes finales: Granjero (fondos terrestres) y Astronauta (fondo Espacio)."""
import math
import random

import pygame

BOSS_NAMES = {"granjero": "GRANJERO", "astronauta": "ASTRONAUTA"}


def boss_kind_for_bg(bg_key):
    return "astronauta" if bg_key == "espacio" else "granjero"


def build_farmer():
    s = pygame.Surface((32, 44), pygame.SRCALPHA)
    f = s.fill
    f((150, 100, 50), (29, 8, 1, 30))                                    # asta del tridente
    f((170, 175, 185), (27, 8, 5, 1))
    for x in (27, 29, 31):
        f((200, 205, 215), (x, 4, 1, 5))
    f((230, 190, 90), (3, 6, 24, 3)); f((240, 205, 110), (8, 0, 14, 7))  # sombrero de paja
    f((150, 60, 40), (8, 5, 14, 2))
    f((240, 190, 150), (9, 9, 12, 9))                                    # cara
    f((20, 20, 30), (12, 12, 2, 2)); f((20, 20, 30), (17, 12, 2, 2))
    f((90, 40, 20), (11, 10, 3, 1)); f((90, 40, 20), (16, 10, 3, 1))     # cejas enojadas
    f((110, 60, 30), (10, 15, 10, 2))                                    # bigote
    f((200, 50, 50), (6, 18, 18, 12))                                    # camisa a cuadros
    for x in range(6, 24, 4):
        f((150, 30, 30), (x, 18, 1, 12))
    for y in range(20, 30, 4):
        f((150, 30, 30), (6, y, 18, 1))
    f((200, 50, 50), (2, 19, 4, 10)); f((200, 50, 50), (24, 19, 4, 10))  # brazos
    f((240, 190, 150), (2, 29, 4, 3)); f((240, 190, 150), (24, 29, 4, 3))
    f((50, 90, 180), (8, 24, 14, 10)); f((50, 90, 180), (9, 18, 2, 7)); f((50, 90, 180), (19, 18, 2, 7))
    f((255, 220, 60), (10, 25, 2, 2)); f((255, 220, 60), (18, 25, 2, 2))
    f((50, 90, 180), (9, 34, 5, 7)); f((50, 90, 180), (16, 34, 5, 7))
    f((90, 55, 30), (8, 41, 7, 3)); f((90, 55, 30), (15, 41, 7, 3))      # botas
    return s


def build_astronaut():
    s = pygame.Surface((30, 40), pygame.SRCALPHA)
    f = s.fill
    f((170, 170, 185), (2, 10, 6, 16))                                   # mochila
    f((235, 238, 245), (7, 16, 16, 14)); f((205, 210, 225), (20, 16, 3, 14))
    f((120, 125, 145), (11, 19, 8, 5)); f((230, 60, 60), (12, 20, 2, 2)); f((70, 220, 110), (16, 20, 2, 2))
    pygame.draw.ellipse(s, (235, 238, 245), (6, 1, 18, 17))              # casco
    pygame.draw.ellipse(s, (30, 50, 110), (9, 5, 12, 10))
    f((140, 190, 255), (11, 6, 4, 2))
    f((235, 238, 245), (3, 17, 4, 9)); f((235, 238, 245), (23, 17, 4, 9))
    f((240, 130, 40), (3, 25, 4, 3)); f((240, 130, 40), (23, 25, 4, 3))
    f((235, 238, 245), (9, 30, 5, 6)); f((235, 238, 245), (16, 30, 5, 6))
    f((240, 130, 40), (8, 36, 7, 3)); f((240, 130, 40), (15, 36, 7, 3))
    return s


class Boss:
    MAX_HP = 70

    def __init__(self, kind, w, ground_y):
        self.kind, self.w, self.ground_y = kind, w, ground_y
        self.img = build_farmer() if kind == "granjero" else build_astronaut()
        self.bw, self.bh = self.img.get_size()
        self.hp = self.MAX_HP
        self.x = w * 0.75
        self.dir = -1
        self.t = 0.0
        self.atk = 2.6            # pausa inicial: da tiempo a ver el cartel
        self.flash = 0.0
        self.proj = []

    @property
    def phase2(self):
        return self.hp <= self.MAX_HP / 2

    @property
    def top(self):
        if self.kind == "granjero":
            return self.ground_y + 4 - self.bh
        return 30 + math.sin(self.t * 1.7) * 8

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.bw / 2), int(self.top), self.bw, self.bh)

    def hurt(self):
        self.hp -= 1
        self.flash = 0.08

    def update(self, dt, duck_x, duck_y):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        speed = 55 if self.phase2 else 35
        self.x += self.dir * speed * dt
        if self.x < 26 or self.x > self.w - 26:
            self.dir *= -1
            self.x = max(26, min(self.w - 26, self.x))
        self.atk -= dt
        if self.atk <= 0:
            self._fire(duck_x, duck_y)
            self.atk = random.uniform(0.7, 1.1) if self.phase2 else random.uniform(1.3, 1.9)
        for p in self.proj:
            p["vy"] += p["g"] * dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["a"] += dt * 9
        self.proj = [p for p in self.proj
                     if -15 < p["x"] < self.w + 15 and -15 < p["y"] < self.ground_y + 8]

    def _fire(self, tx, ty):
        sx, sy = self.x, self.top + self.bh * 0.35
        if self.kind == "granjero":          # lanza tomates y tridentes en arco
            targets = [tx] if not self.phase2 else [tx - 28, tx + 28]
            for x in targets:
                T, g = 1.0, 140.0
                self.proj.append({"x": sx, "y": sy, "vx": (x - sx) / T, "vy": (ty - sy) / T - 0.5 * g * T,
                                  "g": g, "r": 4, "kind": random.choice(("tomate", "tridente")), "a": 0.0})
        else:                                # orbes de energia en linea recta
            base = math.atan2(ty - sy, tx - sx)
            angles = [base] if not self.phase2 else [base - 0.28, base, base + 0.28]
            for a in angles:
                self.proj.append({"x": sx, "y": sy, "vx": math.cos(a) * 85, "vy": math.sin(a) * 85,
                                  "g": 0.0, "r": 4, "kind": "orbe", "a": 0.0})

    def draw(self, surf):
        img = self.img
        if self.flash > 0:
            img = img.copy()
            img.fill((140, 140, 140, 0), special_flags=pygame.BLEND_RGB_ADD)
        r = self.rect
        if self.kind == "astronauta":        # llama del propulsor
            fl = 3 + int(self.t * 30) % 3
            surf.fill((255, 170, 40), (r.x + 8, r.bottom, 5, fl))
            surf.fill((255, 170, 40), (r.x + 16, r.bottom, 5, fl))
            surf.fill((255, 240, 150), (r.x + 9, r.bottom, 3, max(1, fl - 2)))
            surf.fill((255, 240, 150), (r.x + 17, r.bottom, 3, max(1, fl - 2)))
        surf.blit(img, r.topleft)
        for p in self.proj:
            x, y = int(p["x"]), int(p["y"])
            if p["kind"] == "tomate":
                pygame.draw.circle(surf, (220, 40, 40), (x, y), 4)
                surf.fill((60, 170, 60), (x - 1, y - 5, 3, 2))
                surf.set_at((x - 2, y - 2), (255, 160, 160))
            elif p["kind"] == "tridente":
                dx, dy = math.cos(p["a"]), math.sin(p["a"])
                pygame.draw.line(surf, (150, 100, 50), (x - dx * 5, y - dy * 5), (x + dx * 3, y + dy * 3))
                for off in (-2, 0, 2):
                    px, py = x + dx * 3 - dy * off, y + dy * 3 + dx * off
                    pygame.draw.line(surf, (210, 215, 225), (px, py), (px + dx * 3, py + dy * 3))
            else:
                pygame.draw.circle(surf, (120, 60, 200), (x, y), 5)
                pygame.draw.circle(surf, (90, 240, 255), (x, y), 3)
                surf.set_at((x - 1, y - 1), (255, 255, 255))
