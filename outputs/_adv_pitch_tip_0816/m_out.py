# -*- coding: utf-8 -*-
"""판정 원장 조립 — outputs/mesh_adv_refute_pitch_tip_0816.json"""
import datetime
import json
import os
import re

SP = "/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad"
OUT = "/workspace/sionna/outputs/mesh_adv_refute_pitch_tip_0816.json"
J = lambda n: json.load(open(os.path.join(SP, n)))


def logrows(fn, pat):
    rows = []
    for ln in open(os.path.join(SP, fn)):
        m = re.match(pat, ln.strip())
        if m:
            rows.append(ln.strip())
    return rows


wrap = J("wrap.json")
tipspec = J("tip_spectrum_matrice4e_el-30.json")
tipbi = J("tip_bistatic.json")
flash2 = J("flash2.json")
ours = J("ours_tip.json")
solo = J("solo.json")

kst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))

d = {}
d["_meta"] = dict(
    title="적대적 반증 — 감사 0816 의 «피치»·«팁» 주장 (커널로 직접 측정)",
    generated_kst=kst.strftime("%Y-%m-%d %H:%M"),
    role="나는 반증 전담이다. 목적은 확인이 아니라 무너뜨리기다. 못 무너뜨린 것도 적는다.",
    target="docs/MESH_AUDIT_0816.md 의 I7(피치 기준 반경·플래시 −2.2 dB) · I8(팁 −3.10 dB·끝값 0.20)",
    policy="⛔GPU 미사용(전부 numpy/trimesh CPU) ⛔저장소 코드 무변경 ⛔git 미접촉. "
           "대안 형상은 **이 프로세스 안에서만** BLADE_LAWS/PITCH_LAWS dict 에 임시 키로 넣었다.",
    python="/workspace/.venvs/py312/bin/python (PYTHONPATH=src:benchmark)",
    reproduce=dict(
        dir="outputs/_adv_pitch_tip_0816/",
        scripts={
            "m_dji_blade2.py": "DJI 공식 GLB 의 날 8장을 **1장씩 따로** — 원통 단면으로 k(r)·c(r). 축은 허브 PCA ↔ 월드 +y 두 벌.",
            "m_tip_fine.py": "팁 끝 1 % 를 밴드 폭 ±0.06~0.50 mm 로 바꿔가며 — 끝값이 «자» 에 얼마나 끌려다니는지.",
            "m_flash.py": "σ(φ) 를 0.1° 로 훑어 플래시 봉우리·폭·평균 (통제 가족 g=0~1.4 + 피치×1.25).",
            "m_flash2.py": "같은 것을 3.5/10/30 GHz × el −30/−60/0 × matrice4e/mini2 로 — 회절한계 대 비틀림.",
            "m_tip_spectrum.py": "시위 법칙별 마이크로도플러 스펙트럼 밴드 전력 + md_metrics (모노).",
            "m_tip_bi.py": "같은 것을 바이스태틱 β=81°·120° 로.",
            "m_pitch_spec.py": "피치 법칙별 md_metrics(flash_contrast_db·fd_edge_hz).",
            "m_ours_tip.py": "우리 날을 **DJI 와 같은 자**로 재기(원통 단면 ±0.25 mm).",
            "m_photo_tip.py": "제품사진 실루엣에서 투영 평면형 — CAD 와 독립인 팁 증거.",
            "m_wrap.py": "기준 반경 분해능·팁 밴드 면적·3DR Solo 재측정.",
        },
        kernel="src/rcs_po.py (mesh_to_points + PO 면적분). 재질은 PEC — 프롭은 재질 그룹이 "
               "하나뿐이라 |Γ| 는 상수 배수이고 이 실험은 전부 dB **차이**라 정확히 상쇄된다. "
               "(그리고 materials 는 Sionna RT 씬을 열어 OptiX 를 요구한다 — 이번 라운드 GPU 금지.)",
    ),
    scope_declared=[
        "전부 **순수 PO**(가림 없음)·**단일 프로펠러**·평면파다. SBR 도 기체 전체도 안 돌렸다.",
        "스펙트럼은 호버 rpm·PRF 20 kHz·위상표 2880점. 그 표본 간격 민감도는 안 쟀다.",
        "사진 실루엣은 **투영** 평면형이라 참시위를 크게 읽는다 — 팁의 «모양» 판정에만 썼다.",
        "I8 의 «두께까지 넣으면 net −5.08 dB» 중 두께 절반은 안 건드렸다.",
    ],
)

