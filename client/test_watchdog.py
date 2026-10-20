# -*- coding: utf-8 -*-
"""앱이 멈추면 알아채고 강제 종료를 묻는다 (1.13.3, watchdog.py).

    python client/test_watchdog.py

맥의 '응용 프로그램 강제 종료' 창에는 Dock 에 뜨는 앱만 나와서, Dock 에 안 뜨는 포스크탑은 멈추면 끌 길이
없었다 (2026-10-20). 못 박는 것:

  1. 살아 있으면 안 묻는다. HANG_SEC 넘게 멈추면 묻고, 멈춘 곳(메인 스레드 스택)을 기록 · 서버에 남긴다.
  2. [강제 종료] 면 끝낸다. [기다리기] 면 REASK_SEC 동안 안 묻는다. 풀렸다 다시 멈추면 다시 묻는다.
  3. 일부러 기다리는 중(오른쪽 클릭 메뉴 · 확인 창)과 잠들었다 깬 것은 멈춘 게 아니다.
  4. **진짜로 멈춘 프로세스**(메인 스레드가 잠듦 · 파이썬 무한 루프)에서도 감시 스레드가 돌아 끝낸다.
"""
import os
import subprocess
import sys
import tempfile
import time

os.environ["POKET_HOME"] = tempfile.mkdtemp(prefix="poket-test-watchdog-")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

from poketdesktop import trouble                            # noqa: E402
from poketdesktop import watchdog as W                      # noqa: E402

OK = FAIL = 0


