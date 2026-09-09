export const meta = {
  name: 'queue-design-0920',
  description: '0918 이 답한 것을 먼저 읽고, 그 위에서 다음 큐(0920)를 설계한다 — 읽기 → 여섯 관점 설계 → 반증 → 합치기',
  phases: [
    { title: 'Read', detail: '0918 세 묶음과 0919 착지분이 실제로 무엇을 답했나' },
    { title: 'Design', detail: '읽은 답 위에서 여섯 관점이 독립으로' },
    { title: 'Kill', detail: '각 안을 반증한다 — 이미 답이 있나, 못 읽나, 상한에 붙나' },
    { title: 'Merge', detail: '살아남은 것을 비용과 차례를 매겨 하나로' },
  ],
}

const RULES = `
■ 상시 규약 (어기면 그 안은 버린다)
  ⛔말을 지어내지 않는다. 파일에서 읽은 것만 쓰고 경로:줄번호를 함께 적는다.
  ⛔확인 못 한 것은 「모른다」로 적는다. 그럴듯한 추측을 사실처럼 적지 않는다.
  ⛔확산(F 비트)은 **모든 팔에서 항상 켠다** — F0 계열은 발주하지 않는다.
  ⛔프로펠러 단독(--parts prop)은 더 이상 만들지 않는다.
  ⛔「우리 커널이 맞고 솔버가 틀렸다」로 결론짓지 않는다 — 둘 다 근사다.
  ⛔환경은 실외만. 챔버는 어디에도 넣지 않는다.
  ⛔뮌헨은 드론이 12.4 m 앞에서 건물에 막혀 있다 — 결과가 아니다. 발주하지 않는다
    (outputs/builtin_scene_diagnosis_0908.json geometry.scenes.munich, blocked_before_drone=true).
  ⛔지면 거칠기(--env-scat) 축은 경로 상한에 붙어 접어 두었다.
  ⛔상한이 결과를 정하면 그 축은 접는다 — npaths 를 먼저 본다.
  ⛔실기 계측 대조는 이 저장소에 0 건이다 — 「검증됐다」로 읽지 않는다.
  ⛔σ(dBsm) 인용 금지 · 두 엔진 절대 레벨 비교 금지.
  ⭐파이썬은 /workspace/.venvs/py312/bin/python (⛔ ~/.venvs 는 없다)
  ⭐CPU 로만 확인해라 — CUDA_VISIBLE_DEVICES="" · SIONNA2_ALLOW_CPU=1.
    ⛔GPU 큐가 돌고 있다. GPU 를 쓰는 명령을 내지 마라.
  ⛔무거운 CPU 작업은 os.sched_setaffinity 로 코어를 묶어라 — 규약 17.
    (OMP 변수로는 안 막힌다. 2026-09-08 에 두 번 사고를 냈다.)
  ⭐dry-run 으로 파일 이름과 문지기를 확인할 수 있다:
      CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1 python benchmark/elevation_sweep_md.py <줄> --dry-run

■ 자리
  분석 저장소 /workspace/sionna
  발주서      runners/jobs_09*.txt  ·  생성기 runners/make_jobs_09*.py
  샤드        outputs/elev_sweep_shards/   (6,984 → 오늘 더 늘었다)
  원장        outputs/*.json  ·  재개 지점 work/sweep_0904/RESUME_0908.md
  어제 설계판  work/wf/queue_design_result.json  (재고 전수 · 죽은 안 21 개의 이유)
  발주 문법   benchmark/elevation_sweep_md.py 의 argparse (⛔손잡이를 지어내지 마라)

■ ⭐실측한 샤드 하나의 시간
    뮌헨 531 · 거리 협곡 344 · 우리 씬 통째 136 · 우리 씬 땅만 63~75
    빈 하늘 15 m 35~51 · 30 m 40~45 · 60 m 27
    우리 커널(빈 하늘) 12 · ⭐우리 커널(거울 지면 --ground) 30
  ⚠같은 호스트에 남들 작업이 늘 있다. 위 수는 그 조건에서 잰 값이다.
  ⚠어제 「우리 커널 12 분」으로 설계했는데 거울 지면은 30 분이었다 — 두 배 넘게 틀렸다.

■ 지금까지 갈린 것 (2026-09-08 까지)
  ① 실외에서 8,192 자세 중 약 1 % 에서 «지면이 얹는 정적 몫» 이 사라진다. 사라지는 것은
     경로 **하나**이고 레이다 자신의 지면 되돌림이다(닫힌 식과 0.998 로 맞음).
     기하로는 드론을 안 거치는데 드론을 바꾸면 «언제» 사라지는지가 바뀐다. 원인은 모른다.
  ② 손잡이를 흔들어도 걸리는 자세가 거의 안 옮긴다 (outputs/read_0914_0908.json ⑬):
       깊이 1→3 자카드 0.560 · 동체 0.5↔거칠기 0.3 은 0.952 · 동체 0.5↔2 는 0.681
     그런데 기체를 통째로 바꾸면(같은 회전수) 0.024 다. 남은 후보가 프롭·허브다.
  ③ ⛔철회 — 「우리가 만든 씬에서만 난다」는 틀렸다
     (outputs/outdoor_dip_origin_0908.json summary.RETRACTED_ours_only=true).
     문턱 없이 세면 협곡이 오히려 잦다(우리 씬 el−30 74 = 0.90 % · 협곡 96 = 1.17 %).
  ④ 정면(0°) 에서 같은 에코가 경로 목록에 2·3·4 번 적힌다. 창은 방위 0.11°와 0.12°
     사이에서 닫힌다. 광선 예산·거리·씨앗·해시 통 수를 흔들어도 배수가 안 변한다. 원인 모름.
  ⑤ ⛔0° 의 빈 하늘 기록은 철회된 판이다 — 「되풀이」 물음에 그 짝을 쓰면 안 된다.
  ⑥ ⚠자세 번호는 «시각» t=i/PRF 이지 로터 각이 아니다(elevation_sweep_md.py:363).
     회전수가 다른 기체끼리는 같은 번호가 다른 각이라 자세 집합을 못 견준다.
  ⑦ n_dup(같은 에코가 여러 번 적힘)을 가진 샤드는 재고의 11 % 뿐이고,
     n_trunc(상한 잘림)은 4 % 뿐이다. 나머지는 그 물음에 답할 수 없다.
  ⑧ 재고가 메쉬 두 세대로 갈려 있다 — 무태그(옛) 대 _mfixbatteryi5_blperairframe(현행).
     세대를 섞어 사다리를 만들면 안 된다.

■ ⛔0918·0919 와 겹치는 것을 다시 내지 마라 (runners/jobs_0918.txt · runners/jobs_0919.txt)
  0918(28 줄, 끝남): A 협곡 앙각 0·−15·−45·−75 · B 프롭/프레임/동체 el−60 · C 창 120 m 방위 넷
  0919(180 샤드, 도는 중): 널(광선 재표본) · 우리 커널 프롭·프레임 사다리 ·
    굴절 켠 두 팔의 창 · 창의 폭(여섯 거리) · 창의 반대쪽 · 창과 표적 크기 · 다섯째 팔의 창
`

