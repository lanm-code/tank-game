# -*- coding: utf-8 -*-
"""
全局常量定义
Global Constants
"""
import pygame

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
FPS = 60
TILE_SIZE = 64

MAP_COLS = 30
MAP_ROWS = 16

# 极简塔防风配色: 全灰阶, 坦克本色是全游戏唯一彩色来源
# (2026-08 背景改版: 对齐《极简塔防》参考图取样 #2f2f2f 深灰底 / #535352 网格)
NEON_CYAN = (150, 160, 170)      # 原霓虹青 -> 冷灰 (描边/强调线)
NEON_PINK = (210, 210, 218)      # 原霓虹粉 -> 亮灰白 (就绪/强调)
NEON_YELLOW = (205, 200, 180)    # 原霓虹黄 -> 暖灰 (警告/分数)
NEON_GREEN = (120, 200, 140)     # 原霓虹绿 -> 暗绿 (血量正向)
NEON_RED = (200, 85, 85)         # 原霓虹红 -> 暗红 (危险)
NEON_PURPLE = (150, 145, 160)    # 原霓虹紫 -> 灰紫 (Boss)
NEON_ORANGE = (185, 150, 120)    # 原霓虹橙 -> 暗沙色 (爆炸)

BG_DEEP = (47, 47, 47)       # 全局背景: 深灰 (参考图取样, 原近黑)
BG_PANEL = (28, 28, 29)      # UI 面板: 比背景更深的黑灰卡片 (反白对比)
BG_GRID = (83, 83, 82)       # 网格线: 浅一号灰 (参考图取样)

TEXT_PRIMARY = (240, 240, 244)   # 主文字: 亮白
TEXT_DIM = (150, 150, 158)   # 次文字: 灰
TEXT_MUTED = (108, 108, 115) # 注释文字: 暗灰 (浅底上调, 保持可读)

ACCENT = (255, 255, 255)    # 极简强调: 纯白 (标题/hover/边框)


class BulletType:
    EGG = "egg"
    MILKY_EGG = "milky_egg"
    KNIFE = "knife"
    BASKETBALL = "basketball"
    CANNON = "cannon"
    MIC = "mic"                # 麦克风弹 (旺仔小乔)
    MELON = "melon"            # 西瓜弹 (华强)
    PARCEL = "parcel"          # 美团外卖箱弹 (袋鼠)


BULLET_CONFIG = {
    BulletType.EGG: {
        "name": "鸡蛋弹",
        "damage": 20,
        "speed": 9,
        "cooldown": 350,
        "radius": 8,
        "color": NEON_YELLOW,
        "pierce": 0,
        "ricochet": 0,
        "image": "鸡蛋.png",
    },
    BulletType.MILKY_EGG: {
        "name": "奶蛋弹",
        "damage": 24,           # 15 → 24 (伤害提升)
        "speed": 7,
        "cooldown": 550,        # 350 → 550 (发射冷却增加)
        "radius": 10,
        "color": (255, 200, 220),
        "pierce": 1,
        "ricochet": 0,
        "image": "奶蛋.png",
    },
    BulletType.KNIFE: {
        "name": "飞刀弹",
        "damage": 56,
        "speed": 14,
        "cooldown": 1150,
        "radius": 6,
        "color": (200, 200, 220),
        "pierce": 0,
        "ricochet": 0,
        "image": "刀.png",
    },
    BulletType.BASKETBALL: {
        "name": "篮球弹",
        "damage": 22,
        "speed": 7,
        "cooldown": 480,
        "radius": 9,
        "color": (255, 140, 0),
        "pierce": 0,
        "ricochet": 3,
        "image": "篮球.png",
    },
    BulletType.CANNON: {
        "name": "炮弹",
        "damage": 28,
        "speed": 6,
        "cooldown": 900,        # 1100 → 900 (发射冷却降低)
        "radius": 7,
        "color": (120, 120, 130),
        "pierce": 0,
        "ricochet": 0,
        "image": "炮弹.png",
    },
    BulletType.MIC: {
        "name": "麦克风弹",
        "damage": 18,
        "speed": 6,
        "cooldown": 700,
        "radius": 9,
        "color": (255, 150, 200),
        "pierce": 0,
        "ricochet": 0,
        "image": "麦克风.png",
        "stun": 0.4,  # 命中眩晕 0.4 秒 (秒)
        "sine": {"freq": 0.05, "amp_deg": 7},  # 正弦波飞行 (声波感)
    },
    BulletType.MELON: {
        "name": "西瓜弹",
        "damage": 30,
        "speed": 5,
        "cooldown": 1000,
        "radius": 11,
        "color": (90, 210, 90),
        "pierce": 0,
        "ricochet": 1,
        "image": "西瓜.png",
        "explode": True,  # 命中时爆炸
    },
    BulletType.PARCEL: {
        "name": "外卖箱弹",
        "damage": 22,
        "speed": 6,
        "cooldown": 900,
        "radius": 10,
        "color": (190, 140, 80),
        "pierce": 0,
        "ricochet": 0,
        "image": "美团外卖箱.png",
        # 范围伤害: 直击 100%, 半径 55px 内其他目标 60%
        "splash": {"radius": 55, "falloff": 0.6},
    },
}