def chk(name, cond, got=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s   %r" % (name, got))


class Clock(object):
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def make(answer="wait", stack=None):
    clock = Clock()
    asked, exits = [], []

    def ask(text, still_hung):
        asked.append((text, still_hung()))
        return answer

    dog = W.Watchdog(app=None, now=clock, ask=ask, exit=lambda: exits.append(1),
                     stack=stack or (lambda: ['  File "x/desktop_battle.py", line 9, in render\n    big_loop()\n']))
    return dog, clock, asked, exits


def run(dog, clock, seconds):
    """감시 스레드처럼 1초마다 check()."""
    for _ in range(int(seconds)):
        clock.t += 1
        dog.check()


def logic():
    print("=== 감시의 판단 (가짜 시계) ===")
    sent = []
    real_send = trouble.send
    trouble.send = lambda app, kind, ref=None, message="", detail="": sent.append((kind, message, detail)) or True
    try:
        dog, clock, asked, exits = make()
        run(dog, clock, 30)
        chk("메인 루프가 아직 안 돌았으면 안 묻는다", asked == [])
        for _ in range(40):                              # 살아 있다: 0.5초마다 찍는다 (여기선 1초)
            dog.beat()
            run(dog, clock, 1)
        chk("살아 있으면 안 묻는다", asked == [])
        run(dog, clock, W.HANG_SEC - 2)
        chk("  %d초 안쪽 멈춤은 안 묻는다 (무거운 창 열기 등)" % W.HANG_SEC, asked == [])
        run(dog, clock, 3)
        chk("%d초 넘게 멈추면 묻는다" % W.HANG_SEC, len(asked) == 1 and ("%d초" % W.HANG_SEC) in asked[0][0], asked)
        chk("  묻는 동안 '아직 멈춤' 이 참", asked and asked[0][1] is True)
        chk("  멈춘 곳을 서버에 알린다 (hang, 메인 스레드 스택)", sent and sent[0][0] == "hang" and "render" in sent[0][2],
            sent)
        chk("  [기다리기] 면 끝내지 않는다", exits == [])
        run(dog, clock, W.REASK_SEC - 5)
        chk("  [기다리기] 뒤 %d초 동안은 다시 안 묻는다" % W.REASK_SEC, len(asked) == 1, len(asked))
        run(dog, clock, 10)
        chk("  그래도 멈춰 있으면 다시 묻는다 (서버에는 한 번만)", len(asked) == 2 and len(sent) == 1, (len(asked), len(sent)))
        dog.beat()
        run(dog, clock, 3)
        run(dog, clock, W.HANG_SEC + 1)
        chk("풀렸다 다시 멈추면 새로 묻고 새로 알린다", len(asked) == 3 and len(sent) == 2, (len(asked), len(sent)))

        dog, clock, asked, exits = make(answer="kill")
        dog.beat()
        run(dog, clock, W.HANG_SEC + 1)
        chk("[강제 종료] 면 끝낸다", exits == [1], exits)

        dog, clock, asked, exits = make()
        dog.beat()
        stuck = []

        def ask_then_recover(text, still_hung):
            dog.beat()                                    # 묻는 사이에 메인 스레드가 풀렸다
            stuck.append(still_hung())
            return "wait"
        dog.ask = ask_then_recover
        run(dog, clock, W.HANG_SEC + 1)
        chk("묻는 사이에 풀리면 '아직 멈춤' 이 거짓 (맥은 대화상자를 닫는다)", stuck == [False], stuck)

        menu = lambda: ['  File "tkinter/__init__.py", line 3, in tk_popup\n    self.tk.call(...)\n']   # noqa: E731
        dog, clock, asked, exits = make(stack=menu)
        dog.beat()
        run(dog, clock, W.HANG_SEC * 3)
        chk("오른쪽 클릭 메뉴가 열려 있는 동안은 멈춘 게 아니다 (윈도우 tk_popup)", asked == [], asked)
        box = lambda: ['  File "tkinter/commondialog.py", line 45, in show\n    s = master.tk.call(...)\n']  # noqa: E731
        dog, clock, asked, exits = make(stack=box)
        dog.beat()
        run(dog, clock, W.HANG_SEC * 3)
        chk("  확인 · 파일 창도 (tkinter commondialog)", asked == [], asked)

        dog, clock, asked, exits = make()
        dog.beat()
        run(dog, clock, 2)
        clock.t += 3600                                   # 컴퓨터가 한 시간 잠들었다 깼다
        dog.check()
        run(dog, clock, 2)
        chk("잠들었다 깬 것은 멈춘 게 아니다 (감시의 1초 잠이 크게 건너뛰었다)", asked == [], asked)
    finally:
        trouble.send = real_send


CHILD = r"""
import os, sys, time, tkinter as tk
sys.path[:0] = [%(here)r, %(root)r]
os.environ["POKET_HOME"] = %(home)r
from poketdesktop import platform_os as PLAT, trouble, watchdog as W
PLAT.before_tk()
trouble.send = lambda *a, **k: True
root = tk.Tk(); root.withdraw()
def ask(text, still_hung):
    print("ASKED", flush=True)
    return "kill"
dog = W.Watchdog(None, ask=ask, exit=lambda: os._exit(7), hang_sec=1, reask_sec=60)
W.TICK = 0.2
def beat():
    dog.beat(); root.after(100, beat)
import threading
def loop():
    while True:
        time.sleep(0.2); dog.check()
threading.Thread(target=loop, daemon=True).start()
def spin_forever():
    if %(busy)r:
        x = 0
        while True:
            x += 1                      # 파이썬 무한 루프 (GIL 을 나눠 쓴다)
    else:
        time.sleep(60)                  # 메인 스레드가 잠들었다
root.after(100, beat)
root.after(600, spin_forever)
root.mainloop()
"""


def real():
    print("\n=== 진짜로 멈춘 프로세스 (메인 스레드가 Tk 콜백에서 멈춘다) ===")
    for busy, what in ((False, "메인 스레드가 잠듦"), (True, "파이썬 무한 루프")):
        code = CHILD % {"here": HERE, "root": os.path.dirname(HERE), "home": os.environ["POKET_HOME"], "busy": busy}
        t0 = time.time()
        p = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            out, err = p.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            p.kill()
            out, err = p.communicate()
        took = time.time() - t0
        chk("%s: 감시가 묻고 [강제 종료] 로 끝낸다 (%.1f초)" % (what, took),
            b"ASKED" in out and p.returncode == 7 and took < 20,
            (p.returncode, out[-200:], err[-400:]))


def main():
    logic()
    real()
    print("\n%d개 통과, %d개 실패" % (OK, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
