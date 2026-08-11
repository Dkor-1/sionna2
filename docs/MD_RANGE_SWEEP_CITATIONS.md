# `outputs/md_range_sweep.json` 인용처 지도 — 재생성 뒤 할 일

작성 2026-08-11 · 원장 재생성이 **도는 중**에 만든 지도다(PID 1317277, `--workers 10
--capture full_waveform`, 03:27 시작). 원장 본체는 **안 읽었다** — 옛 판
`outputs/pre37db/md_range_sweep_pre37db.json`(2026-07-28T06:13)과 이미 끝난 형제 원장
`outputs/md_range_sweep_mf.json`(2026-08-11T01:55)만 읽어서 «무엇이 어떻게 움직이나» 를 쟀다.

> `experiment_md_range.py:418-421` 은 `.tmp` 에 쓰고 `os.replace` 로 갈아끼운다.
> 즉 **반쯤 써 있는 파일을 읽을 위험은 없다.** 그래도 완료 로그를 본 뒤에 읽어라.

---

## 0. 먼저 — 갱신이 필요한 이유가 **둘**이다. 섞지 마라

| | 원인 | 무엇이 움직이나 |
|---|---|---|
| **(A)** | ⭐정합필터 이득 `G_mf = 10log10(B/PRF) = 36.99 dB` 를 잡음 눈금에 넣었다 (`capture="full_waveform"`) | **잡음 팔(A1·A3) 의 모든 지표** + 새 SNR 사다리 키 전부 |
| **(B)** | 2026-07-28 이후 **표적 메쉬·회전수 사양이 바뀌었다** | σ · `dc_ac_db` · `f_tip_hz` · `rpm` · `n_frame_pts` · `n_blade_pts` — 즉 **결정론 키 전부** |

(B) 는 이 라운드의 주제가 아닌데도 **옛 문서의 σ·dc_ac 인용을 전부 낡게 만든다.**
(A) 만 보고 σ 인용을 그대로 두면 안 된다. 실측 대조(pre37db ↔ mf, 같은 코드·같은 자세격자):

| 칸 (3.5 GHz 외 표시) | n_frame_pts | rpm | f_tip [Hz] | σ 방위평균 [dBsm] | `A0.dc_ac_db` [dB] |
|---|---|---|---|---|---|
| mini5pro | 15879 → 17871 | 5500 → 5500 | 989.8 → 989.8 | −20.00 → **−19.31** | 26.48 → **32.77** |
| mavic4pro | 22055 → 19644 | 3600 → 3600 | 1135.1 → 1135.1 | −15.93 → **−16.79** | 37.18 → **5.33** |
| matrice4e | 24185 → 21248 | 3800 → 3800 | 1229.6 → 1229.6 | −18.88 → **−17.53** | 17.26 → **24.86** |
| s1000plus | 85788 → 123435 | **3600 → 4467** | **1619.7 → 2009.8** | −15.90 → **−12.43** | 18.87 → **22.00** |
| phantom4 | 24088 → 26653 | 5500 → 5500 | 1558.8 → 1558.8 | −16.92 → **−17.91** | 32.51 → **32.20** |
| mavic4pro / LTE | 16823 → 17826 | 3600 → 3600 | 597.7 → 597.7 | −14.56 → **−15.84** | 50.79 → **20.32** |
| mavic4pro / WiFi | 35510 → 31510 | 3600 → 3600 | 1689.7 → 1689.7 | −14.11 → **−15.50** | 27.90 → **35.42** |
| s1000plus / LTE | 45554 → 42824 | **3600 → 4467** | **852.9 → 1058.3** | −17.80 → **−15.07** | 22.67 → **18.99** |
| s1000plus / WiFi | 171734 → 257424 | **3600 → 4467** | **2411.1 → 2991.8** | −12.37 → **−9.01** | 39.40 → **32.17** |

⚠ **`dc_ac_db` 산포가 통째로 뒤집혔다.**
문서가 인용하는 범위(**3.5 GHz 5기체**): 옛 **17.26 ~ 37.18 dB** → 새 **5.33 ~ 32.77 dB**.
9칸 전체로는 옛 17.26 ~ 50.79 → 새 5.33 ~ 35.42 dB.
mavic4pro 3.5 GHz 는 **37.18 → 5.33 dB (−31.9 dB)**, 같은 기체 LTE 는 50.79 → 20.32 dB 다.
「③ 총전력 vs ③′ AC 가 기체별 17.3~37.2 dB 다르다」는 헤드라인 문장이 **옛 원장에서 나온 수**다.
⛔ 재생성이 끝나면 **그 문장부터** 새 수로 갈아라(§5 목록).
⚠ 이 −31.9 dB 이동이 왜 났는지 나는 **모른다**. `verify_noise_injection.py` 의 NI10 게이트는
메쉬 지문이 함께 움직였으면 «설명됨» 으로 통과시키는데, mavic4pro 는 지문이 움직였으므로
**게이트는 통과하지만 이해된 것은 아니다.** 인용 전에 별도로 따져라.

### (A) 가 실제로 한 일 — 실측 두 장면

`arms.A3_both.fd_edge_hz` (NaN = 블레이드선이 잡음에 묻힘), 3.5 GHz:

