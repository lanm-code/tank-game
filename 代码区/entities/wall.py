# -*- coding: utf-8 -*-
"""
墙体实体
Wall Entity
"""
import os
import random
import pygame
from core.constants import *


# ----------------------------------------------------------
# 墙体纹理贴图 (素材库\墙体纹理\*.png), 缺失时自动回退程序化绘制
# ----------------------------------------------------------
_texture_dir = None
_texture_cache = {}
_flash_overlay = None


def _find_texture_dir():
    global _texture_dir
    if _texture_dir is not None:
        return _texture_dir or None
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "..", "素材库", "墙体纹理"),
        os.path.join(here, "..", "..", "..", "素材库", "墙体纹理"),
        os.path.join(here, "..", "..", "..", "..", "素材库", "墙体纹理"),
    ]
    _texture_dir = ""
    for c in candidates:
        c = os.path.normpath(c)
        if os.path.isdir(c):
            _texture_dir = c
            break
    return _texture_dir or None


def _get_texture(name):
    if name in _texture_cache:
        return _texture_cache[name]
    surf = None
    d = _find_texture_dir()
    if d:
        p = os.path.join(d, name)
        if os.path.exists(p):
            try:
                surf = pygame.image.load(p).convert_alpha()
            except Exception:
                surf = None
    _texture_cache[name] = surf
    return surf


def _get_flash_overlay():
    global _flash_overlay
    if _flash_overlay is None:
        s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        s.fill((255, 255, 255, 120))
        _flash_overlay = s
    return _flash_overlay


_TEXTURE_NAMES = {
    WallType.BRICK: "brick.png",
    WallType.SAND: "sand.png",
    WallType.STEEL: "steel.png",
    WallType.CRATE: "crate.png",
    WallType.GLASS: "glass.png",
    WallType.BARREL: "barrel.png",
    WallType.GRASS: "grass.png",
    WallType.WATER: "water.png",
    WallType.WATER_STAIN: "water_stain.png",
    WallType.MUD: "mud.png",
    WallType.ICE: "ice.png",
    WallType.SPIKE: "spike.png",
    WallType.PORTAL: "portal.png",
}
_DAMAGED_NAMES = {
    WallType.BRICK: "brick_damaged.png",
    WallType.SAND: "sand_damaged.png",
}


