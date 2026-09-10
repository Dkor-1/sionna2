export const meta = {
  name: 'queue-design-0922',
  description: '월요일(09-14)까지 돌릴 큐를 설계한다 — 확정된 둘(뒤쪽 반구 · 협곡 널)에 «우리 씬과 솔버 씬의 차이» 분석을 더한다',
  phases: [
    { title: 'Ground', detail: '두 씬의 차이를 무엇으로 가를 수 있나 — 손잡이와 재고' },
    { title: 'Design', detail: '다섯 관점이 씬 차이를 가를 실험을 설계' },
    { title: 'Kill', detail: '반증 — 이미 답이 있나가 첫 관문' },
    { title: 'Merge', detail: '확정 둘 + 살아남은 것을 하나의 발주서로' },
  ],
}

const RULES = `
■ 상시 규약
  ⛔말을 지어내지 않는다. 파일에서 읽은 것만 쓰고 경로:줄번호를 함께 적는다.
  ⛔확인 못 한 것은 「모른다」로 적는다.
  ⛔확산(F 비트)은 모든 팔에서 항상 켠다 — F0 계열은 발주하지 않는다.
  ⛔프로펠러 단독(--parts prop)은 더 이상 만들지 않는다.
  ⛔「우리 커널이 맞고 솔버가 틀렸다」로 결론짓지 않는다 — 둘 다 근사다.
  ⛔뮌헨은 드론이 12.4 m 앞에서 건물에 막혀 있어 결과가 아니다 — 발주하지 않는다.
  ⛔지면 거칠기 축은 경로 상한에 붙어 접어 두었다.
  ⛔상한이 결과를 정하면 그 축은 접는다 — npaths 를 먼저 본다.
  ⛔실기 계측 대조는 0 건이다.
  ⛔σ(dBsm) 인용 금지 · 두 엔진 절대 레벨 비교 금지.
  ⭐파이썬 /workspace/.venvs/py312/bin/python · CPU 로만 — CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1
  ⛔GPU 큐가 돌고 있다. GPU 를 쓰는 명령을 내지 마라.
  ⛔무거운 CPU 작업은 os.sched_setaffinity 로 코어를 묶어라(규약 17).
  ⭐dry-run 으로 이름·문지기 확인: python benchmark/elevation_sweep_md.py <줄> --dry-run

■ 자리
  /workspace/sionna — 발주서 runners/jobs_09*.txt · 샤드 outputs/elev_sweep_shards/
  원장 outputs/*.json · 재개 지점 work/sweep_0904/RESUME_0909.md
  옛 설계판 work/wf/queue_design_result.json · queue_design_0920_result.json ·
            queue_design_0921_result.json
    ⭐**죽은 안 61 개와 그 까닭이 전부 적혀 있다. 먼저 읽어라.**
    ⭐0921 판의 census.truly_empty 에 «정말 안 산 축» 여섯이 세어져 있다.

■ ⭐예산 — 월요일(2026-09-14 09:00)까지 어림 **960 일꾼시간**
  지금 도는 jobs_0920 이 먼저 ~101 시간을 쓴다. 남는 것이 **~850 일꾼시간**이다.
  ⚠어제 「사지 말고 읽어라」로 낸 판정은 **하루밖에 없다는 전제**였다. 그 전제가 바뀌었다.
  ⭐실측 샤드 시간: 거리 협곡 344 · 우리 씬 통째 136 · 우리 씬 땅만 63~75 ·
    빈 하늘 15 m 35~51 · 30 m 40~45 · 60 m 27 · 우리 커널(빈 하늘) 12 · (거울 지면) 30 분

■ ⭐이미 확정된 두 묶음 — 이 판에 **반드시 포함**한다(설계는 그 위에 얹는다)
  ① 뒤쪽 반구 방위 — 재고에 방위 90° 초과가 **0 장**이다.
     matrice4e 는 앞뒤가 대칭이 **아니다**(src/drones.py:364 rotor_deg
     52.45·131.53·228.47·307.55 · rotor_r_mm 228.77·210.36·210.36·228.77).
     좌우(az→−az)는 거울대칭이라 널이지만 앞뒤(az→180−az)는 아니다.
     ⇒ 「정면 창」이 정말 정면의 성질인가. 빈 하늘 15 m · 어림 10 일꾼시간.
  ② 거리 협곡의 널 — 협곡 샤드 24 장이 **전부 광선 4e9 하나**다(널 0 건).
     덱이 싣는 유일한 실외 장면인데 「자세의 약 1 %」가 우연인지 말할 근거가 없다.
     우리 씬의 널(0.89~0.92)은 경로 수가 달라 못 빌린다(협곡 npaths 중앙 3,678 대 2,705).
     ⇒ 광선 ±5 %(3.8e9·4.2e9) × 앙각 −30·−60. 어림 46 일꾼시간.

■ ⭐⭐이 판의 새 물음 — **우리 씬과 솔버가 주는 씬의 차이**
  사용자 지시(2026-09-09): 「우리 환경과 시오나 환경의 차이도 좀 분석을 더 해 보면 좋겠다.」

  지금까지 잰 것 (outputs/scene_compare_0908.json · read_0918A_0909.json · 내가 직접 잰 것):
   · 삼각형 수가 **똑같다** — 둘 다 74 개. 지면도 둘 다 삼각형 2 개짜리 평판.
   · 산란계수 둘 다 0(거울). ⇒ ⛔「재질이 거울이라서」·「면이 적어서」·「지면이 큰 평판이라서」
     세 가설은 **이미 죽었다**(scene_compare_0908.json killed_hypotheses_ko).
   · 지면 넓이 — 우리 120×120 m(14,400 m²) · 협곡 186.4×121.1 m(22,579 m²)
   · 건물 — 우리 넷(가로 10~16 m · 높이 9~24 m) + 기둥 둘(0.35 m · 7 m)
            협곡 여섯(가로 31×28 m · 높이 21.8~50.9 m) · 재질 다섯 가지가 섞임
   · ⭐**드론 고도가 다르다** — 우리 20 m(ENV_SPECS["outdoor01"] alt_m)
     대 솔버 씬 25 m(elevation_sweep_md.py:118 ENV_BUILTIN_ALT). **혼란 요인이다.**
   · ⭐**우리 씬의 «통째» 와 «지면만» 이 사실상 같다** — 자세별 차이 중앙값 1.8e−16~4.5e−16.
     기하로 재 보니 지면 아닌 여섯 부품이 **전부 y=0 을 안 지난다**(방위 기본값이 0 이라
     레이다도 드론도 y=0 평면 안에 있다). ⚠다만 그것이 깊이 2 의 레이다→벽→드론→레이다
     갈래가 **왜 정확히 0 인지**까지 닫는지는 확인 못 했다.
   · ⭐**사건의 성질이 다르다** — 우리 씬은 장면이 얹은 몫이 **사라지고**(|D|/|중앙D| 0.0001~0.0009),
     협곡은 **다른 값으로 갈아탄다**(0.565~2.202). 같은 앙각에서 두 씬의 걸린 자세는 교집합 0.
   · 협곡의 −15°·−45° 「사건 0」은 **잣대 문턱 탓**이다 — 뭉치가 0.346·0.436 으로
     문턱 0.5 바로 아래 눌려 있다. 문턱 0.3 이면 여섯 자리가 143·73·96·115·137·342 다.

  ⇒ 설계할 것: **무엇이 그 차이를 만드나.** 혼란 요인을 하나씩 없애는 실험을 짜라.
     ⛔이미 죽은 세 가설을 다시 내지 마라.

■ ⛔0919(끝남)·0920(도는 중)과 겹치지 마라 — runners/jobs_0919.txt · runners/jobs_0920.txt
`