```
pre37db  mini5pro   1m:970  2m:799  5m:NaN 10m:NaN 20m:NaN 50m:NaN
         mavic4pro  1m:1012 2m:1130 5m:NaN 10m:NaN 20m:NaN 50m:NaN
         matrice4e  1m:1195 2m:1049 5m:NaN 10m:NaN 20m:NaN 50m:NaN
         s1000plus  1m:1491 2m:1580 5m:293 10m:NaN 20m:NaN 50m:NaN
         phantom4   1m:1520 2m:1510 5m:NaN 10m:NaN 20m:NaN 50m:NaN
mf(37dB) mini5pro   … 20m:420  30m:NaN
         mavic4pro  … 70m:1012 100m:NaN
         matrice4e  … 30m:1064 40m:NaN
         s1000plus  … 50m:1393 70m:NaN
         phantom4   … 15m:1335 20m:NaN
```

`arms.A3_both.ac_corr_vs_ref` (3.5 GHz 5기체 평균±sd):

| R | pre37db | mf (37 dB 반영) |
|---|---|---|
| 1 m | 0.439 ± 0.205 | 0.419 ± 0.296 |
| 20 m | **0.019 ± 0.008** | **0.625 ± 0.275** |

⇒ 20 m 에서 «패턴이 완전히 사라진다» 가 «절반 넘게 살아 있다» 로 뒤집힌다.
**A1/A3 을 쓰는 그림·문장은 결론 자체가 바뀐다.**

---

## 1. 키별 판정표 — 무엇이 바뀌고 무엇이 안 바뀌나

### 1-1. `cells[]` 최상위

| 키 | (A) 37 dB | (B) 메쉬 | 판정 |
|---|---|---|---|
| `drone` · `band` · `fc_hz` · `lam_m` | 안 바뀜 | 안 바뀜 | **불변** |
| `extent_m` · `r_ff_m` | 안 바뀜 | ⭐**바뀜**(전 칸) | 실측: mavic4pro extent 0.5556 → **0.5957 m**, `r_ff` 3.5 GHz **7.21 → 8.29 m** · WiFi **10.73 → 12.33 m**; mini5pro 3.33 → **3.03**; matrice4e 8.05 → **8.26**; s1000plus 42.41 → **41.29**; phantom4 5.17 → **5.10 m**. ⇒ F4 의 `R/R_ff` 축과 F7 지도가 함께 움직인다 |
| `rpm` · `f_tip_hz` · `v_tip_ms` · `flash_hz` | 안 바뀜 | ⭐**바뀜**(s1000plus) | s1000plus 만 |
| `n_frame_pts` · `n_blade_pts` | 안 바뀜 | ⭐**바뀜**(전 칸) | — |
| `prf_feasibility.*` | 안 바뀜 | `required_prf_hz = 2·f_tip` 이므로 s1000plus 만 | mini5pro 는 **불변** |
| `n_rotors` | 안 바뀜 | 안 바뀜 | **불변** |

### 1-2. `cells[].rows[]`

| 키 | 판정 | 근거 |
|---|---|---|
| `R_m` | 불변 | 격자는 기본값 그대로 |
| `in_farfield` · `R_over_Rff` | (A) 무관 · (B) ⭐**바뀜** | `r_ff_m` 이 전 칸에서 움직였다 |
| `sigma_eq_plane_dbsm` · `sigma_eq_sph_dbsm` · `d_sigma_db` | (A) 무관 · (B) **바뀜** | 순수 PO, 잡음 없음 |
| `d_sigma_aspect_mean_db` · `sigma_eq_aspect_mean_{plane,sph}_dbsm` | (A) 무관 · (B) **바뀜** | 위 §0 표 |
| `snr_sample_{plane,sph}_db` | ⭐**안 바뀜** (사다리 ①) | 다만 (B) σ 가 움직여 값은 이동 |
| `snr_ac_{plane,sph}_db` | ⭐**신규 키** | 옛 원장에 0 개 |
| `snr_convention` · `capture` · `g_mf_db` | ⭐**신규 키** | `capture="full_waveform"`, `g_mf_db=36.9897` |
| `snr_band_*` (①) | 신규(값 = `snr_sample_*`) | — |
| `snr_slow_*` (③ 총전력) ⭐**주입 눈금** | ⭐**신규 · +36.99 dB** | 여기가 37 dB 가 들어간 자리 |
| `snr_slow_ac_*` (③′) ⭐**정본** | ⭐**신규** | `= ③ − dc_ac_off` |
| `dc_ac_off_{plane,sph}_db` · `snr_map_ac_*` (⑤) | ⭐**신규** | — |
| `snr_ladder_{plane,sph}` · `gain_mf_db` · `gain_stft_db` · `gain_stft_nperseg` · `gain_stft_window` | ⭐**신규** | `nperseg = n_t = 6144` |
| `layer_note` · `snr_note` · `d_sigma_note` | 신규/문자열 | — |

### 1-3. `cells[].rows[].arms[]`

| 팔 | 판정 |
|---|---|
| `A0_reference` · `A2_nearfield` (무잡음) | (A) **안 바뀜** · (B) **바뀜**. `dc_ac_db` · `fd_edge_hz` · `flash_contrast_db` · `harmonic_frac` · `ac_energy` · `spec_peak_over_floor_db` · `ac_corr_vs_ref` · `spec_corr_vs_ref` 전부 |
| `A1_snr_only` · `A3_both` (잡음) | ⭐**(A) 로 크게 바뀜** — 위 목록 + 각 `*_sd` 전부 |

⛔ **스키마 파괴 1건**: `arms[].snr_sample_db` 가 **삭제됐다**(`experiment_md_range.py:258-261`).
같은 이름이 행 수준(`rows[].snr_sample_plane_db`)에도 있어 한 원장 안에 두 뜻이었기 때문이다.
대체 키: `snr_injected_db`(값 동일) · `snr_injected_ref` · `snr_injected_layer` ·
`snr_injected_ac_db` · `snr_pre_mf_db` · `noise_seed` · `noise_prov`.
**`arms[].snr_sample_db` 를 읽는 코드가 있으면 KeyError 로 죽는다.** 지금 저장소에서 그걸 읽는
자리는 못 찾았다(§2 확인). 외부 스크립트가 있으면 거기서 깨진다.

