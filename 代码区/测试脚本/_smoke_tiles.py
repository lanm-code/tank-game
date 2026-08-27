# -*- coding: utf-8 -*-
"""无头冒烟: 各关卡新方块/地块/传送门全流程跑帧, 无崩溃即过
运行: py -3.14 _smoke_tiles.py
"""
import os
import sys
import time

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

gs = GameState()
for p in gs.players:
    p.invincible = True  # 冒烟期间玩家不掉血, 保持战斗持续
game = Game(screen, gs)

ok = True
for lv in (2, 5, 8, 10, 14):
    game.start_level(lv)
    t0 = time.time()
    frames = 0
    try:
        while time.time() - t0 < 4:
            game.begin_frame()
            game.update()
            game.render()
            frames += 1
    except Exception as e:
        import traceback
        print(f"[FAIL] level {lv}: {type(e).__name__}: {e}")
        traceback.print_exc()
        ok = False
        break
    types = {}
    for w in game.walls:
        types[w.type] = types.get(w.type, 0) + 1
    print(f"[OK] level {lv}: {frames} 帧无崩溃, 墙类型: {types}")

pygame.quit()
print("SMOKE PASS" if ok else "SMOKE FAIL")
sys.exit(0 if ok else 1)
