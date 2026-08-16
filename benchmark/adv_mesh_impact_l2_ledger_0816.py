# -*- coding: utf-8 -*-
"""적대 검증 결과를 원장 JSON 하나로 모은다 (outputs/mesh_impact_layer2_adversarial_0816.json)."""
import json
import os
import time

import numpy as np

S = "/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad/"
V = S + "verify2/"
OUT = "/workspace/sionna/outputs/mesh_impact_layer2_adversarial_0816.json"


def kst():
    return time.strftime("%Y-%m-%d %H:%M KST", time.gmtime(time.time() + 9 * 3600))


L = lambda n: json.load(open(S + "l2runs/" + n + ".json"))["drones"]
off = L("off")
runs = {t: L(t) for t in ("i5", "m6", "battery", "i4", "m4", "i3", "mesh5", "all6", "i5_i4")}
G = ("mono_el0", "mono_el-30", "bi_b120_el-30")


def per_az(a, b, g):
    s0 = np.array(a["sigma"][g]); s1 = np.array(b["sigma"][g])
    per = 10 * np.log10(np.maximum(s1, 1e-300)) - 10 * np.log10(np.maximum(s0, 1e-300))
    return dict(
        방위평균Δ_db=round(float(10 * np.log10(s1.mean()) - 10 * np.log10(s0.mean())), 4),
        방위별_절대값_중앙값_db=round(float(np.median(np.abs(per))), 3),
        방위별_절대값_p90_db=round(float(np.percentile(np.abs(per), 90)), 3),
        방위별_절대값_최대_db=round(float(np.abs(per).max()), 3),
        방위중_1dB넘는_비율_pct=round(float((np.abs(per) > 1).mean() * 100), 1),
        방위중_3dB넘는_비율_pct=round(float((np.abs(per) > 3).mean() * 100), 1))


tab = {}
for tag, keys in (("battery", ("mini5pro", "mavic4pro", "mini2", "phantom4")),
                  ("i4", ("mavic4pro", "matrice4e", "typhoonh480", "phantom3")),
                  ("m4", ("x500v2",)),
                  ("i3", ("mini2", "mavic4pro", "mini5pro", "m350rtk", "s1000plus")),
                  ("mesh5", ("mavic4pro", "mini5pro", "x500v2")),
                  ("all6", ("mavic4pro", "mini5pro"))):
    for k in keys:
        if k in runs[tag]:
            tab[f"{tag}/{k}"] = {g: per_az(off[k], runs[tag][k], g) for g in G}
tab["i4/mini2(i5기준)"] = {g: per_az(runs["i5"]["mini2"], runs["i5_i4"]["mini2"], g) for g in G}

md = {t: json.load(open(S + "l2md/" + t + ".json"))["drones"] for t in ("off", "mesh5", "i3")}


def mx(x, y):
    x, y = np.array(x), np.array(y)
    return round(float(np.abs(10 * np.log10(np.maximum(y, 1e-300))
                              - 10 * np.log10(np.maximum(x, 1e-300))).max()), 4)


ac = {k: dict(i3_AC_프롭만_db=mx(md["off"][k]["sigma_ac_prop"], md["i3"][k]["sigma_ac_prop"]),
              i3_AC_전체필드_db=mx(md["off"][k]["sigma_ac_full"], md["i3"][k]["sigma_ac_full"]),
              mesh5_AC_전체필드_db=mx(md["off"][k]["sigma_ac_full"], md["mesh5"][k]["sigma_ac_full"]))
      for k in md["off"]}

