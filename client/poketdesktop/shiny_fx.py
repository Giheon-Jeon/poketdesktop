# -*- coding: utf-8 -*-
"""색이 다른(이로치) 야생이 나타날 때의 반짝임 (1.12.1).

**그 야생 도트의 몸 위에서** 네 갈래 별이 여기저기 차례로 반짝인다 - 두 차례, 합쳐서
1초 남짓. 별 자리는 도트가 그려진 칸(x, y, fw, fh) 안의 비율로 정해 두어서 몸집이
크든 작든 몸 위에 뜨고, 별 크기도 몸집에 맞춘다. 도트가 걸어가면 따라간다.
그동안은 표식이 금빛이고 ★ 가 붙는 것뿐이라, 표식을 읽기 전에는 색이 다른 개체인 줄
몰랐다. (처음에는 도트 바깥 둘레에 고리로 터지게 했는데, 도트와 따로 노는 것처럼
보였다 - 사용자 지적.)

바탕화면 위에 클릭이 통과하는 층(fx_layer)을 잠깐 열어 그리고 닫는다 - 배틀의 체력바와
같은 층이다. 층을 못 열면(클릭 통과가 안 되는 환경) 아무것도 안 그린다. 야생은 그대로
나와 있고 표식도 그대로다. 도트가 그사이 사라지면(잡혔다, 달아났다) 바로 걷는다.
"""
import time

from . import config
from .fx_layer import open_layer

FRAME_MS = 30
STAGGER_MS = 75          # 한 차례 안에서 별이 하나씩 뒤따르는 간격
GROW_MS = 140            # 별이 커지는 시간
FADE_MS = 260            # 다 커진 뒤 줄어들며 사라지는 시간
# 별 자리: 도트 칸 안의 (가로, 세로) 비율. 몸 위와 가장자리에 고루 - 같은 자리에 두 번 안 뜬다.
# (시작 ms, [(u, v, 크기 배수)])
ROUNDS = ((0, ((0.30, 0.22, 1.0), (0.72, 0.38, 0.8), (0.45, 0.62, 1.0),
               (0.18, 0.55, 0.7), (0.80, 0.78, 0.9))),
          (480, ((0.62, 0.12, 0.8), (0.35, 0.42, 0.9), (0.86, 0.52, 0.7),
                 (0.50, 0.88, 0.8), (0.14, 0.82, 0.7), (0.55, 0.40, 1.15))))
SIZE_OF = 0.30           # 가장 큰 별의 반지름 = 도트 짧은 변 x 이것
SIZE_MIN, SIZE_MAX = 4, 13
CORE = "#ffffff"
EDGE = "#ffe27a"


def plan():
    """[(시작 ms, u, v, 크기 배수)] - 별 하나하나가 언제 도트의 어디에서 반짝이나."""
    out = []
    for start, spots in ROUNDS:
        for i, (u, v, k) in enumerate(spots):
            out.append((start + i * STAGGER_MS, u, v, k))
    return out


def length_ms():
    return max(s for s, _u, _v, _k in plan()) + GROW_MS + FADE_MS


def star_size(fw, fh):
    """이 도트에서 가장 큰 별의 반지름 (px). 몸집에 맞추되 너무 작거나 크지 않게."""
    return max(SIZE_MIN, min(SIZE_MAX, min(fw, fh) * SIZE_OF))


def scale_at(dt):
    """시작하고 dt ms 뒤의 크기 비율 (0~1). 아직이거나 끝났으면 None."""
    if dt < 0 or dt > GROW_MS + FADE_MS:
        return None
    if dt < GROW_MS:
        return dt / float(GROW_MS)
    return 1.0 - (dt - GROW_MS) / float(FADE_MS)


def _sparkle(cv, x, y, r):
    """가운데가 잘록한 네 갈래 별."""
    k = r * 0.28
    pts = [x, y - r, x + k, y - k, x + r, y, x + k, y + k,
           x, y + r, x - k, y + k, x - r, y, x - k, y - k]
    return cv.create_polygon(pts, fill=CORE, outline=EDGE, width=1)


class Sparkle(object):
    """한 번 반짝이고 스스로 닫힌다. pet 은 x, y, fw, fh 를 가진 도트 (보통 WildPet)."""

    def __init__(self, root, area, pet, alive=None, on_done=None):
        self.root = root
        self.pet = pet
        self.alive = alive or (lambda: True)
        self.on_done = on_done
        self.stars = plan()
        self.end = length_ms()
        self.layer = None
        self.drawn = 0           # 그린 별 수 (검사가 본다)
        self.closed = False
        self.t0 = None
        try:
            self.layer = open_layer(root, area)
        except Exception as e:                              # noqa: BLE001
            config.log("이로치 반짝임 층을 못 열었습니다: %s" % e)
            self.layer = None

    def start(self):
        if self.layer is None:
            self.finish()
            return self
        self.t0 = time.time()
        self._frame()
        return self

    def _frame(self):
        if self.closed:
            return
        ms = (time.time() - self.t0) * 1000.0
        try:
            if ms >= self.end or not self.alive():
                return self.finish()
            cv = self.layer.cv
            cv.delete("all")
            p = self.pet
            ox, oy = self.layer.to_local(p.x, p.y)       # 도트 칸의 왼쪽 위 (걸어가면 따라간다)
            big = star_size(p.fw, p.fh)
            for start, u, v, k in self.stars:
                s = scale_at(ms - start)
                if s is None or s <= 0:
                    continue
                _sparkle(cv, ox + u * p.fw, oy + v * p.fh, 1.5 + big * k * s)
                self.drawn += 1
        except Exception as e:                              # noqa: BLE001
            config.log("이로치 반짝임 실패: %s" % e)
            return self.finish()
        self.root.after(FRAME_MS, self._frame)

    def finish(self):
        if self.closed:
            return
        self.closed = True
        if self.layer is not None:
            self.layer.destroy()
            self.layer = None
        if self.on_done:
            try:
                self.on_done()
            except Exception:                               # noqa: BLE001
                pass


def play(root, area, pet, alive=None, on_done=None):
    """pet 의 몸 위에서 한 번 반짝인다. 돌고 있는 Sparkle 을 돌려준다."""
    return Sparkle(root, area, pet, alive, on_done).start()