### 1-4. `meta`

| 키 | 판정 |
|---|---|
| `slow_time.capture` · `snr.*`(9개) · `noise.*`(8개) · `point_spacing.note` · `ranges_default_m` · `n_noise_default` · `three_layers` · `link_budget.noise_bw_effective_hz` | ⭐**신규** |
| `runtime_s` | **바뀜** (옛 판 2929.6 s) |
| `ranges_m` | **불변** — 이번 런은 `--ranges` 를 안 줬으므로 기본 `[1,2,5,10,20,50,1000]` |
| `n_noise` | **불변** — `--n-noise` 를 안 줬으므로 기본 **8** |

⚠ **재생성되는 `md_range_sweep.json` 은 `md_range_sweep_mf.json` 보다 성기다.**
mf 는 `[1,2,5,10,15,20,30,40,50,70,100,1000]` · `n_noise=32` 다.
관측 한계(R90·R50)는 **8 실현으로는 12.5 % 단위라 못 잰다**(`experiment_md_range.py:309-311`
가 스스로 경고한다). ⇒ **R90 인용은 계속 `md_range_sweep_mf.json` 에서 해라.**

---

## 2. 인용처 — 코드 (`파일:줄` · 읽는 키 · 바뀌나 · 할 일)

### 2-1. 생산자

- [ ] **`src/experiment_md_range.py:52`** — `OUT`. 이 파일이 원장을 **만든다**. 할 일 없음.

### 2-2. 그림 빌더 `src/viz_md_range.py` ⭐**전면 재실행 대상**

| 줄 | 읽는 키 | 바뀌나 | 할 일 |
|---|---|---|---|
| `:42` | `SRC = outputs/md_range_sweep.json` | — | 경로 그대로 두면 됨 |
| `:88-108` `_series_for` | `meta.slow_time.{prf_hz,n_t,n_phase,capture}` · `meta.geometry.*` · `cells[].fc_hz` | ⭐**바뀜** | `capture` 키가 **처음 생긴다**. 지금까지는 `.get(..., "pre_mf")` 로 폴백해 **37 dB 없이** 그렸다(`:98`). 새 원장이면 자동으로 `full_waveform` 으로 간다 → **A1/A3 패널이 훨씬 깨끗해진다** |
| `:97` 주석 | — | — | 「두 값은 ~1.1 dB 다르다」는 옛 σ 대조에서 나온 수다. 새 원장 기준으로 다시 재거나 수치를 빼라 |
| `:153-159` (F2) | `arms[A1,A2,A3].{ac_corr_vs_ref, spec_corr_vs_ref}` | ⭐**A1·A3 크게 바뀜** | 재실행 |
| `:193-198` (F3) | `f_tip_hz` · `r_ff_m` (A2 시계열 재계산) | (B) 만 | 재실행 |
| `:217-220` (F4) | `R_over_Rff` · `arms.A2_nearfield.{ac_corr_vs_ref, flash_contrast_db}` · `r_ff_m` | (B) 만 | 재실행 |
| `:239-251` (F5) | `d_sigma_aspect_mean_db`(있으면) 아니면 `d_sigma_db` · `r_ff_m` | (B) 만 | 재실행 |
| `:269` (F6) | `rows[].snr_slow_sph_db` ← 없으면 `snr_sample_sph_db` | ⭐⭐**축이 통째로 +37 dB 이동** | 재실행. `:270` 의 `ladder` 플래그가 처음으로 True 가 된다 |
| `:280-281` (F6) | `arms.A0_reference.dc_ac_db` · `rows[].dc_ac_off_sph_db` | ⭐**바뀜** | 재실행 |
| `:289-290` (F6) | `arms[A1,A3].ac_corr_vs_ref` | ⭐**바뀜** | 재실행 |
| `:332-342` (F8) | `cells[].f_tip_hz` · `prf_feasibility[m].mode_prf_hz` | (B) s1000plus 만 | 재실행 |

명령: `cd sionna2 && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/viz_md_range.py`
(GPU 안 쓴다 — 이 사슬에 `torch`/`cuda` import 가 **없다**. §6 참조)

### 2-3. 리포트 빌더 — 읽는 키가 좁다

- [ ] **`src/build_part07_microdoppler.py:71,1303,1313,1317,1319,1321,1327,1362,1368-1372,1381`**
  키: `cells[0].prf_feasibility.{LTE CRS,5G SSB,5G NR-PRS}.{required_prf_hz,mode_prf_hz}` ·
  `cells[0].{drone, fc_hz, rpm, f_tip_hz, flash_hz}` · `cells[0].prf_feasibility` 표.
  **`cells[0]` = mini5pro / 3.5 GHz** 이고 mini5pro 는 rpm·f_tip 이 안 움직였다 →
  ⭐**수치는 안 바뀔 것이다.** 그래도 빌더가 원장에서 직접 읽으니 **다시 돌려서 확인**해라.
- [ ] **`src/make_report07_microdoppler.py:50,95-96,239-241`** — 위와 같은 키의 부분집합. 동일.

### 2-4. 벤치마크 — ⭐⭐**구조적 함정이 여기 있다**

세 스크립트가 `md_range_sweep_mf.json` 을 «새 원장», `md_range_sweep.json` 을 «옛 원장» 으로
**하드코딩**해 두었다. 재생성이 끝나면 **그 전제가 뒤집힌다**(둘 다 37 dB 판이 된다).

