# -*- coding: utf-8 -*-
"""악당 조직 표를 만든다 (시즌 4, 관장 탭의 '악당 출현').

    python tools/build_villains.py           server/data/villains.json 을 쓴다
    python tools/build_villains.py --check   지금 파일이 이 표와 같은지만 본다

간부의 팀(종·기술·특성·도구·노력치)은 **새로 만들지 않는다.** 관장 자료(gyms.json)에 이미
들어 있는 악당 트레이너의 구성을 그대로 쓴다 - 여기서는 '어느 조직에 누가 서고, 다 이기면
어떤 전설을 만나는가' 만 적는다. 레벨과 마릿수는 도전하는 사람의 파티에 맞춘다 (server/app/boss.py).

간부 셋을 채울 수 있는 조직만 넣었다 (플레어단·매크로코스모스는 자료에 한두 명뿐이다).
  pool  간부들. boss 가 있으면 이 중 둘, 없으면 셋이 그날 선다 (날짜로 정해진다).
  boss  보스. 있으면 늘 셋째(마지막)로 선다.
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GYMS = os.path.join(ROOT, "server", "data", "gyms.json")
DEX = os.path.join(ROOT, "server", "data", "pokedex.json")
OUT = os.path.join(ROOT, "server", "data", "villains.json")

TEAMS = [
    {"id": "rocket", "name": "로켓단", "pool": ["archer", "ariana", "petrel", "proton"],
     "boss": "giovanni", "legends": ["MEWTWO"]},
    {"id": "galactic", "name": "갤럭시단", "pool": ["mars", "jupiter", "saturn"],
     "boss": None, "legends": ["DIALGA", "PALKIA", "GIRATINA"]},
    {"id": "magma", "name": "마그마단", "pool": ["tabitha", "courtney"],
     "boss": "maxie", "legends": ["GROUDON"]},
    {"id": "aqua", "name": "아쿠아단", "pool": ["shelly", "matt"],
     "boss": "archie", "legends": ["KYOGRE"]},
    {"id": "plasma", "name": "플라즈마단", "pool": ["zinzolin", "colress"],
     "boss": "ghetsis", "legends": ["RESHIRAM", "ZEKROM", "KYUREM"]},
    {"id": "star", "name": "스타단", "pool": ["giacomo", "mela", "atticus", "ortega", "eri"],
     "boss": None, "legends": ["KORAIDON", "MIRAIDON"]},
    {"id": "aether", "name": "에테르재단·스컬단", "pool": ["plumeria", "guzma", "faba"],
     "boss": "lusamine", "legends": ["SOLGALEO", "LUNALA"]},
]


def build():
    with io.open(GYMS, encoding="utf-8") as f:
        trainers = dict((t["id"], t) for t in json.load(f)["trainers"])
    with io.open(DEX, encoding="utf-8") as f:
        species = dict((s["internal"], s) for s in json.load(f)["species"])
    teams = []
    for t in TEAMS:
        ids = list(t["pool"]) + ([t["boss"]] if t["boss"] else [])
        missing = [i for i in ids if i not in trainers]
        if missing:
            raise SystemExit("gyms.json 에 없는 트레이너: %s (%s)" % (missing, t["id"]))
        if len(t["pool"]) + (1 if t["boss"] else 0) < 3:
            raise SystemExit("간부 셋을 못 채운다: %s" % t["id"])
        bad = [s for s in t["legends"] if not (species.get(s) or {}).get("legendary")]
        if bad:
            raise SystemExit("전설이 아닌 종: %s (%s)" % (bad, t["id"]))
        teams.append({
            "id": t["id"], "name": t["name"], "pool": t["pool"], "boss": t["boss"],
            "legends": t["legends"],
            # 읽는 사람을 위한 이름 (서버는 안 쓴다 - gyms.json 에서 읽는다)
            "names": dict((i, "%s %s" % (trainers[i]["role"], trainers[i]["name"])) for i in ids),
            "legendNames": [species[s]["kr"] for s in t["legends"]],
        })
    return {"version": 1, "source": "tools/build_villains.py", "teams": teams}


def main():
    data = json.dumps(build(), ensure_ascii=False, indent=1, sort_keys=True)
    if "--check" in sys.argv:
        with io.open(OUT, encoding="utf-8") as f:
            same = f.read() == data
        print("villains.json: %s" % ("같다" if same else "다르다 (다시 돌릴 것)"))
        return 0 if same else 1
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(data)
    d = json.loads(data)
    print("villains.json: 조직 %d개 (%s)" % (len(d["teams"]), ", ".join(t["name"] for t in d["teams"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