const READ_SCHEMA = {
  type: 'object',
  properties: {
    answered: {
      type: 'array',
      description: '0918·0919 가 실제로 답한 것 하나에 한 줄',
      items: {
        type: 'object',
        properties: {
          group: { type: 'string' },
          question: { type: 'string' },
          answer: { type: 'string', description: '수와 함께. ⛔못 읽었으면 「못 읽었다」와 그 까닭' },
          evidence: { type: 'string', description: '어느 샤드·어느 원장을 어떻게 읽었나' },
          opens_what: { type: 'string', description: '이 답이 새로 여는 물음' },
        },
        required: ['group', 'question', 'answer', 'evidence'],
      },
    },
    still_missing: { type: 'string', description: '아직 안 들어온 칸' },
    surprises: { type: 'string', description: '기대와 어긋난 것 · 앞의 결론을 흔드는 것' },
  },
  required: ['answered'],
}

phase('Read')
log('0918 이 답한 것을 먼저 읽는다')

const READERS = [
  {
    key: 'canyon',
    prompt: `■ 네 일 — 0918 **A 묶음(거리 협곡 앙각 채우기)** 이 무엇을 답했나 읽어라.

0918 A 는 협곡(env sionna:simple_street_canyon)을 앙각 0·−15·−45·−75 에서 굽었다
(팔 R0D0E0F1 · 15 m · 깊이 2 · 광선 4e9 · 8,192 자세 · 각 2 샤드).
이제 협곡이 앙각 여섯 자리가 됐다(원래 −30·−60 둘).

읽을 것:
  ① 그 넉 자리 샤드가 실제로 다 착지했나 — 세어 확인해라.
  ② 앙각마다 «지면·건물이 얹는 정적 몫» 이 얼마나 되나. 빈 하늘 짝과 견주어라
     (빈 하늘 짝은 el+0·el-15·el-45·el-75 에 이미 있다).
  ③ ⭐«걸리는 자세»(정적 몫이 달라진 자세) 를 앙각마다 세라.
     ⭐잣대는 benchmark/read_0914_0908.py 의 measure() 를 그대로 써라 —
       레벨 문턱을 안 쓰고 D = E_실외 − E_빈하늘 이 중앙에서 |중앙D|×0.5 넘게 벗어난 자세를 센다.
     그 파일을 읽고 같은 식으로 계산해라. ⛔새 잣대를 지어내지 마라.
  ④ 우리 씬(envoutdoor01_ground)의 같은 앙각 값과 나란히 놓아라 — 이제 공정하게 견줄 수 있나.
  ⑤ ⛔npaths 를 먼저 봐라 — 경로 상한(2,000,000)의 99 % 를 넘는 칸이 있으면 그 칸은 접는다.
     그리고 뮌헨처럼 npaths 중앙값이 수십으로 무너진 칸이 있으면 그것은 결과가 아니다.

⛔결론을 짓지 마라 — 수를 읽고 그 수가 무엇을 열고 무엇을 닫는지만 적어라.`,
  },
  {
    key: 'prop',
    prompt: `■ 네 일 — 0918 **B 묶음(프롭인가 동체인가)** 이 무엇을 답했나 읽어라.

0918 B 는 앙각 −60 에서 세 갈래를 굽었다(실외 outdoor01_ground 와 빈 하늘 짝 각각):
  · --prop-scale 0.6            (프롭만 줄인다 · 허브·동체·회전수 고정)
  · --frame-scale 1.5           (프레임만 벌린다 · 프롭 고정)
  · --prop-scale 1.5 --frame-scale 1.5  (기체를 통째로 키운다)

읽을 것:
  ① 여섯 칸이 다 착지했나.
  ② ⭐칸마다 «걸리는 자세» 를 세고, **기준선(배율 없음, el −60)과 자카드**를 내라.
     ⭐benchmark/read_0914_0908.py 의 measure() 와 ⑬ 견주기를 그대로 써라.
     기준선은 sionna_p4000000000_swR0D0E0F1_r15_n8192_envoutdoor01_ground_..._d2_el-60 이다.
  ③ 0914 가 낸 것과 나란히 놓아라 — 동체 0.5↔2 는 0.681, 깊이·거칠기는 0.86~0.95,
     기체 교체는 0.024 였다. 프롭·프레임은 어디에 서나?
  ④ ⚠--prop-scale 은 날개끝 주파수를 배율만큼 옮긴다. 빗살을 읽는다면 comb_snr 이
     _ps 를 읽어 대역을 옮기는지 확인해라(2026-09-08 에 고쳤다).
  ⑤ ⛔자카드 하나로 「프롭이 정한다」를 결론짓지 마라 — 0919 의 «널»(광선 재표본
     3.8e9·4.2e9)이 아직 안 끝났다. 널이 없으면 자카드가 큰지 작은지 말할 수 없다.
     널이 이미 착지했으면 그것도 읽어서 함께 적어라.`,
  },
  {
    key: 'window',
    prompt: `■ 네 일 — 0918 **C 묶음(창이 각도인가 가로 거리인가)** 이 무엇을 답했나 읽어라.

0918 C 는 120 m 에서 방위 0.012·0.017·0.10·0.12 를 굽었다(팔 R0D0E0F1 · el 0 · 깊이 2).
가설 둘:
  · 각도라면 — 15 m 에서 0.11↔0.12 에 닫히니 120 m 에서도 같은 각에 닫힌다
  · 가로 거리라면 — 15 m 의 0.115° ≈ 30 mm 이므로 120 m 에서는 0.0144° 에 닫힌다
120 m 에는 이미 0.01·0.02·0.05 가 있었다. 이제 일곱 점이다.

읽을 것:
  ① 넉 점이 다 착지했나.
  ② ⭐«되풀이된 줄이 있는 자세의 비율» 을 점마다 내라.
     ⭐그 잣대가 어디서 나오는지 찾아라 — outputs/front_window_0906.json 을 만든 스크립트를
       찾아 같은 식을 써라(benchmark/ 를 뒤져라). ⛔새 잣대를 지어내지 마라.
     ⚠n_dup 이 없는 샤드로는 이 물음에 답할 수 없다 — 있는지 먼저 확인해라.
  ③ 일곱 점을 늘어놓고 벼랑이 어디인지 적어라. 두 가설 중 어느 쪽인가, 아니면 둘 다 아닌가.
  ④ ⛔둘 다 아니면 그렇게 적어라 — 셋째 설명을 지어내지 마라.
  ⑤ ⚠15 m 판과 견줄 때 세대(무태그 대 _mfixbatteryi5_blperairframe)가 같은지 확인해라.`,
  },
  {
    key: 'landed',
    prompt: `■ 네 일 — **0919 에서 지금까지 착지한 것**과 재고 전체의 변화를 읽어라.

0919 는 180 샤드 가운데 절반쯤 착지했다(도는 중). 무엇이 들어왔고 무엇이 안 들어왔나.

읽을 것:
  ① outputs/elev_sweep_shards/ 에서 mtime 이 2026-09-09 인 파일을 세고,
     runners/jobs_0919.txt 의 일곱 묶음 가운데 어느 묶음이 얼마나 찼는지 갈라라.
  ② ⭐**«널» 묶음**(--spp 3800000000 · 4200000000, el −60, 땅만과 빈 하늘)이 착지했으면
     그것부터 읽어라 — 이것이 모든 자카드의 잣대다.
     기준선(4e9)과의 자카드를 내고, 되풀이 판(--rep)이 있으면 그것도.
     ⭐이 수가 «자카드 얼마부터 의미가 있나» 를 정한다. 없으면 「아직 없다」로 적어라.
  ③ 재고 전체에서 이번에 처음 채워진 칸이 무엇인지 적어라.
  ④ ⛔실패한 샤드가 있나 — runners/logs/sup_jobs_0919.log 에서 rc≠0 을 세라.
  ⑤ 착지한 것 가운데 **경로 상한에 붙은 칸**이 있나(npaths ≥ 0.99 × 2,000,000).`,
  },
]

