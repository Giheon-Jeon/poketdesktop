# -*- coding: utf-8 -*-
"""친구 집에 놀러 가기 · 친구 채팅 검사 (1.11.0). 서버를 띄워 놓고 돌린다.

    python server/test_visit.py http://127.0.0.1:8788 /tmp/poket-test.db

서버는 POKET_VISIT_GRACE=2 로 띄운다 (끊긴 뒤 끝내기까지 기다리는 초 - 기본 20초).
두 번째 인자(DB 경로)는 **가방에 도구를 넣는 데만** 쓴다.

못 박는 것:

  1. 친구에게만, 친구가 접속해 있을 때만 (놀러 가기 소켓에 붙어 있을 때) 간다.
  2. **수락 없이 바로** 간다. 무조건 1:1 - 둘 중 누구든 연결돼 있으면 못 보낸다.
  3. 보낼 때는 들고 가기만 한다 (아무것도 안 옮긴다). 들고 갈 수 있는 것은 볼·지닌 도구 중 귀함까지,
     볼 5개·지닌 도구 1개까지. 손님이 '여기에 두기' 를 하면 들고 온 것만큼 보따리로 싸서 손님 가방에서
     빼고, 주인이 받으면 주인 가방으로 간다 (둘 다 '받았다' 를 받는다). 받는 것은 하루 한 번 (안 받고
     놓인 것도 센다) - 그러면 손님은 더 못 둔다 (canGive). 안 받은 채 끝나면 손님에게 돌려준다.
  4. 주인의 파티(자리는 안 맞춘다)·말·동작·메가 모습이 상대에게 간다. 주인은 말한 포켓몬을 고른다
     (지금 파티에 있는 것만), 손님은 못 고른다. 이상한 값은 다듬거나 버린다.
  5. 어느 쪽이든 끝내면 둘 다 '끝' 을 받는다. 끊기고 GRACE 초가 지나면 저절로 끝난다.
"""
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request

from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8788").rstrip("/")
DB = sys.argv[2] if len(sys.argv) > 2 else None
WS = BASE.replace("https://", "wss://").replace("http://", "ws://") + "/ws/visit"
OK = FAIL = 0
STAMP = str(int(time.time()) % 100000)


