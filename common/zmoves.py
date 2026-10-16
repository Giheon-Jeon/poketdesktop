# -*- coding: utf-8 -*-
"""Z기술 (시즌 4) — 본가 썬·문 / 울트라썬·울트라문의 규칙.

    · 한 판에 한 번. Z크리스탈을 지닌 포켓몬이, 크리스탈과 **같은 타입의 기술 하나**를 Z기술로 쓴다.
    · 공격기: 원래 위력으로 Z위력이 정해진다 (table_power, 예외는 Z_POWER). 반드시 맞고,
      방어 중인 상대에게는 1/4 만 들어가고, 추가 효과가 없고, 한 번만 친다.
    · 변화기: Z효과(능력치 상승, 내려간 능력치 되돌리기, 회복 ...)가 먼저 나오고 원래 효과가 나간다.
    · 전용 Z기술: 전용 크리스탈 + 그 포켓몬 + 정해진 기술이면 그 기술이 전용 Z기술이 된다.
    · Z크리스탈은 지닌 도구다. 뺏기지도 떨어지지도 않는다 (held.stuck).

이 파일은 **자료와 '무엇으로 바뀌나'** 만 안다. 실제로 쓰는 것은 battle.Battle 이 한다
(Z파워 이벤트, 방어 뚫기, 한 판 한 번). held·attackfx 가 이 파일을 불러오므로 여기서는
그쪽을 불러오지 않는다.

아래 Z_POWER·_Z_STATUS 는 `python tools/add_zcrystals.py --tables` 가 뽑은 것이다
(쇼다운 moves.json 의 zMove). 손으로 고치지 말고 그쪽을 다시 돌릴 것.
"""

# 타입 -> 범용 Z기술의 도감 열쇠 앞부분. 도감에는 물리/특수가 따로 들어 있다
# ("BREAKNECKBLITZPHYSICAL" / "...SPECIAL" - PokeAPI 가 그렇게 준다). 한글 이름은 거기서 읽는다.
TYPE_Z = {
    "NORMAL": "BREAKNECKBLITZ", "FIGHTING": "ALLOUTPUMMELING", "FLYING": "SUPERSONICSKYSTRIKE",
    "POISON": "ACIDDOWNPOUR", "GROUND": "TECTONICRAGE", "ROCK": "CONTINENTALCRUSH",
    "BUG": "SAVAGESPINOUT", "GHOST": "NEVERENDINGNIGHTMARE", "STEEL": "CORKSCREWCRASH",
    "FIRE": "INFERNOOVERDRIVE", "WATER": "HYDROVORTEX", "GRASS": "BLOOMDOOM",
    "ELECTRIC": "GIGAVOLTHAVOC", "PSYCHIC": "SHATTEREDPSYCHE", "ICE": "SUBZEROSLAMMER",
    "DRAGON": "DEVASTATINGDRAKE", "DARK": "BLACKHOLEECLIPSE", "FAIRY": "TWINKLETACKLE",
}

# 타입 크리스탈: id -> (타입, 한글 이름)
_TYPE_CRYSTAL = {
    "NORMALIUMZ": ("NORMAL", "노말Z"), "FIRIUMZ": ("FIRE", "불꽃Z"), "WATERIUMZ": ("WATER", "물Z"),
    "ELECTRIUMZ": ("ELECTRIC", "전기Z"), "GRASSIUMZ": ("GRASS", "풀Z"), "ICIUMZ": ("ICE", "얼음Z"),
    "FIGHTINIUMZ": ("FIGHTING", "격투Z"), "POISONIUMZ": ("POISON", "독Z"),
    "GROUNDIUMZ": ("GROUND", "땅Z"), "FLYINIUMZ": ("FLYING", "비행Z"),
    "PSYCHIUMZ": ("PSYCHIC", "에스퍼Z"), "BUGINIUMZ": ("BUG", "벌레Z"), "ROCKIUMZ": ("ROCK", "바위Z"),
    "GHOSTIUMZ": ("GHOST", "고스트Z"), "DRAGONIUMZ": ("DRAGON", "드래곤Z"),
    "DARKINIUMZ": ("DARK", "악Z"), "STEELIUMZ": ("STEEL", "강철Z"), "FAIRIUMZ": ("FAIRY", "페어리Z"),
}
CRYSTAL_TYPE = dict((k, v[0]) for k, v in _TYPE_CRYSTAL.items())

