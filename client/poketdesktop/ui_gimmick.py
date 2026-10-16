# -*- coding: utf-8 -*-
"""배틀 창의 'Z기술' 단추와 그 사건의 재생 (시즌 4).

관장·실시간·레이드 창이 같이 쓴다. 메가진화 단추(ui_mega.MegaToggle)와 같은 자리, 같은 약속이다.

## 단추

  · 메시지 막대 오른쪽 끝에 메가진화 단추와 나란히 선다. 명령을 고를 때만 보인다.
  · 서버가 준 `view["gimmick"]` 을 그대로 본다:
        zMoves    Z기술로 쓸 수 있는 기술마다 무엇이 되는지 (비었으면 단추 없음)
  · 누르면 켜지고, 다음 **기술**과 함께 보낸다 (교체·기권에는 안 실린다). 한 번 보내면 꺼진다.
  · **Z기술을 켜면 기술 칸이 바뀐다** - Z로 쓸 수 있는 기술은 Z기술의 이름·위력으로 보인다
    (decorate). 다른 기술을 고르면 그 기술이 보통으로 나가고 Z파워는 안 닳는다.

## 사건

    {"t": "zpower", "who", "move", "base", "text"}      Z파워를 두르는 연출 (그 뒤에 기술이 나간다)

창은 cv·later·effects·alive·_next·shown·_center·_show_banner·say 를 가진다
(세 배틀 창이 다 같다). `_apply` 에서 z_event 를 부르고 None 을 돌려주면 된다.
"""
from . import ui_common as U
from .z_fx import ZFx

Z_ON = ("#e0a51c", "#f2bd3d", "#5a3f06")          # 켜졌을 때 (바탕, 올렸을 때, 그림자)
SAFETY_MS = 2600          # 연출이 어디서 멈춰도 판은 흘러가야 한다
AFTER_MS = 420            # 끝난 모습을 잠깐 보여 주고 다음 사건으로


class Toggle(object):
    """켜고 끄는 단추 하나. ui_mega.MegaToggle 과 같은 동작이고, 글자와 색을 받는다."""

    def __init__(self, bar, text, colors, before=None, height=34, make=None, on_change=None):
        self.bar = bar
        self.before = before
        self.colors = colors
        self.on_change = on_change
        self.on = False
        self.shown = False
        self.text = text
        self.btn = (make or U.ghost_button)(bar, text, self.toggle, height=height)
        b = self.btn
        self._off = (b.fill, b._fg, b.hover, b._shadow)

    def toggle(self):
        self.set(not self.on)
        if self.on_change:
            self.on_change()

    def set(self, on):
        self.on = bool(on)
        b = self.btn
        if self.on:
            fill, hover, shadow = self.colors
            b.fill, b._fg, b.hover, b._shadow = fill, "#ffffff", hover, shadow
        else:
            b.fill, b._fg, b.hover, b._shadow = self._off
        b.configure(state="normal")          # 바탕·그림자·글자를 새 색으로 다시 칠한다

    def label(self, text):
        if text != self.text:
            self.text = text
            self.btn.configure(text=text)

    def show(self, can):
        can = bool(can)
        if can and not self.shown:
            kw = {"side": "right", "padx": (8, 0)}
            if self.before is not None:
                kw["before"] = self.before
            self.btn.holder.pack(**kw)
        elif not can and self.shown:
            self.btn.holder.pack_forget()
        self.shown = can
        if not can and self.on:
            self.set(False)

    def take(self):
        """이번 기술과 함께 보낼 값. 한 번 꺼내면 꺼진다."""
        v = bool(self.on and self.shown)
        if self.on:
            self.set(False)
        return v


