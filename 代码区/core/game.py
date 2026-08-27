# -*- coding: utf-8 -*-
"""
核心游戏控制器 Game
"""
import math
import random
import pygame

from core.constants import *
from core.game_state import GamePhase, GameMode
from core.input import InputManager
from core.event_bus import EventBus
from utils.math_utils import (dist, random_choice_weighted,
                               circle_rect_overlap, angle_between)

from entities.tank import PlayerTank
from systems.ai_system import EnemyTank
from entities.bullet import Bullet
from entities.pickup import (Pickup, PICKUP_CONFIG, PickupType,
                             PICKUP_MAX_ON_FIELD)
from entities.particle import (
    Particle, spawn_explosion, spawn_hit_spark
)
from entities.boss import Boss, BossId, BOSS_CONFIG
from entities.wall import Wall

from systems.map_system import MapGenerator
from systems.wave_system import WaveSystem
from systems.upgrade_system import UpgradeSystem
from systems.audio_system import AudioSystem

from ui.hud_controller import HUDRenderer
from ui.menu_controller import ResultOverlay
from utils.fonts import load_font


class Game:
    def __init__(self, screen, game_state):
        self.screen = screen
        self.gs = game_state
        # 内部分辨率 surface (游戏逻辑始终渲染到此)
        self._internal_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        # 当前窗口大小 (用于缩放)
        self._display_w = screen.get_width()
        self._display_h = screen.get_height()
        self.input = InputManager()
        # 虚拟触控层 (手机版玩法): 包装输入 + 虚拟瞄准点, 核心逻辑零改动
        from ui.touch_controls import TouchControls, CombinedInput
        self.touch = TouchControls(screen, game_state)
        self.input = CombinedInput(self.input, self.touch)
        self.event_bus = EventBus()
        self.player_tanks = []
        self.enemy_tanks = []
        self.walls = []
        self.bullets = []
        self.pickups = []
        self.particles = []
        self.map_rect = pygame.Rect(0, 0, MAP_COLS * TILE_SIZE, MAP_ROWS * TILE_SIZE)
        self.base_region = None
        self.map_gen = MapGenerator(MAP_COLS, MAP_ROWS)
        self.wave_sys = WaveSystem(MAP_COLS, MAP_ROWS)
        self.upgrade_sys = UpgradeSystem()
        self.audio = AudioSystem()
        self.hud = HUDRenderer()
        self.result = ResultOverlay()
        self._temp_surface = pygame.Surface(
            (MAP_COLS * TILE_SIZE, MAP_ROWS * TILE_SIZE))
        self._last_dt = 16.666
        self._screen_shake_off = (0, 0)
        self._result_stats = []
        self._boss_spawned_this_level = False
        self._post_level_pending = False
        self._grass_walls = []
        self._boss5_defeat_voice = False  # 华强被击败 → 播萨日朗, 替换坦克胜利语音
        # 剧情台词条 / 终章车轮战状态 (start_level 中按关卡重设)
        self._story_banner = None
        self._story_banner_timer = 0
        self._final_battle = []
        self._final_index = 0
        self._boss_replaced = False
        self._flash_timer = 0  # 末日核弹全屏白闪剩余 (ms)

    # --------------------------------------------------------------
    # Lifecycle
    # --------------------------------------------------------------
    def start_level(self, level):
        self.input.reset()  # 清空上一阶段残留的按键 (菜单/升级页按住的方向键会导致开局持续移动)
        self.gs.level = level
        self.player_tanks = []
        self.enemy_tanks = []
        self.bullets = []
        self.pickups = []
        self.particles = []
        self._boss_spawned_this_level = False
        self._post_level_pending = False
        self._result_stats = []
        is_boss_arena = (self.gs.mode == GameMode.BOSS_RUSH) or (self.gs.level % 5 == 0)
        if is_boss_arena:
            self.walls, self.base_region = self.map_gen.generate_boss_arena(level)
        else:
            self.walls, self.base_region = self.map_gen.generate_level(level)
        self._grass_walls = [w for w in self.walls if w.type == WallType.GRASS]
        # 方块再生: 记录本关初始可破坏方块数 (砖/沙/玻璃), 低于此数时随机补生
        self._regen_types = (WallType.BRICK, WallType.SAND, WallType.GLASS)
        if is_boss_arena:
            # Boss 竞技场初始无方块: 设定目标量, 战斗期间持续补生砖/沙/玻璃
            # (权重 40/40/20 与普通关一致), 拆了还会再长, Boss 战不再空旷
            self._regen_initial = (10 if self.gs.level <= 10
                                   else 12 if self.gs.level <= 20 else 14)
        else:
            self._regen_initial = sum(
                1 for w in self.walls if w.type in self._regen_types)
        self._regen_timer = 3000  # 开局 3 秒保护期不补生
        # 图鉴发现: 记录本关地图出现的所有方块/地块 + 我方坦克与主武器
        for w in self.walls:
            self._codex_seen("tile", w.type)
        for pd in self.gs.players:
            self._codex_seen("tank", pd.tank_color)
            self._codex_seen("bullet", pd.bullet_type)
        self.map_rect = self.map_gen.rect()
        for i, pd in enumerate(self.gs.players):
            x = (2 + i * 5) * TILE_SIZE + TILE_SIZE // 2
            y = (MAP_ROWS - 3) * TILE_SIZE
            pd.x, pd.y = x, y
            if is_boss_arena:
                # Boss 战: 战前回满 (Boss Rush 每关都是 Boss 战, 天然全回)
                pd.hp = pd.max_hp
            else:
                # 普通关: 继承上一关血量 (玩家存活才进下一关, 至少保 1 点)
                pd.hp = max(1, int(pd.hp))
            # 每关重置一次性技能状态与计时器
            pd.last_stand_used = False
            pd.phoenix_used = False
            pd.static_timer = 0
            pd.chrono_timer = 0
            pd.doomsday_timer = 0
            pd.phantom_timer = 0
            pd.timed_buffs.clear()  # 限时道具效果换关清空
            pt = PlayerTank(x, y, pd)
            self.player_tanks.append(pt)
        self.gs.wave = type(self.gs.wave)()
        info = self.wave_sys.level_wave_info(level, self.gs.mode)
        self.gs.wave.total_waves = info["waves"]
        self.gs.wave.enemies_total = info["enemies_per_wave"] * info["waves"]
        self.gs.wave.enemies_killed = 0
        self.gs.wave.enemies_spawned = 0
        self.gs.wave.current = 1
        self.gs.wave.spawn_interval = max(800, 2200 - level * 80)
        self.gs.wave.spawn_timer = 1500
        self.gs.boss = None
        # 剧情模式开场台词条 (极简灰字, 4 秒后消失)
        self._story_banner = None
        self._story_banner_timer = 0
        if self.gs.mode == GameMode.STORY:
            self._story_banner = {
                "chapter": story_chapter(level),
                "line": STORY_LINES.get(level, ""),
            }
            self._story_banner_timer = 4000
        # 终章车轮战 (剧情第 30 关): 五位首领依次登场
        self._final_battle = []
        self._final_index = 0
        self._boss_replaced = False
        if (info["is_boss_level"] and self.gs.mode == GameMode.STORY
                and level == 30):
            self._final_battle = [BossId.BOSS_1, BossId.BOSS_2, BossId.BOSS_3,
                                  BossId.BOSS_4, BossId.BOSS_5]
        if info["is_boss_level"]:
            self.gs.wave.total_waves = 1
            self.gs.wave.enemies_total = 0
        self.gs.phase = GamePhase.PLAYING
        # 进入关卡: 停止上一关胜利语音并启动 BGM
        if self.audio:
            self.audio.stop_voice_resume_bgm()
            self.audio.start_bgm()
        # Boss 关: 必须在 BGM 启动后再播出场音频,
        # 否则出场音频会被 start_bgm 立即覆盖 (前两个 Boss 出场音消失的根因)
        if info["is_boss_level"]:
            self._spawn_boss(level)

    def on_upgrade_confirmed_external(self):
        self._on_upgrade_confirmed()

    def begin_frame(self):
        """每帧开始时调用一次,清空上一帧的 just_pressed/just_released。"""
        self.input.begin_frame()

    def handle_event(self, event):
        self.input.handle_event(event)
        self.touch.handle_event(event)
        if self.gs.phase == GamePhase.PAUSED:
            # 暂停页: 3 个选项 (继续/重新开始/返回主菜单), 键盘 + 鼠标双支持
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                ix, iy = self._screen_to_internal(pygame.mouse.get_pos())
                btn_w, btn_h = 480, 64
                for i in range(3):
                    r = pygame.Rect((SCREEN_WIDTH - btn_w) // 2,
                                    SCREEN_HEIGHT // 2 - 40 + i * (btn_h + 14),
                                    btn_w, btn_h)
                    if r.collidepoint(ix, iy):
                        if i == 0:
                            self.gs.phase = GamePhase.PLAYING
                        elif i == 1:
                            self.start_level(self.gs.level)
                        else:
                            self._back_to_menu()
                        return
            if self.input.is_pause() or self.input.just_pressed(pygame.K_ESCAPE):
                self.gs.phase = GamePhase.PLAYING
            elif self.input.just_pressed(pygame.K_RETURN) or self.input.just_pressed(pygame.K_SPACE):
                self.gs.phase = GamePhase.PLAYING
            elif self.input.just_pressed(pygame.K_r):
                # 重新开始战斗
                self.start_level(self.gs.level)
            elif self.input.just_pressed(pygame.K_m):
                # 返回主菜单
                self._back_to_menu()
            return
        if self.gs.phase == GamePhase.PLAYING and self.input.is_pause():
            self.gs.phase = GamePhase.PAUSED
        if self.gs.phase == GamePhase.PLAYING:
            # Boss3 无敌期间: 按 M 返回主菜单 (隐藏捷径, 不再有提示条)
            boss = self.gs.boss
            if (boss and boss.is_special and boss.immortal
                    and self.input.just_pressed(pygame.K_m)):
                self._back_to_menu()
        if self.gs.phase in (GamePhase.VICTORY, GamePhase.GAME_OVER):
            if (self.input.just_pressed(pygame.K_RETURN) or
                    self.input.just_pressed(pygame.K_SPACE)):
                self._handle_result_continue()
            if self.input.just_pressed(pygame.K_ESCAPE):
                self._back_to_menu()
            # 鼠标点击也可继续
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_result_continue()

    # --------------------------------------------------------------
    # Update
    # --------------------------------------------------------------
    def update(self):
        dt = 16.666
        self.gs.update_shake(dt)
        self.gs.update_combo(dt)
        if self._flash_timer > 0:
            self._flash_timer -= dt
        if self._story_banner_timer > 0 and self.gs.phase == GamePhase.PLAYING:
            self._story_banner_timer -= dt
            if self._story_banner_timer <= 0:
                self._story_banner = None
        if self.audio:
            self.audio.update()
        if self.gs.phase == GamePhase.PLAYING:
            self._update_playing(dt)
        self._update_particles(dt)
        self._cleanup_dead()

    def _update_playing(self, dt):
        all_tanks = self.player_tanks + self.enemy_tanks
        # 瞄准点: 触控激活时优先用虚拟瞄准 (手动=右轮盘方向 / 自动=锁最近敌人)
        if self.touch.active and self.player_tanks:
            tp = self.touch.aim_point(self.player_tanks[0], self.enemy_tanks)
            internal_mouse = tp if tp is not None else \
                self._screen_to_internal(pygame.mouse.get_pos())
        else:
            internal_mouse = self._screen_to_internal(pygame.mouse.get_pos())
        for i, pt in enumerate(self.player_tanks):
            if pt.dead:
                continue
            pt.update(dt, self.input, self.walls, all_tanks, self.map_rect,
                      self.bullets, self.particles, self.audio,
                      mouse_pos=internal_mouse)
        for et in self.enemy_tanks:
            if et.dead:
                continue
            et.update(dt, self.walls, all_tanks, self.player_tanks, self.map_rect,
                      self.bullets, self.particles, self.audio)
        if self.gs.boss and not self.gs.boss.dead:
            self.gs.boss.update(dt, self.map_rect, self.walls, self.player_tanks,
                                self.bullets, self.particles,
                                lambda cnt: self._summon_boss_minions(cnt),
                                self.audio)
        # Boss 被子弹击杀后 dead=True, 必须在 update 块外检测死亡,
        # 否则 _on_boss_defeated 永远不会被触发 (打完Boss卡关)
        if self.gs.boss and self.gs.boss.dead:
            self._on_boss_defeated()
            # 终章车轮战: 下一位首领已在 _on_boss_defeated 内登场, 不要清空
            if not getattr(self, "_boss_replaced", False):
                self.gs.boss = None
            self._boss_replaced = False
        for w in self.walls:
            w.update(dt)  # 受击闪白倒计时
        self._update_wall_regen(dt)
        self._update_skill_effects(dt)
        self._update_portals(dt)
        self._update_waves(dt)
        self._update_bullets(dt)
        self._sweep_uncounted_kills()
        self._update_pickups(dt)
        self._update_timed_buffs(dt)
        self._check_end_conditions()

    def _update_skill_effects(self, dt):
        """史诗/传说技能的计时器机制 (静电场/时间静止/末日核弹/幻影军团)"""
        enemies = [e for e in self.enemy_tanks if not e.dead]
        for pd, pt in zip(self.gs.players, self.player_tanks):
            if pt.dead:
                continue
            lvs = pd.upgrade_levels
            # 静电场: 周期性雷击最近敌人 (附带眩晕)
            if pd.static_interval > 0:
                pd.static_timer -= dt
                if pd.static_timer <= 0:
                    pd.static_timer = pd.static_interval
                    if enemies:
                        tgt = min(enemies,
                                  key=lambda e: dist(e.x, e.y, pt.x, pt.y))
                        tgt.take_damage(int(pd.base_damage * pd.static_ratio),
                                        stun=0.4)
                        spawn_hit_spark(self.particles, tgt.x, tgt.y,
                                        color=(255, 230, 120))
                        from entities.particle import spawn_lightning
                        spawn_lightning(self.particles, pt.x, pt.y,
                                        tgt.x, tgt.y)
                        self.gs.trigger_shake(1.0, 120)
                        if self.audio:
                            self.audio.play_sfx("hit")
            # 时间静止 (每 18 秒: 全场减速 90% + 眩晕 1.5 秒)
            if "chrono_field" in lvs:
                pd.chrono_timer -= dt
                if pd.chrono_timer <= 0:
                    pd.chrono_timer = 18000
                    for e in enemies:
                        e.slow_mult = min(e.slow_mult, 0.10)
                        e.slow_timer = max(e.slow_timer, 5000)
                        e.stun_timer = max(e.stun_timer, 1500)
                    from entities.particle import spawn_chrono_ring
                    spawn_chrono_ring(self.particles, pt.x, pt.y)
                    if self.audio:
                        self.audio.play_sfx("combo")
            # 末日核弹 (每 45 秒全屏核爆)
            if "doomsday" in lvs:
                pd.doomsday_timer -= dt
                if pd.doomsday_timer <= 0:
                    pd.doomsday_timer = 45000
                    self._trigger_doomsday(pd)
            # 幻影军团: 镜像完整复制玩家弹幕 (75% 伤害)
            if "phantom_duo" in lvs and enemies:
                pd.phantom_timer -= dt
                if pd.phantom_timer <= 0:
                    cfg = BULLET_CONFIG[pd.bullet_type]
                    pd.phantom_timer = max(200, cfg["cooldown"] * pd.fire_rate_mult)
                    tgt = min(enemies,
                              key=lambda e: dist(e.x, e.y, pd.x, pd.y))
                    px = self.map_rect.width - pd.x
                    # 弹数: 三发散射按 multi_shot; 二连击按 burst_shots (齐射等效连击总伤)
                    n = max(1, pd.multi_shot)
                    spread_deg = pd.spread_deg
                    if n <= 1:
                        n = max(1, getattr(pd, "burst_shots", 1))
                        spread_deg = 0
                    for i in range(n):
                        spread = 0
                        if n > 1 and spread_deg > 0:
                            spread = ((i - (n - 1) / 2)
                                      * (2 * spread_deg / (n - 1)))
                        ang = angle_between(px, pd.y, tgt.x, tgt.y) + spread
                        b = Bullet(px, pd.y, ang, pd.bullet_type, pd.id,
                                   damage_mult=(pd.base_damage / 20.0 * 0.75)
                                   * pd.shot_dmg_mult,
                                   pierce_add=pd.pierce_add,
                                   ricochet_add=pd.ricochet_add)
                        self.bullets.append(b)

    def _trigger_doomsday(self, pd):
        """末日核弹: 全场敌人 500% 武器伤害 + 清除所有敌方子弹"""
        dmg = int(pd.base_damage * 5)
        for e in self.enemy_tanks:
            if not e.dead:
                e.take_damage(dmg)
        if self.gs.boss and not self.gs.boss.dead:
            self.gs.boss.take_damage(dmg)
        self.bullets[:] = [b for b in self.bullets
                           if getattr(b, "is_friendly", False)]
        spawn_explosion(self.particles, self.map_rect.width / 2,
                        self.map_rect.height / 2, intensity=3.0)
        self.gs.trigger_shake(10, 900)
        self._flash_timer = 300  # 全屏白闪 (render 中绘制)
        if self.audio:
            self.audio.play_sfx("explosion")

    def _death_blast_chain(self, src, pd, visited):
        """死亡爆破连锁: 以 src 为中心炸周围敌人, 被炸死的继续连锁"""
        if id(src) in visited:
            return
        visited.add(id(src))
        dmg = int(pd.base_damage * pd.death_blast_ratio)
        killed = []
        for e2 in self.enemy_tanks:
            if e2 is src or e2.dead:
                continue
            if dist(e2.x, e2.y, src.x, src.y) <= pd.death_blast_radius:
                e2.take_damage(dmg)
                if e2.dead:
                    killed.append(e2)
        spawn_explosion(self.particles, src.x, src.y, intensity=1.4)
        for e in killed:
            self._death_blast_chain(e, pd, visited)

    def _check_end_conditions(self):
        # 取消基地设定: 玩家坦克全部阵亡即结束
        all_dead = all(p.dead for p in self.player_tanks)
        if all_dead:
            # 不死凤凰: 原地复活 1 次 (50% 生命 + 3 秒无敌 + 清除敌方子弹)
            for pd, pt in zip(self.gs.players, self.player_tanks):
                if pt.dead and "phoenix" in pd.upgrade_levels and not pd.phoenix_used:
                    pd.phoenix_used = True
                    pd.hp = max(1, int(pd.max_hp * 0.5))
                    pt.hp = pd.hp
                    pt.dead = False
                    pt.invuln_timer = max(pt.invuln_timer, 3000)
                    self.bullets[:] = [b for b in self.bullets
                                       if getattr(b, "is_friendly", False)]
                    spawn_explosion(self.particles, pt.x, pt.y, intensity=2.0)
                    from entities.particle import spawn_phoenix
                    spawn_phoenix(self.particles, pt.x, pt.y)
                    self.gs.trigger_shake(6, 600)
                    if self.audio:
                        self.audio.play_sfx("victory")
                    return
            self._end_level(False)
            return
        if self.gs.boss is None and not self._boss_spawned_this_level:
            alive = [e for e in self.enemy_tanks if not e.dead]
            all_killed = self.gs.wave.enemies_killed >= self.gs.wave.enemies_total
            if all_killed and len(alive) == 0:
                if self.gs.mode == GameMode.ENDLESS:
                    self._advance_wave_or_level()
                else:
                    self._end_level(True)
                return
            # 无尽模式:当前波杀完且场上无敌人 → 推进到下一波
            if (self.gs.mode == GameMode.ENDLESS and len(alive) == 0
                    and self.gs.wave.current < self.gs.wave.total_waves):
                info = self.wave_sys.level_wave_info(self.gs.level, self.gs.mode)
                per_wave = info["enemies_per_wave"]
                if self.gs.wave.enemies_killed >= per_wave * self.gs.wave.current:
                    self.gs.wave.current += 1
                    self.gs.wave.spawn_timer = 1500

    def _advance_wave_or_level(self):
        info = self.wave_sys.level_wave_info(self.gs.level, self.gs.mode)
        per_wave = info["enemies_per_wave"]
        if (self.gs.wave.enemies_killed >= per_wave * self.gs.wave.current
                and self.gs.wave.current < self.gs.wave.total_waves):
            self.gs.wave.current += 1
            self.gs.wave.spawn_timer = 1500
        else:
            self._end_level(True)

    def _end_level(self, victory):
        if self._post_level_pending:
            return
        self._post_level_pending = True
        total_score = sum(p.score for p in self.gs.players)
        total_kills = sum(p.kills for p in self.gs.players)
        if victory:
            self.gs.high_score = max(self.gs.high_score, total_score)
            if self.gs.mode == GameMode.STORY:
                self.gs.max_unlocked_level = max(
                    self.gs.max_unlocked_level, self.gs.level + 1)
            elif self.gs.mode == GameMode.BOSS_RUSH:
                self.gs.max_unlocked_level = max(
                    self.gs.max_unlocked_level, 10)
            self.gs.save()
        mark = ""
        if victory and self.gs.mode == GameMode.STORY and self.gs.level >= 30:
            mark = " · 剧情通关!"
        elif victory and self.gs.mode == GameMode.BOSS_RUSH and self.gs.level >= 25:
            mark = " · Boss Rush 通关!"
        self._result_stats = [
            ("关卡", f"{self.gs.level}{mark}"),
            ("模式", self._mode_name()),
            ("本局分数", str(total_score)),
            ("历史最高", str(self.gs.high_score)),
            ("击杀数", str(total_kills)),
            ("连击峰值", f"{self.gs.combo}"),
        ]
        # 重置结算页标题入场动画
        try:
            self.result.reset_anim()
        except Exception:
            pass
        if victory:
            self._offer_upgrade_if_any()
            if self.gs.phase != GamePhase.LEVEL_UPGRADE:
                self.gs.phase = GamePhase.VICTORY
            if self.audio and self.gs.players:
                boss = self.gs.boss
                if self._boss5_defeat_voice:
                    self.audio.play_boss_voice("萨日朗", pause_bgm=True)
                    self._boss5_defeat_voice = False
                elif (boss is not None and
                        getattr(boss, "boss_id", None) == BossId.BOSS_4):
                    self.audio.play_boss_voice("你胆子真是肥嘟嘟的",
                                               boss_index=4, pause_bgm=True)
                else:
                    self.audio.play_voice_for_tank_color(
                        self.gs.players[0].tank_color, victory=True)
        else:
            self.gs.phase = GamePhase.GAME_OVER
            if self.audio and self.gs.players:
                boss = self.gs.boss
                if boss is not None and getattr(boss, "boss_id", None) == BossId.BOSS_5:
                    self.audio.play_boss_voice("吞进去", pause_bgm=True)
                elif (boss is not None and
                        getattr(boss, "boss_id", None) == BossId.BOSS_4):
                    self.audio.play_boss_voice("小哥路上帮忙带包烟",
                                               boss_index=4, pause_bgm=True)
                else:
                    self.audio.play_voice_for_tank_color(
                        self.gs.players[0].tank_color, victory=False)
            # 战败: 彻底停止背景 BGM, 战败语音播完后保持安静 (不再恢复循环)
            if self.audio:
                self.audio.stop_bgm()
        self.gs.trigger_shake(4.0 if not victory else 2.0, 500)
        if self.audio:
            self.audio.play_sfx("victory" if victory else "defeat")

    def _mode_name(self):
        return {"story": "剧情闯关", "endless": "无尽生存",
                "bossrush": "Boss Rush", "coop": "双人合作"}.get(
                    self.gs.mode.value, "")

    def _offer_upgrade_if_any(self):
        if self.gs.mode in (GameMode.STORY, GameMode.ENDLESS, GameMode.COOP):
            if self.gs.players:
                p0 = self.gs.players[0]
                self.gs.level_upgrade_choices = self.upgrade_sys.available_upgrades(
                    p0, 3, level=self.gs.level)
                self.gs.phase = GamePhase.LEVEL_UPGRADE

    def _on_upgrade_confirmed(self):
        if self.gs.mode in (GameMode.STORY, GameMode.COOP):
            if self.gs.level < 30:
                self.start_level(self.gs.level + 1)
            else:
                self.gs.phase = GamePhase.VICTORY
        elif self.gs.mode == GameMode.ENDLESS:
            if self.gs.level >= 100:
                self.gs.phase = GamePhase.VICTORY  # 无尽模式 100 关上限: 通关
            else:
                self.start_level(self.gs.level + 1)
        elif self.gs.mode == GameMode.BOSS_RUSH:
            if self.gs.level >= 25:
                self.gs.phase = GamePhase.VICTORY  # 打完第五个 Boss: 通关
            else:
                next_level = self.gs.level + 5
                self.start_level(next_level)

    def _handle_result_continue(self):
        if self.gs.phase == GamePhase.VICTORY:
            if (self.gs.mode in (GameMode.STORY, GameMode.COOP) and
                    self.gs.level < 30):
                self.start_level(self.gs.level + 1)
            elif self.gs.mode == GameMode.ENDLESS:
                if self.gs.level >= 100:
                    self._back_to_menu()  # 已通关 100 关
                else:
                    self.start_level(self.gs.level + 1)
            elif self.gs.mode == GameMode.BOSS_RUSH:
                if self.gs.level >= 25:
                    self._back_to_menu()  # 已通关 Boss Rush
                else:
                    self.start_level(self.gs.level + 5)
            else:
                self._back_to_menu()
        else:
            self._back_to_menu()

    def _back_to_menu(self):
        self.gs.phase = GamePhase.MENU
        self.gs.save()
        if self.audio:
            self.audio.stop_voice_resume_bgm()
            self.audio.stop_bgm()

    # --------------------------------------------------------------
    # Subsystems helpers
    # --------------------------------------------------------------
    # --------------------------------------------------------------
    # 方块再生机制
    # --------------------------------------------------------------
    def _update_wall_regen(self, dt):
        """方块再生: 砖/沙/玻璃总数低于本关初始值时, 随机位置补生;
        场上剩余越少, 生成越快 (清空时 0.25 秒一颗 → 越多越慢, 15 个时最慢 2 秒一颗)"""
        if self._regen_initial <= 0:
            return
        cur = sum(1 for w in self.walls if w.type in self._regen_types)
        if cur >= self._regen_initial:
            # 已回满: 重置保护期, 不再补生
            self._regen_timer = max(self._regen_timer, 2500)
            return
        self._regen_timer -= dt
        if self._regen_timer > 0:
            return
        # 基础 250ms/颗, 生成数量越多速度线性下降; 场上 15 个时达到最慢 2000ms/颗
        self._regen_timer = min(2000, int(250 + 1750 * cur / 15))
        self._spawn_regen_wall()

    def _spawn_regen_wall(self):
        """随机位置生成一颗砖块/沙粒/玻璃 (权重 40/40/20), 全程守护:
        不压坦克/Boss、不进出生区与基地环、不破坏地图连通性"""
        r = random.random()
        if r < 0.40:
            wt = WallType.SAND
        elif r < 0.80:
            wt = WallType.BRICK
        else:
            wt = WallType.GLASS
        cols = self.map_gen.cols
        rows = self.map_gen.rows
        occupied = {(w.col, w.row) for w in self.walls}
        base = self.base_region
        for _ in range(40):
            c = random.randint(0, cols - 1)
            rw = random.randint(0, rows - 1)
            if (c, rw) in occupied:
                continue
            # 底部玩家出生行附近留空
            if rw >= rows - 2 and c <= 7:
                continue
            # 基地保护环
            if base and (base[0] - 1 <= c <= base[2] + 1
                         and base[1] - 1 <= rw <= base[3] + 1):
                continue
            rect = pygame.Rect(c * TILE_SIZE, rw * TILE_SIZE,
                               TILE_SIZE, TILE_SIZE)
            # 不压任何坦克 (含 Boss)
            bad = False
            for t in self.player_tanks + self.enemy_tanks:
                if not getattr(t, "dead", False) and rect.colliderect(t.get_rect()):
                    bad = True
                    break
            if bad:
                continue
            if self.gs.boss and not self.gs.boss.dead:
                br = pygame.Rect(self.gs.boss.x - 80, self.gs.boss.y - 80,
                                 160, 160)
                if rect.colliderect(br):
                    continue
            # 连通性: 放置后玩家出生区仍能走到敌人出生方向, 否则换位置
            new_wall = Wall(c, rw, wt)
            if not self.map_gen._is_connected(self.walls + [new_wall]):
                continue
            self.walls.append(new_wall)
            self._codex_seen("tile", wt)
            return

    def _codex_seen(self, kind, key):
        """图鉴发现记录 (防御式: 轻量测试桩可能没有 gs/mark_codex_seen)"""
        gs_ref = getattr(self, "gs", None)
        mark = getattr(gs_ref, "mark_codex_seen", None)
        if mark is not None:
            mark(kind, key)

    def _update_waves(self, dt):
        if self.gs.boss:
            return
        w = self.gs.wave
        info = self.wave_sys.level_wave_info(self.gs.level, self.gs.mode)
        if info["is_boss_level"]:
            return
        if w.enemies_spawned >= w.enemies_total:
            return
        w.spawn_timer -= dt
        if w.spawn_timer <= 0:
            w.spawn_timer = w.spawn_interval
            batch = min(2, w.enemies_total - w.enemies_spawned)
            for _ in range(batch):
                e = self.wave_sys.spawn_enemy(
                    self.player_tanks + self.enemy_tanks,
                    self.walls, self.gs.level, info["enemy_types"])
                self.enemy_tanks.append(e)
                w.enemies_spawned += 1
                # 图鉴发现: 敌军类型 + 敌军炮弹
                self._codex_seen("enemy", e.enemy_type)
                self._codex_seen("bullet", BulletType.CANNON)

    def _spawn_boss(self, level):
        # Boss id 映射:
        # - 剧情: 5/10/15/20/25/30 关 = B1~B5 (30 关为终章车轮战, 由 _final_battle 队列驱动)
        # - 无尽: 每 5 关一个 Boss, 5 个打完循环 (5=B1, 10=B2, ..., 25=B5, 30=B1 ...)
        # - Boss Rush: 按关卡 5=B1 10=B2 ... 25=B5
        if self._final_battle:
            bid = self._final_battle[0]
            self._final_index += 1
            idx = {BossId.BOSS_1: 1, BossId.BOSS_2: 2, BossId.BOSS_3: 3,
                   BossId.BOSS_4: 4, BossId.BOSS_5: 5}[bid]
            hp_mult, dmg_mult = 1.5, 1.0  # 车轮战沿用剧情倍率
        elif self.gs.mode == GameMode.ENDLESS:
            idx = ((level // 5 - 1) % 5) + 1
            bid = [BossId.BOSS_1, BossId.BOSS_2, BossId.BOSS_3,
                   BossId.BOSS_4, BossId.BOSS_5][idx - 1]
        else:
            idx = min(level // 5, 5)
            bid = [BossId.BOSS_1, BossId.BOSS_2, BossId.BOSS_3,
                   BossId.BOSS_4, BossId.BOSS_5][idx - 1]
        cfg_idx = idx
        # 血量/弹幕伤害倍率:
        # - 剧情: 血量 ×1.5 (基础炮弹28伤, Boss1=420=15发)
        # - 无尽: 血量和伤害随关卡逐渐增长 (Boss 循环时越打越强)
        # - Boss Rush: 不变
        if self._final_battle:
            pass  # 已在上面设置
        elif self.gs.mode == GameMode.STORY:
            hp_mult, dmg_mult = 1.5, 1.0
        elif self.gs.mode == GameMode.ENDLESS:
            hp_mult = 1 + (level - 1) * 0.20
            dmg_mult = 1 + (level - 1) * 0.10
        else:
            hp_mult, dmg_mult = 1.0, 1.0
        # 紧急平衡: Boss Rush 的野生狗奶 = 8 秒吟唱竞速,
        # 此时玩家只有 2~3 次强化, 500 血基本打不过 → ×0.6 (300 ≈ 11 发炮弹)
        if self.gs.mode == GameMode.BOSS_RUSH and bid == BossId.BOSS_3:
            hp_mult = 0.6
        self.gs.boss = Boss(bid, level, hp_mult=hp_mult, dmg_mult=dmg_mult)
        # 图鉴发现: 首领 + 其专属弹幕
        self._codex_seen("boss", bid)
        bcfg = BOSS_CONFIG.get(bid, {})
        if bcfg.get("bullet_type"):
            self._codex_seen("bullet", bcfg["bullet_type"])
        if self._final_battle:
            self.gs.boss.name = f"最终战 {self._final_index}/5 · {self.gs.boss.name}"
        self._boss_spawned_this_level = True
        self.gs.trigger_shake(6, 800)
        # Boss 音频策略:
        # - Boss 5/10: 出场播放出场音频 (1.mp3/2.mp3), 播完恢复普通BGM
        # - Boss 15: 首次受击开始吟唱(播 3.mp3), 第8秒无敌, BGM播完游戏失败
        if self.audio:
            if bid == BossId.BOSS_3:
                # 设置回调: Boss BGM结束时触发游戏失败 (播放推迟到无敌时刻)
                self.audio._on_boss_bgm_end = self._on_boss3_bgm_end
                # 尝试获取 BGM 时长
                bgm_path = self.audio._boss_bgm_paths.get(cfg_idx)
                if bgm_path:
                    try:
                        import pygame.mixer
                        sound = pygame.mixer.Sound(bgm_path)
                        self.gs.boss.immortal_duration = int(sound.get_length() * 1000)
                    except Exception:
                        self.gs.boss.immortal_duration = 180000  # 默认3分钟
                else:
                    self.gs.boss.immortal_duration = 180000
            else:
                self.audio.play_boss_bgm(cfg_idx, on_end='resume_bgm')

    def _on_boss3_bgm_end(self, reason):
        """Boss 15 BGM播放结束 -> 游戏失败 (剧情模式不存在通关可能)"""
        if self.gs.boss and not self.gs.boss.dead:
            self.gs.boss.no_reward = True  # 标记不给奖励
            self.gs.boss.dead = True  # 标记防止继续更新
            self._end_level(False)  # 走统一结算流程: 填充统计/语音/音效
            self.gs.boss = None

    def _summon_boss_minions(self, count):
        info = self.wave_sys.level_wave_info(self.gs.level, self.gs.mode)
        pool = info["enemy_types"] or [(EnemyType.SCOUT, 10)]
        for _ in range(count):
            e = self.wave_sys.spawn_enemy(
                self.player_tanks + self.enemy_tanks, self.walls,
                max(1, self.gs.level - 1), pool)
            x_off = random.choice([-1, 1]) * random.randint(40, 140)
            y_off = random.randint(40, 160)
            e.x = self.gs.boss.x + x_off
            e.y = min(MAP_ROWS * TILE_SIZE - 80, self.gs.boss.y + y_off)
            self.enemy_tanks.append(e)

    def _on_boss_defeated(self):
        boss = self.gs.boss
        # 击败Boss后停止Boss BGM并恢复普通BGM
        if self.audio and self.audio._boss_bgm_active:
            self.audio.stop_boss_bgm_and_resume()
        # Boss 3 BGM结束导致的死亡: 不给奖励, 不爆炸
        if getattr(boss, 'no_reward', False):
            self._end_level(False)
            return
        if boss.boss_id == BossId.BOSS_5:
            self._boss5_defeat_voice = True
        for p in self.gs.players:
            p.score += boss.score_reward
        for _ in range(6):
            x = boss.x + random.randint(-80, 80)
            y = boss.y + random.randint(-60, 60)
            self._drop_random_pickup(x, y)
        self.gs.trigger_shake(12, 1200)
        spawn_explosion(self.particles, boss.x, boss.y, intensity=2.5)
        spawn_explosion(self.particles, boss.x - 40, boss.y + 20, intensity=1.2)
        spawn_explosion(self.particles, boss.x + 30, boss.y - 20, intensity=1.4)
        if self.audio:
            self.audio.play_sfx("explosion")
        # 终章车轮战: 还有下一位首领 → 立即登场, 不结算升级
        if self._final_battle and len(self._final_battle) > 1:
            self._final_battle.pop(0)
            self._spawn_boss(self.gs.level)
            self._boss_replaced = True
            return
        if self._final_battle:
            self._final_battle = []  # 最后一位已击败
        self._end_level(True)

    def _update_bullets(self, dt):
        for b in list(self.bullets):
            if b.dead:
                continue
            b.update(dt, self.walls, self.player_tanks + self.enemy_tanks,
                     self.map_rect, self.particles)
            if b.dead:
                continue
            if b.is_friendly:
                for e in self.enemy_tanks:
                    if e.dead:
                        continue
                    hp_before = e.hp
                    full_hp = hp_before >= e.max_hp
                    if b.try_hit_tank(e, particles=self.particles):
                        owner_p = self._find_player(b.owner_id)
                        # 狙击之眼: 受击前血量≥70% 追加伤害; 满血命中时穿透+1
                        if (owner_p is not None
                                and owner_p.dead_eye_mult > 1.0
                                and hp_before >= e.max_hp * 0.7):
                            e.take_damage(
                                int(b.damage * (owner_p.dead_eye_mult - 1.0)))
                            from entities.particle import spawn_snipe_line
                            spawn_snipe_line(self.particles, b.x, b.y,
                                             e.x, e.y)
                        if (full_hp and owner_p is not None
                                and owner_p.dead_eye_mult > 1.0):
                            b.pierce += 1
                        spawn_hit_spark(self.particles, b.x, b.y, color=b.color)
                        if b.type == BulletType.MELON:
                            spawn_explosion(self.particles, b.x, b.y, intensity=0.9)
                        if b.splash:
                            self._apply_splash(b, direct=e)
                            spawn_explosion(self.particles, b.x, b.y, intensity=0.9)
                        if self.audio:
                            self.audio.play_sfx("hit")
                        if e.dead:
                            self._on_enemy_killed(e, b.owner_id)
                        owner_p = self._find_player(b.owner_id)
                        if owner_p and owner_p.life_steal > 0:
                            heal = int(b.damage * owner_p.life_steal)
                            owner_p.hp = min(owner_p.max_hp, owner_p.hp + heal)
                            from entities.particle import spawn_lifesteal
                            spawn_lifesteal(self.particles, e.x, e.y,
                                            owner_p.x, owner_p.y)
                        break
                if (not b.dead and self.gs.boss and
                        not self.gs.boss.dead):
                    boss = self.gs.boss
                    br = boss.get_rect()
                    if circle_rect_overlap(b.x, b.y, b.radius,
                                          br.x, br.y, br.width, br.height):
                        if id(boss) not in b.hit_set:
                            b.hit_set.add(id(boss))
                            boss.take_damage(b.damage, stun=b.stun * 0.25)
                            spawn_hit_spark(self.particles, b.x, b.y,
                                            color=NEON_YELLOW)
                            if b.splash:
                                self._apply_splash(b, direct=boss)
                                spawn_explosion(self.particles, b.x, b.y,
                                                intensity=0.9)
                            self.gs.trigger_shake(1.2, 150)
                            if self.audio:
                                self.audio.play_sfx("hit")
                            owner_p = self._find_player(b.owner_id)
                            if owner_p:
                                owner_p.score += 10
                                if owner_p.life_steal > 0:
                                    heal = int(b.damage * owner_p.life_steal)
                                    owner_p.hp = min(owner_p.max_hp,
                                                     owner_p.hp + heal)
                                    from entities.particle import spawn_lifesteal
                                    spawn_lifesteal(self.particles, boss.x,
                                                    boss.y, owner_p.x, owner_p.y)
                            if b.pierce > 0:
                                b.pierce -= 1
                            else:
                                b.dead = True
            else:
                for p in self.player_tanks:
                    if p.dead:
                        continue
                    if b.try_hit_tank(p, particles=self.particles):
                        spawn_hit_spark(self.particles, b.x, b.y, color=NEON_RED)
                        if b.type == BulletType.MELON:
                            spawn_explosion(self.particles, b.x, b.y, intensity=0.9)
                        if b.splash:
                            self._apply_splash(b, direct=p)
                            spawn_explosion(self.particles, b.x, b.y, intensity=0.9)
                        self.gs.trigger_shake(2.0, 200)
                        if self.audio:
                            self.audio.play_sfx("hit")
                        break
        self.bullets = [b for b in self.bullets if not b.dead]
        # 木箱掉道具 / 燃油桶爆炸: 本帧被打碎的方块统一结算 (墙体列表尚未清理)
        self._post_wall_events()

    def _post_wall_events(self):
        """被子弹/溅射/油桶击碎的方块事件结算 (每帧一次, 用 effect_done 防重复)。
        循环扫描: 油桶 3×3 摧毁的新方块 (连锁油桶/木箱) 在同一帧内继续结算,
        避免被帧末 _cleanup_dead 提前清掉。"""
        while True:
            pending = [w for w in self.walls if w.destroyed and not w.effect_done]
            if not pending:
                return
            for w in pending:
                if w.effect_done:
                    continue
                w.effect_done = True  # 所有碎块统一标记, 保证循环必然收敛
                if w.type == WallType.BARREL:
                    self._explode_barrel(w)
                elif w.type == WallType.CRATE:
                    if random.random() < 0.15:
                        self._drop_random_pickup(w.x + TILE_SIZE / 2,
                                                 w.y + TILE_SIZE / 2)

    def _explode_barrel(self, w):
        """燃油桶爆炸: 摧毁 3×3 区域所有可摧毁方块 (地块/钢墙/草丛不受影响),
        半径 55px 内敌我双方坦克与 Boss 各受 40 伤害"""
        cfg = WALL_CONFIG[WallType.BARREL].get("boom", {})
        radius = cfg.get("radius", 55)
        dmg = cfg.get("damage", 40)
        cx, cy = w.x + w.width / 2, w.y + w.height / 2
        # 3×3 清场: 只摧毁"方块"(hp≥0 且不可通行坦克), 地块类 (水渍/泥沼/冰面/
        # 尖刺/传送门/草丛/水面) 与钢墙一律不碰; 被清的木箱/油桶走 _post_wall_events 结算
        half = TILE_SIZE * 1.5
        for w2 in self.walls:
            if w2.destroyed:
                continue
            wcfg = WALL_CONFIG[w2.type]
            if wcfg.get("tank_pass") or wcfg.get("hp", -1) < 0:
                continue
            c2x, c2y = w2.x + w2.width / 2, w2.y + w2.height / 2
            if abs(c2x - cx) <= half and abs(c2y - cy) <= half:
                w2.destroyed = True
                from entities.particle import spawn_wall_debris
                spawn_wall_debris(self.particles, c2x, c2y)
        spawn_explosion(self.particles, cx, cy, intensity=1.6)
        self.gs.trigger_shake(2.5, 250)
        if self.audio:
            self.audio.play_sfx("explosion")
        for t in self.player_tanks + self.enemy_tanks:
            if getattr(t, "dead", False):
                continue
            if dist(cx, cy, t.x, t.y) <= radius:
                was_dead = t.dead
                t.take_damage(dmg)
                # 敌人被油桶炸死: 记击杀 (归属第一个玩家)
                if (not was_dead and t.dead and
                        t in self.enemy_tanks):
                    self._on_enemy_killed(t, None)
        if self.gs.boss and not self.gs.boss.dead:
            br = self.gs.boss.get_rect()
            if circle_rect_overlap(cx, cy, radius, br.x, br.y,
                                   br.width, br.height):
                self.gs.boss.take_damage(dmg)

    def _update_portals(self, dt):
        """传送门: 坦克中心踏入传送格 → 传送到配对的另一扇门 (1.5s 冷却防反复弹跳)"""
        for w in self.walls:
            if w.type != WallType.PORTAL or w.destroyed:
                continue
            partner = w.portal_partner
            if partner is None or partner.destroyed:
                continue
            for t in self.player_tanks + self.enemy_tanks:
                if getattr(t, "dead", False) or t.portal_cd > 0:
                    continue
                if w.x <= t.x <= w.x + w.width and w.y <= t.y <= w.y + w.height:
                    t.x = partner.x + partner.width / 2 + random.uniform(-24, 24)
                    t.y = partner.y + partner.height / 2 + random.uniform(-24, 24)
                    t.portal_cd = 1500
                    spawn_hit_spark(self.particles,
                                    partner.x + partner.width / 2,
                                    partner.y + partner.height / 2,
                                    color=(150, 145, 170))

    def _apply_splash(self, b, direct):
        """范围伤害: 直击目标已吃满伤害; 半径内其他敌对目标吃 falloff 伤害。

        溅射不附带眩晕/减速/吸血; 玩家子弹只溅射敌人, 敌方子弹只溅射玩家;
        撞墙/出界的子弹不触发 (子弹死亡即跳过本方法)。
        """
        cfg = b.splash
        radius = cfg.get("radius", 55)
        falloff = cfg.get("falloff", 0.6)
        dmg = max(1, int(b.damage * falloff))
        if b.is_friendly:
            targets = self.enemy_tanks
            boss = self.gs.boss
        else:
            targets = self.player_tanks
            boss = None
        for t in targets:
            if t is direct or getattr(t, "dead", False):
                continue
            if dist(b.x, b.y, t.x, t.y) <= radius:
                was_dead = t.dead
                t.take_damage(dmg)
                # 溅射击杀同样结算击杀奖励/连击 (与直击一致)
                if not was_dead and t.dead and b.is_friendly:
                    self._on_enemy_killed(t, b.owner_id)
        # 外卖溅射破砖 (B2): 溅射半径内可摧毁方块也吃 falloff 伤害 (砖/沙/木箱/玻璃/油桶)
        for w in self.walls:
            if w.destroyed:
                continue
            if WALL_CONFIG[w.type].get("hp", -1) < 0:
                continue
            if circle_rect_overlap(b.x, b.y, radius, w.x, w.y, w.width, w.height):
                w.take_damage(dmg)
        if boss is not None and boss is not direct and not boss.dead:
            br = boss.get_rect()
            if circle_rect_overlap(b.x, b.y, radius,
                                   br.x, br.y, br.width, br.height):
                boss.take_damage(dmg)

    def _find_player(self, owner_id):
        for pd in self.gs.players:
            if pd.id == owner_id:
                return pd
        return None

    def _on_enemy_killed(self, enemy, owner_id):
        # 同一敌人只结算一次 (防止溅射/油桶/补记重复记账)
        if getattr(enemy, "kill_counted", False):
            return
        enemy.kill_counted = True
        pd = self._find_player(owner_id)
        if pd is None and self.gs.players:
            pd = self.gs.players[0]
        if pd:
            pd.score += enemy.score_reward
            pd.kills += 1
            # 死亡爆破: 击杀时对周围敌人造成范围伤害 (爆破击杀的敌人连锁触发)
            if pd.death_blast_radius > 0:
                self._death_blast_chain(enemy, pd, set())
        self.gs.wave.enemies_killed += 1
        trigger_voice = self.gs.add_combo()
        if trigger_voice and self.audio:
            # 连击里程碑只放短音效, 不再误放胜利语音 (胜利语音留给真正通关)
            self.audio.play_sfx("combo")
        spawn_explosion(self.particles, enemy.x, enemy.y, intensity=1.2)
        self.gs.trigger_shake(1.5, 180)
        if self.audio:
            self.audio.play_sfx("explosion")
        if random.random() < 0.18:
            self._drop_random_pickup(enemy.x, enemy.y)

    def _sweep_uncounted_kills(self):
        """非子弹伤害 (尖刺等) 击杀的敌人补记击杀, 防止击杀数差 1 导致不结算"""
        for e in self.enemy_tanks:
            if e.dead and not getattr(e, "kill_counted", False):
                self._on_enemy_killed(e, None)

    def _drop_random_pickup(self, x, y):
        items = [(k, v["weight"]) for k, v in PICKUP_CONFIG.items()]
        t = random_choice_weighted(items)
        self.pickups.append(Pickup(x, y, t))
        # 图鉴发现: 道具类型
        self._codex_seen("pickup", t)
        # 场上上限 5 个: 超出踢最老的 (防 Boss 连掉刷屏)
        while len(self.pickups) > PICKUP_MAX_ON_FIELD:
            self.pickups.pop(0)

    def _update_pickups(self, dt):
        class Light:
            def __init__(self, tank, pdata):
                self.x = tank.x
                self.y = tank.y
                self.pickup_magnet = pdata.pickup_magnet
                self.magnet_range = pdata.magnet_range
                self.magnet_global = pdata.magnet_global
                self._data = pdata

            def apply_pickup(self, pu):
                pu.apply(self._data)

        proxies = [Light(t, t.data) for t in self.player_tanks
                   if not getattr(t, "dead", False)]
        for pu in self.pickups:
            if pu.dead:
                continue
            pu.update(dt, proxies, particles=self.particles)
            if pu.dead:
                continue
            # 敌人接触拾取 (路过即捡, 不加寻路): 增益=抢, 惩罚=踩坑; Boss 不参与
            for e in self.enemy_tanks:
                if e.dead:
                    continue
                if dist(e.x, e.y, pu.x, pu.y) < (pu.radius + 18):
                    pu.apply(e, is_enemy=True)
                    pu.dead = True
                    e.last_hit_flash = max(e.last_hit_flash, 200)
                    # 反馈: 敌人在哪捡走的一眼可见 (防"道具没生效"误判)
                    from entities.particle import (
                        spawn_pickup_ping, spawn_pickup_text)
                    spawn_pickup_ping(self.particles, e.x, e.y,
                                      color=pu.color)
                    if getattr(pu, "label", ""):
                        spawn_pickup_text(self.particles, e.x, e.y - 22,
                                          pu.label, pu.color)
                    break
        for pu in self.pickups:
            if pu.dead and self.audio:
                self.audio.play_sfx("pickup")
        self.pickups = [p for p in self.pickups if not p.dead]

    def _update_timed_buffs(self, dt):
        """限时道具效果倒计时 (敌我共用): 归零即删除, 到期自动还原"""
        for pd in self.gs.players:
            self._tick_buffs(getattr(pd, "timed_buffs", None), dt)
        for e in self.enemy_tanks:
            self._tick_buffs(getattr(e, "timed_buffs", None), dt)

    @staticmethod
    def _tick_buffs(buffs, dt):
        if not buffs:
            return
        for k in list(buffs):
            b = buffs[k]
            if not isinstance(b, dict) or "ms" not in b:
                continue
            b["ms"] -= dt
            if b["ms"] <= 0:
                del buffs[k]

    def _update_particles(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if not p.dead]

    def _cleanup_dead(self):
        self.enemy_tanks = [e for e in self.enemy_tanks if not e.dead]
        self.walls = [w for w in self.walls if not w.destroyed]
        self._grass_walls = [w for w in self._grass_walls if not w.destroyed]

    # --------------------------------------------------------------
    # Render
    # --------------------------------------------------------------
    def render(self):
        # 窗口大小变化时重新计算缩放
        dw = self.screen.get_width()
        dh = self.screen.get_height()
        if dw != self._display_w or dh != self._display_h:
            self._display_w = dw
            self._display_h = dh

        # 始终渲染到内部分辨率 surface
        screen = self._internal_surface
        sh = self.gs.shake
        if sh["magnitude"] > 0 and sh["duration"] > 0:
            self._screen_shake_off = (
                random.uniform(-sh["magnitude"], sh["magnitude"]),
                random.uniform(-sh["magnitude"], sh["magnitude"]),
            )
        else:
            self._screen_shake_off = (0, 0)
        ox, oy = self._screen_shake_off
        ts = self._temp_surface
        ts.fill(BG_DEEP)
        self._draw_grid(ts)
        for w in self.walls:
            if w.type != WallType.GRASS:
                w.draw(ts)
        for pu in self.pickups:
            pu.draw(ts)
        for pt in self.player_tanks:
            if not self._in_grass(pt):
                pt.draw(ts, show_hp=False)
        for et in self.enemy_tanks:
            if not self._in_grass(et):
                et.draw(ts)
        if self.gs.boss:
            self.gs.boss.draw(ts)
        for b in self.bullets:
            b.draw(ts)
        for p in self.particles:
            p.draw(ts)
        for w in self._grass_walls:
            w.draw(ts)
        for pt in self.player_tanks:
            if self._in_grass(pt):
                self._draw_semitransparent(ts, pt)
        for et in self.enemy_tanks:
            if self._in_grass(et):
                self._draw_semitransparent(ts, et, alpha=80)
        screen.blit(ts, (ox, oy))
        # 幻影军团: 镜像位置半透明幽灵坦克
        self._draw_phantom(screen)
        minimap_info = {"walls": self.walls, "enemies": self.enemy_tanks,
                        "boss": self.gs.boss, "players": self.player_tanks}
        if self._story_banner is not None:
            self._draw_story_banner(screen)
        mouse_pos = None
        try:
            mouse_pos = self._screen_to_internal(pygame.mouse.get_pos())
        except Exception:
            pass
        self.hud.draw(screen, self.gs, self.player_tanks,
                      minimap_info=minimap_info, mouse_pos=mouse_pos)
        # 虚拟触控 UI (手机版: 轮盘/射击/暂停) 画在 HUD 之上
        self.touch.draw(screen)
        if self.gs.phase == GamePhase.PAUSED:
            self._draw_pause_overlay(screen)
        if self.gs.phase == GamePhase.VICTORY:
            self.result.draw(screen, True, self._result_stats, self.audio)
        elif self.gs.phase == GamePhase.GAME_OVER:
            self.result.draw(screen, False, self._result_stats, self.audio)

        # Boss 3 不再显示"已进入无敌状态"提示条 (保持神秘感)

        # 将内部分辨率缩放到窗口 (保持比例, 居中显示)
        target_w = self._display_w
        target_h = self._display_h
        src_w, src_h = SCREEN_WIDTH, SCREEN_HEIGHT
        # 计算等比缩放
        scale = min(target_w / src_w, target_h / src_h)
        scaled_w = int(src_w * scale)
        scaled_h = int(src_h * scale)
        offset_x = (target_w - scaled_w) // 2
        offset_y = (target_h - scaled_h) // 2
        # 填充窗口背景 (深色)
        self.screen.fill(BG_DEEP)
        # 缩放并绘制
        scaled = pygame.transform.smoothscale(screen, (scaled_w, scaled_h))
        self.screen.blit(scaled, (offset_x, offset_y))
        # 末日核弹: 全屏白闪 (渐弱)
        if self._flash_timer > 0:
            a = int(160 * (self._flash_timer / 300))
            try:
                flash = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
                flash.fill((255, 255, 255, max(0, min(255, a))))
                self.screen.blit(flash, (0, 0))
            except Exception:
                pass

    def _draw_phantom(self, surface):
        """幻影军团: 镜像位置半透明幽灵坦克 (只画抽象圆环)"""
        for pd, pt in zip(self.gs.players, self.player_tanks):
            if pt.dead or "phantom_duo" not in pd.upgrade_levels:
                continue
            px = self.map_rect.width - pd.x
            py = pd.y
            try:
                ghost = pygame.Surface((44, 44), pygame.SRCALPHA)
                pygame.draw.circle(ghost, (*pd.color, 80), (22, 22), 20)
                pygame.draw.circle(ghost, (255, 255, 255, 150), (22, 22), 20, 2)
                surface.blit(ghost, (px - 22, py - 22))
            except Exception:
                pass

    def _draw_story_banner(self, surface):
        """剧情模式开场台词条: 章节名 + 一行梗剧情 (极简灰字, 4秒后消失)"""
        if not self._story_banner:
            return
        try:
            font_ch = load_font(18)
            font_line = load_font(24)
        except Exception:
            font_ch = pygame.font.Font(None, 18)
            font_line = pygame.font.Font(None, 24)
        ch = font_ch.render(self._story_banner["chapter"], True, TEXT_MUTED)
        line = font_line.render(self._story_banner["line"], True, TEXT_DIM)
        pad_x, pad_y = 36, 14
        w = max(ch.get_width(), line.get_width()) + pad_x * 2
        h = ch.get_height() + line.get_height() + 10 + pad_y * 2
        x = (SCREEN_WIDTH - w) // 2
        y = 158
        try:
            panel = pygame.Surface((w, h), pygame.SRCALPHA)
            panel.fill((*BG_PANEL, 235))
            pygame.draw.rect(panel, TEXT_DIM, (0, 0, w, h), 1, border_radius=4)
            surface.blit(panel, (x, y))
        except Exception:
            pygame.draw.rect(surface, BG_PANEL, (x, y, w, h))
        surface.blit(ch, ((SCREEN_WIDTH - ch.get_width()) // 2, y + pad_y))
        surface.blit(line, ((SCREEN_WIDTH - line.get_width()) // 2,
                            y + pad_y + ch.get_height() + 8))

    def _screen_to_internal(self, screen_pos):
        """屏幕坐标 -> 内部分辨率坐标"""
        sx, sy = screen_pos
        src_w, src_h = SCREEN_WIDTH, SCREEN_HEIGHT
        scale = min(self._display_w / src_w, self._display_h / src_h)
        scaled_w = int(src_w * scale)
        scaled_h = int(src_h * scale)
        offset_x = (self._display_w - scaled_w) // 2
        offset_y = (self._display_h - scaled_h) // 2
        if scaled_w <= 0 or scaled_h <= 0:
            return (sx, sy)
        ix = (sx - offset_x) / scale
        iy = (sy - offset_y) / scale
        return (ix, iy)

    def _in_grass(self, tank):
        tr = tank.get_rect()
        for w in self._grass_walls:
            if w.destroyed:
                continue
            if tr.colliderect(pygame.Rect(w.x, w.y, w.width, w.height)):
                return True
        return False

    def _draw_semitransparent(self, surf, tank, alpha=120):
        try:
            tmp = pygame.Surface((surf.get_width(), surf.get_height()),
                                 pygame.SRCALPHA)
            tmp.set_alpha(alpha)
            tank.draw(tmp, show_hp=False)
            surf.blit(tmp, (0, 0))
        except Exception:
            tank.draw(surf, show_hp=False)

    def _draw_grid(self, surface):
        step = TILE_SIZE
        for x in range(0, MAP_COLS * TILE_SIZE, step):
            pygame.draw.line(surface, BG_GRID, (x, 0),
                             (x, MAP_ROWS * TILE_SIZE), 1)
        for y in range(0, MAP_ROWS * TILE_SIZE, step):
            pygame.draw.line(surface, BG_GRID, (0, y),
                             (MAP_COLS * TILE_SIZE, y), 1)

    def _draw_base_hp(self, surface):
        if not self.base_region:
            return
        if self.gs.mode != GameMode.STORY:
            return
        if self.gs.boss:
            return
        cx1, ry1, cx2, ry2 = self.base_region
        bx = cx1 * TILE_SIZE
        by = ry1 * TILE_SIZE
        bw = (cx2 - cx1 + 1) * TILE_SIZE
        bh = (ry2 - ry1 + 1) * TILE_SIZE
        pygame.draw.rect(surface, NEON_CYAN, (bx, by, bw, bh), 2)
        inner = 6
        pygame.draw.rect(surface, (255, 255, 255),
                         (bx + inner, by + inner,
                          bw - inner * 2, bh - inner * 2))
        r = 14
        cx, cy = bx + bw // 2, by + bh // 2
        pygame.draw.circle(surface, NEON_CYAN, (cx, cy), r, 2)
        ratio = max(0, self.gs.base_hp / self.gs.base_max_hp)
        col = (NEON_GREEN if ratio > 0.5
               else (NEON_YELLOW if ratio > 0.25 else NEON_RED))
        pygame.draw.circle(surface, col, (cx, cy), int(r * ratio))

    def _draw_pause_overlay(self, surface):
        # 半透明遮罩 (极简版) — 画到内部分辨率 surface, 随主画面一起缩放到窗口
        try:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT),
                                     pygame.SRCALPHA)
            overlay.fill((*BG_DEEP, 200))
            surface.blit(overlay, (0, 0))
        except Exception:
            pass
        try:
            font_title = load_font(64, bold=True)
            font_btn = load_font(28, bold=True)
            font_hint = load_font(20)
        except Exception:
            font_title = pygame.font.Font(None, 64)
            font_btn = pygame.font.Font(None, 28)
            font_hint = pygame.font.Font(None, 20)

        # 标题 (白色, 无装饰)
        title = font_title.render("暂停", True, TEXT_PRIMARY)
        surface.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2,
                             SCREEN_HEIGHT // 2 - 240))

        # 3 个按钮: 黑底 + 1px 灰边 (悬停白边高亮, 支持鼠标点击)
        buttons = [
            ("继续游戏", "回车 / 空格 / Esc / P"),
            ("重新开始战斗", "R"),
            ("返回主菜单", "M"),
        ]
        btn_w, btn_h = 480, 64
        gap = 14
        y0 = SCREEN_HEIGHT // 2 - 40
        mx, my = self._screen_to_internal(pygame.mouse.get_pos())
        for i, (label, key) in enumerate(buttons):
            bx = (SCREEN_WIDTH - btn_w) // 2
            by = y0 + i * (btn_h + gap)
            hover = pygame.Rect(bx, by, btn_w, btn_h).collidepoint(mx, my)
            try:
                btn_surf = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
                btn_surf.fill((*BG_PANEL, 255))
                pygame.draw.rect(btn_surf, ACCENT if hover else TEXT_DIM,
                                 (0, 0, btn_w, btn_h),
                                 2 if hover else 1, border_radius=4)
                surface.blit(btn_surf, (bx, by))
            except Exception:
                pygame.draw.rect(surface, BG_PANEL, (bx, by, btn_w, btn_h))
                pygame.draw.rect(surface, ACCENT if hover else TEXT_DIM,
                                 (bx, by, btn_w, btn_h), 2 if hover else 1)
            lt = font_btn.render(label, True, ACCENT if hover else TEXT_PRIMARY)
            surface.blit(lt, (bx + 30, by + (btn_h - lt.get_height()) // 2))
            kt = font_hint.render(f"[ {key} ]", True, TEXT_DIM)
            surface.blit(kt, (bx + btn_w - kt.get_width() - 30,
                              by + (btn_h - kt.get_height()) // 2))
