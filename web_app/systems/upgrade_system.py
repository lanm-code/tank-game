# -*- coding: utf-8 -*-
"""
Roguelike 升级系统 (按《技能系统设计方案.md》大改版)
- 技能池: 每项含 levels 逐级效果表 (desc + apply(player, lv))
- 抽卡: 三选一, 排除满级/互斥技能; 概率权重接入点在 available_upgrades
- 等级: PlayerData.upgrade_levels 记录当前等级
"""
import random

from core.constants import *


class UpgradeIds:
    # 普通
    DAMAGE_FLAT = "damage_flat"
    RAPID_FIRE = "rapid_fire"
    SPEED_BOOST = "speed_boost"
    ARMOR = "armor"
    PIERCE = "pierce"
    DOUBLE_SHOT = "double_shot"
    MAGNET = "magnet"
    FULL_HEAL = "full_heal"
    SHIELD_PICKUP = "shield_pickup"
    # 稀有
    TRIPLE_SHOT = "triple_shot"
    RICOCHET = "ricochet"
    HEAVY_BARREL = "heavy_barrel"
    FROST_ROUNDS = "frost_rounds"
    VELOCITY_ROUNDS = "velocity_rounds"
    # 史诗
    SHIELD_CHANCE = "shield_chance"
    VAMPIRE = "vampire"
    DEATH_BLAST = "death_blast"
    STATIC_FIELD = "static_field"
    LAST_STAND = "last_stand"
    DEAD_EYE = "dead_eye"
    # 传说
    RAILGUN = "railgun"
    CHRONO_FIELD = "chrono_field"
    PHANTOM_DUO = "phantom_duo"
    DOOMSDAY = "doomsday"
    PHOENIX = "phoenix"
    BERSERK = "berserk"


# 稀有度配色 (选技能页卡片边框 + HUD 小图标共用):
# 普通=白 稀有=蓝 史诗=紫 传说=橙
UPGRADE_RARITY_COLORS = {
    "common": (232, 232, 236),
    "rare": (70, 140, 255),
    "epic": (170, 90, 255),
    "legendary": (255, 150, 40),
}

# 技能图标符号 (选技能页大图标 + HUD 小图标共用)
UPGRADE_ICONS = {
    UpgradeIds.DOUBLE_SHOT: "2",
    UpgradeIds.TRIPLE_SHOT: "3",
    UpgradeIds.PIERCE: "P",
    UpgradeIds.RICOCHET: "R",
    UpgradeIds.RAPID_FIRE: "»",
    UpgradeIds.HEAVY_BARREL: "O",
    UpgradeIds.SPEED_BOOST: ">",
    UpgradeIds.ARMOR: "+",
    UpgradeIds.SHIELD_CHANCE: "@",
    UpgradeIds.VAMPIRE: "V",
    UpgradeIds.MAGNET: "M",
    UpgradeIds.FULL_HEAL: "H",
    UpgradeIds.SHIELD_PICKUP: "$",
    UpgradeIds.DAMAGE_FLAT: "X",
    UpgradeIds.FROST_ROUNDS: "❄",
    UpgradeIds.VELOCITY_ROUNDS: "→",
    UpgradeIds.DEATH_BLAST: "✹",
    UpgradeIds.STATIC_FIELD: "⚡",
    UpgradeIds.LAST_STAND: "✚",
    UpgradeIds.DEAD_EYE: "◎",
    UpgradeIds.RAILGUN: "═",
    UpgradeIds.CHRONO_FIELD: "⏱",
    UpgradeIds.PHANTOM_DUO: "♊",
    UpgradeIds.DOOMSDAY: "☢",
    UpgradeIds.PHOENIX: "♨",
    UpgradeIds.BERSERK: "⚔",
}

