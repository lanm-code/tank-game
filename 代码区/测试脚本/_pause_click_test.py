# -*- coding: utf-8 -*-
"""暂停页鼠标点击测试: 三个按钮 (继续/重新开始/返回主菜单) 都能点"""
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

from core.constants import SCREEN_WIDTH  # noqa: E402
from core.game_state import GameState, GamePhase, GameMode  # noqa: E402
from core.game import Game  # noqa: E402

gs = GameState()
game = Game(pygame.display.set_mode((1280, 720)), gs)
game.gs.new_game(GameMode.ENDLESS, level=3)
game.start_level(3)

# 坐标直通: 注入内部坐标
game._screen_to_internal = lambda pos: pos

FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL:", msg)
    else:
        print("ok:", msg)


def click(ix, iy):
    pygame.mouse.get_pos = lambda: (ix, iy)
    game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))


# 按钮几何: x=(1920-480)/2=720, y0=540-40=500, 64 高, 间距 14
g0 = (960, 532)
g1 = (960, 610)
g2 = (960, 688)

# 1) 继续游戏
game.gs.phase = GamePhase.PAUSED
click(*g0)
check(game.gs.phase == GamePhase.PLAYING, "点击[继续游戏] → 恢复战斗")

# 2) 重新开始
game.gs.phase = GamePhase.PAUSED
lvl_before = game.gs.level
click(*g1)
check(game.gs.phase == GamePhase.PLAYING and game.gs.level == lvl_before,
      "点击[重新开始战斗] → 重开本关")

# 3) 返回主菜单
game.gs.phase = GamePhase.PAUSED
click(*g2)
check(game.gs.phase == GamePhase.MENU, "点击[返回主菜单] → 回主菜单")

# 4) 点空白处不应触发
game.gs.new_game(GameMode.ENDLESS, level=3)
game.start_level(3)
game.gs.phase = GamePhase.PAUSED
click(100, 100)
check(game.gs.phase == GamePhase.PAUSED, "点击空白处 → 保持暂停")

pygame.quit()
if FAILS:
    sys.exit(1)
print("ALL OK")
