# -*- coding: utf-8 -*-
"""proc_scratch.py — **프로세스마다 자기 임시 폴더**를 갖게 한다.

■ 왜 필요한가 (2026-08-11 실제 사고)
    Sionna 로 계산하려면 드론 메쉬를 부위별 OBJ 파일로 **디스크에 써서** Mitsuba 에게
    읽히는 절차가 있다. 그 파일 이름이 드론 키로 고정돼 있고(`matrice4e__body.obj` 등),
    임시 폴더 이름도 실행마다 같았다. 그래서 **같은 스크립트를 여러 프로세스로 띄우면
    여덟이 같은 파일 하나를 서로 쓰고 지웠다.**

    자세 하나가 끝날 때마다 그 폴더를 `shutil.rmtree` 로 지우므로, A 가 읽는 순간
    B 가 지우면 이렇게 터진다:

        RuntimeError: [parser.cpp:1716] At dictionary node "root": failed to
        instantiate shape plugin of type "obj": [OBJMesh] Error while loading
        OBJ file "matrice4e__body.obj": file not found

    el 0 광선 예산 사다리에서 **샤드 7 개(약 2 시간치)** 가 이렇게 죽었다.
    ⚠ 폴더 이름에 앙각·샤드를 넣어 두긴 했었지만 **광선 예산이 빠져** 있어서,
      예산이 다른 두 실행을 동시에 띄우자 그대로 겹쳤다. 축을 하나씩 더하는 방식은
      «다음에 또 빠뜨린다» — 그래서 **PID** 로 뿌리에서 가른다.

■ 어떻게 쓰나
    모듈 최상단의 SCRATCH 상수를 이걸로 감싼다.

        from proc_scratch import proc_scratch
        SCRATCH = proc_scratch(os.path.join(ROOT, "outputs", "meshes", "report15_probe"))

    · 돌려주는 경로는 `<base>_pid<PID>` 다. 어떤 두 프로세스도 안 겹친다.
    · 프로세스가 정상 종료하면 **자동으로 지운다**(atexit).
    · 죽어서 못 지운 잔해는 다음 실행이 **주인 없는 것만** 치운다(아래 규칙).

■ ⛔잔해 청소 규칙 — 살아 있는 것은 절대 안 건드린다
    지우는 조건이 **셋 다** 맞아야 한다.
      ① 이름이 `<base>_pid<숫자>` 꼴이고
      ② `/proc/<숫자>` 가 **없고**(그 프로세스가 죽었고)
      ③ 마지막 수정이 **1 시간 이상 전**이다.
    ③ 이 필요한 이유는 리눅스가 PID 를 재사용하기 때문이다. 갓 만든 폴더는
    PID 가 우연히 겹쳤을 뿐일 수 있으므로 손대지 않는다.
    ⭐이 파일은 **폴더만** 지운다. 프로세스는 절대 죽이지 않는다.
"""
from __future__ import annotations

import atexit
import os
import re
import shutil
import time

__all__ = ["proc_scratch", "sweep_stale"]

STALE_AGE_S = 3600.0          # ③ 이보다 오래된 것만 잔해로 본다


def _alive(pid: int) -> bool:
    """그 PID 가 지금 살아 있나. 리눅스 /proc 로 본다."""
    return os.path.isdir(f"/proc/{pid}")


def sweep_stale(base: str, age_s: float = STALE_AGE_S) -> list[str]:
    """`<base>_pid<N>` 중 **주인이 죽었고 오래된 것**만 지운다. 지운 목록을 돌려준다."""
    parent, name = os.path.dirname(base), os.path.basename(base)
    if not os.path.isdir(parent):
        return []
    pat = re.compile(rf"^{re.escape(name)}_pid(\d+)$")
    now, gone = time.time(), []
    for e in os.listdir(parent):
        m = pat.match(e)
        if not m:
            continue
        p = os.path.join(parent, e)
        try:
            if _alive(int(m.group(1))):            # ② 살아 있으면 건드리지 않는다
                continue
            if now - os.path.getmtime(p) < age_s:  # ③ 갓 만든 것도 건드리지 않는다
                continue
            shutil.rmtree(p)
            gone.append(p)
        except OSError:
            pass
    return gone


def proc_scratch(base: str, cleanup: bool = True, sweep: bool = True) -> str:
    """`<base>_pid<PID>` 를 만들어 돌려준다.

    cleanup=True 면 정상 종료 때 지운다. sweep=True 면 주인 없는 잔해도 치운다.
    """
    if sweep:
        sweep_stale(base)
    d = f"{base}_pid{os.getpid()}"
    os.makedirs(d, exist_ok=True)
    if cleanup:
        atexit.register(lambda: shutil.rmtree(d, ignore_errors=True))
    return d
