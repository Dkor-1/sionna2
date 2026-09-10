#!/usr/bin/env python
"""0922 발주서 — 월요일(2026-09-14) 팀미팅까지 돌린다.

⛔발주서를 손으로 쓰지 않는다. 이 생성기가 원장(work/wf/queue_design_0922_result.json)을
  읽어 줄을 내고, 샤드 나눔만 여기서 붙인다.

■ 어떻게 나왔나
  바닥 자료를 두 에이전트가 **메쉬를 직접 열어** 재고, 그 위에서 다섯 관점이 25 묶음을 냈다.
  묶음마다 「죽이려고」 반증했고 **18 이 죽고 7 이 살아남았다.**
  ⭐확정 둘(뒤쪽 반구 · 협곡 널)은 사용자가 이미 승인해 설계를 안 거치고 넣었다.

■ ⛔⛔이 발주서를 읽는 사람이 오해하지 않도록 — 여기 적힌 것은 «물음» 이지 «답» 이 아니다
  · 묶음 이름은 **무엇을 사는지**이지 무엇이 참인지가 아니다.
  · 「죽는 조건」은 그 물음이 **닫히는 방식**이다. 그 조건이 안 걸리면 열린 채로 둔다.
  · ⛔「이 묶음이 답하지 않는 것」을 묶음마다 적었다 — 결과를 읽을 때 그 줄을 먼저 본다.
  · ⛔어떤 줄도 「우리 커널이 맞고 솔버가 틀렸다」를 겨누지 않는다. 둘 다 근사다.
  · ⛔실기 계측 대조는 이 저장소에 **0 건**이다. 이 판으로도 안 생긴다.

■ ⚠2026-09-09 에 외부 지적으로 확인된 한계 — 이 판의 결과를 읽을 때 함께 본다
  ① **상한과 해시 통 수가 묶여 있다** — sb_candidate_generator.py:312 의
     spec_counter_size = max(max_num_paths_per_src, 1e6) 이라, 우리 상한 2,000,000 은
     바닥값 위다. ⇒ 「상한만 바꿨다」는 단일 변수 실험이 아니다. 이 판에는 상한을 흔드는
     줄이 없지만, 결과에 상한 이야기를 붙일 때 이 한계를 함께 적는다.
  ② **반환 경로 수는 후보 수가 아니다** — path_solver.py:194 후보 생성 → :246 무효 경로
     제거. ⇒ 「nret 이 상한보다 작으니 잘림 없다」로 후보 단계 유실을 배제할 수 없다.
  ③ **D = E_장면 − E_빈하늘 은 «환경 산란» 이 아니다** — 환경 때문에 바뀐 드론 경로 ·
     차폐 · 두 실행의 후보 탐색 차이가 함께 들어간다. ⇒ 「장면이 얹은 몫」으로만 부른다.
  ④ **진폭이 늘어난 것을 «경로 유실의 반증» 으로 쓰지 않는다** — 복소 전계는 상쇄한다.
     협곡에서 걸린 자세는 **하나도 빠짐없이 위로** 갔다(el−30 96/96 · el−60 339/339).
  ⑤ **expected_if_unrelated = n_a·n_b/N 은 균일·독립 추출을 가정한 참고값**이다.
     자세는 시각이고 로터 위상 구조가 있다 — 「기댓값에 가까우니 무상관」으로 못 읽는다.
  ⑥ **옵션을 다 켜도 모든 상호작용을 계산하는 것이 아니다** — v2.0.1 후보 생성기는
     회절을 경로당 1 회로 묶고 확산+회절 동거를 막는다.

■ 상시 규약
  ⛔확산(F 비트)은 모든 팔에서 항상 켠다 — F0 계열 없음.
  ⛔프로펠러 단독(--parts prop) 없음. ⛔뮌헨 없음(드론이 건물에 막혀 결과가 아니다).
  ⛔지면 거칠기 축은 경로 상한에 붙어 접은 채로 둔다.

쓰는 법:
    /workspace/.venvs/py312/bin/python runners/make_jobs_0922.py --summary
    /workspace/.venvs/py312/bin/python runners/make_jobs_0922.py > runners/jobs_0922.txt
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = f"{ROOT}/work/wf/queue_design_0922_result.json"
NSH = 2

with open(SRC, encoding="utf-8") as f:
    R = json.load(f)

M = R["merged"]
LINES = M["queue_lines"]
GROUPS = M["groups"]

#: ⛔규약 문지기 — 설계판이 지켰는지 믿지 않고 여기서 한 번 더 막는다
for ln in LINES:
    if "F0" in ln:
        raise SystemExit(f"⛔확산을 끈 팔이 들어 있다: {ln}")
    if "--parts prop" in ln:
        raise SystemExit(f"⛔프로펠러 단독은 안 산다: {ln}")
    if "munich" in ln:
        raise SystemExit(f"⛔뮌헨은 결과가 아니다: {ln}")
    if "--env-scat" in ln:
        raise SystemExit(f"⛔거칠기 축은 접은 채로 둔다: {ln}")
    if "--shard" in ln or "--nshards" in ln:
        raise SystemExit(f"⛔줄에 샤드가 이미 붙어 있다 — 생성기가 붙인다: {ln}")

OUT = []
OUT.append("# ══ 0922 큐 — 월요일(2026-09-14) 팀미팅까지 ══")
OUT.append(f"#  줄 {len(LINES)} × 샤드 {NSH} = {len(LINES) * NSH} 샤드 · 어림 {M['total_hours']} 일꾼시간")
OUT.append("#")
OUT.append("#  ⛔⛔여기 적힌 것은 «물음» 이지 «답» 이 아니다.")
OUT.append("#     묶음 이름은 무엇을 사는지이지 무엇이 참인지가 아니다.")
OUT.append("#     결과를 읽을 때 «이 묶음이 답하지 않는 것» 을 먼저 본다.")
OUT.append("#  ⛔「우리 커널이 맞고 솔버가 틀렸다」를 겨누는 줄은 하나도 없다 — 둘 다 근사다.")
OUT.append("#  ⛔실기 계측 대조는 이 저장소에 0 건이고 이 판으로도 안 생긴다.")
OUT.append("#")
OUT.append("#  ── 2026-09-09 외부 지적으로 확인된 한계 (결과를 읽을 때 함께 본다) ──")
OUT.append("#  ① 상한과 중복제거 해시 통 수가 묶여 있다(spec_counter_size = max(상한, 1e6)).")
OUT.append("#     우리 상한 2,000,000 은 바닥값 위다 — 「상한만 바꿨다」는 단일 변수가 아니다.")
OUT.append("#  ② 반환 경로 수는 후보 수가 아니다(후보 생성 → … → 무효 경로 제거 순).")
OUT.append("#  ③ D = E_장면 − E_빈하늘 은 «환경 산란» 이 아니다 — 차폐·드론 경로 변화·")
OUT.append("#     후보 탐색 차이가 함께 들어간다. 「장면이 얹은 몫」으로만 부른다.")
OUT.append("#  ④ 진폭 증가를 «경로 유실의 반증» 으로 쓰지 않는다 — 복소 전계는 상쇄한다.")
OUT.append("#     협곡에서 걸린 자세는 하나도 빠짐없이 위로 갔다(el−30 96/96 · el−60 339/339).")
OUT.append("#  ⑤ expected_if_unrelated = n_a·n_b/N 은 균일·독립 추출을 가정한 참고값이다.")
OUT.append("#  ⑥ 옵션을 다 켜도 모든 상호작용이 아니다 — 회절은 경로당 1 회, 확산+회절 동거 금지.")
OUT.append("#")
OUT.append("#  ── 묶음 ──")
for g in GROUPS:
    OUT.append(f"#  ▸ {g['name']} ({g['n_lines']} 줄 · 어림 {g['cost_hours']} 시간)")
    OUT.append(f"#      물음      {g['question']}")
    OUT.append(f"#      죽는 조건  {g['kill_condition']}")
    if g.get("caveat"):
        OUT.append(f"#      ⛔안 답함  {g['caveat']}")
    OUT.append(f"#      읽는 법    {g.get('reads_how', '')}")
OUT.append("#")
OUT.append("#  ── 차례를 왜 이렇게 짰나 ──")
for s in str(M.get("order_why", "")).splitlines():
    OUT.append(f"#  {s}")
if M.get("code_work"):
    OUT.append("#")
    OUT.append("#  ── ⛔발주가 아니라 코드로 해야 하는 일 (이 큐에 안 들어간다) ──")
    for c in M["code_work"]:
        for s in str(c).splitlines():
            OUT.append(f"#  · {s}")
if M.get("dropped"):
    OUT.append("#")
    OUT.append("#  ── 버린 것 ──")
    for s in str(M["dropped"]).splitlines():
        OUT.append(f"#  {s}")
OUT.append("")

_SEEN = set()
for ln in LINES:
    for k in range(NSH):
        line = f"{ln} --shard {k} --nshards {NSH}"
        if line in _SEEN:
            OUT.append(f"#   ⤷ 건너뜀(이미 위에 있다): {line}")
            continue
        _SEEN.add(line)
        OUT.append(line)

if "--summary" in sys.argv:
    n = sum(1 for x in OUT if x and not x.startswith("#"))
    print(f"발주 줄 {n} (샤드 나눔 포함) · 조건 {len(LINES)} 개")
    print(f"어림 {M['total_hours']} 일꾼시간")
    for g in GROUPS:
        print(f"  {g['n_lines']:>3} 줄 · {g['cost_hours']:>6.1f} h  {g['name']}")
else:
    print("\n".join(OUT))
