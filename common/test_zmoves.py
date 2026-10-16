# -*- coding: utf-8 -*-
"""Z기술 엔진 검사 (시즌 4) — 본가 썬·문 / 울트라썬·울트라문의 규칙.

    python common/test_zmoves.py

  1. Z링과 Z크리스탈이 있으면, 크리스탈과 **같은 타입의 기술 하나**를 Z기술로 쓴다.
  2. **한 판에 한 번.** 못 움직인 턴(잠듦·풀죽음)에는 닳지 않는다.
  3. 공격기: Z위력표(예외 포함), 반드시 맞고, 방어를 뚫되 1/4, 추가 효과 없음, 한 번만 친다.
     두 턴 걸리는 기술도 바로 나가고, 반동 턴도 없다. PP 는 원래 기술에서 하나 든다.
  4. 변화기: Z효과가 먼저 나오고 원래 효과가 나간다.
  5. 전용 Z기술: 전용 크리스탈 + 그 포켓몬 + 정해진 기술.
  6. Z크리스탈은 지닌 도구다. 트릭·탁쳐서떨구기·도둑질로 못 뺏는다.
  7. 자동 배틀의 AI 는 고른 기술이 Z로 쓸 수 있는 공격기면 그 턴에 쓴다. 같은 시드면 로그가 같다.
  8. Z링이 없으면 아무 일도 없다.
"""
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from common import battle as B                               # noqa: E402
from common import held as H                                 # noqa: E402
from common import party_battle as PB                        # noqa: E402
from common import pokelogic as P                            # noqa: E402
from common import zmoves as ZM                              # noqa: E402

DEX = P.Pokedex.load(os.path.join(os.path.dirname(HERE), "server", "data", "pokedex.json"))
OK = FAIL = 0


