# -*- coding: utf-8 -*-
"""앱이 멈추면 알아채고 강제 종료를 묻는다 (1.13.3).

맥의 '응용 프로그램 강제 종료'(Cmd+Option+Esc) 창에는 Dock 에 뜨는 앱만 나온다. 포스크탑은 켜 두고 잊어버리는
프로그램이라 Dock 에 안 뜬다(LSUIElement, platform_mac.hide_from_dock) - 그래서 멈추면 끌 길이 없어서 전원을
껐다 켜야 하냐는 말까지 나왔다 (2026-10-20). Dock 에 띄우는 대신 앱이 스스로 멈춘 것을 알아챈다 (사용자 결정).

  - 메인 스레드(Tk)가 BEAT_MS 마다 '살아 있음' 을 찍는다. 감시 스레드가 HANG_SEC 넘게 안 찍힌 것을 보면,
  - 그 순간 메인 스레드가 어디서 멈췄는지(파이썬 스택)를 기록에 남기고 서버에도 보낸다 (trouble 'hang') - 원인을 찾는다.
  - 그리고 **앱 바깥에서** 묻는다 (메인 스레드가 멈췄으니 Tk 창은 못 띄운다): 맥은 osascript 대화상자,
    윈도우는 시스템 메시지 상자. [강제 종료] 면 os._exit. [기다리기] 면 REASK_SEC 더 멈춰 있을 때 다시 묻는다.
    묻는 사이에 풀리면(맥) 대화상자를 닫는다.

잘못 묻지 않게:
  - 일부러 기다리는 중은 멈춘 게 아니다 - 오른쪽 클릭 메뉴(윈도우의 tk_popup 은 닫힐 때까지 Tk 시계가 멈춘다),
    확인 · 파일 창(tkinter commondialog). 그때의 스택으로 가린다.
  - 컴퓨터가 잠들었다 깨면 시계가 건너뛴다 (윈도우의 monotonic 은 잠든 시간도 센다). 감시 스레드 자신의 1초 잠이
    SUSPEND_SEC 넘게 걸렸으면 잠들었던 것으로 보고 처음부터 센다.

한계: 파이썬이 통째로 굳는 경우(GIL 을 쥔 채 C 코드에서 멈춤)에는 감시 스레드도 못 돈다 - 그때는 활성 상태 보기로.
"""
import os
import subprocess
import sys
import threading
import time
import traceback

from . import config, trouble

BEAT_MS = 500
HANG_SEC = 15
REASK_SEC = 60
SUSPEND_SEC = 5
TICK = 1.0

MODAL_FUNCS = {"tk_popup"}                                  # 일부러 기다리는 중 (메뉴)
MODAL_FILES = ("commondialog.py", "messagebox.py", "filedialog.py", "simpledialog.py")

TITLE = "포스크탑"
TEXT = ("포스크탑이 %d초 넘게 응답하지 않습니다.\n\n"
        "조금 더 기다리거나, 강제 종료한 뒤 다시 켜 주세요.\n"
        "(멈춘 곳은 고칠 수 있게 개발자에게 전달됩니다)")


def _stack_of(ident):
    frame = sys._current_frames().get(ident)
    return traceback.format_stack(frame) if frame is not None else []


def is_modal(stack_lines):
    """일부러 기다리는 중인가 (메뉴 · 확인 창)."""
    text = "".join(stack_lines)
    return any((" in %s\n" % f) in text for f in MODAL_FUNCS) or any(f in text for f in MODAL_FILES)