| 파일:줄 | 지금 전제 | 재생성 뒤 | 할 일 |
|---|---|---|---|
| `benchmark/md_snr_vs_range.py:45-46,66-70` | `SWEEP_NEW=…_mf.json` 우선, 없으면 `…sweep.json` | mf 가 있으니 **계속 mf 를 읽는다** — 동작은 안전 | ⚠`_sweep_source` 독스트링(「새 원장이 있으면 그쪽」)이 뜻을 잃는다. **의도적으로 mf 를 고른다**(격자·실현 수가 R90 에 필요) 고 고쳐 적어라 |
| `benchmark/build_md_noise_range_fig.py:51-52,66-70` | 같음 | 같음 | 같음. 읽는 키: `cells[].rows[0].sigma_eq_aspect_mean_plane_dbsm` · `arms.A0_reference.dc_ac_db` · `f_tip_hz` · `flash_hz` |
| `benchmark/verify_noise_injection.py:314-315,325-400` (**게이트 NI10**) | 「`md_range_sweep.json` = 2026-07-28 옛 판」 | ⛔**거짓이 된다.** 새 판 대 새 판을 비교하게 되어 `worst≈0` 으로 **공허하게 통과**한다 | ⭐**`SWEEP_OLD` 를 `outputs/pre37db/md_range_sweep_pre37db.json` 로 옮겨라.** 안 그러면 게이트가 아무것도 안 지킨다 |

- [ ] **`benchmark/verify_matched_filter_gain.py:189-190`** — `--sigma-dbsm` 기본값 **−18.879**,
  도움말이 「matrice4e 3.5 GHz 방위평균 σ (md_range_sweep.json)」. **옛 값이다**(새: −17.53).
  게이트 판정에는 σ 가 스케일로만 들어가지만, **원장이 아니라 소스에 박힌 복사본**이라
  갱신하고 출처를 `md_range_sweep_mf.json` 으로 바꿔라.
- [ ] **`benchmark/meshdef_spec_judge.py:503`** — `md_range_sweep_s=2929.6` 하드코딩(옛
  `meta.runtime_s`). 새 `runtime_s` 로 갱신. 파급은 비용표뿐.
- [ ] **`benchmark/meshdef_attack_verdict.py:249-250,256,379`** — 위 상수를 그대로 실어 나른다.
  `spec_judge` 를 고치면 따라온다. `:256`·`:379` 의 서술문도 함께.
- [ ] **`benchmark/regen_mesh_dependents.py:152-153`** — 재생성 계획표의 한 줄
  (「마이크로도플러 거리스윕 … future work 강등」). 값 인용 없음. **강등 딱지가 아직 맞는지만**
  판단해라(37 dB 정정으로 이 축의 지위가 올라갔다면 문구를 바꿔야 한다).

### 2-5. 다른 **원장**이 이 원장을 인용한 자리 (JSON 안의 굳은 복사본)

| 파일:줄 | 읽은 키 / 실은 수 | 바뀌나 | 할 일 |
|---|---|---|---|
| `outputs/noise_rotor_plan.json:95` | 「fd_edge NaN 개시가 5 m → **35~42 m** 로 이동」 | ⛔**이미 철회된 예측** | `RETRACTION_LOG` R14 대로 실측 R90 표로 교체 |
| `outputs/noise_rotor_plan.json:98-115` `range_ladder_example` | `sigma_dbsm = -18.879` · `dc_ac_db = 17.3` (matrice4e) + 그로부터 만든 사다리 전체(`snr_band_at_1m_db = 37.77` 등) | ⭐**바뀜** — 새 σ **−17.53**, dc_ac **24.86** | σ·dc_ac 를 새 값으로 놓고 **사다리 전체를 다시 계산**해라. 두 수가 다 움직여 `snr_slow_ac` 는 **두 번** 움직인다 |
| `outputs/s2rj_compare.json:126-128` | `prf_feasibility` 전수 집계: 「0/36 모드-셀 · 0/9 셀 · 필요 PRF **1195.4~4822.2 Hz** · 플래시선 **120.0~183.3 Hz** · 9/9 셀 생존」 | ⭐**한 수만 바뀜** | 실측 재집계: **0/36 · 0/9 · 9/9 는 그대로**, 필요 PRF 상한만 **4822.2 → 5983.6 Hz**(s1000plus f_tip 2411.1 → 2991.8). 플래시선 범위 120.0~183.3 도 **그대로**(s1000plus 만 120.0 → 148.9 로 이동하나 범위 안) |
| `outputs/meshdef_spec.json:4242` · `:1457` | `md_range_sweep_s = 2929.6` | **바뀜** | `meshdef_spec_judge.py:503` 을 고치고 재생성 |
| `outputs/reports_index/md-prf.json:12` | 입력 파일 목록 | — | 리포트 인덱스 재생성 |
| `outputs/md_map_audit.json:687-709` | F1 감사 + `redraw_when` | — | §4 참조 |
| `outputs/pure_po_removal_map.json:212,519` | 「F1~F8 은 어느 빌더도 안 쓴다」 | **불변** | 근거로 인용만 |
| `outputs/lowfreq_attack.json:271` | `meta.bands` 목록 · 「순수 PO 점구름」 | **불변** | — |
| `outputs/detection_engine_*.json` (7개, 예: `detection_engine_sigma_axis.json:162-163`) | `md_range_sweep_mf.json :: meta.engine` · `meta.sigma_eq_note` 문자열 | **불변** | mf 원장을 가리키고, 인용하는 것은 σ 성격 진술뿐 |
| `outputs/s2rj_*.json` · `outputs/reports_adv_p67.json` · `outputs/restruct_exec_plan.json` · `outputs/meshdef_attack*.json` · `outputs/meshfix_attack.json` · `outputs/s2r_assets*.json` | 파일 **이름**만 | **불변** | — |

