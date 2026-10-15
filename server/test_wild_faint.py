# -*- coding: utf-8 -*-
"""야생 배틀: 볼을 놓친 턴(또는 도망에 실패한 턴)에 쓰러지면 다음 포켓몬 (게시판 #222, 레드 36세).

    python server/test_wild_faint.py

서버를 띄우지 않는다. 임시 DB 에 모듈을 직접 붙인다.

예전에는 공격 턴에 쓰러질 때만 다음 포켓몬을 실어 보냈다. 볼을 놓친 뒤의 반격으로 쓰러지면 교체 없이
판이 그냥 끝나서, 야생이 사라지거나(서버에 남았다가 시간이 다 됨) 다시 누르면 둘 다 체력이 꽉 찬
새 판이 됐다. 못 박는 것:

  1. 볼을 놓친 턴에 쓰러지면 공격 턴처럼 canSwitch · party(다음 포켓몬) · fainted 를 준다.
  2. 다음 포켓몬으로 바꾸면 **같은 판**이 이어진다 - 야생의 체력이 그대로다.
  3. 데리고 다니는 포켓몬을 다 쓰면 allDown 이고 야생은 떠난다.
  4. 도망에 실패한 턴에 쓰러져도 같다.
"""
import datetime
import json
import os
import random
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

TMP = tempfile.mkdtemp(prefix="poket-wildfaint-")
os.environ["POKET_DB"] = os.path.join(TMP, "t.db")
os.environ.pop("POKET_TURSO_URL", None)
os.environ["POKET_POKEDEX"] = os.path.join(HERE, "data", "pokedex.json")
os.environ["POKET_ITEMS"] = os.path.join(HERE, "data", "items.json")

from common import battle as B                               # noqa: E402
from common import pokelogic as P                            # noqa: E402
from app import battle_routes as BR                          # noqa: E402
from app import db, deps                                     # noqa: E402

OK = FAIL = 0


def chk(name, cond, got=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s   %r" % (name, got))


def mkuser(name):
    return db.run(
        "INSERT INTO users (username, pw_hash, pw_salt, pw_iter, balls, money,"
        " created_at, last_login, last_ip) VALUES (?,?,?,1,30,0,'','','')",
        (name, b"x", b"x")).lastrowid


def mkmon(uid, species, level, slot):
    m = P.make_pokemon(deps.dex().get(species), level, random.Random(slot + 3), shiny_rate=10 ** 9)
    pid = db.insert_mon(uid, m, "")
    db.run("UPDATE pokemon SET on_desktop=1, slot=? WHERE id=?", (slot, pid))
    return pid


def mkwild(uid, species, level):
    m = P.make_pokemon(deps.dex().get(species), level, random.Random(7), shiny_rate=10 ** 9)
    later = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).isoformat()
    return db.run("INSERT INTO wild (user_id, state, species, data, created_at, expires_at)"
                  " VALUES (?,'revealed',?,?,'',?)", (uid, species, json.dumps(m), later)).lastrowid


def ctx(uid):
    return {"user": db.q1("SELECT * FROM users WHERE id=?", (uid,))}


def knock_out(bt, ev):
    """상대의 반격 대신: 내 포켓몬이 쓰러진다 (무엇에 맞았는지는 이 검사의 관심이 아니다)."""
    bt.me.hp = 0
    ev.append({"t": "faint", "who": "me", "text": "%s 은(는) 쓰러졌다!" % bt.me.name})
    return None


def main():
    db.init()
    real_catch, real_turn, real_run = P.catch_attempt, BR.foe_only_turn, B.Battle.try_run
    P.catch_attempt = lambda *a, **k: (False, 1)            # 늘 놓친다
    BR.foe_only_turn = knock_out                            # 놓친 턴의 반격에 쓰러진다
    B.Battle.try_run = lambda self, attempts=1: False       # 도망은 늘 실패
    try:
        uid = mkuser("볼던지기")
        lead = mkmon(uid, "SNORLAX", 30, 0)
        second = mkmon(uid, "ONIX", 30, 1)

        print("=== 볼을 놓친 턴에 쓰러지면 ===")
        wid = mkwild(uid, "PIDGEY", 5)
        bid = BR.start(wid, ctx=ctx(uid))["battle"]["id"]
        foe_hp = db.q1("SELECT foe FROM battle WHERE id=?", (bid,))["foe"]
        out = BR.throw_ball(bid, BR.BallIn(ball="POKEBALL"), ctx=ctx(uid))
        b = out.get("battle") or {}
        chk("판이 졌다로 끝나고", b.get("over") and b.get("result") == "lost", b.get("result"))
        chk("  다음 포켓몬을 실어 보낸다 (공격 턴에 쓰러졌을 때와 같다)", out.get("canSwitch") is True
            and [m["id"] for m in out.get("party") or []] == [second] and out.get("fainted") == [lead],
            (out.get("canSwitch"), out.get("party"), out.get("fainted")))
        sw = BR.switch(bid, BR.SwitchIn(pokemon=second), ctx=ctx(uid))
        sb = sw.get("battle") or {}
        chk("다음 포켓몬으로 바꾸면 같은 판이 이어진다 (야생 체력 그대로)", not sb.get("over")
            and (sb.get("me") or {}).get("id") == second
            and json.loads(db.q1("SELECT foe FROM battle WHERE id=?", (bid,))["foe"])["hp"]
            == json.loads(foe_hp)["hp"], sb.get("me"))
        out = BR.throw_ball(bid, BR.BallIn(ball="POKEBALL"), ctx=ctx(uid))
        chk("데리고 다니는 포켓몬을 다 쓰면 야생은 떠난다", out.get("canSwitch") is False and out.get("allDown") is True
            and db.q1("SELECT id FROM wild WHERE id=?", (wid,)) is None, (out.get("canSwitch"), out.get("allDown")))

        print("\n=== 도망에 실패한 턴에 쓰러져도 ===")
        wid2 = mkwild(uid, "RATTATA", 5)
        bid2 = BR.start(wid2, ctx=ctx(uid))["battle"]["id"]
        out = BR.run_away(bid2, ctx=ctx(uid))
        chk("다음 포켓몬을 실어 보낸다", out.get("escaped") is False and (out.get("battle") or {}).get("result") == "lost"
            and out.get("canSwitch") is True and [m["id"] for m in out.get("party") or []] == [second],
            (out.get("canSwitch"), out.get("party")))
    finally:
        P.catch_attempt, BR.foe_only_turn, B.Battle.try_run = real_catch, real_turn, real_run

    print("\n%d개 통과, %d개 실패" % (OK, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
