# -*- coding: utf-8 -*-
"""
道具掉落实体
Pickup Entity
- 奖励道具: 蓝色描边外壳 (敌人可拾取, 抢道具博弈)
- 惩罚道具: 红色描边外壳 (敌我通用, 谁碰谁中招; 磁铁不吸附)
- 掉落寿命统一 10 秒, 最后 3 秒闪烁 (透明度脉动)
- 图标: 白色实心圆 + 单字符号, 2 倍超采样渲染保证清晰
"""
import math
import os
import random
import pygame
from core.constants import *

# 外壳描边颜色: 蓝 = 奖励, 红 = 惩罚
RING_REWARD = (70, 140, 255)
RING_PENALTY = NEON_RED

# 限时效果 key (敌我共用的乘区)
BUFF_DAMAGE = "damage"        # 伤害乘区: 火力 1.5 / 锈蚀 0.6 (同键互顶)
BUFF_RAPID = "rapid"          # 攻速乘区: 急速 0.6 / 卡壳 1.5 (同键互顶)
BUFF_SPEED = "speed"          # 移速乘区: 涡轮 1.3
BUFF_INVINCIBLE = "invincible"  # 无敌星 (仅玩家生效)
BUFF_REVERSE = "reverse"      # 反向操控 (敌我通用, try_move 内取反)

BUFF_LIFETIME_MS = 10000      # 限时效果统一 10 秒
PICKUP_LIFETIME_MS = 10000    # 道具掉落寿命 10 秒
PICKUP_MAX_ON_FIELD = 5       # 场上道具上限 (超出踢最老)

# 缺字形兜底 (微软雅黑缺 ⚔/☠/↺ 等符号字形, 显示为豆腐块)
_SYMBOL_FALLBACK = {
    "⚔": "攻", "☠": "毒", "↺": "卡", "⇄": "反", "◈": "盾",
    "✖": "锈", "»": "速", "→": "移", "★": "无",
}
_SYM_FONT_CACHE = {}   # char -> 字体文件路径 (None = 都没有)
_SYM_IMG_CACHE = {}    # (char, size, color) -> Surface


def _symbol_font_for(char):
    """找第一个包含该字符字形的字体文件 (缓存结果)"""
    if char in _SYM_FONT_CACHE:
        return _SYM_FONT_CACHE[char]
    try:
        import pygame.freetype
    except Exception:
        _SYM_FONT_CACHE[char] = None
        return None
    cands = ["seguisym.ttf", "seguiemj.ttf", "msyhbd.ttc", "msyh.ttc",
             "simhei.ttf", "arialbd.ttf", "arial.ttf"]
    windir = os.environ.get("WINDIR", r"C:\Windows")
    for fname in cands:
        path = os.path.join(windir, "Fonts", fname)
        if not os.path.exists(path):
            continue
        try:
            f = pygame.freetype.Font(path)
            m = f.get_metrics(char)
            if m and m[0] is not None:
                _SYM_FONT_CACHE[char] = path
                return path
        except Exception:
            continue
    _SYM_FONT_CACHE[char] = None
    return None


def _render_symbol(char, size, color):
    """渲染道具符号 (freetype 抗锯齿; 缺字形时回退中文单字)"""
    key = (char, size, tuple(color))
    if key in _SYM_IMG_CACHE:
        return _SYM_IMG_CACHE[key]
    surf = None
    path = _symbol_font_for(char)
    if path:
        try:
            import pygame.freetype
            f = pygame.freetype.Font(path, size=size)
            f.strong = True
            f.pad = False
            surf, _rect = f.render(char, fgcolor=color)
        except Exception:
            surf = None
    if surf is None:
        fallback = _SYMBOL_FALLBACK.get(char, char)
        try:
            from utils.fonts import load_font
            font = load_font(size, bold=True)
            surf = font.render(fallback, True, color)
        except Exception:
            surf = pygame.font.Font(None, size).render(fallback, True, color)
    _SYM_IMG_CACHE[key] = surf
    return surf


class PickupType:
    # 奖励
    HP = "hp"
    SHIELD = "shield"
    DAMAGE = "damage"
    RAPID = "rapid"
    SPEED = "speed"
    SCORE = "score"
    INVINCIBLE = "invincible"
    # 惩罚
    POISON = "poison"
    RUST = "rust"
    JAM = "jam"
    REVERSE = "reverse"


