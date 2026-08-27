# -*- coding: utf-8 -*-
"""
地图生成系统
"""
import random
import pygame
from core.constants import *
from entities.wall import Wall


class MapGenerator:
    def __init__(self, cols=MAP_COLS, rows=MAP_ROWS):
        self.cols = cols
        self.rows = rows
        self.tile = TILE_SIZE

    def rect(self):
        return pygame.Rect(0, 0, self.cols * self.tile, self.rows * self.tile)

    def _fill(self, walls, col1, row1, col2, row2, wtype):
        for r in range(row1, row2 + 1):
            for c in range(col1, col2 + 1):
                walls.append(Wall(c, r, wtype))

    def _random_fill(self, walls, wtype, density, margin=1, exclude_regions=None):
        ex = exclude_regions or []
        taken = self._occupied(walls)  # 不叠加在已有方块上 (修复草丛叠砖墙进不去)
        for r in range(margin, self.rows - margin):
            for c in range(margin, self.cols - margin):
                skip = False
                for (cx1, ry1, cx2, ry2) in ex:
                    if cx1 <= c <= cx2 and ry1 <= r <= ry2:
                        skip = True
                        break
                if skip or (c, r) in taken:
                    continue
                if random.random() < density:
                    taken.add((c, r))
                    walls.append(Wall(c, r, wtype))

    def _occupied(self, walls):
        return {(w.col, w.row) for w in walls}

    def _in_regions(self, c, r, regions):
        for (cx1, ry1, cx2, ry2) in regions:
            if cx1 <= c <= cx2 and ry1 <= r <= ry2:
                return True
        return False

    def _scatter(self, walls, wtype, count, margin=2, exclude_regions=None):
        """在随机空格上撒 count 个方块 (不叠在已有方块上)"""
        ex = exclude_regions or []
        taken = self._occupied(walls)
        placed = 0
        tries = 0
        while placed < count and tries < 200:
            tries += 1
            c = random.randint(margin, self.cols - 1 - margin)
            r = random.randint(margin, self.rows - 1 - margin)
            if (c, r) in taken or self._in_regions(c, r, ex):
                continue
            taken.add((c, r))
            walls.append(Wall(c, r, wtype))
            placed += 1

    def _add_cluster(self, walls, wtype, count, size_min, size_max,
                     margin=2, exclude_regions=None):
        """随机种子格 + 4 邻域扩张, 生成 size_min~size_max 格连片 (水渍/泥沼/冰面/尖刺)"""
        ex = exclude_regions or []
        taken = self._occupied(walls)
        placed = 0
        tries = 0
        while placed < count and tries < 80:
            tries += 1
            c = random.randint(margin, self.cols - 1 - margin)
            r = random.randint(margin, self.rows - 1 - margin)
            if (c, r) in taken or self._in_regions(c, r, ex):
                continue
            size = random.randint(size_min, size_max)
            cells = [(c, r)]
            frontier = [(c, r)]
            while len(cells) < size and frontier:
                cc, rr = frontier.pop(0)
                for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nc, nr = cc + dc, rr + dr
                    if not (margin <= nc < self.cols - margin and
                            margin <= nr < self.rows - margin):
                        continue
                    if ((nc, nr) in cells or (nc, nr) in taken or
                            self._in_regions(nc, nr, ex)):
                        continue
                    cells.append((nc, nr))
                    frontier.append((nc, nr))
                    if len(cells) >= size:
                        break
            if len(cells) < 2:
                continue
            for (cc, rr) in cells:
                taken.add((cc, rr))
                walls.append(Wall(cc, rr, wtype))
            placed += 1

    def _fill_sparse_regions(self, walls, level, exclude_regions):
        """空白区检测: 按 5x4 分块扫描, 内容极少 (<=1 格) 的大片空白区域
        自动补撒可破坏方块 (沙粒/砖块/木箱), 让战场不空旷"""
        ex = exclude_regions or []
        occupied = self._occupied(walls)
        chunk_c, chunk_r = 5, 4
        for cy in range(0, self.rows, chunk_r):
            for cx in range(0, self.cols, chunk_c):
                cells = [(c, r)
                         for r in range(cy, min(cy + chunk_r, self.rows))
                         for c in range(cx, min(cx + chunk_c, self.cols))]
                occ = sum(1 for (c, r) in cells if (c, r) in occupied)
                if occ > 1:
                    continue  # 该块有内容, 不算空白
                # 出生区/基地占大半的块跳过 (避免堵出生视野)
                protected = sum(1 for (c, r) in cells
                                if self._in_regions(c, r, ex))
                if protected > len(cells) // 2:
                    continue
                free = [(c, r) for (c, r) in cells
                        if (c, r) not in occupied and
                        not self._in_regions(c, r, ex)]
                random.shuffle(free)
                n = min(random.randint(3, 5), len(free))
                for (c, r) in free[:n]:
                    roll = random.random()
                    if level >= 3 and roll < 0.15:
                        wt = WallType.CRATE      # 15% 木箱 (有掉落)
                    elif roll < 0.65:
                        wt = WallType.SAND       # 50% 沙粒 (1 发篮球碎)
                    else:
                        wt = WallType.BRICK      # 35% 砖块 (2 炮)
                    walls.append(Wall(c, r, wt))
                    occupied.add((c, r))

    def _add_template(self, walls, level):
        """极简结构化布局模板: 中央砖块堡垒 + 横走廊沙墙 + 阶梯斜墙 (参考极简塔防关卡)
        权重平衡: 走廊墙改沙粒 (1 炮穿), 砖块留给堡垒/阶梯/角掩体, 使砖沙总量接近"""
        # 1) 中央砖块堡垒 (连片 3x5, 玩家从下方绕行) —— 砖块 (2 炮)
        self._fill(walls, self.cols // 2 - 2, 5, self.cols // 2 + 2, 7, WallType.BRICK)
        # 2) 走廊墙: 上半区 4 段短沙墙 (1 炮穿), 段间留 3 格通道
        row = 3
        segments = [(3, 6), (9, 12), (15, 18), (21, 24)]
        for c0, c1 in segments:
            for c in range(c0, c1 + 1):
                walls.append(Wall(c, row, WallType.SAND))
        # 3) 阶梯斜墙: 左侧从 (col2,row9) 阶梯下行 (每行退一格) —— 砖块
        if level >= 3:
            for i in range(6):
                walls.append(Wall(2 + i, 9 + i, WallType.BRICK))
        # 4) 两角小型砖掩体 (四角附近, 避开出生区)
        for c in (3, 4, 5):
            walls.append(Wall(c, 1, WallType.BRICK))
        for c in (self.cols - 6, self.cols - 5, self.cols - 4):
            walls.append(Wall(c, 1, WallType.BRICK))

    def _is_connected(self, walls):
        """BFS 连通性检查: 玩家出生区必须能走到左上/右上角 (敌人出生方向)"""
        blocked = set()
        for w in walls:
            if not WALL_CONFIG[w.type]["tank_pass"]:
                blocked.add((w.col, w.row))
        start = (2, self.rows - 3)
        targets = [(1, 1), (self.cols - 2, 1)]
        seen = {start}
        frontier = [start]
        while frontier:
            c, r = frontier.pop()
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nc, nr = c + dc, r + dr
                if nc < 0 or nc >= self.cols or nr < 0 or nr >= self.rows:
                    continue
                if (nc, nr) in blocked or (nc, nr) in seen:
                    continue
                seen.add((nc, nr))
                frontier.append((nc, nr))
        return all(t in seen for t in targets)

    def generate_level(self, level):
        # 结构化模板 + 随机散布, BFS 兜底重试 (最多 8 次)
        for _attempt in range(8):
            walls = self._gen_level_once(level)
            if self._is_connected(walls):
                return walls, self._base_region()
        return walls, self._base_region()

    def _base_region(self):
        return (self.cols // 2 - 2, self.rows - 4,
                self.cols // 2 + 1, self.rows - 2)

    def _gen_level_once(self, level):
        walls = []
        margin = 1
        spawn_regions = [
            (1, self.rows - 5, 6, self.rows - 2),
            (self.cols - 7, self.rows - 5, self.cols - 2, self.rows - 2),
            (6, self.rows - 5, 8, self.rows - 2),  # P2 出生点保护 (col 7)
        ]
        base_region = self._base_region()
        cx1, ry1, cx2, ry2 = base_region
        for r in range(ry1, ry2 + 1):
            for c in range(cx1, cx2 + 1):
                walls.append(Wall(c, r, WallType.BRICK))
        for s in spawn_regions:
            walls = [w for w in walls
                     if not (s[0] <= w.col <= s[2] and s[1] <= w.row <= s[3])]
        # 结构化模板 (所有关卡都有, 高难度随机密度降低)
        self._add_template(walls, level)
        # 砖块血量升到 56, 随机砖块与沙粒数量对齐 (见下方 ex 区块), 防止打不穿的墙海
        if level <= 2:
            # 新手关: 中部大区砖沙各半填充 (与沙粒量级对齐)
            taken = self._occupied(walls)
            fill = [Wall(c, r, WallType.BRICK)
                    for r in range(4, self.rows - 5)
                    for c in range(4, self.cols - 4)
                    if (c, r) not in taken]
            fill = [w for w in fill if random.random() < 0.25]
            for w in fill:
                if random.random() < 0.5:
                    w.type = WallType.SAND
                    cfg = WALL_CONFIG[WallType.SAND]
                    w.color = cfg["color"]
                    w.max_hp = cfg["hp"]
                    w.hp = cfg["hp"]
            walls.extend(fill)
            self._random_fill(walls, WallType.STEEL, 0.02, margin=3,
                              exclude_regions=spawn_regions + [base_region])
        elif level <= 5:
            self._random_fill(walls, WallType.STEEL, 0.05, margin=4,
                              exclude_regions=spawn_regions + [base_region])
            self._random_fill(walls, WallType.GRASS, 0.04, margin=2,
                              exclude_regions=spawn_regions + [base_region])
        elif level <= 10:
            self._random_fill(walls, WallType.STEEL, 0.06, margin=4,
                              exclude_regions=spawn_regions + [base_region])
            self._random_fill(walls, WallType.GRASS, 0.05, margin=2,
                              exclude_regions=spawn_regions + [base_region])
        else:
            self._random_fill(walls, WallType.STEEL, 0.08, margin=4,
                              exclude_regions=spawn_regions + [base_region])
            self._random_fill(walls, WallType.GRASS, 0.06, margin=2,
                              exclude_regions=spawn_regions + [base_region])
        # ---- 新方块与地块 (按关卡逐级解锁, 全部避开出生区/基地区) ----
        # 注意用基地保护环 (base±1, 与末尾 _clear_region 一致), 否则散布元素会被清理
        ex_ring = (base_region[0] - 1, base_region[1] - 1,
                   base_region[2] + 1, base_region[3] + 1)
        ex = spawn_regions + [ex_ring]
        # 砖块 / 沙粒: 随机量对齐 (砖=2炮重墙, 沙=1炮轻墙, 地图上量级相当)
        brick_count = (10 if level <= 5 else 12 if level <= 10 else 14)
        sand_count = (10 if level == 1 else 12 if level == 2 else
                      10 if level <= 5 else 12 if level <= 10 else 14)
        self._scatter(walls, WallType.BRICK, brick_count, 2, ex)
        self._scatter(walls, WallType.SAND, sand_count, 2, ex)
        if level >= 2:
            self._add_cluster(walls, WallType.SAND, 1, 2, 4, 2, ex)
        # 水渍地块: 集群滑行 (2 关 1 簇 → 5 关 2 → 8 关 3 → 11+ 关 4)
        stain_n = 0
        if level >= 2:
            stain_n = 1
        if level >= 5:
            stain_n = 2
        if level >= 8:
            stain_n = 3
        if level >= 11:
            stain_n = 4
        self._add_cluster(walls, WallType.WATER_STAIN, stain_n, 2, 6, 2, ex)
        # 水面 (不可通行水墙): 成片出现 (3~4 格连片), 不再散点
        if level >= 6:
            self._add_cluster(walls, WallType.WATER,
                              2 if level <= 10 else 3, 3, 4, 3, ex)
        # 木箱: 1 发碎, 15% 掉道具
        if level >= 3:
            self._scatter(walls, WallType.CRATE, 6, 2, ex)
        # 玻璃墙 + 泥沼
        if level >= 4:
            # 玻璃墙数量与砖块/沙粒同量级 (用户要求: 权重一样高)
            self._scatter(walls, WallType.GLASS, sand_count, 2, ex)
            self._add_cluster(walls, WallType.MUD, 1, 2, 4, 2, ex)
        # 燃油桶: 打碎爆炸
        if level >= 5:
            self._scatter(walls, WallType.BARREL, 2, 2, ex)
        # 冰面 (可控提速滑行): 成片出现 (3~5 格连片)
        if level >= 6:
            self._add_cluster(walls, WallType.ICE,
                              2 if level <= 10 else 3, 3, 5, 2, ex)
        # 尖刺 (站立掉血)
        if level >= 8:
            self._add_cluster(walls, WallType.SPIKE, 2, 2, 3, 2, ex)
        # 空白区检测: 大片无内容区域自动补撒可破坏方块
        self._fill_sparse_regions(walls, level, ex)
        for s in spawn_regions:
            walls = self._clear_region(walls, *s)
        walls = self._clear_region(walls, base_region[0] - 1, base_region[1] - 1,
                                   base_region[2] + 1, base_region[3] + 1)
        return walls

    def _clear_region(self, walls, c1, r1, c2, r2):
        c1, c2 = sorted([c1, c2])
        r1, r2 = sorted([r1, r2])
        return [w for w in walls
                if not (c1 <= w.col <= c2 and r1 <= w.row <= r2)]

    def generate_boss_arena(self, level):
        walls = []
        for c in range(0, self.cols):
            walls.append(Wall(c, 0, WallType.STEEL))
            walls.append(Wall(c, self.rows - 1, WallType.STEEL))
        for r in range(0, self.rows):
            walls.append(Wall(0, r, WallType.STEEL))
            walls.append(Wall(self.cols - 1, r, WallType.STEEL))
        if level >= 10:
            # 钢柱布局: 避开 Boss 出生中心线 (col 15) 与玩家出生点直射路线
            for r in range(6, self.rows - 6, 4):    # rows 6, 10
                for c in range(7, self.cols - 7, 7):  # cols 7, 14, 21
                    walls.append(Wall(c, r, WallType.STEEL))
        # 传送门: Boss 关点缀 1 对 (左右对称, 避开钢柱/Boss 出生线/玩家出生点)
        pa = Wall(3, 8, WallType.PORTAL)
        pb = Wall(self.cols - 4, 8, WallType.PORTAL)
        pa.portal_partner = pb
        pb.portal_partner = pa
        walls.append(pa)
        walls.append(pb)
        base_region = (self.cols // 2 - 2, self.rows - 4,
                       self.cols // 2 + 1, self.rows - 2)
        return walls, base_region
