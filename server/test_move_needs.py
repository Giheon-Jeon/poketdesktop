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

    print("\n%d개 통과, %d개 실패" % (OK, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
