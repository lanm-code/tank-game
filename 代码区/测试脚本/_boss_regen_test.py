# -*- coding: utf-8 -*-
"""Boss 关方块再生测试: 竞技场开局无方块 → 战斗中持续补生砖/沙/玻璃 (权重 40/40/20)"""
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

from core.constants import WallType  # noqa: E402
from core.game_state import GameState, GameMode  # noqa: E402
from core.game import Game  # noqa: E402

FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL:", msg)
    else:
        print("ok:", msg)


def breakable(game):
    return [w for w in game.walls if w.type in game._regen_types]


gs = GameState()
game = Game(pygame.display.set_mode((1280, 720)), gs)

# 1) Boss 竞技场设定了再生目标量
gs.new_game(GameMode.ENDLESS, level=5)
game.start_level(5)
check(game._regen_initial == 10, f"Boss 关再生目标 = 10 (实际 {game._regen_initial})")
check(len(breakable(game)) == 0, "Boss 竞技场初始无可破坏方块")

# 2) 战斗中持续补生 (时间驱动)
game._regen_timer = 1
for _ in range(900):
    game._update_wall_regen(16.7)
n = len(breakable(game))
check(n > 0, f"Boss 战中生成方块 (实际 {n})")
check(n <= game._regen_initial, f"不超过目标量 (实际 {n}/{game._regen_initial})")

# 3) 三种类型都会出现 (权重 40/40/20)
counts = {WallType.BRICK: 0, WallType.SAND: 0, WallType.GLASS: 0}
for w in breakable(game):
    counts[w.type] += 1
check(counts[WallType.BRICK] > 0, f"出现砖块 ({counts[WallType.BRICK]})")
check(counts[WallType.SAND] > 0, f"出现沙粒 ({counts[WallType.SAND]})")
check(counts[WallType.GLASS] > 0, f"出现玻璃 ({counts[WallType.GLASS]})")

# 4) 拆掉后继续补回 (维持目标量)
for w in list(breakable(game)):
    w.destroyed = True
game.walls = [w for w in game.walls if not w.destroyed]
game._regen_timer = 1
for _ in range(1200):
    game._update_wall_regen(16.7)
n2 = len(breakable(game))
check(n2 > 0, f"清空后继续补生 (实际 {n2})")

# 5) Boss Rush 同样生效
gs.new_game(GameMode.BOSS_RUSH, level=5)
game.start_level(5)
check(game._regen_initial > 0, "Boss Rush 竞技场同样有再生目标")

# 6) 普通关不受影响 (初始 = 实际方块数, 由地图生成)
gs.new_game(GameMode.ENDLESS, level=2)
game.start_level(2)
check(game._regen_initial == len(breakable(game)),
      "普通关再生目标 = 初始方块数")

pygame.quit()
if FAILS:
    sys.exit(1)
print("ALL OK")
