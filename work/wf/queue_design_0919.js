export const meta = {
  name: 'queue-design-0919',
  description: '0918 다음 큐를 설계한다 — 여섯 관점이 독립으로 내고, 반증으로 거르고, 비용을 매겨 하나로 합친다',
  phases: [
    { title: 'Ground', detail: '재고와 비용을 실제로 센다' },
    { title: 'Design', detail: '여섯 관점이 독립으로 발주안을 낸다' },
    { title: 'Kill', detail: '각 안을 반증한다 — 이미 답이 있나, 상한에 붙나, 못 읽나' },
    { title: 'Merge', detail: '살아남은 것을 비용과 함께 하나의 발주서로' },
  ],
}

const RULES = `
■ 상시 규약 (어기면 그 안은 버린다)
  ⛔말을 지어내지 않는다. 파일에서 읽은 것만 쓰고 경로:줄번호를 함께 적는다.
  ⛔확인 못 한 것은 「모른다」로 적는다.
  ⛔확산(F 비트)은 **모든 팔에서 항상 켠다** — F0 계열(확산 끈 팔)은 발주하지 않는다.
  ⛔프로펠러 단독(--parts prop)은 더 이상 만들지 않는다.
  ⛔「우리 커널이 맞고 솔버가 틀렸다」로 결론짓지 않는다 — 둘 다 근사다.
  ⛔환경은 실외만. 챔버는 어디에도 넣지 않는다.
  ⛔상한이 결과를 정하면 그 축은 접는다 — 지면 거칠기(--env-scat)는 경로 상한에 붙어
    2026-09-07 에 접었다. 되살리려면 --max-paths 를 함께 올려야 하고, 그러면 시간이 폭증한다.
  ⛔실기 계측 대조는 이 저장소에 0 건이다.
  ⭐파이썬은 /workspace/.venvs/py312/bin/python (⛔ ~/.venvs 는 없다)
  ⭐CPU 로만 확인해라 — CUDA_VISIBLE_DEVICES="" · SIONNA2_ALLOW_CPU=1.
    ⛔GPU 큐가 돌고 있다. GPU 를 쓰는 명령을 내지 마라.
  ⭐dry-run 으로 파일 이름을 확인할 수 있다:
      CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1 python benchmark/elevation_sweep_md.py <줄> --dry-run

■ 자리
  분석 저장소 /workspace/sionna
  발주 생성기 runners/make_jobs_09*.py  ·  발주서 runners/jobs_09*.txt
  샤드        outputs/elev_sweep_shards/
  원장        outputs/*.json  ·  재개 지점 work/sweep_0904/RESUME_0908.md
  발주 문법   benchmark/elevation_sweep_md.py 의 argparse (⛔손잡이를 지어내지 마라 — 읽고 써라)

■ ⭐⭐지금까지 실측한 샤드 하나의 시간 (0913+0914+0917, 127 샤드)
    뮌헨            531 분   ⛔지금 결과가 아니다(아래 참조)
    거리 협곡        344 분
    우리 씬 통째      136 분
    우리 씬 땅만       63 분
    빈 하늘 30 m      40 분
    빈 하늘 15 m      35 분
    빈 하늘 60 m      27 분
    ⭐우리 커널        12 분   ← 솔버의 30 분의 1 이다. 여기에 많이 실을 수 있다.
  ⚠120 m 는 실측이 없다. 60 m 가 27 분이라 그 언저리로 어림한다.
  ⚠같은 호스트에 남들 작업이 늘 있다 — 위 수는 그 조건에서 잰 값이다.

■ ⭐오늘(2026-09-08) 새로 갈린 것 — 설계의 출발점
  ① 실외에서 8,192 자세 중 약 1 % 에서 «지면이 얹는 정적 몫» 이 사라진다.
     사라지는 것은 경로 **하나**이고 그것은 레이다 자신의 지면 되돌림이다
     (닫힌 식 |a|=(λ/4π)/(2h)·|Γ| 와 0.998 로 맞음). 기하로는 드론을 안 거친다.
  ② ⭐손잡이를 흔들어도 «걸리는 자세» 가 거의 안 옮긴다 (outputs/read_0914_0908.json ⑬):
       깊이 1 → 깊이 3        자카드 0.560 (51 개가 통째로 82 개 안에 들어간다)
       동체 ×0.5 ↔ 거칠기 0.3  자카드 0.952
       깊이 3 ↔ 거칠기 0.3     자카드 0.901
       동체 ×0.5 ↔ 동체 ×2     자카드 0.681
     그런데 **기체를 통째로 바꾸면** (phantom4 ↔ mini5pro, 둘 다 호버 5500 rpm) 0.024 다.
     ⛔matrice4e(3800 rpm)가 낀 견줌은 못 쓴다 — 자세 i 는 시각 t=i/PRF 이지 로터 각이
       아니라서(elevation_sweep_md.py:363) 회전수가 다르면 같은 번호가 다른 각이다.
     ⇒ 동체·깊이·거칠기가 아니라 **프롭·허브**가 남은 후보다. 0918 B 가 그것을 가른다.
  ③ ⛔철회 — 「우리가 만든 씬에서만 난다」는 틀렸다
     (outputs/outdoor_dip_origin_0908.json summary.RETRACTED_ours_only = true).
     문턱 없이 세면 협곡이 오히려 잦다 — 우리 씬 el−30 74(0.90 %) 대 협곡 el−30 96(1.17 %).
     협곡은 레벨이 **올라가서** 낙차 잣대에 안 잡힐 뿐이다.
  ④ ⛔뮌헨 판은 결과가 아니다 — 드론이 12.4 m 앞에서 건물에 막혔다
     (outputs/builtin_scene_diagnosis_0908.json geometry.scenes.munich.cells,
      blocked_before_drone=true, npaths 중앙 13 대 협곡 2652 · 우리 씬 1893).
     트인 자리는 드론 (−20,0,25) 인데 **그럴 손잡이가 없다** — 코드 일이지 발주 일이 아니다.
  ⑤ 정면(0°) 에서 같은 에코가 경로 목록에 2·3·4 번 적힌다. 창은 방위 0.11°와 0.12° 사이에서
     닫힌다(outputs/front_window_0906.json). 원인은 후보 생성기 안쪽이고 아직 모른다.
  ⑥ ⛔0° 의 빈 하늘 기록은 철회된 판이다 — 「되풀이」 물음에 그 짝을 쓰면 안 된다.

■ 지금 돌고 있는 큐 — runners/jobs_0918.txt (28 줄, 09-08 23:18 발주, 어림 06:45 KST 종료)
    A 8 줄  거리 협곡의 앙각 0·−15·−45·−75 채우기
    B 12 줄 프롭인가 동체인가 — --prop-scale 0.6 · --frame-scale 1.5 · 둘 다 1.5, el −60
    C 8 줄  창이 각도인가 가로 거리인가 — 120 m 에서 방위 0.012·0.017·0.10·0.12
  ⛔이 28 줄과 겹치는 것을 다시 내지 마라.

■ 목요일(2026-09-10) 팀미팅에 필요한 것
  덱은 지금 «빈 하늘에서 같은 에코가 여러 번 적힌다» + «실외에서 무늬가 묻힌다» 둘을 보인다.
  ⛔원인은 모른다고 말한다. ⛔「검증됐다」로 읽히게 하지 않는다.
`

