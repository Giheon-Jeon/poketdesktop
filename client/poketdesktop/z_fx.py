# -*- coding: utf-8 -*-
"""배틀 창의 Z파워 연출 (시즌 4).

본가의 Z기술: 트레이너와 포켓몬이 Z파워를 두르고(기운이 아래에서 위로 솟는다) 큰 기술이
나간다. 여기서는 기술 연출 앞에 붙는 짧은 예고다 - 기술 자체의 연출은 그 뒤의 "move" 사건이
지금까지처럼 그린다.

  1. 솟는다    타입 색 기운의 줄기가 발밑에서 위로 솟고, 몸 둘레에 고리가 선다
  2. 새긴다    머리 위에 'Z' 가 커지며 박힌다
  3. 퍼진다    고리가 한 번 퍼지고 걷힌다

시간은 창의 later 로 흘린다 (ui_mega.MegaFx 와 같은 약속).
"""
import math
import random
import tkinter as tk

from . import ui_common as U

RISE_STEPS = 12
RISE_MS = 38
MARK_STEPS = 6
MARK_MS = 45
SPREAD_STEPS = 6
SPREAD_MS = 42
GOLD = "#ffd23c"


def _mix(color, other, t):
    """color 를 other 쪽으로 t 만큼 섞은 색."""
    try:
        a = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
        b = [int(other[i:i + 2], 16) for i in (1, 3, 5)]
    except (TypeError, ValueError):
        return color
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class ZFx(object):
    """캔버스 위의 Z파워 연출 한 번.

        fx = ZFx(cv, (x, y), later, color, on_done=...)
        fx.play()

    창을 닫을 때는 stop().
    """

    def __init__(self, cv, center, later, color=None, on_done=None, size=None):
        self.cv = cv
        self.cx, self.cy = center
        self.later = later
        self.color = color or GOLD
        self.lite = _mix(self.color, "#ffffff", 0.55)
        self.on_done = on_done
        self.size = float(size or U.h(64))
        self.items = []
        self.dead = False

    def _add(self, item):
        self.items.append(item)
        return item

    def _kill(self, item):
        try:
            self.cv.delete(item)
        except tk.TclError:
            pass
        if item in self.items:
            self.items.remove(item)

    def _ok(self):
        if self.dead:
            return False
        try:
            return bool(self.cv.winfo_exists())
        except tk.TclError:
            return False

    def play(self):
        try:
            streaks = []
            for k in range(10):
                x = self.cx + (k - 4.5) * self.size * 0.26 + random.uniform(-3, 3)
                it = self._add(self.cv.create_line(x, self.cy, x, self.cy,
                                                   fill=GOLD if k % 2 else self.lite,
                                                   width=max(2, int(U.h(3))), capstyle="round"))
                streaks.append((it, x, random.uniform(0.6, 1.0), random.randint(0, 3)))
            ring = self._add(self.cv.create_oval(0, 0, 0, 0, outline=self.color, width=3))
            self._rise(0, streaks, ring)
        except tk.TclError:
            self._finish()
        return self

    # ---- 1. 솟는다 ----
    def _rise(self, i, streaks, ring):
        if not self._ok():
            return self._finish()
        if i >= RISE_STEPS:
            for it, _x, _s, _d in streaks:
                self._kill(it)
            return self._mark(0, ring)
        try:
            base = self.cy + self.size * 0.9
            for it, x, speed, delay in streaks:
                t = max(0.0, (i - delay) / float(RISE_STEPS - 3))
                top = base - self.size * 2.2 * min(1.0, t * speed * 1.4)
                tail = base - self.size * 2.2 * max(0.0, min(1.0, t * speed * 1.4) - 0.35)
                self.cv.coords(it, x, tail, x, top)
                self.cv.tag_raise(it)
            rr = self.size * (0.55 + 0.04 * math.sin(i * 1.3))
            self.cv.coords(ring, self.cx - rr * 1.25, base - rr * 0.32, self.cx + rr * 1.25, base + rr * 0.32)
            self.cv.itemconfigure(ring, outline=GOLD if i % 2 else self.color)
            self.cv.tag_raise(ring)
        except tk.TclError:
            return self._finish()
        self.later(RISE_MS, lambda: self._rise(i + 1, streaks, ring))

    # ---- 2. 새긴다 ----
    def _mark(self, i, ring, mark=None):
        if not self._ok():
            return self._finish()
        try:
            y = self.cy - self.size * 0.95
            if mark is None:
                shadow = self._add(self.cv.create_text(self.cx + 2, y + 2, text="Z", fill="#1a1205",
                                                       font=(U.FAMILY, 8, "bold")))
                face = self._add(self.cv.create_text(self.cx, y, text="Z", fill=GOLD,
                                                     font=(U.FAMILY, 8, "bold")))
                mark = (shadow, face)
            # 커졌다가 살짝 줄며 자리 잡는다
            scale = (0.5, 0.9, 1.3, 1.55, 1.4, 1.3, 1.3)[min(i, 6)]
            px = max(8, int(self.size * 0.62 * scale))
            for it in mark:
                self.cv.itemconfigure(it, font=(U.FAMILY, -px, "bold"))
                self.cv.tag_raise(it)
            self.cv.itemconfigure(mark[1], fill="#ffffff" if i in (2, 3) else GOLD)
        except tk.TclError:
            return self._finish()
        if i >= MARK_STEPS:
            return self.later(120, lambda: self._spread(0, ring, mark))
        self.later(MARK_MS, lambda: self._mark(i + 1, ring, mark))

    # ---- 3. 퍼진다 ----
    def _spread(self, i, ring, mark):
        if not self._ok():
            return self._finish()
        if i >= SPREAD_STEPS:
            return self._finish()
        try:
            base = self.cy + self.size * 0.9
            rr = self.size * (0.6 + 0.3 * i)
            self.cv.coords(ring, self.cx - rr * 1.25, base - rr * 0.32, self.cx + rr * 1.25, base + rr * 0.32)
            self.cv.itemconfigure(ring, width=max(1, 4 - i // 2))
            if i >= SPREAD_STEPS - 2:
                for it in mark:
                    self.cv.itemconfigure(it, fill=_mix(GOLD, "#30384e", 0.5))
        except tk.TclError:
            return self._finish()
        self.later(SPREAD_MS, lambda: self._spread(i + 1, ring, mark))

    # ---- 끝 ----
    def _finish(self):
        if self.dead:
            return
        self.dead = True
        for it in list(self.items):
            try:
                self.cv.delete(it)
            except tk.TclError:
                pass
        self.items = []
        cb, self.on_done = self.on_done, None
        if cb:
            try:
                cb()
            except Exception:                               # noqa: BLE001
                pass

    def stop(self):
        """창을 닫을 때. 다음으로 넘기지 않고 조용히 치운다."""
        self.on_done = None
        self._finish()