# 전용 크리스탈: id -> 누가, 어떤 기술을, 무엇으로. 그 폼이 이 게임에 없는 셋(알로라 라이츄,
# 지우의 피카츄, 울트라네크로즈마)은 뺐다.
EXCLUSIVE = {
    "PIKANIUMZ": {"kr": "피카츄Z", "species": ("PIKACHU",), "base": "VOLTTACKLE", "move": "CATASTROPIKA"},
    "EEVIUMZ": {"kr": "이브이Z", "species": ("EEVEE",), "base": "LASTRESORT", "move": "EXTREMEEVOBOOST"},
    "SNORLIUMZ": {"kr": "잠만보Z", "species": ("SNORLAX",), "base": "GIGAIMPACT",
                  "move": "PULVERIZINGPANCAKE"},
    "MEWNIUMZ": {"kr": "뮤Z", "species": ("MEW",), "base": "PSYCHIC", "move": "GENESISSUPERNOVA"},
    "DECIDIUMZ": {"kr": "모크나이퍼Z", "species": ("DECIDUEYE",), "base": "SPIRITSHACKLE",
                  "move": "SINISTERARROWRAID"},
    "INCINIUMZ": {"kr": "어흥염Z", "species": ("INCINEROAR",), "base": "DARKESTLARIAT",
                  "move": "MALICIOUSMOONSAULT"},
    "PRIMARIUMZ": {"kr": "누리레느Z", "species": ("PRIMARINA",), "base": "SPARKLINGARIA",
                   "move": "OCEANICOPERETTA"},
    "TAPUNIUMZ": {"kr": "카푸Z", "species": ("TAPUKOKO", "TAPULELE", "TAPUBULU", "TAPUFINI"),
                  "base": "NATURESMADNESS", "move": "GUARDIANOFALOLA"},
    "MARSHADIUMZ": {"kr": "마샤도Z", "species": ("MARSHADOW",), "base": "SPECTRALTHIEF",
                    "move": "SOULSTEALING7STARSTRIKE"},
    "SOLGANIUMZ": {"kr": "솔가레오Z", "species": ("SOLGALEO",), "base": "SUNSTEELSTRIKE",
                   "move": "SEARINGSUNRAZESMASH"},
    "LUNALIUMZ": {"kr": "루나아라Z", "species": ("LUNALA",), "base": "MOONGEISTBEAM",
                  "move": "MENACINGMOONRAZEMAELSTROM"},
    "MIMIKIUMZ": {"kr": "따라큐Z", "species": ("MIMIKYU",), "base": "PLAYROUGH",
                  "move": "LETSSNUGGLEFOREVER"},
    "LYCANIUMZ": {"kr": "루가루암Z", "species": ("LYCANROC",), "base": "STONEEDGE",
                  "move": "SPLINTEREDSTORMSHARDS"},
    "KOMMONIUMZ": {"kr": "짜랑고우거Z", "species": ("KOMMOO",), "base": "CLANGINGSCALES",
                   "move": "CLANGOROUSSOULBLAZE"},
}

# 지닐 수 있는 Z크리스탈 전부: id -> 한글 이름 (held.normalize·held.name 이 본다)
CRYSTALS = dict((k, v[1]) for k, v in _TYPE_CRYSTAL.items())
CRYSTALS.update((k, v["kr"]) for k, v in EXCLUSIVE.items())

GUARDIAN = "GUARDIANOFALOLA"       # 알로라의수호자: 상대의 지금 체력의 3/4
GUARDIAN_RATE = 0.75

