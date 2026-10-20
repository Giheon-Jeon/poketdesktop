# -*- coding: utf-8 -*-
"""파티 프리셋 (1.10.3) — 데리고 다니는 파티를 몇 벌 두고 번호로 갈아탄다.

    GET  /api/party                 프리셋 목록과 지금 쓰는 번호
    POST /api/party/{no}/use        그 번호의 파티로 갈아탄다
    POST /api/party/{no}/name       이름을 붙인다 (비우면 기본 이름으로)

## 왜

랭크에 내보낼 여섯, 레이드에 데려갈 여섯, 바탕화면에 풀어 둘 여섯이 서로 다르다. 그때마다
박스에서 꺼내고 넣기를 되풀이해야 했다. 파티를 COUNT 벌까지 두고 번호를 눌러 바꾼다 -
'랭크', '레이드' 같은 이름도 붙일 수 있다.

## 지금 데리고 다니는 파티가 곧 '지금 번호' 의 파티다

따로 저장하는 단추가 없다. 다른 번호로 갈아탈 때 **지금 파티를 지금 번호에 적어 두고**, 가려는
번호에 적혀 있던 파티를 꺼낸다. 그래서 번호를 오가도 잃는 것이 없다. 포켓몬을 잡아 빈 자리에
들어온 것, 박스에서 꺼내 넣은 것, 순서를 바꾼 것 - 전부 '지금 번호' 에서 일어난 일이다.

**한 번도 안 쓴 번호로 가면 지금 파티를 그대로 들고 간다.** 바탕화면이 갑자기 텅 비지 않는다.
거기서 바꾸기 시작하면 그 번호만의 파티가 된다.

## 지키는 것

- **알도 프리셋에 든다** (1.13.3, 게시판 #289 Narud · 사용자 결정 '알도 자유롭게'). 갈아타면 그 번호의 알을
  데리고 다니고, 그 번호에 없는 알은 알 보관함에 내려놓는다 (데리고 다닐 때만 자라므로 알린다). 예전에는 알이
  프리셋에 안 들고 제자리를 지켜서, 알을 데리고 다니며 관장용 파티로 바꾸려면 알을 내렸다 다시 올려야 했다.
  적는 모양: 포켓몬은 id(정수), 알은 "egg:알id". 다른 번호에 있던 알이 그사이 깼으면 태어난 포켓몬이 그 자리를
  잇는다. **예전 모양(포켓몬 id 만, 1.13.2 까지)으로 적힌 번호**로 갈 때는 그때 규칙대로 데리고 다니던 알을
  그대로 둔다 (들어갈 자리만큼) - 떠날 때부터 새 모양으로 적힌다.
- 그사이 놓아준 포켓몬은 조용히 빠진다. 한 포켓몬이 여러 번호에 들어 있어도 된다.
- 박스로 돌아가는 포켓몬은 원래 있던 박스로 간다 (deps.to_box). 꺼내는 일을 **먼저** 한다 -
  박스가 꽉 찬 사람도 자리를 맞바꿀 수 있다.
- 전설·환상 한 마리 제한은 배틀에 나갈 때 건다 (pvp.split_restricted). 여기서는 안 본다.
- 탐험에 나가 있는 포켓몬(1.10.4)은 꺼내지 않는다. 그 포켓몬만 빼고 갈아타고, 뺐다고 알린다.
- 랭크 팀 등록(pvp.set_team)과는 따로다. 등록한 랭크 팀이 있으면 랜덤 배틀은 여전히 그 팀으로 싸운다.
"""
import datetime
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from . import config, db, deps

router = APIRouter()

COUNT = 5                   # 프리셋 수
NAME_MAX = 4                # 이름 글자 수. 탭 다섯이 포켓몬 관리 창의 한 줄에 들어가야 한다 ('바탕화면')


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def default_name(no):
    return "파티 %d" % no


def _rows(uid):
    return dict((r["no"], r) for r in db.q("SELECT * FROM party_preset WHERE user_id=?", (uid,)))


def _active(rows):
    """지금 쓰는 번호. 적힌 것이 없으면 1번이다 (프리셋을 한 번도 안 쓴 사람)."""
    for no in sorted(rows):
        if rows[no]["active"] and 1 <= no <= COUNT:
            return no
    return 1


EGG = "egg:"                # 프리셋에 적는 알의 모양 ("egg:12")


def egg_token(eid):
    return "%s%d" % (EGG, int(eid))


def egg_id(tok):
    """알이면 알 id, 포켓몬이면 None."""
    if isinstance(tok, str) and tok.startswith(EGG) and tok[len(EGG):].isdigit():
        return int(tok[len(EGG):])
    return None


def desktop_ids(uid):
    """지금 데리고 다니는 포켓몬의 id (자리 순). 알은 빼고."""
    return [r["id"] for r in db.q(
        "SELECT id FROM pokemon WHERE user_id=? AND on_desktop=1 ORDER BY slot, id", (uid,))]