const GROUND_SCHEMA = {
  type: 'object',
  properties: {
    inventory: { type: 'string', description: '장면·앙각·팔·거리·방위별 샤드 재고를 실제로 세어 표로' },
    gaps: { type: 'array', items: { type: 'string' }, description: '눈에 띄는 빈칸' },
    flags: { type: 'string', description: 'elevation_sweep_md.py 의 argparse 손잡이 목록 — 이름과 뜻 한 줄씩' },
    guards: { type: 'string', description: '발주를 막는 문지기들 — 어떤 조합이 SystemExit 로 죽나' },
    caveats: { type: 'string', description: '설계자가 반드시 알아야 할 함정' },
  },
  required: ['inventory', 'gaps', 'flags', 'guards'],
}

phase('Ground')
log('먼저 재고와 손잡이를 실제로 센다')

const ground = await agent(RULES + `

■ 네 일 — 설계자들이 쓸 **바닥 자료**를 만든다. 짐작 0 건, 전부 세어라.

① 재고 — outputs/elev_sweep_shards/ 의 파일 이름을 세어 표로 만들어라.
   파일 이름 규칙은 benchmark/elevation_sweep_md.py 의 stem 만드는 곳(:440~460 근처)을
   **직접 읽어** 확인해라. 장면 표식 · 앙각 · 팔(sw 비트) · 거리 · 방위 · 되돌림 깊이 ·
   광선 예산 · 자세 수 · 기체 · 동체/프레임/프롭 배율로 갈라 세라.
   ⭐«우리 커널»(engine ours / ours_free) 샤드도 따로 세라 — 오늘 38 장이 들어왔다.

② 빈칸 — 위 표에서 「대조가 한쪽으로 기울어 있다」거나 「짝이 없다」는 자리를 찾아라.

③ 손잡이 — elevation_sweep_md.py 의 argparse 를 **전부** 훑어 이름과 뜻을 한 줄씩 적어라.
   ⭐설계자가 없는 손잡이를 지어내지 않도록, 실제로 있는 것만 정확히.

④ 문지기 — 어떤 조합이 SystemExit 로 죽는지 찾아라(raise SystemExit 를 grep).
   설계안이 그 조합을 내면 발주가 통째로 죽는다.

⑤ 함정 — 경로 상한 · 세대 어긋남(n_dup 유무) · 자세 번호가 시각이라는 것 ·
   빈 하늘 짝의 세대 · 철회된 0° 기록 등, 설계자가 밟으면 안 되는 것.`,
  { label: 'ground', phase: 'Ground', schema: GROUND_SCHEMA })

