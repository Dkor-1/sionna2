export const meta = {
  name: 'verify-followup-0909',
  description: '해석 후속 검토 10 항목을 독립 검증한다 — 소스·원장·샤드에 직접 대고. 부모가 이미 확인한 둘(5·6)은 제외',
  phases: [
    { title: 'Check', detail: '항목 하나씩 소스·원장에 대고 확인' },
    { title: 'Judge', detail: '고칠 것과 순서' },
  ],
}

const RULES = `
■ 상시 규약
  ⛔말을 지어내지 않는다. 파일에서 읽은 것만 쓰고 경로:줄번호를 함께 적는다.
  ⛔확인 못 한 것은 「모른다」로 적는다.
  ⛔「우리 커널이 맞고 솔버가 틀렸다」로 결론짓지 않는다 — 둘 다 근사다.
  ⛔지적이 옳다고 해서 「시오나가 틀렸다」로도 넘어가지 않는다.
  ⛔**지적에도 같은 잣대를 댄다** — 지적이 과하거나 틀렸으면 근거와 함께 적어라.
  ⛔실기 계측 대조는 이 저장소에 0 건이다.
  ⭐파이썬 /workspace/.venvs/py312/bin/python · CPU 로만 — CUDA_VISIBLE_DEVICES=""
  ⛔GPU 큐가 돌고 있다(jobs_0922). GPU 를 쓰는 명령을 내지 마라.
  ⛔무거운 CPU 작업은 os.sched_setaffinity 로 코어를 묶어라(규약 17).
  ⛔아무것도 고치지 마라 — 이 일은 **검증**이다. 고칠 자리를 찾아 적기만 한다.

■ 자리
  검토 메모  /workspace/sionna/docs/INTERPRETATION_FOLLOWUP_0909.md (10 항목)
  재계산 코드 /workspace/sionna/benchmark/review_interpretation_followup_0909.py
  검산 원장  /workspace/sionna/outputs/interpretation_followup_0909.json
  설치본     /workspace/.venvs/py312/lib/python3.12/site-packages/sionna/rt/
  우리 저장소 /workspace/sionna — 원장 outputs/*.json · 문서 docs/*.md ·
             본편 reports/*.ipynb · 재개 지점 work/sweep_0904/RESUME_090*.md
  덱         /workspace/team_meeting/teammeeting_0910/teammeeting_slides_0910_v21.json

■ ⭐부모가 이미 직접 확인한 것 (다시 확인해도 좋지만 뒤집으려면 근거를 대라)
  · 항목 5(깊이 포함관계) — **맞다.** outputs/read_0914_0908.json 에서
    깊이 1 = 51 · 깊이 2 = 82 · 깊이 3 = 91 이고 교집합이 51·82·51 로 **완전 포함**이다.
    내가 work/sweep_0904/RESUME_0908.md:112 에 「깊이는 걸리는 자세를 안 옮긴다」로
    적었는데 정확히는 「기존 사건이 남고 새 사건이 더 생긴다」다.
  · 항목 6(귀무모형) — **맞다.** benchmark/read_0914_0908.py:211 의
    expected_if_unrelated = n_a·n_b/N 은 균일·독립 추출 가정이다.
    자세는 시각 t=i/PRF 이고(elevation_sweep_md.py:363) 로터 위상 구조가 있다.

■ ⚠2026-09-09 에 이미 검증이 끝난 앞선 지적 아홉 건 (겹치면 그렇게 적어라)
  work/wf/verify_critique_0909_result.json 에 전문이 있다. 아홉 건 모두 본론이 섰고,
  덱 v20 의 틀린 문장 둘을 고쳐 v21 을 냈다(9 쪽 「far deeper」 방향 반대 ·
  5 쪽 「벼랑이다」를 같은 그림의 회절 팔 한 점이 반박).
`

const CLAIM_SCHEMA = {
  type: 'object',
  properties: {
    n: { type: 'integer' },
    title: { type: 'string' },
    verdict: { type: 'string', enum: ['맞다', '대체로 맞다', '부분적으로만', '틀리다', '확인불가'] },
    evidence: { type: 'string', description: '소스·원장·샤드에서 직접 읽거나 재계산한 것 — 경로:줄번호와 실제 값' },
    what_it_breaks: { type: 'string', description: '우리 결론·원장·본편·덱 중 무엇이 흔들리나. 없으면 «없다»' },
    where_to_fix: { type: 'string', description: '고칠 자리 — 파일:줄. 없으면 «없다»' },
    overreach: { type: 'string', description: '지적이 과하거나 틀린 부분. 없으면 «없다»' },
    already_handled: { type: 'string', description: '이미 그렇게 적어 둔 곳' },
  },
  required: ['n', 'title', 'verdict', 'evidence', 'what_it_breaks', 'overreach'],
}

