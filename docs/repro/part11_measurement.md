# 재현 — 부 11 · 실측 설계

*생성: `src/extract_part_docs.py`. 이 표의 명령·출력·소요는 각 편의 여는 블록에서 기계적으로 뽑은 것이라 리포트와 어긋날 수 없다.*

| 편 | 앵커 | 무엇을 만드나 | 출력 | 소요 |
|---|---|---|---|---|
| 67 | `hardware` | X410 의 12-bit ADC 동적범위가 직접파 제거의 천장이다 | `outputs/report06_measurement.json`, `outputs/measurement_plan.json`, `outputs/report06_derived.json` | 약 10 초 (CPU) |
| 68 | `sigma-checklist` | 교정된 절대 σ 를 만드는 조건은 여섯 항목이 전부다 | `outputs/report06_measurement.json`, `outputs/measurement_plan.json`, `outputs/report06_derived.json` | 약 10 초 (CPU) |
| 69 | `site-geometry` | 가장 보수적인 D 정의로도 세션 거리 하나가 두 기체 세 밴드를 덮는다 | `outputs/report06_measurement.json`, `outputs/measurement_plan.json`, `outputs/report06_derived.json` | 약 10 초 (CPU) |
| 70 | `calibration-sphere` | 구가 σ 를 절대량으로 만들고, 반경 17.8 cm 를 고른다 | `outputs/report06_measurement.json`, `outputs/measurement_plan.json`, `outputs/report06_derived.json` | 약 10 초 (CPU) |
| 71 | `subband` | 표적을 한 거리빈에 넣는 최대 대역은 200 MHz 다 | `outputs/report06_measurement.json`, `outputs/measurement_plan.json`, `outputs/report06_derived.json` | 약 10 초 (CPU) |
| 72 | `attitude` | 각도표본을 λ/4D 로 잡아 앵커 문헌의 고정 2° 보다 촘촘하게 간다 | `outputs/report06_measurement.json`, `outputs/measurement_plan.json`, `outputs/report06_derived.json` | 약 10 초 (CPU) |
| 73 | `three-layers` | σ(f) 레인지·파형축·비행검출로 층을 나눈다 | `outputs/report06_measurement.json`, `outputs/measurement_plan.json`, `outputs/report06_derived.json` | 약 10 초 (CPU) |
| 74 | `sim-vs-meas` | 캠페인이 결판내는 양은 절대값이 아니라 순위다 | `outputs/report06_measurement.json`, `outputs/measurement_plan.json`, `outputs/report06_derived.json` | 약 10 초 (CPU) |
| 75 | `decision-matrix` | 주장마다 판정 범위를 결판·사슬확인·캠페인 밖으로 적었다 | `outputs/report06_measurement.json`, `outputs/measurement_plan.json`, `outputs/report06_derived.json` | 약 10 초 (CPU) |
| 76 | `session-drift` | 기울기 판정의 문턱은 세션간 진폭 재현성이고, σ 사슬 세대를 바꾸면 그 문턱이 손닿는 범위 밖으로 좁아진다 | `outputs/report06_measurement.json`, `outputs/measurement_plan.json`, `outputs/report06_derived.json` | 약 10 초 (CPU) |
| 77 | `size-law-differential` | 두 기체를 함께 재면 크기전이 법칙이 차등신호의 부호 하나로 갈린다 | `outputs/report06_measurement.json`, `outputs/measurement_plan.json`, `outputs/report06_derived.json` | 약 10 초 (CPU) |

## 명령

### 편 67 `hardware`

```bash
PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/plan_measurement.py
PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python -c "import sigma_anchor as S; S.write_measurement_plan()"
PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/make_report06_measurement.py
```
