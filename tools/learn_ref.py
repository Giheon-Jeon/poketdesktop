# -*- coding: utf-8 -*-
"""본가 '최신작' 학습표 (1.13.3). build_tms · add_reminder · learn_audit 가 같이 쓴다.

종마다(폼은 폼 id 마다) 그 종이 나온 **가장 최근 본편**의 학습표를 고른다. 같은 세대 안에서는 판 번호가 큰
쪽이 나중이지만, 세대를 먼저 본다 - PokeAPI 는 일본판 재발매(red-green-japan 28 · blue-japan 29)를 나중에
등록해서 번호만 보면 1세대가 SV 를 이긴다 (build_pokedex 가 한 번 당한 일).

빼는 판: 외전(레츠고 19 · 레전드 아르세우스 24 · 레전드 Z-A 30 · 메가디멘션 31 · 챔피언스 32)과 일본판 재발매
(28 · 29). SV 의 DLC 는 PokeAPI 가 SV(25) 하나에 합쳐 적는다.

방법 번호 (pokemon_move_methods): 1 레벨업 · 2 알 · 3 가르치기 · 4 기술머신 · 6 전기구슬 알(볼트태클) ·
10 폼체인지 · 11 지가르데큐브.
"""
import io
import os
import re

SIDE_VG = {19, 24, 28, 29, 30, 31, 32}
ZA_VG = {30, 31}                    # 레전즈 Z-A · 메가디멘션
LEVEL_UP, EGG, TUTOR, MACHINE = 1, 2, 3, 4

# 쇼다운의 레전즈 Z-A 학습표 (1.13.4). PokeAPI 에는 Z-A 의 '누가 무엇을 배우나' 가 비어 있다.
ZA_LEARNSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_cache", "showdown_gen9legends_learnsets.ts")
ZA_URL = "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/mods/gen9legends/learnsets.ts"


def _key(ident):
    return re.sub(r"[^A-Za-z0-9]", "", ident).upper()


def za_codes(path=ZA_LEARNSETS):
    """쇼다운 Z-A 학습표 -> {종 열쇠(CLEFABLE): {기술 열쇠: ["9L52", "9M", ...]}}. 없으면 멈춘다.

    종 열쇠는 쇼다운 이름을 그대로 대문자로 - 폼은 따로 있다 (floetteeternal · meowsticf ...).
    """
    if not os.path.exists(path):
        raise SystemExit("레전즈 Z-A 학습표가 없습니다: %s\n  받기: curl -o '%s' %s" % (path, path, ZA_URL))
    out, cur = {}, None
    with io.open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\t(\w+): \{", line)
            if m:
                cur = _key(m.group(1))
                out[cur] = {}
                continue
            m = re.match(r"^\t\t\t(\w+): \[(.*)\]", line)
            if m and cur:
                out[cur][_key(m.group(1))] = re.findall(r'"([^"]+)"', m.group(2))
    return out


def reference(move_rows, vg_rows):
    """{pokemon_id: {move_id: {방법, ...}}} - 그 종이 나온 가장 최근 본편의 학습표."""
    gen = dict((int(r["id"]), int(r["generation_id"])) for r in vg_rows)
    per = {}                                    # pid -> {vg -> {mid -> set}}
    for r in move_rows:
        vg = int(r["version_group_id"])
        if vg in SIDE_VG:
            continue
        pid, mid, how = int(r["pokemon_id"]), int(r["move_id"]), int(r["pokemon_move_method_id"])
        per.setdefault(pid, {}).setdefault(vg, {}).setdefault(mid, set()).add(how)
    out = {}
    for pid, vgs in per.items():
        best = max(vgs, key=lambda v: (gen.get(v, 0), v))
        out[pid] = vgs[best]
    return out


def ref_vg(move_rows, vg_rows):
    """{pokemon_id: 기준 판 번호} - 검사 · 감사가 어느 판을 봤는지 적을 때."""
    gen = dict((int(r["id"]), int(r["generation_id"])) for r in vg_rows)
    seen = {}
    for r in move_rows:
        vg = int(r["version_group_id"])
        if vg in SIDE_VG:
            continue
        pid = int(r["pokemon_id"])
        if pid not in seen or (gen.get(vg, 0), vg) > (gen.get(seen[pid], 0), seen[pid]):
            seen[pid] = vg
    return seen
