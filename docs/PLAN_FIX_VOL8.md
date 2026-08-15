> ⚠ **2026-08-16 재편 전 번호 체계의 기록이다** — 옛 권 번호(평면 01~18)로 적혀 있다. 옛→새 환산은 [`RESTRUCT_PLAN.md`](RESTRUCT_PLAN.md) §1 표, 현행 편성은 [`REPORTS_VOLUMES.md`](REPORTS_VOLUMES.md).

# 8 권 엔진-팔 정정 계획 — 고칠 자리 확정판

작성 2026-08-12 · 근거 `docs/AUDIT_VOL8_ENGINES.md` + `outputs/audit_vol8_08_[1-5].json`
⛔ 이 라운드는 **계획만** 했다. 노트북·원장·빌더·그림은 한 줄도 안 고쳤다. GPU 0 초 · git 0 회.

---

## 0. 팔 세 개 — 이 문서 전체의 낱말

| 기호 | 이름 | 무엇을 하나 | 원장에서 알아보는 법 |
|---|---|---|---|
| **S** | Sionna PathSolver | 광선을 뿌려 `(a, τ)` 를 낸다. σ 를 안 잰다 | `spp` · `paths_median` · `paths_zero_frac` · `seconds` |
| **B** | 우리 SBR + PO | 광선 격자로 가림을 풀고 보이는 면만 면적분(`rcs_sbr.sbr_field`) | `grid_ref` · `n_lit` · `spacing` · `grid_frozen` |
| **P** | 순수 PO (대조군) | 점구름 전면 면적분. **가림 없음** · 광선 격자 안 씀(`microdoppler_series`) | `engines.po` · `SPACING_PO` · `angle_gamma=False` |

⭐ **«우리 PO» 라는 말로 B 와 P 를 뭉뚱그린 자리가 8 권에 열 곳 있다.** 이 계획의 절반이 그것을 가르는 일이다.
⛔ 낱말 세기로는 B 와 P 를 못 가른다 — `po` 는 `pose` 와 섞인다. 가르는 것은 `arms` 키 이름 · `angle_gamma` · `spacing` · 가림 여부다.

---

## 1. 빌더 대응 — 어느 파일이 어느 편을 내나 (코드로 확인)

| 편 | 빌더 | 함수·줄 | 확인 |
|---|---|---|---|
| **08_1** 장면 | `src/make_report08_microdoppler.py` | `build_08_1()` 555–654 | `write("08_1", "scene", c)` 654 |
| **08_2** 세 엔진과 거리 | 같은 파일 | `build_08_2()` 660–852 (+ `_grid_anchor_cell()` 293–434 · `_flash_census_para()` 437–513) | `write("08_2", "engines", c)` 852 |
| **08_3** 무늬 — **앞머리만** | 같은 파일 | `build_08_3()` 858–963 | `write("08_3", "pattern", c)` 963 |
| **08_3** 무늬 — **절 1~6** | `src/build_part07_microdoppler.py` | `blocks_34`149 · `blocks_35`240 · `blocks_36`344 · `blocks_37`566 · `blocks_38`666 · `blocks_39`785 | `REPORTS` 1458–1469 → `reports/_parts/3N_*.ipynb` |
| **08_4** 무엇을 잴 수 있나 | `src/make_report08_microdoppler.py` | `build_08_4()` 969–1126 | `write("08_4", "sampling", c)` 1126 |
| **08_5** 바이스태틱 | `src/make_report07b_bistatic.py` | 모듈 최상단 `cells = [...]` 145–695 | `json.dump(nb, ...)` 702 |

**`src/build_volumes.py` 는 8 권에서 후처리만 한다 — 코드로 확인했다.**
`EXTERNAL`(150–167) 이 8 권을 «다른 빌더가 내는 권» 으로 등재하고, `_postprocess_external()`(923–1005) 이 하는 일은 셋뿐이다: ① 앞선 실행이 붙인 셀 걷어내기(`_strip_appended`) ② 상호참조 주소 재배선(`_relink`) ③ **조각 34~39 를 `08_3_pattern.ipynb` 뒤에 절로 덧붙이기**(953–981). 8 권 본문 문장을 새로 짓는 자리는 없다.
⇒ **이번 라운드에 `build_volumes.py` 에서 고칠 자리는 0 개.** 다만 빌더를 고친 뒤 **맨 마지막에 반드시 다시 돌려야** 08_3 의 절 1~6 이 복원된다.

**그림 빌더 두 개도 고칠 자리다** — 노트북은 png 를 base64 로 박기만 한다.

| 그림 | 빌더 | 쓰이는 편 |
|---|---|---|
| f9 (거리·예산) | `benchmark/build_range_sweep_fig.py` | 08_4 §1 |
| f1 · f2 · f3 · f4 | `benchmark/build_report07_figs.py` | f2 → 08_2 절 5 · f1/f3/f4 → 08_3 앞머리 |

---

## 2. ⭐ 고칠 자리 표

심각도 `A` = 데이터가 아닌 것을 데이터로 그림 · `B` = 한 팔로 재고 두 팔로 읽히게 씀 · `C` = 귀속·라벨 · `D` = 판(版) 표시.

### 2-1. 08_4 «무엇을 잴 수 있나» — ⭐가장 먼저