const GROUND_SCHEMA = {
  type: 'object',
  properties: {
    knobs: {
      type: 'array',
      description: '두 씬의 차이를 가를 수 있는 손잡이 — argparse 에 실제로 있는 것만',
      items: {
        type: 'object',
        properties: {
          flag: { type: 'string' },
          what: { type: 'string', description: '무엇을 바꾸나 — 코드에서 읽은 대로' },
          inventory: { type: 'string', description: '재고에 몇 가지 값으로 굽혀 있나' },
          separates: { type: 'string', description: '두 씬의 어느 차이를 없애거나 흉내 내나' },
        },
        required: ['flag', 'what', 'inventory', 'separates'],
      },
    },
    scene_facts: { type: 'string', description: '두 씬을 직접 재서 나온 사실 — 메쉬·재질·자리' },
    blocked: { type: 'string', description: '손잡이가 없어 못 하는 것 — 코드 일로 남길 것' },
  },
  required: ['knobs', 'scene_facts'],
}

phase('Ground')
log('두 씬의 차이를 가를 손잡이와 재고를 센다')

const GROUNDERS = [
  {
    key: 'knobs',
    prompt: `■ 네 일 — **두 씬의 차이를 가를 손잡이**를 전부 찾는다.

① benchmark/elevation_sweep_md.py 의 argparse 를 훑어, 장면·기하와 관련된 손잡이를 모아라
   (--env · --env-alt · --env-scat · --az-deg · --range-m · --ground · --ground-alt 등).
   각각 **코드에서 무엇을 바꾸는지** 읽어라 — 도움말만 믿지 마라.
② ⭐특히 확인할 것:
   · --env-alt 가 **솔버가 주는 씬에도 걸리나** — 걸리면 드론 고도(20 대 25 m) 혼란을 없앨 수 있다.
     ⚠2026-09-08 에 「남의 씬에 안 걸린다」는 문지기를 넣은 기억이 있다. 코드에서 확인해라.
   · --az-deg 로 방위를 돌리면 **우리 씬의 건물이 y=0 평면에 들어오나** —
     assets/meshes/outdoor01/*.obj 정점을 직접 읽어 어느 방위에서 벽이 축 위에 오는지 계산해라.
   · 우리 씬을 만드는 코드가 있나(benchmark/make_outdoor_scene_0831.py) —
     건물 크기·높이·지면 넓이를 바꾼 **새 씬**을 만들 수 있나. 만들면 이름이 어떻게 나나.
③ 재고에 각 손잡이가 몇 가지 값으로 굽혀 있는지 세라.
④ ⛔argparse 에 없는 손잡이를 지어내지 마라. 없으면 blocked 에 적어라.`,
  },
  {
    key: 'meshes',
    prompt: `■ 네 일 — **두 씬을 직접 재서** 차이를 목록으로 만든다.

⛔원장을 인용만 하지 말고 메쉬를 직접 열어 재라.
  우리 씬: /workspace/sionna/assets/meshes/outdoor01/*.obj (⚠ENV_SPECS 의 이동을 반영해라)
  솔버 씬: /workspace/.venvs/py312/lib/python3.12/site-packages/sionna/rt/scenes/
           simple_street_canyon/ (xml + meshes/*.ply)

재고 볼 것:
  ① 부품마다 — 삼각형 수 · 가로세로높이 · 재질 · 산란계수
  ② ⭐레이다·드론이 있는 평면(방위 0 이면 y=0)을 **어느 부품이 지나나**
     — 우리 씬은 지면만 지난다는 관측이 있다. 협곡은 어떤가? 직접 계산해라.
  ③ ⭐드론에서 각 벽까지의 거리와, 그 벽이 만드는 **거울상 경로 길이**
     — 두 씬에서 그 길이가 얼마나 다른가.
  ④ 재질의 유전율·도전율 — 두 씬이 다른가(scene_compare_0908.json 은 「기하만 봤다」고 적어 뒀다).
     솔버의 itu-radio-material 정의를 설치본에서 읽어라.
  ⑤ 지면의 «레이다 발밑» 반사점이 두 씬에서 지면 판 안에 들어오나 — 판 크기가 다르다.

scene_facts 에 표로 적어라. ⛔짐작 0 건.`,
  },
]

