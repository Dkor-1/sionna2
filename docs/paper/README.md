<!-- 생성물 — `src/make_reports_index.py` 가 쓴다. 조각 본문은 각 부 빌더가 쓴다. -->

# 논문 조각 — 목차

읽기 경로 ④ 다. **리포트 본문에는 논문 문장이 없다** — 사용자 지시로 논문·재현 서술은
리포트에서 빼고 여기 모았다. 조각마다 «어느 편에서 왔나» 가 붙어 있다.

| 조각 | 무엇 | 어디서 왔나 |
|---|---|---|
| [`00_novelty.md`](00_novelty.md) | 무엇이 새로운가 | 부 2 — 옛 report01 §0 |
| [`01_prior.md`](01_prior.md) | 선행연구 문단 | 부 2 — 옛 report01 §9 |
| [`02_target.md`](02_target.md) | 표적 모델 방법 문단 | 부 3·4·5 — 옛 report02 methods |
| [`03_illuminators.md`](03_illuminators.md) | 조명원 방법 문단 + 그림 캡션 | 부 8 — 옛 report03 |
| [`04_detector.md`](04_detector.md) | 검출기 방법 문단 + 그림 캡션 | 부 9 — 옛 report04 |
| [`05_results.md`](05_results.md) | 결과 방법 문단 | 부 10 — 옛 report05 |
| [`06_measurement.md`](06_measurement.md) | 실측 설계 방법 문단 + 방어선 | 부 11 — 옛 report06 |
| [`figs_part10.md`](figs_part10.md) | 부 10 그림의 완결 문장 캡션 | 부 10 |
| [`figs_part11.md`](figs_part11.md) | 부 11 그림의 완결 문장 캡션 | 부 11 |

## 규약

- **그림 캡션이 두 벌이다.** 리포트 본문은 그림마다 **질문 한 줄**을 달고(하우스 규약),
  논문에 그대로 붙일 **완결 문장 캡션**은 본문에서 빠진다. 부 8·9·11 은 그 캡션이
  자기 방법 문단 문서 안에 있고, 부 10·11 은 `figs_part1N.md` 로 따로 서 있다.
- **숫자는 여기서 손으로 고치지 않는다.** 조각은 생성물이고, 값을 바꾸려면 그 편의
  빌더(`src/build_part*.py`)를 고치고 다시 돌린다.
- 편 ↔ 조각 대응은 [`../REPRODUCE.md`](../REPRODUCE.md) 와
  [`../../outputs/reports_index.json`](../../outputs/reports_index.json) 에 있다.