phase('Check')
log('여덟 항목을 소스·원장에 대고 확인한다 (5·6 은 부모가 이미 봤다)')

const ITEMS = [
  { n: 1, label: 'mode', prompt: `■ 항목 1 — 「흔들림 발생률 2.5 %」는 오류율이 아니다.
  합성 평판 CPU 실험에서 단일 스레드의 최빈 경로 수는 8,059 인데 두 스레드는 8,058 이다.
  두 스레드 40 회 중 39 회가 8,058 이다. ⇒ 자기 최빈값에서 벗어난 비율은 2.5 %지만
  **단일 스레드 기준과 다른 비율은 97.5 %** 다.
  「되풀이할 때 얼마나 달라지나」와 「설정을 바꾸면 얼마나 달라지나」를 따로 보고해야 한다.
  어느 경로 수가 물리적으로 옳은지는 이 비교로 안 정해진다.

확인할 것:
  · 그 수가 어느 원장에 있나 — outputs/thread_ladder_0903.json 을 열어 실제 값을 읽어라.
    8,059 · 8,058 · 40 회 · 39 회가 맞나. 최빈값 이탈률 2.5 %가 어디서 나온 수인가.
  · ⭐「2.5 %」를 인용하는 자리를 저장소 전체에서 찾아라 — docs/*.md · outputs/*.json ·
    reports/*.ipynb · work/sweep_0904/*.md · 덱. 그 문장이 무엇이라 부르고 있나.
  · docs/DEEP_DROP_0902.md 와 CLAUDE.md 의 스레드 사다리 서술을 읽어라.
  · ⛔지적이 과한가 — 「97.5 %」라는 수가 정말 그 자료에서 나오나 직접 세라.` },

  { n: 2, label: 'zeroamp', prompt: `■ 항목 2 — 진폭이 0 인 결과가 편차 집계에서 빠질 수 있다.
  실제 통계 함수는 **h > 0 인 표본만** 편차 계산에 넣는다. 그 함수를 떼어 합성 입력으로
  확인하니 영 진폭을 넣어도 최대 편차가 0 으로 나오는 경우가 있었다.
  과거 실험에 실제로 영 진폭이 있었는지는 미확인이다. 다만 제외된 표본 수를 기록하지 않은 채
  「변화 없음」으로 읽는 것은 위험하다.

확인할 것:
  · ⭐**어느 함수인가** — benchmark/*.py 에서 h > 0 · > 0 필터가 걸린 편차·통계 함수를 찾아라.
    (thread_ladder · true_repeat · el0_drop · probe_drop 계열을 보라)
    찾으면 그 줄을 인용하고, 합성 입력으로 **직접 재현**해라(CPU).
  · ⭐과거 실험에 실제로 영 진폭이 있었나 — 재고 샤드에서 |E| == 0 인 자세를 세라.
    (몇 장만 표본으로 보고, 없으면 「표본에서는 못 찾았다」로 적어라)
  · 그 함수의 결과를 인용하는 자리에 「제외된 표본 수」가 적혀 있나.` },

  { n: 3, label: 'thread', prompt: `■ 항목 3 — 「병렬 축약 순서가 원인으로 규명됐다」가 아직 남아 있다.
  CPU 재현과 스레드 수 대조는 **병렬 실행과의 관련성**을 지지한다. 그러나 특정 내부 연산까지
  지목하려면 별도 계측이 필요하다. 지금 문서에는 「어느 경합인지는 미확정」이라는 한정과
  「기전이 갈렸다」는 제목이 **공존**한다. 제목·생성기·원장의 판정 문구를 함께 맞춰야 한다.

확인할 것:
  · ⭐「기전이 갈렸다」·「원인이 밝혀졌다」류 문구가 어디에 있나 — CLAUDE.md 의 DEEP_DROP 줄 ·
    docs/DEEP_DROP_0902.md · outputs/thread_ladder_0903.json · reports/*.ipynb 를 훑어라.
    그 문장을 **그대로 인용**하고 자리를 적어라.
  · 같은 자리에 「미확정」 한정이 함께 있나. 공존이면 어느 쪽이 제목이고 어느 쪽이 각주인가.
  · benchmark/check_retracted.py 가 이 건을 보나.
  · ⛔지적이 과한가 — 스레드 사다리가 실제로 무엇까지 보였는지 원장에서 확인해라.` },

  { n: 4, label: 'hashscope', prompt: `■ 항목 4 — 경로 상한과 해시 배열을 바꾸는 실험의 적용 범위.
  ⭐지적자 스스로 이전 피드백을 보정했다 — 「상한과 해시 배열 크기의 관계는 **기존 실험
  문서에도 이미 명시돼 있었다**. 이번에는 현재 설치본에서도 그 관계를 확인했다.」

확인할 것:
  · ⭐**정말 기존 문서에 이미 있었나** — docs/*.md · outputs/*.json 에서
    「해시」·「hash」·「spec_counter」·「MIN_SPEC_COUNT」를 훑어라. 있으면 그 자리를 인용해라.
    (docs/DEEP_DROP_0902.md 가 「해시 통 수 32 배」를 흔들었다고 적는다 — 그것과 같은 것인가?)
  · 설치본 확인 — sb_candidate_generator.py:59 MIN_SPEC_COUNT_SIZE · :312-315.
  · ⭐**우리 상한을 흔든 실험이 실제로 어느 범위였나** — 재고의 _mp 꼬리표를 세고,
    2,000,000(규약값)·6e6·1.2e7 이 전부 1e6 위인지 확인해라.
  · 그 실험 결과를 「저장 부족이 원인」으로 읽은 문장이 있나. 있으면 그대로 인용해라.
  · ⛔분리 실험(저장 상한 고정 + 해시 크기만)이 **가능한가** — 손잡이가 있나,
    설치본을 고쳐야 하나. 소스를 읽고 판단해라.` },

  { n: 7, label: 'envscat', prompt: `■ 항목 7 — 기본 장면의 --env-scat 이 **드론 부품까지** 선택한다.

확인할 것:
  · benchmark/elevation_sweep_md.py 의 --env-scat 처리 자리를 읽어라(:858-866 근처).
    조건이 정말 남의 씬에서 sc.objects 전부를 훑나 — 코드를 그대로 인용해라.
  · ⭐**직접 재현해라**(CPU) — 작은 씬에 드론 이름의 물체를 얹고 그 루프를 돌려
    드론에도 산란계수가 걸리는지 확인해라.
  · ⭐**영향 범위** — --env-scat 을 쓴 샤드를 세라(_S 꼬리표). 그중 **남의 씬** 판이 있나?
    있으면 그 샤드의 수를 인용하는 자리를 찾아라. 없으면 「우리 씬에만 썼으니 지금은
    영향이 없다」로 적되, 앞으로 쓰면 문다는 것을 적어라.
  · 거칠기 축을 접은 근거(path_cap_share_pct 99.24 %/100 %)가 이것과 얽히나.` },

  { n: 8, label: 'detdedup', prompt: `■ 항목 8 — --det 와 중복 제거를 함께 쓰면 정렬 전후 인덱스가 어긋난다.
  최소 연산 재현에서 중복 제거 합이 기대값 6 대신 **7** 로 나왔다.

확인할 것:
  · benchmark/elevation_sweep_md.py 에서 --det 처리와 중복 제거(E_dedup·n_dup) 자리를 찾아
    **정렬이 어디서 일어나고 인덱스가 어디서 쓰이는지** 코드로 짚어라.
  · ⭐**최소 재현을 직접 돌려라**(CPU) — 지적이 말한 「6 대신 7」을 재현하나?
    재현되면 그 코드를 적고, 안 되면 왜 안 되는지 적어라.
  · ⭐**영향 범위** — --det 를 쓴 샤드를 세라(_det 꼬리표). 그중 n_dup·E_dedup 을 가진
    샤드가 있나? 있으면 그 수를 인용하는 자리를 찾아라.` },

  { n: 9, label: 'cap', prompt: `■ 항목 9 — 상한 근접·실패를 «물리적 경로 결과» 와 구분해야 한다.

확인할 것:
  · docs/INTERPRETATION_FOLLOWUP_0909.md 의 항목 9 를 읽고 무엇을 주장하는지 정확히 옮겨라.
  · 우리가 「상한에 붙었다」·「잘렸다」를 어떻게 쓰는지 —
    benchmark/elevation_sweep_md.py:927-934 · outputs/*.json 의 n_trunc·at_path_cap ·
    거칠기 축을 접은 문장.
  · ⭐그 문장들이 「경로가 물리적으로 그만큼이다」로 읽힐 자리가 있나.
  · ⚠2026-09-09 검증의 지적 ④(반환 수 ≠ 후보 수)와 겹치나 — 겹치면 그렇게 적어라.` },

  { n: 10, label: 'physics', prompt: `■ 항목 10 — 「모든 물리 옵션」과 「물리 성분의 독립 분해」는 다르다.

확인할 것:
  · docs/INTERPRETATION_FOLLOWUP_0909.md 항목 10 을 읽어 주장을 정확히 옮겨라.
  · sb_candidate_generator.py 에서 회절 1 회 제한·확산+회절 동거 금지를 찾아 인용해라.
  · ⭐우리가 다섯 팔(R0D0E0F1 등)의 차이를 «물리 기여» 로 읽은 자리를 찾아라 —
    원장·본편·덱. 그 문장을 그대로 인용해라.
  · ⭐덱 v21 이 팔 이름을 «no bending around edges» / «with bending around edges» 로
    쓰는데, 이 항목에 비추어 그 이름이 **과한가**? 판단하고 근거를 대라.
  · ⚠2026-09-09 검증의 지적 ⑥과 겹치나 — 겹치면 그렇게 적고 **새로 더해진 것만** 적어라.` },
]

