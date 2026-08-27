# -*- coding: utf-8 -*-
"""
Boss 系统 - 3 个首领敌人
Boss 1 (第5关): 篮球Boss, 发射篮球
Boss 2 (第10关): 鸡蛋Boss, 发射鸡蛋
Boss 3 (第15关): 特殊Boss, 不发射子弹, 10秒后无敌+满血, BGM播完游戏失败
"""
import math
import random
import pygame
from core.constants import *
from entities.bullet import Bullet, BulletType
from entities.particle import spawn_explosion, spawn_hit_spark
from utils.math_utils import dist, angle_between, dir_from_angle
from utils.assets import get_boss_image, get_boss_image_file


class BossId:
    BOSS_1 = "boss_1"   # 第5关 - 篮球Boss (蔡徐坤)
    BOSS_2 = "boss_2"   # 第10关 - 旺仔小乔
    BOSS_3 = "boss_3"   # 第15关 - 野生狗奶 (吟唱机制)
    BOSS_4 = "boss_4"   # 第20关 - 袋鼠快递王
    BOSS_5 = "boss_5"   # 第25关 - 华强瓜王


# Boss 配置表
BOSS_CONFIG = {
    BossId.BOSS_1: {
        "index": 1,
        "name": "蔡徐坤·篮球霸王",
        "max_hp": 280,      # +40% (技能大改成长曲线补偿)
        "width": 140,
        "height": 140,
        "speed": 1.5,
        "accent": (255, 150, 60),
        "score_reward": 8000,
        "bullet_type": BulletType.BASKETBALL,
        "attack_interval": 1400,
        "move": "dash",     # 运球冲撞 + 风筝走位
        "special": False,
    },
    BossId.BOSS_2: {
        "index": 2,
        "name": "旺仔小乔",
        "max_hp": 390,      # +39%
        "width": 150,
        "height": 150,
        "speed": 1.2,
        "accent": (255, 130, 190),
        "score_reward": 12000,
        "bullet_type": BulletType.MIC,   # 专属麦克风弹
        "attack_interval": 1200,
        "move": "runway",   # T台巡游
        "special": False,
    },
    BossId.BOSS_3: {
        "index": 3,
        "name": "野生狗奶",
        "max_hp": 500,      # 恢复原始数值 (测试期临时 220, 技能大改后伤害足够, 8秒吟唱窗口重估可行)
        "width": 170,
        "height": 170,
        "speed": 0.4,       # 移动非常慢
        "accent": NEON_RED,
        "score_reward": 30000,
        "bullet_type": None,  # 不发射子弹
        "attack_interval": 0,
        "special": True,      # 特殊Boss: 首次受击开始吟唱(BGM), 第8秒满血+无敌
        "chant_duration": 8000,  # 吟唱时长(ms), 期间必须击杀
    },
    BossId.BOSS_4: {
        "index": 4,
        "name": "袋鼠快递王",
        "max_hp": 1680,     # +40%
        "width": 150,
        "height": 150,
        "speed": 2.0,
        "accent": (255, 205, 60),
        "score_reward": 16000,
        "bullet_type": BulletType.PARCEL,
        "attack_interval": 1300,
        "move": "hop",       # 蹦跳冲撞
        "image": "美团袋鼠.png",
        "special": False,
    },
    BossId.BOSS_5: {
        "index": 5,
        "name": "华强瓜王",
        "max_hp": 2520,     # +40%
        "width": 150,
        "height": 150,
        "speed": 1.6,
        "accent": (120, 220, 80),
        "score_reward": 22000,
        "bullet_type": BulletType.MELON,
        "attack_interval": 1200,
        "move": "charge",    # 保熟突进
        "image": "华强.png",
        "special": False,
    },
}