# 技能池 (26 个: 普通9 / 稀有5 / 史诗6 / 传说6)
# 每项: id / name / rarity / weight / levels:[{desc, apply(player, lv)} × N]
# excludes: 互斥技能 id (同类机制二选一)
UPGRADE_POOL = [
    # ---------------- 普通 (最高 Lv4) ----------------
    {"id": UpgradeIds.DAMAGE_FLAT, "name": "炮弹强化",
     "rarity": "common", "weight": 10,
     "levels": [
         {"desc": "基础伤害 +8",
          "apply": lambda p, lv: setattr(p, "base_damage", p.base_damage + 8)},
         {"desc": "基础伤害 +16",
          "apply": lambda p, lv: setattr(p, "base_damage", p.base_damage + 8)},
         {"desc": "基础伤害 +26",
          "apply": lambda p, lv: setattr(p, "base_damage", p.base_damage + 10)},
         {"desc": "基础伤害 +38",
          "apply": lambda p, lv: setattr(p, "base_damage", p.base_damage + 12)},
     ]},
    {"id": UpgradeIds.RAPID_FIRE, "name": "急速射击",
     "rarity": "common", "weight": 10,
     "levels": [
         {"desc": "射击间隔 -12%",
          "apply": lambda p, lv: setattr(p, "fire_rate_mult", p.fire_rate_mult * 0.88)},
         {"desc": "射击间隔 -22%",
          "apply": lambda p, lv: setattr(p, "fire_rate_mult", p.fire_rate_mult * 0.886)},
         {"desc": "射击间隔 -30%",
          "apply": lambda p, lv: setattr(p, "fire_rate_mult", p.fire_rate_mult * 0.897)},
         {"desc": "射击间隔 -38%",
          "apply": lambda p, lv: setattr(p, "fire_rate_mult", p.fire_rate_mult * 0.886)},
     ]},
    {"id": UpgradeIds.SPEED_BOOST, "name": "极速引擎",
     "rarity": "common", "weight": 9,
     "levels": [
         {"desc": "移速 +12%",
          "apply": lambda p, lv: setattr(p, "speed", min(7.0, p.speed * 1.12))},
         {"desc": "移速 +22%",
          "apply": lambda p, lv: setattr(p, "speed", min(7.0, p.speed * 1.089))},
         {"desc": "移速 +32%",
          "apply": lambda p, lv: setattr(p, "speed", min(7.0, p.speed * 1.082))},
         {"desc": "移速 +40%",
          "apply": lambda p, lv: setattr(p, "speed", min(7.0, p.speed * 1.061))},
     ]},
    {"id": UpgradeIds.ARMOR, "name": "装甲镀层",
     "rarity": "common", "weight": 9,
     "levels": [
         {"desc": "最大生命 +40 并回满",
          "apply": lambda p, lv: (setattr(p, "max_hp", p.max_hp + 40),
                                  setattr(p, "hp", p.max_hp))},
         {"desc": "最大生命 +80 并回满",
          "apply": lambda p, lv: (setattr(p, "max_hp", p.max_hp + 40),
                                  setattr(p, "hp", p.max_hp))},
         {"desc": "最大生命 +120 并回满",
          "apply": lambda p, lv: (setattr(p, "max_hp", p.max_hp + 40),
                                  setattr(p, "hp", p.max_hp))},
         {"desc": "最大生命 +160 并回满",
          "apply": lambda p, lv: (setattr(p, "max_hp", p.max_hp + 40),
                                  setattr(p, "hp", p.max_hp))},
     ]},
    {"id": UpgradeIds.PIERCE, "name": "穿透强化",
     "rarity": "common", "weight": 10,
     "levels": [
         {"desc": "子弹穿透 +1",
          "apply": lambda p, lv: setattr(p, "pierce_add", lv)},
         {"desc": "子弹穿透 +2",
          "apply": lambda p, lv: setattr(p, "pierce_add", lv)},
         {"desc": "子弹穿透 +3",
          "apply": lambda p, lv: setattr(p, "pierce_add", lv)},
         {"desc": "子弹穿透 +4",
          "apply": lambda p, lv: setattr(p, "pierce_add", lv)},
     ]},
    {"id": UpgradeIds.DOUBLE_SHOT, "name": "双发射击",
     "rarity": "common", "weight": 10, "excludes": [UpgradeIds.TRIPLE_SHOT],
     "levels": [
         {"desc": "二连击: 连发 2 弹, 每发 60% 伤害",
          "apply": lambda p, lv: (setattr(p, "burst_shots", 2),
                                  setattr(p, "burst_delay", 130),
                                  setattr(p, "multi_shot", 1),
                                  setattr(p, "shot_dmg_mult", 0.60))},
         {"desc": "二连击: 连发 2 弹, 每发 70% 伤害",
          "apply": lambda p, lv: (setattr(p, "burst_shots", 2),
                                  setattr(p, "burst_delay", 130),
                                  setattr(p, "multi_shot", 1),
                                  setattr(p, "shot_dmg_mult", 0.70))},
         {"desc": "二连击: 连发 2 弹, 每发 85% 伤害",
          "apply": lambda p, lv: (setattr(p, "burst_shots", 2),
                                  setattr(p, "burst_delay", 130),
                                  setattr(p, "multi_shot", 1),
                                  setattr(p, "shot_dmg_mult", 0.85))},
         {"desc": "二连击: 2 弹均恢复满伤害 (100%)",
          "apply": lambda p, lv: (setattr(p, "burst_shots", 2),
                                  setattr(p, "burst_delay", 130),
                                  setattr(p, "multi_shot", 1),
                                  setattr(p, "shot_dmg_mult", 1.0))},
     ]},
    {"id": UpgradeIds.MAGNET, "name": "蛋形磁铁",
     "rarity": "common", "weight": 7,
     "levels": [
         {"desc": "道具吸附范围 +60%",
          "apply": lambda p, lv: (setattr(p, "pickup_magnet", True),
                                  setattr(p, "magnet_range", 80))},
         {"desc": "道具吸附范围 +120%",
          "apply": lambda p, lv: setattr(p, "magnet_range", 120)},
         {"desc": "全屏吸附 40% 概率",
          "apply": lambda p, lv: (setattr(p, "magnet_range", 160),
                                  setattr(p, "magnet_global", 0.4))},
         {"desc": "全屏吸附 80% 概率",
          "apply": lambda p, lv: (setattr(p, "magnet_range", 200),
                                  setattr(p, "magnet_global", 0.8))},
     ]},
    {"id": UpgradeIds.FULL_HEAL, "name": "紧急维修",
     "rarity": "common", "weight": 7,
     "levels": [
         {"desc": "立即回满生命",
          "apply": lambda p, lv: setattr(p, "hp", p.max_hp)},
         {"desc": "回满 + 上限+25",
          "apply": lambda p, lv: (setattr(p, "max_hp", p.max_hp + 25),
                                  setattr(p, "hp", p.max_hp))},
         {"desc": "回满 + 上限+50",
          "apply": lambda p, lv: (setattr(p, "max_hp", p.max_hp + 25),
                                  setattr(p, "hp", p.max_hp))},
         {"desc": "回满 + 上限+75",
          "apply": lambda p, lv: (setattr(p, "max_hp", p.max_hp + 25),
                                  setattr(p, "hp", p.max_hp))},
     ]},
    {"id": UpgradeIds.SHIELD_PICKUP, "name": "临时护盾",
     "rarity": "common", "weight": 7,
     "levels": [
         {"desc": "获得 80 点护盾",
          "apply": lambda p, lv: setattr(p, "shield", min(250, p.shield + 80))},
         {"desc": "获得 115 点护盾",
          "apply": lambda p, lv: setattr(p, "shield", min(250, p.shield + 35))},
         {"desc": "获得 150 点护盾",
          "apply": lambda p, lv: setattr(p, "shield", min(250, p.shield + 35))},
         {"desc": "获得 185 点护盾",
          "apply": lambda p, lv: setattr(p, "shield", min(250, p.shield + 35))},
     ]},
    # ---------------- 稀有 (最高 Lv3) ----------------
    {"id": UpgradeIds.TRIPLE_SHOT, "name": "三发散射",
     "rarity": "rare", "weight": 6, "excludes": [UpgradeIds.DOUBLE_SHOT],
     "levels": [
         {"desc": "3 发扇形 (±10°, 每发65%)",
          "apply": lambda p, lv: (setattr(p, "multi_shot", 3),
                                  setattr(p, "spread_deg", 10),
                                  setattr(p, "shot_dmg_mult", 0.65))},
         {"desc": "4 发扇形 (±12°, 每发60%)",
          "apply": lambda p, lv: (setattr(p, "multi_shot", 4),
                                  setattr(p, "spread_deg", 12),
                                  setattr(p, "shot_dmg_mult", 0.60))},
         {"desc": "5 发扇形 (±14°, 每发55%)",
          "apply": lambda p, lv: (setattr(p, "multi_shot", 5),
                                  setattr(p, "spread_deg", 14),
                                  setattr(p, "shot_dmg_mult", 0.55))},
     ]},
    {"id": UpgradeIds.RICOCHET, "name": "弹射强化",
     "rarity": "rare", "weight": 8,
     "levels": [
         {"desc": "子弹弹射 +2",
          "apply": lambda p, lv: setattr(p, "ricochet_add", lv * 2)},
         {"desc": "子弹弹射 +4",
          "apply": lambda p, lv: setattr(p, "ricochet_add", lv * 2)},
         {"desc": "子弹弹射 +6",
          "apply": lambda p, lv: setattr(p, "ricochet_add", lv * 2)},
     ]},
    {"id": UpgradeIds.HEAVY_BARREL, "name": "重型炮管",
     "rarity": "rare", "weight": 7,
     "levels": [
         {"desc": "伤害 +50%, 射速 -12%",
          "apply": lambda p, lv: (setattr(p, "base_damage", int(p.base_damage * 1.5)),
                                  setattr(p, "fire_rate_mult", p.fire_rate_mult * 1.12))},
         {"desc": "伤害 +75%, 射速 -12%",
          "apply": lambda p, lv: (setattr(p, "base_damage", int(p.base_damage * 1.167)),
                                  setattr(p, "fire_rate_mult", p.fire_rate_mult * 1.0))},
         {"desc": "伤害 +100%, 射速 -15%",
          "apply": lambda p, lv: (setattr(p, "base_damage", int(p.base_damage * 1.143)),
                                  setattr(p, "fire_rate_mult", p.fire_rate_mult * 1.027))},
     ]},
    {"id": UpgradeIds.FROST_ROUNDS, "name": "冰霜弹头",
     "rarity": "rare", "weight": 7,
     "levels": [
         {"desc": "命中减速并降攻速 15% / 2.5秒",
          "apply": lambda p, lv: (setattr(p, "frost_slow", 0.15),
                                  setattr(p, "frost_slow_fire", 0.15),
                                  setattr(p, "frost_slow_dur", 2500))},
         {"desc": "命中减速并降攻速 25% / 3秒",
          "apply": lambda p, lv: (setattr(p, "frost_slow", 0.25),
                                  setattr(p, "frost_slow_fire", 0.25),
                                  setattr(p, "frost_slow_dur", 3000))},
         {"desc": "命中减速并降攻速 35% / 3.5秒",
          "apply": lambda p, lv: (setattr(p, "frost_slow", 0.35),
                                  setattr(p, "frost_slow_fire", 0.35),
                                  setattr(p, "frost_slow_dur", 3500))},
     ]},
    {"id": UpgradeIds.VELOCITY_ROUNDS, "name": "加速弹头",
     "rarity": "rare", "weight": 7,
     "levels": [
         {"desc": "弹速 ×1.3, 伤害 +10",
          "apply": lambda p, lv: (setattr(p, "bullet_speed_mult", 1.3),
                                  setattr(p, "base_damage", p.base_damage + 10))},
         {"desc": "弹速 ×1.6, 伤害 +20",
          "apply": lambda p, lv: (setattr(p, "bullet_speed_mult", 1.6),
                                  setattr(p, "base_damage", p.base_damage + 10))},
         {"desc": "弹速 ×1.9, 伤害 +30",
          "apply": lambda p, lv: (setattr(p, "bullet_speed_mult", 1.9),
                                  setattr(p, "base_damage", p.base_damage + 10))},
     ]},
    # ---------------- 史诗 (最高 Lv2) ----------------
    {"id": UpgradeIds.SHIELD_CHANCE, "name": "能量护盾",
     "rarity": "epic", "weight": 5,
     "levels": [
         {"desc": "受击 20% 概率免疫 (附0.5秒无敌帧)",
          "apply": lambda p, lv: setattr(p, "shield_chance", 0.20)},
         {"desc": "受击 30% 概率免疫 (附0.5秒无敌帧)",
          "apply": lambda p, lv: setattr(p, "shield_chance", 0.30)},
     ]},
    {"id": UpgradeIds.VAMPIRE, "name": "吸血子弹",
     "rarity": "epic", "weight": 5,
     "levels": [
         {"desc": "造成伤害 12% 回血",
          "apply": lambda p, lv: setattr(p, "life_steal", 0.12)},
         {"desc": "造成伤害 20% 回血",
          "apply": lambda p, lv: setattr(p, "life_steal", 0.20)},
     ]},
    {"id": UpgradeIds.DEATH_BLAST, "name": "死亡爆破",
     "rarity": "epic", "weight": 5,
     "levels": [
         {"desc": "击杀爆炸: 半径120 / 60%伤害",
          "apply": lambda p, lv: (setattr(p, "death_blast_radius", 120),
                                  setattr(p, "death_blast_ratio", 0.6))},
         {"desc": "击杀爆炸: 半径180 / 100%伤害",
          "apply": lambda p, lv: (setattr(p, "death_blast_radius", 180),
                                  setattr(p, "death_blast_ratio", 1.0))},
     ]},
    {"id": UpgradeIds.STATIC_FIELD, "name": "静电场",
     "rarity": "epic", "weight": 5,
     "levels": [
         {"desc": "每 6 秒雷击最近敌人 (100%伤害+0.4秒眩晕)",
          "apply": lambda p, lv: (setattr(p, "static_interval", 6000),
                                  setattr(p, "static_ratio", 1.0))},
         {"desc": "每 4 秒雷击最近敌人 (150%伤害+0.4秒眩晕)",
          "apply": lambda p, lv: (setattr(p, "static_interval", 4000),
                                  setattr(p, "static_ratio", 1.5))},
     ]},
    {"id": UpgradeIds.LAST_STAND, "name": "不屈意志",
     "rarity": "epic", "weight": 5,
     "levels": [
         {"desc": "致命伤保 1 血 + 2.5秒无敌 (每关1次)",
          "apply": lambda p, lv: setattr(p, "last_stand_invuln", 2500)},
         {"desc": "致命伤保 1 血 + 4秒无敌 (每关1次)",
          "apply": lambda p, lv: setattr(p, "last_stand_invuln", 4000)},
     ]},
    {"id": UpgradeIds.DEAD_EYE, "name": "狙击之眼",
     "rarity": "epic", "weight": 5,
     "levels": [
         {"desc": "对血量≥70%敌人伤害 +80% (满血命中穿透+1)",
          "apply": lambda p, lv: setattr(p, "dead_eye_mult", 1.8)},
         {"desc": "对血量≥70%敌人伤害 +150% (满血命中穿透+1)",
          "apply": lambda p, lv: setattr(p, "dead_eye_mult", 2.5)},
     ]},
    # ---------------- 传说 (Lv1 固定) ----------------
    {"id": UpgradeIds.RAILGUN, "name": "轨道炮",
     "rarity": "legendary", "weight": 2,
     "levels": [
         {"desc": "普攻变贯穿激光: 穿透+6 伤害×1.8 冷却+10%, 摧毁沿途砖墙",
          "apply": lambda p, lv: None},
     ]},
    {"id": UpgradeIds.CHRONO_FIELD, "name": "时间静止",
     "rarity": "legendary", "weight": 2,
     "levels": [
         {"desc": "每 18 秒全场敌人减速 90% + 眩晕 1.5 秒",
          "apply": lambda p, lv: None},
     ]},
    {"id": UpgradeIds.PHANTOM_DUO, "name": "幻影军团",
     "rarity": "legendary", "weight": 2,
     "levels": [
         {"desc": "召唤幻影坦克镜像你的完整射击 (75% 伤害)",
          "apply": lambda p, lv: None},
     ]},
    {"id": UpgradeIds.DOOMSDAY, "name": "末日核弹",
     "rarity": "legendary", "weight": 2,
     "levels": [
         {"desc": "每 45 秒全屏核爆: 500% 伤害 + 清除敌方子弹",
          "apply": lambda p, lv: None},
     ]},
    {"id": UpgradeIds.PHOENIX, "name": "不死凤凰",
     "rarity": "legendary", "weight": 2,
     "levels": [
         {"desc": "死亡时原地复活 1 次 (50% 生命 + 3 秒无敌 + 清除敌方子弹)",
          "apply": lambda p, lv: None},
     ]},
    {"id": UpgradeIds.BERSERK, "name": "狂战士",
     "rarity": "legendary", "weight": 2,
     "levels": [
         {"desc": "每损失 1% 生命 +1% 伤害; 生命<30% 额外 +30% 攻速",
          "apply": lambda p, lv: None},
     ]},
]


