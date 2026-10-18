# -*- coding: utf-8 -*-
"""서버 오류 기록 검사 (1.13.1).

    python server/test_errors.py

예전에는 오류 처리기가 except 블록 밖에서 traceback.format_exc() 를 불러서 'NoneType: None' 만 남았다 -
10/18 의 OperationalError 38건이 'database is locked' 인지 디스크인지 알 수 없었다. 못 박는 것:

  1. 오류 문구가 맨 앞에 남는다 ('OperationalError: database is locked').
  2. 어느 함수에서 났는지(역추적)도 남는다. 길면 문구는 남기고 역추적의 끝쪽을 남긴다.
  3. 응답은 그대로 500 과 사람이 읽을 말.
"""
import os
import sqlite3
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

TMP = tempfile.mkdtemp(prefix="poket-errors-")
os.environ["POKET_DB"] = os.path.join(TMP, "t.db")
os.environ.pop("POKET_TURSO_URL", None)
os.environ.setdefault("POKET_POKEDEX", os.path.join(HERE, "data", "pokedex.json"))
os.environ.setdefault("POKET_ITEMS", os.path.join(HERE, "data", "items.json"))

from app import db, errors, main  # noqa: E402

OK = FAIL = 0


def chk(name, cond, got=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s   %r" % (name, got))


def raised(fn):
    try:
        fn()
    except Exception as e:                                  # noqa: BLE001
        return e


def deep_lock():
    raise sqlite3.OperationalError("database is locked")


def deep_long():
    def again(n):
        if n:
            return again(n - 1)
        raise ValueError("마지막 줄의 문구")
    again(60)                                               # 역추적이 DETAIL_MAX 보다 길다


def main_():
    db.init()
    req = types.SimpleNamespace(method="GET", url=types.SimpleNamespace(path="/api/live"))
    r = main.any_error(req, raised(deep_lock))
    row = db.q1("SELECT kind, detail FROM server_error ORDER BY id DESC LIMIT 1")
    chk("응답은 500", r.status_code == 500, r.status_code)
    chk("오류 문구가 맨 앞에 남는다", row["detail"].startswith("OperationalError: database is locked"),
        row["detail"][:80])
    chk("  어느 함수에서 났는지도 남는다", "deep_lock" in row["detail"], row["detail"][-200:])
    chk("  'NoneType: None' 이 아니다", "NoneType: None" not in row["detail"])
    main.any_error(req, raised(deep_long))
    row = db.q1("SELECT kind, detail FROM server_error ORDER BY id DESC LIMIT 1")
    chk("역추적이 길어도 문구는 남는다 (앞에서 자르지 않는다)",
        row["detail"].startswith("ValueError: 마지막 줄의 문구") and len(row["detail"]) <= errors.DETAIL_MAX,
        (row["detail"][:60], len(row["detail"])))
    print("\n%d개 통과, %d개 실패" % (OK, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main_())
