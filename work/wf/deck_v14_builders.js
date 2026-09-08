export const meta = {
  name: 'deck-v14-builders',
  description: '0910 덱 v14 를 위해 그림 빌더 셋을 고치고 다시 굽는다 — 날개끝 안내선 앙각 보정, 사다리 광선 예산 고정, 설정 장 재구성, 실외 새 그림 하나',
  phases: [
    { title: 'Fix', detail: '빌더 셋을 각각 고치고 다시 굽는다 (파일이 겹치지 않는다)' },
    { title: 'Check', detail: '구워진 png 를 열어 고쳐진 것을 눈으로 확인' },
  ],
}

const RULES = `
■ 상시 규약 (어기면 결과를 못 쓴다)
  ⛔말을 지어내지 않는다. 파일에서 읽은 것만 쓴다. 확인 못 한 것은 「모른다」로 적는다.
  ⛔우리끼리 쓰는 말을 덱에 넣지 않는다(최우선). 시험: 「우리 코드를 안 읽은 사람이 이 말을
    읽고 뜻을 아는가?」 **그림 안 글자·축 이름·범례·조건줄까지** 같다.
    ⛔우리가 만든 지표 이름 · 코드에서 샌 말 · 분야 밖 전문어(closed form · nose-on) 금지.
  ⛔그림 안에 판정 배지·네모 상자·숫자 배지를 넣지 않는다.
  ⛔챔버는 어디에도 넣지 않는다. 환경은 실외만.
  ⛔「우리 커널이 맞고 솔버가 틀렸다」로 결론짓지 않는다 — 둘 다 근사다.
  ⛔σ(dBsm) 인용 금지 · 두 엔진의 절대 레벨 비교 금지.
  ⛔실기 계측 대조는 이 저장소에 0 건이다 — 「검증됐다」로 읽지 않는다.
  ⛔무거운 CPU 작업은 os.sched_setaffinity 로 코어를 묶는다(규약 17). 빌더에 이미 있으면 그대로 둔다.
  ⛔GPU 를 쓰지 않는다 — CUDA_VISIBLE_DEVICES="" 로 띄운다. GPU 큐가 돌고 있다.
  ⭐파이썬은 /workspace/.venvs/py312/bin/python (⛔ ~/.venvs 는 없다)

■ 자리
  덱 폴더  /workspace/team_meeting/teammeeting_0910
  분석 저장소 /workspace/sionna
  덱 규약  /workspace/team_meeting/DECK_CONVENTION.md · /workspace/team_meeting/CLAUDE.md

■ ⭐⭐이미 검산이 끝난 사실 — 날개끝 안내선이 틀린 자리에 있다
  bake_window.py:124 와 bake_outdoor.py:52 가 둘 다
    FTIP = float(_TJ["f_tip_hz"])        # _TJ = report07_three_engines.json["_meta"]
  로 **상수 1228.7211819358865 Hz** 를 읽어 모든 판에 같은 안내선을 긋는다.
  그런데 그 값이 나온 판은 같은 _meta 의 el_deg = -15.0 · range_m = 3.0 · n = 4096 이다.

  날개끝 주파수는 앙각을 탄다 — 저장소에 이미 식이 있다:
    benchmark/clutter_parts_ladder_0824.py:92-94
      def f_tip(el_deg): return FTIP_EL30 / cos(radians(-30.0)) * cos(radians(el_deg))
  즉 f_tip(el) = F0 · cos(el) 이고, 원장값을 그 판의 앙각으로 되돌리면
      F0 = 1228.7211819358865 / cos(radians(-15.0)) = 1272.07 Hz
  ⭐이 값을 기체 제원에서 독립으로 검산했다 — matrice4e 프롭 274 mm · 호버 3800 rpm ·
    3.5 GHz 로 2·(2π·f_rev·R)/λ = 1272.91 Hz. 원장에서 되돌린 값과 **0.07 %** 차이다.

  지금 상수가 앙각마다 어긋나는 폭:
      el   0° 참값 1272.1 Hz →  -3.4 %
      el -15° 참값 1228.7 Hz →  +0.0 %   (원장값이 나온 자리)
      el -30° 참값 1101.6 Hz → +11.5 %
      el -45° 참값  899.5 Hz → +36.6 %
      el -60° 참값  636.0 Hz → +93.2 %   ⛔거의 두 배 자리에 그어져 있다

  ⭐고치는 법 (두 빌더에 **똑같이**):
      _EL_TJ = float(_TJ["el_deg"])            # 원장값이 나온 판의 앙각
      FTIP0  = FTIP / math.cos(math.radians(_EL_TJ))   # 앙각 0° 로 되돌린 값
      def f_tip(el_deg):
          """⭐앙각으로 보정한 날개끝 자리. clutter_parts_ladder_0824.py:92-94 와 같은 식.
          ⛔상수 하나를 모든 판에 쓰면 안 된다 — 원장값은 앙각 -15° 판의 것이라
            -60° 판에서 +93.2 % 어긋난다(2026-09-08 훑기에서 잡음)."""
          return FTIP0 * math.cos(math.radians(el_deg))
  그리고 MS.draw(...) 에 넘기는 자리마다 그 판의 **실제 앙각**으로 f_tip(el) 을 넘긴다.
  ⛔ FTIP 상수를 그대로 넘기는 자리를 하나도 남기지 마라.
  ⚠ src/md_mapstyle.py 의 draw() 는 이 값으로 안내선을 긋고 세로 눈금(ylim)까지 잡는다
    (md_mapstyle.py:209-211, YLIM_FTIP=1.9) — 눈금이 판마다 달라지는 것이 **맞는 동작**이다.
`

