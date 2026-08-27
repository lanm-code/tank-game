# -*- coding: utf-8 -*-
"""墙体/地块纹理生成器: 输出 64x64 高细节像素风 PNG 到 素材库\墙体纹理\
运行: py -3.14 _gen_wall_textures.py  (可反复运行微调)
设计: 暗底上高对比; 每种元素独特剪影/图案/图标; 1px 深色描边 (半透明元素用亮边)
"""
import os
import sys
import random

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import pygame

# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

pygame.init()
pygame.display.set_mode((64, 64))

OUT = os.path.normpath(os.path.join(HERE, "..", "..", "素材库", "墙体纹理"))
os.makedirs(OUT, exist_ok=True)
S = 64


def shade(c, f):
    return (min(255, int(c[0] * f)), min(255, int(c[1] * f)), min(255, int(c[2] * f)))


def new_surf(alpha=False):
    return pygame.Surface((S, S), pygame.SRCALPHA if alpha else 0)


def save(s, name):
    pygame.image.save(s, os.path.join(OUT, name))
    print("saved:", name)


def bevel_fill(s, base, light=1.18, dark=0.72, border=None, tl=3, br=3):
    """立体底座: 顶/左亮边 + 底/右暗边 + 深色描边"""
    s.fill(shade(base, 1.0))
    pygame.draw.polygon(s, shade(base, light), [(0, 0), (S, 0), (S - br, br), (tl, br), (tl, S - br), (0, S)])
    pygame.draw.polygon(s, shade(base, dark), [(S, 0), (S, S), (0, S), (0, S - br), (S - br, S - br), (S - br, tl)])
    if border:
        pygame.draw.rect(s, border, (0, 0, S, S), 1)


