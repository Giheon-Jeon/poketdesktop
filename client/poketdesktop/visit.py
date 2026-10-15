# -*- coding: utf-8 -*-
"""친구 집에 놀러 가기 · 친구 채팅 (1.11.0) — 바탕화면 쪽. 규칙은 서버 visit.py 에 있다.

    손님(guest)   내 포켓몬은 잠시 빠지고(맨 앞 한 마리만 오른쪽 아래에 선다), 친구 파티의 포켓몬들이
                  내 화면에서 제 발로 돌아다닌다.
    주인(host)    내 포켓몬은 그대로 돌아다니고, 친구가 보낸 포켓몬이 오른쪽 아래에 선다.
                  내 파티가 바뀌면(넣고 빼기·메가진화) 그때만 보낸다.

**걷는 자리는 맞추지 않는다** (10/15 사용자 결정). 처음에는 주인이 0.5초마다 자리를 보내고 손님 화면이
그 자리를 따라 걷게 했는데, 순간이동은 안 해도 뚝뚝 끊겼다. 그래서 맞추는 것은 누가 있나(파티·모습)와
말·동작뿐이고, 친구 포켓몬은 손님 화면에서 내 포켓몬처럼 스스로 돌아다닌다.

**오고 가는 것은 걸어서** (10/15 사용자 요청). 보낸 포켓몬은 화면 오른쪽 밖에서 걸어 들어와 오른쪽 아래에
서고, 끝나면 오른쪽 밖으로 걸어 나간다 (두 화면 모두). 손님은 집에 돌아오면 그 포켓몬이 다시 오른쪽에서
걸어 들어온다.

**도구는 들고 가서 보따리로 둔다** (10/15 사용자 교정). 보낼 때는 들고 갈 것만 고르고(ui_visit, 가방
모양), 친구 집에서 보낸 포켓몬을 우클릭해 '여기에 두기' 를 하면 고른 만큼 보따리에 싸서 그 옆에 둔다. 두 화면
모두 보따리가 보이고, 주인이 누르면 받는다 - "OO 님에게 ~를 받았다!".

**채팅 창은 없다** (10/15 사용자 교정). 내 포켓몬을 눌러 포커스를 주고 Enter 를 치면 그 머리 위에 입력
말풍선이 뜬다 - 치고 Enter 면 말풍선으로 말하고(포커스는 그 포켓몬에게 돌아간다), Esc 면 닫는다. '/춤' 같은
명령은 동작이다. 손님은 보낸 포켓몬이, 주인은 내 포켓몬 누구나 말할 수 있고 상대 화면에서도 그 포켓몬 위에
뜬다. 우클릭 메뉴에 '말하기' 와 '집으로 돌아오기' (주인은 '돌려보내기') 가 있다. 메가진화한 모습으로 걷기를
켜고 끄면(우클릭 메뉴) 상대 화면에서도 메가진화 연출과 함께 바뀐다.

맥은 테두리 없는 창이 글자를 못 받는다 - PLAT.take_keys 가 고른 창만 받게 연다.

**남의 도트(VisitPet·FriendPet)는 overlay.pets 에 넣지 않는다** - 동기화가 내 목록으로 지워 버린다. 투기장
상대처럼 overlay.extra 에 넣어 프레임만 같이 받는다. 손님일 때는 overlay.locked 로 동기화가 내 도트를 다시
깔지 못하게 막는다 (투기장과 같은 약속 - 끝나면 푼다).
"""
import math
import time
import tkinter as tk

from PIL import Image, ImageDraw

from common import tint as T

from . import config, guild_ws, item_icons, sprite_cache, walk_cache
from . import platform_os as PLAT
from . import ui_common as U
from .overlay import Pet, look_num
from .sprites import LEFT, RIGHT
from .ui_common import run_async

PARTY_MS = 1000              # 주인이 내 파티가 바뀌었나 보는 간격 (서버는 0.5초보다 자주는 안 받는다)
LOOK_MS = 500                # 손님이 보낸 포켓몬의 모습(메가진화)이 바뀌었나 보는 간격
SAY_GAP = 0.65               # 말·동작을 이보다 자주 보내지 않는다 (서버는 0.6초 안의 것을 버린다)
BUBBLE_MS = 6000             # 말풍선이 떠 있는 시간
HINT_MS = 9000               # 처음에 알려 주는 말풍선
FOLLOW_MS = 90               # 말풍선이 도트를 따라가는 간격
STROLL = 1.6                 # 들어오고 나가는 걸음 (평소 걸음의 배수)
POSE_MS = 9000               # 자기·앉기·눕기·기절을 이만큼 한다
HOP_GAP = 380                # 춤·점프의 한 박자
SAY_MAX = 60                 # 서버와 같다
FETCH_RETRY = 60.0           # 못 받은 도트는 이만큼 지나서야 다시 받아 본다 (못 받으면 끝없이 다시 받던 것을 막는다)
PAPER, INK, FAINT = "#fbfbf6", "#1b1b22", "#6e6e66"   # 말풍선 종이·글씨·흐린 글씨

# 명령 -> 동작. 서버 ACTS 와 같은 열쇠다.
ACT_WORDS = {"/춤": "dance", "/자기": "sleep", "/잠": "sleep", "/앉기": "sit", "/앉아": "sit",
             "/눕기": "lie", "/누워": "lie", "/점프": "hop", "/인사": "hello", "/기절": "faint",
             "/일어나": "wake", "/깨기": "wake"}
ACT_KR = {"dance": "춤", "sleep": "자기", "sit": "앉기", "lie": "눕기", "hop": "점프", "hello": "인사",
          "faint": "기절", "wake": "일어나기"}
HINT = "/춤 /자기 /앉기 /눕기 /점프 /인사 /기절 /일어나"
TALK_HINT = "나를 누르고 Enter 를 치면 말할 수 있어요"
GUEST_HINT = TALK_HINT + "\n우클릭: 여기에 두기 · 집으로 돌아오기"
HOST_HINT = TALK_HINT + "\n놀러 온 포켓몬 우클릭: 돌려보내기"
DROP_MS = 380                # 보따리가 머리 위에서 떨어지는 시간
# 자세마다 쓸 동작 (그 종에 있는 것 중 앞에서부터)
POSES = {"sleep": ("Sleep", "EventSleep", "Laying"), "sit": ("Sit", "Idle"),
         "lie": ("Laying", "Sleep", "Sit"), "faint": ("Laying", "Sleep")}


class VisitSocket(guild_ws.GuildSocket):
    PATH = "/ws/visit"
    NAME = "visit-ws"
    GIVE_UP = (4401, 4429)


def make_socket(app, on_event):
    """이 앱의 서버에 붙는 놀러 가기 소켓. 붙을 수 없으면 None (라이브러리가 없거나 시험용 앱)."""
    api = getattr(app, "api", None)
    base, token = getattr(api, "base", None), getattr(api, "token", None)
    if not (guild_ws.available() and base and token):
        return None
    return VisitSocket(app.root, base, token, on_event).start()


def parse(text):
    """입력 말풍선에 친 것. ("act", 동작) / ("say", 말) / ("bad", 알 수 없는 명령) / None (빈 줄)."""
    text = " ".join((text or "").split())
    if not text:
        return None
    if text.startswith("/"):
        act = ACT_WORDS.get(text.split(" ")[0])
        return ("act", act) if act else ("bad", text)
    return ("say", text)


def skin_of(mon):
    return T.skin(mon)


def pet_mon(p, base_id):
    """서버가 준 한 마리(주인의 파티·손님의 포켓몬)를 Overlay.make 가 먹는 꼴로.

    id 는 음수로 둔다 - 내 포켓몬 번호와 절대 안 겹친다.
    """
    num = int(p.get("num") or 0)
    look = int(p.get("look") or 0)
    out = {"id": base_id, "num": num, "shiny": bool(p.get("shiny")), "tint": p.get("tint"),
           "info": {"name": p.get("name") or "?", "level": p.get("level") or 1,
                    "species": p.get("species"), "types": []}}
    if look and look != num:
        out["lookNum"] = look
    return out


def party_order(p):
    """파티 자리 순. 자리 0 이 맨 앞이다 - 0 을 '없음' 으로 읽지 않는다."""
    slot = (p.mon or {}).get("slot")
    return (slot if slot is not None else 99, p.id or 0)


def lead_of(pets):
    """파티 맨 앞."""
    pets = list(pets)
    return min(pets, key=party_order) if pets else None


# ---------------------------------------------------------------- 남의 도트
class _Guest(object):
    """남의 포켓몬에게 공통: 누르고 끌고 두 번 눌러 여는 것은 없다 (우클릭은 놀러 가기 메뉴)."""

    def on_press(self, e):
        self.hide_tip()

    def on_motion(self, e):
        pass

    def on_release(self, e):
        pass

    def on_double(self, e):
        pass

    def can_drag(self):
        return False


