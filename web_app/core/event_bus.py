# -*- coding: utf-8 -*-
"""
事件总线
Event Bus (Publisher/Subscriber)
"""
from collections import defaultdict


class EventBus:
    def __init__(self):
        self.listeners = defaultdict(list)

    def on(self, event_type, callback):
        self.listeners[event_type].append(callback)

    def off(self, event_type, callback):
        if callback in self.listeners[event_type]:
            self.listeners[event_type].remove(callback)

    def emit(self, event_type, **payload):
        for cb in list(self.listeners[event_type]):
            try:
                cb(**payload)
            except Exception as e:
                print(f"[EventBus] 回调异常 {event_type}: {e}")