class Boss:
    def __init__(self, boss_id, level, hp_mult=1.0, dmg_mult=1.0):
        self.boss_id = boss_id
        self.level = level
        cfg = BOSS_CONFIG.get(boss_id) or BOSS_CONFIG[BossId.BOSS_1]
        self.cfg = cfg

        self.name = cfg["name"]
        self.max_hp = int(cfg["max_hp"] * hp_mult)  # 剧情=1.5, 无尽随关卡增长, Boss Rush=1.0
        self.hp = self.max_hp
        self.dmg_mult = dmg_mult  # Boss 弹幕伤害倍率 (无尽模式随关卡增长)
        self.width = cfg["width"]
        self.height = cfg["height"]
        self.speed = cfg["speed"]
        self.accent = cfg["accent"]
        self.score_reward = cfg["score_reward"]
        self.bullet_type = cfg["bullet_type"]
        self.attack_interval = cfg["attack_interval"]
        self.is_special = cfg["special"]

        self.dead = False
        self.phase = 1
        self.action_timer = 0
        self.attack_cooldown = self.attack_interval
        self.move_timer = 0
        self.move_dir = (1, 0)
        self.x = MAP_COLS * TILE_SIZE // 2
        self.y = 4 * TILE_SIZE
        self.turret_angle = 90
        self.target = None
        self.last_hit_flash = 0
        self.stun_timer = 0  # 眩晕剩余 (毫秒), Boss 只吃 25% 时长

        # Boss 3 专属状态 (吟唱机制)
        self.immortal = False
        self.healed_full = False
        self.no_reward = False  # Boss 3 BGM结束死亡时设为True, 不给奖励
        self.immortal_duration = 0  # BGM 总时长(ms)
        self.immortal_elapsed = 0  # 无敌后已过时长(ms)
        self.chanting = False     # 是否在吟唱 (首次受击触发)
        self.chant_timer = 0      # 吟唱已进行时长(ms)
        self._damaged_this_frame = False

        # 移动风格 (dash=运球冲撞 / runway=T台巡游 / drift=漂移游走)
        self.move_style = cfg.get("move", "drift")
        self.dash_state = "idle"        # idle / charging / dashing
        self.dash_timer = 0             # 距下次冲撞的倒计时
        self.charge_timer = 0           # 蓄力倒计时
        self.dash_time = 0              # 冲刺剩余时间
        self.dash_dir = (0, 0)          # 冲刺方向
        self.dash_shot_timer = 0        # 冲刺撒弹间隔
        self.runway_dir = 1             # T台巡游方向
        self.runway_turn_timer = 0      # 距下次转身
        self.runway_base_y = 0          # T台基准高度
        self.orbit_angle = 0            # 螺旋弹幕旋转偏移
        self._last_phase = 1            # 阶段转换检测
        # hop (袋鼠) 状态
        self.hop_state = "idle"         # idle / rising / falling
        self.hop_timer = 0
        self.hop_vx = 0.0
        self.hop_vy = 0.0
        self.hop_gravity = 0.18
        self.hop_ground_y = 0
        # 嘲讽语音计时 (华强/袋鼠)
        self.taunt_timer = 5000
        # 袋鼠首次受击语音标记 (多少)
        self._intro_voiced = False
        # 瓜雨法术计时 (华强)
        self.melon_rain_timer = 2000

        # 加载Boss图片 (新首领按文件名, 旧首领按序号)
        if cfg.get("image"):
            self._image = get_boss_image_file(
                cfg["image"], (self.width + 40, self.height + 40))
        else:
            self._image = get_boss_image(
                cfg["index"], (self.width + 40, self.height + 40))

    @property
    def phase_ratio(self):
        return self.hp / self.max_hp if self.max_hp > 0 else 0

    def compute_phase(self):
        r = self.phase_ratio
        if r > 0.66:
            return 1
        if r > 0.33:
            return 2
        return 3

    def get_rect(self):
        return pygame.Rect(self.x - self.width / 2, self.y - self.height / 2,
                           self.width, self.height)

    def take_damage(self, dmg, stun=0.0):
        if self.dead:
            return False
        # Boss 3 无敌状态: 不掉血
        if self.immortal:
            return False
        self.hp -= dmg
        self.last_hit_flash = 180
        # 眩晕: 只刷新不叠加 (Boss 免疫大部分控制, 时长由调用方 ×0.25)
        if stun > 0:
            self.stun_timer = max(self.stun_timer, int(stun * 1000))
        # 吟唱触发: 首次受击标记 (由 update 处理播 BGM)
        self._damaged_this_frame = True
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
            return True
        return False

    def pick_target(self, players):
        alive = [p for p in players if not getattr(p, "dead", False)]
        if not alive:
            return None
        if self.target and not getattr(self.target, "dead", False) and random.random() < 0.8:
            return self.target
        return min(alive, key=lambda p: dist(self.x, self.y, p.x, p.y))

    def update(self, dt, map_rect, walls, players, bullets_list,
               particles, summon_callback, audio_sys):
        if self.dead:
            return
        if self.last_hit_flash > 0:
            self.last_hit_flash -= dt
        if self.stun_timer > 0:
            self.stun_timer -= dt
        self.phase = self.compute_phase()
        # 阶段转换: 清空敌方子弹 (公平喘息) + 爆炸演出
        if self.phase != self._last_phase:
            self._on_phase_change(bullets_list, particles, audio_sys)
            self._last_phase = self.phase
        self.target = self.pick_target(players)
        self.action_timer += dt

        # Boss 3 特殊逻辑: 首次受击开始吟唱(播BGM), 第8秒满血+无敌
        if self.is_special:
            # 吟唱触发
            if self._damaged_this_frame and not self.chanting and not self.healed_full:
                self.chanting = True
                self.chant_timer = 0
                if audio_sys:
                    try:
                        audio_sys.play_boss_bgm(self.cfg["index"],
                                                on_end='game_over')
                    except Exception:
                        pass
            self._damaged_this_frame = False
            # 吟唱计时: 第 chant_duration 毫秒进入无敌
            if self.chanting and not self.healed_full:
                self.chant_timer += dt
                if self.chant_timer >= self.cfg["chant_duration"]:
                    self.healed_full = True
                    self.hp = self.max_hp
                    self.immortal = True
                    # 无敌闪光效果
                    for _ in range(8):
                        x = self.x + random.randint(-60, 60)
                        y = self.y + random.randint(-60, 60)
                        spawn_hit_spark(particles, x, y, color=NEON_RED)
            if self.healed_full:
                self.immortal_elapsed += dt
            # Boss 3 不移动
            return

        # 眩晕: 本帧不走位不攻击 (攻击冷却也冻结)
        if self.stun_timer > 0:
            return

        # 普通 Boss: 按移动风格走位
        if self.target:
            self.turret_angle = angle_between(self.x, self.y,
                                              self.target.x, self.target.y)
        if self.move_style == "dash":
            self._move_dash(dt, map_rect, bullets_list, particles)
        elif self.move_style == "runway":
            self._move_runway(dt, map_rect, bullets_list)
        elif self.move_style == "hop":
            self._move_hop(dt, map_rect, bullets_list, particles, audio_sys)
        elif self.move_style == "charge":
            self._move_charge(dt, map_rect, bullets_list, particles, audio_sys)
        else:
            self._move_drift(dt, map_rect)

        # Boss 专属嘲讽语音 (周期性): 华强"保熟" / 袋鼠"你胆子真是肥嘟嘟的"
        if self.boss_id in (BossId.BOSS_4, BossId.BOSS_5) and audio_sys:
            self.taunt_timer -= dt
            if self.taunt_timer <= 0:
                self.taunt_timer = 9000
                try:
                    if self.boss_id == BossId.BOSS_4:
                        audio_sys.play_boss_voice("你胆子真是肥嘟嘟的", boss_index=4,
                                                  pause_bgm=False)
                    else:
                        audio_sys.play_boss_voice("保熟", pause_bgm=False)
                except Exception:
                    pass

        # 袋鼠首次受击: 问价 (多少)
        if (self.boss_id == BossId.BOSS_4 and audio_sys
                and not self._intro_voiced and self.hp < self.max_hp):
            self._intro_voiced = True
            try:
                audio_sys.play_boss_voice("多少", boss_index=4,
                                          pause_bgm=False)
            except Exception:
                pass

        # 攻击
        self.attack_cooldown -= dt
        if self.attack_cooldown <= 0 and self.bullet_type is not None:
            self._perform_attack(bullets_list, particles, audio_sys)
            self.attack_cooldown = self._attack_interval()

    # --------------------------------------------------------------
    # 移动风格
    # --------------------------------------------------------------
    def _clamp_pos(self, map_rect, x, y):
        margin = self.width // 2 + 20
        x = max(margin, min(map_rect.width - margin, x))
        y = max(margin + 40, min(map_rect.height // 2 + 40, y))
        return x, y

    def _move_drift(self, dt, map_rect):
        """漂移游走: 随机方向 (通用兜底)"""
        self.move_timer -= dt
        if self.move_timer <= 0:
            self.move_timer = random.randint(1200, 2800)
            a = random.uniform(0, 360)
            ox, oy = dir_from_angle(a)
            self.move_dir = (ox, oy)
        speed_mult = 1.0 if self.phase != 3 else 1.5
        step = dt / 16.666
        self.x, self.y = self._clamp_pos(
            map_rect,
            self.x + self.move_dir[0] * self.speed * speed_mult * step,
            self.y + self.move_dir[1] * self.speed * speed_mult * step)

    def _move_dash(self, dt, map_rect, bullets_list, particles):
        """Boss1 运球冲撞: 风筝走位 + 周期蓄力冲刺撒篮球"""
        step = dt / 16.666
        if self.dash_state == "idle":
            self.dash_timer -= dt
            # 风筝: 与玩家保持 280~450 距离
            if self.target:
                d = dist(self.x, self.y, self.target.x, self.target.y)
                if d > 450:
                    self._step_angle(
                        angle_between(self.x, self.y, self.target.x, self.target.y),
                        self.speed, step, map_rect)
                elif d < 280:
                    self._step_angle(
                        angle_between(self.target.x, self.target.y, self.x, self.y),
                        self.speed * 0.8, step, map_rect)
            if self.dash_timer <= 0 and self.target:
                self.dash_state = "charging"
                self.charge_timer = 500
                self.dash_timer = 7000
                self.dash_dir = dir_from_angle(
                    angle_between(self.x, self.y, self.target.x, self.target.y))
        elif self.dash_state == "charging":
            self.charge_timer -= dt
            # 蓄力闪光
            if particles is not None and random.random() < 0.35:
                spawn_hit_spark(
                    particles,
                    self.x + random.uniform(-50, 50),
                    self.y + random.uniform(-50, 50),
                    color=(255, 190, 110))
            if self.charge_timer <= 0:
                self.dash_state = "dashing"
                self.dash_time = 750
                self.dash_shot_timer = 0
        else:  # dashing
            self.dash_time -= dt
            self.x, self.y = self._clamp_pos(
                map_rect,
                self.x + self.dash_dir[0] * 9.0 * step,
                self.y + self.dash_dir[1] * 9.0 * step)
            # 冲刺沿途撒篮球 (垂直方向各一发)
            self.dash_shot_timer -= dt
            if self.dash_shot_timer <= 0:
                self.dash_shot_timer = 110
                dash_ang = math.degrees(
                    math.atan2(self.dash_dir[1], self.dash_dir[0]))
                for side in (-1, 1):
                    a = dash_ang + 90 * side
                    ox, oy = dir_from_angle(a)
                    b = Bullet(self.x + ox * 30, self.y + oy * 30, a,
                               self.bullet_type, "boss", damage_mult=1.2 * self.dmg_mult)
                    bullets_list.append(b)
            if self.dash_time <= 0:
                self.dash_state = "idle"
                self.dash_timer = 6000

    def _move_runway(self, dt, map_rect, bullets_list):
        """Boss2 T台巡游: 水平走秀 + 正弦摆动, 周期转身扇形齐射"""
        step = dt / 16.666
        if not self.runway_base_y:
            self.runway_base_y = self.y
        speed_mult = 2.4 if self.phase == 3 else 1.6
        self.x += self.runway_dir * self.speed * speed_mult * step
        margin = self.width // 2 + 20
        if self.x > map_rect.width - margin:
            self.runway_dir = -1
            self._runway_turn(bullets_list)
        elif self.x < margin:
            self.runway_dir = 1
            self._runway_turn(bullets_list)
        self.runway_turn_timer -= dt
        if self.runway_turn_timer <= 0:
            self.runway_turn_timer = 3500
            self.runway_dir *= -1
            self._runway_turn(bullets_list)
        bob = math.sin(pygame.time.get_ticks() * 0.003) * 70
        self.x, self.y = self._clamp_pos(map_rect, self.x,
                                         self.runway_base_y + bob)

    def _runway_turn(self, bullets_list):
        """转身瞬间: 向行进方向扇形齐射"""
        if self.bullet_type is None:
            return
        ang = 0 if self.runway_dir > 0 else 180
        for i in range(7):
            a = ang + (i - 3) * 18
            b = Bullet(self.x, self.y, a, self.bullet_type, "boss",
                       damage_mult=1.2 * self.dmg_mult)
            bullets_list.append(b)

    def _move_hop(self, dt, map_rect, bullets_list, particles, audio_sys=None):
        """Boss4 袋鼠: 蹦跳冲撞 (抛物线跳跃, 落地冲击弹幕)"""
        step = dt / 16.666
        if self.hop_state == "idle":
            self.hop_timer -= dt
            if self.target:
                d = dist(self.x, self.y, self.target.x, self.target.y)
                if d > 360:
                    self._step_angle(
                        angle_between(self.x, self.y, self.target.x, self.target.y),
                        self.speed * 0.8, step, map_rect)
            if self.hop_timer <= 0 and self.target:
                self.hop_state = "rising"
                ang = angle_between(self.x, self.y, self.target.x, self.target.y)
                self.hop_vx = math.cos(math.radians(ang)) * 7.5
                self.hop_vy = -3.2          # 向上跳起
                self.hop_ground_y = self.y  # 落地基准高度
                self.hop_timer = 5200
                if audio_sys:
                    try:
                        audio_sys.play_boss_voice("骑手你休息下", boss_index=4,
                                                  pause_bgm=False)
                    except Exception:
                        pass
        elif self.hop_state == "rising":
            self.x += self.hop_vx * step
            self.y += self.hop_vy * step
            self.hop_vy += self.hop_gravity * step
            if self.hop_vy >= 0:
                self.hop_state = "falling"
        else:  # falling
            self.x += self.hop_vx * step
            self.y += self.hop_vy * step
            self.hop_vy += self.hop_gravity * step
            if self.y >= self.hop_ground_y:
                # 落地: 冲击环形弹幕 + 尘土
                self.hop_state = "idle"
                self.x, self.y = self._clamp_pos(map_rect, self.x,
                                                 self.hop_ground_y)
                if self.bullet_type is not None:
                    self._circular_shot(bullets_list, 8, 0, self.bullet_type)
                spawn_explosion(particles, self.x, self.y, intensity=1.0)

    def _move_charge(self, dt, map_rect, bullets_list, particles, audio_sys):
        """Boss5 华强: 慢步巡逻 + 瓜雨法术 + 贴脸劈瓜反击 (与蔡徐坤远距冲刺区分)"""
        step = dt / 16.666
        # 瓜雨法术: 顶部随机位置落瓜
        self.melon_rain_timer -= dt
        if self.melon_rain_timer <= 0:
            self.melon_rain_timer = 2400 if self.phase == 3 else 4200
            self._melon_rain(map_rect, bullets_list)
        if self.dash_state == "idle":
            self.dash_timer -= dt
            # 巡逻: 远距全速逼近, 中距慢步逼近, 太近后撤 (无死区)
            if self.target:
                d = dist(self.x, self.y, self.target.x, self.target.y)
                if d > 330:
                    spd = self.speed if d > 420 else self.speed * 0.6
                    self._step_angle(
                        angle_between(self.x, self.y, self.target.x, self.target.y),
                        spd, step, map_rect)
                elif d < 240:
                    self._step_angle(
                        angle_between(self.target.x, self.target.y, self.x, self.y),
                        self.speed * 0.8, step, map_rect)
                # 贴脸反击: 短促劈瓜 (蓄力350ms → 冲刺300ms → 近身环形瓜)
                if d < 330 and self.dash_timer <= 0:
                    self.dash_state = "charging"
                    self.charge_timer = 350
                    self.dash_timer = 4000
                    self.dash_dir = dir_from_angle(
                        angle_between(self.x, self.y, self.target.x, self.target.y))
                    if audio_sys:
                        try:
                            audio_sys.play_boss_voice("劈我瓜", pause_bgm=False)
                        except Exception:
                            pass
        elif self.dash_state == "charging":
            self.charge_timer -= dt
            if particles is not None and random.random() < 0.5:
                spawn_hit_spark(
                    particles,
                    self.x + random.uniform(-50, 50),
                    self.y + random.uniform(-50, 50),
                    color=(120, 230, 120))
            if self.charge_timer <= 0:
                self.dash_state = "dashing"
                self.dash_time = 300
        else:  # dashing (短促劈瓜, 允许下探到玩家所在行)
            self.dash_time -= dt
            margin = self.width // 2 + 20
            nx = self.x + self.dash_dir[0] * 8.0 * step
            ny = self.y + self.dash_dir[1] * 8.0 * step
            nx = max(margin, min(map_rect.width - margin, nx))
            ny = max(margin + 40, min(map_rect.height - margin, ny))
            self.x, self.y = nx, ny
            if self.dash_time <= 0:
                self.dash_state = "idle"
                # 劈瓜落地: 近身环形瓜
                self._circular_shot(
                    bullets_list,
                    10 if self.phase == 3 else 6, 0, self.bullet_type)

    def _melon_rain(self, map_rect, bullets_list):
        """瓜雨: 地图顶部随机位置落下西瓜"""
        if self.bullet_type is None:
            return
        n = 6 + self.phase * 2
        for _ in range(n):
            x = random.uniform(80, map_rect.width - 80)
            a = 90 + random.uniform(-14, 14)
            b = Bullet(x, 20, a, self.bullet_type, "boss", damage_mult=1.3 * self.dmg_mult)
            bullets_list.append(b)

    def _fan_shot(self, bullets_list, n, center_ang, spread_total):
        """扇形弹幕"""
        if self.bullet_type is None:
            return
        for i in range(n):
            if n <= 1:
                a = center_ang
            else:
                a = center_ang + (i - (n - 1) / 2) * (spread_total / (n - 1))
            b = Bullet(self.x, self.y, a, self.bullet_type, "boss",
                       damage_mult=1.3 * self.dmg_mult)
            bullets_list.append(b)

    def _step_angle(self, ang, speed, step, map_rect):
        ox, oy = dir_from_angle(ang)
        self.x, self.y = self._clamp_pos(
            map_rect, self.x + ox * speed * step, self.y + oy * speed * step)

    def _on_phase_change(self, bullets_list, particles, audio_sys):
        """阶段转换: 清空敌方子弹 + 爆炸演出 (+华强阶段语音)"""
        try:
            bullets_list[:] = [b for b in bullets_list
                               if getattr(b, "is_friendly", False)]
        except Exception:
            pass
        spawn_explosion(particles, self.x, self.y, intensity=1.6)
        if audio_sys:
            try:
                if self.boss_id == BossId.BOSS_5 and self.phase == 3:
                    audio_sys.play_boss_voice("故意找茬", pause_bgm=False)
                elif self.boss_id == BossId.BOSS_4:
                    # 袋鼠阶段语音: P2 报价"100" / P3 加小费
                    audio_sys.play_boss_voice(
                        "100" if self.phase == 2 else "有小费哦",
                        boss_index=4, pause_bgm=False)
            except Exception:
                pass
        if audio_sys:
            try:
                audio_sys.play_sfx("explosion")
            except Exception:
                pass

    def _attack_interval(self):
        base = self.attack_interval
        if self.phase == 2:
            base *= 0.8
        if self.phase == 3:
            base *= 0.6
        return base

    def _perform_attack(self, bullets_list, particles, audio_sys):
        if self.bullet_type is None:
            return
        if self.boss_id == BossId.BOSS_1:
            # 蔡徐坤: 螺旋篮球雨 (环形弹幕 + 逐次旋转偏移)
            self.orbit_angle = (self.orbit_angle + 17) % 360
            n = 8 + self.phase * 2
            self._circular_shot(bullets_list, n, self.orbit_angle, self.bullet_type)
            if self.phase >= 2 and self.target:
                self._tracking_shot(bullets_list, 3 if self.phase == 2 else 5)
            if self.phase == 3:
                # 阶段3: 第二环错位弹幕
                self._circular_shot(bullets_list, 6, self.orbit_angle + 30,
                                    self.bullet_type)
        elif self.boss_id == BossId.BOSS_2:
            # 旺仔小乔: 花瓣弹环 (反向旋转, 更密)
            self.orbit_angle = (self.orbit_angle - 23) % 360
            n = 6 + self.phase * 3
            self._circular_shot(bullets_list, n, self.orbit_angle, self.bullet_type)
            if self.phase >= 2 and self.target:
                self._tracking_shot(bullets_list, 2 if self.phase == 2 else 4)
        elif self.boss_id == BossId.BOSS_4:
            # 袋鼠: 瞄准扇形外卖箱 + 阶段3双扇
            if self.target:
                ang = angle_between(self.x, self.y, self.target.x, self.target.y)
                self._fan_shot(bullets_list, 5 + self.phase, ang, 50)
            if self.phase >= 2:
                self._circular_shot(bullets_list, 6, self.orbit_angle,
                                    self.bullet_type)
                self.orbit_angle = (self.orbit_angle + 25) % 360
            if self.phase == 3 and self.target:
                ang2 = angle_between(self.x, self.y, self.target.x, self.target.y)
                self._fan_shot(bullets_list, 4, ang2 + 90, 70)
        elif self.boss_id == BossId.BOSS_5:
            # 华强: 瞄准三连瓜 + 阶段2扇形瓜雨 + 阶段3旋转切瓜阵
            if self.target:
                ang = angle_between(self.x, self.y, self.target.x, self.target.y)
                for i in range(3):
                    a = ang + (i - 1) * 12
                    b = Bullet(self.x, self.y, a, self.bullet_type, "boss",
                               damage_mult=1.4 * self.dmg_mult)
                    bullets_list.append(b)
            if self.phase == 3:
                self.orbit_angle = (self.orbit_angle + 22) % 360
                for i in range(8):
                    a = self.orbit_angle + i * 45
                    b = Bullet(self.x, self.y, a, self.bullet_type, "boss",
                               damage_mult=1.3 * self.dmg_mult)
                    bullets_list.append(b)
            elif self.phase == 2 and self.target:
                ang2 = angle_between(self.x, self.y, self.target.x, self.target.y)
                self._fan_shot(bullets_list, 7, ang2, 80)
        else:
            # 通用兜底: 环形 + 阶段2+ 追踪
            n = 8 + self.phase * 2
            self._circular_shot(bullets_list, n, 0, self.bullet_type)
            if self.phase >= 2 and self.target:
                self._tracking_shot(bullets_list, 3 if self.phase == 2 else 5)
        if audio_sys:
            audio_sys.play_sfx("boss_shoot")

    def _circular_shot(self, bullets_list, n, offset_angle, btype):
        for i in range(n):
            ang = i * (360 / n) + offset_angle
            b = Bullet(self.x, self.y, ang, btype, "boss", damage_mult=1.4 * self.dmg_mult)
            bullets_list.append(b)

    def _tracking_shot(self, bullets_list, count):
        if not self.target:
            return
        for i in range(count):
            spread = (i - (count - 1) / 2) * 15
            ang = angle_between(self.x, self.y, self.target.x, self.target.y) + spread
            b = Bullet(self.x, self.y, ang, self.bullet_type, "boss",
                       damage_mult=1.5 * self.dmg_mult, pierce_add=1)
            bullets_list.append(b)

    def draw(self, surface, camera_x=0, camera_y=0):
        if self.dead:
            return
        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y)
        color = self.accent
        flash = self.last_hit_flash > 0

        # Boss 3 无敌状态: 单圈暗红细环 (极简)
        if self.is_special and self.immortal:
            try:
                pygame.draw.ellipse(surface, NEON_RED,
                                    (sx - self.width // 2 - 10, sy - self.height // 2 - 10,
                                     self.width + 20, self.height + 20), 2)
            except Exception:
                pass

        # 绘制Boss图片
        if self._image is not None:
            img_rect = self._image.get_rect(center=(sx, sy))
            if flash:
                # 受击闪白: 用白色覆盖
                try:
                    fade = pygame.Surface(self._image.get_size(), pygame.SRCALPHA)
                    fade.fill((255, 255, 255, 160))
                    surface.blit(self._image, img_rect)
                    surface.blit(fade, img_rect,
                                 special_flags=pygame.BLEND_RGBA_ADD)
                except Exception:
                    surface.blit(self._image, img_rect)
            else:
                surface.blit(self._image, img_rect)
        else:
            # 兜底: 用过程化绘制
            self._draw_fallback(surface, sx, sy, flash)

        # 血条
        bw = self.width + 60
        bar_y = sy - self.height // 2 - 24
        try:
            pygame.draw.rect(surface, (70, 72, 92),
                             (sx - bw // 2, bar_y, bw, 10), border_radius=5)
        except Exception:
            pygame.draw.rect(surface, (70, 72, 92),
                             (sx - bw // 2, bar_y, bw, 10))
        ratio = max(0, self.hp / self.max_hp)
        if ratio > 0:
            try:
                pygame.draw.rect(surface, self.accent,
                                 (sx - bw // 2, bar_y, int(bw * ratio), 10), border_radius=5)
            except Exception:
                pygame.draw.rect(surface, self.accent,
                                 (sx - bw // 2, bar_y, int(bw * ratio), 10))
        # 边框
        try:
            pygame.draw.rect(surface, self.accent,
                             (sx - bw // 2, bar_y, bw, 10), 1, border_radius=5)
        except Exception:
            pygame.draw.rect(surface, self.accent,
                             (sx - bw // 2, bar_y, bw, 10), 1)

        # 名字 + 阶段
        try:
            from utils.fonts import load_font
            font = load_font(18, bold=True)
        except Exception:
            font = pygame.font.Font(None, 18)
        if self.is_special:
            # Boss 3: 不显示任何状态文字 (吟唱/无敌均保密, 保持神秘感)
            phase_txt = ""
        else:
            phase_txt = f" [无敌]" if self.immortal else f" P{self.phase}"
        txt = font.render(f"{self.name}{phase_txt}", True, self.accent)
        surface.blit(txt, txt.get_rect(center=(sx, sy - self.height // 2 - 38)))

        # Boss 3 吟唱进度条: 只保留裸进度条, 不显示任何文字提示 (神秘感)
        if self.is_special and not self.healed_full and self.chanting:
            dur = max(1, self.cfg.get("chant_duration", 8000))
            pct = min(100, int(self.chant_timer * 100 / dur))
            bw = 240
            bx = sx - bw // 2
            by = sy + self.height // 2 + 24
            pygame.draw.rect(surface, (56, 56, 64), (bx, by, bw, 10))
            pygame.draw.rect(surface, NEON_RED,
                             (bx, by, int(bw * pct / 100), 10))
            pygame.draw.rect(surface, NEON_RED, (bx, by, bw, 10), 1)

    def _draw_fallback(self, surf, sx, sy, flash):
        """兜底绘制 (无图片时)"""
        color = (255, 255, 255) if flash else self.accent
        try:
            pygame.draw.ellipse(surf, color,
                                (sx - self.width // 2, sy - self.height // 2,
                                 self.width, self.height))
            pygame.draw.ellipse(surf, self.accent,
                                (sx - self.width // 2, sy - self.height // 2,
                                 self.width, self.height), 3)
        except Exception:
            pygame.draw.rect(surf, color,
                             (sx - self.width // 2, sy - self.height // 2,
                              self.width, self.height))
