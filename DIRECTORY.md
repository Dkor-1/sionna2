# 어디에 무엇이 있나

> 2026-09-02 정리. 최상위에 wheel 59 개(2.8 GB)와 옛 세대 노트북 8 개가 깔려 있어
> **정작 리포트가 안 보였다.** 읽는 사람이 볼 것은 `reports/` 하나다.

## 읽는 곳

| | |
|---|---|
| **[`reports/`](reports/)** | ⭐**여기부터.** 본편 11 권 · 별편 8 편. [`01_map.ipynb`](reports/01_map.ipynb) 이 지도다 |
| [`docs/`](docs/) | 규약과 감사 기록. [`CLAIM_GATE.md`](docs/CLAIM_GATE.md) · [`AUDIT_REPORTS_0901.md`](docs/AUDIT_REPORTS_0901.md) · [`RESUME.md`](docs/RESUME.md) |
| [`README.md`](README.md) | 리포트 목차(생성물 — `src/build_volumes.py` 가 낸다) |
| [`CLAUDE.md`](CLAUDE.md) | 이 저장소에서 일할 때의 상시 규약 |

## 만드는 곳

| | |
|---|---|
| `src/` | 커널·빌더. `build_part*.py` → 조각, `build_volumes.py` → 권 |
| `benchmark/` | 실험 스크립트. 원장(`outputs/*.json`)을 낸다 |
| `runners/` | 큐·감독자. `queue_keeper_*.sh` · `worker_supervisor.py` |
| `outputs/` | 원장(JSON) · 그림 · 샤드. **리포트의 모든 숫자가 여기서 온다** |
| `assets/` · `report_mesh/` | 메쉬와 장면 |

## 쌓아 두는 곳

| | |
|---|---|
| `vendor/wheels/` | 설치용 wheel 59 개. ⛔git 에 안 담는다 |
| `archive/legacy_reports/` | 2026-08-16 재편 **이전** 노트북 8 개. 읽지 마라 — `reports/` 가 새 것이다 |
| `work/` | 임시 작업(`scratchpad`, `scratchpad_verify`) |
| `prior_work/` · `refs/` · `jihyuck/` | 선행연구·참고자료 |
| `atlas/` | 마이크로도플러 아틀라스(분석 산출물) |

⛔**발표 자료는 여기 없다** — `/workspace/team_meeting/` 에서만 관리한다(`CLAUDE.md`).

⛔**노트북을 손으로 고치지 않는다.** `reports/*.ipynb` 는 전부 생성물이다 —
`src/build_part*.py` 를 고치고 `src/build_volumes.py` 를 다시 돌린다.