const gr = await parallel(GROUNDERS.map(function (g) {
  return function () {
    return agent(RULES + '\n\n' + g.prompt, { label: 'ground:' + g.key, phase: 'Ground', schema: GROUND_SCHEMA })
  }
}))

const G = gr.filter(Boolean)
const KNOBS = G.flatMap(function (x) { return x.knobs || [] })
log('손잡이 ' + KNOBS.length + ' 개 · 씬 사실 ' + G.length + ' 벌')

const BRIEF = RULES + `

■ ⭐바닥 자료 (두 에이전트가 직접 재고 세어 온 것)

── 쓸 수 있는 손잡이 ──
${KNOBS.map(function (k) { return '· ' + k.flag + ' — ' + String(k.what).slice(0, 200) + '\n    재고: ' + String(k.inventory).slice(0, 160) + '\n    가르는 것: ' + String(k.separates).slice(0, 200) }).join('\n')}

── 두 씬을 직접 잰 것 ──
${G.map(function (x) { return String(x.scene_facts || '') }).filter(Boolean).join('\n\n').slice(0, 5000)}

── 손잡이가 없어 못 하는 것 ──
${G.map(function (x) { return String(x.blocked || '') }).filter(Boolean).join('\n').slice(0, 1500)}
`

const DESIGN_SCHEMA = {
  type: 'object',
  properties: {
    stance: { type: 'string' },
    proposals: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          question: { type: 'string' },
          why_now: { type: 'string' },
          lines: { type: 'array', items: { type: 'string' }, description: '발주 줄 (--shard 없이)' },
          nshards: { type: 'integer' },
          cost_min_per_shard: { type: 'number' },
          reads_how: { type: 'string' },
          kill_condition: { type: 'string' },
          caveat: { type: 'string', description: '⛔이 묶음이 답하지 않는 것' },
        },
        required: ['name', 'question', 'why_now', 'lines', 'nshards', 'cost_min_per_shard', 'reads_how', 'kill_condition'],
      },
    },
    total_shard_hours: { type: 'number' },
  },
  required: ['stance', 'proposals', 'total_shard_hours'],
}