# --- 아래 둘은 tools/add_zcrystals.py --tables 가 뽑았다 ---------------------------------
# 표(table_power)와 다르거나, 원래 위력이 정해져 있지 않은 기술의 Z위력.
Z_POWER = {
    "BONERUSH": 140, "BULLETSEED": 140, "COREENFORCER": 140, "CRUSHGRIP": 190, "DOUBLEHIT": 140,
    "DOUBLEIRONBASH": 180, "ELECTROBALL": 160, "ENDEAVOR": 160, "FINALGAMBIT": 180, "FISSURE": 180,
    "FLAIL": 160, "FLYINGPRESS": 170, "FRUSTRATION": 160, "GEARGRIND": 180, "GRASSKNOT": 160,
    "GUILLOTINE": 180, "GYROBALL": 160, "HEATCRASH": 160, "HEAVYSLAM": 160, "HEX": 160,
    "HORNDRILL": 180, "ICICLESPEAR": 140, "LANDSWRATH": 185, "LOWKICK": 160, "MAGNITUDE": 140,
    "MEGADRAIN": 120, "MULTIATTACK": 185, "NATURALGIFT": 160, "PINMISSILE": 140, "POWERTRIP": 160,
    "PUNISHMENT": 160, "RETURN": 160, "REVERSAL": 160, "ROCKBLAST": 140, "SCALESHOT": 140,
    "SHEERCOLD": 180, "STOREDPOWER": 160, "SURGINGSTRIKES": 140, "TACHYONCUTTER": 180, "TAILSLAP": 140,
    "TERRAINPULSE": 160, "THOUSANDARROWS": 180, "TRIPLEAXEL": 120, "TRIPLEKICK": 120, "TRUMPCARD": 160,
    "VCREATE": 220, "WEATHERBALL": 160, "WRINGOUT": 190,
}

# 변화기의 Z효과. ("효과", "기술 열쇠들"). 효과는 "atk+1,def+1" 같은 능력치 상승이거나
#   clearnegativeboost  내려간 능력치를 되돌린다        heal             체력을 전부 회복한다
#   crit2               급소에 맞기 쉬워진다 (2단계)     curse            고스트면 회복, 아니면 공격 +1
#   healreplacement     다음에 나오는 포켓몬을 회복 (이 엔진에는 없어 아무 일도 없다)
#   redirect            자기에게 기술을 모은다 (1:1 이라 아무 일도 없다)
_Z_STATUS = (
    ("clearnegativeboost",
     "ACIDARMOR AGILITY AMNESIA ATTRACT AUTOTOMIZE BARRIER BATONPASS CALMMIND COIL COTTONGUARD "
     "COTTONSPORE DARKVOID DISABLE DOUBLETEAM DRAGONDANCE ENDURE FLORALHEALING FOLLOWME HEALORDER "
     "HEALPULSE HELPINGHAND IRONDEFENSE KINGSSHIELD LEECHSEED MILKDRINK MINIMIZE MOONLIGHT MORNINGSUN "
     "NASTYPLOT PERISHSONG PROTECT QUIVERDANCE RAGEPOWDER RECOVER REST ROCKPOLISH ROOST SHEDTAIL "
     "SHELLSMASH SHIFTGEAR SHOREUP SLACKOFF SOFTBOILED SPORE SUBSTITUTE SWAGGER SWALLOW SWORDSDANCE "
     "SYNTHESIS TAILGLOW"),
    ("def+1",
     "AQUARING BABYDOLLEYES BANEFULBUNKER BLOCK CHARM DEFENDORDER FAIRYLOCK FEATHERDANCE FLOWERSHIELD "
     "GRASSYTERRAIN GROWL HARDEN MATBLOCK NOBLEROAR PAINSPLIT PLAYNICE POISONGAS POISONPOWDER "
     "QUICKGUARD REFLECT ROAR SPIDERWEB SPIKES SPIKYSHIELD STEALTHROCK STRENGTHSAP TEARFULLOOK TICKLE "
     "TORMENT TOXIC TOXICSPIKES VENOMDRENCH WIDEGUARD WITHDRAW"),
    ("spe+1",
     "AFTERYOU AURORAVEIL ELECTRICTERRAIN ENCORE GASTROACID GRASSWHISTLE GUARDSPLIT GUARDSWAP HAIL "
     "HYPNOSIS LOCKON LOVELYKISS POWERSPLIT POWERSWAP QUASH RAINDANCE ROLEPLAY SAFEGUARD SANDSTORM "
     "SCARYFACE SING SKILLSWAP SLEEPPOWDER SPEEDSWAP STICKYWEB STRINGSHOT SUNNYDAY SUPERSONIC "
     "TOXICTHREAD WORRYSEED YAWN"),
    ("spd+1",
     "CHARGE CONFIDE COSMICPOWER CRAFTYSHIELD EERIEIMPULSE ENTRAINMENT FLATTER GLARE INGRAIN "
     "LIGHTSCREEN MAGICROOM MAGNETICFLUX MEANLOOK MISTYTERRAIN MUDSPORT SPOTLIGHT STUNSPORE THUNDERWAVE "
     "WATERSPORT WHIRLWIND WISH WONDERROOM"),
    ("spa+1",
     "CONFUSERAY ELECTRIFY EMBARGO FAKETEARS GEARUP GRAVITY GROWTH INSTRUCT IONDELUGE METALSOUND "
     "MINDREADER MIRACLEEYE NIGHTMARE PSYCHICTERRAIN REFLECTTYPE SIMPLEBEAM SOAK SWEETKISS TEETERDANCE "
     "TELEKINESIS"),
    ("atk+1",
     "BULKUP HONECLAWS HOWL LASERFOCUS LEER MEDITATE ODORSLEUTH POWERTRICK ROTOTILLER SCREECH SHARPEN "
     "TAILWHIP TAUNT TOPSYTURVY WILLOWISP WORKUP"),
    ("heal",
     "AROMATHERAPY BELLYDRUM CONVERSION2 HAZE HEALBELL MIST PSYCHUP REFRESH SPITE STOCKPILE TELEPORT "
     "TRANSFORM"),
    ("atk+1,def+1,spa+1,spd+1,spe+1",
     "CELEBRATE CONVERSION FORESTSCURSE GEOMANCY HAPPYHOUR HOLDHANDS PURIFY SKETCH TRICKORTREAT"),
    ("eva+1",
     "CAMOUFLAGE DETECT FLASH KINESIS LUCKYCHANT MAGNETRISE SANDATTACK SMOKESCREEN"),
    ("acc+1",
     "COPYCAT DEFENSECURL DEFOG FOCUSENERGY MIMIC SWEETSCENT TRICKROOM"),
    ("spe+2",
     "ALLYSWITCH BESTOW MEFIRST RECYCLE SNATCH SWITCHEROO TRICK"),
    ("crit2",
     "ACUPRESSURE FORESIGHT HEARTSWAP SLEEPTALK TAILWIND"),
    ("spd+2",
     "AROMATICMIST CAPTIVATE IMPRISON MAGICCOAT POWDER"),
    ("healreplacement",
     "MEMENTO PARTINGSHOT"),
    ("redirect",
     "DESTINYBOND GRUDGE"),
    ("spa+2",
     "HEALBLOCK PSYCHOSHIFT"),
    ("atk+2",
     "MIRRORMOVE"),
    ("atk+3",
     "SPLASH"),
    ("curse",
     "CURSE"),
)
# -----------------------------------------------------------------------------------

