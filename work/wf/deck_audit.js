export const meta = {
  name: 'deck-scene-provenance-audit',
  description: '0910 덱 v13 의 모든 그림이 실제로 어느 장면 자료를 쓰는지 추적하고, 말과 그림이 어긋난 곳을 찾고, 실외 절을 어떻게 재구성할지 안을 낸다',
  phases: [
    { title: 'Audit', detail: '그림마다 자료 출처 추적 · 말과 그림 어긋남 · 장면별 자료 재고' },
    { title: 'Verify', detail: '찾은 어긋남을 반증 시도로 검증' },
    { title: 'Design', detail: '실외 절 재구성안 넷을 독립으로' },
    { title: 'Judge', detail: '안을 심사하고 하나로 합친다' },
  ],
}

const RULES = `
■ 이 저장소의 상시 규약 (어기면 결과를 못 쓴다)
  ⛔말을 지어내지 않는다. 파일에서 읽은 것만 적고, 읽은 파일 경로와 줄 번호를 함께 적는다.
  ⛔확인 못 한 것은 「모른다」로 적는다. 그럴듯한 추측을 사실처럼 적지 않는다.
  ⛔「우리 커널이 맞고 솔버가 틀렸다」로 결론짓지 않는다 — 둘 다 근사다.
  ⛔덱에 우리끼리 쓰는 말을 넣지 않는다(최우선). 시험: 「우리 코드를 안 읽은 사람이
    이 말을 읽고 뜻을 아는가?」 그림 안 글자·축 이름·범례까지 같다.
  ⛔챔버(anechoic chamber)는 어디에도 넣지 않는다. 환경은 실외만.
  ⛔실기 계측 대조는 이 저장소에 0 건이다 — 「검증됐다」로 읽지 않는다.

■ 자리
  덱 폴더   /workspace/team_meeting/teammeeting_0910
  최신 판   teammeeting_slides_0910_v13.json   (11 장)
  그림 빌더 bake_window.py · bake_outdoor.py · bake_setup.py
  덱 규약   /workspace/team_meeting/DECK_CONVENTION.md · /workspace/team_meeting/CLAUDE.md
  분석 저장소 /workspace/sionna   (원장은 outputs/*.json · 샤드는 outputs/elev_sweep_shards/)
  파이썬    /workspace/.venvs/py312/bin/python   (⛔ ~/.venvs 는 없다)

■ 지금까지 확인된 사실 (다시 확인해도 좋지만 뒤집으려면 근거를 대라)
  · bake_window.py 는 env 를 전혀 안 쓴다 → 5·6·7 쪽은 빈 하늘(open sky) 자료다.
  · bake_outdoor.py 의 fig_outdoor_shipped 는 TAG="envsionna-simple_street_canyon_" 만 쓴다
    → 9 쪽은 솔버가 기본으로 주는 «거리 협곡» 자료만 쓴다.
  · 8 쪽(나눔장 «Outdoors») 의 발표자 노트는 «우리 씬»(120x120 m 콘크리트 지면 ·
    건물 넷 · 기둥 둘 · 드론 20 m)을 설명한다 — 9 쪽 그림의 장면과 다르다.
  · 3 쪽(설정 장) 은 장면 셋을 렌더로 보여준다: 우리 씬 옆모습 · 우리 씬 위에서 · 거리 협곡.
`

const AUDIT_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          slide: { type: 'integer', description: '덱 v13 의 몇 번째 장 (1 부터)' },
          figure_file: { type: 'string' },
          what: { type: 'string', description: '무엇을 찾았나 — 한 문장' },
          evidence: { type: 'string', description: '파일 경로와 줄 번호, 그리고 읽은 내용 그대로' },
          severity: { type: 'string', enum: ['blocking', 'confusing', 'minor'] },
        },
        required: ['slide', 'what', 'evidence', 'severity'],
      },
    },
    notes: { type: 'string', description: '확인 못 한 것, 열린 물음' },
  },
  required: ['findings'],
}

