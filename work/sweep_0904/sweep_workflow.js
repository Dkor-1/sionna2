export const meta = {
  name: 'sweep-wave1-published',
  description: '발행면(docs·reports·atlas·루트)과 한 번도 조사 안 한 곳을 한 줄씩 전수로 훑어 과잉 결론을 찾는다',
  phases: [
    { title: 'Read', detail: '샤드마다 한 줄씩 읽어 후보를 뽑는다' },
    { title: 'Verify', detail: '후보마다 원본을 열어 맥락을 보고 진위를 가린다' },
  ],
}

// 샤드 폴더 — args.dir 로 넘기면 그것을, 아니면 저장소 안 기본 자리를 쓴다.
// ⭐세션 스크래치패드(/tmp)는 세션이 끝나면 사라진다. 기본을 저장소 안으로 둔다.
const DIR = args.dir || '/workspace/sionna/work/sweep_0904/shards'
const ROOT = '/workspace/sionna'
const IDS = []
for (const r of args.ranges) for (let i = r[0]; i <= r[1]; i++) IDS.push(i)
const pad = (n) => String(n).padStart(4, '0')

const ALREADY_FIXED = `
⛔이미 2026-09-04 에 고친 것들이다. 다시 보고하지 마라(고친 문장이 보이면 통과):
· 조각 79 의 0.17/29.64/28.11 dB → 원장 계산(−0.78/30.79/20.87)
· 조각 80 제목 «스톡 PathSolver 0.81~96.17 %» → 물리 끔 0.81~86.22 %
· GEOMETRY_BENCHMARK·capability_matrix 의 23.17/23.2 dB → R14 무효화 표시
· report00_evidence 49.02 dB → 철회 표시 · decision_map 배지 제거
· deck_facts F23 «36회 나온다 — 전혀 없다» · F27 영문 claim 의 23.17 dB
· 리포트 12 «마이크로도플러 전부가 62 dB 아래» → el −30° · 8,118 자세
· build_volumes 12권 서사 → el −30° 한 칸
· FLEET_VALIDATION «아무도 한 적이 없다» → 아카이브 218편 범위
· REBUILD «실측 논문은 Pfa 통제 불가능» → 내림 · «0.201 dB» → div=16/12 병기
· STANDARD_FRAME 판독 47 m → 40~280 m 규약 의존
· ENGINE_VALIDATION 6 GHz 위 기울기 «측정 구간 안» → 대조 불가
· MESH_METHOD CHORD_MAX_OVER_R «중간값» → 근거 없음
· REPORTS_VOLUMES 11권/8편/23파일/87편 → 13권/7편/33파일
· NEXT_EXPERIMENTS 86.6→32.4 % · 리듬 몫 밴드 → R29/철회 표시
· DEEP_DROP 머리 두 줄 · p99 15.2 · 하네스 무죄 범위
· SIONNA_NONDETERMINISM 계단(2/3) 판정 → 자세의 성질
· GATES_0902 «az 0 이 가장 깨끗» → 단조롭지 않다(45°=15)
· CLAUDE.md 낙차·재실행·6/6 비트동일(2판씩)·빗각 신호 단서
· 편 제목 32·07·27·39 · 편 53 «운용 형상» → 실내 통제 기하
· atlas 대문 «팔 256·칸 830 · 전부 구워» → 445/1433 · 기준 명시
· A_atlas «권 번호 체계 밖» → A 권 등록됨 · 00_since_deck «리듬 90 %» → R29
· RESUME_0731 «23.17 dB ← 200배» → R14 철회 표시
· 지어낸 말 「벌」 → 「같은 줄이 적히는 횟수」
`

