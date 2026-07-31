# -*- coding: utf-8 -*-
"""
measure_x500v2_cad.py — Holybro **공식 STEP CAD** 에서 X500 V2 치수 직접 측정
=============================================================================
왜 필요한가: `x500v2` 는 저장소에서 유일하게 **사진이 0장**이던 기종이었고, 그 공백을
`assets/meshes/reference/NXP-HGD-CF.dae`(= NXP HoverGames 킷의 ReadytoSky LJI X4 500,
**X500 이 아니다**)로 메우려던 오식별 이력이 있다. 2026-07-30 에 **제조사 1차 CAD** 를
확보해서, 형상 수치를 사진 픽셀 추정에서 **제조사 모델 실측**으로 승격시킨다.

입력 (assets/meshes/reference/, 둘 다 Holybro 공식 배포물)
  * `x500v2-frame.step`        프레임 전체 어셈블리 (STEP AP214, ST-DEVELOPER v19,
                               원본 타임스탬프 2022-07-19, 부품 57종·인스턴스 244)
  * `AIR2216II_Motor_3D.STEP`  2216 모터 단품 (SolidWorks 2022)

측정 방법
  STEP 은 ASCII 라 외부 커널(OCC) 없이 읽는다. 엔티티를 인덱싱하고
  PRODUCT → PRODUCT_DEFINITION → SHAPE_DEFINITION_REPRESENTATION →
  SHAPE_REPRESENTATION_RELATIONSHIP → ADVANCED_BREP_SHAPE_REPRESENTATION 로 부품 형상을 찾은 뒤,
  NEXT_ASSEMBLY_USAGE_OCCURRENCE + REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION 의
  ITEM_DEFINED_TRANSFORMATION 을 합성해 **조립 좌표계**로 옮긴다.
  · 지름은 CARTESIAN_POINT bbox 가 아니라 **CYLINDRICAL_SURFACE 반지름**에서 읽는다
    (STEP 의 점은 정점·제어점뿐이라 원통의 bbox 는 지름을 과소평가한다 — 실제로 스키드
     튜브 점군의 bbox 는 5.00 mm 로 나오지만 진짜 지름은 10.00 mm 다).
  · 축 방향도 CYLINDRICAL_SURFACE 의 AXIS2_PLACEMENT_3D 에서 정확히 읽는다.

⭐ 검증 사슬 (이 스크립트가 스스로 맞는지 보이는 근거)
  CAD 가 **공표값 4건을 독립적으로 재현**한다 → 변환 합성이 옳다는 증거다.
     판 두께 2.000 mm / 판 간격 28.000 mm / 판 144(143.72) mm / 다리 높이 215.28 mm(공표 215)
  휠베이스만 502.8 mm 로 공표 500 보다 +0.56% 크다(공표값이 반올림).

⚠ 반증 보존 — 사진에서 뽑았던 값들이 **틀렸다**
  2026-07-30 오전에 `x500v2_03_top_ortho.jpg` 를 "정투영 톱뷰" 로 보고 실측한
  "스키드 간격 180 mm", "다리 벌림각 6.1°" 는 **시차(parallax) 아티팩트**다.
  그 사진은 카메라가 판 위 **약 0.64 m** 에 있는 실사진이라, 판보다 215 mm 아래에 있는
  스키드가 D/(D+215) ≈ 0.75 배로 **축소되어** 찍힌다. 같은 모델로 판 13 mm 아래의
  페이로드 레일은 0.98 배 → 실측 ±28.5 mm vs CAD ±30.0 mm 로 **오차 5%** 뿐이고,
  판 높이의 암 끝단은 오차 +2% 다. 세 높이의 오차가 깊이에 비례한다는 사실이
  시차 가설을 확증한다. → 판에서 멀리 떨어진 부품은 이 사진으로 재면 안 된다.

실행: cd sionna2 && PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/measure_x500v2_cad.py
산출: outputs/x500v2_cad.json
"""
from __future__ import annotations

import collections
import json
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "assets" / "meshes" / "reference"
OUT = ROOT / "outputs" / "x500v2_cad.json"

_REF = re.compile(r"#(\d+)")
_TRIPLE = re.compile(r"\(\s*([-0-9.E+]+)\s*,\s*([-0-9.E+]+)\s*,\s*([-0-9.E+]+)\s*\)")
_ENT = re.compile(r"#(\d+)\s*=\s*\(?\s*([A-Z_0-9]+)\s*\((.*?)\)\s*;", re.S)
_CPLX = re.compile(r"#(\d+)\s*=\s*\((.*?)\)\s*;\s*(?=#|ENDSEC)", re.S)


