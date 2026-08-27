# -*- coding: utf-8 -*-
"""旺仔小乔 / 华强 Boss 图背景重着色: (34,34,40) -> 游戏背景 (47,47,47)
只替换与图像边缘连通的背景像素 (人物深色细节不受影响), alpha 与卡边保留。"""
import os
import shutil
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np
import pygame

# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

pygame.init()
pygame.display.set_mode((64, 64))

ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "素材库", "首领敌人"))
OLD = np.array([34, 34, 40])
NEW = np.array([47, 47, 47])   # BG_DEEP
TOL = 7

TARGETS = [
    os.path.join(ROOT, "首领敌人图", "2.png"),   # 旺仔小乔
    os.path.join(ROOT, "华强.png"),               # 华强
]


def flood_from_edges(near):
    h, w = near.shape
    mask = np.zeros((h, w), dtype=bool)
    mask[0, :] = near[0, :]
    mask[-1, :] = near[-1, :]
    mask[:, 0] = near[:, 0]
    mask[:, -1] = near[:, -1]
    while True:
        prev = int(mask.sum())
        grow = mask.copy()
        grow[1:, :] |= mask[:-1, :]
        grow[:-1, :] |= mask[1:, :]
        grow[:, 1:] |= mask[:, :-1]
        grow[:, :-1] |= mask[:, 1:]
        mask = grow & near
        if int(mask.sum()) == prev:
            break
    return mask


for path in TARGETS:
    if not os.path.exists(path):
        print("skip (not found):", path)
        continue
    bak = path + ".bak"
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
    surf = pygame.image.load(path).convert_alpha()
    w, h = surf.get_size()
    rgb = pygame.surfarray.array3d(surf).copy().transpose(1, 0, 2)  # (h,w,3)
    alpha = pygame.surfarray.pixels_alpha(surf).copy().T             # (h,w)
    near = ((np.abs(rgb.astype(np.int32) - OLD) <= TOL).all(axis=2)
            & (alpha > 200))
    mask = flood_from_edges(near)
    n = int(mask.sum())
    rgb[mask] = NEW
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.surfarray.pixels3d(out)[:, :, :] = rgb.transpose(1, 0, 2)
    pygame.surfarray.pixels_alpha(out)[:, :] = alpha.T
    pygame.image.save(out, path)
    print(f"done: {os.path.basename(path)}  {w}x{h}  replaced {n} px")

pygame.quit()
print("ALL DONE")
