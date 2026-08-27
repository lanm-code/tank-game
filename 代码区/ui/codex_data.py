# -*- coding: utf-8 -*-
"""
游戏图鉴数据层
- 数值字段一律从游戏配置派生 (单一数据源, 改版自动跟进)
- 定位/机制/档案文案为手写 (图鉴专属)
- 条目 id 与游戏内配置 id 一致, 发现记录按 {kind: key} 存取
"""
from core.constants import (BULLET_CONFIG, BulletType, TANK_COLOR_CONFIG,
                            TankColor, SELECTABLE_TANK_COLORS, WALL_CONFIG,
                            WallType, ENEMY_CONFIG, EnemyType)
from systems.upgrade_system import (UPGRADE_POOL, UPGRADE_ICONS,
                                    UPGRADE_RARITY_COLORS, UpgradeIds)
from entities.boss import BOSS_CONFIG, BossId
from entities.pickup import PICKUP_CONFIG, PickupType

K_TANK = "tank"
K_BULLET = "bullet"
K_BOSS = "boss"
K_ENEMY = "enemy"
K_SKILL = "skill"
K_PICKUP = "pickup"
K_TILE = "tile"

RARITY_NAME = {"common": "普通", "rare": "稀有", "epic": "史诗",
               "legendary": "传说"}

# ------------------------------------------------------------------
# 图鉴分类目录 (L2 总览的 6 个入口)
# preview: 左橱窗内容类型
# ------------------------------------------------------------------
CODEX_CATEGORIES = [
    {"id": "tank", "name": "坦克图鉴", "count": 4, "key": "1",
     "desc": "四种颜色坦克与专属弹药",
     "desc2": "小黑子 · 奶龙 · 黑手 · 袋鼠", "preview": "tank"},
    {"id": "bullet", "name": "子弹图鉴", "count": 8, "key": "2",
     "desc": "伤害 · 射速 · 特效一眼看懂",
     "desc2": "破砖破沙发数一栏标清", "preview": "bullet"},
    {"id": "enemy", "name": "敌人图鉴", "count": 11, "key": "3",
     "desc": "五大首领与六种敌军",
     "desc2": "首领圆盘 · 敌军档案", "preview": "boss"},
    {"id": "skill", "name": "技能图鉴", "count": 26, "key": "4",
     "desc": "普通到传说四档稀有度",
     "desc2": "逐级效果全解析", "preview": "skill"},
    {"id": "pickup", "name": "道具图鉴", "count": 11, "key": "5",
     "desc": "蓝环奖励 · 红环惩罚",
     "desc2": "敌人也会抢 · 限时 10 秒", "preview": "pickup"},
    {"id": "tile", "name": "地块图鉴", "count": 13, "key": "6",
     "desc": "方块与地面效果",
     "desc2": "血量 · 通行 · 首次出现", "preview": "tile"},
]

# 发现记录总数表: {kind: 条目 key 集合} —— 收集进度的分母
def _seen_map():
    return {
        K_TANK: {TankColor.RED, TankColor.BLUE, TankColor.GREEN,
                 TankColor.YELLOW},
        K_BULLET: set(BULLET_CONFIG.keys()),
        K_BOSS: set(BOSS_CONFIG.keys()),
        K_ENEMY: set(ENEMY_CONFIG.keys()),
        K_SKILL: {u["id"] for u in UPGRADE_POOL if u["id"] != "residue_dmg"
                  and u["id"] != "residue_hp"},
        K_PICKUP: set(PICKUP_CONFIG.keys()),
        K_TILE: set(WALL_CONFIG.keys()),
    }


SEEN_MAP = _seen_map()


def codex_total():
    return sum(len(v) for v in SEEN_MAP.values())


def _dps(cfg):
    return round(cfg["damage"] * 1000.0 / max(1, cfg["cooldown"]), 1)


