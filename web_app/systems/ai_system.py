# -*- coding: utf-8 -*-
"""
敌人AI系统 - 有限状态机
"""
import math
import random
import pygame
from core.constants import *
from utils.math_utils import dist, angle_between, angle_diff, clamp, dir_from_angle
from entities.tank import Tank, TANK_WIDTH, TANK_HEIGHT


class EnemyStates:
    IDLE = "idle"
    CHASE = "chase"
    ATTACK = "attack"
    FLEE = "flee"
    STRAFE = "strafe"
    HEAL = "heal"


class EnemyTank(Tank):
    def __init__(self, x, y, enemy_type, level=1):
        cfg = ENEMY_CONFIG[enemy_type]
        super().__init__(x, y, cfg["color"])
        self.enemy_type = enemy_type
        self.name = cfg["name"]
        # 敌方统一黑色坦克图片
        self.tank_color = TankColor.BLACK
        lvl_mult = 1 + (level - 1) * 0.10
        # 无尽模式深层 (关卡>30, 剧情模式到不了): 血量/伤害持续增长
        deep = 1.0 + max(0, level - 30) * 0.15
        cap = ENEMY_HP_CAP if level <= 30 else int(ENEMY_HP_CAP * deep)
        self.max_hp = min(cap, int(cfg["hp"] * lvl_mult * deep))
        self.hp = self.max_hp
        self.speed = cfg["speed"]
        self.base_damage = cfg["damage"]
        # 无尽深层: 子弹伤害逐渐增加 (关卡≤30 保持原样, 剧情模式不受影响)
        self.dmg_mult = 1.0 if level <= 30 else 1.0 + (level - 30) * 0.10
        self.bullet_type = cfg["bullet_type"]
        self.sight_range = cfg["sight_range"]
        self.fire_rate = cfg["fire_rate"]
        self.burst = cfg.get("burst", 1)
        self.burst_remaining = 0
        self.burst_timer = 0
        self.healer = cfg.get("healer", False)
        self.phase_through_brick = cfg.get("phase_through_brick", False)
        self.score_reward = int(100 * lvl_mult * deep)
        self.state = EnemyStates.IDLE
        self.state_timer = 0
        self.target_player = None
        self.move_dir = (0, 0)
        self.strafe_angle = random.choice([-1, 1])
        self.wander_timer = 0
        self.wander_dir = (0, 0)
        self.fire_rate_mult = 1.0
        self.heal_timer = 0  # 工程师治疗冷却
        self.kill_counted = False  # 击杀是否已结算 (防重复记账/补记尖刺击杀)
        # 主动进攻: 有直视线时的开火距离 (默认 sight×1.5, 炮兵/精英配置里拉大)
        self.engage_range = cfg.get("engage", int(self.sight_range * 1.5))
        # 墙滑脱困
        self.stuck_dir = 0        # +1 左滑 / -1 右滑 / 0 未定
        self.stuck_timer = 0      # 滑行方向锁定剩余 (ms)
        self._stall = 0           # 朝目标无进展帧数 (卡墙检测)
        self._best_d = None       # 历史最近距离
        self._best_target = None  # 最近距离对应的目标
        self._wall_follow = False  # 墙滑绕行挂起 (持续到畅通)
        self._wall_d0 = 0          # 挂起时的目标距离 (放行基准)
        self._wall_time = 0        # 挂起累计时长 (超时放行)
        self._los_frame = 0       # 视线检测帧计数 (隔帧缓存)
        self._los_blocker = None  # 视线第一个挡弹墙类型缓存

    def _draw_enemy_type_marks(self, surface, sx, sy):
        """兵种细节标记 (全灰阶, 一眼区分六种敌军):
        侦察兵=速度斜纹 · 炮兵=加长炮管+炮口环 · 重甲=加厚装甲框+铆钉
        幽灵=半透明+虚线边(在 tank.draw 内) · 工程师=白十字 · 精英=双线框+顶标"""
        t = self.enemy_type
        hw, hh = self.width // 2, self.height // 2
        try:
            if t == EnemyType.SCOUT:
                # 两侧速度箭头 (白色 V 形, 轻快感; 加粗保证小尺寸可读)
                for side in (-1, 1):
                    cx = sx + side * (hw - 2)
                    pygame.draw.lines(surface, (225, 225, 232), False,
                                      [(cx - 12, sy - 14), (cx, sy + 1),
                                       (cx + 12, sy - 14)], 4)
            elif t == EnemyType.ARTILLERY:
                # 加长炮管 + 炮口环 (远程感)
                r = math.radians(self.turret_angle)
                tip0 = (sx + math.cos(r) * (hw + 16),
                        sy + math.sin(r) * (hw + 16))
                tip1 = (sx + math.cos(r) * (hw + 34),
                        sy + math.sin(r) * (hw + 34))
                pygame.draw.line(surface, (130, 130, 140), tip0, tip1, 5)
                pygame.draw.circle(surface, (205, 205, 215), tip1, 5, 2)
            elif t == EnemyType.HEAVY:
                # 加厚装甲框 + 四角铆钉 (肉盾感)
                pygame.draw.rect(surface, (110, 110, 120),
                                 (sx - hw - 4, sy - hh - 4,
                                  self.width + 8, self.height + 8), 2)
                for dx, dy in ((-hw - 4, -hh - 4), (hw + 4, -hh - 4),
                               (-hw - 4, hh + 4), (hw + 4, hh + 4)):
                    pygame.draw.circle(surface, (165, 165, 175),
                                       (sx + dx, sy + dy), 2)
            elif t == EnemyType.ENGINEER:
                # 白色十字 (医疗标记)
                pygame.draw.rect(surface, (222, 222, 230),
                                 (sx - 3, sy - 9, 6, 18))
                pygame.draw.rect(surface, (222, 222, 230),
                                 (sx - 9, sy - 3, 18, 6))
            elif t == EnemyType.ELITE:
                # 双线框 + 顶部白色三角 (精锐感)
                pygame.draw.rect(surface, (200, 200, 210),
                                 (sx - hw - 6, sy - hh - 6,
                                  self.width + 12, self.height + 12), 1)
                pygame.draw.rect(surface, (120, 120, 130),
                                 (sx - hw - 8, sy - hh - 8,
                                  self.width + 16, self.height + 16), 1)
                pygame.draw.polygon(surface, (200, 200, 210),
                                    [(sx, sy - hh - 18),
                                     (sx - 6, sy - hh - 27),
                                     (sx + 6, sy - hh - 27)])
        except Exception:
            pass

    def _player_hidden(self, p, walls):
        """草地潜行: 坦克完全在草丛中且 1.5s 内未开火 -> 敌人无法索敌"""
        tr = p.get_rect()
        grass = [w for w in walls if w.type == WallType.GRASS and not w.destroyed]
        if not grass:
            return False
        corners = ((tr.left + 1, tr.top + 1), (tr.right - 1, tr.top + 1),
                   (tr.left + 1, tr.bottom - 1), (tr.right - 1, tr.bottom - 1))
        for cx, cy in corners:
            if not any(g.x <= cx <= g.x + g.width and g.y <= cy <= g.y + g.height
                       for g in grass):
                return False
        return pygame.time.get_ticks() - getattr(p, "last_fire_ms", 0) > 1500

    def pick_target_player(self, players):
        if self.target_player and not getattr(self.target_player, "dead", False):
            return self.target_player
        alive = [p for p in players if not getattr(p, "dead", False)]
        if not alive:
            return None
        best = None
        best_d = float("inf")
        for p in alive:
            d = dist(self.x, self.y, p.x, p.y)
            if d < best_d:
                best_d = d
                best = p
        self.target_player = best
        return best

    def update(self, dt, walls, all_tanks, players, map_rect,
               bullets_list, particles, audio_sys):
        self.update_base(dt)
        # 草地潜行: 藏好的玩家不可被索敌 (开火后暴露 1.5s)
        visible = [p for p in players
                   if not getattr(p, "dead", False) and not self._player_hidden(p, walls)]
        if self.target_player is not None:
            if (getattr(self.target_player, "dead", False) or
                    self._player_hidden(self.target_player, walls)):
                self.target_player = None
        target = self.pick_target_player(visible)
        if not target:
            self.apply_tile(dt, walls)
            return
        d = dist(self.x, self.y, target.x, target.y)
        target_angle = angle_between(self.x, self.y, target.x, target.y)
        tdiff = angle_diff(target_angle, self.turret_angle)
        self.turret_angle += clamp(tdiff, -3.0, 3.0) * (dt / 16.666)
        self.body_angle = self.turret_angle
        if self.enemy_type == EnemyType.HEAVY and d < 140:
            self.state = EnemyStates.CHASE
        elif d < self.sight_range * 0.7:
            if self.hp < self.max_hp * 0.25:
                self.state = EnemyStates.FLEE
            elif self.healer and self._ally_need_heal(all_tanks):
                self.state = EnemyStates.HEAL
            else:
                self.state = EnemyStates.ATTACK
        elif d < self.sight_range:
            self.state = EnemyStates.STRAFE
        else:
            self.state = EnemyStates.CHASE
        dx, dy = 0, 0
        if self.state == EnemyStates.CHASE:
            ox, oy = dir_from_angle(target_angle)
            dx, dy = ox, oy
        elif self.state == EnemyStates.STRAFE:
            perp = target_angle + 90 * self.strafe_angle
            ox, oy = dir_from_angle(perp)
            dx, dy = ox * 0.7, oy * 0.7
            self.state_timer += dt
            if self.state_timer > 2000:
                self.state_timer = 0
                self.strafe_angle *= -1
        elif self.state == EnemyStates.FLEE:
            ox, oy = dir_from_angle(target_angle + 180)
            dx, dy = ox, oy
        elif self.state == EnemyStates.HEAL:
            ally = self._find_injured_ally(all_tanks)
            if ally:
                a = angle_between(self.x, self.y, ally.x, ally.y)
                ox, oy = dir_from_angle(a)
                dx, dy = ox, oy
                # 治疗: 靠近友军后每 0.6 秒回血
                self.heal_timer -= dt
                if dist(self.x, self.y, ally.x, ally.y) < TANK_WIDTH * 1.5:
                    if self.heal_timer <= 0:
                        self.heal_timer = 600
                        ally.hp = min(ally.max_hp, ally.hp + 2)
            else:
                self.heal_timer = 0
        else:
            self.wander_timer -= dt
            if self.wander_timer <= 0:
                a = random.uniform(0, 360)
                ox, oy = dir_from_angle(a)
                self.wander_dir = (ox, oy)
                self.wander_timer = random.randint(1200, 3000)
            dx, dy = self.wander_dir
        if self.stun_timer > 0:
            dx, dy = 0, 0  # 眩晕: 敌人原地停顿 (不开火不移动)
        # 地块效果 + 水渍滑行 (敌人对称: 移动中踩入锁方向, 滑行中冻结 AI 转向)
        self.apply_tile(dt, walls)
        if self.slide_grace > 0:
            self.slide_grace -= dt
        if not self.on_stain:
            self.slide_dir = None
        elif self.stun_timer <= 0:
            if self.slide_dir is None and self.slide_grace <= 0 and (dx != 0 or dy != 0):
                m = math.hypot(dx, dy)
                if m > 0:
                    self.slide_dir = (dx / m, dy / m)
            if self.slide_dir is not None:
                dx, dy = self.slide_dir
                self.body_angle = math.degrees(math.atan2(dy, dx))
        move_walls = walls
        if self.phase_through_brick:
            move_walls = [w for w in walls if w.type != WallType.BRICK]
        # 卡墙检测: 朝目标直线长时间无进展 (顶墙/横移卡位) → 墙滑绕行
        if self._best_target is not target:
            self._best_d = None
            self._best_target = target
        if self._best_d is None or d < self._best_d - 8:
            self._best_d = d
            self._stall = 0
        else:
            self._stall += 1
        px, py = self.x, self.y
        moved = self.try_move(dx, dy, move_walls, all_tanks, map_rect)
        actually_moved = (self.x != px or self.y != py)
        if (self.slide_dir is not None and not actually_moved
                and (dx != 0 or dy != 0)
                and self.on_stain and self.stun_timer <= 0):
            self.slide_dir = None   # 滑行撞墙: 停滑
            self.slide_grace = 300  # 0.3s 宽限: 不立刻重锁, 防贴墙钉死
        if self.stun_timer > 0:
            moved = True  # 眩晕时跳过卡墙脱困 (否则会被随机推力挪动)
        # --- 墙滑绕行: 停滞 1.5s 触发, 持续跟随直到真前进 60px 或 10s 超时 ---
        # (水渍上也允许救援: 否则滑行撞钢墙后敌人会钉死在渍上)
        if (self.stun_timer <= 0
                and self.state not in (EnemyStates.FLEE, EnemyStates.HEAL)):
            if self._stall > 90:
                if not self._wall_follow:
                    self._wall_follow = True
                    self._wall_d0 = d
                    self._wall_time = 0
            if self._wall_follow:
                self._wall_time += dt
                tx, ty = target.x - self.x, target.y - self.y
                td = math.hypot(tx, ty) or 1.0
                moved = self.try_move(tx / td, ty / td, move_walls, all_tanks, map_rect)
                if d < self._wall_d0 - 60 or self._wall_time > 10000:
                    self._wall_follow = False  # 已真正越过障碍, 交还状态机
                elif self._stall > 90:
                    # 直线实际被挡 (try_move 分轴移动, 贴墙时 Y 轴仍能滑,
                    # 但距离无进展) → 沿墙滑行
                    if self.stuck_dir == 0 or self.stuck_timer <= 0:
                        # 选"更接近目标"的一侧滑行 (点积), 方向锁定 0.8s 防抖动
                        c1x, c1y = dir_from_angle(self.body_angle + 90)
                        c2x, c2y = dir_from_angle(self.body_angle - 90)
                        self.stuck_dir = 1 if (c1x * tx + c1y * ty >=
                                               c2x * tx + c2y * ty) else -1
                        self.stuck_timer = 800
                    self.stuck_timer -= dt
                    sx, sy = dir_from_angle(self.body_angle + 90 * self.stuck_dir)
                    moved = self.try_move(sx, sy, move_walls, all_tanks, map_rect)
                    if not moved:
                        # 两侧都堵 (墙角死角): 依次试四个方向, 先动起来脱离死角
                        for ang in (self.body_angle + 90 * self.stuck_dir,
                                    self.body_angle - 90 * self.stuck_dir,
                                    self.body_angle, self.body_angle + 180):
                            ox2, oy2 = dir_from_angle(ang)
                            if self.try_move(ox2, oy2, move_walls, all_tanks, map_rect):
                                moved = True
                                break
        if moved:
            self.tread_anim += 0.5
        # 幽灵穿过砖墙后不能停在砖内 (黑坦克藏黑砖里会导致"看起来清完却不结算")
        if self.phase_through_brick:
            self._eject_from_bricks(walls, all_tanks, map_rect)
        # 开火判定 (主动进攻):
        #   有直视线 → 交战距离内直接开火 (不用等玩家靠近)
        #   隔着砖墙 → 允许远程"破墙射击" (炮弹一发碎一块砖, 逐步开路)
        #   隔着钢墙 → 不开火
        can_shoot = (self.stun_timer <= 0 and abs(tdiff) < 12)
        if can_shoot:
            self._los_frame += 1
            if d <= self.engage_range:
                if self._los_frame % 6 == 0 or d <= 320:
                    self._los_blocker = self._first_blocker(
                        move_walls, target.x, target.y)
                can_shoot = self._los_blocker != WallType.STEEL
            elif d <= self.sight_range * 2:
                if self._los_frame % 6 == 0:
                    self._los_blocker = self._first_blocker(
                        move_walls, target.x, target.y)
                can_shoot = self._los_blocker == WallType.BRICK
            else:
                can_shoot = False
        if can_shoot:
            if self.burst > 1 and self.burst_remaining > 0:
                self.burst_timer -= dt
                if self.burst_timer <= 0:
                    # 三连发补射: 清掉首发冷却, 否则补射永远被 fire_cooldown 拦截
                    self.fire_cooldown = 0
                    self.fire(bullets_list, -self.enemy_type_to_id(),
                              damage_mult=self.dmg_mult * self.get_buff("damage"))
                    self.burst_remaining -= 1
                    self.burst_timer = 180
            elif self.fire_cooldown <= 0:
                fired = self.fire(bullets_list, -self.enemy_type_to_id(),
                                  damage_mult=self.dmg_mult * self.get_buff("damage"))
                if fired and self.burst > 1:
                    self.burst_remaining = self.burst - 1
                    self.burst_timer = 180
                if fired and particles:
                    from entities.particle import spawn_muzzle_flash
                    ox, oy = dir_from_angle(self.turret_angle)
                    spawn_muzzle_flash(
                        particles, self.x + ox * 22, self.y + oy * 22,
                        self.turret_angle,
                        color=BULLET_CONFIG[self.bullet_type]["color"])

    def enemy_type_to_id(self):
        mapping = {
            EnemyType.SCOUT: 1, EnemyType.ARTILLERY: 2, EnemyType.HEAVY: 3,
            EnemyType.GHOST: 4, EnemyType.ENGINEER: 5, EnemyType.ELITE: 6,
        }
        return mapping.get(self.enemy_type, 1)

    def _eject_from_bricks(self, walls, tanks, map_rect):
        """幽灵可以穿砖, 但不能停在砖块内部:
        中心在砖内时沿 4 个方向推出, 直到中心离开砖块且不撞非砖障碍/坦克"""
        bricks = [w for w in walls if w.type == WallType.BRICK and not w.destroyed]
        if not bricks:
            return
        inside = any(w.x <= self.x <= w.x + w.width and
                     w.y <= self.y <= w.y + w.height for w in bricks)
        if not inside:
            return
        for ang in (0, 180, 90, -90):
            ox, oy = dir_from_angle(ang)
            nx, ny = self.x + ox * 64, self.y + oy * 64
            # 推出后中心仍在砖内 -> 换方向
            if any(w.x <= nx <= w.x + w.width and
                   w.y <= ny <= w.y + w.height for w in bricks):
                continue
            rect = pygame.Rect(nx - self.width / 2, ny - self.height / 2,
                               self.width, self.height)
            if not map_rect.colliderect(rect):
                continue
            blocked = False
            for w in walls:
                wc = WALL_CONFIG[w.type]
                if wc.get("tank_pass") or w.type == WallType.BRICK:
                    continue
                if rect.colliderect(pygame.Rect(w.x, w.y, w.width, w.height)):
                    blocked = True
                    break
            if blocked:
                continue
            for t in tanks:
                if t is self or getattr(t, "dead", False):
                    continue
                if rect.colliderect(t.get_rect()):
                    blocked = True
                    break
            if blocked:
                continue
            self.x, self.y = nx, ny
            return

    def _first_blocker(self, walls, tx, ty):
        """自身到 (tx,ty) 的直线上第一个挡弹墙类型:
        None=无阻挡, WallType.BRICK=砖墙(可打碎), 其他=钢墙等(打不动)"""
        d = dist(self.x, self.y, tx, ty)
        if d < 1:
            return None
        steps = max(2, int(d // 24))
        for i in range(1, steps + 1):
            px = self.x + (tx - self.x) * i / steps
            py = self.y + (ty - self.y) * i / steps
            for w in walls:
                wc = WALL_CONFIG[w.type]
                if wc.get("tank_pass") or wc.get("bullet_pass"):
                    continue
                if w.x <= px <= w.x + w.width and w.y <= py <= w.y + w.height:
                    return w.type
        return None

    def _ally_need_heal(self, all_tanks):
        for t in all_tanks:
            if t is self or getattr(t, "dead", True):
                continue
            if isinstance(t, EnemyTank) and t.hp < t.max_hp * 0.7:
                return True
        return False

    def _find_injured_ally(self, all_tanks):
        best = None
        best_ratio = 0.7
        for t in all_tanks:
            if t is self or getattr(t, "dead", True):
                continue
            if isinstance(t, EnemyTank):
                r = t.hp / t.max_hp
                if r < best_ratio:
                    best_ratio = r
                    best = t
        return best
