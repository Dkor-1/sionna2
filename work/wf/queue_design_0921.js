export const meta = {
  name: 'queue-design-0921',
  description: '0920 다음 — 두 판 연속 90 %가 「이미 샀다」로 죽었다. 정말 안 산 축이 남았는지, 아니면 발주가 아니라 코드·판독 일인지 가른다',
  phases: [
    { title: 'Census', detail: '무엇을 이미 샀나 · 무엇이 정말 비어 있나' },
    { title: 'Design', detail: '다섯 관점 — 사는 것과 안 사는 것을 함께' },
    { title: 'Kill', detail: '반증 — 이미 답이 있나가 첫 관문' },
    { title: 'Merge', detail: '살아남은 것을 발주서와 «발주 아닌 일» 목록으로' },
  ],
}

const RULES = `
■ 상시 규약
  ⛔말을 지어내지 않는다. 파일에서 읽은 것만 쓰고 경로:줄번호를 함께 적는다.
  ⛔확인 못 한 것은 「모른다」로 적는다.
  ⛔확산(F 비트)은 모든 팔에서 항상 켠다 — F0 계열은 발주하지 않는다.
  ⛔프로펠러 단독(--parts prop)은 더 이상 만들지 않는다.
  ⛔「우리 커널이 맞고 솔버가 틀렸다」로 결론짓지 않는다.
  ⛔뮌헨은 드론이 건물에 막혀 있어 결과가 아니다 — 발주하지 않는다.
  ⛔지면 거칠기 축은 경로 상한에 붙어 접어 두었다.
  ⛔실기 계측 대조는 0 건이다.
  ⭐파이썬 /workspace/.venvs/py312/bin/python · CPU 로만 — CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1
  ⛔GPU 큐가 돌고 있다. GPU 를 쓰는 명령을 내지 마라.
  ⛔무거운 CPU 작업은 os.sched_setaffinity 로 코어를 묶어라(규약 17).

■ 자리
  /workspace/sionna — 발주서 runners/jobs_09*.txt · 샤드 outputs/elev_sweep_shards/
  원장 outputs/*.json · 재개 지점 work/sweep_0904/RESUME_0909.md
  옛 설계판 work/wf/queue_design_result.json · work/wf/queue_design_0920_result.json
    ⭐**여기에 죽은 안 44 개와 그 까닭이 전부 적혀 있다. 먼저 읽어라.**

■ ⭐⭐이 판의 출발점 — 두 판 연속 90 %가 「이미 샀다」로 죽었다
  0919 설계: 27 안 중 21 죽음   0920 설계: 25 안 중 23 죽음
  죽은 까닭의 거의 전부가 게이트 ①「이미 답이 있다」였다. 문지기·상한·손잡이는
  대체로 통과했다 — **줄이 틀린 게 아니라 물음이 이미 닫혀 있었다.**
  재고는 7,000 샤드가 넘고 앙각·거리·방위·배율·광선·기체·설정을 이미 넓게 덮는다.

  ⇒ 그러니 이 판은 **「또 무엇을 살까」로 시작하지 않는다.** 먼저 이렇게 묻는다:
     ⓐ 정말 아직 안 산 축이 남아 있나 — 있으면 무엇인가
     ⓑ 아니면 남은 값이 **사는 것이 아니라 읽는 것·고치는 것**에 있나

■ ⭐지금까지 갈린 것 (짧게)
  · 정면에서 같은 에코가 목록에 여러 번 적힌다. 깊이가 (N−1)/N 꼴이고 N 은
    기체·설정마다 다르다(1·2·3·4·8·9 를 봤다). 창은 방위 0.11°와 0.12° 사이에서 닫힌다.
  · 실외에서 자세의 약 1 %가 달라진다. 우리 씬에서는 장면 몫이 **사라지고**,
    거리 협곡에서는 **다른 값으로 갈아탄다**(같은 앙각에서 두 씬의 자세 집합은 교집합 0).
  · 걸리는 자세를 정하는 것은 프롭·허브다 — 동체는 널 안이다.
    널(광선 표본 재추출)은 0.89~0.92 다.
  ⛔⛔정정(2026-09-10) — 위 두 줄은 **낡았다.** ⛔원문은 이력이라 그대로 둔다.
    ⓐ §1① 이 말한 것은 「«걸리는 자세» 목록을 정하는 것은 **프롭·프레임 기하**다」이고,
       프레임 배율은 정적 프레임 정점 전체와 허브 위치를 **함께** 옮긴다
       (src/articulated_fast.py:141·:169) — 허브만의 몫은 **미분리**다.
    ⓑ 「동체는 널 안이다」는 **철회됐다.** 그 0.86 은 «깊이 3 ∩ 동체 ×0.5» 로 손잡이
       둘이 섞인 칸이었다. 진짜 동체 짝은 ×0.5=0.9524 · ×2=0.6809 이고, ×2 는
       82 중 **18 개**를 바꾼다(RESUME_0910.md §4 · outputs/read_bodyladder_0910.json).
    ⓒ 「광선 표본 재추출 = 널」도 **아니다.** 초기 광선은 씨앗 없는 결정적 피보나치
       격자다(sionna/rt/utils/ray_tracing.py:24-30). 같은 설정 되풀이는 자카드 1.000 이라
       확률적 널이 아예 없다. 0.89~0.92 는 「격자를 갈았을 때의 민감도」다.
  · ⛔우리 씬의 «통째» 와 «지면만» 이 사실상 같다(자세별 차이 1.8e−16~4.5e−16).
    건물 넷·기둥 둘이 15 m·앙각 −15~−60 에서 합에 안 들어온다. 왜인지 모른다.

■ ⛔여러 판이 되풀이해서 「여기서 막힌다」고 적은 것
  「가르려면 **경로 목록을 덤프**해야 하는데 아직 안 했다」 —
  outputs/scene_compare_0908.json 의 open_hypothesis_ko 를 비롯해 여러 원장에 있다.
  ⭐그것이 발주로 풀리는 일인지, 코드로 풀리는 일인지도 이 판이 가른다.

■ ⛔0919·0920 과 겹치지 마라 (runners/jobs_0919.txt · jobs_0920.txt)
`

