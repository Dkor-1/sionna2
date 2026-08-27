# -*- coding: utf-8 -*-
"""fix_canon_airframes.py — 기체 갈래 원장의 «손 덧칠»을 다시 올린다 (2026-08-27 신설)

왜 있나
-------
`build_material_verdict.py` 가 `material_canon_0816_airframes.json` 을 **재생성**하면
손으로 넣었던 정정 셋이 매번 지워진다. 실제로 2026-08-27 판정층 재실행에서 지워졌고,
그 결과 원장이 **J1 이 기각한 −3.43 dB 권고를 살아 있는 규약처럼** 적게 됐다.

`fix_canon.py` 는 정본(`material_canon_0816.json`) 한 파일만 쓴다 — 그 파일 본문이
「기체 갈래 원장은 아직 기각된 권고를 적고 있다」고 **지적만** 하고 고치지는 않았다.
이 스크립트가 그 구멍을 막는다. 멱등이다(여러 번 돌려도 같은 결과).

⛔`run_verdicts_0818.sh` 의 4b 층에서 `fix_canon.py` 바로 뒤에 돌린다.
"""
import json, collections, sys

P = "/workspace/sionna/outputs/material_canon_0816_airframes.json"

REJECT = (
    "⛔[정본 J1 판정 — 2026-08-16] **이 마지막 권고는 기각됐다.** 자세를 «지우는» 솎기는 "
    "균일 시간 표본을 깨뜨려 빗살·리듬 잣대 자체를 부순다 — 아무 자세나 하나 지워도 같은 "
    "크기로 흔들린다(sd 2.26 dB). 이웃 평균 갈아끼우기(−6.95 dB)와 균일 재표집"
    "(−5.78~−6.31 dB)에서는 제자리다. ⇒ 정본 빗살 Δ(el −30 · 프롭 0.9 mm)는 "
    "**−6.95 ~ −6.98 dB, 밴드 밖(유의)** 이고, 여기 적힌 −3.43 dB 는 **인용하지 않는다**."
)
GRADE_HOLE = (
    "⚠[적대적 검산] 고립도(최대÷둘째)만으로는 **여럿이 함께 튀는 칸**을 못 잡는다 — "
    "H5 갈래의 정면 0° 굴절 × 얇은 칸은 고립도가 1.000 인데 유효 자세 수가 6(8192 중)이고 "
    "상위 8 자세가 99.93 % 다. 등급에 유효 자세 수·상위 8 자세 몫을 함께 넣어야 한다."
)

d = json.load(open(P), object_pairs_hook=collections.OrderedDict)
v = d.get("verdict")
if v is None:
    sys.exit("⛔ /verdict 가 없다 — 원장 구조가 바뀌었다")

did = []

# ① 말투 — 내부 축약어 «튐» 을 정본 표현으로
f = v.get("outlier_forensics_ko", "")
if "튀는 자세(이상값) 고립도" not in f and "튐 고립도" in f:
    f = f.replace("튐 고립도", "튀는 자세(이상값) 고립도")
    did.append("말투 «튐» → «튀는 자세(이상값)»")

# ② J1 기각 문장 — 없으면 뒤에 붙인다
if "정본 J1 판정" not in f:
    f = f.rstrip() + " " + REJECT
    did.append("J1 기각 문장 복구")
v["outlier_forensics_ko"] = f

# ③ 적대적 검산이 찾은 등급 구멍 — 없으면 되살린다
if "outlier_grade_hole_ko" not in v:
    v["outlier_grade_hole_ko"] = GRADE_HOLE
    did.append("outlier_grade_hole_ko 복구")

if did:
    json.dump(d, open(P, "w"), ensure_ascii=False, indent=1)
    print("✅ 덧칠 다시 올림 — " + " · ".join(did))
else:
    print("✅ 이미 덧칠돼 있다 (변경 없음)")
