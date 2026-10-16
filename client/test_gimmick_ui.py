# -*- coding: utf-8 -*-
"""배틀 창의 Z기술 단추 검사 (시즌 4).

    python client/test_gimmick_ui.py
    python client/run_as_windows.py client/test_gimmick_ui.py

**창을 진짜로 띄운다.** 가짜 api 는 관장·실시간·레이드 검사의 것을 빌려 쓴다 (Z기술 값을
엔진에 넘기는 것만 얹었다) - 판은 서버와 같은 엔진이 이 프로세스에서 돈다.

테라스탈은 1.11.0 에 내지 않기로 했다 (2026-10-14) - 단추가 없는 것도 본다.

## 무엇을 못 박나

  1. Z링이 있을 때만 단추가 뜬다. 없으면 아예 안 보이고, 보내는 요청도 예전과 같다.
  2. 단추는 메시지 막대에 메가진화 단추와 나란히 선다. 막대 안에 들어오고 눌린 위젯이 없다.
  3. Z기술을 켜면 기술 칸이 바뀐다 - 되는 기술은 Z기술의 이름·위력으로 보인다.
  4. 켜고 기술을 쓰면 그 값이 **그 기술과 함께** 간다. 한 번 보내면 꺼진다.
     Z기술을 켜고 안 되는 기술을 고르면 그 기술이 보통으로 나간다 (Z파워는 안 닳는다).
  5. 쓰고 나면 단추가 다시 안 뜬다.
  6. 실시간·레이드 창도 같다.
"""
import json
import os
import random
import sys
import tempfile

os.environ.setdefault("POKET_HOME", os.path.join(tempfile.gettempdir(), "poket-test-gimmick"))

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import tkinter as tk                                        # noqa: E402

import test_gym_ui as TG                                    # noqa: E402
import test_live_ui as TL                                   # noqa: E402
import test_raid_ui as TR                                   # noqa: E402
from common import live_battle as LB                        # noqa: E402
from common import pokelogic as P                           # noqa: E402
from common import raid_battle as RB                        # noqa: E402
from common import trainer_battle as TB                     # noqa: E402
from poketdesktop import platform_os as PLAT                # noqa: E402
from poketdesktop import ui_common as U                     # noqa: E402
from poketdesktop import ui_gimmick                         # noqa: E402
from poketdesktop import ui_gym_battle as GB                # noqa: E402
from poketdesktop import ui_live_battle as LUI              # noqa: E402
from poketdesktop import ui_raid_battle as RUI              # noqa: E402
from test_learn_dialog import squeezed                      # noqa: E402

OK = FAIL = 0
DATA = os.path.join(ROOT, "server", "data")


