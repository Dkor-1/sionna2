export const meta = {
  name: 'verify-critique-0909',
  description: '외부 지적 아홉 건을 설치본 소스·우리 원장에 대고 독립 검증한다 — 맞는가 · 우리 결론 중 무엇이 흔들리나 · 무엇을 고쳐야 하나',
  phases: [
    { title: 'Check', detail: '지적 하나씩 소스와 원장에 대고 확인' },
    { title: 'Impact', detail: '맞는 지적이 우리 결론·덱·원장 어디를 흔드나' },
    { title: 'Judge', detail: '고칠 것과 그 순서' },
  ],
}

const RULES = `
■ 상시 규약
  ⛔말을 지어내지 않는다. 파일에서 읽은 것만 쓰고 경로:줄번호를 함께 적는다.
  ⛔확인 못 한 것은 「모른다」로 적는다.
  ⛔「우리 커널이 맞고 솔버가 틀렸다」로 결론짓지 않는다 — 둘 다 근사다.
  ⛔지적이 옳다고 해서 「시오나가 틀렸다」로도 넘어가지 않는다.
  ⛔실기 계측 대조는 이 저장소에 0 건이다.
  ⭐파이썬 /workspace/.venvs/py312/bin/python · CPU 로만 — CUDA_VISIBLE_DEVICES=""
  ⛔GPU 큐가 돌고 있다. GPU 를 쓰는 명령을 내지 마라.
  ⛔무거운 CPU 작업은 os.sched_setaffinity 로 코어를 묶어라(규약 17).
  ⛔아무것도 고치지 마라 — 이 일은 **검증**이다. 고칠 것을 찾아 적기만 한다.

■ 자리
  설치본 소스 /workspace/.venvs/py312/lib/python3.12/site-packages/sionna/rt/
    특히 path_solvers/path_solver.py · path_solvers/sb_candidate_generator.py
    · path_solvers/field_calculator.py
  우리 저장소 /workspace/sionna
    원장 outputs/*.json · 문서 docs/*.md · 본편 reports/*.ipynb
    발주 코드 benchmark/elevation_sweep_md.py · 상한 benchmark/report15_probe.py:104
  덱 /workspace/team_meeting/teammeeting_0910/teammeeting_slides_0910_v20.json

■ ⭐부모가 이미 직접 확인한 것 (다시 확인해도 좋지만 뒤집으려면 근거를 대라)
  · sb_candidate_generator.py:312-315 —
      spec_counter_size = dr.maximum(max_num_paths_per_src, MIN_SPEC_COUNT_SIZE)
      specular_chain_counters = [dr.zeros(mi.UInt, spec_counter_size*num_sources) ...]
    :59 MIN_SPEC_COUNT_SIZE = int(1e6). 바로 위 주석(:304-311)이 스스로
    「해시가 같으면 같은 사슬로 보고 저장 안 한다 · 배열이 충분히 커야 충돌로 후보가
     버려지지 않는다」고 적는다.
  · 우리 규약 상한은 benchmark/report15_probe.py:104 의 2,000,000 이고
    재고에 _mp6000000(4 장) · _mp12000000(10 장) 이 있다 — **셋 다 바닥값 1e6 위**다.
    ⇒ 상한을 흔든 우리 실험은 저장 상한과 해시 배열 크기를 **함께** 움직였다.
  · path_solver.py:194 후보 생성 → … → :245-246 무효 경로 제거.
    ⇒ 반환 수는 후보 수가 아니다.
`

const CLAIM_SCHEMA = {
  type: 'object',
  properties: {
    n: { type: 'integer' },
    claim: { type: 'string', description: '지적을 한 줄로' },
    verdict: { type: 'string', enum: ['맞다', '대체로 맞다', '부분적으로만', '틀리다', '확인불가'] },
    evidence: { type: 'string', description: '소스·원장에서 직접 읽은 것 — 경로:줄번호와 실제 내용' },
    what_it_breaks: { type: 'string', description: '우리 결론·원장·덱 중 무엇이 흔들리나. 없으면 «없다»' },
    where_to_fix: { type: 'string', description: '고칠 자리 — 파일:줄. 없으면 «없다»' },
    already_handled: { type: 'string', description: '우리가 이미 그렇게 적어 둔 곳이 있으면 어디' },
  },
  required: ['n', 'claim', 'verdict', 'evidence', 'what_it_breaks'],
}

