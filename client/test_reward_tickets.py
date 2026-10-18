# -*- coding: utf-8 -*-
"""랭크 시즌 보상 도구 화면 검사 (1.13.1): 기술머신 뽑기권 · 랭킹 탭 보상 표.

    python client/test_reward_tickets.py
    python client/run_as_windows.py client/test_reward_tickets.py

**창을 진짜로 띄운다.** 못 박는 것:

  1. 가방: 랜덤 기술머신 뽑기권은 포켓몬을 안 고르고 바로 쓴다. 쓰고 나면 [기술머신] 의 노란 점을 새로 센다.
  2. 타입 확정 뽑기권은 쓰기 전에 타입을 묻는다 - 다 모은 타입은 빼고, 아직 없는 수를 적는다.
     창을 닫으면 안 쓴다. 옛 서버(남은 수 없음)면 타입만 늘어놓는다.
  3. 거절되면(그사이 그 타입을 다 모았다) 가방을 다시 읽어 '아직 없는 것' 수를 맞춘다.
  4. 랭킹 탭의 보상 표에 도구와 '관장 등록'(도구가 아니다 - 구글폼으로 따로 신청)이 실리고, 길어진 챔피언 줄은
     글씨를 줄이지 않고 줄을 바꿔 카드 안에 들어간다.
"""
import json
import os
import sys
import tempfile

os.environ["POKET_HOME"] = tempfile.mkdtemp(prefix="poket-test-rewardtickets-")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import tkinter as tk                                        # noqa: E402

from common import pokelogic as P                           # noqa: E402
from poketdesktop import platform_os as PLAT                # noqa: E402
from poketdesktop import sprite_cache                       # noqa: E402
from poketdesktop import ui_bag, ui_box, ui_rank            # noqa: E402
from poketdesktop import ui_common as U                     # noqa: E402
import smoke_box_filter as SB                               # noqa: E402
import smoke_season as SS                                   # noqa: E402
import test_big_lists as BL                                 # noqa: E402

OK = FAIL = 0
DATA = os.path.join(ROOT, "server", "data")
LEFT = {"FIRE": 3, "WATER": 1, "NORMAL": 12}               # 나머지 타입은 다 모았다