# ─────────────────────────────────────────────────────────── ⓐ
A = wrap["A_reference_station"]
d["A_pitch_reference_radius"] = dict(
    audit_claim="«PITCH_K 의 기준 반경이 0.5R 인데 실물 DJI 는 표준 규약대로 0.75R» "
                "(근거: DJI k 가 0.75R 에서 1.015 로 최대)",
    verdict="부분 정정 — 규약은 참, 그러나 이 데이터로 0.75R 을 **가려낼 수 없다**",
    literature=dict(
        finding="항공기 프로펠러에서 **블레이드 각(=기하 피치)의 기준 정거장은 0.75R** 이 표준이다. "
                "GP = 2π(0.75R)·tan β(0.75R). 여러 출처가 일치한다.",
        caveat="선박 프로펠러는 관례가 **0.7R** 이고, 모형·소형 UAV 프롭 제조사(APC 포함)는 "
               "기준 정거장을 **공개하지 않는다** — APC 기술 페이지 전문에 정거장 문구가 없다. "
               "DJI 도 프로펠러 기하를 일절 공개하지 않는다(레지스트리 mini2 note 가 이미 그렇게 적는다).",
        sources=["https://www.aircraftsystemstech.com/p/propeller-aerodynamic-process-airplane.html",
                 "https://www.sciencedirect.com/topics/engineering/bladed-propeller",
                 "https://www.stefanv.com/rcstuff/qf200203.html",
                 "https://www.apcprop.com/technical-information/engineering/ (정거장 문구 없음)"],
    ),
    my_measurement=dict(
        method="GLB 의 날 8장을 각각 0.4 mm 로 세분 → 허브 정점 PCA 최소분산축을 회전축으로 → "
               "반경 밴드 ±0.35 mm 를 (r·φ, z) 로 펼쳐 최대 캘리퍼 방향 = β(r) → k = 2πr·tanβ / 66.04 mm",
        mean_k=A["mean_k"], sd_k=A["sd_k"],
        reproduces_audit=f"내 k(0.75R) = {A['mine_k_at_0p75']:.3f} ↔ 감사 1.015 (2.5 % 안) — "
                         "감사의 k 표는 **독립 재현된다**",
        per_blade_argmax_r_over_R=A["per_blade_argmax_r_over_R"],
        why_unresolvable=[
            "평균 k 가 최대의 2 % 안에 드는 구간이 r/R 0.70~0.85 다 — 봉우리 위치를 못 가린다.",
            "날마다 argmax 가 갈린다: 4장 @0.75R · 1장 @0.80R · 3장 @0.85R (앞뒤 로터로 갈림).",
            "날 사이 표준편차가 0.75R 에서 4.3 % 인데, 주장의 근거인 «1.015 대 1.014(0.85R)» 차이는 0.1 % 다.",
            "공칭 피치 66.04 mm 를 ±3 % 흔들면 k=1 교차가 0.65~0.85R 로 옮겨간다(아래 표).",
        ],
        k_eq_1_crossing_vs_Pnom={k: v for k, v in A.items() if k.startswith("k_eq_1_crossings")},
        partial_circularity="레지스트리 mini2 note 가 밝히듯 `prop_pitch_in 2.6` 자체가 **이 GLB 를 "
                            "우리 legacy PITCH_K 로 역산해** 얻은 값(중앙값 2.56 → 2.6 채택)이다. "
                            "FCC 제출 사진에 «4726 F» 가 인쇄돼 있어 완전한 순환은 아니지만, "
                            "k 를 정규화하는 상수가 우리 법칙에 한 번 닿았고 ±2 % 면 정거장이 흔들린다.",
        two_different_statements="⚠ 규약은 «공칭 피치를 **어디서 재서 표기하는가**» 이지 "
                                 "«국소 피치가 **어디서 최대인가**» 가 아니다. 감사는 둘을 붙였다. "
                                 "0.75R 규약을 지키는 프롭도 최대는 다른 데 있을 수 있다.",
    ),
    audit_axis_error=dict(
        audit_says="회전축은 월드 +y (허브 관성주축 실측, 편차 0.001)",
        measured="허브 4개의 정점 PCA 최소분산축은 +y 에서 3.16 · 3.46 · 4.64 · 4.73° 기울어져 있다 "
                 "(좌우 대칭이라 잡음이 아니라 모델링된 캔트다)",
        consequence="월드 +y 로 재면 날 사이 k 산포가 sd 4 % → **20~25 %** 로 부푼다. "
                    "그것이 바로 `src/drones.py` mini2 note 가 «뒷 로터 쌍이 코닝 기울기로 "
                    "2.00 / 3.00 in 로 갈린다» 고 적은 그 산포다 — **축 가정의 인공물**이다. "
                    "8장 평균 k 는 축에 둔감하다(내 허브축 평균이 감사보다 2.5 % 낮을 뿐).",
        so_what="감사 원장의 축 문면과 레지스트리의 «피치 밴드 2.0~3.0» 은 둘 다 정정 대상이다.",
    ),
    solo_recheck=dict(
        why="«우리 기준이 0.5R» 이 코드 버그인지 참조물의 성질인지 가른다",
        measured_from="assets/meshes/reference/solo_prop_cw.stl (직경 255.3 mm ↔ 10 in 제원)",
        stations=solo["stations"],
        finding="내 재측정이 저장소 PITCH_K 를 2~4 % 안에서 재현한다(k(0.75R) 1.059 ↔ 코드 1.061). "
                "⇒ «기준 반경 0.5R» 은 유도 버그가 아니라 **Solo 참조 CAD 자신의 성질**이다. "
                "그리고 그 CAD 는 계측 스캔이 아니라 시뮬레이터 자산이다. 감사의 진단은 살아남는다.",
    ),
    size_of_this_defect_alone=dict(
        legacy_k_at_0p75R=A["legacy_k_at_0p75R"],
        meaning="0.75R 규약을 적용하면 우리 날의 그 정거장 국소피치가 +6.1 % 높다(θ 로 약 +0.8°).",
        kernel_price="균일 피치 배율의 커널 민감도는 ×1.25 에서 +0.48 dB(모노 el −30) 였으므로 "
                     "×1.061 은 **≈ +0.12 dB** 다. 기준 반경 그 자체는 dB 축의 손잡이가 아니다.",
    ),
)

