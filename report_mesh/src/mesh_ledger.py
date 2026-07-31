# -*- coding: utf-8 -*-
"""mesh_ledger.py — `mesh_verify.json` 원장과 `DRONES` 레지스트리의 **일치 강제**.

왜 이 파일이 있나
  mesh01~08 생성기는 표적 목록을 `mesh_verify.json` 의 `meta.drones` 에서 읽는다(좋은 규약이다 —
  개수를 하드코딩하지 않는다). 그런데 **원장이 낡으면** 그 좋은 규약이 조용히 거짓말을 한다:
  레지스트리에 기종을 추가하고 검증 스위트를 다시 돌리지 않으면, 리포트가 아무 예외 없이
  "드론 5종" 이라고 써 버린다. 2026-07-30 실제로 그 상태였다(레지스트리 7종 ↔ 원장 5종).

  ⇒ **무음 실패를 예외로 바꾼다.** 재생성 전에는 일부러 멈추는 편이, 리포트가 틀린 개수를
    조용히 쓰는 것보다 낫다. (같은 방침: `report_mesh/src/viz_mesh_reports.py`,
    `src/make_notebook02.py`.)
"""
from __future__ import annotations


def ledger_order(V, what: str = "mesh_verify.json") -> list[str]:
    """`V["meta"]["drones"]` 를 그대로 돌려주되, `DRONES` 레지스트리와 **키·개수**가 다르면 예외.

    반환값은 원장 순서(리포트 그림·표의 축 순서가 원장과 어긋나지 않게 하려면 원장이 기준이다).
    """
    from drones import DRONES                       # 가벼움(numpy/geom 만)

    order = list(V["meta"]["drones"])
    reg = list(DRONES)
    if order != reg:
        missing = [k for k in reg if k not in order]
        extra = [k for k in order if k not in reg]
        raise RuntimeError(
            f"{what} 의 meta.drones 가 DRONES 레지스트리와 다르다 — "
            f"원장 {len(order)}종 {order} vs 레지스트리 {len(reg)}종 {reg} "
            f"(원장 누락 {missing} · 원장 잉여 {extra}). "
            f"먼저 검증 스위트를 다시 돌릴 것: report_mesh/src/verify_mesh_suite.py "
            f"(그 뒤 viz_mesh_reports.py → make_mesh01~08).")
    return order
