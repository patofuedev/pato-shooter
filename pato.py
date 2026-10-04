"""Pato Pistolero - un juego pixel art hecho con pygame.

Controles:
  A/D o flechas  -> mover al pato
  Mouse          -> apuntar
  Click / Espacio-> disparar
  R              -> recargar
  T              -> tienda (en el menu)
  Etapas         -> supera 600 puntos en cada una; tras la 10 hay un jefe final
  Esc            -> salir / volver
"""
import array
import json
import math
import os
import random

import pygame

from boss import BOSS_NAMES, Boss, boss_kind_for_bg
from skins import (BG_SKINS, CATEGORIES, DEFAULT_EQUIPPED, DUCK_SKINS, GUN_SKINS,
                   build_background, build_duck, draw_bullet, draw_gun)

W, H = 320, 180          # resolucion interna (pixel art)
SCALE = 4                # ventana = 1280x720
GROUND_Y = 150
GAME_TIME = 60.0         # segundos por etapa
STAGES = 10
STAGE_GOAL = 600         # hay que superar estos puntos para pasar de etapa
BOSS_COINS = 500
DUCK_LIVES = 3
MAX_AMMO = 8
RELOAD_TIME = 0.8
BULLET_SPEED = 320
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_FILE = os.path.join(BASE_DIR, ".save.json")
OLD_SCORE_FILE = os.path.join(BASE_DIR, ".highscore.json")

RATE = 22050


def synth(duration, fn):
    """Genera un Sound mono de 16 bits; fn(t, progreso) -> muestra en [-1, 1]."""
    n = int(RATE * duration)
    buf = array.array("h", (int(max(-1, min(1, fn(i / RATE, i / n))) * 32000 * 0.5) for i in range(n)))
    return pygame.mixer.Sound(buffer=buf.tobytes())


def make_sounds():
    noise = random.random
    sounds = {
        # disparo: estallido de ruido + golpe grave que cae
        "shoot": synth(0.22, lambda t, p: ((noise() * 2 - 1) * 0.8 + math.sin(math.tau * (180 - 140 * p) * t)) * (1 - p) ** 2.5),
        # impacto: "pop" de tono que baja + chispa de ruido
        "hit": synth(0.18, lambda t, p: (math.sin(math.tau * (700 - 500 * p) * t) * 0.8 + (noise() * 2 - 1) * 0.4) * (1 - p) ** 2),
        # estrella: campanita de dos notas
        "star": synth(0.4, lambda t, p: (math.sin(math.tau * 880 * t) + (math.sin(math.tau * 1320 * t) if p > 0.25 else 0)) * 0.5 * (1 - p) ** 1.5),
        # sin balas
        "click": synth(0.05, lambda t, p: (noise() * 2 - 1) * (1 - p) ** 3 * 0.6),
        # compra: dos notas ascendentes
        "buy": synth(0.3, lambda t, p: math.sin(math.tau * (660 if p < 0.35 else 990) * t) * 0.6 * (1 - p) ** 1.5),
        # sin monedas
        "deny": synth(0.18, lambda t, p: (1 if int(t * 90) % 2 else -1) * 0.4 * (1 - p)),
        # golpe recibido
        "hurt": synth(0.3, lambda t, p: math.sin(math.tau * (300 - 220 * p) * t) * 0.8 * (1 - p)),
        # recarga: dos clicks metalicos
        "reload": synth(0.3, lambda t, p: math.sin(math.tau * 1200 * t) * (1 - ((p * 5) % 1)) ** 4 * (1 if p < 0.15 or 0.55 < p < 0.7 else 0)),
    }
    return sounds


def make_bullseye():
    s = pygame.Surface((13, 18), pygame.SRCALPHA)
    pygame.draw.rect(s, (120, 80, 40), (6, 12, 2, 6))
    for r, col in ((6, (240, 240, 240)), (5, (220, 40, 40)), (3, (240, 240, 240)), (1, (220, 40, 40))):
        pygame.draw.circle(s, col, (6, 6), r)
    return s


def make_balloon(color):
    s = pygame.Surface((11, 18), pygame.SRCALPHA)
    pygame.draw.ellipse(s, color, (0, 0, 11, 13))
    pygame.draw.rect(s, (255, 255, 255), (2, 2, 2, 2))
    pygame.draw.polygon(s, color, [(4, 12), (7, 12), (5, 14)])
    pygame.draw.line(s, (200, 200, 200), (5, 14), (5, 17))
    return s


