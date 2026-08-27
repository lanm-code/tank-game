# -*- coding: utf-8 -*-
"""技能栏排版检查: 模拟 24 个技能, 渲染 HUD 原图"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402
# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))


pygame.init()
pygame.display.set_mode((1280, 720))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT  # noqa: E402
from core.game_state import GameState, GameMode  # noqa: E402
from core.game import Game  # noqa: E402
from systems.upgrade_system import UPGRADE_POOL  # noqa: E402

gs = GameState()
gs.new_game(GameMode.ENDLESS, level=1)
game = Game(pygame.display.set_mode((1280, 720)), gs)
game.start_level(1)

# 给 P1 塞满全部 28 个技能条目 (26 池 + 2 残卡, 等级各不相同)
pd = gs.players[0]
levels = {}
for i, u in enumerate(UPGRADE_POOL):
    levels[u["id"]] = 1 + (i % 3)
pd.upgrade_levels = levels

game.render()
out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "素材检查", "shot_skillbar_full.png")
pygame.image.save(game._internal_surface, out)
print("saved:", out)
pygame.quit()
