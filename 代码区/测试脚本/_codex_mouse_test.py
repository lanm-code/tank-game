# -*- coding: utf-8 -*-
"""_mouse 坐标换算回归: draw 期间 self.screen=内部表面时, 鼠标换算必须仍按真实窗口"""
import os
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import pygame  # noqa: E402
# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))


pygame.init()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT  # noqa: E402
from core.game_state import GameState  # noqa: E402
from ui.codex_ui import CodexUI, HUB_X  # noqa: E402

gs = GameState()


class FakeWin:
    def __init__(self, w, h):
        self._w, self._h = w, h

    def get_width(self):
        return self._w

    def get_height(self):
        return self._h


# 真实窗口 1280×720, 内部分辨率 1920×1080, scale=2/3
win = pygame.display.set_mode((1280, 720))
ui = CodexUI(win, gs, None)
ui._win = FakeWin(1280, 720)

FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print('FAIL:', msg)
    else:
        print('ok:', msg)


orig_get_pos = pygame.mouse.get_pos

try:
    # 模拟窗口坐标 (560, 200) → 内部 (840, 300) (坦克卡左上角附近)
    pygame.mouse.get_pos = lambda: (560, 200)
    # 关键: draw 期间 self.screen 被切成内部表面 (1920×1080), _mouse 仍要用窗口算
    ui.screen = ui._internal
    ix, iy = ui._mouse()
    check((ix, iy) == (840, 300), f'窗口(560,200)→内部(840,300), 实得 ({ix},{iy})')
    ui.screen = win

    # 右下卡片 (技能图鉴, 内部 x=840+525=1365, y=495) 对应窗口 (910, 330)
    pygame.mouse.get_pos = lambda: (910, 330)
    ui.screen = ui._internal
    ix, iy = ui._mouse()
    cards = ui._hub_card_rects()
    hit = [i for i, r in enumerate(cards) if r.collidepoint(ix, iy)]
    check(hit == [3], f'窗口(910,330) 应命中技能图鉴卡(idx3), 实得 {hit}')
    ui.screen = win

    # 左橱窗区域点击 (内部 60,300) → 窗口 (40, 200)
    pygame.mouse.get_pos = lambda: (40, 200)
    ui.screen = ui._internal
    ix, iy = ui._mouse()
    check((ix, iy) == (60, 300), f'窗口(40,200)→内部(60,300), 实得 ({ix},{iy})')
    ui.screen = win

    # ---- 光标跟随: 分类页网格悬停 → 左面板切换 ----
    ui.open(view="cat", cat_id="pickup")
    ui.screen = ui._internal
    # 第 5 张道具卡中心: 内部 x = 740+250/2+(5%4)*(250+24) = 865+274=1139, y = 250+160/2+(5//4)*(160+16)=330+176=506
    pygame.mouse.get_pos = lambda: (int(1139 * 2 / 3), int(506 * 2 / 3))
    ui.draw()
    check(ui.cat_idx == 5, f'悬停第5张道具卡 → cat_idx=5, 实得 {ui.cat_idx}')
    ui.screen = win

    # ---- 光标跟随: Boss 圆盘悬停 → 面板切换 ----
    ui.open(view="boss")
    ui.screen = ui._internal
    # 第 3 个圆盘中心: 内部 (960, 380-48)
    pygame.mouse.get_pos = lambda: (int(960 * 2 / 3), int(332 * 2 / 3))
    ui.draw()
    check(ui.boss_idx == 2, f'悬停第3个Boss圆盘 → boss_idx=2, 实得 {ui.boss_idx}')
    ui.screen = win

    # ---- 光标跟随: 敌军卡悬停 → 面板切换 ----
    ui.boss_tab = "grunt"
    ui.screen = ui._internal
    # 第 4 张敌军卡中心: 内部 x0=150, 卡宽240 间距36 → 中心 = 150+3*276+120=1098, y=330+75=405
    pygame.mouse.get_pos = lambda: (int(1098 * 2 / 3), int(405 * 2 / 3))
    ui.draw()
    check(ui.grunt_idx == 3, f'悬停第4张敌军卡 → grunt_idx=3, 实得 {ui.grunt_idx}')
    ui.screen = win
finally:
    pygame.mouse.get_pos = orig_get_pos

pygame.quit()
if FAILS:
    sys.exit(1)
print('ALL OK')