# 坦克颜色配置: 颜色 -> 子弹类型 / 图片 / 语音
class TankColor:
    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"
    BLACK = "black"


TANK_COLOR_CONFIG = {
    TankColor.RED: {
        "name": "小黑子战车",
        "rgb": (255, 40, 50),
        "bullet_type": BulletType.BASKETBALL,
        "top_view": "红色.png",
        "view3d": "红色3D.png",
        "victory_voice": "鸡你太美",
        "defeat_voice": "你干嘛",
        "avatar": "红色坦克车头像.png",
    },
    TankColor.BLUE: {
        "name": "美团袋鼠",
        "rgb": (0, 180, 255),
        "bullet_type": BulletType.EGG,
        "top_view": "蓝色.png",
        "view3d": "蓝色3D.png",
        # 与 Boss4 袋鼠快递王共用语音 (同一角色)
        "victory_voice": "你胆子真是肥嘟嘟的",
        "defeat_voice": "抢生意抢到我头上来了",  # 与文件名 美团袋鼠-抢生意抢到我头上来了.mp3 完全一致
        "avatar": "蓝色坦克车头像 .png",
    },
    TankColor.GREEN: {
        "name": "黑手坦克",
        "rgb": (57, 255, 20),
        "bullet_type": BulletType.KNIFE,
        "top_view": "绿色.png",
        "view3d": "绿色3D.png",
        "victory_voice": "我给你脸",
        "defeat_voice": "你见没见过黑社会",
        "avatar": "绿色坦克车头像.png",
    },
    TankColor.YELLOW: {
        "name": "奶龙坦克",
        "rgb": (255, 242, 0),
        "bullet_type": BulletType.MILKY_EGG,
        "top_view": "黄色.png",
        "view3d": "黄色3D.png",
        "victory_voice": "奶龙哈哈大笑",
        "defeat_voice": "奶龙",
        "avatar": "黄色坦克头像.png",
    },
    TankColor.BLACK: {
        "name": "黑色",
        "rgb": (45, 45, 55),
        "bullet_type": BulletType.CANNON,
        "top_view": "黑色.png",
        "view3d": "黑色3D.png",
        "victory_voice": None,
        "defeat_voice": None,
        "avatar": None,
    },
}

# 可选玩家坦克颜色 (不含黑色)
SELECTABLE_TANK_COLORS = [TankColor.RED, TankColor.BLUE, TankColor.GREEN, TankColor.YELLOW]

# 敌方坦克血量上限: 技能大改后成长曲线变强, 上限上调 40% (45→63)
ENEMY_HP_CAP = 63


