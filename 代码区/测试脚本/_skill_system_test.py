# -*- coding: utf-8 -*-
"""技能系统专项测试 (27技能大改版):
池完整性 / 逐级效果 / 互斥 / 满级 / 新机制 (冰霜/高速/轨道炮/不屈/狂战士/传说计时器)"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, r"C:\Users\Lenovo\Desktop\tank game\代码区")
import pygame

# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

pygame.init()
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
except Exception:
    pass

from core.constants import (BulletType, EnemyType, MAP_COLS, MAP_ROWS,
                             TILE_SIZE, WALL_CONFIG)
from core.game_state import (GameState, GameMode, GamePhase, PlayerData,
                             TankColor)
from core.game import Game
from ui.menu_controller import MenuController
from systems.map_system import MapGenerator
from entities.bullet import Bullet
from entities.pickup import Pickup
from systems.ai_system import EnemyTank
from entities.boss import Boss, BossId
from systems.upgrade_system import (UpgradeSystem, UPGRADE_POOL, UPGRADE_ICONS,
                                    UpgradeIds)

fails = []


def check(cond, msg):
    print(("  [PASS] " if cond else "  [FAIL] ") + msg)
    if not cond:
        fails.append(msg)


us = UpgradeSystem()
pool = {u["id"]: u for u in UPGRADE_POOL}

print("== 1. 池完整性 ==")
ids = [u["id"] for u in UPGRADE_POOL]
names = [u["name"] for u in UPGRADE_POOL]
check(len(ids) == len(set(ids)), f"技能 id 无重复 (共 {len(ids)} 个)")
check(len(names) == len(set(names)), "技能名称无重复")
check(set(ids) <= set(UPGRADE_ICONS), "每个技能都有图标符号")
check(all(len(u["levels"]) > 0 for u in UPGRADE_POOL), "每个技能都有逐级效果表")
common = sum(1 for u in UPGRADE_POOL if u["rarity"] == "common")
rare = sum(1 for u in UPGRADE_POOL if u["rarity"] == "rare")
epic = sum(1 for u in UPGRADE_POOL if u["rarity"] == "epic")
legend = sum(1 for u in UPGRADE_POOL if u["rarity"] == "legendary")
check(common == 9, f"普通技能 9 个 (实际 {common})")
check(rare == 5, f"稀有技能 5 个 (实际 {rare})")
check(epic == 6, f"史诗技能 6 个 (实际 {epic})")
check(legend == 6, f"传说技能 6 个 (实际 {legend})")

print("== 2. 技能强化不改变子弹类型 ==")
p = PlayerData(1, TankColor.BLUE)
bt = p.bullet_type
for u in UPGRADE_POOL:
    for lv in range(1, len(u["levels"]) + 1):
        us.apply_upgrade(p, u)
check(p.bullet_type == bt, "全技能逐级应用后子弹类型不变 (袋鼠坦克=鸡蛋弹)")

print("== 3. 逐级效果 ==")
# 双发射击 = 二连击: Lv1 每发60%, Lv2 70%, Lv3 85%, Lv4 恢复100% (均 2 连发, 间隔 130ms)
p1 = PlayerData(1, TankColor.RED)
us.apply_upgrade(p1, pool[UpgradeIds.DOUBLE_SHOT])
check(p1.burst_shots == 2 and p1.burst_delay == 130
      and p1.multi_shot == 1 and p1.shot_dmg_mult == 0.60,
      "双发 Lv1: 二连击 每发60%")
us.apply_upgrade(p1, pool[UpgradeIds.DOUBLE_SHOT])
check(p1.burst_shots == 2 and p1.shot_dmg_mult == 0.70,
      "双发 Lv2: 二连击 每发70%")
us.apply_upgrade(p1, pool[UpgradeIds.DOUBLE_SHOT])
check(p1.burst_shots == 2 and p1.shot_dmg_mult == 0.85,
      "双发 Lv3: 二连击 每发85%")
us.apply_upgrade(p1, pool[UpgradeIds.DOUBLE_SHOT])
check(p1.burst_shots == 2 and p1.shot_dmg_mult == 1.0,
      "双发 Lv4: 二连击 每发100% (恢复满伤害)")
check(p1.upgrade_levels[UpgradeIds.DOUBLE_SHOT] == 4, "等级记录 = Lv4")
us.apply_upgrade(p1, pool[UpgradeIds.DOUBLE_SHOT])  # 超上限
check(p1.upgrade_levels[UpgradeIds.DOUBLE_SHOT] == 4, "满级后再应用无效果")
# 满级卡带 MAX 标记
cards_p1 = us.available_upgrades(p1, 3, level=1)
check(all(c["id"] != UpgradeIds.DOUBLE_SHOT for c in cards_p1),
      "满级技能不再出现在技能列表")
p1b = PlayerData(1, TankColor.RED)
us.apply_upgrade(p1b, pool[UpgradeIds.RAILGUN])  # 传说 1 级 = 满级
for _ in range(30):
    cs = us.available_upgrades(p1b, 3, level=25)
    check(all(c["id"] != UpgradeIds.RAILGUN for c in cs), "传说满级后也不出现")
p1c = PlayerData(1, TankColor.RED)
for _ in range(3):
    us.apply_upgrade(p1c, pool[UpgradeIds.PIERCE])
cs = us.available_upgrades(p1c, 3, level=1)
found = [c for c in cs if c["id"] == UpgradeIds.PIERCE]
if found:
    check(found[0]["is_max"] and found[0]["next_level"] == 4,
          "升级到满级的卡片带 is_max 标记 (Lv4 MAX)")
# 互斥: 拿了双发 → 三发散射不出现
cards = us.available_upgrades(p1, 3)
check(all(c["id"] != UpgradeIds.TRIPLE_SHOT for c in cards), "互斥: 双发与三发散射不共存")
# 三发散射
p2 = PlayerData(1, TankColor.RED)
us.apply_upgrade(p2, pool[UpgradeIds.TRIPLE_SHOT])
check(p2.multi_shot == 3 and p2.spread_deg == 10 and p2.shot_dmg_mult == 0.65,
      "三发 Lv1: 3发 ±10° 每发65%")
us.apply_upgrade(p2, pool[UpgradeIds.TRIPLE_SHOT])
check(p2.multi_shot == 4 and p2.spread_deg == 12 and p2.shot_dmg_mult == 0.60,
      "三发 Lv2: 4发 ±12° 每发60%")
us.apply_upgrade(p2, pool[UpgradeIds.TRIPLE_SHOT])
check(p2.multi_shot == 5 and p2.spread_deg == 14 and p2.shot_dmg_mult == 0.55,
      "三发 Lv3: 5发 ±14° 每发55%")
# 弹射 +2/4/6
p2b = PlayerData(1, TankColor.RED)
us.apply_upgrade(p2b, pool[UpgradeIds.RICOCHET])
check(p2b.ricochet_add == 2, "弹射 Lv1: +2")
us.apply_upgrade(p2b, pool[UpgradeIds.RICOCHET])
check(p2b.ricochet_add == 4, "弹射 Lv2: +4")
us.apply_upgrade(p2b, pool[UpgradeIds.RICOCHET])
check(p2b.ricochet_add == 6, "弹射 Lv3: +6")
# 冰霜/加速弹头/护盾/吸血/狙击
p3 = PlayerData(1, TankColor.RED)
us.apply_upgrade(p3, pool[UpgradeIds.FROST_ROUNDS])
check(p3.frost_slow == 0.15 and p3.frost_slow_fire == 0.15
      and p3.frost_slow_dur == 2500, "冰霜 Lv1: 减速+降攻速 15%/2.5s")
us.apply_upgrade(p3, pool[UpgradeIds.FROST_ROUNDS])
us.apply_upgrade(p3, pool[UpgradeIds.FROST_ROUNDS])
check(p3.frost_slow == 0.35 and p3.frost_slow_fire == 0.35
      and p3.frost_slow_dur == 3500, "冰霜 Lv3: 减速+降攻速 35%/3.5s")
bd0 = p3.base_damage
us.apply_upgrade(p3, pool[UpgradeIds.VELOCITY_ROUNDS])
check(p3.bullet_speed_mult == 1.3 and p3.base_damage == bd0 + 10,
      "加速弹头 Lv1: 弹速×1.3 伤害+10")
us.apply_upgrade(p3, pool[UpgradeIds.SHIELD_CHANCE])
check(p3.shield_chance == 0.20, "护盾 Lv1: 20% 免疫")
us.apply_upgrade(p3, pool[UpgradeIds.SHIELD_CHANCE])
check(p3.shield_chance == 0.30, "护盾 Lv2: 30% 免疫")
us.apply_upgrade(p3, pool[UpgradeIds.VAMPIRE])
check(p3.life_steal == 0.12, "吸血 Lv1: 12%")
us.apply_upgrade(p3, pool[UpgradeIds.VAMPIRE])
check(p3.life_steal == 0.20, "吸血 Lv2: 20%")
us.apply_upgrade(p3, pool[UpgradeIds.DEAD_EYE])
check(p3.dead_eye_mult == 1.8, "狙击 Lv1: 血量≥70% 敌人 +80%")
us.apply_upgrade(p3, pool[UpgradeIds.DEAD_EYE])
check(p3.dead_eye_mult == 2.5, "狙击 Lv2: 血量≥70% 敌人 +150%")
# 磁铁
p4 = PlayerData(1, TankColor.RED)
us.apply_upgrade(p4, pool[UpgradeIds.MAGNET])
check(p4.magnet_range == 80 and p4.magnet_global == 0.0, "磁铁 Lv1: 范围80")
for _ in range(3):
    us.apply_upgrade(p4, pool[UpgradeIds.MAGNET])
check(p4.magnet_range == 200 and p4.magnet_global == 0.8, "磁铁 Lv4: 范围200 + 全屏80%")

print("== 4. 子弹参数 ==")
b2 = Bullet(100, 100, 0, BulletType.EGG, 1, speed_mult=1.0)
b3 = Bullet(100, 100, 0, BulletType.EGG, 1, speed_mult=1.9)
check(b3.speed == b2.speed * 1.9, "高速弹道: 子弹速度 ×1.9")
b1 = Bullet(100, 100, 0, BulletType.EGG, 1, damage_mult=1.0,
            speed_mult=1.0, slow_add=0.35, slow_dur=3500)
check(b1.slow > 0 and b1.slow_dur == 3500, "冰霜弹头: 子弹带减速+3.5s时长")
b4 = Bullet(100, 100, 0, BulletType.KNIFE, 1, damage_mult=1.0,
            pierce_add=6, railgun=True)
check(b4.pierce == 6, f"轨道炮: 穿透+6 (实际 {b4.pierce})")

print("== 5. 游戏内机制 (无头) ==")
screen = pygame.display.set_mode((960, 540))
gs = GameState()
game = Game(screen, gs)
gs.new_game(GameMode.STORY, level=1)
game.start_level(1)
pd = gs.players[0]
pt = game.player_tanks[0]

# 不屈意志
us.apply_upgrade(pd, pool[UpgradeIds.LAST_STAND])
pt.invuln_timer = 0  # 出生自带 1.5s 无敌帧, 清零后再测
pt.hp = 10
pt.take_damage(9999)
check(not pt.dead and pt.hp == 1 and pd.last_stand_used, "不屈意志: 致命伤保 1 血")
check(pt.invuln_timer >= 2500, "不屈意志: 附带 2.5s 无敌")
pt.invuln_timer = 0
pt.take_damage(9999)
check(pt.dead, "不屈意志用过后再次致命 → 死亡")

# 不死凤凰
gs2 = GameState()
game2 = Game(screen, gs2)
gs2.new_game(GameMode.STORY, level=1)
game2.start_level(1)
pd2 = gs2.players[0]
pt2 = game2.player_tanks[0]
us.apply_upgrade(pd2, pool[UpgradeIds.PHOENIX])
pt2.hp = 0
pt2.dead = True
game2._check_end_conditions()
check(not pt2.dead and pt2.hp == int(pd2.max_hp * 0.5), "不死凤凰: 原地复活 50% 血")
check(pd2.phoenix_used, "不死凤凰: 复活次数已用")
check(gs2.phase == GamePhase.PLAYING, "复活后游戏继续")
pt2.dead = True
game2._check_end_conditions()
check(gs2.phase == GamePhase.GAME_OVER, "第二次死亡 → 游戏结束")

# 能量护盾实际生效: shield_chance=1.0 → 受击免疫 + 0.5s 无敌帧
pd_shield = PlayerData(1, TankColor.RED)
pd_shield.shield_chance = 1.0
pt_shield = game.player_tanks[0]
pt_shield.data = pd_shield
pt_shield.dead = False
pt_shield.invuln_timer = 0
pt_shield.hp = 100
pt_shield.take_damage(30)
check(pt_shield.hp == 100 and pt_shield.invuln_timer >= 500,
      "能量护盾: 格挡成功不掉血 + 0.5s 无敌帧")
pt_shield.data = pd  # 还原, 供后续狂战士/轨道炮测试使用
# 冰霜降攻速: slow_fire 命中后敌人攻速乘区上升
et_frost = EnemyTank(400, 400, EnemyType.SCOUT, level=1)
et_frost.take_damage(1, slow=0.25, slow_fire=0.25)
check(et_frost.slow_fire_mult >= 1.25 and et_frost.slow_mult <= 0.75,
      "冰霜弹头: 命中后减速 + 降攻速同时生效")
et_frost.update_base(3000)
check(et_frost.slow_fire_mult == 1.0, "减速结束后攻速恢复")
# 狂战士: 低血量伤害提升
pd.hp = 50  # 半血
pd.max_hp = 100
us.apply_upgrade(pd, pool[UpgradeIds.BERSERK])
pt.hp = 50
pt.max_hp = 100
base_mult = pd.base_damage / 20.0
berserk_mult = pt._combat_damage_mult()
check(berserk_mult > base_mult, f"狂战士: 半血伤害提升 (倍率 {berserk_mult:.2f} > {base_mult:.2f})")
pt.hp = 100
full_mult = pt._combat_damage_mult()
check(abs(full_mult - base_mult) < 0.01, "狂战士: 满血无加成")
us.apply_upgrade(pd, pool[UpgradeIds.RAILGUN])
rail_mult = pt._combat_damage_mult()
check(rail_mult > full_mult, "轨道炮: 伤害 ×1.8")

# 传说计时器机制 (时间静止/末日核弹/幻影军团/静电场)
game.bullets.clear()
gs3 = GameState()
game3 = Game(screen, gs3)
gs3.new_game(GameMode.STORY, level=1)
game3.start_level(1)
pd3 = gs3.players[0]
for uid in (UpgradeIds.CHRONO_FIELD, UpgradeIds.DOOMSDAY, UpgradeIds.PHANTOM_DUO,
            UpgradeIds.STATIC_FIELD):
    us.apply_upgrade(pd3, pool[uid])
us.apply_upgrade(pd3, pool[UpgradeIds.DOUBLE_SHOT])  # 二连击: 幻影应复制 2 发弹幕 (burst_shots=2)
et = EnemyTank(500, 500, EnemyType.SCOUT, level=1)
game3.enemy_tanks.append(et)
pd3.chrono_timer = 1
pd3.doomsday_timer = 1
pd3.static_timer = 1
pd3.phantom_timer = 1
game3._update_skill_effects(16.7)
check(et.slow_mult <= 0.10 and et.slow_timer >= 4983, "时间静止: 敌人减速 90% (5s)")
check(et.stun_timer >= 1400, "时间静止: 敌人眩晕 1.5 秒")
check(et.hp < et.max_hp, "末日核弹: 敌人受到 500% 伤害")
check(len(game3.bullets) == 2, f"幻影军团: 镜像复制玩家弹幕 (二连击 burst_shots=2 → {len(game3.bullets)} 发)")
check(pd3.static_interval > 0 and pd3.static_timer > 0, "静电场: 计时器重置")
check(pd3.static_interval == 6000, "静电场: 周期 6 秒")

# 二连击实弹验证: 一次扳机首发 1 发, 到点补射第 2 发 (同方向, 伤害带 shot_dmg_mult)
pt3 = game3.player_tanks[0]
pt3.data.burst_shots = 2
pt3.data.burst_delay = 130
pt3.data.shot_dmg_mult = 0.6
pt3.data.multi_shot = 1
pt3.turret_angle = 0
pt3.fire_cooldown = 0
n0 = len(game3.bullets)
fired = pt3.fire(game3.bullets, pt3.player_id,
                 damage_mult=pt3._combat_damage_mult() * pt3.data.shot_dmg_mult,
                 multi_shot=1, spread_deg=0)
check(len(fired) == 1 and len(game3.bullets) == n0 + 1, "二连击: 首发 1 发")
pt3._burst_left = 1
pt3._burst_timer = 130
pt3._burst_angle = 0
pt3._fire_burst(game3.bullets, None)
check(len(game3.bullets) == n0 + 2, "二连击: 到点补射第 2 发 (同方向)")
check(game3.bullets[n0].angle == game3.bullets[n0 + 1].angle,
      "二连击: 两发同方向 (非扇形)")
game3.bullets.clear()

# 死亡爆破
game3.enemy_tanks.clear()
e1 = EnemyTank(400, 400, EnemyType.SCOUT, level=1)
e2 = EnemyTank(450, 400, EnemyType.SCOUT, level=1)
game3.enemy_tanks.extend([e1, e2])
us.apply_upgrade(pd3, pool[UpgradeIds.DEATH_BLAST])
hp2_before = e2.hp
e1.dead = True
game3._on_enemy_killed(e1, pd3.id)
check(e2.hp < hp2_before, "死亡爆破: 击杀后周围敌人受伤")

print("== 6. 抽卡规则 (1新/2升级/3随机) ==")
p6 = PlayerData(1, TankColor.RED)
# 先拥有 3 个未满级技能 (升级池非空)
for uid in (UpgradeIds.PIERCE, UpgradeIds.ARMOR, UpgradeIds.RAPID_FIRE):
    us.apply_upgrade(p6, pool[uid])
ok1 = ok2 = ok3 = True
for _ in range(500):
    cs = us.available_upgrades(p6, 3, level=3)
    if cs[0]["next_level"] != 1 or cs[0]["id"] in p6.upgrade_levels:
        ok1 = False
    if cs[1]["next_level"] <= 1:
        ok2 = False
    if len({c["id"] for c in cs}) != 3:
        ok3 = False
check(ok1, "第 1 张永远是未拥有的新技能 (Lv1)")
check(ok2, "第 2 张永远是升级卡 (有未满级技能时)")
check(ok3, "三张卡不重复同一技能")

# 升级池为空 → 第 2 张补新技能
p6b = PlayerData(1, TankColor.RED)
ok4 = True
for _ in range(200):
    cs = us.available_upgrades(p6b, 3, level=3)
    if any(c["next_level"] != 1 for c in cs):
        ok4 = False
check(ok4, "无已拥有技能时, 三张全是新技能")

# 全部满级 → 残卡兜底
p6c = PlayerData(1, TankColor.RED)
for u in UPGRADE_POOL:
    p6c.upgrade_levels[u["id"]] = len(u["levels"])
cs = us.available_upgrades(p6c, 3, level=30)
check(all(c["id"].startswith("residue_") for c in cs) and len(cs) == 3,
      "卡池枯竭 → 属性残卡兜底 (3 张)")

print("== 7. 传说门槛 ==")
p7 = PlayerData(1, TankColor.RED)
ok5 = True
for _ in range(500):
    cs = us.available_upgrades(p7, 3, level=9)
    if any(c["rarity"] == "legendary" for c in cs):
        ok5 = False
check(ok5, "第 9 关: 传说不入池")
p7b = PlayerData(1, TankColor.RED)
p7b.legendary_count = 2
ok6 = True
for _ in range(500):
    cs = us.available_upgrades(p7b, 3, level=25)
    if any(c["rarity"] == "legendary" for c in cs):
        ok6 = False
check(ok6, "每局最多 2 个传说 (拿满后不再出现)")
p7c = PlayerData(1, TankColor.RED)
us.apply_upgrade(p7c, pool[UpgradeIds.RAILGUN])
us.apply_upgrade(p7c, pool[UpgradeIds.DOOMSDAY])
check(p7c.legendary_count == 2, "传说计数正确 (=2)")

print("== 8. 无尽模式 (Boss 循环 / 成长 / 100关上限 / 敌人深层成长) ==")
for lvl, expect in [(5, BossId.BOSS_1), (25, BossId.BOSS_5),
                    (30, BossId.BOSS_1), (55, BossId.BOSS_1),
                    (100, BossId.BOSS_5)]:
    gsE = GameState()
    gameE = Game(screen, gsE)
    gsE.mode = GameMode.ENDLESS
    gameE._spawn_boss(lvl)
    check(gameE.gs.boss.boss_id == expect, f"无尽 Boss 循环: 第{lvl}关 = {expect}")
    gameE.audio.stop_bgm()
# 无尽成长: 第100关 B5 血量 = 2520 × (1 + 99×0.2)
gsE2 = GameState()
gameE2 = Game(screen, gsE2)
gsE2.mode = GameMode.ENDLESS
gameE2._spawn_boss(100)
expect_hp = int(2520 * (1 + 99 * 0.20))
check(gameE2.gs.boss.hp == expect_hp,
      f"无尽 Boss 血量随关卡增长 (第100关 = {expect_hp})")
check(gameE2.gs.boss.dmg_mult > 1.0, "无尽 Boss 弹幕伤害随关卡增长")
gameE2.audio.stop_bgm()
# 100 关上限
gsE3 = GameState()
gameE3 = Game(screen, gsE3)
gsE3.mode = GameMode.ENDLESS
gsE3.level = 100
gameE3._on_upgrade_confirmed()
check(gsE3.phase == GamePhase.VICTORY, "无尽 100 关上限: 通关胜利")
# 敌人深层成长 (剧情≤30 不受影响)
e30 = EnemyTank(400, 400, EnemyType.SCOUT, level=30)
e60 = EnemyTank(400, 400, EnemyType.SCOUT, level=60)
e100 = EnemyTank(400, 400, EnemyType.SCOUT, level=100)
check(e30.dmg_mult == 1.0, "30 关及以下敌人伤害不变 (剧情不受影响)")
check(e60.max_hp > e30.max_hp and e100.max_hp > e60.max_hp,
      "无尽敌人血量随关卡持续增长")
check(e60.dmg_mult > 1.0 and e100.dmg_mult > e60.dmg_mult,
      "无尽敌人伤害随关卡持续增长")
# 残卡简化: 只有伤害/生命两种
from systems.upgrade_system import RESIDUE_POOL
check([r["id"] for r in RESIDUE_POOL] == ["residue_dmg", "residue_hp"],
      "残卡只有伤害+5 / 生命+20 两种最基础加成")

print("== 9. 剧情模式特色 (章节 / 开场台词 / 终章车轮战 / 通关标记) ==")
from core.constants import story_chapter, STORY_LINES
check(story_chapter(1) == "第一章 · 篮球霸王", "章节映射: 第1关 = 第一章·篮球霸王")
check(story_chapter(15) == "第三章 · 野生狗奶", "章节映射: 第15关 = 第三章·野生狗奶")
check(story_chapter(30) == "终章 · 车轮战", "章节映射: 第30关 = 终章·车轮战")
# 开场台词条
gsS = GameState()
gameS = Game(screen, gsS)
gsS.new_game(GameMode.STORY, level=3)
gameS.start_level(3)
check(gameS._story_banner is not None
      and gameS._story_banner["line"] == STORY_LINES[3],
      "剧情模式: 开局显示第3关台词")
for _ in range(300):
    gameS.update()
check(gameS._story_banner is None, "台词条 4 秒后消失")
# 无尽模式无台词条
gsN = GameState()
gameN = Game(screen, gsN)
gsN.new_game(GameMode.ENDLESS, level=2)
gameN.start_level(2)
check(gameN._story_banner is None, "无尽模式不显示剧情台词")
gameN.audio.stop_bgm()
# 终章车轮战: 第30关依次 B1→B2→B3→B4→B5
gsF = GameState()
gameF = Game(screen, gsF)
gsF.new_game(GameMode.STORY, level=30)
gameF.start_level(30)
order = []
ok_names = True
for i in range(5):
    b = gameF.gs.boss
    if b is None or not b.name.startswith(f"最终战 {i + 1}/5"):
        ok_names = False
    order.append(getattr(b, "boss_id", None))
    b.take_damage(99999)
    gameF._update_playing(16.666)
check(order == [BossId.BOSS_1, BossId.BOSS_2, BossId.BOSS_3,
                BossId.BOSS_4, BossId.BOSS_5],
      f"车轮战顺序 B1→B5 (实际 {order})")
check(ok_names, "车轮战 Boss 名字带 '最终战 i/5' 前缀")
check(gsF.phase == GamePhase.LEVEL_UPGRADE, "5 位首领全部击败后进入结算")
check("剧情通关" in gameF._result_stats[0][1], "通关标记: 关卡 30 · 剧情通关!")

print("== 10. Boss Rush 五连通关 ==")
gsB = GameState()
gameB = Game(screen, gsB)
gsB.new_game(GameMode.BOSS_RUSH, level=25)
gsB.level = 25
gameB._end_level(True)
check("Boss Rush 通关" in gameB._result_stats[0][1], "通关标记: 关卡 25 · Boss Rush 通关!")
gameB._on_upgrade_confirmed()
check(gsB.phase == GamePhase.VICTORY, "打完第五个 Boss 确认后 → 胜利")
gameB._handle_result_continue()
check(gsB.phase == GamePhase.MENU, "胜利页继续 → 回主菜单 (不再开第30关)")
# 第 20 关 (B4): 继续进入第 25 关
gsB2 = GameState()
gameB2 = Game(screen, gsB2)
gsB2.new_game(GameMode.BOSS_RUSH, level=20)
gsB2.level = 20
gameB2._on_upgrade_confirmed()
check(gsB2.phase == GamePhase.PLAYING and gsB2.level == 25,
      "打完 B4 (20关) 继续 → 进入第 25 关")
gameB2.audio.stop_bgm()

print("== 11. 波次系统 (十位数+1 波数 / 空白处刷敌) ==")
from systems.wave_system import WaveSystem
ws = WaveSystem(MAP_COLS, MAP_ROWS)
for lvl, exp in [(3, 1), (9, 1), (10, 2), (19, 2), (25, 3), (47, 5),
                 (55, 5), (100, 5)]:
    check(ws.wave_count(lvl) == exp, f"波数=十位数+1: 第{lvl}关 = {exp} 波")
info = ws.level_wave_info(24, GameMode.STORY)
check(info["waves"] == 3 and info["enemies_per_wave"] == 14,
      "剧情第24关 = 3 波 × 14 敌")
info = ws.level_wave_info(100, GameMode.ENDLESS)
check(info["waves"] == 5, "无尽第100关 = 5 波 (封顶)")
# 空白处刷敌: 刷敌点不落在墙内/不出现在玩家出生区
gsW = GameState()
gameW = Game(screen, gsW)
gsW.new_game(GameMode.STORY, level=7)
gameW.start_level(7)
ok_spawn = True
for _ in range(30):
    x, y = gameW.wave_sys.pick_spawn_point([], gameW.walls, TILE_SIZE)
    if y > (MAP_ROWS - 4) * TILE_SIZE:
        ok_spawn = False
    for w in gameW.walls:
        wc = WALL_CONFIG[w.type]
        if wc.get("tank_pass"):
            continue
        if pygame.Rect(w.x, w.y, w.width, w.height).collidepoint(x, y):
            ok_spawn = False
check(ok_spawn, "刷敌点在地图空白处 (不重叠墙体/不出生区)")
gameW.audio.stop_bgm()

print("== 12. 升级页鼠标点击 / 草丛生成 ==")
# 鼠标点击第 2 张卡应正确选择第 2 张 (旧 bug: 点不中 → 默认选第 1 张)
gsC = GameState()
gameC = Game(screen, gsC)
menuC = MenuController(screen, gsC, gameC)
gsC.new_game(GameMode.STORY, level=1)
gameC.start_level(1)
choices = gameC.upgrade_sys.available_upgrades(gsC.players[0], 3, level=1)
gsC.level_upgrade_choices = choices
gsC.phase = GamePhase.LEVEL_UPGRADE
menuC.mode = "upgrade"
card0_id, card2_id = choices[0]["id"], choices[1]["id"]
# 打桩鼠标坐标: 内部分辨率下第 2 张卡中心 (830+130, 420+160)
menuC._window_to_internal = lambda *a: (960, 580)
ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(480, 290))
menuC.handle_event(ev)
check(gsC.players[0].upgrade_levels.get(card2_id) == 1,
      f"鼠标点击第 2 张卡 → 正确选中 ({card2_id} Lv1)")
check(gsC.players[0].upgrade_levels.get(card0_id, 0) == 0,
      "不再误选第 1 张卡")
# 草丛可通行: 生成地图无重叠方块 (草丛不再叠在砖墙上)
mg = MapGenerator(MAP_COLS, MAP_ROWS)
ok_map = True
for lvl in range(1, 8):
    ws2, _ = mg.generate_level(lvl)
    cells = [(w.col, w.row) for w in ws2]
    if len(cells) != len(set(cells)):
        ok_map = False
        break
check(ok_map, "地图无重叠方块 (草丛不会叠砖墙, 可正常进入)")

print()
print("ALL PASS" if not fails else f"FAILED: {len(fails)} 项")
for f in fails:
    print("  FAIL:", f)
pygame.quit()
sys.exit(0 if not fails else 1)
