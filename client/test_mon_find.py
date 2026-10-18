# -*- coding: utf-8 -*-
"""가방·기술머신의 '누구에게' 목록 찾기·줄 세우기 검사 (1.13.1).

    python client/test_mon_find.py
    python client/run_as_windows.py client/test_mon_find.py

**창을 진짜로 띄운다.** 가방에서 도구를 쓸 포켓몬, 기술머신을 가르칠 포켓몬을 고르는 오른쪽 목록은
받은 순서 그대로였다 (건의). 못 박는 것:

  1. 찾기는 포켓몬 관리 창과 같은 규칙이다 - 별명 · 종 이름 · 도감 번호. 기술머신 목록은 이름과
     번호만 오는데도 별명을 지은 포켓몬이 종 이름으로 찾힌다.
  2. 가나다순 · 레벨순(높은 것부터) · 기본(받은 순서).
  3. 가방: 고른 포켓몬이 가려지면 보이는 것 중에서 다시 고른다. 못 쓰는 포켓몬은 안 고른다.
     하나도 안 맞으면 목록 자리에 안내가 뜨고 아무도 안 고른다.
  4. 기술머신: 줄은 다시 만들지 않고 순서만 바꿔 담는다. 가려진 포켓몬은 고름이 풀린다.
  5. 도구 · 기술머신을 바꿔도 찾는 말과 순서는 그대로다.
  6. 한 줄이 칸 안에 다 들어간다 (잘리지 않는다).
"""
import json
import os
import sys
import tempfile

os.environ["POKET_HOME"] = tempfile.mkdtemp(prefix="poket-test-monfind-")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import tkinter as tk                                        # noqa: E402

from common import pokelogic as P                           # noqa: E402
from poketdesktop import box_filter                         # noqa: E402
from poketdesktop import platform_os as PLAT                # noqa: E402
from poketdesktop import sprite_cache                       # noqa: E402
from poketdesktop import ui_bag, ui_tms                     # noqa: E402
from poketdesktop import ui_common as U                     # noqa: E402
import smoke_box_filter as SB                               # noqa: E402
import smoke_tms as ST                                      # noqa: E402
import test_big_lists as BL                                 # noqa: E402

OK = FAIL = 0
DATA = os.path.join(ROOT, "server", "data")

# (id, 도감 번호, 레벨, 별명)
MONS = [(1, 25, 30, "번개"), (2, 4, 50, None), (3, 1, 10, None),
        (4, 7, 100, None), (5, 133, 70, None), (6, 150, 20, None)]
BY_NAME = ["꼬부기", "뮤츠", "번개", "이브이", "이상해씨", "파이리"]
BY_LEVEL = [4, 5, 2, 1, 6, 3]