const ANGLES = [
  { key: 'confound', prompt: `⭐**혼란 요인을 하나씩 없애라.** 두 씬을 견줄 때 같이 달라지는 것들 —
드론 고도(20 대 25 m) · 지면 넓이 · 건물 크기 · 건물이 축 위에 있나 · 재질.
하나만 남기고 나머지를 맞추는 실험을 설계해라. **가장 값싼 혼란 제거부터.**` },
  { key: 'azimuth', prompt: `⭐**방위를 돌려 우리 씬의 건물을 축 위로 가져와라.**
우리 씬은 방위 0 에서 지면 말고 아무것도 y=0 을 안 지나서 건물이 합에 안 들어온다.
방위를 돌리면 벽이 축 위에 온다 — 그때 우리 씬이 협곡처럼 «갈아탄다» 로 바뀌나?
⭐어느 방위에서 어느 벽이 축에 오는지 바닥 자료의 계산을 쓰고, 그 각도만 사라.` },
  { key: 'bridge', prompt: `⭐**두 씬 사이를 잇는 사다리**를 설계해라. 우리 씬을 협곡 쪽으로
한 걸음씩 옮기거나(건물을 키운다·높인다·지면을 넓힌다), 협곡을 우리 쪽으로 옮긴다.
씬을 만드는 코드가 있으면 **새 씬을 몇 개 만들** 수 있다 — 무엇을 만들면 되나.
⛔새 씬을 만드는 것은 코드 일이다. 그것도 적되, 발주 줄이 필요하면 함께 내라.` },
  { key: 'event', prompt: `⭐**사건의 «성질» 차이를 곧장 겨눠라.**
우리 씬은 장면 몫이 **사라지고**(0.0001~0.0009) 협곡은 **다른 값으로 갈아탄다**(0.565~2.202).
그 차이가 «정지 경로가 하나냐 여럿이냐» 때문이라는 가설을 시험할 실험을 설계해라.
⭐우리 씬에 정지 경로를 **늘리거나**, 협곡에서 **줄이는** 길이 있나?` },
  { key: 'deck', prompt: `**월요일 덱이 못 말하는 것**부터 거꾸로. 덱을 읽어라 —
/workspace/team_meeting/teammeeting_0910/teammeeting_slides_0910_v20.json
지금 덱은 실외 절이 협곡 하나·앙각 둘에 서 있다. 무엇을 더 사면 그 절이 세지나?
⚠**월요일까지 끝나는 것만** 골라라(실측표로 계산해서 적어라).` },
]

