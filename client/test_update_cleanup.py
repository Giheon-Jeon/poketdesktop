# -*- coding: utf-8 -*-
"""지난 버전 폴더 치우기 (updater.cleanup_old) 검사. 어느 운영체제에서나 돈다.

    python client/test_update_cleanup.py

윈도우는 배포 폴더 이름에 버전이 들어 있다 (`poketdesktop-v1.10.4/`). 새 판을 옆에 풀고
그쪽을 띄운 뒤, 다음에 켤 때 지난 판의 폴더를 치운다.

**자기보다 낮은 버전만 지운다 (1.10.5).** 예전에는 자기와 다른 버전을 전부 지워서, 옛
바로가기로 옛 exe 를 켜면 옆에 있는 더 새 판의 폴더까지 지웠다.
"""
import os
import sys
import tempfile

os.environ["POKET_HOME"] = tempfile.mkdtemp(prefix="poket-test-cleanup-")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

from poketdesktop import updater as U                       # noqa: E402

OK = FAIL = 0


def chk(name, cond, got=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s   %r" % (name, got))


def make(parent, names):
    for n in names:
        d = os.path.join(parent, n)
        os.makedirs(d)
        with open(os.path.join(d, n + ".exe"), "w") as f:
            f.write("x")


def left(parent):
    return sorted(os.listdir(parent))


def main():
    real_mac = U.IS_MAC
    U.IS_MAC = False                    # 폴더를 치우는 것은 윈도우의 일이다 (맥은 번들 하나를 갈아끼운다)
    try:
        parent = tempfile.mkdtemp(prefix="poket-cleanup-")
        make(parent, ["poketdesktop-v1.9.2", "poketdesktop-v1.10.3", "poketdesktop-v1.10.4",
                      "poketdesktop-v1.10.5", "poketdesktop-v1.11.0", "poketdesktop-v2.0.0"])
        os.makedirs(os.path.join(parent, "내 문서"))
        os.makedirs(os.path.join(parent, "poketdesktop-v1.10.4.new"))       # 풀다 만 것 (extract 가 치운다)
        with open(os.path.join(parent, "poketdesktop-v1.0.0"), "w") as f:   # 폴더가 아니라 파일
            f.write("x")
        n = U.cleanup_old(parent, keep="1.10.4")
        got = left(parent)
        chk("자기보다 낮은 버전의 폴더를 지운다 (1.9.2 · 1.10.3)", n == 2
            and "poketdesktop-v1.9.2" not in got and "poketdesktop-v1.10.3" not in got, (n, got))
        chk("자기 폴더는 그대로다", "poketdesktop-v1.10.4" in got)
        chk("**더 새 판의 폴더는 건드리지 않는다** (1.10.5 · 1.11.0 · 2.0.0)",
            all(x in got for x in ("poketdesktop-v1.10.5", "poketdesktop-v1.11.0", "poketdesktop-v2.0.0")), got)
        chk("  그 안의 실행 파일도 그대로다",
            os.path.exists(os.path.join(parent, "poketdesktop-v1.10.5", "poketdesktop-v1.10.5.exe")))
        chk("우리 것이 아닌 폴더·파일은 안 건드린다", "내 문서" in got and "poketdesktop-v1.10.4.new" in got
            and "poketdesktop-v1.0.0" in got, got)
        chk("버전은 숫자로 견준다 (1.9.2 는 1.10.4 보다 낮다 - 글자로 견주면 높다)",
            U.newer("1.10.4", "1.9.2") and not U.newer("1.9.2", "1.10.4") and not U.newer("1.10.4", "1.10.4"))

        # 새 판(1.10.5)이 켜지면 그 아래 것을 치운다 - 평소의 업데이트 흐름
        n = U.cleanup_old(parent, keep="1.10.5")
        got = left(parent)
        chk("새 판이 켜지면 지난 판(1.10.4)을 치운다", n == 1 and "poketdesktop-v1.10.4" not in got
            and "poketdesktop-v1.10.5" in got and "poketdesktop-v1.11.0" in got, (n, got))
        chk("치울 것이 없으면 0", U.cleanup_old(parent, keep="1.10.5") == 0)
        chk("없는 자리를 줘도 죽지 않는다", U.cleanup_old(os.path.join(parent, "없는 곳"), keep="1.10.5") == 0)
        U.IS_MAC = True
        make(parent, ["poketdesktop-v1.0.1"])
        chk("맥에서는 아무것도 안 한다", U.cleanup_old(parent, keep="1.10.5") == 0 and "poketdesktop-v1.0.1" in left(parent))
    finally:
        U.IS_MAC = real_mac
    print("\n합계  OK %d   FAIL %d" % (OK, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
