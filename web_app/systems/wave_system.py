# -*- coding: utf-8 -*-
"""
波次生成系统
"""
import random
from core.constants import *
from systems.ai_system import EnemyTank


class WaveSystem:
    def __init__(self, map_cols, map_rows):
        self.map_cols = map_cols
        self.map_rows = map_rows

    def wave_count(self, level):
        """波数 = 关卡十位数+1, 10 关以下 1 波, 封顶 5 波
        (例: 1~9关=1波, 10~19关=2波, 25关=3波, 47关=5波, 50关以上=5波)"""
        return min(5, level // 10 + 1)

    def level_wave_info(self, level, mode):
        from core.game_state import GameMode
        if mode == GameMode.BOSS_RUSH:
            return {"waves": 1, "enemies_per_wave": 0, "is_boss_level": True,
                    "enemy_types": []}
        if mode == GameMode.ENDLESS:
            base = 3 + level
            return {"waves": self.wave_count(level),
                    "enemies_per_wave": base,
                    "is_boss_level": level % 5 == 0,
                    "enemy_types": self._endless_types(level)}
        # 剧情模式: 第5/10/15关是Boss关卡, 没有普通敌人
        is_boss = level % 5 == 0
        if is_boss:
            return {
                "waves": 0,
                "enemies_per_wave": 0,
                "is_boss_level": True,
                "enemy_types": [],
            }
        return {
            "waves": self.wave_count(level),
            "enemies_per_wave": 2 + level // 2,
            "is_boss_level": False,
            "enemy_types": self._story_types(level),
        }

    def _story_types(self, level):
        pool = [(EnemyType.SCOUT, 10)]
        if level >= 2: pool.append((EnemyType.ARTILLERY, 6))
        if level >= 3: pool.append((EnemyType.HEAVY, 4))
        if level >= 4: pool.append((EnemyType.GHOST, 3))
        if level >= 6: pool.append((EnemyType.ENGINEER, 3))
        if level >= 8: pool.append((EnemyType.ELITE, 2))
        return pool

    def _endless_types(self, level):
        pool = [(EnemyType.SCOUT, 8), (EnemyType.ARTILLERY, 5),
                (EnemyType.HEAVY, 4)]
        if level >= 3: pool.append((EnemyType.GHOST, 4))
        if level >= 5: pool.append((EnemyType.ENGINEER, 3))
        if level >= 7: pool.append((EnemyType.ELITE, 3))
        return pool

    def pick_spawn_point(self, existing_tanks, walls, tile):
        """地图空白处随机刷敌: 全图随机位置, 避开墙体/坦克/底部玩家出生区"""
        import math
        from entities.tank import TANK_WIDTH
        tries = 0
        while tries < 80:
            tries += 1
            c = random.randint(2, self.map_cols - 3)
            r = random.randint(2, self.map_rows - 5)
            x = c * tile + tile // 2
            y = r * tile + tile // 2
            tr = pygame.Rect(x - TANK_WIDTH // 2, y - TANK_WIDTH // 2,
                             TANK_WIDTH, TANK_WIDTH)
            ok = True
            # 避开墙体 (坦克可穿过的草丛/水渍等地块除外; 尖刺/传送门仍要避开)
            for w in walls:
                wc = WALL_CONFIG[w.type]
                if wc.get("tank_pass"):
                    if w.type in (WallType.SPIKE, WallType.PORTAL):
                        if tr.colliderect(pygame.Rect(w.x, w.y, w.width, w.height)):
                            ok = False
                            break
                    continue
                if tr.colliderect(pygame.Rect(w.x, w.y, w.width, w.height)):
                    ok = False
                    break
            if not ok:
                continue
            for t in existing_tanks:
                if math.hypot(t.x - x, t.y - y) < TANK_WIDTH * 2:
                    ok = False
                    break
            if ok:
                return x, y
        # 兜底: 顶部安全点
        return 3 * tile + tile // 2, 2 * tile + tile // 2

    def spawn_enemy(self, existing_tanks, walls, level, enemy_pool):
        items, weights = zip(*enemy_pool)
        total = sum(weights)
        rnd = random.uniform(0, total)
        acc = 0
        chosen = items[0]
        for it, w in zip(items, weights):
            acc += w
            if rnd <= acc:
                chosen = it
                break
        x, y = self.pick_spawn_point(existing_tanks, walls, TILE_SIZE)
        return EnemyTank(x, y, chosen, level=level)
