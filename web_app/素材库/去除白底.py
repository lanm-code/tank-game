# -*- coding: utf-8 -*-
"""
去除白底工具(本地离线,基于 pygame + numpy,无需联网)
=====================================================
原理:
  1. 找出"接近白色"的像素作为背景候选;
  2. 从图片四边做连通泛洪(BFS),只有和背景连通的白色才变透明
     —— 主体内部的白色(如鸡蛋的蛋白、奶盒、高光)不会被误删;
  3. 背景与主体的交界做 2 像素羽化,消除 JPEG 压缩产生的白边;
  4. 按主体包围盒裁剪,输出真 PNG(带 alpha 通道)到 素材库/透明版/。

用法:
  python 去除白底.py            # 处理素材库全部 png/jpg
  python 去除白底.py 奶蛋.png   # 只处理指定文件(相对素材库路径)

特殊处理:
  - 子弹种类/奶蛋.png: 自动检测并裁掉底部的灰绿"桌面";
  - 3D图: 只去白,保留地板(如需裁地板请手动指定裁剪比例)。
"""
import os
import sys
from collections import deque

import numpy as np
import pygame

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "透明版")

TOL = 30          # 背景判定容差:三通道都 >= 255-TOL 视为"近白"
FLOOR_MARGIN = 8  # 奶蛋裁桌面时底部额外留白(px)
CROP_MARGIN = 4   # 裁剪时四周留白(px)


def load_array(path):
    surf = pygame.image.load(path).convert_alpha()
    w, h = surf.get_size()
    arr = pygame.surfarray.array3d(surf).transpose(1, 0, 2).astype(np.int32)
    return arr, (w, h)


