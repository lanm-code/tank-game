# -*- coding: utf-8 -*-
"""技能矢量图标接触表: 28 个全渲染, 供视觉验收"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame  # noqa: E402
# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))


pygame.init()
pygame.display.set_mode((64, 64))

from ui.skill_icons import _DRAWERS, render_skill_icon  # noqa: E402
from ui.codex_data import CODEX  # noqa: E402
from systems.upgrade_system import UPGRADE_POOL  # noqa: E402

names = {u["id"]: u["name"] for u in UPGRADE_POOL}
S, GAP = 120, 24
cols = 7
ids = list(_DRAWERS.keys())
rows = (len(ids) + cols - 1) // cols
W = cols * (S + GAP) + GAP
H = rows * (S + GAP) + GAP + 40
surf = pygame.Surface((W, H))
surf.fill((47, 47, 47))
try:
    from utils.fonts import load_font
    f = load_font(20, bold=True)
except Exception:
    f = pygame.font.Font(None, 20)

for i, sid in enumerate(ids):
    col, row = i % cols, i // cols
    x = GAP + col * (S + GAP)
    y = GAP + row * (S + GAP)
    icon = render_skill_icon(sid, S)
    surf.blit(icon, (x, y))
    lab = f.render(names.get(sid, sid), True, (150, 150, 158))
    surf.blit(lab, (x + (S - lab.get_width()) // 2, y + S + 4))

out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "素材检查", "skill_icons_sheet.png")
pygame.image.save(surf, out)
print("saved:", out, surf.get_size())
pygame.quit()
