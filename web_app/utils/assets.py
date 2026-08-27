# -*- coding: utf-8 -*-
"""
素材资源加载与缓存
Asset loader + rotation cache + white-bg removal
"""
import os
import pygame

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False
    np = None

from core.constants import (BULLET_CONFIG, TANK_COLOR_CONFIG, TankColor,
                            BulletType)

_surface_cache = {}
_rot_cache = {}
_assets_root = None


def _find_assets_root():
    """向上查找 素材库 目录"""
    global _assets_root
    if _assets_root is not None:
        return _assets_root
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "..", "素材库"),
        os.path.join(here, "..", "..", "..", "素材库"),
        os.path.join(here, "..", "..", "..", "..", "素材库"),
    ]
    for c in candidates:
        c = os.path.normpath(c)
        if os.path.exists(c):
            _assets_root = c
            return _assets_root
    _assets_root = ""
    return _assets_root


def _strip_bg(surf):
    """去掉贴图背景: 同时处理白底 (>230) 和黑底 (<25), 近边缘柔化"""
    if surf is None:
        return surf
    try:
        w, h = surf.get_size()
        if _HAS_NUMPY:
            if surf.get_flags() & pygame.SRCALPHA:
                rgb = pygame.surfarray.pixels3d(surf).copy()
                alpha = pygame.surfarray.pixels_alpha(surf)
                # 白色背景
                white_mask = (rgb[:, :, 0] > 230) & (rgb[:, :, 1] > 230) & (rgb[:, :, 2] > 230)
                # 黑色背景
                black_mask = (rgb[:, :, 0] < 25) & (rgb[:, :, 1] < 25) & (rgb[:, :, 2] < 25)
                mask = white_mask | black_mask
                alpha[mask] = 0
                # 近白/近黑柔化
                soft_white = (rgb[:, :, 0] > 200) & (rgb[:, :, 1] > 200) & (rgb[:, :, 2] > 200) & (~mask)
                soft_black = (rgb[:, :, 0] < 50) & (rgb[:, :, 1] < 50) & (rgb[:, :, 2] < 50) & (~mask)
                alpha[soft_white | soft_black] = 60
                del rgb, alpha
                return _flood_strip(surf)
            # 无 alpha 通道
            rgb_data = pygame.surfarray.pixels3d(surf).copy()
            result = pygame.Surface((w, h), pygame.SRCALPHA)
            alpha = pygame.surfarray.pixels_alpha(result)
            alpha[:, :] = 255
            white_mask = (rgb_data[:, :, 0] > 230) & (rgb_data[:, :, 1] > 230) & (rgb_data[:, :, 2] > 230)
            black_mask = (rgb_data[:, :, 0] < 25) & (rgb_data[:, :, 1] < 25) & (rgb_data[:, :, 2] < 25)
            mask = white_mask | black_mask
            alpha[mask] = 0
            soft_white = (rgb_data[:, :, 0] > 200) & (rgb_data[:, :, 1] > 200) & (rgb_data[:, :, 2] > 200) & (~mask)
            soft_black = (rgb_data[:, :, 0] < 50) & (rgb_data[:, :, 1] < 50) & (rgb_data[:, :, 2] < 50) & (~mask)
            alpha[soft_white | soft_black] = 60
            del alpha
            dst_rgb = pygame.surfarray.pixels3d(result)
            dst_rgb[:, :, :] = rgb_data[:, :, :]
            del dst_rgb, rgb_data
            return _flood_strip(result)
        else:
            # 纯 Python 版
            result = pygame.Surface((w, h), pygame.SRCALPHA)
            for x in range(w):
                for y in range(h):
                    px = surf.get_at((x, y))
                    r, g, b = px[0], px[1], px[2]
                    if (r > 230 and g > 230 and b > 230) or (r < 25 and g < 25 and b < 25):
                        a = 0
                    elif (r > 200 and g > 200 and b > 200) or (r < 50 and g < 50 and b < 50):
                        a = 60
                    else:
                        a = 255
                    result.set_at((x, y), (r, g, b, a))
            return result
    except Exception:
        try:
            surf.set_colorkey((255, 255, 255), pygame.RLEACCEL)
        except Exception:
            pass
        return surf


