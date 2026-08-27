# -*- coding: utf-8 -*-
"""
技能矢量图标库: 按技能语义绘制 28 个互不重复的极简线条图标 (单色, 透明底)
- 设计空间 64×64, 2 倍超采样绘制后平滑缩小 (抗锯齿)
- render_skill_icon(sid, size, color) 带缓存; 未知 id 返回 None (调用方回退字符)
- 全灰阶/单色, 与极简塔防风格一致
"""
import math
import pygame

# ---------------------------------------------------------------- 绘制小工具
class Ctx:
    def __init__(self, size, color):
        self.ss = 2  # 超采样
        self.s = size * self.ss / 64.0
        self.surf = pygame.Surface((size * self.ss, size * self.ss),
                                   pygame.SRCALPHA)
        self.c = color

    def _p(self, x, y):
        return (x * self.s, y * self.s)

    def line(self, a, b, w):
        pygame.draw.line(self.surf, self.c, self._p(*a), self._p(*b),
                         max(1, int(w * self.s)))

    def lines(self, pts, w, closed=False):
        p = [self._p(*pt) for pt in pts]
        if closed:
            pygame.draw.polygon(self.surf, self.c, p, 0)
        else:
            pygame.draw.lines(self.surf, self.c, False, p,
                              max(1, int(w * self.s)))

    def poly(self, pts):
        pygame.draw.polygon(self.surf, self.c,
                            [self._p(*pt) for pt in pts])

    def poly_out(self, pts, w):
        pygame.draw.polygon(self.surf, self.c,
                            [self._p(*pt) for pt in pts],
                            max(1, int(w * self.s)))

    def circle(self, cx, cy, r):
        pygame.draw.circle(self.surf, self.c, self._p(cx, cy), r * self.s)

    def circle_out(self, cx, cy, r, w):
        pygame.draw.circle(self.surf, self.c, self._p(cx, cy), r * self.s,
                           max(1, int(w * self.s)))

    def rect(self, x, y, w, h):
        pygame.draw.rect(self.surf, self.c,
                         (x * self.s, y * self.s, w * self.s, h * self.s))

    def rect_out(self, x, y, w, h, bw):
        pygame.draw.rect(self.surf, self.c,
                         (x * self.s, y * self.s, w * self.s, h * self.s),
                         max(1, int(bw * self.s)), border_radius=2 * self.s)

    def arc(self, cx, cy, r, w, a0, a1):
        pygame.draw.arc(self.surf, self.c,
                        ((cx - r) * self.s, (cy - r) * self.s,
                         2 * r * self.s, 2 * r * self.s),
                        a0, a1, max(1, int(w * self.s)))


# ---------------------------------------------------------------- 各技能绘制
def d_damage_flat(g):
    """炮弹强化: 上升箭头 + 炮弹"""
    g.lines([(14, 46), (32, 28), (50, 46)], 4.5)
    g.lines([(23, 34), (32, 24), (41, 34)], 4.5)
    g.circle(32, 15, 7)


def d_rapid_fire(g):
    """急速射击: 三连速度箭头"""
    for x0 in (10, 26, 42):
        g.lines([(x0, 22), (x0 + 11, 32), (x0, 42)], 4)


def d_speed_boost(g):
    """极速引擎: 上箭头 + 两侧速度线"""
    g.lines([(14, 46), (32, 20), (50, 46)], 5)
    g.line((10, 22), (10, 40), 3.5)
    g.line((54, 22), (54, 40), 3.5)


def d_armor(g):
    """装甲镀层: 盾牌"""
    g.poly([(32, 8), (51, 17), (51, 38), (32, 56), (13, 38), (13, 17)])
    g.poly_out([(32, 8), (51, 17), (51, 38), (32, 56), (13, 38), (13, 17)], 1.5)


def d_pierce(g):
    """穿透强化: 直线穿圆"""
    g.line((10, 32), (54, 32), 4.5)
    g.circle_out(32, 32, 11, 3.5)