const G = ground || { inventory: '(못 셈)', gaps: [], flags: '', guards: '', caveats: '' }
log('재고를 셌다 — 빈칸 ' + (G.gaps || []).length + ' 개')

const BRIEF = RULES + `

■ ⭐바닥 자료 (한 에이전트가 실제로 세어 온 것)

── 재고 ──
${String(G.inventory).slice(0, 6000)}

── 눈에 띄는 빈칸 ──
${(G.gaps || []).map(function (s) { return '  · ' + s }).join('\n')}

── 쓸 수 있는 손잡이 ──
${String(G.flags).slice(0, 4000)}

── 발주를 죽이는 문지기 ──
${String(G.guards).slice(0, 2500)}

── 함정 ──
${String(G.caveats || '').slice(0, 2500)}
`

const DESIGN_SCHEMA = {
  type: 'object',
  properties: {
    stance: { type: 'string', description: '이 안이 무엇을 노리나 — 한 문장' },
    proposals: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          question: { type: 'string', description: '이 묶음이 답하려는 물음 하나' },
          why_now: { type: 'string', description: '왜 지금인가 — 오늘 갈린 것과 어떻게 이어지나' },
          lines: { type: 'array', items: { type: 'string' }, description: '실제 발주 줄 (--shard 없이 한 조건에 한 줄)' },
          nshards: { type: 'integer', description: '샤드 나눔 수 (보통 2)' },
          cost_min_per_shard: { type: 'number', description: '위 실측표에서 고른 샤드당 어림 분' },
          reads_how: { type: 'string', description: '결과를 무엇으로 읽나 — 이미 있는 판독기인가, 새로 짜야 하나' },
          kill_condition: { type: 'string', description: '어떤 결과가 나오면 이 가설이 죽나' },
          risks: { type: 'string' },
        },
        required: ['name', 'question', 'why_now', 'lines', 'nshards', 'cost_min_per_shard', 'reads_how', 'kill_condition'],
      },
    },
    total_shard_hours: { type: 'number' },
  },
  required: ['stance', 'proposals', 'total_shard_hours'],
}

