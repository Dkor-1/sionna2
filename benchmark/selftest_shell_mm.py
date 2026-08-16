# -*- coding: utf-8 -*-
"""
selftest_shell_mm.py — **«--shell-mm 을 안 주면 예전과 비트동일»** 회귀검사
============================================================================
이 저장소에서 가장 비싼 사고 유형은 «꼬리표를 안 붙여 옛 샤드와 이름이 겹쳐 원장이 조용히
오염되는 것» 이다. 그래서 배관을 바꾼 직후 이 검사를 통과시킨다.

⛔**GPU 를 안 쓴다.** `sionna.rt` 를 진짜로 부르지 않고 **가짜 모듈로 갈아 끼워서**
`materials.make_material()` 이 Sionna 에게 **무엇을 넘기는지** 만 들여다본다.

검사 항목
  1. 손잡이를 안 켜면 `RadioMaterial(...)` 호출 인자에 `thickness` 가 **아예 없다**
     (=예전 코드와 같은 호출 → Sionna 기본값 0.1 m). ITU 재질은 원래대로 두께를 넘긴다.
  2. `set_thickness_mm(shell=2.0)` 이면 plastic·plastic_blue 만 0.002 m 를 받고,
     prop_plastic·carbon·absorber 는 여전히 안 받는다.
  3. `set_thickness_mm()` 으로 되돌리면 1 번 상태로 정확히 복귀한다.
  4. 파일명 꼬리표: 안 주면 **빈 문자열**, 주면 `_shell2mm` — 그리고 그 꼬리표가
     **기존 샤드 이름 어디에도 안 걸린다**(정규식 대조).
  5. argparse 기본값이 0.0 이라 «안 주면» 이 곧 «0» 이다.
  6. 단위 사고 가드(`--shell-mm 0.002` 같은 m 입력, 100 mm 재현 시도)가 죽는다.
  7. 우리 커널 팔(--engine ours)에 두께를 주면 **거부**한다(내용이 같은데 이름만 다른
     샤드가 생기는 것을 막는다). 이건 run() 을 실제로 태워서 확인한다.

실행:  python benchmark/selftest_shell_mm.py
"""
from __future__ import annotations

import glob
import os
import re
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

FAILED: list[str] = []


def chk(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'✅' if ok else '⛔'} {name}" + (f"  · {detail}" if detail else ""))
    if not ok:
        FAILED.append(name)


# ─── sionna.rt 를 가짜로 갈아 끼운다 (GPU·mitsuba 미사용) ─────────────────────
CALLS: list[tuple[str, dict]] = []


def _fake_radio_material(**kw):
    CALLS.append(("RadioMaterial", dict(kw)))
    return types.SimpleNamespace(**kw)


def _fake_itu_material(**kw):
    CALLS.append(("ITURadioMaterial", dict(kw)))
    return types.SimpleNamespace(**kw)


def install_fake_sionna() -> None:
    if "sionna" in sys.modules or "sionna.rt" in sys.modules:
        raise SystemExit("⛔ 진짜 sionna 가 이미 올라와 있다 — 이 검사는 깨끗한 프로세스에서만")
    rt = types.ModuleType("sionna.rt")
    rt.RadioMaterial = _fake_radio_material
    rt.ITURadioMaterial = _fake_itu_material
    rt.load_scene = lambda: types.SimpleNamespace(frequency=0.0)
    sio = types.ModuleType("sionna")
    sio.rt = rt
    sys.modules["sionna"], sys.modules["sionna.rt"] = sio, rt


def kwargs_of(mat_key: str, M) -> dict:
    CALLS.clear()
    M.make_material(mat_key, name=f"mat_{mat_key}", color=(0.5, 0.5, 0.5))
    assert len(CALLS) == 1, CALLS
    return CALLS[0][1]


