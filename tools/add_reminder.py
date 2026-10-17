# -*- coding: utf-8 -*-
"""'기술 떠올리기' 로만 배우는 기술을 도감(pokedex.json)의 종마다 remind 칸에 넣는다 (1.13).

    python tools/add_reminder.py            # 넣는다 (있으면 고쳐 쓴다)
    python tools/add_reminder.py --check    # 도감이 지금 자료와 같은지만 본다

2026-10-17 사용자 제보: "오거폰 기술 떠올리기에는 우드혼이 없다". 본가(SV)에서 오거폰의 우드혼 · 두번차기는
**기술 떠올리기로 배운다** (PokémonDB · Serebii 의 오거폰 '떠올리기' 목록). 그런데 PokeAPI 는 알을 낳지 못하는
종의 이런 기술을 '알 기술' 로 적어 두어서, 레벨업 표만 읽는 build_pokedex 가 빠뜨렸다 - 이 게임에는 교배가
없고 알 기술은 같은 기술의 기술머신으로만 배우는데, 우드혼은 기술머신이 없어 어디서도 못 배웠다.

**무엇을 넣나:** 알을 낳지 못하는 종(알 그룹 no-eggs) 가운데 **아기 포켓몬이 아닌 것**의 SV 알 기술 전부.
아기 포켓몬(피츄 · 리오르 …)의 알 기술은 본가에서도 진화형의 교배로 물려받는 진짜 알 기술이라 넣지 않는다.

레벨업 표(moves)에는 넣지 않는다 - 거기 넣으면 새로 생기는 포켓몬(알 · 레이드 · 악당 전설)의 처음 기술이
바뀐다. 기술 떠올리기(server/app/tm_routes.rememberable)만 이 칸을 본다.

**build_pokedex.py 를 다시 돌리면 이것도 다시 돌려야 한다** (add_megas · add_forms 와 같다).
"""
import csv
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "tools", "_cache")
DEX = os.path.join(ROOT, "server", "data", "pokedex.json")
SV = "scarlet-violet"
EGG = "2"           # pokemon_move_methods: egg


def _rows(name):
    with io.open(os.path.join(CACHE, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def key(ident):
    return re.sub(r"[^A-Za-z0-9]", "", ident).upper()


def build(dex):
    """{종 내부 이름: [기술 열쇠, ...]}"""
    vg = next((r["id"] for r in _rows("version_groups.csv") if r["identifier"] == SV), "25")
    moves = dict((r["id"], key(r["identifier"])) for r in _rows("moves.csv"))
    by_num = dict((s["num"], s) for s in dex["species"])
    out = {}
    for r in _rows("pokemon_moves.csv"):
        if r["version_group_id"] != vg or r["pokemon_move_method_id"] != EGG:
            continue
        sp = by_num.get(int(r["pokemon_id"]))          # 기본 모습(번호 = 도감 번호)만
        if not sp or sp.get("egg") != ["no-eggs"] or sp.get("isBaby"):
            continue
        mv = moves.get(r["move_id"])
        if not mv or mv not in dex["moves"]:
            continue
        lst = out.setdefault(sp["internal"], [])
        if mv not in lst:
            lst.append(mv)
    return dict((k, sorted(v)) for k, v in out.items())


def apply(dex, table):
    changed = False
    for sp in dex["species"]:
        want = table.get(sp["internal"])
        if want and sp.get("remind") != want:
            sp["remind"] = want
            changed = True
        elif not want and "remind" in sp:
            del sp["remind"]
            changed = True
    return changed


def main():
    check = "--check" in sys.argv
    with io.open(DEX, encoding="utf-8") as f:
        dex = json.load(f)
    table = build(dex)
    changed = apply(dex, table)
    print("떠올리기 전용 기술: %d종 %d개" % (len(table), sum(len(v) for v in table.values())))
    for k, v in sorted(table.items()):
        print("  %-12s %s" % (k, ", ".join(v)))
    if check:
        print("바뀔 것이 있다" if changed else "그대로다")
        return 1 if changed else 0
    with io.open(DEX, "w", encoding="utf-8") as f:
        json.dump(dex, f, ensure_ascii=False, indent=1, sort_keys=True)
    print("썼다: %s" % os.path.relpath(DEX, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