def chk(name, cond, got=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s   %r" % (name, got))


class Api(BL.Api):
    def __init__(self, mons, items, left):
        BL.Api.__init__(self, mons, items)
        self.left = left
        self.uses = []

    def shop(self):
        out = BL.Api.shop(self)
        if self.left is not None:
            out["tmLeft"] = dict(self.left)
        return out

    def use_item(self, item, pid, stat="", hour=None, form="", tm_type=""):
        self.uses.append((item, pid, tm_type))
        if getattr(self, "refuse", None):
            from poketdesktop.api import ApiError
            self.left.pop(tm_type, None)          # 서버에서는 그사이 다 모았다
            raise ApiError(self.refuse, 400)
        self.bag[item] = self.bag.get(item, 0) - 1
        return {"ok": True, "won": True, "tmNew": 3, "tm": {"no": 42, "type": tm_type or "ICE"},
                "message": "기술머신042 냉동빔을(를) 얻었다!"}


class App(BL.App):
    def __init__(self, root, api, dex):
        BL.App.__init__(self, root, api, dex)
        self.noted = []

    def note_tms(self, n, reload=True):
        self.noted.append(n)


def bag(root, dex, left):
    raw = json.load(open(os.path.join(DATA, "items.json"), encoding="utf-8"))["items"]
    items = [dict(i) for i in (raw.values() if isinstance(raw, dict) else raw)
             if i["id"] in ("RANKTICKETTM", "RANKTICKETTMTYPE")]
    mons = [SB.mon(dex, 25, 1), SB.mon(dex, 4, 2)]
    api = Api(mons, items, left)
    app = App(root, api, dex)
    w = ui_bag.BagWindow(root, app)
    top = w.win.winfo_toplevel()
    top.geometry("1000x664+40+40")
    top.deiconify()
    BL.wait(root, lambda: w.mons and w._wait is None)
    return w, api, app


def run_bag(root, dex):
    print("=== 가방: 랜덤 기술머신 뽑기권")
    w, api, app = bag(root, dex, LEFT)
    w.pick_item("RANKTICKETTM")
    BL.settle(root, 0.3)
    chk("포켓몬 목록 대신 설명이 뜬다", not w._mon_list_on and "아직 없는 기술머신" in w.mon_note.cget("text"),
        w.mon_note.cget("text"))
    chk("  쓰기 단추가 켜져 있다", w.use_btn.enabled and w.use_btn.label.cget("text") == "랜덤 기술머신 뽑기권 쓰기",
        w.use_btn.label.cget("text"))
    w.do_use()
    BL.wait(root, lambda: api.uses and w._wait is None)
    BL.settle(root, 0.3)
    chk("포켓몬 없이 쓴다", api.uses == [("RANKTICKETTM", 0, "")], api.uses)
    chk("  얻은 기술머신을 알린다", "냉동빔" in w.status._label.cget("text"), w.status._label.cget("text"))
    chk("  [기술머신] 의 노란 점을 새로 센다", app.noted == [3], app.noted)

    print("\n=== 타입 확정 뽑기권")
    asked = []
    real = ui_box.ask_choice

    def fake(parent, title, message, options, answer="FIRE"):
        asked.append((title, message, list(options)))
        return answer
    ui_box.ask_choice = fake
    try:
        w.pick_item("RANKTICKETTMTYPE")
        BL.settle(root, 0.2)
        chk("설명에 '쓸 때 타입을 고르면'", "타입을 고르면" in w.mon_note.cget("text"), w.mon_note.cget("text"))
        w.do_use()
        BL.wait(root, lambda: len(api.uses) == 2 and w._wait is None)
        BL.settle(root, 0.3)
        opts = asked[-1][2] if asked else []
        chk("쓰기 전에 타입을 묻는다", asked and asked[-1][0] == "타입 확정 기술머신 뽑기권")
        chk("  다 모은 타입은 빼고 타입 순서대로", [k for k, _l, _s in opts] == ["NORMAL", "FIRE", "WATER"],
            [k for k, _l, _s in opts])
        chk("  한글 이름과 아직 없는 수", [(lb, s) for _k, lb, s in opts]
            == [("노말", "아직 없는 것 12개"), ("불꽃", "아직 없는 것 3개"), ("물", "아직 없는 것 1개")], opts)
        chk("고른 타입으로 쓴다", api.uses[-1] == ("RANKTICKETTMTYPE", 0, "FIRE"), api.uses)
        n = len(api.uses)
        ui_box.ask_choice = lambda *a, **k: None
        api.bag["RANKTICKETTMTYPE"] = 1
        w.reload()
        BL.wait(root, lambda: w._wait is None)
        w.pick_item("RANKTICKETTMTYPE")
        w.do_use()
        BL.settle(root, 0.3)
        chk("창을 닫으면 안 쓴다", len(api.uses) == n, api.uses)

        ui_box.ask_choice = fake
        api.refuse = "불꽃 타입 기술머신은 이미 다 모았습니다. 다른 타입을 골라 주세요."
        api.bag["RANKTICKETTMTYPE"] = 1
        w.do_use()
        BL.wait(root, lambda: w._wait is None and len(api.uses) == n + 1)
        BL.settle(root, 0.4)
        chk("거절되면 이유를 보여 주고", "다 모았습니다" in w.status._label.cget("text"), w.status._label.cget("text"))
        chk("  가방을 다시 읽어 남은 수를 맞춘다 (다 모은 불꽃이 빠진다)", "FIRE" not in (w.tm_left or {})
            and (w.tm_left or {}).get("WATER") == 1, w.tm_left)
        api.refuse = None
    finally:
        ui_box.ask_choice = real
    w.close()

    w, api, app = bag(root, dex, None)
    asked.clear()
    ui_box.ask_choice = fake
    try:
        w.pick_item("RANKTICKETTMTYPE")
        w.do_use()
        BL.wait(root, lambda: api.uses and w._wait is None)
        opts = asked[-1][2] if asked else []
        chk("옛 서버(남은 수 없음): 열여덟 타입을 다 늘어놓는다 (스텔라 빼고)", len(opts) == 18
            and "STELLAR" not in [k for k, _l, _s in opts] and all(s is None for _k, _l, s in opts), len(opts))
    finally:
        ui_box.ask_choice = real
    w.close()

    w, api, app = bag(root, dex, {})
    w.pick_item("RANKTICKETTMTYPE")
    asked.clear()
    ui_box.ask_choice = fake
    try:
        w.do_use()
        BL.settle(root, 0.2)
        chk("다 모았으면 묻지도 쓰지도 않고 알린다", not asked and not api.uses
            and "다 모아서" in w.status._label.cget("text"), w.status._label.cget("text"))
    finally:
        ui_box.ask_choice = real

    w.close()


def run_rank(root):
    print("\n=== 랭킹 탭의 보상 표")
    rules = dict(SS.RULES)
    rules["rewards"] = [
        {"tier": "champion", "tierKr": "챔피언", "title": "시즌 4 챔피언", "frame": "금빛 명패",
         "frameColor": "#ffc043", "shiny": 1, "egg": "전설의 포켓몬 알",
         "items": [{"id": "RANKTICKETTMTYPE", "kr": "타입 확정 기술머신 뽑기권", "count": 1}],
         "perks": ["관장 등록"]},
        {"tier": "elite", "tierKr": "사천왕", "title": "시즌 4 사천왕", "frame": "은빛 명패",
         "frameColor": "#c9d1e6", "shiny": 1, "egg": "환상의 포켓몬 알",
         "items": [{"id": "RANKTICKETTM", "kr": "랜덤 기술머신 뽑기권", "count": 1}], "perks": []},
        {"tier": "super", "tierKr": "슈퍼볼", "title": "시즌 4 슈퍼볼", "frame": None,
         "frameColor": None, "shiny": 0, "egg": None, "items": [], "perks": []},
    ]
    real = SS.RULES
    SS.RULES = rules
    try:
        app = SS.FakeApp(root)
        rw = ui_rank.RankWindow(app)
        SS.pump(root, lambda: not rw.busy and "명예의 전당" in SS.texts(rw.win))
        BL.settle(root, 0.3)
        t = SS.texts(rw.win)
        chk("챔피언 줄에 타입 확정 뽑기권 · 관장 등록",
            "금빛 명패 · 이로치사탕 1개 · 타입 확정 기술머신 뽑기권 · 관장 등록" in t, t[-600:])
        chk("사천왕 줄에 랜덤 뽑기권", "은빛 명패 · 이로치사탕 1개 · 랜덤 기술머신 뽑기권" in t)
        chk("도구가 없는 줄은 그대로", "칭호 '시즌 4 슈퍼볼'\n" in t or t.endswith("칭호 '시즌 4 슈퍼볼'"))
        lab = [w for w in SS.walk_all(rw.win) if isinstance(w, tk.Label) and "관장 등록" in str(w.cget("text"))]
        card = lab[0].master
        while card is not None and not int(card.cget("highlightthickness") or 0):
            card = card.master
        right = lab[0].winfo_rootx() + lab[0].winfo_width()
        edge = card.winfo_rootx() + card.winfo_width()
        print("  챔피언 줄 %dx%d (필요 %dx%d) · 오른쪽 끝 %d / 카드 %d · 글꼴 %s"
              % (lab[0].winfo_width(), lab[0].winfo_height(), lab[0].winfo_reqwidth(),
                 lab[0].winfo_reqheight(), right, edge, lab[0].cget("font")))
        chk("  챔피언 줄이 카드 안에 다 들어간다", right <= edge - 1, (right, edge))
        chk("  눌리지 않는다 (줄을 바꿨으면 높이도 그만큼)", lab[0].winfo_height() >= lab[0].winfo_reqheight()
            and lab[0].winfo_width() >= lab[0].winfo_reqwidth())
        same = tk.Label(rw.win, font=U.FONT_XS)
        chk("  글씨는 줄이지 않는다 (다른 작은 글씨와 같은 크기)", str(lab[0].cget("font")) == str(same.cget("font")),
            (lab[0].cget("font"), same.cget("font")))
        same.destroy()
        rw.close()
    finally:
        SS.RULES = real


def main():
    with open(os.path.join(DATA, "pokedex.json"), encoding="utf-8") as f:
        dex = P.Pokedex(json.load(f))
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
    sprite_cache.ensure = lambda api, num, shiny=False: None
    try:
        run_bag(root, dex)
        run_rank(root)
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