def d_double_shot(g):
    """双发射击: 两个弹头并排"""
    g.line((8, 32), (20, 32), 4)
    g.circle(29, 32, 7)
    g.circle(46, 32, 7)


def d_magnet(g):
    """蛋形磁铁: U 形磁铁"""
    g.lines([(20, 16), (44, 16), (44, 44), (37, 44), (37, 25),
             (27, 25), (27, 44), (20, 44), (20, 16)], 5.5)


def d_full_heal(g):
    """紧急维修: 十字"""
    g.rect(27, 14, 10, 36)
    g.rect(14, 27, 36, 10)


def d_shield_pickup(g):
    """临时护盾: 盾 + 十字"""
    g.poly_out([(32, 9), (49, 17), (49, 37), (32, 53), (15, 37), (15, 17)], 2.5)
    g.rect(29, 23, 6, 17)
    g.rect(23.5, 29, 17, 6)


def d_triple_shot(g):
    """三发散射: 扇形三弹"""
    g.circle(23, 18, 6.5)
    g.circle(41, 18, 6.5)
    g.circle(32, 43, 6.5)


def d_ricochet(g):
    """弹射强化: 折线反弹箭头"""
    g.lines([(10, 52), (30, 26), (52, 44)], 4)
    g.lines([(44, 36), (52, 44), (46, 52)], 4)


def d_heavy_barrel(g):
    """重型炮管: 粗炮管 + 炮口"""
    g.rect(10, 28, 34, 9)
    g.circle_out(50, 32, 8, 4)


def d_frost_rounds(g):
    """冰霜弹头: 雪花"""
    for ang in (0, 60, 120):
        r = math.radians(ang)
        g.line((32 - 14 * math.cos(r), 32 - 14 * math.sin(r)),
               (32 + 14 * math.cos(r), 32 + 14 * math.sin(r)), 3)
    for ang in (0, 60, 120):
        r = math.radians(ang + 15)
        g.line((32 - 12 * math.cos(r), 32 - 12 * math.sin(r)),
               (32 - 8 * math.cos(r), 32 - 8 * math.sin(r)), 3)
        g.line((32 + 12 * math.cos(r), 32 + 12 * math.sin(r)),
               (32 + 8 * math.cos(r), 32 + 8 * math.sin(r)), 3)


def d_velocity_rounds(g):
    """加速弹头: 弹头 + 速度线"""
    g.circle(18, 32, 8)
    g.line((30, 32), (52, 32), 3.5)
    g.lines([(44, 26), (52, 32), (44, 38)], 3.5)
    g.line((26, 24), (26, 40), 3)


def d_shield_chance(g):
    """能量护盾: 双环护盾"""
    g.circle_out(32, 32, 17, 3)
    g.circle_out(32, 32, 11, 2)
    g.circle(32, 32, 4)


def d_vampire(g):
    """吸血子弹: 血滴"""
    g.circle(32, 32, 13)
    g.poly([(32, 6), (42, 22), (32, 30), (22, 22)])


def d_death_blast(g):
    """死亡爆破: 爆炸星"""
    for i in range(8):
        r = math.radians(i * 45)
        g.line((32 + 8 * math.cos(r), 32 + 8 * math.sin(r)),
               (32 + 21 * math.cos(r), 32 + 21 * math.sin(r)), 4)
    g.circle(32, 32, 5)


def d_static_field(g):
    """静电场: 闪电"""
    g.poly([(42, 6), (24, 34), (34, 34), (21, 58), (42, 26), (31, 26)])


def d_last_stand(g):
    """不屈意志: 心跳线"""
    g.lines([(6, 40), (18, 40), (25, 20), (32, 50), (39, 34),
             (46, 40), (58, 40)], 4)


def d_dead_eye(g):
    """狙击之眼: 准星"""
    g.circle_out(32, 32, 16, 3.5)
    g.line((32, 8), (32, 19), 3.5)
    g.line((32, 45), (32, 56), 3.5)
    g.line((8, 32), (19, 32), 3.5)
    g.line((45, 32), (56, 32), 3.5)
    g.circle(32, 32, 4)


