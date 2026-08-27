# -*- coding: utf-8 -*-
"""血量继承测试: 普通关继承上一关血量, Boss 战回满"""
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
game = Game(pygame.display.set_mode((1280, 720)), gs)

# 1) 开局满血
gs.new_game(GameMode.ENDLESS, level=1)
game.start_level(1)
check(gs.players[0].hp == gs.players[0].max_hp, "开局满血")

# 2) 普通关继承: 37 血进第 2 关还是 37
gs.players[0].hp = 37
game.start_level(2)
check(gs.players[0].hp == 37, "普通关: 继承上一关血量 37")
check(game.player_tanks[0].hp == 37, "生成的坦克同步继承血量")

# 3) 普通关保底: 1 血进第 3 关还是 1 (不归零)
gs.players[0].hp = 1
game.start_level(3)
check(gs.players[0].hp == 1, "普通关: 1 血保底继承")

# 4) Boss 战回满: 10 血进第 5 关 → 满血
gs.players[0].hp = 10
game.start_level(5)
check(gs.players[0].hp == gs.players[0].max_hp, "Boss 战: 战前回满")

# 5) Boss 战后普通关继续继承: 第 6 关满血进 → 打掉 30 → 第 6 关开局还是满血(本关满)
gs.players[0].hp = 70
game.start_level(6)
check(gs.players[0].hp == 70, "Boss 后普通关: 继承 70")

# 6) Boss Rush: 每关都是 Boss 战 → 全回
gs.new_game(GameMode.BOSS_RUSH, level=5)
game.start_level(5)
gs.players[0].hp = 5
game.start_level(10)
check(gs.players[0].hp == gs.players[0].max_hp, "Boss Rush: 每关 Boss 战全回")

pygame.quit()
if FAILS:
    sys.exit(1)
print("ALL OK")