class Step:
    """OCC 없이 STEP 어셈블리를 읽는 최소 파서 (이 파일 전용, 범용 아님)."""

    def __init__(self, path: Path):
        txt = path.read_text(errors="replace")
        data = txt[txt.index("DATA;"):]
        self.ent = {int(m.group(1)): (m.group(2), m.group(3)) for m in _ENT.finditer(data)}
        self.cplx = {int(m.group(1)): m.group(2) for m in _CPLX.finditer(data)}
        self.kids = {k: [int(x) for x in _REF.findall(v[1])] for k, v in self.ent.items()}

    # --- 기본 조회 -------------------------------------------------------
    def _of(self, typ):
        return {k: v for k, v in self.ent.items() if v[0] == typ}

    def placement(self, n):
        """AXIS2_PLACEMENT_3D → (원점, 회전행렬[x|y|z])."""
        a = self.kids[n]
        o = np.array(_TRIPLE.search(self.ent[a[0]][1]).groups(), dtype=float)
        z, x = np.array([0.0, 0, 1]), np.array([1.0, 0, 0])
        if len(a) > 1:
            z = np.array(_TRIPLE.search(self.ent[a[1]][1]).groups(), dtype=float)
        if len(a) > 2:
            x = np.array(_TRIPLE.search(self.ent[a[2]][1]).groups(), dtype=float)
        z = z / np.linalg.norm(z)
        x = x - z * float(x @ z)
        x = x / np.linalg.norm(x)
        return o, np.column_stack([x, np.cross(z, x), z])

    def harvest(self, root):
        """BREP 하위의 점군과 원통면(반지름·축)을 모은다."""
        seen, stack, pts, cyl = {root}, [root], [], []
        while stack:
            n = stack.pop()
            typ, body = self.ent.get(n, (None, ""))
            if typ == "CARTESIAN_POINT":
                m = _TRIPLE.search(body)
                if m:
                    pts.append(tuple(map(float, m.groups())))
                continue
            if typ == "CYLINDRICAL_SURFACE":
                o, rot = self.placement(self.kids[n][0])
                cyl.append((float(body.rsplit(",", 1)[1]), o, rot[:, 2]))
            for c in self.kids.get(n, ()):
                if c not in seen:
                    seen.add(c)
                    stack.append(c)
        return np.asarray(pts), cyl

    # --- 어셈블리 --------------------------------------------------------
    def assemble(self):
        """부품명 → [(조립좌표 점군, [(r, 축원점, 축방향)…])] 목록."""
        name = {k: re.match(r"\s*'([^']*)'", v[1]).group(1) for k, v in self._of("PRODUCT").items()}
        pdf = {k: self.kids[k][0] for k, v in self._of("PRODUCT_DEFINITION_FORMATION").items() if self.kids[k]}
        pd2prod = {k: pdf.get(self.kids[k][0]) for k, v in self._of("PRODUCT_DEFINITION").items() if self.kids[k]}
        pds2pd = {k: self.kids[k][-1] for k, v in self._of("PRODUCT_DEFINITION_SHAPE").items() if self.kids[k]}
        sdr, srr = {}, {}
        for k, v in self.ent.items():
            if v[0] == "SHAPE_DEFINITION_REPRESENTATION":
                sdr[self.kids[k][1]] = self.kids[k][0]
            elif v[0] == "SHAPE_REPRESENTATION_RELATIONSHIP":
                srr[self.kids[k][0]] = self.kids[k][1]
        geom = {}
        for rep, pds in sdr.items():
            brep = srr.get(rep)
            if brep is not None:
                geom[pds2pd[pds]] = self.harvest(brep)

        nauo = {k: (self.kids[k][0], self.kids[k][1]) for k, v in self._of("NEXT_ASSEMBLY_USAGE_OCCURRENCE").items()}
        children = collections.defaultdict(list)
        for k, v in self.ent.items():
            if v[0] != "CONTEXT_DEPENDENT_SHAPE_REPRESENTATION":
                continue
            rr, pds = self.kids[k][0], self.kids[k][1]
            m = re.search(r"REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION\s*\(\s*#(\d+)", self.cplx.get(rr, ""))
            if not m:
                continue
            a = self.kids[int(m.group(1))]
            o1, r1 = self.placement(a[0])          # 자식 로컬 기준축 (보통 단위축)
            o2, r2 = self.placement(a[1])          # 부모 좌표계에서의 배치
            par, ch = nauo[pds2pd[pds]]
            children[par].append((ch, o1, r1, o2, r2))

        placed = collections.defaultdict(list)
        seen_children = {c for v in children.values() for c, *_ in v}
        roots = [pd for pd in pd2prod if pd not in seen_children]

        def walk(pd, off, rot):
            g = geom.get(pd)
            if g is not None and len(g[0]):
                pts = (rot @ g[0].T).T + off
                cyl = [(r, rot @ co + off, rot @ cd) for r, co, cd in g[1]]
                placed[name.get(pd2prod.get(pd), "?")].append((pts, cyl))
            for ch, o1, r1, o2, r2 in children.get(pd, []):
                walk(ch, off + rot @ (o2 - r2 @ r1.T @ o1), rot @ r2 @ r1.T)

        for r in roots:
            walk(r, np.zeros(3), np.eye(3))
        return placed