# ─────────────────────────────────────────────────────────── ⓑ
d["B_flash_peak_minus_2p2dB"] = dict(
    audit_claim="«외곽 피치각 폭 9.2° ↔ 5.5° 이므로 플래시가 번져 봉우리가 −2.2 dB» (감사 스스로 «어림»). "
                "같은 감사의 커널 민감도는 «피치 ×1.25 → +0.15~+0.82 dB» 라 두 수가 5 배 어긋난다.",
    verdict="감사 반증(크기) · 감사 지지(메커니즘) — 두 수 다 답이 아니었고, "
            "**교체안의 실제 값은 0.0 dB** 다. 다만 비틀림 축 양끝에서는 감사가 말한 방향이 보인다.",
    first_the_two_numbers_were_never_comparable=(
        "−2.2 dB 는 «비틀림 **기울기**» 에 대한 어림이고, +0.15~+0.82 dB 는 «피치 **크기** 균일 배율» "
        "에 대한 커널 측정이다. 서로 다른 섭동이다. 5 배 차이는 모순이 아니라 **다른 질문 두 개**였다."),
    controlled_family=dict(
        design="0.75R 의 피치각을 **고정**하고 기울기만 g 배 — 순수하게 «폭» 만 바꾼다. "
               "k(r) = 2πr·tan θ_g(r)/P 로 임시 피치 법칙을 지어 넣었다.",
        realized_twist_check="빌드된 메쉬를 되재니 0.6→0.9R 폭이 legacy 9.32° · dji_mini2 5.49° — "
                             "감사의 9.2°/5.5° 를 재현한다(즉 형상은 의도대로 바뀌었다).",
    ),
    measured_3p5GHz_matrice4e_el_minus30=dict(
        note="σ(φ) 를 0.1° 로 훑은 봉우리[dBsm] · −3 dB 폭[°] · 회전평균[dBsm]",
        rows={
            "legacy (출하)": dict(peak=-21.08, w3=12.80, mean=-31.34),
            "dji_mini2 피치 (교체안)": dict(peak=-21.09, w3=12.80, mean=-31.35),
            "g=0 (비틀림 없음)": dict(peak=-21.58, w3=12.10, mean=-32.07),
            "g=0.6": dict(peak=-21.30, w3=12.50, mean=-31.65),
            "g=1.4 (1.4배 비틀림)": dict(peak=-20.85, w3=13.00, mean=-31.02),
            "피치 ×1.25 (감사의 통제)": dict(peak=-20.60, w3=14.20, mean=-30.63),
        },
        headline="교체안의 봉우리 변화 = **−0.01 dB**. 비틀림 축 전체(g 0→1.4)를 다 써도 **0.73 dB**.",
    ),
    across_geometry=dict(
        note="matrice4e·mini2 × el −30/−60/0 × 3.5/10/30 GHz — 봉우리 Δ[dB] (legacy 기준)",
        at_3p5GHz="교체안 |Δ| ≤ 0.08 dB (6개 조합 전부). 비틀림 가족 전체는 −1.28 ~ +1.22 dB.",
        rows=flash2,
    ),
    why_the_mechanism_fails_here=dict(
        finding="플래시 폭이 **비틀림이 아니라 회절**로 정해진다.",
        evidence=[
            "3.5 GHz matrice4e: −3 dB 폭 9.8~18.7° ↔ 회절한계 λ/2R = 17.9°. 날 반지름이 1.60 λ 뿐이다.",
            "3.5 GHz mini2: 폭 22.6~43.0° ↔ λ/2R = 41.2°. 반지름 0.70 λ — 정반사 «띠» 라는 것이 아예 없다.",
            "30 GHz matrice4e(13.7 λ): 폭 4.60° ↔ λ/2R 2.09° — 여기서는 비틀림이 폭을 정한다.",
        ],
        steelman="⭐감사의 그림은 **틀린 물리가 아니라 틀린 영역**이다. 날이 전기적으로 길어지면 "
                 "실제로 그렇게 된다 — 30 GHz·el −60 에서 비틀림 2배가 봉우리를 **+9.98 dB** 움직인다. "
                 "우리 대역(3.5 GHz)에서만 회절 아래에 묻힌다.",
        sign_is_not_even_monotone="3.5 GHz el −30 에서는 비틀림이 클수록 봉우리가 **올라간다**(g0 −0.49, "
                                  "g1.4 +0.61). el −60 에서는 반대다. 즉 여기서 일어나는 일은 "
                                  "«번짐» 이 아니라 **간섭**이고, 감사의 단조 그림은 부호조차 안 맞는다.",
    ),
    repo_own_flash_metric=dict(
        metric="microdoppler_nearfield.md_metrics().flash_contrast_db (AC 포락선 최대/중앙값)",
        rows=[dict(drone=m[1], el=float(m[2]), law=m[3], peak_dbsm=float(m[4]),
                   flash_contrast_db=float(m[5]), d_contrast_db=float(m[6]),
                   fd_edge_hz=float(m[7]), f_tip_hz=float(m[8]))
              for m in (re.match(
                  r"(\S+)\s+el\s+([-+]?\d+)\s+(\S+)\s+peak\s+([-\d.]+)\s+contrast\s+([-\d.]+)\s+"
                  r"\(Δ([-+][\d.]+)\)\s+harm\s+[\d.]+\s+fd_edge\s+([\d.]+)/([\d.]+)", ln.strip())
                  for ln in open(os.path.join(SP, "pitchspec.log"))) if m],
        finding="**교체안**(legacy → dji_mini2)의 플래시 선명도 변화는 시험한 네 조합 전부에서 "
                "|Δ| ≤ 0.25 dB 다 (matrice4e el −30 −0.00 · el −60 +0.25 · mini2 el −30 −0.00 · el −60). "
                "fd_edge_hz 도 안 움직인다.",
        honest_caveat="⚠ 그러나 **비틀림 축 자체가 죽어 있는 것은 아니다.** 인위적 양끝에서는 "
                      "감사가 말한 방향 그대로 움직인다 — mini2 el −30 에서 비틀림을 0 으로 만들면 "
                      "flash_contrast 가 **+2.30 dB**(더 날카로워짐), 2배로 만들면 **−1.31 dB**(더 뭉개짐). "
                      "즉 «폭이 넓으면 플래시가 뭉개진다» 는 그림은 이 잣대에서 살아 있다. "
                      "무너진 것은 **크기**다: legacy↔DJI 의 실제 차이(9.3°→5.5°)는 그 감도 구간에 "
                      "닿지 않아 0.00 dB 를 낸다. 감사는 옳은 메커니즘에 틀린 숫자를 붙였다.",
    ),
    bistatic="β=81° 에서도 교체안은 봉우리 −20.07 → −20.07 dBsm, 평균 −29.73 → −29.73 dBsm (변화 0.00 dB).",
    conclusion="3.5 GHz 에서 피치 법칙은 **≤0.1 dB 짜리 손잡이**다. −2.2 dB 는 20 배 이상 과장이고, "
               "+0.15~+0.82 dB 는 다른 질문의 답이었다. ⇒ 감사 §⑤ 17 의 «바꾸기 전에 커널로 플래시 "
               "폭을 재라» 는 지시는 이로써 **이행됐다**. 결과는 «바꿔도 안전하지만, dB 를 근거로 "
               "팔면 안 된다» 이다.",
)