const reads = await parallel(READERS.map(function (r) {
  return function () {
    return agent(RULES + '\n\n' + r.prompt, { label: 'read:' + r.key, phase: 'Read', schema: READ_SCHEMA })
  }
}))

const R = reads.filter(Boolean)
log('읽기 ' + R.length + '/4 — 답 ' + R.flatMap(function (x) { return x.answered || [] }).length + ' 개')

const FOUND = R.map(function (x, i) {
  return '\n════ ' + READERS[i].key + ' ════\n' +
    (x.answered || []).map(function (a) {
      return '  ▸ ' + a.question + '\n    답: ' + String(a.answer).slice(0, 700) +
        '\n    근거: ' + String(a.evidence).slice(0, 400) +
        (a.opens_what ? '\n    ⭐새로 열리는 물음: ' + String(a.opens_what).slice(0, 300) : '')
    }).join('\n') +
    (x.surprises ? '\n  ⚠어긋난 것: ' + String(x.surprises).slice(0, 600) : '') +
    (x.still_missing ? '\n  ⏳아직 없는 칸: ' + String(x.still_missing).slice(0, 400) : '')
}).join('\n')

const BRIEF = RULES + '\n\n■ ⭐0918 이 답한 것 · 0919 가 지금까지 낸 것 (네 판독자가 직접 읽은 것)\n' + FOUND

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
          why_now: { type: 'string', description: '0918·0919 가 낸 답과 어떻게 이어지나 — 그 답을 인용해라' },
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
  { key: 'follow', prompt: `⭐**0918 의 답을 곧장 따라간다.** 위 판독이 낸 답 가운데 가장 센 것을 골라,
그 답이 여는 다음 물음을 설계해라. 답이 「모른다」로 나온 칸이 있으면 그것을 읽을 수 있게 만드는 칸도 좋다.
⛔0918 이 이미 답한 것을 다시 사지 마라.` },
  { key: 'null', prompt: `⭐**잣대(널)를 넓힌다.** 0919 가 el −60·땅만 한 자리에서 광선 재표본 널을 재고 있다.
그런데 우리는 자카드를 여러 자리에서 쓴다 — 다른 앙각·다른 장면·다른 기체에서도 널이 필요한가?
널이 자리마다 다르면 지금까지의 자카드 해석이 통째로 흔들린다. 그것을 재는 최소 격자를 설계해라.
⛔널을 재는 칸은 «같은 조건을 다시 뽑는» 칸이어야 한다 — 조건을 바꾸면 널이 아니다.` },
  { key: 'deck', prompt: `**목요일(2026-09-10) 팀미팅 덱이 못 말하는 것**부터 거꾸로 설계해라.
덱을 읽어라 — /workspace/team_meeting/teammeeting_0910/teammeeting_slides_0910_v13.json
그리고 훑기 원장 /workspace/sionna/outputs/deck_audit_0908.json 도 읽어라.
「이 문장을 하려면 어떤 칸이 필요한데 지금 없다」를 찾아라.
⚠목요일까지 하루 남았다 — **오늘 밤 안에 끝나는 것**만 골라라(실측표로 계산해서 적어라).
⛔협곡 344 분짜리는 못 쓴다.` },
  { key: 'cheap', prompt: `⭐**싼 축을 최대로 쓴다.** 우리 커널은 빈 하늘 12 분·거울 지면 30 분이다.
어제 설계가 «우리 커널 12 분» 으로 잘못 어림해 거울 지면 25 줄을 실었고 실제로는 두 배 걸린다.
이번엔 실측값으로 계산해라. 우리 커널로만 할 수 있는 촘촘한 축을 골라라 —
⛔다만 우리 커널의 지면은 «거울상»이지 메쉬가 아니다. 그 한정을 물음마다 적어라.
⛔우리 커널 결과를 솔버와 절대 레벨로 견주지 마라.` },
  { key: 'break', prompt: `⭐**우리가 틀렸을 경우를 찾는다.** 지금 이야기가 「솔버가 어떤 자세에서
지면 되돌림 경로 하나를 놓친다」에 기대고 있다. 그 이야기를 **깨뜨릴** 실험만 설계해라.
어제 이 관점이 낸 것 가운데 살아남은 것과 죽은 것을 work/wf/queue_design_result.json 에서
읽고, **아직 안 해 본 깨기**를 찾아라.
⛔「우리가 맞다」를 확인하는 실험은 내지 마라.` },
  { key: 'reading', prompt: `⭐**살 수 없는 것 말고, 읽을 수 없는 것**을 고친다.
재고의 89 % 는 n_dup 이 없어 「같은 에코가 몇 번 적혔나」에 답할 수 없고,
96 % 는 n_trunc 가 없어 「상한에 잘렸나」에 답할 수 없다.
지금 우리가 **이미 가진 샤드**로 답하고 싶은데 그 열쇠가 없어 못 읽는 물음이 무엇인지 찾고,
그 칸만 --overwrite 로 다시 굽는 최소 목록을 설계해라.
⛔전부 다시 굽지 마라 — 물음 하나에 필요한 최소 칸만.
⭐--overwrite 가 실제로 어떻게 동작하는지 코드에서 읽고 써라.` },
]