const RULES = `
너는 /workspace/sionna 레포지토리에서 **함부로 결론짓거나 오해의 소지가 있는 표현**을 찾는다.
이 저장소는 드론 마이크로도플러 레이다 시뮬레이션 연구다(Sionna RT · 자체 SBR+PO 커널).

■ 이 저장소가 스스로 정한 규약 (docs/CLAIM_GATE.md · CLAUDE.md · docs/REBUILD_2026-07-30.md §5)
  ⓐ 사실 뒷받침 — 이 숫자가 **물리**의 성질인가 **측정 설정**의 성질인가.
     (포화값 · 끊긴 훑기 · 탐색 바닥 · 퇴화한 분모 · 창/칸 폭 · 산포 미만 · 원장 없음 · 낡음)
  ⓑ 과잉 결론 — 이건 내가 **본** 것인가 **추론한** 것인가.
  ⓒ 상시 규약 — 「우리 커널이 맞고 PathSolver 가 틀렸다」로 결론짓지 않는다(둘 다 근사이고
     현실성 판정은 실측 몫인데 실측 대조는 0 건이다). 환경은 실외만(챔버 수는 인용 금지).
     말을 지어내지 않는다. 확산은 항상 켠다. 리듬 몫 절대값은 자유 파라미터(창 반폭 hw ·
     f_above)를 타므로 **크기를 인용하지 않는다**(RETRACTION_LOG R29).

■ 찾을 것 여덟 가지 — 이것만 본다
  ① 판정형·최상급: 「가장 ~다」 「A 가 아니라 B 다」 「X 가 Y 를 덮는다/묻는다/일으킨다」
     「~만 할 수 있다」 「~는 불가능하다」 — 근거가 그만큼 세지 않은데 쓴 것
  ② 범위 없는 절대수: dB·%·배·m 수치에 기체·거리·앙각·판·밴드·표본 중 **아무것도** 안 붙음
  ③ 부재증명: 「아무도 ~없다」 「처음 낸」 「기존/대부분은 못 한다」 에 코퍼스 범위가 없음
  ④ 철회된 값의 재인용: docs/RETRACTION_LOG.md 가 내린 값을 표시 없이 다시 씀
  ⑤ 추론을 관측처럼: 안 본 것을 본 것처럼 「~이다」로 단정
  ⑥ 지어낸 말: 청중이 모를 조어를 그 자리에서 안 풀고 씀
  ⑦ 자기모순: 같은 파일/문단에서 두 수·두 판정이 어긋남
  ⑧ 표본·범위 누락: 한 칸·한 자세·한 밴드에서 잰 것을 조건 없이 일반화

■ ⛔보고하지 말 것
  · 말투·오타·문체(뜻이 안 바뀌면 뺀다)
  · 같은 문단에 이미 ⛔·「철회」·「무효화」·「인용 금지」 표시가 붙은 것
  · 스스로 「⚠」로 한계를 충분히 밝힌 문장
  · 질문·계획·할 일·가설 목록(주장이 아니다) · 원장의 순수 수치 배열
  · 감사·적대검증 문서가 그 수를 «비판 대상» 으로 인용하는 자리
${ALREADY_FIXED}
`

const FINDING_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string', description: '레포 상대 경로 — 샤드의 ### 줄에 적힌 그대로' },
          line: { type: 'string', description: '샤드에 붙은 줄 번호 (노트북은 c<셀>:<줄>)' },
          quote: { type: 'string', description: '문제 문장 원문 그대로, 최대 200자' },
          kind: { type: 'string', description: '①~⑧ 중 번호와 이름' },
          why: { type: 'string', description: '왜 과잉인가 — 무엇이 빠졌는지 구체적으로' },
          fix: { type: 'string', description: '어떻게 고치면 되는가 — 대체 문장 제안' },
          severity: { type: 'string', enum: ['틀린 수가 인용된다', '발표에 걸린다', '오해를 부른다', '작다'] },
        },
        required: ['file', 'line', 'quote', 'kind', 'why', 'fix', 'severity'],
      },
    },
    lines_read: { type: 'number' },
    files_covered: { type: 'number' },
  },
  required: ['findings', 'lines_read', 'files_covered'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          line: { type: 'string' },
          quote: { type: 'string' },
          real: { type: 'boolean', description: '진짜 과잉인가. 의심스러우면 false' },
          reason: { type: 'string' },
          kind: { type: 'string' },
          why: { type: 'string' },
          fix: { type: 'string' },
          severity: { type: 'string' },
          builder: { type: 'string', description: '이 글을 만드는 빌더 경로. 없으면 "없음(수기)"' },
        },
        required: ['file', 'line', 'quote', 'real', 'reason', 'kind', 'why', 'fix', 'severity', 'builder'],
      },
    },
  },
  required: ['verdicts'],
}

