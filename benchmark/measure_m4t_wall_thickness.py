# -*- coding: utf-8 -*-
"""
measure_m4t_wall_thickness.py — **DJI 공식 CAD 에서 셸 벽 두께를 직접 잰다** (2026-08-15)
==========================================================================================
왜 필요한가
  `docs/RETRACTION_LOG.md` A3 과 `docs/MATERIAL_SOURCES.md` §7 은 «셸 두께는 출처가 없다»
  라고 적어 뒀다. 그래서 Sionna 쪽은 기본값 100 mm 가 쓰였고, 정정안으로 2 mm 가 거론됐다.
  그런데 **출처가 없다는 그 말이 더 이상 참이 아니다** — 저장소에 DJI 공식 STEP CAD 가 있다
  (`assets/meshes/reference/matrice4-M4T_v2.step`, 2026-08-03 확보, md5
   51ff9a47fac2c4c7a9d3817d5444f74d). 이 파일이 커버를 **속 빈 벽**으로 담고 있으면
  벽 두께는 추측이 아니라 **측정**이 된다.

무엇을 재나 — 실효 벽 두께  t = 2V/A
  얇은 껍데기는 «겉면 + 속면» 이라 표면적이 중간면의 두 배다(A ≈ 2·A_mid), 부피는
  V ≈ A_mid·t 다. 그래서 **t = 2V/A** 가 그 부품의 평균 벽 두께다.
  속이 꽉 찬 덩어리(배터리·카메라 블록)에서는 이 값이 부피/표면 비율이라 수 mm 로 크게
  나오므로, 같은 잣대가 «벽» 과 «덩어리» 를 저절로 갈라 준다.
  V·A 는 OCC 커널이 정확히 낸다(메쉬를 굽지 않는다 — 이 파일은 메쉬 생성이 실패한다:
  "Impossible to mesh periodic surface 4456").

자가검사 (이 파일이 스스로 맞는지 보이는 근거)
  벽이 t 인 «접시형 커버»(한쪽 열림) 220×94×74 mm 의 해석식에 2V/A 를 넣으면
  0.5/0.75/1.0/1.5/2.0 mm 를 오차 −0.2~−1.0 % 로 되찾는다. 닫힌 상자에서는 오차 0.0 % 다.
  → 추정자는 편향이 없다. `--selftest` 로 언제든 다시 확인할 수 있다.

⭐ 실측 결과 (2026-08-15) — **DJI Matrice 4T 셸 벽 = 0.75 mm**
  솔리드 125개 중 «벽» 은 이렇게 나온다 (t = 2V/A):
      tag 124  WA345_ID_YW_TOPCOVER_230920_2   217×89×54 mm   0.710 mm   ← 윗커버
      tag 123  WA345_ID_YW_TOPCOVER_230920_1    81×29×27 mm   0.681 mm   ← 윗커버(2)
      tag 119  WA345_ID_BOTCOVER_20230913      140×65×22 mm   0.764 mm   ← 아랫커버
      tag 109  (동체 셸, 이름 없는 BREP_125)    221×94×74 mm   0.756 mm
      tag 118  WA345_BATT_ID_… 배터리 외피      137×57×57 mm   0.667 mm
  반면 속이 찬 덩어리(카메라·배터리 코어 등)는 4.8~6.0 mm 로 확연히 갈린다 —
  **잣대가 «벽» 과 «덩어리» 를 스스로 구분한다.**

  ⭐ 독립 확인 — **광선 실측**: 위 솔리드만 따로 메쉬로 굽고(전체 어셈블리는 못 굽는다)
  표면에서 안쪽(−법선)으로 광선을 쏴 반대 벽까지의 거리를 재면
      109 최빈 0.75 mm (0.70~0.80 구간에 면적의 **92 %**)
      124 최빈 0.75 mm (**92 %**)
      123 최빈 0.75 mm (**82 %**)
  즉 분포가 아니라 **설계 공칭 0.75 mm 한 값**이다. 두 잣대(2V/A · 광선)가 서로 맞는다.
  ⚠ 119 는 "Impossible to mesh periodic surface" 로 광선 판을 못 냈다 — 2V/A 값만 있다.

⚠ 남는 편향 (정직하게)
  리브(rib)는 설계 관행상 벽의 50~60 % 두께라 평균을 **아래로** 끌고, 나사 보스는 위로 끈다.
  즉 2V/A 는 «공칭 벽» 의 하한에 가깝다. 그리고 일부 부위는 겉껍데기 + 속프레임으로
  **두 겹**이라 전파가 지나가는 플라스틱 총량은 한 겹의 두 배일 수 있다.

의존성 ⚠ gmsh(OCC) 가 필요하다. 이 컨테이너에는 없어서 스크래치패드에 따로 깔아 썼다:
    uv pip install --python <venv python> --target <scratch>/pylibs gmsh
    apt-get download libglu1-mesa libgl1 libglx0 libopengl0 libglvnd0 libglapi-mesa \
        libx11-6 libxext6 libxfixes3 libxcb1 libxau6 libxdmcp6 libxcb-glx0 libxcb-dri2-0 \
        libxcb-dri3-0 libxcb-present0 libxcb-sync1 libxshmfence1 libdrm2 libxcb-shm0 \
        libxxf86vm1 libxcursor1 libxrender1 libxinerama1 libxft2 libfontconfig1 \
        libfreetype6 libpng16-16 libbrotli1 libexpat1 libbz2-1.0 libxrandr2 libglx-mesa0
    dpkg-deb -x *.deb <scratch>/opt   →   LD_LIBRARY_PATH=<scratch>/opt/usr/lib/x86_64-linux-gnu

실행:  PYTHONPATH=<scratch>/pylibs LD_LIBRARY_PATH=... python benchmark/measure_m4t_wall_thickness.py
      python benchmark/measure_m4t_wall_thickness.py --selftest        # gmsh 없이 추정자만 검사
GPU 미사용 — sionna.rt·mitsuba 를 부르지 않는다.
"""
from __future__ import annotations