const checked = await parallel(ITEMS.map(function (c) {
  return function () {
    return agent(RULES + '\n\n' + c.prompt, { label: 'item:' + c.label, phase: 'Check', schema: CLAIM_SCHEMA })
  }
}))

const C = checked.filter(Boolean)
log('확인 ' + C.length + '/8')

const brief = C.sort(function (a, b) { return a.n - b.n }).map(function (x) {
  return `[${x.n}] ${x.verdict} — ${x.title}\n    근거: ${String(x.evidence).slice(0, 450)}\n    흔드는 것: ${String(x.what_it_breaks).slice(0, 350)}\n    고칠 자리: ${String(x.where_to_fix || '—').slice(0, 250)}\n    지적이 과한 곳: ${String(x.overreach || '—').slice(0, 250)}`
}).join('\n\n')

const JUDGE_SCHEMA = {
  type: 'object',
  properties: {
    overall: { type: 'string' },
    correct_count: { type: 'integer' },
    fixes: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          what: { type: 'string' }, where: { type: 'string' }, how: { type: 'string' },
          urgency: { type: 'string', enum: ['덱 발표 전', '이번 주', '별건'] },
          breaks_if_not: { type: 'string' },
        },
        required: ['what', 'where', 'how', 'urgency'],
      },
    },
    deck_impact: { type: 'string', description: '덱 v21 에 걸리는 것. 없으면 «없다»' },
    overreach: { type: 'string', description: '지적 중 과하거나 틀린 것 — 근거와 함께' },
    new_experiments: { type: 'string', description: '이 항목들이 요구하는 새 실험 — 다음 큐에 넣을 만한 것' },
  },
  required: ['overall', 'correct_count', 'fixes', 'deck_impact', 'overreach'],
}

phase('Judge')
const judged = await agent(RULES + `

■ 네 일 — 확인 결과를 모아 **무엇을 어떤 순서로 고칠지** 낸다.

■ 여덟 항목 확인 결과 (항목 5·6 은 부모가 이미 «맞다» 로 확인했다)
${brief}

판정할 것:
  · 전체적으로 맞나. ⛔**과하거나 틀린 것은 근거와 함께 적어라** — 지적에도 같은 잣대다.
  · 고칠 것을 «덱 발표 전 / 이번 주 / 별건» 으로 갈라라.
    ⚠팀미팅은 2026-09-14(월)이다. 덱은 v21 이 최신이다.
  · ⭐**덱 v21 에 걸리는 것**이 있나 — 지금 덱이 틀리게 말하는 것.
  · 이 항목들이 요구하는 **새 실험**이 있으면 적어라(다음 큐에 넣는다).

⛔칭찬하지 마라. 무엇이 맞고 무엇이 안 맞는지, 무엇을 고칠지만.`,
  { label: 'judge', phase: 'Judge', schema: JUDGE_SCHEMA })

return { items: C, judge: judged }
