# -*- coding: utf-8 -*-
"""기술이 있어야 쓰는 것을 이 게임에서 채울 수 있는가 (2026-10-19, 게시판 #277).

    python server/test_move_needs.py

피카츄Z 는 상점에서 파는데, 바탕 기술인 볼트태클을 이 게임 어디서도 배울 수 없어서 필살피카슛을 쓸 수
없었다. 본가에서 볼트태클은 교배로만 배우는 특별한 알 기술이고, 이 게임에는 교배도 볼트태클 기술머신도 없다.

같은 일이 다시 생기지 않게 **기술이 걸린 것을 전부** 본다:

  1. 전용 Z크리스탈의 바탕 기술 (피카츄Z 볼트태클, 이브이Z 비장의무기 …) - 그 Z 를 쓸 수 있는 종 모두
  2. 기술로 하는 메가진화 (메가레쿠쟈 - 화룡점정)
  3. 기술이 있어야 바뀌는 폼 (케르디오 각오의 모습 - 신비의칼, 메로엣타 스텝폼 - 옛노래)
  4. 기술을 알아야 하는 진화 (내루미 - 구르기, 과미르 - 드래곤옐 …)

'배울 수 있다' = 그 종(또는 진화 전 종)이 레벨업 · 기술 떠올리기 전용(remind) · 기술머신 중 하나로 배운다.
못 배우는 것이 생기면 tools/add_reminder.py 의 MANUAL 에 넣는다 (떠올리기로 배운다).

그리고 실제로 피카츄의 '기술 떠올리기' 목록에 볼트태클이 나오는지 서버 함수로 본다.
"""
import json
import os
import random
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

TMP = tempfile.mkdtemp(prefix="poket-move-needs-")
os.environ["POKET_DB"] = os.path.join(TMP, "t.db")
os.environ.pop("POKET_TURSO_URL", None)
os.environ["POKET_POKEDEX"] = os.path.join(HERE, "data", "pokedex.json")
os.environ["POKET_ITEMS"] = os.path.join(HERE, "data", "items.json")

from common import zmoves as ZM                     # noqa: E402

from app import db, deps, tms                       # noqa: E402
from app import tm_routes as TR                     # noqa: E402

OK = FAIL = 0


