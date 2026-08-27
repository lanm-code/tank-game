# -*- coding: utf-8 -*-
"""临时验证: 子弹 vs 墙体规则 (方块血量制 v2: 砖=56/沙=28)
运行: py -3.14 _wall_hit_test.py
"""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
# 已移入 测试脚本/ 子目录: 把游戏根目录(上一级)加入搜索路径
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from core.constants import *
from entities.wall import Wall
from entities.bullet import Bullet

pygame.init()
pygame.display.set_mode((100, 100))
TILE = TILE_SIZE
MAP = pygame.Rect(0, 0, 1920, 1024)


def shoot(w, btype, owner=1, start_x=None):
    cfg = BULLET_CONFIG[btype]
    hit_r = cfg["radius"] + 4
    if start_x is None:
        start_x = w.x - (cfg["speed"] + hit_r) + 2
    b = Bullet(start_x, w.y + w.height / 2, 0, btype, owner)
    b.update(16.666, [w], None, MAP, [])
    return b


def run():
    # 1) 锚点: 砖块 hp = 56 = 飞刀伤害; 沙粒 hp = 22 = 篮球伤害
    assert WALL_CONFIG[WallType.BRICK]["hp"] == 56 == BULLET_CONFIG[BulletType.KNIFE]["damage"], "砖块血量锚点错误"
    assert WALL_CONFIG[WallType.SAND]["hp"] == 22 == BULLET_CONFIG[BulletType.BASKETBALL]["damage"], "沙粒血量锚点错误"
    print('1 血量锚点: 砖=56=飞刀, 沙=22=篮球 (期望 True)')

    # 2) 鸡蛋 (20) 打砖墙 -> 扣 20 剩 36, 墙不毁, 子弹消失
    w = Wall(5, 5, WallType.BRICK)
    b = shoot(w, BulletType.EGG)
    print('2 鸡蛋打砖墙: hp =', w.hp, '| destroyed =', w.destroyed,
          '| bullet.dead =', b.dead, '(期望 36/False/True)')

    # 3) 飞刀 (56) 打砖墙 -> 1 发打穿, 子弹消失, ricochet 不消耗
    w2 = Wall(5, 5, WallType.BRICK)
    b2 = shoot(w2, BulletType.KNIFE)
    print('3 飞刀打砖墙: destroyed =', w2.destroyed, '| bullet.dead =', b2.dead,
          '| ricochet =', b2.ricochet, '(期望 True/True/3)')

    # 4) 飞刀打钢墙 -> 墙不毁, 反弹, ricochet-1
    w3 = Wall(5, 5, WallType.STEEL)
    b3 = shoot(w3, BulletType.KNIFE)
    print('4 飞刀打钢墙: destroyed =', w3.destroyed, '| bullet.dead =', b3.dead,
          '| ricochet =', b3.ricochet, '(期望 False/False/2)')

    # 5) 鸡蛋打钢墙 -> 墙不毁, 子弹消失
    w4 = Wall(5, 5, WallType.STEEL)
    b4 = shoot(w4, BulletType.EGG)
    print('5 鸡蛋打钢墙: destroyed =', w4.destroyed, '| bullet.dead =', b4.dead,
          '(期望 False/True)')

    # 6) 碰撞余量: 子弹停在墙边 11px (半径8, 旧规则打不到) -> 应命中扣血
    w5 = Wall(5, 5, WallType.BRICK)
    b5 = Bullet(320 - 11, 352, 0, BulletType.EGG, 1)
    b5.update(16.666, [w5], None, MAP, [])
    print('6 边缘11px打砖墙: hp =', w5.hp, '(期望 36)')

    # 7) 炮弹 (28) 打砖墙: 第 1 发剩 28, 第 2 发打穿
    w7 = Wall(5, 5, WallType.BRICK)
    shoot(w7, BulletType.CANNON)
    hit1 = (w7.hp == 28 and not w7.destroyed)
    shoot(w7, BulletType.CANNON)
    print('7 炮弹2发破砖: 第1发hp =', w7.hp + 28 if not hit1 else 28,
          '| 第2发 destroyed =', w7.destroyed, '(期望 True)')

    # 8) 炮弹 (28) 打沙粒 -> 1 发打穿
    w8 = Wall(5, 5, WallType.SAND)
    b8 = shoot(w8, BulletType.CANNON)
    print('8 炮弹打沙粒: destroyed =', w8.destroyed, '| bullet.dead =', b8.dead,
          '(期望 True/True)')

    # 8b) 篮球 (22) 打沙粒 -> 1 发打穿 (沙粒 = 一发篮球的量)
    w8b = Wall(5, 5, WallType.SAND)
    b8b = shoot(w8b, BulletType.BASKETBALL)
    print('8b 篮球打沙粒: destroyed =', w8b.destroyed, '| bullet.dead =', b8b.dead,
          '(期望 True/True)')

    # 9) 鸡蛋 (20) 打沙粒: 第 1 发剩 2, 第 2 发打穿
    w9 = Wall(5, 5, WallType.SAND)
    shoot(w9, BulletType.EGG)
    hp1 = w9.hp
    shoot(w9, BulletType.EGG)
    print('9 鸡蛋2发碎沙: 第1发hp =', hp1, '| 第2发 destroyed =', w9.destroyed,
          '(期望 2/True)')

    # 10) 篮球 (22, ricochet=3) 打砖墙 -> 扣血, 子弹消失, 不反弹 (ricochet 不消耗)
    w10 = Wall(5, 5, WallType.BRICK)
    b10 = shoot(w10, BulletType.BASKETBALL)
    print('10 篮球打砖墙: hp =', w10.hp, '| bullet.dead =', b10.dead,
          '| ricochet =', b10.ricochet, '(期望 34/True/3)')

    # 11) 奶蛋 (15, pierce=1) 打砖墙 -> 扣 15, 子弹消失, pierce 不消耗
    w11 = Wall(5, 5, WallType.BRICK)
    b11 = shoot(w11, BulletType.MILKY_EGG)
    print('11 奶蛋打砖墙: hp =', w11.hp, '| bullet.dead =', b11.dead,
          '| pierce =', b11.pierce, '(期望 41/True/1)')

    # 12) 木箱 / 油桶: 任意子弹 1 发打碎
    w12a = Wall(5, 5, WallType.CRATE)
    b12a = shoot(w12a, BulletType.EGG)
    w12b = Wall(5, 5, WallType.BARREL)
    b12b = shoot(w12b, BulletType.EGG)
    print('12 木箱/油桶1发碎: crate =', w12a.destroyed, '| barrel =', w12b.destroyed,
          '(期望 True/True)')

    # 13) 玻璃墙: 子弹穿过且玻璃碎, 子弹继续飞
    w13 = Wall(5, 5, WallType.GLASS)
    b13 = shoot(w13, BulletType.EGG)
    print('13 玻璃墙: destroyed =', w13.destroyed, '| bullet.dead =', b13.dead,
          '(期望 True/False)')

    # 14) 敌人炮弹对称: owner=-1 炮弹打砖 -> 扣 28 剩 28
    w14 = Wall(5, 5, WallType.BRICK)
    shoot(w14, BulletType.CANNON, owner=-1)
    print('14 敌人炮弹打砖: hp =', w14.hp, '(期望 28)')

    # 15) 连续更新模拟: 鸡蛋从远处飞向砖墙, 命中即消失 (不再多帧追击)
    w15 = Wall(5, 5, WallType.BRICK)
    b15 = Bullet(200, 352, 0, BulletType.EGG, 1)
    frames = 0
    while not b15.dead and frames < 60:
        b15.update(16.666, [w15], None, MAP, [])
        frames += 1
    print('15 远距离飞行: frames =', frames, '| hp =', w15.hp,
          '(期望 <=20/36)')

    pygame.quit()
    print('ALL DONE')


if __name__ == '__main__':
    run()