const CENSUS_SCHEMA = {
  type: 'object',
  properties: {
    truly_empty: {
      type: 'array',
      description: '정말 아직 안 산 축 — 재고를 세어 확인한 것만',
      items: {
        type: 'object',
        properties: {
          axis: { type: 'string' },
          why_empty: { type: 'string', description: '어떻게 확인했나 — 세어 본 명령과 수' },
          worth: { type: 'string', description: '사면 무엇이 갈리나 · 안 사면 무엇을 못 하나' },
        },
        required: ['axis', 'why_empty', 'worth'],
      },
    },
    not_a_queue_job: {
      type: 'array',
      description: '발주가 아니라 코드·판독 일인 것',
      items: {
        type: 'object',
        properties: {
          what: { type: 'string' },
          why_not_queue: { type: 'string' },
          how: { type: 'string', description: '무엇을 고치거나 다시 읽으면 되나 — 파일:줄' },
          unlocks: { type: 'string', description: '그러면 무엇을 답할 수 있게 되나' },
        },
        required: ['what', 'why_not_queue', 'how', 'unlocks'],
      },
    },
    saturated: { type: 'string', description: '이미 충분히 산 축 — 더 사도 새 답이 안 나오는 것' },
  },
  required: ['truly_empty', 'not_a_queue_job'],
}

phase('Census')
log('먼저 «정말 비어 있는 축» 과 «발주가 아닌 일» 을 가른다')

