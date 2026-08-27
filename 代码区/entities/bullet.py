# -*- coding: utf-8 -*-
"""
子弹实体
Bullet Entity
"""
import math
import pygame
from core.constants import *
from utils.math_utils import dir_from_angle, clamp, aabb_overlap, circle_rect_overlap
from utils.assets import get_bullet_image, get_rotated


class Bullet:
    def __init__(self, x, y, angle_deg, bullet_type, owner_id, damage_mult=1.0,
                 pierce_add=0, ricochet_add=0, speed_mult=1.0, slow_add=0.0,
                 slow_dur=0, slow_fire=0.0, railgun=False):
        cfg = BULLET_CONFIG[bullet_type]
        self.x = float(x)
        self.y = float(y)
        self.angle = angle_deg
        self.type = bullet_type
        self.owner_id = owner_id  # positive: player, negative: enemy, "boss": boss
        self.speed = cfg["speed"] * speed_mult
        self.radius = cfg["radius"]
        self.damage = int(cfg["damage"] * damage_mult)
        self.pierce = cfg.get("pierce", 0) + pierce_add
        self.ricochet = cfg.get("ricochet", 0) + ricochet_add
        self.slow = cfg.get("slow", 0.0) + slow_add
        self.slow_dur = slow_dur if slow_dur > 0 else 2500  # 减速持续 (ms)
        self.slow_fire = slow_fire  # 命中同时降低攻速的比例 (冰霜弹头)
        self.stun = cfg.get("stun", 0.0)          # 命中眩晕时长 (秒)
        self.splash = cfg.get("splash")           # 范围伤害配置 dict 或 None
        self.railgun = railgun                    # 轨道炮: 摧毁砖墙并穿透钢墙
        self.color = cfg["color"]
        self.dead = False
        self.hit_set = set()
        self.trail = []
        self.flight_dist = 0.0  # 累计飞行距离 (正弦弹道用)

    @property
    def is_friendly(self):
        return isinstance(self.owner_id, int) and self.owner_id > 0

    def update(self, dt, walls, tanks=None, map_rect=None, particles=None):
        step = self.speed * (dt / 16.666)
        self.flight_dist += step
        dx, dy = dir_from_angle(self.angle)
        # 正弦波飞行 (麦克风弹): 沿基准方向左右摆动
        sine = BULLET_CONFIG[self.type].get("sine")
        if sine:
            a_deg = self.angle + math.sin(self.flight_dist * sine["freq"]) * sine["amp_deg"]
            dx, dy = dir_from_angle(a_deg)
        nx = self.x + dx * step
        ny = self.y + dy * step

        ricocheted_x = False
        ricocheted_y = False
        mr = map_rect or pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)

        if nx - self.radius < mr.left or nx + self.radius > mr.right:
            if self.ricochet > 0 and not ricocheted_x:
                self.angle = 180 - self.angle
                self.ricochet -= 1
                ricocheted_x = True
                nx = self.x
                if particles is not None:
                    from .particle import spawn_ricochet_ring
                    spawn_ricochet_ring(particles, self.x, self.y)
            else:
                self.dead = True
                return

        if ny - self.radius < mr.top or ny + self.radius > mr.bottom:
            if self.ricochet > 0 and not ricocheted_y:
                self.angle = -self.angle
                self.ricochet -= 1
                ricocheted_y = True
                ny = self.y
                if particles is not None:
                    from .particle import spawn_ricochet_ring
                    spawn_ricochet_ring(particles, self.x, self.y)
            else:
                self.dead = True
                return

        # 碰撞半径略大于贴图中心圆, 视觉"打中"即判定
        hit_r = self.radius + 4
        new_x, new_y = nx, ny
        for w in walls:
            wcfg = WALL_CONFIG[w.type]
            if wcfg["bullet_pass"]:
                # 玻璃墙: 子弹穿过但玻璃破碎 (hp=1, 一发即碎)
                if w.type == WallType.GLASS and not w.destroyed:
                    if circle_rect_overlap(nx, ny, hit_r, w.x, w.y, w.width, w.height):
                        w.take_damage(self.damage)
                        if particles is not None:
                            from .particle import spawn_wall_debris
                            spawn_wall_debris(particles, nx, ny)
                continue
            if circle_rect_overlap(nx, ny, hit_r, w.x, w.y, w.width, w.height):
                if self.railgun:
                    # 轨道炮: 摧毁沿途砖墙 (直接打碎), 钢墙不挡
                    if wcfg.get("hp", -1) >= 0:
                        w.take_damage(9999)
                        if particles is not None:
                            from .particle import spawn_wall_debris
                            spawn_wall_debris(particles, nx, ny)
                    continue
                if wcfg.get("hp", -1) >= 0:
                    # 可摧毁方块 (砖/沙/木箱/油桶): 按伤害扣血, 子弹消失 (不反弹/不穿透)
                    w.take_damage(self.damage)
                    if particles is not None:
                        from .particle import spawn_wall_debris
                        spawn_wall_debris(particles, nx, ny)
                    self.dead = True
                    return
                # 钢墙: 不可摧毁; 弹射弹反弹, 其余子弹消失 (亮光反馈)
                if particles is not None:
                    from .particle import spawn_clang
                    spawn_clang(particles, nx, ny)
                if self.ricochet > 0:
                    if abs(nx - self.x) > abs(ny - self.y):
                        self.angle = 180 - self.angle
                    else:
                        self.angle = -self.angle
                    self.ricochet -= 1
                    new_x, new_y = self.x, self.y
                    if particles is not None:
                        from .particle import spawn_ricochet_ring
                        spawn_ricochet_ring(particles, self.x, self.y)
                else:
                    self.dead = True
                    return

        self.x, self.y = new_x, new_y
        self.trail.append((self.x, self.y))
        if len(self.trail) > 3:
            self.trail.pop(0)

    def draw(self, surface, camera_x=0, camera_y=0):
        sx, sy = int(self.x - camera_x), int(self.y - camera_y)
        # 轨道炮: 白色光束拖尾
        if self.railgun and self.trail:
            tx, ty = self.trail[-1]
            pygame.draw.line(surface, (240, 240, 245),
                             (int(tx - camera_x), int(ty - camera_y)),
                             (sx, sy), 3)
        # 极简短拖尾 (低透明度, 无渐变色带)
        for i, (tx, ty) in enumerate(self.trail):
            a = (i + 1) / len(self.trail) * 0.5
            r = max(1, int(self.radius * a * 0.8))
            c = tuple(int(ch * a) for ch in self.color)
            pygame.draw.circle(surface, c, (int(tx - camera_x), int(ty - camera_y)), r)

        img_size = (self.radius * 4, self.radius * 4)
        img = get_bullet_image(self.type, img_size)
        if img is not None:
            rot = get_rotated(img, -(self.angle + 90), step=3)
            rect = rot.get_rect(center=(sx, sy))
            surface.blit(rot, rect)
            return

        # 图片缺失时过程化兜底
        if self.type == BulletType.EGG:
            pygame.draw.circle(surface, NEON_YELLOW, (sx, sy), self.radius + 1, 1)
            pygame.draw.circle(surface, (255, 255, 200), (sx, sy), self.radius)
            pygame.draw.circle(surface, (255, 180, 50), (sx - self.radius // 3, sy - self.radius // 3), 2)
        elif self.type == BulletType.MILKY_EGG:
            pygame.draw.circle(surface, (255, 150, 200), (sx, sy), self.radius + 2, 1)
            pygame.draw.circle(surface, self.color, (sx, sy), self.radius)
            pygame.draw.circle(surface, (255, 255, 255), (sx, sy), self.radius // 2)
        elif self.type == BulletType.KNIFE:
            r = math.radians(self.angle)
            tip = (sx + math.cos(r) * self.radius * 2.5, sy + math.sin(r) * self.radius * 2.5)
            base_l = (sx - math.cos(r) * self.radius + math.sin(r) * self.radius,
                      sy - math.sin(r) * self.radius - math.cos(r) * self.radius)
            base_r = (sx - math.cos(r) * self.radius - math.sin(r) * self.radius,
                      sy - math.sin(r) * self.radius + math.cos(r) * self.radius)
            pygame.draw.polygon(surface, (240, 240, 255), [tip, base_l, base_r])
            pygame.draw.polygon(surface, NEON_CYAN, [tip, base_l, base_r], 1)
        elif self.type == BulletType.BASKETBALL:
            pygame.draw.circle(surface, (120, 60, 0), (sx, sy), self.radius + 1, 1)
            pygame.draw.circle(surface, (255, 140, 30), (sx, sy), self.radius)
            pygame.draw.line(surface, (60, 30, 0), (sx - self.radius, sy), (sx + self.radius, sy), 1)
            pygame.draw.line(surface, (60, 30, 0), (sx, sy - self.radius), (sx, sy + self.radius), 1)
        elif self.type == BulletType.CANNON:
            pygame.draw.circle(surface, (40, 40, 50), (sx, sy), self.radius + 1)
            pygame.draw.circle(surface, (120, 120, 130), (sx, sy), self.radius)
            pygame.draw.circle(surface, (200, 200, 210), (sx - 2, sy - 2), max(1, self.radius // 3))
        elif self.type == BulletType.MIC:
            # 麦克风: 粉色圆 + 网罩格纹 + 手柄
            pygame.draw.circle(surface, (255, 150, 200), (sx, sy), self.radius)
            pygame.draw.circle(surface, (200, 90, 140), (sx, sy), self.radius, 1)
            for i in range(-self.radius + 2, self.radius, 4):
                pygame.draw.line(surface, (200, 90, 140),
                                 (sx + i, sy - self.radius + 2),
                                 (sx + i, sy + self.radius - 2), 1)
            pygame.draw.line(surface, (60, 60, 70),
                             (sx, sy + self.radius), (sx, sy + self.radius + 6), 2)
        elif self.type == BulletType.MELON:
            # 西瓜: 绿圆 + 深色条纹 + 高光
            pygame.draw.circle(surface, (90, 200, 90), (sx, sy), self.radius)
            pygame.draw.circle(surface, (40, 130, 60), (sx, sy), self.radius, 1)
            for i in range(-self.radius // 2, self.radius // 2 + 1, 4):
                pygame.draw.line(surface, (40, 130, 60),
                                 (sx + i, sy - self.radius + 1),
                                 (sx + i + self.radius // 2, sy + self.radius - 1), 1)
            pygame.draw.circle(surface, (200, 240, 200), (sx - 2, sy - 3), 2)
        elif self.type == BulletType.PARCEL:
            # 外卖箱: 棕色方箱 + 封箱胶带
            r = self.radius + 2
            pygame.draw.rect(surface, (150, 105, 60),
                             (sx - r, sy - r, r * 2, r * 2), border_radius=3)
            pygame.draw.rect(surface, (90, 60, 35),
                             (sx - r, sy - r, r * 2, r * 2), 1, border_radius=3)
            pygame.draw.rect(surface, (225, 210, 180),
                             (sx - r + 2, sy - 2, r * 2 - 4, 4))

    def try_hit_tank(self, tank, particles=None):
        if self.dead:
            return False
        tid = id(tank)
        if tid in self.hit_set:
            return False
        tr = tank.get_rect()
        if circle_rect_overlap(self.x, self.y, self.radius, tr.x, tr.y, tr.width, tr.height):
            self.hit_set.add(tid)
            tank.take_damage(self.damage, slow=self.slow, stun=self.stun,
                             slow_dur=self.slow_dur, slow_fire=self.slow_fire,
                             particles=particles)
            if self.pierce > 0:
                self.pierce -= 1
            else:
                self.dead = True
            return True
        return False