const LENSES = [
  {
    key: 'provenance',
    prompt: `${RULES}

■ 네 일 — 덱 v13 의 **그림마다 자료 출처를 끝까지 추적**한다.

teammeeting_slides_0910_v13.json 의 열한 장을 모두 읽고, figure_file 이 있는 장마다:
  ① 그 png 를 굽는 함수가 어느 빌더의 몇 번째 줄인지
  ② 그 함수가 읽는 자료의 «장면 표식»이 무엇인지
     (env 를 안 쓰면 빈 하늘 · envoutdoor01_ 계열이면 우리 씬 ·
      envsionna-simple_street_canyon_ 이면 솔버가 주는 거리 협곡 · envsionna-munich_ 면 뮌헨)
  ③ 팔(sw 비트)·거리·내려다보는 각도·자세 수
  ④ ⭐**어느 빌더도 굽지 않는 그림이 있으면 그것도 찾아라** — 예: f_drops_stft.png 는
     이 폴더의 빌더에 없다. 어디서 왔는지(옛 덱 폴더? git 이력?) 찾아서 그 자료의 장면을 밝혀라.
     찾으려면 git log --diff-filter=A -- 경로 나 /workspace/team_meeting 의 다른 덱 폴더를 봐라.

각 장을 findings 한 줄로 낸다 — what 에 「N 쪽 <그림> = <장면>」 을 쓰고
evidence 에 빌더 경로:줄번호와 거기 있는 표식 문자열을 그대로 적어라.
장면이 확실치 않으면 severity 를 minor 로 두고 what 에 「모른다」를 쓴다.`,
  },
  {
    key: 'mismatch',
    prompt: `${RULES}

■ 네 일 — **말과 그림이 어긋난 곳**을 전부 찾는다.

teammeeting_slides_0910_v13.json 의 열한 장에서 제목·리드(lead)·결론바(conclusion_bar)·
발표자 노트(notes_ko)가 말하는 «장면·조건»과, 그 장의 그림이 실제로 쓰는 자료의
«장면·조건»이 다른 곳을 찾아라. 빌더를 직접 읽고 대조해라.

특히 살펴라:
  · 나눔장(T5_Divider)의 노트가 설명하는 장면과, 바로 뒤 그림의 장면이 같은가
  · 리드에 적힌 거리·각도·자세 수·팔이 빌더가 실제로 읽는 값과 같은가
  · 결론바가 그 그림에서 실제로 보이는 것을 말하는가, 아니면 다른 그림 이야기인가
  · 3 쪽 설정 장이 보여주는 장면 셋 가운데, 덱 뒤쪽에서 **결과가 한 번도 안 나오는** 장면이 있는가
  · 어떤 장면을 렌더로 소개해 놓고 그 장면 결과를 안 싣는 것은 청중에게 혼란이다 — 그런 곳

evidence 에는 반드시 「덱 JSON 의 그 문장」과 「빌더 경로:줄번호의 그 값」을 나란히 적어라.`,
  },
  {
    key: 'inventory',
    prompt: `${RULES}

■ 네 일 — **장면마다 실외 자료가 얼마나 있는지 재고를 센다**.

물음: 「실외 절을 우리 씬 없이 «솔버가 주는 거리 협곡» 만으로 다 채울 수 있나?」

/workspace/sionna/outputs/elev_sweep_shards/ 의 파일 이름을 세어서 장면별 재고표를 만들어라.
파일 이름 규칙은 benchmark/elevation_sweep_md.py 의 stem 만드는 곳을 읽어서 확인해라.
장면 표식: env 없음(빈 하늘) · envoutdoor01_ · envoutdoor01_ground_ · envoutdoor01_bldg_ ·
envsionna-simple_street_canyon_ · envsionna-munich_

각 장면마다 다음을 세라:
  · 어느 내려다보는 각도(el)가 있나 — 0 · −30 · −60 · 그 밖
  · 어느 팔(sw 비트)이 있나
  · 자세 수 · 거리 · 되돌림 깊이
  · 샤드가 짝(0/1)으로 다 있나, 아니면 반쪽인가

그리고 **결론**을 findings 에 낸다:
  ① 거리 협곡만으로 9 쪽의 넉 장(빈 하늘 / 협곡 안 / 정지 성분 뺀 판 / 튄 자세 갈아끼운 판)을
     0°·30°·60° 전부에서 채울 수 있나 — 있다/없다와 빠진 칸 목록
  ② 우리 씬에만 있고 협곡에는 없는 자료가 무엇인가
     (특히 «땅만» 대 «건물만» 으로 쪼갠 판 — fig_outdoor_parts 가 쓰는 것)
  ③ 협곡에만 있고 우리 씬에 없는 것

⛔세어 보지 않고 짐작하지 마라. ls 와 grep 으로 실제 파일 이름을 세라.`,
  },
  {
    key: 'story',
    prompt: `${RULES}

■ 네 일 — **청중이 이 덱을 순서대로 보면 어디서 길을 잃는지** 찾는다.

너는 우리 코드를 한 줄도 안 읽은 팀 동료다. teammeeting_slides_0910_v13.json 의
열한 장을 1 쪽부터 순서대로 읽고(발표자 노트 포함), 다음을 표시해라:

  · 앞 장이 깔아 놓은 기대를 뒤 장이 배신하는 곳
    (예: 「이제 실외를 보겠습니다, 우리 장면은 이렇습니다」 해 놓고 다른 장면 결과가 나옴)
  · 왜 이 장이 여기 있는지 모르겠는 곳
  · 같은 것을 두 번 말하는 곳
  · 앞에서 소개한 것이 뒤에서 안 쓰이는 곳 (설정 장의 장면 셋 가운데 결과가 없는 것)
  · 우리끼리 쓰는 말이 남아 있는 곳 (제목·리드·결론바·그림 안 글자)
  · 빈 하늘 자료인데 실외처럼 읽힐 위험이 있는 곳, 또는 그 반대

⛔「좋다/나쁘다」 같은 평은 쓰지 마라. 어느 장의 어느 문장이 어느 장의 무엇과
   어긋나는지만 구체로 적어라. evidence 에 두 문장을 나란히 인용해라.`,
  },
]