phase('Check')
log('지적 아홉 건을 소스·원장에 대고 확인한다')

const CLAIMS = [
  {
    n: 1,
    label: 'basescene',
    prompt: `■ 지적 ① — 「NVIDIA 기본 환경에서는 문제가 발생하지 않는다」는 출발점부터 틀렸다.
  거리 협곡에서도 복소 잔차의 이상 사건이 검출됐고, 일부는 **진폭이 늘었다**.
  진폭 감소만 찾으면 놓친다. 뮌헨은 문턱을 넘는 사건이 없었지만 **중심선 차폐**가 확인됐다.
  ⇒ 정확한 서술은 「기본 제공 장면에서도 장면·배치에 따라 복소 잔차 사건이 관측됐다.
     뮌헨의 그 배치에서는 쓴 판정 기준을 넘는 사건이 없었다. 중심선 차폐가 함께 확인됐으나
     그것이 미검출의 원인인지는 분리 실험이 필요하다.」

확인할 것:
  · outputs/outdoor_dip_origin_0908.json · read_0918A_0909.json ·
    builtin_scene_diagnosis_0908.json 을 열어 그 수가 실제로 그런지.
  · ⭐**우리가 이미 그렇게 고쳤나** — reports/12_outdoor-scene.ipynb 와
    src/build_report12_outdoor.py 를 읽어라(2026-09-09 에 고쳤다는 커밋 626d3667 이 있다).
  · 덱(teammeeting_slides_0910_v20.json)은 어떻게 적는가.
  · ⭐뮌헨의 «차폐가 미검출의 원인인가» 를 **분리한 실험이 있나** — 없으면 그렇게 적어라.`,
  },
  {
    n: 2,
    label: 'threshold',
    prompt: `■ 지적 ② — 「이벤트 없음」은 「오류 없음」이 아니다.
  판정식이 **중앙값 크기에 비례하는 문턱**을 쓰므로 장면별 배경 잔차가 다르면 검출 민감도가
  달라진다. 장면 간 비교에는 사건 개수뿐 아니라 **절대 편차 · 기준 중앙값 · 문턱을 흔든 결과**
  가 필요하다.

확인할 것:
  · benchmark/read_0914_0908.py 의 measure() 를 읽어 문턱이 정말 중앙값에 비례하는지.
  · outputs/read_0918A_0909.json 의 ladder_n_by_dev · cluster_ratio_min/max 를 읽어라 —
    협곡 −15°·−45° 가 문턱 바로 아래 눌려 있다는 관측이 있다. 사실인가.
  · ⭐우리 원장·본편·덱이 «절대 편차와 기준 중앙값을 함께» 적고 있나. 아니면 어디에 없나.
  · ⭐«문턱을 흔든 결과» 가 이미 있나(threshold_ladder · ladder_n_by_dev).`,
  },
  {
    n: 3,
    label: 'hash',
    prompt: `■ 지적 ③ — 「경로 수 상한만 바꿨다」가 단일 변수 실험이 아니다.
  max_num_paths_per_src 가 저장 상한뿐 아니라 **중복 판정용 해시 배열 크기**에도 쓰이고
  그 크기는 max(상한, 1,000,000) 이다. 바닥값보다 큰 범위에서 상한을 바꾸면 **해시 충돌
  조건도 함께** 달라진다. 공식 코드도 해시 충돌로 후보가 유실될 수 있다고 적는다.
  ⇒ 상한을 늘려 결과가 좋아졌더라도 「저장 공간 부족이 원인」으로 바로 못 간다.

⭐부모가 이미 소스에서 확인했다(위 참조). 네가 할 일은 **우리 쪽 영향**이다:
  · 우리가 상한을 흔든 **모든 자리**를 찾아라 — 재고의 _mp 꼬리표 · docs/*.md ·
    outputs/*.json · reports/*.ipynb 에서 「상한」·「max_paths」·「n_trunc」를 훑어라.
  · 그중 「상한을 올리니 좋아졌다 ⇒ 저장 부족이 원인이었다」로 읽히는 문장이 있나.
    있으면 **그 문장을 그대로 인용**하고 자리를 적어라.
  · ⭐거칠기 축을 「상한에 붙어서 접었다」로 적어 둔 자리들도 이 지적에 걸리나?
    (path_cap_share_pct 거칠기 0.3 → 99.24 % · 0.7 → 100 %)
  · 분리 실험(저장 상한 고정 + 해시 크기만 바꾸기)이 **가능한가** — 손잡이가 있나,
    아니면 설치본을 고쳐야 하나. 소스를 읽고 판단해라.`,
  },
  {
    n: 4,
    label: 'trunc',
    prompt: `■ 지적 ④ — 「반환된 경로 수가 상한보다 작으므로 내부 잘림은 없다」가 성립 안 한다.
  솔버는 후보 생성 → 경로 보정 → 전계 계산 → **무효 경로 제거** 순이라 최종 반환 수는
  중간 후보 수와 다르다. nret == npaths 도 「반환 후 필터가 추가로 제거한 것이 없다」까지다.
  ⇒ 필요한 계측은 생성 후보 → 중복 탈락 → 상한 초과 → 기하 검증 탈락 → 전계 후 제거의
     **단계별 수**다. 하나의 n_trunc 에 그 의미를 다 주면 원인을 잘못 좁힌다.

확인할 것:
  · path_solver.py 의 __call__ 을 처음부터 끝까지 읽고 **실제 단계 순서**를 적어라.
  · 우리가 n_trunc 와 nret==npaths 를 어떻게 쓰는지 —
    benchmark/elevation_sweep_md.py:927-934 와, 그 수를 인용하는 원장·본편을 찾아라.
  · ⭐「하네스 무죄 — nret == npaths, n_dup = 0, n_trunc = 0」 같은 문장이
    work/sweep_0904/RESUME_0908.md 등에 있다. 그 문장이 이 지적에 걸리나?
  · 단계별 수를 **셀 수 있나** — 설치본이 그 수를 내주나, 아니면 고쳐야 하나.`,
  },
  {
    n: 5,
    label: 'budget',
    prompt: `■ 지적 ⑤ — 「경로 수를 맞추면 공정한 계산 예산 비교」에 조건이 더 필요하다.
  확산 반사를 포함하는 전계 계산에서는 **샘플 수가 ray tube 의 초기 입체각과 계산
  가중치에 들어간다.** 경로 수가 같아도 추정량의 가중치·경로 종류·변동성이 같다고
  보장 못 한다. 이것이 Mini2 의 +7.40 dB 해석과 이어진다.

확인할 것:
  · field_calculator.py 에서 확산 반사의 가중치가 어떻게 계산되는지 읽어라 —
    samples_per_src(우리 --spp)가 어디에 들어가나. 입체각·가중치 식을 인용해라.
  · 우리가 「경로 수를 맞췄을 때 …」로 적은 자리를 찾아라
    (reports/06_6_microdoppler-limits.ipynb · 그 빌더). +7.40 dB 가 어떻게 나온 수인가.
  · ⭐2026-09-08 검토가 그것을 「외삽 예측」으로 이미 고쳤다는 기록이 있다
    (docs/COMPLETED_INTERPRETATIONS_REVIEW_0908.md 항목 3). 그 고침이 이 지적을
    **충분히** 덮나, 아니면 더 적을 것이 있나.`,
  },
  {
    n: 6,
    label: 'physics',
    prompt: `■ 지적 ⑥ — 「모든 물리를 켰다」와 「옵션 차이만큼이 그 물리의 기여도」는 다르다.
  v2.0.1 후보 생성기는 **회절을 1 회로 제한**하고, 한 경로에 확산 반사와 회절이 함께
  들어가는 조합을 **제한**한다. 전역 옵션을 다 켜도 가능한 모든 상호작용을 계산하지 않는다.
  ⇒ 안전한 표현: 「그 버전이 지원하는 상호작용 조합과 설정한 최대 깊이 안에서 옵션을 켰다.」
  또한 옵션 변경은 **후보 탐색 과정 자체**에도 영향을 준다. 두 실행의 전계 차이를
  특정 물리의 기여도로 읽으려면 공통 경로와 추가·소실 경로를 대응시켜야 한다.

확인할 것:
  · sb_candidate_generator.py 에서 회절 1 회 제한과 확산+회절 조합 제한을 **찾아 인용**해라
    (loc_en_inter 근처를 보라).
  · 우리가 「물리를 다 켰다」·「이 팔과 저 팔의 차이가 회절의 기여」로 적은 자리를 찾아라 —
    다섯 팔(R0D0E0F1 등)의 차이를 물리 기여로 읽는 문장이 원장·본편·덱에 있나.
  · ⭐덱 v20 이 팔 이름을 «no bending around edges» / «with bending around edges» 로
    쓰는데, 이 지적에 비추어 그 이름이 **과한가**?`,
  },
  {
    n: 7,
    label: 'diff',
    prompt: `■ 지적 ⑦ — D = E_scene − E_free 를 곧바로 «환경 산란 성분» 이라 부르면 안 된다.
  거기에는 환경 경로뿐 아니라 **환경 때문에 바뀐 드론 경로 · 차폐 · 두 실행의 후보 탐색
  차이**도 들어간다. 복소 전계는 서로 상쇄할 수 있어, **진폭 증가를 경로 유실의 반증으로
  쓸 수 없다.**
  같은 주의가 nadir 의 AC 비율에도 걸린다 — 직교하지 않는 신호는 전력에 교차항이 생긴다.
  63.7/31.1/5.2 같은 수를 「원인별 기여율」이나 「수치 잡음의 하한」으로 읽으면 안 된다.

확인할 것:
  · 우리가 D 를 무엇이라 부르는지 — benchmark/read_0914_0908.py 의 metric_ko,
    read_0918A/B, 본편, 덱. 「지면이 올린 몫」·「장면이 얹은 몫」 같은 이름이 이 지적에 걸리나.
  · ⭐진폭 증가(협곡 +6.86 dB)를 우리가 어떻게 읽었나 — 「경로 유실의 반증」으로 쓴 자리가 있나.
  · 63.7/31.1/5.2 가 어느 원장·어느 본편에 있나. 그 수가 지금 어떻게 서술돼 있나.
  · ⭐이미 「환경 산란·차폐·탐색 차이로 나누는 작업은 안 끝났다」고 적어 둔 곳이 있나.`,
  },
  {
    n: 8,
    label: 'evidence',
    prompt: `■ 지적 ⑧ — 재현성 · 주기성 · 원인 규명은 각각 다른 증거다.
  같은 씨앗에서 되풀이된다는 것은 «그 설정에서 재현된다» 는 증거이지 «기하가 유일한 원인» 의
  증거가 아니다. 수치적 경계 처리도 회전 각도와 함께 되풀이될 수 있다.
  경계할 연결 넷:
    · 같은 각도에서 되풀이됨 → 물리적 산란이라고 확정
    · 일부 원형 모멘트가 작음 → 모든 주기성이 없다고 결론
    · 보간 후 스펙트럼이 좋아짐 → 실제 신호를 복원했다고 표현
    · f_tip 밖 에너지가 있음 → 모두 수치 오류라고 분류
  ⭐반대로, 앞서 쓴 FM 반례도 「순간 주파수 최댓값이 엄격한 FFT 대역 경계가 아니다」를
    보일 뿐 실제 데이터의 꼬리가 물리적이라는 증명은 아니다. **비판하는 쪽에도 같은 잣대**를.

확인할 것:
  · 우리가 그 넷 중 어느 것이라도 저지른 자리를 찾아라 — 원장·본편·덱·재개 지점.
  · ⭐특히 work/sweep_0904/RESUME_0908.md §④ 「되풀이된다 — 자카드 1.0000」과
    RESUME_0909.md §1② 의 철회를 읽어라. 그 철회가 이 지적을 이미 덮나?
  · 「위상 집중을 못 찾았다 → 날개 가림이 아니다」로 넓힌 자리가 있나(설계 검토 ⑨).
  · ⭐«복원» 이라 쓴 자리가 남아 있나 — 덱 v20 은 어떻게 적나.
  · FM 반례가 어느 항목의 근거인지 찾아, 그 항목이 지금 어떻게 서술돼 있는지 보라.`,
  },
  {
    n: 9,
    label: 'audit',
    prompt: `■ 지적 ⑨ — 앞선 13 항목 검사의 통과 결과도 범위를 좁혀 설명해야 한다.
  그 검사는 «수정 문구의 존재 · 일부 철회 표현의 부재 · 수치와 문서 연결» 을 확인했을 뿐
  전체 연구 해석이 검증됐다는 뜻이 아니다.
  특히 **원본 JSON 에 남은 과거의 서술형 판정**과 현재 보고서의 수정된 해석이 공존하면,
  나중에 보고서를 다시 만들면서 **오래된 결론을 도로 가져올 수 있다.**
  원래 판정을 보존하더라도 «현재 유효성 · 철회 사유 · 대체 해석» 을 연결해야 한다.

확인할 것:
  · ⭐**원장 JSON 에 서술형 판정이 남아 있는가** — outputs/*.json 을 훑어
    「verdict」·「판정」·「결론」 같은 산문 필드를 찾고, 그중 지금 철회됐거나 바뀐 것을 골라라.
  · 그 필드를 **빌더가 본편으로 그대로 옮기는가** — 옮기면 재생성 때 옛 결론이 돌아온다.
    src/build_*.py 에서 그 키를 읽는 자리를 찾아라.
  · ⭐2026-09-09 검증이 이미 잡은 것과 겹치나 — work/wf/verify_review_0908_result.json 을 읽어라.
  · 「철회 사유·대체 해석을 연결」하는 얼개가 이미 있나
    (benchmark/check_retracted.py 의 RETRACTED 표가 그 구실을 하나?).`,
  },
]

