# 2026-09-12 기준선 — 세 갈래를 시작하기 전의 수

> ⛔이 문서는 손으로 쓰지 않는다. `benchmark/freeze_0912.py` 가 굽는다.
> 지금과 대조하려면 `--check`. 받아들이려면 `--update`(왜 움직였는지 커밋에 적는다).

- 뜬 때 `2026-09-14T05:27:44Z` · 커밋 `a0ae69e41e181de355fa0e6530efab1031e467cf`
- 사용자 지시: 「가·나·다 모두 시행해 볼 수 없을까? 현재까지의 결과들도 잘 보존하고」

## 원장

| | |
|---|---:|
| 칸 | 2408 |
| 그중 완결(자세 8,192 · 결측 0) | 2341 |
| 미완 | 6 |
| 영 전계가 있는 칸 | 14 |
| 잘린 칸 | 14 |
| 세대를 고른 칸 | 4 |
| 팔 | 850 |
| 앙각 | 46 |
| 창고 샤드 | 7718 |

아틀라스 — 주제 9 · 팔 850 · 칸 2408

## 지면이 있으면 기체 사이 레벨이 모인다

⛔같은 팔·거리·예산·앙각에서만 견준다. 기체가 둘 미만이면 안 잰다.

| 앙각 | 기체 | 빈 하늘 퍼짐 | 지면 있음 퍼짐 |
|---|---:|---:|---:|
| el-30 | 1 | — | 기체가 둘 미만 — 못 잰다 |
| el-60 | 3 | 2.44 dB | 0.07 dB |

## 지키는 수

| 원장 | 뜬 필드 수 |
|---|---:|
| `outputs/read_canyonnull_0910.json` | 441 |
| `outputs/read_dropladder_0910.json` | 89 |
| `outputs/read_scenephysics_0913.json` | 1031 |
| `outputs/read_wfsurvive_0912.json` | 36489 |

⛔문자열 포함 검사가 아니라 **수를 그대로** 뜬다 — 사건 수가 바뀌면 --check 가 짚는다.

## 검사기

| 검사 | 종료코드 |
|---|---:|
| row_pointers | 0 |
| retracted | 0 |
| report_links | 0 |

## 세대를 고른 칸

| 팔 | 앙각 | 무엇으로 갈랐나 | 동점 미해결 | 중복 | 갈린 자세 |
|---|---:|---|---|---:|---:|
| `92_az0.05_mfixbatteryi5_blperairframe_d2` | +0 | meta.nshards | False | 0 | 0 |
| `192_az0.1_mfixbatteryi5_blperairframe_d2` | +0 | meta.nshards | False | 0 | 0 |
| `92_az0.05_mfixbatteryi5_blperairframe_d2` | +0 | meta.nshards | False | 0 | 0 |
| `192_az0.1_mfixbatteryi5_blperairframe_d2` | +0 | meta.nshards | False | 0 | 0 |

