# -*- coding: utf-8 -*-
"""듀얼 모니터 - 주 화면 왼쪽에 둔 모니터에서도 체력바 · 이름표가 보인다 (게시판 #268).

    python client/test_dual_monitor.py
    python client/run_as_windows.py client/test_dual_monitor.py

**창을 진짜로 띄운다** (이펙트 레이어는 Tk 창이다). 모니터는 흉내 낸다 - PLAT.virtual_screen 이 '주 화면 왼쪽에
1920 짜리 모니터가 하나 더 있다' 를 돌려주게 한다. 주 화면 왼쪽(위)에 둔 화면은 좌표가 음수다.

제보 (최새벽 · 재렬띠, 둘 다 메인 모니터가 오른쪽): 오른쪽 화면에서는 체력바 · '지금 던지세요' 가 뜨는데 왼쪽
화면으로 옮기면 안 뜬다. 이펙트 레이어가 자리를 max(0, …) 로 잡아서 주 화면 쪽으로 밀려났기 때문이다 - 왼쪽
화면의 포켓몬 위에 그린 것은 레이어 밖이었다. 실시간 배틀의 상대 이름표도 같은 레이어에 그려진다.

  1. 레이어가 왼쪽 화면까지 덮는다 (0 에서 자르지 않는다). 왼쪽 화면의 포켓몬 위 체력바 · 글씨가 캔버스 안에 그려진다.
  2. 모니터가 한 대면 예전과 같은 자리 · 크기다.
  3. 실시간 배틀 무대는 활동 영역이 있는 모니터의 작업 영역 안에서 자란다 (주 화면으로 끌려가지 않는다).
"""
import os
import sys
import tempfile

os.environ["POKET_HOME"] = tempfile.mkdtemp(prefix="poket-test-dual-")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import tkinter as tk                                        # noqa: E402

from poketdesktop import arena_layout as L                  # noqa: E402
from poketdesktop import fx_layer as FL                     # noqa: E402
from poketdesktop import platform_os as PLAT                # noqa: E402
from poketdesktop import ui_common as U                     # noqa: E402

OK = FAIL = 0
LEFT = (-1920, 0, 0, 1080)          # 주 화면 왼쪽의 모니터
MAIN = (0, 0, 1920, 1080)