phase('Design')
log('읽은 답 위에서 여섯 관점이 설계한다')

const designs = await parallel(ANGLES.map(function (a) {
  return function () {
    return agent(BRIEF + '\n\n■ 네 각도\n' + a.prompt +
      '\n\n■ 내는 것\n  묶음 2~5 개. 묶음마다 물음 하나 · 실제 발주 줄 · 어림 비용 · 읽는 법 · 죽는 조건 · ⛔안 답하는 것.\n' +
      '  ⛔발주 줄은 elevation_sweep_md.py 가 실제로 받는 문법이어야 한다 — dry-run 으로 확인해라.\n' +
      '  ⛔0918·0919 와 겹치지 마라. ⛔어제 죽은 안(work/wf/queue_design_result.json 의 killed)을 다시 내지 마라.',
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

■ 네 일 — 아래 발주안을 **죽이려고** 해라. 기본값은 「사면 안 된다」다.

묶음: ${p.name}
물음: ${p.question}
왜 지금: ${p.why_now}
줄 (${(p.lines || []).length} 개 × 샤드 ${p.nshards} × ${p.cost_min_per_shard} 분):
${(p.lines || []).slice(0, 14).map(function (l) { return '  ' + l }).join('\n')}
읽는 법: ${p.reads_how}
죽는 조건: ${p.kill_condition}

이 차례로 죽여라:
  ① **이미 답이 있나** — outputs/*.json 과 outputs/elev_sweep_shards/ 를 뒤져라.
     dry-run 으로 파일 이름을 만들어 존재를 확인해라. runners/jobs_0918.txt·jobs_0919.txt 와도 대조해라.
     ⭐어제 죽은 21 개의 이유가 work/wf/queue_design_result.json 의 killed 에 있다 — 먼저 읽어라.
  ② **문지기에 걸리나** — elevation_sweep_md.py 의 raise SystemExit 를 전부 보고 대조해라.
  ③ **읽을 수 있나** — 자세 1,024 미만이면 빗살 SNR 이 None 이다. 짝이 없거나 세대가
     어긋나면(n_dup·_mfix 유무) 못 읽는다. n_dup 이 필요한 물음인데 그 열쇠가 없으면 죽는다.
  ④ **상한에 붙나** — npaths 가 2,000,000 의 99 % 를 넘으면 그 축은 못 잰다.
  ⑤ **비용이 값어치를 넘나** — 실측표로 계산해라.
  ⑥ **손잡이가 실제로 있나** — argparse 에 없는 이름을 쓰면 죽는다.

살릴 수 있으면 fixed_lines 에 고친 줄을 내라. ⛔애매하면 survives=false 다.`,
      { label: 'kill:' + p.name.slice(0, 18), phase: 'Kill', schema: KILL_SCHEMA })
      .then(function (v) { return Object.assign({}, p, { verdict: v }) })
  }
}))

const alive = killed.filter(Boolean).filter(function (x) { return x.verdict && x.verdict.survives })
log('살아남은 묶음 ' + alive.length + ' / ' + props.length)

const MERGE_SCHEMA = {
  type: 'object',
  properties: {
    queue_lines: { type: 'array', items: { type: 'string' }, description: '최종 발주 줄 — --shard 없이. 생성기가 나눈다.' },
    groups: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          question: { type: 'string' },
          n_lines: { type: 'integer' },
          cost_hours: { type: 'number' },
          reads_how: { type: 'string' },
          kill_condition: { type: 'string' },
          caveat: { type: 'string' },
        },
        required: ['name', 'question', 'n_lines', 'cost_hours', 'reads_how', 'kill_condition'],
      },
    },
    order_why: { type: 'string' },
    total_hours: { type: 'number' },
    dropped: { type: 'string' },
  },
  required: ['queue_lines', 'groups', 'order_why', 'total_hours', 'dropped'],
}

phase('Merge')
const packet = alive.map(function (p) {
  return '\n════ ' + p.name + ' (' + p.angle + ') ════\n물음: ' + p.question +
    '\n왜 지금: ' + String(p.why_now).slice(0, 400) +
    '\n줄 ' + (p.lines || []).length + ' × 샤드 ' + p.nshards + ' × ' + p.cost_min_per_shard + ' 분\n' +
    ((p.verdict.fixed_lines && p.verdict.fixed_lines.length ? p.verdict.fixed_lines : p.lines) || []).map(function (l) { return '  ' + l }).join('\n') +
    '\n읽는 법: ' + String(p.reads_how).slice(0, 300) + '\n죽는 조건: ' + String(p.kill_condition).slice(0, 300) +
    (p.caveat ? '\n⛔안 답함: ' + String(p.caveat).slice(0, 250) : '')
}).join('\n')

const merged = await parallel(['값어치', '시간'].map(function (lens) {
  return function () {
    return agent(BRIEF + `

■ 네 일 — 반증을 이겨 낸 묶음들을 **하나의 발주서**로 합친다. 관점: «${lens}»
    값어치 = 물음이 얼마나 센가, 답이 무엇을 바꾸나
    시간   = 목요일(내일)에 쓸 수 있나, 오늘 밤 안에 끝나나

■ 살아남은 묶음
${packet || '(없음)'}

■ 규칙
  · ⭐총량을 **90~140 일꾼시간**으로 맞춰라. 0919(180 샤드·97 시간)가 오늘 20:45 에 빈다.
    그 뒤로 하루는 버텨야 한다.
  · ⭐**무거운 줄과 가벼운 줄을 섞어 차례를 짜라.** 0918 은 344 분짜리 여덟 줄을 맨 앞에
    몰아 뒤가 굶었다. 0919 는 섞어서 시간당 11 샤드가 나왔다 — 그 방식을 이어라.
  · 묶음마다 ⛔«이 묶음이 답하지 않는 것» 을 한 줄 적어라.
  · queue_lines 는 --shard 를 **빼고** 한 조건에 한 줄.
  · ⛔0918·0919 와 겹치지 마라. ⛔확산 항상 켬 · 프로펠러 단독 없음 · 뮌헨 없음 · 거칠기 접음.`,
      { label: 'merge:' + lens, phase: 'Merge', schema: MERGE_SCHEMA })
  }
}))

return {
  read: R,
  n_proposals: props.length,
  n_alive: alive.length,
  killed: killed.filter(Boolean).filter(function (x) { return x.verdict && !x.verdict.survives })
    .map(function (x) { return { name: x.name, why: String(x.verdict.why).slice(0, 600), already: x.verdict.already_answered } }),
  alive: alive.map(function (x) {
    return {
      name: x.name, angle: x.angle, question: x.question, why_now: x.why_now, caveat: x.caveat,
      lines: (x.verdict.fixed_lines && x.verdict.fixed_lines.length) ? x.verdict.fixed_lines : x.lines,
      nshards: x.nshards, cost_min_per_shard: x.cost_min_per_shard,
      reads_how: x.reads_how, kill_condition: x.kill_condition,
    }
  }),
  merged: merged.filter(Boolean),
}