class WallType:
    BRICK = "brick"
    STEEL = "steel"
    GRASS = "grass"
    WATER = "water"
    SAND = "sand"                # 沙粒方块: 1 发篮球/炮弹打穿 (hp=22)
    WATER_STAIN = "water_stain"  # 水渍地块: 集群滑行, 无法转向
    CRATE = "crate"              # 木箱: 1 发碎, 15% 掉道具
    GLASS = "glass"              # 玻璃墙: 挡坦克不挡子弹, 1 发碎
    BARREL = "barrel"            # 燃油桶: 1 发碎, 爆炸敌我 40 伤
    MUD = "mud"                  # 泥沼: 移速 x0.6
    ICE = "ice"                  # 冰面: 移速 x1.4 (可控)
    SPIKE = "spike"              # 尖刺: 站立每秒 8 伤
    PORTAL = "portal"            # 传送门: 成对传送 (Boss 关 1 对)


WALL_CONFIG = {
    # 砖块: hp = 56 = 一把飞刀的伤害; 飞刀 1 发打穿, 其余子弹按伤害累计
    WallType.BRICK: {"color": (138, 95, 70), "hp": 56, "bullet_pass": False, "tank_pass": False},
    WallType.STEEL: {"color": (158, 163, 172), "hp": -1, "bullet_pass": False, "tank_pass": False},
    WallType.GRASS: {"color": (38, 72, 44), "hp": -1, "bullet_pass": True, "tank_pass": True, "hide": True},
    WallType.WATER: {"color": (32, 52, 105), "hp": -1, "bullet_pass": True, "tank_pass": False},
    # 沙粒方块: hp = 22 = 一发篮球/炮弹 (轻墙, 只有鸡蛋/奶蛋/麦克风需 2 发)
    WallType.SAND: {"color": (168, 158, 128), "hp": 22, "bullet_pass": False, "tank_pass": False},
    # 水渍地块: 高透明度, 集群出现, 踩上滑行无法转向
    WallType.WATER_STAIN: {"color": (96, 116, 138), "hp": -1, "bullet_pass": True, "tank_pass": True, "slide": True},
    # 木箱: 任意子弹 1 发打碎, 15% 掉道具
    WallType.CRATE: {"color": (120, 88, 52), "hp": 1, "bullet_pass": False, "tank_pass": False, "drop_chance": 0.15},
    # 玻璃墙: 子弹穿过但玻璃碎, 坦克不可过
    WallType.GLASS: {"color": (150, 160, 175), "hp": 1, "bullet_pass": True, "tank_pass": False, "glass": True},
    # 燃油桶: 打碎时爆炸, 半径 55px 敌我双方各 40 伤害
    WallType.BARREL: {"color": (70, 70, 78), "hp": 1, "bullet_pass": False, "tank_pass": False,
                      "boom": {"radius": 55, "damage": 40}},
    # 泥沼: 可通行, 踩上移速 x0.6
    WallType.MUD: {"color": (86, 72, 50), "hp": -1, "bullet_pass": True, "tank_pass": True, "speed_mult": 0.6},
    # 冰面: 可通行, 踩上移速 x1.4 (可控滑行)
    WallType.ICE: {"color": (168, 178, 190), "hp": -1, "bullet_pass": True, "tank_pass": True, "speed_mult": 1.4},
    # 尖刺: 可通行, 站立每秒 60 伤害 (0.5s 一跳 30, 敌我同伤)
    WallType.SPIKE: {"color": (105, 105, 112), "hp": -1, "bullet_pass": True, "tank_pass": True, "spike_dps": 60},
    # 传送门: 成对出现, 坦克传送 (Boss 关 1 对)
    WallType.PORTAL: {"color": (128, 122, 150), "hp": -1, "bullet_pass": True, "tank_pass": True, "portal": True},
}


class EnemyType:
    SCOUT = "scout"
    ARTILLERY = "artillery"
    HEAVY = "heavy"
    GHOST = "ghost"
    ENGINEER = "engineer"
    ELITE = "elite"


# --------------------------------------------------------------
# 剧情模式: 章节结构 + 每关开场剧情台词
# --------------------------------------------------------------
STORY_CHAPTERS = {
    1: "第一章 · 篮球霸王",
    2: "第二章 · 旺仔小乔",
    3: "第三章 · 野生狗奶",
    4: "第四章 · 袋鼠快递",
    5: "第五章 · 华强瓜王",
    6: "终章 · 车轮战",
}