class FriendPet(_Guest, Pet):
    """손님 화면의 친구 포켓몬. 내 포켓몬처럼 스스로 돌아다닌다 (자리를 맞추지 않는다)."""


class VisitPet(_Guest, Pet):
    """주인 화면의 놀러 온 포켓몬. 스스로 돌아다니지 않는다 - 들어오고 나가는 걸음은 Stroll 이 맡는다."""

    def __init__(self, overlay, mon, anim):
        Pet.__init__(self, overlay, mon, anim)
        self.battling = True          # Pet 의 판단으로는 안 움직인다
        self.state = "idle"
        self._visit_act = None

    def rest_anim(self):
        return "Idle" if self.anim_for("Idle") is not None else "Walk"

    def update(self, ms):
        self.advance(ms)
        if self.once or self.state == "walk" or getattr(self, "_visit_act", None):
            return                    # 걷는 중(Stroll)이거나 동작 중이면 그쪽이 고른 그림 그대로
        want = self.rest_anim()
        if want != self.anim_name:
            self.play(want)


# ---------------------------------------------------------------- 걸어 들어오고 나가기
class Stroll(object):
    """도트 하나를 (tx, ty) 까지 걸려 보낸다. 닿으면 done().

    스스로 돌아다니지 않는 도트(battling 이 참)에게만 쓴다 - 아니면 Pet.update 와 서로 끌어당긴다.
    걸은 거리(walked)를 쌓아 주어야 발이 굴러간다 (Pet.advance). 동작 중(_visit_act)에는 멈춰 선다.
    """

    def __init__(self, root, pet, tx, ty, speed, done=None, tick_ms=33):
        self.root, self.pet = root, pet
        self.tx, self.ty = float(tx), float(ty)
        self.speed = max(10.0, float(speed))
        self.done = done
        self.tick_ms = tick_ms
        self.job = None
        self.dead = False
        old = getattr(pet, "_stroll", None)
        if old is not None:
            old.cancel()
        pet._stroll = self
        self.last = time.time()
        self.step()

    def step(self):
        self.job = None
        if self.dead:
            return
        p = self.pet
        now = time.time()
        dt, self.last = min(0.1, now - self.last), now
        if getattr(p, "_visit_act", None):
            self.job = self.root.after(self.tick_ms, self.step)
            return
        try:
            dx, dy = self.tx - p.x, self.ty - p.y
            d = math.hypot(dx, dy)
            move = self.speed * dt
            if d <= max(0.8, move):
                p.x, p.y = self.tx, self.ty
                p.place()
                return self.finish()
            p.state = "walk"
            if p.anim_name != "Walk" and not p.once:
                p.play("Walk")
            p.x += dx / d * move
            p.y += dy / d * move
            p.walked += move
            p.turn_to(dx, dy)
            p.place()
        except Exception:                                   # noqa: BLE001
            return self.cancel()                            # 그사이 도트가 없어졌다
        self.job = self.root.after(self.tick_ms, self.step)

    def finish(self):
        self._unhook()
        p = self.pet
        p.state = "idle"
        try:
            p.play(p.rest_anim())
        except Exception:                                   # noqa: BLE001
            pass
        if self.done is not None:
            self.done()

    def cancel(self):
        self._unhook()

    def _unhook(self):
        self.dead = True
        if self.job is not None:
            try:
                self.root.after_cancel(self.job)
            except Exception:                               # noqa: BLE001
                pass
            self.job = None
        if getattr(self.pet, "_stroll", None) is self:
            self.pet._stroll = None


# ---------------------------------------------------------------- 보따리
CLOTH, CLOTH_LO, CLOTH_HI = (226, 86, 107), (176, 52, 76), (246, 146, 160)
CLOTH_DOT, CLOTH_LINE, CLOTH_SHADOW = (255, 236, 238), (54, 22, 32), (24, 26, 34)