def main() -> None:
    install_fake_sionna()
    import materials as M                                            # noqa: E402
    import elevation_sweep_md as ESM                                 # noqa: E402
    import argparse

    non_itu = ("plastic", "plastic_blue", "prop_plastic", "carbon", "absorber")
    itu = ("metal", "camera_assembly", "pcb", "concrete_light", "concrete_dark")

    print("\n═══ 1. 손잡이 안 켠 상태 = 예전 호출과 비트동일 ═══")
    base = {k: kwargs_of(k, M) for k in non_itu + itu}
    for k in non_itu:
        chk(f"{k}: thickness 를 안 넘긴다", "thickness" not in base[k],
            f"넘긴 인자 {sorted(base[k])}")
    for k in itu:
        chk(f"{k}(ITU): 원래대로 두께를 넘긴다", "thickness" in base[k],
            f"{base[k].get('thickness')} m")
    chk("손잡이 상태가 비어 있다", M.thickness_state() == {})

    print("\n═══ 2. set_thickness_mm(shell=2.0) — 셸만 바뀐다 ═══")
    M.set_thickness_mm(shell=2.0)
    now = {k: kwargs_of(k, M) for k in non_itu}
    for k in ("plastic", "plastic_blue"):
        chk(f"{k}: thickness = 0.002 m", abs(now[k].get("thickness", -1) - 0.002) < 1e-12)
    for k in ("prop_plastic", "carbon", "absorber"):
        chk(f"{k}: 그대로 안 넘긴다", "thickness" not in now[k])
    for k in non_itu:                       # 두께 말고는 아무것도 안 바뀌어야 한다
        a_, b_ = dict(base[k]), dict(now[k])
        b_.pop("thickness", None)
        chk(f"{k}: 두께 말고는 인자가 같다", a_ == b_)

    print("\n═══ 2b. shell·prop 을 갈라 준다 ═══")
    M.set_thickness_mm(shell=2.0, prop=1.0)
    chk("prop_plastic: 0.001 m",
        abs(kwargs_of("prop_plastic", M).get("thickness", -1) - 0.001) < 1e-12)
    chk("carbon: 여전히 안 넘긴다", "thickness" not in kwargs_of("carbon", M))

    print("\n═══ 3. 되돌리면 1 번 상태로 정확히 복귀 ═══")
    M.set_thickness_mm()
    back = {k: kwargs_of(k, M) for k in non_itu + itu}
    chk("모든 재질 호출 인자가 처음과 같다", back == base)
    chk("상태 표가 비었다", M.thickness_state() == {})

    print("\n═══ 4. 파일명 꼬리표 ═══")
    chk("안 주면 빈 문자열", ESM._tag_thickness(0.0, 0.0) == "")
    chk("shell 2 mm → _shell2mm", ESM._tag_thickness(2.0, 0.0) == "_shell2mm")
    chk("shell 1.5 · prop 1 → _shell1.5mm_prop1mm",
        ESM._tag_thickness(1.5, 1.0) == "_shell1.5mm_prop1mm")
    arms = sorted({os.path.basename(f).rsplit("_el", 1)[0]
                   for f in glob.glob(f"{ESM.SHD}/*_el*.npz")})
    hit = [a for a in arms if re.search(r"_(shell|prop)\d+(\.\d+)?mm", a)]
    chk(f"기존 샤드 {len(arms)} 팔 중 새 꼬리표와 겹치는 것 없음", not hit, str(hit))
    # 새 꼬리표가 기존 파서(_r·_p·_az·_div·_fc)에 잘못 걸리지 않는가
    probe = "sionna_p4000000000_r15_n8192_shell2mm_prop1mm_d1"
    chk("_p(\\d+) 파서가 _prop1mm 을 광선수로 오독하지 않는다",
        re.search(r"_p(\d+)", probe).group(1) == "4000000000")
    chk("_r(\\d+) 파서가 거리 15 를 그대로 읽는다",
        re.search(r"_r(\d+(?:\.\d+)?)", probe).group(1) == "15")
    chk("_fc 파서가 안 걸린다", ESM.carrier_of(probe) == ESM.FC)

    print("\n═══ 5. argparse 기본값 = 0.0 (안 주면 = 0) ═══")
    saved = sys.argv
    try:
        sys.argv = ["elevation_sweep_md.py"]
        ap = argparse.ArgumentParser()
        # main() 의 파서를 그대로 쓸 수 없으므로 **실제 파일에서** 기본값을 읽어 확인한다
        src = open(os.path.join(HERE, "elevation_sweep_md.py"), encoding="utf-8").read()
    finally:
        sys.argv = saved
    for nm in ("--shell-mm", "--prop-mm"):
        m = re.search(rf'ap\.add_argument\("{nm}", type=float, default=([0-9.]+)', src)
        chk(f"{nm} 기본값 0.0", bool(m) and float(m.group(1)) == 0.0,
            "" if m else "선언을 못 찾았다")
    ns = argparse.Namespace(shell_mm=0.0, prop_mm=0.0)
    chk("기본값이면 thickness() 가 (0,0,'')", ESM.thickness(ns) == (0.0, 0.0, ""))
    chk("인자 자체가 없어도 (0,0,'')", ESM.thickness(argparse.Namespace()) == (0.0, 0.0, ""))

    print("\n═══ 6. 단위 사고 가드 ═══")
    for bad, why in ((0.002, "미터를 그대로 친 경우 — 0.002 mm = 2 µm 가 된다"),
                     (100.0, "100 mm 재현 시도 — 인자를 빼는 게 맞다"),
                     (-1.0, "음수")):
        try:
            ESM.thickness(argparse.Namespace(shell_mm=bad, prop_mm=0.0))
            chk(f"--shell-mm {bad} 는 죽는다", False, "안 죽었다 — " + why)
        except SystemExit:
            chk(f"--shell-mm {bad} 는 죽는다", True, why)
    for good in (0.5, 1.0, 2.0, 3.0):
        chk(f"--shell-mm {good} 는 통과한다",
            ESM.thickness(argparse.Namespace(shell_mm=good, prop_mm=0.0))[0] == good)
    try:
        M.set_thickness_mm(shell=-1.0)
        chk("음수 두께는 죽는다", False)
    except ValueError:
        chk("음수 두께는 죽는다", True)
    try:
        M.set_thickness_mm(metal=2.0)
        chk("ITU 재질에 손잡이를 걸면 죽는다", False)
    except ValueError:
        chk("ITU 재질에 손잡이를 걸면 죽는다", True)
    try:
        M.set_thickness_mm(plastik=2.0)          # 오타
        chk("모르는 재질 키는 죽는다", False)
    except KeyError:
        chk("모르는 재질 키는 죽는다", True)
    chk("가드 뒤에도 상태가 안 남는다", M.thickness_state() == {})

    print("\n═══ 7. 우리 커널 팔에 두께를 주면 거부한다 (run() 실제 경로) ═══")
    #  run() 앞부분이 부르는 무거운 모듈을 가벼운 가짜로 갈아 끼운다 — 가드까지만 가면 된다.
    import numpy as np
    g = types.ModuleType("gpu"); g.pick = lambda **kw: None
    af = types.ModuleType("articulated_fast")
    af.FastPoser = lambda spec: types.SimpleNamespace(dirs=[0, 1, 2, 3], f=None, g=None)
    af.rotor_phases = lambda t, rpms, dirs: np.zeros((len(t), len(dirs)))
    dr = types.ModuleType("drones")
    dr.DRONES = {ESM.TJ.get("drone", "matrice4e"): types.SimpleNamespace(
        key=ESM.TJ.get("drone", "matrice4e"), hover_rpm=6000.0)}
    dr.DRONE_GROUP_MAT = {"body": ("plastic", "")}
    for nm, mod in (("gpu", g), ("articulated_fast", af), ("drones", dr)):
        sys.modules[nm] = mod
    ns = argparse.Namespace(engine="ours", shard=0, nshards=1, els="0", spp=0,
                            range_m=15.0, drone="", sw="", stock=False, only="",
                            plane_wave=False, n_poses=0, max_depth=0,
                            az_deg=float("nan"), div=0, parts="", ptd=False,
                            overwrite=False, fc_ghz=3.5, grid_shift="",
                            shell_mm=2.0, prop_mm=0.0)
    try:
        ESM.run(ns)
        chk("ours + --shell-mm 은 거부된다", False, "안 죽었다")
    except SystemExit as e:
        chk("ours + --shell-mm 은 거부된다", "shell-mm" in str(e), str(e)[:60])

    print(f"\n═══ 결과: {'전부 통과' if not FAILED else '실패 ' + str(len(FAILED))} ═══")
    if FAILED:
        for f in FAILED:
            print(f"  ⛔ {f}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
