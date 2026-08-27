# -*- coding: utf-8 -*-
"""
全局状态管理
Game State Manager
"""
import json
import os
from enum import Enum
from .constants import *


class GamePhase(Enum):
    MENU = "menu"
    PLAYING = "playing"
    PAUSED = "paused"
    LEVEL_UPGRADE = "level_upgrade"
    GAME_OVER = "gameover"
    VICTORY = "victory"


class GameMode(Enum):
    STORY = "story"
    ENDLESS = "endless"
    BOSS_RUSH = "bossrush"
    COOP = "coop"


SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "savegame.json")


class PlayerData:
    def __init__(self, player_id=1, tank_color=None):
        self.id = player_id
        # 坦克颜色 (红/蓝/绿/黄/黑), P2 默认红色
        self.tank_color = tank_color or (TankColor.RED if player_id == 1 else TankColor.BLUE)
        tc = TANK_COLOR_CONFIG[self.tank_color]
        self.x = 300 if player_id == 1 else SCREEN_WIDTH - 300
        self.y = SCREEN_HEIGHT - 180
        self.angle = -90  # degrees
        self.hp = 100
        self.max_hp = 100
        self.shield = 0
        self.speed = 3.0
        self.base_damage = 20
        self.bullet_type = tc["bullet_type"]
        self.unlocked_bullets = {tc["bullet_type"]}
        self.fire_rate_mult = 1.0
        self.buffs = []              # 已获技能 id 列表 (每次拾取追加一条)
        self.upgrade_levels = {}     # 技能 id -> 当前等级 (Lv1 起)
        self.timed_buffs = {}        # 限时道具效果 {key: {"ms": 剩余毫秒, "mult": 倍率}}
        self.legendary_count = 0     # 本局已获传说技能数 (上限 2)
        self.score = 0
        self.kills = 0
        self.pierce_add = 0
        self.ricochet_add = 0
        self.multi_shot = 1
        self.spread_deg = 10        # 多弹扇形张角 (双发/三发散射逐级设定)
        self.shot_dmg_mult = 1.0    # 分裂弹每发伤害系数 (双发/三发散射)
        self.burst_shots = 1        # 二连击: 一次扳机连发弹数 (1=无连击)
        self.burst_delay = 0        # 二连击: 两弹间隔 (ms)
        self.life_steal = 0.0
        self.shield_chance = 0.0
        self.pickup_magnet = False
        self.magnet_range = 50      # 蛋形磁铁: 道具吸附范围
        self.magnet_global = 0.0    # 蛋形磁铁: 全屏吸附概率
        # 冰霜弹头
        self.frost_slow = 0.0
        self.frost_slow_fire = 0.0  # 命中同时降低敌人攻速的比例
        self.frost_slow_dur = 0
        # 高速弹道
        self.bullet_speed_mult = 1.0
        # 死亡爆破
        self.death_blast_radius = 0
        self.death_blast_ratio = 0.0
        # 静电场
        self.static_interval = 0
        self.static_ratio = 0.0
        self.static_timer = 0
        # 不屈意志 (每关重置)
        self.last_stand_invuln = 0
        self.last_stand_used = False
        # 狙击之眼
        self.dead_eye_mult = 1.0
        # 传说: 幻影军团 / 时间静止 / 末日核弹 (计时器)
        self.phantom_timer = 0
        self.chrono_timer = 0
        self.doomsday_timer = 0
        # 不死凤凰 (每关重置)
        self.phoenix_used = False
        self.color = tc["rgb"]
        self.invincible = False  # 运行时无敌 (由 god_mode 驱动)


class WaveState:
    def __init__(self):
        self.current = 1
        self.total_waves = 5
        self.enemies_spawned = 0
        self.enemies_killed = 0
        self.enemies_total = 8
        self.spawn_timer = 0
        self.spawn_interval = 2000


class GameState:
    def __init__(self):
        self.phase = GamePhase.MENU
        self.mode = GameMode.STORY
        self.level = 1
        self.max_unlocked_level = 1
        self.high_score = 0
        self.players = []
        self.wave = WaveState()
        self.boss = None
        self.base_hp = 100
        self.base_max_hp = 100
        self.shake = {"magnitude": 0.0, "duration": 0.0}
        self.level_upgrade_choices = []
        self.combo = 0
        self.combo_timer = 0
        self.selected_tank_color = TankColor.RED  # 菜单选择的玩家坦克颜色
        self.god_mode = False  # 无敌模式
        self.aim_mode = "manual"  # 手机瞄准模式: manual=右轮盘手动 / auto=自动锁敌
        self.codex_seen = {}   # 图鉴发现记录: {kind: {key: True}} (kind: tank/bullet/boss/enemy/skill/pickup/tile)
        self.load()

    def mark_codex_seen(self, kind, key):
        """图鉴发现点亮 (存档持久化)"""
        if not key:
            return
        self.codex_seen.setdefault(kind, {})[key] = True

    def codex_seen_count(self, total_map=None):
        """已收录条目数; total_map 为 {kind: 条目 id 集合}, 传 None 时直接数已见"""
        n = 0
        if total_map is None:
            for d in self.codex_seen.values():
                n += len(d)
            return n
        for kind, keys in total_map.items():
            seen = self.codex_seen.get(kind, {})
            for k in keys:
                if seen.get(k):
                    n += 1
        return n

    def new_game(self, mode=GameMode.STORY, level=1):
        self.phase = GamePhase.PLAYING
        self.mode = mode
        self.level = level
        self.wave = WaveState()
        self.boss = None
        self.base_hp = 100
        self.shake = {"magnitude": 0.0, "duration": 0.0}
        self.combo = 0
        self.combo_timer = 0
        self.players = []
        p1 = PlayerData(1, self.selected_tank_color)
        p1.invincible = self.god_mode
        self.players.append(p1)
        if mode == GameMode.COOP:
            # 合作模式 P2 用蓝色 (若 P1 已选蓝色则用红色)
            p2_color = TankColor.BLUE if self.selected_tank_color != TankColor.BLUE else TankColor.RED
            p2 = PlayerData(2, p2_color)
            p2.invincible = self.god_mode
            self.players.append(p2)

    def trigger_shake(self, magnitude, duration_ms):
        self.shake["magnitude"] = max(self.shake["magnitude"], magnitude)
        self.shake["duration"] = max(self.shake["duration"], duration_ms)

    def update_shake(self, dt):
        if self.shake["duration"] > 0:
            self.shake["duration"] -= dt
            if self.shake["duration"] <= 0:
                self.shake["magnitude"] = 0
                self.shake["duration"] = 0

    def add_combo(self):
        self.combo += 1
        self.combo_timer = 3000
        if self.combo >= 10 and self.combo % 5 == 0:
            return True
        return False

    def update_combo(self, dt):
        if self.combo_timer > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo = 0

    def save(self):
        data = {
            "high_score": self.high_score,
            "max_unlocked_level": self.max_unlocked_level,
            "codex_seen": self.codex_seen,
        }
        try:
            with open(SAVE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception:
            pass

    def load(self):
        try:
            if os.path.exists(SAVE_PATH):
                with open(SAVE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.high_score = data.get("high_score", 0)
                self.max_unlocked_level = data.get("max_unlocked_level", 1)
                self.codex_seen = data.get("codex_seen", {}) or {}
        except Exception:
            pass