### 2-6. 키 이름만 언급 (조치 불필요)

`src/microdoppler_nearfield.py:331,581,601` · `benchmark/md_classify_run.py:162` ·
`benchmark/md_classify_dataset.py:897` · `benchmark/verify_snr_convention.py:260` ·
`benchmark/verify_md_nearfield.py:6,24,184` · `docs/REPORT_CODE_MAP.md:263` — 스크립트 **이름**만
가리킨다. 원장 키를 안 읽는다.

⚠ 예외 하나: **`benchmark/verify_md_nearfield.py:161`** 이 「`experiment_md_range.py` 가 36자세로
이미 검증했다(AC 0.334±0.096 @1 m → 0.995±0.004 @20 m)」고 쓴다.
**이 두 수의 출처를 나는 확인 못 했다.** 두 원장 어느 쪽의 `A2_nearfield.ac_corr_vs_ref` 와도
안 맞는다(pre37db 3.5 GHz 5기체: 0.449±0.213 @1 m → 0.990±0.013 @20 m / mf: 0.419±0.296 →
0.991±0.017 / 9칸 전체: 0.361±0.229 → 0.936±0.107). ⇒ **어느 키에서 나온 수인지 밝히고
새 원장 값으로 갈아라. 못 밝히면 수를 지워라.**

---

## 3. 인용처 — 노트북 (빌더가 만든다. 직접 고치지 마라)

- [ ] **`reports/_parts/43_md-prf.ipynb:49,140-150`** — provenance 표 10행.
  키: `cells[0].prf_feasibility.LTE CRS.required_prf_hz`=1980 · `…LTE CRS.mode_prf_hz`=1000 ·
  `…5G SSB.mode_prf_hz`=50 · `…5G NR-PRS.mode_prf_hz`=200 · `cells[0].flash_hz`=183.3 ·
  `cells[0].prf_feasibility` · `cells[0].drone`=mini5pro · `cells[0].fc_hz`=3.5e+09 ·
  `cells[0].rpm`=5500 · `cells[0].f_tip_hz`=989.8.
  **전부 mini5pro → 값은 안 바뀔 전망.** `build_part07_microdoppler.py` 재실행 후 diff 로 확인.
- [ ] **`reports/09_microdoppler-limits.ipynb:658,749-759`** — 위와 같은 10행([^66]~[^76]).
  `make_report07_microdoppler.py` 재실행 후 diff 로 확인.

⚠ VSCode 가 노트북 셀 id 를 덧붙이는 사고가 있었다(메모리 기록). **빌더로만 갱신**해라.

---

## 4. 그림 — 어느 것이 다시 나야 하나

`outputs/figures/md_range_f{1..8}.png` (F1 은 2026-08-10 10:09, 나머지 7장은 2026-07-28 06:35).

| 그림 | 읽는 키 | 다시 내나 | 왜 |
|---|---|---|---|
| **F1** `md_range_f1_spectrogram_grid.png` | 시계열 재계산 + `meta.slow_time.capture` | ⭐⭐**반드시** | 08-10 판도 `capture` 키가 없어 **`pre_mf` 로 폴백**해 그렸다. A1/A3 패널 12칸이 37 dB 만큼 틀리다 |
| **F2** `…f2_attribution.png` | `arms[A1,A2,A3].{ac_corr,spec_corr}_vs_ref` | ⭐⭐**반드시** | A3 @20 m 0.019 → 0.625. **결론이 뒤집힌다** |
| **F3** `…f3_doppler_marginal.png` | A2 시계열 · `f_tip_hz` · `r_ff_m` | ⭕**해야** | (A) 무관. (B) 메쉬로 바뀜 |
| **F4** `…f4_collapse.png` | `R_over_Rff` · A2 `ac_corr_vs_ref`·`flash_contrast_db` | ⭕**해야** | (B) 만 — 다만 **x축(`R/R_ff`) 자체가 이동**한다(`r_ff` 가 −9 % ~ +15 %). 「전 기종이 겹치는가」 라는 이 그림의 질문에 직접 걸린다 |
| **F5** `…f5_dsigma.png` | `d_sigma_aspect_mean_db` · `r_ff_m` | ⭕**해야** | (B) 만. σ 축이라 37 dB 와 무관 |
| **F6** `…f6_snr_wall.png` | `snr_slow_sph_db`(신규) · `dc_ac_off_sph_db`(신규) · A1/A3 `ac_corr_vs_ref` | ⭐⭐**반드시** | **y축이 +37 dB 이동하고**, 처음으로 사다리 라벨이 붙는다(`:270`) |
| **F7** `…f7_farfield_map.png` | `meta.bands` · `radar_scene.target_extent`(원장 아님) | ⭕**해야** | `r_ff` 가 전 칸에서 움직였다 (mavic4pro WiFi 10.73 → 12.33 m). 「1/5/10/20 m 중 몇 개가 근거리장인가」 칸수가 바뀔 수 있다 |
| **F8** `…f8_prf_feasibility.png` | `cells[].f_tip_hz` · `prf_feasibility[m].mode_prf_hz` | ⭕**해야** | s1000plus f_tip 1619.7 → 2009.8 Hz |

