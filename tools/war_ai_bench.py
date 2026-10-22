# -*- coding: utf-8 -*-
"""길드전 방어 AI 벤치마크 - 옛 셈과 새 셈을 같은 판으로 견준다 (2026-10-22).

    python tools/war_ai_bench.py --ai old --proxy greedy --pairs 24 --seeds 3 --jobs 8
    python tools/war_ai_bench.py --ai new --proxy switcher --pairs 12 --seeds 2 --json out.json
    python tools/war_ai_bench.py --ai new --quick            # 운영 서버에서 시간만 잴 때 (판 넷)

팀은 관장 자료(gyms.json)의 챔피언 · 사천왕 · 프런티어브레인 팀을 Lv.50 개체값 31 로 맞춘 것 (길드전 AI 수비대와
같은 방식). 방어 쪽은 길드전 판과 같은 트레이너(ai="war"), 공격 쪽은 사람 대역이 둔다:

  greedy    가장 아픈 기술만. 쓰러지면 형세(_standing)가 가장 나은 포켓몬 (지금 셈이 쓰는 사람 모델).
  switcher  greedy + 이번 턴에 쓰러질 판이면 그 기술을 버티는 포켓몬으로 교체.

잰다: 방어 승률 · 무승부 · 턴 수 · AI 가 고른 수의 종류(교체 · 깔기 · 랭크업 · 시간 끌기 · 공격) · 셈 시간.
DB · 서버를 건드리지 않는다 (계산만).
"""
import argparse
import json
import multiprocessing
import os
import random
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROLES = ("챔피언", "사천왕", "프런티어브레인")
STALL_EXTRA = ("SUBSTITUTE", "WISH", "REST")
TURN_CAP = 400

_G = {}


def _setup(root):
    if root not in sys.path:
        sys.path.insert(0, root)
    from common import pokelogic as P, trainer_battle as TB                     # noqa: E402
    data = os.path.join(root, "server", "data") if os.path.isdir(os.path.join(root, "server", "data")) \
        else os.path.join(root, "data")
    _G["TB"] = TB
    _G["dex"] = P.Pokedex.load(os.path.join(data, "pokedex.json"))
    with open(os.path.join(data, "gyms.json"), encoding="utf-8") as f:
        gyms = json.load(f)
    _G["teams"] = [(t["name"], t["team"]) for t in gyms["trainers"] if t.get("role") in ROLES]


def teams(level=50):
    TB = _G["TB"]
    return [(n, [TB.trainer_mon(dict(e, level=level, iv=31)) for e in team]) for n, team in _G["teams"]]


def pairs(n):
    """결정적인 (방어, 공격) 쌍 n 개."""
    k = len(_G["teams"])
    out = []
    i = 0
    while len(out) < n:
        d, a = i % k, (i * 7 + 3) % k
        if d != a:
            out.append((d, a))
        i += 1
    return out


def classify(tb, choice):
    """AI 가 고른 수의 종류."""
    from common import statusmoves as SM                                     # noqa: E402
    slot, key = choice
    if slot is not None:
        return "switch"
    if not key:
        return "attack"
    md = tb.bt.move_of(key) or {}
    if key in SM.HAZARD_MOVES:
        return "hazard"
    if md.get("statSelf") and any(c > 0 for _s, c in (md.get("stat") or [])) and not md.get("power"):
        return "setup"
    if (md.get("heal") or 0) > 0 and not md.get("power") or key in SM.PROTECTS or key in STALL_EXTRA:
        return "stall"
    return "attack"


def human_move(tb, proxy):
    """사람 대역의 이번 수: ('move', key) / ('switch', slot)."""
    TB = _G["TB"]
    from common import statusmoves as SM                                     # noqa: E402
    me, foe = tb.me, tb.foe
    if proxy == "switcher" and not (SM.trapped(tb.bt, me) or SM.must_stay(me) or SM.locked_move(me, tb.bt)):
        their_d, their_k = tb._best(foe, me)
        my_d, my_k = tb._best(me, foe)
        if their_k:
            their_md = tb.bt.move_of(their_k)
            dies = their_d * TB.KO_ROLL >= me.hp and not (
                my_k and tb._first(me, foe, tb.bt.move_of(my_k), their_md))
            if dies:
                best, best_sc = None, None
                for i in tb.valid_switches():
                    f = tb.me_team[i]
                    if tb._est(foe, f, their_k) >= f.hp * 0.6:
                        continue
                    sc = tb._standing(f, foe)
                    if best_sc is None or sc > best_sc:
                        best, best_sc = i, sc
                if best is not None:
                    return "switch", best
    lock = SM.locked_move(me, tb.bt)
    _d, k = tb._best(me, foe)
    return "move", lock or k or tb.bt.usable(me)[0]