def chk(name, cond, got=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s   %r" % (name, got))


class GymApi(TG.FakeApi):
    """관장 검사의 가짜 api + Z기술. 받은 요청을 그대로 적어 둔다."""

    def gym_act(self, bid, kind, move="", slot=-1, mega=False, **kw):
        self.megas.append(bool(mega))
        self.sent = getattr(self, "sent", []) + [dict(kw, move=move)]
        if kind == "move":
            ev = self.tb.act("move", move, mega=mega, z=bool(kw.get("z")))
        else:
            ev = self.tb.act(kind, slot) if kind != "forfeit" else self.tb.act("forfeit")
        return self._out(ev, {})


class LiveApi(TL.FakeApi):
    def live_act(self, kind, move="", slot=-1, mega=False, **kw):
        self.sent = getattr(self, "sent", []) + [dict(kw, move=move)]
        value = move if kind == "move" else (slot if kind == "switch" else None)
        self.lb.choose("a", kind, value, mega=mega, z=bool(kw.get("z")))
        if self.auto_foe and self.lb.can_act("b"):
            self.lb.choose("b", *self.lb.auto_choice("b"))
        if self.lb.ready():
            self.events = self.lb.resolve()
            self.turn = self.lb.turn
            if self.lb.over:
                self.state = "done"
        return self.match()


class RaidApi(TR.FakeApi):
    def raid_act(self, kind, move="", slot=-1, mega=False, **kw):
        self.sent = getattr(self, "sent", []) + [dict(kw, move=move)]
        self.rb.choose(0, kind, move if kind == "move" else slot, mega=mega, z=bool(kw.get("z")))
        for i in range(1, len(self.rb.players)):
            if self.rb.players[i].playing():
                self.rb.choose(i, *self.rb.auto_choice(i))
        self.events = self.rb.resolve()
        self.round = self.rb.round
        if self.rb.over:
            self.state = "done"
        return self.room()


def in_bar(toggle):
    """단추가 보이고, 메시지 막대 안에 온전히 들어와 있나."""
    h = toggle.btn.holder
    if not (toggle.shown and h.winfo_ismapped()):
        return False, "안 보임"
    bar = h.master
    x, w = h.winfo_x(), h.winfo_width()
    return (x >= 0 and x + w <= bar.winfo_width() and h.winfo_height() <= bar.winfo_height()
            and w >= h.winfo_reqwidth()), (x, w, bar.winfo_width(), h.winfo_reqwidth())


def cell_names(win):
    """기술 칸에 적힌 굵은 이름들 (왼쪽 위부터)."""
    out = []

    def walk(w):
        for c in w.winfo_children():
            if isinstance(c, tk.Label):
                f = str(c.cget("font"))
                if "bold" in f and c.master.master.master is not None and c.cget("anchor") == "w":
                    out.append(c.cget("text"))
            walk(c)
    walk(win.left)
    return out


def no_tera(gim):
    """테라스탈 단추가 없다 (1.11.0 에 내지 않는다)."""
    return not hasattr(gim, "tera") and "테라스탈" not in [w.cget("text") for w in _labels(gim.z.bar)]


def _labels(w):
    out = []
    for c in w.winfo_children():
        if isinstance(c, tk.Label):
            out.append(c)
        out.extend(_labels(c))
    return out


def gym_part(root, dex, gyms, kmap):
    print("=== 관장 배틀 창 ===")
    liz = TG.mon(dex, "CHARIZARD", 100, ["FLAMETHROWER", "DRAGONCLAW", "AIRSLASH", "SUNNYDAY"], "BLAZE", 21)
    liz["held"] = "FIRIUMZ"
    party = [liz, TG.mon(dex, "GARCHOMP", 100, ["EARTHQUAKE"], "ROUGHSKIN", 22)]
    api = GymApi(dex, gyms, kmap, party)
    app = TG.FakeApp(root, api, dex)
    low = min((t for t in gyms["trainers"] if t["level"] < 60), key=lambda t: t["level"])

    def open_battle(have):
        api.region = low["region"]
        api.tb = TB.TrainerBattle(dex, [dict(m) for m in party], api.by_region[low["region"]],
                                  random.Random(7))
        api.tb.zring["me"] = have
        b = GB.GymBattleWindow(app, api._out(api.tb.start()))
        TG.pump(root, lambda: not b.busy, 30)
        root.update()
        return b

    b = open_battle(False)
    chk("Z링이 없으면 단추가 안 뜬다", not b.gim.z.shown and not b.gim.z.btn.holder.winfo_ismapped())
    b.use_move("FLAMETHROWER")
    TG.pump(root, lambda: not b.busy, 30)
    chk("  그때 보내는 요청에는 Z 칸이 아예 없다 (예전과 같다)",
        api.sent[-1] == {"move": "FLAMETHROWER"}, api.sent[-1])
    b.close()
    root.update()

    b = open_battle(True)
    ok, got = in_bar(b.gim.z)
    chk("Z기술 단추가 메시지 막대 안에 뜬다", ok, got)
    chk("  테라스탈 단추는 없다", no_tera(b.gim))
    chk("  메시지 글이 함께 보인다", "무엇을 할까" in b.msg.cget("text"), b.msg.cget("text"))
    chk("  눌린 위젯이 없다", not squeezed(b.win), squeezed(b.win)[:3])
    chk("기본은 꺼짐", not b.gim.z.on)
    before = cell_names(b)
    chk("끄면 기술 칸은 원래 이름", "화염방사" in before and "다이내믹풀플레임" not in before, before)

    b.gim.z.toggle()
    root.update()
    after = cell_names(b)
    chk("Z기술을 켜면 되는 기술이 Z기술 이름으로 바뀐다", "다이내믹풀플레임" in after and "화염방사" not in after,
        after)
    chk("  변화기는 Z + 원래 이름", "Z쾌청" in after, after)
    chk("  안 되는 기술은 그대로다", "드래곤클로" in after and "에어슬래시" in after, after)
    chk("  켠 색으로 바뀐다", b.gim.z.on and b.gim.z.btn.box.cget("bg") == ui_gimmick.Z_ON[0],
        b.gim.z.btn.box.cget("bg"))
    z = b.gim.decorate({"key": "FLAMETHROWER", "kr": "화염방사", "power": 90, "acc": 100})
    chk("  칸에 그릴 값: 위력 175, 반드시 명중", z["power"] == 175 and z["acc"] == 0 and z.get("z"), z)
    chk("  눌린 위젯이 없다 (다시 그린 뒤)", not squeezed(b.win), squeezed(b.win)[:3])
    b.gim.z.toggle()
    root.update()
    chk("다시 끄면 원래 이름으로 돌아온다", "화염방사" in cell_names(b), cell_names(b))

    b.gim.z.toggle()
    b.open_switch()
    root.update()
    chk("교체 화면에서는 숨고 꺼진다", not b.gim.z.shown and not b.gim.z.on)
    b.show_commands()
    root.update()
    chk("기술 화면으로 돌아오면 다시 뜬다 (꺼진 채)", b.gim.z.shown and not b.gim.z.on)

    # Z기술을 켜고 안 되는 기술을 고르면 그 기술이 보통으로 나간다
    b.gim.z.toggle()
    b.use_move("DRAGONCLAW")
    TG.pump(root, lambda: not b.busy, 30)
    root.update()
    chk("Z를 켜고 안 되는 기술을 고르면 Z를 안 싣는다", api.sent[-1] == {"move": "DRAGONCLAW"}, api.sent[-1])
    chk("  Z파워가 안 닳아 단추가 다시 뜬다", b.gim.z.shown and not b.view["gimmick"]["zUsed"])

    seen = []
    orig = b._apply
    b._apply = lambda ev: (seen.append(ev.get("t")), orig(ev))[1]
    b.gim.z.toggle()
    b.use_move("FLAMETHROWER")
    chk("보내면 단추가 바로 꺼진다", not b.gim.z.on)
    TG.pump(root, lambda: not b.busy, 40)
    root.update()
    chk("켜고 쓰면 z 가 기술과 함께 간다", api.sent[-1] == {"move": "FLAMETHROWER", "z": True}, api.sent[-1])
    chk("Z파워 사건을 재생한다 (테라스탈은 없다)", "zpower" in seen and "tera" not in seen, seen)
    chk("쓰고 나면 단추가 다시 안 뜬다", not b.gim.z.shown and b.view["gimmick"]["zUsed"], b.view.get("gimmick"))
    chk("연출이 남기고 간 것이 없다", all(e.dead for e in b.effects), [type(e).__name__ for e in b.effects])
    b.close()
    root.update()


def live_part(root, dex):
    print("\n=== 실시간 배틀 창 ===")
    api = LiveApi(dex)
    liz = TL.mon(dex, "CHARIZARD", ["FLAMETHROWER", "DRAGONCLAW"], 1)
    liz["held"] = "FIRIUMZ"
    a = [liz, TL.mon(dex, "PIKACHU", ["THUNDERBOLT"], 2)]
    b = [TL.mon(dex, "SNORLAX", ["TACKLE"], 3), TL.mon(dex, "BLASTOISE", ["SURF"], 4)]
    api.lb = LB.LiveBattle(dex, (1, "나", a), (2, "상대", b), rng=random.Random(4))
    api.lb.zring["me"] = True                                  # 자리 a 가 me
    api.events = api.lb.start()
    app = TL.FakeApp(root, api, dex)
    w = LUI.LiveBattleWindow(app, api.match())
    TL.pump(root, lambda: not w.busy, 25)
    TL.rest(root, 0.3)
    ok, got = in_bar(w.gim.z)
    chk("Z기술 단추가 메시지 막대 안에 뜬다", ok, got)
    chk("  테라스탈 단추는 없다", no_tera(w.gim))
    chk("  눌린 위젯이 없다", not squeezed(w.win), squeezed(w.win)[:3])
    w.gim.z.toggle()
    root.update()
    chk("Z기술을 켜면 기술 칸이 바뀐다", "다이내믹풀플레임" in cell_names(w), cell_names(w))
    w.use_move("FLAMETHROWER")
    TL.pump(root, lambda: "me" in api.lb.z_done and not w.busy, 25)
    chk("z 가 기술과 함께 간다", api.sent[-1] == {"move": "FLAMETHROWER", "z": True}, api.sent[-1])
    TL.rest(root, 0.3)
    chk("쓰고 나면 단추가 다시 안 뜬다", not w.gim.z.shown)
    w.close()
    root.update()


def raid_part(root, dex):
    print("\n=== 레이드 배틀 창 ===")
    api = RaidApi(dex, n=3, revealed=True)
    players = []
    for i in range(3):
        lead = RB.leveled(TR.mon(dex, "CHARIZARD" if i == 0 else "SNORLAX", 50,
                                 ["FLAMETHROWER", "DRAGONCLAW"] if i == 0 else ["TACKLE"],
                                 100 + i), 50)
        if i == 0:
            lead["held"] = "FIRIUMZ"
        players.append((i + 1, "참가자%d" % (i + 1),
                        [lead, RB.leveled(TR.mon(dex, "PIKACHU", 50, ["THUNDERBOLT"], 200 + i), 50)]))
    boss = TR.mon(dex, "MEWTWO", 60, ["PSYCHIC", "SHADOWBALL", "AURASPHERE", "RECOVER"], 1)
    api.rb = RB.RaidBattle(dex, boss, players, hp_mult=40, max_rounds=15, rng=random.Random(5))
    p0 = api.rb.players[0]
    p0.zring["me"] = True                              # 서버(raid.begin)가 하는 것과 같다
    api.events = api.rb.start()
    api.round = 0
    api.state = "fighting"
    app = TR.FakeApp(root, api, dex)
    bw = RUI.RaidBattleWindow(app, api.room())
    TR.pump(root, lambda: not bw.busy, 25)
    TR.rest(root, 0.3)
    ok, got = in_bar(bw.gim.z)
    chk("Z기술 단추가 메시지 막대 안에 뜬다", ok, got)
    chk("  테라스탈 단추는 없다", no_tera(bw.gim))
    chk("  눌린 위젯이 없다", not squeezed(bw.win), squeezed(bw.win)[:3])
    bw.gim.z.toggle()
    root.update()
    chk("Z기술을 켜면 기술 칸이 바뀐다", "다이내믹풀플레임" in cell_names(bw), cell_names(bw))
    bw.use_move("FLAMETHROWER")
    TR.pump(root, lambda: "me" in p0.z_done and not bw.busy, 25)
    chk("z 가 기술과 함께 간다", api.sent[-1] == {"move": "FLAMETHROWER", "z": True}, api.sent[-1])
    TR.rest(root, 0.3)
    chk("쓰고 나면 단추가 다시 안 뜬다", not bw.gim.z.shown)
    bw.close()
    root.update()


def main():
    with open(os.path.join(DATA, "pokedex.json"), encoding="utf-8") as f:
        dex = P.Pokedex(json.load(f))
    with open(os.path.join(DATA, "gyms.json"), encoding="utf-8") as f:
        gyms = json.load(f)
    with open(os.path.join(DATA, "korea_map.json"), encoding="utf-8") as f:
        kmap = json.load(f)

    PLAT.before_tk()
    root = tk.Tk()
    root.withdraw()
    U.init_fonts(root)
    U.apply_theme(root)
    errors = []

    def on_err(exc, val, tb):
        import traceback
        errors.append("".join(traceback.format_exception(exc, val, tb))[-400:])
    root.report_callback_exception = on_err
    print("글꼴 %s / 본문 %dpt (BASE_PT=%d)" % (U.FAMILY, U.FONT[1], U.BASE_PT))
    # 연출 대기를 1/10 로
    orig_later = GB.GymBattleWindow.later
    GB.GymBattleWindow.later = lambda self, ms, fn: orig_later(self, max(1, ms // 10), fn)

    gym_part(root, dex, gyms, kmap)
    live_part(root, dex)
    raid_part(root, dex)

    TG.pump(root, lambda: False, 1.0)
    chk("Tk 콜백에서 난 오류가 없다", not errors, errors[:2])
    root.destroy()
    print("\n%d개 통과, %d개 실패" % (OK, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