phase('Audit')
log('네 관점으로 덱 v13 을 훑는다 — 출처 · 어긋남 · 재고 · 이야기 흐름')

const audits = await parallel(LENSES.map(l => () =>
  agent(l.prompt, { label: `audit:${l.key}`, phase: 'Audit', schema: AUDIT_SCHEMA })))

const all = audits.filter(Boolean).flatMap((a, i) =>
  (a.findings || []).map(f => ({ ...f, lens: LENSES[i].key })))
log(`찾은 것 ${all.length} 개 — blocking ${all.filter(f => f.severity === 'blocking').length}`)

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    holds: { type: 'boolean', description: '반증하려 했으나 못 했다 = true' },
    why: { type: 'string', description: '무엇을 직접 열어 보고 그렇게 판정했나 — 경로:줄번호' },
    corrected: { type: 'string', description: '틀렸다면 실제로는 무엇인가' },
  },
  required: ['holds', 'why'],
}

phase('Verify')
const toVerify = all.filter(f => f.severity !== 'minor')
log(`${toVerify.length} 개를 반증 시도한다`)

const verified = await parallel(toVerify.map(f => () =>
  agent(`${RULES}

■ 네 일 — 아래 주장을 **반증하려고** 해라. 기본값은 「틀렸다」다.

주장: ${f.what}
근거로 제시된 것: ${f.evidence}
(덱 ${f.slide} 쪽 · 그림 ${f.figure_file || '없음'})

파일을 **직접 열어서** 확인해라. 인용된 줄 번호가 실제로 그 내용인지, 장면 표식이
정말 그것인지, 덱 JSON 의 문장이 정말 그렇게 적혀 있는지.
확인이 안 되거나 애매하면 holds=false 로 둔다.
틀렸으면 corrected 에 실제 내용을 적어라.`,
    { label: `verify:${f.slide}:${f.lens}`, phase: 'Verify', schema: VERDICT_SCHEMA })
    .then(v => ({ ...f, verdict: v }))))

const confirmed = verified.filter(Boolean).filter(v => v.verdict && v.verdict.holds)
log(`살아남은 것 ${confirmed.length} / ${toVerify.length}`)

const brief = confirmed.map(f => `· ${f.slide} 쪽 [${f.severity}] ${f.what}\n    ${f.evidence.slice(0, 400)}`).join('\n')

const DESIGN_SCHEMA = {
  type: 'object',
  properties: {
    stance: { type: 'string', description: '한 문장으로 이 안의 입장' },
    slides: {
      type: 'array',
      description: '고친 뒤의 장 차례 — 한 줄에 한 장',
      items: {
        type: 'object',
        properties: {
          n: { type: 'integer' },
          title: { type: 'string', description: '영어 이름구 2~5 낱말. ⛔문장·판정·인과 금지' },
          figure: { type: 'string', description: '쓸 그림 파일 이름, 또는 나눔장이면 빈 문자열' },
          scene: { type: 'string', description: '이 장이 쓰는 장면 — 빈 하늘 / 우리 씬 / 거리 협곡 / 없음' },
          change: { type: 'string', enum: ['그대로', '고침', '새로', '뺌'] },
          why: { type: 'string' },
        },
        required: ['n', 'title', 'scene', 'change', 'why'],
      },
    },
    drops_our_scene: { type: 'boolean', description: '우리 씬을 덱에서 아예 빼는가' },
    risks: { type: 'string', description: '이 안이 틀릴 수 있는 지점 · 청중이 물을 것' },
    new_figures_needed: { type: 'string', description: '새로 구워야 하는 그림이 있으면 무엇을 어떻게' },
  },
  required: ['stance', 'slides', 'drops_our_scene', 'risks'],
}

