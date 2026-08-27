# -*- coding: utf-8 -*-
"""
虚拟触控层 (手机版玩法)
- 左轮盘 = 移动 (动态锚点, 灰白圆环)
- 右轮盘 = 瞄准 (手动模式) / 自动锁敌 (自动模式, 菜单可切换)
- 射击大按钮 = 持续开火 (对应桌面"按住右键")
- 暂停小按钮 = Esc
- 游戏核心零改动: 通过 CombinedInput 包装 + 虚拟瞄准点注入
- 桌面调试: 环境变量 TANK_TOUCH_DEBUG=1 时用鼠标左键拖拽模拟双指
"""
import math
import os
import pygame
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT

RING = (208, 208, 214)        # 灰白圆环
RING_ACTIVE = (255, 255, 255)  # 激活时纯白
FILL = (120, 120, 128)
STICK_R = 70                 # 轮盘半径 (内部分辨率坐标)
KNOB_R = 30
DEAD_ZONE = 14               # 死区 (px)
FIRE_R = 72                  # 射击按钮半径
PAUSE_R = 34
LEFT_HALF = SCREEN_WIDTH // 2


class TouchControls:
    def __init__(self, screen, gs):
        self.screen = screen
        self.gs = gs
        self._debug = os.environ.get("TANK_TOUCH_DEBUG") == "1"
        self.active = self._debug          # 收到真实触摸后永久激活
        self.move_vec = (0.0, 0.0)          # 左轮盘方向 (dx, dy), 长度 ≤1
        self.aim_vec = (0.0, 0.0)           # 右轮盘方向
        self.shooting = False
        self._pause_flag = False
        self._left_id = None
        self._left_anchor = (0.0, 0.0)
        self._right_id = None
        self._right_anchor = (0.0, 0.0)
        self._fire_id = None
        self._fire_pressed = False
        # 布局 (内部分辨率坐标)
        self.fire_c = (SCREEN_WIDTH - 175, SCREEN_HEIGHT - 190)
        self.pause_c = (112, 214)

    # ------------------------------------------------------------
    # 事件
    # ------------------------------------------------------------
    def handle_event(self, event):
        if not self._debug:
            if event.type == pygame.FINGERDOWN:
                self.active = True
                x, y = self._finger_to_internal(event.x, event.y)
                self._touch_down(event.finger_id, x, y)
            elif event.type == pygame.FINGERMOTION:
                if self.active:
                    x, y = self._finger_to_internal(event.x, event.y)
                    self._touch_move(event.finger_id, x, y)
            elif event.type == pygame.FINGERUP:
                if self.active:
                    x, y = self._finger_to_internal(event.x, event.y)
                    self._touch_up(event.finger_id, x, y)
            return
        # 桌面调试: 鼠标左键拖拽 = 手指 0 (右键仍是桌面开火, 互不干扰)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            x, y = self._screen_to_internal(pygame.mouse.get_pos())
            self._touch_down(0, x, y)
        elif event.type == pygame.MOUSEMOTION and \
                (self._left_id == 0 or self._right_id == 0 or
                 self._fire_id == 0):
            x, y = self._screen_to_internal(pygame.mouse.get_pos())
            self._touch_move(0, x, y)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            x, y = self._screen_to_internal(pygame.mouse.get_pos())
            self._touch_up(0, x, y)

    def _screen_to_internal(self, pos):
        dw = self.screen.get_width()
        dh = self.screen.get_height()
        scale = min(dw / SCREEN_WIDTH, dh / SCREEN_HEIGHT)
        sw = int(SCREEN_WIDTH * scale)
        sh = int(SCREEN_HEIGHT * scale)
        ox = (dw - sw) // 2
        oy = (dh - sh) // 2
        if sw <= 0 or sh <= 0:
            return pos
        return ((pos[0] - ox) / scale, (pos[1] - oy) / scale)

    def _finger_to_internal(self, fx, fy):
        dw = self.screen.get_width()
        dh = self.screen.get_height()
        scale = min(dw / SCREEN_WIDTH, dh / SCREEN_HEIGHT)
        sw = int(SCREEN_WIDTH * scale)
        sh = int(SCREEN_HEIGHT * scale)
        ox = (dw - sw) // 2
        oy = (dh - sh) // 2
        # FINGER 事件坐标是相对窗口的 0~1 归一化
        return ((fx * dw - ox) / scale, (fy * dh - oy) / scale)

    def _touch_down(self, fid, x, y):
        if math.hypot(x - self.fire_c[0], y - self.fire_c[1]) <= FIRE_R:
            self._fire_id = fid
            self._fire_pressed = True
            self.shooting = True
            return
        if math.hypot(x - self.pause_c[0], y - self.pause_c[1]) <= PAUSE_R:
            self._pause_flag = True
            return
        if self._left_id is None and x < LEFT_HALF:
            self._left_id = fid
            self._left_anchor = (x, y)
            self.move_vec = (0.0, 0.0)
            return
        if self._right_id is None:
            self._right_id = fid
            self._right_anchor = (x, y)
            self.aim_vec = (0.0, 0.0)

    def _touch_move(self, fid, x, y):
        if fid == self._left_id:
            dx = x - self._left_anchor[0]
            dy = y - self._left_anchor[1]
            self.move_vec = self._stick_vec(dx, dy)
        elif fid == self._right_id:
            dx = x - self._right_anchor[0]
            dy = y - self._right_anchor[1]
            self.aim_vec = self._stick_vec(dx, dy)

    def _touch_up(self, fid, x, y):
        if fid == self._left_id:
            self._left_id = None
            self.move_vec = (0.0, 0.0)
        elif fid == self._right_id:
            self._right_id = None
            self.aim_vec = (0.0, 0.0)
        elif fid == self._fire_id:
            self._fire_id = None
            self._fire_pressed = False
            self.shooting = False

    def _stick_vec(self, dx, dy):
        d = math.hypot(dx, dy)
        if d < DEAD_ZONE:
            return (0.0, 0.0)
        m = min(1.0, d / STICK_R)
        return (dx / d * m, dy / d * m)

    # ------------------------------------------------------------
    # 注入接口
    # ------------------------------------------------------------
    def consume_pause(self):
        v = self._pause_flag
        self._pause_flag = False
        return v

    def aim_point(self, player, enemies):
        """返回虚拟瞄准点 (内部坐标); 无输入时返回 None (回退鼠标)。"""
        if not self.active:
            return None
        if self.gs.aim_mode == "auto":
            alive = [e for e in enemies
                     if not getattr(e, "dead", False)]
            if alive:
                t = min(alive, key=lambda e: (e.x - player.x) ** 2
                        + (e.y - player.y) ** 2)
                return (t.x, t.y)
            return None
        if self.aim_vec[0] or self.aim_vec[1]:
            return (player.x + self.aim_vec[0] * 420,
                    player.y + self.aim_vec[1] * 420)
        return None

    # ------------------------------------------------------------
    # 绘制 (内部分辨率 surface, 在 HUD 之后调用)
    # ------------------------------------------------------------
    def draw(self, surface):
        if not self.active:
            return
        # 左轮盘
        if self._left_id is not None:
            self._draw_stick(surface, self._left_anchor, self.move_vec)
        # 右轮盘
        if self._right_id is not None:
            self._draw_stick(surface, self._right_anchor, self.aim_vec)
        # 射击按钮
        ring = RING_ACTIVE if self._fire_pressed else RING
        pygame.draw.circle(surface, FILL, self.fire_c, FIRE_R)
        pygame.draw.circle(surface, ring, self.fire_c, FIRE_R, 3)
        try:
            from utils.fonts import load_font
            ft = load_font(30, bold=True).render("开火", True, ring)
        except Exception:
            ft = pygame.font.Font(None, 44).render("FIRE", True, ring)
        surface.blit(ft, (self.fire_c[0] - ft.get_width() // 2,
                          self.fire_c[1] - ft.get_height() // 2))
        # 暂停按钮
        pygame.draw.circle(surface, FILL, self.pause_c, PAUSE_R)
        pygame.draw.circle(surface, RING, self.pause_c, PAUSE_R, 2)
        bar_w = 10
        for dx in (-9, 9):
            pygame.draw.rect(surface, RING,
                             (self.pause_c[0] + dx - bar_w // 2,
                              self.pause_c[1] - 12, bar_w, 24),
                             border_radius=2)

    def _draw_stick(self, surface, anchor, vec):
        ax, ay = anchor
        pygame.draw.circle(surface, (92, 92, 100), (int(ax), int(ay)),
                           STICK_R, 0)
        pygame.draw.circle(surface, RING_ACTIVE if (vec[0] or vec[1]) else RING,
                           (int(ax), int(ay)), STICK_R, 2)
        kx = ax + vec[0] * (STICK_R - KNOB_R)
        ky = ay + vec[1] * (STICK_R - KNOB_R)
        pygame.draw.circle(surface, (180, 180, 188), (int(kx), int(ky)),
                           KNOB_R, 0)
        pygame.draw.circle(surface, RING, (int(kx), int(ky)), KNOB_R, 2)


class CombinedInput:
    """InputManager 包装: 触控优先, 其余按键/方法转发给原 InputManager"""
    def __init__(self, base, touch):
        self.base = base
        self.touch = touch

    def __getattr__(self, name):
        return getattr(self.base, name)

    def get_player_move(self, player_id=1):
        v = self.touch.move_vec
        if v[0] or v[1]:
            # 触控为全向向量; 游戏侧会归一化
            return (v[0], v[1])
        return self.base.get_player_move(player_id)

    def is_shooting(self, player_id=1):
        if self.touch.shooting:
            return True
        return self.base.is_shooting(player_id)

    def is_pause(self):
        return self.touch.consume_pause() or self.base.is_pause()