# ---------------------------------------------------------------- 砖块
def brick(damaged=False):
    s = new_surf()
    bevel_fill(s, (150, 102, 74), border=(96, 60, 42))
    seam = (96, 60, 42)
    light = (188, 138, 96)
    dark = (112, 74, 52)
    step = 16
    for r in range(0, S, step):
        pygame.draw.line(s, seam, (0, r), (S, r), 1)
        off = (r // step) % 2 * (step // 2)
        for c in range(off, S, step):
            if c > 0:
                pygame.draw.line(s, seam, (c, r), (c, min(r + step, S)), 1)
        # 每块砖自身的顶亮底暗 (立体感)
        for c in range(off, S, step):
            x0 = max(0, c)
            x1 = min(S, c + step)
            pygame.draw.line(s, light, (x0 + 1, r + 1), (x1 - 1, r + 1), 1)
            pygame.draw.line(s, dark, (x0 + 1, min(r + step, S) - 2),
                             (x1 - 1, min(r + step, S) - 2), 1)
    if damaged:
        rnd = random.Random(7)
        # 裂纹 (深线 + 亮偏移线)
        for _ in range(6):
            x0, y0 = rnd.randint(4, S - 8), rnd.randint(4, S - 8)
            pts = [(x0, y0)]
            for _ in range(3):
                x0 += rnd.randint(-10, 10)
                y0 += rnd.randint(4, 12)
                pts.append((min(S - 3, max(3, x0)), min(S - 3, max(3, y0))))
            pygame.draw.lines(s, (66, 40, 30), False, pts, 1)
            pygame.draw.lines(s, (196, 148, 106), False,
                              [(x + 1, y + 1) for x, y in pts], 1)
        # 缺角崩落 (深坑)
        for (cx, cy, w, h) in ((6, 8, 8, 6), (S - 16, S - 12, 10, 8), (S - 10, 14, 6, 10)):
            pygame.draw.rect(s, (60, 38, 30), (cx, cy, w, h))
            pygame.draw.rect(s, (176, 126, 90), (cx, cy, w, h), 1)
    return s


# ---------------------------------------------------------------- 沙粒
def sand(damaged=False):
    s = new_surf()
    bevel_fill(s, (188, 172, 132) if not damaged else (152, 136, 102),
               border=(128, 112, 82))
    rnd = random.Random(13)
    # 沙丘横带 (亮/暗交替)
    for i, y in enumerate(range(10, S - 6, 14)):
        col = (204, 190, 152) if i % 2 == 0 else (164, 148, 110)
        if damaged:
            col = shade(col, 0.88)
        for x in range(4, S - 4):
            dy = int(3 * __import__("math").sin(x * 0.35 + i * 2.1))
            s.fill(col, (x, y + dy, 1, 2))
    # 颗粒麻点 (受损后变稀)
    n = 16 if damaged else 46
    for _ in range(n):
        x, y = rnd.randint(3, S - 5), rnd.randint(3, S - 5)
        s.fill(rnd.choice([(140, 124, 90), (212, 198, 158)]), (x, y, 2, 2))
    # 小石子簇
    for _ in range(4 if damaged else 7):
        x, y = rnd.randint(6, S - 10), rnd.randint(6, S - 10)
        pygame.draw.circle(s, (120, 104, 76), (x, y), 2)
        s.fill((170, 156, 120), (x - 1, y - 1, 2, 2))
    if damaged:
        for _ in range(2):
            x0, y0 = rnd.randint(6, S - 12), rnd.randint(6, S - 12)
            pygame.draw.line(s, (110, 94, 68), (x0, y0),
                             (x0 + rnd.randint(-10, 10), y0 + 14), 1)
    return s


# ---------------------------------------------------------------- 钢墙
def steel():
    s = new_surf()
    bevel_fill(s, (156, 163, 174), border=(92, 98, 110))
    # 内嵌面板
    pygame.draw.rect(s, (132, 139, 152), (6, 6, S - 12, S - 12), 1)
    pygame.draw.line(s, (206, 212, 222), (7, 7), (S - 8, 7), 1)
    # 十字筋
    pygame.draw.line(s, (114, 120, 134), (S // 2, 8), (S // 2, S - 8), 4)
    pygame.draw.line(s, (114, 120, 134), (8, S // 2), (S - 8, S // 2), 4)
    pygame.draw.line(s, (188, 194, 204), (S // 2 - 1, 8), (S // 2 - 1, S - 8), 1)
    pygame.draw.line(s, (188, 194, 204), (8, S // 2 - 1), (S - 8, S // 2 - 1), 1)
    # 四角铆钉 + 中部两铆钉
    for bx, by in ((10, 10), (S - 14, 10), (10, S - 14), (S - 14, S - 14),
                   (S // 2 - 2, 18), (S // 2 - 2, S - 22)):
        pygame.draw.circle(s, (80, 86, 98), (bx + 2, by + 2), 3)
        pygame.draw.circle(s, (216, 222, 232), (bx + 1, by + 1), 2)
        s.fill((240, 244, 252), (bx, by, 2, 2))
    # 顶边高光
    pygame.draw.line(s, (224, 230, 240), (2, 2), (S - 3, 2), 1)
    return s


# ---------------------------------------------------------------- 木箱
def crate():
    s = new_surf()
    bevel_fill(s, (130, 92, 52), border=(84, 56, 30))
    # 横向木板 (顶亮底暗)
    for r in range(8, S - 4, 16):
        pygame.draw.line(s, (96, 64, 34), (3, r), (S - 4, r), 2)
        pygame.draw.line(s, (168, 122, 72), (3, r - 6), (S - 4, r - 6), 1)
        pygame.draw.line(s, (104, 70, 38), (3, r + 2), (S - 4, r + 2), 1)
    # 交叉斜板
    pygame.draw.line(s, (112, 78, 44), (4, 4), (S - 5, S - 5), 9)
    pygame.draw.line(s, (112, 78, 44), (S - 5, 4), (4, S - 5), 9)
    pygame.draw.line(s, (158, 114, 66), (5, 5), (S - 6, S - 6), 1)
    pygame.draw.line(s, (158, 114, 66), (S - 6, 5), (5, S - 6), 1)
    # 铆钉
    for nx, ny in ((10, 10), (S - 13, 10), (10, S - 13), (S - 13, S - 13)):
        pygame.draw.circle(s, (64, 42, 22), (nx + 1, ny + 1), 2)
        s.fill((206, 166, 110), (nx, ny, 2, 2))
    return s


# ---------------------------------------------------------------- 玻璃墙 (半透明)
def glass():
    s = new_surf(alpha=True)
    s.fill((150, 165, 185, 105))
    pygame.draw.rect(s, (216, 224, 236, 235), (0, 0, S, S), 2)
    pygame.draw.rect(s, (255, 255, 255, 150), (3, 3, S - 6, S - 6), 1)
    # 对角高光条纹
    for off in (8, 26, 44):
        pygame.draw.line(s, (240, 246, 255, 95), (off, S), (S, off), 3)
    pygame.draw.line(s, (240, 246, 255, 150), (14, S - 4), (S - 4, 14), 1)
    # 高光点
    s.fill((255, 255, 255, 190), (10, 10, 4, 4))
    s.fill((255, 255, 255, 120), (46, 40, 3, 3))
    return s


# ---------------------------------------------------------------- 燃油桶
def barrel():
    s = new_surf()
    s.fill((24, 24, 30))
    bevel_fill(s, (70, 70, 80), border=(40, 40, 48))
    # 桶身 (圆角柱)
    pygame.draw.rect(s, (66, 66, 76), (8, 8, S - 16, S - 16), border_radius=8)
    pygame.draw.rect(s, (120, 120, 134), (8, 8, S - 16, S - 16), 1, border_radius=8)
    # 左高光 / 右阴影
    pygame.draw.rect(s, (104, 104, 118), (11, 11, 6, S - 22), border_radius=3)
    pygame.draw.rect(s, (46, 46, 56), (S - 17, 11, 6, S - 22), border_radius=3)
    # 上下箍
    pygame.draw.rect(s, (130, 130, 144), (9, 16, S - 18, 5), border_radius=2)
    pygame.draw.rect(s, (130, 130, 144), (9, S - 21, S - 18, 5), border_radius=2)
    for x in (14, S - 18):
        pygame.draw.circle(s, (66, 66, 76), (x, 18), 2)
        pygame.draw.circle(s, (66, 66, 76), (x, S - 18), 2)
    # 白色叹号 (核心识别)
    pygame.draw.rect(s, (238, 238, 244), (S // 2 - 4, 24, 8, 22))
    pygame.draw.rect(s, (238, 238, 244), (S // 2 - 4, 52, 8, 8))
    # 顶边高光
    pygame.draw.line(s, (150, 150, 162), (11, 9), (S - 12, 9), 1)
    return s


# ---------------------------------------------------------------- 草丛
def grass():
    s = new_surf()
    s.fill((44, 78, 50))
    rnd = random.Random(21)
    # 草叶簇 (双色短竖线, 交错排布)
    for r in range(0, S, 8):
        off = (r // 8) % 2 * 4
        for c in range(off, S, 8):
            for k in range(3):
                x = min(S - 2, c + rnd.randint(0, 5))
                y = r + rnd.randint(0, 5)
                h = rnd.randint(5, 7)
                col = rnd.choice([(58, 100, 62), (32, 60, 38), (80, 122, 84)])
                s.fill(col, (x, y, 1, h))
                s.fill(shade(col, 1.3), (x, y, 1, 1))  # 草尖高光
    pygame.draw.rect(s, (28, 52, 34), (0, 0, S, S), 1)
    return s


# ---------------------------------------------------------------- 水面 (不可通行)
def water():
    s = new_surf()
    s.fill((34, 54, 108))
    for i, y in enumerate(range(0, S, 8)):
        # 两层波纹线 (亮/暗), 正弦偏移
        for x in range(0, S, 2):
            dy = int(2.5 * __import__("math").sin(x * 0.28 + i * 1.7))
            yy = y + 3 + dy
            if 0 <= yy < S:
                s.fill((58, 84, 152) if i % 2 == 0 else (22, 36, 78), (x, yy, 1, 1))
    # 波峰高光点
    rnd = random.Random(5)
    for _ in range(18):
        x = rnd.randint(4, S - 6)
        y = rnd.randint(4, S - 6)
        s.fill((96, 124, 196), (x, y, 2, 1))
    pygame.draw.rect(s, (16, 28, 62), (0, 0, S, S), 1)
    return s


# ---------------------------------------------------------------- 水渍 (半透明湿斑)
def water_stain():
    s = new_surf(alpha=True)
    # 不规则水斑主体 (圆角多边, 四角留空)
    pts = [(12, 4), (S - 8, 8), (S - 3, 26), (S - 12, S - 6), (34, S - 2), (6, S - 14), (2, 34)]
    pygame.draw.polygon(s, (96, 116, 138, 150), pts)
    pygame.draw.polygon(s, (150, 170, 196, 215), pts, 1)
    # 内侧深色小水坑
    pygame.draw.ellipse(s, (74, 92, 112, 130), (16, 18, 30, 22))
    pygame.draw.ellipse(s, (74, 92, 112, 130), (34, 36, 18, 14))
    # 高光短弧
    pygame.draw.line(s, (176, 194, 216, 120), (18, 14), (34, 14), 2)
    pygame.draw.line(s, (176, 194, 216, 120), (38, 34), (48, 30), 2)
    pygame.draw.line(s, (176, 194, 216, 100), (12, 30), (16, 36), 2)
    # 边缘水珠
    for (x, y) in ((46, 8), (S - 14, 18), (S - 8, 44), (30, S - 6)):
        pygame.draw.circle(s, (150, 170, 196, 160), (x, y), 2)
        s.fill((196, 210, 228, 200), (x - 1, y - 1, 1, 1))
    return s


# ---------------------------------------------------------------- 泥沼
def mud():
    s = new_surf()
    s.fill((88, 72, 50))
    rnd = random.Random(9)
    # 横向泥痕
    for y in range(6, S - 4, 10):
        x0 = rnd.randint(2, 8)
        pygame.draw.line(s, (66, 52, 36), (x0, y), (S - rnd.randint(2, 8), y), 2)
        pygame.draw.line(s, (112, 94, 66), (x0, y + 1), (S - 6, y + 1), 1)
    # 深色泥坑
    for (cx, cy, w, h) in ((14, 16, 20, 10), (36, 40, 22, 12), (10, 50, 16, 9)):
        pygame.draw.ellipse(s, (58, 44, 30), (cx, cy, w, h))
        pygame.draw.ellipse(s, (116, 96, 66), (cx, cy, w, h), 1)
    # 小石子
    for _ in range(6):
        x, y = rnd.randint(6, S - 8), rnd.randint(6, S - 8)
        pygame.draw.circle(s, (124, 102, 72), (x, y), 2)
        s.fill((150, 128, 94), (x - 1, y - 1, 1, 1))
    pygame.draw.rect(s, (56, 44, 30), (0, 0, S, S), 1)
    return s


# ---------------------------------------------------------------- 冰面
def ice():
    """不规则半透明冰斑 (与水渍同款形状语言, 四角留空), 亮灰白 + 细斜纹"""
    s = new_surf(alpha=True)
    pts = [(10, 6), (S - 10, 4), (S - 4, 22), (S - 8, S - 10),
           (40, S - 4), (8, S - 14), (4, 36)]
    pygame.draw.polygon(s, (172, 184, 198, 185), pts)
    pygame.draw.polygon(s, (214, 224, 238, 235), pts, 1)
    # 细斜纹 (冰面反光感, 像水渍波纹的直线版)
    for i in range(-S, S, 13):
        pygame.draw.line(s, (196, 206, 218, 175), (i, 0), (i + S, S), 1)
    # 高光短弧
    pygame.draw.line(s, (238, 244, 252, 210), (16, 12), (34, 12), 2)
    pygame.draw.line(s, (238, 244, 252, 150), (36, 30), (46, 26), 2)
    pygame.draw.line(s, (238, 244, 252, 120), (10, 32), (14, 40), 2)
    # 边缘碎冰点
    for (x, y) in ((44, 6), (S - 12, 16), (S - 6, 42), (30, S - 8)):
        pygame.draw.circle(s, (214, 224, 238, 170), (x, y), 2)
        s.fill((238, 244, 252, 210), (x - 1, y - 1, 1, 1))
    return s


# ---------------------------------------------------------------- 尖刺
def spike():
    s = new_surf()
    s.fill((42, 42, 48))
    # 2x2 金属尖刺
    for cx in (16, 48):
        for cy in (16, 48):
            tip = (cx, cy - 20)
            base_l = (cx - 12, cy + 10)
            base_r = (cx + 12, cy + 10)
            pygame.draw.polygon(s, (100, 100, 112), [tip, base_l, base_r])
            pygame.draw.polygon(s, (150, 150, 162), [tip, (cx - 12, cy + 10), (cx + 12, cy + 10)], 1)
            pygame.draw.line(s, (170, 170, 184), tip, (cx, cy + 10), 1)  # 中心棱
            s.fill((196, 196, 208), (cx - 1, cy - 18, 2, 2))  # 针尖高光
    # 底部暗影
    pygame.draw.rect(s, (30, 30, 36), (0, S - 4, S, 4))
    pygame.draw.rect(s, (74, 74, 84), (0, 0, S, S), 1)
    return s


# ---------------------------------------------------------------- 传送门
def portal():
    s = new_surf()
    s.fill((26, 24, 36))
    # 外框 + 同心环
    pygame.draw.rect(s, (128, 122, 150), (0, 0, S, S), 1)
    c = (S // 2, S // 2)
    pygame.draw.circle(s, (110, 104, 132), c, 27, 1)
    pygame.draw.circle(s, (128, 122, 150), c, 26, 3)
    pygame.draw.circle(s, (170, 164, 190), c, 24, 1)
    pygame.draw.circle(s, (140, 134, 162), c, 17, 2)
    pygame.draw.circle(s, (196, 190, 214), c, 14, 1)
    # 内部漩涡弧
    for a0 in (0, 120, 240):
        rect = pygame.Rect(c[0] - 8, c[1] - 8, 16, 16)
        pygame.draw.arc(s, (178, 172, 198), rect, a0 * 0.01745, (a0 + 90) * 0.01745, 1)
    pygame.draw.circle(s, (222, 218, 238), c, 4)
    s.fill((236, 232, 250), (c[0] - 2, c[1] - 8, 1, 1))
    # 环上光点
    import math
    for a in (45, 135, 225, 315):
        x = int(c[0] + 25 * math.cos(math.radians(a)))
        y = int(c[1] + 25 * math.sin(math.radians(a)))
        s.fill((210, 204, 228), (x, y, 2, 2))
    return s


save(brick(False), "brick.png")
save(brick(True), "brick_damaged.png")
save(sand(False), "sand.png")
save(sand(True), "sand_damaged.png")
save(steel(), "steel.png")
save(crate(), "crate.png")
save(glass(), "glass.png")
save(barrel(), "barrel.png")
save(grass(), "grass.png")
save(water(), "water.png")
save(water_stain(), "water_stain.png")
save(mud(), "mud.png")
save(ice(), "ice.png")
save(spike(), "spike.png")
save(portal(), "portal.png")
print("TEXTURES DONE ->", OUT)
pygame.quit()