def bundle_image(size, key=(255, 0, 255), squash=0.0):
    """보따리 그림 (점무늬 보자기로 싼 꾸러미). size = 높이(px). 배경은 투명색 key 로 채운다 (풀숲처럼).

    squash 는 바닥에 떨어진 순간 찌그러지는 정도 (0 ~ 0.25).
    """
    w, h = int(round(size * 1.2)), int(size)
    im = Image.new("RGB", (w, h), key)
    d = ImageDraw.Draw(im)
    lw = max(1, int(round(size / 22.0)))
    base = h - max(2, h // 12)
    cx = w / 2.0
    d.ellipse((w * 0.14, base - h * 0.06, w * 0.86, base + h * 0.05), fill=CLOTH_SHADOW)
    bh = h * 0.56 * (1 - squash * 0.55)
    bw = min(w - 2, w * 0.80 * (1 + squash * 0.3))
    x0, y1 = cx - bw / 2.0, base
    y0 = y1 - bh
    for s_ in (-1, 1):                    # 귀 (묶고 남은 보자기 두 끝) - 매듭 뒤에
        d.polygon([(cx + s_ * w * 0.04, y0 + h * 0.03), (cx + s_ * w * 0.07, y0 - h * 0.13),
                   (cx + s_ * w * 0.31, y0 - h * 0.30), (cx + s_ * w * 0.27, y0 - h * 0.08)],
                  fill=CLOTH, outline=CLOTH_LINE, width=lw)
        d.line([(cx + s_ * w * 0.09, y0 - h * 0.08), (cx + s_ * w * 0.25, y0 - h * 0.22)], fill=CLOTH_HI, width=lw)
    d.rounded_rectangle((x0, y0, x0 + bw, y1), radius=bh * 0.42, fill=CLOTH, outline=CLOTH_LINE, width=lw)
    d.rounded_rectangle((x0 + lw, y0 + bh * 0.58, x0 + bw - lw, y1 - lw), radius=bh * 0.30, fill=CLOTH_LO)
    d.ellipse((x0 + bw * 0.12, y0 + bh * 0.14, x0 + bw * 0.30, y0 + bh * 0.34), fill=CLOTH_HI)
    for s_ in (-1, 1):                    # 매듭에서 퍼지는 주름
        d.line([(cx + s_ * bw * 0.06, y0 + bh * 0.10), (cx + s_ * bw * 0.26, y0 + bh * 0.46)], fill=CLOTH_LO, width=lw)
    r = max(1.0, size * 0.04)
    for fx, fy in ((0.22, 0.60), (0.50, 0.50), (0.78, 0.62), (0.36, 0.82), (0.66, 0.84)):
        px, py = x0 + bw * fx, y0 + bh * fy
        d.ellipse((px - r, py - r, px + r, py + r), fill=CLOTH_DOT)
    kx, ky, kcy = w * 0.10, h * 0.085, y0 - h * 0.035
    d.ellipse((cx - kx, kcy - ky, cx + kx, kcy + ky), fill=CLOTH, outline=CLOTH_LINE, width=lw)
    d.ellipse((cx - kx * 0.45, kcy - ky * 0.55, cx + kx * 0.05, kcy - ky * 0.05), fill=CLOTH_HI)
    return im


def items_text(rows):
    """[{kr, count}] -> '이상한사탕 1개, 불꽃의돌 2개'."""
    return ", ".join("%s %d개" % (x.get("kr") or x.get("id") or "?", int(x.get("count") or 0)) for x in rows or [])


def bundle_size(ov):
    """바탕화면 보따리의 (그림 높이, 창 폭, 창 높이) - 도트 크기 설정을 따른다."""
    size = max(24, int(int(ov.settings.get("targetHeight") or 64) * 0.6))
    return size, int(round(size * 1.2)), size


class BundleObj(object):
    """바탕화면에 놓인 보따리 (풀숲과 같은 투명 창). 주인은 눌러서 받고, 손님에게는 안내만 뜬다."""

    def __init__(self, visit, bundle, x, y, drop_from=None):
        self.visit = visit
        self.bundle = bundle
        self.id = bundle.get("id")
        self.dead = False
        self.pending = False
        ov = visit.app.overlay
        self.root = ov.root
        key = ov.key
        hexkey = "#%02x%02x%02x" % key
        size = bundle_size(ov)[0]
        frames = [bundle_image(size, key), bundle_image(size, key, squash=0.22)]
        self.fw, self.fh = frames[0].size
        self.win = tk.Toplevel(self.root)
        self.win.overrideredirect(True)
        bg = PLAT.transparent_window(self.win, hexkey)
        self.view = PLAT.SpriteView(self.win, bg, self.fw, self.fh, cursor="hand2")
        self.label = self.view.widget
        self.photos = self.view.frames(frames, key)
        self.label.bind("<Button-1>", lambda _e: self.visit.on_bundle_click(self))
        self.label.bind("<Enter>", lambda _e: self.visit.bundle_tip(self, True))
        self.label.bind("<Leave>", lambda _e: self.visit.bundle_tip(self, False))
        self.x, self.y = float(x), float(y)
        self._job = None
        self._fall = None
        if drop_from is not None and drop_from < self.y:
            self._fall = (time.time(), float(drop_from), self.y)
            self.y = float(drop_from)
        self.win.geometry("+%d+%d" % (int(self.x), int(self.y)))
        self.view.show(self.photos[0])
        PLAT.raise_above(self.win)
        self.tick()

    def move(self, x, y):
        self.x, self.y = float(x), float(y)
        if self._fall is not None:
            t0, top, _ground = self._fall
            self._fall = (t0, top, self.y)
            return
        self.place()

    def place(self):
        try:
            self.win.geometry("+%d+%d" % (int(self.x), int(self.y)))
        except tk.TclError:
            pass

    def tick(self):
        """떨어지는 연출 (머리 위에서 바닥으로, 닿으면 한 번 찌그러진다) + 맥의 빈자리 클릭 통과."""
        self._job = None
        if self.dead:
            return
        if self._fall is not None:
            t0, top, ground = self._fall
            k = min(1.0, (time.time() - t0) * 1000.0 / DROP_MS)
            if k < 1.0:
                self.y = top + (ground - top) * k * k
                self.place()
            else:
                self._fall = None
                self.y = ground
                self.place()
                self.view.show(self.photos[1])
                self.root.after(110, lambda: (not self.dead) and self.view.show(self.photos[0]))
        if PLAT.NEEDS_HIT_TRACKING:
            try:
                cx, cy = self.root.winfo_pointerxy()
                self.view.update_hit(cx - int(self.x), cy - int(self.y))
            except Exception:                               # noqa: BLE001
                pass
        self._job = self.root.after(33 if self._fall is not None else 110, self.tick)

    def destroy(self):
        self.dead = True
        if self._job is not None:
            try:
                self.root.after_cancel(self._job)
            except Exception:                               # noqa: BLE001
                pass
            self._job = None
        try:
            self.view.destroy()
        except Exception:                                   # noqa: BLE001
            pass
        try:
            self.win.destroy()
        except Exception:                                   # noqa: BLE001
            pass


# ---------------------------------------------------------------- 말풍선
class _Floater(object):
    """도트 머리 위에 떠서 따라다니는 작은 창 (말풍선·입력 말풍선)."""

    def _make_win(self, root, border):
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        try:
            self.win.attributes("-topmost", True)
        except tk.TclError:
            pass
        self.win.configure(bg=border)

    def follow(self):
        self._job = None
        if self.dead:
            return
        if self.until is not None and time.time() >= self.until:
            return self.close()
        try:
            p = self.pet
            self.win.update_idletasks()
            w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
            lift = (getattr(p, "name_h", 0) + 6) if getattr(p, "name_win", None) else 0
            x = int(p.x + getattr(p, "ax", p.fw / 2.0) - w / 2.0)
            y = int(p.y - h - lift - 4)
            sw = self.root.winfo_screenwidth()
            x = max(4, min(x, sw - w - 4))
            y = max(4, y)
            self.win.geometry("+%d+%d" % (x, y))
            PLAT.raise_above(self.win)
        except Exception:                                   # noqa: BLE001
            return self.close()
        self._job = self.root.after(FOLLOW_MS, self.follow)

    def _stop_follow(self):
        self.dead = True
        if self._job is not None:
            try:
                self.root.after_cancel(self._job)
            except Exception:                               # noqa: BLE001
                pass
            self._job = None


class Bubble(_Floater):
    """도트 머리 위의 말풍선. 정한 시간 동안 도트를 따라다니다 사라진다. hint 는 흐린 글씨(알림)."""

    def __init__(self, root, pet, text, ms=BUBBLE_MS, hint=False, icon=None, gift=False):
        self.root = root
        self.pet = pet
        self.dead = False
        self._job = None
        self._make_win(root, U.ACCENT if gift else U.LINE2)
        self.label = tk.Label(self.win, text=text, bg=PAPER, fg=FAINT if hint else INK,
                              font=U.FONT_XS if hint else (U.FONT_B if gift else U.FONT_S),
                              wraplength=U.h(230 if gift else 190), justify="left", padx=8, pady=4)
        if icon is not None:
            self.label.configure(image=icon, compound="left")
            self.label.image = icon
        self.label.pack(padx=2 if gift else 1, pady=2 if gift else 1)
        self.until = time.time() + ms / 1000.0
        self.follow()

    def close(self):
        self._stop_follow()
        try:
            self.win.destroy()
        except Exception:                                   # noqa: BLE001
            pass


class InputBubble(_Floater):
    """내 포켓몬 머리 위의 입력 말풍선. Enter 면 말하고 닫는다(포커스는 그 포켓몬에게), Esc 면 그냥 닫는다.

    다른 데를 눌러 포커스를 잃었을 때 친 것이 없으면 닫는다 (친 것이 있으면 남겨 둔다 - 다시 포켓몬을
    누르면 이어서 친다).
    """

    def __init__(self, visit, pet):
        self.visit, self.pet, self.root = visit, pet, visit.root
        self.dead = False
        self._job = None
        self.until = None
        self._make_win(self.root, U.ACCENT)
        box = tk.Frame(self.win, bg=PAPER)
        box.pack(padx=1, pady=1)
        self.var = tk.StringVar()
        self.var.trace_add("write", self._trim)
        self.entry = tk.Entry(box, textvariable=self.var, width=24, font=U.FONT_S, bg=PAPER, fg=INK,
                              insertbackground=INK, relief="flat", bd=0, highlightthickness=0)
        self.entry.pack(fill="x", padx=8, pady=(6, 2))
        self.tip = tk.Label(box, text="Enter 말하기 · Esc 닫기\n" + HINT, bg=PAPER, fg=FAINT, font=U.FONT_XS,
                            justify="left", anchor="w", wraplength=U.h(230))
        self.tip.pack(fill="x", padx=8, pady=(0, 5))
        for seq in ("<Return>", "<KP_Enter>"):
            self.entry.bind(seq, self.send)
        self.entry.bind("<Escape>", lambda _e: self.close(refocus=True) or "break")
        self.win.bind("<Escape>", lambda _e: self.close(refocus=True) or "break")
        self.entry.bind("<FocusOut>", self._lost)
        self.follow()
        self.focus()
        self.root.after(60, self._focus_again)       # 윈도우는 새 창이 뜬 바로 그때 포커스를 안 주기도 한다

    def _trim(self, *_a):
        t = self.var.get()
        if len(t) > SAY_MAX:
            self.var.set(t[:SAY_MAX])

    def focus(self):
        if self.dead:
            return
        try:
            PLAT.take_keys(self.win)
            self.entry.focus_set()
            self.entry.icursor("end")
        except tk.TclError:
            pass

    def _focus_again(self):
        if self.dead:
            return
        try:
            if self.root.focus_get() is not self.entry:
                self.entry.focus_force()
        except Exception:                                   # noqa: BLE001
            pass

    def type_in(self, ch):
        """포켓몬 창으로 온 글자를 받아 넣는다 (Visit.pet_typed)."""
        if self.dead:
            return
        try:
            self.entry.insert("insert", ch)
        except tk.TclError:
            pass

    def backspace(self):
        if self.dead:
            return
        try:
            i = self.entry.index("insert")
            if i > 0:
                self.entry.delete(i - 1)
        except tk.TclError:
            pass

    def send(self, _e=None):
        text = self.var.get()
        got = parse(text)
        if got is None:
            self.close(refocus=True)
            return "break"
        if got[0] == "bad":
            self.tip.configure(text="그런 명령은 없어요\n" + HINT, fg=U.DANGER)
            return "break"
        self.close(refocus=True)
        self.visit.say(text, self.pet)
        return "break"

    def _lost(self, _e=None):
        def check():
            if self.dead:
                return
            try:
                f = self.root.focus_get()
            except Exception:                               # noqa: BLE001
                f = None
            mine = f is not None and (str(f) == str(self.win) or str(f).startswith(str(self.win) + "."))
            if not mine and not self.var.get().strip():
                self.close()
        self.root.after(200, check)

    def close(self, refocus=False):
        if self.dead:
            return
        self._stop_follow()
        try:
            PLAT.drop_keys(self.win)
        except Exception:                                   # noqa: BLE001
            pass
        try:
            self.win.destroy()
        except Exception:                                   # noqa: BLE001
            pass
        if self.visit.input is self:
            self.visit.input = None
        if refocus:
            self.visit.focus_pet(self.pet)


# ---------------------------------------------------------------- 놀러 가기
class Visit(object):
    """놀러 가기 하나를 맡는다. 앱에 하나 있고, 로그인해 있는 동안 소켓을 붙여 둔다."""

    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.sock = None
        self.v = None                 # 지금 연결된 놀러 가기 (서버의 view)
        self.role = None              # "host" / "guest"
        self.mirrors = {}             # 손님: {주인의 포켓몬 번호: FriendPet}
        self.visitor = None           # 주인: 놀러 온 포켓몬 (VisitPet)
        self.lead = None              # 손님: 내가 보낸 포켓몬 (내 도트 그대로)
        self.host_lead = None         # 손님: 주인의 파티 맨 앞 번호 (말한 포켓몬을 모를 때 그 위에)
        self._saved = None            # 손님: 내 도트를 되돌릴 것
        self._hidden = []             # 손님: 잠시 감춘 내 도트·알
        self._pending = set()         # 받는 중인 도트 (번호, 색)
        self._failed = {}             # {(번호, 색): 못 받은 때} - FETCH_RETRY 동안 다시 안 받는다
        self._party = None            # 손님: 늦게 받은 도트를 만든 뒤 다시 깔 마지막 파티
        self._sent_party = None       # 주인: 마지막으로 보낸 파티
        self._job = None
        self._sent_look = None
        self._talk_at = 0.0           # 마지막으로 말·동작을 보낸 때
        self._outro = None            # 손님: 걸어 나간 뒤에 할 일 (내 도트 되살리기)
        self._home = None             # 손님: 집으로 걸어 들어오는 중인 (도트, 원래 battling)
        self._leaving = []            # 걸어 나가는 중인 남의 도트 (다 나가면 치운다)
        self._keyed = set()           # 글자를 받게 열어 준 창 (끝나면 닫는다)
        self.bubbles = {}             # {id(도트): Bubble}
        self.input = None             # 입력 말풍선 (하나만)
        self.bundle_objs = {}         # {보따리 번호: BundleObj} - 두 화면 모두 보인다
        self._tips = {}               # {보따리 번호: Bubble} - 마우스를 올리면 뜨는 안내
        self._claims_told = set()     # '받았다' 를 이미 띄운 보따리 (응답과 소켓이 둘 다 온다)

    # ---------------- 소켓 ----------------
    def start(self):
        if self.sock is None:
            try:
                self.sock = make_socket(self.app, self.on_event)
            except Exception:                               # noqa: BLE001
                self.sock = None
        return self

    def stop(self):
        self.leave(None, tell=False, walk=False)
        self._finish_outro()
        self._settle_home()
        for p in list(self._leaving):
            self._drop_pet(p)
        self._leaving = []
        sock, self.sock = self.sock, None
        if sock is not None:
            try:
                sock.stop()
            except Exception:                               # noqa: BLE001
                pass

    @property
    def active(self):
        return self.v is not None

    @property
    def guest(self):
        return self.role == "guest"

    def send(self, obj):
        return bool(self.sock is not None and self.sock.send(obj))

    def on_event(self, ev):
        t = (ev or {}).get("t")
        try:
            if t == "visit":
                self.enter(ev.get("visit") or {})
            elif t == "end":
                if self.v is not None and (ev.get("id") in (None, self.v.get("id"))):
                    self.leave(ev.get("text"), returned=ev.get("returned"))
            elif not self.active:
                return
            elif t == "party" and self.guest:
                self.apply_party(ev.get("party") or [], ev.get("lead"))
            elif t == "say":
                self.heard(ev.get("text") or "", ev.get("pet"))
            elif t == "act":
                self.do_act(self.partner_pet(ev.get("pet")), ev.get("act"))
            elif t == "look" and not self.guest:
                self.visitor_look(ev.get("look"))
            elif t == "bundles":
                if "canGive" in ev and self.v is not None:
                    self.v["canGive"] = ev.get("canGive")
                self.set_bundles(ev.get("bundles") or [], ev.get("carry"))
            elif t == "claimed":
                self.claimed(ev.get("bundle") or {}, ev.get("from"), ev.get("by"))
            elif t == "closed":
                config.log("친구 채팅 연결이 잠시 끊겼습니다. 다시 붙는 중...")
        except Exception as e:                              # noqa: BLE001
            import traceback
            config.log("놀러 가기 오류 (%s): %s\n%s" % (t, e, traceback.format_exc()))

    # ---------------- 보내기 ----------------
    def can_go(self):
        """지금 놀러 갈 수 있나. 못 가면 그 까닭."""
        app = self.app
        if self.active:
            return "이미 친구와 연결돼 있습니다."
        if getattr(app, "battle", None) or getattr(app, "arena", None):
            return "배틀 중에는 놀러 갈 수 없습니다."
        if self.sock is None:
            return "이 PC 에서는 친구 채팅을 쓸 수 없습니다 (연결 라이브러리가 없습니다)."
        if not getattr(self.sock, "connected", False):
            return "서버와 연결되는 중입니다. 잠시 뒤에 다시 해 주세요."
        return None

    def my_lead_pet(self):
        """내 파티 맨 앞 (바탕화면, 자리 순)."""
        ov = self.app.overlay
        if not ov or not ov.pets:
            return None
        return lead_of(ov.pets.values())

    def partner_id(self):
        v = self.v or {}
        return v.get("host") if self.guest else v.get("guest")

    def go(self, friend, items, done=None):
        """친구에게 놀러 간다. items = [{"id", "count"}] (들고 가는 것). 끝나면 done(r, err)."""
        why = self.can_go()
        if why:
            if done:
                done(None, why)
            return
        lead = self.my_lead_pet()
        look = getattr(lead, "look", None) if lead is not None else None
        look = look if (look or 0) >= 10000 else 0

        def finish(r, err):
            if not err and r and r.get("visit"):
                self.enter(r["visit"])
            if done:
                done(r, err)
        run_async(self.root, lambda: self.app.api.visit_start(friend, items, look), finish)

    def end_visit(self):
        """끝낸다 (손님은 돌아오기, 주인은 돌려보내기). 서버가 둘 다에게 '끝' 을 민다."""
        if not self.active:
            return

        def done(_r, err):
            if err:
                self.leave("연결을 끝냈습니다.")
        run_async(self.root, self.app.api.visit_end, done)
        self.leave("돌아왔습니다." if self.guest else "친구의 포켓몬을 돌려보냈습니다.")

    # ---------------- 들어가고 나오기 ----------------
    def enter(self, v):
        if not v or not v.get("id"):
            return
        if self.v is not None and self.v.get("id") == v.get("id"):
            self.v = v                    # 다시 붙었다 - 같은 놀러 가기
            if self.guest and v.get("party") is not None:
                self.apply_party(v["party"], v.get("hostLead"))
            self.set_bundles(v.get("bundles") or [], v.get("carry"), fall=False)
            return
        if self.v is not None:
            self.leave(None, tell=False, walk=False)
        self._finish_outro()              # 걸어 나가던 것은 바로 마무리한다
        self._settle_home()
        self.v, self.role = v, v.get("role")
        if self.guest:
            self._enter_guest(v)
            self.app.notify("%s 님의 집에 놀러 왔다!" % v.get("partner"))
        else:
            self._enter_host(v)
            carry = items_text(v.get("carry"))
            self.app.notify("%s 님의 포켓몬이 놀러 왔다!%s" % (
                v.get("partner"), (" 들고 온 도구: " + carry) if carry else ""))
        if v.get("bundles"):
            self.set_bundles(v["bundles"], v.get("carry"), fall=False)
        vid = v.get("id")
        self.root.after(1800, lambda: self._hint(vid))

    def _hint(self, vid):
        """어떻게 말하는지 내 포켓몬 머리 위에 한 번 알려 준다."""
        if self.v is None or self.v.get("id") != vid:
            return
        self.show_bubble(self.my_pet(), GUEST_HINT if self.guest else HOST_HINT, ms=HINT_MS, hint=True)

    def leave(self, text=None, tell=True, walk=True, returned=None):
        """끝났다. walk 면 걸어 나가는 연출을 하고(손님은 그 뒤에 집으로 걸어 들어온다), 아니면 바로 치운다.

        returned = 안 받아서 손님에게 돌아간 보따리의 도구 (서버가 '끝' 에 실어 준다).
        """
        if self.v is None:
            return
        role = self.role
        partner = self.v.get("partner") or "친구"
        self.v, self.role = None, None
        if self._job is not None:
            try:
                self.root.after_cancel(self._job)
            except Exception:                               # noqa: BLE001
                pass
            self._job = None
        if self.input is not None:
            self.input.close()
        for b in list(self.bubbles.values()):
            b.close()
        self.bubbles = {}
        self.set_bundles([], None)
        for w in list(self._keyed):
            try:
                PLAT.drop_keys(w)
            except Exception:                               # noqa: BLE001
                pass
        self._keyed = set()
        ov = self.app.overlay
        if role == "guest":
            for p in list(self.mirrors.values()):
                self._drop_pet(p)
            self.mirrors = {}
            lead = self.lead
            if walk and lead is not None and ov is not None and lead in ov.pets.values():
                self._end_act(lead)
                self._outro = lambda: self._restore_guest(ov, home=True)
                self._walk(lead, self._offstage(lead), lead.y, done=self._finish_outro)
            else:
                self._restore_guest(ov)
        elif self.visitor is not None:
            vp, self.visitor = self.visitor, None
            if walk:
                self._end_act(vp)
                self._leaving.append(vp)
                self._walk(vp, self._offstage(vp), vp.y, done=lambda: self._gone(vp))
            else:
                self._drop_pet(vp)
            for p in (list(ov.pets.values()) if ov is not None else []):
                self._end_act(p)
        self._party = None
        self._sent_party = None
        self._sent_look = None
        self._claims_told = set()
        if tell and text:
            self.app.notify(text)
        if returned and role == "guest":
            back = items_text(returned)
            self.app.notify("%s 님이 안 받은 보따리를 돌려받았다: %s" % (partner, back))
            self.show_bubble(self.lead or self._home_pet(), "보따리를 돌려받았다\n" + back, ms=HINT_MS, hint=True)
            try:
                self.app.request_sync()
            except Exception:                               # noqa: BLE001
                pass

    def _home_pet(self):
        return self._home[0] if self._home else None

    def _gone(self, p):
        if p in self._leaving:
            self._leaving.remove(p)
        self._drop_pet(p)

    def _finish_outro(self):
        fn, self._outro = self._outro, None
        if fn is not None:
            lead = self.lead
            st = getattr(lead, "_stroll", None)
            if st is not None:
                st.cancel()
            fn()

    def _drop_pet(self, p):
        ov = self.app.overlay
        st = getattr(p, "_stroll", None)
        if st is not None:
            st.cancel()
        b = self.bubbles.pop(id(p), None)
        if b is not None:
            b.close()
        try:
            if ov is not None and p in ov.extra:
                ov.extra.remove(p)
        except Exception:                                   # noqa: BLE001
            pass
        try:
            p.destroy()
        except Exception:                                   # noqa: BLE001
            pass

    def _corner(self, pet):
        """오른쪽 아래 - 놀러 간 포켓몬이 서는 자리 (왼쪽 위 기준)."""
        x1, y1, x2, y2 = self.app.overlay.area()
        m = self.app.overlay.settings.get("areaMargin", 4)
        return x2 - pet.fw - m - U.h(8), y2 - pet.fh - m

    def _offstage(self, pet):
        """화면 오른쪽 밖 (걸어 들어오고 나가는 곳) - 활동 영역이 있는 화면의 오른쪽 끝 너머."""
        ov = self.app.overlay
        x1, y1, x2, y2 = ov.area()
        right = x2
        try:
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            for sx1, sy1, sx2, sy2 in PLAT.screens(sw, sh):
                if sx1 <= x2 - 1 < sx2 and sy1 <= y2 - 1 < sy2:
                    right = max(right, sx2)
                    break
            else:
                right = max(right, sw if x2 <= sw else x2)
        except Exception:                                   # noqa: BLE001
            pass
        return right + 2

    def _walk(self, pet, tx, ty, done=None):
        """들어오고 나가는 걸음 (평소보다 조금 빠르게)."""
        s = self.app.overlay.settings
        fps = max(1, int(s.get("fps") or 30))
        speed = float(s.get("walkSpeed") or 1.2) * fps * STROLL
        return Stroll(self.root, pet, tx, ty, speed, done=done, tick_ms=int(1000 / fps))

    # ---- 손님 ----
    def _enter_guest(self, v):
        app = self.app
        ov = app.overlay
        if app.wild is not None:
            try:
                app.wild.stop()
            except Exception:                               # noqa: BLE001
                pass
        if ov is None:
            return
        lead = self._hide_mine(ov, v)
        if lead is not None:
            self._saved = (lead.x, lead.y, lead.battling, lead.state)
            lead.battling = True
            try:
                lead.wake(show=False)
                cx, cy = self._corner(lead)
                lead.x, lead.y = self._offstage(lead), cy       # 친구 집 오른쪽 밖에서 걸어 들어온다
                lead.state = "idle"
                lead.place()
                self._walk(lead, cx, cy)
            except Exception:                               # noqa: BLE001
                pass
            self._arm(lead)
        self._sent_look = getattr(lead, "look", None)
        if v.get("party"):
            self.apply_party(v["party"], v.get("hostLead"))
        self._job = self.root.after(LOOK_MS, self._guest_tick)

    def _hide_mine(self, ov, v):
        """손님: 내 도트(보낸 포켓몬 말고)와 알을 감추고 동기화를 잠근다. 보낸 포켓몬을 돌려준다."""
        ov.locked = True              # 이제부터 동기화가 내 도트를 다시 깔지 않는다
        lead = ov.pets.get(((v.get("mon") or {}).get("id")))
        self.lead = lead
        self._hidden = []
        for p in list(ov.pets.values()) + list(ov.eggs.values()):
            if p is lead:
                continue
            for w in (p.win, getattr(p, "name_win", None)):
                if w is None:
                    continue
                try:
                    w.withdraw()
                except Exception:                           # noqa: BLE001
                    pass
            self._hidden.append(p)
            try:
                p.hide_tip()
            except Exception:                               # noqa: BLE001
                pass
        return lead

    def overlay_rebuilt(self):
        """도트를 전부 다시 만들었다 (포켓몬 크기 바꾸기 - Overlay.refresh_visuals). 놀러 가기 화면을 다시 세운다.

        다시 만들면 남의 도트(extra)가 지워지고, 잠금이 풀리고, 감춰 둔 내 포켓몬이 새 도트로 다시 나온다.
        보낸 포켓몬도 새 도트라 예전 것을 붙들고 있으면 안 된다 (10/15 사용자 제보: 놀러 간 채로 크기를 바꾸면
        연결이 끊긴 것처럼 망가졌다). 걷는 연출은 건너뛰고 제자리에 바로 세운다.
        """
        ov = self.app.overlay
        if ov is None:
            return
        if self.input is not None:
            self.input.close()
        for b in list(self.bubbles.values()):
            b.close()
        self.bubbles = {}
        self._leaving = []                                   # 걸어 나가던 남의 도트는 이미 지워졌다
        self._finish_outro()                                 # 걸어 나가던 손님은 바로 집으로
        self._home = None                                    # 집으로 걸어 들어오던 도트도 새 것이다
        self._keyed = set()
        self.mirrors = {}
        self.visitor = None
        if not self.active:
            return
        if self.guest:
            lead = self._hide_mine(ov, self.v)
            if lead is not None:
                lead.battling = True
                lead.state = "idle"
                try:
                    lead.wake(show=False)
                    lead.x, lead.y = self._corner(lead)
                    lead.place()
                except Exception:                           # noqa: BLE001
                    pass
                self._arm(lead)
            if self._party:
                self.apply_party(*self._party)
        else:
            self._make_visitor(walk=False)
            for p in self.speakers():
                self._arm(p)
        for bid in list(self.bundle_objs):                   # 크기가 바뀌었다 - 보따리도 그 크기로
            self._drop_bundle(bid)
        self.set_bundles((self.v or {}).get("bundles") or [], None, fall=False)

    def _restore_guest(self, ov, home=False):
        """내 도트를 되살린다. home 이면 보낸 포켓몬이 화면 오른쪽 밖에서 걸어 들어온다."""
        app = self.app
        lead, saved = self.lead, self._saved
        self.lead, self._saved = None, None
        if lead is not None and saved:
            try:
                self._end_act(lead)
                st = getattr(lead, "_stroll", None)
                if st is not None:
                    st.cancel()
                lead.x, lead.y, battling, lead.state = saved
                lead.clamp()
                if home and ov is not None and lead in ov.pets.values():
                    cx, cy = self._corner(lead)
                    lead.x, lead.y = self._offstage(lead), cy
                    lead.state = "idle"
                    lead.place()
                    self._home = (lead, battling)
                    self._walk(lead, cx, cy, done=self._settle_home)
                else:
                    lead.battling = battling
                    lead.place()
            except Exception:                               # noqa: BLE001
                pass
        hidden_all = bool(getattr(ov, "hidden", False))
        for p in self._hidden:
            if hidden_all:
                continue                  # 사용자가 도트를 숨겨 둔 중이면 그대로
            try:
                PLAT.show_again(p.win)
            except Exception:                               # noqa: BLE001
                pass
        self._hidden = []
        if ov is not None:
            ov.locked = False
            try:
                ov.apply_names()
            except Exception:                               # noqa: BLE001
                pass
        try:
            app.request_sync()
        except Exception:                                   # noqa: BLE001
            pass
        if app.wild is not None:
            try:
                app.wild.start()
            except Exception:                               # noqa: BLE001
                pass

    def _settle_home(self):
        """집으로 걸어 들어온 포켓몬을 풀어 준다 (다시 스스로 돌아다닌다)."""
        got, self._home = self._home, None
        if got is None:
            return
        lead, battling = got
        st = getattr(lead, "_stroll", None)
        if st is not None:
            st.cancel()
        lead.battling = battling
        lead.state = "idle"
        try:
            lead.clamp()
            lead.place()
        except Exception:                                   # noqa: BLE001
            pass

    def _guest_tick(self):
        """손님: 보낸 포켓몬의 모습(메가진화)이 바뀌었으면 알린다."""
        self._job = None
        if not self.guest:
            return
        lead = self.lead
        look = getattr(lead, "look", None) if lead is not None else None
        look = look if (look or 0) >= 10000 else None
        if look != self._sent_look and not getattr(lead, "evolving", False):
            if self.send({"t": "look", "look": look or 0}):
                self._sent_look = look
        self._job = self.root.after(LOOK_MS, self._guest_tick)

    def apply_party(self, party, lead=None):
        """손님: 주인의 파티를 받았다. 없는 도트는 만들고(도트를 먼저 받는다), 빠진 것은 치우고,
        모습이 바뀐 것은 메가진화 연출로 갈아 입힌다. 자리는 손대지 않는다 - 스스로 돌아다닌다."""
        ov = self.app.overlay
        if ov is None:
            return
        self.host_lead = lead
        self._party = (party, lead)
        seen = set()
        want_fetch = []
        for p in party:
            pid = p.get("id")
            seen.add(pid)
            mon = pet_mon(p, -1000000 - int(pid or 0))
            pet = self.mirrors.get(pid)
            if pet is not None and (bool(pet.mon.get("shiny")) != mon["shiny"]
                                    or (pet.mon.get("tint") or None) != (mon.get("tint") or None)):
                self._drop_pet(self.mirrors.pop(pid))       # 색이 바뀌었다 - 새로 만든다
                pet = None
            if pet is None:
                if not self._have_sprite(mon):
                    want_fetch.append(mon)
                    continue
                pet = ov.make(mon, cls=FriendPet)           # 메가 모습 도트가 없으면 원래 모습으로 선다
                if pet is None:
                    continue
                ov.extra.append(pet)
                self.mirrors[pid] = pet
                if not self._has(look_num(mon), skin_of(mon)):
                    want_fetch.append(mon)                  # 메가 모습은 받아서 나중에 갈아 입힌다
                continue
            want = look_num(mon)
            if (want != pet.look and not getattr(pet, "evolving", False)
                    and self._has(want, skin_of(mon))):
                self._mega_swap(pet, mon)
            elif want != pet.look and not self._has(want, skin_of(mon)):
                want_fetch.append(mon)
            info = pet.mon.get("info") or {}
            if (info.get("name"), info.get("level")) != (mon["info"]["name"], mon["info"]["level"]):
                pet.mon = dict(pet.mon, info=dict(info, name=mon["info"]["name"], level=mon["info"]["level"]))
                pet.refresh_nameplate()           # 글자가 바뀌면 폭도 바뀐다 - 다시 재서 가운데에
        for pid in [k for k in self.mirrors if k not in seen]:
            self._drop_pet(self.mirrors.pop(pid))
        if want_fetch:
            self._fetch(want_fetch)

    def _has(self, n, sh):
        """그 번호·색의 도트(걷는 도트나 배틀 도트)가 이 PC 에 있나."""
        ov = self.app.overlay
        return bool(n) and bool(ov.walks.get(walk_cache.key(n, sh)) or ov.walks.get(n)
                                or ov.paths.get((n, sh)) or ov.paths.get((n, False)))

    def _have_sprite(self, mon):
        """세울 수 있나: 지금 모습(메가) 도트가 있거나, 없어도 원래 모습 도트가 있으면 (Overlay.make 가 대신 쓴다)."""
        sh = skin_of(mon)
        return self._has(look_num(mon), sh) or self._has(mon.get("num"), sh)

    def _fetch(self, mons):
        """남의 도트를 받아 둔다 (일하는 스레드). 다 받으면 마지막 파티를 다시 깐다."""
        want = []
        now = time.time()
        for m in mons:
            for n in (look_num(m), m.get("num")):
                k = (n, skin_of(m))
                if (n and k not in self._pending and k not in want and not self._has(*k)
                        and now - self._failed.get(k, 0) > FETCH_RETRY):
                    want.append(k)
        if not want:
            return
        self._pending.update(want)
        api = self.app.api

        def work():
            paths = sprite_cache.ensure_many(api, want)
            walks = walk_cache.ensure_many(api, want)
            return paths, walks

        def done(r, err):
            self._pending.difference_update(want)
            ov = self.app.overlay
            if err or not r or ov is None:
                return
            paths, walks = r
            got_p = dict((k, v) for k, v in (paths or {}).items() if v)
            got_w = dict((k, v) for k, v in (walks or {}).items() if v and v[0])
            ov.paths.update(got_p)
            ov.walks.update(got_w)
            missed = [k for k in want if k not in got_p and k not in got_w]
            for k in missed:
                self._failed[k] = time.time()               # 다시 깔아도 또 못 받는다 - 한동안 다시 안 받는다
            if len(missed) == len(want):
                return                                      # 새로 생긴 것이 없다 (끝없이 다시 받지 않는다)
            try:
                self.app._prefetch_anims(mons)        # 자기·앉기 같은 동작도
            except Exception:                               # noqa: BLE001
                pass
            if self.guest and self._party:
                self.apply_party(*self._party)
            elif not self.guest and self.active:
                if self.visitor is None:
                    self._make_visitor()
                else:
                    self.visitor_look((self.v or {}).get("look"))
        run_async(self.root, work, done)

    def _mega_swap(self, pet, mon):
        """남의 도트의 모습(메가진화)이 바뀌었다 - 메가진화 연출과 함께 갈아 입힌다."""
        from . import mega_fx
        want = look_num(mon)
        revert = not mon.get("lookNum")
        pet.mon = dict(pet.mon, lookNum=mon.get("lookNum"))
        if revert:
            pet.mon.pop("lookNum", None)
        try:
            mega_fx.play(self.app, pet, want, revert=revert)
        except Exception as e:                              # noqa: BLE001
            config.log("놀러 가기 메가 연출 실패: %s" % e)

    # ---- 주인 ----
    def _enter_host(self, v):
        self._make_visitor()
        for p in self.speakers():
            self._arm(p)
        self._job = self.root.after(50, self._host_tick)

    def _make_visitor(self, walk=True):
        ov = self.app.overlay
        v = self.v
        if ov is None or v is None or self.visitor is not None:
            return
        m = dict(v.get("mon") or {})
        m["look"] = v.get("look") or 0
        mon = pet_mon(m, -900000 - int(m.get("id") or 0))
        if not self._have_sprite(mon):
            return self._fetch([mon])
        pet = ov.make(mon, cls=VisitPet)                    # 메가 모습 도트가 없으면 원래 모습으로 선다
        if pet is None:
            return
        if not self._has(look_num(mon), skin_of(mon)):
            self._fetch([mon])                              # 받으면 visitor_look 이 갈아 입힌다
        ov.extra.append(pet)
        cx, cy = self._corner(pet)
        self.visitor = pet
        if not walk:                                       # 다시 세울 때는 제자리에 바로
            pet.x, pet.y = cx, cy
            pet.place()
            return
        pet.x, pet.y = self._offstage(pet), cy             # 화면 오른쪽 밖에서 걸어 들어온다
        pet.place()
        self._walk(pet, cx, cy)

    def visitor_look(self, look):
        pet = self.visitor
        if pet is None:
            if self.v is not None:
                self.v["look"] = look
            return
        mon = dict(pet.mon)
        if look:
            mon["lookNum"] = int(look)
        else:
            mon.pop("lookNum", None)
        if look_num(mon) == pet.look:
            return
        if self._has(look_num(mon), skin_of(mon)):
            self._mega_swap(pet, mon)
        else:
            self._fetch([mon])                              # 도트를 받은 뒤에 갈아 입는다

    def party(self):
        """주인: 내 바탕화면 파티 (서버에 보낼 꼴). 자리는 없다."""
        ov = self.app.overlay
        if ov is None or not ov.pets:
            return []
        lead = self.my_lead_pet()
        out = []
        for p in sorted(ov.pets.values(), key=party_order)[:6]:
            mon = p.mon or {}
            info = mon.get("info") or {}
            out.append({"id": p.id, "num": mon.get("num"), "look": p.look or mon.get("num"),
                        "shiny": bool(mon.get("shiny")), "tint": mon.get("tint"),
                        "name": info.get("name") or mon.get("nickname") or "",
                        "level": info.get("level") or mon.get("level") or 1, "lead": p is lead})
        return out

    def _host_tick(self):
        """주인: 파티가 바뀌었으면 보낸다 (넣고 빼기·메가진화). 새로 나온 내 포켓몬도 말할 수 있게."""
        self._job = None
        if not self.active or self.guest:
            return
        for p in self.speakers():
            self._arm(p)
        if not any(getattr(p, "evolving", False) for p in self.speakers()):
            party = self.party()
            if party != self._sent_party and self.send({"t": "party", "party": party}):
                self._sent_party = party
        self._job = self.root.after(PARTY_MS, self._host_tick)

    # ---------------- 말과 동작 ----------------
    def speakers(self):
        """말할 수 있는 내 포켓몬: 손님은 보낸 포켓몬, 주인은 바탕화면의 내 포켓몬 전부."""
        if not self.active:
            return []
        if self.guest:
            return [self.lead] if self.lead is not None else []
        ov = self.app.overlay
        return list(ov.pets.values()) if ov is not None else []

    def my_pet(self):
        """알림 말풍선이 뜰 내 도트: 손님은 보낸 포켓몬, 주인은 파티 맨 앞."""
        return self.lead if self.guest else self.my_lead_pet()

    def partner_pet(self, pid=None):
        """상대 말풍선이 뜰 도트: 손님에게는 주인이 고른 포켓몬(모르면 맨 앞), 주인에게는 놀러 온 포켓몬."""
        if self.guest:
            return (self.mirrors.get(pid) or self.mirrors.get(self.host_lead)
                    or next(iter(self.mirrors.values()), None))
        return self.visitor

    def _arm(self, pet):
        """내 포켓몬을 누르면 포커스를 받고, Enter 를 치면 입력 말풍선이 뜨게 한다 (도트마다 한 번만 건다).

        묶는 것은 앱의 지금 Visit 이다 - 다시 로그인하면 Visit 이 새로 생긴다.
        """
        if pet is None or getattr(pet, "_visit_armed", False):
            return
        app = self.app

        def click(_e, p=pet):
            vis = getattr(app, "visit", None)
            if vis is not None:
                vis.on_pet_click(p)

        def key(_e, p=pet):
            vis = getattr(app, "visit", None)
            if vis is not None:
                vis.pet_enter(p)
            return "break"

        def esc(_e, p=pet):
            vis = getattr(app, "visit", None)
            if vis is not None:
                vis.pet_escape(p)
            return "break"

        def typed(e, p=pet):
            vis = getattr(app, "visit", None)
            if vis is not None and vis.pet_typed(p, e.keysym, e.char):
                return "break"
            return None
        try:
            pet.label.bind("<Button-1>", click, add="+")
            for seq in ("<Return>", "<KP_Enter>"):
                pet.win.bind(seq, key)
            pet.win.bind("<Escape>", esc)
            pet.win.bind("<Key>", typed)
            pet._visit_armed = True
        except tk.TclError:
            pass

    # ---- 글자가 입력 말풍선이 아니라 포켓몬 창으로 왔을 때 ----
    # 윈도우는 앞에 나와 있지 않은 프로그램이 새 창에 글자 포커스를 주는 것을 막는다. 그러면 말풍선이 떠도
    # 글자는 방금 누른 포켓몬 창으로 간다 (CI 의 윈도우 러너에서 Esc 가 안 먹어 드러났다). 그때는 포켓몬 창이
    # 받은 것을 말풍선 일로 읽는다: Enter = 보내기, Esc = 닫기, 글자 = 말풍선 칸에 넣기.
    def _input_of(self, pet):
        inp = self.input
        return inp if (inp is not None and not inp.dead and inp.pet is pet) else None

    def pet_enter(self, pet):
        inp = self._input_of(pet)
        if inp is not None:
            return inp.send()
        return self.open_input(pet)

    def pet_escape(self, pet):
        inp = self._input_of(pet)
        if inp is not None:
            inp.close(refocus=True)
            return True
        return False

    def pet_typed(self, pet, keysym, char):
        inp = self._input_of(pet)
        if inp is None:
            return False
        if keysym == "BackSpace":
            inp.backspace()
            return True
        if char and char.isprintable():
            inp.type_in(char)
            return True
        return False

    def on_pet_click(self, pet):
        """내 포켓몬을 눌렀다: 포커스를 준다 (입력 말풍선이 그 포켓몬 것이면 그리로)."""
        if pet not in self.speakers():
            return
        inp = self.input
        if inp is not None and not inp.dead and inp.pet is pet:
            return inp.focus()
        self.focus_pet(pet)

    def focus_pet(self, pet):
        if not self.active or pet is None:
            return
        try:
            PLAT.take_keys(pet.win)
            self._keyed.add(pet.win)
        except Exception:                                   # noqa: BLE001
            pass

    def open_input(self, pet):
        """그 포켓몬 머리 위에 입력 말풍선을 연다 (Enter · 우클릭 '말하기')."""
        if pet is None or pet not in self.speakers():
            return None
        inp = self.input
        if inp is not None and not inp.dead:
            if inp.pet is pet:
                inp.focus()
                return inp
            inp.close()
        old = self.bubbles.pop(id(pet), None)
        if old is not None:
            old.close()
        try:
            self.input = InputBubble(self, pet)
        except Exception as e:                              # noqa: BLE001
            import traceback
            config.log("입력 말풍선을 못 열었습니다: %s\n%s" % (e, traceback.format_exc()))
            self.input = None
        return self.input

    def say(self, text, pet=None):
        """말하거나('/' 명령이면) 동작한다. 내 화면에 띄우고 상대에게 보낸다."""
        pet = pet if pet is not None else self.my_pet()
        got = parse(text)
        if got is None or pet is None:
            return False
        kind, val = got
        if kind == "bad":
            self.show_bubble(pet, "그런 명령은 없어요. " + HINT, hint=True)
            return False
        wire = {"pet": pet.id} if (not self.guest and (pet.id or 0) > 0) else {}
        if kind == "act":
            self.do_act(pet, val)
            self._talk(dict({"t": "act", "act": val}, **wire))
            return True
        self.show_bubble(pet, val)
        self._talk(dict({"t": "say", "text": val}, **wire))
        return True

    def _talk(self, obj):
        """말·동작을 보낸다. 너무 빨리 이어 치면 조금 기다렸다 보낸다 (서버가 버리지 않게)."""
        now = time.time()
        wait = self._talk_at + SAY_GAP - now
        if wait <= 0:
            self._talk_at = now
            return self.send(obj)
        self._talk_at = now + wait
        vid = (self.v or {}).get("id")

        def later():
            if self.v is not None and self.v.get("id") == vid:
                self.send(obj)
        self.root.after(int(wait * 1000) + 10, later)
        return True

    def heard(self, text, pid=None):
        self.show_bubble(self.partner_pet(pid), text)

    def show_bubble(self, pet, text, ms=BUBBLE_MS, hint=False, gift=False, icon=None):
        if pet is None or not text:
            return None
        inp = self.input
        if inp is not None and not inp.dead and inp.pet is pet and hint:
            return None                   # 치는 중인 사람에게 알림은 덮지 않는다
        old = self.bubbles.pop(id(pet), None)
        if old is not None:
            old.close()
        try:
            b = Bubble(self.root, pet, text, ms=ms, hint=hint, gift=gift, icon=icon)
        except Exception as e:                              # noqa: BLE001
            config.log("말풍선 실패: %s" % e)
            return None
        self.bubbles[id(pet)] = b
        return b

    def _hold(self, pet):
        """동작 동안 스스로 안 움직이게 한다 (원래 값을 기억해 둔다).

        자고 있었으면 먼저 깨운다 - 안 그러면 다음 프레임에 Pet.update 가 깨우면서 걷기 그림으로 덮는다.
        """
        try:
            pet.wake(show=False)
        except Exception:                                   # noqa: BLE001
            pass
        if not hasattr(pet, "_visit_prev"):
            pet._visit_prev = pet.battling
        pet.battling = True
        token = object()
        pet._visit_act = token
        return token

    def _end_act(self, pet, token=None):
        """동작을 끝내고 원래대로 (token 을 주면 그 동작일 때만)."""
        if pet is None or not hasattr(pet, "_visit_act"):
            return
        if token is not None and getattr(pet, "_visit_act", None) is not token:
            return
        pet._visit_act = None
        if hasattr(pet, "_visit_prev"):
            pet.battling = pet._visit_prev
            del pet._visit_prev
        try:
            pet.play("Walk" if pet.state == "walk" else pet.rest_anim())
        except Exception:                                   # noqa: BLE001
            pass

    def do_act(self, pet, act):
        """그 도트가 동작을 한다 (/춤 /자기 ...). 상대 화면에서도 같은 동작을 부른다."""
        if pet is None or act not in ACT_KR:
            return False
        if act == "wake":
            self._end_act(pet)
            return True
        token = self._hold(pet)
        later = self.root.after

        def end():
            self._end_act(pet, token)

        if act in POSES:
            name = next((n for n in POSES[act] if pet.anim_for(n) is not None), None)
            if act == "faint" and pet.anim_for("Faint") is not None:
                pet.play("Faint", once=True, then=lambda: name and pet.play(name))
            elif name:
                pet.play(name)
            later(POSE_MS, end)
            return True
        if act in ("hop", "hello"):
            if act == "hello":
                self.show_bubble(pet, "안녕!")
            n = 2 if act == "hop" else 1

            def hop(i=0):
                if getattr(pet, "_visit_act", None) is not token:
                    return
                if i >= n:
                    return later(200, end)
                try:
                    if pet.anim_for("Hop") is not None:
                        pet.play("Hop", once=True)
                except Exception:                           # noqa: BLE001
                    return                                  # 그사이 도트가 없어졌다
                later(HOP_GAP + 120, lambda: hop(i + 1))
            hop()
            return True
        # 춤: 좌우로 몸을 돌리며 뛴다
        def step(i=0):
            if getattr(pet, "_visit_act", None) is not token:
                return
            if i >= 8:
                return later(200, end)
            try:
                pet.turn_to(1 if i % 2 == 0 else -1, 0)
                if pet.anim_for("Hop") is not None:
                    pet.play("Hop", once=True)
                else:
                    pet.facing = RIGHT if i % 2 == 0 else LEFT
                    pet.redraw()
            except Exception:                               # noqa: BLE001
                pass
            later(HOP_GAP, lambda: step(i + 1))
        step()
        return True

    # ---------------- 우클릭 메뉴 ----------------
    def end_label(self):
        return "집으로 돌아오기" if self.guest else "%s 님의 포켓몬 돌려보내기" % (self.v or {}).get("partner", "친구")

    def menu_rows(self, pet):
        """내 포켓몬의 우클릭 메뉴에 넣을 줄 (놀러 가기 중일 때만, 말할 수 있는 포켓몬에게)."""
        if pet not in self.speakers():
            return []
        rows = [{"text": "말하기 (Enter)", "command": lambda: self.open_input(pet)}]
        if self.guest:
            v = self.v or {}
            if not v.get("carry"):
                rows.append({"text": "여기에 두기 (들고 온 도구 없음)", "enabled": False})
            elif v.get("canGive") is False:
                rows.append({"text": "여기에 두기 (친구가 오늘 이미 받음)", "enabled": False})
            else:
                rows.append({"text": "여기에 두기...", "command": self.open_drop})
        rows.append({"text": self.end_label(), "command": self.end_visit})
        return rows

    def open_drop(self):
        """'여기에 두기' - 들고 온 것 중 고른 만큼 보따리에 싼다 (가방 모양 창)."""
        if not self.guest:
            return None
        from . import ui_visit
        return ui_visit.DropDialog(self.app)

    # ---------------- 보따리 ----------------
    def _bundle_anchor(self):
        """보따리가 놓이는 곳의 기준 도트: 놀러 간 포켓몬 (주인 화면은 놀러 온 포켓몬, 손님 화면은 내가 보낸 포켓몬)."""
        return self.lead if self.guest else self.visitor

    def _bundle_spot(self, i):
        """i 번째 보따리 자리 (왼쪽 위): 놀러 간 포켓몬의 왼쪽 바닥에 차례로."""
        ov = self.app.overlay
        x1, y1, x2, y2 = ov.area()
        m = ov.settings.get("areaMargin", 4)
        _size, fw, fh = bundle_size(ov)
        anchor = self._bundle_anchor()
        right = self._corner(anchor)[0] if anchor is not None else x2 - m - U.h(70)
        gap = U.h(6)
        return right - gap - (i + 1) * (fw + gap), y2 - fh - m

    def set_bundles(self, bundles, carry=None, fall=True):
        """서버가 준 보따리 목록대로 바탕화면을 맞춘다 (새 것은 머리 위에서 떨어진다, 없어진 것은 치운다)."""
        if carry is not None and self.v is not None:
            self.v["carry"] = carry
        if self.v is not None:
            self.v["bundles"] = list(bundles)
        want = [b for b in bundles if b.get("id") is not None] if self.active else []
        ids = set(b["id"] for b in want)
        for bid in [k for k in self.bundle_objs if k not in ids]:
            self._drop_bundle(bid)
        if self.app.overlay is None:
            return
        anchor = self._bundle_anchor()
        for i, b in enumerate(want):
            obj = self.bundle_objs.get(b["id"])
            x, y = self._bundle_spot(i)
            if obj is None:
                top = (anchor.y + anchor.fh * 0.3) if (fall and anchor is not None) else None
                try:
                    self.bundle_objs[b["id"]] = BundleObj(self, b, x, y, drop_from=top)
                except Exception as e:                      # noqa: BLE001
                    config.log("보따리를 못 띄웠습니다: %s" % e)
            else:
                obj.bundle = b
                obj.move(x, y)

    def _drop_bundle(self, bid):
        obj = self.bundle_objs.pop(bid, None)
        tip = self._tips.pop(bid, None)
        if tip is not None:
            tip.close()
        if obj is not None:
            obj.destroy()

    def bundle_tip(self, obj, on):
        """보따리에 마우스를 올리면: 누구의 무엇인지, 어떻게 받는지."""
        old = self._tips.pop(obj.id, None)
        if old is not None:
            old.close()
        if not on or obj.dead or not self.active:
            return
        what = items_text(obj.bundle.get("items"))
        if self.guest:
            text = "내가 둔 보따리 (%s)\n%s 님이 누르면 받는다" % (what, (self.v or {}).get("partner", "친구"))
        else:
            text = "%s 님의 보따리 (%s)\n눌러서 받기" % (obj.bundle.get("from") or (self.v or {}).get("partner"), what)
        try:
            self._tips[obj.id] = Bubble(self.root, obj, text, ms=8000, hint=True)
        except Exception:                                   # noqa: BLE001
            pass

    def on_bundle_click(self, obj):
        """보따리를 눌렀다: 주인은 받는다, 손님에게는 친구가 받는다고 알려 준다."""
        if not self.active or obj.dead:
            return
        if self.guest:
            return self.bundle_tip(obj, True)
        if obj.pending:
            return
        obj.pending = True
        bid = obj.id

        def done(r, err):
            obj.pending = False
            if err:
                try:
                    self._tips[bid] = Bubble(self.root, obj, getattr(err, "message", None) or str(err), ms=4000,
                                             hint=True)
                except Exception:                           # noqa: BLE001
                    pass
                return
            b = (r or {}).get("bundle") or obj.bundle
            self._drop_bundle(bid)                          # 소켓보다 응답이 먼저 와도 바로 치운다
            self.claimed(b, b.get("from") or (self.v or {}).get("partner"), None)
        run_async(self.root, lambda: self.app.api.visit_claim(bid), done)

    def claimed(self, bundle, giver=None, taker=None):
        """보따리를 받았다 - 주인: 'OO 님에게 ~를 받았다!', 손님: 'OO 님이 보따리를 받았다!'."""
        bid = bundle.get("id")
        if bid in self._claims_told or not self.active:
            return
        self._claims_told.add(bid)
        self._drop_bundle(bid)
        what = items_text(bundle.get("items"))
        first = ((bundle.get("items") or [{}])[0]).get("id")
        icon = item_icons.photo(first, 26) if first else None
        if self.guest:
            text = "%s 님이 보따리를 받았다! (%s)" % (taker or (self.v or {}).get("partner", "친구"), what)
            self.app.notify(text)
            self.show_bubble(self.lead, text, ms=BUBBLE_MS, gift=True, icon=icon)
            return
        text = "%s 님에게 %s를 받았다!" % (giver or (self.v or {}).get("partner", "친구"), what)
        self.app.notify(text)
        self.show_bubble(self.visitor or self.my_lead_pet(), text, ms=BUBBLE_MS + 2000, gift=True, icon=icon)
        try:
            self.app.request_sync()                         # 가방이 늘었다
        except Exception:                                   # noqa: BLE001
            pass

    def open_menu(self, pet, event):
        """남의 포켓몬(친구 포켓몬·놀러 온 포켓몬)의 우클릭 메뉴: 누구 것인지와 끝내기."""
        if not self.active:
            return
        info = (pet.mon or {}).get("info") or {}
        title = "%s 님의 %s" % ((self.v or {}).get("partner", "친구"), info.get("name", "?"))
        rows = [{"text": title, "enabled": False}, None, {"text": self.end_label(), "command": self.end_visit}]
        if not PLAT.NATIVE_MENU:
            U.PopupMenu(self.root, rows, event.x_root, event.y_root, width=230)
            return
        m = tk.Menu(self.root, tearoff=0, bg=U.BG2, fg=U.FG, activebackground=U.BG4, activeforeground=U.FG,
                    bd=0, font=U.FONT_S)
        m.add_command(label=title, state="disabled")
        m.add_separator()
        m.add_command(label=self.end_label(), command=self.end_visit)
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()
