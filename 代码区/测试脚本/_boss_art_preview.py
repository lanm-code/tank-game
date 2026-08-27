# -*- coding: utf-8 -*-
"""临时验证: 预处理后的 Boss 立绘经游戏加载管线(保留alpha/缩放)的实际效果"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import pygame

# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

pygame.init()
pygame.display.set_mode((100, 100))

from utils.assets import get_boss_image, get_boss_image_file

OUT = r"D:\DeepSeek-Harness-EAC\Deepseek Harness EAC\deepseek工作区\坦克游戏\素材检查\boss_预览3.png"

surf = pygame.Surface((1600, 440))
surf.fill((48, 50, 48))  # 地板色 #303230

imgs = [
    ("Boss1 篮球霸王", get_boss_image(1, (180, 180)), 60),
    ("Boss2 旺仔小乔", get_boss_image(2, (190, 190)), 360),
    ("Boss3 野生狗奶", get_boss_image(3, (210, 210)), 670),
    ("Boss4 袋鼠快递王", get_boss_image_file("美团袋鼠.png", (190, 190)), 1000),
    ("Boss5 华强瓜王", get_boss_image_file("华强.png", (190, 190)), 1310),
]
for name, img, x in imgs:
    if img:
        surf.blit(img, (x, (440 - img.get_height()) // 2))
        print(name, "OK", img.get_size())
    else:
        print(name, "LOAD FAIL")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
pygame.image.save(surf, OUT)
print("saved:", OUT)
pygame.quit()