# ---------------------------------------------------------------- 앱 바깥에서 묻기
def _ask_mac(text, still_hung):
    """osascript 대화상자. 'kill' / 'wait'. 묻는 사이에 풀리면 대화상자를 닫고 'wait'."""
    esc = text.replace("\\", "\\\\").replace('"', '\\"')
    script = ('display dialog "%s" with title "%s" buttons {"기다리기", "강제 종료"} '
              'default button "기다리기" cancel button "기다리기" with icon caution giving up after 300'
              % (esc, TITLE))
    try:
        p = subprocess.Popen(["osascript", "-e", script], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except Exception:                                       # noqa: BLE001
        return "wait"
    while p.poll() is None:
        if not still_hung():
            p.terminate()
            return "wait"
        time.sleep(0.5)
    out = (p.stdout.read() or b"").decode("utf-8", "replace")
    return "kill" if "강제 종료" in out else "wait"


def _ask_win(text, still_hung):
    """시스템 메시지 상자 (이 스레드에서 돈다 - 멈춘 메인 스레드와 상관없다). [예] = 강제 종료."""
    try:
        import ctypes
        MB_YESNO, MB_ICONWARNING, MB_DEFBUTTON2 = 0x4, 0x30, 0x100
        MB_SYSTEMMODAL, MB_SETFOREGROUND, MB_TOPMOST = 0x1000, 0x10000, 0x40000
        r = ctypes.windll.user32.MessageBoxW(
            None, text + "\n\n[예] 강제 종료    [아니요] 조금 더 기다리기", TITLE,
            MB_YESNO | MB_ICONWARNING | MB_DEFBUTTON2 | MB_SYSTEMMODAL | MB_SETFOREGROUND | MB_TOPMOST)
        return "kill" if r == 6 else "wait"                # IDYES
    except Exception:                                       # noqa: BLE001
        return "wait"


def default_ask(text, still_hung):
    if sys.platform == "darwin":
        return _ask_mac(text, still_hung)
    if sys.platform.startswith("win"):
        return _ask_win(text, still_hung)
    return "wait"


def _hard_exit():
    config.log("멈춘 앱을 강제 종료합니다 (사용자가 골랐다)")
    os._exit(1)


class Watchdog(object):
    """check() 를 TICK 마다 부르는 감시. 검사는 시계 · 묻기 · 끝내기 · 스택을 바꿔 끼워 한 단계씩 돌린다."""

    def __init__(self, app=None, now=time.monotonic, ask=default_ask, exit=_hard_exit, stack=None,
                 hang_sec=HANG_SEC, reask_sec=REASK_SEC, main_ident=None):
        self.app = app
        self.now = now
        self.ask = ask
        self.exit = exit
        self.main_ident = main_ident if main_ident is not None else threading.main_thread().ident
        self.stack = stack or (lambda: _stack_of(self.main_ident))
        self.hang_sec = hang_sec
        self.reask_sec = reask_sec
        self.last_beat = None           # 메인 스레드가 마지막으로 찍은 때 (None = 아직 한 번도)
        self.last_tick = None           # 감시가 마지막으로 돈 때 (잠들었다 깼는지 본다)
        self.asked_at = None            # 이번 멈춤에서 마지막으로 물은 때
        self.reported = False           # 이번 멈춤을 서버에 알렸나
        self.hangs = 0

    def beat(self):
        """메인 스레드가 부른다."""
        self.last_beat = self.now()
        self.asked_at = None
        self.reported = False

    def check(self):
        """감시 스레드가 TICK 마다 부른다. 물었으면 그 답('kill'/'wait'), 아니면 None."""
        t = self.now()
        if self.last_tick is not None and t - self.last_tick > SUSPEND_SEC + TICK:
            self.last_beat = t                              # 잠들었다 깼다 - 처음부터 센다
        self.last_tick = t
        if self.last_beat is None:
            return None                                     # 아직 메인 루프가 안 돌았다
        stalled = t - self.last_beat
        if stalled < self.hang_sec:
            return None
        if self.asked_at is not None and t - self.asked_at < self.reask_sec:
            return None
        lines = self.stack()
        if is_modal(lines):
            self.last_beat = t                              # 메뉴 · 확인 창 - 멈춘 게 아니다
            return None
        if not self.reported:
            self.reported = True
            self.hangs += 1
            where = "".join(lines[-12:])
            config.log("앱이 %d초째 응답 없음 - 메인 스레드 위치:\n%s" % (stalled, where))
            try:
                trouble.send(self.app, "hang", None, "앱이 %d초 넘게 응답 없음" % self.hang_sec, where)
            except Exception:                               # noqa: BLE001
                pass
        self.asked_at = t
        start = self.last_beat
        answer = self.ask(TEXT % self.hang_sec, lambda: self.last_beat == start)
        if answer == "kill":
            self.exit()
        else:
            self.asked_at = self.now()
        return answer


def start(root, app):
    """메인 루프를 돌기 직전에 부른다. 맥 · 윈도우에서만."""
    if os.environ.get("POKET_NO_WATCHDOG") or not (sys.platform == "darwin" or sys.platform.startswith("win")):
        return None
    dog = Watchdog(app)

    def beat():
        dog.beat()
        try:
            root.after(BEAT_MS, beat)
        except Exception:                                   # noqa: BLE001
            pass

    def loop():
        while True:
            time.sleep(TICK)
            try:
                dog.check()
            except Exception as e:                          # noqa: BLE001
                config.log("멈춤 감시 오류: %s" % e)

    root.after(BEAT_MS, beat)
    threading.Thread(target=loop, name="poket-watchdog", daemon=True).start()
    return dog