def make_can():
    s = pygame.Surface((8, 10), pygame.SRCALPHA)
    pygame.draw.rect(s, (190, 190, 200), (0, 0, 8, 10))
    pygame.draw.rect(s, (220, 50, 50), (0, 3, 8, 4))
    pygame.draw.rect(s, (255, 255, 255), (1, 4, 2, 2))
    pygame.draw.rect(s, (120, 120, 130), (0, 0, 8, 1))
    pygame.draw.rect(s, (120, 120, 130), (0, 9, 8, 1))
    return s


def make_star():
    s = pygame.Surface((13, 13), pygame.SRCALPHA)
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = 6 if i % 2 == 0 else 2.5
        pts.append((6 + r * math.cos(a), 6 + r * math.sin(a)))
    pygame.draw.polygon(s, (255, 210, 30), pts)
    pygame.draw.polygon(s, (255, 250, 150), [(6, 2), (7, 5), (6, 6)])
    return s


class Target:
    def __init__(self, kind, img, x, y, vx, vy, r, points, gravity=0.0, wobble=0.0):
        self.kind, self.img = kind, img
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.r, self.points, self.gravity, self.wobble = r, points, gravity, wobble
        self.t = random.random() * 6
        self.angle = 0.0
        self.spin = random.uniform(-400, 400) if kind == "can" else 0.0
        self.alive = True

    def update(self, dt):
        self.t += dt
        self.vy += self.gravity * dt
        self.x += self.vx * dt + math.sin(self.t * 3) * self.wobble * dt
        self.y += self.vy * dt
        self.angle += self.spin * dt
        if self.x < -30 or self.x > W + 30 or self.y < -30 or self.y > GROUND_Y + 8:
            self.alive = False

    def draw(self, surf):
        img = self.img
        if self.spin:
            img = pygame.transform.rotate(img, self.angle)
        surf.blit(img, img.get_rect(center=(int(self.x), int(self.y))))


class Particle:
    def __init__(self, x, y, color):
        a = random.uniform(0, math.tau)
        v = random.uniform(30, 110)
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(a) * v, math.sin(a) * v - 30
        self.life = random.uniform(0.3, 0.7)
        self.color = color

    def update(self, dt):
        self.life -= dt
        self.vy += 220 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt


class Game:
    def __init__(self):
        pygame.mixer.pre_init(RATE, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption("Pato Pistolero")
        self.window = pygame.display.set_mode((W * SCALE, H * SCALE))
        self.screen = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 14)
        self.big = pygame.font.Font(None, 30)
        pygame.mouse.set_visible(False)

        try:
            self.sounds = make_sounds()
        except pygame.error:   # sin dispositivo de audio: se juega en silencio
            self.sounds = {}

        self.bullseye = make_bullseye()
        self.balloons = [make_balloon(c) for c in ((230, 60, 60), (60, 140, 240), (80, 200, 90), (200, 90, 220))]
        self.can = make_can()
        self.star = make_star()
        self.clouds = [(random.randint(0, W), random.randint(10, 60), random.randint(18, 34)) for _ in range(5)]
        self.save = self._load_save()
        self.high = self.save["high"]
        self.duck_cache = {k: build_duck(k) for k in DUCK_SKINS}
        self.bg_cache = {k: build_background(k, W, H, GROUND_Y) for k in BG_SKINS}
        self.shop_tab = 0
        self.shop_msg = ("", 0.0)
        self.state = "title"
        self.prev_state = "title"
        self.coins_run = 0
        self.reset_armed = 0.0
        self.reset()

    # ---------- utilidades ----------
    def _load_save(self):
        data = {"high": 0, "coins": 0, "owned": {c: [DEFAULT_EQUIPPED[c]] for c, _, _ in CATEGORIES},
                "equipped": dict(DEFAULT_EQUIPPED), "stage": 1, "wins": 0}
        try:
            with open(OLD_SCORE_FILE) as f:            # migrar el record de versiones anteriores
                data["high"] = int(json.load(f))
        except (OSError, ValueError, TypeError):
            pass
        try:
            with open(SAVE_FILE) as f:
                raw = json.load(f)
            data["high"] = int(raw.get("high", data["high"]))
            data["coins"] = max(0, int(raw.get("coins", 0)))
            data["stage"] = min(STAGES + 1, max(1, int(raw.get("stage", 1))))
            data["wins"] = max(0, int(raw.get("wins", 0)))
            for cat, _, skins in CATEGORIES:
                owned = [k for k in raw.get("owned", {}).get(cat, []) if k in skins]
                data["owned"][cat] = sorted(set(owned) | {DEFAULT_EQUIPPED[cat]})
                eq = raw.get("equipped", {}).get(cat)
                if eq in data["owned"][cat]:
                    data["equipped"][cat] = eq
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        return data

    def _save_game(self):
        self.save["high"] = self.high
        try:
            with open(SAVE_FILE, "w") as f:
                json.dump(self.save, f)
        except OSError:
            pass

    @property
    def eq(self):
        return self.save["equipped"]

    @property
    def stage(self):
        return self.save["stage"]     # 1..STAGES = etapas, STAGES+1 = jefe final

    def play(self, name):
        if name in self.sounds:
            self.sounds[name].play()

    def text(self, msg, x, y, color=(255, 255, 255), font=None, center=False):
        font = font or self.font
        shadow = font.render(msg, False, (30, 30, 50))
        img = font.render(msg, False, color)
        rect = img.get_rect(midtop=(x, y)) if center else img.get_rect(topleft=(x, y))
        self.screen.blit(shadow, rect.move(1, 1))
        self.screen.blit(img, rect)

    def reset(self):
        self.duck_x = W / 2
        self.facing = 1
        self.bullets, self.targets, self.particles, self.popups = [], [], [], []
        self.score = 0
        self.combo = 0
        self.ammo = MAX_AMMO
        self.reload = 0.0
        self.time_left = GAME_TIME
        self.spawn_cd = 0.5
        self.shake = 0.0
        self.recoil = 0.0
        self.hits = self.shots = 0
        self.coins_run = 0
        self.boss = None
        self.lives = DUCK_LIVES
        self.invuln = 0.0
        self.banner = 0.0
        self.fail_reason = ""
        self.bonus = 0
        self.cleared_stage = 0

    def start_run(self):
        self.reset()
        if self.stage > STAGES:
            self.boss = Boss(boss_kind_for_bg(self.eq["bg"]), W, GROUND_Y)
            self.banner = 2.5
        self.state = "play"

    def end_run(self, state):
        if self.score > self.high:
            self.high = self.score
        self._save_game()
        self.state = state

    # ---------- logica ----------
    def mouse(self):
        mx, my = pygame.mouse.get_pos()
        return mx / SCALE, my / SCALE

    def gun_pivot(self):
        return self.duck_x, GROUND_Y - 4

    def aim_angle(self):
        px, py = self.gun_pivot()
        mx, my = self.mouse()
        return math.atan2(my - py, mx - px)

    def shoot(self):
        if self.reload > 0:
            return
        if self.ammo <= 0:
            self.play("click")
            self.reload = RELOAD_TIME
            return
        a = self.aim_angle()
        px, py = self.gun_pivot()
        self.bullets.append([px + math.cos(a) * 16, py + math.sin(a) * 16,
                             math.cos(a) * BULLET_SPEED, math.sin(a) * BULLET_SPEED])
        self.ammo -= 1
        self.shots += 1
        self.play("shoot")
        self.shake = 0.12
        self.recoil = 1.0
        for _ in range(4):
            self.particles.append(Particle(px + math.cos(a) * 17, py + math.sin(a) * 17, GUN_SKINS[self.eq['gun']]['flash']))
        if self.ammo == 0:
            self.reload = RELOAD_TIME
            self.play("reload")

    def spawn(self, spd=1.0):
        n = len(self.targets)
        r = random.random()
        if r < 0.40:
            self.targets.append(Target("balloon", random.choice(self.balloons), random.randint(20, W - 20), GROUND_Y + 5,
                                       0, -random.uniform(22, 40), 6, 5, wobble=random.uniform(10, 30)))
        elif r < 0.70:
            d = random.choice((-1, 1))
            self.targets.append(Target("bullseye", self.bullseye, -10 if d > 0 else W + 10, random.randint(30, 105),
                                       d * random.uniform(40, 80), 0, 7, 10))
        elif r < 0.93:
            d = random.choice((-1, 1))
            self.targets.append(Target("can", self.can, -5 if d > 0 else W + 5, random.randint(100, 140),
                                       d * random.uniform(60, 110), -random.uniform(110, 160), 5, 15, gravity=150))
        else:
            d = random.choice((-1, 1))
            self.targets.append(Target("star", self.star, -10 if d > 0 else W + 10, random.randint(15, 70),
                                       d * random.uniform(110, 150), 0, 7, 50, wobble=60))
        for t in self.targets[n:]:
            t.vx *= spd

    def burst(self, t):
        cols = {"balloon": (230, 80, 80), "bullseye": (240, 240, 240), "can": (200, 200, 210), "star": (255, 220, 50)}
        for _ in range(14):
            self.particles.append(Particle(t.x, t.y, cols[t.kind]))

    def update(self, dt):
        keys = pygame.key.get_pressed()
        move = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        self.duck_x = max(8, min(W - 8, self.duck_x + move * 110 * dt))
        self.facing = 1 if self.mouse()[0] >= self.duck_x else -1

        if self.reload > 0:
            self.reload -= dt
            if self.reload <= 0:
                self.reload = 0
                self.ammo = MAX_AMMO
        self.shake = max(0, self.shake - dt)
        self.recoil = max(0, self.recoil - dt * 8)
        self.invuln = max(0, self.invuln - dt)

        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.popups:
            p[1] -= 20 * dt
            p[2] -= dt
        self.popups = [p for p in self.popups if p[2] > 0]

        if self.boss:
            self.update_boss(dt)
        else:
            self.update_stage(dt)

    def update_stage(self, dt):
        n = self.stage - 1            # cada etapa: objetivos mas rapidos y mas frecuentes
        self.time_left -= dt
        if self.time_left <= 0:
            self.time_left = 0
            self.fail_reason = "time"
            self.end_run("over")
            return

        self.spawn_cd -= dt
        if self.spawn_cd <= 0:
            self.spawn(1 + 0.07 * n)
            self.spawn_cd = random.uniform(0.35, 0.9) / (1 + 0.06 * n)

        for t in self.targets:
            t.update(dt)

        for b in self.bullets:
            b[0] += b[2] * dt
            b[1] += b[3] * dt
        survivors = []
        for b in self.bullets:
            hit = False
            for t in self.targets:
                if t.alive and (b[0] - t.x) ** 2 + (b[1] - t.y) ** 2 <= (t.r + 1) ** 2:
                    t.alive = False
                    self.combo += 1
                    self.hits += 1
                    mult = 1 + min(self.combo - 1, 9) // 3
                    gained = t.points * mult
                    self.score += gained
                    coins = max(1, gained // 5)
                    self.save["coins"] += coins
                    self.coins_run += coins
                    self.popups.append([t.x, t.y, 0.8, f"+{gained}" + (f" x{mult}" if mult > 1 else "")])
                    self.burst(t)
                    self.play("star" if t.kind == "star" else "hit")
                    hit = True
                    break
            if hit:
                continue
            if -10 < b[0] < W + 10 and -10 < b[1] < H + 10:
                survivors.append(b)
            elif b[1] <= GROUND_Y + 12:   # se fue por arriba/lados: combo roto
                self.combo = 0
        self.bullets = survivors
        self.targets = [t for t in self.targets if t.alive]

        if self.score > STAGE_GOAL:
            self.bonus = 25 * self.stage
            self.save["coins"] += self.bonus
            self.coins_run += self.bonus
            self.cleared_stage = self.stage
            self.save["stage"] = self.stage + 1
            self.play("buy")
            self.end_run("clear")

    def gain_coins(self, n):
        self.save["coins"] += n
        self.coins_run += n

    def update_boss(self, dt):
        boss = self.boss
        duck_y = GROUND_Y - 2
        boss.update(dt, self.duck_x, duck_y)

        survivors = []
        for b in self.bullets:
            b[0] += b[2] * dt
            b[1] += b[3] * dt
            if boss.rect.collidepoint(b[0], b[1]):
                boss.hurt()
                self.hits += 1
                self.gain_coins(1)
                self.play("hit")
                for _ in range(5):
                    self.particles.append(Particle(b[0], b[1], (255, 240, 150)))
                continue
            shot = next((p for p in boss.proj if (b[0] - p["x"]) ** 2 + (b[1] - p["y"]) ** 2 <= (p["r"] + 2) ** 2), None)
            if shot:                  # los proyectiles del jefe se pueden derribar a tiros
                boss.proj.remove(shot)
                self.hits += 1
                self.gain_coins(2)
                self.play("hit")
                self.popups.append([shot["x"], shot["y"], 0.6, "+2"])
                for _ in range(8):
                    self.particles.append(Particle(shot["x"], shot["y"], (255, 255, 255)))
                continue
            if -10 < b[0] < W + 10 and -10 < b[1] < H + 10:
                survivors.append(b)
        self.bullets = survivors

        if self.invuln <= 0:
            for p in boss.proj:
                if (p["x"] - self.duck_x) ** 2 + (p["y"] - duck_y) ** 2 <= (p["r"] + 5) ** 2:
                    boss.proj.remove(p)
                    self.lives -= 1
                    self.invuln = 1.6
                    self.shake = 0.3
                    self.play("hurt")
                    for _ in range(12):
                        self.particles.append(Particle(self.duck_x, duck_y, (255, 80, 80)))
                    break

        if boss.hp <= 0:
            for _ in range(60):
                self.particles.append(Particle(boss.x, boss.top + boss.bh / 2, random.choice(((255, 220, 60), (255, 120, 40), (255, 255, 255)))))
            self.gain_coins(BOSS_COINS)
            self.save["stage"] = 1
            self.save["wins"] += 1
            self.play("star")
            self.end_run("victory")
        elif self.lives <= 0:
            self.fail_reason = "boss"
            self.end_run("over")

    # ---------- dibujo ----------
    def draw_duck(self):
        a = self.aim_angle()
        px, py = self.gun_pivot()
        img = self.duck_cache[self.eq["duck"]]
        if self.facing < 0:
            img = pygame.transform.flip(img, True, False)
        if self.invuln > 0 and int(self.invuln * 14) % 2:
            return
        bob = 1 if int(pygame.time.get_ticks() / 250) % 2 and pygame.key.get_pressed()[pygame.K_a] else 0
        self.screen.blit(img, (int(self.duck_x - 8), GROUND_Y - 12 - bob))
        draw_gun(self.screen, self.eq["gun"], px, py, a, self.recoil * 2, self.recoil > 0.7)

    def draw_coin(self, x, y):
        pygame.draw.circle(self.screen, (200, 140, 20), (x + 3, y + 3), 4)
        pygame.draw.circle(self.screen, (255, 215, 50), (x + 3, y + 3), 3)
        self.screen.fill((255, 245, 170), (x + 2, y + 1, 1, 2))

    def draw_coins_total(self):
        label = str(self.save["coins"])
        w = self.font.size(label)[0]
        self.text(label, W - 4 - w, 3, (255, 225, 90))
        self.draw_coin(W - 4 - w - 10, 3)

    HEART = ("01010", "11111", "11111", "01110", "00100")

    def draw_hearts(self):
        for i in range(DUCK_LIVES):
            col = (230, 50, 70) if i < self.lives else (70, 60, 80)
            for y, row in enumerate(self.HEART):
                for x, c in enumerate(row):
                    if c == "1":
                        self.screen.set_at((4 + i * 8 + x, 4 + y), col)

    def draw_hud(self):
        if self.boss:
            self.draw_hearts()
            name = "JEFE: " + BOSS_NAMES[self.boss.kind]
            self.text(name, W // 2, 3, (255, 120, 120), center=True)
            bar = pygame.Rect(W // 2 - 50, 14, 100, 6)
            pygame.draw.rect(self.screen, (40, 20, 30), bar)
            self.screen.fill((230, 60, 70) if not self.boss.phase2 else (255, 150, 40),
                             (bar.x, bar.y, int(bar.w * max(0, self.boss.hp) / self.boss.MAX_HP), bar.h))
            pygame.draw.rect(self.screen, (255, 255, 255), bar, 1)
            if self.banner > 0:
                self.text("JEFE FINAL", W // 2, 62, (255, 90, 90), self.big, center=True)
                self.text(BOSS_NAMES[self.boss.kind], W // 2, 86, (255, 220, 120), center=True)
        else:
            self.text(f"ETAPA {self.stage}/{STAGES}", 4, 3, (255, 230, 120))
            self.text(f"PUNTOS {self.score}/{STAGE_GOAL}", 4, 13)
            bar = pygame.Rect(4, 24, 70, 4)
            pygame.draw.rect(self.screen, (30, 30, 50), bar)
            self.screen.fill((90, 230, 120), (bar.x, bar.y, int(bar.w * min(1, self.score / STAGE_GOAL)), bar.h))
            pygame.draw.rect(self.screen, (255, 255, 255), bar, 1)
            self.text(f"{int(math.ceil(self.time_left)):02d}s", W // 2, 3, (255, 255, 255) if self.time_left > 10 else (255, 90, 90), center=True)
            if self.combo >= 2:
                self.text(f"COMBO {self.combo}", W // 2, 13, (255, 200, 80), center=True)
        # balas
        for i in range(MAX_AMMO):
            col = (255, 220, 80) if i < self.ammo else (70, 70, 80)
            self.screen.fill(col, (W - 6 - i * 5, 5, 3, 7))
        label = f"+{self.coins_run}"
        self.text(label, W - 4 - self.font.size(label)[0], 25, (255, 225, 90))
        self.draw_coin(W - 4 - self.font.size(label)[0] - 10, 25)
        if self.reload > 0:
            self.text("RECARGANDO...", W - 4 - self.font.size("RECARGANDO...")[0], 14, (255, 150, 90))

    menu_btn = pygame.Rect(W // 2 - 32, 142, 64, 16)
    back_btn = pygame.Rect(W - 70, 150, 60, 16)
    reset_btn = pygame.Rect(4, 160, 70, 16)

    def draw_button(self, rect, label):
        hot = rect.collidepoint(self.mouse())
        pygame.draw.rect(self.screen, (255, 200, 60) if hot else (60, 60, 90), rect)
        pygame.draw.rect(self.screen, (255, 255, 255), rect, 1)
        self.text(label, rect.centerx, rect.y + 4, (30, 30, 50) if hot else (255, 255, 255), center=True)

    def tab_rect(self, i):
        return pygame.Rect(12 + i * 98, 6, 94, 16)

    def card_rect(self, i):
        return pygame.Rect(12 + i * 60, 30, 56, 108)

    def draw_shop(self):
        s = self.screen
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((15, 15, 35, 225))
        s.blit(dim, (0, 0))
        mouse = self.mouse()
        now = pygame.time.get_ticks()
        for i, (cat, label, _) in enumerate(CATEGORIES):
            r = self.tab_rect(i)
            active = i == self.shop_tab
            pygame.draw.rect(s, (255, 200, 60) if active else (60, 60, 90), r)
            pygame.draw.rect(s, (255, 255, 255) if (active or r.collidepoint(mouse)) else (120, 120, 150), r, 1)
            self.text(label, r.centerx, r.y + 4, (30, 30, 50) if active else (255, 255, 255), center=True)

        cat, _, skins = CATEGORIES[self.shop_tab]
        owned, equipped = self.save["owned"][cat], self.eq[cat]
        for i, (key, spec) in enumerate(skins.items()):
            r = self.card_rect(i)
            is_eq, is_owned = key == equipped, key in owned
            border = (90, 230, 120) if is_eq else (255, 255, 255) if is_owned else (130, 130, 160)
            pygame.draw.rect(s, (50, 50, 85) if r.collidepoint(mouse) else (36, 36, 62), r)
            pygame.draw.rect(s, border, r, 2 if is_eq else 1)
            # vista previa
            if cat == "duck":
                img = pygame.transform.scale(self.duck_cache[key], (32, 32))
                s.blit(img, (r.x + 12, r.y + 18))
            elif cat == "gun":
                draw_gun(s, key, r.x + 8, r.y + 38, 0)
                draw_bullet(s, key, r.x + 42, r.y + 40, 1, 0, now)
            else:
                s.blit(pygame.transform.scale(self.bg_cache[key], (50, 28)), (r.x + 3, r.y + 24))
            self.text(spec["name"], r.centerx, r.y + 70, center=True)
            if is_eq:
                self.text("ACTIVO", r.centerx, r.y + 88, (90, 230, 120), center=True)
            elif is_owned:
                self.text("EQUIPAR", r.centerx, r.y + 88, center=True)
            else:
                afford = self.save["coins"] >= spec["price"]
                label = str(spec["price"])
                w = self.font.size(label)[0] + 10
                self.draw_coin(r.centerx - w // 2, r.y + 87)
                self.text(label, r.centerx - w // 2 + 10, r.y + 88, (255, 225, 90) if afford else (230, 90, 90))

        self.draw_coins_total()
        msg, t = self.shop_msg
        if t > 0:
            self.text(msg, W // 2, 152, (255, 150, 90), center=True)
        self.draw_button(self.back_btn, "VOLVER")

    def shop_click(self, pos):
        for i in range(len(CATEGORIES)):
            if self.tab_rect(i).collidepoint(pos):
                self.shop_tab = i
                return
        if self.back_btn.collidepoint(pos):
            self.state = self.prev_state
            return
        cat, _, skins = CATEGORIES[self.shop_tab]
        for i, (key, spec) in enumerate(skins.items()):
            if not self.card_rect(i).collidepoint(pos):
                continue
            if key in self.save["owned"][cat]:
                self.eq[cat] = key
            elif self.save["coins"] >= spec["price"]:
                self.save["coins"] -= spec["price"]
                self.save["owned"][cat].append(key)
                self.eq[cat] = key
                self.shop_msg = (f"Compraste {spec['name']}!", 1.5)
                self.play("buy")
            else:
                self.shop_msg = (f"Te faltan {spec['price'] - self.save['coins']} monedas", 1.5)
                self.play("deny")
            self._save_game()
            return

    def next_boss_name(self):
        return BOSS_NAMES[boss_kind_for_bg(self.eq["bg"])].capitalize()

    def draw_crosshair(self):
        mx, my = (int(v) for v in self.mouse())
        c = (255, 50, 50)
        for dx, dy in ((-4, 0), (3, 0), (0, -4), (0, 3)):
            self.screen.fill(c, (mx + dx, my + dy, 2 if dx else 1, 1 if dx else 2))
        self.screen.set_at((mx, my), c)

    def draw(self):
        s = self.screen
        s.blit(self.bg_cache[self.eq["bg"]], (0, 0))
        for cx, cy, cw in (self.clouds if BG_SKINS[self.eq["bg"]]["clouds"] else ()):
            x = (cx + pygame.time.get_ticks() / 400) % (W + 60) - 30
            pygame.draw.rect(s, (255, 255, 255), (int(x), cy, cw, 6))
            pygame.draw.rect(s, (255, 255, 255), (int(x) + 4, cy - 4, cw - 10, 6))

        for t in self.targets:
            t.draw(s)
        if self.boss:
            self.boss.draw(s)
        for b in self.bullets:
            draw_bullet(s, self.eq["gun"], b[0], b[1], b[2], b[3], pygame.time.get_ticks())
        for p in self.particles:
            s.fill(p.color, (int(p.x), int(p.y), 2, 2))
        self.draw_duck()
        for x, y, _, msg in self.popups:
            self.text(msg, int(x), int(y), (255, 255, 120), center=True)

        if self.state in ("clear", "victory", "over"):
            dim = pygame.Surface((W, H), pygame.SRCALPHA)
            dim.fill((10, 10, 30, 140))
            s.blit(dim, (0, 0))
        if self.state == "play":
            self.draw_hud()
        elif self.state == "title":
            self.draw_coins_total()
            self.text("PATO PISTOLERO", W // 2, 36, (255, 220, 40), self.big, center=True)
            self.text("Dispara a globos, latas, dianas y estrellas", W // 2, 70, center=True)
            self.text("A/D mover   Mouse apuntar   Click disparar   R recargar", W // 2, 83, center=True)
            if self.stage <= STAGES:
                goal = f"ETAPA {self.stage}/{STAGES}: supera {STAGE_GOAL} puntos"
            else:
                goal = f"JEFE FINAL: {self.next_boss_name()}"
            self.text(goal, W // 2, 96, (255, 225, 90), center=True)
            if int(pygame.time.get_ticks() / 400) % 2:
                self.text("Click para empezar", W // 2, 112, (255, 150, 90), center=True)
            self.text(f"RECORD {self.high}", W // 2, 126, (255, 230, 120), center=True)
            self.draw_button(self.menu_btn, "TIENDA (T)")
            if self.stage > 1:
                self.draw_button(self.reset_btn, "SEGURO?" if self.reset_armed > 0 else "REINICIAR")
        elif self.state == "clear":
            self.draw_coins_total()
            self.text(f"ETAPA {self.cleared_stage} COMPLETA!", W // 2, 30, (120, 240, 140), self.big, center=True)
            self.text(f"Puntos: {self.score}", W // 2, 64, center=True)
            self.text(f"Bonus de etapa: +{self.bonus} monedas", W // 2, 77, (255, 225, 90), center=True)
            if self.stage <= STAGES:
                nxt = f"Siguiente: etapa {self.stage}"
            else:
                nxt = f"Siguiente: JEFE FINAL ({self.next_boss_name()})"
                self.text("El jefe depende del fondo que tengas equipado", W // 2, 103, (200, 200, 230), center=True)
            self.text(nxt, W // 2, 90, center=True)
            if int(pygame.time.get_ticks() / 400) % 2:
                self.text("Click para continuar", W // 2, 118, (255, 150, 90), center=True)
            self.draw_button(self.menu_btn, "TIENDA (T)")
        elif self.state == "victory":
            self.draw_coins_total()
            self.text("VICTORIA!", W // 2, 28, (255, 220, 40), self.big, center=True)
            self.text(f"Derrotaste al {BOSS_NAMES[self.boss.kind].capitalize()} y terminaste el juego", W // 2, 64, center=True)
            self.text(f"Premio: +{BOSS_COINS} monedas", W // 2, 77, (255, 225, 90), center=True)
            self.text(f"Juegos completados: {self.save['wins']}", W // 2, 90, center=True)
            if int(pygame.time.get_ticks() / 400) % 2:
                self.text("Click para volver al menu", W // 2, 118, (255, 150, 90), center=True)
            self.draw_button(self.menu_btn, "TIENDA (T)")
        elif self.state == "over":
            self.draw_coins_total()
            if self.fail_reason == "boss":
                self.text("DERROTADO", W // 2, 30, (255, 90, 90), self.big, center=True)
                self.text(f"El {BOSS_NAMES[self.boss.kind].capitalize()} te vencio", W // 2, 64, center=True)
                self.text(f"Vida del jefe: {max(0, self.boss.hp)}/{self.boss.MAX_HP}", W // 2, 77, center=True)
                retry = "Click para reintentar el jefe"
            else:
                self.text("TIEMPO AGOTADO", W // 2, 30, (255, 90, 90), self.big, center=True)
                self.text(f"Puntos: {self.score}   (meta: mas de {STAGE_GOAL})", W // 2, 64, center=True)
                self.text(f"Record: {self.high}", W // 2, 77, (255, 230, 120), center=True)
                retry = f"Click para reintentar la etapa {self.stage}"
            self.text(f"Monedas ganadas: +{self.coins_run}", W // 2, 90, (255, 225, 90), center=True)
            if int(pygame.time.get_ticks() / 400) % 2:
                self.text(retry, W // 2, 118, (255, 150, 90), center=True)
            self.draw_button(self.menu_btn, "TIENDA (T)")
        else:
            self.draw_shop()
        self.draw_crosshair()

        ox = oy = 0
        if self.shake > 0:
            ox, oy = random.randint(-1, 1), random.randint(-1, 1)
        scaled = pygame.transform.scale(s, (W * SCALE, H * SCALE))
        self.window.fill((0, 0, 0))
        self.window.blit(scaled, (ox * SCALE, oy * SCALE))
        pygame.display.flip()

    # ---------- bucle ----------
    def run(self):
        while True:
            dt = min(self.clock.tick(60) / 1000, 0.05)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self._save_game()
                    pygame.quit()
                    return
                key = e.key if e.type == pygame.KEYDOWN else None
                if key == pygame.K_ESCAPE:
                    if self.state == "shop":
                        self.state = self.prev_state
                        continue
                    self._save_game()
                    pygame.quit()
                    return
                click = e.type == pygame.MOUSEBUTTONDOWN and e.button == 1
                shoot_btn = click or key == pygame.K_SPACE
                if self.state == "play":
                    if shoot_btn:
                        self.shoot()
                    elif key == pygame.K_r and self.ammo < MAX_AMMO and self.reload <= 0:
                        self.reload = RELOAD_TIME
                        self.play("reload")
                elif self.state == "shop":
                    if click:
                        self.shop_click(self.mouse())
                    elif key in (pygame.K_RIGHT, pygame.K_TAB):
                        self.shop_tab = (self.shop_tab + 1) % len(CATEGORIES)
                    elif key == pygame.K_LEFT:
                        self.shop_tab = (self.shop_tab - 1) % len(CATEGORIES)
                    elif key == pygame.K_t:
                        self.state = self.prev_state
                else:
                    if key == pygame.K_t or (click and self.menu_btn.collidepoint(self.mouse())):
                        self.prev_state = self.state
                        self.state = "shop"
                    elif click and self.state == "title" and self.stage > 1 and self.reset_btn.collidepoint(self.mouse()):
                        if self.reset_armed > 0:       # segundo click: confirma
                            self.save["stage"] = 1
                            self.reset_armed = 0.0
                            self._save_game()
                        else:
                            self.reset_armed = 2.0
                    elif shoot_btn:
                        if self.state == "victory":
                            self.reset()
                            self.state = "title"
                        else:
                            self.start_run()
            if self.state == "play":
                self.update(dt)
            self.reset_armed = max(0.0, self.reset_armed - dt)
            self.shop_msg = (self.shop_msg[0], max(0.0, self.shop_msg[1] - dt))
            self.draw()


if __name__ == "__main__":
    Game().run()
