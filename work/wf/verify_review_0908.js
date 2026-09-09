export const meta = {
  name: 'verify-review-0908',
  description: '완료 실험 해석 검토(13 건 · 리포트 8 권)가 실제로 주장대로 되었는지 독립 검증한다 — 반영됐나 · 인용이 맞나 · 검사가 진짜 통과했나 · 새 오류를 넣지 않았나',
  phases: [
    { title: 'Verify', detail: '13 건을 하나씩 원문·본편·생성코드와 대조' },
    { title: 'Cross', detail: '검사 통과 주장 · 그림 변경 · 미해결 기록 · 새 오류 여부' },
    { title: 'Judge', detail: '전체 판정' },
  ],
}

const RULES = `
■ 상시 규약
  ⛔말을 지어내지 않는다. 파일에서 읽은 것만 쓰고 경로:줄번호를 함께 적는다.
  ⛔확인 못 한 것은 「모른다」로 적는다. 그럴듯한 추측을 사실처럼 적지 않는다.
  ⛔「우리 커널이 맞고 솔버가 틀렸다」로 결론짓지 않는다.
  ⛔실기 계측 대조는 이 저장소에 0 건이다.
  ⛔σ(dBsm) 인용 금지 · 두 엔진 절대 레벨 비교 금지.
  ⭐파이썬 /workspace/.venvs/py312/bin/python
  ⭐CPU 로만 확인해라 — CUDA_VISIBLE_DEVICES="" OPENBLAS_NUM_THREADS=1
    ⛔GPU 큐가 돌고 있다. GPU 를 쓰는 명령을 내지 마라.
  ⛔무거운 CPU 작업은 os.sched_setaffinity 로 코어를 묶어라(규약 17).
  ⛔노트북을 손으로 고치지 않는다 — 이 일은 **검증**이지 수정이 아니다. 아무것도 고치지 마라.

■ 무엇을 검증하나
  누군가 «완료 실험 결과 해석 검토» 를 하고 이렇게 보고했다:
    · 리포트 8 권에서 해석 13 건을 고쳤다
    · 빌더를 고치고 노트북·그림·목차를 다시 생성했다
    · 제목·철회 문구·각주·링크 검사를 통과했다
    · 기존 원장 3 개의 생성 경로 문제는 미해결로 기록했다
    · GPU 재실험은 수행하지 않았다

  ⛔**그 보고를 믿지 말고 확인해라.** 좋은 문서로 보인다는 것과 실제로 맞다는 것은 다르다.

■ 자리
  검토 메모   /workspace/sionna/docs/COMPLETED_INTERPRETATIONS_REVIEW_0908.md
  검토 노트북 /workspace/sionna/docs/COMPLETED_INTERPRETATIONS_REVIEW_0908.ipynb
  재현 코드   /workspace/sionna/benchmark/review_completed_interpretations_0908.py
  검산 원장   /workspace/sionna/outputs/completed_interpretations_review_0908.json
  본편        /workspace/sionna/reports/*.ipynb
  빌더        /workspace/sionna/src/build_part*.py · src/make_report*.py
  ⚠**182 개 파일이 미커밋 상태다.** git status 로 무엇이 바뀌었는지 직접 봐라.
    수정 전 상태는 git stash 없이 \`git show HEAD:<경로>\` 로 볼 수 있다.

■ 저장소 규약 (검증할 때 이 잣대를 쓴다)
  · docs/CLAIM_GATE.md — ⓐ사실 뒷받침 ⓑ과잉 결론
  · 제목은 이름이지 판정이 아니다. 「X 가 Y 를 일으킨다」는 판정이다.
  · 관측과 예측을 구분한다. 외삽을 재실험 결과로 적지 않는다.
  · 원인 단정을 하지 않는다.
`

const CLAIM_SCHEMA = {
  type: 'object',
  properties: {
    item: { type: 'integer', description: '검토 메모의 항목 번호' },
    quote_is_real: { type: 'boolean', description: '메모가 인용한 «원문» 이 수정 전 커밋에 실제로 있었나' },
    quote_evidence: { type: 'string', description: 'git show HEAD:… 로 확인한 결과 — 실제 문장과 셀 번호' },
    fix_landed: { type: 'boolean', description: '메모가 «현재 본편 반영» 이라 한 문구가 지금 노트북에 실제로 있나' },
    fix_evidence: { type: 'string', description: '어느 파일 어느 셀에서 확인했나' },
    builder_changed: { type: 'boolean', description: '메모가 가리킨 «생성 코드» 가 실제로 바뀌었나' },
    builder_evidence: { type: 'string', description: 'git diff 로 본 결과 — 줄 번호가 맞나' },
    fix_is_correct: { type: 'boolean', description: '고친 문장이 **더 정확한가** — 새 과장이나 새 오류를 넣지 않았나' },
    correctness_note: { type: 'string', description: '왜 그렇게 판단했나. 문제가 있으면 무엇이' },
    verdict: { type: 'string', enum: ['확인', '부분', '틀림', '확인불가'] },
    detail: { type: 'string' },
  },
  required: ['item', 'quote_is_real', 'fix_landed', 'builder_changed', 'fix_is_correct', 'verdict', 'detail'],
}