def desktop_members(uid):
    """지금 데리고 다니는 것 전부 (자리 순) - 포켓몬 id 와 'egg:알id'. 자리 번호가 없는 옛 알은 맨 뒤."""
    rows = [(r["slot"], 0, r["id"], r["id"]) for r in db.q(
        "SELECT id, slot FROM pokemon WHERE user_id=? AND on_desktop=1", (uid,))]
    rows += [(r["slot"], 1, r["id"], egg_token(r["id"])) for r in db.q(
        "SELECT id, slot FROM egg WHERE user_id=? AND on_desktop=1 AND hatched_at IS NULL", (uid,))]
    rows.sort(key=lambda x: (x[0] is None, x[0] or 0, x[1], x[2]))
    return [t for _s, _k, _i, t in rows]


def _stored(row):
    """적힌 것 (포켓몬 id · 'egg:알id', 순서대로)과 예전 모양인지. 예전 모양 = 포켓몬 id 만 적던 1.13.2 까지."""
    try:
        raw = json.loads(row["ids"] or "[]")
    except ValueError:
        raw = []
    legacy = isinstance(raw, list)
    ids = raw if legacy else (raw.get("members") if isinstance(raw, dict) else [])
    out = []
    for i in ids if isinstance(ids, list) else []:
        if (isinstance(i, int) or egg_id(i) is not None) and i not in out:
            out.append(i)
    return out[:config.MAX_PARTY], legacy


def _owned(uid, ids):
    """그 가운데 아직 내 것만 (순서는 그대로). 놓아준 포켓몬은 빠지고, 그사이 깬 알은 태어난 포켓몬이 잇는다."""
    if not ids:
        return []
    mons = [i for i in ids if isinstance(i, int)]
    mine = set()
    if mons:
        marks = ",".join("?" * len(mons))
        mine = set(r["id"] for r in db.q(
            "SELECT id FROM pokemon WHERE user_id=? AND id IN (%s)" % marks, (uid,) + tuple(mons)))
    out = []
    for i in ids:
        eid = egg_id(i)
        if eid is None:
            if i in mine and i not in out:
                out.append(i)
            continue
        e = db.q1("SELECT hatched_at, pokemon_id FROM egg WHERE id=? AND user_id=?", (eid, uid))
        if e is None:
            continue
        if e["hatched_at"] is None:
            out.append(i)
        elif e["pokemon_id"] and e["pokemon_id"] not in out and e["pokemon_id"] not in ids and \
                db.q1("SELECT id FROM pokemon WHERE id=? AND user_id=?", (e["pokemon_id"], uid)):
            out.append(e["pokemon_id"])
    return out


def state(uid):
    """화면에 줄 것. 지금 번호의 내용은 적어 둔 것이 아니라 **지금 데리고 다니는 것**이다."""
    rows = _rows(uid)
    cur = _active(rows)
    live = desktop_members(uid)
    out = []
    for no in range(1, COUNT + 1):
        r = rows.get(no)
        if no == cur:
            ids, saved = live, True
        elif r is not None and r["saved"]:
            ids, saved = _owned(uid, _stored(r)[0]), True
        else:
            ids, saved = [], False
        name = (r["name"] if r is not None else None) or ""
        # ids 는 포켓몬만 (옛 화면이 정수로 읽는다), 알은 eggs 에 따로. size 는 둘 다 센다.
        out.append({"no": no, "name": name or default_name(no), "named": bool(name),
                    "active": no == cur, "saved": saved, "size": len(ids),
                    "ids": [i for i in ids if egg_id(i) is None],
                    "eggs": [egg_id(i) for i in ids if egg_id(i) is not None]})
    return {"active": cur, "count": COUNT, "nameMax": NAME_MAX, "max": config.MAX_PARTY, "presets": out}


def _check(no):
    try:
        no = int(no)
    except (TypeError, ValueError):
        no = 0
    if not 1 <= no <= COUNT:
        raise HTTPException(404, "그런 파티 번호가 없습니다.")
    return no


def _write(uid, no, ids, active):
    """새 모양({"v": 2, "members": [...]})으로 적는다 - 알까지 든다."""
    db.run("INSERT INTO party_preset (user_id, no, ids, active, saved, updated_at) VALUES (?,?,?,?,1,?)"
           " ON CONFLICT(user_id, no) DO UPDATE SET ids=excluded.ids, active=excluded.active,"
           " saved=1, updated_at=excluded.updated_at",
           (uid, no, json.dumps({"v": 2, "members": list(ids)}), 1 if active else 0, _now()))