| ID | 절 | 파일 : 줄 | 무엇이 틀렸나 | 어떻게 고치나 | 원장 |
|---|---|---|---|---|---|
| **F4-1** `A` | §1 그림 f9 (c) | `benchmark/build_range_sweep_fig.py:120-121` | `ax.axhline(1.0, color=C_OURS, label="Ours (SBR+PO), range invariant")` — **데이터 원점이 없는 손그림 선**이다 | 그 두 줄을 **지우고** 실측 세 점을 찍는다: 3/15/40 m 에서 자세당 0.601 / 0.512 / 0.635 s → 자기 3 m 로 정규화하면 **1.000 / 0.852 / 1.057**. 범례 `Ours (SBR+PO), measured, 3 ranges` | ✅ `outputs/deck_ours_by_range.json : ranges.{3,15,40}.cpu_seconds ÷ _meta.n(4096)` |
| **F4-1b** `A` | §1 그림 f9 (c) | 같은 파일 `:117-119`, `:137-143` | 빨간 곡선이 **측정 seconds 가 아니라 해석식** `(R/3)²` 인데 축 이름은 «Relative cost» 다 | 범례를 `PathSolver, rays needed to hold path count — analytic rule` 로 바꾸고 캡션에 «두 곡선은 다른 질문에 답한다 — 규칙 대 측정, 절대 비용은 견주지 않는다» 를 넣는다 | 규칙은 `report07_sionna_ranges.json:_meta.spp_scaling_ko` |
| **F4-1c** `A` | §1 그림 f9 (c) 캡션 | 같은 파일 `:137-143` | 같은 원장에 PathSolver **측정** 자세당 초가 있고 그 값은 0.167 → 0.147 s 로 **거의 평평**하다(그 스윕이 규칙값보다 적게 쏜 탓 — (b) 판이 그것이다). 지금 캡션은 그 사실을 안 적어 (b) 와 (c) 가 어긋나 보인다 | 캡션에 한 줄: «measured wall time in the same ledger is flat because that sweep under-launched — panel (b)» | ✅ `report07_sionna_ranges.json : ranges.*.seconds` (85.6/79.1/77.6/75.5 s @ 자세 512) |
| **F4-2** `B` | §1 맺음 두 문단 | `src/make_report08_microdoppler.py:1011-1016` | 잰 팔은 S 하나인데 «반면 우리 SBR+PO 는 … **한 번 계산하면 거리에 무관**하다» 로 맺는다. 이 절에 B 값이 0 개다 | 문장을 지우지 말고 **근거를 데려온다** — «우리 팔의 거리 비용은 따로 쟀다: 3/15/40 m 에서 자세당 0.601/0.512/0.635 s(`deck_ours_by_range.json`)» 를 본문 표로 넣고, «거리 무관» 은 그 측정에 매단다 | ✅ 같은 원장 |
| **F4-3** `B` | §1 · 8 권 구조 | `outputs/report07_three_engine_ranges.json:_meta.grid_note_ko` | 원장이 «sbr·po 열은 **거리 무관이라** 그 원장을 그대로 쓴다» 고 적는다 — **거리 무관이 가정으로 파이프라인에 박혀 있다.** 08_4 §1 이 그것을 결론으로 다시 쓰면 순환이다 | ⛔원장은 안 고친다. 08_4 §1 과 08_2 절 2 에 «세 거리를 다시 푼 팔은 S 하나이고, 우리 두 팔의 거리 무관은 `deck_ours_by_range.json` 이 따로 잰 것이다» 를 박는다 | ✅ 위와 같음 |
| **F4-4** `C` | 부록 f9 행 | `src/make_report08_microdoppler.py:1082-1083` | 행의 팔 칸이 «Sionna 팔(광선 격자 무관)» 인데 그림 안에는 Ours 범례가 있다 — 부록과 그림이 어긋난다 | F4-1 뒤에 «S 팔(측정 · 광선 격자 무관) + 우리 팔 3 점(`deck_ours_by_range`)» 로 고친다. 같은 행에 원장 두 개의 시각을 **둘 다** 적는다(04:31 · 09:19) | ✅ 두 원장 `_meta.generated` |
| **F4-5** `D` | §2 + 부록 f10 행 + ⚠문단 | `:1019` · `:1084-1085` · `:1087-1090` | «채널은 08_3 의 h(t) **그대로**다(같은 원장)» 가 거짓 — 이 절의 채널열은 **얼기 전 판**이다. 부록의 «얼림(한 변 124 칸)» 도, «**f3 만** 옛 판이다» 도 같이 틀렸다 | 세 자리를 문장으로 고친다: §2 시나리오에 «⚠ 이 절의 채널열은 얼기 전 판이다(`outputs/prefreeze/report07_hover_long.npz::E` 와 바이트 동일)», f10 행 격자 칸을 `_PLATE_HOV` 대신 «⚠얼기 전 판(2026-08-10 15:11)», ⚠문단을 «f3·f10 이 옛 판이다» 로 | ✅ 감사가 바이트 동일성으로 재현(AUDIT §7). ⛔재계산은 이번 라운드 밖 |
| **F4-6** `C` | §2 표 머리 | `:1023` · `:1025` | 이 절만 «팔» 을 **표본율** 뜻으로 쓴다. 8 권의 다른 곳은 전부 엔진 뜻이다 | «네 갈래» · «표본율 넷» 으로 바꾼다 | — |
| **F4-7** `D` | §1 | `:1012` | 원거리장 경계가 8.3 m(`report15_probe`) ↔ 8.04 m(`report07_sionna_ranges:_meta.farfield_boundary_m`) 로 한 절 안에 둘이다 | 한 원장으로 통일하고 다른 값은 각주로 밝힌다 | ✅ 두 원장 |
| **F4-8** `D` | §1 사다리 표 | `:994-1002` | 사다리는 자세 128, 스윕은 자세 512 인데 안 적혀 있다. 두 판이 77.3 % ↔ 78.3 % 로 서로 맞는 좋은 교차검증인데 그 사실도 없다 | «같은 32M 에서 자세 128 판 77.3 % ↔ 자세 512 판 78.3 % — 두 판이 맞는다» 한 줄 | ✅ `report07_ray_budget_test:_meta.n_poses` · `report07_sionna_ranges:_meta.n` |

### 2-2. 08_5 «바이스태틱»

