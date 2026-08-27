# -*- coding: utf-8 -*-
"""六种敌军外观差异化验证: 同屏渲染侦察兵/炮兵/重甲/幽灵/工程师/精英"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402
# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))


pygame.init()
pygame.display.set_mode((64, 64))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.constants import (SCREEN_WIDTH, SCREEN_HEIGHT, BG_DEEP, BG_GRID,
                            EnemyType)  # noqa: E402
from systems.ai_system import EnemyTank  # noqa: E402

surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
surf.fill(BG_DEEP)
step = 80
for x in range(0, SCREEN_WIDTH + step, step):
    pygame.draw.line(surf, BG_GRID, (x, 0), (x, SCREEN_HEIGHT), 1)
for y in range(0, SCREEN_HEIGHT + step, step):
    pygame.draw.line(surf, BG_GRID, (0, y), (SCREEN_WIDTH, y), 1)

types = [EnemyType.SCOUT, EnemyType.ARTILLERY, EnemyType.HEAVY,
         EnemyType.GHOST, EnemyType.ENGINEER, EnemyType.ELITE]
names = ["侦察兵", "炮兵", "重甲", "幽灵", "工程师", "精英"]
try:
    from utils.fonts import load_font
    f = load_font(24, bold=True)
except Exception:
    f = pygame.font.Font(None, 24)

for i, (t, n) in enumerate(zip(types, names)):
    x = 260 + i * 280
    y = 300
    e = EnemyTank(x, y, t, level=1)
    e.turret_angle = 45
    e.draw(surf, show_hp=False)
    lab = f.render(n, True, (200, 200, 210))
    surf.blit(lab, (x - lab.get_width() // 2, y + 80))

# 侦察兵放大 4 倍单独存一张 (细节验证)
e = EnemyTank(260, 300, EnemyType.SCOUT, level=1)
e.turret_angle = 45
zoom = pygame.Surface((920, 520))
zoom.fill(BG_DEEP)
tmp = pygame.Surface((230, 130))
tmp.fill(BG_DEEP)
e.x, e.y = 115, 65
e.draw(tmp, show_hp=False)
try:
    z = pygame.transform.scale(tmp, (920, 520))
except Exception:
    z = pygame.transform.smoothscale(tmp, (920, 520))
zoom.blit(z, (0, 0))
out2 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "素材检查", "shot_scout_zoom.png")
pygame.image.save(zoom, out2)
print("saved:", out2)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "素材检查", "shot_enemy_types.png")
pygame.image.save(surf, out)
print("saved:", out)
pygame.quit()