def chk(name, cond, got=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s   %r" % (name, got))


def ids(rows):
    return [m["id"] for m in rows]


def names(rows):
    return [box_filter.name_of(m) for m in rows]


def inside(w, box):
    """w 가 box 안에 다 들어가고 글자가 안 잘렸나."""
    x = w.winfo_rootx() - box.winfo_rootx()
    return (x >= 0 and x + w.winfo_width() <= box.winfo_width() + 1
            and w.winfo_width() >= w.winfo_reqwidth() - 1
            and w.winfo_height() >= w.winfo_reqheight() - 1)


def seg_ok(bar):
    cells = list(bar.seg.cells.values())
    return all(c.winfo_width() >= c.winfo_reqwidth() - 1 for c in cells) and inside(bar.seg.frame, bar.frame)


def pure(dex):
    print("=== 찾기 · 줄 세우기 (box_filter.pick_view)")
    mons = [dict(SB.mon(dex, n, i, nickname=nick), level=lv) for i, n, lv, nick in MONS]
    v = box_filter.pick_view
    chk("기본: 받은 순서 그대로", ids(v(mons, dex)) == [1, 2, 3, 4, 5, 6], ids(v(mons, dex)))
    chk("가나다순", names(v(mons, dex, "", "name")) == BY_NAME, names(v(mons, dex, "", "name")))
    chk("레벨순 (높은 것부터)", ids(v(mons, dex, "", "level")) == BY_LEVEL, ids(v(mons, dex, "", "level")))
    chk("별명으로 찾는다", ids(v(mons, dex, "번개")) == [1])
    chk("별명을 지었어도 종 이름으로 찾힌다", ids(v(mons, dex, "피카")) == [1])
    chk("도감 번호로 찾는다", ids(v(mons, dex, "133")) == [5])
    chk("빈칸 · 앞뒤 공백은 무시", ids(v(mons, dex, " 이 상 ")) == [3])
    chk("찾고 나서 줄 세운다", ids(v(mons, dex, "이", "level")) == [5, 2, 3], ids(v(mons, dex, "이", "level")))
    chk("받은 목록은 그대로", ids(mons) == [1, 2, 3, 4, 5, 6])

    rows = [{"id": 10 + i, "name": nick or dex.get(n)["kr"], "num": n, "level": lv}
            for i, n, lv, nick in MONS]
    chk("기술머신 줄(이름 · 번호만)도 종 이름으로 찾힌다", ids(v(rows, dex, "피카")) == [11], ids(v(rows, dex, "피카")))
    chk("  가나다순은 적힌 이름으로", names(v(rows, dex, "", "name")) == BY_NAME, names(v(rows, dex, "", "name")))
    chk("  레벨순", ids(v(rows, dex, "", "level")) == [10 + i for i in BY_LEVEL])


def bag(root, dex):
    print("\n=== 가방")
    mons = []
    for i, n, lv, nick in MONS:
        m = SB.mon(dex, n, i, on=(i <= 2), nickname=nick, held=("ORANBERRY" if i == 4 else None))
        m["level"] = lv
        mons.append(m)
    raw = json.load(open(os.path.join(DATA, "items.json"), encoding="utf-8"))["items"]
    items = [dict(i) for i in (raw.values() if isinstance(raw, dict) else raw)
             if i["id"] in ("RARECANDY", "ORANBERRY")]
    api = BL.Api(mons, items)
    app = BL.App(root, api, dex)
    w = ui_bag.BagWindow(root, app)
    w.win.winfo_toplevel().geometry("1000x664+40+40")
    w.win.winfo_toplevel().deiconify()
    BL.wait(root, lambda: w.mons and w._wait is None)
    w.pick_item("RARECANDY")
    BL.settle(root, 0.4)
    bar = w.find
    chk("찾기 칸과 [기본 | 가나다순 | 레벨순] 이 있다",
        [c.cget("text") for c in bar.seg.cells.values()] == ["기본", "가나다순", "레벨순"])
    chk("  처음엔 받은 순서 · 다 보인다", ids(w._view) == [1, 2, 3, 4, 5, 6]
        and [p for p, _r in w.shown_mons()] == [1, 2, 3, 4, 5, 6], ids(w._view))
    chk("  한 줄이 칸 안에 다 들어간다 (찾기 칸 · 단추)", inside(bar.box, bar.frame) and seg_ok(bar)
        and bar.box.winfo_rootx() + bar.box.winfo_width() <= bar.seg.frame.winfo_rootx(),
        (bar.frame.winfo_width(), bar.box.winfo_width(), bar.seg.frame.winfo_width()))
    chk("  목록은 여섯 줄이 다 보일 만큼 남는다", w.mon_vl.canvas.winfo_height() >= 6 * ui_bag.MON_H,
        w.mon_vl.canvas.winfo_height())
    chk("  처음 골라 둔 것은 맨 위", w.mon_id == 1, w.mon_id)

    bar.pick_sort("name")
    BL.settle(root, 0.2)
    chk("가나다순으로 줄 선다", names(w._view) == BY_NAME
        and [r.mon["id"] for _p, r in w.shown_mons()] == ids(w._view), names(w._view))
    chk("  보이는 줄의 이름도 그 순서", [r.name.cget("text") for _p, r in w.shown_mons()] == BY_NAME,
        [r.name.cget("text") for _p, r in w.shown_mons()])
    chk("  고른 포켓몬은 그대로 (보이니까)", w.mon_id == 1, w.mon_id)
    bar.pick_sort("level")
    BL.settle(root, 0.2)
    chk("레벨순 (높은 것부터)", ids(w._view) == BY_LEVEL, ids(w._view))
    chk("  누른 칸이 칠해진다", bar.seg.current == "level")

    w.pick_mon(2)
    bar.q.set("이")
    BL.settle(root, 0.2)
    chk("찾기: 이름에 '이' 가 든 것만, 레벨순 그대로", ids(w._view) == [5, 2, 3], ids(w._view))
    chk("  '3마리' 라고 적는다", bar.count.cget("text") == "3마리", bar.count.cget("text"))
    chk("  고른 포켓몬이 보이면 그대로", w.mon_id == 2, w.mon_id)
    bar.q.set("번개")
    BL.settle(root, 0.2)
    chk("고른 포켓몬이 가려지면 보이는 것 중에서 다시 고른다", ids(w._view) == [1] and w.mon_id == 1, w.mon_id)
    w.pick_item("ORANBERRY")
    bar.q.set("꼬부기")                    # 오랭열매를 이미 지녔다 - 못 쓴다
    BL.settle(root, 0.2)
    chk("보이는 것이 다 못 쓰는 포켓몬이면 아무도 안 고른다", ids(w._view) == [4] and w.mon_id is None, w.mon_id)
    bar.q.set("없는포켓몬")
    BL.settle(root, 0.2)
    chk("하나도 안 맞으면 목록 자리에 안내", not w._mon_list_on and "없는포켓몬" in w.mon_note.cget("text")
        and w.mon_id is None and w.current_mon() is None, w.mon_note.cget("text"))
    chk("  '0마리'", bar.count.cget("text") == "0마리", bar.count.cget("text"))
    bar.q.set("피카")
    BL.settle(root, 0.2)
    chk("다시 맞으면 목록이 돌아오고 골라 준다", w._mon_list_on and ids(w._view) == [1] and w.mon_id == 1)
    w.pick_item("RARECANDY")
    BL.settle(root, 0.2)
    chk("다른 도구를 골라도 찾는 말과 순서는 그대로", bar.q.get() == "피카" and bar.sort == "level"
        and ids(w._view) == [1], (bar.q.get(), ids(w._view)))
    bar.q.set("")
    BL.settle(root, 0.2)
    chk("지우면 다 보인다 (레벨순)", ids(w._view) == BY_LEVEL and bar.count.cget("text") == "", ids(w._view))
    bar.pick_sort("")
    BL.settle(root, 0.2)
    chk("기본으로 되돌린다", ids(w._view) == [1, 2, 3, 4, 5, 6], ids(w._view))
    w.close()
    try:
        w.win.winfo_toplevel().destroy()
    except tk.TclError:
        pass


def tms(root, dex):
    print("\n=== 기술머신")
    tm = ST.load_tms()
    have = [t["no"] for t in tm if t["have"]]
    learners = [{"id": 10 + i, "name": nick or dex.get(n)["kr"], "num": n, "level": lv, "shiny": False,
                 "moves": ["TACKLE"], "known": i == 4} for i, n, lv, nick in MONS]
    api = ST.FakeApi(tm, learners)
    app = ST.FakeApp(root, api)
    app.dex = dex
    win = ui_tms.TmWindow(root, app)
    win.win.geometry("1000x664+40+40")
    BL.wait(root, lambda: len(win.rows) > 0 and win._wait is None)
    win.pick(have[0])
    BL.wait(root, lambda: len(win.mon_rows) == len(learners))
    BL.settle(root, 0.3)

    def packed():
        by = dict((str(v[0]), i) for i, v in win.mon_rows.items())
        return [by[str(s)] for s in win.mon_inner.pack_slaves() if str(s) in by]

    bar = win.find
    chk("처음엔 받은 순서", packed() == [11, 12, 13, 14, 15, 16], packed())
    chk("  한 줄이 칸 안에 다 들어간다", inside(bar.box, bar.frame) and seg_ok(bar)
        and bar.box.winfo_rootx() + bar.box.winfo_width() <= bar.seg.frame.winfo_rootx())
    frames = dict((i, v[0]) for i, v in win.mon_rows.items())
    bar.pick_sort("name")
    BL.settle(root, 0.2)
    chk("가나다순", [win.mon_rows[i][2].cget("text").split(" Lv.")[0] for i in packed()] == BY_NAME, packed())
    bar.pick_sort("level")
    BL.settle(root, 0.2)
    chk("레벨순", packed() == [10 + i for i in BY_LEVEL], packed())
    chk("  줄은 다시 만들지 않는다 (순서만 바꿔 담는다)",
        all(win.mon_rows[i][0] is f for i, f in frames.items()) and len(win.mon_rows) == 6)

    win.pick_mon(12)
    bar.q.set("이")
    BL.settle(root, 0.2)
    chk("찾기: '이' 가 든 것만, 레벨순", packed() == [15, 12, 13], packed())
    chk("  보이는 포켓몬을 고른 것은 그대로", win.mon_id == 12, win.mon_id)
    bar.q.set("피카")
    BL.settle(root, 0.2)
    chk("별명 '번개' 도 종 이름(피카츄)으로 찾힌다", packed() == [11], packed())
    chk("  가려진 포켓몬은 고름이 풀린다 (안 보이는 포켓몬에게 가르치지 않게)", win.mon_id is None
        and win.mon_rows[12][0].cget("bg") == U.BG2, win.mon_id)
    bar.q.set("없는포켓몬")
    BL.settle(root, 0.2)
    chk("하나도 안 맞으면 안내", packed() == [] and win._mon_none is not None
        and "없는포켓몬" in win._mon_none.cget("text"))
    bar.q.set("파이")
    BL.settle(root, 0.2)
    chk("다시 맞으면 안내가 걷힌다", packed() == [12] and win._mon_none is None, packed())
    api.gate.clear()
    win.pick(have[1])
    BL.settle(root, 0.1)
    bar.q.set("파이리")                     # 묻는 동안 쳐도 '불러오는 중' 을 걷지 않는다
    BL.settle(root, 0.1)
    waiting = [c for c in win.mon_inner.winfo_children()
               if isinstance(c, tk.Label) and "불러오는" in str(c.cget("text"))]
    chk("묻는 동안 쳐도 '불러오는 중' 은 그대로", len(waiting) == 1 and waiting[0].winfo_manager() == "pack")
    api.gate.set()
    BL.wait(root, lambda: len(win.mon_rows) == 1)
    BL.settle(root, 0.2)
    chk("다른 기술머신에서도 찾는 말 · 순서는 그대로 (안 맞는 줄은 만들지도 않는다)",
        packed() == [12] and bar.sort == "level" and len(win.mon_rows) == 1, (packed(), len(win.mon_rows)))
    bar.q.set("")
    BL.settle(root, 0.3)
    chk("지우면 다 담긴다 (레벨순)", packed() == [10 + i for i in BY_LEVEL] and len(win.mon_rows) == 6, packed())
    win.close()


def main():
    with open(os.path.join(DATA, "pokedex.json"), encoding="utf-8") as f:
        dex = P.Pokedex(json.load(f))
    pure(dex)
    PLAT.before_tk()
    root = tk.Tk()
    root.withdraw()
    U.init_fonts(root)
    U.apply_theme(root)
    errors = []

    def on_err(exc, val, tb):
        import traceback
        errors.append("".join(traceback.format_exception(exc, val, tb))[-600:])
    root.report_callback_exception = on_err
    real = sprite_cache.ensure
    sprite_cache.ensure = lambda api, num, shiny=False: None      # 도트 없이 (네트워크를 안 탄다)
    try:
        bag(root, dex)
        tms(root, dex)
    finally:
        sprite_cache.ensure = real
    chk("콜백 예외가 없다", not errors, errors[:2])
    try:
        root.destroy()
    except tk.TclError:
        pass
    print("\n%d개 통과, %d개 실패" % (OK, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
