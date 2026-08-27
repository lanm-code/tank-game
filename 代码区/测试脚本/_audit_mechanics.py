# -*- coding: utf-8 -*-
"""全机制交叉校验: 配置引用完整性 / 数值自洽 / 图鉴与配置一致
- 每项 OK/FAIL, 最终汇总
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402
# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))


pygame.init()
pygame.display.set_mode((64, 64))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.constants import (BULLET_CONFIG, BulletType, TANK_COLOR_CONFIG,  # noqa: E402
                            SELECTABLE_TANK_COLORS, WALL_CONFIG, WallType,
                            ENEMY_CONFIG, EnemyType, STORY_CHAPTERS,
                            STORY_LINES)
from systems.upgrade_system import UPGRADE_POOL, UPGRADE_ICONS, UpgradeIds  # noqa: E402
from entities.boss import BOSS_CONFIG, BossId  # noqa: E402
from entities.pickup import PICKUP_CONFIG, PickupType  # noqa: E402
from ui.codex_data import CODEX, SEEN_MAP, codex_total, TILE_NAMES, TILE_TEXTURES  # noqa: E402

FAILS = []
OKS = []


def check(cond, msg):
    if cond:
        OKS.append(msg)
    else:
        FAILS.append(msg)


# 1. 子弹: 基准锚点 + 特殊效果字段合法
cannon = BULLET_CONFIG[BulletType.CANNON]
check(cannon["damage"] == 28, f"炮弹基准伤害=28, 实际 {cannon['damage']}")
for b, cfg in BULLET_CONFIG.items():
    check(cfg.get("damage", 0) > 0, f"子弹 {b} 伤害>0")
    check(cfg.get("cooldown", 0) > 0, f"子弹 {b} 冷却>0")
    check(cfg.get("speed", 0) > 0, f"子弹 {b} 弹速>0")
    for k in ("pierce", "ricochet", "stun", "splash"):
        if k in cfg:
            check(isinstance(cfg[k], (int, float, dict)), f"子弹 {b} 字段 {k} 类型合法")
check(BULLET_CONFIG[BulletType.KNIFE]["damage"] == 56,
      "飞刀=2×炮弹=56 (锚点关系)")

# 2. 坦克: 4 色可选 + 每色子弹存在
check(len(SELECTABLE_TANK_COLORS) == 4, "可选坦克=4 色")
for c in SELECTABLE_TANK_COLORS:
    cfg = TANK_COLOR_CONFIG[c]
    bt = cfg["bullet_type"]
    check(bt in BULLET_CONFIG, f"坦克 {cfg['name']} 的子弹 {bt} 存在")
    check(cfg.get("victory_voice") is not None or c == "blue",
          f"坦克 {cfg['name']} 胜利语音已配置")

# 3. 墙体: 血量锚点 + 通行标志自洽
check(WALL_CONFIG[WallType.BRICK]["hp"] == 56, "砖块 hp=56=飞刀伤害")
check(WALL_CONFIG[WallType.SAND]["hp"] == 22, "沙粒 hp=22=篮球伤害")
check(WALL_CONFIG[WallType.STEEL]["hp"] == -1, "钢墙 hp=-1 不可摧毁")
for w, cfg in WALL_CONFIG.items():
    check("bullet_pass" in cfg and "tank_pass" in cfg,
          f"墙体 {w} 通行标志齐全")
    check(w in TILE_NAMES, f"墙体 {w} 有图鉴名称")
    check(w in TILE_TEXTURES, f"墙体 {w} 有纹理映射")

# 4. 敌军: 六型配置齐全
for t in [v for k, v in EnemyType.__dict__.items()
          if not k.startswith("_") and isinstance(v, str)]:
    check(t in ENEMY_CONFIG, f"敌军 {t} 有配置")

# 5. 技能池: 26 个 + 稀有度数量 + 逐级效果
real = [u for u in UPGRADE_POOL if u["id"] not in ("residue_dmg", "residue_hp")]
check(len(real) == 26, f"技能池=26, 实际 {len(real)}")
from collections import Counter
rc = Counter(u["rarity"] for u in real)
check(rc["common"] == 9 and rc["rare"] == 5 and rc["epic"] == 6
      and rc["legendary"] == 6,
      f"稀有度分布 普通9/稀有5/史诗6/传说6, 实际 {dict(rc)}")
for u in real:
    check(len(u.get("levels", [])) > 0, f"技能 {u['id']} 有逐级效果")
    check(u["id"] in UPGRADE_ICONS, f"技能 {u['id']} 有图标")
    check(u.get("weight", 0) > 0, f"技能 {u['id']} 有权重")

# 6. 首领: 5 个 + 弹幕子弹存在 + 关卡映射
check(len(BOSS_CONFIG) == 5, f"首领=5, 实际 {len(BOSS_CONFIG)}")
for bid, cfg in BOSS_CONFIG.items():
    bt = cfg.get("bullet_type")
    if bt:
        check(bt in BULLET_CONFIG, f"Boss {cfg['name']} 弹幕子弹存在")
    check(cfg["max_hp"] > 0, f"Boss {cfg['name']} 血量>0")

# 7. 道具: 11 种 + 权重总和 + 奖励/惩罚结构
check(len(PICKUP_CONFIG) == 11, f"道具=11, 实际 {len(PICKUP_CONFIG)}")
wt = sum(v["weight"] for v in PICKUP_CONFIG.values())
check(wt > 0, f"道具权重总和={wt}")
for t, cfg in PICKUP_CONFIG.items():
    check(cfg["kind"] in ("reward", "penalty"), f"道具 {cfg['name']} 类别合法")
    check("symbol" in cfg, f"道具 {cfg['name']} 有符号")

# 8. 剧情: 章节/台词覆盖 1~30
check(len(STORY_CHAPTERS) == 6, "剧情章节=6")
missing_lines = [lv for lv in range(1, 31) if lv not in STORY_LINES]
check(not missing_lines, f"台词 1~30 关全齐, 缺失 {missing_lines}")

# 9. 图鉴: 条目数与分类一致
expected = {"tank": 4, "bullet": 8, "boss": 5, "enemy": 6,
            "skill": 26, "pickup": 11, "tile": 13}
for k, n in expected.items():
    check(len(CODEX[k]) == n, f"图鉴 {k}={n}, 实际 {len(CODEX[k])}")
check(codex_total() == 73, f"图鉴总条目=73, 实际 {codex_total()}")
for kind, keys in SEEN_MAP.items():
    ids = {e["id"] for e in CODEX[kind]}
    check(keys == ids, f"发现表 {kind} 与图鉴条目 id 一致")

# 10. 图鉴数值与配置派生一致 (抽查)
bc = BULLET_CONFIG[BulletType.CANNON]
entry = [e for e in CODEX["bullet"] if e["id"] == BulletType.CANNON][0]
check(("伤害", str(bc["damage"])) in entry["stats"], "图鉴炮弹伤害=配置")
kn = BULLET_CONFIG[BulletType.KNIFE]
w_brick = WALL_CONFIG[WallType.BRICK]["hp"]
check(w_brick == kn["damage"], "砖血=飞刀伤 (图鉴锚点文案成立)")

# 11. 语音文件存在性 (配置引用 → 素材库)
import utils.assets as A
root = A._find_assets_root()
for c in SELECTABLE_TANK_COLORS:
    cfg = TANK_COLOR_CONFIG[c]
    for key in ("victory_voice", "defeat_voice"):
        v = cfg.get(key)
        if not v:
            continue
        folder = "战胜语音" if key == "victory_voice" else "战败语音"
        d = os.path.join(root, folder)
        hit = any(v in f for f in os.listdir(d)) if os.path.isdir(d) else False
        check(hit, f"坦克 {cfg['name']} {key}「{v}」有音频文件")

print(f"\n===== 机制体检: {len(OKS)} OK / {len(FAILS)} FAIL =====")
for f in FAILS:
    print("FAIL:", f)
if FAILS:
    sys.exit(1)
print("ALL MECHANICS CONSISTENT")
