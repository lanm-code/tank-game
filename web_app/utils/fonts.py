# -*- coding: utf-8 -*-
"""
稳健字体加载器

问题背景: pygame.font.SysFont 在部分 Windows 环境会因系统字体枚举 bug
(initsysfonts_win32 TypeError) 抛异常, 导致全部中文回退为默认字体 (豆腐块)。
这里直接用 C:\\Windows\\Fonts 下的字体文件加载, 并逐级兜底。
"""
import os
import pygame

_FONT_CACHE = {}

# (tag, 文件名) 候选, 按优先级排列
_CANDIDATES = [
    ("msyhbd", "msyhbd.ttc"),   # 微软雅黑 Bold
    ("msyh", "msyh.ttc"),       # 微软雅黑
    ("simhei", "simhei.ttf"),   # 黑体
    ("deng", "Deng.ttf"),       # 等线
    ("simsun", "simsun.ttc"),   # 宋体
    ("arialbd", "arialbd.ttf"),
    ("arial", "arial.ttf"),
]


def _font_dirs():
    dirs = []
    windir = os.environ.get("WINDIR", r"C:\Windows")
    dirs.append(os.path.join(windir, "Fonts"))
    # Linux/mac 兜底目录
    for d in ("/usr/share/fonts", "/System/Library/Fonts"):
        if os.path.isdir(d):
            dirs.append(d)
    return dirs


def _bundled_fonts():
    """网页版内置字体 (wasm 无系统字体目录; 打包时放在应用根目录)"""
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [
        os.path.join(here, "..", "fonts_msyhbd.ttc"),
        os.path.join(here, "..", "fonts_simhei.ttf"),
        os.path.join(here, "..", "fonts", "msyhbd.ttc"),
        os.path.join(here, "..", "fonts", "simhei.ttf"),
    ]
    return [os.path.normpath(p) for p in cands]


def _find_font_file(bold):
    names = [fname for _tag, fname in _CANDIDATES]
    if bold:
        # 粗体文件优先
        prefer = [fname for tag, fname in _CANDIDATES if tag.endswith("bd")]
        names = prefer + [n for n in names if n not in prefer]
    # 1) 内置字体 (网页版优先, 保证中文不豆腐块)
    for p in _bundled_fonts():
        if os.path.exists(p):
            return p
    # 2) 系统字体
    for fname in names:
        for d in _font_dirs():
            p = os.path.join(d, fname)
            if os.path.exists(p):
                return p
    return None


def load_font(size, bold=False):
    """返回 size 号的字体对象 (带缓存); 永不抛异常。"""
    key = (size, bool(bold))
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    font = None
    path = _find_font_file(bool(bold))
    if path:
        try:
            font = pygame.font.Font(path, size)
            if bold and not path.lower().endswith(("bd.ttc", "bd.ttf")):
                font.set_bold(True)
        except Exception:
            font = None
    if font is None:
        # 兜底 1: SysFont (环境正常时可用, 失败则跳过)
        try:
            font = pygame.font.SysFont(
                "microsoftyahei, simhei, arial", size, bold=bold)
        except Exception:
            font = None
    if font is None:
        # 兜底 2: pygame 内置字体 (无中文, 仅保底不崩)
        font = pygame.font.Font(None, size)
        if bold:
            font.set_bold(True)
    _FONT_CACHE[key] = font
    return font