| ID | 절 | 파일 : 줄 | 무엇이 틀렸나 | 어떻게 고치나 | 원장 |
|---|---|---|---|---|---|
| **F5-1** `B` ⭐ | 절 4 «플래시» | `src/make_report07b_bistatic.py:451-464` | 편의 헤드라인이 **교차-팔 비교**다 — «도플러 축척» 열은 **P**(fc·cos(β/2) · λ/11 · 가림 없음 · Γ(θ) 꺼짐), «플래시열 상관» 열은 **B**(3.5 GHz · λ/12 · 가림 있음 · Γ(θ) 켜짐). 표에도 본문에도 표시가 0 칸 | 열 제목에 팔을 박는다 — `도플러 축척 (순수 PO 팔)` · `플래시열 상관 (SBR 팔)`. 표 아래 한 줄로 두 팔의 조건 차이를 적고, 결론 문장을 «두 팔에 걸친 관측» 으로 낮춘다 | ✅ 열 값은 `report07b_bistatic_md.json:rows[*].{po_ratio, flash_lag_corr}` |
| **F5-1b** `B` | 절 4 | 같은 곳 | «한 엔진 안에서도 같은 갈림이 보이는가» 를 확인할 값이 **없다** — `rows[*]` 에 `po_flash*` 키가 0 개다 | ⭐숫자를 지어내지 말고 «순수 PO 팔의 플래시 관측량은 이 원장에 없다» 를 적고 «남긴 문제» 표에 한 줄 더한다 | ⛔**원장 없음** |
| **F5-2** `C` | 절 1 팔 선택 근거 | `:280-282` | «순수 PO 바닥 −127 dB · SBR 바닥 −62 dB» 는 이 스윕이 아니라 **모노·얼린격자 원장**의 값이다. 절 2 가 금지한 이어붙임을 절 1 이 근거로 쓴다 | 그 문장에 «(모노 원장 기준)» 을 박고, 이 스윕의 자기 바닥 **−13.4 ~ −33.5 dB** 를 나란히 적는다 | ✅ `rows[*].sbr_floor_rel_db` · `outofband_power.json` |
| **F5-3** `C` | 셀 3 그림 2 머리말 | `:269` | «판정은 (k) 칸의 **별도 추정기**가 한다» — 오도. 맵과 (k) 의 차이는 추정기가 아니라 **팔**이다(맵 10 칸 = B, (k) = P) | «맵 열 칸은 SBR 팔이고 (k) 칸은 순수 PO 대조팔이다» 로 교체. 영문 캡션은 이미 «two arms» 로 맞다 | ✅ `benchmark/build_bistatic_md_fig.py` |
| **F5-4** `B` ⭐ | 셀 9 모노↔바이 대조표 | `:524-553` | 6 행이 전부 단일 팔인데 팔 표시가 **한 칸도 없다**(f_tip=해석 · 도플러 축척=P · 플래시율·상관·레벨=B · A_eff=B 격자 기하). «8 권 모노 편» 열도 모노 원장이 아니라 이 스윕 β=0 **prefreeze 판**이다 | ① 팔 열을 하나 더 박는다 ② 1 행에 «예측» 표시(1 행 예측 ↔ 2 행 실측이 β60 에서 14.9 % 어긋난다) ③ «8 권 모노 편» 열에 각주 — «이 스윕의 β=0 칸 · 현재 모노 원장과 진폭 상관 0.464» | ✅ `regression.mono_ledger.checked_now.*` |
| **F5-5** `C` | 셀 0 표지 | `:157-184` | 요약 셋이 각각 한 팔(1=P · 2=B · 3=B+기하)인데 셀 0 원문에 «PO»·«SBR»·«대조팔»·«Sionna» 가 0 회. 설정표 «커널» 칸에 `sbr_field_bistatic` 하나뿐 | 요약마다 팔을 한 낱말로 붙이고, 설정표 커널 칸에 순수 PO 대조팔(`src/microdoppler.py::microdoppler_series`)을 한 줄 더한다. 경계 문단에 «PathSolver 는 이 편의 β 스윕에서 한 번도 안 돌았다»(npz 에 `sionna` 키 없음) | ✅ `independent_recheck.sionna_key_in_bistatic_npz = false` |
| **F5-6** `C` | 셀 10 부록 이력 | `:555-568` | «그림 2 · Γ(θ) ✅ 후(커널 기본값)» 한 줄이 그림 2 전체를 덮는데, (k) 칸의 **P 팔은 Γ(θ) 를 안 켰다**(`microdoppler_series` 의 `angle_gamma` 기본값 False, 스윕이 안 넘긴다). 이력표에 절 2 표의 실제 출처 `outofband_power.json` 도 빠졌다 | 그림 2 행을 팔별 두 줄로 쪼개고, `outofband_power.json` 행을 더한다 | ✅ `src/microdoppler.py:39` · `benchmark/report07b_bistatic_md.py:465` |
| **F5-7** `C` | 셀 11 부록 설정 | `:570-614` | 계산 설정이 **한 벌**이라 두 팔이 같은 판으로 돈 것처럼 읽힌다. 실제로는 격자 λ/12 ↔ λ/11 · Γ(θ) 켜짐 ↔ 꺼짐 · 가림 있음 ↔ 없음이다. `SPACING_PO` 가 노트북에도 `_meta` 에도 없다 | 팔별 열을 만든다. `SPACING_PO = λ/11` 을 적고 출처를 `benchmark/report07b_bistatic_md.py:449` 로 단다. **PO 팔의 계산 시간 칸은 «원장 없음»** — `_meta.seconds_field` 는 SBR 팔만이다 | ✅ 코드 / ⛔PO 시간은 **원장 없음** |
| **F5-8** `C` | 절 3 «레벨» | `:405-440` | 어느 팔로 쟀는지가 절 안에 없다 — 귀속이 절 2 끝줄 한 곳에만 있다 | 표 제목이나 첫 문장에 «SBR 팔» 을 박는다 | ✅ `benchmark/report07b_bistatic_md.py:518` |
| **F5-9** `C` | 절 5 «정직» | `:480-522` | 한계 목록이 **SBR 커널 것뿐**이다. 절 1 의 판정을 낸 P 대조팔의 근사(가림 없음 · Γ(θ) 없음 · 진폭 게이트를 n̂·û_b 하나로)가 없다. «상반성 부분성립» 이라고 말만 하고 6.5 dB 를 안 적는다 | P 팔 근사 세 줄을 목록에 더하고, `reciprocity.max_abs_d_db = 6.487 dB` 를 숫자로 적는다 | ✅ `outputs/verify_bistatic_field.json:reciprocity.max_abs_d_db` · 스크립트 446–448행 |
| **F5-10** `D` | 절 2 | `:329-342` | 원장 `verdict.sbr_edge_unusable.mono_ledger_engine_floors_db` 에 폐기된 옛 값(sbr −33.5 · po −118.8 · sionna −41.4 dB)이 superseded 표시 없이 남아 있고, 그 값으로 읽으면 바닥 순서가 **뒤집힌다** | ⛔원장은 안 고친다. 노트북이 그 키를 안 읽는지 확인하고(현재는 `outofband_power.json` 을 읽는다 — 맞다), 절 2 에 «이 편이 쓰는 바닥 값의 출처는 `outofband_power.json` 이다» 를 한 줄 박아 오독을 막는다 | ✅ 현재 코드가 `OOBE` 를 읽음 |