const ANGLES = [
  { key: 'cheap-deep', prompt: `⭐**우리 커널이 싸다**는 것을 최대로 쓴다 — 샤드 하나 12 분이라 솔버의 30 분의 1 이다.
지금까지 우리 커널은 실외를 오늘 처음 돌았다(0915 A, 38 장). 우리 커널로만 할 수 있는
촘촘한 축을 설계해라 — 앙각을 조밀하게, 거리를 사다리로, 방위를 촘촘하게.
⛔다만 우리 커널의 «지면» 은 거울상이지 메쉬가 아니다 — 그 한정을 물음마다 적어라.
⛔우리 커널 결과를 솔버와 절대 레벨로 견주지 마라.` },
  { key: 'rotor', prompt: `0918 B 가 «프롭인가 동체인가» 를 el −60 한 자리에서만 묻는다.
그 답이 어느 쪽으로 나오든 **다음에 무엇을 물어야 하는지**를 미리 설계해라 — 두 갈래 다.
  · 프롭이 정한다로 나오면 → 무엇을 더 흔드나(날개 수? 회전수? 허브 간격?)
  · 동체도 프롭도 아니면 → 남은 것이 무엇인가
⭐손잡이가 실제로 있는지 argparse 에서 확인하고 써라. 없으면 「손잡이가 없다」로 적어라.` },
  { key: 'scene-fair', prompt: `⛔「우리 씬에서만 난다」는 철회됐다. 그런데 지금 재고는 우리 씬 199 장 대 협곡 8 장으로
크게 기울어 있어, 두 씬을 나란히 놓는 말을 할 때마다 한쪽만 촘촘하다.
**두 씬을 공정하게 견줄 수 있는 최소 격자**를 설계해라 — 같은 앙각·같은 팔·같은 거리로.
0918 A 가 협곡 앙각 넷을 채우고 있으니 그다음에 무엇이 필요한지.
⚠협곡 샤드는 344 분이다 — 비싸다. 값어치 있는 칸만 골라라.` },
  { key: 'window', prompt: `«같은 에코가 여러 번 적힌다» 쪽을 판다. 지금 아는 것: 정면 0° 에서 2·3·4 번,
창은 방위 0.11~0.12° 에서 닫힌다, 광선 예산·거리·씨앗·해시 통 수를 흔들어도 배수가 안 변한다.
0918 C 가 «각도인가 가로 거리인가» 를 120 m 에서 묻는다.
그 밖에 **아직 안 흔들어 본 축**을 찾아 설계해라 — argparse 를 훑어 후보를 고르고,
docs/DEEP_DROP_0902.md 를 읽어 이미 흔든 것을 빼라.
⛔이미 흔든 축을 다시 내면 그 줄은 버려진다.` },
  { key: 'deck', prompt: `**목요일 덱이 실제로 못 말하는 것**부터 거꾸로 설계해라.
덱을 읽고(/workspace/team_meeting/teammeeting_0910/teammeeting_slides_0910_v13.json)
「이 문장을 하려면 어떤 칸이 필요한데 지금 없다」를 찾아라.
⚠목요일까지 시간이 얼마 없다 — 샤드 344 분짜리는 하나도 못 쓸 수 있다.
  **오늘 밤 안에 끝나는 것**만 골라라(실측표를 보고 계산해서 적어라).` },
  { key: 'negative', prompt: `**우리가 틀렸을 경우**를 찾는 설계를 해라. 지금 이야기 전체가
「솔버가 어떤 자세에서 경로 하나를 놓친다」에 기대고 있다.
그 이야기를 **깨뜨릴** 실험을 설계해라 —
  · 우리 하네스 쪽 문제일 가능성을 재는 칸
  · 자세 번호가 시각이라는 성질이 만들어 내는 착시를 재는 칸(PRF 를 바꿔 본다든지)
  · 같은 조건을 씨앗만 바꿔 되풀이하는 칸
⭐--prf 손잡이가 실제로 있는지 확인하고, 있으면 그것이 무엇을 바꾸는지 코드에서 읽어라.
⛔「우리가 맞다」를 확인하는 실험은 내지 마라 — 깨는 실험만.` },
]

