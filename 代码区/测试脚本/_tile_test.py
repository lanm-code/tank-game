# -*- coding: utf-8 -*-
"""方块与地块创新规则测试 (Headless)
运行: py -3.14 _tile_test.py
覆盖: 血量锚点 / 水渍滑行 / 泥沼冰面 / 尖刺 / 传送门 / 油桶爆炸 /
      木箱掉道具 / 外卖溅射破砖 / 草地潜行 / 地图生成
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
from core.game import Game
from entities.bullet import Bullet
from entities.tank import Tank, PlayerTank
from entities.wall import Wall
from systems.ai_system import EnemyTank
from systems.map_system import MapGenerator

MAP = pygame.Rect(0, 0, 1920, 1024)

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
        self.base_damage = 20
        self.bullet_type = BulletType.CANNON
        self.fire_rate_mult = 1.0
        self.pierce_add = 0
        self.ricochet_add = 0
        self.multi_shot = 1
        self.super_charge = 0
        self.x = 0
        self.y = 0
        self.angle = -90


class FakeInput:
    def __init__(self, mv=(0, 0), shoot=False, super_=False):
        self.mv = mv
        self.shoot = shoot
        self.super = super_

    def get_player_move(self, pid):
        return self.mv

    def is_shooting(self, pid):
        return self.shoot

    def is_super(self, pid):
        return self.super


class FakePlayer:
    """敌人 AI 所需的极简玩家"""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.dead = False
        self.last_fire_ms = -10 ** 9  # 默认"很久没开火" (避免 get_ticks 起始值 < 1500 干扰)

    def get_rect(self):
        return pygame.Rect(self.x - 28, self.y - 28, 56, 56)


class FakeBoss:
    def __init__(self, x, y, w=120, h=120):
        self.x, self.y = x, y
        self.w, self.h = w, h
        self.dead = False
        self.hp = 100

    def get_rect(self):
        return pygame.Rect(self.x - self.w / 2, self.y - self.h / 2, self.w, self.h)

    def take_damage(self, dmg, stun=0.0, **kwargs):
        self.hp -= dmg


class FakeGS:
    def __init__(self):
        self.players = []
        self.boss = None
        self.wave = None

    def trigger_shake(self, *a):
        pass

    def add_combo(self):
        return False


def make_player(x, y):
    d = FakeData()
    d.x, d.y = x, y
    return PlayerTank(x, y, d)


def stain_row(c0, c1, r=6):
    return [Wall(c, r, WallType.WATER_STAIN) for c in range(c0, c1 + 1)]


def run():
    # ================= 1. 血量锚点与子弹交互 =================
    print("== 1 血量锚点 ==")
    check(WALL_CONFIG[WallType.BRICK]["hp"] == 56 == BULLET_CONFIG[BulletType.KNIFE]["damage"],
          "砖块 hp == 56 == 飞刀伤害")
    check(WALL_CONFIG[WallType.SAND]["hp"] == 22 == BULLET_CONFIG[BulletType.BASKETBALL]["damage"],
          "沙粒 hp == 22 == 篮球伤害 (1 发篮球打穿)")
    check(WALL_CONFIG[WallType.STEEL]["hp"] == -1, "钢墙 hp == -1 打不动")

    print("== 2 特殊子弹与墙的交互 ==")
    w = Wall(5, 5, WallType.BRICK)
    b = Bullet(306, 352, 0, BulletType.PARCEL, 1)
    b.update(16.666, [w], None, MAP, [])
    check(not w.destroyed and w.hp == 34 and b.dead and b.splash is not None,
          "外卖撞砖: 扣22不爆不毁, 子弹消失")
    w = Wall(5, 5, WallType.BRICK)
    b = Bullet(306, 352, 0, BulletType.MIC, 1)
    b.update(16.666, [w], None, MAP, [])
    check(not w.destroyed and w.hp == 38, "麦克风撞砖: 扣18, 墙体不吃眩晕")
    w = Wall(5, 5, WallType.SAND)
    for _ in range(4):
        b = Bullet(306, 352, 0, BulletType.MILKY_EGG, 1)
        b.update(16.666, [w], None, MAP, [])
    check(w.destroyed, "奶蛋(15)磨沙粒: 2 发 (30>=22) 打穿")
    w = Wall(5, 5, WallType.SAND)
    b = Bullet(306, 352, 0, BulletType.BASKETBALL, 1)
    b.update(16.666, [w], None, MAP, [])
    check(w.destroyed and b.dead, "篮球(22)打沙粒: 1 发打穿")

    # ================= 3. 水渍滑行 =================
    print("== 3 水渍滑行 ==")
    # 3.1 移动中踩入: 锁方向, 之后输入改向无效; 滑出集群后恢复操控
    pt = make_player(600, 416)
    inp = FakeInput((1, 0))
    walls = stain_row(10, 11)
    for _ in range(30):
        pt.update(16.666, inp, walls, [pt], MAP, [], [], None, mouse_pos=(100, 100))
    check(pt.on_stain and pt.slide_dir == (1.0, 0.0), "移动中踩入水渍: 锁定进入方向")
    x1, y1 = pt.x, pt.y
    inp.mv = (0, -1)
    for _ in range(15):
        pt.update(16.666, inp, walls, [pt], MAP, [], [], None, mouse_pos=(100, 100))
    check(pt.x > x1 and pt.y == y1, "滑行中改输入无效: 仍沿原方向滑 (x增y不变)")
    for _ in range(60):
        pt.update(16.666, inp, walls, [pt], MAP, [], [], None, mouse_pos=(100, 100))
        if not pt.on_stain:
            break
    y2 = pt.y
    for _ in range(10):
        pt.update(16.666, inp, walls, [pt], MAP, [], [], None, mouse_pos=(100, 100))
    check(pt.y < y2 - 10, "滑出水渍集群后恢复操控 (向上移动)")
    # 3.2 静止踩入: 可原地操控, 一动即滑
    pt2 = make_player(672, 416)
    inp2 = FakeInput((0, 0))
    for _ in range(5):
        pt2.update(16.666, inp2, walls, [pt2], MAP, [], [], None, mouse_pos=(100, 100))
    check(pt2.on_stain and pt2.slide_dir is None and pt2.x == 672,
          "静止踩入: 不自动滑, 保持原位")
    inp2.mv = (0, -1)
    pt2.update(16.666, inp2, walls, [pt2], MAP, [], [], None, mouse_pos=(100, 100))
    check(pt2.slide_dir == (0.0, -1.0), "静止踩入后一动即锁方向滑行")
    # 3.3 撞墙停滑: 被挡住后无输入也不再被推
    pt3 = make_player(672, 416)
    inp3 = FakeInput((1, 0))
    walls3 = stain_row(10, 11) + [Wall(12, 6, WallType.STEEL)]
    px = pt3.x
    for _ in range(200):
        pt3.update(16.666, inp3, walls3, [pt3], MAP, [], [], None, mouse_pos=(100, 100))
        if abs(pt3.x - px) < 0.01 and pt3.x > 700:
            break
        px = pt3.x
    check(pt3.on_stain and abs(pt3.x - px) < 0.01, "滑行撞钢墙: 被挡住停住")
    inp3.mv = (0, 0)
    pt3.update(16.666, inp3, walls3, [pt3], MAP, [], [], None, mouse_pos=(100, 100))
    check(abs(pt3.x - px) < 0.01, "撞墙停滑后无输入不再被推 (滑行已解除)")
    # 3.4 眩晕优先: 眩晕中原地不动且滑行方向保留, 眩晕结束续滑
    pt4 = make_player(672, 416)
    inp4 = FakeInput((0, 1))
    pt4.on_stain = True
    pt4.slide_dir = (1.0, 0.0)
    pt4.stun_timer = 500
    x0, y0 = pt4.x, pt4.y
    for _ in range(10):
        pt4.update(16.666, inp4, walls, [pt4], MAP, [], [], None, mouse_pos=(100, 100))
    check(pt4.x == x0 and pt4.y == y0 and pt4.slide_dir == (1.0, 0.0),
          "眩晕优先: 原地不动且滑行方向保留")
    pt4.stun_timer = 0
    for _ in range(10):
        pt4.update(16.666, inp4, walls, [pt4], MAP, [], [], None, mouse_pos=(100, 100))
    check(pt4.x > x0 and pt4.y == y0, "眩晕结束仍在水渍上: 继续沿锁方向滑")
    # 3.5 滑行中可开火
    pt5 = make_player(672, 416)
    inp5 = FakeInput((1, 0), shoot=True)
    bullets = []
    pt5.slide_dir = (1.0, 0.0)
    pt5.update(16.666, inp5, walls, [pt5], MAP, bullets, [], None, mouse_pos=(100, 100))
    check(len(bullets) > 0, "滑行中仍可开火")
    # 3.6 敌人对称: 滑行中 AI 决策冻结 (目标转左仍向右滑)
    e = EnemyTank(672, 416, EnemyType.SCOUT, 1)
    p = FakePlayer(1100, 416)
    walls_e = stain_row(10, 13)
    for _ in range(30):
        e.update(16.666, walls_e, [e], [p], MAP, [], [], None)
    check(e.slide_dir == (1.0, 0.0), "敌人踩入水渍: 锁方向滑行")
    xe = e.x
    p.x = 500
    for _ in range(20):
        e.update(16.666, walls_e, [e], [p], MAP, [], [], None)
    check(e.x > xe, "敌人滑行中 AI 冻结: 目标转左仍向右滑")

    # ================= 4. 泥沼 / 冰面 / 尖刺 =================
    print("== 4 泥沼 / 冰面 / 尖刺 ==")
    t = Tank(672, 416)
    t.apply_tile(16.666, [Wall(10, 6, WallType.MUD)])
    check(abs(t.tile_speed_mult - 0.6) < 1e-6, "泥沼: 移速乘区 0.6")
    t.apply_tile(16.666, [Wall(10, 6, WallType.ICE)])
    check(abs(t.tile_speed_mult - 1.4) < 1e-6, "冰面: 移速乘区 1.4")
    t.apply_tile(16.666, [])
    check(abs(t.tile_speed_mult - 1.0) < 1e-6, "平地: 移速乘区 1.0")
    t2 = Tank(672, 416)
    spike = [Wall(10, 6, WallType.SPIKE)]
    for _ in range(31):
        t2.apply_tile(16.666, spike)
    check(t2.hp == 70, "尖刺: 站 ~0.5s 掉 30 血 (100->70)")
    for _ in range(31):
        t2.apply_tile(16.666, spike)
    check(t2.hp == 40, "尖刺: 站 ~1s 掉 60 血 (70->40)")
    t2.apply_tile(16.666, [])
    t2.apply_tile(16.666, spike)
    t2.apply_tile(16.666, spike)
    check(t2.hp == 40, "尖刺 tick 离开后重置: 重新站上去不立刻扣血")

    # ================= 5. 传送门 =================
    print("== 5 传送门 ==")
    g = object.__new__(Game)
    pa = Wall(3, 8, WallType.PORTAL)
    pb = Wall(10, 8, WallType.PORTAL)
    pa.portal_partner = pb
    pb.portal_partner = pa
    g.walls = [pa, pb]
    t3 = Tank(pa.x + 32, pa.y + 32)
    g.player_tanks = [t3]
    g.enemy_tanks = []
    g.particles = []
    g._update_portals(16.666)
    on_b = abs(t3.x - (pb.x + 32)) < 30 and abs(t3.y - (pb.y + 32)) < 30
    check(on_b and t3.portal_cd == 1500, "踏入 A 门: 传送到 B 门并进入 1.5s 冷却")
    g._update_portals(16.666)
    check(abs(t3.x - (pb.x + 32)) < 30, "冷却中不弹回")
    t3.portal_cd = 0
    g._update_portals(16.666)
    check(abs(t3.x - (pa.x + 32)) < 30, "冷却结束仍站在 B 门: 弹回 A 门")

    # ================= 6. 燃油桶爆炸 =================
    print("== 6 燃油桶爆炸 ==")
    g2 = object.__new__(Game)
    from types import SimpleNamespace
    g2.gs = FakeGS()
    g2.gs.wave = SimpleNamespace(enemies_killed=0)
    g2.audio = None
    g2.particles = []
    g2.pickups = []
    barrel = Wall(5, 5, WallType.BARREL)  # 中心 (352, 352)
    p_near = Tank(370, 352)
    p_far = Tank(600, 352)
    e_near = EnemyTank(360, 352, EnemyType.SCOUT, 1)
    e_near.hp = e_near.max_hp = 60
    g2.player_tanks = [p_near, p_far]
    g2.enemy_tanks = [e_near]
    # 3×3 清场夹具: (4,4)砖 / (6,4)沙 在范围内; (4,6)水渍 / (6,6)钢墙 保留; (2,2)玻璃 范围外
    g2.walls = [
        Wall(4, 4, WallType.BRICK),
        Wall(6, 4, WallType.SAND),
        Wall(4, 6, WallType.WATER_STAIN),
        Wall(6, 6, WallType.STEEL),
        Wall(2, 2, WallType.GLASS),
    ]
    g2._explode_barrel(barrel)
    check(p_near.hp == 60 and p_far.hp == 100,
          "油桶爆炸: 55px 内玩家 -40, 55px 外无伤")
    check(e_near.hp == 20, "油桶爆炸: 敌人同样 -40 (敌我同伤)")
    check(g2.walls[0].destroyed and g2.walls[1].destroyed,
          "油桶爆炸: 3×3 内砖块/沙粒被摧毁")
    check(not g2.walls[2].destroyed, "油桶爆炸: 3×3 内水渍地块不清除")
    check(not g2.walls[3].destroyed, "油桶爆炸: 3×3 内钢墙不摧毁")
    check(not g2.walls[4].destroyed, "油桶爆炸: 3×3 外玻璃不受影响")
    boss = FakeBoss(360, 352)
    g2.gs.boss = boss
    g2._explode_barrel(barrel)
    check(boss.hp == 60, "油桶爆炸: Boss 在范围内吃 40")
    check(e_near.dead and g2.gs.wave.enemies_killed == 1,
          "油桶二次爆炸击杀敌人: 计入击杀数")
    check(p_near.hp == 20, "油桶二次爆炸: 玩家再 -40 (60->20)")

    print("== 6b 油桶连锁 (同帧结算) ==")
    g2b = object.__new__(Game)
    g2b.gs = FakeGS()
    g2b.gs.wave = SimpleNamespace(enemies_killed=0)
    g2b.audio = None
    g2b.particles = []
    g2b.pickups = []
    g2b.player_tanks = []
    g2b.enemy_tanks = []
    ba = Wall(5, 5, WallType.BARREL)
    ba.destroyed = True                       # 被子弹打碎 → 触发爆炸
    bb = Wall(6, 5, WallType.BARREL)          # 3×3 内第二个油桶 → 连锁引爆
    cc = Wall(4, 5, WallType.CRATE)           # 3×3 内木箱 → 被清并掉道具
    be = Wall(7, 5, WallType.BRICK)           # 第二个油桶 3×3 内 → 被连锁摧毁
    bd = Wall(9, 5, WallType.BRICK)           # 两个油桶 3×3 都够不着 → 保留
    g2b.walls = [ba, bb, cc, be, bd]
    import random as _r
    _r_real = _r.random
    _r.random = lambda: 0.0  # 木箱必掉
    try:
        g2b._post_wall_events()
    finally:
        _r.random = _r_real
    check(bb.destroyed and bb.effect_done, "油桶连锁: 3×3 内第二个油桶被引爆")
    check(cc.destroyed and len(g2b.pickups) == 1,
          "油桶连锁: 3×3 内木箱被清并掉道具")
    check(be.destroyed, "油桶连锁: 第二油桶 3×3 内的砖块被摧毁")
    check(not bd.destroyed, "油桶连锁: 3×3 外砖块不受影响")

    # ================= 7. 木箱掉道具 =================
    print("== 7 木箱掉道具 ==")
    g3 = object.__new__(Game)
    g3.pickups = []
    crate = Wall(5, 5, WallType.CRATE)
    crate.destroyed = True
    g3.walls = [crate]
    import random as _r
    _r_real = _r.random
    _r.random = lambda: 0.0  # 必掉
    g3._post_wall_events()
    _r.random = _r_real
    check(len(g3.pickups) == 1, "木箱被打碎: 15% 掉道具 (mock 为必掉)")

    # ================= 8. 外卖溅射破砖 (B2) =================
    print("== 8 外卖溅射破砖 ==")
    g4 = object.__new__(Game)
    g4.gs = FakeGS()
    brick = Wall(5, 5, WallType.BRICK)     # 中心 (352,352)
    glass_out = Wall(5, 8, WallType.GLASS)  # 中心 (352,544), 最近点距离 160 > 55 → 不碎
    steel = Wall(5, 7, WallType.STEEL)
    glass2 = Wall(6, 5, WallType.GLASS)    # 中心 (416,352), 最近点距离 32 <= 55 → 碎
    g4.walls = [brick, glass_out, steel]
    g4.enemy_tanks = []
    g4.player_tanks = []
    b = Bullet(352, 352, 0, BulletType.PARCEL, 1)
    g4._apply_splash(b, direct=None)
    check(brick.hp == 56 - 13, "溅射半径内砖块吃 60% (13) 伤害")
    check(not glass_out.destroyed and not glass2.destroyed,
          "溅射半径外玻璃不碎")
    check(not steel.destroyed and steel.hp == -1, "溅射不伤钢墙")
    g4.walls = [glass2]
    g4._apply_splash(b, direct=None)
    check(glass2.destroyed, "溅射半径内玻璃 (hp=1) 被 13 点溅射打碎")

    # ================= 9. 草地潜行 =================
    print("== 9 草地潜行 ==")
    grass = [Wall(5, 5, WallType.GRASS)]
    p_hid = FakePlayer(352, 352)   # 完全在草丛内 (rect 324..380)
    p_out = FakePlayer(352, 400)   # 底角在草丛外
    e2 = EnemyTank(100, 352, EnemyType.SCOUT, 1)
    check(e2._player_hidden(p_hid, grass), "完全在草丛内且未开火: 不可索敌")
    p_hid.last_fire_ms = pygame.time.get_ticks()
    check(not e2._player_hidden(p_hid, grass), "开火后 1.5s 内: 暴露可索敌")
    check(not e2._player_hidden(p_out, grass), "半身在外: 不隐藏")
    p_hid.last_fire_ms = -10 ** 9
    e2.update(16.666, grass, [e2], [p_hid], MAP, [], [], None)
    check(e2.target_player is None, "全隐藏玩家不可被选为目标")
    p_hid.last_fire_ms = pygame.time.get_ticks()
    e2.update(16.666, grass, [e2], [p_hid], MAP, [], [], None)
    check(e2.target_player is p_hid, "暴露后恢复索敌")

    # ================= 10. 地图生成 =================
    print("== 10 地图生成 ==")
    gen = MapGenerator()
    walls2, _ = gen.generate_level(2)
    stains = [w for w in walls2 if w.type == WallType.WATER_STAIN]
    check(2 <= len(stains) <= 6, "第 2 关: 水渍 1 簇 (2-6 格)")
    spawn_ok = all(not (1 <= w.col <= 6 and MAP_ROWS - 5 <= w.row <= MAP_ROWS - 2)
                   for w in stains)
    check(spawn_ok, "水渍不在玩家出生区")
    check(gen._is_connected(walls2), "第 2 关 BFS 连通性通过")
    walls5, _ = gen.generate_level(5)
    stains5 = [w for w in walls5 if w.type == WallType.WATER_STAIN]
    check(4 <= len(stains5) <= 12, "第 5 关: 水渍 2 簇")
    check(len([w for w in walls5 if w.type == WallType.BARREL]) == 2, "第 5 关: 燃油桶 2 个")
    walls8, _ = gen.generate_level(8)
    check(6 <= len([w for w in walls8 if w.type == WallType.WATER_STAIN]) <= 18,
          "第 8 关: 水渍 3 簇")
    check(len([w for w in walls8 if w.type == WallType.SPIKE]) >= 4, "第 8 关: 尖刺 2 簇")
    walls1, _ = gen.generate_level(1)
    check(len([w for w in walls1 if w.type == WallType.SAND]) >= 4, "第 1 关: 沙粒散落")
    check(len([w for w in walls1 if w.type == WallType.CRATE]) == 0, "第 1 关: 无木箱")
    # 砖沙权重对齐: 砖块与沙粒总量同量级
    def _ratio(wl):
        b = len([w for w in wl if w.type == WallType.BRICK])
        s = len([w for w in wl if w.type == WallType.SAND])
        return b, s
    b2, s2 = _ratio(walls2)
    check(0.5 <= b2 / max(1, s2) <= 1.6, f"第 2 关: 砖/沙同量级 ({b2}/{s2})")
    b8, s8 = _ratio(walls8)
    check(0.9 <= b8 / max(1, s8) <= 1.5, f"第 8 关: 砖/沙同量级 ({b8}/{s8})")
    # 水面成片 (3~4 格连片, 有相邻格)
    water8 = [w for w in walls8 if w.type == WallType.WATER]
    wset = {(w.col, w.row) for w in water8}
    w_adj = any((c + 1, r) in wset or (c - 1, r) in wset or
                (c, r + 1) in wset or (c, r - 1) in wset
                for (c, r) in wset)
    check(6 <= len(water8) <= 8 and w_adj, f"第 8 关: 水面成片出现 ({len(water8)} 格)")
    # 冰面成片 (3~5 格连片)
    ice8 = [w for w in walls8 if w.type == WallType.ICE]
    iset = {(w.col, w.row) for w in ice8}
    i_adj = any((c + 1, r) in iset or (c - 1, r) in iset or
                (c, r + 1) in iset or (c, r - 1) in iset
                for (c, r) in iset)
    check(6 <= len(ice8) <= 10 and i_adj, f"第 8 关: 冰面成片出现 ({len(ice8)} 格)")
    check(gen._is_connected(walls8), "第 8 关: 水面成片后 BFS 连通性仍通过")
    arena, _ = gen.generate_boss_arena(10)
    portals = [w for w in arena if w.type == WallType.PORTAL]
    check(len(portals) == 2 and portals[0].portal_partner is portals[1]
          and portals[1].portal_partner is portals[0], "Boss 关: 1 对互相配对的传送门")
    # 空白区检测: 大片无内容区域自动补撒可破坏方块
    walls_sp = [Wall(0, 0, WallType.STEEL), Wall(1, 0, WallType.STEEL)]
    gen._fill_sparse_regions(walls_sp, 8, [])
    fill_types = {w.type for w in walls_sp[2:]}
    check(len(walls_sp) > 30, f"空白区自动补撒方块 (整图空白 → 补了 {len(walls_sp) - 2} 个)")
    check(fill_types <= {WallType.SAND, WallType.BRICK, WallType.CRATE} and len(fill_types) >= 2,
          "补撒的方块只含可破坏类型 (沙/砖/木箱)")
    # 有内容的块不再补
    dense = [Wall(c, r, WallType.SAND) for r in range(0, 4) for c in range(0, 5)]
    gen._fill_sparse_regions(dense, 8, [])
    chunk0 = [w for w in dense if w.col < 5 and w.row < 4]
    check(len(chunk0) == 20, "内容密集的块不再补撒 (块内格数不变)")

    # ================= 11. 击杀记账 / 幽灵出砖 / 输入重置 (bug 修复回归) =================
    print("== 11 击杀记账 / 幽灵出砖 / 输入重置 ==")
    from types import SimpleNamespace
    g5 = object.__new__(Game)
    g5.gs = FakeGS()
    g5.gs.wave = SimpleNamespace(enemies_killed=0)
    g5.audio = None
    g5.particles = []
    g5.pickups = []
    g5.enemy_tanks = []
    e3 = EnemyTank(200, 200, EnemyType.SCOUT, 1)
    check(getattr(e3, "kill_counted", False) is False, "敌人生成时 kill_counted=False")
    g5._on_enemy_killed(e3, None)
    g5._on_enemy_killed(e3, None)
    check(g5.gs.wave.enemies_killed == 1, "击杀防重复记账: 同一敌人只计 1 次")
    e4 = EnemyTank(200, 200, EnemyType.SCOUT, 1)
    e4.dead = True  # 模拟尖刺击杀 (未走子弹结算路径)
    g5.enemy_tanks = [e4]
    g5._sweep_uncounted_kills()
    check(g5.gs.wave.enemies_killed == 2 and e4.kill_counted,
          "尖刺等非子弹击杀被补记 (sweep)")
    g5._sweep_uncounted_kills()
    check(g5.gs.wave.enemies_killed == 2, "sweep 不重复补记")
    ghost = EnemyTank(352, 352, EnemyType.GHOST, 1)  # 中心在砖 (5,5) 内部
    brick_w = Wall(5, 5, WallType.BRICK)
    ghost._eject_from_bricks([brick_w], [ghost], MAP)
    inside = (brick_w.x <= ghost.x <= brick_w.x + brick_w.width and
              brick_w.y <= ghost.y <= brick_w.y + brick_w.height)
    check(not inside, "幽灵不再停在砖块内部 (被弹出)")
    from core.input import InputManager
    im = InputManager()
    im.keys_pressed.add(pygame.K_d)
    im.reset()
    check(im.get_player_move(1) == (0, 0), "输入重置: 清卡键, 不再持续移动")

    print("")
    if FAILS:
        print(f"FAILED {len(FAILS)} items:")
        for f in FAILS:
            print("  -", f)
        sys.exit(1)
    print(f"ALL PASS ({len(FAILS)} fails)")
    pygame.quit()


if __name__ == "__main__":
    run()