# ─────────────────────────────────────────────────────────── ⓒ
rows = {r["law"]: r for r in tipspec["rows"]}
d["C_tip_band_into_f_tip"] = dict(
    audit_claim="«팁 밴드(0.90~0.96R) 면적비 0.700 = −3.10 dB, 두께까지 넣으면 net −5.08 dB. "
                "회전 날의 스펙트럼 포락선은 시위분포를 주파수축에 옮긴 것이라 f_tip 근방 세기를 "
                "이 밴드가 정한다» (감사 자신이 «커널로 안 쟀다» 고 선언)",
    verdict="감사 반증 — 그만큼 안 들어간다. 게다가 −3.10 dB 는 **감사 자신이 C5 에서 폐기한 번역**이다",
    the_metric_does_not_exist=dict(
        grep="«f_tip 밴드 세기» 는 저장소의 **잣대가 아니다** — 전수 grep 결과 이 표현이 나오는 곳은 "
             "MESH_AUDIT_0816.md · 그 산출 원장 · 그리고 거기서 옮겨 적힌 `src/drone_cad.py` 168~172 행 "
             "주석뿐이다. 즉 감사가 만든 말이고, 이미 코드 주석으로 번져 «끝값 0.200» 의 근거 문장이 돼 있다.",
        what_actually_exists={
            "f_tip": "2·v_tip·cos(el)/λ — **순수 운동학**. 시위와 무관하므로 정의상 0 dB.",
            "fd_edge_hz": "md_metrics 의 관측 도플러 가장자리. 내 실험 전 조건에서 **1054.7 Hz 로 동일**. "
                          "모듈 docstring 자신이 «형상이 미는 가장자리는 flash_hz 통짜 계단으로만 움직인다» "
                          "고 이미 경고한다.",
            "OOB": "f_tip 밖 전력 몫 — report07b·report08 이 쓰는 잣대.",
        },
    ),
    internal_contradiction=dict(
        arithmetic="20·log10(0.7002) = −3.098 ⇒ I8 의 −3.10 dB 는 **면적비를 평판식에 그대로 넣은 값**이다.",
        but="같은 문서의 C5 가 바로 그 번역을 «과대 번역» 이라 반증하고 «형상 오차의 dB 를 인용할 때는 "
            "면적비가 아니라 커널 측정치를 쓸 것» 이라고 수리안까지 적어 놓았다. I8 은 그 폐기된 자를 다시 썼다.",
        empirical="내 측정으로 그 번역은 실제보다 dB 로 **약 2 배** 과대다(끝값 변경: 면적비 예측 +0.69 dB ↔ 커널 +0.27 dB).",
    ),
    measured_monostatic=dict(
        setup="matrice4e · el −30 · 3.5 GHz · 호버 rpm · PRF 20 kHz · 단일 프로펠러 PO. "
              "c_max/R 을 spec 필드로 **못박아** 시위 분포만 바뀌게 했다(안 그러면 판 이름 때문에 "
              "c_max 가 0.25→0.190 으로 같이 튄다 — 아래 landmine 참조).",
        f_tip_hz=tipspec["meta"]["f_tip_hz"],
        rows={r["law"]: {k: round(r[k], 3) for k in
                         ("sigma_mean_dbsm", "d_P_total_db", "d_P_tipband_090_100_db",
                          "d_P_oob_db")} | {"fd_edge_hz": r["fd_edge_hz"]}
              for r in tipspec["rows"]},
        headline=[
            "끝값 0.10 → 0.20 (I8 의 문면 그대로): f_tip 밴드(0.90~1.0 f_tip) **+0.27 dB**, "
            "OOB +0.39 dB, 총 AC 전력 +0.00 dB, σ 평균 0.00 dB.",
            "끝값 0.10 → 0.30 로 더 밀어도 +0.50 dB.",
            "평면형 통째 교체(같은 c_max): +1.59 dB. 포장된 판(c_max 0.190 동반): +0.50 dB.",
            "내 실측 팁 마디까지 넣으면: +1.86 dB (같은 c_max) / +0.78 dB (포장판).",
        ],
    ),
    measured_bistatic=dict(
        why="감사 C5 가 «형상 민감도는 바이스태틱에서 커진다» 고 했으므로 모노만으로 끝내지 않았다. "
            "헤드라인 팔이 실제로 β≈81° 다.",
        rows=tipbi,
        headline="β=81°: 끝값 변경 **+0.19 dB**, 평면형 교체 +2.25 dB. "
                 "β=120°: 끝값 **+0.14 dB**, 평면형 +2.70 dB. "
                 "⇒ 가장 우호적인 밴드·가장 우호적인 기하를 다 골라도 «팁 끝값» 은 0.2 dB 짜리다.",
    ),
    conclusion="«팁 밴드 −3.10 dB» 가 f_tip 축으로 그대로 들어간다는 주장은 성립하지 않는다. "
               "f_tip 자체 0 dB · fd_edge 0 Hz · 가장 우호적 밴드에서 끝값은 +0.14~+0.39 dB. "
               "스펙트럼 축에서 실제로 값을 만드는 것은 **끝값이 아니라 평면형 전체**(+1.6~+2.7 dB)다.",
)

