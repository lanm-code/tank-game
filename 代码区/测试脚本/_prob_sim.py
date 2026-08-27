# -*- coding: utf-8 -*-
"""概率模拟 (设计方案 2.6): 模拟大量三选一抽取, 统计各稀有度新技能分布,
与方案B期望权重对照。运行: python _prob_sim.py"""
import random
import sys

sys.path.insert(0, r"C:\Users\Lenovo\Desktop\tank game\代码区")
from core.
# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
game_state import PlayerData, TankColor
from systems.upgrade_system import UpgradeSystem

N = 20000
us = UpgradeSystem()
EXPECT = {
    3: {"common": 70, "rare": 25, "epic": 5, "legendary": 0},
    8: {"common": 55, "rare": 33, "epic": 12, "legendary": 0},
    15: {"common": 45, "rare": 35, "epic": 15, "legendary": 5},
    25: {"common": 35, "rare": 40, "epic": 17, "legendary": 8},
}

print(f"模拟抽取 {N} 次/档 (每次取第 1 张新技能, 统计稀有度分布)")
print(f"{'关卡档':<6} {'稀有度':<8} {'实际%':>8} {'期望%':>8} {'偏差':>8}")
all_ok = True
for lvl, exp in EXPECT.items():
    counts = {"common": 0, "rare": 0, "epic": 0, "legendary": 0}
    for _ in range(N):
        p = PlayerData(1, TankColor.RED)
        cs = us.available_upgrades(p, 3, level=lvl)
        c0 = cs[0]
        counts[c0["rarity"]] += 1
    for rar, e_pct in exp.items():
        a_pct = counts[rar] * 100.0 / N
        dev = a_pct - e_pct
        flag = "OK" if abs(dev) <= 4.0 else "!!DEVIATION!!"
        if abs(dev) > 4.0:
            all_ok = False
        print(f"Lv{lvl:<5} {rar:<9} {a_pct:>7.2f}% {e_pct:>7.2f}% {dev:>+7.2f}% {flag}")

print()
print("SIM OK" if all_ok else "SIM DEVIATION")
sys.exit(0 if all_ok else 1)