⭐**여덟 장 전부 지금 어느 리포트·덱도 안 쓴다.** 세 갈래가 같은 말을 한다:
`grep -rn "md_range_f[1-8]"` 이 원장 두 개 말고는 **0 건** · `outputs/pure_po_removal_map.json:212`
「Sole consumer of md_range_sweep.json. Produces … 8 files on disk, **referenced by no builder**」 ·
`docs/RESUME_0730.md:35` 「미공개 상태 → 삭제해도 리포트 파급 없음」.
⇒ **우선순위는 낮다.** 다만 `viz_md_range.py` 한 번이면 8장이 함께 나온다.

- [ ] **`outputs/md_map_audit.json` `maps.md_range_f1_spectrogram_grid`** — 이 원장이 F1 을
  감사하면서 스스로 **`"redraw_when": "md_range_sweep 원장이 바뀔 때"`** 라고 적어 두었다.
  ⇒ **이 항목이 지금 발동한다.** 같은 블록의 `rerun_cmd` 로 F1 만 다시 낼 수 있다
  (기록된 비용: 근접장 PO 4팔×4거리 재계산 **약 12 분, CPU**). 다시 낸 뒤
  `figure.png.mtime`(현재 「2026-08-10 10:09」)과 `ledger` 표기도 갱신해라.

- [ ] `outputs/figures/md_noise_vs_range.{png,pdf}` (2026-08-11 02:01) — **`…_mf.json` 에서
  나왔다.** 이번 재생성과 무관하니 **다시 내지 마라.** 단 `build_md_noise_range_fig.py:66-70`
  의 폴백 전제(§2-4)만 고쳐라.

---

## 5. 인용처 — 문서 (⭐여기가 실제 위험이다)

> ⚠⚠ **줄 번호는 흔들린다.** 이 지도를 쓰는 동안 메인 세션이 `NOISE_AND_ROTOR_PLAN.md`(03:43) ·
> `RETRACTION_LOG.md`(03:41) · `PLAN_0818.md`(03:41) · `RESUME.md`(03:39) 를 **동시에 고치고 있었다.**
> 아래 줄 번호는 **2026-08-11 03:47 기준**이고, 상태 칸의 ✅ 는 그 세션이 **이미 고친 것**이다.
> ⇒ 줄 번호보다 **앵커 문자열로 grep** 해서 찾아라.

### 5-0. ⭐ 이 라운드가 닫는 미해결 하나 — 「17.3 · 18.9 · 26.5 · 32.5 · 37.2」 의 출처

`docs/RETRACTION_LOG.md:713-715` 가 「**기체별 내역의 원장 출처는 못 찾았다**」고 적어 두었다.
**찾았다.** `outputs/pre37db/md_range_sweep_pre37db.json` →
`cells[].rows[0].arms.A0_reference.dc_ac_db` 가 그대로다(3.5 GHz):

| | matrice4e | s1000plus | mini5pro | phantom4 | mavic4pro |
|---|---|---|---|---|---|
| pre37db 원장 | 17.26 | 18.87 | 26.48 | 32.51 | 37.18 |
| 문서가 인용한 수 | 17.3 | 18.9 | 26.5 | 32.5 | 37.2 |

**5/5 반올림 일치.** ⇒ 출처는 **옛 `md_range_sweep.json`(2026-07-28)** 이고, 지금
`outputs/pre37db/` 에 대피해 있다. 「출처 불명」 딱지를 떼고 **「옛 메쉬 세대의 원장 값」** 으로
바꿔 적어라. `outputs/noise_rotor_plan.json` 의 `gap_db_range = [17.3, 37.2]` 도 같은 출처다.

### 5-1. ⛔ 아직 옛 수가 그대로인 자리 (grep 앵커 · 03:47 기준 줄)

