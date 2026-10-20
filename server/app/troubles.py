# -*- coding: utf-8 -*-
"""야생 배틀이 앱에서 끊긴 것을 서버가 안다 (1.13.3, 게시판 #266 레드 36세 · #280 니뉴).

예전에는 앱이 배틀을 접으면 까닭이 그 사람 PC 의 poketdesktop.log 에만 남아서, 제보가 오면 그 파일을 열어
달라고 해야 했다 - 좋은 경험이 아니다. 두 길로 서버에 남긴다 (trouble 표):

  1. **서버가 스스로 안다** (source='server'). 진행 중(active)인 판을 배틀 엔진이 아닌 다른 길이 닫으면, 앱이
     그 판을 끝까지 몰고 가지 않았다는 뜻이다 - 새 배틀이 옛 판을 닫았다 · 시간이 지났다 · 야생이 사라졌다 ·
     앱이 야생을 놓아줬다 · 배틀 밖에서 볼로 잡았다. **옛 앱(1.13.2 이하)도 잡힌다.** (레드 36세의 10/19 08:24
     판이 이것 - 네 번째 포켓몬이 나온 뒤 한 번도 안 움직였고, 8분 뒤 새 배틀이 그 판을 닫았다.)
  2. **앱이 알린다** (source='client', 1.13.3~). 배틀을 접은 까닭, 그때의 상태, 오류 내용, 버전, OS.
     경로는 앱이 파일 이름만 남기고 보낸다 (윈도우 사용자 이름이 경로에 들어 있다).

server_error 와 따로 둔다 - 거기 적으면 /api/health 의 오류 수가 튀어서 keepalive 워크플로가 실패한다.
2주 지난 것은 지운다. 보는 법: 서버에서 deploy/troubles.py 를 돌린다 (읽기만).

**남기다가 터지면 안 된다.** 배틀을 시작하는 길 한가운데에서 부르므로 전부 감싸고 실패하면 조용히 넘어간다.
"""
import datetime
import json
import random
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from . import db, deps

router = APIRouter()

KEEP_DAYS = 14
CLIENT_PER_HOUR = 30            # 한 사람이 한 시간에 보낼 수 있는 앱 알림 (넘으면 버린다)
MSG_MAX = 300
DETAIL_MAX = 4000
PRUNE_CHANCE = 0.02             # 남길 때 가끔 오래된 것을 지운다 (매번 지우면 배틀 시작마다 쓰기가 하나 는다)

# 진행 중이던 판이 어느 길로 닫혔나 (kind = 'left_' + 이것)
HOW_KR = {
    "new_battle": "새 배틀을 걸어 옛 판을 닫음",
    "party_changed": "싸우던 포켓몬이 파티에 없어 옛 판을 닫음",
    "expired": "제한 시간(15분)이 지난 판을 앱이 이어 가려 함",
    "stale": "야생이 없거나 시간이 지난 판을 정리함",
    "wild_expired": "야생의 시간이 다 되어 닫힘",
    "wild_flee": "앱이 야생을 놓아주며 닫힘",
    "field_catch": "배틀 밖에서 볼로 잡아 닫힘",
}


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def record(uid, source, kind, ref=None, message="", detail="", version="", os_=""):
    """하나 남긴다. 실패해도 조용히 넘어간다."""
    try:
        db.run("INSERT INTO trouble (at, user_id, source, kind, ref, version, os, message, detail)"
               " VALUES (?,?,?,?,?,?,?,?,?)",
               (_now().isoformat(), uid, (source or "")[:10], (kind or "?")[:40], ref,
                (version or "")[:20], (os_ or "")[:60], (message or "")[:MSG_MAX],
                (detail or "")[-DETAIL_MAX:]))
        if random.random() < PRUNE_CHANCE:
            prune()
    except Exception:                                       # noqa: BLE001
        pass


def prune(now=None):
    cut = ((now or _now()) - datetime.timedelta(days=KEEP_DAYS)).isoformat()
    db.run("DELETE FROM trouble WHERE at < ?", (cut,))


def _js(raw):
    try:
        return json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}


def battle_left(row, how):
    """진행 중이던 판이 배틀 엔진 밖에서 닫힌다 = 앱이 그 판을 끝까지 몰고 가지 않았다. 닫기 **전에** 부른다."""
    try:
        me, foe = _js(row["me"]), _js(row["foe"])
        mm, fm = me.get("mon") or {}, foe.get("mon") or {}
        try:
            fainted = len(json.loads(row["fainted"] or "[]"))
        except (KeyError, IndexError, TypeError, ValueError):
            fainted = 0
        try:
            age = int((_now() - datetime.datetime.fromisoformat(row["created_at"])).total_seconds())
        except (TypeError, ValueError):
            age = -1
        msg = "%s · 턴 %s · 쓰러진 %d · 시작 뒤 %d초 · 나 %s(HP %s) · 상대 %s Lv%s(HP %s)" % (
            HOW_KR.get(how, how), row["turn"], fainted, age, mm.get("species"), me.get("hp"),
            fm.get("species"), fm.get("level"), foe.get("hp"))
        record(row["user_id"], "server", "left_" + how, row["id"], msg)
    except Exception:                                       # noqa: BLE001
        pass


def close_active(uid, where, params, result, how):
    """조건에 맞는 진행 중인 판을 닫고, 닫기 전에 하나씩 남긴다. where 는 'AND ...' 꼴."""
    rows = db.q("SELECT * FROM battle WHERE user_id=? AND state='active' " + where, (uid,) + tuple(params))
    for r in rows:
        battle_left(r, how)
    if rows:
        db.run("UPDATE battle SET state='done', result=? WHERE user_id=? AND state='active' " + where,
               (result, uid) + tuple(params))
    return len(rows)


# ---------------------------------------------------------------- 앱이 알린다 (1.13.3~)
class TroubleIn(BaseModel):
    kind: str
    ref: Optional[int] = None
    message: str = ""
    detail: str = ""
    version: str = ""
    os: str = ""


@router.post("/api/client/trouble")
def client_trouble(body: TroubleIn, ctx=Depends(deps.current)):
    """앱이 배틀을 접었다 (desktop_battle.abort). 한 사람이 한 시간에 CLIENT_PER_HOUR 개까지만 받는다."""
    uid = ctx["user"]["id"]
    since = (_now() - datetime.timedelta(hours=1)).isoformat()
    n = db.q1("SELECT COUNT(*) n FROM trouble WHERE user_id=? AND source='client' AND at>=?", (uid, since))
    if n and n["n"] >= CLIENT_PER_HOUR:
        return {"ok": False}
    record(uid, "client", body.kind, body.ref, body.message, body.detail, body.version, body.os)
    return {"ok": True}