const checked = await parallel(CLAIMS.map(function (c) {
  return function () {
    return agent(RULES + '\n\n' + c.prompt, { label: 'claim:' + c.label, phase: 'Check', schema: CLAIM_SCHEMA })
  }
}))

const C = checked.filter(Boolean)
log('확인 ' + C.length + '/9 — 맞다 ' + C.filter(function (x) { return x.verdict === '맞다' }).length)

const brief = C.sort(function (a, b) { return a.n - b.n }).map(function (x) {
  return `[${x.n}] ${x.verdict} — ${x.claim}\n    근거: ${String(x.evidence).slice(0, 400)}\n    흔드는 것: ${String(x.what_it_breaks).slice(0, 350)}\n    고칠 자리: ${String(x.where_to_fix || '—').slice(0, 250)}\n    이미 적어 둔 곳: ${String(x.already_handled || '—').slice(0, 250)}`
}).join('\n\n')

const JUDGE_SCHEMA = {
  type: 'object',
  properties: {
    overall: { type: 'string', description: '지적 전체에 대한 한 줄 판정' },
    correct_count: { type: 'integer' },
    fixes: {
      type: 'array',
      description: '고칠 것 — 값어치·급함 순',
      items: {
        type: 'object',
        properties: {
          what: { type: 'string' },
          where: { type: 'string', description: '파일:줄' },
          how: { type: 'string' },
          urgency: { type: 'string', enum: ['덱 발표 전', '이번 주', '별건'] },
          breaks_if_not: { type: 'string', description: '안 고치면 무엇이 틀린 채 남나' },
        },
        required: ['what', 'where', 'how', 'urgency'],
      },
    },
    deck_impact: { type: 'string', description: '월요일 덱(v20)에 걸리는 것과 어떻게 고칠지' },
    not_correct: { type: 'string', description: '지적 중 틀렸거나 과한 것 — 있으면 근거와 함께' },
    new_experiments: { type: 'string', description: '이 지적이 요구하는 새 실험 — 큐에 넣을 만한 것' },
  },
  required: ['overall', 'correct_count', 'fixes', 'deck_impact'],
}

phase('Judge')
const judged = await agent(RULES + `

■ 네 일 — 확인 결과를 모아 **무엇을 어떤 순서로 고칠지** 낸다.

■ 아홉 건 확인 결과
${brief}

판정할 것:
  · 지적이 전체적으로 맞나. 틀렸거나 과한 것이 있으면 **근거와 함께** 적어라
    (⛔지적이라고 다 맞는 것은 아니다 — 같은 잣대를 지적에도 댄다).
  · 고칠 것을 «덱 발표 전 / 이번 주 / 별건» 으로 갈라라.
    ⚠팀미팅이 09-11(금) 또는 09-14(월)로 미뤄졌다.
  · ⭐**덱 v20 에 걸리는 것**을 따로 적어라 — 지금 덱이 틀리게 말하는 것이 있나?
  · 이 지적이 요구하는 **새 실험**이 있으면 적어라(지금 0922 큐를 설계 중이다).

⛔칭찬하지 마라. 무엇이 맞고 무엇이 안 맞는지, 무엇을 고칠지만.`,
  { label: 'judge', phase: 'Judge', schema: JUDGE_SCHEMA })

return { claims: C, judge: judged }