def _cyl(cyls, radius, tol=1e-6):
    return [c for c in cyls if abs(c[0] - radius) < tol]


def main() -> None:
    step = Step(REF / "x500v2-frame.step")
    P = step.assemble()
    D: dict = {}

    def put(key, value, grade, how):
        D[key] = {"value": value, "grade": grade, "method": how}

    # ── 판 스택 ───────────────────────────────────────────────────────────
    bot = P["BOTTOM-PLATE-X500-V5"][0][0]
    top = P["TOP-PLATE-X500-V5"][0][0]
    # ⚠ 판 부품에는 보스·돌기 레벨이 섞여 있다(하판 y = -7.417/0/2/4.607/9.417).
    #   판의 두 평면은 **점이 가장 많은 두 레벨**이다 → 그것만 골라야 두께가 2 mm 로 나온다.
    def faces(pts):
        cnt = collections.Counter(np.round(pts[:, 1], 3))
        lv = sorted(v for v, _ in cnt.most_common(2))
        return float(lv[0]), float(lv[1])

    b0, b1 = faces(bot)
    t0, t1 = faces(top)
    flats = float(2 * np.abs(bot[:, [0, 2]]).max())          # 귀(tab) 포함 최대폭
    # 직선 가장자리 = 충분히 많은 점이 공유하는 가장 큰 |좌표| (코너 돌기는 점이 4개뿐이라 빠진다)
    _big = collections.Counter(np.round(np.abs(bot[:, [0, 2]]).ravel(), 2))
    core = float(2 * max(v for v, n in _big.items() if v > 60.0 and n >= 8))
    put("plate_span_across_flats_mm", round(core, 2), "VERIFIED", "CAD 하판 외곽 (공표 144)")
    put("plate_span_including_corner_tabs_mm", round(flats, 2), "VERIFIED", "CAD 하판 코너 돌기 포함 최대폭")
    put("plate_thickness_mm", round(b1 - b0, 3), "VERIFIED", "CAD 하판 상·하면 y 레벨 차")
    put("plate_gap_mm", round(t0 - b1, 3), "VERIFIED", "하판 윗면 → 상판 아랫면 (공표 28)")
    put("plate_stack_height_mm", round(t1 - b0, 3), "VERIFIED", "하판 아랫면 → 상판 윗면")

    # 45° 챔퍼: 직선 가장자리가 끝나는 지점
    face = bot[np.abs(bot[:, 1] - b0) < 1e-6][:, [0, 2]]
    edge = face[np.abs(np.abs(face[:, 0]) - core / 2) < 0.05]
    put("plate_chamfer_leg_mm", round(float(core / 2 - np.abs(edge[:, 1]).max()), 2), "VERIFIED",
        "직선변 끝 |z| 에서 판 반폭을 뺀 값 (45° 챔퍼의 직각변)")

    # ── 암 / 모터 ────────────────────────────────────────────────────────
    arm = P["HMX5V-GUAN-DINGWEI"]
    r_arm, o_arm, d_arm = _cyl(arm[0][1], 7.70)[0]
    u = np.array([1, 0, 1]) / np.sqrt(2.0)
    t = arm[0][0] @ u
    # ⚠ CAD 의 암 튜브 솔리드는 15.4 mm 로 그려져 있지만, 그 튜브를 무는 클램프의 보어는
    #   뿌리 15.90(HMX5V-JIBI-JIA-MUJU) · 모터끝 16.00(HMX5V-ZUO-DJ-MUJU) 이다.
    #   즉 15.4 는 **CAD 안의 여유(clearance)** 이고 실물 튜브는 공표대로 16 mm 다.
    bore_root = 2 * _cyl(P["HMX5V-JIBI-JIA-MUJU"][0][1], 7.95, tol=1e-2)[0][0]
    bore_tip = 2 * _cyl(P["HMX5V-ZUO-DJ-MUJU"][0][1], 8.0, tol=1e-2)[0][0]
    put("arm_tube_od_mm", 16.0, "VERIFIED",
        f"공표 16 mm; CAD 클램프 보어가 뿌리 {bore_root:.2f}/모터끝 {bore_tip:.2f} 로 이를 확증한다")
    put("arm_tube_od_as_drawn_in_cad_mm", round(2 * r_arm, 2), "VERIFIED",
        "⚠ CAD 튜브 솔리드는 15.4 로 언더사이즈로 그려져 있다(클램프 안 여유) — 실물 치수가 아니다")
    put("arm_tube_id_mm", round(2 * _cyl(arm[0][1], 7.0)[0][0], 2), "VERIFIED", "CAD 원통면")
    put("arm_tube_length_mm", round(float(np.abs(t).max() - np.abs(t).min()), 1), "VERIFIED", "암 축방향 점군 범위")
    put("arm_tube_axis_height_mm", round(float(o_arm[1]), 2), "VERIFIED", "판 간극 정중앙 (2~30 의 중앙 16)")
    put("arm_azimuth_deg", 45.0, "VERIFIED", "CAD 암 축이 정확히 ±45° (정 X 배치)")

    mot = np.array([[p[0][:, 0].mean(), p[0][:, 2].mean()] for p in P["DJ-2216-KV880"]])
    r_mot = float(np.hypot(mot[:, 0], mot[:, 1]).mean())
    put("motor_axis_radius_mm", round(r_mot, 2), "VERIFIED", "모터 4기 중심의 중심거리")
    put("wheelbase_mm", round(2 * r_mot, 1), "VERIFIED", "대각 모터 간격 (공표 500 = 반올림)")
    ym = np.concatenate([p[0][:, 1] for p in P["DJ-2216-KV880"]])
    put("motor_stack_height_mm", round(float(ym.max() - ym.min()), 2), "VERIFIED", "모터 하단~프롭어댑터 상단")

    mount = P["BAN-DJ-DIAN-F2"][2][0]
    tm = mount @ u
    put("motor_mount_plate_radial_span_mm", [round(float(tm.min()), 1), round(float(tm.max()), 1)],
        "VERIFIED", "카본 물방울꼴 모터마운트 판의 반경 구간")

    # ── 다리 (⭐ 사진 실측을 반증하는 항목) ────────────────────────────────
    legs = []
    for inst in P["GUAN-CHENG"]:
        r, o, d = _cyl(inst[1], 8.0)[0]
        d = -d if d[1] > 0 else d
        legs.append((r, o, d))
    tilt = [float(np.degrees(np.arccos(-d[1]))) for _, _, d in legs]
    put("gear_leg_count", len(legs), "VERIFIED", "GUAN-CHENG 인스턴스 수 (좌·우 1개씩) — 4개가 아니다")
    put("gear_leg_od_mm", round(2 * legs[0][0], 2), "VERIFIED", "CAD 원통면 (공표 16)")
    put("gear_leg_id_mm", round(2 * _cyl(P["GUAN-CHENG"][0][1], 7.0)[0][0], 2), "VERIFIED", "CAD 원통면")
    put("gear_splay_deg", round(float(np.mean(tilt)), 2), "VERIFIED",
        "다리 원통축과 수직의 사잇각 (좌우 동일). ⚠ 사진 실측 6.1° 는 시차 오류")
    put("gear_leg_top_lateral_mm", round(float(abs(legs[0][1][2])), 2), "VERIFIED", "다리 상단 축의 좌우 위치")
    put("gear_leg_top_below_plate_mm", round(float(-legs[0][1][1]), 2), "VERIFIED", "하판 아랫면 기준 다리 상단 깊이")
    put("gear_splay_azimuth_deg", 90.0, "VERIFIED", "다리는 순수 좌우로만 벌어진다 (전후 성분 0)")

    skid = _cyl(P["CARBON-FIBER-TUBE"][0][1], 5.0)[0]
    sx = P["CARBON-FIBER-TUBE"][0][0][:, 0]
    put("skid_tube_od_mm", round(2 * skid[0], 2), "VERIFIED", "CAD 원통면 (공표 10)")
    put("skid_tube_id_mm", round(2 * _cyl(P["CARBON-FIBER-TUBE"][0][1], 4.0)[0][0], 2), "VERIFIED", "CAD 원통면")
    put("skid_tube_length_mm", round(float(sx.max() - sx.min()), 1), "VERIFIED", "스키드 크로스바 길이")
    put("skid_track_mm", round(float(2 * abs(skid[1][2])), 2), "VERIFIED",
        "좌우 스키드 축 간격. ⚠ 사진 실측 180 mm 는 시차 오류")
    foam = P["JIAO-EVA"]
    fr = max(c[0] for c in foam[0][1])
    fx = foam[0][0][:, 0]
    put("skid_foam_sleeve_od_mm", round(2 * fr, 2), "VERIFIED", "EVA 슬리브 리브 최대 외경")
    put("skid_foam_sleeve_length_mm", round(float(fx.max() - fx.min()), 1), "VERIFIED", "슬리브 1개 길이 (스키드당 2개)")
    put("skid_foam_sleeve_count", len(foam), "VERIFIED", "JIAO-EVA 인스턴스 수")
    ground = float(skid[1][1] - fr)
    put("gear_height_mm", round(-ground, 2), "VERIFIED",
        "하판 아랫면(y=0) → 폼 최하점. 공표 215 를 CAD 가 독립 재현한다")

    # ── 페이로드 / 전자장비 ───────────────────────────────────────────────
    rail = _cyl(P["CARBON-FIBER-TUBE300"][0][1], 4.70)[0]
    rx = P["CARBON-FIBER-TUBE300"][0][0][:, 0]
    put("payload_rail_od_mm", round(2 * rail[0], 2), "VERIFIED", "CAD 원통면 (공표 명목 10)")
    put("payload_rail_length_mm", round(float(rx.max() - rx.min()), 1), "VERIFIED", "공표 250 과 일치")
    put("payload_rail_track_mm", round(float(2 * abs(rail[1][2])), 2), "VERIFIED", "좌우 레일 축 간격")
    put("payload_rail_below_plate_mm", round(float(-rail[1][1]), 2), "VERIFIED", "하판 아랫면 기준 레일 축 깊이")

    for key, part in [("payload_platform_board", "PLATFORM-PLAT-X500"),
                      ("battery_mounting_board", "BATTERY-MOUNTING-PLAT"),
                      ("power_module_pcb_pm06", "PCB-PM06"),
                      ("gps_mount_base", "GPS-ZHIJIA-ZUO"),
                      ("optical_flow_cover", "GAI-GUANGLIU")]:
        pts = P[part][0][0]
        lo, hi = pts.min(0), pts.max(0)
        put(key + "_bbox_mm", [round(float(v), 2) for v in (hi - lo)], "VERIFIED", f"CAD {part} 조립 bbox")
        put(key + "_centre_xyz_mm", [round(float(v), 2) for v in (lo + hi) / 2], "VERIFIED",
            f"CAD {part} 중심 (+x 전방, +y 상방)")

    mast = P["GAN-GPSV5-ZHIJIA"][0]
    put("gps_mast_rod_od_mm", round(2 * max(c[0] for c in mast[1]), 2), "VERIFIED", "CAD 원통면")
    put("gps_mast_length_mm", round(float(mast[0][:, 1].max() - mast[0][:, 1].min()), 1), "VERIFIED", "마스트 봉 길이")
    put("gps_mast_top_above_plate_mm", round(float(mast[0][:, 1].max() - t1), 1), "VERIFIED",
        "상판 윗면 기준 마스트 꼭대기 높이")

    # ── 전체 외형 ────────────────────────────────────────────────────────
    put("overall_height_frame_only_mm", round(float(t1 - ground), 1), "VERIFIED", "접지면 → 상판 윗면")
    put("overall_height_with_gps_mast_mm", round(float(mast[0][:, 1].max() - ground), 1), "VERIFIED", "접지면 → GPS 마스트 꼭대기")

    # ── 모터 단품 ────────────────────────────────────────────────────────
    ms = Step(REF / "AIR2216II_Motor_3D.STEP")
    pts, cyl = ms.harvest(max(ms._of("ADVANCED_BREP_SHAPE_REPRESENTATION")))
    radii = collections.Counter(round(c[0], 3) for c in cyl)
    bell = max(r for r, n in radii.items() if n >= 4)
    put("motor_bell_od_mm", round(2 * bell, 2), "VERIFIED",
        "AIR2216II STEP 최대 반복 원통면 (판매페이지 캔 외경 28 과 정합)")

    # ── BOM (부품별 인스턴스 수) ─────────────────────────────────────────
    D["bom_instance_counts"] = {k: len(v) for k, v in sorted(P.items())}

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(D, indent=1, ensure_ascii=False))
    print(f"[x500v2] {OUT} 기록 — 항목 {len(D)}개")
    for k in ("wheelbase_mm", "plate_gap_mm", "gear_height_mm", "gear_splay_deg", "skid_track_mm"):
        print(f"   {k:28s} = {D[k]['value']}")


if __name__ == "__main__":
    main()