def flood_border_connected(mask):
    """BFS:返回与图像边界连通的背景像素(bool 数组)。"""
    h, w = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    q = deque()
    for y in range(h):
        for x in (0, w - 1):
            if mask[y, x] and not visited[y, x]:
                visited[y, x] = True
                q.append((y, x))
    for x in range(w):
        for y in (0, h - 1):
            if mask[y, x] and not visited[y, x]:
                visited[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not visited[ny, nx]:
                visited[ny, nx] = True
                q.append((ny, nx))
    return visited


def dilate(mask, n=1):
    out = mask.copy()
    for _ in range(n):
        prev = out
        out = prev.copy()
        out[1:, :] |= prev[:-1, :]
        out[:-1, :] |= prev[1:, :]
        out[:, 1:] |= prev[:, :-1]
        out[:, :-1] |= prev[:, 1:]
    return out


def remove_white(arr, tol=TOL):
    cand = np.all(arr >= 255 - tol, axis=2)
    bg = flood_border_connected(cand)
    # 羽化:背景外扩 1 圈 alpha=110,2 圈 alpha=200
    ring1 = dilate(bg, 1) & ~bg
    ring2 = dilate(bg, 2) & ~dilate(bg, 1)
    alpha = np.full(bg.shape, 255, dtype=np.uint8)
    alpha[bg] = 0
    alpha[ring1] = 110
    alpha[ring2] = 200
    return alpha


def floor_cut_row_3d(arr, w, h):
    """3D图专用:切到坦克履带底边,下方渐隐阴影带/白底全部切除。
    判据:自下而上找最后一行「行中位数」仍具坦克特征(饱和度≥30 或 极暗≤110)的行。
    履带区:彩色坦克=饱和色,黑坦克=极暗;阴影渐隐带=低饱和中等亮度。"""
    mx = arr.max(axis=2)
    rng = mx - arr.min(axis=2)
    for y in range(h - 1, -1, -1):
        med = np.median(arr[y].reshape(-1, 3), axis=0)
        r = int(med.max() - med.min())
        m = int(med.max())
        if r >= 30 or m <= 110:
            return min(h, y + 2)
    return h


def remove_shadow(alpha, arr, w, h, body_like):
    """阴影去除:按"行密度"找主体底边,整体切除下方阴影带,并做列间清理。

    坦克本体行:body_like 像素多(数百);阴影行:稀疏(反光碎块 ≤100)。
    切线 = 最后一行 body_like 计数 ≥ max(60, 峰值40%) 的行 + 2。
    """
    counts = body_like.sum(axis=1)
    maxc = int(counts.max())
    if maxc < 60:
        return
    thr = max(60, int(maxc * 0.4))
    cut = h
    for y in range(h - 1, -1, -1):
        if counts[y] >= thr:
            cut = min(h, y + 2)
            break
    alpha[cut:, :] = 0
    # 列间清理:主体底边在切线之上的列,其下方非主体像素(阴影)一并删除
    for x in range(w):
        col = np.where(body_like[:, x])[0]
        if len(col) == 0:
            continue
        b = int(col.max())
        if b < cut - 1:
            seg = body_like[b + 1:cut, x]
            alpha[b + 1:cut, x] = np.where(seg, alpha[b + 1:cut, x], 0)


def convert(path, rel):
    arr, (w, h) = load_array(path)
    alpha = remove_white(arr)
    if "3D" in rel or "3d" in rel:
        cut = floor_cut_row_3d(arr, w, h)
        alpha[cut:, :] = 0
        print(f"   3D图:履带以下渐隐阴影/白底已切除(保留 0~{cut} 行)")
    # 阴影去除:奶蛋(主体为暖色,底部暗色阴影带按列切除)
    if "奶蛋" in os.path.basename(path):
        warm = arr[:, :, 0].astype(np.int32) - arr[:, :, 2].astype(np.int32)
        remove_shadow(alpha, arr, w, h, warm >= 80)
        print("   奶蛋:底部阴影已去除")
    # 裁剪到主体包围盒
    ys, xs = np.where(alpha > 0)
    if len(xs) == 0:
        print(f"   [警告] {rel}: 未检测到主体,输出原图")
        x0, y0, x1, y1 = 0, 0, w - 1, h - 1
    else:
        x0 = max(0, int(xs.min()) - CROP_MARGIN)
        y0 = max(0, int(ys.min()) - CROP_MARGIN)
        x1 = min(w - 1, int(xs.max()) + CROP_MARGIN)
        y1 = min(h - 1, int(ys.max()) + CROP_MARGIN)
    sub_arr = arr[y0:y1 + 1, x0:x1 + 1]
    sub_alpha = alpha[y0:y1 + 1, x0:x1 + 1]
    buf = np.empty((sub_arr.shape[0], sub_arr.shape[1], 4), dtype=np.uint8)
    buf[..., :3] = sub_arr
    buf[..., 3] = sub_alpha
    raw = np.ascontiguousarray(buf).tobytes()
    img = pygame.image.frombuffer(raw, (sub_arr.shape[1], sub_arr.shape[0]), "RGBA")
    surf = pygame.Surface((sub_arr.shape[1], sub_arr.shape[0]), pygame.SRCALPHA)
    surf.blit(img, (0, 0))
    out_rel = rel.replace("\\", "/")
    out_path = os.path.join(OUT_DIR, *out_rel.split("/"))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    pygame.image.save(surf, out_path)
    print(f"   OK -> 透明版/{out_rel}  ({x1 - x0 + 1}x{y1 - y0 + 1})")


def main():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1, 1))
    exts = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
    targets = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs
                   if d != os.path.basename(OUT_DIR) and not d.startswith("_")]
        for f in files:
            if f.lower().endswith(exts) and not f.startswith("_"):
                targets.append(os.path.join(root, f))
    if len(sys.argv) > 1:
        wanted = os.path.normpath(os.path.join(ROOT, sys.argv[1]))
        targets = [t for t in targets if os.path.normpath(t) == wanted]
        if not targets:
            print("找不到:", sys.argv[1])
            return
    for path in sorted(targets):
        rel = os.path.relpath(path, ROOT)
        print("处理:", rel)
        convert(path, rel)
    print("完成,输出目录:", OUT_DIR)


if __name__ == "__main__":
    main()