### 2-3. 08_1 «장면»

| ID | 절 | 파일 : 줄 | 무엇이 틀렸나 | 어떻게 고치나 | 원장 |
|---|---|---|---|---|---|
| **F1-1** `D` ⭐ | 셀 3 | `src/make_report08_microdoppler.py:635-639` | 우리 팔 숫자가 **폐기된 안 얼린 판**의 값이다 — `SG12['rays_per_pose']` = 14,122 · `SG12['n_lit_mean']` = 610.5. 8 권 생산 팔은 **얼린 판**이다 | 광선 수를 **15,376**(얼린 판 한 변 124 칸)으로 바꾼다. 같은 파일에 이미 `_ray_count_phrase()`(265–271) 가 얼린 판을 읽으므로 그것을 쓰면 08_2 와 자동으로 맞는다 | ✅ `report07_three_engines.json:engines.sbr.grid_ref.n = 124` / `verify_frozen_grid.json:gate2_frozen_grid_invariant.frozen.n_rays = 15376` |
| **F1-1b** `D` | 셀 3 | 같은 곳 | 조명점 «611 점» 도 안 얼린 판 값이다 | ⭐**얼린 판 값이 있다** — `n_lit_froz_mean = 605.3`(자세 산포 상대표준편차 3.6 % · `n0_frozen = 124`). ⚠단 그 얼린 판은 **격자 사다리의 봉투**이고 생산 판은 `n_mesh=24` 봉투다(한 변 칸수·간격은 같고 Rout 이 0.4422 ↔ 0.44207). 그래서 «같은 칸수·같은 간격의 얼린 판에서 자세 평균 605 점(±3.6 %)» 으로 **출처와 차이를 밝혀** 쓰거나, 숫자를 빼고 «생산 판의 조명점 수를 내는 원장이 없다» 로 적는다. ⛔610.5 를 얼린 판 값으로 적는 것만은 금지 | ⚠준-원장 `outputs/adv_grid_freeze_audit.json : audit_2_signal_loss.rows[div=12].n_lit_froz_mean` (교차 확인 `audit_5_recompute.arms.froz.n_lit_mean = 607.3`) |
| **F1-1c** `B` | 셀 3 «61 배» | `:623` · `:638-639` | 분자는 **표적 표면 조명점**, 분모 10 은 **직행 1 + 표적 경유 9** — 잣대가 다르다. 게다가 9 는 원장 밖(빌더 문자열)이고 10 은 하드코딩(`SG12['n_lit_mean']/10`) | 분모를 **원장의 표적 경유 중앙값 5** 로 통일해 다시 재고(≈120 배) 잣대를 문장에 박는다. 렌더의 «9 가닥» 은 «이 렌더 실행의 기록값 · 원장 없음» 으로 남기고 **비율에 안 쓴다** | ✅ `report07_three_engine_ranges.json:ranges.R3.paths_median = 5` / ⛔9 는 **원장 없음** |
| **F1-2** `C` | 셀 0 | `:548-549` (`LEDGER_NOTE`) | «숫자는 **전부** 원장에서 주입된다» 가 이 편에서 거짓이다 | F1-1c 뒤에도 «9 가닥» 이 원장 밖이므로 «전부» 를 뺀다. ⚠`LEDGER_NOTE` 는 08_1·08_2·08_4 가 함께 쓰는 **모듈 상수**다 — 소유자는 08_1 담당(§4) | — |
| **F1-3** `C` | 편 전체 | `:641-652` 뒤 | 원장 7 개에서 숫자를 끌어오면서 **출처 블록이 없다**. 08_3·08_5 에는 «## 출처» 가 있다 | 편 끝에 «## 출처» 를 붙이고 7 개 파일명·키를 적는다 — `audit_vol8_08_1.json:sections[].ledger` 를 그대로 쓰면 된다 | ✅ 감사 파일 |
| **F1-4** `B` | 셀 3 | `:635` | 셋째 팔(P)이 이 편에 **이름조차 없다**. «SBR+PO» 한 덩어리로 적혔는데 그 숫자(광선·조명점)는 B 팔만의 것이다 — P 는 광선 격자를 아예 안 쓴다 | 장면 편에서 세 팔을 한 줄씩 세운다 — S / B(가림 O) / P(가림 X, 광선 격자 안 씀) | ✅ `report07_three_engines.json:engines.*.engine` |
| **F1-5** `C` | 셀 3 | `:637-638` | 조명점은 **자세 평균**이고 흔들리는데 확정 수처럼 적혔다. S 쪽 흔들림만 «추첨 한 장» 으로 경고한 비대칭 | «자세 평균 605 점(자세마다 ±3.6 %)» 처럼 적는다 | ✅ F1-1b 와 같음 |
| **F1-6** `B` | 셀 3 | `:631-632` | «시드만 바꾸면 그 수가 배로 움직인다» 가 «같은 3 m 조건» 뒤에 붙어 있는데 **3 m 시드 사다리 원장이 없다**(8 m·40 m 만) | «8 m 에서 잰 것» 이라고 거리·예산을 밝힌다(자세당 중앙값 13/6/9 · spp 7.1M). 밝히기 싫으면 문장을 뺀다 | ✅ `probe_8m_anomaly.json` / ⛔3 m 는 **원장 없음** |
| **F1-7** `D` | 셀 2 | `:601` | «날개끝 도플러 1230 Hz» 가 어느 정의인지 안 밝힌다(앙각 −15° 사영). 바로 아래 문단이 «정의를 안 밝힌 경계는 비교하지 않는다» 고 못 박는데 일관성이 없다 | «1230 Hz (앙각 −15° 사영 · 브로드사이드는 1273 Hz)» 로 적는다 | ✅ `report15b:physics.f_tip` · `report00_microdoppler.json:rows[matrice4e].f_tip_hz` |
| **F1-8** `B` | 셀 2(뒤) | `:613-617` | `h = Σ a_p·exp(−j2πf_cτ_p)` 를 **권 전체**의 신호로 선언하는데, 원장에서 그 식이 붙은 팔은 `engines.sionna` 하나다 | 팔마다 `a_p·τ_p` 가 무엇인지 한 줄씩 붙이거나, «세 팔 모두 같은 슬로타임 격자 위의 복소 코히어런트 합» 이라는 **공통 규약**으로 다시 쓴다 | ✅ `report07_three_engines.json:engines.*.engine` · `report15b:_meta.po_arms_not_recomputed_ko` |
| **F1-9** `D` | — | `benchmark/render_md_scene.py:3-18` | docstring 이 아직 «TX/RX 기선 0.2 m · 바이스태틱각 3.8°(준-모노스태틱)» 인데 코드는 `BASE = 0.0`(48행)이다. 이 파일만 읽는 사람은 08_1 의 «진짜 모노스태틱» 을 반증으로 오독한다 | docstring 을 `BASE=0.0` 에 맞춘다 | ✅ 코드 48행 |