const ANGLES = [
  {
    key: 'drop-ours',
    prompt: `사용자가 낸 안을 **가장 세게 밀어라**: 「거리 협곡으로 실험을 돌렸으면
우리 씬은 아예 무시하고 협곡 결과만 실으면 되지 않나?」
이 안대로 덱을 다시 짜라. 우리 씬을 3 쪽 설정 장의 렌더에서도 뺄지, 남길지도 정해라.
⭐재고표(inventory 관점의 findings)를 근거로 «협곡만으로 다 채워지는가»를 반드시 따져라.
못 채우는 칸이 있으면 그 칸을 어떻게 할지(빼기? 새로 굽기?)까지 적어라.`,
  },
  {
    key: 'keep-both',
    prompt: `**둘 다 남기되 순서를 고치는** 안을 짜라. 지금 문제는 「우리 씬을 소개해 놓고
협곡 결과를 보여준다」는 어긋남이지, 우리 씬 자체가 쓸모없다는 것이 아닐 수 있다.
우리 씬을 남길 때만 할 수 있는 이야기가 무엇인지 찾아서(예: 땅만 대 건물만 으로 쪼갠 판),
그것이 청중에게 값이 있으면 그 자리를 만들어라. 값이 없으면 스스로 빼라.`,
  },
  {
    key: 'canyon-first',
    prompt: `**협곡을 앞에 두고 우리 씬을 각주로 내리는** 안을 짜라.
「남이 만든 장면에서도 같은 일이 난다」가 더 센 이야기라면, 그것을 본문으로 올리고
우리 씬은 「우리가 만든 장면에서도 같다」는 한 줄로만 남긴다. 그 한 줄을 어디에
어떻게 둘지(발표자 노트? 결론바? 작은 곁그림?) 구체로 정해라.`,
  },
  {
    key: 'audience',
    prompt: `**청중이 물을 것부터 거꾸로** 짜라. 이 발표를 듣는 팀 동료가 실외 절에서
낼 물음 다섯 개를 먼저 적고(예: 「그 장면은 누가 만들었나」 「우리 장면이 이상한 것 아닌가」
「그래서 실제 계측과 맞나」), 그 물음이 슬라이드 순서만으로 풀리도록 다시 짜라.
⛔실기 계측 대조는 0 건이다 — 「맞다」고 답하는 장을 만들지 마라.`,
  },
]

phase('Design')
log('실외 절 재구성안 넷을 독립으로 낸다')

const designs = await parallel(ANGLES.map(a => () =>
  agent(`${RULES}

■ 지금 덱 v13 의 차례 (11 장)
  1 표지 · 2 Sudden drops at 0° (RECAP, 그림 f_drops_stft) · 3 How the runs are set up (f_setup)
  4 나눔장 «The same echo, listed twice» · 5 Same aspect, 0.2° apart (f_window_stft)
  6 How far off before it stops (f_window_ladder) · 7 Forty times more rays (f_window_rays)
  8 나눔장 «Outdoors» · 9 Outdoors, in a scene we did not build (f_outdoor_shipped)
  10 Open questions · 11 Next week

■ 검증을 통과한 어긋남
${brief || '(없음)'}

■ 이미 구워져 있는 실외 그림들 (bake_outdoor.py)
  f_outdoor_stft    빈 하늘 / 실외 / 정지 성분 뺀 판 / 튄 자세 갈아끼운 판 — 우리 씬(envoutdoor01_)
  f_outdoor_parts   땅만 vs 건물만 — 우리 씬
  f_outdoor_scenes  우리 씬 · 거리 협곡 · 뮌헨 셋을 나란히
  f_outdoor_defect  우리 씬 vs 거리 협곡, 둘 다 땅을 넣은 판
  f_outdoor_shipped 거리 협곡만 — 지금 9 쪽이 쓰는 것
  (⛔이 목록의 장면 표식은 bake_outdoor.py 를 직접 열어 다시 확인해라)

■ 네 각도
${a.prompt}

■ 내는 것
  고친 뒤의 **전체 차례**를 slides 로 낸다(11 장이 아니어도 된다 — 늘려도 줄여도 된다).
  제목은 규약대로 «이름»이지 «설명»이 아니다 — 명사구 2~5 낱말, 문장·판정·인과 금지.
  각 장에 어느 장면 자료를 쓰는지 반드시 밝혀라.
  ⛔청중이 이해 못 할 우리끼리 쓰는 말을 제목·리드에 쓰지 마라.`,
    { label: `design:${a.key}`, phase: 'Design', schema: DESIGN_SCHEMA })))