Z_STATUS = {}
for _tag, _keys in _Z_STATUS:
    for _k in _keys.split():
        Z_STATUS[_k] = _tag
STAT_KEYS = ("atk", "def", "spa", "spd", "spe", "acc", "eva")


def _key(move):
    return "".join(c for c in ((move or {}).get("en") or "").upper() if c.isalnum())


def is_crystal(item):
    return bool(item) and item in CRYSTALS


def name(item):
    return CRYSTALS.get(item)


def table_power(bp):
    """원래 위력 -> Z위력 (본가 표)."""
    bp = int(bp or 0)
    if bp >= 140:
        return 200
    if bp >= 130:
        return 195
    if bp >= 120:
        return 190
    if bp >= 110:
        return 185
    if bp >= 100:
        return 180
    if bp >= 90:
        return 175
    if bp >= 80:
        return 160
    if bp >= 70:
        return 140
    if bp >= 60:
        return 120
    return 100


def power_of(move):
    """이 공격기를 Z기술로 쓸 때의 위력."""
    k = _key(move)
    if k in Z_POWER:
        return Z_POWER[k]
    return table_power((move or {}).get("power"))


def boosts(tag):
    """'atk+1,def+1' -> [("atk", 1), ("def", 1)]. 능력치 상승이 아니면 빈 목록."""
    out = []
    for bit in (tag or "").split(","):
        for s in STAT_KEYS:
            if bit.startswith(s + "+"):
                out.append((s, int(bit[len(s) + 1:])))
    return out


