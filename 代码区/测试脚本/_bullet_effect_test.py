# -*- coding: utf-8 -*-
"""子弹效果规则测试 (Headless)
运行: py -3.14 _bullet_effect_test.py
覆盖: 炮弹纯净 / 篮球回弹3次 / 奶蛋穿透1次 / 鸡蛋射速 / 飞刀2倍伤害 /
      麦克风眩晕 / 外卖范围伤害 (直击100% 溅射60%) / Boss 25% 眩晕
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
from core.game_state import GameState
from core.game import Game
from entities.bullet import Bullet
from entities.tank import Tank, PlayerTank
from entities.wall import Wall
from entities.boss import Boss, BossId
from systems.ai_system import EnemyTank
from utils.math_utils import dist

MAP = pygame.Rect(0, 0, 600, 400)

FAILS = []


def check(cond, msg):
    if cond:
        print("  [PASS]", msg)
    else:
        print("  [FAIL]", msg)
        FAILS.append(msg)


class FakeData:
    """PlayerTank 所需的极简 player_data"""

    def __init__(self):
        self.id = 1
        self.color = (0, 180, 255)
        self.tank_color = None
        self.hp = 100
        self.max_hp = 100
        self.speed = 3.0
        self.shield = 0
        self.invincible = False


class FakePlayer:
    """EnemyTank / Boss update 所需的极简玩家"""

    def __init__(self, x=500, y=300):
        self.x = x
        self.y = y
        self.dead = False
        self.last_fire_ms = 0

    def get_rect(self):
        return pygame.Rect(self.x - 28, self.y - 28, 56, 56)


class FakeBoss:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.dead = False
        self.hp = 100

    def get_rect(self):
        return pygame.Rect(self.x - 50, self.y - 50, 100, 100)

    def take_damage(self, dmg, **kwargs):
        self.hp -= dmg


def run():
    print("== 1. 炮弹 = 纯净基准 ==")
    c = BULLET_CONFIG[BulletType.CANNON]
    check(c["pierce"] == 0 and c["ricochet"] == 0
          and c.get("slow", 0) == 0 and c.get("stun", 0) == 0
          and c.get("splash") is None
          and c.get("explode", False) is False and "sine" not in c,
          "炮弹无 pierce/ricochet/slow/stun/splash/explode/sine")

    print("== 2. 篮球: 未命中可回弹3次 ==")
    check(BULLET_CONFIG[BulletType.BASKETBALL]["ricochet"] == 3, "篮球配置 ricochet=3")
    b = Bullet(50, 200, 0, BulletType.BASKETBALL, 1)
    flips, frames, last_angle = 0, 0, b.angle
    while not b.dead and frames < 5000:
        b.update(16.666, [], None, MAP, [])
        if b.angle != last_angle:
            flips += 1
            last_angle = b.angle
        frames += 1
    check(b.dead and flips == 3 and b.ricochet == 0,
          f"回弹3次后第4次触边消失 (flips={flips}, ricochet={b.ricochet}, frames={frames})")

    b2 = Bullet(300, 200, 0, BulletType.BASKETBALL, 1)
    hit = b2.try_hit_tank(Tank(320, 200))
    check(hit and b2.dead and b2.ricochet == 3, "篮球命中目标后消失且不回弹")

    print("== 3. 奶蛋: 体型不变 + 穿透1次 ==")
    c3 = BULLET_CONFIG[BulletType.MILKY_EGG]
    check(c3["radius"] == 10 and c3["pierce"] == 1 and "slow" not in c3,
          "奶蛋 radius=10 不变 / pierce=1 / 无减速")
    b3 = Bullet(130, 200, 0, BulletType.MILKY_EGG, 1)
    t1, t2 = Tank(130, 200), Tank(135, 200)
    check(b3.try_hit_tank(t1) and not b3.dead and t1.hp == 76,
          "奶蛋命中第一目标 (伤害24) 后继续飞行")
    check(not b3.try_hit_tank(t1), "同一目标不重复结算 (hit_set)")
    check(b3.try_hit_tank(t2) and b3.dead and t2.hp == 76 and b3.pierce == 0,
          "穿透第二目标后消失, pierce 耗尽")

    print("== 4. 鸡蛋: 发射速度最快 ==")
    c4 = BULLET_CONFIG[BulletType.EGG]
    min_cd = min(cfg["cooldown"] for cfg in BULLET_CONFIG.values())
    check(c4["cooldown"] == 350 and c4["cooldown"] == min_cd, "鸡蛋冷却350 = 全场最快")
    check(c4["speed"] == 9, "鸡蛋弹速9")
    t4 = Tank(300, 300)
    t4.bullet_type = BulletType.EGG
    t4.fire([], 1)
    check(t4.fire_cooldown == 350, "鸡蛋实际开火冷却 350ms")

    print("== 5. 飞刀: 2倍伤害 + 最慢射速 + 无回弹极速 ==")
    c5 = BULLET_CONFIG[BulletType.KNIFE]
    base = BULLET_CONFIG[BulletType.CANNON]["damage"]
    max_cd = max(cfg["cooldown"] for cfg in BULLET_CONFIG.values())
    max_spd = max(cfg["speed"] for cfg in BULLET_CONFIG.values())
    check(c5["damage"] == base * 2, f"飞刀伤害 {c5['damage']} == 2×炮弹 {base}")
    check(c5["cooldown"] == max_cd, f"飞刀冷却 {c5['cooldown']} = 全场最慢")
    check(c5["ricochet"] == 0, f"飞刀不回弹 (ricochet={c5['ricochet']})")
    check(c5["speed"] == max_spd, f"飞刀弹速 {c5['speed']} = 全场最快")
    t5 = Tank(300, 300)
    t5.bullet_type = BulletType.KNIFE
    t5.fire([], 1)
    check(t5.fire_cooldown == 1150, "飞刀实际开火冷却 1150ms")

    print("== 6. 麦克风: 命中眩晕 0.4s ==")
    c6 = BULLET_CONFIG[BulletType.MIC]
    check(c6.get("stun") == 0.4, "麦克风配置 stun=0.4")
    check(c6.get("sine") is not None, "正弦摆动视觉保留")
    t6 = Tank(300, 300)
    t6.take_damage(1, stun=0.4)
    check(t6.stun_timer == 400, "眩晕计时 400ms")
    t6.update_base(100)
    check(t6.stun_timer == 300, "眩晕倒计时递减")
    t6.take_damage(1, stun=0.4)
    check(t6.stun_timer == 400, "连续命中只刷新不叠加 (仍400)")
    check(t6.fire([], 1) == [] and t6.fire_cooldown == 0, "眩晕中不能开火")

    et = EnemyTank(300, 300, EnemyType.SCOUT, level=1)
    et.stun_timer = 400
    et.wander_dir = (1, 0)
    et.wander_timer = 1000
    x0, y0 = et.x, et.y
    et.update(16.666, [], [], [FakePlayer()], MAP, [], None, None)
    check(et.x == x0 and et.y == y0, "敌人眩晕时原地不动 (不触发脱困位移)")
    et2 = EnemyTank(300, 300, EnemyType.SCOUT, level=1)
    et2.wander_dir = (1, 0)
    et2.wander_timer = 1000
    et2.update(16.666, [], [], [FakePlayer()], MAP, [], None, None)
    check(et2.x > 300, "对照组: 未眩晕敌人正常移动")

    pm = PlayerTank(200, 200, FakeData())
    pm.invuln_timer = 0
    bm = Bullet(200, 200, 0, BulletType.MIC, -1)
    bm.try_hit_tank(pm)
    check(pm.stun_timer == 400, "玩家被敌方麦克风命中同样眩晕400ms")

    print("== 7. Boss: 只吃 25% 眩晕 ==")
    boss = Boss(BossId.BOSS_1, 1)
    boss.take_damage(1, stun=0.1)  # 0.4 × 0.25
    check(boss.stun_timer == 100, "Boss 眩晕时长 0.1s")
    bx, by = boss.x, boss.y
    boss.update(16.666, MAP, [], [FakePlayer()], [], None, None, None)
    check(boss.x == bx and boss.y == by and boss.stun_timer < 100,
          "Boss 眩晕时不走位且计时递减")

    print("== 8. 美团外卖: 范围伤害 ==")
    c8 = BULLET_CONFIG[BulletType.PARCEL]
    check(c8["ricochet"] == 0 and c8.get("splash") == {"radius": 55, "falloff": 0.6},
          "外卖 ricochet=0 + splash 配置 (55px / 60%)")

    gs = GameState()
    screen = pygame.display.set_mode((320, 240))
    game = Game(screen, gs)

    # 精确伤害值用 100 血普通 Tank 验证 (侦察兵 hp=10 会被秒杀导致钳制)
    e1 = Tank(200, 200)  # 直击目标
    e2 = Tank(240, 200)  # 距爆炸点 40px -> 溅射
    e3 = Tank(400, 200)  # 200px -> 无伤
    pa = PlayerTank(240, 200, FakeData())  # 队友站在爆炸中心旁
    pa.invuln_timer = 0
    game.enemy_tanks = [e1, e2, e3]
    game.player_tanks = [pa]

    hp1, hp2, hp3, hpa = e1.hp, e2.hp, e3.hp, pa.hp
    bx8 = Bullet(200, 200, 0, BulletType.PARCEL, 1)
    check(bx8.try_hit_tank(e1) and bx8.dead, "外卖命中目标即消失")
    check(e1.hp == hp1 - 22 and not e1.dead, "直击伤害 100% = 22")

    fb = FakeBoss(240, 200)
    game.gs.boss = fb
    game._apply_splash(bx8, direct=e1)
    check(e2.hp == hp2 - 13, "半径内敌人溅射 60% = 13")
    check(e3.hp == hp3, "半径外敌人无伤")
    check(pa.hp == hpa, "队友/自身免疫溅射")
    check(fb.hp == 100 - 13, "范围内 Boss 吃溅射 13")

    e2.hp = hp2
    game._apply_splash(bx8, direct=fb)
    check(fb.hp == 100 - 13, "直击 Boss 时不重复溅射 Boss")
    check(e2.hp == hp2 - 13, "直击 Boss 时周围敌人仍被溅射")

    # 溅射击杀同样计入击杀数 (固定 hp=10: 直击22/溅射13 均可击杀;
    # 侦察兵当前配置 hp=14 会剩 1 血, 故夹具显式固定)
    ke = EnemyTank(200, 200, EnemyType.SCOUT, level=1)
    k2 = EnemyTank(240, 200, EnemyType.SCOUT, level=1)
    ke.hp = 10
    k2.hp = 10
    game.enemy_tanks = [ke, k2]
    game.gs.boss = None
    k0_kills = game.gs.wave.enemies_killed
    kb = Bullet(200, 200, 0, BulletType.PARCEL, 1)
    kb.try_hit_tank(ke)
    game._on_enemy_killed(ke, kb.owner_id)  # 模拟 game.py 直击杀结算
    game._apply_splash(kb, direct=ke)
    check(ke.dead and k2.dead, "溅射可击杀低血敌人")
    check(game.gs.wave.enemies_killed == k0_kills + 2, "溅射击杀计入击杀数")

    p0 = PlayerTank(200, 200, FakeData())
    p1 = PlayerTank(240, 200, FakeData())
    p0.invuln_timer = 0
    p1.invuln_timer = 0
    game.player_tanks = [p0, p1]
    game.gs.boss = None
    be = Bullet(200, 200, 0, BulletType.PARCEL, -1)
    hp0 = p0.hp
    check(be.try_hit_tank(p0) and p0.hp == hp0 - 22, "敌方外卖直击玩家 22")
    game._apply_splash(be, direct=p0)
    check(p1.hp == 87, "敌方外卖溅射另一玩家 13")

    w9 = Wall(5, 5, WallType.STEEL)
    b9 = Bullet(300, 352, 0, BulletType.PARCEL, 1)
    b9.update(16.666, [w9], None, MAP, [])
    check(b9.dead, "外卖撞钢墙直接消失 (game 层不触发溅射)")

    pygame.quit()
    if FAILS:
        print("\n== FAILED %d 项 ==" % len(FAILS))
        for f in FAILS:
            print("  -", f)
        raise SystemExit(1)
    print("\nALL PASS")


if __name__ == "__main__":
    run()