| 상태 | 자리 | 앵커 | 무엇으로 |
|---|---|---|---|
| ⛔ | `docs/NOISE_AND_ROTOR_PLAN.md:338` | `기체마다 dc_ac 가 17.3~37.2 dB 로 달라` | **5.33~32.77 dB** (3.5 GHz 5기체, 현행 메쉬) |
| ⛔ | `docs/NOISE_AND_ROTOR_PLAN.md:228` | `σ −18.879 dBsm·dc_ac 17.3 dB` (§1-3 계산 전제) | σ **−17.53** · dc_ac **24.86** — ⭐**그 아래 사다리 수치 전체가 다시 계산돼야 한다** |
| ⛔ | `docs/NOISE_AND_ROTOR_PLAN.md:311` | `matrice4e·σ = −18.88 dBsm·…·dc_ac 17.3 dB` (§1-3 결과 표 제목) | 같음. 이 표가 **「8/18 덱 헤드라인 후보」**(`:337`) 라 파급이 크다 |
| ⛔ | `docs/NOISE_AND_ROTOR_PLAN.md:788` | `nf.echo_over_noise_db(10**(-18.879/10), 1.0, 3.5e9)` | σ 갱신 후 `snr_band(1 m) = 37.77 dB` 재계산 |
| ⛔ | `docs/NOISE_AND_ROTOR_PLAN.md:67` | `두 규약은 dc_ac_db 만큼(기체별 17.3 ~ 37.2 dB) 다르다` | 바로 아래 `:72-76` 에 **출처 정정 상자는 이미 있다**. 문장 안의 수만 남았다 |
| ⛔ | `docs/RETRACTION_LOG.md:690-691` (R20 본문) | `두 눈금은 기체별 17.3 ~ 37.2 dB` + 다섯 기체 | 5.33~32.77. **순서까지 뒤집힌다** — 옛 최대 mavic4pro 가 새 판의 **최소**(5.33) |
| ⛔ | `docs/RETRACTION_LOG.md:696` | `실제 범위는 17.3 ~ 37.2 dB 이고, 33~37 은 일부 기체만` | 같음 |
| ⛔ | `docs/RETRACTION_LOG.md:707` | `microdoppler_nearfield.py:552 … 측정 dc_ac_db = 17~37 dB` | 줄 번호도 틀렸다 — 실제는 **`src/microdoppler_nearfield.py:651`** |
| ⛔ | **`src/microdoppler_nearfield.py:651`** (코드) | `(측정 dc_ac_db = 17~37 dB)` | **5~33 dB**. ⭐코드 독스트링이라 문서보다 오래 산다 |
| ⛔ | `docs/PLAN_0818.md:161` | `«17.3~37.2 dB»(matrice4e 17.3 · s1000plus 18.9 ·` | `:163` 에 **현행 메쉬 값이 이미 병기돼 있다**. 「옛 메쉬 세대」 딱지만 붙이면 끝 |
| ⛔ | `prior_work/noise_modeling_survey.md:57, 311` | `33~37 dB` | RETRACTION `:705-706` 이 이미 잡아 뒀다. **17.3~37.2 가 아니라 5.33~32.77 로** 가야 한다(두 세대를 건너뛴다) |
| ⛔ | `benchmark/verify_matched_filter_gain.py:190` | `default=-18.879` + 도움말 `(md_range_sweep.json)` | −17.53 · 출처를 mf 원장으로 |
| ⛔ | `benchmark/verify_snr_convention.py:199-201` | `sig = 10.0 ** (-18.879 / 10.0)` · `dc_ac_db=17.3` | 자기정합 게이트라 **판정은 안 뒤집힌다**(스케일). 그래도 굳은 옛 복사본이다 |
| ⛔ | `benchmark/verify_noise_injection.py:196-197` | `sig = 10.0 ** (-18.879 / 10.0)` · `dc_ac_db=17.26` | 같음 |
| ✅ | `docs/NOISE_AND_ROTOR_PLAN.md:300-301` (σ·dc_ac 재료표) | — | **이미 현행 메쉬 값 + mf 원장 출처로 갈렸다** |
| ✅ | `docs/RESUME.md:91-96` (U-5) · `docs/PLAN_0818.md:163` | — | **이미 「옛 메쉬」 배지 + 현행 값 병기** |
| ✅ | `docs/RETRACTION_LOG.md:713-718` | — | **이미 31.9 dB 격차를 적었다.** 남은 것은 §5-0 의 출처뿐 |

### 5-2. ⭕ 전제·출처 표기 — 재생성이 끝나면 해소되는 것

| 자리 | 앵커 | 할 일 |
|---|---|---|
| `docs/NOISE_AND_ROTOR_PLAN.md:444` | `⚠⚠**이미 두 겹으로 낡았다**` | 「두 겹」 → **「세 겹」**(NI10 이 옛 메쉬라는 셋째 겹을 찾았다) + **「2026-08-11 재생성으로 해소」** + 새 `meta.generated` |
| `docs/NOISE_AND_ROTOR_PLAN.md:726` (실행표 6단계) | `❌ CPU 10 workers … 40 min` | **✅ 완료** + 실제 `meta.runtime_s` |
| `docs/RESUME.md:85, 88-89` | `세 겹 — ① G_mf 누락 ② 단일자세 σ ③ …` / `재생성 중` | 표 첫 줄 삭제(그 문서가 `:89`·`:108` 에 스스로 그렇게 적어 뒀다) |
| `docs/RESUME.md:281-282` | `옛 파일을 지우지 말고 **인용 금지 배지**를 meta 에 박아라` | 배지 대상이 **`outputs/pre37db/md_range_sweep_pre37db.json`** 으로 바뀐다 |
| `docs/PLAN_0818.md:85-86, 179-180` | `세 겹으로 낡았다 … 대체 = md_range_sweep_mf.json` | 해소 처리 |
| `docs/PLAN_0818.md:20` | `거리별 관측성 R90 … md_range_sweep_mf.json` | ⭐**그대로 둬라.** R90 은 `n_noise=32`·조밀 격자가 필요하고 재생성판(8 실현·7점)은 못 잰다(§1-4) |
| `docs/RESUME.md:205, 220` · `docs/NOISE_AND_ROTOR_PLAN.md:255, 262` | `g_stft_db … 36.12 dB` | 재생성판도 `nperseg = n_t = 6144` 라 **수는 그대로**. 원장 이름만 「mf 와 재생성판 둘 다」로 |
| `docs/RESUME.md:256` | `형제 에이전트가 낸 새 원장 md_range_sweep_mf.json` | 두 원장의 관계(격자 12점/7점 · 실현 32/8 · **둘 다 37 dB 판**)를 한 줄로 |
| `docs/PLAN_PATHSOLVER_CLASSIFY.md:267` | `NOT an absolute RCS anchor` | **불변**. 할 일 없음 |

### 5-3. ⭕ 서술만 — 할 일 없음 / 확인만

- `docs/NOISE_AND_ROTOR_PLAN.md:118-133` (⛔정정 상자, 실측 R90 표) — **유효.** 다만 재생성판이
  성긴 격자라 다른 인상을 줄 수 있으니 「**R90 은 mf 원장에서만 읽는다**」를 한 줄 못 박아라.
- `docs/RETRACTION_LOG.md:647, 658, 674` (R14) — 역사 서술. 파일명 옆에
  **`(→ outputs/pre37db/ 로 대피)`** 만 붙여라.