log(`${IDS.length} 샤드 — 발행면(docs·reports·atlas·루트) + 한 번도 조사 안 한 곳`)

const results = await pipeline(
  IDS,
  (id) => agent(
    `${RULES}

■ 네 일
Read 로 \`${DIR}/${'PADME'}\` 를 **끝까지 전부** 읽어라. 파일이 길면 offset/limit 으로 나눠
여러 번 읽되 **한 줄도 건너뛰지 마라.** 각 줄은 \`줄번호<탭>내용\` 이고 \`### 경로\` 줄이
파일 경계다. 이 샤드는 한국어가 든 줄만 뽑아 둔 것이다.

의심스러운 줄을 찾으면 **원본 파일을 ${ROOT} 아래에서 직접 열어** 앞뒤 맥락을 확인해라 —
같은 문단에 ⛔ 표시가 이미 있는지, 다음 줄이 한계를 밝히는지. 맥락이 덮어 주면 보고하지 않는다.
숫자가 의심스러우면 Grep 으로 docs/RETRACTION_LOG.md 를 뒤져 철회됐는지 확인해라.
원장 값을 다시 계산해야 하면 Bash 로 \`CUDA_VISIBLE_DEVICES="" python3\` 를 써라.

발견이 없으면 findings 를 빈 배열로 둬라 — **없는데 만들어 내지 마라.**
lines_read·files_covered 에는 실제로 읽은 줄 수와 파일 수를 적어라.`.replace('PADME', pad(id) + '.txt'),
    { label: `읽기:${pad(id)}`, phase: 'Read', schema: FINDING_SCHEMA, effort: 'medium' }
  ),
  (r, id) => {
    if (!r || !r.findings || r.findings.length === 0) return { verdicts: [] }
    return agent(
      `${RULES}

■ 네 일 — **적대적 재검증**
아래는 다른 조사자가 샤드 ${pad(id)} 에서 올린 지적이다. 너는 이것을 **깎아내는** 쪽이다.
각 건마다 **원본 파일을 ${ROOT} 아래에서 직접 열어** 확인해라:

  · 인용문이 원문에 정말 그대로 있나 (Grep 으로 대조) → 없으면 real=false
  · 같은 문단·바로 앞뒤에 ⛔·⚠·「철회」·범위 한정어가 이미 있나 → 있으면 real=false
  · 「틀렸다」고 한 수는 원장(outputs/*.json)을 열어 **직접 다시 계산**했나
    (Bash 로 CUDA_VISIBLE_DEVICES="" python3) → 확인 못 하면 real=false
  · 그 파일이 질문·계획·감사·적대검증 문서라 그 수를 «주제» 로 다루는 자리인가 → real=false
  · 이미 고친 목록에 든 것인가 → real=false
  · **이 글을 만드는 빌더**를 찾아라 — Grep 으로 원문 조각을 src/·benchmark/ 에서 검색.
    빌더가 있으면 그 경로를, 없으면 "없음(수기)" 를 builder 에 적어라.

**의심스러우면 real=false.** 확실히 남는 것만 true 다. 살아남는 건마다 reason 에
«원본에서 무엇을 확인했는지» 를 구체적으로 적어라.

지적 목록(JSON):
${JSON.stringify(r.findings, null, 1).slice(0, 60000)}`,
      { label: `확인:${pad(id)}`, phase: 'Verify', schema: VERDICT_SCHEMA, effort: 'high' }
    )
  }
)

const ok = results.filter(Boolean)
const all = ok.flatMap((r) => (r && r.verdicts) || [])
const confirmed = all.filter((v) => v.real)
log(`후보 ${all.length}건 → 확인 ${confirmed.length}건`)

const order = { '틀린 수가 인용된다': 0, '발표에 걸린다': 1, '오해를 부른다': 2, '작다': 3 }
confirmed.sort((a, b) => (order[a.severity] ?? 9) - (order[b.severity] ?? 9))

return {
  n_shards: IDS.length,
  n_shards_returned: ok.length,
  n_candidates: all.length,
  n_confirmed: confirmed.length,
  by_severity: confirmed.reduce((m, v) => ((m[v.severity] = (m[v.severity] || 0) + 1), m), {}),
  findings: confirmed,
}