### 2-4. 08_2 «세 엔진과 거리»

| ID | 절 | 파일 : 줄 | 무엇이 틀렸나 | 어떻게 고치나 | 원장 |
|---|---|---|---|---|---|
| **F2-1** `B` ⭐ | 절 5 | `src/make_report08_microdoppler.py:828-838` + `benchmark/build_report07_figs.py:166,183,201` | 제목 «두 엔진» 이 어느 둘인지 안 밝힌다. 실체는 **S ↔ P(가림 없는 대조군)** 이고 이 편의 주력 **B 가 빠진다**. 범례 «Our PO kernel» · suptitle «two independent engines» 가 **대조군을 주력 커널로 읽히게** 한다 | 범례를 이 편의 정본 낱말 `ARM_PO = "Ours, nothing blocked (control)"`(`src/md_mapstyle.py:62`) 로 통일하고, suptitle 을 «stock path solver vs our unoccluded PO control» 로 바꾼다. 절 제목·본문에 «이 절에는 SBR 팔이 없다» 를 한 줄 | ⛔SBR 은 이 원장에 **없다**(`report15_verdict.json` 최상위에 `sbr` 키 0 개) |
| **F2-2** `D` | 절 5 | `:835-838` | 이 원장은 **준-모노스태틱 기선 0.2 m** 인데(`benchmark/report15_verdict_po_grid.py:46 BASELINE_M = 0.20`) 절 2 는 «진짜 모노스태틱(기선 0)» 이다. 본문은 자세 차이만 밝힌다 | «이 그림만 자세가 다르다» 줄에 «**기선도 다르다 — 0.2 m**» 를 같이 넣는다 | ✅ 코드 46행 |
| **F2-3** `C` | 절 3 | `:368-374` | «27 열 전부(**세 엔진** · report15b 여섯 자세 · 호버 두 프리셋)» 의 «세 엔진» 은 **원장 이름**이지 세 팔이 아니다. 27 키는 전부 SBR 계열이고 세 엔진 원장에서 온 것은 `sbr` 한 줄이다(27 = 1 + 24 + 2) | «세 엔진 **원장의 sbr 열**» 로 고친다 | ✅ `freeze_before_after.json:ledgers` 키 27 개 |
| **F2-4** `B` | 절 3 | `:396-399` | 얼리기 판정을 **P 열만** 들어 «0.440 → 0.953 으로 올랐다» 고 쓴다. 같은 원장의 S 열은 **5 개 격자 전부에서 내려간다**(0.743→0.695 · 0.727→0.662 · 0.722→0.603 · 0.722→0.633 · 0.721→0.622) | S 열을 같이 적거나 판정을 «순수 PO 기준으로는» 으로 좁힌다. 왜 두 팔이 반대로 움직이는지 한 줄(«P 는 광선을 안 쓰고 S 는 경로가 성기다») | ✅ `sbr_grid_convergence.json:in_band_fidelity.rows[*].cos_{prod,froz}_vs_sionna` |
| **F2-5** `C` | 절 2 제목 | `:694` | 제목 «세 엔진을 같은 격자에, **거리 3 / 8 / 15 m**» — 거리축은 S 팔만 다시 푼 것이다. 바로 아래 ⭐줄이 밝히지만 제목만 읽으면 세 팔이 세 거리를 돈 것으로 읽힌다 | 제목에 «(거리축은 Sionna 열만)» 을 넣는다 | ✅ `report07_three_engine_ranges.json:_meta.grid_note_ko` |
| **F2-6** `C` | 편 전체 | 셀 0 `:663-668` 뒤 | 헤드라인 숫자를 내는 원장 넷이 본문에 **한 번도 안 나온다** — `report07_three_engines.json`(코사인·레벨 차) · `outofband_power.json`(대역밖 표 전부) · `report07_three_engine_ranges.json`(거리 표) · `verify_frozen_grid.json`(자 흔들림·대가 표) | «## 출처» 블록을 붙이거나 각 표 밑에 원장 포인터를 단다 | ✅ 네 원장 |
| **F2-7** `D` | 절 2 대역밖 표 | `:735` 부근 (`_oob_*` 인용부) | Sionna 행이 우리 두 팔과 같은 열에 있다. 그 행은 `units_comparable_to_po = false` 이고 절대 순위에서 빠져 있다. 단위 경고가 절 4 에만 있고 표 옆에는 없다 | 표 바로 밑에 단위 경고를 되풀이한다(인용해도 되는 것은 무차원 두 칸뿐) | ✅ `outofband_power.json:three_engines[*].units_comparable_to_po` |
| **F2-8** `D` | 절 3 | `:313-323` | 자 흔들림 실측(101~129 칸 · 61 번 · 9.8 mm · 98 mm)은 **검증판**(`n_mesh=16`)에서 나오고 바로 다음 문단의 «이 편이 쓴 판» 은 **생산판**(`n_mesh=24`)이다. 두 문단이 붙어 있어 같은 판으로 읽힌다 | 두 문단에 판 이름을 박는다(«검증판 n_mesh=16» · «생산판 n_mesh=24» · 둘 다 한 변 124 칸이라 결론은 같다) | ✅ `verify_frozen_grid:gate2.grid_ref.n_mesh` ↔ `report07_three_engines:engines.sbr.grid_ref.n_mesh` |
| **F2-9** `C` | 절 6 맺음 | `:840-846` | «그 원인은 경로 수 — 프롭 정반사가 이 격자에서 0 칸» 은 S 단독 인구조사에 기댄 문장인데, 절 4 가 붙여 둔 단서 둘(① 이 편의 자세 −15° 는 그 인구조사 격자에 없다 ② 앙각을 85° 까지 열면 matrice4e 는 2/960 칸)이 맺음말에 없다 | 두 단서를 맺음말로 데려온다 | ✅ `report15_blade_flash_ladder.json:elevation_axis.*` |