def chk(name, cond, got=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s   %r" % (name, got))


def needs(raw):
    """(무엇, 종, 기술) 전부 - 기술이 있어야 쓰는 것."""
    out = []
    for c in ZM.EXCLUSIVE.values():
        for sp in c.get("species") or ():
            out.append(("Z크리스탈 %s" % c["kr"], sp, c["base"]))
    for m in raw.get("megas") or []:
        if m.get("megaMove"):
            out.append(("메가진화 %s" % m["kr"], m["megaOf"], m["megaMove"]))
    for f in raw.get("forms") or []:
        if f.get("move"):
            out.append(("폼 %s %s" % (f["kr"], f.get("formKr") or ""), f["formOf"], f["move"]))
    for s in raw["species"]:
        for b in s.get("evo") or []:
            if b.get("move"):
                out.append(("진화 %s -> %s" % (s["kr"], b.get("to")), s["internal"], b["move"]))
    return out


def learn_ways(d, sp_key):
    """그 종과 진화 전 종이 배우는 기술 {기술: 어떻게}."""
    out = {}
    cur, seen = sp_key, set()
    while cur and cur not in seen:
        seen.add(cur)
        sp = d.get(cur) or {}
        tag = "" if cur == sp_key else " (진화 전 %s)" % sp.get("kr")
        for lv, mv in sp.get("moves") or []:
            out.setdefault(mv, "레벨업 Lv.%s%s" % (lv, tag))
        for mv in sp.get("remind") or []:
            out.setdefault(mv, "떠올리기%s" % tag)
        for no in tms.learnable(sp.get("num") or 0):
            t = tms.get(no)
            if t:
                out.setdefault(t["move"], "기술머신%03d%s" % (int(no), tag))
        cur = sp.get("prevo")
    return out


def main():
    db.init()
    d = deps.dex()
    raw = d.raw

    print("== 기술이 있어야 쓰는 것을 이 게임에서 채울 수 있다")
    rows = needs(raw)
    chk("살펴볼 것이 빠지지 않았다 (전용 Z 15 · 메가 1 · 폼 2 · 진화 13 이상)", len(rows) >= 31, len(rows))
    for what, sp, mv in rows:
        how = learn_ways(d, sp).get(mv)
        chk("%s: %s 이(가) %s 을(를) 배운다 (%s)" % (what, (d.get(sp) or {}).get("kr", sp),
                                              (d.move(mv) or {}).get("kr", mv), how or "못 배움"),
            how is not None, (sp, mv))

    print("\n== 피카츄의 기술 떠올리기에 볼트태클 (게시판 #277)")
    cur = db.run("INSERT INTO users (username, pw_hash, pw_salt, pw_iter, balls, money, created_at, last_login,"
                 " last_ip) VALUES ('needs',?,?,1,10,0,'2026-01-01','2026-01-01','')", (b"x", b"x"))
    uid = cur.lastrowid
    m = d.roll_wild(30, 30, random.Random(1))
    m.update(species="PIKACHU", moves=["THUNDERSHOCK"], ability="STATIC")
    pid = db.insert_mon(uid, m, "2026-01-01")
    r = db.q1("SELECT * FROM pokemon WHERE id=?", (pid,))
    got = TR.rememberable(r, d.get("PIKACHU"), d)
    chk("Lv.30 피카츄의 떠올리기 목록에 볼트태클이 있다 (레벨 1 로)", ("VOLTTACKLE", 1) in got, got)
    db.run("UPDATE pokemon SET moves=? WHERE id=?", (json.dumps(["VOLTTACKLE"]), pid))
    r = db.q1("SELECT * FROM pokemon WHERE id=?", (pid,))
    chk("  이미 알면 목록에서 빠진다", "VOLTTACKLE" not in [mv for mv, _lv in TR.rememberable(r, d.get("PIKACHU"), d)])
    chk("  피카츄Z 의 바탕 기술이 바로 그것이다", ZM.EXCLUSIVE["PIKANIUMZ"]["base"] == "VOLTTACKLE")
    chk("레벨업 표는 그대로 (새로 생기는 피카츄의 처음 기술이 바뀌지 않는다)",
        "VOLTTACKLE" not in [mv for _lv, mv in d.get("PIKACHU").get("moves") or []])

    print("\n== 본가 최신작의 가르침 · 알 기술 · 옛 전용기 (1.13.3, 2026-10-20 전수 검사 tools/learn_audit.py)")
    # 고치기 전: 최신작이 소드실드 · 울트라썬문인 132종이 그 게임의 가르침 기술을, 교배가 없어 알 기술 1,619줄을
    # 어디서도 못 배웠다. 캐시(tools/_cache)가 git 에 없어서 감사는 CI 에서 못 돌리고, 여기서 대표 사례를 본다.
    def tm_learns(sp_key, mv):
        no = next((n for n, t in tms.all_tms().items() if t["move"] == mv), None)
        return no is not None and tms.can_learn(d.get(sp_key)["num"], no)

    def reminds(sp_key, mv):
        return mv in (d.get(sp_key).get("remind") or [])

    chk("가르침(기술머신 있음): 단굴이 메테오빔을 기술머신으로 (소드실드 가르침)", tm_learns("BOLDORE", "METEORBEAM"))
    chk("  야나프가 코골기를 기술머신으로 (울트라썬문 가르침)", tm_learns("PANSAGE", "SNORE"))
    chk("가르침(기술머신 없음): 야나프가 탐내다 · 광합성을 떠올리기로", reminds("PANSAGE", "COVET") and reminds("PANSAGE", "SYNTHESIS"))
    chk("알 기술(기술머신 없음)은 떠올리기로: 리자몽 배북 · 역린돌격", reminds("CHARIZARD", "BELLYDRUM") and reminds("CHARIZARD", "DRAGONRUSH"))
    chk("  아기에게만 적힌 알 기술은 진화형도 (피츄 -> 피카츄 바라기 · 선물)", reminds("PIKACHU", "WISH") and reminds("PIKACHU", "PRESENT"))
    chk("  기술머신이 있는 알 기술은 떠올리기에 안 넣는다 (기술머신으로 배운다)",
        not any(mv in set(t["move"] for t in tms.all_tms().values()) for mv in d.get("CHARIZARD").get("remind") or []))
    chk("옛 전용기: 무한다이노 무한다이빔 · 비퀸 회복지령 · 나시 구슬던지기 · 텅구리 뼈다귀치기",
        reminds("ETERNATUS", "ETERNABEAM") and reminds("VESPIQUEN", "HEALORDER") and reminds("EXEGGUTOR", "BARRAGE")
        and reminds("MAROWAK", "BONECLUB"))
    chk("  예전 떠올리기 전용 기술은 그대로 (오거폰 우드혼)", reminds("OGERPON", "HORNLEECH"))
    r = db.q1("SELECT * FROM pokemon WHERE id=?", (pid,))
    db.run("UPDATE pokemon SET moves=? WHERE id=?", (json.dumps(["THUNDERSHOCK"]), pid))
    r = db.q1("SELECT * FROM pokemon WHERE id=?", (pid,))
    got = dict(TR.rememberable(r, d.get("PIKACHU"), d))
    chk("실제 떠올리기 목록에 피츄의 알 기술(바라기)이 나온다 (레벨 1)", got.get("WISH") == 1, sorted(got)[:12])

    print("\n== 진화 전 단계의 레벨업 기술도 떠올린다 (1.13.3, 게시판 #291 니뉴)")
    # 본가 SV 는 진화형 표에 진화 전 기술을 Lv.1 로 다 싣는다 (픽시에 삐삐 기술 21개 - 쇼다운 9L1). PokeAPI 자료에는
    # 돌로 진화하는 종(나인테일 · 픽시 …)이 빠져 있어서, 진화한 뒤에는 그 기술을 떠올릴 수 없었다.
    def remember_names(species, level, moves):
        m2 = d.roll_wild(level, level, random.Random(2))
        m2.update(species=species, moves=list(moves), ability=(d.get(species).get("abil") or [None])[0])
        p2 = db.insert_mon(uid, m2, "2026-01-01")
        return dict(TR.rememberable(db.q1("SELECT * FROM pokemon WHERE id=?", (p2,)), d.get(species), d))
    got = remember_names("NINETALES", 50, ["FLAMETHROWER"])
    chk("나인테일 Lv.50: 식스테일의 인페르노(Lv.48) · 신통력 · 사슬묶기를 떠올린다",
        {"INFERNO", "EXTRASENSORY", "DISABLE"} <= set(got), sorted(got))
    chk("  식스테일 표의 레벨 그대로 (인페르노 Lv.48)", got.get("INFERNO") == 48, got.get("INFERNO"))
    got = remember_names("NINETALES", 45, ["FLAMETHROWER"])
    chk("  지금 레벨보다 높은 진화 전 기술은 안 나온다 (Lv.45 나인테일 - 인페르노 Lv.48)",
        "INFERNO" not in got and "SAFEGUARD" in got, sorted(got))
    chk("  나인테일 자기 표 기술은 그대로", "QUICKATTACK" in remember_names("NINETALES", 50, ["FLAMETHROWER"]))

    print("\n%d개 통과, %d개 실패" % (OK, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
