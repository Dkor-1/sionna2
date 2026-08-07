# 재현 — 부 6 · 표적 사다리

*생성: `src/extract_part_docs.py`. 이 표의 명령·출력·소요는 각 편의 여는 블록에서 기계적으로 뽑은 것이라 리포트와 어긋날 수 없다.*

| 편 | 앵커 | 무엇을 만드나 | 출력 | 소요 |
|---|---|---|---|---|
| 30 | `ladder-three` | 사다리가 하나가 아니라 셋이었다 — 여섯 단이 서로 다른 운동학을 쓰고 있었다 | `outputs/report16_synthesis.json` | 약 3 초 (CPU — 저장된 위상표 후처리) |
| 31 | `ladder-calibrated` | 몸통은 진짜 CAD, 프로펠러만 갈아 끼운 교정 사다리가 답할 자격이 있는 유일한 축이다 | `outputs/report16_synthesis.json` | 약 3 초 (CPU — 저장된 위상표 후처리) |
| 32 | `ladder-answer` | 모양의 유무는 수십 dB 를 가르고, 모양의 정밀도는 한 자릿수 dB 안에서 논다 | `outputs/report16_synthesis.json` | 약 3 초 (CPU — 저장된 위상표 후처리) |
| 33 | `ladder-premature` | 이 답을 아직 결론이라고 부를 수 없는 이유가 일곱 가지이고, 그중 둘이 치명적이다 | `outputs/report16_verify_tautology.json`, `outputs/report16_verify_kernel.json`, `outputs/report16_verify_detector.json`, `outputs/report16_synthesis.json` | 약 40 분 (GPU 1장 — 커널 렌즈의 가림 재계산이 대부분) |

## 명령

### 편 30 `ladder-three`

```bash
PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report16_synthesis.py
```

### 편 33 `ladder-premature`

```bash
PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report16_verify_tautology.py
PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report16_verify_kernel.py
PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report16_verify_detector.py
```


## 입력 지문 (sha256 앞 12자리)

*출처 `outputs/report16_synthesis.json : meta.provenance`. 사다리 여섯 단이 서로 다른 파일에서 오므로, 어느 판을 이어 붙였는지가 여기서 확인된다.*

| 입력 | sha256 (앞 12) |
|---|---|
| `outputs/report16_base.json` | `ec7a8b0a8f9b` |
| `outputs/report16_base_tables.npz` | `876d1fb0dd09` |
| `outputs/report16_rung_sphere_eqvol_tables.npz` | `9be315068684` |
| `outputs/report16_rung_cube_eqvol_tables.npz` | `cca681f13cab` |
| `outputs/report16_rung_box_bbox_tables.npz` | `e97af9c13738` |
| `outputs/report16_rung_mesh_no_rotor_tables.npz` | `ba4bcbaf2eea` |
| `outputs/report16_rung_mesh_half_tri_tables.npz` | `cc7b579ce0f1` |
| `outputs/report16_rung_mesh_full_tables.npz` | `8b464b7fa2b1` |
| `outputs/report16_metric_sphere_eqvol.json` | `47b3314a1a72` |
| `outputs/report16_metric_cube_eqvol.json` | `a36cab5e68cb` |
| `outputs/report16_metric_box_bbox.json` | `c4eb677168e3` |
| `outputs/report16_metric_mesh_no_rotor.json` | `2d23b5965c7c` |
| `outputs/report16_metric_mesh_half_tri.json` | `693043847fe3` |
| `outputs/report16_metric_mesh_full.json` | `536036d78abf` |
| `outputs/report16_verify_tautology.json` | `e4f8a8f83da0` |
| `outputs/report16_verify_kernel.json` | `2d6e6e171800` |
| `outputs/report16_verify_detector.json` | `700dd70f0e41` |
| `outputs/p3_validation_v2.json` | `380a0f40ac9c` |

게이트: G1 PASS · G2 PASS · G3 PASS · G4 PASS
