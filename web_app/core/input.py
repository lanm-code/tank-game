# -*- coding: utf-8 -*-
"""
键盘输入管理器
Input Manager
"""
import pygame
from .constants import *


class InputManager:
    def __init__(self):
        self.keys_pressed = set()
        self.keys_just_pressed = set()
        self.keys_just_released = set()

    def begin_frame(self):
        self.keys_just_pressed.clear()
        self.keys_just_released.clear()

    def reset(self):
        """清空所有按键状态 (进关卡/窗口失焦时调用, 防止卡键持续移动)"""
        self.keys_pressed.clear()
        self.keys_just_pressed.clear()
        self.keys_just_released.clear()

    def handle_event(self, event):
        # 窗口失焦: 键盘事件会丢失 KEYUP -> 必须清空按键, 否则坦克持续移动
        if hasattr(pygame, "WINDOWFOCUSLOST") and event.type == pygame.WINDOWFOCUSLOST:
            self.reset()
            return
        if event.type == pygame.ACTIVEEVENT and not getattr(event, "gain", True):
            self.reset()
            return
        if event.type == pygame.KEYDOWN:
            if event.key not in self.keys_pressed:
                self.keys_just_pressed.add(event.key)
            self.keys_pressed.add(event.key)
        elif event.type == pygame.KEYUP:
            self.keys_pressed.discard(event.key)
            self.keys_just_released.add(event.key)

    def is_down(self, key):
        return key in self.keys_pressed

    def just_pressed(self, key):
        return key in self.keys_just_pressed

    def just_released(self, key):
        return key in self.keys_just_released

    def get_player_move(self, player_id=1):
        dx, dy = 0, 0
        if player_id == 1:
            if self.is_down(pygame.K_w):
                dy = -1
            if self.is_down(pygame.K_s):
                dy = 1
            if self.is_down(pygame.K_a):
                dx = -1
            if self.is_down(pygame.K_d):
                dx = 1
        else:
            if self.is_down(pygame.K_UP):
                dy = -1
            if self.is_down(pygame.K_DOWN):
                dy = 1
            if self.is_down(pygame.K_LEFT):
                dx = -1
            if self.is_down(pygame.K_RIGHT):
                dx = 1
        return dx, dy

    def is_shooting(self, player_id=1):
        if player_id == 1:
            # P1 开火: 鼠标右键
            try:
                return bool(pygame.mouse.get_pressed(num_buttons=3)[2])
            except Exception:
                try:
                    return bool(pygame.mouse.get_pressed()[2])
                except Exception:
                    return False
        # P2 开火: 空格
        return self.is_down(pygame.K_SPACE)

    def just_shot(self, player_id=1):
        # P1 鼠标右键无 "just pressed" 概念, 由 is_shooting 持续判定
        if player_id == 1:
            return False
        return self.just_pressed(pygame.K_SPACE)

    def is_switch_bullet_next(self, player_id=1):
        if player_id == 1:
            return self.just_pressed(pygame.K_e)
        return self.just_pressed(pygame.K_PERIOD)

    def is_switch_bullet_prev(self, player_id=1):
        if player_id == 1:
            return self.just_pressed(pygame.K_q)
        return self.just_pressed(pygame.K_COMMA)

    def is_pause(self):
        return self.just_pressed(pygame.K_ESCAPE) or self.just_pressed(pygame.K_p)

    def upgrade_pick(self):
        if self.just_pressed(pygame.K_1):
            return 1
        if self.just_pressed(pygame.K_2):
            return 2
        if self.just_pressed(pygame.K_3):
            return 3
        return None
