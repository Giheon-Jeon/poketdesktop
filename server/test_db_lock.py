# -*- coding: utf-8 -*-
"""db.run 이 실패해도 쓰기 잠금을 쥔 채 남지 않는다 (2026-10-21 22:35 운영 장애). 서버를 띄우지 않는다.

    python server/test_db_lock.py

파이썬 sqlite3 는 쓰기 문장 앞에 트랜잭션을 저절로 연다. 문장이 실패하면(유일 조건 위반을 부르는 쪽이 잡아서
넘기는 곳이 있다) 그 트랜잭션이 스레드의 커넥션에 남아 쓰기 잠금을 계속 쥐었다 - 그 스레드가 다음에 쓰기를
커밋할 때까지 다른 스레드의 쓰기가 전부 'database is locked' 로 떨어졌다 (78초 동안 572건). 못 박는 것:

  1. 실패한 db.run 뒤에 그 커넥션에 열린 트랜잭션이 없다.
  2. 그 사이 다른 스레드의 쓰기가 바로 된다 (잠금을 기다리지 않는다).
  3. 실패한 스레드도 다음 쓰기가 된다 (낡은 읽기 시점을 쥐고 있지 않다).
  4. 실패한 문장은 서버 로그에 남는다 (그날은 잡아서 넘긴 실패라 어느 문장이었는지 끝내 몰랐다).
     잠금 대기 실패('database is locked')는 장애 때 수백 건씩 나오므로 남기지 않는다.
"""
import io
import os
import sqlite3
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

TMP = tempfile.mkdtemp(prefix="poket-dblock-")
os.environ["POKET_DB"] = os.path.join(TMP, "t.db")
os.environ.pop("POKET_TURSO_URL", None)
os.environ["POKET_POKEDEX"] = os.path.join(HERE, "data", "pokedex.json")
os.environ["POKET_ITEMS"] = os.path.join(HERE, "data", "items.json")

from app import db                                           # noqa: E402

OK = FAIL = 0


def chk(name, cond, got=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s   %r" % (name, got))


def other_thread_write(k):
    """다른 스레드(= 다른 커넥션)에서 쓰기 하나. (성공했나, 걸린 초)"""
    out = {}

    def go():
        t = time.time()
        try:
            db.run("INSERT INTO lk (k) VALUES (?)", (k,))
            out["ok"] = True
        except sqlite3.OperationalError as e:
            out["ok"] = False
            out["err"] = str(e)
        out["sec"] = time.time() - t
    th = threading.Thread(target=go)
    th.start()
    th.join(30)
    return out.get("ok"), round(out.get("sec", 99), 2), out.get("err")


def main():
    db.init()
    db.run("CREATE TABLE IF NOT EXISTS lk (k INTEGER PRIMARY KEY)")
    db.run("INSERT INTO lk (k) VALUES (1)")

    print("=== 유일 조건 위반을 잡아서 넘긴 뒤 ===")
    real_err, sys.stderr = sys.stderr, io.StringIO()
    try:
        try:
            db.run("INSERT INTO lk (k) VALUES (1)")
            raised = False
        except sqlite3.IntegrityError:
            raised = True
        logged = sys.stderr.getvalue()
        db._note_failure("UPDATE lk SET k=k", sqlite3.OperationalError("database is locked"))
        quiet = sys.stderr.getvalue() == logged
    finally:
        sys.stderr = real_err
    chk("db.run 은 오류를 그대로 올린다 (부르는 쪽이 판단한다)", raised)
    chk("실패한 문장이 서버 로그에 남는다 (오류 종류 · 문장)",
        "[db.run 실패] IntegrityError" in logged and "INSERT INTO lk" in logged, logged)
    chk("  잠금 대기 실패는 남기지 않는다", quiet)
    chk("그 커넥션에 열린 트랜잭션이 없다 (쓰기 잠금을 안 쥔다)", not db.connect().in_transaction,
        db.connect().in_transaction)
    ok, sec, err = other_thread_write(2)
    chk("다른 스레드의 쓰기가 바로 된다 (예전: 15초 기다리다 database is locked)", ok and sec < 2, (ok, sec, err))
    db.run("INSERT INTO lk (k) VALUES (3)")
    chk("실패했던 스레드의 다음 쓰기도 된다",
        [r["k"] for r in db.q("SELECT k FROM lk ORDER BY k")] == [1, 2, 3],
        [r["k"] for r in db.q("SELECT k FROM lk ORDER BY k")])

    print("\n=== 없는 칸에 쓰기 (다른 종류의 실패) ===")
    try:
        db.run("UPDATE lk SET nope=1 WHERE k=1")
    except sqlite3.OperationalError:
        pass
    ok, sec, err = other_thread_write(4)
    chk("실패 뒤에도 다른 스레드의 쓰기가 바로 된다", ok and sec < 2, (ok, sec, err))

    print("\n%d개 통과, %d개 실패" % (OK, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