def one(args):
    """판 하나. 결과 dict."""
    root, ai, proxy, d, a, seed, atk_level, sets, old_eval = args
    if "TB" not in _G:
        _setup(root)
    TB = _G["TB"]
    TB.TrainerBattle.WAR_V2 = (ai == "new")
    for k, v in sets:                                       # 실험용: 셈의 상수를 바꿔 본다 (--set NAME=VALUE)
        setattr(TB.TrainerBattle, k, v)
    if old_eval:                                            # 실험용: 새 셈에 옛 형세 평가
        TB.TrainerBattle._eval_v2 = TB.TrainerBattle._eval
    dname, dteam = teams()[d]
    # 사람 대역은 사람보다 약하다 - 공격 쪽 레벨만 올려 옛 AI 의 방어 승률을 50% 근처에 두면 차이가 잘 보인다
    aname, ateam = teams(atk_level)[a]
    tr = {"id": "gw:bench", "name": dname, "role": "[bench]", "level": 50, "team": dteam, "noMega": True,
          "ai": "war", "keystone": True, "zring": True}
    stats = {"switch": 0, "hazard": 0, "setup": 0, "stall": 0, "attack": 0}
    think = []
    real = TB.TrainerBattle._war_choice

    def timed(self):
        t0 = time.time()
        got = real(self)
        think.append(time.time() - t0)
        stats[classify(self, got)] += 1
        return got
    TB.TrainerBattle._war_choice = timed
    try:
        tb = TB.TrainerBattle(_G["dex"], ateam, tr, random.Random(seed))
        tb.start()
        guard = 0
        while not tb.over and guard < TURN_CAP * 3:
            guard += 1
            if tb.need_switch:
                opts = tb.valid_switches()
                tb.act("switch", max(opts, key=lambda i: (tb._standing(tb.me_team[i], tb.foe), -i)))
                continue
            kind, value = human_move(tb, proxy)
            try:
                tb.act(kind, value)
            except ValueError:
                tb.act("move", tb.bt.usable(tb.me)[0])
        result = tb.result
        turns = tb.turn
        # 마진: AI 쪽에 남은 (마리 + 체력 비율) - 사람 쪽. 승패보다 예민하다 (같은 판끼리 견줄 때)
        margin = sum(1 + f.hp / float(f.maxhp or 1) for f in tb.foe_team if f.alive()) \
            - sum(1 + f.hp / float(f.maxhp or 1) for f in tb.me_team if f.alive())
    finally:
        TB.TrainerBattle._war_choice = real
    return {"def": dname, "atk": aname, "seed": seed, "result": result, "turns": turns, "margin": round(margin, 3),
            "moves": stats,
            "think": think}


def summarize(rows):
    n = len(rows)
    think = sorted(t for r in rows for t in r["think"])

    def pct(p):
        return 1000 * think[min(len(think) - 1, int(p * len(think)))] if think else 0.0
    moves = dict((k, sum(r["moves"][k] for r in rows)) for k in ("switch", "hazard", "setup", "stall", "attack"))
    return {
        "battles": n,
        "def_win_rate": round(sum(1 for r in rows if r["result"] in ("lost", "forfeit")) / float(n or 1), 4),
        "draws": sum(1 for r in rows if r["result"] == "draw"),
        "turns_mean": round(sum(r["turns"] for r in rows) / float(n or 1), 1),
        "margin_mean": round(sum(r["margin"] for r in rows) / float(n or 1), 3),
        "turns_max": max([r["turns"] for r in rows] or [0]),
        "ai_moves": moves,
        "think_ms": {"mean": round(1000 * sum(think) / float(len(think) or 1), 1), "p95": round(pct(0.95), 1),
                     "max": round(1000 * (think[-1] if think else 0), 1)},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", choices=("old", "new"), default="old")
    ap.add_argument("--proxy", choices=("greedy", "switcher"), default="greedy")
    ap.add_argument("--pairs", type=int, default=24)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--quick", action="store_true", help="판 넷 - 운영 서버에서 시간만 잴 때")
    ap.add_argument("--atk-level", type=int, default=50, help="공격 쪽(사람 대역) 레벨 - 방어 승률을 가운데로")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--json")
    ap.add_argument("--set", action="append", default=[], help="실험: 셈의 상수 NAME=VALUE (여러 번)")
    ap.add_argument("--old-eval", action="store_true", help="실험: 새 셈에 옛 형세 평가")
    a = ap.parse_args()
    _setup(a.root)
    if a.quick:
        a.pairs, a.seeds, a.jobs = 2, 2, 1
    sets = [(kv.split("=", 1)[0], float(kv.split("=", 1)[1])) for kv in a.set]
    sets = [(k, int(v) if v == int(v) and k.endswith(("DEPTH", "SEEDS", "FREE", "TURN")) else v) for k, v in sets]
    work = [(a.root, a.ai, a.proxy, d, at, s, a.atk_level, sets, a.old_eval)
            for d, at in pairs(a.pairs) for s in range(1, a.seeds + 1)]
    t0 = time.time()
    if a.jobs > 1:
        with multiprocessing.Pool(a.jobs) as pool:
            rows = pool.map(one, work, chunksize=1)
    else:
        rows = [one(w) for w in work]
    out = summarize(rows)
    out.update({"ai": a.ai, "proxy": a.proxy, "pairs": a.pairs, "seeds": a.seeds, "atk_level": a.atk_level,
                "set": a.set, "old_eval": a.old_eval,
                "wall_sec": round(time.time() - t0, 1)})
    print(json.dumps(out, ensure_ascii=False))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(dict(out, rows=[dict(r, think=None) for r in rows]), f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
