# -*- coding: utf-8 -*-
"""道具系统规则测试 (Headless)
运行: py -3.14 _pickup_test.py
覆盖: 寿命10秒 / 场上上限5 / 生命回复 / 能量护盾 / 火力×1.5 刷新 /
      急速射击 / 涡轮引擎 / 无敌星 / 毒液不致死 / 锈蚀 / 卡壳 / 反向操控 /
      同键互顶 / 磁铁不吸惩罚 / 敌人拾取 (对称 + 无敌星分数无效) /
      Boss 不参与 / 换关清空
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import pygame

# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

pygame.init()
pygame.display.set_mode((320, 240))
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
except Exception:
    pass

from core.constants import *
from core.game_state import GameState, PlayerData, TankColor
from core.game import Game
from entities.pickup import (
    Pickup, PickupType, PICKUP_CONFIG, set_buff,
    BUFF_DAMAGE, BUFF_RAPID, BUFF_SPEED, BUFF_INVINCIBLE, BUFF_REVERSE,
    PICKUP_LIFETIME_MS, PICKUP_MAX_ON_FIELD,
)
from entities.tank import Tank, PlayerTank
from systems.ai_system import EnemyTank

MAP = pygame.Rect(0, 0, 600, 400)
FAILS = []


def check(cond, msg):
    print(("  [PASS] " if cond else "  [FAIL] ") + msg)
    if not cond:
        FAILS.append(msg)


def tick(buffs, ms, step=16.666):
    """模拟 Game._tick_buffs 倒计时"""
    n = int(ms / step) + 1
    for _ in range(n):
        Game._tick_buffs(buffs, step)


def fresh_player():
    pd = PlayerData(1, TankColor.RED)
    pt = PlayerTank(100, 100, pd)
    return pd, pt


def run():
    print("== 1. 掉落寿命 10 秒 ==")
    pu = Pickup(100, 100, PickupType.HP)
    check(pu.lifetime == PICKUP_LIFETIME_MS == 10000, "lifetime == 10000ms")
    for _ in range(int(12000 / 16.666) + 1):
        pu.update(16.666, [])
    check(pu.dead, "12000ms 后消失")
    check(all(PICKUP_CONFIG[k]["kind"] in ("reward", "penalty")
              for k in PICKUP_CONFIG), "全部道具都有 reward/penalty 分类")

    print("== 2. 场上上限 5 个 ==")
    g = Game(pygame.display.set_mode((320, 240)), GameState())
    for _ in range(8):
        g._drop_random_pickup(100, 100)
    check(len(g.pickups) == PICKUP_MAX_ON_FIELD == 5,
          f"连续掉 8 个后场上只有 {len(g.pickups)} 个 (踢最老)")

    print("== 3. 生命回复 ==")
    pd, _ = fresh_player()
    pd.hp = 50
    Pickup(0, 0, PickupType.HP).apply(pd)
    check(pd.hp == 80, "50 血吃 HP -> 80")
    Pickup(0, 0, PickupType.HP).apply(pd)
    check(pd.hp == 100, "满血封顶不溢出")

    print("== 4. 能量护盾 ==")
    pd, _ = fresh_player()
    Pickup(0, 0, PickupType.SHIELD).apply(pd)
    check(pd.shield == 40, "0 盾吃 -> 40")
    pd.shield = 60
    Pickup(0, 0, PickupType.SHIELD).apply(pd)
    check(pd.shield == 80, "60 盾吃 -> 80 封顶")
    pd.shield = 100  # 已有升级盾
    Pickup(0, 0, PickupType.SHIELD).apply(pd)
    check(pd.shield == 140, "升级盾 100 时吃 -> 140 不倒退 (上限 250)")

    print("== 5. 火力强化 ×1.5 (限时10s / 刷新) ==")
    pd, pt = fresh_player()
    Pickup(0, 0, PickupType.DAMAGE).apply(pd)
    b = pd.timed_buffs.get(BUFF_DAMAGE)
    check(b and b["mult"] == 1.5 and b["ms"] == 10000, "写入 damage×1.5 / 10000ms")
    check(abs(pt._combat_damage_mult() - 1.5) < 0.001,
          f"战斗倍率 = base(1.0)×1.5 (实际 {pt._combat_damage_mult():.3f})")
    tick(pd.timed_buffs, 10100)
    check(BUFF_DAMAGE not in pd.timed_buffs, "10.1 秒后自动还原")
    Pickup(0, 0, PickupType.DAMAGE).apply(pd)
    tick(pd.timed_buffs, 1000)
    Pickup(0, 0, PickupType.DAMAGE).apply(pd)
    check(pd.timed_buffs[BUFF_DAMAGE]["ms"] == 10000, "第 9 秒再吃刷新回 10 秒")
    check(len(pd.timed_buffs) == 1, "同种道具只有 1 条效果 (刷新, 绝不叠加时间)")
    Pickup(0, 0, PickupType.DAMAGE).apply(pd)
    Pickup(0, 0, PickupType.DAMAGE).apply(pd)
    check(pd.timed_buffs[BUFF_DAMAGE]["ms"] == 10000
          and len(pd.timed_buffs) == 1, "连吃 2 个同种道具: 时长仍 10 秒, 条目仍 1 条")

    print("== 6. 急速射击 (冷却 ×0.6) ==")
    pd, pt = fresh_player()
    Pickup(0, 0, PickupType.RAPID).apply(pd)
    cfg = BULLET_CONFIG[pt.bullet_type]
    pt.fire([], 1)
    check(pt.fire_cooldown == int(cfg["cooldown"] * 0.6),
          f"冷却 {cfg['cooldown']} -> {pt.fire_cooldown} (×0.6)")
    tick(pd.timed_buffs, 10100)
    pt.fire_cooldown = 0
    pt.fire([], 1)
    check(pt.fire_cooldown == cfg["cooldown"], "到期后冷却还原")

    print("== 7. 涡轮引擎 (移速 ×1.3, 上限 7.0) ==")
    pd, pt = fresh_player()
    Pickup(0, 0, PickupType.SPEED).apply(pd)
    x0 = pt.x
    pt.try_move(1, 0, [], [], MAP)
    check(abs(pt.x - (x0 + 3.0 * 1.3)) < 0.01, f"移速 3.0 -> {pt.x - x0:.2f} (×1.3)")
    pd.speed = 6.0
    pt.speed = 6.0
    pt.x = 100
    pt.try_move(1, 0, [], [], MAP)
    check(abs(pt.x - 107.0) < 0.01, "6.0×1.3=7.8 -> 封顶 7.0")
    tick(pd.timed_buffs, 10100)
    pd.speed = 3.0
    pt.speed = 3.0
    pt.x = 100
    pt.try_move(1, 0, [], [], MAP)
    check(abs(pt.x - (100 + 3.0)) < 0.01, "到期后移速还原")

    print("== 8. 无敌星 5 秒 ==")
    pd, pt = fresh_player()
    pt.invuln_timer = 0  # 关掉出生无敌帧, 只测道具无敌
    Pickup(0, 0, PickupType.INVINCIBLE).apply(pd)
    check(pd.timed_buffs[BUFF_INVINCIBLE]["ms"] == 5000, "无敌时长 5000ms")
    pt.take_damage(999)
    check(pt.hp == 100 and pt.shield == 0, "无敌期间不受伤害不破盾")
    tick(pd.timed_buffs, 5100)
    pt.take_damage(10)
    check(pt.hp == 90, "5.1 秒后正常受伤")

    print("== 9. 毒液泄漏 (不致死) ==")
    pd, _ = fresh_player()
    pd.hp = 30
    Pickup(0, 0, PickupType.POISON).apply(pd)
    check(pd.hp == 10, "30 血 -> 10")
    pd.hp = 5
    Pickup(0, 0, PickupType.POISON).apply(pd)
    check(pd.hp == 1, "5 血 -> 1 (最低 1 不致死)")

    print("== 10. 锈蚀 / 卡壳 / 反向 ==")
    pd, pt = fresh_player()
    Pickup(0, 0, PickupType.RUST).apply(pd)
    check(pd.timed_buffs[BUFF_DAMAGE]["mult"] == 0.6, "锈蚀 -> 伤害 ×0.6")
    check(abs(pt._combat_damage_mult() - 0.6) < 0.001, "战斗倍率实际 ×0.6")
    Pickup(0, 0, PickupType.JAM).apply(pd)
    check(pd.timed_buffs[BUFF_RAPID]["mult"] == 1.5, "卡壳 -> 冷却 ×1.5")
    pt.x, pt.y = 100, 100
    Pickup(0, 0, PickupType.REVERSE).apply(pd)
    check(pd.timed_buffs[BUFF_REVERSE]["ms"] == 5000, "反向时长 5000ms")
    pt.try_move(1, 0, [], [], MAP)
    check(pt.x < 100, f"反向操控: 按右实际向左 (x={pt.x:.1f})")
    tick(pd.timed_buffs, 5100)
    pt.x = 100
    pt.try_move(1, 0, [], [], MAP)
    check(pt.x > 100, "反向到期后恢复正常移动")

    print("== 11. 同键互顶 (不叠乘) ==")
    pd, _ = fresh_player()
    Pickup(0, 0, PickupType.DAMAGE).apply(pd)
    Pickup(0, 0, PickupType.RUST).apply(pd)
    check(pd.timed_buffs[BUFF_DAMAGE]["mult"] == 0.6, "火力后踩锈蚀 -> 只剩 ×0.6")
    Pickup(0, 0, PickupType.RAPID).apply(pd)
    Pickup(0, 0, PickupType.JAM).apply(pd)
    check(pd.timed_buffs[BUFF_RAPID]["mult"] == 1.5, "急速后踩卡壳 -> 只剩 ×1.5")

    print("== 12. 磁铁不吸惩罚道具 ==")
    class Mag:
        def __init__(self):
            self.x, self.y = 300, 200
            self.pickup_magnet = True
            self.magnet_range = 200
            self.magnet_global = 0.0

    reward = Pickup(200, 200, PickupType.HP)
    reward.update(16.666, [Mag()])
    check(abs(reward.x - 204) < 0.01, f"奖励道具被磁铁吸附 (x={reward.x:.1f})")
    penalty = Pickup(200, 200, PickupType.POISON)
    penalty.update(16.666, [Mag()])
    check(penalty.x == 200 and penalty.y == 200, "惩罚道具不被磁铁吸附")

    print("== 13. 敌人拾取 (对称 / 无敌星分数无效) ==")
    e = EnemyTank(100, 100, EnemyType.SCOUT, 1)
    e.max_hp = 60
    e.hp = 15
    Pickup(0, 0, PickupType.HP).apply(e, is_enemy=True)
    check(e.hp == 45, "敌人吃 HP: 15 -> 45 (不超 max_hp)")
    Pickup(0, 0, PickupType.DAMAGE).apply(e, is_enemy=True)
    check(e.timed_buffs[BUFF_DAMAGE]["mult"] == 1.5, "敌人吃火力 -> 伤害 ×1.5")
    Pickup(0, 0, PickupType.RAPID).apply(e, is_enemy=True)
    e.fire_cooldown = 0
    e.fire([], -1, damage_mult=e.dmg_mult * e.get_buff("damage"))
    check(e.fire_cooldown == int(BULLET_CONFIG[e.bullet_type]["cooldown"] * 0.6),
          "敌人吃急速 -> 冷却 ×0.6")
    e2 = EnemyTank(100, 100, EnemyType.SCOUT, 1)
    Pickup(0, 0, PickupType.INVINCIBLE).apply(e2, is_enemy=True)
    check(BUFF_INVINCIBLE not in e2.timed_buffs, "敌人吃无敌星 -> 无效果")
    Pickup(0, 0, PickupType.SCORE).apply(e2, is_enemy=True)
    check(not hasattr(e2, "score"), "敌人吃分数 -> 无效果且道具消失")
    e3 = EnemyTank(100, 100, EnemyType.SCOUT, 1)
    e3.hp = 15
    Pickup(0, 0, PickupType.POISON).apply(e3, is_enemy=True)
    check(e3.hp == 1, "敌人踩毒液: 15 -> 1 (最低 1)")
    tick(e.timed_buffs, 10100)
    check(not e.timed_buffs, "敌人限时效果到期清空")

    print("== 14. Boss 不参与拾取 ==")
    class FakeBoss:
        def __init__(self, x, y):
            self.x, self.y = x, y
            self.dead = False

    g2 = Game(pygame.display.set_mode((320, 240)), GameState())
    g2.player_tanks = []
    g2.enemy_tanks = []
    g2.pickups = [Pickup(100, 100, PickupType.HP)]
    g2.gs.boss = FakeBoss(100, 100)
    g2._update_pickups(16.666)
    check(len(g2.pickups) == 1 and not g2.pickups[0].dead,
          "Boss 压住道具 -> 不拾取不消失")
    g2.enemy_tanks = [EnemyTank(100, 100, EnemyType.SCOUT, 1)]
    g2._update_pickups(16.666)
    check(not g2.pickups, "敌人接触 -> 道具被抢走")

    print("== 15. 换关清空限时效果 ==")
    gs = GameState()
    pd2 = PlayerData(1, TankColor.RED)
    gs.players = [pd2]
    Pickup(0, 0, PickupType.DAMAGE).apply(pd2)
    check(BUFF_DAMAGE in pd2.timed_buffs, "吃火力后 buff 存在")
    g3 = Game(pygame.display.set_mode((320, 240)), gs)
    g3.start_level(1)
    check(not pd2.timed_buffs, "start_level 后限时效果全部清空")

    print()
    if FAILS:
        print(f"共 {len(FAILS)} 项失败")
        for m in FAILS:
            print("  -", m)
        sys.exit(1)
    print("ALL PASSED")


if __name__ == "__main__":
    run()
