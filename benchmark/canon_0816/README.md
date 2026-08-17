# `canon_0816/` — 판정 원장을 만드는 생성기 (스크래치패드에서 구조)

## 왜 여기에 있나

`outputs/*.json` 중 아홉 개는 `_meta.generator` 가 **`scratchpad/…`** 로 적혀 있었다.
스크래치패드는 `/tmp` 아래라 **컨테이너가 새로 뜨면 사라진다**. 실제로 옛 세션의 생성기
스무 개는 이미 없어졌고(아래 «잃은 것»), 그 원장들은 **다시 만들 수 없다**.

2026-08-18, PC 이전 도중에 **아직 살아 있던 아홉 개를 저장소로 옮겼다**. 내용은 손대지 않았다
(바이트 그대로 복사). 경로는 전부 `/workspace/sionna` 절대경로라 저장소 안에서 그대로 돈다.

## 무엇이 무엇을 만드나

| 생성기 | 원장 | 앙각 원장을 읽나 |
|---|---|---|
| `frame_completion_0816.py` | `outputs/frame_completion_0816.json` — 표준 프레임 완성표 | ✅ |
| `build_material_verdict.py` | `outputs/material_verdict_0816.json` — 재질 정정 판정 | ✅ |
| `build_material_canon.py` | `outputs/material_canon_0816.json` | ✅ |
| `build_airframe_canon_verdict.py` | `outputs/material_canon_0816_airframes.json` — 기체 교차 판정 | ✅ |
| `ladder_final.py` | `outputs/material_canon_0816_ladder.json` — 프롭 두께 사다리 | ✅ |
| `write_h5.py` | `outputs/material_canon_0816_h5_refraction.json` | ✅ |
| `make_prereg.py` | `outputs/noise_main_prereg_0816.json` — 잡음 본판 사전등록 | ✗ (간접 — `noise_distance_frame`·`material_canon_0816`·`detection_curves` 를 읽는다) |
| `audit.py` | `outputs/refute_coinflip_numbers_audit.json` | ✗ (아틀라스 그림 검사) |
| `diag.py` | `outputs/restruct_diagnose.json` | ✗ |

⭐**위 표의 ✅ 여섯은 `outputs/elevation_sweep_md.json` 을 직접 읽는다** — 즉 앙각 원장이 갱신되면
**다시 돌려야 하는 것들**이다. 이것이 `docs/RESUME.md` 가 말하는 «판정 재실행» 의 실체다.
`make_prereg.py` 는 한 다리 건너다 — 앞선 원장들이 갱신된 **뒤에** 돌린다.

## 잃은 것 (정직하게 적어 둔다)

아래 생성기는 이미 사라졌고 복구 경로가 없다. 해당 원장은 **재생성 불가**이며, 인용할 때는
«생성기 유실» 을 함께 적는다:

`build_das_fleet_spec_v2.py` · `verify_comparability_yuan.py` · `build_meshdef_spec.py` ·
`build_meshgate_fisheye.py` · `mkplan.py` · `mkplan_16_17.py` · `build_specs.py` ·
`refute_coinflip.py` · `refute_coinflip_counterexamples.py` · `refute_comb.py` ·
`survey2.py` · `build_valfeas.py` · `viz_mesh_photo.py` — 그리고 `_meta.generator` 가
«ad-hoc»·«scratchpad»·«각도» 처럼 **파일 이름이 아닌** 원장 여섯 개.

⇒ 앞으로 원장을 만드는 스크립트는 **처음부터 저장소 안**에 둔다. 스크래치패드는 일회용 실험용으로만.