def chk(name, cond, got=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s   %r" % (name, got))


def inside(cv, item, w, h):
    x1, y1, x2, y2 = cv.bbox(item)
    return 0 <= x1 and 0 <= y1 and x2 <= w and y2 <= h


def main():
    PLAT.before_tk()
    root = tk.Tk()
    root.withdraw()
    U.init_fonts(root)
    real = PLAT.virtual_screen
    try:
        print("=== 왼쪽 모니터 (주 화면 왼쪽, 좌표가 음수)")
        PLAT.virtual_screen = lambda w, h: (LEFT[0], 0, MAIN[2], 1080)
        chk("모니터 전부의 왼쪽 위는 (-1920, 0)", FL.screen_origin(root) == (-1920, 0), FL.screen_origin(root))
        area = (-1800, 400, -200, 1000)                     # 활동 영역이 왼쪽 화면에 있다
        layer = FL.FxLayer(root, area)
        root.update_idletasks()
        w, h = int(layer.cv.cget("width")), int(layer.cv.cget("height"))
        chk("레이어가 왼쪽 화면에서 시작한다 (0 으로 밀려나지 않는다)", layer.x == -1890 and layer.y == 310, (layer.x, layer.y))
        chk("  활동 영역을 넉넉히 덮는다", layer.x <= area[0] and layer.x + w >= area[2] and layer.y + h >= area[3],
            (layer.x, w, h))
        pet = (-1500, 700)                                  # 왼쪽 화면의 포켓몬 (가운데 x, 위 y)
        bar = FL.HpBar(layer)
        bar.draw(*pet)
        chk("왼쪽 화면 포켓몬의 체력바가 캔버스 안에 그려진다", bar.items and all(inside(layer.cv, i, w, h) for i in bar.items),
            [layer.cv.bbox(i) for i in bar.items])
        txt = FL.FloatText(layer, pet[0], pet[1] - 6, "지금 던지세요!", "#ffd447")
        chk("  '지금 던지세요!' 도 캔버스 안", txt.items and all(inside(layer.cv, i, w, h) for i in txt.items),
            [layer.cv.bbox(i) for i in txt.items])
        txt.stop()
        layer.destroy()

        print("\n=== 모니터 한 대 (예전과 같다)")
        PLAT.virtual_screen = lambda w, h: MAIN
        area = (1300, 600, 1900, 1040)
        layer = FL.FxLayer(root, area)
        w, h = int(layer.cv.cget("width")), int(layer.cv.cget("height"))
        chk("자리 · 크기가 예전 계산과 같다 (영역 + 90 씩)", (layer.x, layer.y, w, h) == (1210, 510, 780, 620),
            (layer.x, layer.y, w, h))
        layer.destroy()
        layer = FL.FxLayer(root, (40, 30, 600, 500))
        w, h = int(layer.cv.cget("width")), int(layer.cv.cget("height"))
        chk("화면 왼쪽 위 구석이면 화면 안에서 시작하고 오른쪽 아래는 그대로 덮는다",
            (layer.x, layer.y) == (0, 0) and (w, h) == (690, 590), (layer.x, layer.y, w, h))
        # 떠오르는 글씨는 도트 가운데에 맞춘다. 화면 끝에 붙은 도트 위의 긴 글씨(1.13.2 '볼을 던지기 전에
        # 쓰러뜨렸다', 게시판 #280)는 앞이나 뒤가 화면 밖으로 잘렸다 - 글꼴을 줄이지 않고 안쪽으로 민다.
        for sx, where in ((30, "왼쪽"), (layer.x + w - 30, "오른쪽")):
            t = FL.FloatText(layer, sx, 200, "배틀이 끝나서 볼을 던지지 않았다", "#ffd447")
            boxes = [layer.cv.bbox(i) for i in t.items]
            chk("화면 %s 끝 도트 위의 긴 글씨도 캔버스 안 (잘리지 않는다)" % where,
                all(inside(layer.cv, i, w, h) for i in t.items), boxes)
            t.stop()
        t = FL.FloatText(layer, 300, 200, "+120 exp", "#7bffa0")
        x1, _y1, x2, _y2 = layer.cv.bbox(t.items[1])
        chk("  가운데 도트 위 글씨는 예전처럼 도트 가운데", abs((x1 + x2) / 2.0 - 300) <= 2, (x1, x2))
        t.stop()
        layer.destroy()

        print("\n=== 왼쪽 모니터를 막 뺐을 때 (영역은 아직 옛 자리, 리뷰에서 찾음)")
        before = len([w for w in root.winfo_children() if isinstance(w, tk.Toplevel)])
        try:
            layer = FL.FxLayer(root, (-900, 600, -100, 1000))    # 모니터 전부의 밖
            ok, size = True, (int(layer.cv.cget("width")), int(layer.cv.cget("height")))
            layer.destroy()
        except Exception as e:                              # noqa: BLE001
            ok, size = False, e
        chk("영역이 화면 밖이어도 레이어가 터지지 않는다 (크기는 1 이상)", ok and min(size) >= 1, size)
        after = len([w for w in root.winfo_children() if isinstance(w, tk.Toplevel)])
        chk("  만들다 만 창이 남지 않는다", after == before, (before, after))

        print("\n=== 실시간 배틀 무대 (활동 영역이 있는 모니터의 작업 영역)")
        screens = [MAIN, LEFT]                              # 첫 번째가 주 화면
        works = [(0, 0, 1920, 1040), (-1920, 0, 0, 1040)]   # 작업표시줄을 뺀 자리
        area = (-900, 600, -100, 1000)
        work = L.work_for(area, screens, works)
        chk("왼쪽 화면의 활동 영역 -> 왼쪽 화면의 작업 영역", work == works[1], work)
        rect = L.stage_rect(area, work)
        chk("  무대가 왼쪽 화면 안에 선다 (주 화면 왼쪽 끝으로 끌려가지 않는다)",
            rect[0] >= -1920 and rect[2] <= 0 and rect[2] - rect[0] > 600, rect)
        old = L.stage_rect(area, works[0])
        chk("  (예전처럼 주 화면 것을 쓰면 주 화면 왼쪽 끝의 좁은 자리였다)", old[0] >= 0 and old[2] - old[0] < 300, old)
        chk("오른쪽(주) 화면이면 주 화면 것", L.work_for((1300, 600, 1900, 1000), screens, works) == works[0])
        chk("어느 화면에도 없으면 None (부르는 쪽이 주 화면 것을 쓴다)", L.work_for((5000, 0, 5100, 50), screens, works) is None)
    finally:
        PLAT.virtual_screen = real
        root.destroy()
    print("\n%d개 통과, %d개 실패" % (OK, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
