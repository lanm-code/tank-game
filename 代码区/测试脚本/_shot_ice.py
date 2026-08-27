# -*- coding: utf-8 -*-
"""临时: 渲染第 6 关场景截图 (冰面成片出现的关卡), 验证新冰面纹理"""
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

gs = GameState()
gs.new_game(GameMode.ENDLESS, level=6)
game = Game(pygame.display.set_mode((1280, 720)), gs)
game.start_level(6)
for _ in range(30):
    game.update()
game.render()
out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "素材检查", "shot_lv6_ice.png")
pygame.image.save(game._internal_surface, out)
print("saved:", out)
pygame.quit()