phase('Design')
const designs = await parallel(ANGLES.map(function (a) {
  return function () {
    return agent(BRIEF + '\n\n■ 네 각도\n' + a.prompt +
      '\n\n■ 내는 것\n  묶음 2~5 개. 묶음마다 물음 하나 · 실제 발주 줄 · 어림 비용 · 읽는 법 ·\n' +
      '  죽는 조건 · ⛔안 답하는 것.\n' +
      '  ⛔dry-run 으로 한 줄이라도 확인해라. ⛔0919·0920 과 겹치지 마라.\n' +
      '  ⛔work/wf/queue_design_*.json 의 killed 61 개를 먼저 읽고 재제출을 피해라.',
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
    why: { type: 'string' },
    already_answered: { type: 'string' },
    fixed_lines: { type: 'array', items: { type: 'string' } },
  },
  required: ['survives', 'why'],
}

phase('Kill')
const killed = await parallel(props.map(function (p) {
  return function () {
    return agent(BRIEF + `

■ 네 일 — 아래 안을 **죽이려고** 해라. 기본값은 「사면 안 된다」다.

묶음: ${p.name}
물음: ${p.question}
왜 지금: ${p.why_now}
줄 (${(p.lines || []).length} 개 × 샤드 ${p.nshards} × ${p.cost_min_per_shard} 분):
${(p.lines || []).slice(0, 14).map(function (l) { return '  ' + l }).join('\n') || '  (발주 줄 없음)'}
읽는 법: ${p.reads_how}
죽는 조건: ${p.kill_condition}

이 차례로 죽여라:
  ① ⭐**이미 답이 있나** — 세 판의 killed 61 개(work/wf/queue_design_*.json)를 먼저 읽어라.
     그다음 outputs/*.json 과 샤드 재고를 dry-run 으로 대조해라.
  ② **이미 죽은 가설의 재탕인가** — scene_compare_0908.json killed_hypotheses_ko 셋
     (재질이 거울 · 면이 적음 · 지면이 큰 평판)을 다시 사려는 것이면 죽는다.
  ③ **문지기에 걸리나** — raise SystemExit 를 전부 보고 대조해라.
  ④ **읽을 수 있나** — 짝이 있나 · 세대가 맞나(n_dup·_mfix) · 자세 1,024 이상인가.
  ⑤ **상한에 붙나** — npaths 가 2,000,000 의 99 % 를 넘나.
  ⑥ **손잡이가 실제로 있나** — argparse 에 없으면 죽는다.
  ⑦ **비용** — 예산은 넉넉하다(~850 일꾼시간). 비용만으로는 죽이지 마라.

살릴 수 있으면 fixed_lines 에 고친 줄을. ⛔애매하면 survives=false.`,
      { label: 'kill:' + p.name.slice(0, 18), phase: 'Kill', schema: KILL_SCHEMA })
      .then(function (v) { return Object.assign({}, p, { verdict: v }) })
  }
}))

const alive = killed.filter(Boolean).filter(function (x) { return x.verdict && x.verdict.survives })
log('살아남음 ' + alive.length + ' / ' + props.length)

const MERGE_SCHEMA = {
  type: 'object',
  properties: {
    queue_lines: { type: 'array', items: { type: 'string' }, description: '최종 발주 줄 — --shard 없이. ⭐확정 두 묶음을 반드시 포함' },
    groups: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' }, question: { type: 'string' },
          n_lines: { type: 'integer' }, cost_hours: { type: 'number' },
          reads_how: { type: 'string' }, kill_condition: { type: 'string' }, caveat: { type: 'string' },
        },
        required: ['name', 'question', 'n_lines', 'cost_hours', 'reads_how', 'kill_condition'],
      },
    },
    order_why: { type: 'string' },
    total_hours: { type: 'number' },
    code_work: { type: 'array', items: { type: 'string' }, description: '발주가 아니라 코드로 해야 하는 일' },
    dropped: { type: 'string' },
  },
  required: ['queue_lines', 'groups', 'order_why', 'total_hours'],
}