# ─────────────────────────────────────────────────────────── ⓓ
B = wrap["B_tip_band_area"]
d["D_tip_endvalue_0p20"] = dict(
    audit_recommendation="«CHORD_FRAC 끝값 0.10 → 0.20 근처» (이미 CHORD_FRAC_DJI_MINI2 에 집행됨)",
    verdict="부분 정정 — 방향은 맞다(실물 팁은 뭉툭하다). 그러나 값 0.20 은 **자에 끌려다니는 수**이고, "
            "감사 자신의 측정표(1.00R 정규화 0.078)와 2.5 배 어긋나며, 수리로서는 8 %만 메운다.",
    real_tips_are_blunt=dict(
        independent_of_CAD=[
            "FCC 제출 사진의 **실물** Mini 2 프로펠러(자와 함께 찍힘): "
            "assets/photos/mini2/mini2_c07_fcc_mt2wd_propeller_2blade_ruler.jpg — 주황 팁이 넓고 각지게 끝난다.",
            "제품사진 실루엣(투영 평면형) mavic4pro 1158F: c/c_max 0.594@0.90R · 0.488@0.95 · "
            "0.436@0.97 · 0.354@0.99 · 0.113@1.00. matrice4e 1157F·1154F 도 같은 모양(경사 절단 팁).",
        ],
        glb_measured="내 GLB 측정(밴드 ±0.25 mm): 0.575@0.90 · 0.468@0.95 · 0.445@0.96 · "
                     "0.422@0.97 · 0.402@0.98 · 0.370@0.99 · 0.292@1.00",
        ours_same_ruler="우리 legacy 날을 **같은 자**로: 0.424@0.90 · 0.367@0.95 · 0.335@0.96 · "
                        "0.289@0.97 · 0.234@0.98 · 0.178@0.99 · 0.120@1.00",
        so="0.90~0.99R 전 구간에서 우리가 좁다는 것은 사실이다 — 세 갈래 증거가 같은 말을 한다.",
    ),
    but_0p20_is_a_ruler_artifact=dict(
        measurement="정확히 r=R 에서 시위는 **퇴화**한다(둥근 팁이면 0 으로 간다). 밴드 폭을 바꾸면:",
        dji_c_over_cmax_at_1p00R={"band ±0.06 mm": 0.114, "band ±0.12 mm": 0.191,
                                  "band ±0.25 mm": 0.292, "band ±0.50 mm": 0.341},
        audit_own_number="감사 H_tip 은 1.00R 에서 c/R 0.0206 = 정규화 **0.078** 이라 적었다 — "
                         "그건 우리 legacy 끝값 0.10 **보다도 낮다**. 그러고서 0.20 을 권고했다. "
                         "**권고가 자기 측정과 2.5 배 어긋난다.**",
        reading="따라서 «실물 끝값은 0.20» 이라는 명제는 참이 아니다. 참인 명제는 «실물은 0.94~0.99R 에서 "
                "여전히 넓고, 마지막 1~2 % 에서 급히 둥글어진다» 이다.",
    ),
    as_a_fix_it_barely_moves_anything=dict(
        metric="0.90~1.00R 의 정규화 시위 적분 ∫c dr (실측 = 1.000)",
        area=B["area"], ratio_to_measured=B["ratio_to_measured"],
        reading="legacy 0.651 → 끝값만 0.20 으로 0.705 (**빈틈의 8 %만 메운다**) ↔ "
                "평면형 표 교체 0.933 (**86 %**). 팁 결손은 끝값이 아니라 0.90~0.98R **구간 전체**에 있다.",
        node_by_node=B["node_by_node"],
        residual="코드에 들어간 표(0.475@0.95 → 0.200@1.00 직선)는 0.97R 에서 16 % · 0.98R 에서 23 % 좁고, "
                 "정작 1.00R 에서는 감사 자신의 측정치의 2.5 배다.",
    ),
    tip_refine_does_not_help_shape="⚠ `tip_refine=3` 은 로프트 단면을 더 촘촘히 놓을 뿐, 시위는 **같은 "
                                   "구간선형 표**에서 보간한다. 즉 틀린 직선을 더 충실히 따라갈 뿐 팁 모양 "
                                   "정보를 더하지 않는다. 정보를 더하는 것은 **새 마디**뿐이다.",
    what_would_be_right=dict(
        add_nodes={"0.96": 0.445, "0.97": 0.422, "0.98": 0.402, "0.99": 0.370},
        endpoint="1.00R 은 «실물 값» 이 아니라 **메쉬 마감 규약**이라고 적을 것(±0.06~0.50 mm 자에서 "
                 "0.11~0.34 로 흔들린다). 0.20~0.29 어디를 골라도 스펙트럼 차이는 0.2 dB 안이다.",
        payoff="이 마디를 넣으면 팁 밴드 면적이 0.933 → 1.000 이 되고, 스펙트럼 밴드 전력이 "
               "포장판 대비 +0.28 dB 더 붙는다(측정: +0.50 → +0.78 dB).",
    ),
)

