# -*- coding: utf-8 -*-
"""
游戏图鉴 UI (方舟结构 × 极简塔防皮肤)
- hub: 图鉴总览 (左侧预览橱窗 + 右侧分类行 + 收集进度)
- cat: 统一分类页 (右网格 + 左档案面板 + 顶部筛选页签)
- boss: 敌人图鉴 (首领 5 圆立绘圆盘 / 敌军 6 卡, Tab 切换)
- skill: 技能图鉴 (左技能图 + 右技能解析 + 稀有度页签)
"""
import math
import pygame
from core.constants import (SCREEN_WIDTH, SCREEN_HEIGHT, BG_DEEP, BG_PANEL,
                            BG_GRID, TEXT_PRIMARY, TEXT_DIM, TEXT_MUTED,
                            ACCENT, BULLET_CONFIG, BulletType, TankColor,
                            WallType, TANK_COLOR_CONFIG)
from core.game_state import GamePhase
from systems.upgrade_system import UPGRADE_RARITY_COLORS
from entities.boss import BOSS_CONFIG
from entities.pickup import (PICKUP_CONFIG, PickupType, RING_REWARD,
                             RING_PENALTY, _render_symbol)
from entities.wall import _get_texture
from utils.assets import (get_tank_view3d, get_tank_top_view,
                          get_bullet_image, get_boss_image, _circular_crop)
from utils.fonts import load_font
from ui.codex_data import (CODEX, CODEX_CATEGORIES, SEEN_MAP, codex_total,
                           K_TANK, K_BULLET, K_BOSS, K_ENEMY, K_SKILL,
                           K_PICKUP, K_TILE, TILE_NAMES, TILE_TEXTURES)
from ui.skill_icons import render_skill_icon

# 分类页签配置: {分类 id: [(页签文字, 过滤函数组名)]}
CAT_TABS = {
    "pickup": [("全部", None), ("奖励", "奖励"), ("惩罚", "惩罚")],
    "bullet": [("全部", None), ("我方", "我方"), ("敌方", "敌方")],
    "tile": [("全部", None), ("方块", "方块"), ("地块", "地块")],
    "tank": [], "enemy": [],
}
SKILL_TABS = [("全部", None, TEXT_PRIMARY),
              ("普通", "common", UPGRADE_RARITY_COLORS["common"]),
              ("稀有", "rare", UPGRADE_RARITY_COLORS["rare"]),
              ("史诗", "epic", UPGRADE_RARITY_COLORS["epic"]),
              ("传说", "legendary", UPGRADE_RARITY_COLORS["legendary"])]
RARITY_BADGE = {"common": "普通", "rare": "稀有", "epic": "史诗",
                "legendary": "传说"}

CAT_GRID_COLS = 4
CAT_CARD_W = 250
CAT_CARD_H = 160
CAT_CARD_GAP = 24
CAT_GRID_X = 740
CAT_GRID_Y = 250
CAT_ROWS = 3
CAT_PER_PAGE = CAT_GRID_COLS * CAT_ROWS

# 图鉴总览右侧: 2 列 × 3 行大卡片 (每列三个)
HUB_CARD_W = 495
HUB_CARD_H = 175
HUB_GAP_X = 30
HUB_GAP_Y = 20
HUB_X = 840
HUB_Y = 300