def story_chapter(level):
    return STORY_CHAPTERS.get((level - 1) // 5 + 1, "?")


STORY_LINES = {
    1: "球场灯光未亮, 敌影先至——这是你的第一球。",
    2: "鸡你太美的旋律, 隔着砖墙一遍遍洗脑。",
    3: "敌人学会了一种新战术: 用篮球砸坦克。",
    4: "三分线外, 炮口已对准你的履带。",
    5: "篮球霸王登场: 接球, 还是接炮?",
    6: "红毯铺进战场, 模特们端着麦克风走秀。",
    7: "旺仔小乔的海报贴满墙, 笑容高达 120 分贝。",
    8: "麦克风比炮弹先到, 掌声比爆炸更响。",
    9: "后台练歌声飘来, 调子准得不像话。",
    10: "旺仔小乔登场: T台巡游开始, 请勿挡路。",
    11: "雾里有影子一动不动, 像在等你先开口。",
    12: "没人说得清它是什么, 只知道它不爱说话。",
    13: "四周安静得反常, 子弹都犹豫要不要上膛。",
    14: "传闻: 它的歌, 只有挨一下打才开场。",
    15: "野生狗奶登场: (沉默地看着你)",
    16: "快递箱堆成小山, 每一箱都是\"货到付款\"。",
    17: "袋鼠的跳远纪录: 从地图这头, 到那头。",
    18: "骑手留言: 这单必须送到——哪怕是送到你脸上。",
    19: "口袋里有小费, 也有外卖箱弹幕。",
    20: "袋鼠快递王登场: 你的胆子真是肥嘟嘟的。",
    21: "瓜摊开张, 老板的刀磨得比炮弹还亮。",
    22: "这瓜保熟吗? 老板的眼神回答: 你说呢。",
    23: "瓜雨预警: 局部有大量西瓜, 注意躲避。",
    24: "街坊传言: 惹了卖瓜的, 别想走出这条街。",
    25: "华强瓜王登场: 这瓜保熟, 这刀也保熟。",
    26: "终点的雾里, 五个身影依次亮起。",
    27: "篮球、麦克风、沉默、快递箱、西瓜刀——全来了。",
    28: "最后一战没有观众, 只有你和五段梗。",
    29: "把这一路的梗, 都用炮弹还回去。",
    30: "最终战: 五位首领车轮战, 一个都别想逃。",
}


# 敌方坦克统一为黑色, 统一发射炮弹; 基础血量上调 40% 匹配新技能成长曲线
ENEMY_CONFIG = {
    EnemyType.SCOUT: {
        "name": "侦察兵", "hp": 14, "speed": 2.5, "damage": 15,
        "fire_rate": 1200, "color": (45, 45, 55), "bullet_type": BulletType.CANNON, "sight_range": 350,
    },
    EnemyType.ARTILLERY: {
        "name": "炮兵", "hp": 17, "speed": 1.2, "damage": 35,
        "fire_rate": 2000, "color": (45, 45, 55), "bullet_type": BulletType.CANNON, "sight_range": 600,
        "engage": 900,  # 主动开火距离: 有直视线就远程轰
    },
    EnemyType.HEAVY: {
        "name": "重甲", "hp": 20, "speed": 1.0, "damage": 25,
        "fire_rate": 1400, "color": (45, 45, 55), "bullet_type": BulletType.CANNON, "sight_range": 300,
        "burst": 3,
    },
    EnemyType.GHOST: {
        "name": "幽灵", "hp": 15, "speed": 2.0, "damage": 20,
        "fire_rate": 1100, "color": (45, 45, 55), "bullet_type": BulletType.CANNON, "sight_range": 320, "phase_through_brick": True,
    },
    EnemyType.ENGINEER: {
        "name": "工程师", "hp": 18, "speed": 1.8, "damage": 18,
        "fire_rate": 1500, "color": (45, 45, 55), "bullet_type": BulletType.CANNON, "sight_range": 300, "healer": True,
    },
    EnemyType.ELITE: {
        "name": "精英", "hp": 21, "speed": 1.8, "damage": 30,
        "fire_rate": 900, "color": (45, 45, 55), "bullet_type": BulletType.CANNON, "sight_range": 450,
        "engage": 650,
    },
}