phase('Verify')
log('13 건을 하나씩 대조한다')

const ITEMS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]

const verified = await parallel(ITEMS.map(function (n) {
  return function () {
    return agent(RULES + `

■ 네 일 — 검토 메모의 **항목 ${n}** 하나만 끝까지 대조한다.

docs/COMPLETED_INTERPRETATIONS_REVIEW_0908.md 에서 «## ${n}.» 절을 읽어라.
그 절은 이렇게 주장한다: 원문이 이랬고 · 왜 오해인지 · 지금 본편에 이렇게 반영됐고 ·
생성 코드는 여기다.

넷을 각각 확인해라:

① **인용이 진짜인가** — «원문» 으로 적은 문장이 **수정 전** 파일에 실제로 있었나.
   \`git show HEAD:reports/<파일>.ipynb\` 로 꺼내서 그 셀을 찾아 대조해라.
   ⛔셀 번호까지 맞는지 봐라. 메모는 「파일 내부의 영 기준 번호」라고 적어 두었다.

② **고침이 실제로 들어갔나** — «현재 본편 반영» 으로 적은 문구가 **지금** 노트북에 있나.
   지금 파일(reports/<파일>.ipynb)에서 찾아라.

③ **빌더가 바뀌었나** — «생성 코드» 로 가리킨 파일:줄이 실제로 그 문장을 만드는 곳인가.
   \`git diff HEAD -- <그 파일>\` 로 무엇이 바뀌었는지 봐라. 줄 번호가 맞나.
   ⛔노트북만 바뀌고 빌더는 안 바뀌었으면 다시 구울 때 되돌아간다 — 그건 «부분» 이다.

④ ⭐**고친 문장이 더 정확한가** — 이것이 가장 중요하다.
   · 원문의 문제가 메모의 설명대로인가, 아니면 메모가 과장했나?
   · 고친 문장이 **새 과장이나 새 오류를 넣지 않았나**?
   · 「남는 결과」로 적은 것이 정말 남는가?
   · 원장 수를 인용했다면 그 수가 실제 원장에 있나 — 직접 열어 확인해라.
   ⛔메모가 스스로 「확인」이라 적었다고 확인된 것이 아니다.

verdict 는 넷이 다 맞으면 «확인», 하나라도 안 되면 «부분» 또는 «틀림»,
파일을 못 찾거나 판단 근거가 없으면 «확인불가» 다.`,
      { label: 'item:' + n, phase: 'Verify', schema: CLAIM_SCHEMA })
  }
}))

const V = verified.filter(Boolean)
log('대조 ' + V.length + '/13 — 확인 ' + V.filter(function (x) { return x.verdict === '확인' }).length)

const CROSS_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          what: { type: 'string' },
          holds: { type: 'boolean', description: '보고한 대로인가' },
          evidence: { type: 'string' },
          severity: { type: 'string', enum: ['blocking', 'concerning', 'minor', 'ok'] },
        },
        required: ['what', 'holds', 'evidence', 'severity'],
      },
    },
    detail: { type: 'string' },
  },
  required: ['findings'],
}

