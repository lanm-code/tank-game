# -*- coding: utf-8 -*-
"""
粒子与爆炸特效
"""
import math
import random
import pygame
from core.constants import *


class Particle:
    def __init__(self, x, y, vx, vy, color, lifetime_ms, size,
                 shrink=True, gravity=0.0, glow=True, kind="circle",
                 tx=None, ty=None, text=None):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.lifetime = lifetime_ms
        self.age = 0
        self.size = size
        self.max_size = size
        self.shrink = shrink
        self.gravity = gravity
        self.glow = glow
        self.kind = kind          # circle=圆点 / ring=扩散圆环 / line=线段 / text=飘字
        self.tx = tx              # line 终点
        self.ty = ty
        self.text = text          # text 内容
        self.dead = False

    def update(self, dt):
        self.age += dt
        if self.age >= self.lifetime:
            self.dead = True
            return
        step = dt / 16.666
        self.x += self.vx * step
        self.y += self.vy * step
        self.vy += self.gravity * step
        self.vx *= 0.98
        self.vy *= 0.98
        if self.kind == "ring":
            # 扩散环: 半径随时间增长
            self.size = self.max_size * (self.age / self.lifetime)
        elif self.shrink:
            t = self.age / self.lifetime
            self.size = self.max_size * (1 - t)

    def draw(self, surface, camera_x=0, camera_y=0):
        if self.dead or self.size < 0.5:
            return
        sx, sy = int(self.x - camera_x), int(self.y - camera_y)
        t = 1 - (self.age / self.lifetime)
        col = tuple(max(0, min(255, int(c * t))) for c in self.color[:3])
        if self.kind == "text":
            # 飘字: 上浮淡出 (道具拾取反馈)
            try:
                from utils.fonts import load_font
                font = load_font(14, bold=True)
                img = font.render(self.text, True, col)
                surface.blit(img, (sx - img.get_width() // 2,
                                   sy - img.get_height() // 2))
            except Exception:
                pass
            return
        if self.kind == "ring":
            pygame.draw.circle(surface, col, (sx, sy), max(1, int(self.size)), 2)
            return
        if self.kind == "line":
            tx, ty = int(self.tx - camera_x), int(self.ty - camera_y)
            pygame.draw.line(surface, col, (sx, sy), (tx, ty), 2)
            return
        if self.glow:
            r = int(self.size * 2)
            if r > 0:
                try:
                    glow_s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                    pygame.draw.circle(glow_s, (*col, min(200, int(120 * t))), (r, r), r)
                    surface.blit(glow_s, (sx - r, sy - r),
                                 special_flags=pygame.BLEND_RGBA_ADD)
                except Exception:
                    pass
        pygame.draw.circle(surface, col, (sx, sy), max(1, int(self.size)))


def spawn_explosion(particles_list, x, y, intensity=1.0, color=None):
    # 极简灰阶爆炸: 白/灰小方块, 无光晕, 数量减半
    colors = color or [(220, 220, 225), (160, 160, 165), (100, 100, 105),
                       (255, 255, 255)]
    count = int(15 * intensity)
    for _ in range(count):
        ang = random.uniform(0, math.pi * 2)
        spd = random.uniform(1, 6) * intensity
        particles_list.append(Particle(
            x, y, math.cos(ang) * spd, math.sin(ang) * spd,
            random.choice(colors), random.randint(400, 900),
            random.uniform(2, 5) * intensity, shrink=True, glow=False
        ))
    for _ in range(int(8 * intensity)):
        ang = random.uniform(0, math.pi * 2)
        spd = random.uniform(0.5, 2) * intensity
        particles_list.append(Particle(
            x, y, math.cos(ang) * spd, math.sin(ang) * spd,
            (80, 80, 88), random.randint(600, 1400),
            random.uniform(3, 8) * intensity, shrink=True, glow=False, gravity=0.05
        ))


def spawn_hit_spark(particles_list, x, y, color=(200, 200, 205)):
    for _ in range(4):
        ang = random.uniform(0, math.pi * 2)
        spd = random.uniform(1, 4)
        particles_list.append(Particle(
            x, y, math.cos(ang) * spd, math.sin(ang) * spd,
            color, random.randint(200, 500), random.uniform(1, 3),
            shrink=True, glow=False
        ))


def spawn_muzzle_flash(particles_list, x, y, angle_deg, color=(210, 210, 215)):
    for _ in range(3):
        spread = random.uniform(-15, 15)
        ang = math.radians(angle_deg + spread)
        spd = random.uniform(2, 6)
        particles_list.append(Particle(
            x, y, math.cos(ang) * spd, math.sin(ang) * spd,
            color, random.randint(100, 250), random.uniform(2, 4),
            shrink=True, glow=False
        ))


def spawn_tank_dust(particles_list, x, y, angle_deg, color=(160, 140, 100)):
    rear = math.radians(angle_deg + 180 + random.uniform(-20, 20))
    particles_list.append(Particle(
        x, y,
        math.cos(rear) * random.uniform(0.5, 1.5),
        math.sin(rear) * random.uniform(0.5, 1.5),
        color, random.randint(300, 700),
        random.uniform(2, 5), shrink=True, glow=False
    ))


def spawn_wall_debris(particles_list, x, y):
    """砖墙被摧毁的碎屑 (暗砖色小方块, 无光晕)"""
    for _ in range(6):
        ang = random.uniform(0, math.pi * 2)
        spd = random.uniform(1, 4)
        particles_list.append(Particle(
            x, y, math.cos(ang) * spd, math.sin(ang) * spd,
            random.choice([(150, 115, 92), (120, 90, 72), (90, 68, 55)]),
            random.randint(250, 550), random.uniform(2, 4),
            shrink=True, gravity=0.06, glow=False
        ))


def spawn_clang(particles_list, x, y):
    """钢墙命中火花 (白色小点, 表示"打不动")"""
    for _ in range(4):
        ang = random.uniform(0, math.pi * 2)
        spd = random.uniform(1, 3)
        particles_list.append(Particle(
            x, y, math.cos(ang) * spd, math.sin(ang) * spd,
            (220, 225, 235), random.randint(120, 320), random.uniform(1, 2),
            shrink=True, glow=False
        ))


# --------------------------------------------------------------
# 技能特效 (极简: 白/灰 + 坦克本色, 小粒子无光晕)
# --------------------------------------------------------------
def spawn_frost(particles_list, x, y):
    """冰霜弹头命中: 白色小冰晶"""
    for _ in range(7):
        ang = random.uniform(0, math.pi * 2)
        spd = random.uniform(0.5, 2.5)
        particles_list.append(Particle(
            x, y, math.cos(ang) * spd, math.sin(ang) * spd,
            (200, 220, 235), random.randint(250, 500),
            random.uniform(1.5, 3), shrink=True, glow=False))


def spawn_shield_block(particles_list, x, y):
    """能量护盾格挡: 白圈扩散"""
    particles_list.append(Particle(x, y, 0, 0, (232, 232, 236), 300, 16,
                                   shrink=False, glow=False, kind="ring"))


def spawn_shield_break(particles_list, x, y):
    """不屈意志触发: 金色护盾破碎"""
    for _ in range(10):
        ang = random.uniform(0, math.pi * 2)
        spd = random.uniform(1, 4)
        particles_list.append(Particle(
            x, y, math.cos(ang) * spd, math.sin(ang) * spd,
            random.choice([(255, 210, 90), (255, 240, 180), (255, 255, 255)]),
            random.randint(300, 700), random.uniform(2, 4),
            shrink=True, glow=False))


def spawn_lifesteal(particles_list, x, y, px, py):
    """吸血: 绿色粒子从目标飞向玩家"""
    for _ in range(3):
        ang = math.atan2(py - y, px - x) + random.uniform(-0.4, 0.4)
        spd = random.uniform(3, 6)
        particles_list.append(Particle(
            x, y, math.cos(ang) * spd, math.sin(ang) * spd,
            (110, 220, 140), random.randint(300, 600),
            random.uniform(2, 3.5), shrink=True, glow=False))


def spawn_boom_ring(particles_list, x, y, radius):
    """死亡爆破: 白环扩散"""
    particles_list.append(Particle(x, y, 0, 0, (220, 220, 225), 350, radius,
                                   shrink=False, glow=False, kind="ring"))


def spawn_lightning(particles_list, x0, y0, x1, y1):
    """静电场雷击: 白色线段"""
    particles_list.append(Particle(x0, y0, 0, 0, (255, 255, 255), 250, 2,
                                   shrink=False, glow=False, kind="line",
                                   tx=x1, ty=y1))


def spawn_ricochet_ring(particles_list, x, y):
    """弹射强化: 白圈小扩散"""
    particles_list.append(Particle(x, y, 0, 0, (200, 200, 210), 250, 10,
                                   shrink=False, glow=False, kind="ring"))


def spawn_chrono_ring(particles_list, x, y):
    """时间静止触发: 大灰圈扩散"""
    particles_list.append(Particle(x, y, 0, 0, (180, 180, 190), 600, 260,
                                   shrink=False, glow=False, kind="ring"))


def spawn_phoenix(particles_list, x, y):
    """不死凤凰复活: 上升的火羽粒子"""
    for _ in range(16):
        ang = random.uniform(0, math.pi * 2)
        spd = random.uniform(0.5, 2)
        particles_list.append(Particle(
            x + random.uniform(-20, 20), y + random.uniform(-20, 20),
            math.cos(ang) * spd, -random.uniform(1, 4),
            random.choice([(255, 120, 60), (255, 200, 80), (255, 255, 255)]),
            random.randint(400, 900), random.uniform(2, 5),
            shrink=True, gravity=0.04, glow=False))


def spawn_snipe_line(particles_list, x0, y0, x1, y1):
    """狙击之眼: 细白瞄准线"""
    particles_list.append(Particle(x0, y0, 0, 0, (240, 240, 245), 180, 1,
                                   shrink=False, glow=False, kind="line",
                                   tx=x1, ty=y1))


def spawn_magnet_dot(particles_list, x, y):
    """磁铁吸附: 小灰点拖尾"""
    particles_list.append(Particle(x, y, 0, 0, (150, 150, 160), 250, 2,
                                   shrink=True, glow=False))


def spawn_pickup_ping(particles_list, x, y, color=(120, 200, 140)):
    """拾取反馈: 短促扩散圆环 + 少量飞散点 (玩家/敌人拾取道具时)"""
    particles_list.append(Particle(x, y, 0, 0, color, 380, 22,
                                   shrink=False, glow=False, kind="ring"))
    for _ in range(4):
        particles_list.append(Particle(
            x, y,
            random.uniform(-1.3, 1.3), random.uniform(-1.3, 1.3),
            color, random.uniform(280, 450), random.uniform(1.5, 2.6),
            shrink=True, glow=False))


def spawn_pickup_text(particles_list, x, y, text, color=(232, 232, 236)):
    """拾取反馈: 上浮飘字 (显示道具效果, 例如 +30 / 攻↑ / -20)"""
    particles_list.append(Particle(x, y, 0, -0.55, color, 750, 14,
                                   shrink=False, glow=False, kind="text",
                                   text=text))