const OUT_SCHEMA = {
  type: 'object',
  properties: {
    edits: {
      type: 'array',
      description: '실제로 고친 것 하나에 한 줄',
      items: {
        type: 'object',
        properties: {
          where: { type: 'string', description: '파일:줄번호' },
          what: { type: 'string', description: '무엇을 어떻게 고쳤나' },
          verified: { type: 'string', description: '고쳐진 것을 어떻게 확인했나 (돌려 본 명령·읽은 값)' },
        },
        required: ['where', 'what', 'verified'],
      },
    },
    baked: { type: 'array', items: { type: 'string' }, description: '다시 구워진 png 경로와 크기·시각' },
    numbers_for_notes: { type: 'string', description: '발표자 노트에 쓸 수 있게, 원장에서 읽은 수와 그 출처 경로:줄번호' },
    not_done: { type: 'string', description: '지시받았으나 못 한 것과 그 까닭. 없으면 «없다»' },
    warnings: { type: 'string', description: '고치다 발견한 새 문제 · 인용하면 안 되는 수' },
  },
  required: ['edits', 'baked', 'not_done'],
}

const TASKS = [
  {
    key: 'window',
    label: 'bake_window.py',
    prompt: `■ 네 파일 — /workspace/team_meeting/teammeeting_0910/bake_window.py
  (⛔다른 빌더 파일은 건드리지 마라. 같은 시간에 다른 에이전트가 고치고 있다.)

이 빌더가 굽는 것: f_window_stft.png(5 쪽) · f_window_ladder.png(6 쪽) · f_window_rays.png(7 쪽).
셋 다 **빈 하늘(자유공간)** 자료다 — 이 파일에 env 라는 글자가 한 번도 안 나온다.

■ 고칠 것 여섯

① ⭐날개끝 안내선 앙각 보정 — 위 「이미 검산이 끝난 사실」 그대로.
   :124 FTIP 를 쓰는 자리는 :181 의 MS.draw(axes[r][c], t_, f_, S_, FTIP, ref=refs[r]) 다.
   fig_pair_stft 가 그리는 판의 앙각을 코드에서 확인하고(찾는 글자열이 «_d2_el+0_» 이면 0°)
   f_tip(그 앙각) 을 넘겨라. ⛔앙각을 짐작하지 말고 glob 패턴에서 읽어라.

② ⛔사다리가 광선 예산이 다른 판을 한 점에 섞고 있다 — :41 근처의 찾는 글자열
   "sionna_p*_sw{arm}_..." 에서 «p*» 를 «p4000000000» 으로 고정해라.
   ⭐고치기 전에, 고정하면 **빠지는 칸이 있는지** 두 팔 × 두 축 격자 전부를 세어 확인해라
   (고정 전 몇 장 / 고정 후 몇 장). 빠지는 칸이 있으면 고치지 말고 not_done 에 적어라.
   ⭐고정 뒤 :108 근처 조건줄의 «8,192 rotor positions per point» 가 참이 되는지 실제로 세어 확인해라.

③ 범례가 판 밖으로 잘려 «diffuse scattering o» 로 끝난다 — :105-107 근처.
   범례를 판 **아래**로 내리고(loc="lower center", ncol=2, bbox_to_anchor 로 판 밖 아래)
   subplots_adjust 로 자리를 만들어라. 구운 png 를 **열어서** 범례가 온전히 보이는지 확인해라.

④ 범례 이름 :33-34 를 청중 말로 짧게 — 지금 «diffuse scattering only» 는 틀리기도 하다.
   ⭐elevation_sweep_md.py:872 를 열어 확인해라: los=True 와 specular_reflection=True 는
   **모든 팔에서 늘 켜져 있고**, --sw 가 끄는 것은 refraction·diffraction·edge_diffraction 뿐이다.
   그러니 «diffuse scattering only» 는 사실과 다르다. 두 팔 이름을 이렇게 바꿔라:
     R0D0E0F1 → "no bending around edges"
     R0D1E1F1 → "with bending around edges"
   ⛔더 긴 이름을 쓰지 마라 — 잘림이 다시 난다.

⑤ x 축 이름 :100 근처 «{axis} off the nose [deg]» → «{axis} away from 0° [deg]».
   («off the nose» 는 분야 밖 전문어다.)

⑥ 조건줄에서 «diffuse scattering only» 를 쓰는 곳이 더 있으면 ④ 와 같은 말로 바꿔라.
   ⛔ f_window_rays.png(7 쪽) 의 자료·판 구성은 **그대로 둔다** — 말만 고친다.

■ 마지막
  CUDA_VISIBLE_DEVICES="" 로 빌더를 돌려 세 png 를 다시 굽고, **셋 다 Read 로 열어 보고**
  ①안내선이 판마다 제자리인지 ③범례가 안 잘리는지 ⑤축 이름이 바뀌었는지 눈으로 확인해라.
  numbers_for_notes 에 ② 에서 센 실제 자세 수를 점마다 적어라.`,
  },
  {
    key: 'setup',
    label: 'bake_setup.py',
    prompt: `■ 네 파일 — /workspace/team_meeting/teammeeting_0910/bake_setup.py
  (⛔다른 빌더 파일은 건드리지 마라. 같은 시간에 다른 에이전트가 고치고 있다.)

이 빌더가 굽는 것: f_setup.png — 3 쪽 «어떤 환경에서 어떤 세팅으로 실험했나» 장.
왼쪽은 옆에서 본 기하 도면, 오른쪽은 장면 렌더, 아래는 공통 설정 줄.

■ 훑기가 찾은 결함 넷 (전부 검증을 통과했다)

① 도면이 내려다보는 각 30°·60° 둘만 그리는데, 덱의 여덟 그림 중 **네 장이 0°** 다
   (2·5·6·7 쪽 — bake_window.py 의 찾는 글자열이 «_d2_el+0_» 이다).
   :58 근처의 ((-30.0,"30°"), (-60.0,"60°")) 에 (0.0,"0°") 를 더해 세 자리를 그려라.
   ⚠0° 는 레이다가 드론과 **같은 높이**이고 그 판들에는 **지면이 없다**.
     도면에서 그 점이 청중에게 보이게 해라(예: 0° 선은 지면선에 안 닿게, 또는 각주 한 줄).
     ⛔없는 지면을 0° 자리에 그리지 마라.

② 렌더 셋 중 둘이 저장소의 어느 스크립트도 굽지 않는다 — 카메라도 드론 유무도 모른다.
   ⭐직접 확인해라: grep -rn 으로 outdoor01_top 과 canyon_wide 를 /workspace 에서 찾아
     bake_setup.py 한 줄씩만 잡히는지, 그리고 make_outdoor_scene_0831.py:117-120 의
     cams 사전에 어떤 이름이 있는지.
   확인되면 :97-99 의 shots 를 **둘**로 줄여라:
     · /workspace/sionna/outputs/renders/outdoor01_wide.png — 굽는 스크립트가 있는 것
     · 거리 협곡은 **/workspace/sionna/outputs/figs_builtin_scenes/simple_street_canyon.png**
       (⭐이 파일이 실제로 있는지, 무엇이 굽는지 먼저 확인해라. 없으면 not_done 에 적고
        canyon_wide.png 를 남기되 그 한계를 warnings 에 적어라.)
   ⛔렌더 이름표에 우리끼리 쓰는 말을 넣지 마라 — «our outdoor scene» ·
     «street canyon, comes with the solver» 정도.

③ 드론 높이가 한 값으로 적혀 있는데 실제로는 장면마다 다르다.
   :39 ALT_M = 20.0 이지만 — 우리 씬은 20 m(elevation_sweep_md.py:122 ENV_SPECS["outdoor01"]),
   솔버가 주는 씬은 **25 m**(elevation_sweep_md.py:118 ENV_BUILTIN_ALT = 25.0).
   ⭐두 값을 직접 열어 확인하고, 도면이나 아래 설명줄에 **둘 다** 적어라.

④ :109 의 «scenes    open sky · our outdoor scene · two shipped with the solver» 가
   장면 넷을 약속하는데 v14 에 결과가 실리는 장면은 셋(빈 하늘 · 우리 씬 · 거리 협곡)이다.
   뮌헨을 빼라 → «one shipped with the solver».
   :115-116 credit 줄도 같은 기준으로 손봐라.
   ⚠뮌헨을 빼는 까닭을 numbers_for_notes 에 적어 둬라 — /workspace/sionna/outputs/
     builtin_scene_diagnosis_0908.json 의 geometry.scenes.munich 를 열어 무엇이 적혀 있는지
     읽고 그대로 인용해라(짐작 금지).

⑤ 발표자 노트용: 지금 :34-37 이 원장에서 읽는 값이 무엇인지, 손으로 박힌 상수가 무엇인지
   (:38-40 RANGE_M · ALT_M · N_POS) 갈라서 numbers_for_notes 에 적어라.
   ⛔「아래 넉 줄은 모든 그림에 공통」은 **거짓**이다 — 되돌림 깊이가 2 쪽(1)과 나머지(2)에서
     다르다. 조건줄에 «공통» 이라는 말이 있으면 빼라.

■ 마지막
  CUDA_VISIBLE_DEVICES="" 로 다시 굽고 f_setup.png 를 **Read 로 열어** 세 각도가 그려졌는지,
  렌더가 둘로 줄었는지, 높이 둘이 적혔는지 눈으로 확인해라.`,
  },
  {
    key: 'outdoor',
    label: 'bake_outdoor.py',
    prompt: `■ 네 파일 — /workspace/team_meeting/teammeeting_0910/bake_outdoor.py
  (⛔다른 빌더 파일은 건드리지 마라. 같은 시간에 다른 에이전트가 고치고 있다.)

이 빌더가 굽는 것 다섯: f_outdoor_stft · f_outdoor_parts · f_outdoor_scenes ·
f_outdoor_defect · f_outdoor_shipped. v14 는 이 가운데 넷을 쓴다.

■ 고칠 것

① ⭐날개끝 안내선 앙각 보정 — 위 「이미 검산이 끝난 사실」 그대로.
   :52 FTIP 를 :120 의 MS.draw(ax, t_, f_, S_, FTIP, ...) 에 넘기고 있다.
   이 빌더의 판들은 앙각 **0 이 아니다**(30°·60° 등). 각 판의 실제 앙각을 코드에서 읽어
   f_tip(el) 을 넘겨라. ⛔-60° 판은 지금 안내선이 참값의 거의 두 배 자리에 있다.

② ⛔⛔**철회된 주장이 주석에 살아 있다** — 반드시 고쳐라.
   :241-243 과 :360-364 근처의 「우리 씬에서만 난다」 · 「우리가 만든 씬에는 결함이 있다」.
   /workspace/sionna/outputs/outdoor_dip_origin_0908.json 을 열어 summary 를 읽어라 —
   RETRACTED_ours_only 가 무엇으로 적혀 있는지 확인하고, 그 원장이 실제로 적어 둔 수를
   인용해 주석을 고쳐라. ⛔새 결론을 짓지 마라 — 원장에 적힌 것만 옮겨라.

③ f_outdoor_defect 의 두 열이 짝이 안 맞는다 — :305 근처가 왼쪽에 «envoutdoor01_ground_»
   (지면만 판)를 쓰면서 이름표는 «our scene» 이고, 오른쪽은 온전한 협곡이다.
   ⭐먼저 «envoutdoor01_» (온전한 우리 씬) 샤드가 그 앙각에 실제로 있는지 세어 확인해라.
     있으면 태그를 바꿔 짝을 맞춰라. 없으면 고치지 말고 이름표를 사실대로 고쳐라
     («our scene, ground only»). 어느 쪽을 골랐는지 edits 에 적어라.

④ 조건줄 고치기
   · :180-181 (f_outdoor_stft) — 우리 씬. 드론 높이 20 m 가 이미 적혀 있는지 확인.
   · :405-406 (f_outdoor_shipped) — 거리 협곡. **드론 높이 25 m 가 어디에도 없다**
     (elevation_sweep_md.py:118 ENV_BUILTIN_ALT = 25.0). 넣어라.
   · 모든 조건줄·이름표의 «diffuse scattering only» 를 고쳐라 — elevation_sweep_md.py:872 에서
     los 와 specular_reflection 이 **늘 True** 임을 확인하고, «no bending around edges» 로 바꿔라.

⑤ ⭐새 그림 하나 — f_outdoor_same_event.png (v14 의 12 쪽)
   목적: 「우리 씬이 깨진 것이 아니라, 두 씬 모두에서 같은 일이 난다」를 **그림으로** 보인다.
     지금은 발표자 노트에만 있고, f_outdoor_defect 는 오히려 철회된 주장을 그림으로 가르친다.
   짜임: 2 행 × 2 열.
     열 = 우리 씬 / 거리 협곡(솔버가 준 것)
     행 = «as recorded» / «with the open-sky record subtracted»
   조건: 팔 R0D0E0F1 · 15 m · 내려다보는 각 60° · 깊이 2 · 광선 4e9 · 앞 1,200 자세
     (f_outdoor_defect 와 같은 창 — 그 함수를 열어 실제 창 크기를 읽고 맞춰라).
   ⭐아랫줄은 D = E_그장면 − E_빈하늘 의 크기를 자세 번호에 대해 그린다.
   ⛔행마다 세로 눈금을 **같게** 해라 — 두 열을 견주는 그림이다.
   ⛔숫자 배지·판정 배지·네모 상자를 얹지 마라. 축 이름·이름표는 청중 말로.
   ⛔새 발주를 내지 마라 — 이미 있는 샤드만 쓴다. 샤드가 없으면 굽지 말고 not_done 에 적어라.
   ⭐먼저 두 장면의 그 앙각 샤드가 **둘 다 있는지** 세어 확인하고 시작해라.

■ 마지막
  CUDA_VISIBLE_DEVICES="" 로 다시 굽고, 고친 png 를 **Read 로 열어** 눈으로 확인해라.
  numbers_for_notes 에 원장에서 읽은 수를 출처와 함께 적어라 — 특히
  outputs/hampel_vs_handrule_0908.json 의 summary.by_scene 과
  outputs/outdoor_dip_origin_0908.json 의 scene_rows.
  ⛔인용하면 안 되는 수가 있으면 warnings 에 적어라.`,
  },
]

