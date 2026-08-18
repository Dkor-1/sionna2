# `canon_0816/` — 원장을 만드는 생성기 (스크래치패드에서 구조)

## 왜 여기에 있나

`outputs/*.json` 의 상당수가 **스크래치패드(`/tmp/claude-0/…`)에 있는 스크립트**로 만들어졌다.
스크래치패드는 컨테이너가 새로 뜨면 사라진다 — 실제로 옛 세션 생성기 스무 개는 **이미 없어졌고**
그 원장들은 다시 만들 수 없다(아래 «잃은 것»).

2026-08-18, PC 이전 도중에 **아직 살아 있던 것 전부를 저장소로 옮겼다**. 스크립트 24 개는 바이트
그대로 복사했고, 그중 일부가 읽는 입력 데이터 4 개는 `data/` 에 뒀다.

## 1. ⭐앙각 원장을 읽는 것 — 「판정 재실행」의 실체

`outputs/elevation_sweep_md.json` 이 갱신되면 **다시 돌려야 하는 것들**이다. 층 순서는
의존 그래프에서 나왔고 `runners/run_verdicts_0818.sh` 가 그대로 집행한다.

| 층 | 생성기 | 원장 |
|---|---|---|
| 1 | `frame_completion_0816.py` | `frame_completion_0816.json` — 표준 프레임 완성표 |
| 1 | `build_material_verdict.py` | `material_verdict_0816.json` — 재질 정정 판정 |
| 2 | `build_airframe_canon_verdict.py` | `material_canon_0816_airframes.json` — 기체 교차 판정 |
| 2 | `write_h5.py` | `material_canon_0816_h5_refraction.json` |
| 2 | `ladder_final.py` | `material_canon_0816_ladder.json` — 프롭 두께 사다리 |
| 4 | `build_material_canon.py` | `material_canon_0816.json` — 재질 정본 |
| 4b | ⚠`fix_canon.py` | 위 원장을 **덧칠**한다 (§3) |
| 5 | `make_prereg.py` | `noise_main_prereg_0816.json` — 잡음 본판 사전등록 (간접) |

`ladder_canon.py` 는 `ladder_final.py` 의 **옛 판**이다(원장이 밝힌 생성자는 final 쪽). 참고로만 둔다.

## 2. 앙각 원장과 무관한 것 (한 번 만들고 끝난 원장)

| 생성기 | 원장 |
|---|---|
| `build_prop_identity.py` | `prop_identity_0816.json` |
| `audit6_prop_area.py` · `s7_final.py` | `reference_props.json` |
| `xcheck_mini2_exact.py` · `xcheck_mini2_thickness.py` | `prop_measure_mini2_reference_0816.json` |
| `m6_m4e_cad.py` | `meshfix_matrice4e.json` |
| `m_out.py` | `mesh_adv_refute_pitch_tip_0816.json` |
| `build_output.py` | `mesh_audit_0816_topology_physics.json` |
| `make_report.py` | `mesh_audit_0816_scale_anchor.json` |
| `write_ledger.py` · `write_ledger3.py` | `mesh_inspect_internal_metal_0816.json` |
| `build_md_class_ledger.py` | `md_classification_dl_survey.json` |
| `build_papers_md.py` | `team_meeting/dl_framework_papers/PAPERS.md` |
| `audit.py` | `refute_coinflip_numbers_audit.json` (아틀라스 그림 검사) |
| `diag.py` | `restruct_diagnose.json` |

## 3. ⛔⛔덧칠 스크립트 — 빌더를 다시 돌리면 **지워진다**

`fix_canon.py` 는 별도 적대적 검산 세션이 `material_canon_0816.json` 을 **만든 뒤에 고친** 것이다.
실측으로 확인했다: 디스크의 정본에는 `adversarial_recheck_0816_2049kst` 키가 있는데
`build_material_canon.py` 를 다시 돌린 결과물에는 **없다**. 그 안에는 DC 밴드 앙각별 표 신설
(«6.613 은 정면 값인데 빗각에 쓰고 있었다» 정정) 같은 실제 수정이 들어 있다.

⇒ **재실행 규칙**: `build_material_canon.py` 를 돌렸으면 **반드시 이어서 `fix_canon.py`** 를 돌린다.
`runners/run_verdicts_0818.sh` 의 층 4 가 그 순서를 강제한다.

## 4. ⚠`/tmp` 를 아직 가리키는 스크립트 아홉 개

`audit6_prop_area.py` · `build_md_class_ledger.py` · `build_output.py` · `m6_m4e_cad.py` ·
`m_out.py` · `make_report.py` · `s7_final.py` · `write_ledger*.py` · `xcheck_mini2_*.py` 는
입력 경로가 옛 스크래치패드다. **스크립트 바이트를 안 바꾸려고 경로는 그대로 뒀고**, 그 입력 중
파일로 특정되는 넷은 `data/` 에 복사해 뒀다:

| 파일 | 쓰는 스크립트 |
|---|---|
| `data/dji_prop.json` | `audit6_prop_area.py` |
| `data/part1.json` | `write_ledger.py` |
| `data/part2.json` | `write_ledger3.py` |
| `data/xcheck_mini2_exact.json` | `xcheck_mini2_exact.py` |

다시 돌리려면 이 파일들을 스크립트가 기대하는 경로로 되돌려 놓거나 스크립트 상단의 경로 상수를
`data/` 로 고친다. ⚠나머지 다섯은 스크래치패드 **디렉터리**를 훑는 코드라 무엇을 읽는지가 실행
시점에 정해진다 — 완전 복구는 보장 못 한다.

## 5. 잃은 것 (정직하게 적어 둔다)

아래 생성기는 이미 사라졌고 복구 경로가 없다. 해당 원장은 **재생성 불가**이며 인용할 때
«생성기 유실» 을 함께 적는다:

`build_das_fleet_spec_v2.py` · `verify_comparability_yuan.py` · `build_meshdef_spec.py` ·
`build_meshgate_fisheye.py` · `mkplan.py` · `mkplan_16_17.py` · `build_specs.py` ·
`refute_coinflip.py` · `refute_coinflip_counterexamples.py` · `refute_comb.py` ·
`survey2.py` · `build_valfeas.py` · `viz_mesh_photo.py` — 그리고 `_meta.generator` 가
«ad-hoc»·«scratchpad»·«각도» 처럼 **파일 이름이 아닌** 원장 여섯 개.

⇒ 앞으로 원장을 만드는 스크립트는 **처음부터 저장소 안**에 둔다. 스크래치패드는 일회용 실험용으로만.