const CENSUS = [
  {
    key: 'inventory',
    prompt: `■ 네 일 — **정말 아직 안 산 축**을 찾는다. 짐작 0 건, 전부 세어라.

① 재고를 축별로 세라 — outputs/elev_sweep_shards/ 의 이름을 정규식으로 풀어서.
   이름 규칙은 benchmark/elevation_sweep_md.py 의 stem 만드는 곳을 직접 읽어라.
② argparse 의 손잡이를 **전부** 훑어, 각 손잡이가 재고에서 **몇 가지 값**으로 굽혔는지 세라.
   ⭐값이 1 가지(=기본값만)인 손잡이가 「안 산 축」의 후보다.
③ 그 후보마다 «사면 무엇이 갈리나» 를 적어라. 갈리는 게 없으면 후보에서 빼라.
④ ⛔0919·0920 발주서에 이미 들어간 것은 빼라.
⑤ 옛 설계판 둘의 killed 를 읽고, 거기서 「이미 샀다」로 죽은 축도 빼라.

⛔「살 수 있다」가 아니라 「사면 무엇이 갈린다」로 판단해라.`,
  },
  {
    key: 'reading',
    prompt: `■ 네 일 — **사는 것이 아니라 읽는 것**으로 풀리는 물음을 찾는다.

⭐알려진 것: 재고의 89 %는 «같은 에코가 몇 번 적혔나»(n_dup) 열쇠가 없고,
  96 %는 «경로가 상한에 잘렸나»(n_trunc) 열쇠가 없다. 그래서 이미 가진 샤드로도
  못 답하는 물음이 있다.

① 지금 **이미 가진 샤드**로 답할 수 있는데 아직 안 읽은 물음을 찾아라.
   outputs/*.json 원장을 훑어 「아직 안 읽었다 · 다음에 읽는다」로 남은 것을 모아라.
② 열쇠(n_dup·n_trunc·E_dedup)가 없어 막힌 물음이 있으면, **그 물음 하나에 필요한
   최소 칸**만 --overwrite 로 다시 굽는 목록을 만들어라. ⛔전부 다시 굽지 마라.
   ⭐--overwrite 가 실제로 어떻게 도는지 코드에서 읽고 써라.
③ 판독기(benchmark/read_*.py)들이 이미 있는데 안 돌린 칸이 있나.

not_a_queue_job 에 «읽는 일» 을, truly_empty 에 «다시 구워야 하는 최소 칸» 을 적어라.`,
  },
  {
    key: 'code',
    prompt: `■ 네 일 — **발주가 아니라 코드 일**인 것을 찾는다.

여러 원장이 되풀이해서 「여기서 막힌다」고 적어 두었다. 그것들을 모아라.

① ⭐**경로 목록 덤프** — 여러 판이 「가르려면 경로 목록을 덤프해야 한다」로 멈춰 있다.
   그런 코드가 이미 있나(benchmark/ 를 뒤져라 — elephant_id_0903.py 같은 것)?
   있으면 왜 다시 안 돌리나. 없으면 무엇을 쓰면 되나.
   ⭐이것이 「솔버가 왜 그 경로를 못 찾나」에 답할 수 있는 유일한 길인지 판단해라.
② **뮌헨** — 드론이 건물에 막혀 있다. 옮길 손잡이가 argparse 에 있나? 없으면
   무엇을 고치면 되나(elevation_sweep_md.py 의 어느 줄).
③ **comb_snr 이 프롭 배율을 대역에 안 넣는다** — 어디를 고치면 되나.
   고치면 어느 칸을 읽을 수 있게 되나.
④ 그 밖에 원장이 「코드가 없어서 못 한다」로 적어 둔 것.

⛔고치지는 마라 — 무엇을 고치면 되는지만 정확히 적어라.`,
  },
]

const cen = await parallel(CENSUS.map(function (c) {
  return function () {
    return agent(RULES + '\n\n' + c.prompt, { label: 'census:' + c.key, phase: 'Census', schema: CENSUS_SCHEMA })
  }
}))

const C = cen.filter(Boolean)
const EMPTY = C.flatMap(function (x) { return x.truly_empty || [] })
const NOTQ = C.flatMap(function (x) { return x.not_a_queue_job || [] })
log('정말 빈 축 ' + EMPTY.length + ' · 발주 아닌 일 ' + NOTQ.length)