phase('Design')
log('여섯 관점이 독립으로 발주안을 낸다')

const designs = await parallel(ANGLES.map(function (a) {
  return function () {
    return agent(BRIEF + '\n\n■ 네 각도\n' + a.prompt +
      '\n\n■ 내는 것\n  묶음 2~5 개. 묶음마다 물음 하나 · 실제 발주 줄 · 어림 비용 · 읽는 법 · 죽는 조건.\n' +
      '  ⛔발주 줄은 elevation_sweep_md.py 가 실제로 받는 문법이어야 한다 — dry-run 으로 한 줄이라도 확인해라.\n' +
      '  ⛔0918 의 28 줄과 겹치지 마라.',
      { label: 'design:' + a.key, phase: 'Design', schema: DESIGN_SCHEMA })
  }
}))

const props = designs.filter(Boolean).flatMap(function (d, i) {
  return (d.proposals || []).map(function (p) { return Object.assign({ angle: ANGLES[i].key }, p) })
})
log('안 ' + props.length + ' 개 — 반증으로 거른다')

const KILL_SCHEMA = {
  type: 'object',
  properties: {
    survives: { type: 'boolean' },
    why: { type: 'string', description: '무엇을 직접 열어 보고 그렇게 판정했나 — 경로:줄번호' },
    already_answered: { type: 'string', description: '이미 답이 있으면 어디에' },
    would_die: { type: 'string', description: '문지기·상한·세대 어긋남으로 죽으면 어떻게' },
    fixed_lines: { type: 'array', items: { type: 'string' }, description: '살릴 수 있으면 고친 발주 줄' },
  },
  required: ['survives', 'why'],
}

phase('Kill')
const killed = await parallel(props.map(function (p) {
  return function () {
    return agent(BRIEF + `

■ 네 일 — 아래 발주안을 **죽이려고** 해라. 기본값은 「사면 안 된다」다.

묶음: ${p.name}
물음: ${p.question}
왜 지금: ${p.why_now}
줄 (${(p.lines || []).length} 개, 샤드 ${p.nshards}):
${(p.lines || []).slice(0, 12).map(function (l) { return '  ' + l }).join('\n')}
읽는 법: ${p.reads_how}
죽는 조건: ${p.kill_condition}

죽이는 근거를 이 차례로 찾아라:
  ① **이미 답이 있나** — outputs/*.json 과 outputs/elev_sweep_shards/ 를 뒤져라.
     같은 조건 샤드가 이미 있으면 산 것이다. dry-run 으로 파일 이름을 만들어 존재를 확인해라.
  ② **문지기에 걸리나** — elevation_sweep_md.py 의 raise SystemExit 를 전부 보고 대조해라.
  ③ **읽을 수 있나** — 자세가 1,024 미만이면 빗살 하모닉 SNR 이 None 을 낸다.
     짝(빈 하늘 대조군)이 필요한데 없으면, 또는 세대가 어긋나면(n_dup 유무) 못 읽는다.
  ④ **상한에 붙나** — 거칠기·큰 씬·깊은 되돌림은 경로 상한 2,000,000 에 붙어 조용히 잘린다.
  ⑤ **비용이 값어치를 넘나** — 실측표로 계산해라. 하나에 344 분짜리가 여럿이면 그 근거를 대라.
  ⑥ **손잡이가 실제로 있나** — argparse 에 없는 이름을 쓰면 죽는다.

살릴 수 있으면 fixed_lines 에 고친 줄을 내라. 못 살리면 survives=false.
⛔애매하면 survives=false 다.`,
      { label: 'kill:' + p.name.slice(0, 20), phase: 'Kill', schema: KILL_SCHEMA })
      .then(function (v) { return Object.assign({}, p, { verdict: v }) })
  }
}))

const alive = killed.filter(Boolean).filter(function (x) { return x.verdict && x.verdict.survives })
log('살아남은 묶음 ' + alive.length + ' / ' + props.length)