phase('Fix')
log('빌더 셋을 각각 고친다 — 파일이 겹치지 않는다')

const fixed = await parallel(TASKS.map(t => () =>
  agent(RULES + '\n\n' + t.prompt, { label: 'fix:' + t.key, phase: 'Fix', schema: OUT_SCHEMA })))

const ok = fixed.filter(Boolean)
log('고침 ' + ok.length + '/3 · 다시 구운 png ' + ok.flatMap(r => r.baked || []).length + ' 장')

const CHECK_SCHEMA = {
  type: 'object',
  properties: {
    pass: { type: 'boolean', description: '지시받은 것이 실제로 고쳐졌나' },
    problems: { type: 'array', items: { type: 'string' }, description: '아직 남은 문제 · 새로 생긴 문제' },
    insider_words: { type: 'array', items: { type: 'string' }, description: '그림 안 글자 가운데 청중이 모를 말' },
    detail: { type: 'string' },
  },
  required: ['pass', 'problems', 'detail'],
}

phase('Check')
const FIGS = [
  'f_window_stft.png', 'f_window_ladder.png', 'f_window_rays.png',
  'f_setup.png', 'f_outdoor_stft.png', 'f_outdoor_parts.png',
  'f_outdoor_shipped.png', 'f_outdoor_defect.png', 'f_outdoor_same_event.png',
]
log('구워진 그림 ' + FIGS.length + ' 장을 열어 확인한다')

