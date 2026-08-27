# -*- coding: utf-8 -*-
"""
数学与工具函数
Math / Utility helpers
"""
import math
import random


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def lerp(a, b, t):
    return a + (b - a) * t


def dist(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


def angle_between(x1, y1, x2, y2):
    return math.degrees(math.atan2(y2 - y1, x2 - x1))


def normalize_angle(deg):
    while deg > 180:
        deg -= 360
    while deg < -180:
        deg += 360
    return deg


def angle_diff(target, current):
    return normalize_angle(target - current)


def rad(deg):
    return math.radians(deg)


def deg(rad_val):
    return math.degrees(rad_val)


def dir_from_angle(deg_angle):
    r = rad(deg_angle)
    return math.cos(r), math.sin(r)


def aabb_overlap(ax, ay, aw, ah, bx, by, bw, bh):
    return not (ax + aw < bx or ax > bx + bw or ay + ah < by or ay > by + bh)


def circle_rect_overlap(cx, cy, cr, rx, ry, rw, rh):
    closest_x = clamp(cx, rx, rx + rw)
    closest_y = clamp(cy, ry, ry + rh)
    return (cx - closest_x) ** 2 + (cy - closest_y) ** 2 <= cr * cr


def random_choice_weighted(items_weights):
    items, weights = zip(*items_weights)
    total = sum(weights)
    r = random.uniform(0, total)
    acc = 0
    for it, w in zip(items, weights):
        acc += w
        if r <= acc:
            return it
    return items[-1]
