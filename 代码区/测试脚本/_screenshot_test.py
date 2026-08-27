# -*- coding: utf-8 -*-
"""临时截图验证脚本: 渲染菜单/关卡/Boss/升级/结算到 PNG"""
import os
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame
# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from core.game_state import GameState, GamePhase, GameMode
from core.game import Game
from ui.menu_controller import MenuController

OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
os.makedirs(OUT, exist_ok=True)


def save(surf, name):
    path = os.path.join(OUT, name)
    pygame.image.save(surf, path)
    print("saved:", path)


def main():
    pygame.init()
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    except Exception:
        pass
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    gs = GameState()
    game = Game(screen, gs)
    menu = MenuController(screen, gs, game)

    # 1. 主菜单
    menu.draw_menu()
    save(screen, 'shot_menu.png')

    # 2. 第 1 关 (跑 120 帧让敌人刷出)
    gs.new_game(GameMode.STORY, level=1)
    game.start_level(1)
    gs.players[0].upgrade_levels = {"double_shot": 2, "pierce": 1, "armor": 1}
    for _ in range(120):
        game.update()
    game.render()
    save(screen, 'shot_level1.png')

    # 3. 第 5 关 Boss 竞技场
    gs.new_game(GameMode.STORY, level=5)
    game.start_level(5)
    gs.players[0].shield = 40
    for _ in range(60):
        game.update()
    game.render()
    save(screen, 'shot_boss5.png')

    # 4. 升级弹窗
    gs.new_game(GameMode.STORY, level=1)
    game.start_level(1)
    menu.show_upgrade_modal(gs.players[0])
    gs.phase = GamePhase.LEVEL_UPGRADE
    menu.draw_menu()
    save(screen, 'shot_upgrade.png')

    # 5. 结算页
    gs.phase = GamePhase.VICTORY
    game._result_stats = [
        ("关卡", "5"), ("模式", "剧情闯关"), ("本局分数", "4250"),
        ("历史最高", "9999"), ("击杀数", "36"), ("连击峰值", "12"),
    ]
    game.render()
    save(screen, 'shot_victory.png')

    pygame.quit()
    print("OK")


if __name__ == "__main__":
    main()