def _flood_strip(surf):
    """边缘主导色洪水填充: 抠掉白/黑以外的纯色背景 (黄底袋鼠/近白底等)。

    仅当边缘颜色统一 (中位绝对差 <= 60) 时执行, 照片背景自动跳过;
    从四边向内洪水传播, 移除与边缘色接近 (容差 26) 的连通区域。
    """
    if surf is None or not _HAS_NUMPY:
        return surf
    try:
        import numpy as np
        w, h = surf.get_size()
        rgb = pygame.surfarray.pixels3d(surf).copy()
        alpha = pygame.surfarray.pixels_alpha(surf)
        # 采样边缘仍不透明的像素 (白/黑底已被上一阶段抠掉)
        edge_px = []
        for x in range(0, w, max(1, w // 40)):
            for y in (0, h - 1):
                if alpha[x, y] > 120:
                    edge_px.append(rgb[x, y])
        for y in range(0, h, max(1, h // 40)):
            for x in (0, w - 1):
                if alpha[x, y] > 120:
                    edge_px.append(rgb[x, y])
        if len(edge_px) < 20:
            del rgb, alpha
            return surf
        arr = np.array(edge_px, dtype=np.int32)
        med = np.median(arr, axis=0)
        spread = np.median(np.abs(arr - med).sum(axis=1))
        if spread > 60:
            del rgb, alpha
            return surf
        tol = 26
        near = (
            (np.abs(rgb[:, :, 0].astype(np.int32) - med[0]) <= tol)
            & (np.abs(rgb[:, :, 1].astype(np.int32) - med[1]) <= tol)
            & (np.abs(rgb[:, :, 2].astype(np.int32) - med[2]) <= tol))
        seed = np.zeros((h, w), dtype=bool)
        seed[0, :] = True
        seed[-1, :] = True
        seed[:, 0] = True
        seed[:, -1] = True
        mask = near & seed
        for _ in range(max(w, h) + 10):
            prev = mask.sum()
            shifted = np.zeros_like(mask)
            shifted[1:, :] |= mask[:-1, :]
            shifted[:-1, :] |= mask[1:, :]
            shifted[:, 1:] |= mask[:, :-1]
            shifted[:, :-1] |= mask[:, 1:]
            mask = shifted & near
            if mask.sum() == prev:
                break
        alpha[mask] = 0
        del rgb, alpha
        return surf
    except Exception:
        return surf


def _load(path):
    if not path or not os.path.exists(path):
        return None
    # 统一走缓存: 素材路径固定, 进程内内容不变;
    # 之前 3D 图强制重载会导致主菜单每帧重新加载+去背景+缩放大图
    if path in _surface_cache:
        return _surface_cache[path]
    try:
        if "新3D图" in path or "首领敌人" in path:
            # 新3D图 / Boss 立绘已预处理为透明底 PNG: 保留 alpha, 不再去背景
            surf = pygame.image.load(path).convert_alpha()
        else:
            surf = pygame.image.load(path).convert()
    except Exception:
        try:
            surf = pygame.image.load(path)
        except Exception:
            surf = None
    if surf is not None and "新3D图" not in path and "首领敌人" not in path:
        surf = _strip_bg(surf)
    _surface_cache[path] = surf
    return surf


def _scale_to(surf, size, keep_alpha=False):
    if surf is None:
        return None
    # 先缩放, 再做一次去白 (缩放会产生新的白色边缘)
    try:
        scaled = pygame.transform.smoothscale(surf, size)
    except Exception:
        scaled = pygame.transform.scale(surf, size)
    # 缩放后重新去背景 (透明底素材保持 alpha)
    if scaled is not None and not keep_alpha:
        scaled = _strip_bg(scaled)
    return scaled


def get_tank_top_view(color, size=None):
    """加载坦克俯视图 (用于游戏内渲染)"""
    cfg = TANK_COLOR_CONFIG.get(color) or TANK_COLOR_CONFIG[TankColor.BLACK]
    root = _find_assets_root()
    path = os.path.join(root, "坦克示意图", "俯视图", cfg["top_view"])
    surf = _load(path)
    if surf is not None and size is not None:
        key = (path, tuple(size), "top")
        if key not in _surface_cache:
            _surface_cache[key] = _scale_to(surf, size)
        return _surface_cache[key]
    return surf


def get_tank_view3d(color, size=None):
    """加载坦克3D图 (用于选择界面, 使用新3D图文件夹中已抠背景的图片)"""
    cfg = TANK_COLOR_CONFIG.get(color) or TANK_COLOR_CONFIG[TankColor.BLACK]
    root = _find_assets_root()
    fname = cfg.get("view3d") or cfg["top_view"]
    sub = "新3D图" if cfg.get("view3d") else "俯视图"
    path = os.path.join(root, "坦克示意图", sub, fname)
    surf = _load(path)
    if surf is not None and size is not None:
        key = (path, tuple(size), "3d")
        if key not in _surface_cache:
            _surface_cache[key] = _scale_to(surf, size, keep_alpha=("新3D图" in path))
        return _surface_cache[key]
    return surf


def _circular_crop(surf, diameter):
    """把图片裁成圆形 (居中, 透明圆外区域)"""
    d = max(1, int(diameter))
    try:
        scaled = pygame.transform.smoothscale(surf, (d, d))
    except Exception:
        scaled = pygame.transform.scale(surf, (d, d))
    mask = pygame.Surface((d, d), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (d // 2, d // 2), d // 2)
    out = pygame.Surface((d, d), pygame.SRCALPHA)
    out.blit(scaled, (0, 0))
    out.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return out


def get_tank_avatar(color, size):
    """加载坦克头像并裁成圆形 (用于 HUD / 坦克头顶徽章)"""
    cfg = TANK_COLOR_CONFIG.get(color) or TANK_COLOR_CONFIG[TankColor.BLACK]
    fname = cfg.get("avatar")
    if not fname:
        return None
    root = _find_assets_root()
    path = os.path.join(root, "坦克车头像", fname)
    if not os.path.exists(path):
        return None
    d = int(size)
    key = (path, d, "avatar")
    if key in _surface_cache:
        return _surface_cache[key]
    surf = _load(path)
    if surf is None:
        _surface_cache[key] = None
        return None
    _surface_cache[key] = _circular_crop(surf, d)
    return _surface_cache[key]


def _scale_to_fit_content(surf, size):
    """裁剪到内容边界后按原始比例缩放 (子弹图保持形状, 不拉伸)"""
    if surf is None:
        return None
    crop = None
    try:
        if _HAS_NUMPY:
            import numpy as np
            alpha = pygame.surfarray.pixels_alpha(surf)
            ys, xs = np.where(alpha > 40)
            if len(xs) >= 10:
                x0, x1 = int(xs.min()), int(xs.max())
                y0, y1 = int(ys.min()), int(ys.max())
                w = max(1, x1 - x0 + 1)
                h = max(1, y1 - y0 + 1)
                crop = surf.subsurface((x0, y0, w, h)).copy()
            del alpha
    except Exception:
        crop = None
    if crop is None:
        crop = surf
    try:
        cw, ch = crop.get_size()
        scale = min(size[0] / cw, size[1] / ch)
        tw = max(1, int(cw * scale))
        th = max(1, int(ch * scale))
        scaled = pygame.transform.smoothscale(crop, (tw, th))
    except Exception:
        cw, ch = crop.get_size()
        scale = min(size[0] / cw, size[1] / ch)
        tw = max(1, int(cw * scale))
        th = max(1, int(ch * scale))
        scaled = pygame.transform.scale(crop, (tw, th))
    scaled = _strip_bg(scaled)
    return scaled


def get_bullet_image(bullet_type, size=None):
    cfg = BULLET_CONFIG.get(bullet_type)
    if not cfg:
        return None
    root = _find_assets_root()
    path = os.path.join(root, "子弹种类", cfg["image"])
    # 子弹原图极大 (麦克风 1280×2275 等), 全尺寸抠图+洪水填充一次要卡数秒
    # (图鉴子弹页一次加载 8 张会直接无响应)。先降到上限尺寸再抠,
    # 游戏内子弹渲染 ≤260px, 视觉无差但快几个数量级。
    surf = _bullet_master(path)
    if surf is not None and size is not None:
        key = (path, tuple(size), "bullet")
        if key not in _surface_cache:
            _surface_cache[key] = _scale_to_fit_content(surf, size)
        return _surface_cache[key]
    return surf


_BULLET_MASTER_MAX = 512
_bullet_master_cache = {}


def _bullet_master(path):
    """子弹图母版: 原图缩小到 ≤512px 后一次性抠底缓存, 之后所有尺寸从母版缩放"""
    if path in _bullet_master_cache:
        return _bullet_master_cache[path]
    try:
        raw = pygame.image.load(path).convert_alpha()
    except Exception:
        raw = None
    if raw is None:
        _bullet_master_cache[path] = None
        return None
    try:
        w, h = raw.get_size()
        m = max(w, h)
        if m > _BULLET_MASTER_MAX:
            sc = _BULLET_MASTER_MAX / m
            raw = pygame.transform.smoothscale(
                raw, (max(1, int(w * sc)), max(1, int(h * sc))))
        surf = _strip_bg(raw)
    except Exception:
        surf = raw
    _bullet_master_cache[path] = surf
    return surf


def get_rotated(surface, angle_deg, step=2):
    """旋转并缓存 (按 step 度量化以控制缓存体积)"""
    if surface is None:
        return None
    a = int(angle_deg // step) * step
    key = (id(surface), a % 360)
    if key not in _rot_cache:
        try:
            rot = pygame.transform.rotate(surface, a)
            # 旋转后可能产生黑边, 再去白/黑
            rot = _strip_bg(rot)
            _rot_cache[key] = rot
        except Exception:
            _rot_cache[key] = surface
    return _rot_cache[key]


def get_boss_image(boss_index, size=None):
    """加载Boss图片 (index: 1/2/3, 对应第5/10/15关Boss)"""
    root = _find_assets_root()
    path = os.path.join(root, "首领敌人", "首领敌人图", f"{boss_index}.png")
    surf = _load(path)
    if surf is not None and size is not None:
        key = (path, tuple(size), "boss")
        if key not in _surface_cache:
            _surface_cache[key] = _scale_to(surf, size, keep_alpha=True)
        return _surface_cache[key]
    return surf


def get_boss_image_file(name, size=None):
    """按文件名加载Boss图 (新首领: 华强.png / 美团袋鼠.png 等)"""
    root = _find_assets_root()
    if not root:
        return None
    base = os.path.join(root, "首领敌人")
    for cand in (os.path.join(base, name),
                 os.path.join(base, "首领敌人图", name)):
        if not os.path.exists(cand):
            continue
        surf = _load(cand)
        if surf is None:
            return None
        if size is not None:
            key = (cand, tuple(size), "bossfile")
            if key not in _surface_cache:
                _surface_cache[key] = _scale_to(surf, size, keep_alpha=True)
            return _surface_cache[key]
        return surf
    return None
