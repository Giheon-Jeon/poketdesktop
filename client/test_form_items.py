# -*- coding: utf-8 -*-
"""가방의 폼 도구 (1.13). 진짜 Tk 로 확인한다.

    python client/test_form_items.py

사용자 요청 "포켓몬들의 폼체인지까지" (2026-10-17). 서버(server/test_forms.py)가 모습을 바꾸고,
여기서는 가방이 그것을 제대로 묻고 보내는지를 본다.

  1. 설명: 누가 어떤 모습이 되는지, 쓰면 어떻게 되는지 (켜고 끄기·고르기·꽃꿀).
  2. 대상: 통하는 종만 밝히고 나머지는 막는다. 지금 모습을 줄 끝에 적는다.
  3. 쓰기 전에 묻기: 로토무카탈로그는 모습을 고른다(지금 모습은 빼고 '원래 모습' 을 넣는다).
     그만두면 안 보낸다. 합체 도구는 넣지 않았다 (2026-10-17 사용자 결정).
  4. 서버로 form 을 같이 보낸다. 옛 api(form 을 모르는 것)면 직접 보낸다.
  5. 고르는 창: 줄이 많으면 창을 키우지 않고 안쪽이 구르고, 취소 단추는 창 안에 있다.
  6. 그림: 폼이면 formNum 으로 그린다 (도감 번호 num 은 그대로).
"""
import os
import sys
import tempfile
import types

os.environ["POKET_HOME"] = tempfile.mkdtemp(prefix="poket-test-forms-")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import tkinter as tk                                        # noqa: E402

from poketdesktop import platform_os as PLAT                # noqa: E402
from poketdesktop import overlay, ui_bag, ui_box, ui_common as U, ui_shop  # noqa: E402

OK = FAIL = 0


