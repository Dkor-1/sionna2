# -*- coding: utf-8 -*-
"""
build_part03_target_mesh.py — 부 3 「표적 메쉬」 → 편 15~17
==========================================================================================
부 3 이 답하는 질문 하나
    **기체 7종을 무엇에서 지었고 실물과 얼마나 맞나.**

편 하나 = 중심 메시지 하나 (제목이 곧 그 편의 결론 문장이다)

    15 mesh-build    기체 7종을 제원과 제조사 CAD 치수에서 세우고 부품을 재질 그룹으로 유지했다
    16 mesh-vs-real  외형이 실물과 얼마나 맞는지를 사진 IoU·CAD 치수·실물 스캔 세 자로 쟀다
    17 materials     도전성 재질이 면적의 45.3% 로 Σ|Γ|A 의 73.5% 를 낸다

어디서 왔나 (재구성 전 → 후)
    `report02_target.ipynb` c2~c6
    계획: `outputs/restruct_exec_plan.json : reports[no in 15..17]`

⚠ 이 부는 **메쉬만** 다룬다. 그 메쉬 위에서 도는 산란 커널은 부 4, σ 를 측정에 맞추는 앵커는
   부 5 다 — 같은 옛 빌더(`src/make_report02_target.py`)에서 왔지만 편은 갈라져 있다.

실행
    cd /home/yunjung/workspace/sionna2
    PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part03_target_mesh.py

⚠ GPU 도 Sionna 실행도 필요 없다.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(_ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from report_registry import index_shard, nb_path, ref, ref_part          # noqa: E402
from report_style import (build_notebook, caption, fetch, header, md,    # noqa: E402
                          next_steps, num, table, table_from)

# --------------------------------------------------------------------------- #
#  근거 파일
# --------------------------------------------------------------------------- #
DER = "outputs/report02_derived.json"        # 이 편의 파생 원장(메쉬·사진·CAD·재질)
MFX = "outputs/meshfix_applied.json"         # 형상 정정이 옮긴 것
PH4 = "outputs/phantom4_scan_compare.json"   # 실물 스캔 대조
RCAD = "outputs/real_cad_compare.json"       # 실물 유래 CAD 대조
COM = "outputs/community_compare.json"       # 커뮤니티 메쉬 대조
MFX_ATK = "outputs/meshfix_attack.json"      # 형상 정정 적대검증 — σ 재계산 전 관문
GAL = "outputs/mesh_gallery.json"            # 메쉬 함대 원장 — 모집단(σ 함대보다 넓다)
AGI = "outputs/angle_gamma_impact.json"      # Γ(θ) 각도 모양 — 커널이 |Γ| 에 곱하는 축

FIG = "../outputs/figures"

#: 메쉬 함대 모집단 — σ 함대 7종보다 넓다. 원장 목록의 길이라 함대가 바뀌면 따라 바뀐다.
_FLEET_N = len(fetch((GAL, "order_by_size")))


def _n(key: str, src: str, fmt: str | None = None, unit: str = "") -> str:
    return num(None, (src, key), fmt, unit)


def _fig(no: int, stem: str, question: str) -> list[str]:
    return [f"![{stem}]({FIG}/{stem}.png)", "", caption(no, question)]


def _repro(cmd_extra: list[str], out: list[str], runtime: str, note: str = "") -> dict:
    d = dict(cmd=cmd_extra + ["PYTHONPATH=src python src/build_part03_target_mesh.py"],
             out=out, runtime=runtime)
    if note:
        d["note"] = note
    return d


_DERIVE_CMD = "PYTHONPATH=src python src/make_report02_target.py --derive-only"


# =========================================================================== #
#  편 15 — mesh-build
# =========================================================================== #
def report_15_mesh_build():
    return [
        header(
            num=15,
            title="기체 7종을 제원과 제조사 CAD 치수에서 세우고 부품을 재질 그룹으로 유지했다",
            did="공식 외형(L×W×H)·모터 대각·프롭 지름에 맞춰 기체 7종의 메쉬를 세우고, 부품을 "
                "재질 그룹으로 나눠 유지했다.",
            results=[
                f"메쉬 함대는 {_FLEET_N}종이고(⟨{GAL} : order_by_size⟩ 길이) 이 편의 표는 "
                f"그중 σ 함대 {_n('mesh.n', DER, '{:.0f}', '종')} 이다 — 크기 극값은 함대 "
                f"전체에서 {_n('mesh.smallest', DER)} "
                f"{_n('mesh.smallest_span_mm', DER, '{:.0f}', 'mm')} 부터 "
                f"{_n('mesh.largest', DER)} "
                f"{_n('mesh.largest_span_mm', DER, '{:.0f}', 'mm')} 까지 "
                f"{_n('mesh.span_ratio', DER, '{:.2f}')}배다.",

                f"부품은 {_n('mesh.n_parts_total', DER, '{:.0f}', '개')}, 삼각형은 "
                f"{_n('mesh.n_tris_total', DER, '{:,.0f}', '개')} 이고, 부품 수는 그룹별 "
                f"연결성분의 합이다 — 모터 4개는 4로 센다.",

                f"전기적 크기 kr 은 "
                f"{_n('electrical.kr_min', DER, '{:.1f}')}"
                f"({_n('electrical.kr_min_name', DER)} @ {_n('electrical.kr_min_band', DER)})부터 "
                f"{_n('electrical.kr_max', DER, '{:.1f}')}"
                f"({_n('electrical.kr_max_name', DER)} @ {_n('electrical.kr_max_band', DER)})까지 "
                f"벌어진다.",

                f"외접반경 r 은 빌더가 메쉬에서 직접 다시 재고 갤러리 원장과 대조한다 — 최대 차이 "
                f"{_n('mesh.r_crosscheck_max_pct', DER, '{:.2f}', '%')} 다.",

                f"이 편의 그림과 표는 {_n('_meta.date', MFX)} 형상 정정 **후** 메쉬에서 "
                f"재측정한 값이다. 정정이 옮긴 양은 아래에 그대로 적었다.",
            ],
            method=[
                ("치수 출처", "공식 외형(L×W×H)·모터 대각·프롭 지름 — 제원과 제조사 CAD 치수표 "
                            "(`src/drones.py` `DroneSpec` · 치수표)"),
                ("부품 유지", "부품을 **재질 그룹**으로 나눠 유지한다 — 산란 커널이 그룹마다 "
                            "다른 |Γ| 를 읽기 때문이다"),
                ("외접반경", "빌더가 메쉬 정점에서 직접 재고 갤러리 원장과 교차확인한다"),
                ("실측 대상", "matrice4e · mini5pro 가 실측 대상이다 — 표에서 ⭐ 로 표시된다"),
            ],
            repro=_repro([_DERIVE_CMD, "PYTHONPATH=src python src/viz_mesh_gallery.py"],
                         [DER, MFX], "약 2분 (GPU 0장 — 메쉬 조립과 렌더다)",
                         "메쉬 지문(꼭짓점과 삼각형 전체를 한 값으로 요약한 것)이 "
                         "`outputs/meshfix_applied.json:edits` 에 기록된다"),
        ),

        md("## 무엇에서 지었나", "",
           "메쉬는 제원과 제조사 CAD 치수에서 세운다 — 공식 외형(L×W×H)·모터 대각·프롭 지름에 "
           "맞춘 뒤 부품을 **재질 그룹**으로 나눠 유지한다(`src/drones.py` `DroneSpec` · 치수표"
           "). **matrice4e · mini5pro 가 실측 대상**이다.", "",
           f"크기 폭이 {_n('mesh.span_ratio', DER, '{:.2f}')}배다 — "
           f"{_n('mesh.smallest', DER)} "
           f"{_n('mesh.smallest_span_mm', DER, '{:.0f}', 'mm')} 대 "
           f"{_n('mesh.largest', DER)} "
           f"{_n('mesh.largest_span_mm', DER, '{:.0f}', 'mm')}, 메쉬 함대 {_FLEET_N}종 전체에서 "
           f"잰 극값이다(이 편의 표는 그중 σ 함대 {_n('mesh.n', DER, '{:.0f}', '종')}). 그 폭이 "
           f"kr 을 "
           f"{_n('electrical.kr_min', DER, '{:.1f}')}"
           f"({_n('electrical.kr_min_name', DER)} @ {_n('electrical.kr_min_band', DER)})~"
           f"{_n('electrical.kr_max', DER, '{:.1f}')}"
           f"({_n('electrical.kr_max_name', DER)} @ {_n('electrical.kr_max_band', DER)})로 "
           f"벌리고, 거기가 {ref('po-knee')} 의 눈금이 걸리는 자리다."),

        md("## 일곱 대는 어떻게 생겼나", "",
           *_fig(1, "mesh_gallery_all",
                 "우리가 지은 일곱 대는 어떻게 생겼고 서로 얼마나 다른가?")),

        md(table_from(f"{DER}:mesh.rows",
                      [("기체", "airframe"), ("L×W×H [mm] (프롭 포함)", "lwh_mm"),
                       ("무게 [g]", "weight_g"), ("부품", "n_parts"),
                       ("재질 그룹", "n_groups"), ("삼각형", "n_tris"),
                       ("외접반경 r [m]", "r_encl_m"), ("kr @5G", "kr_5g")],
                      fmt={"weight_g": "{:.0f}", "n_parts": "{:.0f}", "n_groups": "{:.0f}",
                           "n_tris": "{:,.0f}", "r_encl_m": "{:.3f}", "kr_5g": "{:.1f}"})),

        md("## 표를 읽는 법, 그리고 형상 정정이 옮긴 양", "",
           f"맨 오른쪽 **kr** 은 표적을 파장으로 잰 크기다 — 외접반경 r 에 파수 k = 2π/λ 를 곱한 "
           f"값이고, 클수록 파장에 비해 몸이 크다는 뜻이다. 외접반경 r 은 이 빌더가 메쉬에서 직접 "
           f"다시 재고 갤러리 원장과 대조한다(최대 차이 "
           f"{_n('mesh.r_crosscheck_max_pct', DER, '{:.2f}', '%')}).", "",
           f"위 그림과 표는 {_n('_meta.date', MFX)} 형상 정정 **후** 메쉬에서 재측정한 값이다. "
           f"그날 Matrice 4E · Mini 2 · X500 V2 의 형상 상수가 공식 CAD 실측으로 정정되면서 "
           f"몸통을 공표 높이에 맞추던 z 축 배율이 Matrice 4E "
           f"{_n('per_drone.matrice4e.fit_scale_before[2]', MFX, '{:.3f}')}→"
           f"{_n('per_drone.matrice4e.fit_scale_after[2]', MFX, '{:.3f}')} · Mini 2 "
           f"{_n('per_drone.mini2.fit_scale_before[2]', MFX, '{:.3f}')}→"
           f"{_n('per_drone.mini2.fit_scale_after[2]', MFX, '{:.3f}')} 로 움직였고 세 기체의 메쉬 "
           f"지문이 셋 다 달라졌다. X500 V2 는 배율 대신 삼각형이 "
           f"{_n('per_drone.x500v2.n_tri_before', MFX, '{:,.0f}')}→"
           f"{_n('per_drone.x500v2.n_tri_after', MFX, '{:,.0f}')} 로 바뀐 쪽이다 "
           f"⟨{MFX} : edits⟩."),

        next_steps([
            ("이 메쉬의 외형을 사진·공식 CAD·실물 스캔 세 자로 잰다",
             "메쉬가 실물과 얼마나 맞는지가 지표마다 눈금과 함께 확정된다",
             ref("mesh-vs-real", short=True)),
            ("부품 그룹마다 재질을 붙여 PO 적분의 물리 입력을 만든다",
             "면적의 몇 %가 반사 진폭의 몇 %를 내는지가 확정된다",
             ref("materials", short=True)),
            ("σ 를 다시 돌리기 전에 형상 관문을 통과시킨다 — 선언된 기하 결함을 끄거나 고치고, "
             "σ 캐시 키에 메쉬 지문을 넣고, 봉인해 둔 예측과 대조한다",
             "새 σ 가 형상 정정 때문에 움직인 것인지 다른 것 때문인지가 구별된다",
             f"⟨{MFX_ATK} : recommended_gate_before_any_sigma_claim⟩"),
            ("형상 원장 셋(사진·공식 CAD·재질)을 정정된 메쉬로 다시 돌린다",
             "사진·CAD·재질 표가 갤러리(재측정 완료)와 같은 형상 세대 위에 선다",
             "`src/viz_mesh_photo.py` · `viz_cad_compare.py` · `viz_mesh_material.py`"),
            ("이 부의 그림 넷을 게재 규격(벡터 + 300 dpi · 8 pt)으로 다시 그린다",
             "원고 그림 전부가 2단 조판 축소에서 살아남는다",
             "`src/viz_mesh_gallery.py` · `src/viz_mesh_material.py`"),
            ("정정된 메쉬로 σ 격자를 같은 설정에서 다시 낸다",
             "형상 정정이 σ 를 어느 방향으로 얼마나 옮기는지가 기체별로 확정된다",
             ref("fleet-prereg", short=True)),
        ]),
    ]


# =========================================================================== #
#  편 16 — mesh-vs-real
# =========================================================================== #
def report_16_mesh_vs_real():
    return [
        header(
            num=16,
            title="메쉬 외형이 실제 기체와 얼마나 맞는지를 사진 IoU·CAD 치수·실물 스캔 "
                  "세 자로 쟀다",
            did="사진 실루엣 IoU · 제조사 CAD 치수 · 실물 유래 메쉬 σ 세 가지 검사를 각각 자기 "
                "바닥과 함께 재서 한 표에 올렸다.",
            results=[
                f"사진 {_n('photo.n_pairs', DER, '{:.0f}', '장')} 을 정합해 실루엣 IoU 를 쟀다 — "
                f"{_n('photo.worst_iou', DER, '{:.3f}')}~{_n('photo.best_iou', DER, '{:.3f}')} "
                f"이고 자기복제 상한 대비 "
                f"{_n('photo.worst_pct', DER, '{:.0f}')}~"
                f"{_n('photo.best_pct', DER, '{:.0f}', '%')} 다.",

                f"그 상한 자체가 "
                f"{_n('photo.ceiling_min', DER, '{:.3f}')}~"
                f"{_n('photo.ceiling_max', DER, '{:.3f}')} 다 — 같은 메쉬로 만든 가짜 사진을 같은 "
                f"파이프라인에 넣었을 때의 값이고, 암·블레이드가 몇 px 이라 1.0 아래에 있다.",

                f"제조사 CAD 어셈블리 {_n('cad.n_assemblies', DER, '{:.0f}', '종')} · 치수 "
                f"{_n('cad.n_dims', DER, '{:.0f}', '개')} 를 맞대면 최대 편차가 CAD 대비 "
                f"{_n('cad.worst_vs_cad_pct', DER, '{:.2f}', '%')} · 발행 제원 대비 "
                f"{_n('cad.worst_vs_published_pct', DER, '{:.2f}', '%')} 다.",

                f"실물 유래 메쉬와의 Δ 방위평균 σ 는 "
                f"{_n('d_sigma_db', PH4, '{:+.2f}')} · "
                f"{_n('typhoon.d_sigma_db', RCAD, '{:+.2f}')} · "
                f"{_n('m600.d_sigma_db', COM, '{:+.2f}', 'dB')} 이고, 자세별 RMS 는 "
                f"{_n('d_sigma_rms_db', PH4, '{:.1f}')}~"
                f"{_n('m600.d_sigma_rms_db', COM, '{:.1f}', 'dB')} 다.",

                f"⭐ 이 세 자가 σ 의 **인용 단위**를 정한다 — 방위평균과 로브 위치로 인용하고, "
                f"널 깊이는 자세별 RMS 열에 그 크기가 그대로 적혀 있다.",
            ],
            method=[
                ("사진 정합", "카메라 자세·원근·배율·위치와 로터별 프로펠러 위상을 맞춘 뒤 겹친다 "
                            "(`src/viz_mesh_photo.py`)"),
                ("IoU 의 눈금", "같은 메쉬로 만든 가짜 사진을 같은 파이프라인에 넣어 자기복제 "
                              "상한을 잰다 — 그 값이 이 검사가 낼 수 있는 최고점이다"),
                ("CAD 의 바닥", "제조사 CAD 와 자사 발행 제원이 서로 갈리는 폭을 함께 잰다 — "
                              "그 폭 아래로는 이 검사가 아무것도 못 가른다"),
                ("실물 유래 메쉬", "스캔·실물 CAD·커뮤니티 메쉬를 우리 커널에 넣어 Δ 방위평균 σ "
                                "와 자세별 RMS 를 함께 낸다"),
            ],
            repro=_repro([_DERIVE_CMD, "PYTHONPATH=src python src/viz_mesh_photo.py"],
                         [DER, PH4, RCAD, COM],
                         "약 3분 (GPU 0장 — 사진 정합과 표 조립이다)",
                         "자료 규칙에 걸린 사진은 사유와 함께 원장에 남긴다"),
        ),

        md("## 사진과 맞댔다", "",
           f"사진 {_n('photo.n_pairs', DER, '{:.0f}', '장')} 을 각각 정합해 실루엣 "
           f"**IoU**(두 실루엣이 겹친 넓이를 둘을 합친 넓이로 나눈 값 — 1 에 가까울수록 잘 "
           f"맞는다)를 쟀다. 카메라 자세·원근·배율·위치와 로터별 프로펠러 위상을 맞춘 뒤 겹친다"
           f"(`src/viz_mesh_photo.py`). 자료 규칙에 걸린 사진 "
           f"{_n('photo.n_excluded', DER, '{:.0f}', '장')} 은 사유와 함께 원장에 남겼다."),

        md("## 실루엣이 겹치는가", "",
           *_fig(1, "report02_f2_mesh_photo",
                 "우리 메쉬의 외형은 실제 기체 사진과 얼마나 맞는가?")),

        md("## 형상 검사 세 가지 — 한 표로", "",
           table(["검사", "대상", "지표", "값", "그 지표의 바닥"],
                 [["사진 실루엣",
                   f"7기체 · 사진 {_n('photo.n_pairs', DER, '{:.0f}', '장')}",
                   "IoU (상한 대비)",
                   f"{_n('photo.worst_iou', DER, '{:.3f}')}~"
                   f"{_n('photo.best_iou', DER, '{:.3f}')} "
                   f"({_n('photo.worst_pct', DER, '{:.0f}')}~"
                   f"{_n('photo.best_pct', DER, '{:.0f}', '%')})",
                   f"자기복제 상한 {_n('photo.ceiling_min', DER, '{:.3f}')}~"
                   f"{_n('photo.ceiling_max', DER, '{:.3f}')} · 자세 1° 오차에서 "
                   f"{_n('photo.iou_at_1deg_pose_error', DER, '{:.3f}')}"],
                  ["제조사 CAD 치수",
                   f"어셈블리 {_n('cad.n_assemblies', DER, '{:.0f}', '종')} · 치수 "
                   f"{_n('cad.n_dims', DER, '{:.0f}', '개')}",
                   "최대 편차",
                   f"CAD 대비 {_n('cad.worst_vs_cad_pct', DER, '{:.2f}', '%')} · 발행 제원 대비 "
                   f"{_n('cad.worst_vs_published_pct', DER, '{:.2f}', '%')}",
                   f"제조사 CAD ↔ 자사 발행 제원이 "
                   f"{_n('cad.floor_pct', DER, '{:.2f}', '%')} 까지 갈린다"],
                  ["실물 유래 메쉬",
                   f"{_n('name_real', PH4)} 스캔 · {_n('typhoon.name_real', RCAD)} · "
                   f"{_n('m600.name_real', COM)}",
                   "Δ 방위평균 σ",
                   f"{_n('d_sigma_db', PH4, '{:+.2f}')} · "
                   f"{_n('typhoon.d_sigma_db', RCAD, '{:+.2f}')} · "
                   f"{_n('m600.d_sigma_db', COM, '{:+.2f}', 'dB')}",
                   f"자세별 RMS {_n('d_sigma_rms_db', PH4, '{:.1f}')}~"
                   f"{_n('m600.d_sigma_rms_db', COM, '{:.1f}', 'dB')}"]])),

        md("## 이 표가 σ 의 인용 단위를 정한다", "",
           "**방위평균**과 **로브**(방위를 돌릴 때 σ 가 솟는 봉우리) 위치로 인용하고, "
           "**널 깊이**(그 봉우리 사이에서 σ 가 꺼지는 골이 얼마나 깊은지)는 메쉬 세부에 걸리므로 "
           "자세별 RMS 열에 그 크기가 그대로 적혀 있다.", "",
           f"IoU 에는 눈금이 붙어 있다 — 표 오른쪽 끝의 **자기복제 상한**은 같은 메쉬로 만든 가짜 "
           f"사진을 같은 파이프라인에 넣었을 때 나오는 값, 즉 이 검사가 낼 수 있는 최고점이다. "
           f"그 값이 {_n('photo.ceiling_min', DER, '{:.3f}')}~"
           f"{_n('photo.ceiling_max', DER, '{:.3f}')} 다(암·블레이드가 몇 px 이라 최고점이 "
           f"1.0 아래다). 같은 메쉬끼리도 자세가 1° 어긋나면 "
           f"{_n('photo.iou_at_1deg_pose_error', DER, '{:.3f}')}, 2° 면 "
           f"{_n('photo.iou_at_2deg_pose_error', DER, '{:.3f}')} 로 내려간다.", "",
           f"⭐ 그래서 이 편이 파는 것은 «메쉬가 맞다» 가 아니라 **«어느 인용 단위까지 맞다»** 다. "
           f"그 단위 안에서 σ 를 쓰는 자리가 {ref_part(5)} 이고, 단위 밖의 양을 인용하지 않는다.", "",
           f"⚠ 사진 IoU·CAD 표는 {_n('_meta.date', MFX)} 형상 정정 **전** 메쉬의 산출이고, "
           f"σ 대조 세 값은 그 메쉬 위에서 {_n('_meta.generated', AGI)} Γ(θ) 각도 모양(기본 켬) "
           f"**이전** 커널로 돌린 것이다 — 재측정은 다음 단계 표에 있다."),

        next_steps([
            ("실물 스캔 대조를 실측 대상 두 기체로 넓힌다",
             "Δ 방위평균 σ 의 크기가 우리 1차 표적에서도 같은 범위인지가 확정된다",
             ref("sim-vs-meas", short=True)),
            ("자세별 RMS 를 널 깊이 인용 규약의 문턱으로 굳힌다",
             "어느 자세 해상도까지 σ 를 인용해도 되는지가 숫자로 확정된다",
             ref("anchor-ledger", short=True)),
            ("형상 정정 후 메쉬로 사진 IoU 를 다시 잰다",
             "정정이 외형 일치도를 얼마나 옮겼는지가 확정된다",
             "`src/viz_mesh_photo.py`"),
            ("Matrice 4E · Mini 5 Pro 의 짐벌·착륙장치를 사진 실루엣에 맞춘다",
             "실측 두 기체의 IoU 가 상한 대비 어디까지 오르는지 확정된다",
             "`src/drone_cad.py` → 사진 실루엣 재측정"),
        ]),
    ]


# =========================================================================== #
#  편 17 — materials
# =========================================================================== #
def report_17_materials():
    return [
        header(
            num=17,
            title="도전성 재질이 면적의 45.3% 로 Σ|Γ|A 의 73.5% 를 낸다",
            did="부품 그룹마다 재질을 붙여 7기체의 표면적을 재질로 나누고, 같은 면적을 반사계수 "
                "크기로 가중해 무엇이 반사 진폭을 내는지까지 셌다.",
            results=[
                f"재질은 {_n('material.n_materials', DER, '{:.0f}', '가지')} 이고, 7기체 합계 "
                f"표면적은 {_n('material.total_area_m2', DER, '{:.3f}', 'm²')} 다.",

                f"도전성 {_n('material.conducting', DER)} 가 면적의 "
                f"{_n('material.conducting_area_pct', DER, '{:.1f}', '%')} 를 차지하고 반사계수 "
                f"가중 면적 Σ Γ·A 의 "
                f"{_n('material.conducting_gamma_pct', DER, '{:.1f}', '%')} 를 낸다.",

                f"유전체 셸(body·canopy)은 반사계수 크기 "
                f"{_n('material.gamma_shell', DER, '{:.2f}')} 로 왕복 투과 τ = 1−Γ², 즉 "
                f"{_n('material.shell_tau_db', DER, '{:.2f}', 'dB')}(수직입사 기준) 를 곱해 "
                f"통과시키고 그 뒤 금속(배터리·PCB)을 코히런트 합산한다(`src/rcs_sbr.py` `rcs_sbr(penetrate=True)`).",

                f"Sionna RT 와 우리 PO 적분기는 **같은 재질 표**를 읽는다"
                f"(`src/materials.py` `MATERIALS`, `src/drones.py` `DRONE_GROUP_MAT`) — "
                f"전파 계산과 산란 계산이 같은 물성에서 나온다.",
            ],
            method=[
                ("재질 배정", "부품 그룹마다 재질을 붙인다 — 그룹은 메쉬를 지을 때 유지한 그 "
                            "그룹이고, 재질 표는 전파 쪽과 공유한다"),
                ("면적 계수", "7기체의 메쉬 표면적을 재질별로 합산한다"),
                ("반사계수 가중 면적", "같은 면적을 반사계수 크기로 가중한 장부다 — PO 적분에 "
                                    "들어가는 양이고, 위상이 없으므로 σ 자체는 아니다"),
                ("PO 실효 반사계수", "수직입사 실효값이다 — 커널은 여기에 각도 모양 "
                                 "|Γ(θ)|/|Γ(0)| (TE·TM 전력평균, `ANGLE_GAMMA=1` 기본)을 "
                                 "곱한다 ⟨" + AGI + " : _meta.design⟩"),
            ],
            repro=_repro([_DERIVE_CMD, "PYTHONPATH=src python src/viz_mesh_material.py"],
                         [DER], "약 2분 (GPU 0장)",
                         "재질 표의 정의는 `outputs/report02_derived.json:material.definition` "
                         "에 문장으로 적혀 있다"),
        ),

        md("## 부품별 재질 — PO 적분에 들어가는 물리 입력", "",
           "Sionna RT 와 우리 PO 적분기는 **같은 재질 표**를 읽는다(`src/materials.py` `MATERIALS`"
           ", `src/drones.py` `DRONE_GROUP_MAT`). 아래 그림은 7기체의 표면적을 재질로 "
           "나누고, 같은 면적을 |Γ| 로 가중해 **무엇이 반사 진폭을 내는지**까지 함께 싣는다."),

        md("## 무엇으로 이루어져 있고, 무엇이 진폭을 내는가", "",
           *_fig(1, "mesh_compare_material_area",
                 "기체는 무엇으로 이루어져 있고, 그 중 무엇이 반사 진폭을 내는가?"), "",
           f"도전성 {_n('material.conducting', DER)} 가 면적의 "
           f"{_n('material.conducting_area_pct', DER, '{:.1f}', '%')} 를 차지하고 Σ|Γ|A 의 "
           f"{_n('material.conducting_gamma_pct', DER, '{:.1f}', '%')} 를 낸다."),

        md(table_from(f"{DER}:material.rows",
                      [("재질", "material"), ("부품 그룹", "groups"),
                       (r"\|Γ\| 벌크", "gamma_bulk"), (r"\|Γ\| PO 실효", "gamma_po"),
                       ("면적 [m²] (7기체)", "area_m2"), ("면적 비중", "area_pct"),
                       ("Σ\\|Γ\\|A 비중", "gamma_pct")],
                      fmt={"gamma_bulk": "{:.3f}", "gamma_po": "{:.2f}", "area_m2": "{:.3f}",
                           "area_pct": "{:.1f} %", "gamma_pct": "{:.1f} %"}), "",
           f"표의 |Γ| 두 열은 **수직입사** 값이다 — 커널은 여기에 각도 모양 |Γ(θ)|/|Γ(0)| "
           f"(TE·TM 전력평균, `ANGLE_GAMMA=1` 기본)을 곱한다 ⟨{AGI} : _meta.design⟩. 그 축이 "
           f"옮기는 크기는 프롭 채널 레벨 "
           f"{_n('propeller_channel_el_-15_3p5GHz.matrice4e.level_delta_db', AGI, '{:+.2f}')} ~ "
           f"{_n('propeller_channel_el_-15_3p5GHz.mini5pro.level_delta_db', AGI, '{:+.2f}', 'dB')}"
           f" · 전체 드론 σ "
           f"{_n('whole_drone_sigma_az24_el_-15.mini5pro.delta_db', AGI, '{:+.2f}')} ~ "
           f"{_n('whole_drone_sigma_az24_el_-15.matrice4e.delta_db', AGI, '{:+.2f}', 'dB')} 다."),

        md("## 셸을 통과한 뒤 금속을 더한다", "",
           f"유전체 셸(body·canopy)은 |Γ| = "
           f"{_n('material.gamma_shell', DER, '{:.2f}')} 로 왕복 투과 τ = 1−|Γ|², 즉 "
           f"{_n('material.shell_tau_db', DER, '{:.2f}', 'dB')} 를 곱해 통과시키고 그 뒤 "
           f"금속(배터리·PCB)을 코히런트 합산한다 — τ 는 수직입사 기준이고, 각도 모양은 "
           f"|Γ(θ)| 축이 따로 든다(`src/rcs_sbr.py` `rcs_sbr(penetrate=True)`).", "",
           f"⚠ Σ|Γ|A 는 **위상 없는 장부**다 — 어느 재질이 진폭에 얼마나 기여하는지의 크기 "
           f"순서를 보는 데 쓰고, σ 자체는 위상을 가진 면적분에서 나온다. 그 적분이 "
           f"{ref('kernel-what')} 다."),

        next_steps([
            ("이 재질 표를 실은 채로 조명면 면적분을 돌린다",
             "재질 가중이 σ 에 실제로 얼마나 실리는지가 확정된다",
             ref("kernel-what", short=True)),
            ("PO 실효 |Γ| 와 벌크 |Γ| 의 차이가 σ 에 주는 크기를 잰다",
             "실효값 선택이 어느 밴드에서 몇 dB 를 옮기는지가 확정된다",
             ref("sigma-robustness", short=True)),
            ("셸 투과 모형을 실측 기체 한 대에서 확인한다",
             "왕복 투과 가정이 실제 기체에서 성립하는 범위가 확정된다",
             ref("sim-vs-meas", short=True)),
        ]),
    ]


# =========================================================================== #
REPORTS = [
    ("mesh-build", report_15_mesh_build),
    ("mesh-vs-real", report_16_mesh_vs_real),
    ("materials", report_17_materials),
]


def main() -> int:
    print(f"── 부 3 「표적 메쉬」 — 편 {len(REPORTS)}개 ──")
    bad = 0
    for anchor, fn in REPORTS:
        rep = build_notebook(nb_path(anchor), fn(), strict=True, quiet=True)
        index_shard(anchor, md_cells=rep["md_cells"], figures=rep["figures"],
                    provenance_tags=rep["provenance_tags"],
                    negatives=rep["n_negatives"], builder=os.path.basename(__file__))
        mark = "✅" if rep["ok"] else "⛔"
        print(f"  {mark} {rep['path']:44s} md {rep['md_cells']:2d}/25 · "
              f"그림 {rep['figures']}/8 · 출처 {rep['provenance_tags']:3d} · "
              f"부정문 {rep['n_negatives']}/3 · 완충어 {rep['n_hedges']}/0")
        bad += 0 if rep["ok"] else 1
    print(f"── {len(REPORTS) - bad}/{len(REPORTS)} 통과 ──")
    return bad


if __name__ == "__main__":
    sys.exit(main())