doc = dict(
    _meta=dict(
        title="2층 수리 영향 라운드 — 적대 검증(별도 검증자)",
        generated_kst=kst(),
        역할="영향 라운드가 낸 수를 **다른 방법으로 다시 재고** 빠진 축을 찾는다. 값은 안 넣었다.",
        compute="CPU 전용(GPU 금지 준수) · git 무접촉",
        검증한_정본="outputs/mesh_impact_layer2_0816.json · docs/MESH_AUDIT_0816.md §⑨",
        원자료="/tmp/.../scratchpad/l2runs/*.json · l2md/*.json (영향 라운드가 남긴 원시 σ 배열)"),
    재현된_것=dict(
        게이트="현재 저장소에서 다시 돌림 — mesh_check 끔 10/10 · 켬(i5,m6,battery,i4,m4) 10/10 · "
               "adv_mesh_check_faults 끔 16/16 · 켬 16/16",
        기본경로_비트동일=dict(
            계측="수리 함수(cadkit.collapse_degenerate_faces · _fix_i4_canopy · _fix_m4_arm_clamp)를 "
                 "감시하며 10기체를 지었다 — 호출 0회. MESH_FIX 빈문자열·mesh_fix=False·켰다 끈 뒤 "
                 "모두 지문 동일.",
            귀속_재현_3층="src 사본에서 3층 값 5묶음만 되돌리자 드론 10 + uv_sphere 4 = **14/14** 가 "
                          "i5·m6 라운드의 «수리전코드» 지문과 일치 ⇒ 2층 스위치 몫 0 (영향 라운드 결론과 같다)"),
        대조군="지문 불변 칸 5개 전부 σ 바이트 동일 · 겹침 없던 3기체(matrice4e·phantom3·m350rtk)의 "
               "battery 수리는 Δ ≤ 1e-5 dB 수치잡음",
        누적_상호작용="30칸(10기체×3배치) 전부 원장과 일치(내 첫 계산이 mini2 i4 항을 빠뜨렸던 것이지 "
                      "원장이 틀린 게 아니다)",
        σ_독립재계산=dict(
            방법="샘플러(4분할 무게중심)·방위격자(1°부터 3°, 120점)·점간격(λ/6)·주파수(5점)를 전부 바꿔 "
                 "다시 쟀다 — 저장소 커널 함수를 안 부른다",
            결과="12칸 최대차 0.15 dB(i3/mini5pro), 중앙 0.02 dB. 부호·크기·밴드 판정 전부 같다"),
        마이크로도플러="mesh5 에서 프롭 메쉬 지문·프롭 복소필드 sha256 동일 확인(5기체)",
        질량축="battery 수리의 질량·관성 변화가 수리자 원장과 소수점까지 일치"),
    고침_1_AC칸이_다른_값이다=dict(
        무엇="§9-4 표의 «AC(움직이는 성분) 최대Δ» 칸은 원장의 `max_dac_prop_db`(프롭 점만의 AC)를 실었다. "
             "그런데 같은 절의 정의문은 «**전체 필드**에서 위상평균을 뺀 뒤의 세기» 라고 적는다 — "
             "그 값은 `max_dac_full_db` 이고 원장에 이미 들어 있다.",
        왜_중요한가="i3 는 위상마다 마스크가 달라져 **프레임 면까지** 위상 의존이 생긴다. 그래서 두 값이 "
                    "갈라진다. 큰 쪽이 실제로 관측되는 «없던 변조» 의 크기다.",
        수=ac,
        방향="결론(«i3 를 마이크로도플러에 그대로 쓰지 마라»)은 **더 강해진다** — 축소가 아니라 확대다."),
    남김_1_방위평균만_보면_안_움직인다=dict(
        무엇="«메쉬 수리 5종은 σ 를 거의 안 움직인다» 는 **방위평균**에서만 참이다. 같은 원시 배열을 "
             "방위별로 보면 절반 안팎의 방위가 1 dB 넘게 움직인다.",
        예=dict(
            mesh5_mavic4pro_bi="방위평균 −1.23 dB인데 방위별 |Δ| 중앙값 3.30 dB · 79 % 가 1 dB 초과",
            m4_x500v2_mono_el0="방위평균 −0.14 dB(밴드 «보임»)인데 방위별 |Δ| 중앙값 1.30 dB · 59 % 가 1 dB 초과"),
        왜_최악방위_경고로는_안_덮이나="원장은 «최악방위는 널이라 부호가 뒤집힌다» 며 최댓값만 물리쳤다. "
                                       "그러나 **중앙값**이 1~3 dB 라는 것은 널의 문제가 아니라 방위 패턴 자체가 "
                                       "재배열됐다는 뜻이다.",
        무엇이_안_바뀌나="방위평균을 쓰는 결론(탐지거리 사다리·기체 간 서열)은 안 흔들린다. 흔들리는 것은 "
                        "**방위(자세)별 σ 를 그대로 쓰는 계산**이다.",
        표=tab),
    남김_2_i3의_dB는_규칙_선택에_매달린다=dict(
        무엇="`mesh_buried.INTERNAL_GROUPS` 는 «반투명 셸 뒤라서 보인다» 를 battery·pcb·fc **세 그룹**에만 "
             "인정한다. 그런데 셸 **안에만** 들어 있는 camera·motor·gear·accent 도 물리적으로 같은 상황이고, "
             "지금 규칙은 그것들을 «결함» 으로 지운다.",
        크기="i3 가 지우는 면적 중 «셸 안에만» 있는 것 — mavic4pro 38,233 / 94,862 mm² (40.3 %), "
             "mini5pro 15,266 / 43,603 (35.0 %), mini2 10,012 / 31,400 (31.9 %). "
             "그중 camera 만 해도 mavic4pro 18,296 mm².",
        σ_민감도="camera·motor·gear·accent 중 «셸 안에만» 있는 면을 도로 살린 판과 비교: "
                 "mavic4pro −2.46 → −1.16 dB(차 1.30) · mini5pro −4.10 → −1.86(차 2.24) · "
                 "mini2 −3.48 → −2.99(차 0.49). el −30·바이까지 보면 0.15~2.24 dB.",
        판정="어느 쪽이 옳은지 이 검증으로는 못 정한다. 다만 **이 라운드의 가장 큰 dB(i3)가 측정된 적 없는 "
             "규칙 선택에 1~2 dB 매달려 있다**는 것은 원장의 «안 잰 것» 에 들어가야 한다."),
    남김_3_게이트는_예산을_넓힌_뒤의_통과다=dict(
        무엇="i4(불리언 합집합)는 씨접합 슬리버를 새로 만든다. 검사기가 통과하는 것은 "
             "`mesh_check.SLIVER_BUDGET_MESH_FIX` 로 두 칸을 넓혔기 때문이다.",
        내가_센_값="mini2 185→215(예산 198→240) · typhoonh480 461→508(508→560) · mini5pro 235→285 · "
                   "matrice4e 239→261 · x500v2 381→389(m4). 수리자 선언과 일치.",
        면적="mini2 슬리버 면적 3.63→4.36 mm² (표면적의 0.005 %) — σ 영향은 없다.",
        요구="§9-5 의 «10/10 통과» 문장에 **예산 두 칸을 넓혔다**는 사실을 같이 적어야 한다."),
    남김_4_질량_관성축이_영향원장에_없다=dict(
        무엇="battery 합집합은 겹친 부피를 한 번만 세게 만든다 ⇒ 부피·질량배분·관성이 바뀐다. "
             "영향 라운드 §⑨ 에는 이 축이 없다(«안 잰 것» 목록에도 없다).",
        내가_잰_값="battery 부피 −12.27 %(4기체 공통) · battery 질량 mavic4pro 214.2→192.7 g · "
                   "phantom4 319.9→288.8 g · CoM 0.18~0.45 mm 이동 · 관성 대각 +1.9~+2.8 %. "
                   "matrice4e(겹침 0)는 정확히 0.",
        이미_잰_사람="수리자 원장 outputs/mesh_layer2_battery_overlap_0816.json :: 질량축_감사I9 — "
                     "내 값과 소수점까지 같다. 즉 **측정 누락이 아니라 인계 누락**이다."),
    확인만_한_것=dict(
        GPU="내 실행 전부 CUDA_VISIBLE_DEVICES='' · 영향 라운드 스크립트도 같은 기본값. GPU 프로세스 목록에 "
            "내 파이썬 없음.",
        git="HEAD e574d2c 그대로 · 스테이징 0 · 새 커밋 0.",
        교차검증_75칸의_성격="영향 라운드의 «앞 라운드 재현 75칸 최대차 0.0000 dB» 는 같은 커널·같은 격자·"
                            "같은 소스 스냅샷을 다시 돌린 것이라 **재실행**이지 독립 방법이 아니다. "
                            "독립성은 위 σ_독립재계산(다른 샘플러·격자)이 담당하고, 그쪽도 통과했다."),
)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(doc, fh, ensure_ascii=False, indent=1)
print("wrote", OUT, os.path.getsize(OUT), "bytes")
print(json.dumps(ac, ensure_ascii=False, indent=1))
