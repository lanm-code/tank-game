# -*- coding: utf-8 -*-
"""一次性预处理: Boss 立绘 → 透明底 PNG。

策略:
1. 四角采样估背景色, 按双线性插值重建渐变背景 (华强上白下灰背景适用);
2. 从四边泛洪, 只抠与边缘连通的背景 (白婚纱/黑衣服等图内内容保留);
3. 若泛洪会吃掉主体 (移除比例过高, 白底白主体无解场景),
   自动降级为"整图保留 + 圆角卡片遮罩" (白盒/海报本身就是主体卡片)。
"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"D:\DeepSeek-Harness-EAC\Deepseek Harness EAC\deepseek工作区\坦克游戏\tools")

import numpy as np
import pygame

# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

pygame.init()
pygame.display.set_mode((100, 100))

ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "素材库", "首领敌人"))

JOBS = [
    # (输入, 输出, 模式)
    #   auto           = 泛洪抠图, 移除过多则圆角卡片兜底
    #   dark_bg_tight  = 近纯白背景替换为深色底板 (白底白人物海报)
    #   dark_bg_light  = 浅灰低饱和背景替换为深色底板 (华强渐变灰背景)
    #   dark_bg_floor  = 白底替换为游戏地板色, 无卡片边框 (与场景融为一体)
    (r"C:\Users\Lenovo\Downloads\野生狗奶.jpg",
     os.path.join(ROOT, "首领敌人图", "3.png"), "dark_bg_floor"),
    (r"C:\Users\Lenovo\Downloads\旺仔小乔2025探寻者演唱会海报(官方).jpg_2026.08.27.jpg",
     os.path.join(ROOT, "首领敌人图", "2.png"), "dark_bg_tight"),
    (os.path.join(ROOT, "华强.jpg"),
     os.path.join(ROOT, "华强.png"), "dark_bg_light"),
    (os.path.join(ROOT, "首领敌人图", "1.png"),
     os.path.join(ROOT, "首领敌人图", "1.png"), "auto"),
    (os.path.join(ROOT, "美团袋鼠.png"),
     os.path.join(ROOT, "美团袋鼠.png"), "auto"),
]

CARD_FALLBACK = 0.55  # 移除比例超过此值 -> 圆角卡片保留整图


def bilinear_bg(h, w, tl, tr, bl, br):
    """四角颜色双线性重建的逐像素背景估计 (h,w,3)"""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    tx = xx / max(1.0, w - 1.0)
    ty = yy / max(1.0, h - 1.0)
    top = tl[None, None, :] * (1 - tx)[:, :, None] + tr[None, None, :] * tx[:, :, None]
    bot = bl[None, None, :] * (1 - tx)[:, :, None] + br[None, None, :] * tx[:, :, None]
    return top * (1 - ty)[:, :, None] + bot * ty[:, :, None]


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


def rounded_card_alpha(h, w, r=26):
    """圆角卡片遮罩: 内部 255, 圆角平滑过渡"""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    alpha = np.full((h, w), 255.0)
    for cx, cy in ((r, r), (w - 1 - r, r), (r, h - 1 - r), (w - 1 - r, h - 1 - r)):
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        alpha = np.minimum(alpha, np.clip((d - r + 1.0) * 255.0, 0, 255))
    return alpha.astype(np.uint8)


def dark_bg_replace(rgb, mode="tight"):
    """白底替换: 把与边缘连通的近白/浅灰背景换成深色底板 (浅色人物在深底上显形)"""
    h, w = rgb.shape[:2]
    if mode == "tight":
        near = (rgb.min(axis=2) > 242)                       # 近纯白背景
    elif mode == "floor":
        near = (rgb.min(axis=2) > 242)                       # 近纯白背景
    else:
        near = ((rgb.min(axis=2) > 140)                      # 浅灰渐变背景
                & ((rgb.max(axis=2) - rgb.min(axis=2)) < 35))
    if mode == "floor":
        plate = np.array([48, 50, 48])                       # 游戏地板色 #303230
        draw_border = False
    else:
        plate = np.array([34, 34, 40])                       # 深色底板
        draw_border = True
    mask = flood_from_edges(near)
    out = rgb.copy()
    out[mask] = plate
    alpha = rounded_card_alpha(h, w)
    if draw_border:
        # 卡片边缘一圈细边
        solid = alpha > 128
        er = solid.copy()
        er[1:, :] &= solid[:-1, :]
        er[:-1, :] &= solid[1:, :]
        er[:, 1:] &= solid[:, :-1]
        er[:, :-1] &= solid[:, 1:]
        border = solid & ~er
        out[border] = (120, 122, 132)
    return out, alpha, float(mask.mean() * 100)


def process(rgb):
    h, w = rgb.shape[:2]
    p = 8
    tl = np.median(rgb[:p, :p].reshape(-1, 3), axis=0)
    tr = np.median(rgb[:p, -p:].reshape(-1, 3), axis=0)
    bl = np.median(rgb[-p:, :p].reshape(-1, 3), axis=0)
    br = np.median(rgb[-p:, -p:].reshape(-1, 3), axis=0)
    corners = np.stack([tl, tr, bl, br])
    corner_bright = corners.min() > 200
    corner_dark = corners.max() < 60
    bg_est = bilinear_bg(h, w, tl, tr, bl, br)
    tol = 22 if corner_bright else (30 if corner_dark else 26)
    near = (np.abs(rgb.astype(np.int32) - bg_est) <= tol).all(axis=2)
    mask = flood_from_edges(near)
    removed = float(mask.mean())
    if removed > CARD_FALLBACK:
        # 白底白主体等无法分离场景: 整图保留为圆角卡片
        alpha = rounded_card_alpha(h, w)
        return rgb, alpha, "card", removed
    alpha = np.full((h, w), 255, dtype=np.uint8)
    alpha[mask] = 0
    grow = np.zeros_like(mask)
    grow[1:, :] |= mask[:-1, :]
    grow[:-1, :] |= mask[1:, :]
    grow[:, 1:] |= mask[:, :-1]
    grow[:, :-1] |= mask[:, 1:]
    loose = (np.abs(rgb.astype(np.int32) - bg_est) <= tol + 40).all(axis=2)
    fringe = grow & ~mask & loose
    alpha[fringe] = 100
    return rgb, alpha, "cutout", removed


for src, dst, mode in JOBS:
    print("process:", os.path.basename(src), "->", os.path.relpath(dst, ROOT))
    surf = pygame.image.load(src).convert()
    w, h = surf.get_size()
    rgb = pygame.surfarray.array3d(surf).copy().transpose(1, 0, 2)  # (h,w,3)
    if mode in ("dark_bg_tight", "dark_bg_light", "dark_bg_floor"):
        rgb_out, alpha, removed = dark_bg_replace(
            rgb, "tight" if mode == "dark_bg_tight" else
                 ("floor" if mode == "dark_bg_floor" else "light"))
        print(f"  size={w}x{h} mode={mode} replaced={removed:.1f}%")
    else:
        rgb_out, alpha, mode2, removed = process(rgb)
        print(f"  size={w}x{h} mode={mode2} removed={removed * 100:.1f}%")
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.surfarray.pixels3d(out)[:, :, :] = rgb_out.transpose(1, 0, 2)
    pygame.surfarray.pixels_alpha(out)[:, :] = alpha.T
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    pygame.image.save(out, dst)

pygame.quit()
print("ALL DONE")