import argparse
import json
import os
import time

STEP_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "assets", "meshes", "reference", "matrice4-M4T_v2.step")


def dish_2v_over_a(L: float, W: float, H: float, t: float) -> float:
    """한쪽이 열린 접시형 커버(벽 두께 t)의 2V/A — 자가검사용 해석식."""
    V = L * W * H - (L - 2 * t) * (W - 2 * t) * (H - t)
    A = (L * W + 2 * (L + W) * H) \
        + ((L - 2 * t) * (W - 2 * t) + 2 * ((L - 2 * t) + (W - 2 * t)) * (H - t)) \
        + (2 * t * (L + W) - 4 * t * t)
    return 2 * V / A


def selftest() -> list[dict]:
    out = []
    for t in (0.5, 0.75, 1.0, 1.5, 2.0):
        got = dish_2v_over_a(220.0, 94.0, 74.0, t)
        out.append(dict(check=f"접시형 커버 벽 {t} mm", got=round(got, 4), want=t,
                        err_pct=round(100 * (got - t) / t, 2), pass_=abs(got - t) / t < 0.02))
    return out


def measure(step_path: str) -> list[dict]:
    import gmsh
    t0 = time.time()
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.option.setNumber("General.NumThreads", 1)
    gmsh.option.setNumber("Geometry.OCCParallel", 0)
    gmsh.option.setNumber("Geometry.OCCImportLabels", 1)   # 부품 이름을 살린다
    gmsh.model.occ.importShapes(step_path)
    gmsh.model.occ.synchronize()
    rows = []
    for _, tag in gmsh.model.getEntities(3):
        try:
            V = gmsh.model.occ.getMass(3, tag)
        except Exception:
            continue
        bb = gmsh.model.getBoundingBox(3, tag)
        ext = sorted([bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2]], reverse=True)
        A = 0.0
        for _, s in gmsh.model.getBoundary([(3, tag)], oriented=False, recursive=False):
            try:
                A += gmsh.model.occ.getMass(2, abs(s))
            except Exception:
                pass
        if A <= 0:
            continue
        rows.append(dict(tag=int(tag), V_mm3=round(V, 1), A_mm2=round(A, 1),
                         t_eff_mm=round(2.0 * V / A, 3),
                         ext_mm=[round(float(x), 2) for x in ext],
                         name=gmsh.model.getEntityName(3, tag)))
    gmsh.finalize()
    print(f"[측정] 솔리드 {len(rows)}개 · {time.time() - t0:.0f}s")
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", default=STEP_DEFAULT)
    ap.add_argument("--selftest", action="store_true", help="gmsh 없이 추정자만 검사")
    ap.add_argument("--json", default="", help="결과를 이 경로에 쓴다(안 주면 안 쓴다)")
    a = ap.parse_args()

    print("■ 자가검사 — 2V/A 가 벽 두께를 되찾는가")
    for c in selftest():
        print(f"   {'OK ' if c['pass_'] else '실패'} {c['check']:24s} → {c['got']:.3f} mm "
              f"({c['err_pct']:+.2f} %)")
    if a.selftest:
        return
    rows = measure(a.step)
    rows.sort(key=lambda r: -r["ext_mm"][0])
    print(f"\n{'tag':>5} {'bbox(mm)':>26} {'t=2V/A':>8}  이름(끝 40자)")
    for r in rows[:25]:
        print(f"{r['tag']:>5} {str(r['ext_mm']):>26} {r['t_eff_mm']:>8.3f}  ...{r['name'][-40:]}")
    thin = [r for r in rows if r["t_eff_mm"] < 2.0]
    print(f"\n벽(2 mm 미만) 솔리드 {len(thin)}/{len(rows)}")
    if thin:
        v = sorted(r["t_eff_mm"] for r in thin)
        print(f"  두께 중앙값 {v[len(v) // 2]:.3f} mm · 최소 {v[0]:.3f} · 최대 {v[-1]:.3f}")
    if a.json:
        json.dump(rows, open(a.json, "w"), ensure_ascii=False, indent=1)
        print("→", a.json)


if __name__ == "__main__":
    main()