# ─────────────────────────────────────────────────────────── 살아남은 것 / 새 결함
d["E_survived_my_attack"] = [
    "0.75R 은 실제로 프로펠러 공학의 표준 기준 정거장이다(항공기 프롭). 감사의 규약 인용은 맞다.",
    "감사의 DJI k(r) 표는 내 독립 파이프라인이 2.5 % 안에서 재현한다.",
    "감사의 DJI 팁 c/R 표(0.90~0.99R)도 1~2 % 안에서 재현한다.",
    "우리 법칙의 기준 반경이 0.5R 인 것, 그것이 3DR Solo 참조 CAD 의 성질인 것 — 재측정으로 확인 "
    "(내 Solo 측정이 코드 PITCH_K 를 2~4 % 안에서 재현).",
    "외곽 비틀림 폭 9.3° ↔ 5.5° 는 빌드된 메쉬에서 그대로 나온다(9.32 / 5.49°).",
    "실물 DJI 팁이 우리보다 뭉툭한 것은 사진·GLB 세 갈래로 확인된다.",
    "⭐교체를 정당화하는 **더 강한 논거가 따로 있다**: k_DJI 는 정의상 P_loc/P_nom 이므로, "
    "k_DJI 를 쓰고 공표 피치를 넣으면 θ(r)=atan(P_loc/2πr) = **GLB 에서 잰 날각 그대로**가 된다. "
    "mini2 에 대해서는 교체가 실측 비틀림을 구성적으로 재현한다 — «0.75R 표준» 수사는 필요 없다.",
]
d["F_new_defects_i_found"] = [
    dict(what="감사 원장의 회전축 문면이 틀렸다",
         detail="«월드 +y(편차 0.001)» ↔ 실측 허브 캔트 3.16~4.73°. 파급: `src/drones.py` mini2 note 의 "
                "«피치 2.00/3.00 in, 밴드 2.0~3.0» 산포는 축 가정의 인공물이다(허브축으로 재면 sd 4 %).",
         action="감사 C3 문면과 레지스트리 note 를 함께 정정. 8장 평균 k 는 영향 없음."),
    dict(what="`resolve_chord_max_over_r` 이 판 **이름 문자열**로 분기한다",
         detail="`blade_law == 'legacy'` 인지로 c_max/R 을 고르므로, `chord_max_mode='constant'` 라고 "
                "적힌 새 판을 만들어도 조용히 기종별 실측값으로 떨어진다. 내 첫 통제 실험이 이걸로 "
                "1.1~1.4 dB 오염됐다(재실행해서 걷어냄).",
         action="분기 조건을 `chord_max_mode` 로 바꿀 것. 지금은 함정이다."),
]
d["G_recommendations"] = [
    "① 시위 평면형 교체(C4·I2)는 **계속 간다** — 내 측정이 지지하고, 스펙트럼 이득도 실재한다"
    "(f_tip 밴드 +1.6 dB 모노 / +2.3~+2.7 dB 바이).",
    "② 팁은 **끝값이 아니라 마디**를 고칠 것(0.96/0.97/0.98/0.99 = 0.445/0.422/0.402/0.370). "
    "1.00R 값은 «메쉬 마감 규약» 이라고 적을 것.",
    "③ I8 의 «−3.10 dB / net −5.08 dB» 를 팁 변경의 근거에서 **뺄 것** — C5 가 폐기한 평판 번역이다. "
    "대신 측정치(+0.14~+2.70 dB, 조건 명시)를 쓸 것.",
    "④ PITCH_K 교체의 근거를 «0.75R 표준» 이 아니라 «실측 날각을 구성적으로 재현» 으로 바꿔 쓸 것. "
    "그리고 «플래시 봉우리 −2.2 dB» 는 **삭제**할 것(측정 0.00 dB). 3.5 GHz 에서 피치는 ≤0.1 dB 손잡이라 "
    "켜도 안전하지만 급하지도 않다.",
    "⑤ `src/drone_cad.py` 168~172 행의 팁 주석(«아직 커널로 안 쟀다»)은 이제 잰 값으로 갱신할 것.",
    "⑥ 감사 §⑤ 17 의 게이트(«확정 전 플래시 폭을 커널로 직접 잴 것»)는 **충족됐다** — 이 원장이 그 측정이다.",
]
json.dump(d, open(OUT, "w"), indent=1, ensure_ascii=False)
print("wrote", OUT, os.path.getsize(OUT), "bytes")
