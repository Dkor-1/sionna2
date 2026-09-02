# 재개 지점 — 2026-09-02 (세션 끊김 대비)

## ⭐지금 하던 것 — 「ECA 라 부르던 것은 사실 0 Hz 노치」 정정

사용자 지적으로 시작. 저장소에 `eca` 가 **둘**인데 서로 다른 물건이었다.

| | 무엇 | 기준채널 | 우리 앙각 스윕에 맞나 |
|---|---|---|---|
| `src/passive_process.eca(surv, ref, n_taps)` | **진짜 ECA** — 기준채널 지연 복사본의 부분공간에 투영해 뺀다. 패시브 바이스태틱 | 필요 | ⛔안 맞다(기준채널 없음) |
| `benchmark/clutter_parts_ladder_0824.cs_eca(x, fcut)` | **도플러 0 Hz 노치** — DFT 에서 \|f\| ≤ fcut 칸을 0 으로 | 없음 | ✅맞다 |

⭐우리 기하는 **모노스태틱**이다(`elevation_sweep_md.py` 의 `baseline=0.0`).
⇒ **연산은 맞고 이름이 틀렸다.** 0 Hz 노치는 모노스태틱 CW 정지클러터 제거의 정석이다.

### 실측 (el 0 · matrice4e · 8,192 자세 · PRF 19,700)
```
도플러 격자          2.40479 Hz  (= 19700/8192)
|f| ≤ 100 Hz         83 칸       (k = 0…41 과 -1…-41)
                     83/8192 = 1.013 %  ·  비DC 82/8191 = 1.001 %
날개 박자 126.7 Hz   노치 가장자리보다 26.7 Hz 위 — 신호를 안 건드린다
몸통 상수            6.879e-04 → 3.2e-23   (100.0000 % 제거)
낙차 58 자세 변동 몫  99.3 % → 98.4 %       (거의 안 지워진다)
```
⛔**내가 어제 「84 칸」이라 썼는데 83 이 맞다.** 레포트 12 가 처음부터 83 으로 맞게 적고 있었다.
   고친 곳: `clutter_parts_ladder_0824.py` 독스트링 · 덱 v4 JSON 노트 3 장.

### 「STFT 에서 도플러 0 이 왜 안 비나」 (사용자 질문 · 측정 완료)
⓵ **STFT 는 다른 창으로 다시 본다** — 노치는 기록 전체(8,192점, 격자 2.40 Hz)에서 걸었는데
   STFT 창은 560 점이라 칸 간격 **35.2 Hz**. 노치 폭 ±100 Hz 안에 STFT 칸이 **5 개**뿐.
⓶ **임펄스는 대역 전체에 퍼져 있다** — 낙차만 남긴 신호의 \|f\|≤100 Hz 평균 대 500~2000 Hz
   평균이 **2.1 dB** 차. 거의 평평 → 0 Hz 둘레만 도려내는 노치에 안 걸린다.
⚠**낙차를 지우면 0 Hz 칸이 −4.5 → −0.1 dB 로 오히려 밝아진다**(판 최댓값이 같이 내려가서).
   ⇒ 낙차는 원인의 **일부**지 전부가 아니다. 「낙차가 0 Hz 를 채운다」로 결론짓지 말 것.
⇒ 답: **「0 Hz 가 비어야 한다」는 노치를 건 그 DFT 에서만 참이다.**

## ✅이번 세션에 끝낸 것
- `benchmark/outdoor_scene_0901.py` 방법표: 「투영 소거」 → 「직각 노치」
- `src/build_report12_outdoor.py`: 「ECA 계열 부분공간 소거」 → 「도플러 0 Hz 노치」
- `benchmark/switch_clutter_stft_0818.py`: ⓑ 팔 이름·독스트링 2 곳
- `src/report14_stap.py`: 비교 라벨
- `clutter_parts_ladder_0824.py` 독스트링 84 → 83
- 덱 v4 JSON: 84 → 83 · 노트 3 장에 「0 Hz 가 왜 안 비나」 추가
- ⇒ **원본(.py)에는 오기가 남아 있지 않다**(grep 확인)

## ⚠바로 다음에 할 것
1. ⭐**노트북 2 권 재빌드** — 원본은 고쳤지만 노트북에 옛 글이 박혀 있다:
   - `reports/05_2_switch-grid.ipynb`  ← `benchmark/switch_clutter_stft_0818.py`
   - `reports/12_outdoor-scene.ipynb`  ← `src/build_report12_outdoor.py`
   ⛔노트북을 손으로 고치지 않는다. 빌더 → `src/build_volumes.py` 순서.
   ```
   PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/build_report12_outdoor.py
   ```
2. **덱 v10 재빌드** — v4 JSON 을 고쳤으므로 `_out_0903_v10.pptx` 를 다시 낸다
   (`/workspace/team_meeting/teammeeting_0903/`)
3. 나머지 ECA 언급 레포트 14 권은 **대부분 진짜 ECA(패시브 바이스태틱)라 정상**이다 —
   `cs_eca` 를 쓰는 레포트는 **12 뿐**이었다. 05_2 는 자체 노치 구현.

## 그 밖 미결 (발표와 무관 · 다음 주)
- Part 1(슬라이드 3/4/5)은 아직 **깊이 1**, Part 3 는 깊이 2 — `partsprop` 이 깊이 1 에만 있다
- 빌더 2 개가 **내 패치 이전부터** 깨져 있다: `build_report18_switch_grid.py`(KeyError 'edge only') ·
  `build_part12_elevation.py`(ContractError)
- 레포트 감사 serious 41 / minor 13 미적용 — `docs/AUDIT_REPORTS_0901.md`
- 레포트 12 를 `src/build_volumes.py` 의 `VOLUMES` 에 등록
- 낙차 2/3 기작 **미상** · el −60 은 낙차를 메워도 \|corr\| 0.39 (둘째 원인 있음) ·
  el −15 는 0°/−30° 어느 쪽과도 다름(산포 0.146 · 낙차 0 개)
- 큐 `runners/jobs_0902_resume.txt` — 다음 주 몫