const checks = await parallel(FIGS.map(f => () =>
  agent(RULES + `

■ 네 일 — 그림 한 장을 **눈으로** 검사한다.

/workspace/team_meeting/teammeeting_0910/figs/` + f + ` 를 Read 로 **열어서** 본다.
(없으면 pass=false 로 두고 problems 에 «파일이 없다» 를 적어라. figs/ 말고 다른 자리에
 있을 수도 있으니 find 로 한 번 찾아보고 판단해라.)

보는 것:
  ① 잘린 글자가 있나 — 범례·축 이름·제목·조건줄이 판 밖으로 나가지 않았나
  ② 겹친 글자가 있나
  ③ ⛔청중이 모를 말이 있나 — 우리가 만든 지표 이름, 코드에서 샌 말,
     분야 밖 전문어(closed form · nose-on · dBsm · SBR · PO · PathSolver 같은 도구 이름).
     찾으면 insider_words 에 **그대로** 적어라.
  ④ ⛔판정 배지·네모 상자·숫자 배지가 얹혀 있나
  ⑤ 흰 파선(날개끝 자리)이 있으면, 그 판의 앙각에 맞는 자리인가.
     ⭐f_tip(el) = 1272.07 · cos(el) Hz 다. 조건줄에서 그 판의 앙각을 읽고
       파선이 세로축 어디에 있는지 눈으로 재서 견줘라. 세로축 눈금이 안 보이면 그렇게 적어라.
  ⑥ 두 열·두 행을 견주는 그림이면 눈금이 같은가

⛔「좋다/나쁘다」 평을 쓰지 마라. 보이는 것만 구체로 적어라.`,
    { label: 'check:' + f.replace('.png', ''), phase: 'Check', schema: CHECK_SCHEMA })))

const bad = checks.filter(Boolean).filter(c => !c.pass || (c.problems || []).length)

return {
  fixes: ok.map((r, i) => ({ file: TASKS[i] && TASKS[i].label, ...r })),
  checks: checks.filter(Boolean).map((c, i) => ({ fig: FIGS[i], ...c })),
  still_broken: bad.length,
  insider_words: checks.filter(Boolean).flatMap(c => c.insider_words || []),
}
