# -*- coding: utf-8 -*-
"""
钢铁前线：霓虹坦克战 - 主入口
Tank Battle - Main Entry
"""
import sys
import os
import traceback

# 全局异常捕获: 写崩溃日志
_CRASH_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_crash_log.txt")

def _crash_hook(exc_type, exc_value, exc_tb):
    with open(_CRASH_LOG, "w", encoding="utf-8") as f:
        f.write("=== GAME CRASH ===\n")
        traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    traceback.print_exception(exc_type, exc_value, exc_tb)
    sys.exit(1)

sys.excepthook = _crash_hook

import pygame

from core.constants import *
from core.game import Game
from core.game_state import GameState, GamePhase, GameMode
from ui.menu_controller import MenuController


def main():
    pygame.init()
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    except Exception:
        pass  # 音频初始化失败不阻止游戏

    pygame.display.set_caption("钢铁前线：霓虹坦克战")

    # 内部分辨率 (游戏逻辑用) 与显示分辨率 (窗口大小) 分离
    # 游戏内部始终按 SCREEN_WIDTH x SCREEN_HEIGHT 渲染, 再缩放到窗口
    from core.constants import SCREEN_WIDTH as _IW, SCREEN_HEIGHT as _IH
    DISPLAY_W = 1280
    DISPLAY_H = 720
    screen = pygame.display.set_mode((DISPLAY_W, DISPLAY_H), pygame.RESIZABLE)
    print(f"[Display] OK: window={DISPLAY_W}x{DISPLAY_H}  internal={_IW}x{_IH}")

    clock = pygame.time.Clock()

    game_state = GameState()
    game = Game(screen, game_state)
    menu = MenuController(screen, game_state, game)

    running = True
    while running:
        if game_state.phase in (GamePhase.MENU, GamePhase.LEVEL_UPGRADE):
            menu.draw_menu()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                menu.handle_event(event)
        else:
            game.begin_frame()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                game.handle_event(event)
            game.update()
            game.render()

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
