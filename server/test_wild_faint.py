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
  5. 공격 턴에 내 포켓몬이 쓰러져도 다음 포켓몬이 있으면 야생의 턴 끝(화염구슬 · 독 데미지)이 온다 (1.13.3).
     야생이 턴 끝 데미지로 쓰러지면 이긴 판이다. 마지막 포켓몬이 쓰러졌으면 턴 끝은 없다.
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
    end_of_turn_checks()

    print("\n%d개 통과, %d개 실패" % (OK, FAIL))
    return 1 if FAIL else 0


def mkfoe(uid, held=None):
    """마하펀치(선공기)로 레벨 2 캐터피를 먼저 쓰러뜨리는 야생 괴력몬."""
    m = P.make_pokemon(deps.dex().get("CONKELDURR"), 30, random.Random(7), shiny_rate=10 ** 9)
    m["moves"], m["held"], m["ability"] = ["MACHPUNCH"], held, "GUTS"
    later = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).isoformat()
    return db.run("INSERT INTO wild (user_id, state, species, data, created_at, expires_at)"
                  " VALUES (?,'revealed',?,?,'',?)", (uid, "CONKELDURR", json.dumps(m), later)).lastrowid


def happy(pid):
    return db.q1("SELECT happiness FROM pokemon WHERE id=?", (pid,))["happiness"]


def end_of_turn_checks():
    print("\n=== 내 포켓몬이 쓰러진 턴에도 야생의 턴 끝이 온다 (게시판 #295) ===")
    uid = mkuser("턴끝")
    weak = mkmon(uid, "CATERPIE", 2, 0)
    mkmon(uid, "ONIX", 30, 1)
    bid = BR.start(mkfoe(uid, "FLAMEORB"), ctx=ctx(uid))["battle"]["id"]
    out = BR.use_move(bid, BR.MoveIn(move="TACKLE"), ctx=ctx(uid))
    ev = out.get("events") or []
    faint_at = next((i for i, e in enumerate(ev) if e.get("t") == "faint" and e.get("who") == "me"), None)
    burn_at = next((i for i, e in enumerate(ev) if e.get("who") == "foe" and e.get("t") == "ailment"
                    and e.get("status") == "burn"), None)
    chk("캐터피가 쓰러진 턴 끝에 야생의 화염구슬이 터진다", faint_at is not None and burn_at is not None
        and burn_at > faint_at, [(e.get("t"), e.get("who")) for e in ev])
    chk("  야생의 화상이 판에 남는다 (다음 포켓몬과 싸울 때 그대로)",
        json.loads(db.q1("SELECT foe FROM battle WHERE id=?", (bid,))["foe"])["status"] == "burn")
    chk("  판은 졌다 · 다음 포켓몬을 실어 보낸다", (out.get("battle") or {}).get("result") == "lost"
        and out.get("canSwitch") is True, (out.get("battle") or {}).get("result"))

    print("\n=== 야생이 턴 끝 데미지(독)로 쓰러지면 이긴 판이다 ===")
    uid = mkuser("독끝")
    weak = mkmon(uid, "CATERPIE", 2, 0)
    mkmon(uid, "ONIX", 30, 1)
    wid = mkfoe(uid)
    bid = BR.start(wid, ctx=ctx(uid))["battle"]["id"]
    foe = json.loads(db.q1("SELECT foe FROM battle WHERE id=?", (bid,))["foe"])
    foe["hp"], foe["status"] = 1, "poison"
    db.run("UPDATE battle SET foe=? WHERE id=?", (json.dumps(foe), bid))
    before = happy(weak)
    out = BR.use_move(bid, BR.MoveIn(move="TACKLE"), ctx=ctx(uid))
    ev = out.get("events") or []
    chk("내 포켓몬이 쓰러지고 야생도 독으로 쓰러진다", [e.get("who") for e in ev if e.get("t") == "faint"]
        == ["me", "foe"], [(e.get("t"), e.get("who")) for e in ev])
    chk("  이긴 판이다 · 야생은 사라진다", (out.get("battle") or {}).get("result") == "won"
        and db.q1("SELECT id FROM wild WHERE id=?", (wid,)) is None, (out.get("battle") or {}).get("result"))
    chk("  쓰러진 캐터피의 친밀도는 깎인다 (진 판에서 쓰러졌을 때와 같다)", happy(weak) < before,
        (before, happy(weak)))

    print("\n=== 마지막 포켓몬이 쓰러지면 턴 끝은 없다 ===")
    uid = mkuser("혼자")
    mkmon(uid, "CATERPIE", 2, 0)
    bid = BR.start(mkfoe(uid, "FLAMEORB"), ctx=ctx(uid))["battle"]["id"]
    out = BR.use_move(bid, BR.MoveIn(move="TACKLE"), ctx=ctx(uid))
    chk("화염구슬이 안 터진다 · 데리고 다니는 포켓몬을 다 써서 야생은 떠난다",
        not any(e.get("t") == "ailment" and e.get("who") == "foe" for e in out.get("events") or [])
        and out.get("allDown") is True, (out.get("allDown"), [(e.get("t"), e.get("who")) for e in out.get("events")]))


if __name__ == "__main__":
    sys.exit(main())