### 2-5. 08_3 «무엇이 무늬를 정하나»

⚠ 이 편은 파일이 **둘**이다 — 앞머리는 `make_report08_microdoppler.py`, 절 1~6 은 `build_part07_microdoppler.py`.

| ID | 절 | 파일 : 줄 | 무엇이 틀렸나 | 어떻게 고치나 | 원장 |
|---|---|---|---|---|---|
| **F3-1** `B` ⭐ | 절 3 소절(셀 35) | `src/build_part07_microdoppler.py:546-551` | 숫자가 **전부 S 인구조사**인데 «위상은 광선 엔진이, **세기는 PO 커널이** 맡는 분업의 근거가 여기 있다» 로 맺는다. 이 소절에 PO 값이 0 개다. 덤으로 «이 편이 쓰는 자세 격자(앙각 0~60°)» 도 틀렸다 — 이 편 맵은 el −15° 다 | 귀속을 옮긴다: «그 근거는 이 절 그림 1·2 의 두 팔 대조이고, 이 인구조사는 스톡 팔 쪽 한계를 보탠다». 격자를 «**이 인구조사의** 자세 격자(앙각 0~60°)» 로 고쳐 적는다 | ✅ `report00_microdoppler.json:specular_census` · `report15_blade_flash_ladder.json:_meta.el_base` |
| **F3-2** `B` | 절 3 (셀 33) | `:468-474` | F2-4 와 **같은 병** — 얼리기 효과를 P 열만 들어 «0.440 → 0.953» 이라 쓰고, S 열이 5 격자 전부에서 내려가는 것을 안 적는다 | S 열을 같이 적거나 «순수 PO 기준으로는» 으로 좁힌다 | ✅ F2-4 와 같음 |
| **F3-3** `B` | 앞머리 셀 4·5 (f7·f11) | `src/make_report08_microdoppler.py:908-915` | 원장이 스스로 «⚠ 이 두 열에는 **순수 PO 대조 팔이 없다** — 2 초 창의 능선이 심판을 못 받는 유일한 자리다» 라고 선언했는데 본문에 한 줄도 없다. 셀 5 는 «SBR 팔» 이라 밝히지만 셀 4 는 엔진을 안 밝힌다 | 셀 4 에 «SBR 팔 · 순수 PO 대조 없음» 한 줄 + `verdict.open_ko` 인용 | ✅ `outputs/freeze_signal_loss.json:verdict.open_ko` / ⛔PO 팔 계산은 GPU |
| **F3-4** `B` | 절 4 · 앞머리 셀 1 | `src/build_part07_microdoppler.py:627-643` (표) · `make_report08:867-880` | 순수 PO 쌍둥이(`C_po_locked`·`D_po_spread`)가 **6 칸 전부 이미 원장에 있는데** 한 번도 인용하지 않는다. 그 팔이 같은 결론을 독립으로 낸다 | 표에 PO 열을 한 줄 더한다 — 반창 상관 **1.0000 → 0.7669**(P) 대 **1.0000 → 0.7691**(B). 계산 0 초이고 이 절이 진짜 두 팔이 된다 | ✅ `report15b_microdoppler.json:cells[matrice4e/belly].arms.{C_po_locked,D_po_spread}` |
| **F3-5** `C` | 절 5 · 앞머리 셀 2 | `src/build_part07_microdoppler.py:666-784` · `make_report08:882-889` | 가림 축을 왜 한 팔로만 재는지가 본문에 없고, 절 어디에도 엔진 이름이 없다(«광선 엔진» 이라고만). 6 칸 중 `mini5pro/nose` 는 F 와 G 가 소수 7 자리까지 같아 가림 효과 0 인데 그 칸이 안 보이고, 부호가 칸마다 갈린다 | «이 축은 SBR 팔에서만 선다 — 순수 PO 는 정의상 아무것도 안 막는다» 한 줄 + 6 칸 부호표(+1.315 / −0.042 / −0.847 / −0.000 / −1.136 / −1.057) | ✅ `report15b:cells[*].findings.occlusion_level_db` |
| **F3-6** `D` | 절 6 방법 표 · 그림 5 설명 · 앞머리 셀 3 | `src/build_part07_microdoppler.py:813-815, 830-831` · `make_report08:891-906` | «두 채널은 **같은 추적에서** 나오므로 기하·재질·광선 격자가 같다» 가 사실이 아니다. `A_sbr_locked`(잠근 rpm · 동체 재질 그대로 · penetrate True)와 `F_blade_occ`(흩뜨린 rpm · 동체 Γ=0 · penetrate False)는 **따로 돈 실행**이다(seconds 2833 대 1634) | 짝을 `B_sbr_spread ↔ F_blade_occ` 로 바꾸고(같은 rpm) 문장을 «같은 얼린 판·같은 자세의 두 실행 — 한쪽은 동체를 완전흡수로 둔다» 로 낮춘다. 변조 깊이 3.26 → 5.36 dB · 반창 상관 1.0000 → 0.7691 로 바뀌고 **헤드라인은 유지된다** | ✅ 같은 원장 `arms.B_sbr_spread` · `benchmark/report15b_microdoppler_recompute.py:139-184, 311-316` |
| **F3-7** `D` | 절 6 그림 5 · 앞머리 셀 3(f3) | `make_report08:891-906` | `report07_f3` 는 원장을 안 읽는다 — `benchmark/build_report07_figs.py:208-209` 에 `whole={3.5:2.84}`, `prop={3.5:32.32}` 가 박혀 있다. 본문(3.26/50.32)과 그림이 다른 판이다. 머리말에 경고가 있지만 절 6 에는 없다 | 절 6 그림 설명에 «⚠ 이 그림의 밴드별 dB 는 그림 빌더에 박힌 2026-08-07 값 — 절대값 인용 금지» 를 되풀이한다 | ⛔그림 재생산은 계산이 필요 |
| **F3-8** `C` | 앞머리 셀 0 ↔ 절 3 | `make_report08:863` | 머리말이 «엔진 비교는 08_2 가 했다. 이 편은 표적 쪽 요인만 다룬다» 인데, 이어 붙인 **절 3 이 바로 엔진 비교**이고 8 권에서 가장 긴 절이다 | «엔진 비교의 결론은 08_2 가 요약하고, 그 **근거 절은 이 편 절 3** 에 있다» 로 고친다 | — |
| **F3-9** `D` | 절 1 | `src/build_part07_microdoppler.py:149-239` | 98 개(mini2)와 296 개(matrice4e)가 한 서술에 섞였고, «프롭 경유 경로 296 개» 의 키 `n_target_paths` 는 **표적 경유 전체** 경로 수다 | 기체를 밝히고 296 을 «표적 경유 경로» 로 고쳐 적는다 | ✅ `report15_probe.json` · `report15_probe.py:384` |
| **F3-10** `C` | 절 3 «다음 단계» | `src/build_part07_microdoppler.py:556-559` | «두 엔진 일치도를 가림 있는 SBR 팔로 한 번 더 잰다» 를 앞으로 할 일로 적었는데 같은 절 그림 2 가 한 칸에서 이미 했다 | «한 칸에서는 했다(그림 2 · sbr_vs_po 0.955) — 남은 것은 15 칸 격자 전체로 넓히는 것» 으로 고친다 | ✅ `report07_three_engines.json:verdict.cosine_in_ftip` |
| **F3-11** `D` | 절 3 결과 1~4 · 그림 2 | `src/build_part07_microdoppler.py:352-370` · `422-447` | 한 절에 통계 단위가 셋인데 안 적혀 있다 — 결과 1 은 nose·3 m **한 칸**, 결과 2~4 는 **15 칸 중앙값**(1/3/10 m 섞임), 그림 2 는 belly·el −15°·3 m **한 칸** | 각 줄에 «(nose · 3 m 한 칸)» / «(15 칸 중앙값)» / «(belly · −15° 한 칸)» 을 병기한다 | ✅ `report00_microdoppler.json:_meta` · `report15_verdict.json:tail_excess` |

