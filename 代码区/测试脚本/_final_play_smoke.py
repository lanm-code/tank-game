# -*- coding: utf-8 -*-
"""最终游玩冒烟: 真实游戏循环跑 90 模拟秒 (随机移动/持续开火/敌人/道具/再生),
再手动击杀推进到第 3 关, 全程无异常即通过。"""
import os
import random
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
from core.game_state import GameState, GameMode, GamePhase  # noqa: E402
from core.game import Game  # noqa: E402

gs = GameState()
game = Game(pygame.display.set_mode((1280, 720)), gs)
gs.new_game(GameMode.ENDLESS, level=2)
game.start_level(2)

rnd = random.Random(42)
frames = 0
errors = []


def key(k, down=True):
    game.handle_event(pygame.event.Event(
        pygame.KEYDOWN if down else pygame.KEYUP, key=k))


try:
    while frames < 90 * 60:  # 90 秒
        # 随机游走输入
        for k in (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d):
            if rnd.random() < 0.5:
                key(k, rnd.random() < 0.7)
        # 持续开火 (按住右键 = 射击键)
        game.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=3))
        game.update()
        game.render()
        frames += 1
        # 每 5 秒: 若有敌人, 直接清掉一半 (模拟击杀推进), 触发掉落/再生
        if frames % 300 == 0 and game.enemy_tanks:
            for e in game.enemy_tanks[:max(1, len(game.enemy_tanks) // 2)]:
                e.take_damage(999)
    # 再各跑第 3 / 4 关 30 秒 (草丛/木箱/玻璃/泥沼 + 方块再生场景)
    for lv in (3, 4):
        game.gs.phase = GamePhase.PLAYING
        game.start_level(lv)
        for _ in range(30 * 60):
            game.update()
            game.render()
            if rnd.random() < 0.3:
                game.handle_event(pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN, button=3))
        print(f"level {lv} ok")
except Exception as e:
    import traceback
    traceback.print_exc()
    errors.append(str(e))

print(f"frames={frames} level={game.gs.level} errors={len(errors)}")
pygame.quit()
sys.exit(1 if errors else 0)
