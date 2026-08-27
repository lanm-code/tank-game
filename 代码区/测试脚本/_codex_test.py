# -*- coding: utf-8 -*-
"""
图鉴截图验收: 无头渲染每个图鉴页面并存 PNG 到 素材检查/
用法: python _codex_test.py
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402
# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))


pygame.init()
pygame.display.set_mode((1280, 720))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT  # noqa: E402
from core.game_state import GameState  # noqa: E402
from ui.codex_ui import CodexUI  # noqa: E402
from ui.codex_data import CODEX_CATEGORIES  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "素材检查")
os.makedirs(OUT, exist_ok=True)

gs = GameState()
# 模拟部分发现: 坦克全见、炮弹/篮球已见、Boss1 已见、侦察兵已见、
# 技能几个已见、道具 HP/POISON 已见、钢墙/砖块已见
gs.codex_seen = {
    "tank": {"red": True, "blue": True, "green": True, "yellow": True},
    "bullet": {"cannon": True, "basketball": True},
    "boss": {"boss_1": True},
    "enemy": {"scout": True, "artillery": True, "heavy": True,
              "ghost": True, "engineer": True, "elite": True},
    "skill": {"damage_flat": True, "railgun": True},
    "pickup": {"hp": True, "poison": True},
    "tile": {"steel": True, "brick": True},
}

screen = pygame.display.set_mode((1280, 720))
ui = CodexUI(screen, gs, None)


def shot(name, view="hub", cat=None, **setup):
    ui.open(view=view, cat_id=cat)
    for k, v in setup.items():
        setattr(ui, k, v)
    ui.draw()
    path = os.path.join(OUT, name)
    pygame.image.save(screen, path)
    print("saved:", name)


shot("codex_hub.png")
ui.hub_idx = 1
shot("codex_hub_bullet_hover.png")
shot("codex_cat_pickup.png", view="cat", cat_id="pickup")
shot("codex_cat_pickup_penalty.png", view="cat", cat_id="pickup",
     cat_tab=2, cat_idx=0)
shot("codex_cat_bullet.png", view="cat", cat_id="bullet")
shot("codex_cat_tank.png", view="cat", cat_id="tank")
shot("codex_cat_tile.png", view="cat", cat_id="tile")
shot("codex_cat_tile_page2.png", view="cat", cat_id="tile", cat_idx=12)
shot("codex_boss.png", view="boss")
shot("codex_boss_3.png", view="boss", boss_idx=2)
shot("codex_grunt.png", view="boss", boss_tab="grunt")
shot("codex_skill_common.png", view="skill", skill_tab=1, skill_idx=0)
shot("codex_skill_legendary.png", view="skill", skill_tab=4, skill_idx=0)
shot("codex_skill_all.png", view="skill", skill_tab=0, skill_idx=14)

pygame.quit()
print("ALL SHOTS DONE")