def set_buff(target, key, ms, mult):
    """写/刷新限时效果: 同键覆盖 (互顶), 不叠加。"""
    buffs = getattr(target, "timed_buffs", None)
    if buffs is None:
        buffs = {}
        try:
            target.timed_buffs = buffs
        except Exception:
            pass
    buffs[key] = {"ms": ms, "mult": mult}


PICKUP_CONFIG = {
    # ---------------- 奖励 (蓝描边) ----------------
    PickupType.HP: {"kind": "reward", "color": NEON_GREEN, "name": "生命回复",
                    "symbol": "血", "label": "+30", "weight": 20,
                    "instant": "hp"},
    PickupType.SHIELD: {"kind": "reward", "color": NEON_CYAN,
                        "name": "能量护盾", "symbol": "盾", "label": "+40盾",
                        "weight": 12, "instant": "shield"},
    PickupType.DAMAGE: {"kind": "reward", "color": NEON_RED, "name": "火力强化",
                        "symbol": "攻", "label": "攻↑", "weight": 14,
                        "buff": (BUFF_DAMAGE, BUFF_LIFETIME_MS, 1.5)},
    PickupType.RAPID: {"kind": "reward", "color": NEON_YELLOW,
                       "name": "急速射击", "symbol": "速", "label": "速↑",
                       "weight": 14,
                       "buff": (BUFF_RAPID, BUFF_LIFETIME_MS, 0.6)},
    PickupType.SPEED: {"kind": "reward", "color": NEON_ORANGE,
                       "name": "涡轮引擎", "symbol": "移", "label": "移↑",
                       "weight": 14,
                       "buff": (BUFF_SPEED, BUFF_LIFETIME_MS, 1.3)},
    PickupType.SCORE: {"kind": "reward", "color": NEON_PURPLE,
                       "name": "分数补给", "symbol": "分", "label": "+500",
                       "weight": 10, "instant": "score"},
    PickupType.INVINCIBLE: {"kind": "reward", "color": (255, 200, 60),
                            "name": "无敌星", "symbol": "★", "label": "无敌",
                            "weight": 4, "buff": (BUFF_INVINCIBLE, 5000, 1.0)},
    # ---------------- 惩罚 (红描边) ----------------
    PickupType.POISON: {"kind": "penalty", "color": NEON_RED,
                        "name": "毒液泄漏", "symbol": "毒", "label": "-20",
                        "weight": 8, "instant": "poison"},
    PickupType.RUST: {"kind": "penalty", "color": (170, 110, 90),
                      "name": "锈蚀弹头", "symbol": "锈", "label": "攻↓",
                      "weight": 6,
                      "buff": (BUFF_DAMAGE, BUFF_LIFETIME_MS, 0.6)},
    PickupType.JAM: {"kind": "penalty", "color": (150, 150, 155),
                     "name": "履带卡壳", "symbol": "卡", "label": "速↓",
                     "weight": 6,
                     "buff": (BUFF_RAPID, BUFF_LIFETIME_MS, 1.5)},
    PickupType.REVERSE: {"kind": "penalty", "color": NEON_PURPLE,
                         "name": "反向操控", "symbol": "反", "label": "反向",
                         "weight": 4, "buff": (BUFF_REVERSE, 5000, 1.0)},
}


