# -*- coding: utf-8 -*-
"""
主菜单 / 三选一升级 / 结算界面
"""
import math
import random
import pygame
from core.constants import *
from core.game_state import GamePhase, GameMode
from systems.upgrade_system import (UpgradeSystem, UPGRADE_POOL,
                                     UPGRADE_ICONS, UPGRADE_RARITY_COLORS)
from utils.assets import get_tank_view3d, get_bullet_image
from utils.fonts import load_font
from ui.codex_ui import CodexUI
from ui.skill_icons import render_skill_icon

# 主菜单布局常量 (1920×1080 极简封面版)
MENU_BTN_W = 320
MENU_BTN_H = 64
MENU_BTN_GAP = 12
MENU_BTN_X = (SCREEN_WIDTH - MENU_BTN_W) // 2
MENU_BTN_Y0 = 360
TANK_STRIP_W = 520
TANK_STRIP_H = 140
TANK_STRIP_X = (SCREEN_WIDTH - TANK_STRIP_W) // 2
TANK_STRIP_Y = 780


class MenuController:
    def __init__(self, screen, game_state, game):
        self.screen = screen
        self.gs = game_state
        self.game = game
        # 内部分辨率 surface
        self._internal = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.buttons = []
        self.hover_idx = 0
        self._rects_cache = []
        self._god_rect = None
        self._aim_rect = None
        try:
            self.font_title = load_font(96, bold=True)
            self.font_big = load_font(36, bold=True)
            self.font = load_font(22, bold=True)
            self.font_small = load_font(16)
            self.font_icon = load_font(84, bold=True)
        except Exception:
            self.font_title = pygame.font.Font(None, 96)
            self.font_big = pygame.font.Font(None, 36)
            self.font = pygame.font.Font(None, 22)
            self.font_small = pygame.font.Font(None, 16)
            self.font_icon = pygame.font.Font(None, 84)
        self.upgrade_sys = UpgradeSystem()
        self.codex_ui = CodexUI(screen, game_state, game)
        self._title_phase = 0
        # 标题动态粒子: 标题带内缓慢上飘的灰白微尘 (极简幅度, 不用发光)
        self._title_particles = []
        _rnd = random.Random(7)
        for _ in range(30):
            self._title_particles.append({
                "x": _rnd.uniform(120, SCREEN_WIDTH - 120),
                "y": _rnd.uniform(60, 250),
                "ph": _rnd.uniform(0, math.pi * 2),
                "spd": _rnd.uniform(0.12, 0.45),
                "amp": _rnd.uniform(6, 22),
                "r": _rnd.uniform(1.0, 2.6),
                "base": _rnd.uniform(90, 170),
            })
        self.mode = "main"
        self.intro_title = ""
        # 背景创意飞弹: 随机位置生成 8 种炮弹之一, 横穿画面直至消失
        self._bg_bullets = []
        self._bg_bullet_timer = 30
        self._bg_tick = 0
        self.build_main_menu()

    def build_main_menu(self):
        self.mode = "main"
        self.hover_idx = 0
        self.buttons = [
            {"id": "story", "text": "剧情闯关", "key": "1", "enabled": True},
            {"id": "endless", "text": "无尽生存", "key": "2", "enabled": True},
            {"id": "bossrush", "text": "Boss Rush", "key": "3", "enabled": True},
            {"id": "codex", "text": "游戏图鉴", "key": "4", "enabled": True},
            {"id": "quit", "text": "退出游戏", "key": "Esc", "enabled": True},
        ]

    def _window_to_internal(self, mx, my):
        """窗口坐标 -> 内部分辨率坐标"""
        dw = self.screen.get_width()
        dh = self.screen.get_height()
        src_w, src_h = SCREEN_WIDTH, SCREEN_HEIGHT
        scale = min(dw / src_w, dh / src_h)
        sw = int(src_w * scale)
        sh = int(src_h * scale)
        ox = (dw - sw) // 2
        oy = (dh - sh) // 2
        # 反向映射
        ix = (mx - ox) / scale
        iy = (my - oy) / scale
        return int(ix), int(iy)

    def handle_event(self, event):
        if self.gs.phase == GamePhase.LEVEL_UPGRADE:
            self.mode = "upgrade"
        if self.mode == "codex":
            res = self.codex_ui.handle_event(event)
            if res == "exit":
                self.build_main_menu()
            return
        mx, my = pygame.mouse.get_pos()
        mx, my = self._window_to_internal(mx, my)
        if self.mode == "main":
            # 通用列表页交互 (封面)
            if event.type == pygame.MOUSEMOTION:
                rects = self._button_rects()
                self.hover_idx = -1
                for i, b in enumerate(rects):
                    if b and b.collidepoint(mx, my):
                        self.hover_idx = i
                        break
                if self.hover_idx == -1:
                    self._ensure_valid_hover()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # 封面专属: 无敌开关
                if (self.mode == "main" and hasattr(self, '_god_rect')
                        and self._god_rect and self._god_rect.collidepoint(mx, my)):
                    self.gs.god_mode = not self.gs.god_mode
                    return
                # 瞄准模式开关 (手机版: 手动轮盘 / 自动锁敌)
                if (self.mode == "main" and hasattr(self, '_aim_rect')
                        and self._aim_rect and self._aim_rect.collidepoint(mx, my)):
                    self.gs.aim_mode = ("manual"
                                        if getattr(self.gs, "aim_mode", "manual") == "auto"
                                        else "auto")
                    return
                # 封面专属: 坦克切换箭头
                if self.mode == "main":
                    if self._tank_arrow_rect(-1).collidepoint(mx, my):
                        self._cycle_tank(-1)
                        return
                    elif self._tank_arrow_rect(1).collidepoint(mx, my):
                        self._cycle_tank(1)
                        return
                rects = self._button_rects()
                for i, r in enumerate(rects):
                    if r.collidepoint(mx, my) and self.buttons[i].get("enabled", True):
                        self._trigger(self.buttons[i]["id"])
                        return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.hover_idx = (self.hover_idx - 1) % len(self.buttons)
                    self._ensure_valid_hover()
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.hover_idx = (self.hover_idx + 1) % len(self.buttons)
                    self._ensure_valid_hover()
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if 0 <= self.hover_idx < len(self.buttons):
                        if self.buttons[self.hover_idx].get("enabled", True):
                            self._trigger(self.buttons[self.hover_idx]["id"])
                elif event.key == pygame.K_ESCAPE:
                    self._trigger("quit")
                elif event.key == pygame.K_1:
                    self._trigger("story")
                elif event.key == pygame.K_2:
                    self._trigger("endless")
                elif event.key == pygame.K_3:
                    self._trigger("bossrush")
                elif event.key == pygame.K_4:
                    self._trigger("codex")
                elif event.key in (pygame.K_q, pygame.K_e):
                    self._cycle_tank(1 if event.key == pygame.K_e else -1)
        elif self.mode == "upgrade":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1: self._pick_upgrade(0)
                elif event.key == pygame.K_2: self._pick_upgrade(1)
                elif event.key == pygame.K_3: self._pick_upgrade(2)
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    if self.gs.level_upgrade_choices:
                        self._pick_upgrade(0)  # 默认选第一个
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                cards = self.gs.level_upgrade_choices
                if cards:
                    # 与 _draw_upgrade_modal 完全一致的布局 (否则点不中卡片)
                    card_w, card_h = 260, 320
                    total_w = card_w * 3 + 40 * 2
                    start_x = (SCREEN_WIDTH - total_w) // 2
                    y = 420
                    for i in range(len(cards)):
                        x = start_x + i * (card_w + 40)
                        r = pygame.Rect(x, y, card_w, card_h)
                        if r.collidepoint(mx, my):
                            self._pick_upgrade(i)
                            break

    def _ensure_valid_hover(self):
        if self.hover_idx < 0:
            self.hover_idx = 0
        tries = 0
        while not self.buttons[self.hover_idx].get("enabled", True) and tries < len(self.buttons):
            self.hover_idx = (self.hover_idx + 1) % len(self.buttons)
            tries += 1

    def _button_rects(self):
        rects = []
        x = MENU_BTN_X
        y = MENU_BTN_Y0
        for i, b in enumerate(self.buttons):
            r = pygame.Rect(x, y, MENU_BTN_W, MENU_BTN_H)
            rects.append(r)
            y += MENU_BTN_H + MENU_BTN_GAP
        self._rects_cache = rects
        return rects

    def _trigger(self, btn_id):
        if self.game and hasattr(self.game, "audio") and self.game.audio:
            try:
                self.game.audio.play_sfx("button")
            except Exception:
                pass
        if btn_id == "story":
            self.gs.new_game(GameMode.STORY, level=1)
            self.game.start_level(1)
        elif btn_id == "endless":
            self.gs.new_game(GameMode.ENDLESS, level=1)
            self.game.start_level(1)
        elif btn_id == "bossrush":
            self.gs.new_game(GameMode.BOSS_RUSH, level=5)
            self.game.start_level(5)
        elif btn_id == "codex":
            self.mode = "codex"
            self.codex_ui.open("hub")
        elif btn_id == "quit":
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def draw_menu(self):
        if self.gs.phase == GamePhase.LEVEL_UPGRADE:
            self.mode = "upgrade"
        if self.mode == "codex":
            self.codex_ui.draw()
            return
        # 用内部分辨率渲染
        orig_screen = self.screen
        self.screen = self._internal
        self._draw_menu_bg()
        if self.mode == "main":
            self._draw_title()
            self._draw_menu_buttons()
            self._draw_tank_selector()
            self._draw_tips()
            self._draw_god_mode_switch()
        elif self.mode == "upgrade":
            self._draw_upgrade_modal()
        self.screen = orig_screen
        # 缩放到窗口
        dw = self.screen.get_width()
        dh = self.screen.get_height()
        src_w, src_h = SCREEN_WIDTH, SCREEN_HEIGHT
        scale = min(dw / src_w, dh / src_h)
        sw = int(src_w * scale)
        sh = int(src_h * scale)
        ox = (dw - sw) // 2
        oy = (dh - sh) // 2
        self.screen.fill(BG_DEEP)
        scaled = pygame.transform.smoothscale(self._internal, (sw, sh))
        self.screen.blit(scaled, (ox, oy))

    def _draw_menu_bg(self):
        # 极简: 纯色背景 + 缓慢漂移的网格 (仅菜单动, 关卡内静态)
        self.screen.fill(BG_DEEP)
        step = 80
        t = pygame.time.get_ticks()
        ox = int(t * 0.030) % step   # 横线向右移 ~30px/s
        oy = int(t * 0.020) % step   # 竖线向下移 ~20px/s
        for x in range(-step, SCREEN_WIDTH + step, step):
            pygame.draw.line(self.screen, BG_GRID, (x + ox, 0),
                             (x + ox, SCREEN_HEIGHT), 1)
        for y in range(-step, SCREEN_HEIGHT + step, step):
            pygame.draw.line(self.screen, BG_GRID, (0, y + oy),
                             (SCREEN_WIDTH, y + oy), 1)
        self._update_draw_bg_bullets()

    def _update_draw_bg_bullets(self):
        """背景创意飞弹: 8 种炮弹随机从左右屏外发射横穿画面, 出屏即消失"""
        self._bg_tick += 1
        self._bg_bullet_timer -= 1
        if self._bg_bullet_timer <= 0 and len(self._bg_bullets) < 6:
            bt = random.choice(list(BULLET_CONFIG.keys()))
            if random.random() < 0.22:
                # 少量从右侧向左飞
                b = {"t": bt, "x": SCREEN_WIDTH + 50.0,
                     "vx": -random.uniform(3.2, 7.0), "flip": True}
            else:
                b = {"t": bt, "x": -50.0,
                     "vx": random.uniform(3.2, 7.0), "flip": False}
            b.update({"y": random.uniform(90, SCREEN_HEIGHT - 130),
                      "vy": random.uniform(-0.6, 0.6),
                      "ph": random.uniform(0, math.pi * 2)})
            self._bg_bullets.append(b)
            self._bg_bullet_timer = random.randint(26, 62)
        for b in self._bg_bullets[:]:
            b["x"] += b["vx"]
            b["y"] += b["vy"] + math.sin(self._bg_tick * 0.05 + b["ph"]) * 0.6
            if b["x"] < -80 or b["x"] > SCREEN_WIDTH + 80:
                self._bg_bullets.remove(b)
                continue
            img = get_bullet_image(b["t"], (46, 46))
            if img is None:
                continue
            try:
                im = img.copy()
                if b.get("flip"):
                    im = pygame.transform.flip(im, True, False)
                im.set_alpha(185)
                self.screen.blit(im, im.get_rect(
                    center=(int(b["x"]), int(b["y"]))))
            except Exception:
                self.screen.blit(img, img.get_rect(
                    center=(int(b["x"]), int(b["y"]))))

    def _draw_title_particles(self):
        """标题动态粒子: 灰白微尘在标题字面上缓慢上飘 + 左右轻摆 + 明暗呼吸"""
        t = pygame.time.get_ticks()
        for p in self._title_particles:
            p["y"] -= p["spd"]
            if p["y"] < 52:
                p["y"] = 258
                p["x"] = random.uniform(120, SCREEN_WIDTH - 120)
            tw = 0.5 + 0.5 * math.sin(t * 0.0012 + p["ph"])
            c = min(235, int(p["base"] + 55 * tw))
            x = p["x"] + math.sin(t * 0.0006 + p["ph"]) * p["amp"]
            pygame.draw.circle(self.screen, (c, c, c),
                               (int(x), int(p["y"])), max(1, int(p["r"])))

    def _draw_title(self):
        # 封面式大标题: 逐字渲染 + 宽字距 (参考极简塔防的舒展排版)
        # 动态粒子画在标题文字之后、副标题之前
        title = "钢铁前线"
        gap = 48                      # 字间距 (px)
        sub = "STEEL · FRONTIER"
        sub_gap = 8

        def _draw_spaced(font, text, g, y, color):
            widths = [font.size(ch)[0] for ch in text]
            total = sum(widths) + g * (len(text) - 1)
            x = (SCREEN_WIDTH - total) // 2
            for ch, w in zip(text, widths):
                s = font.render(ch, True, color)
                self.screen.blit(s, (x, y))
                x += w + g
            return total

        _draw_spaced(self.font_title, title, gap, 80, TEXT_PRIMARY)
        self._draw_title_particles()
        _draw_spaced(self.font_small, sub, sub_gap, 218, TEXT_DIM)
        tag = self.font_small.render("版本 1.0 · Solo Builder Edition", True, TEXT_MUTED)
        self.screen.blit(tag, (SCREEN_WIDTH - tag.get_width() - 20, SCREEN_HEIGHT - 30))

    def _draw_page_title(self, title):
        """列表页大标题 (更多/图鉴页)"""
        s = self.font_title.render(title, True, TEXT_PRIMARY)
        self.screen.blit(s, ((SCREEN_WIDTH - s.get_width()) // 2, 110))

    def _draw_page_hint(self, text):
        t = self.font_small.render(text, True, TEXT_MUTED)
        self.screen.blit(t, ((SCREEN_WIDTH - t.get_width()) // 2,
                             SCREEN_HEIGHT - 60))

    def _draw_menu_buttons(self):
        rects = self._button_rects()
        for i, (b, r) in enumerate(zip(self.buttons, rects)):
            hover = i == self.hover_idx and b.get("enabled", True)
            border = ACCENT if hover else TEXT_DIM
            text_c = ACCENT if hover else TEXT_PRIMARY
            try:
                panel = pygame.Surface(r.size, pygame.SRCALPHA)
                alpha = 255 if b.get("enabled", True) else 140
                panel.fill((*BG_PANEL, alpha))
                pygame.draw.rect(panel, border, (0, 0, r.w, r.h),
                                 1, border_radius=4)
                self.screen.blit(panel, r.topleft)
            except Exception:
                pygame.draw.rect(self.screen, BG_PANEL, r)
                pygame.draw.rect(self.screen, border, r, 1)
            tx = self.font.render(b["text"], True, text_c)
            self.screen.blit(tx, (r.x + 28, r.y + (r.h - tx.get_height()) // 2))
            key = b.get("key", "")
            if key:
                kt = self.font_small.render(key, True, TEXT_MUTED)
                self.screen.blit(kt, (r.x + r.w - kt.get_width() - 22,
                                      r.y + (r.h - kt.get_height()) // 2))

    def _cycle_tank(self, direction):
        colors = SELECTABLE_TANK_COLORS
        try:
            idx = colors.index(self.gs.selected_tank_color)
        except ValueError:
            idx = 0
        self.gs.selected_tank_color = colors[(idx + direction) % len(colors)]
        if self.game and hasattr(self.game, "audio") and self.game.audio:
            try:
                self.game.audio.play_sfx("button")
            except Exception:
                pass

    def _tank_arrow_rect(self, side):
        # side=-1 左箭头, side=1 右箭头
        cy = TANK_STRIP_Y + TANK_STRIP_H // 2
        if side < 0:
            return pygame.Rect(TANK_STRIP_X + 16, cy - 24, 48, 48)
        return pygame.Rect(TANK_STRIP_X + TANK_STRIP_W - 64, cy - 24, 48, 48)

    def _draw_tank_selector(self):
        color = self.gs.selected_tank_color
        cfg = TANK_COLOR_CONFIG[color]
        panel = pygame.Rect(TANK_STRIP_X, TANK_STRIP_Y, TANK_STRIP_W, TANK_STRIP_H)
        # 标题小字
        ttitle = self.font_small.render("选择你的坦克", True, TEXT_MUTED)
        self.screen.blit(ttitle, (panel.x + (panel.w - ttitle.get_width()) // 2,
                                  panel.y - 28))
        try:
            ps = pygame.Surface(panel.size, pygame.SRCALPHA)
            ps.fill((*BG_PANEL, 255))
            pygame.draw.rect(ps, TEXT_DIM, (0, 0, panel.w, panel.h),
                             1, border_radius=4)
            self.screen.blit(ps, panel.topleft)
        except Exception:
            pygame.draw.rect(self.screen, BG_PANEL, panel)
            pygame.draw.rect(self.screen, TEXT_DIM, panel, 1)
        # 左右箭头
        mx, my = self._window_to_internal(*pygame.mouse.get_pos())
        for side, sym in ((-1, "<"), (1, ">")):
            r = self._tank_arrow_rect(side)
            hover = r.collidepoint(mx, my)
            c = ACCENT if hover else TEXT_DIM
            try:
                ar = pygame.Surface(r.size, pygame.SRCALPHA)
                ar.fill((*BG_PANEL, 255))
                pygame.draw.rect(ar, c, (0, 0, r.w, r.h), 1, border_radius=4)
                self.screen.blit(ar, r.topleft)
            except Exception:
                pygame.draw.rect(self.screen, BG_PANEL, r)
                pygame.draw.rect(self.screen, c, r, 1)
            t = self.font_big.render(sym, True, c)
            self.screen.blit(t, (r.x + (r.w - t.get_width()) // 2,
                                 r.y + (r.h - t.get_height()) // 2))
        # 3D 坦克图 (缩小, 居中偏左)
        img = get_tank_view3d(color, (96, 96))
        if img is not None:
            ir = img.get_rect(center=(panel.x + 118, panel.y + panel.h // 2 + 4))
            self.screen.blit(img, ir)
        # 名称 + 弹药 (图右侧, 行距拉开)
        name = self.font_big.render(cfg["name"], True, cfg["rgb"])
        self.screen.blit(name, (panel.x + 196, panel.y + 16))
        bcfg = BULLET_CONFIG[cfg["bullet_type"]]
        btxt = self.font_small.render("弹药: " + bcfg["name"], True, TEXT_PRIMARY)
        self.screen.blit(btxt, (panel.x + 196, panel.y + 70))
        hint = self.font_small.render("按 Q / E 或点击箭头切换", True, TEXT_MUTED)
        self.screen.blit(hint, (panel.x + 196, panel.y + 100))

    def _draw_tips(self):
        tips = (
            "WASD 移动 · 鼠标右键射击      "
            f"历史最高分 {self.gs.high_score} · 最远通关 第{self.gs.max_unlocked_level}关"
        )
        t = self.font_small.render(tips, True, TEXT_MUTED)
        self.screen.blit(t, ((SCREEN_WIDTH - t.get_width()) // 2, 960))

    def _draw_god_mode_switch(self):
        """右上角无敌模式小字开关 (极简)"""
        x, y = SCREEN_WIDTH - 260, 28
        w, h = 240, 40
        on = self.gs.god_mode
        label = f"无敌模式: {'开' if on else '关'}"
        color = NEON_RED if on else TEXT_DIM
        txt = self.font_small.render(label, True, color)
        try:
            bg_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            bg_surf.fill((*BG_PANEL, 220))
            pygame.draw.rect(bg_surf, color, (0, 0, w, h), 1, border_radius=4)
            self.screen.blit(bg_surf, (x, y))
        except Exception:
            pygame.draw.rect(self.screen, BG_PANEL, (x, y, w, h))
            pygame.draw.rect(self.screen, color, (x, y, w, h), 1)
        self.screen.blit(txt, (x + (w - txt.get_width()) // 2,
                               y + (h - txt.get_height()) // 2))
        self._god_rect = pygame.Rect(x, y, w, h)
        # 瞄准模式开关 (手机版: 手动右轮盘 / 自动锁敌), 无敌开关下方
        y2 = y + h + 10
        auto = getattr(self.gs, "aim_mode", "manual") == "auto"
        label2 = "手机瞄准: " + ("自动锁敌" if auto else "手动轮盘")
        color2 = ACCENT if auto else TEXT_DIM
        txt2 = self.font_small.render(label2, True, color2)
        try:
            bg2 = pygame.Surface((w, h), pygame.SRCALPHA)
            bg2.fill((*BG_PANEL, 220))
            pygame.draw.rect(bg2, color2, (0, 0, w, h), 1, border_radius=4)
            self.screen.blit(bg2, (x, y2))
        except Exception:
            pygame.draw.rect(self.screen, BG_PANEL, (x, y2, w, h))
            pygame.draw.rect(self.screen, color2, (x, y2, w, h), 1)
        self.screen.blit(txt2, (x + (w - txt2.get_width()) // 2,
                                y2 + (h - txt2.get_height()) // 2))
        self._aim_rect = pygame.Rect(x, y2, w, h)

    def show_upgrade_modal(self, player):
        self.mode = "upgrade"
        self.gs.level_upgrade_choices = self.upgrade_sys.available_upgrades(
            player, 3, level=self.gs.level)

    def _pick_upgrade(self, idx):
        if not self.gs.players:
            return
        cards = self.gs.level_upgrade_choices
        if idx < 0 or idx >= len(cards):
            return
        up = cards[idx]
        for p in self.gs.players:
            self.upgrade_sys.apply_upgrade(p, up)
            # 图鉴发现: 技能 (残卡不记录)
            if up.get("id") not in ("residue_dmg", "residue_hp"):
                self.gs.mark_codex_seen("skill", up["id"])
        self.gs.phase = GamePhase.PLAYING
        self.mode = "main"
        self.build_main_menu()
        if self.game:
            self.game.on_upgrade_confirmed_external()

    def _draw_upgrade_modal(self):
        # 极简: 纯色底, 1px 灰/白边框卡片, 无发光
        self.screen.fill(BG_DEEP)
        # 弹窗整体垂直居中: 标题 + 卡片块在页面上留白上下均衡
        title = self.font_big.render(
            "选择一项强化 (按 1/2/3 或点击)", True, TEXT_PRIMARY)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 340))
        cards = self.gs.level_upgrade_choices
        card_w, card_h = 260, 320
        total_w = card_w * 3 + 40 * 2
        start_x = (SCREEN_WIDTH - total_w) // 2
        y = 420
        mx, my = self._window_to_internal(*pygame.mouse.get_pos())
        for i, up in enumerate(cards):
            x = start_x + i * (card_w + 40)
            r = pygame.Rect(x, y, card_w, card_h)
            hover = r.collidepoint(mx, my)
            rarity = up.get("rarity", "common")
            # 稀有度配色: 普通=白 稀有=蓝 史诗=紫 传说=橙
            rcol = UPGRADE_RARITY_COLORS.get(rarity, TEXT_PRIMARY)
            try:
                panel = pygame.Surface(r.size, pygame.SRCALPHA)
                panel.fill((*BG_PANEL, 255))
                if rarity == "legendary":
                    pygame.draw.rect(panel, rcol, (0, 0, card_w, card_h),
                                     1, border_radius=4)
                    pygame.draw.rect(panel, rcol,
                                     (4, 4, card_w - 8, card_h - 8),
                                     1, border_radius=2)
                else:
                    pygame.draw.rect(panel, rcol, (0, 0, card_w, card_h),
                                     1, border_radius=4)
                self.screen.blit(panel, r.topleft)
            except Exception:
                pygame.draw.rect(self.screen, BG_PANEL, r)
                pygame.draw.rect(self.screen, rcol, r, 1)
            if hover:
                pygame.draw.rect(self.screen, rcol, r, 1, border_radius=4)
            num = self.font_small.render(str(i + 1), True, TEXT_MUTED)
            self.screen.blit(num, (x + card_w - num.get_width() - 14, y + 14))
            rarity_label = {"common": "普通", "rare": "稀有",
                            "epic": "史诗", "legendary": "传说"}.get(rarity, "")
            rt = self.font_small.render(rarity_label, True, rcol)
            self.screen.blit(rt, (x + 14, y + 16))
            pygame.draw.line(self.screen, BG_GRID,
                             (x + 14, y + 48), (x + card_w - 14, y + 48), 1)
            nt = self.font.render(up["name"], True, ACCENT)
            self.screen.blit(nt, (x + card_w // 2 - nt.get_width() // 2, y + 60))
            # 等级徽标: 新技能 Lv1, 升级卡显示升级后的等级, 满级显示 MAX
            nxt = up.get("next_level", 1)
            lv_text = f"Lv {nxt}"
            if up.get("is_max"):
                lv_text += " MAX"
            lvt = self.font_small.render(lv_text, True, rcol)
            self.screen.blit(lvt, (x + card_w // 2 - lvt.get_width() // 2, y + 88))
            # 大图标 (矢量绘制, 按技能语义; 未知技能回退字符)
            icon_surf = render_skill_icon(up["id"], 84, TEXT_PRIMARY)
            if icon_surf is not None:
                self.screen.blit(icon_surf,
                                 (x + card_w // 2 - 42, y + 108))
            else:
                sym = self._upgrade_icon(up["id"])
                big = self.font_icon.render(sym, True, TEXT_PRIMARY)
                self.screen.blit(big, (x + card_w // 2 - big.get_width() // 2,
                                       y + 112))
            dl = self._wrap_lines(up["desc"], 18)
            dy = y + 210
            for line in dl:
                dt = self.font_small.render(line, True, TEXT_PRIMARY)
                self.screen.blit(dt, (x + card_w // 2 - dt.get_width() // 2, dy))
                dy += 22
            key_hint = self.font_small.render(
                f"数字键 {i+1} / 点击卡片", True, TEXT_MUTED)
            self.screen.blit(key_hint,
                              (x + card_w // 2 - key_hint.get_width() // 2,
                               y + card_h - 26))

    def _upgrade_icon(self, uid):
        return UPGRADE_ICONS.get(uid, "U")

    def _wrap_lines(self, text, max_chars):
        lines = []
        cur = ""
        for ch in text:
            cur += ch
            if len(cur) >= max_chars and ch in "，。,.;: ":
                lines.append(cur)
                cur = ""
        if cur:
            lines.append(cur)
        return lines


class ResultOverlay:
    def __init__(self):
        try:
            self.font_huge = load_font(72, bold=True)
            self.font_big = load_font(40, bold=True)
            self.font_num = load_font(28, bold=True)
            self.font = load_font(22, bold=True)
            self.font_small = load_font(18)
        except Exception:
            self.font_huge = pygame.font.Font(None, 72)
            self.font_big = pygame.font.Font(None, 40)
            self.font_num = pygame.font.Font(None, 28)
            self.font = pygame.font.Font(None, 22)
            self.font_small = pygame.font.Font(None, 18)
        self._title_cache_key = None
        self._title_surf = None
        self._anim_t0 = 0

    def reset_anim(self):
        """结算页出现时重置标题入场动画"""
        self._anim_t0 = pygame.time.get_ticks()

    def _build_title_surface(self, title, color):
        """合成优化版大标题: 投影 + 描边 + 垂直渐变填充"""
        font = self.font_huge
        base = font.render(title, True, (255, 255, 255))
        w, h = base.get_size()
        pad = 10
        total = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        # 1) 深色投影 (右下偏移)
        try:
            sh = font.render(title, True, (0, 0, 0))
            sh.set_alpha(150)
            total.blit(sh, (pad + 7, pad + 9))
        except Exception:
            pass
        # 2) 亮色描边 (8 方向偏移)
        for dx, dy in [(-4, 0), (4, 0), (0, -4), (0, 4),
                       (-3, -3), (3, 3), (-3, 3), (3, -3)]:
            o = font.render(title, True, (255, 240, 235))
            total.blit(o, (pad + dx, pad + dy))
        # 3) 垂直渐变填充 (顶部亮 -> 底部暗)
        grad = pygame.Surface((w, h), pygame.SRCALPHA)
        top = tuple(min(255, c + 80) for c in color)
        bottom = tuple(max(30, int(c * 0.3)) for c in color)
        for y in range(h):
            t = y / max(1, h - 1)
            c = (int(top[0] + (bottom[0] - top[0]) * t),
                 int(top[1] + (bottom[1] - top[1]) * t),
                 int(top[2] + (bottom[2] - top[2]) * t))
            pygame.draw.line(grad, (*c, 255), (0, y), (w, y))
        grad.blit(base, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        total.blit(grad, (pad, pad))
        # 4) 顶部高光 (上半部白色微光)
        try:
            hi = pygame.Surface((w, h // 3), pygame.SRCALPHA)
            hi.blit(grad, (0, 0))
            hi.fill((255, 255, 255, 60), special_flags=pygame.BLEND_RGBA_ADD)
            total.blit(hi, (pad, pad))
        except Exception:
            pass
        return total

    def _draw_big_title(self, surface, title, color):
        """绘制优化版大标题: 呼吸辉光 + 入场缩放动画 + 装饰线"""
        key = (title, color)
        if self._title_cache_key != key:
            self._title_surf = self._build_title_surface(title, color)
            self._title_cache_key = key
        s = self._title_surf
        now = pygame.time.get_ticks()
        # 入场动画 (ease-out-back 过冲缩放)
        t_in = min(1.0, (now - self._anim_t0) / 400.0)
        x = t_in - 1
        k = 1 + 2.70158 * x * x * x + 1.70158 * x * x
        scale = 0.5 + 0.5 * max(0.0, min(1.0, k))
        alpha = int(255 * min(1.0, t_in * 1.5))
        sw = max(1, int(s.get_width() * scale))
        sh = max(1, int(s.get_height() * scale))
        try:
            scaled = pygame.transform.smoothscale(s, (sw, sh))
        except Exception:
            scaled = pygame.transform.scale(s, (sw, sh))
        scaled.set_alpha(alpha)
        # 呼吸辉光 (彩色扩散)
        pulse = 0.5 + 0.5 * math.sin(now * 0.004)
        try:
            glow = pygame.Surface((sw + 36, sh + 36), pygame.SRCALPHA)
            for dx, dy in [(-9, 0), (9, 0), (0, -9), (0, 9),
                           (-6, -6), (6, 6), (-6, 6), (6, -6)]:
                glow.blit(scaled, (18 + dx, 18 + dy))
            glow.fill((*color, int(70 + 55 * pulse)),
                      special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(glow, ((SCREEN_WIDTH - glow.get_width()) // 2, 82),
                         special_flags=pygame.BLEND_RGBA_ADD)
        except Exception:
            pass
        tx = (SCREEN_WIDTH - sw) // 2
        ty = 100 + int(3 * math.sin(now * 0.002))  # 轻微浮动
        surface.blit(scaled, (tx, ty))
        # 装饰线: 标题下方霓虹横线 + 两端菱形
        line_y = ty + sh + 8
        lw = min(520, sw + 80)
        lx = (SCREEN_WIDTH - lw) // 2
        try:
            line = pygame.Surface((lw, 4), pygame.SRCALPHA)
            for i in range(lw):
                t = i / max(1, lw - 1)
                fade = int(255 * (1 - abs(2 * t - 1)))
                line.set_at((i, 1), (*color, min(alpha, fade)))
                line.set_at((i, 2), (*color, min(alpha, fade)))
            surface.blit(line, (lx, line_y))
        except Exception:
            pygame.draw.line(surface, color, (lx, line_y + 2), (lx + lw, line_y + 2), 2)
        for sx0 in (lx - 14, lx + lw + 2):
            pts = [(sx0, line_y + 2), (sx0 + 6, line_y - 4), (sx0 + 12, line_y + 2),
                   (sx0 + 6, line_y + 8)]
            try:
                pygame.draw.polygon(surface, color, pts)
            except Exception:
                pass
        return ty + sh

    def draw(self, surface, victory, stats, audio=None):
        # 极简结算页: 半透明遮罩 + 64px 白色大字 + 直排数据
        try:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((*BG_DEEP, 225))
            surface.blit(overlay, (0, 0))
        except Exception:
            pass
        title = "胜  利" if victory else "GAME OVER"
        t = self.font_big.render(title, True, TEXT_PRIMARY)
        surface.blit(t, ((SCREEN_WIDTH - t.get_width()) // 2, 170))
        # 直排数据
        y = 330
        for lab, val in stats:
            lt = self.font.render(f"{lab}    {val}", True, TEXT_PRIMARY)
            surface.blit(lt, ((SCREEN_WIDTH - lt.get_width()) // 2, y))
            y += 48
        hint = self.font_small.render(
            "按 回车/空格 继续或下一关    按 Esc 返回主菜单", True, TEXT_MUTED)
        surface.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2,
                            SCREEN_HEIGHT - 70))
