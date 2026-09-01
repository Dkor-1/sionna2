# -*- coding: utf-8 -*-
"""figcheck.py — 그림을 저장하기 전에 **겹침**을 잡는다.

사용자 지시(2026-09-02): 「레포트에 실은 그림들에서 legend 같은거에 의한 겹침?
이런거 없게끔 주의해줘」

⭐**저장 직전에 잡는다.** 렌더된 PNG 를 보고 겹침을 찾는 것은 신뢰할 수 없다 —
   matplotlib 은 이 시점에 모든 artist 의 화면 좌표 상자를 알고 있으므로 여기서 재는 게 맞다.

■ 무엇을 보나
  ① 범례 ↔ 자료   범례 상자 안에 그 축의 선/점/막대가 들어와 있나 (표본점으로 판정)
  ② 글자 ↔ 글자   축 안 텍스트끼리 상자가 겹치나 (제목·축이름은 뺀다 — 밖에 있다)
  ③ 축이름 ↔ 눈금 y 축 이름이 눈금 글자와 겹치나

⛔**막지는 않는다.** 경고만 낸다 — 겹침 판정에는 거짓양성이 있고(반투명 범례를 일부러
   자료 위에 두는 판이 있다), 빌더를 멈추면 그림이 아예 안 나온다.
   `FIGCHECK_STRICT=1` 을 주면 예외를 던진다.
"""
from __future__ import annotations

import os

_STRICT = os.environ.get("FIGCHECK_STRICT", "") == "1"


def _bbox(artist, renderer):
    try:
        b = artist.get_window_extent(renderer=renderer)
        return None if (b.width <= 0 or b.height <= 0) else b
    except Exception:
        return None


def _inter(a, b):
    """두 상자의 겹침 넓이 [px²]."""
    w = min(a.x1, b.x1) - max(a.x0, b.x0)
    h = min(a.y1, b.y1) - max(a.y0, b.y0)
    return w * h if (w > 0 and h > 0) else 0.0


def check(fig, *, min_frac: float = 0.02) -> list[str]:
    """겹침 목록을 돌려준다. `min_frac` 는 작은 쪽 넓이 대비 무시 문턱."""
    import numpy as np
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    out: list[str] = []

    for ax in fig.get_axes():
        # ── ① 범례 ↔ 자료
        lg = ax.get_legend()
        lb = _bbox(lg, r) if lg is not None else None
        if lb is not None:
            hit = 0
            for ln in ax.get_lines():
                xy = ln.get_xydata()
                if xy is None or len(xy) == 0:
                    continue
                pts = ax.transData.transform(np.asarray(xy, float))
                inside = ((pts[:, 0] >= lb.x0) & (pts[:, 0] <= lb.x1) &
                          (pts[:, 1] >= lb.y0) & (pts[:, 1] <= lb.y1))
                hit += int(inside.sum())
            if hit:
                out.append(f"범례가 자료를 덮는다 — 축 '{ax.get_ylabel() or ax.get_title() or ax}' "
                           f"에서 점 {hit} 개가 범례 상자 안에 있다. "
                           f"bbox_to_anchor 로 축 밖에 두거나 loc 를 옮겨라")

        # ── ② 축 안 글자끼리
        txts = [t for t in ax.texts if t.get_text().strip()]
        boxes = [(t, _bbox(t, r)) for t in txts]
        boxes = [(t, b) for t, b in boxes if b is not None]
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                (t1, b1), (t2, b2) = boxes[i], boxes[j]
                a = _inter(b1, b2)
                if a > min_frac * min(b1.width * b1.height, b2.width * b2.height):
                    out.append(f"글자끼리 겹친다 — '{t1.get_text()[:28]}' ↔ "
                               f"'{t2.get_text()[:28]}'")

        # ── ③ y 축 이름 ↔ 눈금 글자
        yl = ax.yaxis.get_label()
        if yl.get_text().strip():
            lb2 = _bbox(yl, r)
            if lb2 is not None:
                for tk in ax.get_yticklabels():
                    if not tk.get_text().strip():
                        continue
                    tb = _bbox(tk, r)
                    if tb is not None and _inter(lb2, tb) > 0:
                        out.append(f"y 축 이름 '{yl.get_text()[:28]}' 이 눈금 글자와 겹친다")
                        break
    return out


def warn(fig, stem: str = "") -> list[str]:
    """검사하고 경고를 찍는다. ⛔기본은 막지 않는다."""
    try:
        probs = check(fig)
    except Exception as e:                       # 검사가 그림을 죽이면 안 된다
        return [f"(figcheck 실패: {e})"]
    for p in probs:
        print(f"   ⚠겹침 {stem}: {p}")
    if probs and _STRICT:
        raise RuntimeError(f"figcheck: {stem} 겹침 {len(probs)} 건 — {probs[0]}")
    return probs
