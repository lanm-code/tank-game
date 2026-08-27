# -*- coding: utf-8 -*-
"""
Headless 自动化测试: Boss 关卡推进流程
运行: py -3.14 _test_boss_progression.py
覆盖:
  1. 剧情第5关 Boss 击杀 -> 升级页 -> 进入第6关
  2. 快速清关 6-9 -> 第10关 Boss2 生成并击杀 -> 第11关
  3. 第15关 Boss3 生成 + 无敌机制 + BGM结束失败结算
  4. Boss Rush 5 -> 胜利页 -> 第10关
"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import pygame

# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

pygame.init()
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
except Exception as e:
    print("[warn] mixer init failed:", e)

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from core.game import Game
from core.game_state import GameState, GamePhase, GameMode
from entities.boss import BossId

SAVE = os.path.join(HERE, "savegame.json")
save_backup = None
if os.path.exists(SAVE):
    with open(SAVE, "r", encoding="utf-8") as f:
        save_backup = f.read()

FAILS = []


def check(cond, msg):
    if cond:
        print("  [PASS]", msg)
    else:
        print("  [FAIL]", msg)
        FAILS.append(msg)


def run_frames(game, n):
    for _ in range(n):
        game.update()


def clear_level(gs, game):
    """快速清掉当前普通关: 把刷怪/击杀数拉满并清空场上敌人"""
    gs.wave.enemies_spawned = gs.wave.enemies_total
    gs.wave.enemies_killed = gs.wave.enemies_total
    for e in game.enemy_tanks:
        e.dead = True
    run_frames(game, 1)


try:
    gs = GameState()
    screen = pygame.display.set_mode((1280, 720))
    game = Game(screen, gs)

    print("== T1: 剧情第5关 Boss 击杀 -> 第6关 ==")
    gs.new_game(GameMode.STORY, level=5)
    game.start_level(5)
    check(gs.boss is not None, "第5关生成 Boss")
    check(gs.boss.boss_id == BossId.BOSS_1, "Boss1 类型正确")
    check(gs.phase == GamePhase.PLAYING, "开局 phase=PLAYING")

    game.gs.boss.take_damage(99999)
    run_frames(game, 3)
    check(gs.boss is None, "击杀后 boss 被清除")
    check(gs.phase == GamePhase.LEVEL_UPGRADE, f"击杀后进入升级页 (实际 {gs.phase})")
    check(len(gs.level_upgrade_choices) >= 1, "升级卡非空")

    game.on_upgrade_confirmed_external()
    check(gs.level == 6, f"确认升级后进入第6关 (实际 {gs.level})")
    check(gs.phase == GamePhase.PLAYING, "第6关 phase=PLAYING")
    check(gs.boss is None, "第6关无 Boss")

    print("== T2: 清关 6-9 -> 第10关 Boss2 ==")
    for expected in (7, 8, 9):
        clear_level(gs, game)
        check(gs.phase == GamePhase.LEVEL_UPGRADE,
              f"第{gs.level}关通关进入升级页 (实际 {gs.phase})")
        game.on_upgrade_confirmed_external()
        check(gs.level == expected, f"进入第{expected}关 (实际 {gs.level})")

    # 清掉第9关 -> 进入第10关 Boss 关
    clear_level(gs, game)
    check(gs.phase == GamePhase.LEVEL_UPGRADE,
          f"第9关通关进入升级页 (实际 {gs.phase})")
    game.on_upgrade_confirmed_external()
    check(gs.level == 10, f"进入第10关 (实际 {gs.level})")
    check(gs.boss is not None, "第10关生成 Boss")
    check(gs.boss.boss_id == BossId.BOSS_2, "第10关为 Boss2")
    game.gs.boss.take_damage(99999)
    run_frames(game, 3)
    check(gs.phase == GamePhase.LEVEL_UPGRADE, f"Boss2 击杀后进入升级页 (实际 {gs.phase})")
    game.on_upgrade_confirmed_external()
    check(gs.level == 11, f"Boss2 通关后进入第11关 (实际 {gs.level})")

    print("== T3: 清关 11-14 -> 第15关 Boss3 机制 ==")
    for expected in (12, 13, 14, 15):
        clear_level(gs, game)
        check(gs.phase == GamePhase.LEVEL_UPGRADE,
              f"第{gs.level}关通关进入升级页 (实际 {gs.phase})")
        game.on_upgrade_confirmed_external()
        check(gs.level == expected, f"进入第{expected}关 (实际 {gs.level})")

    check(gs.boss is not None, "第15关生成 Boss")
    check(gs.boss.boss_id == BossId.BOSS_3, "第15关为 Boss3")
    check(gs.boss.is_special, "Boss3 特殊标记")
    # 验证 10 秒后进入无敌并开始播放音频 (屏蔽 mixer 自动结束检测)
    game.audio._boss_bgm_active = False
    bgm_calls = []
    game.audio.play_boss_bgm = lambda *a, **k: bgm_calls.append((a, k))
    game.gs.boss.take_damage(1)  # 首次受击触发吟唱 (Boss3 机制入口)
    run_frames(game, 660)  # ~11 秒
    check(gs.boss is not None and gs.boss.immortal, "11秒后 Boss3 进入无敌")
    check(gs.boss.hp == gs.boss.max_hp, "无敌时满血")
    check(len(bgm_calls) >= 1, "无敌时刻开始播放 Boss 音频")
    check(bgm_calls[0][0][0] == 3 and bgm_calls[0][1].get("on_end") == "game_over",
          "Boss 音频播完判负")
    # 直接模拟 BGM 结束回调: 应进入失败结算
    game._on_boss3_bgm_end("game_over")
    check(gs.phase == GamePhase.GAME_OVER, f"BGM结束 -> 失败结算 (实际 {gs.phase})")

    print("== T4: Boss Rush 5 -> 胜利页 -> 第10关 ==")
    gs.new_game(GameMode.BOSS_RUSH, level=5)
    game.start_level(5)
    check(gs.boss is not None, "Boss Rush 第5关生成 Boss")
    game.gs.boss.take_damage(99999)
    run_frames(game, 3)
    check(gs.phase == GamePhase.VICTORY, f"Boss Rush 击杀 -> 胜利页 (实际 {gs.phase})")
    game._handle_result_continue()
    check(gs.level == 10, f"胜利页继续 -> 第10关 (实际 {gs.level})")
    check(gs.boss is not None and gs.boss.boss_id == BossId.BOSS_2,
          "Boss Rush 第10关 Boss2")

    print("== T5: 普通关正常通关判定 ==")
    gs.new_game(GameMode.STORY, level=1)
    game.start_level(1)
    check(gs.wave.enemies_total > 0, "第1关敌人总数>0")
    clear_level(gs, game)
    check(gs.phase == GamePhase.LEVEL_UPGRADE, f"第1关通关进入升级页 (实际 {gs.phase})")

finally:
    # 恢复真实存档
    if save_backup is not None:
        with open(SAVE, "w", encoding="utf-8") as f:
            f.write(save_backup)
        print("\n[savegame.json 已恢复]")
    else:
        if os.path.exists(SAVE):
            os.remove(SAVE)
            print("\n[测试产生的 savegame.json 已删除]")

print("\n================")
if FAILS:
    print(f"FAILED: {len(FAILS)} 项")
    for f in FAILS:
        print(" -", f)
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