class Pickup:
    def __init__(self, x, y, pickup_type):
        self.x = x
        self.y = y
        self.type = pickup_type
        cfg = PICKUP_CONFIG[pickup_type]
        self.kind = cfg["kind"]      # reward / penalty
        self.color = cfg["color"]    # 符号颜色
        self.symbol = cfg["symbol"]
        self.label = cfg.get("label", "")
        self.name = cfg["name"]
        self.radius = 16
        self.lifetime = PICKUP_LIFETIME_MS
        self.age = 0
        self.bob_phase = random.uniform(0, math.pi * 2)
        self.dead = False

    def update(self, dt, players, magnet_range=120, particles=None):
        self.age += dt
        if self.age >= self.lifetime:
            self.dead = True
            return
        for p in players:
            if self.kind == "reward":
                # 蛋形磁铁: 只吸附奖励道具 (惩罚道具永不被吸附, 磁铁升级不吃亏)
                rng = getattr(p, "magnet_range", None)
                if rng is None:
                    rng = magnet_range if getattr(p, "pickup_magnet", False) \
                        else min(magnet_range, 50)
                if getattr(p, "magnet_global", 0) > 0 \
                        and random.random() < p.magnet_global:
                    rng = 2000
                d = math.hypot(p.x - self.x, p.y - self.y)
                if 1 < d < rng:
                    spd = 4 if d < rng else 2
                    self.x += (p.x - self.x) / d * spd
                    self.y += (p.y - self.y) / d * spd
                    if particles is not None and random.random() < 0.3:
                        from entities.particle import spawn_magnet_dot
                        spawn_magnet_dot(particles, self.x, self.y)
            else:
                d = math.hypot(p.x - self.x, p.y - self.y)
            if d < (self.radius + 18):
                # 优先使用对象的 apply_pickup (游戏内 Light 代理, 内部转发到 PlayerData)
                ap = getattr(p, "apply_pickup", None)
                if callable(ap):
                    ap(self)
                else:
                    self.apply(p)
                if particles is not None:
                    self._spawn_feedback(particles)
                self.dead = True
                return

    def _spawn_feedback(self, particles):
        """拾取/中招反馈: 扩散圆环 + 上浮飘字 (效果一眼可见)"""
        from entities.particle import spawn_pickup_ping, spawn_pickup_text
        spawn_pickup_ping(particles, self.x, self.y, color=self.color)
        if self.label:
            spawn_pickup_text(particles, self.x, self.y - 22, self.label,
                              self.color)

    def apply(self, target, is_enemy=False):
        """即时/限时双路由结算。target 可为 PlayerData 或 EnemyTank。"""
        if self.kind == "reward":
            # 蛋形磁铁: 有磁铁时每次拾取奖励道具额外 +15 分
            if getattr(target, "pickup_magnet", False) and not is_enemy:
                target.score = getattr(target, "score", 0) + 15
            # 敌人拾取无敌星/分数: 无效果 (道具照样消失, 纯抢走)
            if is_enemy and self.type in (PickupType.INVINCIBLE, PickupType.SCORE):
                return
        if self.type == PickupType.HP:
            target.hp = min(target.max_hp, target.hp + 30)
        elif self.type == PickupType.SHIELD:
            # 默认上限 80; 已有升级盾 (>80) 时按升级上限 250, 不倒退
            cap = 250 if getattr(target, "shield", 0) > 80 else 80
            target.shield = min(cap, getattr(target, "shield", 0) + 40)
        elif self.type == PickupType.SCORE:
            target.score = getattr(target, "score", 0) + 500
        elif self.type == PickupType.POISON:
            # 毒液: -20 血, 最低剩 1 (不致死, 补刀靠枪)
            target.hp = max(1, target.hp - 20)
            d = getattr(target, "data", None)
            if d is not None:
                d.hp = target.hp
        else:
            key, ms, mult = PICKUP_CONFIG[self.type]["buff"]
            set_buff(target, key, ms, mult)

    def draw(self, surface, camera_x=0, camera_y=0):
        t = self.age / 1000.0
        bob = math.sin(t * 4 + self.bob_phase) * 3
        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y + bob)
        ring = RING_REWARD if self.kind == "reward" else RING_PENALTY
        # 2 倍超采样: 圆滑描边 + 清晰符号, 再平滑缩小 (抗锯齿)
        ss = 2
        pad = 4
        size = (self.radius + pad) * 2 * ss
        tmp = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size // 2
        pygame.draw.circle(tmp, (255, 255, 255), (c, c), self.radius * ss)
        pygame.draw.circle(tmp, ring, (c, c), self.radius * ss, 4 * ss)
        sym = _render_symbol(self.symbol, 20 * ss, self.color)
        tmp.blit(sym, sym.get_rect(center=(c, c)))
        icon = pygame.transform.smoothscale(tmp, (size // ss, size // ss))
        if self.lifetime - self.age < 3000:
            # 最后 3 秒闪烁提醒: 透明度脉动 (淡入淡出, 不整帧消失)
            alpha = int(90 + 165 * abs(math.sin(t * 10)))
            icon.set_alpha(alpha)
        surface.blit(icon, icon.get_rect(center=(sx, sy)))
