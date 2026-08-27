# -*- coding: utf-8 -*-
"""技能页点击闪退复现: 模拟鼠标悬停/点击所有缩略图、页签、圆盘"""
import os
import sys
import traceback

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import pygame  # noqa: E402
# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))


pygame.init()
pygame.display.set_mode((1280, 720))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT  # noqa: E402
from core.game_state import GameState  # noqa: E402
from ui.codex_ui import CodexUI, SKILL_TABS  # noqa: E402

gs = GameState()
screen = pygame.display.set_mode((1280, 720))
ui = CodexUI(screen, gs, None)
ui.open(view="skill")
ui.skill_tab = 0

# 把窗口坐标换算成内部分辨率坐标 (1280x720 窗口按比例缩放 1920x1080)
SCALE = min(1280 / SCREEN_WIDTH, 720 / SCREEN_HEIGHT)


def to_internal(wx, wy):
    sw = int(SCREEN_WIDTH * SCALE)
    sh = int(SCREEN_HEIGHT * SCALE)
    ox = (1280 - sw) // 2
    oy = (720 - sh) // 2
    return int((wx - ox) / SCALE), int((wy - oy) / SCALE)


def click(wx, wy):
    ix, iy = to_internal(wx, wy)
    ui._mouse = lambda: (ix, iy)
    ui.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
    ui.draw()


def click_internal(ix, iy):
    """直接注入内部分辨率坐标 (无需窗口换算)"""
    ui._mouse = lambda: (ix, iy)
    ui.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
    ui.draw()


errors = []
try:
    # 1) 每个稀有度页签
    for tab in range(len(SKILL_TABS)):
        ui.skill_tab = tab
        ui.skill_idx = 0
        skills = ui._skill_list()
        print(f"tab {tab}: {len(skills)} skills")
        # 2) 每个缩略图位置: 缩略图条在 y=680, x 从 340 - total//2 起
        tw, gap = 48, 6
        total = len(skills) * (tw + gap) - gap
        tx0 = 340 - total // 2
        for i in range(len(skills)):
            ix = tx0 + i * (tw + gap) + tw // 2
            iy = 680 + tw // 2
            click(ix, iy)
        # 3) 大圆盘中心
        click(340, 400)
        # 4) 页签行: 从 60+名称宽+60 开始 (名称=技能图鉴 36px 粗体≈144px)
        cx = 60 + 144 + 60
        for i, tab3 in enumerate(SKILL_TABS):
            text = tab3[0]
            w = ui.f.render(text, True, (255, 255, 255)).get_width()
            click(cx + w // 2, 118)
            cx += w + 44
    # 5) 其他页面各点击一轮 (排除其他页闪退可能)
    for view, cat in [("hub", None), ("cat", "pickup"), ("cat", "bullet"),
                      ("cat", "tile"), ("cat", "tank"), ("boss", None)]:
        ui.open(view=view, cat_id=cat)
        print("view:", view, cat)
        for i in range(20):
            click(60 + i * 90, 100 + (i % 8) * 90)
    # 6) 翻页大按钮点击: 地块页 13 条 = 2 页 (内部坐标直接注入)
    ui.open(view="cat", cat_id="tile")
    ui.cat_idx = 0
    ui.draw()  # 生成 _page_rects
    mid_x = 740 + (250 * 4 + 24 * 3) // 2
    click_internal(mid_x + 70 + 100, 800 + 27)      # 下一页 (中心)
    assert ui.cat_idx == 12, f"下一页应到 idx12, 实得 {ui.cat_idx}"
    click_internal(mid_x - 270 + 100, 800 + 27)     # 上一页 (中心)
    assert ui.cat_idx == 0, f"上一页应回 idx0, 实得 {ui.cat_idx}"
    print("page buttons ok")
    print("NO CRASH")
except Exception:
    traceback.print_exc()
    errors.append("crash")
    print("CRASH REPRODUCED")

pygame.quit()
sys.exit(1 if errors else 0)