- `docs/RETRACTION_LOG.md:672-673, 975` — `outputs/noise_rotor_plan.json` 의 「5 m → 35~42 m」가
  **아직 옛 문장**이라고 그 문서가 이미 적어 뒀다. §2-5 와 같은 항목이다.
- `docs/RESUME_0729.md:279` · `docs/S2R_JEPA_POSITION.md:6, 584` · `docs/REPORT_CODE_MAP.md:263` —
  이름 언급뿐. 할 일 없음.
- `docs/RESUME_0730.md:35` — 「그림 8장은 미공개 → 삭제해도 파급 없음」. §4 에서 독립 확인.
  **여전히 참.**
- `docs/RESUME.md:5` · `docs/RETRACTION_LOG.md:984` — 「계산 중이니 건드리지 마라」 경고.
  **재생성이 끝나면 지워라.**

### 5-4. ⛔ 재현 문서가 **틀렸다**(이번 라운드와 무관하게)

- [ ] **`docs/REPRODUCE.md:109`** 와 **`docs/repro/part07_microdoppler.md:16`** —
  둘 다 「약 12 분 (**GPU 1장**)」이라 적는다. **둘 다 틀렸다.**
  - GPU: `experiment_md_range.py` → `microdoppler_nearfield.py` 사슬에 `torch`·`cuda` import 가
    **하나도 없다**. `ProcessPoolExecutor(max_workers=10)` 의 **순수 CPU** 다
    (지금 도는 프로세스 11개도 전부 CPU).
  - 시간: 옛 `meta.runtime_s` = **2929.6 s ≈ 49 분**, mf 판 2825.6 s. 12 분이 아니다.
  ⇒ 「약 50 분 (CPU 10 workers)」 + 새 `runtime_s` 로 고쳐라.
  ⚠ 추측(미확인): 「12 분」은 `md_map_audit.json` 이 **F1 한 장 재작화** 비용으로 적은
  「약 12 분, CPU」가 **스윕 전체 비용으로 새어 들어간 것**일 수 있다. 확인은 못 했다.

---

## 6. 재생성이 끝나면 이 순서로 (상류부터)

1. [ ] `outputs/md_range_sweep.json` 의 `meta.generated` · `meta.slow_time.capture`(=`full_waveform`) ·
   `meta.snr.g_mf_db`(=36.9897) · `meta.runtime_s` · `meta.n_noise`(=8) · `meta.ranges_m`(7점) 확인.
2. [ ] **결정론 대조**: 새 `md_range_sweep.json` 의 σ·`dc_ac_db`·`f_tip_hz` 가
   `md_range_sweep_mf.json` 과 **같은지** 확인(같은 코드·같은 메쉬이므로 같아야 한다).
   다르면 그 사이에 또 무언가 움직인 것이고, **이 지도의 §0 표를 다시 재야 한다.**
3. [ ] `benchmark/verify_noise_injection.py:314-315` 의 `SWEEP_OLD` 를 **pre37db 사본으로 옮긴 뒤**
   게이트 재실행 (§2-4). 안 옮기면 NI10 이 공허하게 통과한다.
4. [ ] `benchmark/verify_matched_filter_gain.py:190` σ 기본값 갱신 → 게이트 11/11 재확인.
5. [ ] 문서: §5-1 (아직 옛 수인 자리 14곳, **코드 3곳 포함**) → §5-0 (출처 확정) →
   §5-2 (전제 해소) → §5-4 (재현표) 순. ⚠줄 번호 말고 **앵커 문자열로 grep** 해라 —
   메인 세션이 같은 파일을 고치는 중이다.
6. [ ] `src/build_part07_microdoppler.py` · `src/make_report07_microdoppler.py` 재실행 → 노트북
   provenance 표 diff **0 이어야 정상**(전부 mini5pro).
7. [ ] 다른 원장의 굳은 복사본 (§2-5): `noise_rotor_plan.json` 사다리 예시 ⭐**먼저** →
   `s2rj_compare.json` 필요 PRF 상한 → `meshdef_spec.json` / `meshdef_spec_judge.py:503`
   런타임 → `reports_index/md-prf.json`.
8. [ ] `src/viz_md_range.py` 재실행 → 그림 8장 (우선순위 낮음, §4). F1 만이면
   `md_map_audit.json` 의 `rerun_cmd`.

---

## 7. ⚠ 내가 확인 못 한 것

- 재생성 중인 `outputs/md_range_sweep.json` 자체를 **안 읽었다**(지시). 위의 「바뀐다/안 바뀐다」는
  **코드(`experiment_md_range.py`)와 형제 원장(`md_range_sweep_mf.json`)에서 유추**한 것이다.
- `verify_md_nearfield.py:161` 의 「AC 0.334±0.096 @1 m → 0.995±0.004 @20 m」 **출처를 못 찾았다**(§2-5).
- mavic4pro `dc_ac_db` 가 37.18 → 5.33 dB 로 **31.9 dB** 무너진 **이유를 모른다.** 메쉬 지문이
  함께 움직였으니 NI10 게이트는 통과하겠지만, 그것은 「설명됨」이지 「이해됨」이 아니다.
- `arms[].snr_sample_db` 삭제로 깨질 **저장소 밖** 소비자가 있는지 모른다.
- 이 지도를 쓰는 동안 **메인 세션이 같은 문서 4편을 동시에 고치고 있었다**(03:39~03:43).
  §5 의 ✅/⛔ 는 **03:47 스냅샷**이고, 지금은 더 고쳐졌을 수 있다.
- 「12 분」의 출처가 정말 `md_map_audit.json` 의 F1 재작화 비용인지 **확인 못 했다**(§5-4).