phase('Judge')
const good = designs.filter(Boolean)
log(`${good.length} 안을 심사한다`)

const JUDGE_SCHEMA = {
  type: 'object',
  properties: {
    ranking: { type: 'array', items: { type: 'string' }, description: '안 이름을 좋은 순으로' },
    winner: { type: 'string' },
    why: { type: 'string' },
    graft: { type: 'string', description: '진 안에서 반드시 가져와야 할 것' },
    final_slides: {
      type: 'array',
      description: '합친 최종 차례',
      items: {
        type: 'object',
        properties: {
          n: { type: 'integer' },
          title: { type: 'string' },
          figure: { type: 'string' },
          scene: { type: 'string' },
          change: { type: 'string' },
          why: { type: 'string' },
        },
        required: ['n', 'title', 'scene', 'change', 'why'],
      },
    },
    answer_to_user: {
      type: 'string',
      description: '사용자의 물음 셋에 대한 곧은 답 — ① 4~7 쪽은 빈 하늘인가 ② 8~9 쪽은 3 쪽 그림의 장면인가 ③ 우리 씬을 빼고 협곡만 실으면 되는가. 한국어로, 근거와 함께.',
    },
    open_risks: { type: 'string' },
  },
  required: ['ranking', 'winner', 'why', 'final_slides', 'answer_to_user'],
}

const packet = good.map((d, i) => `
════ 안 «${ANGLES[i].key}» ════
입장: ${d.stance}
우리 씬을 빼는가: ${d.drops_our_scene}
차례:
${(d.slides || []).map(s => `  ${s.n}. ${s.title} [${s.scene}] (${s.change}) — ${s.why}`).join('\n')}
위험: ${d.risks}
새로 구울 그림: ${d.new_figures_needed || '없음'}`).join('\n')

const judges = await parallel(['엄격', '청중', '실행'].map(lens => () =>
  agent(`${RULES}

■ 네 일 — 실외 절 재구성안 넷을 «${lens}» 관점으로 심사하고 하나로 합쳐라.

  엄격 = 사실 뒷받침과 과잉 결론을 본다. 근거 없는 장은 떨어뜨린다.
  청중 = 우리 코드를 안 읽은 동료가 순서대로 보고 이해되는지만 본다.
  실행 = 목요일(2026-09-10)까지 실제로 구울 수 있는지, 새 그림이 몇 장 필요한지 본다.

■ 검증을 통과한 어긋남
${brief || '(없음)'}

■ 안 넷
${packet}

■ 반드시 답할 것 — 사용자가 낸 물음 셋 (answer_to_user 에 한국어로)
  ① 「4~7 쪽 내용은 빈 하늘(open sky) 에서 돌린 것 아니냐」
  ② 「8~9 쪽 결과는 3 쪽 그림에 나온 장면이 맞느냐」
  ③ 「거리 협곡으로 돌렸으면 우리 씬은 아예 빼고 저것만 실으면 되지 않느냐」
  ⛔짐작하지 말고 빌더와 덱 JSON 을 직접 열어 확인한 것만 답해라.`,
    { label: `judge:${lens}`, phase: 'Judge', schema: JUDGE_SCHEMA })))

return {
  audit_findings: all,
  confirmed_mismatches: confirmed.map(f => ({
    slide: f.slide, severity: f.severity, what: f.what,
    evidence: f.evidence, lens: f.lens, verify_why: f.verdict.why })),
  refuted: verified.filter(Boolean).filter(v => v.verdict && !v.verdict.holds)
    .map(v => ({ slide: v.slide, what: v.what, corrected: v.verdict.corrected })),
  designs: good.map((d, i) => ({ key: ANGLES[i].key, ...d })),
  judgements: judges.filter(Boolean),
}
