# -*- coding: utf-8 -*-
"""临时验证: Boss4 袋鼠 / Boss5 华强 机制 + 截图"""
import os
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame
# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from core.game_state import GameState, GameMode
from core.game import Game

OUT = sys.argv[1] if len(sys.argv) > 1 else '.'


def main():
    pygame.init()
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    except Exception:
        pass
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    # Boss4 袋鼠 (第20关)
    gs = GameState()
    game = Game(screen, gs)
    gs.new_game(GameMode.STORY, level=20)
    game.start_level(20)
    b4 = game.gs.boss
    hop_states = {}
    for _ in range(900):  # 15秒
        game.update()
        hop_states[b4.hop_state] = hop_states.get(b4.hop_state, 0) + 1
    print('Boss4:', b4.name, '| hp =', b4.hp, '| hop states =', hop_states)
    game.render()
    pygame.image.save(screen, os.path.join(OUT, 'shot_boss20.png'))

    # Boss5 华强 (第25关)
    gs2 = GameState()
    game2 = Game(screen, gs2)
    gs2.new_game(GameMode.STORY, level=25)
    game2.start_level(25)
    b5 = game2.gs.boss
    dash_states = {}
    for _ in range(900):
        game2.update()
        dash_states[b5.dash_state] = dash_states.get(b5.dash_state, 0) + 1
    print('Boss5:', b5.name, '| hp =', b5.hp, '| charge states =', dash_states)
    game2.render()
    pygame.image.save(screen, os.path.join(OUT, 'shot_boss25.png'))

    # Boss5 半血狂暴 (阶段3)
    b5.hp = 500
    for _ in range(300):
        game2.update()
    print('Boss5 phase =', b5.phase, '(期望3) | bullets =', len(game2.bullets))
    game2.render()
    pygame.image.save(screen, os.path.join(OUT, 'shot_boss25_phase3.png'))

    pygame.quit()
    print('ALL OK')


if __name__ == '__main__':
    main()