def chk(name, cond, got=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s   %s" % (name, str(got)[:300]))


def call(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except ValueError:
            return e.code, {}


def register(name):
    st, r = call("POST", "/api/auth/register",
                 {"username": name, "password": "1234", "starter": "PIKACHU", "device": "t"})
    if st != 200:
        raise SystemExit("가입 실패 %s %s" % (st, r))
    return r.get("token") or r["session"]["token"], r["user"]["id"]


def sql(q, args=()):
    c = sqlite3.connect(DB, timeout=20)
    c.execute(q, args)
    c.commit()
    c.close()


def bag(uid, item):
    c = sqlite3.connect(DB, timeout=20)
    r = c.execute("SELECT count FROM bag WHERE user_id=? AND item=?", (uid, item)).fetchone()
    c.close()
    return r[0] if r else 0


def ws(token=None):
    head = {"Authorization": "Bearer " + token} if token else {}
    return connect(WS, additional_headers=head, open_timeout=10)


def recv(sock, want=None, timeout=5.0):
    """t 가 want 인 것이 올 때까지 받는다 (다른 것은 버린다). 안 오면 None."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            raw = sock.recv(timeout=max(0.05, end - time.time()))
        except TimeoutError:
            return None
        if raw == "pong":
            if want == "pong":
                return raw
            continue
        msg = json.loads(raw)
        if want is None or msg.get("t") == want:
            return msg
    return None


def befriend(asker_tok, asker_id, target_tok, target_name):
    """asker 가 target 에게 신청하고 target 이 받는다."""
    st, r = call("POST", "/api/friends/request", {"username": target_name}, token=asker_tok)
    if st != 200:
        raise SystemExit("친구 신청 실패 %s %s" % (st, r))
    st, r = call("POST", "/api/friends/%d/accept" % asker_id, {}, token=target_tok)
    if st != 200:
        raise SystemExit("친구 수락 실패 %s %s" % (st, r))


def main():
    if not DB:
        raise SystemExit("DB 경로를 주세요")
    ta, a = register("방문가" + STAMP)
    tb, b = register("집주인" + STAMP)
    tc, c = register("손님셋" + STAMP)
    befriend(ta, a, tb, "집주인" + STAMP)          # a - b 친구
    befriend(tc, c, tb, "집주인" + STAMP)          # c - b 친구 (a 와 c 는 친구가 아니다)
    for item, n in (("GREATBALL", 10), ("ULTRABALL", 4), ("BLACKBELT", 2), ("FOCUSSASH", 1),
                    ("MASTERBALL", 1), ("FIRESTONE", 3)):
        sql("INSERT INTO bag (user_id, item, count) VALUES (?,?,?)", (a, item, n))

    print("=== 붙기 ===")
    try:
        bad = ws("틀린토큰")
        bad.recv(timeout=5)
        code = None
    except ConnectionClosed as e:
        code = e.rcvd.code if e.rcvd else None
    chk("토큰이 틀리면 4401 로 끊는다", code == 4401, code)
    st, r = call("POST", "/api/visit/start", {"friend": b}, token=ta)
    chk("친구가 소켓에 안 붙어 있으면 못 간다", st == 409 and "접속" in (r.get("error") or ""), (st, r))
    sb = ws(tb)
    chk("붙으면 hello", (recv(sb, "hello") or {}).get("userId") == b)
    sb.send("ping")
    chk("ping 에는 pong", recv(sb, "pong") == "pong")
    st, r = call("GET", "/api/friends", token=ta)
    fb = next((x for x in r.get("friends") or [] if x["id"] == b), {})
    chk("친구 목록: 붙어 있는 친구는 놀러 갈 수 있다", fb.get("visitable") is True and fb.get("visitBusy") is False, fb)

    print("\n=== 놀러 가기 ===")
    st, r = call("POST", "/api/visit/start", {"friend": c}, token=ta)
    chk("친구가 아니면 못 간다", st == 403, (st, r))
    st, r = call("POST", "/api/visit/start", {"friend": a}, token=ta)
    chk("자기 집에는 못 간다", st == 400, (st, r))
    for iid, why in (("FIRESTONE", "볼·지닌 도구가 아닌 것"), ("MASTERBALL", "전설 등급 볼"),
                     ("FOCUSSASH", "진귀 등급 지닌 도구")):
        st, r = call("POST", "/api/visit/start", {"friend": b, "items": [{"id": iid, "count": 1}]}, token=ta)
        chk("들고 갈 수 없다: %s (%s)" % (why, iid), st == 400 and "들고 갈 수 없습니다" in (r.get("error") or ""),
            (st, r))
    st, r = call("POST", "/api/visit/start", {"friend": b, "items": [
        {"id": "GREATBALL", "count": 4}, {"id": "ULTRABALL", "count": 2}]}, token=ta)
    chk("볼은 합쳐서 5개까지", st == 400 and "볼은 5개" in (r.get("error") or ""), (st, r))
    st, r = call("POST", "/api/visit/start", {"friend": b, "items": [{"id": "BLACKBELT", "count": 2}]}, token=ta)
    chk("지닌 도구는 1개까지", st == 400 and "지닌 도구는 1개" in (r.get("error") or ""), (st, r))
    st, r = call("POST", "/api/visit/start", {"friend": b, "items": [{"id": "ULTRABALL", "count": 5}]}, token=ta)
    chk("가진 것보다 많이는 못 들고 간다", st == 409, (st, r))
    st, r = call("POST", "/api/visit/start", {"friend": b, "look": 10006, "items": [
        {"id": "GREATBALL", "count": 3}, {"id": "ULTRABALL", "count": 2}, {"id": "BLACKBELT", "count": 1}]}, token=ta)
    v = r.get("visit") or {}
    chk("수락 없이 바로 간다 (나는 손님)", st == 200 and v.get("role") == "guest" and v.get("partner") == "집주인" + STAMP,
        (st, r))
    lead = (call("GET", "/api/pokemon", token=ta)[1].get("pokemon") or [{}])[0]
    chk("  파티 맨 앞 포켓몬이 간다, 메가 모습도 같이", (v.get("mon") or {}).get("id") == lead.get("id")
        and (v.get("mon") or {}).get("num", 0) > 0 and v.get("look") == 10006, (v.get("mon"), lead.get("id")))
    chk("  들고 가기만 한다 (아무것도 안 옮긴다)", bag(a, "GREATBALL") == 10 and bag(b, "GREATBALL") == 0
        and bag(a, "BLACKBELT") == 2, (bag(a, "GREATBALL"), bag(b, "GREATBALL")))
    chk("  들고 간 것 목록, 친구에게 둘 수 있다", [(x["id"], x["count"]) for x in v.get("carry") or []]
        == [("BLACKBELT", 1), ("GREATBALL", 3), ("ULTRABALL", 2)] and v.get("bundles") == []
        and v.get("canGive") is True, (v, r))
    hv = recv(sb, "visit")
    hv = (hv or {}).get("visit") or {}
    chk("주인에게 바로 알린다 (나는 주인, 손님의 포켓몬·들고 온 것)", hv.get("role") == "host"
        and hv.get("partner") == "방문가" + STAMP and (hv.get("mon") or {}).get("id") == v["mon"]["id"]
        and [x["id"] for x in hv.get("carry") or []] == ["BLACKBELT", "GREATBALL", "ULTRABALL"], hv)

    print("\n=== 무조건 1:1 ===")
    st, r = call("POST", "/api/visit/start", {"friend": a}, token=tb)
    chk("연결돼 있으면 주인도 못 보낸다", st == 409, (st, r))
    sc = ws(tc)
    recv(sc, "hello")
    st, r = call("POST", "/api/visit/start", {"friend": b}, token=tc)
    chk("다른 친구도 그 집에는 못 간다", st == 409 and "다른 친구" in (r.get("error") or ""), (st, r))
    st, r = call("GET", "/api/friends", token=tc)
    fb = next((x for x in r.get("friends") or [] if x["id"] == b), {})
    chk("  친구 목록에 '연결 중'", fb.get("visitBusy") is True and fb.get("visitable") is False, fb)

    print("\n=== 주고받기 ===")
    sa = ws(ta)
    recv(sa, "hello")
    chk("손님이 붙으면 지금 놀러 가 있는 것을 다시 준다", ((recv(sa, "visit") or {}).get("visit") or {}).get("role") == "guest")
    sb.send(json.dumps({"t": "party", "party": [
        {"id": 5, "num": 6, "look": 10006, "x": 0.25, "y": 1.7, "lead": True,
         "name": "리자몽", "level": 50, "shiny": True, "tint": "a"},
        {"id": 8, "num": 3, "name": "이상해꽃", "level": 40},
        {"id": 6, "num": "x"}, {"id": 7, "num": 0}, {"id": 5, "num": 6}]}))
    p = recv(sa, "party")
    chk("주인의 파티가 손님에게 간다 (이상한 줄·겹친 번호는 버린다)", p and [x["id"] for x in p["party"]] == [5, 8]
        and p["party"][0]["look"] == 10006 and p["party"][0]["tint"] == "a" and p["lead"] == 5, p)
    chk("  자리는 안 보낸다 (걷는 것은 손님 화면 몫)", p and not any(k in p["party"][0] for k in ("x", "y", "face", "anim")), p)
    sb.send(json.dumps({"t": "party", "party": [{"id": 8, "num": 3}]}))
    chk("  너무 자주 보내면 버린다", recv(sa, "party", timeout=0.3) is None)
    sa.send(json.dumps({"t": "party", "party": [{"id": 1, "num": 25}]}))
    chk("  손님은 파티를 못 보낸다", recv(sb, "party", timeout=1.0) is None)
    st, r = call("GET", "/api/visit", token=ta)
    chk("  손님이 다시 물으면 마지막 파티를 준다", [x["id"] for x in (r.get("visit") or {}).get("party") or []] == [5, 8]
        and (r.get("visit") or {}).get("hostLead") == 5, r.get("visit"))
    sa.send(json.dumps({"t": "say", "text": "안녕   하세요" + "!" * 100, "pet": 5}))
    m = recv(sb, "say")
    chk("말이 상대에게 간다 (빈칸 하나로, 60자까지, 손님은 포켓몬을 못 고른다)", m and m["from"] == "guest"
        and m["text"].startswith("안녕 하세요") and len(m["text"]) == 60 and m.get("pet") is None, m)
    sa.send(json.dumps({"t": "say", "text": "도배"}))
    chk("  너무 빨리 또 보내면 버린다", recv(sb, "say", timeout=0.4) is None)
    time.sleep(0.7)
    sb.send(json.dumps({"t": "say", "text": "어서 와", "pet": 8}))
    m = recv(sa, "say")
    chk("주인은 말한 포켓몬을 고른다 (그 포켓몬 위에 말풍선)", m and m["from"] == "host" and m.get("pet") == 8, m)
    time.sleep(0.7)
    sb.send(json.dumps({"t": "act", "act": "dance", "pet": 99}))
    m = recv(sa, "act")
    chk("동작이 상대에게 간다 (파티에 없는 포켓몬은 고르지 못한다)", m and m["from"] == "host" and m["act"] == "dance"
        and m.get("pet") is None, m)
    time.sleep(0.7)
    sb.send(json.dumps({"t": "act", "act": "fly"}))
    chk("  없는 동작은 버린다", recv(sa, "act", timeout=0.6) is None)
    sa.send(json.dumps({"t": "look", "look": 0}))
    m = recv(sb, "look")
    chk("손님이 메가 모습을 풀면 주인에게 간다", m and m["look"] is None, m)
    st, r = call("GET", "/api/visit", token=tb)
    chk("주인이 다시 물어도 지금 모습", (r.get("visit") or {}).get("look") is None and r.get("online") is True, r)

    print("\n=== 보따리 ===")
    st, r = call("POST", "/api/visit/drop", {"items": [{"id": "GREATBALL", "count": 1}]}, token=tb)
    chk("주인은 둘 수 없다 (놀러 간 쪽만)", st == 409, (st, r))
    st, r = call("POST", "/api/visit/drop", {"items": [{"id": "GREATBALL", "count": 4}]}, token=ta)
    chk("들고 온 것보다 많이는 못 둔다", st == 409 and "들고 온" in (r.get("error") or ""), (st, r))
    st, r = call("POST", "/api/visit/drop", {"items": [{"id": "GREATBALL", "count": 2},
                                                       {"id": "BLACKBELT", "count": 1}]}, token=ta)
    b1 = r.get("bundle") or {}
    chk("여기에 두기: 보따리로 싸서 둔다, 손님 가방에서 바로 빠진다", st == 200 and b1.get("count") == 3
        and bag(a, "GREATBALL") == 8 and bag(a, "BLACKBELT") == 1 and bag(b, "GREATBALL") == 0, (st, r))
    chk("  친구가 오늘 한 번을 썼다 - 더 못 둔다 (canGive)", (r.get("visit") or {}).get("canGive") is False, r)
    ma, mb = recv(sa, "bundles"), recv(sb, "bundles")
    chk("  둘 다 보따리를 받는다 (누가 두었나), 들고 온 것은 그만큼 준다", ma and mb
        and [x["id"] for x in mb["bundles"]] == [b1.get("id")] and mb["bundles"][0]["from"] == "방문가" + STAMP
        and [(x["id"], x["count"]) for x in mb["carry"]] == [("GREATBALL", 1), ("ULTRABALL", 2)]
        and ma["canGive"] is False, mb)
    st, r = call("POST", "/api/visit/drop", {"items": [{"id": "ULTRABALL", "count": 1}]}, token=ta)
    chk("받는 것은 하루 한 번 (안 받고 놓인 것도 센다)", st == 409 and "오늘 이미" in (r.get("error") or ""), (st, r))
    st, r = call("POST", "/api/visit/claim", {"bundle": b1.get("id")}, token=ta)
    chk("손님은 받을 수 없다 (주인만)", st == 409, (st, r))
    st, r = call("POST", "/api/visit/claim", {"bundle": b1.get("id")}, token=tb)
    chk("주인이 보따리를 받는다 -> 주인 가방으로", st == 200 and bag(b, "GREATBALL") == 2 and bag(b, "BLACKBELT") == 1,
        (st, r, bag(b, "GREATBALL")))
    ca, cb = recv(sa, "claimed"), recv(sb, "claimed")
    chk("  둘 다 '누가 누구에게 무엇을 받았다' 를 받는다", ca and cb and cb["from"] == "방문가" + STAMP
        and cb["by"] == "집주인" + STAMP and [x["id"] for x in cb["bundle"]["items"]] == ["BLACKBELT", "GREATBALL"],
        (ca, cb))
    st, r = call("POST", "/api/visit/claim", {"bundle": b1.get("id")}, token=tb)
    chk("  한 번만 받는다", st == 404 and bag(b, "GREATBALL") == 2, (st, r))
    st, r = call("GET", "/api/visit", token=tb)
    chk("  주인: 오늘 받은 수 1", r.get("receivedToday") == 1 and r.get("receivePerDay") == 1, r)

    print("\n=== 끝내기 ===")
    st, r = call("POST", "/api/visit/end", {}, token=ta)
    chk("손님이 돌아온다", st == 200 and r.get("ended") is True and r.get("visit") is None, (st, r))
    ea, eb = recv(sa, "end"), recv(sb, "end")
    chk("  둘 다 '끝' 을 받는다 (돌려줄 보따리 없음)", ea and eb and eb["by"] == "guest" and "돌아갔습니다" in eb["text"]
        and ea.get("returned") == [], (ea, eb))
    st, r = call("POST", "/api/visit/start", {"friend": b, "items": [{"id": "ULTRABALL", "count": 1}]}, token=ta)
    recv(sb, "visit")
    chk("다시 가도 그 친구는 오늘 이미 받았다 - 둘 수 없다", (r.get("visit") or {}).get("canGive") is False, r)
    st, r = call("POST", "/api/visit/drop", {"items": [{"id": "ULTRABALL", "count": 1}]}, token=ta)
    chk("  두기를 보내도 거절", st == 409 and "오늘 이미" in (r.get("error") or ""), (st, r))
    st, r = call("POST", "/api/visit/end", {}, token=tb)
    eb, ea = recv(sb, "end"), recv(sa, "end")
    chk("주인이 돌려보낸다 - 둘 다 '끝'", st == 200 and ea and ea["by"] == "host" and "돌려보냈습니다" in ea["text"], ea)
    st, r = call("POST", "/api/visit/end", {}, token=tb)
    chk("  이미 끝났으면 아무 일도 없다", st == 200 and r.get("ended") is False)
    # 거꾸로: 집주인이 방문가 집에 가서 두고, 방문가가 안 받은 채 끝낸다 -> 돌려받는다
    st, r = call("POST", "/api/visit/start", {"friend": a, "items": [{"id": "GREATBALL", "count": 2}]}, token=tb)
    recv(sa, "visit")
    st, r = call("POST", "/api/visit/drop", {"items": [{"id": "GREATBALL", "count": 2}]}, token=tb)
    chk("오늘 아직 안 받은 사람에게는 둘 수 있다", st == 200 and bag(b, "GREATBALL") == 0, (st, r))
    recv(sb, "bundles")
    st, r = call("POST", "/api/visit/end", {}, token=ta)
    eb = recv(sb, "end")
    chk("  안 받은 채 끝나면 손님에게 돌려준다", eb and [(x["id"], x["count"]) for x in eb.get("returned") or []]
        == [("GREATBALL", 2)] and bag(b, "GREATBALL") == 2 and bag(a, "GREATBALL") == 8, (eb, bag(b, "GREATBALL")))
    st, r = call("GET", "/api/visit", token=ta)
    chk("  돌려준 것은 받은 것으로 안 센다", r.get("receivedToday") == 0, r)
    recv(sa, "end")

    print("\n=== 끊기면 ===")
    st, r = call("POST", "/api/visit/start", {"friend": b}, token=ta)
    recv(sb, "visit")
    recv(sa, "visit")
    sa.close()
    time.sleep(0.5)
    chk("끊겨도 바로 끝내지는 않는다 (다시 켜는 사이)", (call("GET", "/api/visit", token=tb)[1].get("visit")) is not None)
    eb = recv(sb, "end", timeout=8)
    chk("GRACE 초가 지나도 안 돌아오면 끝낸다", eb and eb["by"] == "gone" and "끊겨" in eb["text"], eb)
    for s in (sb, sc):
        try:
            s.close()
        except Exception:                                   # noqa: BLE001
            pass

    print("\n" + "=" * 54)
    print("  합계  OK %d   FAIL %d" % (OK, FAIL))
    print("=" * 54)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