class GimmickBar(object):
    """Z기술 단추. 창마다 하나씩 만든다.

    on_change: Z기술 단추를 켜고 끌 때 부른다 - 창이 기술 칸을 다시 그린다 (decorate 가 달라진다).
    prev: 앞서 쓰던 막대. 창 크기를 바꾸면 메시지 막대를 통째로 다시 만드는데(battle_zoom),
          그때 켜 둔 단추가 꺼지지 않게 다음에 보일 때 한 번 되살린다.
    """

    def __init__(self, bar, before=None, make=None, on_change=None, prev=None):
        self.g = {}
        self.z = Toggle(bar, "Z기술", Z_ON, before=before, make=make, on_change=on_change)
        self._keep = bool(prev.z.on and prev.z.shown) if prev is not None else False

    def show(self, g):
        """명령을 고를 때 부른다. g = view["gimmick"] (숨길 때는 None)."""
        self.g = dict(g or {})
        self.z.show(bool(self.g.get("zMoves")))
        keep, self._keep = self._keep, False
        if keep and self.z.shown:
            self.z.set(True)                 # 창 크기를 바꾸기 전에 켜 둔 것

    def hide(self):
        self.show(None)

    def z_of(self, key):
        """이 기술을 Z기술로 쓰면 무엇이 되는지. 못 쓰면 None."""
        for z in self.g.get("zMoves") or []:
            if z.get("key") == key:
                return z
        return None

    def decorate(self, move):
        """기술 칸에 그릴 것. Z기술을 켜 두었고 이 기술이 되는 기술이면 Z기술의 모습으로 바꾼다."""
        if not (self.z.on and self.z.shown):
            return move
        z = self.z_of(move.get("key"))
        if not z:
            return move
        out = dict(move, kr=z.get("name") or move.get("kr"), z=True)
        if z.get("status"):
            note = z.get("effect")
            out["desc"] = ("Z파워: %s. 그다음 %s 이(가) 나간다." % (note, move.get("kr") or "원래 기술")
                           if note else "Z파워를 두른 뒤 %s 이(가) 나간다." % (move.get("kr") or "원래 기술"))
        else:
            out["power"] = z.get("power")
            out["acc"] = 0
            out["desc"] = ("%s 을(를) Z기술로 쓴다. 반드시 맞고, 방어 중인 상대에게도 1/4 이 들어간다. "
                           "추가 효과는 없다." % (move.get("kr") or "이 기술"))
            if z.get("power") is None:
                out["desc"] = "상대의 남은 체력의 3/4 을 깎는다. 반드시 맞는다."
        return out

    def take(self, move_key):
        """이번에 Z기술로 보낼지. 한 번 꺼내면 꺼진다.

        고른 기술이 Z기술이 되는 기술일 때만 싣는다 - 아니면 그 기술이 보통으로 나간다.
        """
        z = self.z.take()
        return bool(z and self.z_of(move_key))


def act_kwargs(mega, z):
    """api.*_act 에 넘길 것. **Z기술은 켰을 때만 싣는다** - 안 켠 요청은 시즌 4 전과
    한 글자도 다르지 않다 (서버도, 이 창들을 가짜 api 로 돌리는 검사도 그대로 받는다)."""
    kw = {"mega": bool(mega)}
    if z:
        kw["z"] = True
    return kw


# ---------------------------------------------------------------- 사건 재생
def _run(win, make):
    """연출 하나를 돌리고, 끝나면 win._next 로 넘긴다 (ui_mega.play_in 과 같은 약속)."""
    state = {"done": False}

    def done():
        if state["done"] or not win.alive:
            return
        state["done"] = True
        win.later(AFTER_MS, win._next)

    try:
        fx = make(done)
        win.effects = [e for e in win.effects if not e.dead] + [fx]
        win.later(SAFETY_MS, done)
        fx.play()
    except Exception:                                       # noqa: BLE001
        done()


def z_event(win, ev, size=None, color=None, key=None, banner=None):
    """{"t": "zpower"}: Z파워를 두르는 연출. 기술 자체는 뒤따르는 "move" 사건이 그린다."""
    if key is None:
        key = ev.get("who") if ev.get("who") in ("me", "foe") else None
    win.say(ev.get("text"))
    if key is None or win.shown.get(key) is None:
        return win.later(600, win._next)
    (banner or (lambda t: win._show_banner(key, t)))("Z기술! %s" % (ev.get("move") or ""))
    _run(win, lambda done: ZFx(win.cv, win._center(key), win.later, color, on_done=done, size=size))