phase('Cross')
const CROSS = [
  {
    key: 'checks',
    prompt: `■ 네 일 — **검사가 진짜 통과했나** 확인한다.

메모는 이렇게 적었다:
  check_stale_titles 0 · check_retracted 0 · check_row_pointers 0
  check_new_file_rules 1 · check_report_links 0

① 그 검사기들을 **직접 돌려라**(CPU 로만). 메모가 적은 종료 코드와 같은가?
   메모가 적은 재현 명령도 그대로 돌려 봐라:
     CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 python benchmark/review_completed_interpretations_0908.py --check-reports
② check_new_file_rules 가 1(실패)인데 «미해결로 기록했다» 고 한다.
   실패 내용이 정말 메모가 적은 원장 3 개(deck_audit_0908 · jaccard_0914_0908 · read_0918A_0909)뿐인가?
   더 있으면 적어라.
③ ⭐그 원장 셋은 **내가(이 세션이) 만든 것**이다. 「생성 경로 누락」이 무슨 뜻인지
   docs/NEW_FILE_RULES.md 를 읽어 확인하고, 실제로 그 규칙을 어겼는지 판단해라.`,
  },
  {
    key: 'figures',
    prompt: `■ 네 일 — **그림이 왜 바뀌었나** 확인한다.

git status 에 그림 여러 장이 M(고쳐짐)으로 잡힌다 —
sigma_sens_f1~f7 · wideband_energy · ch1_nadir_residual 등.

① 어느 그림이 바뀌었는지 전부 세라.
② 각각 **왜** 바뀌었는지 빌더의 diff 로 확인해라(git diff HEAD -- <빌더>).
   메모가 말한 «범례 겹침 제거» · «그림의 값과 맞지 않는 요약» 이 실제 변경 내용인가?
③ ⭐**그림의 자료가 바뀐 것인가, 글자만 바뀐 것인가?**
   자료가 바뀌었다면 GPU 재실험 없이 어떻게 바뀌었는지 설명이 되나.
   («GPU 재실험은 수행하지 않았다» 는 보고와 어긋나지 않나)
④ 바뀐 그림을 몇 장 **Read 로 열어** 실제로 나아졌는지(겹침이 사라졌는지) 눈으로 봐라.`,
  },
  {
    key: 'scope',
    prompt: `■ 네 일 — **범위와 빠뜨림**을 확인한다.

① 메모는 리포트 8 권을 봤다고 한다. reports/ 에 몇 권이 있나? 안 본 권은 무엇인가?
   ⭐안 본 권에도 같은 종류의 문제가 있는지 **표본으로 두세 권** 훑어라.
   (관측과 예측 섞기 · 원인 단정 · 조건 빠진 거리·ADC 표현 · 취소된 검증이 제목에 남음)
② git status 의 182 개 변경 가운데 메모가 설명하지 않는 변경이 있나?
   ⭐특히 README.md · docs/REPRODUCE.md · outputs/reports_index*.json 이 왜 바뀌었나.
③ 이 변경 뭉치가 **커밋되지 않았다.** 그것이 문제인가 — 저장소 규약이 무엇을 요구하나?`,
  },
  {
    key: 'nvidia',
    prompt: `■ 네 일 — **엔비디아 기본 장면에 대한 서술**을 확인한다.

보고는 이렇게 적었다:
  「NVIDIA 기본 장면도 «문제가 없다» 로 정리하지 않았다. 협곡에서는 복소 신호 변화가
   관측되고, 뮌헨은 중심선 가림 때문에 비교 조건이 다르다. 무사건의 원인은 여전히 미확정이다.」

① 그 서술이 원장과 맞나 — outputs/outdoor_dip_origin_0908.json ·
   builtin_scene_diagnosis_0908.json · read_0918A_0909.json 를 열어 확인해라.
② ⭐**「무사건」이라는 말이 맞나.** 0918 A 판독(read_0918A_0909.json)은
   협곡의 −15°·−45° 에서 사건이 0 으로 세어지지만 그것이 **잣대의 문턱 탓**이라고
   적어 두었다(뭉치가 문턱 바로 아래에 눌려 있다). 그 한정이 반영됐나?
③ 본편 노트북에서 엔비디아 장면을 말하는 곳을 찾아, 위 한정이 실제로 적혀 있는지 봐라.
④ ⛔「우리 씬에서만 난다」가 철회됐다는 것(RETRACTED_ours_only)이 본편에 반영됐나?`,
  },
]

const cross = await parallel(CROSS.map(function (c) {
  return function () {
    return agent(RULES + '\n\n' + c.prompt, { label: 'cross:' + c.key, phase: 'Cross', schema: CROSS_SCHEMA })
  }
}))

const X = cross.filter(Boolean)
const XF = X.flatMap(function (x) { return x.findings || [] })
log('교차 확인 ' + XF.length + ' 건 — 어긋남 ' + XF.filter(function (f) { return !f.holds }).length)

const JUDGE_SCHEMA = {
  type: 'object',
  properties: {
    overall: { type: 'string', enum: ['믿을 만하다', '대체로 맞다', '부분적으로만 맞다', '못 믿는다'] },
    why: { type: 'string' },
    confirmed: { type: 'array', items: { type: 'string' }, description: '보고대로 확인된 것' },
    problems: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          what: { type: 'string' }, severity: { type: 'string' }, evidence: { type: 'string' },
        },
        required: ['what', 'severity', 'evidence'],
      },
    },
    what_to_do: { type: 'string', description: '사용자가 지금 무엇을 해야 하나 — 커밋해도 되나' },
  },
  required: ['overall', 'why', 'confirmed', 'problems', 'what_to_do'],
}

phase('Judge')
const brief = V.map(function (v) {
  return `[${v.item}] ${v.verdict} · 인용진짜 ${v.quote_is_real} · 반영 ${v.fix_landed} · 빌더 ${v.builder_changed} · 더정확 ${v.fix_is_correct}\n    ${String(v.detail).slice(0, 300)}`
}).join('\n') + '\n\n── 교차 확인 ──\n' + XF.map(function (f) {
  return `[${f.severity}] ${f.holds ? '맞다' : '⛔어긋남'} ${f.what}\n    ${String(f.evidence).slice(0, 250)}`
}).join('\n')

const judged = await agent(RULES + `

■ 네 일 — 위 검증을 모아 **전체 판정**을 내린다.

■ 항목별 대조 (13 건)
${brief}

판정할 것:
  · 보고가 주장한 것이 실제로 되었나
  · 고친 문장이 정말 더 정확한가 — 새 과장을 넣지 않았나
  · 사용자가 이 변경 뭉치를 **커밋해도 되나**, 아니면 먼저 고칠 것이 있나
  · ⛔남은 위험이 무엇인가

⛔칭찬하지 마라. 무엇이 확인됐고 무엇이 안 됐는지만 적어라.`,
  { label: 'judge', phase: 'Judge', schema: JUDGE_SCHEMA })

return { items: V, cross: X, judge: judged }
