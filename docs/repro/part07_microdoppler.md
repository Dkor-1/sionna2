# 재현 — 부 7 · 마이크로도플러

*생성: `src/extract_part_docs.py`. 이 표의 명령·출력·소요는 각 편의 여는 블록에서 기계적으로 뽑은 것이라 리포트와 어긋날 수 없다.*

| 편 | 앵커 | 무엇을 만드나 | 출력 | 소요 |
|---|---|---|---|---|
| 34 | `md-paths-doppler` | 스톡 Paths.doppler 로는 블레이드 변조가 안 나온다 — SceneObject.velocity 가 객체당 강체 1벡터다 | `outputs/report15_probe.json` | 약 7 분 (GPU 1장) |
| 35 | `md-slowtime` | 시간표본마다 자세를 새로 놓고 다시 쏘아 슬로타임 복소열을 만든다 | `outputs/report15b_microdoppler.json`, `outputs/report15b_series.npz` | 약 25 분 (GPU 1장 — 광선 추적이 6칸 × 4팔) |
| 36 | `md-two-engines` | 두 엔진이 날개끝 주파수 아래에서 겹치고 그 위에서 갈린다 | `outputs/report15_po_control.json`, `outputs/report15_verdict_geomref.json`, `outputs/report15_verdict.json` | 약 30 분 (GPU 1장) |
| 37 | `md-rpm` | 네 로터가 같은 회전수로 돌면 무늬는 시간에 못 변한다 | `outputs/report15b_microdoppler.json`, `outputs/report15b_series.npz` | 약 25 분 (GPU 1장 — 광선 추적이 6칸 × 4팔) |
| 38 | `md-occlusion` | 동체가 날개를 가리면 변조 깊이와 레벨이 함께 바뀐다 | `outputs/report15b_microdoppler.json`, `outputs/report15b_series.npz` | 약 25 분 (GPU 1장 — 광선 추적이 6칸 × 4팔) |
| 39 | `md-blade-vs-body` | 블레이드 신호는 약하지 않다 — 동체 정적 반사가 덮고 있을 뿐이다 | `outputs/report15b_microdoppler.json`, `outputs/report15b_series.npz` | 약 25 분 (GPU 1장 — 광선 추적이 6칸 × 4팔) |
| 40 | `md-attitude` | 지상 레이더는 기체를 아래에서 보므로 가림이 무는 자세가 우리 자세다 | `outputs/report15b_microdoppler.json`, `outputs/report15b_series.npz` | 약 25 분 (GPU 1장 — 광선 추적이 6칸 × 4팔) |
| 41 | `md-calibration` | 판정 잣대를 널 팔 15 칸과 이상 점산란자로 먼저 교정했다 | `outputs/report15_null_control.json`, `outputs/report15_verdict_geomref.json`, `outputs/report15_verdict.json`, `outputs/report15_attack_stats.json` | 약 35 분 (GPU 1장 — 널 팔 20 개) |
| 42 | `md-ray-budget` | 두 기체가 갈리는 이유는 메쉬 품질이 아니라 표적 크기 대비 광선예산이다 | `outputs/report15_attack_spp_ladder.json`, `outputs/report15_attack_stats.json` | 약 36 분 (GPU 1장 — 사다리 전량 재추적) |
| 43 | `md-prf` | 상시 기준신호가 주는 것은 날개끝 확산이 아니라 블레이드 통과율까지다 | `outputs/md_range_sweep.json` | 약 12 분 (GPU 1장) |

## 명령

### 편 34 `md-paths-doppler`

```bash
PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_probe.py
```

### 편 35 `md-slowtime`

```bash
PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15b_microdoppler_recompute.py
PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15b_stamp_provenance.py
PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_report15b_figs.py
```

### 편 36 `md-two-engines`

```bash
PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_po_control.py
PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_verdict_geomref.py
PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_verdict.py
```

### 편 41 `md-calibration`

```bash
PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_null_control_v2.py
PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_attack_stats.py
```

### 편 42 `md-ray-budget`

```bash
PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_attack_spp_ladder.py
```

### 편 43 `md-prf`

```bash
PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_md_range.py
```