def _apply(uid, live, want):
    """데리고 다니는 것을 want 로 바꾼다 (자리 0~5 를 순서대로). 내려놓은 알의 수를 돌려준다."""
    # 꺼내는 일이 먼저다. 박스가 꽉 찬 사람도, 나온 자리에 들어갈 것이 들어간다.
    for i, tok in enumerate(want):
        eid = egg_id(tok)
        if eid is None:
            db.run("UPDATE pokemon SET on_desktop=1, slot=? WHERE id=? AND user_id=?", (i, tok, uid))
        else:
            db.run("UPDATE egg SET on_desktop=1, slot=? WHERE id=? AND user_id=? AND hatched_at IS NULL",
                   (i, eid, uid))
    keep = set(want)
    down = 0
    for tok in live:
        if tok in keep:
            continue
        eid = egg_id(tok)
        if eid is not None:
            db.run("UPDATE egg SET on_desktop=0, slot=NULL WHERE id=? AND user_id=?", (eid, uid))
            down += 1
            continue
        row = db.q1("SELECT box FROM pokemon WHERE id=? AND user_id=?", (tok, uid))
        if row is not None:
            deps.to_box(uid, tok, prefer=(row["box"] if "box" in row.keys() else 0) or 0)
    return down


def use(uid, no):
    """그 번호의 파티로 갈아탄다."""
    no = _check(no)
    rows = _rows(uid)
    cur = _active(rows)
    if no == cur:
        return dict(state(uid), ok=True, changed=False, message="")
    live = desktop_members(uid)
    row = rows.get(no)
    fresh = row is None or not row["saved"]       # 한 번도 안 쓴 번호: 지금 파티를 들고 간다
    legacy = False
    if fresh:
        want = live
    else:
        stored, legacy = _stored(row)
        want = _owned(uid, stored)
    # 탐험에 나가 있는 포켓몬은 못 꺼낸다 (1.10.4). 그 포켓몬만 빼고 갈아탄다 - 까닭은 아래에서 알린다.
    away = 0
    if not fresh:
        from . import expedition
        out_now = expedition.away_ids(uid)
        away = len([i for i in want if i in out_now])
        want = [i for i in want if i not in out_now]
        if legacy:
            # 예전 모양(알이 프리셋에 안 들던 때)으로 적힌 번호: 그때처럼 데리고 다니던 알은 그대로 둔다
            room = config.MAX_PARTY - len(want)
            want = want + [t for t in live if egg_id(t) is not None][:max(0, room)]
    name = (row["name"] if row is not None else None) or default_name(no)
    _write(uid, cur, live, False)                 # 지금 파티를 지금 번호에 적어 둔다
    down = 0
    if not fresh:
        down = _apply(uid, live, want)
    _write(uid, no, want, True)
    # 이름에 조사를 붙이지 않는다 (사람이 지은 이름이라 '을/를' 을 맞출 수 없다)
    if fresh:
        message = "파티를 바꿨습니다: [%s] - 처음 쓰는 번호라 지금 파티를 그대로 가져왔습니다." % name
    elif want:
        message = "파티를 바꿨습니다: [%s]" % name
    else:
        message = "파티를 바꿨습니다: [%s] - 비어 있는 파티입니다." % name
    if away:
        message += " (탐험에 나가 있는 %d마리는 빼고 꺼냈습니다.)" % away
    if down:
        message += " (그 파티에 없는 알 %d개는 알 보관함에 내려놓았습니다 - 데리고 다닐 때만 자랍니다.)" % down
    return dict(state(uid), ok=True, changed=not fresh, message=message)


def rename(uid, no, name):
    no = _check(no)
    text = " ".join((name or "").split())
    if len(text) > NAME_MAX:
        raise HTTPException(400, "파티 이름은 %d자까지입니다." % NAME_MAX)
    rows = _rows(uid)
    cur = _active(rows)
    if no in rows:
        db.run("UPDATE party_preset SET name=? WHERE user_id=? AND no=?", (text or None, uid, no))
    else:
        # 아직 줄이 없는 번호. 내용은 그대로 '안 쓴 번호' 로 두고 이름만 적는다
        # (지금 번호라면 active 를 같이 적는다 - 줄이 생기면 그 줄이 '지금 번호' 를 정한다).
        db.run("INSERT INTO party_preset (user_id, no, name, ids, active, saved, updated_at)"
               " VALUES (?,?,?,'[]',?,0,?)", (uid, no, text or None, 1 if no == cur else 0, _now()))
        if no != cur and cur not in rows:
            db.run("INSERT INTO party_preset (user_id, no, ids, active, saved, updated_at)"
                   " VALUES (?,?,'[]',1,0,?)", (uid, cur, _now()))
    return dict(state(uid), ok=True,
                message="파티 이름을 바꿨습니다: [%s]" % (text or default_name(no)))


class NameIn(BaseModel):
    name: str = ""


@router.get("/api/party")
def get(ctx=Depends(deps.current)):
    return state(ctx["user"]["id"])


@router.post("/api/party/{no}/use")
def post_use(no: int, ctx=Depends(deps.current)):
    return use(ctx["user"]["id"], no)


@router.post("/api/party/{no}/name")
def post_name(no: int, body: NameIn, ctx=Depends(deps.current)):
    return rename(ctx["user"]["id"], no, body.name)