class CodexUI:
    def __init__(self, screen, gs, game):
        self.screen = screen
        self._win = screen          # 真实窗口 (draw 时会切换 self.screen 到内部分辨率表面, 鼠标换算必须用窗口尺寸)
        self.gs = gs
        self.game = game
        self._internal = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        try:
            self.f_title = load_font(96, bold=True)
            self.f_big = load_font(36, bold=True)
            self.f_30 = load_font(30, bold=True)
            self.f_name = load_font(28, bold=True)
            self.f_stat = load_font(26, bold=True)
            self.f = load_font(22, bold=True)
            self.f_mid = load_font(20)
            self.f_small = load_font(16)
            self.f_icon = load_font(150, bold=True)
            self.f_icon_mid = load_font(72, bold=True)
            self.f_q = load_font(56, bold=True)
        except Exception:
            self.f_title = pygame.font.Font(None, 96)
            self.f_big = pygame.font.Font(None, 36)
            self.f_30 = pygame.font.Font(None, 30)
            self.f_name = pygame.font.Font(None, 28)
            self.f_stat = pygame.font.Font(None, 26)
            self.f = pygame.font.Font(None, 22)
            self.f_mid = pygame.font.Font(None, 20)
            self.f_small = pygame.font.Font(None, 16)
            self.f_icon = pygame.font.Font(None, 150)
            self.f_icon_mid = pygame.font.Font(None, 72)
            self.f_q = pygame.font.Font(None, 56)
        self.view = "hub"          # hub / cat / boss / skill
        self.cat_id = "pickup"
        self.hub_idx = 0
        self.cat_tab = 0
        self.cat_idx = 0
        self.boss_tab = "boss"     # boss / grunt
        self.boss_idx = 0
        self.grunt_idx = 0
        self.skill_tab = 0
        self.skill_idx = 0
        self._pickup_icon_cache = {}
        self._enemy_prev_cache = {}
        self._page_rects = (None, None)

    # ------------------------------------------------------------
    # 基础工具
    # ------------------------------------------------------------
    def _mouse(self):
        """窗口鼠标坐标 → 内部分辨率坐标 (必须用真实窗口尺寸, draw 期间 self.screen 是内部表面)"""
        mx, my = pygame.mouse.get_pos()
        win = self._win if self._win is not None else self.screen
        dw = win.get_width()
        dh = win.get_height()
        scale = min(dw / SCREEN_WIDTH, dh / SCREEN_HEIGHT)
        sw = int(SCREEN_WIDTH * scale)
        sh = int(SCREEN_HEIGHT * scale)
        ox = (dw - sw) // 2
        oy = (dh - sh) // 2
        return int((mx - ox) / scale), int((my - oy) / scale)

    def _seen(self, kind, key):
        return bool(self.gs.codex_seen.get(kind, {}).get(key))

    def _seen_count(self):
        return self.gs.codex_seen_count(SEEN_MAP)

    def _wrap(self, text, max_chars):
        lines = []
        cur = ""
        for ch in text:
            cur += ch
            if len(cur) >= max_chars and ch in "，。,.;:、 ":
                lines.append(cur)
                cur = ""
        if cur:
            lines.append(cur)
        return lines

    def _panel(self, x, y, w, h, border=TEXT_DIM, fill=BG_PANEL, bw=1):
        try:
            p = pygame.Surface((w, h), pygame.SRCALPHA)
            p.fill((*fill, 255))
            pygame.draw.rect(p, border, (0, 0, w, h), bw, border_radius=4)
            self.screen.blit(p, (x, y))
        except Exception:
            pygame.draw.rect(self.screen, fill, (x, y, w, h))
            pygame.draw.rect(self.screen, border, (x, y, w, h), bw)

    def _draw_back(self):
        """左上角返回按钮"""
        r = pygame.Rect(40, 30, 220, 44)
        mx, my = self._mouse()
        hover = r.collidepoint(mx, my)
        c = ACCENT if hover else TEXT_MUTED
        t = self.f_small.render("← 返回", True, c)
        self.screen.blit(t, (r.x + 6, r.y + 10))
        return r

    def _draw_breadcrumb(self, path):
        t = self.f_small.render("图鉴 > " + path, True, TEXT_DIM)
        self.screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 44))

    def _draw_tabs(self, tabs, sel, x, y):
        """页签行: tabs=[(文字, 颜色)]; 返回页签 rects"""
        rects = []
        cx = x
        for i, (text, color) in enumerate(tabs):
            sel_on = (i == sel)
            tc = ACCENT if sel_on else (color if color else TEXT_DIM)
            t = self.f.render(text, True, tc)
            self.screen.blit(t, (cx, y))
            rects.append(pygame.Rect(cx - 6, y - 4, t.get_width() + 12,
                                     t.get_height() + 8))
            if sel_on:
                pygame.draw.line(self.screen, ACCENT,
                                 (cx - 6, y + t.get_height() + 6),
                                 (cx + t.get_width() + 6,
                                  y + t.get_height() + 6), 2)
            cx += t.get_width() + 44
        return rects

    # ------------------------------------------------------------
    # 素材获取
    # ------------------------------------------------------------
    def _blit_asset(self, surf, center, seen, radius=None):
        """贴素材; 未发现时加暗影 + '?'"""
        if surf is None:
            return
        r = surf.get_rect(center=center)
        self.screen.blit(surf, r)
        if not seen:
            try:
                ov = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
                ov.fill((10, 10, 14, 215))
                if radius:
                    m = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
                    pygame.draw.circle(m, (255, 255, 255, 255),
                                       (surf.get_width() // 2,
                                        surf.get_height() // 2), radius)
                    ov.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                self.screen.blit(ov, r)
                q = self.f_q.render("?", True, TEXT_DIM)
                self.screen.blit(q, q.get_rect(center=center))
            except Exception:
                pass

    def _seen_dot(self, rect, seen):
        """未发现条目左上角白点角标"""
        if not seen:
            pygame.draw.circle(self.screen, TEXT_PRIMARY,
                               (rect.x + 12, rect.y + 12), 3)

    def _pickup_icon(self, ptype, size):
        key = (ptype, size)
        if key in self._pickup_icon_cache:
            return self._pickup_icon_cache[key]
        cfg = PICKUP_CONFIG[ptype]
        ring = RING_REWARD if cfg["kind"] == "reward" else RING_PENALTY
        d = int(size)
        r = max(4, d // 2 - 3)
        ss = 2
        tmp = pygame.Surface((d * ss, d * ss), pygame.SRCALPHA)
        c = d * ss // 2
        pygame.draw.circle(tmp, (255, 255, 255), (c, c), r * ss)
        pygame.draw.circle(tmp, ring, (c, c), r * ss, max(2, r // 4) * ss)
        sym = _render_symbol(cfg["symbol"], int(r * 1.15) * ss, cfg["color"])
        tmp.blit(sym, sym.get_rect(center=(c, c)))
        icon = pygame.transform.smoothscale(tmp, (d, d))
        self._pickup_icon_cache[key] = icon
        return icon

    def _tile_tex(self, wtype, size):
        name = TILE_TEXTURES.get(wtype)
        surf = _get_texture(name) if name else None
        if surf is None:
            return None
        try:
            return pygame.transform.smoothscale(surf, (size, size))
        except Exception:
            return pygame.transform.scale(surf, (size, size))

    def _boss_surf(self, bid, size):
        cfg = BOSS_CONFIG.get(bid)
        if not cfg:
            return None
        idx = cfg.get("index", 1)
        surf = get_boss_image(idx, (size, size))
        if surf is None and cfg.get("image"):
            from utils.assets import get_boss_image_file
            surf = get_boss_image_file(cfg["image"], (size, size))
        return surf

    def _entry_asset(self, entry, size):
        """按条目类型取素材"""
        k = entry["kind"]
        if k == K_TANK:
            return get_tank_view3d(entry["id"], (size, size))
        if k == K_BULLET:
            return get_bullet_image(entry["id"], (size, size))
        if k == K_PICKUP:
            return self._pickup_icon(entry["id"], size)
        if k == K_TILE:
            return self._tile_tex(entry["id"], size)
        if k == K_ENEMY:
            # 用真实 EnemyTank 渲染兵种预览 (含六种差异化标记)
            return self._enemy_preview(entry["id"], size)
        if k == K_BOSS:
            return self._boss_surf(entry["id"], size)
        return None

    def _enemy_preview(self, etype, size):
        """渲染敌军兵种预览图 (与战斗内同款: 黑坦克 + 兵种标记), 缓存"""
        key = (etype, size)
        if key in self._enemy_prev_cache:
            return self._enemy_prev_cache[key]
        from systems.ai_system import EnemyTank
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        try:
            t = EnemyTank(size // 2, size // 2, etype, level=1)
            t.turret_angle = 45
            t.draw(surf, 0, 0, False)
        except Exception:
            pass
        self._enemy_prev_cache[key] = surf
        return surf

    # ------------------------------------------------------------
    # HUB 图鉴总览
    # ------------------------------------------------------------
    def open(self, view="hub", cat_id=None):
        self.view = view
        if cat_id:
            self.cat_id = cat_id
        self.hub_idx = 0
        self.cat_tab = 0
        self.cat_idx = 0
        self.skill_idx = 0
        self.skill_tab = 0
        self.boss_idx = 0

    def _hub_open_cat(self, idx):
        self.cat_id = CODEX_CATEGORIES[idx]["id"]
        self.cat_tab = 0
        self.cat_idx = 0
        if self.cat_id == "enemy":
            self.view = "boss"
        elif self.cat_id == "skill":
            self.view = "skill"
        else:
            self.view = "cat"

    def _hub_card_rects(self):
        """右侧 2 列 × 3 行大卡片 (视觉序: 1 2 / 3 4 / 5 6)"""
        rects = []
        for i in range(6):
            col, row = i % 2, i // 2
            x = HUB_X + col * (HUB_CARD_W + HUB_GAP_X)
            y = HUB_Y + row * (HUB_CARD_H + HUB_GAP_Y)
            rects.append(pygame.Rect(x, y, HUB_CARD_W, HUB_CARD_H))
        return rects

    def _draw_hub(self):
        self._draw_back()
        t = self.f_title.render("图 鉴", True, TEXT_PRIMARY)
        self.screen.blit(t, ((SCREEN_WIDTH - t.get_width()) // 2, 96))
        sub = "ARCHIVE · 档案库"
        widths = [self.f_small.size(ch)[0] for ch in sub]
        total = sum(widths) + 8 * (len(sub) - 1)
        sx = (SCREEN_WIDTH - total) // 2
        for ch, w in zip(sub, widths):
            s = self.f_small.render(ch, True, TEXT_DIM)
            self.screen.blit(s, (sx, 232))
            sx += w + 8
        # 左橱窗
        self._panel(60, 300, 720, 565)
        self._draw_hub_preview(CODEX_CATEGORIES[self.hub_idx])
        # 收集进度
        seen = self._seen_count()
        total = codex_total()
        ptext = self.f_small.render(f"已收录 {seen}/{total}", True, TEXT_DIM)
        self.screen.blit(ptext, (90, 812))
        bar_x, bar_y, bar_w = 200, 822, 400
        pygame.draw.rect(self.screen, BG_GRID, (bar_x, bar_y, bar_w, 4))
        fill = int(bar_w * seen / max(1, total))
        if fill:
            pygame.draw.rect(self.screen, ACCENT, (bar_x, bar_y, fill, 4))
        # 右侧 2×3 大卡片
        cards = self._hub_card_rects()
        mx, my = self._mouse()
        hover = -1
        for i, r in enumerate(cards):
            if r.collidepoint(mx, my):
                hover = i
                break
        if hover >= 0:
            self.hub_idx = hover
        for i, (cat, r) in enumerate(zip(CODEX_CATEGORIES, cards)):
            sel = i == self.hub_idx
            self._panel(r.x, r.y, r.w, r.h,
                        border=ACCENT if sel else TEXT_DIM,
                        bw=2 if sel else 1)
            bar_c = ACCENT if sel else TEXT_MUTED
            pygame.draw.rect(self.screen, bar_c, (r.x + 12, r.y + 20, 3, 92))
            num = self.f_small.render(f"[{i+1}]", True,
                                      ACCENT if sel else TEXT_MUTED)
            self.screen.blit(num, (r.x + 30, r.y + 22))
            name_c = ACCENT if sel else TEXT_PRIMARY
            nt = self.f_name.render(cat["name"], True, name_c)
            self.screen.blit(nt, (r.x + 88, r.y + 18))
            cnt = self.f_small.render(f"({cat['count']})", True, TEXT_DIM)
            self.screen.blit(cnt, (r.x + 88 + nt.get_width() + 14,
                                   r.y + 30))
            dt = self.f_small.render(cat["desc"], True, TEXT_MUTED)
            self.screen.blit(dt, (r.x + 88, r.y + 96))
            dt2 = self.f_small.render(cat["desc2"], True, TEXT_MUTED)
            self.screen.blit(dt2, (r.x + 88, r.y + 126))
            self._draw_hub_thumb(cat, r)
        hint = self.f_small.render("数字键 1-6 · 方向键 · 回车 · Esc 返回",
                                   True, TEXT_MUTED)
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, 990))

    def _draw_hub_thumb(self, cat, r):
        """卡片右侧缩略图 (与左橱窗同素材)"""
        cx = r.x + r.w - 78
        cy = r.y + r.h // 2
        p = cat["preview"]
        try:
            if p == "tank":
                surf = get_tank_view3d(self.gs.selected_tank_color, (92, 92))
                if surf:
                    self.screen.blit(surf, surf.get_rect(center=(cx, cy)))
            elif p == "bullet":
                surf = get_bullet_image(BulletType.CANNON, (88, 88))
                if surf:
                    self.screen.blit(surf, surf.get_rect(center=(cx, cy)))
            elif p == "boss":
                surf = get_boss_image(1, (84, 84))
                if surf:
                    disc = _circular_crop(surf, 84)
                    self.screen.blit(disc, disc.get_rect(center=(cx, cy)))
            elif p == "skill":
                sym = self.f_icon_mid.render("═", True, TEXT_PRIMARY)
                self.screen.blit(sym, sym.get_rect(center=(cx, cy - 4)))
            elif p == "pickup":
                i1 = self._pickup_icon(PickupType.HP, 64)
                i2 = self._pickup_icon(PickupType.POISON, 64)
                self.screen.blit(i1, i1.get_rect(center=(cx - 38, cy)))
                self.screen.blit(i2, i2.get_rect(center=(cx + 38, cy)))
            elif p == "tile":
                for i, wt in enumerate([WallType.STEEL, WallType.BRICK,
                                        WallType.SAND,
                                        WallType.WATER_STAIN]):
                    tex = self._tile_tex(wt, 42)
                    if tex:
                        gx = cx - 25 + (i % 2) * 50
                        gy = cy - 25 + (i // 2) * 50
                        self.screen.blit(tex, tex.get_rect(center=(gx, gy)))
        except Exception:
            pass

    def _draw_hub_preview(self, cat):
        cx = 60 + 360
        cy = 300 + 220
        p = cat["preview"]
        try:
            if p == "tank":
                surf = get_tank_view3d(self.gs.selected_tank_color, (340, 340))
                if surf:
                    self.screen.blit(surf, surf.get_rect(center=(cx, cy)))
                cap = self.f_small.render(
                    TANK_COLOR_CONFIG[self.gs.selected_tank_color]["name"],
                    True, TEXT_DIM)
                self.screen.blit(cap, cap.get_rect(center=(cx, cy + 200)))
            elif p == "bullet":
                surf = get_bullet_image(BulletType.CANNON, (260, 260))
                if surf:
                    self.screen.blit(surf, surf.get_rect(center=(cx, cy - 20)))
                cap = self.f_small.render("炮弹 · 基准弹 · 伤害 28", True,
                                          TEXT_DIM)
                self.screen.blit(cap, cap.get_rect(center=(cx, cy + 190)))
            elif p == "boss":
                surf = get_boss_image(1, (330, 330))
                if surf:
                    self.screen.blit(surf, surf.get_rect(center=(cx, cy)))
                cap = self.f_small.render("蔡徐坤·篮球霸王 · 第 5 关首领",
                                          True, TEXT_DIM)
                self.screen.blit(cap, cap.get_rect(center=(cx, cy + 200)))
            elif p == "skill":
                ic = render_skill_icon("railgun", 110, TEXT_PRIMARY)
                if ic is not None:
                    self.screen.blit(ic, ic.get_rect(center=(cx, cy)))
                cap = self.f_small.render("轨道炮 · 传说技能", True,
                                          UPGRADE_RARITY_COLORS["legendary"])
                self.screen.blit(cap, cap.get_rect(center=(cx, cy + 200)))
            elif p == "pickup":
                i1 = self._pickup_icon(PickupType.HP, 150)
                i2 = self._pickup_icon(PickupType.POISON, 150)
                self.screen.blit(i1, i1.get_rect(center=(cx - 100, cy)))
                self.screen.blit(i2, i2.get_rect(center=(cx + 100, cy)))
                cap = self.f_small.render("蓝环 = 奖励 · 红环 = 惩罚", True,
                                          TEXT_DIM)
                self.screen.blit(cap, cap.get_rect(center=(cx, cy + 130)))
            elif p == "tile":
                for i, wt in enumerate([WallType.STEEL, WallType.BRICK,
                                        WallType.SAND,
                                        WallType.WATER_STAIN]):
                    tex = self._tile_tex(wt, 150)
                    if tex:
                        gx = cx - 85 + (i % 2) * 170
                        gy = cy - 100 + (i // 2) * 170
                        self.screen.blit(tex, tex.get_rect(center=(gx, gy)))
                cap = self.f_small.render("钢墙 · 砖块 · 沙粒 · 水渍", True,
                                          TEXT_DIM)
                self.screen.blit(cap, cap.get_rect(center=(cx, cy + 130)))
        except Exception:
            pass

    # ------------------------------------------------------------
    # CAT 统一分类页
    # ------------------------------------------------------------
    def _cat_entries(self):
        entries = CODEX[self.cat_id]
        tabs = CAT_TABS.get(self.cat_id, [])
        if tabs and 0 <= self.cat_tab < len(tabs):
            group = tabs[self.cat_tab][1]
            if group:
                # 多方共用条目 (如篮球=我方+敌方) 两个页签都能筛到
                entries = [e for e in entries
                           if group in e.get("groups", [e["group"]])]
        return entries

    def _cat_grid_rects(self):
        rects = []
        for i in range(CAT_PER_PAGE):
            col = i % CAT_GRID_COLS
            row = i // CAT_GRID_COLS
            x = CAT_GRID_X + col * (CAT_CARD_W + CAT_CARD_GAP)
            y = CAT_GRID_Y + row * (CAT_CARD_H + 16)
            rects.append(pygame.Rect(x, y, CAT_CARD_W, CAT_CARD_H))
        return rects

    def _cat_open(self, cat_id):
        self.cat_id = cat_id
        self.cat_tab = 0
        self.cat_idx = 0
        self.view = "cat"

    def _draw_cat(self):
        back = self._draw_back()
        cat = [c for c in CODEX_CATEGORIES if c["id"] == self.cat_id][0]
        self._draw_breadcrumb(cat["name"])
        nt = self.f_big.render(cat["name"], True, TEXT_PRIMARY)
        self.screen.blit(nt, (60, 100))
        cnt = self.f_small.render(f"共 {cat['count']} 条", True, TEXT_DIM)
        self.screen.blit(cnt, (60 + nt.get_width() + 20, 118))
        tabs = CAT_TABS.get(self.cat_id, [])
        tab_rects = []
        if tabs:
            tab_rects = self._draw_tabs(
                [(t[0], None) for t in tabs], self.cat_tab, 60, 170)
        entries = self._cat_entries()
        if not entries:
            return
        page = self.cat_idx // CAT_PER_PAGE
        page_entries = entries[page * CAT_PER_PAGE:
                               (page + 1) * CAT_PER_PAGE]
        rects = self._cat_grid_rects()
        mx, my = self._mouse()
        # 光标跟随: 悬停哪张卡, 左侧档案面板就切到哪条
        for i, r in enumerate(rects):
            if i < len(page_entries) and r.collidepoint(mx, my):
                self.cat_idx = page * CAT_PER_PAGE + i
                break
        # 左档案面板
        self._draw_cat_panel(entries[self.cat_idx], 60, 230, 640, 710)
        # 右网格
        for i, (e, r) in enumerate(zip(page_entries, rects)):
            sel = (page * CAT_PER_PAGE + i == self.cat_idx)
            self._panel(r.x, r.y, r.w, r.h,
                        border=ACCENT if sel else TEXT_DIM, bw=2 if sel else 1)
            seen = self._seen(e["kind"], e["id"])
            self._seen_dot(r, seen)
            surf = self._entry_asset(e, 110)
            self._blit_asset(surf, (r.x + r.w // 2, r.y + 72), seen)
            name = e["name"] if seen else "???"
            t = self.f_small.render(name, True,
                                    ACCENT if sel else TEXT_PRIMARY)
            self.screen.blit(t, (r.x + r.w // 2 - t.get_width() // 2,
                                 r.y + 126))
        # 翻页大按钮
        n_pages = (len(entries) + CAT_PER_PAGE - 1) // CAT_PER_PAGE
        self._page_rects = (None, None)
        if n_pages > 1:
            mid_x = CAT_GRID_X + (CAT_CARD_W * 4 + CAT_CARD_GAP * 3) // 2
            btn_w, btn_h = 200, 54
            prev_r = pygame.Rect(mid_x - btn_w - 70, 800, btn_w, btn_h)
            next_r = pygame.Rect(mid_x + 70, 800, btn_w, btn_h)
            self._page_rects = (prev_r, next_r)
            mx2, my2 = mx, my
            for r, text in ((prev_r, "← 上一页"), (next_r, "下一页 →")):
                hover = r.collidepoint(mx2, my2)
                self._panel(r.x, r.y, r.w, r.h,
                            border=ACCENT if hover else TEXT_DIM, bw=2 if hover else 1)
                t = self.f.render(text, True, ACCENT if hover else TEXT_PRIMARY)
                self.screen.blit(t, (r.x + (r.w - t.get_width()) // 2,
                                     r.y + (r.h - t.get_height()) // 2))
            mt = self.f_mid.render(f"{page+1} / {n_pages}", True, TEXT_DIM)
            self.screen.blit(mt, (mid_x - mt.get_width() // 2, 814))
        hint = self.f_small.render("方向键选择 · PageUp/PageDown 翻页 · Tab 切换页签 · Esc 返回",
                                   True, TEXT_MUTED)
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, 990))

    def _draw_cat_panel(self, e, x, y, w, h):
        self._panel(x, y, w, h)
        seen = self._seen(e["kind"], e["id"])
        cx = x + w // 2
        surf = self._entry_asset(e, 180)
        self._blit_asset(surf, (cx, y + 120), seen)
        name = e["name"] if seen else "???"
        nt = self.f_big.render(name, True, TEXT_PRIMARY)
        self.screen.blit(nt, (cx - nt.get_width() // 2, y + 226))
        gt = self.f_mid.render(f"{e['group']} · {e['pos']}", True,
                               TEXT_DIM)
        self.screen.blit(gt, (cx - gt.get_width() // 2, y + 278))
        line_y = y + 322
        pygame.draw.line(self.screen, BG_GRID, (x + 24, line_y),
                         (x + w - 24, line_y), 1)
        ty = line_y + 16
        for label, val in e.get("stats", []):
            lt = self.f_mid.render(label, True, TEXT_DIM)
            vt = self.f_stat.render(val, True, TEXT_PRIMARY)
            self.screen.blit(lt, (x + 30, ty))
            self.screen.blit(vt, (x + 150, ty - 4))
            ty += 42
        ty += 8
        pygame.draw.line(self.screen, BG_GRID, (x + 24, ty),
                         (x + w - 24, ty), 1)
        ty += 14
        for line in e.get("mech", []):
            for wl in self._wrap(line, 27):
                mt = self.f_mid.render(wl, True, TEXT_PRIMARY)
                self.screen.blit(mt, (x + 30, ty))
                ty += 28
        lore = e.get("lore", "")
        if lore:
            ty += 6
            pygame.draw.line(self.screen, BG_GRID, (x + 24, ty),
                             (x + w - 24, ty), 1)
            ty += 14
            for wl in self._wrap("「" + lore + "」", 25):
                lt = self.f_mid.render(wl, True, TEXT_DIM)
                self.screen.blit(lt, (x + 30, ty))
                ty += 28

    # ------------------------------------------------------------
    # BOSS 圆盘页 / 敌军
    # ------------------------------------------------------------
    def _boss_circles(self):
        cs = []
        offsets = [0, -30, -48, -30, 0]
        for i in range(5):
            cx = 480 + i * 240
            cy = 380 + offsets[i]
            cs.append(pygame.Rect(cx - 90, cy - 90, 180, 180))
        return cs

    def _draw_boss(self):
        back = self._draw_back()
        self._draw_breadcrumb("敌人图鉴")
        cat = [c for c in CODEX_CATEGORIES if c["id"] == "enemy"][0]
        nt = self.f_big.render(cat["name"], True, TEXT_PRIMARY)
        self.screen.blit(nt, (60, 100))
        tabs = self._draw_tabs([("首领", None), ("敌军", None)],
                               0 if self.boss_tab == "boss" else 1,
                               60 + nt.get_width() + 60, 118)
        mx, my = self._mouse()
        if self.boss_tab == "boss":
            bosses = CODEX["boss"]
            circles = self._boss_circles()
            # 光标跟随: 悬停哪个圆盘, 档案面板就切到哪个首领
            for i, r in enumerate(circles):
                if r.collidepoint(mx, my):
                    self.boss_idx = i
                    break
            for i, (e, r) in enumerate(zip(bosses, circles)):
                sel = i == self.boss_idx
                seen = self._seen(e["kind"], e["id"])
                surf = self._boss_surf(e["id"], 178)
                if surf and seen:
                    disc = _circular_crop(surf, 178)
                    self.screen.blit(disc, r.topleft)
                else:
                    # 未发现: 灰盘 + 问号占位 (在黑底上保持可见)
                    pygame.draw.circle(self.screen, BG_PANEL, r.center, 89)
                    q = self.f_q.render("?", True, TEXT_DIM)
                    self.screen.blit(q, q.get_rect(center=r.center))
                ring_c = ACCENT if sel else TEXT_DIM
                pygame.draw.circle(self.screen, ring_c, r.center, 90,
                                   2 if sel else 1)
                if sel:
                    try:
                        ring = pygame.Surface((200, 200), pygame.SRCALPHA)
                        pygame.draw.circle(ring, (255, 255, 255, 80),
                                           (100, 100), 97, 8)
                        self.screen.blit(ring, (r.x - 10, r.y - 10))
                    except Exception:
                        pass
                    pygame.draw.line(self.screen, ACCENT,
                                     (r.centerx - 18, r.y + 104),
                                     (r.centerx + 18, r.y + 104), 2)
                name = e["name"] if seen else "???"
                nc = ACCENT if sel else (TEXT_DIM if seen else TEXT_MUTED)
                lt = self.f.render(name, True, nc)
                self.screen.blit(lt, (r.centerx - lt.get_width() // 2,
                                      r.y + 112))
            self._draw_boss_panel(bosses[self.boss_idx], 60, 560, 1800, 440)
        else:
            grunts = CODEX["enemy"]
            card_w, card_h, gap = 240, 150, 36
            total = 6 * card_w + 5 * gap
            x0 = (SCREEN_WIDTH - total) // 2
            y0 = 330
            # 光标跟随: 悬停哪张敌军卡, 档案面板就切到哪条
            for i in range(6):
                r = pygame.Rect(x0 + i * (card_w + gap), y0, card_w, card_h)
                if r.collidepoint(mx, my):
                    self.grunt_idx = i
                    break
            for i, (e) in enumerate(grunts):
                r = pygame.Rect(x0 + i * (card_w + gap), y0, card_w, card_h)
                sel = i == self.grunt_idx
                self._panel(r.x, r.y, r.w, r.h,
                            border=ACCENT if sel else TEXT_DIM,
                            bw=2 if sel else 1)
                seen = self._seen(e["kind"], e["id"])
                self._seen_dot(r, seen)
                surf = self._enemy_preview(e["id"], 110)
                self._blit_asset(surf, (r.x + card_w // 2, r.y + 60), seen)
                name = e["name"] if seen else "???"
                t = self.f_small.render(name, True,
                                        ACCENT if sel else TEXT_PRIMARY)
                self.screen.blit(t, (r.x + card_w // 2 - t.get_width() // 2,
                                     r.y + 116))
            self._draw_boss_panel(grunts[self.grunt_idx], 60, 560, 1800, 440)
        hint = self.f_small.render("左右键 / 数字键切换 · Tab 切换页签 · Esc 返回",
                                   True, TEXT_MUTED)
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, 1020))

    def _draw_boss_panel(self, e, x, y, w, h):
        """两栏档案面板 (大字号疏排): 左半 = 档案数据, 右半 = 阶段机制/行为解析, 底部 = 档案文案"""
        self._panel(x, y, w, h)
        seen = self._seen(e["kind"], e["id"])
        name = e["name"] if seen else "???"
        nt = self.f_big.render(name, True, TEXT_PRIMARY)
        self.screen.blit(nt, (x + 56, y + 18))
        pt = self.f_mid.render(e["pos"], True, TEXT_DIM)
        self.screen.blit(pt, (x + 56, y + 64))
        # 分隔线与中线
        pygame.draw.line(self.screen, BG_GRID, (x + 24, y + 100),
                         (x + w - 24, y + 100), 1)
        mid_x = x + w // 2
        pygame.draw.line(self.screen, BG_GRID, (mid_x, y + 112),
                         (mid_x, y + h - 72), 1)
        # ---- 左栏: 档案数据 ----
        lx = x + 56
        lt = self.f_small.render("档案数据", True, TEXT_MUTED)
        self.screen.blit(lt, (lx, y + 112))
        ty = y + 144
        for label, val in e.get("stats", []):
            lab = self.f.render(label, True, TEXT_DIM)
            vt = self.f_30.render(val, True, TEXT_PRIMARY)
            self.screen.blit(lab, (lx, ty))
            self.screen.blit(vt, (lx + 230, ty - 5))
            ty += 54
        # ---- 右栏: 阶段机制 / 行为解析 ----
        rx = mid_x + 56
        is_boss = e["kind"] == K_BOSS
        rt = self.f_small.render("阶段机制" if is_boss else "行为解析",
                                 True, TEXT_MUTED)
        self.screen.blit(rt, (rx, y + 112))
        ty = y + 144
        for line in e.get("mech", []):
            for wl in self._wrap(line, 36):
                mt = self.f.render(wl, True, TEXT_PRIMARY)
                self.screen.blit(mt, (rx, ty))
                ty += 36
        # ---- 底部: 档案文案 ----
        lore = e.get("lore", "")
        if lore:
            by = y + h - 64
            pygame.draw.line(self.screen, BG_GRID, (x + 24, by),
                             (x + w - 24, by), 1)
            lt2 = self.f_mid.render("「" + lore + "」", True, TEXT_DIM)
            self.screen.blit(lt2, (x + 56, by + 16))

    # ------------------------------------------------------------
    # SKILL 技能页
    # ------------------------------------------------------------
    def _skill_list(self):
        skills = CODEX["skill"]
        tab = SKILL_TABS[self.skill_tab]
        if tab[1]:
            skills = [s for s in skills if s["rarity"] == tab[1]]
        return skills

    def _draw_skill(self):
        back = self._draw_back()
        self._draw_breadcrumb("技能图鉴")
        cat = [c for c in CODEX_CATEGORIES if c["id"] == "skill"][0]
        nt = self.f_big.render(cat["name"], True, TEXT_PRIMARY)
        self.screen.blit(nt, (60, 100))
        tabs = self._draw_tabs(
            [(t[0], t[2]) for t in SKILL_TABS], self.skill_tab,
            60 + nt.get_width() + 60, 118)
        skills = self._skill_list()
        if not skills:
            return
        s = skills[self.skill_idx]
        rcol = UPGRADE_RARITY_COLORS.get(s["rarity"], TEXT_PRIMARY)
        # 左侧大圆盘
        cx, cy = 340, 400
        pygame.draw.circle(self.screen, BG_PANEL, (cx, cy), 150)
        if s["rarity"] == "legendary":
            pygame.draw.circle(self.screen, rcol, (cx, cy), 150, 2)
            pygame.draw.circle(self.screen, rcol, (cx, cy), 140, 1)
        else:
            pygame.draw.circle(self.screen, rcol, (cx, cy), 150, 2)
        ic = render_skill_icon(s["id"], 130, TEXT_PRIMARY)
        if ic is not None:
            self.screen.blit(ic, ic.get_rect(center=(cx, cy - 4)))
        else:
            sym = self.f_icon.render(s["icon"], True, TEXT_PRIMARY)
            self.screen.blit(sym, sym.get_rect(center=(cx, cy - 6)))
        nt2 = self.f_name.render(s["name"], True, TEXT_PRIMARY)
        self.screen.blit(nt2, (cx - nt2.get_width() // 2, 566))
        bt = self.f_small.render(RARITY_BADGE.get(s["rarity"], "?"), True,
                                 rcol)
        self.screen.blit(bt, (cx - bt.get_width() // 2, 604))
        # 缩略图条: 每行 13 个, 超过自动换行 (全部档 26 个 = 2 行), 居中且硬钳制不出屏
        thumbs = []
        tw, gap = 48, 6
        per_row = 13
        rows = (len(skills) + per_row - 1) // per_row
        mx, my = self._mouse()
        for i, sk in enumerate(skills):
            col, row = i % per_row, i // per_row
            row_n = min(len(skills) - row * per_row, per_row)
            row_w = row_n * (tw + gap) - gap
            tx0 = max(12, cx - row_w // 2)
            ty = 672 + row * (tw + 8)
            r = pygame.Rect(tx0 + col * (tw + gap), ty, tw, tw)
            thumbs.append(r)
            sel = i == self.skill_idx
            sc = UPGRADE_RARITY_COLORS.get(sk["rarity"], TEXT_PRIMARY)
            self._panel(r.x, r.y, tw, tw,
                        border=ACCENT if sel else sc,
                        bw=2 if sel else 1)
            ic2 = render_skill_icon(sk["id"], tw - 12,
                                    TEXT_PRIMARY if sel else sc)
            if ic2 is not None:
                self.screen.blit(ic2, (r.x + 6, r.y + 6))
            else:
                st = self.f_small.render(sk["icon"], True,
                                         TEXT_PRIMARY if sel else sc)
                self.screen.blit(st, (r.x + tw // 2 - st.get_width() // 2,
                                      r.y + tw // 2 - st.get_height() // 2))
            if r.collidepoint(mx, my):
                self.skill_idx = i
        # 右解析区
        px, py, pw, ph = 760, 230, 1100, 700
        self._panel(px, py, pw, ph)
        hn = self.f_big.render(s["name"], True, TEXT_PRIMARY)
        self.screen.blit(hn, (px + 30, py + 24))
        badge = self.f_small.render(RARITY_BADGE.get(s["rarity"], "?"), True,
                                    rcol)
        bw_, bh_ = badge.get_width() + 20, badge.get_height() + 10
        try:
            bp = pygame.Surface((bw_, bh_), pygame.SRCALPHA)
            bp.fill((*BG_PANEL, 255))
            pygame.draw.rect(bp, rcol, (0, 0, bw_, bh_), 1, border_radius=3)
            self.screen.blit(bp, (px + pw - bw_ - 30, py + 28))
        except Exception:
            pass
        self.screen.blit(badge, (px + pw - bw_ - 20, py + 33))
        pt = self.f.render(s["pos"], True, TEXT_DIM)
        self.screen.blit(pt, (px + 30, py + 76))
        ty = py + 116
        pygame.draw.line(self.screen, BG_GRID, (px + 24, ty),
                         (px + pw - 24, ty), 1)
        ty += 14
        lt = self.f_small.render("效果解析", True, TEXT_MUTED)
        self.screen.blit(lt, (px + 30, ty))
        ty += 30
        for i, desc in enumerate(s["levels"]):
            tline = self.f.render(f"Lv{i+1}  {desc}", True, TEXT_PRIMARY)
            self.screen.blit(tline, (px + 30, ty))
            ty += 36
        ty += 10
        pygame.draw.line(self.screen, BG_GRID, (px + 24, ty),
                         (px + pw - 24, ty), 1)
        ty += 14
        lt = self.f_small.render("档案文案", True, TEXT_MUTED)
        self.screen.blit(lt, (px + 30, ty))
        ty += 30
        for wl in self._wrap("「" + s["lore"] + "」", 30):
            lt2 = self.f.render(wl, True, TEXT_DIM)
            self.screen.blit(lt2, (px + 30, ty))
            ty += 36
        hint = self.f_small.render("左右键切换技能 · Tab 切换稀有度 · Esc 返回",
                                   True, TEXT_MUTED)
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, 990))

    # ------------------------------------------------------------
    # 事件
    # ------------------------------------------------------------
    def handle_event(self, event):
        mx, my = self._mouse()
        if event.type == pygame.KEYDOWN:
            return self._handle_key(event)
        if event.type == pygame.MOUSEMOTION:
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_click(mx, my)
        return None

    def _handle_key(self, event):
        k = event.key
        if k == pygame.K_ESCAPE:
            if self.view == "hub":
                return "exit"
            self.view = "hub"
            return None
        if self.view == "hub":
            if k in (pygame.K_UP, pygame.K_w):
                self.hub_idx = (self.hub_idx - 2) % len(CODEX_CATEGORIES)
            elif k in (pygame.K_DOWN, pygame.K_s):
                self.hub_idx = (self.hub_idx + 2) % len(CODEX_CATEGORIES)
            elif k in (pygame.K_LEFT, pygame.K_a):
                self.hub_idx = (self.hub_idx - 1) % len(CODEX_CATEGORIES)
            elif k in (pygame.K_RIGHT, pygame.K_d):
                self.hub_idx = (self.hub_idx + 1) % len(CODEX_CATEGORIES)
            elif k in (pygame.K_RETURN, pygame.K_SPACE):
                self._hub_open_cat(self.hub_idx)
            elif pygame.K_1 <= k <= pygame.K_6:
                idx = k - pygame.K_1
                if idx < len(CODEX_CATEGORIES):
                    self.hub_idx = idx
                    self._hub_open_cat(idx)
        elif self.view == "cat":
            entries = self._cat_entries()
            if not entries:
                return None
            tabs = CAT_TABS.get(self.cat_id, [])
            if k == pygame.K_TAB and tabs:
                self.cat_tab = (self.cat_tab + 1) % len(tabs)
                self.cat_idx = 0
            elif k in (pygame.K_PAGEUP, pygame.K_q):
                self.cat_idx = max(0, self.cat_idx - CAT_PER_PAGE)
            elif k in (pygame.K_PAGEDOWN, pygame.K_e):
                self.cat_idx = min(len(entries) - 1,
                                   self.cat_idx + CAT_PER_PAGE)
            elif k in (pygame.K_LEFT, pygame.K_a):
                self.cat_idx = max(0, self.cat_idx - 1)
            elif k in (pygame.K_RIGHT, pygame.K_d):
                self.cat_idx = min(len(entries) - 1, self.cat_idx + 1)
            elif k in (pygame.K_UP, pygame.K_w):
                self.cat_idx = max(0, self.cat_idx - CAT_GRID_COLS)
            elif k in (pygame.K_DOWN, pygame.K_s):
                self.cat_idx = min(len(entries) - 1,
                                   self.cat_idx + CAT_GRID_COLS)
        elif self.view == "boss":
            if k == pygame.K_TAB:
                self.boss_tab = "grunt" if self.boss_tab == "boss" else "boss"
            elif self.boss_tab == "boss":
                if k in (pygame.K_LEFT, pygame.K_a):
                    self.boss_idx = (self.boss_idx - 1) % 5
                elif k in (pygame.K_RIGHT, pygame.K_d):
                    self.boss_idx = (self.boss_idx + 1) % 5
                elif pygame.K_1 <= k <= pygame.K_5:
                    self.boss_idx = k - pygame.K_1
            else:
                if k in (pygame.K_LEFT, pygame.K_a):
                    self.grunt_idx = (self.grunt_idx - 1) % 6
                elif k in (pygame.K_RIGHT, pygame.K_d):
                    self.grunt_idx = (self.grunt_idx + 1) % 6
                elif pygame.K_1 <= k <= pygame.K_6:
                    self.grunt_idx = k - pygame.K_1
        elif self.view == "skill":
            skills = self._skill_list()
            if not skills:
                return None
            if k == pygame.K_TAB:
                self.skill_tab = (self.skill_tab + 1) % len(SKILL_TABS)
                self.skill_idx = 0
            elif k in (pygame.K_LEFT, pygame.K_a):
                self.skill_idx = (self.skill_idx - 1) % len(skills)
            elif k in (pygame.K_RIGHT, pygame.K_d):
                self.skill_idx = (self.skill_idx + 1) % len(skills)
            elif pygame.K_1 <= k <= pygame.K_9:
                idx = k - pygame.K_1
                if idx < len(skills):
                    self.skill_idx = idx
        return None

    def _handle_click(self, mx, my):
        back = pygame.Rect(40, 30, 220, 44)
        if back.collidepoint(mx, my):
            if self.view == "hub":
                return "exit"
            self.view = "hub"
            return None
        if self.view == "hub":
            for i, r in enumerate(self._hub_card_rects()):
                if r.collidepoint(mx, my):
                    self.hub_idx = i
                    self._hub_open_cat(i)
                    return None
        elif self.view == "cat":
            tabs = CAT_TABS.get(self.cat_id, [])
            if tabs:
                tx, ty = 60, 170
                cx = tx
                for i, (text, _c) in enumerate([(t[0], None) for t in tabs]):
                    t = self.f.render(text, True, TEXT_PRIMARY)
                    if pygame.Rect(cx - 6, ty - 4, t.get_width() + 12,
                                   t.get_height() + 8).collidepoint(mx, my):
                        self.cat_tab = i
                        self.cat_idx = 0
                        return None
                    cx += t.get_width() + 44
            entries = self._cat_entries()
            page = self.cat_idx // CAT_PER_PAGE
            page_entries = entries[page * CAT_PER_PAGE:
                                   (page + 1) * CAT_PER_PAGE]
            # 翻页大按钮
            prev_r, next_r = getattr(self, "_page_rects", (None, None))
            if prev_r and prev_r.collidepoint(mx, my):
                self.cat_idx = max(0, self.cat_idx - CAT_PER_PAGE)
                return None
            if next_r and next_r.collidepoint(mx, my):
                self.cat_idx = min(len(entries) - 1,
                                   self.cat_idx + CAT_PER_PAGE)
                return None
            for i, r in enumerate(self._cat_grid_rects()):
                if i < len(page_entries) and r.collidepoint(mx, my):
                    self.cat_idx = page * CAT_PER_PAGE + i
                    return None
        elif self.view == "boss":
            # 页签
            t = self.f.render("首领", True, TEXT_PRIMARY)
            tx = 60 + self.f_big.render(
                [c for c in CODEX_CATEGORIES if c["id"] == "enemy"][0]["name"],
                True, TEXT_PRIMARY).get_width() + 60
            if pygame.Rect(tx - 6, 114, t.get_width() + 12,
                           t.get_height() + 8).collidepoint(mx, my):
                self.boss_tab = "boss"
                return None
            t2 = self.f.render("敌军", True, TEXT_PRIMARY)
            if pygame.Rect(tx + t.get_width() + 38, 114, t2.get_width() + 12,
                           t2.get_height() + 8).collidepoint(mx, my):
                self.boss_tab = "grunt"
                return None
            if self.boss_tab == "boss":
                for i, r in enumerate(self._boss_circles()):
                    if r.collidepoint(mx, my):
                        self.boss_idx = i
                        return None
            else:
                card_w, card_h, gap = 240, 150, 36
                total = 6 * card_w + 5 * gap
                x0 = (SCREEN_WIDTH - total) // 2
                for i in range(6):
                    r = pygame.Rect(x0 + i * (card_w + gap), 330,
                                    card_w, card_h)
                    if r.collidepoint(mx, my):
                        self.grunt_idx = i
                        return None
        elif self.view == "skill":
            # 页签
            nt = self.f_big.render(
                [c for c in CODEX_CATEGORIES if c["id"] == "skill"][0]["name"],
                True, TEXT_PRIMARY)
            tx = 60 + nt.get_width() + 60
            cx = tx
            for i, tab3 in enumerate(SKILL_TABS):
                text = tab3[0]
                t = self.f.render(text, True, TEXT_PRIMARY)
                if pygame.Rect(cx - 6, 114, t.get_width() + 12,
                               t.get_height() + 8).collidepoint(mx, my):
                    self.skill_tab = i
                    self.skill_idx = 0
                    return None
                cx += t.get_width() + 44
        return None

    # ------------------------------------------------------------
    # 主绘制入口
    # ------------------------------------------------------------
    def draw(self):
        orig = self.screen
        self.screen = self._internal
        self._draw_bg()
        if self.view == "hub":
            self._draw_hub()
        elif self.view == "cat":
            self._draw_cat()
        elif self.view == "boss":
            self._draw_boss()
        elif self.view == "skill":
            self._draw_skill()
        self.screen = orig
        dw = self.screen.get_width()
        dh = self.screen.get_height()
        scale = min(dw / SCREEN_WIDTH, dh / SCREEN_HEIGHT)
        sw = int(SCREEN_WIDTH * scale)
        sh = int(SCREEN_HEIGHT * scale)
        ox = (dw - sw) // 2
        oy = (dh - sh) // 2
        self.screen.fill(BG_DEEP)
        scaled = pygame.transform.smoothscale(self._internal, (sw, sh))
        self.screen.blit(scaled, (ox, oy))

    def _draw_bg(self):
        # 与主菜单同款: 缓慢漂移的网格 (仅菜单动)
        self.screen.fill(BG_DEEP)
        step = 80
        t = pygame.time.get_ticks()
        ox = int(t * 0.030) % step   # 与主菜单同步: 横线 →30px/s
        oy = int(t * 0.020) % step   # 竖线 ↓20px/s
        for x in range(-step, SCREEN_WIDTH + step, step):
            pygame.draw.line(self.screen, BG_GRID, (x + ox, 0),
                             (x + ox, SCREEN_HEIGHT), 1)
        for y in range(-step, SCREEN_HEIGHT + step, step):
            pygame.draw.line(self.screen, BG_GRID, (0, y + oy),
                             (SCREEN_WIDTH, y + oy), 1)
