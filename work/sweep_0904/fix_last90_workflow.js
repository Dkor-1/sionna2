export const meta = {
  name: 'sweep-fix-all',
  description: '전수조사에서 남은 지적 전부를 원문·원장으로 재확인하고 치환 명세를 낸다',
  phases: [{ title: 'Spec', detail: '조각마다 지적을 다시 확인하고 old/new 명세를 만든다' }],
}

//: ⭐지적 목록은 **파일**에 있다 — 스크립트에 박으면 382 건이 안 들어간다.
//  에이전트는 파일을 읽을 수 있으므로, 각자 자기 조각 번호만 받아 그 범위를 읽는다.
const TODO = '/workspace/sionna/work/sweep_0904/todo_last90.json'
const ROOT = '/workspace/sionna'
const N = (typeof args !== 'undefined' && args && args.n) || 382
const CHUNK = (typeof args !== 'undefined' && args && args.chunk) || 4
const FROM = (typeof args !== 'undefined' && args && args.from) || 0
const TO = Math.min(FROM + ((typeof args !== 'undefined' && args && args.count) || N), N)

const RULES = `
너는 /workspace/sionna 에서 **이미 확인된 지적**을 받아 **정확한 치환 명세**를 만든다.

■ 규약
  · ⛔⛔**고칠 파일은 반드시 ${ROOT} 안이어야 한다.** 레포 밖(/data/... 등)은 **남의
    디렉토리**다 — 그런 명세를 내지 마라(2026-09-06 에 실제로 두 건이 나왔고 되돌렸다).
  · ⛔노트북(reports/*.ipynb)을 손으로 고치지 않는다 — 고칠 곳은 그것을 만든 **빌더**다
    (src/build_part*.py · benchmark/*.py). 빌더가 없으면(수기 문서·원장) 그 파일을 직접 고친다.
    지적의 builder 칸이 힌트지만 **믿지 말고 Grep 으로 직접 확인**해라.
  · 수치는 손으로 치지 않는다 — 가능하면 원장에서 f-string 으로 뽑는다.
    ⛔순수 JSON 원장이라 f-string 이 안 되면, 원장 경로·키를 문장에 박아 대조 가능하게 한다.
  · 철회·정정은 **지우지 말고 ⛔표시로 남긴다**(왜 내렸는지 추적이 되게).
  · 「우리 커널이 맞고 PathSolver 가 틀렸다」로 결론짓지 않는다(둘 다 근사, 실측 대조 0 건).
    리듬 몫 **크기**는 인용하지 않는다(R29). 환경은 실외만. 말을 지어내지 않는다.
    최상급·부재증명은 범위를 붙인다(「보유 아카이브 218편 안에서」).

■ 두 단
  ① **다시 확인.** 인용문이 지금 파일에 정말 있나(Grep). 이미 정정 표식이 붙었나.
     수를 다투면 원장을 열어 **직접 다시 계산**(Bash: CUDA_VISIBLE_DEVICES="" python3).
     ⛔GPU 를 쓰는 스크립트는 돌리지 마라 — 읽기만 한다.
  ② **치환 명세.** old_string 은 대상 파일에 **정확히 한 번만** 나와야 한다(앞뒤를 넉넉히).
     ⛔파일을 직접 고치지 마라 — 명세만 낸다. 적용은 사람이 한다.
     ⚠**이 묶음은 앞 세 판이 못 고친 어려운 자리다.** 인용문이 파일에 **여러 번**
       나오거나(항목의 n_hits 참조), 앞 치환이 그 자리를 이미 바꾼 것들이다.
       ⇒ old_string 에 **앞뒤 줄을 넉넉히 넣어** 반드시 한 번만 맞게 만들어라.
       같은 문장이 여러 자리에 진짜로 있으면 **자리마다 명세를 따로** 내라.
     ⛔파이썬에 글을 넣을 때는 **주석이나 문자열 안**이어야 하고 **괄호 균형**을 맞춰라.

확인 못 했거나 이미 고쳐졌으면 still_valid=false. **없는 것을 만들어 내지 마라.**
`

const SPEC_SCHEMA = {
  type: 'object',
  properties: {
    specs: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          still_valid: { type: 'boolean' },
          checked: { type: 'string', description: '원문·원장에서 무엇을 확인했는지' },
          old_string: { type: 'string' },
          new_string: { type: 'string' },
          rebuild: { type: 'string' },
          note: { type: 'string' },
        },
        required: ['file', 'still_valid', 'checked', 'old_string', 'new_string', 'rebuild', 'note'],
      },
    },
  },
  required: ['specs'],
}

const idx = []
for (let i = FROM; i < TO; i += CHUNK) idx.push(i)
log(`지적 ${FROM}~${TO - 1} · ${idx.length} 조각 (조각당 ${CHUNK} 건)`)

const out = await pipeline(
  idx,
  (start) => agent(
    `${RULES}

■ 네 조각
\`${TODO}\` 를 Read 로 열어 **배열의 ${start} 번부터 ${Math.min(start + CHUNK, TO) - 1} 번까지**
(0-기준, 그 범위만) 맡아라. 각 항목은 file·line·sev·quote·why·fix·builder 를 든다.
레포 루트는 ${ROOT} 다.

각 건마다 ① 다시 확인 ② 치환 명세. 유효하지 않으면 still_valid=false 로 두고 이유를 적어라.`,
    { label: `명세:${start}`, phase: 'Spec', schema: SPEC_SCHEMA, effort: 'high' }
  )
)

const specs = out.filter(Boolean).flatMap((r) => (r && r.specs) || [])
const valid = specs.filter((s) => s.still_valid)
log(`명세 ${specs.length} → 유효 ${valid.length}`)
return { from: FROM, to: TO, n_specs: specs.length, n_valid: valid.length, specs }
