# -*- coding: utf-8 -*-
"""无头截图: 验证新方块/地块的极简视觉 (输出到工作区 素材检查\)
运行: py -3.14 _shot_tiles.py
"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import pygame

# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

pygame.init()
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
except Exception:
    pass
screen = pygame.display.set_mode((640, 360))

from core.game import Game
from core.game_state import GameState

OUT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "deepseek工作区", "坦克游戏", "素材检查"))
# 上面路径对不上时退回桌面素材检查
if not os.path.isdir(OUT):
    OUT = os.path.join(os.path.dirname(HERE), "素材检查")
os.makedirs(OUT, exist_ok=True)

gs = GameState()
for p in gs.players:
    p.invincible = True
game = Game(screen, gs)

for lv in (2, 5, 8):
    game.start_level(lv)
    for _ in range(30):
        game.begin_frame()
        game.update()
        game.render()
    path = os.path.join(OUT, f"shot_tiles_lv{lv}.png")
    pygame.image.save(game._internal_surface, path)
    print("saved:", path)

pygame.quit()
print("SHOT DONE")