class Wall:
    # 半透明地块共享贴图缓存 (预渲染一次, 逐帧 blit, 避免逐帧造 SRCALPHA)
    _tile_cache = {}

    def __init__(self, col, row, wall_type):
        self.col = col
        self.row = row
        self.type = wall_type
        cfg = WALL_CONFIG[wall_type]
        self.x = col * TILE_SIZE
        self.y = row * TILE_SIZE
        self.width = TILE_SIZE
        self.height = TILE_SIZE
        self.color = cfg["color"]
        self.max_hp = cfg["hp"]
        self.hp = cfg["hp"]
        self.destroyed = False
        self.flash = 0          # 受击闪白剩余帧 (ms)
        self.effect_done = False  # 木箱掉道具 / 油桶爆炸 是否已结算
        self.portal_partner = None  # 传送门配对 (PORTAL 专用)

    def take_damage(self, dmg):
        if self.max_hp < 0:
            return
        self.hp -= dmg
        self.flash = 150
        if self.hp <= 0:
            self.destroyed = True

    def update(self, dt):
        if self.flash > 0:
            self.flash -= dt

    def _flash_color(self, base):
        if self.flash > 0 and (self.flash // 50) % 2 == 0:
            return tuple(min(255, c + 70) for c in base)
        return base

    # ----------------------------------------------------------
    # 半透明贴图构建 (水渍 / 玻璃)
    # ----------------------------------------------------------
    @classmethod
    def _get_tile_surface(cls, wtype):
        s = cls._tile_cache.get(wtype)
        if s is not None:
            return s
        s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        if wtype == WallType.WATER_STAIN:
            # 高透明度暗蓝灰水斑 + 1px 亮边 + 极淡静态波纹
            s.fill((*WALL_CONFIG[WallType.WATER_STAIN]["color"][:3], 165))
            pygame.draw.rect(s, (150, 170, 196, 230), (0, 0, TILE_SIZE, TILE_SIZE), 1)
            for i, off in ((0, 18), (1, 34), (2, 50)):
                pygame.draw.line(s, (170, 190, 214, 110),
                                 (10 + off, 14 + i * 2), (10 + off, 30 + i * 2), 2)
        elif wtype == WallType.GLASS:
            # 浅灰半透明玻璃 + 白边 + 对角高光
            s.fill((*WALL_CONFIG[WallType.GLASS]["color"][:3], 110))
            pygame.draw.rect(s, (225, 230, 238, 220), (0, 0, TILE_SIZE, TILE_SIZE), 1)
            pygame.draw.line(s, (225, 230, 238, 140), (10, TILE_SIZE - 10),
                             (TILE_SIZE - 10, 10), 2)
        cls._tile_cache[wtype] = s
        return s

    def _texture_name(self):
        if self.max_hp > 0 and self.hp <= self.max_hp // 2:
            dn = _DAMAGED_NAMES.get(self.type)
            if dn:
                return dn
        return _TEXTURE_NAMES.get(self.type)

    def draw(self, surface, camera_x=0, camera_y=0):
        if self.destroyed:
            return
        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y)
        # 优先使用高细节纹理贴图; 缺失时回退下方程序化绘制
        tex = _get_texture(self._texture_name())
        if tex is not None:
            surface.blit(tex, (sx, sy))
            if self.flash > 0 and (self.flash // 50) % 2 == 0:
                surface.blit(_get_flash_overlay(), (sx, sy))
            return
        if self.type == WallType.BRICK:
            # 砖墙 (可摧毁, hp=56): 暖棕色 + 规则错位砖缝; hp<=28 叠加裂纹
            base = (138, 95, 70)
            surface.fill(self._flash_color(base), (sx, sy, self.width, self.height))
            seam = (85, 55, 42)
            step = 16
            for r in range(step, self.height, step):
                pygame.draw.line(surface, seam, (sx, sy + r),
                                 (sx + self.width, sy + r), 1)
            for r in range(0, self.height, step):
                off = (r // step) % 2 * (step // 2)
                for c in range(off, self.width, step):
                    if c == 0:
                        continue
                    pygame.draw.line(surface, seam, (sx + c, sy + r),
                                     (sx + c, sy + min(r + step, self.height)), 1)
            pygame.draw.rect(surface, (95, 60, 45),
                             (sx, sy, self.width, self.height), 1)
            if self.max_hp > 0 and self.hp <= self.max_hp // 2:
                # 重裂状态: 确定性裂纹 (同格同纹, 不闪跳)
                rnd = random.Random(self.col * 97 + self.row)
                for _ in range(5):
                    x0 = rnd.randint(6, self.width - 10)
                    y0 = rnd.randint(6, self.height - 10)
                    x1 = x0 + rnd.randint(-12, 12)
                    y1 = y0 + rnd.randint(-12, 12)
                    pygame.draw.line(surface, (70, 42, 32), (sx + x0, sy + y0),
                                     (sx + x1, sy + y1), 1)
                    pygame.draw.line(surface, (150, 110, 88),
                                     (sx + x0 + 1, sy + y0 + 1),
                                     (sx + x1 + 1, sy + y1 + 1), 1)
        elif self.type == WallType.STEEL:
            # 钢墙 (不可摧毁): 亮银装甲 + 白边 + 四角铆钉 + 十字筋
            surface.fill(self._flash_color((158, 163, 172)),
                         (sx, sy, self.width, self.height))
            pygame.draw.rect(surface, (212, 216, 224),
                             (sx, sy, self.width, self.height), 2)
            pygame.draw.line(surface, (120, 126, 138),
                             (sx, sy + self.height // 2),
                             (sx + self.width, sy + self.height // 2), 2)
            pygame.draw.line(surface, (120, 126, 138),
                             (sx + self.width // 2, sy),
                             (sx + self.width // 2, sy + self.height), 2)
            for bx, by in ((sx + 6, sy + 6), (sx + self.width - 10, sy + 6),
                           (sx + 6, sy + self.height - 10),
                           (sx + self.width - 10, sy + self.height - 10)):
                pygame.draw.rect(surface, (90, 96, 108), (bx, by, 4, 4))
        elif self.type == WallType.SAND:
            # 沙粒方块 (hp=28): 灰黄沙色 + 颗粒麻点; 半损时颜色变暗、颗粒变稀
            base = (168, 158, 128)
            damaged = self.max_hp > 0 and self.hp <= self.max_hp // 2
            if damaged:
                base = (140, 128, 100)
            surface.fill(self._flash_color(base), (sx, sy, self.width, self.height))
            pygame.draw.rect(surface, (110, 100, 80),
                             (sx, sy, self.width, self.height), 1)
            rnd = random.Random(self.col * 131 + self.row * 7)
            count = 8 if damaged else 16
            for _ in range(count):
                px = sx + rnd.randint(6, self.width - 8)
                py = sy + rnd.randint(6, self.height - 8)
                surface.fill((126, 116, 92), (px, py, 3, 3))
        elif self.type == WallType.CRATE:
            # 木箱: 深棕底 + 横板纹 + 边框
            surface.fill(self._flash_color((120, 88, 52)),
                         (sx, sy, self.width, self.height))
            for r in range(14, self.height, 14):
                pygame.draw.line(surface, (88, 62, 36), (sx + 4, sy + r),
                                 (sx + self.width - 4, sy + r), 2)
            pygame.draw.line(surface, (80, 56, 32), (sx + 4, sy + 4),
                             (sx + self.width - 4, sy + self.height - 4), 2)
            pygame.draw.line(surface, (80, 56, 32), (sx + self.width - 4, sy + 4),
                             (sx + 4, sy + self.height - 4), 2)
            pygame.draw.rect(surface, (150, 116, 74),
                             (sx, sy, self.width, self.height), 1)
        elif self.type == WallType.GLASS:
            # 玻璃墙: 半透明贴图 (子弹可穿, 坦克不可过)
            surface.blit(self._get_tile_surface(WallType.GLASS), (sx, sy))
        elif self.type == WallType.BARREL:
            # 燃油桶: 深灰桶身 + 白框 + 白色叹号 (危险提示)
            pygame.draw.rect(surface, self._flash_color((70, 70, 78)),
                             (sx + 8, sy + 8, self.width - 16, self.height - 16),
                             border_radius=6)
            pygame.draw.rect(surface, (130, 130, 140),
                             (sx + 8, sy + 8, self.width - 16, self.height - 16),
                             1, border_radius=6)
            pygame.draw.line(surface, (140, 140, 150), (sx + 8, sy + 22),
                             (sx + self.width - 8, sy + 22), 1)
            # 白色叹号
            pygame.draw.rect(surface, (235, 235, 240),
                             (sx + self.width // 2 - 3, sy + self.height // 2 - 16, 6, 18))
            pygame.draw.rect(surface, (235, 235, 240),
                             (sx + self.width // 2 - 3, sy + self.height // 2 + 8, 6, 6))
        elif self.type == WallType.WATER_STAIN:
            surface.blit(self._get_tile_surface(WallType.WATER_STAIN), (sx, sy))
        elif self.type == WallType.MUD:
            # 泥沼: 暗棕块 + 深色横纹
            surface.fill((86, 72, 50), (sx, sy, self.width, self.height))
            pygame.draw.rect(surface, (110, 94, 66),
                             (sx, sy, self.width, self.height), 1)
            for i, r in enumerate((14, 32, 50)):
                pygame.draw.line(surface, (66, 54, 38),
                                 (sx + 8 + (i % 2) * 8, sy + r),
                                 (sx + self.width - 8, sy + r), 2)
        elif self.type == WallType.ICE:
            # 冰面: 亮灰白 + 淡蓝细斜纹
            surface.fill((168, 178, 190), (sx, sy, self.width, self.height))
            pygame.draw.rect(surface, (200, 210, 220),
                             (sx, sy, self.width, self.height), 1)
            for i in range(3):
                off = i * 22
                pygame.draw.line(surface, (140, 158, 176),
                                 (sx + off, sy + self.height),
                                 (sx + self.width, sy + off), 1)
        elif self.type == WallType.SPIKE:
            # 尖刺: 深灰底 + 3 个三角
            surface.fill((44, 44, 50), (sx, sy, self.width, self.height))
            for i, cx in enumerate((16, 32, 48)):
                pygame.draw.polygon(surface, (95, 95, 104),
                                    [(sx + cx - 8, sy + self.height - 6),
                                     (sx + cx + 8, sy + self.height - 6),
                                     (sx + cx, sy + self.height - 30)])
                pygame.draw.polygon(surface, (150, 150, 160),
                                    [(sx + cx - 8, sy + self.height - 6),
                                     (sx + cx + 8, sy + self.height - 6),
                                     (sx + cx, sy + self.height - 30)], 1)
        elif self.type == WallType.PORTAL:
            # 传送门: 暗底 + 灰紫同心环
            surface.fill((30, 28, 40), (sx, sy, self.width, self.height))
            pygame.draw.rect(surface, (128, 122, 150),
                             (sx, sy, self.width, self.height), 1)
            cx, cy = sx + self.width // 2, sy + self.height // 2
            pygame.draw.circle(surface, (128, 122, 150), (cx, cy), 22, 2)
            pygame.draw.circle(surface, (150, 145, 170), (cx, cy), 14, 1)
            pygame.draw.circle(surface, (200, 196, 220), (cx, cy), 5)
        elif self.type == WallType.GRASS:
            surface.fill((38, 72, 44), (sx, sy, self.width, self.height))
        elif self.type == WallType.WATER:
            import time
            t = time.time() * 1.2 + self.row
            surface.fill((32, 52, 105), (sx, sy, self.width, self.height))
            for i in range(0, self.width, 8):
                h = int(2 + 1 * __import__("math").sin(t + i * 0.5))
                surface.fill((60, 85, 140), (sx + i, sy + self.height // 2 - h // 2, 4, h))


def pygame_rect_stroke(surface, color, x, y, w, h, t=1):
    import pygame
    pygame.draw.rect(surface, color, (x, y, w, h), t)
