# -*- coding: utf-8 -*-
"""一次性: 测试脚本移入 测试脚本/ 子目录后, 批量修路径
1. 每个 .py 在 import pygame 之后插入游戏根目录 sys.path (父目录)
2. 修 3 个素材工具的 素材库 相对路径 (.. → ..\..)
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = HERE  # 脚本本体就在本文件夹里

PATH_SHIM = (
    "# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径\n"
    "import sys as _sys, os as _os\n"
    "_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))\n"
)

ROOT_FIXES = {
    "_recolor_boss_bg.py": (('join(HERE, "..", "素材库"', 'join(HERE, "..", "..", "素材库"'),),
    "_preprocess_boss_art.py": (('join(HERE, "..", "素材库"', 'join(HERE, "..", "..", "素材库"'),),
    "_gen_wall_textures.py": (('join(HERE, "..", "素材库"', 'join(HERE, "..", "..", "素材库"'),),
}

patched = 0
for name in sorted(os.listdir(SCRIPTS)):
    if not name.endswith(".py"):
        continue
    p = os.path.join(SCRIPTS, name)
    with open(p, "r", encoding="utf-8") as f:
        src = f.read()
    out = src
    # 1) sys.path shim: 插在第一个 import pygame 行之后 (含行尾注释), 
    #    兜底插在第一个游戏模块导入之前
    if PATH_SHIM not in src:
        m = re.search(r"^import pygame.*$", src, re.M)
        if not m:
            m = re.search(r"^(from (core|entities|systems|ui|utils)[\. ])", src, re.M)
        if m:
            out = src[:m.end()] + "\n" + PATH_SHIM + src[m.end():]
    # 2) 素材库相对路径修正
    for old, new in ROOT_FIXES.get(name, ()):
        out = out.replace(old, new)
    if out != src:
        with open(p, "w", encoding="utf-8") as f:
            f.write(out)
        patched += 1

print(f"patched {patched} files")