def d_railgun(g):
    """轨道炮: 贯穿光束 + 双环"""
    g.line((8, 32), (56, 32), 3.5)
    g.circle_out(28, 32, 10, 2.5)
    g.circle_out(40, 32, 6, 2.5)
    g.circle(16, 32, 2.5)


def d_chrono_field(g):
    """时间静止: 时钟"""
    g.circle_out(32, 32, 17, 3.5)
    g.line((32, 32), (32, 20), 3.5)
    g.line((32, 32), (41, 37), 3.5)
    g.circle(32, 32, 3)


def d_phantom_duo(g):
    """幻影军团: 两个幽灵"""
    for cx in (23, 41):
        g.circle(cx, 20, 8)
        g.rect(cx - 8, 20, 16, 18)
        g.lines([(cx - 8, 38), (cx - 4, 33), (cx, 38), (cx + 4, 33),
                 (cx + 8, 38)], 3)


def d_doomsday(g):
    """末日核弹: 辐射扇"""
    g.circle(32, 32, 5)
    for a0 in (math.pi * 0.85, math.pi * 2.95, math.pi * 5.05):
        g.arc(32, 32, 15, 3.5, a0, a0 + 1.05)


def d_phoenix(g):
    """不死凤凰: 火焰"""
    g.poly([(32, 5), (43, 24), (51, 38), (40, 53), (32, 47),
            (24, 53), (13, 38), (21, 24)])
    g.poly([(32, 24), (37, 34), (40, 42), (34, 48), (32, 45),
            (30, 48), (24, 42), (27, 34)])


def d_berserk(g):
    """狂战士: 交叉双剑"""
    g.line((16, 16), (48, 48), 5)
    g.line((48, 16), (16, 48), 5)
    g.line((10, 12), (18, 8), 3)
    g.line((54, 52), (46, 56), 3)
    g.line((54, 12), (46, 8), 3)
    g.line((10, 52), (18, 56), 3)


def d_residue_dmg(g):
    """残能·伤害: 细十字"""
    g.rect(29, 16, 6, 32)
    g.rect(16, 29, 32, 6)


def d_residue_hp(g):
    """残能·生命: 心形"""
    g.circle(26, 24, 7)
    g.circle(38, 24, 7)
    g.poly([(19, 29), (45, 29), (32, 51)])


_DRAWERS = {
    "damage_flat": d_damage_flat,
    "rapid_fire": d_rapid_fire,
    "speed_boost": d_speed_boost,
    "armor": d_armor,
    "pierce": d_pierce,
    "double_shot": d_double_shot,
    "magnet": d_magnet,
    "full_heal": d_full_heal,
    "shield_pickup": d_shield_pickup,
    "triple_shot": d_triple_shot,
    "ricochet": d_ricochet,
    "heavy_barrel": d_heavy_barrel,
    "frost_rounds": d_frost_rounds,
    "velocity_rounds": d_velocity_rounds,
    "shield_chance": d_shield_chance,
    "vampire": d_vampire,
    "death_blast": d_death_blast,
    "static_field": d_static_field,
    "last_stand": d_last_stand,
    "dead_eye": d_dead_eye,
    "railgun": d_railgun,
    "chrono_field": d_chrono_field,
    "phantom_duo": d_phantom_duo,
    "doomsday": d_doomsday,
    "phoenix": d_phoenix,
    "berserk": d_berserk,
    "residue_dmg": d_residue_dmg,
    "residue_hp": d_residue_hp,
}

_cache = {}


def render_skill_icon(sid, size, color=(235, 235, 240)):
    """返回 size×size 透明底图标; 未知技能返回 None"""
    fn = _DRAWERS.get(sid)
    if fn is None:
        return None
    key = (sid, size, tuple(color))
    if key in _cache:
        return _cache[key]
    g = Ctx(size, color)
    fn(g)
    try:
        surf = pygame.transform.smoothscale(g.surf, (size, size))
    except Exception:
        surf = pygame.transform.scale(g.surf, (size, size))
    _cache[key] = surf
    return surf
