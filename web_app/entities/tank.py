# -*- coding: utf-8 -*-
"""
坦克基类 + 玩家坦克 + 敌人坦克
"""
import math
import random
import pygame
from core.constants import *
from utils.math_utils import (
    clamp, dist, angle_between, angle_diff, dir_from_angle, circle_rect_overlap
)
from utils.assets import get_tank_top_view, get_rotated
from .bullet import Bullet

TANK_WIDTH = 56
TANK_HEIGHT = 56
# 图片渲染尺寸 (原 2× 碰撞框=112 时贴墙会压进墙砖 28px, 视觉穿模;
# 收到 1.64× 平衡细节与压墙: 压砖余量 28px → 18px)
TANK_IMG_SIZE = 92


class Tank:
    def __init__(self, x, y, color=(0, 245, 255)):
        self.x = float(x)
        self.y = float(y)
        self.body_angle = -90.0
        self.turret_angle = -90.0
        self.color = color
        self.tank_color = None  # 坦克颜色 (用于图片渲染), None=用过程化绘制
        self.width = TANK_WIDTH
        self.height = TANK_HEIGHT
        self.hp = 100
        self.max_hp = 100
        self.speed = 3.0
        self.base_damage = 20
        self.fire_cooldown = 0
        self.fire_rate = 500
        self.bullet_type = BulletType.EGG
        self.dead = False
        self.slow_mult = 1.0
        self.slow_timer = 0
        self.slow_fire_mult = 1.0  # 冰霜弹头: 攻速降低乘区 (受击减速时生效)
        self.stun_timer = 0   # 眩晕剩余时间 (毫秒), >0 时不能移动/开火
        self.timed_buffs = {}  # 限时道具效果 {key: {"ms": 剩余毫秒, "mult": 倍率}} (敌方坦克直接使用, 玩家从 data 读取)
        self.invuln_timer = 0
        self.shield = 0
        self.tread_anim = 0
        self.last_hit_flash = 0
        self.fire_rate_mult = 1.0
        # 地块效果状态
        self.slide_dir = None      # 水渍滑行锁定方向 (dx, dy) 或 None
        self.slide_grace = 0       # 撞停后的宽限 (ms): 期间不重新锁定滑行, 恢复操控
        self.portal_cd = 0         # 传送门冷却 (ms), 防止反复传送
        self.tile_speed_mult = 1.0 # 泥沼/冰面速度乘区 (每帧由 apply_tile 刷新)
        self.on_stain = False      # 中心点当前是否在水渍上
        self.spike_tick = 0        # 尖刺伤害累计 (ms)
        self.last_fire_ms = 0      # 最近一次开火时间 (草地潜行暴露判定)

    def get_rect(self):
        return pygame.Rect(self.x - self.width / 2, self.y - self.height / 2,
                           self.width, self.height)

    def take_damage(self, dmg, slow=0.0, stun=0.0, slow_dur=2500, slow_fire=0.0,
                    particles=None):
        if self.invuln_timer > 0 or self.dead:
            return
        # 无敌星 (限时道具): 完全免疫, 不受伤不破盾
        if self.has_buff("invincible"):
            self.last_hit_flash = 150
            return
        d = getattr(self, 'data', None)
        # 无敌模式: 不掉血
        if d is not None and getattr(d, 'invincible', False):
            self.last_hit_flash = 150
            return
        # 能量护盾: 概率免疫 (附 0.5 秒无敌帧)
        if d is not None and getattr(d, 'shield_chance', 0) > 0 \
                and random.random() < d.shield_chance:
            self.last_hit_flash = 150
            self.invuln_timer = max(self.invuln_timer, 500)
            if particles is not None:
                from .particle import spawn_shield_block
                spawn_shield_block(particles, self.x, self.y)
            return
        actual = dmg
        if self.shield > 0:
            absorb = min(self.shield, dmg)
            self.shield -= absorb
            actual -= absorb
        self.hp -= actual
        # 关键修复: 同步到 player data, 防止下帧 sync_from_data 覆盖血量 (玩家无敌 bug)
        if d is not None:
            d.hp = self.hp
            d.shield = self.shield
        self.last_hit_flash = 200
        if slow > 0:
            # 取更强的减速, 不互相覆盖
            self.slow_mult = min(self.slow_mult, 1.0 - slow)
            self.slow_timer = max(self.slow_timer, slow_dur)
        if slow_fire > 0:
            # 冰霜弹头: 同时降低攻速 (取更强, 不覆盖)
            self.slow_fire_mult = max(self.slow_fire_mult, 1.0 + slow_fire)
            if particles is not None:
                from .particle import spawn_frost
                spawn_frost(particles, self.x, self.y)
        # 眩晕: 只刷新不叠加 (防止被连续命中永久定身)
        if stun > 0:
            self.stun_timer = max(self.stun_timer, int(stun * 1000))
        if self.hp <= 0:
            if (d is not None and getattr(d, 'last_stand_invuln', 0) > 0
                    and not getattr(d, 'last_stand_used', False)):
                # 不屈意志: 致命伤保 1 血 + 无敌 (每关 1 次)
                self.hp = 1
                d.hp = 1
                d.last_stand_used = True
                self.invuln_timer = max(self.invuln_timer, d.last_stand_invuln)
                self.last_hit_flash = 300
                if particles is not None:
                    from .particle import spawn_shield_break
                    spawn_shield_break(particles, self.x, self.y)
            else:
                self.hp = 0
                self.dead = True
                if d is not None:
                    d.hp = 0

    def update_base(self, dt):
        if self.fire_cooldown > 0:
            self.fire_cooldown -= dt
        if self.slow_timer > 0:
            self.slow_timer -= dt
            if self.slow_timer <= 0:
                self.slow_mult = 1.0
                self.slow_fire_mult = 1.0
        if self.stun_timer > 0:
            self.stun_timer -= dt
        if self.invuln_timer > 0:
            self.invuln_timer -= dt
        if self.last_hit_flash > 0:
            self.last_hit_flash -= dt
        if self.portal_cd > 0:
            self.portal_cd -= dt

    def get_buff(self, key):
        """限时效果倍率 (无则 1.0)。玩家坦克由子类覆写为读取 PlayerData。"""
        buffs = getattr(self, "timed_buffs", None) or {}
        b = buffs.get(key)
        return b["mult"] if isinstance(b, dict) else 1.0

    def has_buff(self, key):
        buffs = getattr(self, "timed_buffs", None) or {}
        return key in buffs

    def try_move(self, dx, dy, walls, tanks, map_rect):
        # 反向操控 (惩罚道具): 敌我移动方向全部取反
        if self.has_buff("reverse"):
            dx, dy = -dx, -dy
        spd = min(self.speed * self.slow_mult * self.tile_speed_mult
                  * self.get_buff("speed"), 7.0)
        nx = self.x + dx * spd
        ny = self.y + dy * spd
        moved = False
        rx = pygame.Rect(nx - self.width / 2, self.y - self.height / 2,
                         self.width, self.height)
        can_x = True
        for w in walls:
            wc = WALL_CONFIG[w.type]
            if wc["tank_pass"]:
                continue
            if rx.colliderect(pygame.Rect(w.x, w.y, w.width, w.height)):
                can_x = False
                break
        if can_x:
            for t in tanks:
                if t is self or getattr(t, "dead", False):
                    continue
                if rx.colliderect(t.get_rect()):
                    can_x = False
                    break
        if can_x and map_rect.colliderect(rx):
            self.x = nx
            moved = True
        ry = pygame.Rect(self.x - self.width / 2, ny - self.height / 2,
                         self.width, self.height)
        can_y = True
        for w in walls:
            wc = WALL_CONFIG[w.type]
            if wc["tank_pass"]:
                continue
            if ry.colliderect(pygame.Rect(w.x, w.y, w.width, w.height)):
                can_y = False
                break
        if can_y:
            for t in tanks:
                if t is self or getattr(t, "dead", False):
                    continue
                if ry.colliderect(t.get_rect()):
                    can_y = False
                    break
        if can_y and map_rect.colliderect(ry):
            self.y = ny
            moved = True
        return moved

    # ----------------------------------------------------------
    # 地块效果 (水渍滑行 / 泥沼 / 冰面 / 尖刺)
    # ----------------------------------------------------------
    def _tile_at_center(self, walls):
        """返回中心点所在的"地块"(可通行墙格), 无则 None。"""
        for w in walls:
            wcfg = WALL_CONFIG[w.type]
            if not wcfg.get("tank_pass"):
                continue
            if w.x <= self.x <= w.x + w.width and w.y <= self.y <= w.y + w.height:
                return w
        return None

    def apply_tile(self, dt, walls):
        """每帧刷新地块状态: on_stain / tile_speed_mult / 尖刺伤害 tick。"""
        self.on_stain = False
        self.tile_speed_mult = 1.0
        w = self._tile_at_center(walls)
        if w is None:
            self.spike_tick = 0
            return
        t = w.type
        if t == WallType.WATER_STAIN:
            self.on_stain = True
            self.spike_tick = 0
        elif t == WallType.MUD:
            self.tile_speed_mult = WALL_CONFIG[t].get("speed_mult", 1.0)
            self.spike_tick = 0
        elif t == WallType.ICE:
            self.tile_speed_mult = WALL_CONFIG[t].get("speed_mult", 1.0)
            self.spike_tick = 0
        elif t == WallType.SPIKE:
            # 站立每秒 60 伤害 (0.5s 一跳 30 点, 敌我同伤, 无敌帧内不触发)
            self.spike_tick += dt
            if self.spike_tick >= 500:
                self.spike_tick -= 500
                dps = WALL_CONFIG[t].get("spike_dps", 60)
                self.take_damage(max(1, dps // 2))
        else:
            self.spike_tick = 0

    def fire(self, bullets_list, owner_id, damage_mult=1.0, pierce_add=0,
             ricochet_add=0, multi_shot=1, spread_deg=10, speed_mult=1.0,
             slow_add=0.0, slow_dur=0, slow_fire=0.0, railgun=False):
        if self.fire_cooldown > 0 or self.stun_timer > 0:
            return []
        cfg = BULLET_CONFIG[self.bullet_type]
        cooldown = int(cfg["cooldown"] * self.fire_rate_mult * self.slow_fire_mult
                       * self.get_buff("rapid"))
        if railgun:
            cooldown = int(cooldown * 1.1)  # 轨道炮: 冷却 +10%
        self.fire_cooldown = cooldown
        self.last_fire_ms = pygame.time.get_ticks()
        return self._spawn_volley(bullets_list, owner_id, self.turret_angle,
                                  damage_mult, pierce_add, ricochet_add,
                                  multi_shot, spread_deg, speed_mult,
                                  slow_add, slow_dur, slow_fire, railgun)

    def _spawn_volley(self, bullets_list, owner_id, base_angle, damage_mult,
                      pierce_add, ricochet_add, multi_shot, spread_deg,
                      speed_mult, slow_add, slow_dur, slow_fire, railgun):
        """生成一组子弹 (齐射); 不动冷却 (二连击补射复用)"""
        new_bullets = []
        for i in range(multi_shot):
            spread = 0
            if multi_shot > 1:
                # 最外侧子弹偏移 ±spread_deg°, 中间均匀分布
                spread = (i - (multi_shot - 1) / 2) * (2 * spread_deg / (multi_shot - 1))
            angle = base_angle + spread
            ox, oy = dir_from_angle(angle)
            bx = self.x + ox * (self.width / 2 + 6)
            by = self.y + oy * (self.height / 2 + 6)
            b = Bullet(bx, by, angle, self.bullet_type, owner_id,
                       damage_mult=damage_mult, pierce_add=pierce_add,
                       ricochet_add=ricochet_add, speed_mult=speed_mult,
                       slow_add=slow_add, slow_dur=slow_dur,
                       slow_fire=slow_fire, railgun=railgun)
            bullets_list.append(b)
            new_bullets.append(b)
        return new_bullets

    def _draw_body(self, surface, color, sx, sy):
        # 极简车身: 纯色块 + 深色描边, 无发光底板
        pygame.draw.rect(surface, color,
                         (sx - self.width // 2, sy - self.height // 2,
                          self.width, self.height), border_radius=4)
        dark = tuple(max(0, c - 80) for c in color)
        pygame.draw.rect(surface, dark,
                         (sx - self.width // 2, sy - self.height // 2,
                          self.width, self.height), 2, border_radius=4)
        tread_off = int(self.tread_anim) % 8
        pygame.draw.rect(surface, (30, 30, 45),
                         (sx - self.width // 2 - 2, sy - self.height // 2, 6, self.height))
        pygame.draw.rect(surface, (30, 30, 45),
                         (sx + self.width // 2 - 4, sy - self.height // 2, 6, self.height))
        for i in range(-self.height // 2, self.height // 2, 8):
            pygame.draw.rect(surface, (80, 80, 100),
                             (sx - self.width // 2 - 2, sy + i, 6, 2))
            pygame.draw.rect(surface, (80, 80, 100),
                             (sx + self.width // 2 - 4, sy + i, 6, 2))

    def _draw_tracks(self, surface, sx, sy):
        """绘制履带 (左右各一条, 带滚动动画)"""
        hw = self.width // 2
        hh = self.height // 2
        t_off = int(self.tread_anim) % 12
        # 左履带
        for side in (-1, 1):
            tx = sx + side * (hw + 4)
            ty = sy
            # 履带底色
            try:
                pygame.draw.rect(surface, (25, 25, 35),
                                 (tx - 4, ty - hh + 4, 8, self.height - 8),
                                 border_radius=2)
            except Exception:
                pygame.draw.rect(surface, (25, 25, 35),
                                 (tx - 4, ty - hh + 4, 8, self.height - 8))
            # 履带纹 (滚动)
            for i in range(-hh + 6, hh - 6, 6):
                yoff = (i + t_off) % (self.height - 8) - (self.height // 2 - 4)
                try:
                    pygame.draw.rect(surface, (70, 70, 90),
                                     (tx - 3, ty + yoff, 6, 3), border_radius=1)
                except Exception:
                    pygame.draw.rect(surface, (70, 70, 90),
                                     (tx - 3, ty + yoff, 6, 3))

    def _draw_turret(self, surface, color, sx, sy, angle, barrel_len=None,
                     barrel_w=None, avatar=None):
        if barrel_len is None:
            barrel_len = self.width // 2 + 8
        if barrel_w is None:
            barrel_w = max(5, self.width // 10)
        r = math.radians(angle)
        # 炮管
        tip = (sx + math.cos(r) * (barrel_len + 6),
               sy + math.sin(r) * (barrel_len + 6))
        bcl = (sx - math.sin(r) * barrel_w // 2,
               sy + math.cos(r) * barrel_w // 2)
        bcr = (sx + math.sin(r) * barrel_w // 2,
               sy - math.cos(r) * barrel_w // 2)
        back_l = (bcl[0] - math.cos(r) * barrel_len * 0.3,
                  bcl[1] - math.sin(r) * barrel_len * 0.3)
        back_r = (bcr[0] - math.cos(r) * barrel_len * 0.3,
                  bcr[1] - math.sin(r) * barrel_len * 0.3)
        points = [tip, bcl, back_l, back_r, bcr]
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, (60, 60, 70), points, 1)
        # 炮管口
        pygame.draw.circle(surface, (20, 20, 30), tip, max(3, barrel_w // 2))
        # 炮塔圆盘 (缩小: 32 -> 24) / 玩家坦克显示圆形头像徽章
        turret_r = max(14, self.width // 2 - 4)
        if avatar is not None:
            pygame.draw.circle(surface, color, (sx, sy), turret_r + 2, 1)
            surface.blit(avatar, avatar.get_rect(center=(sx, sy)))
        else:
            pygame.draw.circle(surface, color, (sx, sy), turret_r)
            pygame.draw.circle(surface, (60, 60, 70), (sx, sy), turret_r, 1)
        # 中心圆
        pygame.draw.circle(surface, (90, 90, 100), (sx, sy), 4)

    def draw(self, surface, camera_x=0, camera_y=0, show_hp=True):
        if self.dead:
            return
        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y)
        color = self.color
        # 狂战士: 血量越低红光脉冲越强
        d = getattr(self, 'data', None)
        if d is not None and "berserk" in getattr(d, "upgrade_levels", {}):
            ratio = max(0, self.hp) / max(1, self.max_hp)
            if ratio < 1.0:
                pulse = 1 + math.sin(pygame.time.get_ticks() * 0.015) * 0.3
                r = int((self.width // 2 + 8) * pulse)
                a = int(120 * (1.0 - ratio))
                try:
                    ring = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                    pygame.draw.circle(ring, (200, 85, 85, a), (r, r), r, 2)
                    surface.blit(ring, (sx - r, sy - r))
                except Exception:
                    pass
        # 受击闪烁: 车身颜色交替 (白/原色), 不是全屏白闪
        if self.last_hit_flash > 0:
            flash_phase = (self.last_hit_flash // 50) % 2 == 0
            color = (255, 255, 255) if flash_phase else self.color
        if self.invuln_timer > 0 and (self.invuln_timer // 100) % 2 == 0:
            return
        img = None
        if self.tank_color is not None:
            img = get_tank_top_view(self.tank_color, (TANK_IMG_SIZE, TANK_IMG_SIZE))
        # 履带
        self._draw_tracks(surface, sx, sy)
        if img is not None:
            rot = get_rotated(img, -(self.body_angle + 90), step=2)
            rect = rot.get_rect(center=(sx, sy))
            # 受击时: 偶尔跳过绘制车身 (产生闪烁效果)
            show_body = not (self.last_hit_flash > 0 and (self.last_hit_flash // 50) % 2 != 0)
            if show_body:
                # 幽灵: 半透明车身 (一眼认出"穿墙者")
                if (self.tank_color == TankColor.BLACK
                        and getattr(self, "enemy_type", None) == EnemyType.GHOST):
                    ghost_rot = rot.copy()
                    ghost_rot.set_alpha(150)
                    surface.blit(ghost_rot, rect)
                else:
                    surface.blit(rot, rect)
                # 敌方坦克 (黑色): 碰撞框外 1px 亮边, 浅灰底上保证轮廓
                if self.tank_color == TankColor.BLACK:
                    if getattr(self, "enemy_type", None) == EnemyType.GHOST:
                        # 幽灵: 虚线边 (幽灵感)
                        for seg in range(-self.height // 2 + 3,
                                         self.height // 2 - 3, 8):
                            pygame.draw.rect(surface, (228, 228, 236),
                                             (sx - self.width // 2 - 1,
                                              sy + seg, 2, 4))
                            pygame.draw.rect(surface, (228, 228, 236),
                                             (sx + self.width // 2 - 1,
                                              sy + seg, 2, 4))
                    else:
                        pygame.draw.rect(surface, (228, 228, 236),
                                         (sx - self.width // 2 - 1,
                                          sy - self.height // 2 - 1,
                                          self.width + 2, self.height + 2), 1)
        else:
            self._draw_body(surface, color, sx, sy)
        # 炮塔 + 炮管 (独立旋转, 用闪烁后的颜色)
        avatar = None
        if getattr(self, "player_id", None) is not None:
            try:
                from utils.assets import get_tank_avatar
                avatar = get_tank_avatar(
                    self.tank_color, max(24, (self.width // 2 - 4) * 2))
            except Exception:
                avatar = None
        self._draw_turret(surface, color, sx, sy, self.turret_angle,
                          avatar=avatar)
        # 敌方兵种细节标记 (侦察/炮兵/重甲/幽灵/工程师/精英 一眼区分)
        marks = getattr(self, "_draw_enemy_type_marks", None)
        if marks is not None:
            marks(surface, sx, sy)
        # 护盾 (极简: 单圈灰白细环)
        if self.shield > 0:
            r = self.width // 2 + 4
            try:
                pygame.draw.circle(surface, (*TEXT_PRIMARY, 110), (sx, sy), r, 1)
            except Exception:
                pygame.draw.circle(surface, TEXT_PRIMARY, (sx, sy), r, 1)
        if show_hp and self.hp < self.max_hp:
            bar_w = self.width + 14
            hp_ratio = max(0, self.hp / self.max_hp)
            bar_y = sy - self.height // 2 - 12
            try:
                pygame.draw.rect(surface, (44, 44, 48),
                                 (sx - bar_w // 2, bar_y, bar_w, 6))
            except Exception:
                pygame.draw.rect(surface, (44, 44, 48),
                                 (sx - bar_w // 2, bar_y, bar_w, 6))
            c = NEON_GREEN if hp_ratio > 0.5 else (NEON_YELLOW if hp_ratio > 0.25 else NEON_RED)
            try:
                pygame.draw.rect(surface, c,
                                 (sx - bar_w // 2, bar_y,
                                  int(bar_w * hp_ratio), 6), border_radius=3)
            except Exception:
                pygame.draw.rect(surface, c,
                                 (sx - bar_w // 2, bar_y,
                                  int(bar_w * hp_ratio), 6))


class PlayerTank(Tank):
    def __init__(self, x, y, player_data):
        super().__init__(x, y, player_data.color)
        self.player_id = player_data.id
        self.data = player_data
        self.tank_color = player_data.tank_color
        self.hp = player_data.hp
        self.max_hp = player_data.max_hp
        self.speed = player_data.speed
        self.shield = player_data.shield
        self.invuln_timer = 1500
        # 二连击状态 (一次扳机连发 2 弹, 间隔 burst_delay)
        self._burst_left = 0
        self._burst_timer = 0
        self._burst_delay = 130
        self._burst_angle = -90

    def _fire_burst(self, bullets_list, particles):
        """二连击补射: 沿首发方向再打一发, 不动冷却"""
        lvs = getattr(self.data, "upgrade_levels", None) or {}
        railgun = "railgun" in lvs
        pierce_add = self.data.pierce_add + 6 if railgun else self.data.pierce_add
        angle = getattr(self, "_burst_angle", self.turret_angle)
        self._spawn_volley(
            bullets_list, self.player_id, angle,
            self._combat_damage_mult() * getattr(self.data, "shot_dmg_mult", 1.0),
            pierce_add,
            getattr(self.data, "ricochet_add", 0),
            1, 0,
            getattr(self.data, "bullet_speed_mult", 1.0),
            getattr(self.data, "frost_slow", 0.0),
            getattr(self.data, "frost_slow_dur", 0),
            getattr(self.data, "frost_slow_fire", 0.0),
            railgun)
        if particles is not None:
            from .particle import spawn_muzzle_flash
            ox, oy = dir_from_angle(angle)
            spawn_muzzle_flash(particles, self.x + ox * 22, self.y + oy * 22,
                               angle)

    def _combat_damage_mult(self):
        """战斗伤害倍率 (基础武器伤害折算 + 狂战士 + 轨道炮 + 限时道具)"""
        lvs = getattr(self.data, "upgrade_levels", None) or {}
        mult = self.data.base_damage / 20.0
        # 狂战士: 每损失 1% 生命 +1% 伤害 (最高 +100%)
        if "berserk" in lvs:
            hp_ratio = max(0, self.hp) / max(1, self.max_hp)
            mult *= (1.0 + (1.0 - hp_ratio))
        # 轨道炮: 伤害 ×1.8
        if "railgun" in lvs:
            mult *= 1.8
        # 限时道具伤害乘区: 火力强化 ×1.5 / 锈蚀弹头 ×0.6 (同键互顶)
        mult *= self.get_buff("damage")
        return mult

    def get_buff(self, key):
        """玩家限时效果从 PlayerData 读取 (来源: 拾取道具)"""
        buffs = getattr(self.data, "timed_buffs", None) or {}
        b = buffs.get(key)
        return b["mult"] if isinstance(b, dict) else 1.0

    def has_buff(self, key):
        return key in (getattr(self.data, "timed_buffs", None) or {})

    def sync_to_data(self):
        self.data.x = self.x
        self.data.y = self.y
        self.data.hp = self.hp
        self.data.shield = self.shield
        self.data.angle = self.turret_angle

    def sync_from_data(self):
        self.hp = self.data.hp
        self.max_hp = self.data.max_hp
        self.speed = self.data.speed
        self.base_damage = self.data.base_damage
        self.bullet_type = self.data.bullet_type
        self.shield = self.data.shield
        self.fire_rate_mult = self.data.fire_rate_mult

    def update(self, dt, input_mgr, walls, all_tanks, map_rect,
               bullets_list, particles, audio_sys, mouse_pos=None):
        self.update_base(dt)
        self.sync_from_data()
        dx, dy = input_mgr.get_player_move(self.player_id)
        stunned = self.stun_timer > 0
        if stunned:
            dx, dy = 0, 0  # 眩晕: 不能移动 (炮塔仍可瞄准)
        # 地块效果 + 水渍滑行: 移动中踩入锁定方向, 滑行中无法转向/停止
        self.apply_tile(dt, walls)
        if self.slide_grace > 0:
            self.slide_grace -= dt
        if not self.on_stain:
            self.slide_dir = None
        elif not stunned:
            if self.slide_dir is None and self.slide_grace <= 0 and (dx != 0 or dy != 0):
                m = math.hypot(dx, dy)
                if m > 0:
                    self.slide_dir = (dx / m, dy / m)
            if self.slide_dir is not None:
                dx, dy = self.slide_dir
        if dx != 0 or dy != 0:
            target_angle = math.degrees(math.atan2(dy, dx))
            diff = angle_diff(target_angle, self.body_angle)
            self.body_angle += clamp(diff, -4.0, 4.0) * (dt / 16.666)
            self.tread_anim += 0.6
            if particles is not None and random.random() < 0.3:
                from .particle import spawn_tank_dust
                spawn_tank_dust(particles, self.x, self.y, self.body_angle)
        px, py = self.x, self.y
        moved = self.try_move(dx, dy, walls, all_tanks, map_rect)
        actually_moved = (self.x != px or self.y != py)
        if (self.slide_dir is not None and not actually_moved
                and (dx != 0 or dy != 0) and self.on_stain and not stunned):
            self.slide_dir = None  # 滑行撞墙/坦克/边缘: 停滑
            self.slide_grace = 300  # 0.3s 宽限: 不立刻重锁, 恢复操控防钉死
        try:
            if mouse_pos is not None:
                mx, my = mouse_pos
            else:
                mx, my = pygame.mouse.get_pos()
            if self.player_id == 1:
                self.turret_angle = angle_between(self.x, self.y, mx, my)
            else:
                if dx != 0 or dy != 0:
                    self.turret_angle = self.body_angle
        except Exception:
            if dx != 0 or dy != 0:
                self.turret_angle = self.body_angle
                self.body_angle = self.turret_angle
        # 已删除: 切换子弹功能 (坦克颜色固定子弹类型)
        # 二连击补射: 到点就打 (无需继续按住扳机)
        if self._burst_left > 0 and not stunned:
            self._burst_timer -= dt
            if self._burst_timer <= 0:
                self._burst_left -= 1
                self._fire_burst(bullets_list, particles)
                if self._burst_left > 0:
                    self._burst_timer = self._burst_delay
        if not stunned and input_mgr.is_shooting(self.player_id):
            lvs = getattr(self.data, "upgrade_levels", None) or {}
            dmg_mult = self._combat_damage_mult()
            railgun = "railgun" in lvs
            if railgun:
                pierce_add = self.data.pierce_add + 6
            else:
                pierce_add = self.data.pierce_add
            saved_rate = self.fire_rate_mult
            # 狂战士: 生命<30% 额外 +30% 攻速
            if ("berserk" in lvs and
                    max(0, self.hp) / max(1, self.max_hp) < 0.3):
                self.fire_rate_mult *= 0.7
            fired = self.fire(
                bullets_list, self.player_id,
                damage_mult=dmg_mult * getattr(self.data, "shot_dmg_mult", 1.0),
                pierce_add=pierce_add,
                ricochet_add=getattr(self.data, "ricochet_add", 0),
                multi_shot=getattr(self.data, "multi_shot", 1),
                spread_deg=getattr(self.data, "spread_deg", 10),
                speed_mult=getattr(self.data, "bullet_speed_mult", 1.0),
                slow_add=getattr(self.data, "frost_slow", 0.0),
                slow_dur=getattr(self.data, "frost_slow_dur", 0),
                slow_fire=getattr(self.data, "frost_slow_fire", 0.0),
                railgun=railgun,
            )
            self.fire_rate_mult = saved_rate
            if fired and particles is not None:
                from .particle import spawn_muzzle_flash
                ox, oy = dir_from_angle(self.turret_angle)
                spawn_muzzle_flash(
                    particles, self.x + ox * 22, self.y + oy * 22,
                    self.turret_angle,
                    color=BULLET_CONFIG[self.bullet_type]["color"])
                if audio_sys:
                    audio_sys.play_sfx("shoot")
            # 二连击: 首发成功 → 排队补射 (与三发散射的齐射互斥, 不会叠加)
            if fired and getattr(self.data, "burst_shots", 1) > 1 \
                    and getattr(self.data, "multi_shot", 1) <= 1:
                self._burst_left = self.data.burst_shots - 1
                self._burst_delay = getattr(self.data, "burst_delay", 130)
                self._burst_timer = self._burst_delay
                self._burst_angle = self.turret_angle
        self.sync_to_data()