const MERGE_SCHEMA = {
  type: 'object',
  properties: {
    queue_lines: { type: 'array', items: { type: 'string' }, description: '최종 발주 줄 — 샤드 나눔 **없이** 한 조건에 한 줄. 생성기가 나눈다.' },
    groups: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          question: { type: 'string' },
          why_now: { type: 'string' },
          n_lines: { type: 'integer' },
          cost_hours: { type: 'number' },
          reads_how: { type: 'string' },
          kill_condition: { type: 'string' },
          caveat: { type: 'string', description: '⛔이 묶음이 답하지 **않는** 것' },
        },
        required: ['name', 'question', 'n_lines', 'cost_hours', 'reads_how', 'kill_condition'],
      },
    },
    order_why: { type: 'string', description: '왜 이 차례인가 — 무거운 것과 가벼운 것을 어떻게 섞었나' },
    total_hours: { type: 'number', description: '샤드 나눔 포함 총 일꾼시간' },
    dropped: { type: 'string', description: '버린 안과 그 까닭' },
  },
  required: ['queue_lines', 'groups', 'order_why', 'total_hours', 'dropped'],
}

phase('Merge')
const packet = alive.map(function (p) {
  return '\n════ ' + p.name + ' (' + p.angle + ') ════\n물음: ' + p.question +
    '\n왜 지금: ' + p.why_now +
    '\n줄 ' + (p.lines || []).length + ' 개 × 샤드 ' + p.nshards + ' × ' + p.cost_min_per_shard + ' 분\n' +
    ((p.verdict.fixed_lines && p.verdict.fixed_lines.length ? p.verdict.fixed_lines : p.lines) || []).map(function (l) { return '  ' + l }).join('\n') +
    '\n읽는 법: ' + p.reads_how + '\n죽는 조건: ' + p.kill_condition +
    '\n반증이 남긴 말: ' + String(p.verdict.why).slice(0, 400)
}).join('\n')

const merged = await parallel(['값어치', '시간'].map(function (lens) {
  return function () {
    return agent(BRIEF + `

■ 네 일 — 반증을 이겨 낸 묶음들을 **하나의 발주서**로 합친다. 관점: «${lens}»
    값어치 = 물음이 얼마나 센가, 답이 무엇을 바꾸나
    시간   = 오늘 밤~내일 안에 실제로 끝나나, 목요일에 쓸 수 있나

■ 살아남은 묶음
${packet || '(없음)'}

■ 규칙
  · ⭐총량을 **60~120 일꾼시간**으로 맞춰라. 0918(28 줄·60 시간)은 얇았다 —
    이번엔 큐가 하루는 버텨야 한다.
  · ⭐**무거운 것과 가벼운 것을 섞어 차례를 짜라.** 0918 은 344 분짜리 여덟 줄이
    맨 앞에서 여덟 자리를 다 차지해 뒤가 굶었다. 그 실수를 되풀이하지 마라.
  · 묶음마다 ⛔«이 묶음이 답하지 않는 것» 을 한 줄 적어라.
  · queue_lines 는 --shard 를 **빼고** 한 조건에 한 줄로 내라.
  · ⛔0918 의 28 줄과 겹치지 마라.
  · ⛔확산은 항상 켠다 · 프로펠러 단독 없음 · 뮌헨 없음 · 거칠기 축 접은 채로.`,
      { label: 'merge:' + lens, phase: 'Merge', schema: MERGE_SCHEMA })
  }
}))

return {
  ground: G,
  n_proposals: props.length,
  n_alive: alive.length,
  killed: killed.filter(Boolean).filter(function (x) { return x.verdict && !x.verdict.survives })
    .map(function (x) { return { name: x.name, why: x.verdict.why, already: x.verdict.already_answered } }),
  alive: alive.map(function (x) {
    return {
      name: x.name, angle: x.angle, question: x.question, why_now: x.why_now,
      lines: (x.verdict.fixed_lines && x.verdict.fixed_lines.length) ? x.verdict.fixed_lines : x.lines,
      nshards: x.nshards, cost_min_per_shard: x.cost_min_per_shard,
      reads_how: x.reads_how, kill_condition: x.kill_condition,
    }
  }),
  merged: merged.filter(Boolean),
}
