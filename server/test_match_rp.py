# -*- coding: utf-8 -*-
"""랜덤 배틀 상대 고르기 — 시즌 4: 점수(RP)가 가까운 사람부터.

    python server/test_match_rp.py

서버를 띄우지 않는다. 임시 DB 에 모듈을 직접 붙인다. 못 박는 것:

  1. **RP 가 가까운 사람이 먼저다.** 전력이 더 비슷한 사람이 있어도 RP 가 먼 띠에 있으면
     가까운 띠의 사람을 고른다.
  2. 띠는 ±50 -> ±100 -> ±200 -> 전체로 넓어진다. 전체까지 가므로 받을 수 있는 사람이
     하나라도 있으면 붙는다 (전력 띠는 이제 사람을 떨어뜨리지 않는다).
  3. 띠 안에서는 전력이 가까운 몇 명 중에서 고른다.
  4. 그대로인 것: 받는 쪽 마릿수, 배치를 마친 사람끼리 먼저, 방금 붙은 사람·차단한 사람 제외.
"""
import os
import random
import sys
import tempfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

TMP = tempfile.mkdtemp(prefix="poket-matchrp-")
os.environ["POKET_DB"] = os.path.join(TMP, "t.db")
os.environ.pop("POKET_TURSO_URL", None)
os.environ["POKET_POKEDEX"] = os.path.join(HERE, "data", "pokedex.json")
os.environ["POKET_ITEMS"] = os.path.join(HERE, "data", "items.json")

from app import db, deps, pvp  # noqa: E402

OK = FAIL = 0


