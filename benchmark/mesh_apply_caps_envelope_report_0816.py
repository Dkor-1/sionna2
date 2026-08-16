# -*- coding: utf-8 -*-
"""
mesh_apply_caps_envelope_report_0816.py — 측정 결과를 **정본 JSON** 으로 엮는다
================================================================================
입력 : outputs/mesh_apply_caps_envelope_0816.json (측정기가 쓴 원시값 — 이 파일이 덮어쓴다)
       outputs/_capdiag_0816.json            (캡 삼각화 후보 비교)
       outputs/_capdiag_groups_0816.json     (그룹별 귀속)
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs", "mesh_apply_caps_envelope_0816.json")

RAW = json.load(open(OUT))
DIAG = json.load(open(os.path.join(ROOT, "outputs", "_capdiag_0816.json")))
GRP = json.load(open(os.path.join(ROOT, "outputs", "_capdiag_groups_0816.json")))

#  같은 대조를 서로 다른 소스 기준선 위에서 3번 돌린 결과(다른 라운드가 그 사이 파일을 고쳤다).
#  Δ 가 기준선에 둔감한지 보는 자기검사다.
REPEAT = {
    "왜 3번인가": "병행 라운드가 drone_cad.py 를 계속 고쳐 기준선이 움직였다. 같은 Δ 를 "
                  "서로 다른 기준선 위에서 재서 «Δ 가 기준선에 둔감한가» 를 시험한다.",
    "기준선(drone_cad.py md5 앞 8자리)": ["f3a461f0", "66a2b8b3", "11ff23f1"],
    "Δ 방위평균 [dB] (el 0°)": {
        "matrice4e": [-0.008, -0.010, -0.009], "mavic4pro": [-0.009, -0.009, +0.003],
        "mini5pro": [+0.001, +0.001, +0.001], "phantom4": [-0.002, -0.002, -0.002],
        "phantom3": [-0.005, -0.005, -0.005], "mini2": [-0.001, -0.001, -0.001]},
    "Δ 최악방위 [dB] (el 15°, matrice4e)": [-0.158, -0.097, +0.473],
    "판정": "⭐ **방위평균 Δ 는 기준선에 둔감하다**(최대 산포 0.012 dB). "
            "⛔ **최악방위 Δ 는 아니다**(같은 수리가 −0.16 ~ +0.47 dB 로 흔들린다) — "
            "이 저장소가 이미 «널 깊이는 이산화에 6~17 dB 요동한다» 고 선언한 자리이므로 "
            "이 라운드의 형상 변화로 귀속하면 안 된다. 최악방위 숫자는 참고로만 남긴다.",
}

CAP_ALT = {
    "질문": "«스무딩을 줄이면 가운데도 거칠어지는가» — 거칠어진다면 스무딩 대신 "
            "끝단 캡 삼각화를 손대야 한다(라운드 지시).",
    "답": "⭐ **아니다. 가운데는 스무딩을 꺼도 그대로다.**",
    "근거1_가운데_거칠기(이면각, |x|<0.38·bl)": {
        k: {"iters4_mean_deg": DIAG[k]["variants"]["fan_it4"]["rough_mid"]["mean_deg"],
            "iters0_mean_deg": DIAG[k]["variants"]["fan_it0"]["rough_mid"]["mean_deg"],
            "iters4_p95_deg": DIAG[k]["variants"]["fan_it4"]["rough_mid"]["p95_deg"],
            "iters0_p95_deg": DIAG[k]["variants"]["fan_it0"]["rough_mid"]["p95_deg"]}
        for k in DIAG if k != "_replica_check"},
    "근거2_가운데_정점이동[mm]": {
        "잣대": "iters 0 ↔ 4 의 셸 정점 1:1 대응 거리, |x| ≤ 0.45·bl 구간",
        "값": {"matrice4e": 0.149, "mavic4pro": 0.124, "mini5pro": 0.061,
               "phantom4": 0.137, "phantom3": 0.101, "mini2": 0.118},
        "해석": "셸 길이의 0.06 % 이하. 스무딩이 실제로 하는 일은 **양 끝 5 % 구간**에 있다 — "
                "로프트가 이미 (3차 스플라인 × 초타원 · 30 × 72 격자) 매끈해서 Taubin 저역통과가 "
                "손댈 고주파는 **부채꼴 캡의 중심점 하나**(밸런스 72)뿐이기 때문이다."},
    "근거3_가운데_단면적_변화": "가운데 4 스테이션 전부 ≤ 0.05 % (6종)",
    "그래도_재본_대안": {
        "무엇": "끝단 캡을 «부채꼴 1장(중심점 1개)» → «동심 링 N장» 으로 다시 삼각화하고 "
                "스무딩은 4회 그대로 둔다. 링을 넣으면 테두리의 캡쪽 이웃이 중심이 아니라 "
                "반지름 (1−1/N) 자리에 앉아 안쪽으로 당기는 힘이 1/N 로 준다.",
        "결과(끝단 스테이션 오차, matrice4e 기수)": {
            "부채꼴(현행)": DIAG["matrice4e"]["variants"]["fan_it4"]["+0.50"]["err_w_pct"],
            "동심링 N=3": DIAG["matrice4e"]["variants"]["disk3_it4"]["+0.50"]["err_w_pct"],
            "동심링 N=6": DIAG["matrice4e"]["variants"]["disk6_it4"]["+0.50"]["err_w_pct"],
            "동심링 N=10": DIAG["matrice4e"]["variants"]["disk10_it4"]["+0.50"]["err_w_pct"],
            "동심링 N=16": DIAG["matrice4e"]["variants"]["disk16_it4"]["+0.50"]["err_w_pct"],
            "smooth_iters=0": DIAG["matrice4e"]["variants"]["fan_it0"]["+0.50"]["err_w_pct"]},
        "삼각형 수(셸)": {"부채꼴/iters0": DIAG["matrice4e"]["variants"]["fan_it4"]["n_tri"],
                          "동심링 N=16": DIAG["matrice4e"]["variants"]["disk16_it4"]["n_tri"]},
        "채택 안 한 이유": "N=16 까지 늘려도 끝단 오차가 −4.3 % 에서 멈추는데 셸 삼각형은 "
                           "4320 → 8640 으로 두 배가 된다. `smooth_iters=0` 은 같은 자리를 "
                           "**오차 0.00~0.06 %** 로 만들면서 삼각형을 하나도 안 늘린다. "
                           "즉 «가운데가 거칠어진다» 는 전제가 거짓이므로 캡 삼각화를 "
                           "손댈 이유 자체가 없다. ⛔ `cadkit.loft` 는 **한 글자도 안 바꿨다** "
                           "(캐노피 등 다른 호출부가 공유하는 함수이고, 캐노피는 남의 라운드 자리다)."},
    "⚠ 스무딩을 줄일 때 흔한 착각": "iters 를 1 이나 3(홀수)으로 두면 안 된다. trimesh 의 "
                                   "`filter_taubin(iterations=n)` 은 n 을 **반쪽 패스**로 센다 — "
                                   "짝수 인덱스는 수축(λ), 홀수는 팽창(ν). 홀수에서 멈추면 캡 "
                                   "테두리가 수축 상태로 남아 스테이션 단면이 −92 ~ −99 % 로 "
                                   "무너진다(실측: fan_it1 −99.9 % · fan_it3 −92.8 %). "
                                   "쓸 값은 0 또는 짝수뿐이다.",
}

d3, d6 = RAW["step3_loft_end_caps"], RAW["step6_phantom4_envelope"]

for k, v in d3["per_drone"].items():
    v["group_attribution"] = GRP[k]
GRP["_읽는 법"] = (
    "«움직인 그룹» 은 **지문이 바뀐** 그룹이지 «눈에 띄게 움직인» 그룹이 아니다. 실제 이동량:\n"
    "  · matrice4e `camera` — 최대 **0.0115 mm**(11.5 µm). 짐벌 x 가 셸 기수에 매달려 있어서 "
    "셸이 표값으로 돌아온 만큼 따라온다. 그림·σ 어디에도 안 보인다.\n"
    "  · phantom3 은 전 그룹이 움직인다 — 셸 bbox 가 바뀌자 높이 강제 배율 sz 가 "
    "0.99810851 → 0.99807348 (−0.0035 %) 로 재계산되기 때문이다. 190 mm 부품에서 "
    "**0.007 mm** 다(실측 camera 최대 0.0044 mm).\n"
    "  · 나머지 4종은 `body` 하나만 움직인다 = 끝단 캡 수리가 셸 밖으로 새지 않았다.")
d3["group_attribution_all"] = GRP

HEAD = [
    "① ③ **로프트 끝단 캡** — 셸형 6종 전부 `smooth_iters=0`. 끝단 스테이션이 표와 정확히 "
    "일치하게 된다(−38 ~ −44 % → **0.00 ~ 0.06 %**). 표면이 실제로 움직인 거리는 최대 "
    "1.0 ~ 2.7 mm(캡 테두리)이고 셸 길이가 표값으로 돌아온다(matrice4e 236.91 → 234.60 mm).",
    "② ⭐ **«가운데가 거칠어진다» 는 거짓이다 — 측정했다.** 가운데(|x| ≤ 0.45·bl)에서 iters "
    "0 ↔ 4 차이는 정점 이동 ≤ 0.15 mm · 이면각 평균 2.978° → 2.975° · 단면적 ≤ 0.05 %. "
    "그래서 라운드가 대안으로 지시한 «캡 삼각화 변경» 은 **필요 없다**(재 보긴 했다 — 동심 링 "
    "N=16 도 −4.3 % 에서 멈추고 삼각형만 2배가 된다).",
    "③ **③ 의 σ 대가는 사실상 0 이다** — 방위평균 |Δσ| ≤ **0.009 dB**(6종 · el 0°/15° 전부), "
    "기수/옆/꼬리 컷 |Δ| ≤ 0.21 dB. 즉 이것은 **레벨 수리가 아니라 형상 수리**다(감사가 "
    "예고한 대로). 값을 넣을 이유는 σ 가 아니라 «공식 CAD 가 잰 뭉툭한 기수를 메쉬가 절반만 "
    "싣고 있었다» 는 사실이다.",
    "④ ⑥ **phantom4 L/W 강제 해제** — 축간거리 356.92 → **350.000 mm**(공표와 오차 0.000 %, "
    "전에는 +1.977 %). 대가는 선언한다: 프레임 L/W 가 이제 **지어진 값**이라 283.89 mm 로 "
    "공표 289.5 보다 −1.94 % 다. 프롭 여유는 여전히 양수(이웃 로터 247.49 mm ↔ 프롭 240 mm = "
    "+7.49 mm).",
    "⑤ **⑥ 의 σ 는 진짜로 움직인다** — 방위평균 −0.286 dB(el 0°) / −0.177 dB(el 15°). "
    "감사가 평판극한 상한으로 예고한 −0.39 / −0.14 dB 와 부호·자릿수가 맞는다(우리 커널이 "
    "상한보다 작게 나오는 것이 정상이다).",
    "⑥ **검사기 10/10 통과**, 안 건드린 4종(s1000plus·typhoonh480·x500v2·m350rtk)은 "
    "**비트동일**로 증명. 건드린 6종은 지문이 바뀌었고 그것이 의도다.",
]

RAW["_meta"].update({
    "round": "값 적용 — **셸 계열 2건**(③ 로프트 끝단 캡 · ⑥ phantom4 L/W 강제 해제)",
    "date": "2026-08-16",
    "source_of_truth": "outputs/mesh_inspect_body_arms_0816.json (발견 B3 · B6)",
    "discipline": {
        "gpu": "⛔ 미사용 (CUDA_VISIBLE_DEVICES='')",
        "git": "⛔ 미사용",
        "남의 자리": "⛔ INTERNALS · 캐노피 묻힘 · geom.py uv_sphere · x500v2 · mini2 body 구멍 · "
                     "rcs_po.py 매몰면 경로 · 프로펠러 날 법칙 — **읽기만** 했다. "
                     "`cadkit.loft` 도 안 건드렸다(캐노피가 공유하는 함수).",
        "잣대": {
            "σ 엔진": "src/rcs_po.py **순수 PO**(가림 없음 · 재질 가중 |Γ|) · CPU",
            "설정": "fc 3.5 GHz · 점 간격 λ/7 · 대역평균 5주파(±50 MHz) · 방위 1.0° · el 0°/15°",
            "방위평균": "10·log10(mean_az σ)",
            "최악방위": "3° 각도평활 뒤 최저 σ. ⚠ 이 통계는 **이 라운드가 신뢰하지 않는다** — "
                        "self_check_repeatability 참조",
            "⚠ 선언": "점구름은 중심주파수의 λ/7 로 한 번 깔고 5주파에 재사용한다(대역 안에서 "
                      "간격 변화 1.4 %). 이 잣대는 «절대 σ» 가 아니라 «전후 차» 를 재는 것이다. "
                      "가림이 있는 SBR 로 다시 재면 절대값은 다르다(리포트 원장은 별건)."},
        "귀속": "「전」과 「후」를 **한 프로세스 안에서** 잰다. 전 상태는 파일이 아니라 코드로 "
                "고정한다(smooth_iters=4 · envelope=(289.5,289.5,196.0)) — 병행 라운드가 같은 "
                "파일을 동시에 고치고 있어서 파일을 다시 읽는 방식으로는 귀속이 깨진다.",
    },
    "source_edits": [
        "src/drone_cad.py — `_SHELL_SHAPE[*]['smooth_iters'] = 0` 6곳 + `_body_folding` "
        "docstring 에 결정·측정 기록",
        "src/drones.py — phantom4 `envelope_mm=(289.5,289.5,196.0)` → `(None,None,196.0)` "
        "+ note 에 근거·대가",
    ],
    "new_files": [
        "benchmark/mesh_apply_caps_envelope_0816.py (측정기 — 전/후 대조 + 파일 재확인)",
        "benchmark/capdiag_0816.py (캡 후보 진단 — 거칠기·동심링 캡)",
        "benchmark/capdiag_groups_0816.py (그룹별 귀속)",
        "benchmark/mesh_apply_caps_envelope_report_0816.py (이 정본 JSON 을 엮는 스크립트)",
        "src/mesh_check.py — ⚠ **주석 한 줄만** 고쳤다(대각 허용오차 표의 «최대 phantom4 "
        "+1.98 %» 가 이 라운드로 낡았다). 문턱값은 안 건드렸다.",
    ],
})
#  라운드가 요구한 4칸 기록 — 수리마다 ①상수 전후 ②형상 변화[mm] ③σ 변화[dB] ④게이트
RAW["record_4cols"] = {
    "③ 로프트 끝단 캡 (B3)": {
        k: {
            "①상수": f"_SHELL_SHAPE['{k}']['smooth_iters']  4(옛 리터럴) → 0",
            "②형상[mm]": (
                f"끝단 캡 테두리가 최대 {v['shell_move_mm']['max_all']} mm 이동 "
                f"(가운데 |x|≤0.45·bl 은 {v['shell_move_mm']['max_middle_le045bl']} mm 이하) · "
                f"셸 길이 {v['geom_before']['shell_len_mm']} → {v['geom_after']['shell_len_mm']} mm · "
                f"기수 단면 {v['geom_before']['+0.50']['half_w_mm']}×{v['geom_before']['+0.50']['half_h_mm']}"
                f" → {v['geom_after']['+0.50']['half_w_mm']}×{v['geom_after']['+0.50']['half_h_mm']} "
                f"(표 {v['geom_after']['+0.50']['target_w_mm']}×{v['geom_after']['+0.50']['target_h_mm']})"),
            "③σ[dB]": (
                f"방위평균 el0 {v['sigma_delta_db']['el0']['d_az_mean_db']:+.3f} · "
                f"el15 {v['sigma_delta_db']['el15']['d_az_mean_db']:+.3f}  |  "
                f"최악방위 el0 {v['sigma_delta_db']['el0']['d_worst_db']:+.3f} · "
                f"el15 {v['sigma_delta_db']['el15']['d_worst_db']:+.3f} "
                f"(⚠최악방위는 신뢰 불가 — self_check_repeatability)"),
            "④게이트": "mesh_check 10/10 통과",
            "움직인 그룹": v["group_attribution"]["moved_groups"],
        } for k, v in d3["per_drone"].items()},
    "⑥ phantom4 L/W 강제 해제 (B6)": {
        "①상수": "DRONES['phantom4'].envelope_mm  (289.5, 289.5, 196.0) → (None, None, 196.0)",
        "②형상[mm]": (
            f"축간거리 {d6['wheelbase_mm']['before']} → {d6['wheelbase_mm']['after']} "
            f"(공표 350, 오차 {d6['wheelbase_mm']['err_pct_before']:+.3f} % → "
            f"{d6['wheelbase_mm']['err_pct_after']:+.3f} %) · "
            f"로터 중심 ±126.19 → ±123.744 (각 축) · "
            f"프레임 L/W {d6['frame_before']['frame_bbox_mm'][0]} → "
            f"{d6['frame_after']['frame_bbox_mm'][0]} (높이 196 은 그대로 강제)"),
        "③σ[dB]": (
            f"방위평균 el0 {d6['sigma_delta_db']['el0']['d_az_mean_db']:+.3f} · "
            f"el15 {d6['sigma_delta_db']['el15']['d_az_mean_db']:+.3f}  |  "
            f"컷 el0 az0 {d6['sigma_delta_db']['el0']['d_cuts_db']['az0']:+.3f} · "
            f"az90 {d6['sigma_delta_db']['el0']['d_cuts_db']['az90']:+.3f} · "
            f"az180 {d6['sigma_delta_db']['el0']['d_cuts_db']['az180']:+.3f}"),
        "④게이트": "mesh_check 10/10 통과 · phantom4 대각 오차 +1.98 % → +0.00 %",
        "감사 예고와의 대조": "감사 B6 는 평판극한 상한으로 −0.39 dB(el0) / −0.14 dB(el15) 를 "
                              "예고했다. 우리 커널 PO 는 −0.286 / −0.177 dB — el0 는 상한 안, "
                              "el15 는 상한보다 살짝 크다(평판극한은 투영면적만 보고 위상을 "
                              "안 보므로 방향을 단정하는 어림이 아니다).",
    },
}
RAW["headline"] = HEAD
RAW["step3_loft_end_caps"]["decision"] = CAP_ALT
RAW["self_check_repeatability"] = REPEAT
RAW["gate"] = {
    "cmd": "PYTHONPATH=src:benchmark python src/mesh_check.py",
    "result": "**10/10 통과**",
    "phantom4 치수줄": "프롭지름 240.00 mm (−0.000 %) · 대각 **350.0 mm (+0.00 %)** · "
                       "외형 [None, None, 0.0] ✅  (전에는 대각 +1.98 %)",
    "⚠": "이 게이트는 이 라운드가 돈 **직후** 결과다. 병행 라운드가 같은 파일을 고치고 있으므로 "
         "합류 후 한 번 더 돌려야 한다.",
}
RAW["not_settled_declared"] = [
    "⚠ **기준선이 움직인다** — 이 라운드가 도는 동안 병행 «2층 수리» 라운드가 drone_cad.py 를 "
    "3번 고쳤다(matrice4e·mavic4pro 지문 드리프트). 이 파일의 **Δ** 는 안전하지만(한 프로세스 "
    "안 대조 + 3회 반복으로 둔감함 확인), **절대 σ 값**은 측정 시각의 기준선 것이다. "
    "step9_verify_from_file 의 match=false 는 그 드리프트이지 이 라운드의 값이 안 들어간 것이 "
    "아니다(constants_in_file 이 값을 직접 보여준다).",
    "⚠ **끝단 캡은 이제 완전한 평면**이다. matrice4e 는 공식 CAD 가 «전방 정면이 거의 평면» "
    "이라고 직접 말하므로(F04/F05) 근거가 있다. 나머지 5종은 표의 끝단 스테이션이 «셸이 거기서 "
    "끝난다» 는 뜻일 뿐, «끝면이 평면이다» 라고 말한 사진·CAD 는 없다 — 로프트를 닫는 방법이 "
    "평면 아니면 둥근 캡뿐이고, 둥근 캡은 표를 −38~−44 % 깎으므로 **표를 지키는 쪽**을 골랐다. "
    "이건 판단이고, 그 사실을 여기 적어 둔다.",
    "⚠ **B8(스테이션 사이 스플라인 오버슛)은 이 수리로 안 고쳐진다** — 셸 배가 3.93 mm 아래로 "
    "부푸는 것은 CubicSpline 이지 스무딩이 아니다. 실제로 iters 0 ↔ 4 에서 가운데 단면은 "
    "0.05 % 밖에 안 움직인다. 그건 별건(스테이션 6 → 8~10 또는 PCHIP)이다.",
    "⚠ **phantom4 프레임 L/W −1.94 %** 는 남는 잔차다. 공표 289.5 는 셸·다리가 정하는데 우리 "
    "셸 표(fl 0.605 · fw 0.545)는 사진 실측이고 다리 아치는 B5 로 «떠 있다» 고 적혀 있다. "
    "L/W 를 맞추려면 그 둘을 고쳐야지 배율로 늘리면 안 된다 — 그것이 이번 해제의 요지다.",
    "⚠ **최악방위 Δ 는 이 라운드의 결론에 못 쓴다**(self_check_repeatability 판정). "
    "표에는 남기되 인용하지 말 것.",
]
RAW["not_applied_and_why"] = {
    "캡 삼각화 변경(동심 링)": "전제(«가운데가 거칠어진다»)가 측정으로 거짓이라 불필요. "
                               "게다가 끝단 오차를 0 으로 못 만든다(N=16 에서 −4.3 %).",
    "_SHELL_DEFAULT 의 smooth_iters": "안 넣었다. 지금 셸 로프트를 타는 기종은 6종뿐이고 "
                                      "전부 _SHELL_SHAPE 에 자기 항목이 있다(계측으로 확인). "
                                      "기본값 4 는 «표가 없는 새 기종» 용으로 남겨 둔다 — "
                                      "근거 없이 미래 기종의 값을 정하지 않는다.",
    "다른 5건(①②④⑤⑦)": "이 라운드 범위 밖(다른 값 적용자 담당).",
}
json.dump(RAW, open(OUT, "w"), ensure_ascii=False, indent=1)
print("wrote", OUT)
