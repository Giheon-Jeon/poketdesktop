# -*- coding: utf-8 -*-
"""앱이 배틀을 접은 까닭을 서버에 알린다 (1.13.3, 서버는 app/troubles.py).

예전에는 poketdesktop.log 에만 남아서, 제보가 오면 사용자에게 그 파일을 열어 달라고 해야 했다
(게시판 #266 레드 36세 · #280 니뉴). 이제 접는 순간 서버의 trouble 표에 남는다.

  - **경로는 파일 이름만 남긴다.** 역추적의 경로에 윈도우 사용자 이름이 들어 있다
    (C:\\Users\\<이름>\\AppData\\...). 'File "...\\desktop_battle.py"' -> 'File "desktop_battle.py"'.
  - **뒤에서 보낸다.** 배틀을 정리하는 길을 서버 응답이 막으면 안 된다. 실패해도 조용히 넘어간다.
  - **한 시간에 LIMIT_PER_HOUR 개까지.** 같은 오류가 되풀이되면 서버도 한 사람당 30개에서 자른다.
"""
import platform
import re
import threading
import time

from common.version import VERSION

from . import config

LIMIT_PER_HOUR = 10
DETAIL_MAX = 3500

# 따옴표 안의 경로 (역추적의 File "..." · 오류 문구의 '...') 와 따옴표 없는 경로
_QUOTED = re.compile(r'(["\'])((?:[A-Za-z]:)?[^"\'\n]*[\\/][^"\'\n]*)\1')
_BARE = re.compile(r'(?:[A-Za-z]:)?(?:[\\/][^\\/\s"\']+){2,}')

_sent = []          # 보낸 시각들 (한 시간 안의 것만 센다)


def _base(path):
    return re.split(r"[\\/]", path.rstrip("\\/"))[-1]


def clean(text):
    """경로를 파일 이름만 남긴다."""
    text = _QUOTED.sub(lambda m: m.group(1) + _base(m.group(2)) + m.group(1), text or "")
    return _BARE.sub(lambda m: _base(m.group(0)), text)


def os_name():
    try:
        return ("%s %s" % (platform.system(), platform.release())).strip()
    except Exception:                                       # noqa: BLE001
        return ""


def _run(fn):
    threading.Thread(target=fn, daemon=True).start()


RUN = _run          # 검사는 바로 부르는 것으로 바꿔 낀다


def send(app, kind, ref=None, message="", detail=""):
    """하나 보낸다. 보냈으면(보내러 갔으면) True."""
    api = getattr(app, "api", None)
    post = getattr(api, "report_trouble", None)
    if post is None:
        return False
    now = time.time()
    _sent[:] = [t for t in _sent if now - t < 3600]
    if len(_sent) >= LIMIT_PER_HOUR:
        return False
    _sent.append(now)
    body = {"kind": kind, "ref": ref, "message": clean(message)[:300],
            "detail": clean(detail)[-DETAIL_MAX:], "version": VERSION, "os": os_name()}

    def go():
        try:
            post(body)
        except Exception as e:                              # noqa: BLE001
            config.log("배틀 문제를 서버에 못 알림: %s" % e)
    RUN(go)
    return True
