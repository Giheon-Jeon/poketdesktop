# -*- coding: utf-8 -*-
"""야생 배틀이 앱에서 끊긴 기록을 본다 (1.13.3, server/app/troubles.py). **읽기만 한다.**

    ssh -i <키> ubuntu@<서버> 'docker exec -i poketdesktop-server python -' < deploy/troubles.py

맨 위의 NICK 에 닉네임을 넣으면 그 사람 것만 (정확히 같은 닉네임). HOURS 는 얼마나 거슬러 볼지.

  source=server  서버가 알아챘다: 진행 중이던 판이 배틀 엔진 밖에서 닫혔다 (left_new_battle · left_expired ...).
                 옛 앱도 잡힌다. 메시지에 턴 · 쓰러진 수 · 시작 뒤 몇 초 · 나 · 상대.
  source=client  앱이 알렸다 (1.13.3~): 접은 까닭, 그때의 상태, 오류 역추적(경로는 파일 이름만).
"""
import datetime
import sqlite3

NICK = None          # 예: "레드 36세"
HOURS = 48
SHOW = 40

KST = datetime.timezone(datetime.timedelta(hours=9))
c = sqlite3.connect("file:/data/poket.db?mode=ro", uri=True)
c.row_factory = sqlite3.Row
since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=HOURS)).isoformat()


def kst(s):
    try:
        return datetime.datetime.fromisoformat(s).astimezone(KST).strftime("%m/%d %H:%M:%S")
    except Exception:                                       # noqa: BLE001
        return s


where, args = "t.at >= ?", [since]
if NICK:
    u = c.execute("SELECT id FROM users WHERE username=?", (NICK,)).fetchone()
    if not u:
        raise SystemExit("그런 닉네임이 없습니다: %s" % NICK)
    where += " AND t.user_id=?"
    args.append(u["id"])

print("== 지난 %d시간%s" % (HOURS, " · %s" % NICK if NICK else ""))
for r in c.execute("SELECT source, kind, COUNT(*) n, COUNT(DISTINCT user_id) people FROM trouble t WHERE %s"
                   " GROUP BY source, kind ORDER BY n DESC" % where, args):
    print("  %-6s %-18s %4d건 · %d명" % (r["source"], r["kind"], r["n"], r["people"]))

print("\n== 최근 %d건" % SHOW)
for r in c.execute("SELECT t.*, u.username FROM trouble t LEFT JOIN users u ON u.id = t.user_id WHERE %s"
                   " ORDER BY t.id DESC LIMIT ?" % where, args + [SHOW]):
    head = "%s  %s  [%s] %s  판 %s" % (kst(r["at"]), r["username"], r["source"], r["kind"], r["ref"])
    if r["version"] or r["os"]:
        head += "  (%s · %s)" % (r["version"], r["os"])
    print(head)
    print("    " + (r["message"] or ""))
    if r["detail"]:
        lines = [x for x in r["detail"].splitlines() if x.strip()]
        print("    " + lines[0][:240])                    # 그때의 상태
        if len(lines) > 1:
            print("    ... " + lines[-1][:240])           # 역추적의 마지막 줄 (오류 문구)
