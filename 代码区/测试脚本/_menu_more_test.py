# -*- coding: utf-8 -*-
"""图鉴导航流程验证: 封面 → 游戏图鉴 → 各分类 → Esc 逐级返回"""
import os
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame
# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from core.game_state import GameState
from core.game import Game
from ui.menu_controller import MenuController

OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print('FAIL:', msg)
    else:
        print('ok:', msg)


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
    cx = menu.codex_ui

    def key(k):
        menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k))

    def shot(name):
        menu.draw_menu()
        pygame.image.save(screen, os.path.join(OUT, name))

    print('initial:', menu.mode, [b['text'] for b in menu.buttons])
    check(menu.buttons[3]['text'] == '游戏图鉴', '主菜单第 4 按钮 = 游戏图鉴')
    shot('shot_codex_flow_main.png')

    key(pygame.K_4)
    check(menu.mode == 'codex' and cx.view == 'hub', 'K4 → 图鉴总览')
    shot('shot_codex_flow_hub.png')

    key(pygame.K_1)
    check(cx.view == 'cat' and cx.cat_id == 'tank', '总览 1 → 坦克图鉴')
    key(pygame.K_ESCAPE)
    check(cx.view == 'hub', 'Esc → 回总览')

    key(pygame.K_2)
    check(cx.view == 'cat' and cx.cat_id == 'bullet', '总览 2 → 子弹图鉴')
    key(pygame.K_ESCAPE)

    key(pygame.K_3)
    check(cx.view == 'boss', '总览 3 → 敌人图鉴 (首领圆盘)')
    key(pygame.K_TAB)
    check(cx.boss_tab == 'grunt', 'Tab → 敌军页签')
    key(pygame.K_ESCAPE)
    check(cx.view == 'hub', 'Esc → 回总览')

    key(pygame.K_4)
    check(cx.view == 'skill', '总览 4 → 技能图鉴')
    key(pygame.K_TAB)
    check(cx.skill_tab == 1, 'Tab → 普通档')
    key(pygame.K_ESCAPE)
    check(cx.view == 'hub', 'Esc → 回总览')

    key(pygame.K_5)
    check(cx.view == 'cat' and cx.cat_id == 'pickup', '总览 5 → 道具图鉴')
    key(pygame.K_TAB)
    check(cx.cat_tab == 1, 'Tab → 奖励页签')
    key(pygame.K_ESCAPE)

    key(pygame.K_6)
    check(cx.view == 'cat' and cx.cat_id == 'tile', '总览 6 → 地块图鉴')
    key(pygame.K_RIGHT)
    check(cx.cat_idx == 1, '→ 切换条目')
    key(pygame.K_ESCAPE)

    key(pygame.K_ESCAPE)
    check(menu.mode == 'main', '总览 Esc → 回主菜单')
    shot('shot_codex_flow_back.png')

    # 鼠标点击路径: 总览页点击返回按钮 → 返回 "exit" 信号 (由 menu.handle_event 转成回主菜单)
    key(pygame.K_4)
    res = menu.codex_ui._handle_click(60, 52)
    check(res == 'exit', '总览点击左上角返回 → exit 信号')
    menu.build_main_menu()
    check(menu.mode == 'main', 'exit 后重建主菜单')

    # 分类页点击返回 → 回总览
    key(pygame.K_4)
    key(pygame.K_1)
    res = menu.codex_ui._handle_click(60, 52)
    check(res is None and menu.codex_ui.view == 'hub', '分类页点击返回 → 回总览')
    pygame.quit()
    if FAILS:
        print(f'{len(FAILS)} FAILS')
        sys.exit(1)
    print('ALL OK')


if __name__ == '__main__':
    main()
