# -*- coding: utf-8 -*-
"""虚拟触控层测试: 桌面调试模式 (鼠标左键拖拽模拟手指)
覆盖: 左轮盘移动 / 右轮盘手动瞄准 / 自动锁敌 / 射击按钮 / 暂停按钮 / CombinedInput 包装"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["TANK_TOUCH_DEBUG"] = "1"
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
from systems.ai_system import EnemyTank  # noqa: E402
from core.constants import EnemyType  # noqa: E402

gs = GameState()
game = Game(pygame.display.set_mode((1280, 720)), gs)
game.gs.new_game(GameMode.ENDLESS, level=1)
game.start_level(1)
t = game.touch
assert t.active, "调试模式应激活触控层"

SCALE = min(1280 / SCREEN_WIDTH, 720 / SCREEN_HEIGHT)  # 0.667


def win(ix, iy):
    return (ix * SCALE, iy * SCALE)


def ev(t, **kw):
    return pygame.event.Event(t, **kw)


def down(wx, wy):
    pygame.mouse.get_pos = lambda: (wx, wy)
    game.handle_event(ev(pygame.MOUSEBUTTONDOWN, button=1))


def drag(wx, wy):
    pygame.mouse.get_pos = lambda: (wx, wy)
    game.handle_event(ev(pygame.MOUSEMOTION))


def up(wx, wy):
    pygame.mouse.get_pos = lambda: (wx, wy)
    game.handle_event(ev(pygame.MOUSEBUTTONUP, button=1))


FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL:", msg)
    else:
        print("ok:", msg)


# 1) 左轮盘: 左半区按下 → 拖动 → 移动向量
down(*win(320, 600))
drag(*win(320, 460))
check(t.move_vec[1] < -0.3, f"左轮盘上推: move_vec={t.move_vec}")
up(*win(320, 460))
check(t.move_vec == (0.0, 0.0), "松手移动归零")

# 2) 右轮盘手动瞄准
gs.aim_mode = "manual"
player = game.player_tanks[0]
down(*win(1200, 600))
drag(*win(1400, 600))
check(t.aim_vec[0] > 0.3, f"右轮盘右推: aim_vec={t.aim_vec}")
ap = t.aim_point(player, [])
check(ap is not None and ap[0] > player.x + 100,
      f"手动瞄准点沿右轮盘方向前伸: {ap}")
up(*win(1400, 600))
check(t.aim_point(player, []) is None, "无右轮盘输入时返回 None (回退鼠标)")

# 3) 自动锁敌
gs.aim_mode = "auto"
e = EnemyTank(900, 500, EnemyType.SCOUT, level=1)
game.enemy_tanks.append(e)
ap = t.aim_point(player, game.enemy_tanks)
check(ap == (900, 500), f"自动锁敌 = 最近敌人中心: {ap}")
game.enemy_tanks.clear()
check(t.aim_point(player, []) is None, "无敌人时不锁 (回退鼠标)")

# 4) 射击按钮
down(*win(1745, 890))
check(t.shooting is True, "按住射击按钮 → 持续开火")
check(game.input.is_shooting(1) is True, "CombinedInput.is_shooting 透传触控")
up(*win(1745, 890))
check(t.shooting is False, "松手停火")

# 5) 暂停按钮
down(*win(112, 214))
check(game.gs.phase == GamePhase.PAUSED, "点暂停按钮 → 游戏进入暂停")
check(game.input.is_pause() is False, "暂停信号被游戏消费 (不重复触发)")
game.gs.phase = GamePhase.PLAYING  # 恢复战斗继续测
up(*win(112, 214))

# 6) CombinedInput: 触控优先, 其余转发
down(*win(400, 600))
drag(*win(400, 500))
check(game.input.get_player_move(1) == t.move_vec,
      "get_player_move 返回触控向量")
up(*win(400, 500))
check(game.input.get_player_move(1) == (0, 0),
      "无触控时转发键盘 (无按键 → 0,0)")

# 7) 绘制不崩溃 + 截图验收
down(*win(320, 600))
drag(*win(320, 500))
down(*win(1200, 600))
drag(*win(1300, 600))
game.render()
out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "素材检查", "shot_touch_ui.png")
pygame.image.save(game._internal_surface, out)
print("render with touch UI ok, saved:", out)

pygame.quit()
if FAILS:
    sys.exit(1)
print("ALL OK")
