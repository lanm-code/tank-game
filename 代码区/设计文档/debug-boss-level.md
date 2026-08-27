# Debug Session: Boss Level Progression

## Status: [RESOLVED] 2026-08-26

## Problem
1. ~~After defeating Boss at level 5, cannot advance to level 6~~ → FIXED
2. ~~User has never seen level 10 or level 15 Bosses~~ → verified reachable now
3. ~~Need full end-to-end verification of Boss progression~~ → done (headless test)

## Root Cause

`core/game.py` `_update_playing()` 中 Boss 死亡检测缩进错误:

```python
# 原代码 (bug):
if self.gs.boss and not self.gs.boss.dead:
    self.gs.boss.update(...)
    if self.gs.boss.dead:          # ← 永远为 False!
        self._on_boss_defeated()   # ← 永远不会执行
```

Boss 是被子弹 (`_update_bullets` -> `take_damage`) 打死的,而
`boss.update()` 内部永远不会把 `dead` 置真。因此 `_on_boss_defeated`
从不触发:Boss 消失、不再刷敌人、过关判定永远不满足 → 卡关。

## 修复清单

| # | 文件 | 问题 | 修复 |
|---|------|------|------|
| 1 | core/game.py | `_on_boss_defeated` 缩进在 boss.update 块内,永不触发(卡关主因) | 移出 if 块;击杀后 `gs.boss = None` |
| 2 | core/game.py | Boss3 BGM 结束直接设 phase,跳过统一结算(无统计/语音) | 改走 `_end_level(False)` |
| 3 | core/game_state.py | SAVE_PATH 指向上一级目录,存档从未生效 | 指向 `代码区/savegame.json` |
| 4 | core/game.py | 第5关通关进度虚标解锁到第10关 | 删除,进度=level+1 |
| 5 | core/game.py | Boss3 无敌提示 3 个按钮无事件处理(死按钮) | 补上点击:暂停/返回主菜单 |
| 6 | core/game.py | Boss3 倒计时偏移 10 秒(计时起点不同) | 用 immortal_timer 对齐 BGM |
| 7 | systems/map_system.py | P2 出生点(col 7)不在保护区内,可能被随机墙压住 | 增加 P2 保护区域并统一清理 |
| 8 | systems/ai_system.py | 工程师 HEAL 状态只移动不回血 | 靠近友军每 0.6s 回 2 血 |
| 9 | systems/upgrade_system.py | 升级卡兜底可能给满级/重复卡 | 兜底同样过滤满级与重复 |
| 10 | utils/assets.py | 3D 图强制绕过缓存,主菜单每帧重载大图 | 统一走缓存 |
| 11 | ui/menu_controller.py | 坦克箭头/升级卡 hover 用窗口坐标未换算 | 换算到内部分辨率 |
| 12 | ui/hud_controller.py | 显示已废弃的 [Q/E切换] 提示 | 移除 |
| 13 | README.md | 操作表/存档路径过时 | 同步 |

## Verification

`_test_boss_progression.py` (headless, SDL dummy):
- T1 剧情第5关 Boss1 击杀 -> 升级页 -> 第6关 ✓
- T2 清关 6-9 -> 第10关 Boss2 生成/击杀 -> 第11关 ✓
- T3 清关 11-14 -> 第15关 Boss3 生成 + BGM 结束失败结算 ✓
- T4 Boss Rush 5 -> 胜利页 -> 第10关 Boss2 ✓
- T5 普通关通关判定 ✓

ALL TESTS PASSED;渲染冒烟测试(菜单/游戏/暂停/升级/结算/Boss)全通过;
26 关 × 30 次随机地图生成,出生点 0 次被墙阻挡。

## Hypotheses 回顾

- H1 (phase guard): 排除 — 同帧后续逻辑无副作用
- H2 (upgrade page broken): 排除 — 升级页链路正常
- H3 (start_level(6) crash): 排除
- H4 (level gate): 排除 (顺带发现存档路径 bug,但不是卡关原因)
- H5 (boss level calc): 排除 — level//5 映射正确 (5→B1, 10→B2, 15→B3)

## 设计提醒 (非 bug)

- Boss 15 是限时击杀:10 秒内打掉 500 血,否则满血+无敌,BGM 播完必败。
- Boss 实体移动不检测墙体碰撞(视觉上会压着钢柱走)。