# 属性残卡 (卡池枯竭时的无限兜底, 见设计方案 2.5): 最基础数值加成
RESIDUE_POOL = [
    {"id": "residue_dmg", "name": "残能·伤害", "rarity": "common", "weight": 0,
     "levels": [{"desc": "基础伤害 +5",
                 "apply": lambda p, lv: setattr(p, "base_damage", p.base_damage + 5)}] * 99},
    {"id": "residue_hp", "name": "残能·生命", "rarity": "common", "weight": 0,
     "levels": [{"desc": "最大生命 +20 并回满",
                 "apply": lambda p, lv: (setattr(p, "max_hp", p.max_hp + 20),
                                         setattr(p, "hp", p.max_hp))}] * 99},
]

for _r in RESIDUE_POOL:
    UPGRADE_ICONS[_r["id"]] = {"residue_dmg": "+", "residue_hp": "H"}.get(
        _r["id"], "?")


class UpgradeSystem:
    @staticmethod
    def _rarity_weights(level):
        """方案B 渐进稀有度权重 (普通/稀有/史诗/传说 %), 按关卡档位"""
        if level <= 5:
            return {"common": 70, "rare": 25, "epic": 5, "legendary": 0}
        if level <= 10:
            return {"common": 55, "rare": 33, "epic": 12, "legendary": 0}
        if level <= 20:
            return {"common": 45, "rare": 35, "epic": 15, "legendary": 5}
        return {"common": 35, "rare": 40, "epic": 17, "legendary": 8}

    def available_upgrades(self, player, count=3, level=1):
        """三选一抽卡:
        第1张必为新技能 (按方案B稀有度权重加权);
        第2张必为升级卡 (已拥有且未满级, 等概率), 没有则补新技能;
        第3张随机 (新技能/升级卡各半, 某类为空则另一类);
        传说: 第10关起入池, 每局最多 2 个; 池枯竭时属性残卡兜底。
        """
        levels = getattr(player, "upgrade_levels", None) or {}
        chosen = set()

        def owned(u):
            return levels.get(u["id"], 0)

        def excluded(u):
            for ex in u.get("excludes", []):
                if levels.get(ex, 0) > 0:
                    return True
            return False

        def is_new_able(u):
            return owned(u) == 0 and not excluded(u)

        def is_upgrade_able(u):
            return 0 < owned(u) < len(u["levels"])

        new_pool = [u for u in UPGRADE_POOL if is_new_able(u)]
        up_pool = [u for u in UPGRADE_POOL if is_upgrade_able(u)]
        tier = self._rarity_weights(level)
        legend_ok = (level >= 10
                     and getattr(player, "legendary_count", 0) < 2)

        def pick_new():
            # 先按方案B稀有度概率选档, 再档内等概率选技能
            by_rarity = {}
            for r, w in tier.items():
                if w <= 0:
                    continue
                cands = [u for u in new_pool
                         if u["id"] not in chosen and u["rarity"] == r]
                if r == "legendary" and not legend_ok:
                    cands = []
                by_rarity[r] = cands
            avail = [(r, tier[r]) for r, cs in by_rarity.items() if cs]
            if not avail:
                return None
            r = random.choices([x[0] for x in avail],
                               weights=[x[1] for x in avail], k=1)[0]
            return random.choice(by_rarity[r])

        def pick_upgrade():
            cands = [u for u in up_pool if u["id"] not in chosen]
            if not cands:
                return None
            return random.choice(cands)  # 升级卡等概率, 不按稀有度加权

        def make_card(u):
            lv = owned(u) + 1
            return {"id": u["id"], "name": u["name"], "rarity": u["rarity"],
                    "weight": u.get("weight", 1), "next_level": lv,
                    "desc": u["levels"][lv - 1]["desc"], "levels": u["levels"],
                    "is_max": lv >= len(u["levels"])}

        options = []
        # 第 1 张: 必为新技能
        u = pick_new()
        if u:
            chosen.add(u["id"])
            options.append(make_card(u))
        # 第 2 张: 必为升级卡 (没有则补新技能)
        if len(options) < count:
            u = pick_upgrade()
            if u is None:
                u = pick_new()
            if u:
                chosen.add(u["id"])
                options.append(make_card(u))
        # 第 3 张: 随机 (新技能/升级卡各半)
        if len(options) < count:
            want_new = random.random() < 0.5
            u = pick_new() if want_new else pick_upgrade()
            if u is None:
                u = pick_upgrade() if want_new else pick_new()
            if u:
                chosen.add(u["id"])
                options.append(make_card(u))
        # 兜底: 属性残卡补位 (无尽模式后期卡池枯竭)
        while len(options) < count:
            cands = [r for r in RESIDUE_POOL if r["id"] not in chosen]
            if not cands:
                cands = list(RESIDUE_POOL)
            r = random.choice(cands)
            chosen.add(r["id"])
            options.append(make_card(r))
        return options[:count]

    def apply_upgrade(self, player, upgrade):
        uid = upgrade["id"]
        levels = getattr(player, "upgrade_levels", None)
        if levels is None:
            levels = {}
            player.upgrade_levels = levels
        lv = levels.get(uid, 0) + 1
        lv_list = upgrade.get("levels") or []
        if lv > len(lv_list):
            return  # 已满级 (卡池本应已排除, 防御性兜底)
        lv_list[lv - 1]["apply"](player, lv)
        levels[uid] = lv
        player.buffs.append(uid)
        if upgrade.get("rarity") == "legendary":
            player.legendary_count = getattr(player, "legendary_count", 0) + 1