phase('Merge')
const packet = alive.map(function (p) {
  return '\n════ ' + p.name + ' (' + p.angle + ') ════\n물음: ' + p.question +
    '\n왜 지금: ' + String(p.why_now).slice(0, 350) +
    '\n줄 ' + (p.lines || []).length + ' × 샤드 ' + p.nshards + ' × ' + p.cost_min_per_shard + ' 분\n' +
    ((p.verdict.fixed_lines && p.verdict.fixed_lines.length ? p.verdict.fixed_lines : p.lines) || [])
      .map(function (l) { return '  ' + l }).join('\n') +
    '\n읽는 법: ' + String(p.reads_how).slice(0, 250) +
    '\n죽는 조건: ' + String(p.kill_condition).slice(0, 250) +
    (p.caveat ? '\n⛔안 답함: ' + String(p.caveat).slice(0, 200) : '')
}).join('\n')

const merged = await agent(BRIEF + `

■ 네 일 — 하나의 발주서로 합친다.

■ ⭐**반드시 포함할 확정 두 묶음** (설계 단계를 안 거친다 — 사용자가 이미 승인했다)
  ① 뒤쪽 반구 방위 — 빈 하늘 · 15 m · 팔 R0D0E0F1 · 깊이 2 · 광선 4e9 · 8,192 자세 ·
     내려다보는 각 0. 방위는 축 뒤(180°) 근처를 촘촘히 — 예: 175 · 179 · 179.9 · 180 ·
     180.1 · 181 · 185. ⭐앞쪽에서 창이 0.11~0.12° 에 닫혔으니 뒤쪽도 그 폭으로 재라.
     ⚠좌우 거울대칭(az→−az)이 널이 되는지도 함께 확인할 수 있게 음수 방위를 한둘 넣어라.
  ② 거리 협곡의 널 — --env sionna:simple_street_canyon · 광선 3.8e9 과 4.2e9 ·
     앙각 −30 과 −60 · 나머지는 기존 협곡 칸과 같게(R0D0E0F1 · r15 · d2 · n8192).
     ⭐빈 하늘 짝이 그 광선 예산에 있는지 확인하고, 없으면 그 짝도 함께 사라.

■ 살아남은 묶음 (${alive.length} 개)
${packet || '(하나도 없다)'}

■ 규칙
  · 총량 **500~800 일꾼시간** (월요일까지 ~850 이 남는다. 여유를 남긴다).
  · ⭐**무거운 줄과 가벼운 줄을 섞어 차례를 짜라** — 0919 가 그렇게 해서 시간당 11 샤드였다.
    ⛔0918 은 344 분짜리 여덟 줄을 맨 앞에 몰아 뒤가 굶었다.
  · ⭐확정 두 묶음(특히 ②)을 **앞쪽**에 둔다 — 덱에 실을 것이라 먼저 들어와야 한다.
  · 묶음마다 ⛔«이 묶음이 답하지 않는 것» 을 한 줄.
  · queue_lines 는 --shard 를 **빼고** 한 조건에 한 줄.
  · ⛔확산 항상 켬 · 프로펠러 단독 없음 · 뮌헨 없음 · 거칠기 접음 · 0919·0920 과 안 겹침.`,
  { label: 'merge', phase: 'Merge', schema: MERGE_SCHEMA })

return {
  ground: { knobs: KNOBS, scene_facts: G.map(function (x) { return x.scene_facts }) },
  n_proposals: props.length,
  n_alive: alive.length,
  killed: killed.filter(Boolean).filter(function (x) { return x.verdict && !x.verdict.survives })
    .map(function (x) { return { name: x.name, why: String(x.verdict.why).slice(0, 500) } }),
  alive: alive.map(function (x) {
    return {
      name: x.name, angle: x.angle, question: x.question, caveat: x.caveat,
      lines: (x.verdict.fixed_lines && x.verdict.fixed_lines.length) ? x.verdict.fixed_lines : x.lines,
      nshards: x.nshards, cost_min_per_shard: x.cost_min_per_shard,
      reads_how: x.reads_how, kill_condition: x.kill_condition,
    }
  }),
  merged: merged,
}