def _break_shots(dmg):
    if dmg <= 0:
        return "—"
    b = -(-56 // dmg)
    s = -(-22 // dmg)
    return f"破砖 {b} 发 · 破沙 {s} 发"


# ------------------------------------------------------------------
# 子弹图鉴 (8)
# ------------------------------------------------------------------
_BULLET_LORE = {
    BulletType.CANNON: "最普通的答案, 也是最可靠的。",
    BulletType.EGG: "火力不足恐惧症的解药。",
    BulletType.MILKY_EGG: "一发穿两个, 才算不浪费。",
    BulletType.KNIFE: "一刀, 一面墙。",
    BulletType.BASKETBALL: "球会拐弯, 敌人不会。",
    BulletType.MIC: "安静点, 听我唱。",
    BulletType.MELON: "保熟, 也保送。",
    BulletType.PARCEL: "货到付款, 概不拒收。",
}
_BULLET_POS = {
    BulletType.CANNON: "基准弹",
    BulletType.EGG: "高频压制",
    BulletType.MILKY_EGG: "直线对群",
    BulletType.KNIFE: "极速重炮",
    BulletType.BASKETBALL: "技巧弹射",
    BulletType.MIC: "控场眩晕",
    BulletType.MELON: "首领弹幕",
    BulletType.PARCEL: "对群爆发",
}
# 阵营 (可为多方共用: 篮球既是我方红坦克弹药, 也是 Boss1 的弹幕)
_BULLET_GROUPS = {
    BulletType.CANNON: ["敌方"],
    BulletType.EGG: ["我方"],
    BulletType.MILKY_EGG: ["我方"],
    BulletType.KNIFE: ["我方"],
    BulletType.BASKETBALL: ["我方", "敌方"],
    BulletType.MIC: ["敌方"],
    BulletType.MELON: ["敌方"],
    BulletType.PARCEL: ["敌方"],
}


def _bullet_mech(t, cfg):
    lines = []
    if cfg.get("pierce"):
        lines.append(f"穿透 {cfg['pierce']} 个目标")
    if cfg.get("ricochet"):
        lines.append(f"未命中时撞钢墙/边缘可回弹 {cfg['ricochet']} 次")
    if cfg.get("stun"):
        lines.append(f"命中眩晕 {cfg['stun']} 秒 (首领只吃 25%)")
    if cfg.get("sine"):
        lines.append("正弦波飞行 (声波感)")
    if cfg.get("splash"):
        lines.append(f"命中爆炸: {cfg['splash']['radius']}px 内溅射 "
                     f"{int(cfg['splash']['falloff'] * 100)}% 伤害")
    if cfg.get("explode"):
        lines.append("命中时爆炸")
    if not lines:
        lines.append("无特殊效果, 命中即消失")
    return lines


def _build_bullets():
    out = []
    for t, cfg in BULLET_CONFIG.items():
        groups = _BULLET_GROUPS.get(t, ["敌方"])
        out.append({
            "kind": K_BULLET, "id": t, "name": cfg["name"],
            "group": " / ".join(groups),   # 展示用 ("我方 / 敌方")
            "groups": groups,              # 筛选用 (多方共用)
            "pos": _BULLET_POS.get(t, ""),
            "lore": _BULLET_LORE.get(t, ""),
            "stats": [
                ("伤害", str(cfg["damage"])),
                ("冷却", f"{cfg['cooldown']} ms"),
                ("弹速", str(cfg["speed"])),
                ("秒伤 DPS", f"≈{_dps(cfg)}"),
                ("对墙", _break_shots(cfg["damage"])),
            ],
            "mech": _bullet_mech(t, cfg),
        })
    return out


# ------------------------------------------------------------------
# 坦克图鉴 (4)
# ------------------------------------------------------------------
_TANK_POS = {
    TankColor.RED: "弹射艺术",
    TankColor.BLUE: "高频压制",
    TankColor.GREEN: "重炮破墙",
    TankColor.YELLOW: "直线对群",
}
_TANK_TIP = {
    TankColor.RED: "朝钢墙斜着开炮, 篮球会自己找上敌人。",
    TankColor.BLUE: "按住右键就是泼水式输出, 最适合上手。",
    TankColor.GREEN: "飞刀一发打穿砖块, 专门用来开路。",
    TankColor.YELLOW: "让敌人排成一列再开火, 一发穿俩。",
}
_TANK_LORE = {
    TankColor.RED: "球可以不进, 敌人必须出局。",
    TankColor.BLUE: "准时送达, 分量管够。",
    TankColor.GREEN: "砖墙挡路? 给个面子, 让开。",
    TankColor.YELLOW: "奶蛋不是用来喝的, 是用来穿的。",
}


def _build_tanks():
    out = []
    for c in SELECTABLE_TANK_COLORS:
        cfg = TANK_COLOR_CONFIG[c]
        bc = BULLET_CONFIG[cfg["bullet_type"]]
        voice = cfg.get("victory_voice") or "无"
        dvoice = cfg.get("defeat_voice") or "无"
        out.append({
            "kind": K_TANK, "id": c, "name": cfg["name"],
            "group": "可选坦克", "pos": _TANK_POS.get(c, ""),
            "lore": _TANK_LORE.get(c, ""),
            "stats": [
                ("主武器", bc["name"]),
                ("武器特点", _BULLET_POS.get(cfg["bullet_type"], "")),
                ("胜利语音", f"「{voice}」" if voice != "无" else voice),
                ("战败语音", f"「{dvoice}」" if dvoice != "无" else dvoice),
            ],
            "mech": [_TANK_TIP.get(c, "")],
        })
    return out


# ------------------------------------------------------------------
# 首领图鉴 (5)
# ------------------------------------------------------------------
_BOSS_STAGE = {
    BossId.BOSS_1: ["阶段1 运球冲撞: 蓄力冲刺一路撒篮球",
                    "阶段2 螺旋篮球雨: 环形弹幕逼走位",
                    "阶段3 双环弹幕: 环缝站位输出"],
    BossId.BOSS_2: ["阶段1 T台巡游: 水平走秀 + 转身扇形齐射",
                    "阶段2 花瓣弹环: 麦克风花瓣弹幕",
                    "阶段3 走秀冲刺: 加速冲撞"],
    BossId.BOSS_3: ["首次受击开始吟唱 (全场 BGM)",
                    "第 8 秒: 满血 + 无敌, 击杀窗口关闭",
                    "BGM 结束: 直接判负"],
    BossId.BOSS_4: ["阶段1 蹦跳冲撞: 起跳越过砖墙砸落点",
                    "阶段2 外卖箱弹幕: 扇形连发 + 瞄准单发",
                    "阶段3 半血狂暴: 连跳两次",
                    "语音: 嘲讽「你胆子真是肥嘟嘟的」· 被击败「带是不可能带的」"],
    BossId.BOSS_5: ["阶段1 保熟突进: 蓄力 1 秒冲锋劈砍",
                    "阶段2 顶部落瓜雨: 全屏随机瓜弹",
                    "阶段3 旋转切瓜阵: 近身环形刀阵"],
}
_BOSS_TIP = {
    BossId.BOSS_1: "冲刺前摇明显, 下蹲就是信号, 横向拉开。",
    BossId.BOSS_2: "麦克风弹会眩晕你 0.4 秒, 躲弹优先于输出。",
    BossId.BOSS_3: "见面就全力开火, 8 秒内打完; 火力不足先去无尽发育。",
    BossId.BOSS_4: "它起跳时立刻横移; 外卖箱爆炸会溅射, 别贴墙站。",
    BossId.BOSS_5: "蓄力红光时朝冲锋路线垂直躲; 被近身劈到非常痛。",
}
_BOSS_LORE = {
    BossId.BOSS_1: "球场灯光未亮, 敌影先至。",
    BossId.BOSS_2: "掌声比爆炸更响, 笑容高达 120 分贝。",
    BossId.BOSS_3: "它不说话, 只等你先开炮。",
    BossId.BOSS_4: "这单必须送到——哪怕是送到你脸上。",
    BossId.BOSS_5: "这瓜保熟, 这刀也保熟。",
}
_BOSS_LEVEL = {
    BossId.BOSS_1: 5, BossId.BOSS_2: 10, BossId.BOSS_3: 15,
    BossId.BOSS_4: 20, BossId.BOSS_5: 25,
}


def _build_bosses():
    out = []
    for bid, cfg in BOSS_CONFIG.items():
        hp_story = int(cfg["max_hp"] * 1.5)
        shots = hp_story // 28
        bt = cfg.get("bullet_type")
        bname = BULLET_CONFIG[bt]["name"] if bt else "无 (纯 DPS 竞速)"
        stats = [
            ("出现关卡", f"第 {_BOSS_LEVEL.get(bid, '?')} 关"),
            ("血量 · 剧情", f"{hp_story} ≈ {shots} 发炮弹"),
            ("弹幕", bname),
            ("终章", "第 30 关全员返场"),
        ]
        if bid == BossId.BOSS_4:
            stats.append(("击败语音", "“你胆子真是肥嘟嘟的”"))
        out.append({
            "kind": K_BOSS, "id": bid, "name": cfg["name"],
            "group": "首领",
            "pos": f"第 {_BOSS_LEVEL.get(bid, '?')} 关首领",
            "lore": _BOSS_LORE.get(bid, ""),
            "stats": stats,
            "mech": _BOSS_STAGE.get(bid, []) + ["应对: " + _BOSS_TIP.get(bid, "")],
        })
    return out


# ------------------------------------------------------------------
# 敌军图鉴 (6)
# ------------------------------------------------------------------
_ENEMY_BEHAVIOR = {
    EnemyType.SCOUT: "高速贴脸, 开火偏慢。",
    EnemyType.ARTILLERY: "超远射程, 隔墙瞄人, 炮弹按伤害磨你的墙。",
    EnemyType.HEAVY: "肉盾三连发, 走得慢但很硬。",
    EnemyType.GHOST: "直接穿过砖墙 (但不会停在砖里)。",
    EnemyType.ENGINEER: "治疗友军, 每 0.6 秒回 2 血, 优先集火。",
    EnemyType.ELITE: "综合强化, 主动远程开火。",
}
_ENEMY_LORE = {
    EnemyType.SCOUT: "它不思考, 它只冲锋。",
    EnemyType.ARTILLERY: "它的炮弹, 专拆你的墙。",
    EnemyType.HEAVY: "它走得慢, 但你得打很久。",
    EnemyType.GHOST: "墙, 对它来说只是建议。",
    EnemyType.ENGINEER: "先打它, 不然白打。",
    EnemyType.ELITE: "军装笔挺, 弹道笔直。",
}


def _build_enemies():
    out = []
    for t, cfg in ENEMY_CONFIG.items():
        out.append({
            "kind": K_ENEMY, "id": t, "name": cfg["name"],
            "group": "敌军",
            "pos": _ENEMY_BEHAVIOR.get(t, ""),
            "lore": _ENEMY_LORE.get(t, ""),
            "stats": [
                ("血量", str(cfg["hp"])),
                ("移速", str(cfg["speed"])),
                ("伤害", str(cfg["damage"])),
                ("开火间隔", f"{cfg['fire_rate']} ms"),
            ],
            "mech": [_ENEMY_BEHAVIOR.get(t, "")],
        })
    return out


# ------------------------------------------------------------------
# 技能图鉴 (26, 不含残卡)
# ------------------------------------------------------------------
_SKILL_POS = {
    UpgradeIds.DAMAGE_FLAT: "伤害基石",
    UpgradeIds.RAPID_FIRE: "射速基石",
    UpgradeIds.SPEED_BOOST: "机动",
    UpgradeIds.ARMOR: "生存基石",
    UpgradeIds.PIERCE: "对群",
    UpgradeIds.DOUBLE_SHOT: "弹数 (与三发散射互斥)",
    UpgradeIds.MAGNET: "发育",
    UpgradeIds.FULL_HEAL: "急救",
    UpgradeIds.SHIELD_PICKUP: "护盾",
    UpgradeIds.TRIPLE_SHOT: "扇形火力 (与双发射击互斥)",
    UpgradeIds.RICOCHET: "弹射技巧",
    UpgradeIds.HEAVY_BARREL: "重炮",
    UpgradeIds.FROST_ROUNDS: "控场减速",
    UpgradeIds.VELOCITY_ROUNDS: "弹速",
    UpgradeIds.SHIELD_CHANCE: "格挡",
    UpgradeIds.VAMPIRE: "续航",
    UpgradeIds.DEATH_BLAST: "连锁爆炸",
    UpgradeIds.STATIC_FIELD: "自动雷击",
    UpgradeIds.LAST_STAND: "保命",
    UpgradeIds.DEAD_EYE: "先手狙击",
    UpgradeIds.RAILGUN: "机制: 贯穿激光",
    UpgradeIds.CHRONO_FIELD: "机制: 全场时停",
    UpgradeIds.PHANTOM_DUO: "机制: 幻影分身",
    UpgradeIds.DOOMSDAY: "机制: 全屏核爆",
    UpgradeIds.PHOENIX: "机制: 原地复活",
    UpgradeIds.BERSERK: "残血反击",
}
_SKILL_LORE = {
    UpgradeIds.DAMAGE_FLAT: "多打一点, 少打一炮。",
    UpgradeIds.RAPID_FIRE: "快一点, 再快一点。",
    UpgradeIds.SPEED_BOOST: "跑得快, 活得久。",
    UpgradeIds.ARMOR: "多扛一炮, 就多一分底气。",
    UpgradeIds.PIERCE: "一炮两响, 买一送一。",
    UpgradeIds.DOUBLE_SHOT: "双倍的弹, 双倍的快乐。",
    UpgradeIds.MAGNET: "道具自己会走路。",
    UpgradeIds.FULL_HEAL: "当场回满, 不带商量。",
    UpgradeIds.SHIELD_PICKUP: "先扣盾, 再扣命。",
    UpgradeIds.TRIPLE_SHOT: "三路并进, 总有一发打中。",
    UpgradeIds.RICOCHET: "让子弹再飞一会儿。",
    UpgradeIds.HEAVY_BARREL: "慢一点, 疼一点。",
    UpgradeIds.FROST_ROUNDS: "冻住它, 慢慢打。",
    UpgradeIds.VELOCITY_ROUNDS: "先到, 先赢。",
    UpgradeIds.SHIELD_CHANCE: "这一次, 弹开了。",
    UpgradeIds.VAMPIRE: "你的血, 归我了。",
    UpgradeIds.DEATH_BLAST: "一个倒, 一片倒。",
    UpgradeIds.STATIC_FIELD: "天雷滚滚, 自动瞄准。",
    UpgradeIds.LAST_STAND: "最后一口气, 也站得住。",
    UpgradeIds.DEAD_EYE: "满血, 即是猎场。",
    UpgradeIds.RAILGUN: "一束光, 一面墙, 一条路。",
    UpgradeIds.CHRONO_FIELD: "全场按下慢放键。",
    UpgradeIds.PHANTOM_DUO: "另一个你, 也在开炮。",
    UpgradeIds.DOOMSDAY: "一发, 清场。",
    UpgradeIds.PHOENIX: "死了? 重来一次。",
    UpgradeIds.BERSERK: "血越少, 越危险。",
}


def _build_skills():
    out = []
    for u in UPGRADE_POOL:
        if u["id"] in ("residue_dmg", "residue_hp"):
            continue
        out.append({
            "kind": K_SKILL, "id": u["id"], "name": u["name"],
            "rarity": u["rarity"],
            "group": RARITY_NAME.get(u["rarity"], "?"),
            "pos": _SKILL_POS.get(u["id"], ""),
            "lore": _SKILL_LORE.get(u["id"], ""),
            "icon": UPGRADE_ICONS.get(u["id"], "?"),
            "levels": [lv["desc"] for lv in u["levels"]],
        })
    return out


# ------------------------------------------------------------------
# 道具图鉴 (11)
# ------------------------------------------------------------------
_PICKUP_MECH = {
    PickupType.HP: "回复 +30 (不超上限); 满血拾取作废; 敌人捡走同样 +30。",
    PickupType.SHIELD: "护盾 +40 (上限 80); 护盾先于生命承伤。",
    PickupType.DAMAGE: "限时 10 秒伤害 ×1.5; 与锈蚀弹头互顶 (后拾取者覆盖)。",
    PickupType.RAPID: "限时 10 秒射击间隔 ×0.6; 与履带卡壳互顶。",
    PickupType.SPEED: "限时 10 秒移速 ×1.3 (不超上限 7.0)。",
    PickupType.SCORE: "分数 +500; 敌人捡走无效但道具消失 (抢分)。",
    PickupType.INVINCIBLE: "限时 5 秒免疫一切伤害; 敌人捡走无效但道具消失。",
    PickupType.POISON: "立即 -20 生命 (最低剩 1, 不致死); 敌我同坑。",
    PickupType.RUST: "限时 10 秒伤害 ×0.6; 覆盖火力强化。",
    PickupType.JAM: "限时 10 秒射击间隔 ×1.5; 覆盖急速射击。",
    PickupType.REVERSE: "限时 5 秒移动方向颠倒 (瞄准不受影响); 敌我同坑。",
}
_PICKUP_LORE = {
    PickupType.HP: "战场上最朴素的善意——但敌人也会捡。",
    PickupType.SHIELD: "先扣盾, 再扣命。",
    PickupType.DAMAGE: "十秒真男人。",
    PickupType.RAPID: "按住右键, 世界安静了。",
    PickupType.SPEED: "腿长, 命硬。",
    PickupType.SCORE: "分数无价, 五百也行。",
    PickupType.INVINCIBLE: "五秒之内, 你说了算。",
    PickupType.POISON: "看着像回复, 其实是陷阱。",
    PickupType.RUST: "炮管锈了, 火力打折。",
    PickupType.JAM: "卡住了, 慢慢打。",
    PickupType.REVERSE: "向左? 不, 向右。",
}
_PICKUP_STAT = {
    PickupType.HP: ("效果", "+30 生命"),
    PickupType.SHIELD: ("效果", "+40 护盾 (上限 80)"),
    PickupType.DAMAGE: ("效果", "伤害 ×1.5 · 持续 10 秒"),
    PickupType.RAPID: ("效果", "射击间隔 ×0.6 · 持续 10 秒"),
    PickupType.SPEED: ("效果", "移速 ×1.3 · 持续 10 秒"),
    PickupType.SCORE: ("效果", "分数 +500"),
    PickupType.INVINCIBLE: ("效果", "免疫伤害 · 持续 5 秒"),
    PickupType.POISON: ("效果", "生命 -20 (最低剩 1)"),
    PickupType.RUST: ("效果", "伤害 ×0.6 · 持续 10 秒"),
    PickupType.JAM: ("效果", "射击间隔 ×1.5 · 持续 10 秒"),
    PickupType.REVERSE: ("效果", "方向颠倒 · 持续 5 秒"),
}

_PICKUP_COMMON = [
    "掉落: 击杀敌人 18% / 木箱 15% / 首领击败 6 个",
    "场上最多 5 个, 10 秒不捡自动消失 (最后 3 秒闪烁)",
    "敌人同样会抢道具: 蓝环奖励它们吃, 红环惩罚它们也中",
]


def _build_pickups():
    out = []
    for t, cfg in PICKUP_CONFIG.items():
        kind_label = ("奖励 · 即时" if cfg["kind"] == "reward"
                      and "instant" in cfg
                      else "奖励 · 限时" if cfg["kind"] == "reward"
                      else "惩罚")
        out.append({
            "kind": K_PICKUP, "id": t, "name": cfg["name"],
            "group": "奖励" if cfg["kind"] == "reward" else "惩罚",
            "pos": kind_label,
            "lore": _PICKUP_LORE.get(t, ""),
            "symbol": cfg["symbol"],
            "pcolor": cfg["color"],
            "stats": [_PICKUP_STAT.get(t, ("效果", "")),
                      ("类别", kind_label)],
            "mech": [_PICKUP_MECH.get(t, "")] + _PICKUP_COMMON,
        })
    return out


# ------------------------------------------------------------------
# 地块图鉴 (13)
# ------------------------------------------------------------------
_TILE_UNLOCK = {
    WallType.STEEL: "第 1 关起",
    WallType.BRICK: "第 1 关起",
    WallType.SAND: "第 1 关起",
    WallType.CRATE: "第 3 关起",
    WallType.GLASS: "第 4 关起",
    WallType.BARREL: "第 5 关起",
    WallType.GRASS: "第 3 关起",
    WallType.WATER: "第 6 关起 (成片)",
    WallType.WATER_STAIN: "第 2 关起 (集群)",
    WallType.MUD: "第 4 关起",
    WallType.ICE: "第 6 关起 (成片)",
    WallType.SPIKE: "第 8 关起",
    WallType.PORTAL: "仅首领关 1 对",
}
_TILE_MECH = {
    WallType.STEEL: ["打不动: 任何攻击零伤害",
                     "弹射弹 (飞刀/篮球/西瓜) 撞它反弹, 其余子弹消失"],
    WallType.BRICK: ["56 血 = 一把飞刀的伤害",
                     "子弹命中扣自身伤害后消失 (不反弹不穿透不溅射)",
                     "飞刀 1 发打穿; 炮弹/西瓜 2 发; 篮球/外卖/鸡蛋 3 发"],
    WallType.SAND: ["22 血 = 一发篮球的伤害, 规则同砖块",
                    "篮球/炮弹/外卖/飞刀 1 发打穿; 鸡蛋/奶蛋/麦克风 2 发"],
    WallType.CRATE: ["1 发碎, 15% 概率掉一个随机道具",
                     "敌方炮弹打碎同样会掉, 先下手为强"],
    WallType.GLASS: ["挡坦克不挡子弹: 子弹穿过但玻璃碎 (1 发)",
                     "敌人能隔玻璃瞄你, 也会打碎它"],
    WallType.BARREL: ["打碎瞬间爆炸: 55px 内敌我各吃 40 伤害",
                      "同时摧毁 3×3 区域内所有可摧毁方块 (地块不受影响)",
                      "白色叹号是提醒——引爆前先拉开距离"],
    WallType.GRASS: ["潜行: 完全藏进草丛且 1.5 秒未开火, 敌人看不见你",
                     "开火立刻暴露; 首领不吃潜行"],
    WallType.WATER: ["坦克过不去, 子弹飞得过, 永久存在"],
    WallType.WATER_STAIN: ["移动踩入: 锁定当时方向滑行, 无法转向/停止",
                           "滑行中仍可开火; 撞墙/坦克/边缘恢复操控",
                           "敌人同样会滑行 (AI 冻结)"],
    WallType.MUD: ["踩上移速 ×0.6 (与减速/冰面乘区叠加)"],
    WallType.ICE: ["踩上移速 ×1.4, 可控 (和水渍的失控滑相反)"],
    WallType.SPIKE: ["站立每 0.5 秒掉 30 血, 敌我同伤, 离开即重置"],
    WallType.PORTAL: ["成对出现: 坦克中心踏入即传送到配对门",
                      "1.5 秒冷却防无限弹跳; 首领不传送, 小兵会传"],
}
_TILE_LORE = {
    WallType.STEEL: "它不说话, 它只是站在那里。",
    WallType.BRICK: "一把刀, 换一面墙。",
    WallType.SAND: "软柿子, 也要一炮。",
    WallType.CRATE: "拆墙如拆盲盒。",
    WallType.GLASS: "看得见, 打得到, 过不去。",
    WallType.BARREL: "站远点, 它是双刃剑。",
    WallType.GRASS: "趴好, 别开炮。",
    WallType.WATER: "坦克过不去, 子弹飞得过。",
    WallType.WATER_STAIN: "它不伤人, 但会让你撞上别人。",
    WallType.MUD: "泥巴糊履带, 走不动。",
    WallType.ICE: "踩上去, 跑得飞快。",
    WallType.SPIKE: "别站上去, 一秒都不想。",
    WallType.PORTAL: "门的那头, 是战场的另一头。",
}
_TILE_GROUP = {
    WallType.STEEL: "方块", WallType.BRICK: "方块", WallType.SAND: "方块",
    WallType.CRATE: "方块", WallType.GLASS: "方块", WallType.BARREL: "方块",
    WallType.GRASS: "地块", WallType.WATER: "地块",
    WallType.WATER_STAIN: "地块", WallType.MUD: "地块",
    WallType.ICE: "地块", WallType.SPIKE: "地块", WallType.PORTAL: "地块",
}


def _build_tiles():
    out = []
    for t, cfg in WALL_CONFIG.items():
        hp = cfg["hp"]
        hp_txt = "打不动" if hp < 0 else str(hp)
        block = "挡" if not cfg.get("tank_pass") else "过"
        bullet = "挡" if not cfg.get("bullet_pass") else "过"
        out.append({
            "kind": K_TILE, "id": t,
            "name": TILE_NAMES.get(t, str(t)),  # 名称在 UI 侧映射 (见 TILE_NAMES)
            "group": _TILE_GROUP.get(t, "地块"),
            "pos": _TILE_UNLOCK.get(t, ""),
            "lore": _TILE_LORE.get(t, ""),
            "stats": [
                ("血量", hp_txt),
                ("坦克", block),
                ("子弹", bullet),
                ("首次出现", _TILE_UNLOCK.get(t, "")),
            ],
            "mech": _TILE_MECH.get(t, []),
        })
    return out


TILE_NAMES = {
    WallType.STEEL: "钢墙", WallType.BRICK: "砖块", WallType.SAND: "沙粒方块",
    WallType.CRATE: "木箱", WallType.GLASS: "玻璃墙",
    WallType.BARREL: "燃油桶", WallType.GRASS: "草丛",
    WallType.WATER: "水面", WallType.WATER_STAIN: "水渍",
    WallType.MUD: "泥沼", WallType.ICE: "冰面", WallType.SPIKE: "尖刺",
    WallType.PORTAL: "传送门",
}

# 墙体纹理贴图文件名 (与 素材库\墙体纹理 对应, 兜底程序化绘制)
TILE_TEXTURES = {
    WallType.STEEL: "steel.png", WallType.BRICK: "brick.png",
    WallType.SAND: "sand.png", WallType.CRATE: "crate.png",
    WallType.GLASS: "glass.png", WallType.BARREL: "barrel.png",
    WallType.GRASS: "grass.png", WallType.WATER: "water.png",
    WallType.WATER_STAIN: "water_stain.png", WallType.MUD: "mud.png",
    WallType.ICE: "ice.png", WallType.SPIKE: "spike.png",
    WallType.PORTAL: "portal.png",
}


# ------------------------------------------------------------------
# 汇总
# ------------------------------------------------------------------
def build_codex():
    """组装全部图鉴条目 (按分类 id 聚合)"""
    return {
        "tank": _build_tanks(),
        "bullet": _build_bullets(),
        "boss": _build_bosses(),
        "enemy": _build_enemies(),
        "skill": _build_skills(),
        "pickup": _build_pickups(),
        "tile": _build_tiles(),
    }


CODEX = build_codex()