---

## 3. ⛔ 원장이 없어 못 고치는 것 — 숫자를 빼는 것이 답이다

| # | 어디 | 없는 것 | 이번 라운드의 답 | 닫으려면 |
|---|---|---|---|---|
| 1 | 08_1 셀 3 | 렌더가 찾은 «표적 경유 9 가닥» — `benchmark/render_md_scene.py:101` 이 stdout 으로만 찍고 `json.dump` 가 없다 | «이 렌더 실행의 기록값 · 원장 없음» 으로 남기고 **비율에서 뺀다**. 비율은 원장 중앙값 5 로 다시 잰다 | 그 스크립트에 `json.dump` 를 붙인다(GPU) |
| 2 | 08_1 셀 3 | 3 m 시드 사다리 — `outputs/` 에 8 m·40 m 만 있다 | 거리·예산을 «8 m» 로 밝히거나 문장을 뺀다 | 3 m 시드 사다리 실행(GPU) |
| 3 | 08_5 절 4 | 순수 PO 팔의 **플래시 관측량** — `rows[*]` 에 `po_flash*` 키 0 개 | «순수 PO 팔의 플래시는 이 원장에 없다» 를 적고 «남긴 문제» 로 넘긴다 | `Epo` 로 `flash_envelope` 를 한 번 돌린다 |
| 4 | 08_5 부록 설정 | 순수 PO 팔의 **계산 시간** — `_meta.seconds_field` 는 SBR 팔만 | 설정표 PO 열의 시간 칸을 «원장 없음» 으로 | 스윕이 PO 시간을 `_meta` 에 남기게 한다 |
| 5 | 08_3 앞머리 f7·f11 | 2 초 호버 두 열의 **순수 PO 대조** — 원장이 스스로 «없다» 고 선언 | 그 경고를 본문에 적는다(F3-3) | 같은 자세·rpm 궤적으로 PO 팔 1 회(모노 PO 는 4096 자세 8.4 초) |
| 6 | 08_4 §2 | **얼린 판 위의 5G 채널** — 지금 원장은 prefreeze 채널이다 | 문장·부록만 «얼기 전 판» 으로 고친다(F4-5) | `report07_5g_waveform.py` 를 현재 hover npz 로 다시 돌리고, 같은 실행에서 `resample_poly(h5k, 28, 5)`(66행)의 5 kHz 하드코딩을 PRF 에서 읽게 고친다 — 표의 «접힘» 판정이 뒤집힌다 |
| 7 | 08_1 셀 3 | ⚠**준-원장 있음** — 얼린 팔의 조명점 수 | `adv_grid_freeze_audit.json` 의 605.3 을 **출처와 판 차이를 밝혀** 쓰거나 뺀다(F1-1b). ⛔610.5(안 얼린 판)를 얼린 판 값으로 쓰는 것만은 금지 | 생산 판(`n_mesh=24`)에서 `n_lit` 를 내는 원장을 뽑는다 |