def effect_text(tag):
    """Z효과를 사람이 읽는 말로 (화면의 단추 설명)."""
    if not tag:
        return ""
    kr = {"atk": "공격", "def": "방어", "spa": "특수공격", "spd": "특수방어", "spe": "스피드",
          "acc": "명중률", "eva": "회피율"}
    b = boosts(tag)
    if b:
        if len(b) == 5 and len(set(n for _s, n in b)) == 1:
            return "모든 능력치 +%d" % b[0][1]
        return ", ".join("%s +%d" % (kr[s], n) for s, n in b)
    return {"clearnegativeboost": "내려간 능력치를 되돌린다", "heal": "체력을 전부 회복한다",
            "crit2": "급소에 맞기 쉬워진다", "curse": "고스트 타입이면 체력 회복, 아니면 공격 +1",
            }.get(tag, "")


def can_power(dex, mon, held, key, move):
    """이 포켓몬이 이 도구로 이 기술을 Z기술로 쓸 수 있는가 (변화기 포함)."""
    if not is_crystal(held) or not move:
        return False
    own = EXCLUSIVE.get(held)
    if own:
        return (mon or {}).get("species") in own["species"] and key == own["base"] \
            and bool(dex.move(own["move"]))
    if move.get("type") != CRYSTAL_TYPE.get(held):
        return False
    if move.get("cat") == "status":
        return True
    return bool(move.get("power")) or _key(move) in Z_POWER


def options(dex, mon, held, keys):
    """keys 가운데 Z기술로 쓸 수 있는 것."""
    return [k for k in keys if can_power(dex, mon, held, k, dex.move(k))]


def convert(dex, mon, held, key, move, phys=None, target_hp=0):
    """Z기술로 바꾼 것. 못 바꾸면 None.

    돌려주는 것:
      공격기  {"status": False, "key": Z기술 열쇠, "name": 한글 이름, "move": 실제로 나갈 기술}
      변화기  {"status": True, "name": "Z" + 원래 이름, "effect": Z효과 꼬리표 또는 None}
              (전용 변화 Z기술 - 나인이볼부스트 - 은 "own" 에 그 기술을 싣는다)

    phys 는 물리로 나가는가 (포톤가이저처럼 쓸 때 정해지는 기술은 부르는 쪽이 안다).
    """
    if not can_power(dex, mon, held, key, move):
        return None
    own = EXCLUSIVE.get(held)
    if own:
        zm = dex.move(own["move"]) or {}
        if zm.get("cat") == "status":
            return {"status": True, "name": zm.get("kr") or own["move"], "effect": None,
                    "own": dict(zm), "key": own["move"]}
        # target 은 '한 마리' 로 둔다 - 도감에 여럿을 노리는 기술로 적힌 것(브레이징소울비트)이
        # 와이드가드에 통째로 막히고 Z파워만 닳았다. Z기술은 방어를 뚫는다.
        d = dict(zm, acc=0, pri=0, flags=["protect"], _z=True, target=10)
        if own["move"] == GUARDIAN:
            d["power"] = 1
            d["_fixed"] = max(1, int(target_hp * GUARDIAN_RATE))
        return {"status": False, "key": own["move"], "name": zm.get("kr") or own["move"], "move": d}
    if move.get("cat") == "status":
        return {"status": True, "name": "Z" + (move.get("kr") or key),
                "effect": Z_STATUS.get(_key(move)), "key": key}
    t = CRYSTAL_TYPE[held]
    if phys is None:
        phys = move.get("cat") == "physical"
    zkey = TYPE_Z[t] + ("PHYSICAL" if phys else "SPECIAL")
    base = dex.move(zkey) or {}
    d = {"kr": base.get("kr") or TYPE_Z[t], "en": base.get("en") or TYPE_Z[t], "type": t,
         "cat": "physical" if phys else "special", "power": power_of(move), "acc": 0, "pp": 1,
         "pri": 0, "hits": [1, 1], "stat": [], "ail": None, "ailChance": 0, "statChance": 0,
         "statSelf": False, "drain": 0, "heal": 0, "flinch": 0, "crit": 0, "eff": 0,
         "flags": ["protect"], "target": 10, "desc": base.get("desc") or "", "_z": True}
    return {"status": False, "key": zkey, "name": d["kr"], "move": d}