def chk(name, cond, got=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s   %s" % (name, got))


def mon(species, moves=("TACKLE",), held=None, level=50, ability=None):
    m = P.make_pokemon(DEX.get(species), level, random.Random(1), shiny_rate=10 ** 9)
    m["ivs"] = dict((s, 31) for s in P.STATS)
    m["evs"] = dict((s, 0) for s in P.STATS)
    m["nature"] = "HARDY"
    m["moves"] = list(moves)
    m["held"] = held
    m["nickname"] = None
    if ability:
        m["ability"] = ability
    return m


def duel(a, b, ring=True, abil=True, seed=3, foe_ring=False):
    fa, fb = B.Fighter(DEX, a), B.Fighter(DEX, b)
    fa.ability_on = fb.ability_on = abil
    bt = B.Battle(DEX, fa, fb, random.Random(seed), ai="trainer")
    bt.kind = "gym"
    bt.zring = {"me": ring, "foe": foe_ring}
    return bt, fa, fb


def kinds(ev):
    return [e.get("t") for e in ev]


def main():
    print("=== 자료 ===")
    chk("타입 크리스탈 18개", len(ZM.CRYSTAL_TYPE) == 18 and set(ZM.CRYSTAL_TYPE.values()) == set(ZM.TYPE_Z))
    chk("전용 크리스탈 14개 (폼이 없는 셋은 뺐다)",
        len(ZM.EXCLUSIVE) == 14 and "PIKASHUNIUMZ" not in ZM.CRYSTALS and "ALORAICHIUMZ" not in ZM.CRYSTALS)
    chk("지닌 도구로 안다", H.normalize("firium-z") == "FIRIUMZ" and H.name("FIRIUMZ") == "불꽃Z"
        and H.name("PIKANIUMZ") == "피카츄Z")
    chk("뺏기지 않는 도구다", H.stuck("FIRIUMZ") and H.stuck("CHARIZARDITEX") and not H.stuck("LEFTOVERS"))
    for t, base in sorted(ZM.TYPE_Z.items()):
        for cat in ("PHYSICAL", "SPECIAL"):
            if not (DEX.move(base + cat) or {}).get("kr"):
                chk("범용 Z기술 이름이 도감에 있다 (%s)" % (base + cat), False)
                break
    else:
        chk("범용 Z기술 36개의 이름이 도감에 있다", True)
    chk("전용 Z기술과 그 바탕 기술이 다 도감에 있다",
        all(DEX.move(v["move"]) and DEX.move(v["base"]) and all(DEX.get(s) for s in v["species"])
            for v in ZM.EXCLUSIVE.values()))
    chk("도구 설명에 무엇을 하는지 적힌다", "불꽃 타입 기술 하나를 Z기술로" in H.effect_note("FIRIUMZ"),
        H.effect_note("FIRIUMZ"))

    print("\n=== 위력표 ===")
    table = ((40, 100), (55, 100), (60, 120), (65, 120), (70, 140), (75, 140), (80, 160), (85, 160),
             (90, 175), (95, 175), (100, 180), (110, 185), (120, 190), (125, 190), (130, 195),
             (140, 200), (150, 200), (250, 200))
    bad = [(bp, z, ZM.table_power(bp)) for bp, z in table if ZM.table_power(bp) != z]
    chk("본가 표와 같다", not bad, bad)
    chk("예외: 메가드레인 120, 병상첨병 160, V제너레이트 220, 플라잉프레스 170, 코어퍼니셔 140",
        [ZM.power_of(DEX.move(k)) for k in ("MEGADRAIN", "HEX", "VCREATE", "FLYINGPRESS", "COREENFORCER")]
        == [120, 160, 220, 170, 140])
    chk("위력이 정해져 있지 않은 기술: 안다리걸기 160, 자이로볼 160, 땅가르기 180",
        [ZM.power_of(DEX.move(k)) for k in ("LOWKICK", "GYROBALL", "FISSURE")] == [160, 160, 180])
    chk("연속기: 씨기관총 140", ZM.power_of(DEX.move("BULLETSEED")) == 140)

    print("\n=== 쓸 수 있는 기술 ===")
    bt, a, b = duel(mon("CHARIZARD", ("FLAMETHROWER", "AIRSLASH", "SUNNYDAY", "EMBER"), held="FIRIUMZ"),
                    mon("SNORLAX"))
    chk("크리스탈과 같은 타입만 (변화기도 된다)",
        bt.z_moves("me") == ["FLAMETHROWER", "SUNNYDAY", "EMBER"], bt.z_moves("me"))
    bt2, _, _ = duel(mon("CHARIZARD", ("FLAMETHROWER",), held="FIRIUMZ"), mon("SNORLAX"), ring=False)
    chk("Z링이 없으면 없다", bt2.z_moves("me") == [])
    bt3, _, _ = duel(mon("CHARIZARD", ("FLAMETHROWER",), held="LEFTOVERS"), mon("SNORLAX"))
    chk("크리스탈이 없으면 없다", bt3.z_moves("me") == [])
    bt4, a4, _ = duel(mon("CHARIZARD", ("FLAMETHROWER",), held="FIRIUMZ"), mon("SNORLAX"))
    a4.pp["FLAMETHROWER"] = 0
    chk("PP 가 없는 기술은 안 된다", bt4.z_moves("me") == [])

    print("\n=== 공격 Z기술 ===")
    bt, a, b = duel(mon("CHARIZARD", ("FLAMETHROWER", "AIRSLASH"), held="FIRIUMZ"), mon("SNORLAX", ("TACKLE",)))
    plain, _c, _e = B.damage(DEX, bt.move_of("FLAMETHROWER"), a, b, B.MAX_RNG, crit=False)
    pp0, hp0 = a.pp["FLAMETHROWER"], b.hp
    ev = bt.take_turn("FLAMETHROWER", z=True)
    zp = [e for e in ev if e.get("t") == "zpower"]
    mv = [e for e in ev if e.get("t") == "move" and e.get("who") == "me"]
    chk("Z파워 사건이 난다", len(zp) == 1 and zp[0]["move"] == "다이내믹풀플레임" and zp[0]["base"] == "화염방사"
        and zp[0]["item"] == "FIRIUMZ", zp)
    chk("기술 이름이 Z기술 이름으로 뜬다", mv and mv[0]["move"] == "다이내믹풀플레임" and mv[0].get("z") is True
        and mv[0]["moveType"] == "FIRE" and mv[0]["cat"] == "special", mv)
    chk("Z파워가 기술보다 먼저", ev.index(zp[0]) < ev.index(mv[0]))
    hit = [e for e in ev if e.get("t") == "hit" and e.get("who") == "me"]
    chk("한 번만 친다", len(hit) == 1, len(hit))
    # 화염방사 90 -> 175. 난수(0.85~1)·급소를 빼고 보면 1.9배쯤
    ratio = hit[0]["damage"] / float(plain)
    chk("위력 175 로 들어간다 (화염방사의 1.6~2.9배, 급소 포함)", 1.6 < ratio < 2.95, (plain, hit[0]["damage"]))
    chk("원래 기술의 PP 가 하나 든다", a.pp["FLAMETHROWER"] == pp0 - 1, (pp0, a.pp["FLAMETHROWER"]))
    chk("마지막으로 쓴 기술은 원래 기술이다", a.cond.get("lastMove") == "FLAMETHROWER", a.cond.get("lastMove"))
    chk("이 판에서 썼다고 적힌다", "me" in bt.z_done and bt.z_moves("me") == [])
    ev2 = bt.take_turn("FLAMETHROWER", z=True)
    chk("두 번째에는 그냥 화염방사", not any(e.get("t") == "zpower" for e in ev2)
        and [e["move"] for e in ev2 if e.get("t") == "move" and e.get("who") == "me"] == ["화염방사"])

    print("\n=== 물리·특수는 원래 기술을 따른다 ===")
    bt, a, b = duel(mon("CHARIZARD", ("FIREPUNCH",), held="FIRIUMZ"), mon("SNORLAX"))
    ev = bt.take_turn("FIREPUNCH", z=True)
    mv = [e for e in ev if e.get("t") == "move" and e.get("who") == "me"]
    chk("불꽃펀치의 Z기술은 물리", mv[0]["cat"] == "physical" and mv[0]["move"] == "다이내믹풀플레임", mv)

    print("\n=== 반드시 맞는다 / 추가 효과가 없다 ===")
    miss = 0
    for seed in range(40):
        bt, a, b = duel(mon("MAGMORTAR", ("FIREBLAST",), held="FIRIUMZ"), mon("SNORLAX", ("DOUBLETEAM",)),
                        seed=seed)
        b.stages["eva"] = 6                               # 회피 +6
        ev = bt.take_turn("FIREBLAST", z=True)
        miss += any(e.get("t") == "miss" and e.get("who") == "me" for e in ev)
    chk("회피 +6 인 상대에게 마흔 번 다 맞는다 (불대문자는 명중 85)", miss == 0, miss)
    burn = 0
    for seed in range(60):
        bt, a, b = duel(mon("CHARIZARD", ("LAVAPLUME",), held="FIRIUMZ"), mon("SNORLAX", ("TACKLE",)), seed=seed)
        bt.take_turn("LAVAPLUME", z=True)
        burn += b.status == "burn"
    chk("분연(화상 30%)의 Z기술은 화상을 안 건다", burn == 0, burn)
    bt, a, b = duel(mon("VENUSAUR", ("GIGADRAIN",), held="GRASSIUMZ"), mon("BLASTOISE", ("TACKLE",)))
    a.hp = 1
    ev = bt.take_turn("GIGADRAIN", z=True)
    chk("기가드레인의 Z기술은 체력을 안 빨아들인다",
        not any(e.get("t") == "heal" and e.get("who") == "me" for e in ev), kinds(ev))

    print("\n=== 방어를 뚫되 1/4 ===")
    full = None
    for guard in (False, True):
        bt, a, b = duel(mon("CHARIZARD", ("FLAMETHROWER",), held="FIRIUMZ"),
                        mon("SNORLAX", ("PROTECT", "TACKLE")), seed=11)
        b.cond["protect"] = "PROTECT" if guard else None
        if not guard:
            b.cond.pop("protect", None)
        ev = []
        bt.z_want["me"] = "FLAMETHROWER"
        bt.rng = B.MAX_RNG if False else random.Random(1)
        bt._use("me", a, b, "FLAMETHROWER", ev)
        hit = [e for e in ev if e.get("t") == "hit"]
        if not guard:
            full = hit[0]["damage"] / (1.5 if hit[0]["crit"] else 1.0)
        else:
            chk("방어 중인 상대에게도 들어간다", len(hit) == 1, kinds(ev))
            chk("못 막았다는 말이 뜬다", any("완전히 막아내지 못했다" in (e.get("text") or "") for e in ev))
            got = hit[0]["damage"] / (1.5 if hit[0]["crit"] else 1.0)
            chk("데미지는 1/4 쯤", 0.2 < got / full < 0.31, (full, got))
            chk("뚫었다는 표시는 그 한 수로 끝난다", not a.cond.get("pierce"))
    bt, a, b = duel(mon("CHARIZARD", ("FLAMETHROWER",)), mon("SNORLAX", ("PROTECT",)))
    b.cond["protect"] = "PROTECT"
    ev = []
    bt._use("me", a, b, "FLAMETHROWER", ev)
    chk("보통 기술은 방어에 막힌다 (그대로다)", not any(e.get("t") == "hit" for e in ev))

    print("\n=== 두 턴 기술·반동 턴 ===")
    bt, a, b = duel(mon("VENUSAUR", ("SOLARBEAM",), held="GRASSIUMZ"), mon("BLASTOISE", ("TACKLE",)))
    ev = bt.take_turn("SOLARBEAM", z=True)
    chk("솔라빔의 Z기술은 모으지 않고 바로 나간다",
        any(e.get("t") == "hit" and e.get("who") == "me" for e in ev) and not a.cond.get("charge2"), kinds(ev))
    bt, a, b = duel(mon("SNORLAX", ("HYPERBEAM",), held="NORMALIUMZ"), mon("BLASTOISE", ("TACKLE",)))
    bt.take_turn("HYPERBEAM", z=True)
    chk("파괴광선의 Z기술은 반동 턴이 없다", not a.cond.get("recharge"), a.cond)
    ev = bt.take_turn("HYPERBEAM")
    chk("다음 턴에 바로 움직인다", any(e.get("t") == "move" and e.get("who") == "me" for e in ev), kinds(ev))

    print("\n=== 못 움직인 턴에는 닳지 않는다 ===")
    bt, a, b = duel(mon("CHARIZARD", ("FLAMETHROWER",), held="FIRIUMZ"), mon("SNORLAX", ("TACKLE",)))
    a.status, a.sleep_turns = "sleep", 3
    ev = bt.take_turn("FLAMETHROWER", z=True)
    chk("잠들어 못 움직였으면 Z파워가 남는다",
        not any(e.get("t") == "zpower" for e in ev) and "me" not in bt.z_done and bt.z_moves("me"),
        (kinds(ev), bt.z_done))
    bt, a, b = duel(mon("CHARIZARD", ("FLAMETHROWER", "AIRSLASH"), held="FIRIUMZ"), mon("SNORLAX", ("TACKLE",)))
    ev = bt.take_turn("AIRSLASH", z=True)
    chk("타입이 다른 기술에 누르면 그냥 그 기술이 나간다",
        not any(e.get("t") == "zpower" for e in ev) and "me" not in bt.z_done)

    print("\n=== 변화 Z기술 ===")
    bt, a, b = duel(mon("GYARADOS", ("SPLASH", "WATERFALL"), held="NORMALIUMZ"), mon("SNORLAX", ("TACKLE",)))
    ev = bt.take_turn("SPLASH", z=True)
    mv = [e for e in ev if e.get("t") == "move" and e.get("who") == "me"]
    chk("Z튀어오르기: 공격 +3", a.stages["atk"] == 3, a.stages)
    chk("이름이 Z + 원래 이름", mv and mv[0]["move"] == "Z튀어오르기", mv)
    chk("한 판 한 번을 쓴다", "me" in bt.z_done)
    bt, a, b = duel(mon("SNORLAX", ("BELLYDRUM",), held="NORMALIUMZ"), mon("BLASTOISE", ("TACKLE",)), seed=5)
    a.hp = a.maxhp // 3
    ev = bt.take_turn("BELLYDRUM", z=True)
    chk("Z배북: 체력을 다 채운 뒤에 배북이 나간다 (공격 +6, 체력 절반)",
        a.stages["atk"] == 6 and any(e.get("t") == "heal" and e.get("who") == "me" for e in ev),
        (a.stages["atk"], a.hp, a.maxhp))
    bt, a, b = duel(mon("SCIZOR", ("SWORDSDANCE",), held="NORMALIUMZ"), mon("BLASTOISE", ("TACKLE",)))
    a.stages["def"], a.stages["spe"] = -2, -1
    bt.take_turn("SWORDSDANCE", z=True)
    chk("Z칼춤: 내려간 능력치가 돌아오고 칼춤이 나간다",
        a.stages["def"] == 0 and a.stages["spe"] == 0 and a.stages["atk"] == 2, a.stages)
    chk("효과 설명", ZM.effect_text(ZM.Z_STATUS["SPLASH"]) == "공격 +3"
        and ZM.effect_text(ZM.Z_STATUS["SWORDSDANCE"]) == "내려간 능력치를 되돌린다"
        and ZM.effect_text(ZM.Z_STATUS["CONVERSION"]) == "모든 능력치 +1")

    print("\n=== 전용 Z기술 ===")
    bt, a, b = duel(mon("PIKACHU", ("VOLTTACKLE", "THUNDERBOLT"), held="PIKANIUMZ"), mon("BLASTOISE", ("TACKLE",)))
    chk("피카츄Z: 볼트태클만 된다", bt.z_moves("me") == ["VOLTTACKLE"], bt.z_moves("me"))
    ev = bt.take_turn("VOLTTACKLE", z=True)
    mv = [e for e in ev if e.get("t") == "move" and e.get("who") == "me"]
    chk("필살피카슛이 나간다", mv and mv[0]["move"] == "필살피카슛", mv)
    chk("볼트태클의 반동이 없다", not any(e.get("t") == "recoil" and e.get("who") == "me" for e in ev))
    bt, a, b = duel(mon("RAICHU", ("VOLTTACKLE",), held="PIKANIUMZ"), mon("BLASTOISE"))
    chk("다른 포켓몬이 들면 안 된다", bt.z_moves("me") == [])
    bt, a, b = duel(mon("PIKACHU", ("THUNDERBOLT",), held="ELECTRIUMZ"), mon("BLASTOISE"))
    chk("타입 크리스탈로는 범용 Z기술", bt.z_moves("me") == ["THUNDERBOLT"])
    bt, a, b = duel(mon("EEVEE", ("LASTRESORT",), held="EEVIUMZ"), mon("BLASTOISE", ("TACKLE",)))
    ev = bt.take_turn("LASTRESORT", z=True)
    chk("나인이볼부스트: 모든 능력치 +2",
        all(a.stages[k] == 2 for k in ("atk", "def", "spa", "spd", "spe")), a.stages)
    chk("그 턴에 뒤집어지기는 안 나간다",
        [e["move"] for e in ev if e.get("t") == "move" and e.get("who") == "me"] == ["나인이볼부스트"])
    bt, a, b = duel(mon("TAPUKOKO", ("NATURESMADNESS",), held="TAPUNIUMZ"), mon("SNORLAX", ("TACKLE",)))
    hp0 = b.hp
    ev = bt.take_turn("NATURESMADNESS", z=True)
    hit = [e for e in ev if e.get("t") == "hit" and e.get("who") == "me"]
    chk("알로라의수호자: 지금 체력의 3/4", hit and hit[0]["damage"] == int(hp0 * 0.75), (hp0, hit))

    print("\n=== 뺏기지 않는다 ===")
    bt, a, b = duel(mon("CHARIZARD", ("FLAMETHROWER",), held="FIRIUMZ"), mon("ALAKAZAM", ("TRICK",)))
    ev = []
    bt._use("foe", b, a, "TRICK", ev)
    chk("트릭으로 못 바꾼다", a.held == "FIRIUMZ" and b.held is None, (a.held, b.held))
    bt, a, b = duel(mon("CHARIZARD", ("FLAMETHROWER",), held="FIRIUMZ"), mon("WEAVILE", ("KNOCKOFF", "THIEF")))
    ev = []
    bt._use("foe", b, a, "KNOCKOFF", ev)
    chk("탁쳐서떨구기로 안 떨어진다", a.held == "FIRIUMZ", a.held)
    bt._use("foe", b, a, "THIEF", ev)
    chk("도둑질로 못 뺏는다", a.held == "FIRIUMZ" and b.held is None, (a.held, b.held))

    print("\n=== 자동 배틀 ===")
    team_a = [mon("CHARIZARD", ("FLAMETHROWER", "AIRSLASH"), held="FIRIUMZ"),
              mon("GYARADOS", ("WATERFALL", "ICEFANG")), mon("SNORLAX", ("BODYSLAM", "EARTHQUAKE"))]
    team_b = [mon("VENUSAUR", ("ENERGYBALL", "SLUDGEBOMB"), held="GRASSIUMZ"),
              mon("GOLEM", ("ROCKSLIDE", "EARTHQUAKE"), held="GROUNDIUMZ"),
              mon("ALAKAZAM", ("PSYCHIC", "SHADOWBALL"))]
    plain = PB.simulate(DEX, team_a, team_b, seed=42)
    chk("Z링이 없으면 Z 사건이 없다", not any(e.get("t") == "zpower" for e in plain["events"]))
    both = {"me": True, "foe": True}
    r1 = PB.simulate(DEX, team_a, team_b, seed=42, zring=both)
    r2 = PB.simulate(DEX, team_a, team_b, seed=42, zring=both)
    zs = [e for e in r1["events"] if e.get("t") == "zpower"]
    chk("Z링이 있으면 AI 가 쓴다", 1 <= len(zs) <= 2, [(e["who"], e["move"]) for e in zs])
    chk("한 쪽에 한 번씩만", len(set(e["who"] for e in zs)) == len(zs), [e["who"] for e in zs])
    chk("같은 시드면 로그가 한 글자도 안 다르다", json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True))
    flipped = PB.flip_log(r1["events"])
    fz = [e for e in flipped if e.get("t") == "zpower"]
    chk("시점을 뒤집으면 쓴 쪽도 뒤집힌다",
        [e["who"] for e in fz] == [{"me": "foe", "foe": "me"}[e["who"]] for e in zs])
    one = PB.simulate(DEX, team_a, team_b, seed=42, zring={"me": True, "foe": False})
    chk("한쪽만 가졌으면 그쪽만", all(e["who"] == "me" for e in one["events"] if e.get("t") == "zpower"))
    # AI 는 변화기를 Z로 쓰지 않는다, 안 통하는 상대에게도 안 쓴다
    bt, a, b = duel(mon("SNORLAX", ("BODYSLAM",), held="NORMALIUMZ"), mon("GENGAR", ("SHADOWBALL",)))
    bt.auto_z = {"me": True, "foe": False}
    bt._auto_z("me", "BODYSLAM")
    chk("효과가 없는 상대에게는 AI 가 안 쓴다 (노말 -> 고스트)", "me" not in bt.z_want, bt.z_want)
    bt, a, b = duel(mon("GYARADOS", ("SPLASH",), held="NORMALIUMZ"), mon("SNORLAX"))
    bt.auto_z = {"me": True, "foe": False}
    bt._auto_z("me", "SPLASH")
    chk("AI 는 변화기를 Z로 쓰지 않는다", "me" not in bt.z_want, bt.z_want)

    print("\n=== 다른 것들과 엮일 때 (리뷰에서 나온 것) ===")
    # 스킨 특성은 Z기술의 타입도 위력도 못 바꾼다
    bt, a, b = duel(mon("SYLVEON", ("HYPERVOICE",), held="NORMALIUMZ", ability="PIXILATE"),
                    mon("DRAGONITE", ("TACKLE",)))
    plain_fairy = B.damage(DEX, bt.move_of("HYPERVOICE"), a, b, B.MAX_RNG, crit=False)
    chk("(보통의 하이퍼보이스는 페어리스킨으로 페어리가 되어 망나뇽에게 2배)", plain_fairy[2] == 2.0, plain_fairy)
    ev = bt.take_turn("HYPERVOICE", z=True)
    hit = [e for e in ev if e.get("t") == "hit" and e.get("who") == "me"]
    mv = [e for e in ev if e.get("t") == "move" and e.get("who") == "me"]
    chk("페어리스킨이어도 Z기술은 노말 그대로다", hit and hit[0]["eff"] == 1.0 and mv[0]["moveType"] == "NORMAL",
        (hit[:1], mv[:1]))
    # 부자유친이어도 한 번만 친다
    bt, a, b = duel(mon("KANGASKHAN", ("RETURN",), held="NORMALIUMZ", ability="PARENTALBOND"),
                    mon("SNORLAX", ("TACKLE",)))
    ev = bt.take_turn("RETURN", z=True)
    chk("부자유친이어도 Z기술은 한 번만 친다",
        len([e for e in ev if e.get("t") == "hit" and e.get("who") == "me"]) == 1)
    # Z크리스탈을 지닌 레쿠쟈는 화룡점정으로 메가진화하지 못한다
    bt, a, b = duel(mon("RAYQUAZA", ("DRAGONASCENT", "OUTRAGE"), held="DRAGONIUMZ"), mon("SNORLAX", ("TACKLE",)))
    bt.keystone = {"me": True, "foe": False}
    chk("Z크리스탈을 지닌 레쿠쟈는 메가진화하지 못한다", bt.can_mega("me") is None and bt.z_moves("me") == ["OUTRAGE"],
        (bt.can_mega("me"), bt.z_moves("me")))
    bt, a, b = duel(mon("RAYQUAZA", ("DRAGONASCENT", "OUTRAGE")), mon("SNORLAX", ("TACKLE",)))
    bt.keystone = {"me": True, "foe": False}
    chk("  아무것도 안 지녔으면 예전처럼 된다", bt.can_mega("me") is not None)
    # 알로라의수호자도 방어를 뚫을 때는 1/4
    got = {}
    for guard in (False, True):
        bt, a, b = duel(mon("TAPUKOKO", ("NATURESMADNESS",), held="TAPUNIUMZ"), mon("SNORLAX", ("PROTECT",)))
        if guard:
            b.cond["protect"] = "PROTECT"
        ev = []
        bt.z_want["me"] = "NATURESMADNESS"
        bt._use("me", a, b, "NATURESMADNESS", ev)
        got[guard] = [e["damage"] for e in ev if e.get("t") == "hit"]
    chk("알로라의수호자: 방어 중이면 1/4", got[False] and got[True] and got[True][0] == got[False][0] // 4, got)
    # 여럿을 노리는 전용 Z기술도 와이드가드에 통째로 막히지 않는다
    bt, a, b = duel(mon("KOMMOO", ("CLANGINGSCALES",), held="KOMMONIUMZ"), mon("SNORLAX", ("WIDEGUARD",)))
    bt.field.side("foe")["wideguard"] = True
    ev = []
    bt.z_want["me"] = "CLANGINGSCALES"
    bt._use("me", a, b, "CLANGINGSCALES", ev)
    chk("브레이징소울비트는 와이드가드에 안 막힌다", any(e.get("t") == "hit" for e in ev)
        and not any("와이드가드" in (e.get("text") or "") for e in ev), kinds(ev))
    chk("  쓴 뒤 능력치가 오른다 (그 기술의 효과)", a.stages["atk"] == 1 and a.stages["spe"] == 1, a.stages)
    # Z기술로 썼어도 그 기술을 쓴 것으로 센다 (비장의무기)
    bt, a, b = duel(mon("SNORLAX", ("HYPERBEAM", "LASTRESORT"), held="NORMALIUMZ"), mon("BLASTOISE", ("TACKLE",)))
    bt.take_turn("HYPERBEAM", z=True)
    chk("Z기술로 쓴 기술도 '쓴 기술' 에 적힌다", "HYPERBEAM" in (a.cond.get("usedMoves") or []),
        a.cond.get("usedMoves"))

    print("\n" + "=" * 54)
    print("  합계  OK %d   FAIL %d" % (OK, FAIL))
    print("=" * 54)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