const BRIEF = RULES + `

■ ⭐인구조사 결과 (세 에이전트가 실제로 세어 온 것)

── 정말 아직 안 산 축 ──
${EMPTY.map(function (e) { return '· ' + e.axis + '\n    비었다: ' + String(e.why_empty).slice(0, 300) + '\n    값어치: ' + String(e.worth).slice(0, 300) }).join('\n')}

── 발주가 아니라 코드·판독 일 ──
${NOTQ.map(function (n) { return '· ' + n.what + '\n    왜 발주가 아닌가: ' + String(n.why_not_queue).slice(0, 250) + '\n    어떻게: ' + String(n.how).slice(0, 300) + '\n    풀리는 것: ' + String(n.unlocks).slice(0, 250) }).join('\n')}

── 이미 충분히 산 축 ──
${C.map(function (x) { return String(x.saturated || '') }).filter(Boolean).join('\n').slice(0, 1500)}
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
          lines: { type: 'array', items: { type: 'string' }, description: '발주 줄 (--shard 없이). 발주가 아닌 안이면 빈 배열' },
          nshards: { type: 'integer' },
          cost_min_per_shard: { type: 'number' },
          reads_how: { type: 'string' },
          kill_condition: { type: 'string' },
          caveat: { type: 'string' },
        },
        required: ['name', 'question', 'why_now', 'lines', 'nshards', 'cost_min_per_shard', 'reads_how', 'kill_condition'],
      },
    },
    total_shard_hours: { type: 'number' },
  },
  required: ['stance', 'proposals', 'total_shard_hours'],
}

const ANGLES = [
  { key: 'empty', prompt: `인구조사가 찾은 **정말 빈 축**만 골라 설계해라. 하나도 없으면 그렇게 적고
「살 것이 없다」를 결론으로 내라 — 억지로 만들지 마라.` },
  { key: 'reread', prompt: `⭐**다시 굽기**로만 풀리는 것을 설계해라. 이미 가진 기하를 --overwrite 로 다시 사서
열쇠(n_dup·n_trunc)를 붙이면 답할 수 있는 물음. ⛔물음 하나에 필요한 최소 칸만.` },
  { key: 'dump', prompt: `⭐**경로 목록 덤프**가 「솔버가 왜 그 경로를 못 찾나」에 답할 수 있나를 설계해라.
그 코드가 있으면 어느 칸에 돌릴지, 없으면 무엇을 쓰면 되는지. 발주 줄이 필요하면 내고,
필요 없으면 빈 배열로 두고 «코드 일» 로 적어라.` },
  { key: 'contrast', prompt: `⭐**두 씬의 사건이 성질이 다르다**(우리 씬은 사라지고 협곡은 갈아탄다,
자세 교집합 0)를 가를 실험을 설계해라. 부품으로 쪼갤 수 있는 **새 장면**이 필요한가?
씬을 만드는 코드가 있나(benchmark/make_outdoor_scene_0831.py)? 있으면 무엇을 만들면 되나.` },
  { key: 'stop', prompt: `⭐**사지 말아야 할 이유**를 찾아라. 지금 큐를 더 채우는 것이 옳은가?
두 판 연속 90 %가 「이미 샀다」로 죽었다면, 그것 자체가 신호일 수 있다.
「지금은 사지 말고 읽어라 / 고쳐라」가 답이면 그렇게 내라 — 근거와 함께.
⛔proposals 를 억지로 채우지 마라. 비워도 된다.` },
]

phase('Design')
const designs = await parallel(ANGLES.map(function (a) {
  return function () {
    return agent(BRIEF + '\n\n■ 네 각도\n' + a.prompt +
      '\n\n■ 내는 것\n  묶음 0~4 개. ⭐**0 개도 좋은 답이다** — 살 것이 없으면 그렇게 적어라.\n' +
      '  발주 줄은 dry-run 으로 한 줄이라도 확인해라. ⛔0919·0920 과 겹치지 마라.',
      { label: 'design:' + a.key, phase: 'Design', schema: DESIGN_SCHEMA })
  }
}))

const props = designs.filter(Boolean).flatMap(function (d, i) {
  return (d.proposals || []).map(function (p) { return Object.assign({ angle: ANGLES[i].key }, p) })
})
log('안 ' + props.length + ' 개')

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
줄 (${(p.lines || []).length} 개):
${(p.lines || []).slice(0, 14).map(function (l) { return '  ' + l }).join('\n') || '  (발주 줄 없음 — 코드·판독 일)'}
읽는 법: ${p.reads_how}
죽는 조건: ${p.kill_condition}

⭐**첫 관문이 가장 중요하다 — 「이미 답이 있나」.**
  두 판 연속 90 %가 여기서 죽었다. outputs/*.json 과 샤드 재고를 뒤지고,
  work/wf/queue_design_result.json · queue_design_0920_result.json 의 killed 44 개를
  읽어 같은 안의 재제출인지 확인해라.
그다음 ②문지기 ③읽을 수 있나 ④상한 ⑤비용 ⑥손잡이가 실제로 있나.

발주 줄이 없는 «코드 일» 안이면, 그 일이 **정말 코드로만 되는지**와
**그것이 무엇을 열어 주는지**를 검증해라.
⛔애매하면 survives=false 다.`,
      { label: 'kill:' + p.name.slice(0, 18), phase: 'Kill', schema: KILL_SCHEMA })
      .then(function (v) { return Object.assign({}, p, { verdict: v }) })
  }
}))