def chk(name, cond, got=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s   %s" % (name, got))


def mkuser(name, mons=6, level=50, species="PIKACHU", rp=0, games=10, rating=1000):
    """포켓몬 mons 마리(같은 종·레벨)를 데리고 다니는 사람. 전력은 종과 레벨로만 정해진다."""
    cur = db.run(
        "INSERT INTO users (username, pw_hash, pw_salt, pw_iter, balls, money,"
        " created_at, last_login, last_ip) VALUES (?,?,?,1,10,0,?,?,'')",
        (name, b"x", b"x", "2026-01-01", "2026-01-01"))
    uid = cur.lastrowid
    d = deps.dex()
    rng = random.Random(zlib.crc32(name.encode("utf-8")))
    for i in range(mons):
        m = d.roll_wild(level, level, rng)
        m["species"] = species
        pid = db.insert_mon(uid, m, "2026-01-01")
        db.run("UPDATE pokemon SET on_desktop=1, slot=?, level=? WHERE id=?", (i, level, pid))
    pvp._rating_row(uid)
    db.run("UPDATE rank_stat SET rp=?, peak_rp=?, games=?, rating=? WHERE user_id=?",
           (rp, rp, games, rating, uid))
    return uid


def picks(uid, n=40):
    return [pvp.find_opponent(uid, random.Random(k)) for k in range(n)]


def wipe():
    for t in ("battle_record", "pvp_match", "match_log", "friend_block", "rank_team",
              "rank_stat", "pokemon", "users"):
        db.run("DELETE FROM %s" % t)


def main():
    db.init()

    print("=== 띠 ===")
    chk("RP 띠는 ±50, ±100, ±200, 전체 순", pvp.RP_BANDS == (50, 100, 200, None), pvp.RP_BANDS)

    print("\n=== RP 가 가까운 사람이 먼저 ===")
    me = mkuser("mm_me", rp=300)
    # 랭크전은 Lv.50 이상 여섯 마리만 나간다 (시즌 4) - 전력 차이는 레벨 대신 종족값으로 낸다
    near_rp = mkuser("mm_near_rp", species="RATTATA", rp=320)  # RP 는 가깝고 전력은 30% 쯤 낮다 (253 대 320)
    twin = mkuser("mm_twin", level=50, rp=700)                 # 전력은 똑같고 RP 는 멀다
    got = set(picks(me))
    chk("전력이 똑같은 사람이 있어도 RP 가 가까운 사람을 고른다", got == {near_rp}, got)
    row = db.q1("SELECT stage, band, near FROM match_log WHERE user_id=? ORDER BY id DESC LIMIT 1", (me,))
    chk("±50 띠에서 골랐다고 남는다", row["band"] == 50 and row["near"] == 1, dict(row))

    print("\n=== 띠가 넓어진다 ===")
    wipe()
    me = mkuser("mm_me", rp=300)
    b100 = mkuser("mm_b100", rp=380)
    b200 = mkuser("mm_b200", rp=480)
    far = mkuser("mm_far", rp=900)
    chk("±50 에 없으면 ±100 에서", set(picks(me)) == {b100}, set(picks(me)))
    db.run("DELETE FROM pokemon WHERE user_id=?", (b100,))
    chk("±100 에도 없으면 ±200 에서", set(picks(me)) == {b200}, set(picks(me)))
    db.run("DELETE FROM pokemon WHERE user_id=?", (b200,))
    got = set(picks(me))
    chk("그 밖에만 있으면 전체에서", got == {far}, got)
    row = db.q1("SELECT band FROM match_log WHERE user_id=? ORDER BY id DESC LIMIT 1", (me,))
    chk("전체에서 골랐다고 남는다 (-1)", row["band"] == -1, dict(row))

    print("\n=== 전력은 이제 사람을 떨어뜨리지 않는다 ===")
    wipe()
    me = mkuser("mm_me", species="DRAGONITE", level=50, rp=0)   # 전설은 한 마리만 나가서 랭크전 조건에 못 든다
    weak = mkuser("mm_weak", species="CATERPIE", level=50, rp=0)
    teams = pvp._all_teams()
    gap = abs(pvp.team_power(teams[weak]) / pvp.team_power(teams[me]) - 1)
    chk("전력이 25% 넘게 달라도", gap > pvp.POWER_BANDS[-1], gap)
    chk("RP 가 같으면 붙는다", set(picks(me, 6)) == {weak}, set(picks(me, 6)))

    print("\n=== 띠 안에서는 전력이 가까운 사람 ===")
    wipe()
    me = mkuser("mm_me", level=50, rp=100)
    # 피카츄(320) 와 종족값이 가까운 셋 (전력 차 2~7%) / 먼 넷 (전력 차 50% 쯤) - 모두 Lv.50
    close = [mkuser("mm_c%d" % i, species=sp, rp=100 + 5 * i)
             for i, sp in enumerate(("KRABBY", "CLEFAIRY", "MANKEY"), 1)]
    loose = [mkuser("mm_l%d" % i, species=sp, rp=100)
             for i, sp in enumerate(("CATERPIE", "WEEDLE", "MAGIKARP", "SUNKERN"))]
    got = set(picks(me, 60))
    chk("같은 띠에 여럿이면 전력이 가까운 셋 중에서만", got == set(close), (got, close))
    chk("늘 한 사람만 나오지는 않는다", len(got) >= 2, got)

    print("\n=== 그대로인 규칙 ===")
    wipe()
    me = mkuser("mm_me", mons=6, rp=200)
    five = mkuser("mm_five", mons=5, rp=200)                   # 받는 쪽이 더 적다
    six_far = mkuser("mm_six", mons=6, rp=900)
    chk("받는 쪽이 적으면 RP 가 같아도 안 붙인다", set(picks(me, 8)) == {six_far}, set(picks(me, 8)))

    wipe()
    me = mkuser("mm_me", rp=200, games=10)
    rookie = mkuser("mm_rookie", rp=200, games=0)              # 배치 전, RP 는 같다
    vet = mkuser("mm_vet", rp=420, games=30)                   # 배치를 마쳤고 RP 는 ±200 밖
    chk("배치를 마친 사람끼리 먼저 (RP 가 멀어도)", set(picks(me, 8)) == {vet}, set(picks(me, 8)))
    db.run("DELETE FROM pokemon WHERE user_id=?", (vet,))
    chk("없으면 배치 전인 사람과도", set(picks(me, 8)) == {rookie}, set(picks(me, 8)))

    wipe()
    me = mkuser("mm_me", rp=200)
    a = mkuser("mm_a", rp=200)
    b = mkuser("mm_b", rp=900)
    pvp.run_match(me, a, kind="random", seed=3)
    db.run("UPDATE rank_stat SET rp=200 WHERE user_id IN (?,?)", (me, a))
    chk("방금 붙은 사람은 RP 가 같아도 다시 안 고른다", set(picks(me, 8)) == {b}, set(picks(me, 8)))

    wipe()
    me = mkuser("mm_me", rp=200)
    a = mkuser("mm_a", rp=200)
    b = mkuser("mm_b", rp=900)
    db.run("INSERT INTO friend_block (user_id, target_id, created_at) VALUES (?,?,?)",
           (a, me, "2026-01-01"))
    chk("나를 차단한 사람은 안 고른다", set(picks(me, 8)) == {b}, set(picks(me, 8)))

    wipe()
    me = mkuser("mm_me", rp=200)
    chk("아무도 없으면 None", pvp.find_opponent(me) is None)

    print("\n" + "=" * 54)
    print("  합계  OK %d   FAIL %d" % (OK, FAIL))
    print("=" * 54)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