def chk(name, cond, got=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s   %r" % (name, got))


def T(of, ofkr, form, fkr):
    return {"of": of, "ofKr": ofkr, "form": form, "formKr": fkr}


GRACIDEA = {"id": "GRACIDEA", "kr": "그라시데아꽃", "cat": "form", "desc": "꽃다발.",
            "effect": {"kind": "form", "forms": ["SHAYMIN_SKY"]},
            "forms": [T("SHAYMIN", "쉐이미", "SKY", "스카이폼")]}
CATALOG = {"id": "ROTOMCATALOG", "kr": "로토무카탈로그", "cat": "form", "desc": "가전제품 카탈로그.",
           "effect": {"kind": "form", "forms": []},
           "forms": [T("ROTOM", "로토무", k, kr) for k, kr in
                     (("HEAT", "히트로토무"), ("WASH", "워시로토무"), ("FROST", "프로스트로토무"),
                      ("FAN", "스핀로토무"), ("MOW", "커트로토무"))]}
PINK = {"id": "PINKNECTAR", "kr": "연분홍꿀", "cat": "form", "desc": "꽃꿀.",
        "effect": {"kind": "form", "forms": ["ORICORIO_PAU"], "consume": True},
        "forms": [T("ORICORIO", "춤추새", "PAU", "훌라훌라스타일")]}

def M(pid, species, name, level=50, **kw):
    m = {"id": pid, "species": species, "level": level, "info": {"name": name}}
    m.update(kw)
    return m


def main():
    PLAT.before_tk()
    root = tk.Tk()
    root.withdraw()
    U.init_fonts(root)
    U.apply_theme(root)

    print("=== 설명")
    d = ui_bag.item_desc(GRACIDEA)
    chk("켜고 끄기: 본가 설명 + 누가 무엇이 되나 + 다시 쓰면 돌아온다",
        d.startswith("꽃다발.") and "쉐이미 → 스카이폼" in d and "원래 모습으로 돌아온다" in d, d)
    d = ui_bag.item_desc(CATALOG)
    chk("고르기: 다섯 모습을 한 줄에 · 쓸 때 고른다", "로토무 → 히트로토무 · 워시로토무" in d and "고른다" in d, d)
    chk("꽃꿀: 쓰면 없어진다", "쓰면 없어진다" in ui_bag.item_desc(PINK))
    chk("상점 덧말도 같은 줄 (본가 설명은 빼고)", ui_shop.effect_note(CATALOG).startswith("로토무 → 히트로토무"),
        ui_shop.effect_note(CATALOG))
    chk("상점 분류에 '폼 도구' 가 있다", ("form", "폼 도구") in ui_shop.CATS)
    chk("가방 분류·쓸 수 있는 효과에 form", "form" in ui_bag.CAT_ORDER and "form" in ui_bag.USABLE
        and ui_bag.CAT_KR["form"] == "폼 도구")

    print("\n=== 대상")
    st = ui_bag.BagWindow._form_state
    chk("통하지 않는 종은 막는다", st(GRACIDEA, M(1, "PIKACHU", "피카츄"))[1] is True)
    g = st(GRACIDEA, M(2, "SHAYMIN", "쉐이미"))
    chk("쉐이미: 밝히고 '→ 스카이폼'", g[0] and not g[1] and "스카이폼" in g[2], g)
    g = st(GRACIDEA, M(2, "SHAYMIN", "쉐이미", form="SKY"))
    chk("  스카이폼이면 '원래 모습으로'", "원래 모습으로" in g[2], g)
    g = st(CATALOG, M(3, "ROTOM", "로토무", form="WASH"))
    chk("로토무: 지금 모습을 적는다", g[0] and "워시로토무" in g[2], g)
    chk("  원래 모습이면 '원래 모습'", "원래 모습" in st(CATALOG, M(3, "ROTOM", "로토무"))[2])
    chk("꽃꿀: 이미 그 모습이면 막는다", st(PINK, M(4, "ORICORIO", "춤추새", form="PAU"))[1] is True)
    chk("  다른 모습이면 쓸 수 있다", st(PINK, M(4, "ORICORIO", "춤추새"))[1] is False)

    print("\n=== 쓰기 전에 묻기")
    asked = []
    answer = {"v": None}
    real_ask = ui_box.ask_choice

    def fake_ask(parent, title, message, options):
        asked.append((title, message, list(options)))
        return answer["v"]
    mons = [M(14, "ROTOM", "로토무", 30, form="HEAT"), M(15, "SHAYMIN", "쉐이미")]
    said = []
    bag = types.SimpleNamespace(win=root, mons=mons, say=lambda *a, **k: said.append(a[0]))
    try:
        ui_box.ask_choice = fake_ask
        ask = lambda it, m: ui_bag.BagWindow._ask_form(bag, it, m)   # noqa: E731

        chk("켜고 끄기는 안 묻는다", ask(GRACIDEA, mons[1]) == "" and not asked, asked)
        answer["v"] = "WASH"
        got = ask(CATALOG, mons[0])
        opts = [o[0] for o in asked[-1][2]]
        chk("로토무카탈로그: 고른 모습을 보낸다", got == "WASH", got)
        chk("  지금 모습(히트)은 빼고 '원래 모습' 을 넣는다", "HEAT" not in opts and "" in opts
            and len(opts) == 5, opts)
        chk("  지금 모습을 적는다", "히트로토무" in asked[-1][1], asked[-1][1])
        answer["v"] = None
        chk("  그만두면 None (안 보낸다)", ask(CATALOG, mons[0]) is None)
        answer["v"] = ""
        chk("  '원래 모습' 은 빈 글자", ask(CATALOG, mons[0]) == "")
    finally:
        ui_box.ask_choice = real_ask

    print("\n=== 서버로 보내기")
    sent = []

    class NewApi(object):
        def use_item(self, item, pokemon=0, stat="", hour=None, form=""):
            sent.append(("new", item, pokemon, form, hour))
            return {"ok": True}

    class OldApi(object):
        def use_item(self, item, pokemon=0, stat="", hour=None):
            sent.append(("old-method", item))

        def _call(self, method, path, body):
            sent.append(("call", path, dict(body)))
            return {"ok": True}
    ui_bag.use_item(NewApi(), "ROTOMCATALOG", 14, "", 9, form="WASH")
    chk("새 api: form 을 같이 보낸다", sent[-1] == ("new", "ROTOMCATALOG", 14, "WASH", 9), sent[-1])
    ui_bag.use_item(OldApi(), "ROTOMCATALOG", 14, "", 9, form="WASH")
    chk("옛 api(form 을 모름): 직접 보낸다", sent[-1][0] == "call" and sent[-1][2].get("form") == "WASH",
        sent[-1])
    ui_bag.use_item(OldApi(), "RARECANDY", 14, "", 9)
    chk("  폼이 아닌 도구는 옛 api 그대로", sent[-1] == ("old-method", "RARECANDY"), sent[-1])

    print("\n=== 모습을 바꿔 배우려는 기술이 생기면 바로 묻는다 (1.13.3, 게시판 #279 주호)")
    # 워시로토무로 바꾸면 기술이 넷이라 하이드로펌프가 '배우려고 기다리는 기술' 이 되는데, 가방이 그걸 안 보고
    # 진화만 챙겨서 창이 안 떴다 - 레벨업을 해야 그제야 물었다.
    asked_learn = []
    app = types.SimpleNamespace(want_learn=lambda pid, name="": asked_learn.append((pid, name)))
    rotom = M(14, "ROTOM", "로토무", 30, form="HEAT")
    rotom["pending"] = []
    r = {"ok": True, "message": "로토무은(는) 워시로토무(으)로 모습이 바뀌었다!",
         "pokemon": dict(rotom, form="WASH", pending=["HYDROPUMP"])}
    chk("기다리는 기술이 새로 생기면 바로 묻는다", ui_bag.ask_new_learns(app, rotom, r) is True
        and asked_learn == [(14, "로토무")], asked_learn)
    asked_learn[:] = []
    rotom["pending"] = ["HYDROPUMP"]
    chk("  원래 있던 기다리는 기술로는 다시 안 묻는다", ui_bag.ask_new_learns(app, rotom, r) is False and not asked_learn)
    chk("  답에 포켓몬이 없으면(옛 서버) 조용히 넘어간다", ui_bag.ask_new_learns(app, rotom, {"ok": True}) is False)
    chk("  앱이 물을 줄 모르면 넘어간다", ui_bag.ask_new_learns(types.SimpleNamespace(), M(1, "ROTOM", "로토무"), r) is False)
    src = open(ui_bag.__file__, encoding="utf-8").read()
    body = src[src.index("    def do_use(self):"):src.index("    def _ask_form(self, it, mon):")]
    chk("  가방에서 도구를 쓴 뒤(do_use) 이것을 부른다", "ask_new_learns(self.app, mon, r)" in body)

    print("\n=== 고르는 창")
    made = []
    real_ghost = U.ghost_button

    def spy(parent, text, command=None, **kw):
        made.append((text, command))
        return real_ghost(parent, text, command, **kw)
    try:
        U.ghost_button = spy
        seen = {}

        def press(label):
            def go():
                wins = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]
                seen["h"] = wins[-1].winfo_height() if wins else 0
                seen["w"] = wins[-1] if wins else None
                cmd = next(c for t, c in made if t == label)
                cmd()
            root.after(150, go)
        press("워시로토무")
        got = ui_box.ask_choice(root, "로토무카탈로그", "모습을 고르세요.",
                                [("HEAT", "히트로토무", None), ("WASH", "워시로토무", None), ("", "원래 모습", None)])
        chk("누른 줄의 열쇠를 돌려준다", got == "WASH", got)
        made[:] = []
        press("취소")
        got = ui_box.ask_choice(root, "x", "y", [("A", "가", None)])
        chk("취소는 None", got is None, got)

        made[:] = []
        cancel_in = {}

        def check_many():
            w = [x for x in root.winfo_children() if isinstance(x, tk.Toplevel)][-1]
            w.update_idletasks()
            cancel_in["h"] = w.winfo_height()
            # 취소 단추(마지막 PushButton 이 아니라 '취소' 글자를 가진 것)가 창 안에 있나
            lab = [c for c in _walk(w) if isinstance(c, tk.Label) and c.cget("text") == "취소"]
            if lab:
                cancel_in["bottom"] = lab[0].winfo_rooty() - w.winfo_rooty() + lab[0].winfo_height()
            next(c for t, c in made if t == "취소")()
        root.after(200, check_many)
        ui_box.ask_choice(root, "많다", "고르세요.", [(i, "포켓몬 %d" % i, "Lv.%d" % i) for i in range(30)])
        chk("줄이 30개여도 창은 상한(520) 안", 0 < cancel_in.get("h", 0) <= U.h(520) + 4, cancel_in)
        chk("  취소 단추가 창 안에 있다", cancel_in.get("bottom", 99999) <= cancel_in.get("h", 0), cancel_in)
    finally:
        U.ghost_button = real_ghost

    print("\n=== 그림 번호")
    chk("폼이면 formNum 으로 그린다", overlay.look_num({"num": 492, "formNum": 10006}) == 10006)
    chk("  메가 모습(lookNum)이 먼저", overlay.look_num({"num": 6, "formNum": 1, "lookNum": 10034}) == 10034)
    chk("  폼이 아니면 num", overlay.look_num({"num": 25}) == 25)

    root.destroy()
    print()
    print("합계  OK %d   FAIL %d" % (OK, FAIL))
    return 1 if FAIL else 0


def _walk(w):
    for c in w.winfo_children():
        yield c
        for x in _walk(c):
            yield x


if __name__ == "__main__":
    sys.exit(main())
