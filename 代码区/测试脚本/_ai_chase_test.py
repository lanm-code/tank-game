# -*- coding: utf-8 -*-
"""敌人 AI 主动进攻 + 卡墙脱困 规则测试 (Headless)
运行: py -3.14 _ai_chase_test.py
覆盖: 超视界远程开火 / 隔砖墙破墙射击 / 隔钢墙不开火 / 远距不开火仍追击 / 墙滑绕行
"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import pygame

# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

pygame.init()
pygame.display.set_mode((320, 240))

from core.constants import *
from entities.wall import Wall
from systems.ai_system import EnemyTank

MAP = pygame.Rect(0, 0, 1000, 600)

FAILS = []


def check(cond, msg):
    if cond:
        print("  [PASS]", msg)
    else:
        print("  [FAIL]", msg)
        FAILS.append(msg)


class FakePlayer:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.dead = False
        self.last_fire_ms = 0

    def get_rect(self):
        return pygame.Rect(self.x - 28, self.y - 28, 56, 56)


def full_height_wall(col, wtype):
    """整列墙体 (y 0..640), 防止敌人横移绕出射线"""
    return [Wall(col, r, wtype) for r in range(0, 10)]


def run():
    print("== 1. 远程主动开火 (超出视界, 有直视线) ==")
    et = EnemyTank(100, 100, EnemyType.ARTILLERY, level=1)
    p = FakePlayer(750, 100)  # d=650 > 视界600*0.95, <= engage 900
    bullets = []
    fired = False
    for _ in range(120):
        et.update(16.666, [], [], [p], MAP, bullets, None, None)
        if bullets:
            fired = True
            break
    check(fired, "炮兵在 650px 外(超视界)主动开火")

    print("== 2. 隔钢墙不开火 ==")
    et2 = EnemyTank(300, 300, EnemyType.SCOUT, level=1)
    steel2 = full_height_wall(6, WallType.STEEL)  # 整列钢墙挡在弹道上
    p2 = FakePlayer(500, 300)
    bullets2 = []
    for _ in range(120):
        et2.update(16.666, steel2, [], [p2], MAP, bullets2, None, None)
    check(len(bullets2) == 0, "隔钢墙不开火 (打了没用)")

    print("== 3. 隔砖墙破墙射击 ==")
    et3 = EnemyTank(300, 300, EnemyType.SCOUT, level=1)
    bricks3 = full_height_wall(6, WallType.BRICK)
    p3 = FakePlayer(600, 300)
    bullets3 = []
    fired3 = False
    for _ in range(600):
        et3.update(16.666, bricks3, [], [p3], MAP, bullets3, None, None)
        for b in bullets3:
            if not b.dead:
                b.update(16.666, bricks3, None, MAP, [])
        bullets3 = [b for b in bullets3 if not b.dead]
        if bullets3:
            fired3 = True
        if any(w.destroyed for w in bricks3):
            break
    check(fired3, "隔砖墙仍然开火")
    check(any(w.destroyed for w in bricks3), "炮弹打碎砖墙开路")

    print("== 4. 超远距离不开火但仍追击 ==")
    et4 = EnemyTank(100, 100, EnemyType.ARTILLERY, level=1)
    p4 = FakePlayer(1600, 100)  # d=1500 > engage 900 且 > sight*2
    x0 = et4.x
    bullets4 = []
    for _ in range(60):
        et4.update(16.666, [], [], [p4], MAP, bullets4, None, None)
    check(len(bullets4) == 0, "1500px 外不开火")
    check(et4.x > x0, "仍然向玩家方向追击")

    print("== 5. 被墙挡住时墙滑绕行 ==")
    walls5 = [Wall(5, 3, WallType.STEEL), Wall(5, 4, WallType.STEEL),
              Wall(5, 5, WallType.STEEL), Wall(5, 6, WallType.STEEL)]
    et5 = EnemyTank(250, 300, EnemyType.SCOUT, level=1)
    p5 = FakePlayer(600, 300)
    for _ in range(1200):
        et5.update(16.666, walls5, [], [p5], MAP, [], None, None)
        if et5.x > 400:
            break
    check(et5.x > 400, f"沿墙滑行绕过钢墙 (x={et5.x:.0f}, y={et5.y:.0f})")

    print("== 6. 水渍滑行撞钢墙不钉死 ==")
    # 水渍 2x3 集群 (x 192..320, y 192..448) + 右侧整列钢墙 (x 320..384)
    walls6 = [Wall(3, 3, WallType.WATER_STAIN), Wall(4, 3, WallType.WATER_STAIN),
              Wall(3, 4, WallType.WATER_STAIN), Wall(4, 4, WallType.WATER_STAIN),
              Wall(3, 5, WallType.WATER_STAIN), Wall(4, 5, WallType.WATER_STAIN)]
    for r in (3, 4, 5):
        walls6.append(Wall(5, r, WallType.STEEL))
    et6 = EnemyTank(288, 288, EnemyType.SCOUT, level=1)
    p6 = FakePlayer(600, 288)
    for _ in range(900):
        et6.update(16.666, walls6, [], [p6], MAP, [], None, None)
        if et6.x > 400:
            break
    check(et6.x > 400,
          f"水渍上滑行撞钢墙后仍能脱困绕行 (x={et6.x:.0f}, y={et6.y:.0f})")

    print("== 7. 玩家水渍撞墙后能改向脱出 ==")
    from entities.tank import PlayerTank

    class FakeData:
        def __init__(self):
            self.id = 1
            self.color = (0, 180, 255)
            self.tank_color = None
            self.hp = 100
            self.max_hp = 100
            self.speed = 3.0
            self.shield = 0
            self.invincible = False
            self.base_damage = 20
            self.bullet_type = BulletType.EGG
            self.fire_rate_mult = 1.0
            self.pierce_add = 0
            self.ricochet_add = 0
            self.multi_shot = 1
            self.super_charge = 0

    class FakeInput:
        def __init__(self, dx=0, dy=0):
            self.dx = dx
            self.dy = dy

        def get_player_move(self, pid):
            return self.dx, self.dy

        def is_shooting(self, pid):
            return False

        def is_super(self, pid):
            return False

    pt = PlayerTank(288, 288, FakeData())
    inp = FakeInput(1, 0)  # 一直按住右键冲向钢墙
    walls7 = [Wall(4, 4, WallType.WATER_STAIN), Wall(5, 4, WallType.STEEL)]
    for _ in range(90):
        pt.update(16.666, inp, walls7, [], MAP, [], None, None)
    x_pin = pt.x
    check(x_pin <= 293, f"玩家被钢墙挡住 (x={x_pin:.1f})")
    inp.dx, inp.dy = 0, -1  # 松开右键改按上
    y0 = pt.y
    for _ in range(30):
        pt.update(16.666, inp, walls7, [], MAP, [], None, None)
    check(pt.y < y0 - 5, f"撞墙后改向立即脱出 (y {y0:.0f} -> {pt.y:.0f})")

    pygame.quit()
    if FAILS:
        print("\n== FAILED %d 项 ==" % len(FAILS))
        for f in FAILS:
            print("  -", f)
        raise SystemExit(1)
    print("\nALL PASS")


if __name__ == "__main__":
    run()
