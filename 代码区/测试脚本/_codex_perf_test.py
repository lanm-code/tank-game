# -*- coding: utf-8 -*-
"""子弹图加载性能回归: 图鉴子弹页一次加载 8 张 × 3 尺寸, 必须在数秒内完成
(修复前: 全尺寸抠图+洪水填充单张卡 8~15 秒, 8 张直接程序无响应)"""
import os
import sys
import time

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import pygame  # noqa: E402
# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))


pygame.init()
pygame.display.set_mode((64, 64))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.constants import BULLET_CONFIG  # noqa: E402
from utils.assets import get_bullet_image  # noqa: E402

# 清空缓存计时 (模拟图鉴首次打开)
t0 = time.time()
for _type in BULLET_CONFIG:
    for size in ((110, 110), (180, 180), (260, 260)):
        s = get_bullet_image(_type, size)
        assert s is not None, f"{_type} @{size} 加载失败"
elapsed = time.time() - t0
print(f"8 弹 × 3 尺寸总耗时: {elapsed:.2f}s")
assert elapsed < 5.0, f"加载过慢 {elapsed:.2f}s"
print("PERF OK")
pygame.quit()
