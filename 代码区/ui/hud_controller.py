# -*- coding: utf-8 -*-
"""
HUD 绘制 (1920×1080 优化版)
"""
import math
import pygame
from core.constants import *
from utils.fonts import load_font
from ui.skill_icons import render_skill_icon


class HUDRenderer:
    def __init__(self):
        try:
            self.font_huge = load_font(36, bold=True)
            self.font_big = load_font(26, bold=True)
            self.font = load_font(20, bold=True)
            self.font_small = load_font(16)
        except Exception:
            self.font_huge = pygame.font.Font(None, 36)
            self.font_big = pygame.font.Font(None, 26)
            self.font = pygame.font.Font(None, 20)
            self.font_small = pygame.font.Font(None, 16)

    def draw(self, surface, game_state, player_tanks, minimap_info=None,
             mouse_pos=None):
        for i, pt in enumerate(player_tanks):
            self._draw_player_panel(surface, pt, i)
        for i, pt in enumerate(player_tanks):
            self._draw_skill_icons(surface, pt, i, mouse_pos)
        for i, pt in enumerate(player_tanks):
            self._draw_buff_bar(surface, player_tanks, i, mouse_pos)
        self._draw_top_center(surface, game_state)
        if game_state.boss and not game_state.boss.dead:
            self._draw_boss_bar(surface, game_state.boss)
        if game_state.combo >= 3:
            self._draw_combo(surface, game_state.combo)
        if minimap_info:
            self._draw_minimap(surface, minimap_info)

    def _draw_player_panel(self, surface, ptank, idx):
        # 加大面板: 320×128, 1px 灰边 + 细血条
        pd = ptank.data
        x = 30 if idx == 0 else SCREEN_WIDTH - 350
        y = 30
        w, h = 320, 128
        try:
            panel = pygame.Surface((w, h), pygame.SRCALPHA)
            panel.fill((*BG_PANEL, 255))
            pygame.draw.rect(panel, TEXT_DIM, (0, 0, w, h), 1, border_radius=4)
            surface.blit(panel, (x, y))
        except Exception:
            pygame.draw.rect(surface, BG_PANEL, (x, y, w, h))
            pygame.draw.rect(surface, TEXT_DIM, (x, y, w, h), 1)
        # 坦克圆形头像徽章 (大)
        try:
            from utils.assets import get_tank_avatar
            av = get_tank_avatar(pd.tank_color, 32)
            cx, cy = x + 34, y + 42
            if av is not None:
                pygame.draw.circle(surface, pd.color, (cx, cy), 19, 1)
                surface.blit(av, av.get_rect(center=(cx, cy)))
            else:
                pygame.draw.circle(surface, pd.color, (cx, cy), 9)
        except Exception:
            pygame.draw.circle(surface, pd.color, (x + 34, y + 42), 9)
        tname = TANK_COLOR_CONFIG.get(pd.tank_color, {}).get("name", "")
        title = self.font.render(f"P{idx + 1}  {tname}", True, TEXT_PRIMARY)
        surface.blit(title, (x + 64, y + 12))
        bname = BULLET_CONFIG[pd.bullet_type]["name"]
        info = self.font_small.render(
            f"分 {pd.score} · 杀 {pd.kills} · 弹药 {bname}", True, TEXT_DIM)
        surface.blit(info, (x + 64, y + 52))
        # 细血条 (加高到 8px)
        hp_w = w - 32
        hx, hy = x + 16, y + 92
        pygame.draw.rect(surface, (56, 56, 64), (hx, hy, hp_w, 8))
        ratio = max(0, pd.hp / pd.max_hp)
        c = NEON_GREEN if ratio > 0.5 else (NEON_YELLOW if ratio > 0.25 else NEON_RED)
        if ratio > 0:
            pygame.draw.rect(surface, c, (hx, hy, int(hp_w * ratio), 8))
        hp_txt = self.font_small.render(
            f"HP {pd.hp}/{pd.max_hp}" + (f"  盾 {pd.shield}" if pd.shield > 0 else ""),
            True, TEXT_DIM)
        surface.blit(hp_txt, (hx, hy + 12))

    def _draw_skill_icons(self, surface, ptank, idx, mouse_pos=None):
        """左下角技能栏: 已获技能小图标 (Lv>1 时右下角显示等级/MAX);
        鼠标悬停时显示技能名称与等级提示"""
        pd = ptank.data
        levels = getattr(pd, "upgrade_levels", None) or {}
        if not levels:
            return
        try:
            from systems.upgrade_system import (UPGRADE_ICONS, UPGRADE_POOL,
                                                RESIDUE_POOL, UPGRADE_RARITY_COLORS)
        except Exception:
            UPGRADE_ICONS, UPGRADE_POOL, RESIDUE_POOL, UPGRADE_RARITY_COLORS = {}, [], [], {}
        names = {u["id"]: u["name"] for u in (UPGRADE_POOL + RESIDUE_POOL)}
        rarity_of = {u["id"]: u["rarity"] for u in (UPGRADE_POOL + RESIDUE_POOL)}
        max_of = {u["id"]: len(u["levels"]) for u in (UPGRADE_POOL + RESIDUE_POOL)}
        icon, gap, step = 40, 6, 46
        per_row = 14        # 两行制: 每行 14 个, 28 技能恰好两行装完, 不再向上堆叠
        items = sorted(levels.items())[:28]  # 硬上限 28, 防异常存档溢出
        hover_info = None
        for i, (uid, lv) in enumerate(items):
            col, row = i % per_row, i // per_row
            if idx == 0:
                # P1: 左下角, 从左往右排, 两行向上堆叠 (硬钳制, 永不越界)
                x = max(10, min(SCREEN_WIDTH - icon - 10,
                                30 + col * step))
                y = max(140, SCREEN_HEIGHT - 30 - icon - row * step)
            else:
                # P2: 右下角镜像
                x = max(10, min(SCREEN_WIDTH - icon - 10,
                                SCREEN_WIDTH - 30 - icon - col * step))
                y = max(140, SCREEN_HEIGHT - 30 - icon - row * step)
            # 按稀有度着色边框 (2px): 普通=白 稀有=蓝 史诗=紫 传说=橙+内环
            rarity = rarity_of.get(uid, "common")
            rcol = UPGRADE_RARITY_COLORS.get(rarity, TEXT_PRIMARY)
            pygame.draw.rect(surface, BG_PANEL, (x, y, icon, icon))
            pygame.draw.rect(surface, rcol, (x, y, icon, icon), 2,
                             border_radius=2)
            if rarity == "legendary":
                pygame.draw.rect(surface, rcol,
                                 (x + 4, y + 4, icon - 8, icon - 8),
                                 1, border_radius=1)
            # 矢量技能图标 (按语义绘制, 未知技能回退字符)
            ic = render_skill_icon(uid, icon - 8, rcol)
            if ic is not None:
                surface.blit(ic, (x + 4, y + 4))
            else:
                sym = UPGRADE_ICONS.get(uid, "?")
                st = self.font.render(sym, True, rcol)
                surface.blit(st, (x + (icon - st.get_width()) // 2,
                                  y + (icon - st.get_height()) // 2))
            if lv > 1:
                if lv >= max_of.get(uid, 999):
                    lvt = self.font_small.render("MAX", True, NEON_YELLOW)
                else:
                    lvt = self.font_small.render(str(lv), True, TEXT_PRIMARY)
                surface.blit(lvt, (x + icon - lvt.get_width() - 2,
                                   y + icon - lvt.get_height() - 1))
            if mouse_pos is not None:
                mx, my = mouse_pos
                if x <= mx <= x + icon and y <= my <= y + icon:
                    hover_info = (x, y, names.get(uid, uid), lv)
        # 悬停提示: 技能名称 + 等级
        if hover_info:
            x, y, name, lv = hover_info
            txt = self.font_small.render(f"{name} Lv {lv}", True, TEXT_PRIMARY)
            tw, th = txt.get_width() + 16, txt.get_height() + 8
            tx = min(max(0, x + icon // 2 - tw // 2), SCREEN_WIDTH - tw)
            ty = y - th - 6 if y - th - 6 > 0 else y + icon + 6
            try:
                panel = pygame.Surface((tw, th), pygame.SRCALPHA)
                panel.fill((*BG_PANEL, 255))
                pygame.draw.rect(panel, TEXT_PRIMARY, (0, 0, tw, th), 1,
                                 border_radius=2)
                surface.blit(panel, (tx, ty))
            except Exception:
                pygame.draw.rect(surface, BG_PANEL, (tx, ty, tw, th))
            surface.blit(txt, (tx + 8, ty + 4))

    def _draw_buff_bar(self, surface, player_tanks, idx, mouse_pos=None):
        """屏幕右下角 (P2 镜像左下角): 限时道具效果图标 + 倒计时 + 悬停说明。
        框色: 蓝=加成, 红=惩罚, 金=无敌星"""
        pd = player_tanks[idx].data
        buffs = getattr(pd, "timed_buffs", None) or {}
        if not buffs:
            return
        ring_blue = (70, 140, 255)
        ring_gold = (255, 190, 40)
        # (key, mult) -> (符号, 框色, 符号色, 名称, 效果说明)
        meta = {
            ("damage", 1.5): ("攻", ring_blue, NEON_RED, "火力强化", "伤害 ×1.5"),
            ("damage", 0.6): ("锈", NEON_RED, NEON_RED, "锈蚀弹头", "伤害 ×0.6"),
            ("rapid", 0.6): ("速", ring_blue, NEON_YELLOW, "急速射击",
                             "射击间隔 -40%"),
            ("rapid", 1.5): ("卡", NEON_RED, (150, 150, 155), "履带卡壳",
                             "射击间隔 +50%"),
            ("speed", 1.3): ("移", ring_blue, NEON_ORANGE, "涡轮引擎",
                             "移速 ×1.3"),
            ("invincible", 1.0): ("★", ring_gold, ring_gold, "无敌星",
                                  "免疫伤害"),
            ("reverse", 1.0): ("反", NEON_RED, NEON_PURPLE, "反向操控",
                               "移动方向颠倒"),
        }
        icon, gap = 40, 6
        per_row = 8
        # 该角落被另一玩家技能图标占用的行数 → 整体上移让位
        occupy = 0
        if len(player_tanks) > 1:
            other = player_tanks[1 - idx]
            olv = getattr(other.data, "upgrade_levels", None) or {}
            if olv:
                occupy = (len(olv) + per_row - 1) // per_row
        y = SCREEN_HEIGHT - 30 - icon - occupy * 46 - 8
        items = sorted(buffs.items())
        rects = []  # (x, y, name, desc, ring)
        for i, (key, b) in enumerate(items):
            if not isinstance(b, dict):
                continue
            mult = round(b.get("mult", 1.0), 2)
            sym, ring, sym_color, name, desc = meta.get(
                (key, mult), ("?", ring_blue, TEXT_PRIMARY, key, ""))
            if idx == 0:
                # 右下角: 右对齐, 向左延伸
                x = SCREEN_WIDTH - 30 - icon - i * (icon + gap)
            else:
                # P2: 左下角镜像
                x = 30 + i * (icon + gap)
            cx, cy = x + icon // 2, y + icon // 2
            pygame.draw.circle(surface, (255, 255, 255), (cx, cy), icon // 2)
            pygame.draw.circle(surface, ring, (cx, cy), icon // 2, 2)
            st = self.font.render(sym, True, sym_color)
            surface.blit(st, (x + (icon - st.get_width()) // 2,
                              y + (icon - st.get_height()) // 2))
            secs = max(0, int(math.ceil(b["ms"] / 1000)))
            tt = self.font_small.render(f"{secs}s", True, TEXT_PRIMARY)
            surface.blit(tt, (x + (icon - tt.get_width()) // 2, y + icon + 2))
            rects.append((x, y, name, desc, ring))
        # 光标触碰: 显示效果名称与说明
        if mouse_pos is not None:
            mx, my = mouse_pos
            for (x, y, name, desc, ring) in rects:
                if x <= mx <= x + icon and y <= my <= y + icon:
                    txt = self.font_small.render(
                        f"{name}  {desc}", True, TEXT_PRIMARY)
                    tw = txt.get_width() + 16
                    th = txt.get_height() + 8
                    tx = min(max(0, x + icon // 2 - tw // 2),
                             SCREEN_WIDTH - tw)
                    ty = y - th - 6 if y - th - 6 > 0 else y + icon + 6
                    try:
                        panel = pygame.Surface((tw, th), pygame.SRCALPHA)
                        panel.fill((*BG_PANEL, 255))
                        pygame.draw.rect(panel, ring, (0, 0, tw, th), 1,
                                         border_radius=2)
                        surface.blit(panel, (tx, ty))
                    except Exception:
                        pygame.draw.rect(surface, BG_PANEL, (tx, ty, tw, th))
                    surface.blit(txt, (tx + 8, ty + 4))
                    break

    def _draw_top_center(self, surface, gs):
        # 极简顶栏两行: 主行=关卡/波次进度, 次行=章节/模式/分数 (加大字号)
        info = f"关卡 {gs.level}"
        wv = gs.wave
        if not gs.boss:
            info += (f" · 波次 {wv.current}/{wv.total_waves}"
                     f" ({wv.enemies_killed}/{wv.enemies_total})")
        else:
            info += " · Boss 战"
        txt = self.font_big.render(info, True, TEXT_PRIMARY)
        surface.blit(txt, ((SCREEN_WIDTH - txt.get_width()) // 2, 12))
        mn = {"endless": "无尽", "bossrush": "Boss Rush", "coop": "双人合作",
              "story": story_chapter(gs.level)}.get(gs.mode.value, "")
        total_score = sum(p.score for p in gs.players)
        sub = f"{mn} · 分数 {total_score} · 最高 {gs.high_score}"
        stxt = self.font.render(sub, True, TEXT_MUTED)
        surface.blit(stxt, ((SCREEN_WIDTH - stxt.get_width()) // 2, 48))

    def _draw_boss_bar(self, surface, boss):
        # 极简 Boss 条: 底部居中细条 + 1px 白边
        w, h = SCREEN_WIDTH - 500, 16
        x, y = 250, SCREEN_HEIGHT - 120
        name = self.font.render(boss.name, True, TEXT_PRIMARY)
        surface.blit(name, (x, y - 30))
        phase_txt = self.font_small.render(f"阶段 {boss.phase}", True, TEXT_DIM)
        surface.blit(phase_txt, (x + w - phase_txt.get_width(), y - 30))
        pygame.draw.rect(surface, (56, 56, 64), (x, y, w, h))
        ratio = max(0, boss.hp / boss.max_hp)
        if ratio > 0:
            pygame.draw.rect(surface, ACCENT, (x, y, int(w * ratio), h))
        pygame.draw.rect(surface, ACCENT, (x, y, w, h), 1)

    def _draw_combo(self, surface, combo):
        txt = self.font.render(f"{combo} 连击!", True, TEXT_PRIMARY)
        surface.blit(txt, ((SCREEN_WIDTH - txt.get_width()) // 2, 78))

    def _draw_minimap(self, surface, info):
        mw, mh = 200, 140
        mx, my = SCREEN_WIDTH - mw - 30, 170
        try:
            pygame.draw.rect(surface, BG_PANEL, (mx - 4, my - 4, mw + 8, mh + 8))
            pygame.draw.rect(surface, TEXT_DIM,
                             (mx - 4, my - 4, mw + 8, mh + 8), 1, border_radius=4)
        except Exception:
            pygame.draw.rect(surface, BG_PANEL, (mx - 4, my - 4, mw + 8, mh + 8))
            pygame.draw.rect(surface, TEXT_DIM, (mx - 4, my - 4, mw + 8, mh + 8), 1)
        mm = pygame.Surface((mw, mh), pygame.SRCALPHA)
        mm.fill((0, 0, 0, 0))
        scale_x = mw / (MAP_COLS * TILE_SIZE)
        scale_y = mh / (MAP_ROWS * TILE_SIZE)
        for w in info.get("walls", []):
            if w.type == WallType.GRASS:
                continue
            # 可通行的地块 (水渍/泥沼/冰面/尖刺/传送门) 不画成障碍
            if WALL_CONFIG[w.type].get("tank_pass"):
                continue
            pygame.draw.rect(mm, (120, 120, 128),
                             (max(0, w.x * scale_x), max(0, w.y * scale_y),
                              max(1, w.width * scale_x), max(1, w.height * scale_y)))
        for e in info.get("enemies", []):
            if getattr(e, "dead", False):
                continue
            pygame.draw.circle(mm, TEXT_DIM,
                               (int(e.x * scale_x), int(e.y * scale_y)), 2)
        b = info.get("boss")
        if b and not getattr(b, "dead", False):
            pygame.draw.rect(mm, ACCENT,
                             (max(0, int((b.x - b.width / 2) * scale_x)),
                              max(0, int((b.y - b.height / 2) * scale_y)),
                              max(3, int(b.width * scale_x)),
                              max(3, int(b.height * scale_y))), 1)
        for p in info.get("players", []):
            if getattr(p, "dead", False):
                continue
            pygame.draw.circle(mm, p.color,
                               (int(p.x * scale_x), int(p.y * scale_y)), 3)
        surface.blit(mm, (mx, my))
