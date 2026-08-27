# -*- coding: utf-8 -*-
"""方块再生机制测试: 砖/沙/玻璃低于初始值时补生, 越少越快, 且守护约束全守"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402
# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))


pygame.init()
pygame.display.set_mode((320, 240))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.constants import (WallType, TILE_SIZE)  # noqa: E402
from core.game_state import GameState, GameMode  # noqa: E402
from core.game import Game  # noqa: E402

FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL:", msg)
    else:
        print("ok:", msg)


gs = GameState()
game = Game(pygame.display.set_mode((320, 240)), gs)
game.gs.new_game(GameMode.ENDLESS, level=4)
game.start_level(4)

RE = game._regen_types
initial = sum(1 for w in game.walls if w.type in RE)
check(initial > 0, f"第 4 关初始可破坏方块 {initial} > 0")

# 1) 清空所有可破坏方块 → 应触发补生
game.walls = [w for w in game.walls if w.type not in RE]
check(sum(1 for w in game.walls if w.type in RE) == 0, "清空后为 0")
game._regen_timer = 0
game._update_wall_regen(0)
cur = sum(1 for w in game.walls if w.type in RE)
check(cur == 1, f"补生 1 颗, 实得 {cur}")
check(game._regen_timer <= 300, f"清空时最快档 (~250ms), 实得 {game._regen_timer}")
for w in game.walls:
    if w.type in RE:
        check(w.type in (WallType.BRICK, WallType.SAND, WallType.GLASS),
              "补生类型只可能是砖/沙/玻璃")

# 2) 越少越快: 接近满时补生间隔应明显更慢
game.walls = [w for w in game.walls if w.type not in RE]
for _ in range(initial - 1):
    game._spawn_regen_wall()
cur = sum(1 for w in game.walls if w.type in RE)
check(cur == initial - 1, f"补到 initial-1 ({initial-1}), 实得 {cur}")
game._regen_timer = 0
game._update_wall_regen(0)
slow_interval = game._regen_timer
check(slow_interval > 1500, f"接近满时慢档 (>1500ms), 实得 {slow_interval}")

# 3) 守护约束: 补生块不压玩家、不进基地环、连通性保持
game.walls = [w for w in game.walls if w.type not in RE]
game._regen_timer = 0
for _ in range(initial):
    game._regen_timer = 0
    game._update_wall_regen(0)
for w in game.walls:
    if w.type in RE:
        rect = pygame.Rect(w.col * TILE_SIZE, w.row * TILE_SIZE,
                           TILE_SIZE, TILE_SIZE)
        for t in game.player_tanks:
            check(not rect.colliderect(t.get_rect()),
                  "补生块不压玩家坦克")
        base = game.base_region
        if base:
            check(not (base[0] - 1 <= w.col <= base[2] + 1
                       and base[1] - 1 <= w.row <= base[3] + 1),
                  "补生块不进基地保护环")
check(game.map_gen._is_connected(game.walls), "补生后地图仍连通")

pygame.quit()
if FAILS:
    print(f"{len(FAILS)} FAILS")
    sys.exit(1)
print("ALL OK")