const alive = killed.filter(Boolean).filter(function (x) { return x.verdict && x.verdict.survives })
log('살아남음 ' + alive.length + ' / ' + props.length)

const MERGE_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', description: '지금 큐를 더 채워야 하나 — 「채운다」 / 「채우지 말고 읽어라」 중 하나와 그 까닭' },
    queue_lines: { type: 'array', items: { type: 'string' }, description: '살 것이 있으면 발주 줄 (--shard 없이). 없으면 빈 배열' },
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
    code_work: {
      type: 'array',
      description: '발주가 아니라 코드·판독으로 해야 하는 일 — 값어치 순',
      items: {
        type: 'object',
        properties: {
          what: { type: 'string' }, how: { type: 'string' },
          unlocks: { type: 'string' }, effort: { type: 'string' },
        },
        required: ['what', 'how', 'unlocks'],
      },
    },
    total_hours: { type: 'number' },
    dropped: { type: 'string' },
  },
  required: ['verdict', 'queue_lines', 'code_work'],
}

phase('Merge')
const packet = alive.map(function (p) {
  return '\n════ ' + p.name + ' (' + p.angle + ') ════\n물음: ' + p.question +
    '\n왜 지금: ' + String(p.why_now).slice(0, 350) +
    '\n줄 ' + (p.lines || []).length + ' 개\n' +
    ((p.verdict.fixed_lines && p.verdict.fixed_lines.length ? p.verdict.fixed_lines : p.lines) || [])
      .map(function (l) { return '  ' + l }).join('\n') +
    '\n읽는 법: ' + String(p.reads_how).slice(0, 250) +
    '\n반증이 남긴 말: ' + String(p.verdict.why).slice(0, 350)
}).join('\n')

const merged = await agent(BRIEF + `

■ 네 일 — 살아남은 것을 합치고, **먼저 판정하라**: 지금 큐를 더 채워야 하나?

■ 살아남은 묶음 (${alive.length} 개)
${packet || '(하나도 없다)'}

■ 판정 기준
  · 살아남은 발주 묶음이 없거나 값어치가 낮으면 **「채우지 말고 읽어라」**로 내라.
    그것이 정직한 답이면 그렇게 적어라 — 억지로 발주서를 만들지 마라.
  · 살 것이 있으면 queue_lines 에 내라. 총량은 **60~120 일꾼시간**.
    ⭐무거운 줄과 가벼운 줄을 섞어 차례를 짜라(0919 가 시간당 11 샤드로 가장 빨랐다).
  · code_work 에는 발주가 아닌 일을 **값어치 순**으로 적어라.
    ⭐그중 「경로 목록 덤프」가 있으면 맨 위에 두고 무엇을 어떻게 하면 되는지 구체로.

⛔확산 항상 켬 · 프로펠러 단독 없음 · 뮌헨 없음 · 거칠기 접음.
⛔0919·0920 과 겹치지 마라.`,
  { label: 'merge', phase: 'Merge', schema: MERGE_SCHEMA })

return {
  census: { truly_empty: EMPTY, not_a_queue_job: NOTQ },
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