---

## 4. 편별 분담 — ⚠파일이 겹친다

| 묶음 | 편 | 전담 파일 (충돌 없음) | ⚠공유 파일 · 담당 줄 |
|---|---|---|---|
| **W1** | 08_4 | `benchmark/build_range_sweep_fig.py` | `src/make_report08_microdoppler.py` **969–1126** |
| **W2** | 08_5 | `src/make_report07b_bistatic.py` | 없음 — **완전 독립** |
| **W3** | 08_1 | `benchmark/render_md_scene.py`(docstring) | `src/make_report08_microdoppler.py` **543–655** |
| **W4** | 08_2 | `benchmark/build_report07_figs.py` (`fig2_three_engines` 152–203) | `src/make_report08_microdoppler.py` **265–434 · 660–852** |
| **W5** | 08_3 | `src/build_part07_microdoppler.py` (`blocks_34`~`blocks_39`, 149–872) | `src/make_report08_microdoppler.py` **858–963** |

### ⚠ 겹치는 파일 두 개

**① `src/make_report08_microdoppler.py` — W1·W3·W4·W5 넷이 함께 쓴다.**
줄 범위는 겹치지 않지만 파일이 하나라 동시 편집은 서로의 파일 상태를 깨뜨린다.
· ⭐**한 번에 한 묶음씩** 이 파일을 고친다. 권장 순서 **W3 → W4 → W5 → W1**(위에서 아래로 — 되돌리기 쉽다).
· ⛔**1–262 줄(원장 적재 블록)은 아무도 안 고친다.** 새 원장이 필요하면 자기 함수 안에서 `_opt(f"{_ROOT}/outputs/....json")` 으로 읽는다.
 — W1 은 `deck_ours_by_range.json`, W3 은 `adv_grid_freeze_audit.json` 이 필요하다.
· 모듈 상수 소유자: `LEDGER_NOTE`(548) · `NAV`(543) → **W3**. `_ray_count_phrase`·`_freeze_para`·`_grid_anchor_cell`·`_flash_census_para`(265–513) → **W4**. 다른 묶음은 읽기만 한다.

**② `benchmark/build_report07_figs.py` — W4 가 소유한다.**
`fig2`(f2)는 08_2, `fig1/fig3/fig4`(f1·f3·f4)는 08_3 이 쓴다. 이번 라운드에 **코드를 고치는 것은 `fig2` 뿐**이고(F2-1), 08_3 의 f3 결함(F3-7)은 **노트북 문장으로** 처리하므로 W5 는 이 파일을 안 건드린다.

**③ 겹치지 않는 것** — W2(08_5)는 전담 파일 하나뿐이라 언제든 병렬로 돈다. 그림 빌더 두 개(`build_range_sweep_fig.py`·`build_report07_figs.py`)도 서로 독립이다.

---

## 5. 다시 돌리는 순서 (고친 뒤)

```bash
# ① 그림 — 고친 그림 빌더만
PYTHONPATH=src python benchmark/build_range_sweep_fig.py     # f9  (W1)
PYTHONPATH=src python benchmark/build_report07_figs.py       # f1~f4 (W4)
# ② 조각 — 08_3 의 절 1~6
PYTHONPATH=src python src/build_part07_microdoppler.py       # (W5)
# ③ 8 권 다섯 편
PYTHONPATH=src python src/make_report08_microdoppler.py      # 08_1~08_4
PYTHONPATH=src python src/make_report07b_bistatic.py         # 08_5   (W2)
# ④ ⭐맨 마지막 — 안 돌리면 08_3 의 절 1~6 이 사라진다
PYTHONPATH=src python src/build_volumes.py
```

⛔ 이 라운드는 **GPU 를 안 쓴다.** 위 다섯 줄은 전부 디스크의 원장·그림을 읽어 문서를 다시 짜는 일이다.
⛔ `outputs/*.json` 원장은 한 줄도 안 고친다 — 고치는 것은 **빌더 소스**뿐이다.

---

## 6. 고치는 사람이 지킬 것 여섯

1. **지우지 말고 바꿔라.** 틀린 문장을 삭제하면 리포트가 얇아진다. 옳은 서술로 **교체**한다.
2. **숫자가 없으면 «원장 없음» 이라고 쓰고 본문에서 그 숫자를 뺀다.** §3 의 일곱 자리가 그것이다.
3. **손그림 선은 지운다.** 대신 «이 팔은 이 축에서 안 쟀다» 를 캡션에 적는다(F4-1).
4. **팔 표시를 붙인다** — 표에는 «어느 팔» 열, 그림 범례에는 팔 이름. 낱말은 `src/md_mapstyle.py` 의 `ARM_SIONNA`·`ARM_SBR`·`ARM_PO` 가 정본이다.
5. ⛔**정규화가 다른 값을 나란히 놓지 않는다.** 각 팔을 **자기 기준**으로 정규화하고, 그 사실을 캡션에 적는다.
6. 집 규약 — 완충어 0 · 부정문 3 이하 · **과정 서사 금지**(과거 버그 이야기를 쓰지 않는다. 현재 상태만) · 그림 글자 영어 · 방어적 표현 대신 **주장의 크기를 맞춘다**.

---

## 7. 이 계획이 안 다루는 것

· 원장 재계산 여섯 가지(§3) — GPU 가 필요하거나 이번 라운드 밖이다.
· `outputs/report07b_bistatic_md.json` 의 폐기값에 `superseded` 표시 달기 — 원장 편집이라 이번 라운드 밖(F5-10 은 노트북 쪽 방어만 한다).
· 08_3 ↔ 08_2 가 같은 원장(`report15_verdict.json`)을 다른 통계로 내는지의 정합 — 감사가 대조하지 않았다. **근거 없음**.
· 08_2 절 5 를 «반증» 으로 판정한 1 차 감사의 원래 근거 — **모른다**. 2 차 감사가 파일을 새로 열어 세운 근거(F2-1)만 쓴다.
