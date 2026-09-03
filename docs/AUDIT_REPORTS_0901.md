# 레포트 24권 적대 검증 — 2026-09-01

> **왜 이 문서가 있나.** 사용자가 물었다 — 「여태까지 해 온 작업중에서도 저런 말도 안되는
> 결론 지은 것들이 있을거같아서 걱정되네」. 같은 날 덱 13 장에서 포화 인공물을 물리 발견으로
> 읽은 사고가 났고, 그 유형이 과거 기록에도 있는지 전권을 훑었다.
> 규약은 [`CLAIM_GATE.md`](CLAIM_GATE.md) — ⓐ사실 뒷받침 ⓑ과잉 결론.
>
> **사냥 견본으로 우리가 실제로 밟은 사고 4 건을 넣었다** — 포화 인공물, PRF 사다리가 탐색
> 바닥에 걸려 항등식이 된 건, dB 지표가 자세 누락을 비트로 읽은 건, el 0 이 실은 이진이었던 건.

## 0. 총괄

```
제기 89 건  →  독립 재검증  →  살아남음 59 건  (헛짚음 30 건, 34 %)
확인된 것 심각도   fatal 5 · serious 41 · minor 13
지금도 인용되는 것  49 / 59
```

⭐**숫자 위조나 원장 불일치는 사실상 없다.** 한 검증 요원의 말 그대로 「원장 대조 107 개
각주 전부 일치」다. 확인된 것은 전부 **「맞게 계산한 숫자를, 그 숫자가 답할 수 없는 질문에
쓴 것」** 이다 — 덱에서 나온 것과 같은 유형이다.

⛔**이 문서는 «틀렸다» 목록이 아니다.** 대부분은 한 문장(창·격자·전제)을 덧붙이면 끝난다.
각 항목의 «고칠 문장» 이 검증 요원이 제안한 수정안이다.

## 0-1. ⭐먼저 볼 것 — fatal 5 건

| # | 레포트 | 무엇이 인공물인가 |
|---|---|---|
| 1 | `12_outdoor-scene` | 「실외에서 ρ +0.974 → +0.005 로 무너진다」 — 그 변동은 **솔버 낙차**다(el −30 에서 8,192 중 74 자세가 중앙값의 0.25 % 로 떨어졌다 바로 다음 자세에 복귀) |
| 2 | `12_outdoor-scene` | 「정지 클러터 제거로도 박자가 안 돌아온다(ρ +0.039)」 — **같은 낙차를 보간하면 ECA 잔차가 자유공간 기록과 거의 완전히 맞는다.** 결론이 뒤집힌다 |
| 3 | `02_2_stock-engine` | 「사다리 붕괴폭 49.02 dB」 — 마지막 단(450 tri)에 **정반사 경로가 0 개**다. −42.97 dB 는 확산 잔차 바닥으로 갈아탄 값이고, 그 바닥은 광선예산의 함수다(spp 4e6→1.024e9 로 **29.89 dB** 움직인다) |
| 4 | `05_2_switch-grid` | 「el −60 에서 리듬 몫이 86.6 → 32.4 % 로 무너진다(−54 %p)」 — **8,192 자세 중 단 하나**(#3399, 중앙값의 5.4 배)가 만든 값. 둘째로 큰 자세는 1.7 배뿐이다 |
| 5 | `06_6_microdoppler-limits` | 「변조 깊이 +23.19 dB」 — `ptp_db = max − min` 인데 결맞음 합이 거의 완전한 널을 지나므로 **최솟값에 하한이 없다.** 표본을 늘리면 값이 계속 커진다 |

⛔⛔**1·2 번은 어제(2026-08-31~09-01) 내가 쓴 레포트 12 이고, 다음 주 발표 주제가 실외다.**
   그리고 그 낙차는 덱 4 쪽에서 잡은 것과 **같은 유형**이다 — 같은 실수를 이틀에 걸쳐 두 곳에서 했다.
   ⇒ **실외 결과를 다음 주에 올리기 전에 이 둘을 먼저 고친다.**

⭐3·4·5 번의 공통점: **하나의 자세·하나의 단·하나의 정의가 헤드라인 숫자를 통째로 정한다.**
   [`CLAIM_GATE.md`](CLAIM_GATE.md) §1-2 「손잡이 흔들기」 로 잡히는 것들이다.

## 1. 냄새별 분포

| 냄새 | 건수 |
|---|---|
| a difference smaller than the RUN-TO-RUN SPREAD being report | 3 |
| a conclusion that would flip if a free parameter were nudged | 3 |
| a ratio that is large because the DENOMINATOR is tiny/degene | 2 |
| a metric whose value is set by the averaging window (band) r | 1 |
| a metric whose value is set by the grid resolution and by th | 1 |
| a trend that only exists because a SWEEP WAS CUT at a partic | 1 |
| a metric whose value is set by a sampling budget rather than | 1 |
| a 'law' that holds with zero residual because it is an ident | 1 |
| a number quoted with NO LEDGER behind it + a metric whose va | 1 |
| a number from a ledger built with a DIFFERENT convention tha | 1 |
| a quantity pinned at the numerical floor so the 'law' is an  | 1 |
| a ratio/difference that is large because the DENOMINATOR (re | 1 |

## 2. 레포트별

심각도 순, 각 항목은 ⓐ주장 ⓑ왜 인공물인가 ⓒ검증이 직접 돌린 것 ⓓ고칠 문장.

### `12_outdoor-scene.ipynb` — 5 건 (살아 있음 5)

#### 🔴 fatal · **지금도 인용됨**

- **자리** 절 1 결과 2 (cell 2), 목차표 (cell 0), 「이 절이 고정한 것」 ① (cell 6)
- **주장** 「실외 장면을 넣으면 그 둘이 ρ +0.005 와 +0.002 로 무너진다」 / TOC: 「빗각의 박자가 실외에서 ρ +0.974 → +0.005 로 사라지고」 (cells.el-30.rho_outdoor = 0.0047, cells.el-60.rho_outdoor = 0.0021)
- **냄새** a difference/effect produced by a handful of degenerate samples — the same dropout pathology worked example 4 describes, plus 'a ratio large because a few samples are degenerate'
- **왜 인공물인가** The outdoor record's variation is not a physical modulation, it is a solver dropout. At el-30, 74 of 8192 poses (0.90 %) have |E| collapse to ~0.25 % of the median and recover on the very next pose (poses 13-18: 1.071e-04, 1.071e-04, 2.729e-07, 1.071e-04, 1.071e-04, 1.072e-04; consecutive poses are 1/19700 s = 50.8 us apart, and there are 155 poses per 126.7 Hz flash period). On those poses the returned field equals the FREE-SPACE field (|O[bad]| mean 2.415e-07 vs |F[bad]| mean 2.408e-07, ratio 1.00; corr(O[bad],F[bad]) = 0.987) — i.e. the whole 120x120 m ground + 4 buildings + 2 poles contrib
- **직접 돌린 검산** From /workspace/sionna, npz outputs/elevation_sweep_md.npz, arms sionna_p4000000000_swR0D0E0F1_r15_n8192[_envoutdoor01]_mfixbatteryi5_blperairframe_d2/el{+0,-30,-60}. Outlier mask = |a-median|>10*MAD on a=|E|. el-30: 74 bad poses (0.90 %), top 68 poses hold 90 % of AC power, top 1 % hold 99.1 %; rho over good poses only = 0.9636; rho after linear complex repair of the 74 poses = 0.9736 (ledger says 0.0047). el-60: 92
- ⭐**고칠 문장** Section 1 result 2 and the TOC line must not say the beat disappears. The honest statement is that the outdoor record's rho is destroyed by a solver dropout, not by the environment.  Replace 「실외 장면을 넣으면 그 둘이 ρ +0.005 와 +0.002 로 무너진다」 with something like:  "실외 팔의 ρ 는 겉으로 +0.005(el −30) · +0.002(el −60) 지만, 이 값은 8,192 자세 중 74 개(0.90 %) · 92 개(1.12 %)의 솔버 낙차가 만든 것이다. 그 자세에서 |E| 는 중앙값의 0.2~0.5 % 로 떨어졌다가 다음 자세(50.8 µs 뒤)에 완전히 돌아오고, 떨어진 값은 같은 자세의 자유공간 값과 같다(|O|/|F| 중앙값 1.07 · 0.97, |O−F|/|F| 중앙값 0.15). 정적인 장면에서 지면·건물 전체가 한 자세만 사라졌다 돌아오는 것은 물리가 아니다. 자유공간 팔의 같은 앙각에는 그런 자세가 0 개이고, el −30 의 낙차 74 개 중 57
- 확신도 high

#### 🔴 fatal · **지금도 인용됨**

- **자리** 절 2 결과 1·2 (cell 9), 「이 절이 고정한 것」 ① (cell 14)
- **주장** 「제거 뒤에도 박자는 안 돌아온다 — ρ +0.039 / +0.027」 그리고 「잔차가 자유공간 신호와 안 닮았다 — |상관| 0.0228 와 0.0271」; 「이 절이 고정한 것 ① 정지 클러터 제거로는 실외에서 박자가 안 돌아온다」
- **냄새** a conclusion set by a handful of degenerate samples, not by the filter or the physics — it flips when the free parameter (the dropout poses) is nudged
- **왜 인공물인가** cs_eca is a linear DFT projection and is untouched by the dropouts, but the metrics computed on its output are dominated by them. With the same 74/92 dropout poses repaired by linear interpolation and the SAME notch (fcut = 100 Hz) applied, the ECA residual matches the free-space record almost perfectly. So the honest statement is the opposite of the report's: static-clutter removal DOES recover the buried wing beat outdoors; the shipped numbers only say that 0.9 % of the poses are broken.
- **직접 돌린 검산** Same arms. Complex linear repair of the outlier poses, then cs_eca(fcut=100): el-30 rho(residual) = 0.9849 and |corr(residual, free)| = 0.9876 (ledger: 0.0388 and 0.0228); el-60 rho = 0.9768 and |corr| = 0.9911 (ledger: 0.0273 and 0.0271). Without repair I reproduce the ledger exactly (0.0388/0.0228, 0.0273/0.0271).
- ⭐**고칠 문장** 절 2 결과 1·2 와 「이 절이 고정한 것」 ① 은 뒤집혀야 한다. 정직한 진술은:  절 2 결과 1 (교체): 실외 기록의 자세 8,192 개 중 74 개(el −30°) · 92 개(el −60°)에서 |E| 가 중앙값의 0.1~0.5 % 로 떨어지는 **솔버 낙차**가 있다. 그 ≈1 % 의 자세가 기록 변동(AC)의 **99.1 % · 98.8 %** 를 혼자 갖는다 — 나머지 8,118 자세는 |E| 가 중앙값 대비 표준편차 0.0009 인 사실상 상수다. cs_eca 는 전역 DFT 투영이라 그 임펄스가 잔차 전체에 번진다.  절 2 결과 2 (교체): ⭐**정지 클러터 제거는 실외에서 박자를 되찾는다.** 같은 낙차 자세를 복선형 보간으로 메우고 **같은 노치(fcut 100 Hz)** 를 걸면 — el −30° ρ 0.0388 → **+0.9849**, |상관(잔차↔자유공간)| 0.0228 → **0.9876**; el −60° ρ 0.0273 → **+0.9768**, |상관| 0.0271 → **0.9911**. 채움 규칙을 평균 채움으로 바꿔도 같다(el −30° 0.9521 / 0.9823).  절 2 결과 3 (교체): 「걷어낸 것이
- 확신도 high

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 2 결과 3 (cell 9), 머리말 (cell 0), 「지울 것이 정지 성분이 아니다」 (cell 12), 「이 절이 고정한 것」 ② (cell 14)
- **주장** 「⭐걷어낸 것이 거의 없다 — 변동(AC)의 98.7 % 와 98.9 % 가 그대로 남는다」 그리고 그로부터 「환경 에코는 정지 성분이 아니다 — 제거가 변동의 1 % 밖에 못 건드린다」 / 「변동의 99 % 가 남는 것이 그 뜻이다」
- **냄새** a quantity pinned by the bin count / a metric whose value is set by the FFT notch width rather than by the signal, plus a denominator that excludes the very thing being measured
- **왜 인공물인가** ac_left_pct = sum|R-mean(R)|^2 / sum|O-mean(O)|^2. Both sides are mean-removed, so the static component is excluded from the denominator BY CONSTRUCTION — the metric structurally cannot register removal of static clutter, whatever the physics. What it actually measures is how many DFT bins the notch zeroes: fcut = 100 Hz at PRF 19700 / N 8192 (bin width 2.405 Hz) zeroes 83 bins, i.e. 82 of the 8191 non-DC bins = 1.001 %. The measured AC loss is 1.34 % (el-30), 1.08 % (el-60), 0.92 % (el+0) — the flat-spectrum expectation of that bin count, nothing more. And the underlying physical claim is con
- **직접 돌린 검산** FFT of the outdoor arms: bins with |f| <= 100 Hz = 83 of 8192 (1.013 %); 82 of 8191 non-DC (1.001 %). AC energy inside the notch / total AC energy = 1.341 % (el-30), 1.077 % (el-60), 0.915 % (el+0), reproducing ac_left_pct = 98.66 / 98.92 / 99.08. DC energy as fraction of total record energy = 99.093 % (el-30), 98.966 % (el-60), 99.948 % (el+0).
- ⭐**고칠 문장** Section 2 result 3 and everything drawn from it should be replaced. Result 3 currently reads "⭐걷어낸 것이 거의 없다 — 변동(AC)의 98.7 % 와 98.9 % 가 그대로 남는다". It should read roughly:  「3. 제거는 기록 총 에너지의 99.1 %(el −30°) · 99.0 %(el −60°) 를 걷어낸다 — 환경 에코는 압도적으로 정지 성분이다(절 1 이 이미 그렇게 말했다: 오른 것은 표적 변조가 아니라 정지 성분이다). ⭐그런데 남은 1 % 의 변동이 자유공간 드론 변조보다 +36.0 dB(el −30°) · +33.9 dB(el −60°) 커서, 정지 성분을 다 걷어내도 박자가 그 아래 묻혀 있다.」  And the AC-비 숫자는 본문에서 빼거나, 빼지 않으려면 잣대의 한계를 같이 적어야 한다: 「⚠«AC 남은 몫» 은 분모·분자에서 DC 를 이미 뺀 값이라 정지 성분 제거를 구조적으로 못 잰다(제거 뒤 mean(R) = 0). 그 1 % 는 노치가 지운 칸 수다 — 8192 칸 중 83 칸, 비DC 82/8191 = 1.001 %. fcut 을 
- 확신도 high

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 2 결과 4 (cell 9), 「노치 폭 사다리 전체」 (cell 11)
- **주장** 「노치 폭을 100 Hz 에서 5~120 Hz 로 흔들어도 잔차의 닮음이 0.023 에서 0.023 로 소수점 셋째 자리까지 안 움직인다」 및 「|상관| 열이 한 칸도 안 움직이는 것이 그 증거다」
- **냄새** a trend/invariance that is a property of the measurement (impulses are broadband, so no low-frequency notch touches them) rather than of the signal — the same flat column appears for the opposite conc
- **왜 인공물인가** The |r| column is flat because the ~1 % dropout impulses that dominate the residual are broadband and are untouched by any |f| <= 120 Hz notch — not because the beat is genuinely gone. The test has no discriminating power: rerun the identical 5-rung ladder on the dropout-repaired record and the column is equally flat, at the opposite value. An invariance that reads the same for 'beat destroyed' and 'beat intact' is not evidence for either.
- **직접 돌린 검산** Ladder |corr(cs_eca(x,fcut), free)| for fcut = 5/20/60/100/120 Hz. As shipped (x = O): el-30 {0.023, 0.023, 0.023, 0.023, 0.023}, el-60 {0.027 x5} — matches the ledger. On the dropout-repaired record: el-30 {0.988, 0.988, 0.988, 0.988, 0.988}, el-60 {0.992, 0.992, 0.992, 0.991, 0.986}.
- ⭐**고칠 문장** 절 2 결과 4 and cell 11 should not present the flat |상관| column as evidence at all, and the section's headline numbers need to be withdrawn pending a rerun.  Minimum honest replacement for result 4 / cell 11: "노치 폭 5~120 Hz 사다리는 답을 못 바꾼다 — 사다리 전체가 박자 126.7 Hz 아래에 있어 어느 칸도 신호에 닿지 않기 때문이다. 같은 사다리를 박자가 살아 있는 기록에 걸어도 |상관| 열은 똑같이 평평하다(0.988 x5). ⇒ 평평함 자체는 어느 쪽 증거도 아니다. 이 사다리는 자유 파라미터가 결론을 안 바꾼다는 것만 말하고, 박자가 사라졌다는 것은 말하지 않는다."  But the larger correction is that 결과 1~3 and cell 12's mechanism story cannot stand on this ledger. The outdoor arms carry a ~1 % 환경 경로 낙차: 74 / 8192 poses (el-30) and 84 + 8 (e
- 확신도 high

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 3 결과 5 (cell 17), 「격자 비용 전체」 표 (cell 19), 「이 절이 고정한 것」 ③ (cell 21)
- **주장** 「2 × 2 m 조각이면 격자점 213,444 개로 23 배다 — 감당된다」 (grid_cost.patch_2m.points = 213444, vs_drone = 22.7), 그리고 「프레넬 존만큼의 조각(2 × 2 m, 23 배)이면 감당된다」
- **냄새** a number quoted from a geometry different from the one the surrounding text implies — the bbox is computed for the patch alone, but the proposed design puts the patch in the SAME mesh as the drone
- **왜 인공물인가** grid() in outdoor_scene_0901.py is fed R_max = hypot(1,1) = 1.414 m, i.e. the half-diagonal of the patch ON ITS OWN. But src/rcs_sbr.py:grid_ref_from builds the grid from the UNION bounding box of all meshes handed to it (lo/hi over every vertex, ctr = (lo+hi)/2, Rmax from that centre), and the report's own plan (cell 21: 「프레넬 존 조각을 우리 커널의 메쉬에 합치는 설계」) merges the patch into the drone mesh. In this scene's geometry the patch is nowhere near the drone: drone at the origin, ground 20 m below (ENV_SPECS['outdoor01'] alt_m = 20.0), radar at 15 m / el -30, so the ground specular point is 7.99 m hori
- **직접 돌린 검산** Reimplemented grid(): Rout = Rmax*1.15 + 3d, n = ceil(2*Rout/d), d = lam/12 = 7.138 mm. Specular point from flat-earth image geometry (drone z=0, ground z=-20, radar at (15cos30, 0, -7.5)): horizontal 7.99 m. Union bbox of a 0.44 m drone and a 2x2 m patch there -> Rmax 11.16 m -> n = 3,601, points = 12,967,201 = 1,378x the drone-only 9,409 (el-60: Rmax 10.71 m, 11,950,849 points, 1,270x). Report's figure: 462 / 213,4
- ⭐**고칠 문장** 절 3 결과 5 / 「격자 비용 전체」 표 / 이 절이 고정한 것 ③, and the same sentence in the benchmark/elevation_sweep_md.py --env guard, should read roughly:  「프레넬 존 조각(2 × 2 m)은 **크기**로는 작지만, 격자가 **합집합 bbox** 로 정해지므로 그것만으로는 값이 안 나온다. 이 씬의 기하에서 정반사점은 드론에서 el −30° 21.5 m · el −60° 20.8 m 떨어져 있고(드론 원점 · 지면 z −20 m · 레이다 15 m), 조각을 드론 메쉬에 **합치면** R_max 가 조각 크기(1.41 m)가 아니라 그 **떨어진 거리**로 정해진다 — Rout 12.79 m · n 3,583 · 격자점 **12,837,889 개**(el −60° 는 11,819,844). 드론만(실제 격자 n 128 · 16,384 점) 대비 **약 780 배**다. 213,444 개(23 배)는 조각을 **제자리가 아닌 자기 원점에 홀로 놓았을 때**의 값이고, 지금 설계에는 해당하지 않는다.  두 자리 다 격자에 담으려면 온 지면(46,000 배)보다는 낫지만 800
- 확신도 high

### `05_2_switch-grid.ipynb` — 4 건 (살아 있음 4)

#### 🔴 fatal · **지금도 인용됨**

- **자리** cell 0 결과 7; cell 11 «깊이 — 종결하려 했으나 살아 있다» §2; cell 14 판정 4
- **주장** ⚠**깊이 축은 아직 살아 있다** — 깊이 1↔3 을 견준 13 쌍 중 5 쌍이 문턱 밖이다. … **판 밖(−60°)** — R0D0E0F1 은 움직이는 성분의 세기가 +0.09 dB 로 «같은데», 상한 위 바닥만 +12.7 dB 오르고 리듬 몫이 86.6 → 32.4 %(54 %p 낙차)로 무너진다. 세기 하나로는 안 보이던 자리다.
- **냄새** an effect that is 100% one record (worked example 4) — and a number quoted from a ledger whose own retraction the text does not carry
- **왜 인공물인가** The entire −54 pp rhythm collapse and the entire +12.7 dB above-cap floor rise at el −60 are produced by ONE pose out of 8,192 (#3399), whose |E| is 5.4x the median while the second-largest pose is only 1.7x and its immediate neighbours are 1.08–1.13x. It is a single spike, not a depth effect. This was already diagnosed and formally retracted in outputs/depth_axis_verdict_0816.json (2026-08-16, do_not_write_ko: «−60° 에서 깊이 3 이 리듬을 무너뜨린다» 는 철회한다) and in docs/RESUME.md:477 (인용 금지) — eleven days before switch_factorial.json was regenerated on 08-27 — yet the notebook still prints it as live evide
- **직접 돌린 검산** Loaded outputs/elev_sweep_shards/sionna_p4000000000_r15_n8192_d1_el-60_*.npz and ..._onlydepth3_..._el-60_*.npz (8192 poses, 0 missing) and recomputed the report's own metric (P=|FFT((E-mean)*hanning)|^2, above = |f|>=636.5 Hz, comb = k*126.667 +-8 Hz). Reproduced depth1 86.61% / floor -79.97 dB and depth3 32.36% / floor -67.23 dB. Then: depth3 max|E| = 4.615e-06 at pose 3399 vs median 8.521e-07 (ratio 5.4x; 2nd larg
- ⭐**고칠 문장** Cell 11 §2 ("판 밖(−60°)") must be deleted, not softened, and replaced with the forensic note. Suggested house-format replacement:  **cell 11 §2 →** "2. ⛔**판 밖(−60°) 은 반례가 아니었다 — 자세 하나였다.** R0D0E0F1 의 «세기는 +0.09 dB 로 같은데 바닥만 +12.7 dB, 리듬 86.6 → 32.4 %» 는 **자세 8,192 개 중 #3399 하나** 탓이다. 그 자세의 |E−평균| 은 중앙값의 **20.1 배**인데 둘째는 2.89 배뿐이고(isolation 6.97), 이웃 자세도(1.07~1.13 배)·로터 4 회 대칭 짝(1351·5447·7495)도·경로 수(2308 ≈ 중앙값 2260)도 전부 정상이며, 깊이 1 판의 같은 자세는 평범하다. **그 자세 하나만 이웃 평균으로 바꾸면** 깊이 3 이 리듬 **86.36 %** · 바닥 **−153.94 dB** 로 깊이 1(86.61 % · −153.98 dB)과 붙는다 — 깊이 1 에 같은 수술을 하면 86.61 → 86.62 % 로 아무 일도 안 일어난다
- 확신도 high

#### 🟠 serious · **지금도 인용됨**

- **자리** cell 13 «적대적 검증» V8 paragraph; the «1차 선 [dB]» column of the cell 6 table
- **주장** ⛔그러나 이것을 «무늬가 없다» 로 읽으면 틀린다. 같은 원장의 **1 차 선**(제곱검파 뒤 변조 스펙트럼) 열이 회절 켠 네 팔에서 **8.17 · 8.46 · 11.66 · 11.91 dB** 이고, 봉우리가 **넷 다 126.1 Hz** — 예측 박자 자리다. 백색 대조군의 봉우리는 **135.8 Hz**, 엉뚱한 칸이다. ⇒ 리듬 몫(에너지 잣대)은 백색 자리로 내려가지만 **제곱검파로 보면 박자가 남아 있다.**
- **냄새** a peak/floor ratio whose value is set by the search-window bin count rather than the signal (worked example 3) — no null was ever built for this metric, unlike the rhythm share
- **왜 인공물인가** h1_over_floor_db is max over a 7-bin window divided by the median of the 20–500 Hz band, with the peak search confined to a 13-bin window around the predicted bin (build_switch_grid_figs.py:224-227). Its white-noise distribution has median 8.13 dB, so 8.17 and 8.46 dB are literally the null median (p = 0.49 and 0.45), and 11.66 / 11.91 are only p ≈ 0.05 / 0.04. A white draw lands on the 126.10 Hz bin 7.6 % of the time simply because the window is 13 bins wide, and the four arms are near-duplicates (V5 already reports ρ = 0.9868 between two of them), so they are not four independent hits. The s
- **직접 돌린 검산** Reproduced the eight column values exactly from the shards through build_switch_grid_figs.modspec (53.76 / 63.39 / 46.70 / 63.39 / 11.66 / 11.91 / 8.17 / 8.46 dB, all peaks 126.10 Hz). Then ran 2000 complex-white draws (n=8192) through the identical code: null mean 8.03 dB, sd 2.38, p50 8.13, p95 11.71, p99 13.04. p-values: 8.17 → 0.491, 8.46 → 0.446, 11.66 → 0.054, 11.91 → 0.040, while 46.70/53.76/63.39 → 0.0000. Pe
- ⭐**고칠 문장** Cell 13's V8 rebuttal paragraph should keep its conclusion but change its evidence. Replace the 1차 선 argument and the 135.8 Hz contrast with the 2nd/4th harmonic and a window-free peak search, e.g.:  ⛔그러나 이것을 «무늬가 없다» 로 읽으면 틀린다. ⚠다만 근거로 1 차 선을 쓰면 안 된다 — 회절 켠 네 팔의 1 차 선 8.17 · 8.46 dB 는 이 잣대의 백색 귀무 중앙값과 같고(백색 2,000 뽑기: 평균 7.94 · sd 2.39 · 중앙 7.99 dB ⇒ p ≈ 0.47 · 0.42), 11.66 · 11.91 dB 도 p ≈ 0.05 로 아슬아슬하다. 봉우리가 넷 다 126.1 Hz 인 것도 증거가 못 된다 — 봉우리 탐색이 예측 칸 ±6, 즉 13 칸 창 안에 갇혀 있어(build_switch_grid_figs.py:226) 백색도 7.3 % 확률로 그 칸에 앉는다. 백색 대조군의 135.8 Hz 는 «엉뚱한 칸» 이 아니라 같은 창 안의 옆칸이고(백색이 8.4 % 확률로 앉는다), 게
- 확신도 high

#### 🟠 serious · **지금도 인용됨**

- **자리** cell 8 «적용 범위 — 정면(0°)은 예외다»
- **주장** 다만 «계수 1» 이 3σ 안에 드는지는 자리마다 다르다 — −60° 는 3σ 밖(계수 1.08) 이라 그 자리에서는 «품고 있다» 를 단정하지 않는다. … 문장을 쓰는 범위는 **빗각 −15°~−75°** 로 적는다.
- **냄새** a test that passes because the denominator (the error bar) is degenerate — the pass/fail is set by how noisy the measurement is, not by how close the coefficient is to 1
- **왜 인공물인가** contain_sigma is defined as ||residual||/(||e0||*sqrt(n)) (switch_factorial.py:359), so it grows in direct proportion to the added diffraction term. At el −15° the added term is 33.7 dB above the specular series, giving sigma = 0.537 and a 3σ band of [0.35, 3.57] — the test cannot distinguish 'contained at coefficient 1' from 'contained at 3.5'. The measured coefficient there is a = 1.957 ∠ −13.1° with coherence 0.040 (null 0.011), i.e. essentially no measurable containment, yet it passes. el −90° is a = 1.419 with sigma 0.227 and coherence 0.069, also passing. Meanwhile el −60°, whose sigma i
- **직접 돌린 검산** Read outputs/switch_factorial.json diffraction_scope_other_elevations and printed contain_coeff / contain_phase_deg / contain_sigma / contain_dev_sigma / contains_unit_within_3sigma / coh_rho / d_ac_db per elevation: el 0 a=0.980 σ=0.0068 ρ=0.848; el −15 a=1.9574 ∠−13.06 σ=0.5366 dev=1.78σ PASS ρ=0.040 Δac=+33.73 dB; el −45 a=1.0351 σ=0.0166 PASS ρ=0.567; el −60 a=1.0837 σ=0.0191 dev=4.38σ FAIL ρ=0.531; el −75 a=0.96
- ⭐**고칠 문장** Cell 8's scope paragraph should report the coefficients and say what the test can and cannot resolve, instead of reading pass/fail off a band whose width is set by the added term. Suggested replacement for the «다만 …» sentence onward:  「다만 «품고 있다» 를 **잴 수 있는 정도**가 자리마다 다르다. 담김계수는 −15° **1.96∠−13.1°** · −45° 1.04 · −60° 1.08 · −75° 0.97 · −90° **1.42∠−20.5°** 다. 3σ 판정만 보면 −60° 하나만 떨어지는데, 그것은 σ = ‖r‖/(‖e₀‖√n) 가 «얹힌 항 ÷ 원래 항» 에 그대로 비례하기 때문이다 — −15° 는 얹힌 항이 원래 항보다 **33.7 dB** 커서 3σ 띠가 |a| ≤ **2.61** 까지 열려 있고, 계수 1 과 계수 2.5 를 못 가른다. 실제로 원래 항과 겹치는 전력이 −15° 에서 **0.16 %** · −90° 에서 **0.47 %** 뿐이다(판 위 −
- 확신도 high

#### 🟠 serious · **지금도 인용됨**

- **자리** cell 6 «숫자 확인 — 그림에서 본 것» sourcing paragraph; cell 13 V3; figure captions in cells 1, 3, 4
- **주장** 리듬 몫 · 상한 위 바닥 · 빗살 솟음 · 빠진 자세는 outputs/switch_factorial.json … 에서, **1 차 선과 봉우리는 그림 네 장을 만든 outputs/switch_grid.json 에서 읽었다**. … ⭐**두 원장이 겹치는 일곱 행**에서 리듬 몫 기준 **0.04 %p 안**에서 일치한다 — 잣대 두 개가 서로를 검산한다
- **냄새** a number quoted from a ledger built with a different mesh / depth / convention than the surrounding text implies
- **왜 인공물인가** outputs/switch_grid.json was regenerated on 2026-08-27 11:17 (the V3 cross-check ledger adv_switch_grid_0818.json is from 08-18) and now contains five rows built from `..._mfixbatteryi5_blperairframe_d2` arms — canonical mesh at max-depth 2 — while the notebook's plate declares 깊이 1 and its number table comes from depth-1, old-mesh arms. So: the overlap is 4 rows not 7 and the worst rhythm difference is 3.37 %p not 0.04 %p (V3's own pass tolerance is 0.1 pp, so the adversarial test would now fail); the h1 values actually in that file (54.28/64.61/49.45/12.63/10.97) are not the eight printed in
- **직접 돌린 검산** Compared current outputs/switch_grid.json against switch_factorial.json depth-1 el −30 cells: all off 80.60 vs 80.50 (0.10 pp), refraction 58.70 vs 62.07 (3.37 pp), diffraction 12.90 vs 11.67 (1.23 pp), refraction+diffraction 13.20 vs 12.46 (0.74 pp) — 4 overlapping rows, worst 3.37 pp. Checked mtimes (switch_grid.json 08-27 11:17:00 vs adv_switch_grid_0818.json 08-24, generated_kst 08-18) and read benchmark/adv_swit
- ⭐**고칠 문장** Either re-point the report at the ledger it was actually built from, or rebuild the report on the new axis — but the current mixed state must not stand.  Minimal honest fix (keep the depth-1 story, fix the pointers):  - Cell 6 sourcing paragraph — replace "1 차 선과 봉우리는 그림 네 장을 만든 outputs/switch_grid.json 에서 읽었다" with a pinned reference, e.g. "1 차 선과 봉우리는 outputs/switch_grid.json 의 **2026-08-24 판**(git 2ef0aac9 — 여덟 팔 · 깊이 1 · 구 메시)에서 읽었다. ⚠현재 저장소의 같은 파일은 2026-08-27(b480289d)에 **다섯 팔 · 깊이 2 · 정본 메시**로 다시 구워졌으므로 이 표의 여덟 값과 대응하지 않는다."  - Cell 6 cross-check sentence — "두 원장이 겹치는 일곱 행에서 0.04 %p 안에서 
- 확신도 high

### `02_2_stock-engine.ipynb` — 2 건 (살아 있음 2)

#### 🔴 fatal · **지금도 인용됨**

- **자리** 절 5 «면적을 1600배로 키워도 경로 진폭은 7.4e-07 dB 움직인다» — 결과 3 (cell 40) 및 «드론 메쉬에서는 정반사 경로가 자세 하나에서만 살아남는다» (cell 44)
- **주장** 「같은 실험을 기체 메쉬로 옮기면 … 면 2→1 계단이 -6.05 dB … 면 1→0 계단이 -42.97 dB 여서 합이 49.02 dB 다」 / 「둘을 합한 49.02 dB 가 사다리 전체의 붕괴폭이고」 (§5 결과 3 · 셀 40, 셀 44; 각주 [^46] step_1to0_facet_db, [^47] total_collapse_db)
- **냄새** a metric whose value is set by a sampling budget rather than the signal (+ a ratio whose endpoint is degenerate: the '0 facet' rung has no specular path at all, so the number is the diffuse-channel fl
- **왜 인공물인가** 사다리의 마지막 단(450 tri)에는 정반사 경로가 0개다 (facet_count.json levels[-1].spec_n_paths_total = 0, spec_best_coh_db = null). 그래서 -42.97 dB 는 «정반사 진폭이 면 하나 잃고 떨어진 값»이 아니라, 확산(diffuse_reflection=True)을 켠 coh_db — 즉 확산 채널 잔차 바닥 — 으로 갈아탄 값이다. 그 바닥은 물리량이 아니라 광선예산의 함수다: 같은 450-tri 메쉬에서 spp 만 4e6→1.024e9 로 바꾸면 coh_db 가 -102.49 → -72.61 로 29.89 dB 움직인다(같은 표의 incoh_db 는 3.4 dB 만 움직이며 수렴). 헤드라인은 spp=256e6 한 점에서 나온 것이고, 같은 실행을 4e6 또는 1024e6 으로 돌렸으면 계단은 -66.5 dB / -36.6 dB, 합은 72.6 dB / 42.7 dB 로 인쇄됐을 것이다. 게다가 그 마지막 단은 스크립트 자신의 형상 게이트에 걸린 단이다(shape_ok=False, 실루엣 19.3%·bbox 10.2% 편차). 본문은 «그 뒤 계단은 형상 판정에서 떨어지는 마지막 단에서
- **직접 돌린 검산** facet_count.json 에서 직접 재계산: hot rows coh_db = [-33.9045, -33.9042, -33.9045, -39.9579, -39.9583, -82.9256], spec_n_paths_total = [2,2,2,1,1,0], spec_best_coh_db[-1] = None → step_1to0 = -82.9256 − (-39.9579) = -42.9677 dB, total = 49.0211 dB (원장 재현). 같은 파일 budget_sweep 의 450-tri 행: spp 4e6 → coh -102.494, 16e6 → -89.763, 64e6 → -85.164, 256e6 → -78.969, 1024e6 → -72.605 (드리프트 +29.89 dB; incoh 는 -103.93 → -100.53, +3.
- ⭐**고칠 문장** §5 결과 3 (셀 40) and 셀 44 should stop printing -42.97 dB and 49.02 dB. Replacement text:  셀 40 결과 3: "같은 실험을 기체 메쉬로 옮기면 정반사 경로가 존재하는 자세는 36 자세 중 1 개뿐이고, 그 자세에서 정반사 경로 수는 2→1→0 으로 줄어든다. 정반사가 살아 있는 구간의 계단은 -6.05 dB [^45] 로 닫힌형 20·log₁₀(1/2) 에 붙는다 — 다만 그 2 개는 서로 다른 산란체가 아니라 같은 면의 **이미지법 중복 경로**이므로(진폭·지연·위상 산포 0, 1경로값+20log₁₀2 와 5e-07 dB 일치), 잃은 것은 산란체가 아니라 복사본이다. 마지막 단(450 tri)에는 정반사 경로가 **0 개**이므로 그 단의 값은 이 축에서 인쇄하지 않는다."  셀 44 마지막 문단 (replacing "면 1→0 계단이 -42.97 dB 다. 둘을 합한 49.02 dB 가 …"): "⚠ 마지막 단(450 tri)에는 정반사 경로가 0 개다(`spec_n_paths_total` = 0, `spec_best_coh_db` = 없음). 그 단의 coh_db -82.93 dB 는
- 확신도 high

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 5 «드론 메쉬에서는 정반사 경로가 자세 하나에서만 살아남는다» (cell 44) / 절 6 Z4 행 밑의 ⚠ 분해 (cell 54)
- **주장** 「그 한 자세에서 진폭은 기여 면 개수를 따라 계단으로 떨어진다. 면 2→1 계단이 -6.05 dB 로 닫힌형 20·log₁₀(1/2) = -6.02 dB 에 붙고」 (§5 셀 44) — 및 §6 «실루엣이 유지되는 구간(shape_ok = 예)의 몫은 면 2→1 계단 -6.05 dB 이고» (셀 54)
- **냄새** a 'law' that holds with zero residual because it is an identity, not a measurement (+ causal framing reversed: the fine mesh was inflated, the coarse mesh was not depleted)
- **왜 인공물인가** 20·log₁₀(1/2) 에 «붙는» 정도가 -5.5e-07 dB 다 — 두 경로가 물리적으로 다른 두 삼각형이었다면 위상이 달라 이렇게 붙을 수 없다. 실제로 이것은 이 절이 바로 다음 셀(45)에서 스스로 «완전한 복사본»이라 부른 그 중복 경로다: 1경로값 -39.8914794921875 dB 에 20log10(2)=6.0206 dB 를 더하면 -33.870879579, 측정된 2경로값은 -33.870880127 (잔차 -5.48e-07 dB). 즉 데시메이션이 지운 것은 산란체가 아니라 image-method 가 만들어 낸 중복 복사본이고, 부호가 본문 서사(«메쉬를 깎으면 무너진다»)와 반대다 — 성긴 메쉬의 -39.89 dB 쪽이 중복 없는 image-source 값이다. facet_attack.json 이 같은 결론을 이미 적어 두었다: C3.drone_link «데시메이션이 지운 것은 물리적 산란체가 아니라 중복 복사본이다. 6.02 dB 는 애초에 허수 부풀림이었고», must_not_say «'드론에서 면 하나가 없어지자 6 dB 가 날아갔다 = 산란체를 잃었다' — 잃은 것은 중복 복사본이다», direction_warning «⚠ 부호가
- **직접 돌린 검산** -39.8914794921875 + 20*log10(2) = -33.870879579 vs 원장의 2경로값 -33.870880126953125 → 잔차 -5.480e-07 dB. facet_mechanism.json H/G 블록: duplicate_path_forensics 의 per_path_amp_db 가 모두 -75.37211608886719 로 동일, amp_spread_db=0.0 · tau_spread_ns=0.0 · phase_spread_deg=0.0. B_subdivide side=1.0 m: n_tri 2/8/32 에서 coh_db 가 모두 -75.37211455072149 (16배 세분에 0.0 dB).
- ⭐**고칠 문장** §5 (셀 40 결과 3, 셀 44) 과 §6 (셀 54) 에서 -6.05 dB 를 «기여 면 개수» 의 계단으로 인쇄하는 대목을 다음으로 바꾸는 것이 정직하다.  제안 본문 (셀 44): 「그 한 자세에서 스톡 솔버가 내놓는 **정반사 경로 수**가 2→1 로 줄고, 값이 정확히 20·log₁₀(2) 만큼 떨어진다 — 1경로값 -39.8915 dB 에 6.0206 dB 를 더하면 -33.87088 dB 이고, 측정된 2경로값이 -33.87088 dB 다(잔차 5.5e-07 dB). 같은 자세의 **인코히어런트 전력**도 정확히 10·log₁₀(2) = 3.010 dB 차이다(-36.8812 vs -39.8915, 잔차 3.5e-06 dB). 두 경로는 진폭도 위상도 같다 — 이 잔차가 허용하는 위상차는 0.04°, 왕복 경로장 차이로 10 µm 다. 서로 다른 두 삼각형에서는 나올 수 없는 일치이고, 바로 다음 절에서 «완전한 복사본» 이라 부르는 평판 세분 중복과 같은 서명이다. 즉 ⚠ **데시메이션이 지운 것은 산란체가 아니라 중복 복사본이고, 부호가 «메쉬를 깎으면 무너진다» 의 반대다** — 성긴 쪽 -39.89 dB 가 중복 없는 image-sou
- 확신도 high

### `06_6_microdoppler-limits.ipynb` — 2 건 (살아 있음 2)

#### 🔴 fatal · **지금도 인용됨**

- **자리** 절 1, 결과 2-3 and the 「세 자세의 값」 table (cells 2 and 5); footnotes [^2][^5][^8] -> outputs/report15b_microdoppler.json : cells.*.findings.occlusion_ptp_db
- **주장** 「배 쪽(앙각 -15 도)에서는 -4.79 dB · +1.31 dB, 배 옆(방위 90 도)에서는 +23.19 dB · -0.85 dB 다」 and the 세 자세의 값 table: 코 쪽 +4.44 dB / 배 쪽 -4.79 dB / 배 옆 +23.19 dB in the 「가림 · 변조 깊이」 column; the section's stated conclusion 「세 줄이 서로 다른 값을 낸다 — 가림이 자세에 따라 다르게 문다」
- **냄새** a metric whose value is set by a WINDOW LENGTH / sample count rather than the signal (and consequently a difference smaller than the estimator's own spread)
- **왜 인공물인가** benchmark/report15b_microdoppler_recompute.py:225 defines modulation_ptp_db = db.max() - db.min() over the n_t = 6000 slow-time samples, where db = 20*log10|E|. Because the coherent sum passes through near-perfect nulls, the minimum of that series has no limit: it keeps falling as more samples are taken, so ptp diverges with n_t and never converges to a physical value. occlusion_ptp_db is then the DIFFERENCE of two such divergent numbers (F_blade_occ minus G_blade_free), i.e. a difference of two accidental null depths. The +23.19 dB headline is produced by exactly one sample out of 6000: matri
- **직접 돌린 검산** From outputs/report15b_series.npz (raw E series). (1) Drop-k-deepest on matrice4e/belly_side: occlusion ptp = +23.19 dB (k=0), +11.87 (k=1), +7.11 (k=2), +3.65 (k=5), -0.41 (k=10) — one sample of 6000 carries 11.3 dB, ten carry the whole effect. Same test on nose: +4.44 -> +0.12 (k=5); belly: -4.79 -> -0.76 (k=5). (2) ptp vs sample count (random subsets, median of 200 draws, belly_side/F_blade_occ): n=100 -> 35.4 dB,
- ⭐**고칠 문장** 절 1 should stop quoting occlusion_ptp_db as the attitude axis, because that statistic is a difference of two null depths and does not converge in sample count.  Replace 결과 2-3 and the 「세 자세의 값」 table's 「가림 · 변조 깊이」 column with a converging spread statistic, and state its own resampling spread next to it. Suggested wording:    결과 2-3: 「코 쪽(앙각 15도)의 가림 효과는 변조 폭(5-95 백분위) +0.12 dB · 레벨 -0.04 dB, 배 쪽(앙각 -15도)에서는 -1.65 dB · +1.31 dB, 배 옆(방위 90도)에서는 -1.85 dB · -0.85 dB 다.」    Table 「가림 · 변조 깊이」 column: +0.12 / -1.65 / -1.85 dB (5-95 백분위 폭 차), with a footnote that the p-p (max-min) version of the sam
- 확신도 high

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 1, 「판 한 장이 그 dB 의 부호를 정한다」 (cell 6) and the 방법 table row 「⚠ 부호와 크기를 인용하는 범위」; footnotes [^10][^16]-[^24][^28] -> outputs/freeze_plate_sensitivity.json
- **주장** 「판의 중심만 반 칸 옮긴 같은 크기의 판으로 같은 자세를 다시 태우면 가림 dB 가 판마다 이렇게 갈린다 — 세 판(P0 · 반 칸 둘)의 값이다」 with matrice4e/belly = -17.98 / -18.27 / +8.26 and matrice4e/nose = +14.47 / -9.95 / +0.09; 「변조 깊이의 판 셋 흩어짐 26.52 dB p-p 가 위 세 자세의 크기를 삼킨다」; 「그 dB 의 부호와 크기는 판 앙상블 평균(오프셋 여러 판의 평균)이 낸다」
- **냄새** a number quoted from a ledger built with a DIFFERENT convention (150 poses / stride 40) than the surrounding text implies — the instability is booked to plate choice when most of it is sample count
- **왜 인공물인가** The text attributes the entire instability to plate choice and prescribes averaging over plate offsets as the fix. But P0 is by construction the SAME plate as the production run — freeze_plate_sensitivity.json P0 ctr = [-3.5082823943433095e-05, -0.00010858681740835707, 0.01493864451752398] is bit-identical to report15b_microdoppler.json grid_ref.ctr — and P0's own arm levels agree with the production ledger to 0.008-0.53 dB (its p0_vs_production block), i.e. the same physics was traced. Yet P0's occlusion_ptp_db is -17.98 against the headline table's -4.79 for the same cell, and +14.47 against
- **직접 돌린 검산** outputs/freeze_plate_sensitivity.json _meta.stride = 40, cells.*.n_pose = 150; report15b physics n_t = 6000. P0 ctr vs grid_ref.ctr: identical to all 17 digits. p0_vs_production diffs: A_sbr_locked 0.008 dB, F_blade_occ -0.309 dB, G_blade_free -0.526 dB. P0 occlusion_ptp_db: belly -17.978 vs ledger_occlusion_ptp_db -4.792 (gap 13.19 dB); nose +14.469 vs +4.440 (gap 10.03 dB). Independently, decimating the production 
- ⭐**고칠 문장** 절 1 의 판 표(cell 6)와 방법 표의 ⚠ 행은 아래처럼 고쳐야 한다.  ① 표본 수를 밝힌다. 「이 판 표는 생산 자세열 6000 을 stride 40 으로 솎은 **150 자세**에서 났다(`freeze_plate_sensitivity.json _meta.stride = 40 · cells.*.n_pose = 150`). 바로 위 세 자세 표는 6000 자세다 — 두 표는 같은 양의 서로 다른 추정치이지 같은 잣대가 아니다. 같은 판(P0 = 생산 판, `ctr` 이 `grid_ref.ctr` 과 비트까지 같다)에서도 `matrice4e/belly` 가 6000 자세에서 -4.79 dB, 150 자세에서 -17.98 dB 이고 nose 는 +4.44 → +14.47 dB 다.」  ② 26.52 dB 를 판 탓으로 적지 않는다. 「변조 깊이 = 20log10|E| 의 **최대−최소**라 표본 수에 상한이 없다 — 같은 생산 열에서 F 팔 ptp 가 n=75→6000 에서 29.1→50.3 dB 로 마지막 배증에서도 +3.8 dB 씩 계속 오르고, F−G 는 -2.1→-4.79 dB 로 흐른다. 판을 **하나도 안 옮기고** 150 자세를 어느 위상에서
- 확신도 high

### `02_3_target-mesh.ipynb` — 5 건 (살아 있음 5)

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 2 결과 5 (cell 11) · 「이 표가 σ 의 인용 단위를 정한다」 (cell 16)
- **주장** ⭐ 이 세 자가 σ 의 **인용 단위**를 정한다 — 방위평균과 로브 위치로 인용하고, 널 깊이는 자세별 RMS 열에 그 크기가 그대로 적혀 있다.
- **냄새** a number quoted with NO LEDGER behind it + a metric whose value is set by a BIN WIDTH rather than the signal
- **왜 인공물인가** 이 편의 ⭐ 결론은 σ 를 '로브 위치'로 인용해도 된다고 허가하는데, 그 허가를 뒷받침하는 원장이 없다. outputs/{phantom4_scan_compare,real_cad_compare,community_compare}.json 어디에도 lobe/peak 키가 없고(저장소 전체 grep 무소득), 그 세 원장이 재는 것은 Δ 방위평균 σ 와 자세별 RMS 뿐이다. 게다가 방위 격자(7.5°/5.0°/7.5°)가 로브 폭 λ/2D(7.0°/4.7°/1.5° @3.5 GHz)보다 넓어 로브가 아예 해상되지 않는다 — 각 패턴의 lag-1 자기상관이 −0.19~+0.11 로 이웃 칸끼리 무상관이다. 즉 이 격자로는 로브 위치를 잴 수도, 맞다고 말할 수도 없다. 있는 데이터는 오히려 반대다.
- **직접 돌린 검산** 세 원장의 sigma_real/sigma_ours 로 (1) 최대 σ 방위: phantom4 실물 120° 대 우리 180°(Δ60°), typhoon 50° 대 70°(Δ20°), m600 127.5° 대 180°(Δ52.5°) — 상위 3 로브도 세 대조 모두 불일치. (2) dB 패턴 Pearson r = −0.138 / +0.526 / −0.128. (3) 국소최대 개수 17·25·12 개(48~72 칸 중) — 최근접 로브까지 중앙 거리 7.5°/5.0°/7.5° 로 정확히 격자 한 칸, 즉 우연 수준. (4) lag-1 자기상관 real/ours = −0.189/−0.104, −0.094/+0.108, +0.081/−0.146. (5) λ/2D = 7.03°/4.72°/1.47° 대 격자 7.5°/5.0°/7.5°.
- ⭐**고칠 문장** 절 2 결과 5 (cell 11) 와 cell 16 의 「이 표가 σ 의 인용 단위를 정한다」 에서 **로브 위치**를 인용 단위로 허가하는 절반을 걷어내야 한다. 세 원장이 실제로 잰 것은 Δ 방위평균 σ 와 자세별 RMS 뿐이고, 로브 위치를 잰 원장은 저장소 어디에도 없다(빌더 309행의 ⭐ 문장만 유일하게 `_n(...)` 주입 없는 하드코딩이다).  권장 문안:  결과 5 — "⭐ 이 세 자가 σ 의 **인용 단위**를 정한다 — **방위평균으로만 인용한다**. 자세별 RMS 5.2~10.0 dB 는 널 깊이만이 아니라 **칸별 불일치 전체**의 크기다(실물 패턴 상위 4분위 칸에서 RMS 가 phantom4 10.6 dB · m600 12.4 dB 로 하위 4분위 7.2 · 7.8 dB 보다 오히려 크다). **로브 위치는 이 대조가 재지 못했다** — 방위 격자 7.5°/5.0°/7.5° 는 이 연구가 채택한 방위 표본 요구 λ/4D(3.5 GHz 에서 2.33°/1.73°/0.52°, `outputs/report06_derived.json:aspect_finest_deg` 1.38°)보다 3.2~14.4 배 성기고, 패턴의 lag-1 자기상관이
- 확신도 high

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 2 결과 4 (cell 11) · 「형상 검사 세 가지 — 한 표로」 3행 (cell 15) · 「다음 단계」 2행 (cell 17)
- **주장** 자세별 RMS 는 세 대조 전체에서 5.2 ~ 10.0 dB 다 (표 5열 「자세별 RMS 5.2~10.0 dB」, 다음 단계: 「자세별 RMS 를 널 깊이 인용 규약의 문턱으로 굳힌다」)
- **냄새** a difference smaller than the RUN-TO-RUN SPREAD being reported as a difference / 값이 신호가 아니라 격자·정합 규약으로 정해짐
- **왜 인공물인가** 이 RMS 는 널 깊이의 물리적 크기로 인용되고 문턱으로 굳힐 예정인데, 두 메쉬의 방위각이 서로 정합돼 있지 않다. compare_community.py:load_community() 는 원점 이동만 하고 요각을 맞추지 않는다. compare_phantom_scan.py 는 PCA 로 정렬하는데 스캔 bbox 가 348.70 × 348.99 mm(수평 두 축 분산 차 0.08%)라 어느 축이 x 가 될지가 잡음으로 결정된다. 결과적으로 방위 셀 짝짓기가 임의이고, 보고된 값은 무작위 짝짓기 널과 구분되지 않는다. 인용 범위의 상단 10.0 dB 는 가장 정합이 안 된 짝(m600)이 만든다.
- **직접 돌린 검산** σ(az) 를 원형 이동시키며 RMS 재계산 — phantom4: 그대로 6.78 dB, 요 이동 전체에서 min 5.04 / median 6.50 / max 6.95 (관측값이 최악 쪽). m600: 그대로 10.00, min 8.19 / median 9.69 / max 10.30 (역시 최악 쪽). typhoon: 그대로 5.16, min 4.75 / median 7.08 / max 8.23. 방위 셀 무작위 셔플 널 20,000 회 — phantom4 널 평균 6.36 dB [5.43, 7.17], 관측 6.78 = 83 백분위(p=0.83); m600 널 9.56 [8.58, 10.50], 관측 10.00 = 81 백분위(p=0.81); m100 널 7.56, 관측 7.18 (p=0.22). 즉 3 대조 중 2 개는 방위 대응을 무작위
- ⭐**고칠 문장** Keep the Δ 방위평균 σ row as-is (-2.00 / -0.40 / +1.80 dB) — it is exactly invariant to yaw registration. Fix the 5th column and the null-depth sentence. Suggested replacement for 결과 4 and the table's "그 지표의 바닥" cell: "실물 유래 메쉬와의 Δ 방위평균 σ 는 -2.00 · -0.40 · +1.80 dB 다. 자세별 RMS 는 5.2~10.0 dB 지만, **이 값은 널 깊이의 물리적 크기가 아니다** — 두 메쉬의 요각이 정합돼 있지 않다(`mesh_compare.compare()` 는 방위 셀을 첨자 순서로 짝짓고, `compare_phantom_scan.py` 의 PCA 축은 스캔 bbox 348.70 x 348.99 mm 에서 잡음으로 갈린다). 방위 셀을 무작위로 섞은 널(2만 회)에서 Phantom 4 는 6.36 dB [5.43, 7.17] · M600 은 9.56 dB [8.58, 10.51] 이 나오고, 관측값 6.78 · 10.00 은 각각 83 · 81 백분위다 — 즉 방위 대응
- 확신도 high

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 2 결과 4 (cell 11) · 「형상 검사 세 가지 — 한 표로」 3행 (cell 15) · 방법 표 「실물 유래 메쉬」 행 (cell 12)
- **주장** 실물 유래 메쉬와의 Δ 방위평균 σ 는 -2.00 · **-0.40** · +1.80 dB 이고 … 대상은 Typhoon H480 (real CAD, Apache-2.0) — 방법: 「우리 SBR+PO 커널(B)에 넣어 … 양쪽 메쉬를 전부 PEC 로 덮고 … Phantom 4 는 프롭·짐벌을 뺀 채」 (원장 name_ours = "Typhoon H480 (ours, from spec sheet)")
- **냄새** a conclusion that would flip if a free parameter were nudged / 원장이 본문이 시사하는 것과 다른 규약으로 만들어짐
- **왜 인공물인가** 셋 중 가장 좋은 일치(-0.40 dB)를 '제원에서 지은 메쉬가 실물 CAD 와 이만큼 맞는다'로 읽게 되어 있지만, benchmark/compare_real_cad.py:ours_body_only() 는 우리 메쉬의 envelope_mm 을 실물 STL 의 bbox 로 덮어쓴 뒤 A.scaled(...) 로 외형을 강제 정합한다. 자유 배율이 참조에 맞춰진 것이다. 또 이 비교는 동체만이고(프롭·다리·짐벌 제외 — 코드 주석: "로터 배치는 우리 추측이라 비교를 오염시킨다") 본문은 그 제외를 Phantom 4 에 대해서만 밝힌다. el 15° 실루엣은 측면 투영이 지배하므로 z 배율 0.52 는 이 수를 몇 dB 옮긴다.
- **직접 돌린 검산** 원장 대조: bbox_real_mm = [455.4132385253906, 520.3530883789062, 158.24980163574222], bbox_ours_mm = [455.4132385253907, 520.3530883789062, 158.24980163574222] — 유효숫자 13 자리 일치(다른 두 대조는 phantom4 348.7×349.0×184.7 대 289.5×289.5×196.0, m600 높이 670.6 대 292.0 으로 크게 어긋남). 정합 전 메쉬를 직접 다시 지어 봄: 우리 from-spec 동체 452.169 × 517.000 × **304.240** mm 대 실물 455.413 × 520.353 × **158.250** mm → ours_body_only 가 적용하는 축별 배율 [1.0072, 1.0065
- ⭐**고칠 문장** §2 결과 4 (cell 11) 과 「형상 검사 세 가지」 표 3행 (cell 15) 의 Typhoon 값은 다음 두 가지를 명시해야 한다.  (1) **대상**: Typhoon 대조는 조립 전체가 아니라 **동체(프레임)만**이다 — 다리·프롭·CGO3 짐벌은 빠져 있고 비교 대상은 455×520×158 mm 의 동체다(§1 갤러리 표의 634×704×319 mm 가 아니다). 현재 방법 표는 프롭·짐벌 제외를 Phantom 4 에만 적어 두었다.  (2) **−0.40 dB 는 독립 일치가 아니다**: `benchmark/compare_real_cad.py:ours_body_only()` 가 실물 STL 의 바운딩박스를 `envelope_mm` 으로 주입한 뒤 다시 축별로 `A.scaled(...)` 를 걸어 외형을 **참조에 강제 정합**한다(축별 배율 [1.0072, 1.0065, **0.5201**] — z 를 48% 눌러 다리·짐벌이 만든 높이 초과를 지운다). 그래서 원장의 `bbox_ours_mm` 이 `bbox_real_mm` 과 마지막 자리까지 같다. 같은 조건(el 15° · 3.5 GHz · 방위 72 · 양쪽 PEC)에서 이 정합만 끄
- 확신도 high

#### 🟡 minor · **지금도 인용됨**

- **자리** 절 2 결과 4 (cell 11) · 「형상 검사 세 가지 — 한 표로」 3행 값 열 (cell 15)
- **주장** 실물 유래 메쉬와의 Δ 방위평균 σ 는 -2.00 · -0.40 · **+1.80 dB** 이다
- **냄새** a difference smaller than the RUN-TO-RUN SPREAD being reported as a difference
- **왜 인공물인가** 세 값이 소수 둘째 자리까지 인용되지만, 각 값은 48~72 개 방위 칸의 평균이고 칸끼리 무상관(lag-1 자기상관 ≈ 0)이라 방위 표본추출 자체의 오차가 dB 단위다. 특히 m600 의 +1.80 dB 는 0 과 구분되지 않는다 — 즉 '커뮤니티 메쉬 대비 +1.8 dB 밝다'가 아니라 '이 격자로는 차이를 못 잰다'가 정직한 판정이다. Δ 의 인용 자릿수(±0.01 dB)가 그 수의 표본오차(±0.9~1.9 dB)보다 두 자릿수 작다.
- **직접 돌린 검산** 방위 칸 부트스트랩 20,000 회(칸 재추출 후 10log10(mean) 재계산): phantom4 Δ=-2.00 dB, SE 0.94, 95% CI [-3.77, -0.08]; typhoon Δ=-0.40, SE 0.45, CI [-1.27, +0.51]; m600 Δ=+1.80, SE **1.85**, CI [**-2.60, +4.55**] — 0 을 넉넉히 포함. m100(원장에 있으나 본문 미인용) Δ=+0.58, CI [-1.69, +2.36].
- ⭐**고칠 문장** 절 2 결과 4 와 「형상 검사 세 가지」 3행은 다음과 같이 적어야 한다.  "실물 유래 메쉬와의 Δ 방위평균 σ 는 Phantom 4 스캔 -2.0 dB · Typhoon H480 실물 CAD -0.4 dB 다. **M600 커뮤니티 메쉬는 이 격자로 못 잰다** — 우리 M600 메쉬가 6회 대칭이라 방위 48칸(7.5° 간격)이 60° 주기의 대칭축 여섯 곳(az 0·60·120·180·240·300)에 정확히 얹히고, 그 여섯 칸만으로 우리 쪽 방위평균의 91.9% 가 나온다(커뮤니티 메쉬는 상위 6칸이 32.9%, 대칭축 위 칸 8.9%). 같은 스윕을 한 칸씩 걸러 둘로 나누면 우리 쪽 평균이 13.95 dB 움직이고(커뮤니티 메쉬는 1.73 dB) Δ 가 +5.6 dB 와 -10.1 dB 로 갈린다. 격자를 반칸(3.75°) 밀거나 4배(192칸)로 조밀하게 해 다시 돌리면 우리 쪽 평균이 -7.58 → -8.87/-9.11 dBsm 로 내려가, 인용된 +1.80 dB 가 사실상 사라진다. 즉 +1.80 dB 는 두 메쉬의 밝기 차가 아니라 방위 격자가 대칭축에 얹힌 결과다."  그리고 세 값 전부 소수 둘째 자리로 인용하지 않는다 — 방위 칸
- 확신도 high

#### 🟡 minor · **지금도 인용됨**

- **자리** 「형상 검사 세 가지 — 한 표로」 2행 '그 지표의 바닥' 열 (cell 15) · [^59] cad.floor_pct = 6.896
- **주장** 독립 눈금 — 제조사 CAD ↔ 자사 발행 제원이 6.90% 까지 갈린다
- **냄새** a number from a ledger built with a DIFFERENT convention than the surrounding text implies
- **왜 인공물인가** 이 6.90% 는 CAD 검사가 아무것도 못 가르는 바닥으로 인용되지만, 원장이 같은 블록에 그 값이 정의 불일치일 가능성을 적어 두었다 — floor_caveat: "917 is likely mount-edge to mount-edge, not axis to axis". 게다가 이 값은 우리 함대에 없는 기체(Freefly Astro, maps_to '—', 파일명 [Shelled] 외피뿐)의 'Motor-axis diagonal' 한 항목에서 나오고, 두 번째로 큰 간극은 1.07%(Sentinel)로 6.4 배 작다. 본문은 caveat 도 second 값도 옮기지 않아, 물리적 CAD↔제원 불일치처럼 읽히지만 실제로는 치수 정의 규약 차이가 만든 수다. 방향은 보수적이지만(검사를 실제보다 6 배 무디게 보이게 함) 그만큼 X500 V2 의 0.56% 일치가 뜻하는 바를 지운다.
- **직접 돌린 검산** outputs/report02_derived.json cad 블록 직독: floor_pct 6.8961617667414705, floor_dim 'Motor-axis diagonal', floor_aircraft 'Astro', floor_caveat '917 is likely mount-edge to mount-edge, not axis to axis', floor_second_pct 1.0692228357168665 (Sentinel, 'Motor-to-motor square side'). assemblies 표에서 Astro 는 n_part_types 1 · maps_to '—' · note '외피뿐, 내부 산란체 없음'. 6.896 / 1.069 = 6.4 배.
- ⭐**고칠 문장** The floor cell should not quote 6.90%. Suggested replacement for the 「그 지표의 바닥」 cell of row 2, plus a ⚠ line:  「독립 눈금 — 정의가 같은 치수에서 제조사 CAD ↔ 자사 발행 제원 간극은 최대 1.07% (Sentinel, 모터 사각 변) 이고, X500 V2 자신은 0.56% (공표 500 mm 가 반올림값) 다.」  ⚠ 원장의 최대 간극은 Astro 「Motor-axis diagonal」 6.90% 지만 이는 CAD↔제원 불일치가 아니라 치수 정의 불일치다 — 발행 917 mm 는 축간이 아니라 모터 마운트 바깥끝 대각이고, 벤더 GLB 에서 그 바깥끝 대각을 직접 재면 916.96 mm 로 공표값과 0.005% (0.04 mm) 안에서 맞는다 (축간은 853.76 mm, 마운트 반경 31.6 mm 차이). Astro 는 우리 함대에 없고(maps_to '—', [Shelled] 외피뿐) 이 바닥에 들어갈 자리가 아니다.  And the 「방법」 row should read: 「CAD 의 바닥 | 제조사 CAD 와 자사 발행 제원이 **같은 정의의 치수에서** 갈리는
- 확신도 high

### `10_2_robustness.ipynb` — 5 건 (살아 있음 5)

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 2 (표적모형 갈아끼우기) — 셀 13 표, 셀 10 결과 4, 셀 15
- **주장** 표: 「무엇을 맞추나 | M1 평판 [dB] | ... | 선형평균 +0.00 [^35] / 중앙값 +0.00 [^38] / dB 평균 +0.00 [^41] / p10 +0.00 [^44]」 그리고 「⚠ 검출기가 읽는 p10 에서 맞추면 낙차가 2.30 dB [^29] 로 줄고 세 팔의 순서가 뒤집혀 M1 이 가장 어려운 팔이 된다」
- **냄새** quantity pinned by construction — the 'law' is an identity; conclusion driven by a degenerate (zero-variance) reference arm
- **왜 인공물인가** M1 은 측정된 팔이 아니라 눈금 자체다. 원장 outputs/tm_result.json 의 protocol.operating_point.definition 이 직접 이렇게 적어 놓았다: "...M1 under normalisation (a) reads 0.000 dB extra gain in every environment BY CONSTRUCTION — it is the ruler, not a result". 동작점 A_ref 를 «평판 -12.81 dBsm 이 정확히 앙상블평균 Pd=0.9 에 앉도록» 정의했으므로 M1 의 요구 추가이득은 어떤 추정량으로 맞추든 0 이다. 표의 네 행은 서로 다른 각주 4개(^35/^38/^41/^44)를 달아 네 번 독립 확인한 것처럼 보이지만 같은 항등식 하나다. 더 중요한 것은 결과 4 의 «순서가 뒤집혀 M1 이 가장 어려운 팔» 이라는 결론인데, M1 은 자세분산이 정확히 0 이라 p10 = 평균이고 분산이 있는 다른 두 팔은 p10 < 평균이므로, p10 에서 레벨을 맞추면 M1 이 21/21 셀에서 자동으로 최악이 된다. 물리가 아니라 분산 0 의 산술이다. 원장 자신도 이 정규화를 "순환적이라 정본이 될 
- **직접 돌린 검산** outputs/tm_attack.json:Q1_normalisation.recomputed_spread_db_by_matching_estimator.<est>.per_model_extra_gain_db.M1 을 여섯 추정량 전부에서 읽음 → mean_lin/median/mean_db/p10/p95/max 모두 M1 = 1.27531131e-06 (부동소수 잡음, 비트 동일). 같은 파일 circular_diagnostic_p10.order_counts = {M3<M2<M1: 10, M2<M3<M1: 11} → M1 이 21/21 셀에서 최상(가장 어려움). outputs/tm_result.json:protocol.operating_point.definition 원문 확인.
- ⭐**고칠 문장** Section 2 should mark the M1 column and the p10 row as constructions, not measurements. Concretely:  Table (cell 13) — replace the bare M1 column with a note, e.g. column header "M1 평판 [dB] — 눈금(동작점 정의)" and a line under the table: "M1 은 자세분산이 정확히 0 (snr_spread_std_db = 0.0, 210셀 전부) 이고 동작점 A_ref 자체가 «평판 -12.81 dBsm 이 앙상블평균 Pd = 0.9 에 정확히 앉도록» 정의되어 있으므로(tm_result.json:protocol.operating_point.definition, 원문 «it is the ruler, not a result»), 어떤 추정량으로 맞추든 M1 의 요구 추가이득은 정의상 0 이다. 네 행의 +0.00 은 네 번의 독립 확인이 아니라 같은 항등식 하나다."  결과 4 / 셀 15 — keep the estimator-dependence point but strip the ranking cla
- 확신도 high

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 2 — 셀 12·13 (M1 정의), 셀 10 결과 1, 셀 17 다음 단계
- **주장** 「우리 SBR+PO 격자(M3) ... 선형평균 +7.52 dB [^37]」 · 「우리 팔의 요구 추가이득 7.52 dB [^52] 와 낙차 몫 25.7% [^53] 가 현재 메쉬 위에 선다」 · 「세 모형은 자세무관 평판 σ -12.81 dBsm [^21] (3GPP, M1)」
- **냄새** a conclusion that would flip (halve) if a free parameter were restored to the standard's own value; the baseline's degenerate variance inflates the numerator
- **왜 인공물인가** M1 의 «자세무관 평평함» 은 3GPP 가 아니라 우리 규약이다. TR 38.901 은 σ_S(3.74 dB 로그정규)를 경로마다 뽑는데, 이 실험은 그것을 평균(=1)에 얼려 M1 을 인위적으로 평평하게 만들었다. 리포트는 M1 을 그냥 «(3GPP, M1)» 로 표기해 그 평평함이 표준의 성질인 것처럼 읽히게 한다. 프로젝트 자신의 적대검증 원장(outputs/tm_attack.json)이 이것을 ⭐ must_fix 로 올려 놓았다: "M1 을 3GPP 규정대로 σ_S 를 뽑아 돌린 M1c 분기를 추가하고 그것을 정본으로 삼아라(현재 M1b 는 3GPP 의 확률항을 우리가 끈 변형이다). M3−M1 은 7.52 가 아니라 3.02 dB 다." 즉 헤드라인의 60% 가 우리가 끈 확률항의 몫이다. 리포트에는 σ_S 라는 단어가 한 번도 없고(grep 0회), 그런데도 7.52 dB 를 다음 라운드로 들고 갈 수(다음 단계) 로 적었다.
- **직접 돌린 검산** outputs/tm_attack.json:Q5_shape_vs_aspect_dependence.evidence[«M1 을 3GPP 규정대로(σ_S 3.74 dB 로그정규) 돌리면»].result = {m1_penalty_if_drawn_db: 4.5025, m3_minus_m1_frozen_db: 7.5196, m3_minus_m1_live_db: 3.0171, spread_frozen_mean_db: 29.3022, spread_live_mean_db: 24.7997} → M3−M1 이 7.52 → 3.02 dB (−59.9%), 3모형 낙차가 29.30 → 24.80 dB. grep 'σ_S|sigma_S|Swerling' reports/10_2_robustness.ipynb reports/_parts/65_target-model-swap
- ⭐**고칠 문장** 셀 12·13 (M1 정의) — 「(3GPP, M1)」 를 「(3GPP TR 38.901 §7.9.2.1 RCS model 1, σ_S 를 평균에 얼린 우리 규약 — M1b)」 로 바꾸고, 셀 12 의 「M1 은 3GPP 표값 상수이고」 뒤에 한 문장을 붙인다:    ⚠ M1 의 «평평함» 은 절반만 3GPP 다. TR 38.901 Table 7.9.2.1-1 은 σ_M = -12.81 dBsm 과 함께 σ_S 표준편차 3.74 dB 로그정규를 주고, 그것을 경로마다 뽑는다(eq 7.9.4-1 Step 10, μ = -(ln10/20)σ² 에서 μ+3σ 절단). 우리 폐형 사슬에는 경로 앙상블이 없어 σ_S 를 평균(=1)에 얼렸다 — tm_setup 이 «어느 쪽인지 declare 하라» 고 적어 둔 그 선택이다. 켜면 M1 도 4.50 dB 를 문다.  셀 10 결과 1 · 셀 13 표 — M1 열의 +0.00 dB 는 «결과가 아니라 자» 임을 명시하고(tm_result.json protocol.operating_point: "M1 ... reads 0.000 dB BY CONSTRUCTION — it is the ruler, not a result")
- 확신도 high

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 1 (σ-free 축) — 셀 2 결과 1, 셀 3 방법표, 셀 5 표 WiFi 행
- **주장** 「WiFi 는 상시 기준(등급 1)에서 11.87 dB [^1], 세션 기준(등급 3)에서 11.66 dB [^2] 라 상시 제약의 대가가 +0.21 dB [^3] 다」 · 방법표 「무엇을 읽나 | 기준신호 대역과 프레임 수가 정하는 파형 축 하나다」 · 표의 «거리분해능 대비 3.92 m ↔ 3.92 m»
- **냄새** a number quoted from a ledger built with a different convention than the surrounding text implies — the named explanatory axis is identical on both sides of the comparison
- **왜 인공물인가** WiFi 행에서 리포트가 축으로 지목한 양은 두 등급 사이에 전부 같다. W1 과 W3 는 기준신호 이름(VHT-LTF) · 기준신호 대역(76.5625 MHz) · 프레임 수 M=112 · b=9 · Ns · PRF · 거리분해능(3.9157 m)이 모두 동일하다. 따라서 +0.21 dB 는 «기준신호 대역과 프레임 수» 로는 원리적으로 설명될 수 없다. 실제로 유일하게 다른 것은 송신파형의 데이터 점유율(0.091 vs 0.891)이고, 그것이 결과에 들어오는 이유는 시뮬레이션이 «기지 기준신호» 가 아니라 **송신파형 전체**를 상관 기준으로 쓰기 때문이다(experiment_detection.py:144-145 `ref_cpi = np.tile(wf.tx, b*M)`, 코드 주석: "각 모드는 그 모드의 송신 파형(wf.tx) 을 기준으로 상관한다(full-waveform capture 상한)"). 즉 이 칸이 재는 것은 상시 기준신호 제약의 대가가 아니라 기준채널 모형화 규약(전파형 포착 상한)의 대가다. 같은 표가 거리분해능은 ref_bw 로 계산한 값(3.92 m)을 나란히 실어 두 규약을 섞는다. 리포트 §1 은 이 규약을 한 번도 밝히지 않는
- **직접 돌린 검산** outputs/detection_rx_sweep.json 모드 메타 비교: W1 ref_name=VHT-LTF ref_bw=76.5625 MHz occ=0.091 M=112 b=9 Ns=4193280 prf=2136.8 dR=3.9157 / W3 ref_name=VHT-LTF ref_bw=76.5625 occ=0.891 M=112 b=9 Ns=4193280 prf=2136.8 dR=3.9157 — occupancy 외 전부 동일. src/experiment_detection.py:144-145 및 :117 주석 확인.
- ⭐**고칠 문장** The WiFi row should stop calling its +0.21 dB a cost of the always-on reference-signal constraint, and §1 should state the correlation convention once.  Concretely:  1. Result bullet 1 — replace the reference-signal framing for WiFi:    "WiFi 의 두 등급은 기준신호가 같다 — W1·W3 모두 VHT-LTF 이고 기준신호 대역 76.56 MHz · M=112 · 거리분해능 3.92 m 가 전부 같다. 그래서 이 칸의 +0.21 dB 는 상시 기준신호 제약의 대가가 아니라, 상관 기준으로 송신파형 전체를 쓰는 규약(full-waveform capture 상한) 아래에서 데이터 점유(9.1% → 89.1%)가 파형의 자기상관 부엽을 −7.35 dB → −13.62 dB 로 낮춘 몫이다."  2. Method table 무엇을 읽나 — the current line is false for the WiFi row; it should read:    "기준신호 대역 · 프레임 수 
- 확신도 high

#### 🟡 minor · **지금도 인용됨**

- **자리** 절 1 — 셀 2 결과 2, 셀 5 표 LTE 행
- **주장** 「LTE 의 대가는 +0.08 dB [^4]」 (표: LTE 13.76 dB [^13] ↔ 13.68 dB [^14], +0.08 dB)
- **냄새** a difference smaller than the run-to-run (Monte-Carlo) spread reported as a difference
- **왜 인공물인가** 같은 노트북 절 3 이 SNR50 한 추정의 몬테카를로 표준편차를 0.043 dB [^60] 로 못박고, +0.47 dB 의 초과분을 «11.0σ / 7.8σ» 라며 유의성을 따진다. 그 잣대를 절 1 에 그대로 대면 LTE 의 +0.0754 dB 는 차이의 σ 대비 1.5σ 밖에 안 된다 — 절 3 이 요구한 문턱의 1/5 이다. 물리적으로도 그럴 만하다: L1(CRS) 과 L3(PRS) 의 기준신호 대역은 17.985 vs 18.015 MHz(0.17% 차)이고 거리분해능은 16.67 vs 16.64 m 로 사실상 같다. 리포트는 이 숫자를 오차 표기 없이 결과 목록과 표에 확정값으로 싣는다. (WiFi 4~6σ, 5G 100σ 이상이라 이 지적은 LTE 행에 한정된다.)
- **직접 돌린 검산** Pd 곡선의 이항오차로 SNR50 의 σ 를 재계산: σ = sqrt(0.25/K)/slope, K=6000 → L1 0.0353 dB, L3 0.0364 dB → σ(차) = 0.0507 dB, cost 0.0754/0.0507 = 1.49σ. 독립 이항 부트스트랩(B=20000, 단조 강제)으로도 σ(차)=0.0353 → 2.14σ. 같은 계산에서 WiFi 3.9~5.7σ, 5G 75~106σ.
- ⭐**고칠 문장** 절 1 결과 2 와 셀 5 표의 LTE 행은 «+0.08 dB» 를 확정값으로 실을 수 없다. 절 3 이 이미 못박은 SNR50 의 몬테카를로 산포(0.043 dB [^60], K = 6000 [^59])를 같은 벤치·같은 동작점에 그대로 대면, 시드 7개로 다시 돌린 LTE 의 대가는 +0.011 ± 0.010 dB (표준편차 0.025 dB, 95% 구간 −0.013 ~ +0.034 dB)이고 시드에 따라 부호까지 바뀐다.  제안 문장 — · 결과 2: "5G 의 대가는 +3.82 dB [^5] 다. LTE 는 +0.08 dB [^4] 로 읽히지만 이 값은 SNR50 추정의 몬테카를로 산포(σ ≈ 0.03~0.04 dB, 절 3 [^60]) 안에 있다 — 시드를 바꿔 7회 재현하면 +0.011 ± 0.010 dB 로 0 과 구별되지 않고 부호도 뒤집힌다. 즉 **LTE 는 상시 제약의 대가가 측정되지 않는다**. 물리적으로도 그럴 만하다: L1(CRS) 과 L3(PRS) 의 기준신호 대역이 17.985 [^?] 대 18.015 MHz [^?] 로 0.17% 차이뿐이다." · 셀 5 표 LTE 행의 «대가» 칸: `+0.08 dB [^4]` → `≈ 0 (
- 확신도 high

#### 🟡 minor · **지금도 인용됨**

- **자리** 절 5 (교정 절대 σ 체크리스트) — 셀 38 결과 4, 셀 41 표 «배경 차감» 행
- **주장** 「배경 차감은 지면반사 경로차가 거리분해능보다 커야 성립하고, 기하 78% [^83] 가 그 조건을 만족한다」 · 체크리스트 「지면반사 경로차 > ΔR — 기하 78% [^83] 가 분리」
- **냄새** a ratio whose value is set by the grid the author typed in, not by the physics; and the grid includes a point the report's own neighbouring row forbids
- **왜 인공물인가** 78% 는 21/27 이고, 27 은 손으로 적은 h∈{1.5,2,3} × H∈{5,10,20} × R∈{20,30,50} 조합수다. 확률도 가중도 없는 열거이므로 값은 전적으로 그 세 리스트의 끝점이 정한다. 게다가 R=20 m 행 9개는 **같은 표의 «원거리장 거리» 행이 요구하는 R ≥ 24.44 m [^80] 를 위반**한다. 그 9행을 빼면 78% 가 아니라 66.7% 이고, R=100 m 를 한 줄 더 넣으면 63.9%, 둘 다 적용하면 51.9% 다. 즉 «기하의 78%» 는 부지 기하의 성질이 아니라 격자 선택의 성질이다. 리포트 11 절 1 도 같은 78% 를 인용한다.
- **직접 돌린 검산** outputs/report06_derived.json:ground_bounce (27행) · ground_bounce_n_geom=27 · ground_bounce_sep_frac_200MHz=0.7777778 = 21/27. 판정식 2hH/R > c/(2·200MHz)=0.74948 m 를 직접 재계산: as-shipped 21/27=0.7778 · R≥24.44 m 만(R∈{30,50}) 12/18=0.6667 · R∈{20,30,50,100} 23/36=0.6389 · 둘 다 14/27=0.5185.
- ⭐**고칠 문장** Two edits, both to /workspace/sionna/reports/10_2_robustness.ipynb (cell 38 result 4 and cell 41 «배경 차감» row); no ledger change needed.  Cell 38, result 4 — say what the 78% counts and at which bandwidth: "배경 차감은 지면반사 경로차 2hH/R 이 거리분해능보다 커야 성립한다. 설계 격자 27 개 (h∈{1.5,2,3} m × H∈{5,10,20} m × R∈{20,30,50} m, 가중 없는 열거) 중 200 MHz 눈금에서 분리되는 것이 21 개, 78% [^83] 다 — 부지 확률이 아니라 격자 계수다. 이 비율은 눈금 대역에 강하게 의존한다: 400 MHz 게이팅에서 96%, 100 MHz 에서 48% 다."  Cell 41, «배경 차감» 수치 임계 칸: "지면반사 경로차 > ΔR — 설계 격자 27 개 중 21 개 [^83] (200 MHz 눈금) 가 분리. 부지 선정은 리포트 11 절 1 그림 2 로 한다"  Recommended additions, in order of value: 1
- 확신도 medium

### `09_observability.ipynb` — 4 건 (살아 있음 0)

#### 🟠 serious · 이미 사문화

- **자리** 셀 8 «관측가능성 — 수신기 2대면 위치가 풀린다» 의 4행 표 (source: reports/_parts/55_observability.ipynb; ledger outputs/verify_observability.json → fixes.'1RX (baseline)'.pos_rms_m)
- **주장** 절 1 «관측가능성» 표: "| 1RX (baseline) | 3 | 57.75 m |" — 형상별 «위치 RMS 오차» 열에 1RX 값 57.75 m 를 싣고, 2RX 0.19 m 와 나란히 놓아 수신기를 하나 더하면 오차가 300배 줄어드는 것처럼 읽히게 한다.
- **냄새** a number set by a numerical cutoff (pinv rcond) rather than the signal — and the same table uses two different tolerances in two adjacent columns
- **왜 인공물인가** 1RX 그램행렬은 정규화 고윳값이 [-1.5e-17, 8.3e-18, 1.5e-11, 2.3e-07, 0.051, 1.0] 로 **두 방향이 정확히 영**이다(회전 유령). 그 방향의 CRLB 는 무한대인데, np.linalg.pinv(G, rcond=1e-13) 이 영공간을 버리기 때문에 남은 부분공간만으로 유한한 57.75 m 가 나온다. 생성 스크립트 benchmark/verify_observability.py:627 은 바로 이 문장을 stdout 으로 찍는다 — «1RX 의 위치 CRLB 가 유한해 보이는 것은 pinv 가 영공간을 버리기 때문이다 — 그 방향의 실제 오차는 무한대(회전 유령)». 노트북은 그 경고를 옮기지 않았다. 게다가 같은 표의 랭크 열은 실용 허용오차 1e-08 (1RX → 3)을 쓰는데 RMS 열은 rcond 1e-13 (=4방향 유지)을 쓴다. 두 열을 같은 1e-08 로 맞추면 1RX 의 RMS 는 0.042 m 가 되어 2RX 의 0.19 m 보다 **좋아진다** — 표가 말하는 방향이 뒤집힌다. 즉 57.75 m 는 기하가 정한 값이 아니라 어느 고윳값에서 자르느냐가 정한 값이다. (2RX 행은 최소 고윳값 1.2e-
- **직접 돌린 검산** benchmark/verify_observability.py 의 gramian() 을 그대로 재구성(ref=nr100_G3, K=16, t_obs=3 s)해 고윳값 재현: [-2.84e-10, 1.61e-10, 2.97e-04, 4.40, 9.88e+05, 1.94e+07] (원장과 일치). pinv rcond 를 훑으니 pos_rms = 57.75 m (rcond 1e-16…1e-11) → 0.04221 m (rcond 1e-10…1e-07) → 0.001006 m (rcond 1e-06). 원장이 쓴 1e-13 은 57.75 m 구간, 노트북 표의 랭크 열이 쓰는 1e-08 은 0.042 m 구간이다. 2RX 는 같은 스윕 전체에서 0.1896 m 로 불변.
- ⭐**고칠 문장** 셀 8 표의 1RX 행 «위치 RMS 오차» 는 57.75 m 가 아니라 **∞ (풀리지 않음)** 로 적어야 한다. 그램행렬의 정규화 고윳값이 [-1.5e-17, 8.3e-18, 1.5e-11, 2.3e-07, 0.051, 1.0] 로 두 방향이 배정밀도 영(longdouble 로 다시 계산하면 부호까지 뒤집힌다)이므로 위치 CRLB 는 그 두 방향에서 무한대다. 57.75 m 는 `verify_observability.py:615` 의 `np.linalg.pinv(G, rcond=1e-13)` 이 그 영공간을 버리고 남긴 부분공간의 값이고, 그 값의 100.0% (3335.34 m² 중 3335.34 m²) 가 λ_norm = 1.5e-11 인 단 하나의 준영(準零) 방향에서 나온다 — **같은 표의 랭크 열이(허용오차 1e-08) 이미 관측 불가로 세고 있는 바로 그 방향**이다. 나머지 방향을 다 합쳐도 0.042 m 다.  따라서 표는 두 열이 서로 다른 판 위에 서 있다: 랭크 열은 1e-08, RMS 열은 pinv rcond 1e-13. 두 열을 1e-08 로 맞추면 1RX 의 RMS 는 0.0422 m 가 되어 2RX 의 0.1896 m 보다 
- 확신도 high

#### 🟠 serious · 이미 사문화

- **자리** 셀 19 «앙각 클램프 — 이 창의 열린 끝» (ledger outputs/report13_freespace.json → solve.W1.snr_ceiling_db / snr_peak_d_m)
- **주장** 절 2: "그 천장 66.81 dB [^51] 은 `d` = 248 m [^52] 에서 서고, 그 자리는 위 표의 β = 45° 지점보다 안쪽이라 게이트 안 · 상반성 창 밖이다" — 근거리 SNR 천장을 값과 위치를 붙여 물리적 사실처럼 싣는다.
- **냄새** a value that is the edge of the analysis window (validity gate) reported as a ceiling / maximum — a trend that exists only because the sweep was cut there
- **왜 인공물인가** src/freespace_link.py:solve_range 의 snr_ceiling_db 는 «valid 게이트를 적용한 d 격자 위의 argmax» 다. 이 형상(L=500·alt=60·φ=90°)에서 SNR(d)는 게이트가 열린 뒤 단조 감소하므로, argmax 는 항상 **게이트가 열리는 첫 칸**이다. 실제로 β≤90° 가 처음 성립하는 칸은 240칸 중 41번(d=248.16 m)이고 그 칸의 SNR 이 정확히 66.81344621627343 dB — 원장의 천장 값과 마지막 자리까지 같다. 즉 66.81 dB 는 SNR 곡선의 봉우리가 아니라 β 게이트 상수 BETA_VALID_MAX_DEG=90° 가 서 있는 자리의 값이고, 그 상수를 85°/100° 로 옮기면 «천장» 은 63.15 dB(d=404 m)/68.18 dB(d=208 m)로 따라 움직인다. 안쪽으로는 SNR 이 계속 올라가 게이트 밖 69.64 dB(d=163 m)까지 간다 — 천장이 아니다. d=248 m 라는 위치도 geomspace(100,20000,240) 격자칸이라 이웃칸이 242.7 / 253.7 m 다(2.24% 눈금).
- **직접 돌린 검산** outputs/report13_freespace.json 의 solve.W1 배열로 직접: first index with beta<=90 → i=41, d=248.163 m, snr=66.81345 dB, beta=89.51°; 원장 snr_ceiling_db=66.81344621627343, snr_peak_d_m=248.16319008748 (동일). argmax(snr where valid)=41. 격자 전체 최대는 69.64 dB @ d=162.9 m (게이트 밖). 게이트 상수를 80/85/89/90/91/95/100/110° 로 바꿔 재계산: 63.15/63.15/66.62/66.81/67.00/67.53/68.18/69.41 dB.
- ⭐**고칠 문장** 절 2 의 마지막 문장을 «천장» 으로 쓰지 말고, 게이트 모서리 값이라고 그대로 밝혀 적는 것이 맞다. 예를 들어:  > `solve` 가 내는 `snr_ceiling_db` 는 **valid 게이트를 적용한 d 격자 위의 argmax** 다. 이 배치(L=500·alt=60·φ=90°)에서 그 argmax 는 **β 게이트가 열리는 첫 칸**이다 — 240칸 중 41번(d = 248.2 m, β = 89.51°)이고, 그 칸의 SNR 66.81 dB [^51] 가 곧 원장의 «천장» 값이다(마지막 자리까지 같다). 즉 이 값은 SNR(d) 의 봉우리가 아니라 `BETA_VALID_MAX_DEG` = 90° 가 서 있는 자리의 값이다. 안쪽으로는 SNR 이 계속 올라 게이트 밖 69.64 dB(d = 163 m)까지 가고, 게이트 상수를 88/90/95/100° 로 옮기면 이 값이 66.43/66.81/67.53/68.18 dB 로 따라 움직인다. 위치 248 m 도 geomspace(100, 20000, 240) 격자칸(눈금 2.24%, 이웃칸 242.7/253.7 m)이라 β=90° 실제 교차점 246.0 m 을 격자로 반올림한 값이다. 여기에 σ 조회
- 확신도 high

#### 🟠 serious · 이미 사문화

- **자리** 셀 14 결과 5 · 셀 18 표 «σ 격자 앙각» 행 · 셀 19 · 셀 20 «다음 단계» (ledger outputs/phi_sweep.json → geometry.rows[*].frac_el_outside_sigma_grid)
- **주장** 절 2 결과 5 및 셀 19: "조회의 4.6% [^49] (φ=90°) ~ 22.5% [^50] (φ=0°) 가 경계 행으로 클램프됐다" + "근거리 SNR 천장이 그 조회 위에 서므로, 확장된 앙각 격자 위에서 다시 푸는 일을 다음 단계에 건다" (다음 단계 표도 «클램프 조회가 격자 안으로 들어오고, 근거리 SNR 천장이 격자 위에 선다» 로 되풀이한다).
- **냄새** a fraction whose value is set by how wide the ungated d-window was, plus causal language linking it to a number it cannot touch
- **왜 인공물인가** frac_el_outside_sigma_grid 는 benchmark/phi_sweep.py:152 에서 np.mean(el < -20) — **게이트를 적용하지 않은** d 격자 240칸 전체에 대한 비율이다. 같은 스크립트가 다른 양들은 «게이트 뒤 값을 봐야 한다» 며 *_gated_* 키를 따로 내는데(phi_sweep.py:104-117 주석) 이 키만 그 규약 밖에 있다. 클램프되는 칸(el<-20 → d<126 m)은 β≤90°·원거리장 게이트(φ=90° 에서 d<248 m 컷)의 부분집합이라, 헤드라인 방위 φ=90° 에서 게이트를 통과하면서 동시에 클램프된 칸은 **0개(0.0%)** 다. φ 전 원주에서도 최악이 5.4%(φ=0/5°)로 22.5% 가 아니다. 그리고 천장이 서는 자리(d=248 m)의 앙각은 el=-10.49° 로 격자(0~-20°) 한복판이라 클램프와 무관하다 — 본문이 붙인 인과(«천장이 그 조회 위에 선다»)는 성립하지 않고, 앙각 격자를 넓혀도 φ=90° 의 R90·천장은 한 칸도 바뀌지 않는다.
- **직접 돌린 검산** freespace_scene 로 φ=0…355° (5° 간격 72방위), d=geomspace(100,20000,240), L=500·alt=60 에서 el 과 게이트(beta_gate & farfield_gate) 를 재계산: φ=90° → frac(el<-20)=0.0458(=원장 4.6%, 11칸) 이지만 frac(el<-20 AND valid)=0.0000 (0칸/199 유효칸). φ=0° → 0.2250(=원장 22.5%) 대 게이트 후 0.0542(13칸). 72방위 합계로 클램프 칸 2056개 중 게이트를 통과하는 것은 154개뿐. 천장 칸(index 41)의 el = -10.49° (격자 안).
- ⭐**고칠 문장** 절 2 결과 5 · 셀 19 · 셀 20 을 게이트 뒤 규약으로 다시 쓴다:  결과 5 (제안): "σ 격자의 앙각 행은 9 개이고 최솟값이 -20° 다 — 조회의 일부가 경계 행으로 클램프되지만, 클램프되는 칸(el < -20° ⇔ d < 126 m)은 β ≤ 90° 게이트가 이미 빼는 구간(φ=90° 에서 d ≤ 243 m)의 부분집합이라 **헤드라인 방위에서 R90 해에 들어오는 클램프 조회는 0 칸(0.0%)** 이다."  셀 19 (제안): "같은 스윕이 σ 조회의 앙각도 잰다. 게이트 이전 d 격자 240칸 기준으로는 4.6%(φ=90°) ~ 22.5%(φ=0°) 가 경계 행으로 클램프되지만, 이 키는 `phi_sweep.py:152` 에서 **게이트를 적용하지 않은** 비율이다(같은 스크립트의 다른 기하량은 `*_gated_*` 로 게이트 뒤 값을 따로 낸다). 게이트를 적용하면 φ=90° 0.0%(0/199칸), 전 원주 최악이 φ=0/5/355° 의 5.4%(13/199칸)다 — 72방위 합계로 클램프 칸 2056개 중 게이트를 통과하는 것은 154개다.  천장 66.81 dB 는 d = 248.2 m 에서 서고 그 자리의 앙각은 el = -
- 확신도 high

#### 🟡 minor · 이미 사문화

- **자리** 셀 34 결과 4 / 셀 38 «세 밴드가 문턱 하나를 공유한다» 표 (ledger outputs/report05_derived.json → threshold.l1_delta_db / l1_range_shift_pct; 원천 outputs/report13_freespace.json → threshold.S_G)
- **주장** 절 4 결과 4 및 셀 38 표: "LTE 자기 문턱은 11.91 dB [^106] 로 공유 문턱과 +0.047 dB [^107] 차이이고, R90 에 주는 차는 -0.27% [^108] 다"
- **냄새** a difference smaller than the estimator's own Monte-Carlo spread, reported as a difference (and its sign flips with an arbitrary grid choice)
- **왜 인공물인가** 두 문턱은 K=4000 시행의 Pd 곡선에서 뽑은 SNR90 이고 원장이 Wilson 신뢰구간을 함께 싣는다: W1 11.861 dB [11.804, 11.922], L1 11.908 dB [11.855, 11.964]. 두 구간이 거의 완전히 겹치고, 차 +0.047 dB 는 각 추정치의 반폭(≈0.06 dB)보다 작다. 게다가 «자기 문턱» 을 어느 dopoff 칸에서 읽느냐가 자유변수인데, 같은 모드 안에서 dopoff 격자(3/5/8/15/30빈)를 옮기면 W1 은 11.858~11.901(폭 0.043 dB), L1 은 11.843~11.985(폭 0.142 dB)로 흔들린다 — dopoff=8 을 골랐다면 L1(11.843) 이 W1(11.861) **아래**여서 부호가 뒤집힌다. 즉 +0.047 dB 와 -0.27% 는 측정된 밴드 차가 아니라 몬테카를로 잡음 + 격자칸 선택의 산물이다. 다만 본문이 이 수로 주장하는 결론(«그 선택의 크기는 작다»)은 그대로 성립한다 — 숫자가 과대정밀할 뿐 방향이 틀리지 않는다.
- **직접 돌린 검산** outputs/report13_freespace.json threshold.S_G 를 전수 출력: W1 N=1 dopoff 3/5/8/15/30 → snr90 = 11.8614 / 11.8577 / 11.9007 / 11.8895 / 11.8673, Wilson [lo,hi] 예: [11.8036, 11.9217]. L1 → 11.9083 / 11.9348 / 11.8430 / 11.9846 / 11.9245, [11.8548, 11.9643]. 인용된 11.86/11.91 은 둘 다 dopoff=3 칸. 차 = 0.0469 dB (= 원장 threshold.l1_delta_db 0.04689), 이는 W1 CI 반폭 0.059 dB 와 L1 dopoff 스프레드 0.142 dB 보다 작다. n≈4 로 환산한 -0.27% 도 같은 잡음 크기.
- ⭐**고칠 문장** 셀 34 결과 4 및 셀 38 표는 차를 상한으로 적어야 한다. 예: 「그 선택의 크기는 작다 — LTE 자기 문턱(같은 dopoff=3 칸)은 11.91 dB 로 공유 문턱 11.86 dB 와 +0.05 dB 차이지만, 이 차는 K=4000 시행의 몬테카를로 오차(95% CI [-0.03, +0.12] dB, 0 을 포함)보다 작고 dopoff 칸을 옮기면 부호가 뒤집힌다(dopoff=8 에서 L1 11.84 < W1 11.86). 따라서 이것은 측정된 밴드 차가 아니라 상한이다 — 문턱을 공유한 선택이 R90 에 주는 영향은 |0.7%| 이하다(95% CI [-0.69, +0.15]%, 최악 dopoff 칸 -0.71%).」 표의 「공유 문턱과의 차」·「R90 에 주는 차」 열은 +0.047 dB / -0.27% 대신 ≲0.12 dB / ≲0.7% 로 적고, 원장이 이미 싣고 있는 threshold.S_G.*.1.dopoff.3.snr90_lo_db/hi_db 를 같은 표에 나란히 실어 K=4000·2 dB 격자·dopoff 칸 선택이라는 측정 설정을 드러내는 것이 좋다. 절의 결론(「세 밴드가 문턱 하나를 공유한다」·「그 선택의 크기는 작다」)은 그대로
- 확신도 high

### `10_results.ipynb` — 4 건 (살아 있음 4)

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 4 «CPI 를 늘리면 세 파형 모두 블라인드율이 내려간다» — 셀 37(결과 3) · 셀 41(«CPI 를 늘리면 — 촘촘한 격자» 표) · 출처 [^89][^90][^118][^123][^129][^135][^141]
- **주장** "WiFi 대비 배수는 CPI 0.1 ~ 2.0 s 5칸에서 11.0 ~ 19.0배 로 남는다 — 이것이 이 대가를 구조로 만드는 첫 번째 사실이다." (표의 5G/WiFi 열: 12.1 / 12.1 / 14.3 / 19.0 / 11.0배, 그리고 WiFi 블라인드 열 0.053/0.025/0.008/0.003/0.003)
- **냄새** a quantity pinned at a GRID RESOLUTION (분모가 격자 2칸) + a ratio that is large because the DENOMINATOR is tiny/degenerate
- **왜 인공물인가** 분모 blind_hard_W1 은 720점 헤딩 격자 위의 칸수 38/18/6/2/2 다 — CPI 1.0 s 와 2.0 s 에서는 720칸 중 2칸, 즉 격자 분해능 그 자체다. 격자를 72,000점(및 720,000점)으로 올리면 W1 은 0.05508/0.02753/0.01097/0.00547/0.00275 로 매끄럽게 절반씩 줄고, 5G/WiFi 배수는 11.58/10.72/10.59/10.58/10.58 — 5칸 전부 사실상 상수(10.6~11.6)가 된다. 즉 본문이 인용한 14.3·19.0·11.0 과 그 '11.0~19.0' 폭은 전부 격자 양자화이지 물리가 아니다(19.0 = 38/2, 11.0 = 22/2). 같은 표의 5G/LTE 열(4.0→3.7)은 분모가 커서 이미 수렴해 있다 — 오염된 것은 WiFi 열뿐이다. 결론의 방향(배수가 CPI 로 안 없어진다)은 오히려 수렴 격자에서 더 깨끗해지지만, 인용된 수와 폭은 못 쓴다. 부수적으로 절 제목 '세 파형 모두 블라인드율이 내려간다'인데 표의 WiFi 는 1.0→2.0 s 에서 0.003→0.003 으로 안 내려간다; 수렴 격자에서는 0.00547→0.00275 로 정확히 절반이 된다.
- **직접 돌린 검산** CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark python -c 'cpi_guard_sweep.cell(m,facts,T,R90[m],5.0,psi_n)' 를 psi_n = 720/7200/72000/720000 로 재실행. G1/W1 배수 — 720: 12.05, 12.11, 14.33, 19.00, 11.00 (원장과 비트단위 일치) / 72000: 11.57, 10.71, 10.61, 10.62, 10.56 / 720000: 11.58, 10.72, 10.59, 10.58, 10.58. blind_hard_W1 × 720 = 38, 18, 6, 2, 2 칸.
- ⭐**고칠 문장** 두 곳(셀 37 결과 3, 셀 41)의 "11.0 ~ 19.0배" 와 표의 5G/WiFi 열 12.1/12.1/14.3/19.0/11.0, WiFi 열 0.053/0.025/0.008/0.003/0.003 은 헤딩 격자 720점을 수렴 격자로 오인한 결과다. 격자를 72,000 · 720,000 점으로 올려 수렴시키면:  | CPI | WiFi | LTE | 5G | 5G/WiFi | 5G/LTE | |---|---|---|---|---|---| | 0.1 s | 0.0551 | 0.1572 | 0.6374 | 11.6배 | 4.05배 | | 0.2 s | 0.0275 | 0.0780 | 0.2949 | 10.7배 | 3.78배 | | 0.5 s | 0.0110 | 0.0311 | 0.1165 | 10.6배 | 3.74배 | | 1.0 s | 0.0055 | 0.0156 | 0.0581 | 10.6배 | 3.74배 | | 2.0 s | 0.0027 | 0.0078 | 0.0291 | 10.6배 | 3.73배 |  따라서 본문은 이렇게 고쳐 써야 한다: "WiFi 대비 배수는 CPI 0.1 ~ 2.0 s 5칸에서 10.6 ~ 11.6배로 **사실상 상수**다 
- 확신도 high

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 5 «모호속도는 표본화율의 성질이라…» — 셀 46(결과 2·3·4) · 셀 48 · 셀 49(패리티의 대가 표) · 셀 50 · 출처 [^148][^150][^151][^152][^153][^154][^162][^163][^164][^166]
- **주장** "커버리지를 WiFi 수준으로 올리는 CPI 는 1.00 s" / 패리티의 대가 표 «WiFi 수준 | 1.00 s | 50 버스트 | 10.00배 | 10.00 dB» / "패리티 CPI 가 코히어런스 한계 안에 머무는 구간은 20 m/s 까지다 — 25 m/s 에서 한계(0.84 s)를 넘어선다" / "거리·속도 격자 16칸 중 8칸이 WiFi 패리티를 허용한다"
- **냄새** a quantity pinned at a GRID RESOLUTION — 판정이 격자 양자화의 정확한 동수 위에 서 있고, 자유 파라미터(헤딩 격자 점수)를 조금만 나누면 결론이 뒤집힌다
- **왜 인공물인가** benchmark/cpi_guard_sweep.py:321 parity_cpi 는 blind_G1(T) <= blind_W1(0.1 s) + 1e-12 의 첫 지점을 T 격자에서 그냥 읽는다. 720점 격자에서 G1@M=50(T=1.00 s) = 38/720 = 0.0527778 이고 목표 W1@0.1 s 도 38/720 = 0.0527778 — 두 독립 계수가 정확히 같은 정수라 등호로 통과한다. 게다가 720점에서 G1 blind 는 M=50~59 내내 0.0527778 로 얼어붙어(38칸 고정) 이 축에 분해능이 아예 없다. 72,000점에서는 목표가 0.055083 이고 G1 은 M=50 에서 0.058139 로 아직 위, M=53 (T=1.06 s, blind 0.054917) 에서 처음 내려간다. ⇒ 필요 CPI 1.00 → 1.06 s, SSB 버스트 50 → 53, 헤드라인 대비 10.00 → 10.6배, 코히어런트 이득 10.00 → 10.25 dB (표의 반올림된 '10.00'들은 1.00 s 라는 우연한 동수의 산물이다). 그리고 20 m/s 칸의 T_coh 는 1.0517 s 라 1.06 s 를 못 받는다 → 결과 3 의 '20 m/s 
- **직접 돌린 검산** psi_n=720 vs 72000 으로 G1 blind_hard 를 M=48..59 에서 재계산: 720 → M=48,49 에서 0.058333, M=50~59 전부 0.052778(=38/720, 완전히 평평); 72000 → 0.060583, 0.059361, 0.058139, 0.057028, 0.055917, 0.054917(M=53 최초로 목표 0.055083 이하), 0.053861, … . parity_cpi 를 그대로 재실행: psi_n=720 → req_WiFi = 1.0 s, psi_n=72000 → req_WiFi = 1.0724 s(T격자 상), 연속 M 축에서는 M=53 → 1.06 s. 원장 cost_of_long_cpi.by_speed[6].T_coh_s = 1.0517 < 1.06 → 20 m/s 칸 infeasi
- ⭐**고칠 문장** 절 5 결과 2·3·4 와 «패리티의 대가» 표의 WiFi 행은 수렴된 헤딩 격자 위의 값으로 바꾸고, 격자 caveat 을 달아야 한다.  결과 2: "커버리지를 WiFi 수준으로 올리는 CPI 는 1.06 s (스크립트 T 격자 위에서는 1.07 s), LTE 수준은 0.38 s 이고 그 대가는 재방문 시간이다." (LTE 값은 그대로다.)  패리티의 대가 표 WiFi 행: 필요 CPI 1.06 s · SSB 버스트 53 · 헤드라인 대비 10.6배 · 코히어런트 이득 10.25 dB. (T 격자 정본을 쓰면 1.07 s / 54 / 10.7배 / 10.30 dB.) LTE 행(0.38 s · 19 · 3.75배 · 5.75 dB)은 변하지 않는다.  결과 3: "패리티 CPI 가 코히어런스 한계 안에 머무는 구간은 15 m/s (T_coh 1.40 s) 까지다 — 20 m/s 에서 한계(1.05 s)가 필요 CPI 1.06 s 를 이미 밑돈다." 다만 20 m/s 칸은 여유가 1 % 뿐이므로 '아슬아슬하게 못 받는다' 로 읽어야 한다.  결과 4: "거리·속도 격자 16칸 중 7칸이 WiFi 패리티를 허용한다."  그리고 절 5 방법 표(또는 절 4 «
- 확신도 high

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 3 «그 순위는 자세평균이면 하나로 모이고…» — 셀 27(결과 4) · 셀 31 · 셀 34(다음 단계) · 출처 [^61]
- **주장** "크기와 뒤집힘 문턱의 상관은 -0.62 [^61] 다 — 취약성을 정하는 것은 **밴드 간 σ 로브 산포**다." (절 제목: «취약성을 정하는 것은 크기가 아니다», 결과 4: "취약성을 정하는 것은 기체 크기가 아니라 밴드 간 σ 로브 산포다")
- **냄새** causal language ("X 가 정한다") where only a CORRELATION was observed — 게다가 n=5 에서 유의하지 않고, 기각하는 쪽 상관이 채택하는 쪽보다 강하다
- **왜 인공물인가** 표본은 기체 5대다. 본문이 인용한 -0.618(extent vs flip_span_single_aspect)은 p=0.27(Spearman rho=-0.90, p=0.037)로 이 표에서 가장 강한 — 그리고 유일하게 명목상 유의한 — 관계다. 반면 본문이 원인으로 지목하는 '밴드 간 σ 로브 산포'와 뒤집힘 문턱의 상관은 같은 원장에 corr_sigma_spread_vs_flip_single = -0.3150 으로 이미 적혀 있는데(p=0.61, Spearman -0.10, p=0.87) 본문은 그 수를 싣지 않는다. 즉 '크기가 아니라 산포가 정한다'는 문장은, 기각하는 가설의 상관이 채택하는 가설의 상관보다 두 배 강한 상태에서 5점으로 내려진 인과 선언이다. 원장 finding 이 덧붙인 근거 '(σ 로브 산포는) 전기적 크기가 클수록 커진다' 도 같은 원장의 corr_extent_vs_sigma_spread = +0.0913 (p=0.88) 이 부정한다. 본문은 이 셋 중 -0.62 하나만 인용한다.
- **직접 돌린 검산** outputs/sigma_sensitivity.json:size_vs_fragility.by_drone 5행에서 scipy.stats 로 재계산 — extent vs flip_single: pearson -0.618 (p=0.266), spearman -0.900 (p=0.037) / spread vs flip_single: pearson -0.315 (p=0.606), spearman -0.100 (p=0.873) / extent vs spread: pearson +0.091 (p=0.884) / spread vs flip_avg: pearson -0.646 (p=0.239). 본문 인용값 -0.62 는 원장 corr_extent_vs_flip_single = -0.6182 와 일치 확인.
- ⭐**고칠 문장** 셀 27 결과 4 · 셀 31 절 제목·본문을, 리포트 3 절(03_anchor 「뒤집힘 문턱은 어느 열을 따라가나」)이 이미 쓰고 있는 형태로 맞춘다:  제목: «작은 기체가 더 취약하다는 예상은 뒤집힌다» («취약성을 정하는 것은 크기가 아니다» 는 인용한 -0.62 자신이 부정한다)  본문: "가장 작은 mini5pro(전장 0.378 m, LTE 에서 D/λ = 2.32)가 단일자세·자세평균 양쪽에서 가장 견고하다 — 작은 기체가 더 취약하다는 예상은 뒤집혔다. 뒤집힘 문턱은 최대 치수 열과 밴드 간 σ 로브 산포 열 둘 다에 약하게 걸리고, 단일자세 문턱과의 상관은 크기 쪽 -0.62, 산포 쪽 -0.31 로 오히려 크기 쪽이 더 강하다. 두 열 사이 상관은 +0.09 라 서로 다른 축이다. ⚠ 기체가 5 대뿐이라 이 세 수는 유의수준이 아니라 서술용이다(크기-문턱 p=0.27, 산포-문턱 p=0.61). 원장 `size_vs_fragility.finding` 은 산포를 단독 원인으로 들지만, 본문은 세 상관계수를 그대로 읽고 인과를 주장하지 않는다."  선택적으로(더 강한 대체): 뒤집힘 문턱을 실제로 정하는 것은 σ 산포가 아니라 **밴드쌍 총격
- 확신도 high

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 2 ⭐ «앵커 σ 위의 R90 은 비교가능 12칸에서…» — 셀 12(절 제목) · 셀 13(결과 2) · 셀 14(R90 정의) · 셀 15 · 셀 17(표) · 출처 [^23][^24][^25]
- **주장** "R90 = 검출확률 P_d 가 0.9 로 떨어지는 거리다" · "앵커 비교가능 기체 12칸의 R90 은 3.69 ~ 7.44 km 다" · R90 표의 5G 열 5.10 / 6.61 / 5.93 / 5.65 / 10.11 km (권 제목: «결과 — 얼마나 멀리서 보이나»)
- **냄새** a number whose value is set by the EVALUATION CONVENTION (단일 공칭 헤딩 + 도플러 게이트 미적용) rather than by achievable detection; 같은 원장 리프의 형제 키가 그 수를 부정한다
- **왜 인공물인가** R90 은 공칭 헤딩 ψ=0 한 점의 σ 로 만든 SNR(d) 에서 읽는다(셀 14). 그런데 이 권이 쓰는 φ=90° 기하에서 ψ=0 은 **정확히 0-도플러 헤딩**이다 — f_d(ψ=0) = -5.9e-5 Hz (d=6301 m), -1.9e-4 Hz (d=4282 m). 검출기 가드 반폭은 1.5빈 15 Hz · 2.5빈 25 Hz 이므로 세 파형 모두 그 헤딩에서 blind 다. 즉 표의 15칸 전부가 '검출기가 지우는 헤딩'에서 읽은 거리다. 같은 원장 리프(ranges.*.*.equal_psd.full_waveform_capture.by_N.1)의 형제 키가 이를 그대로 적어 둔다 — 5기체 5G 전부 blind_heading_frac = 1.0 · coverage_ceiling = 0.0 · E_psi_Pd_at_R90 = 0.0 이고, WiFi 는 E_psi_Pd_at_R90 = 0.100~0.151, LTE 는 0.004~0.653 이다. 절 2 는 R90_C50_m 만 인용하고 이 형제 키를 한 번도 들지 않는다. 결과적으로 '5G 는 5.10 km 에서 P_d=0.9' 로 읽히는 칸의 헤딩평균 P_d 는 같은 행에서 정확히 0 이다. (
- **직접 돌린 검산** freespace_scene._fd_of_heading(psi=[0,45,90], phi=90, d=R90, L=500, alt=60, v=5) → f_d = [-5.9e-5, -82.5, -116.7] Hz (d=6301 m); blind_fractions(psi=[0], T=0.1) → guard_hard = 15.0 Hz, guard_declared = 25.0 Hz, blind_hard = blind_declared = 1.0 (세 모드 전부). report13_freespace.json 리프 재확인 — 5기체 G1: coverage_ceiling 0.0 / blind_heading_frac 1.0 / E_psi_Pd_at_R90 0.0; mavic4pro W1 0.9167 / 0.0833 / 0.1003, L1 0.75 / 0.25 
- ⭐**고칠 문장** 절 2 는 R90 을 "검출확률 P_d 가 0.9 로 떨어지는 거리" 로 정의하지만, 표의 15칸 전부가 **검출기가 지우는 헤딩에서 읽은 거리**다. 본문에 다음을 넣어야 한다.  1) 셀 14·15·16 의 R90 정의에 규약을 명시한다: "이 R90 은 헤드라인 방위 φ=90° · 공칭 헤딩 ψ=0 에서 SNR(d) 가 문턱을 하강교차하는 거리이고, **적용된 유효 게이트는 β≤90°·원거리장 둘뿐이다 — 0-도플러 가드는 이 해에 들어가지 않는다**."  2) 그 규약이 왜 문제인지 수로 적는다: φ=90° 에서 ψ=0 은 **정확히 0-도플러 헤딩**이다 — f_d(ψ=0) = -1e-4 ~ -3e-4 Hz (표의 모든 거리, 세 밴드 공통). CPI 0.1 s 의 가드 반폭은 하드 1.5빈 15 Hz · 선언 2.5빈 25 Hz 이므로 **WiFi·LTE·5G 전부** 그 헤딩에서 blind 다(72점 격자에서 ψ=0 은 블라인드 섹터의 한가운데 — W1 blind = {0,5,175,180,185,355}°). 스펙 §7.2 는 "블라인드 헤딩은 SNR 이 아무리 높아도 미검출로 센다" 이므로, 이 규약에서 Pd(ψ=0)=0 이다. 즉 셀 15 
- 확신도 high

### `03_2_size-law.ipynb` — 3 건 (살아 있음 3)

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 3 «모양의 유무는…» — 결과 4 (cell 22), 축 ③ 표 (cell 30), 절 4 P1 표 (cell 38)
- **주장** 메쉬와 구의 시간 변조 간격 62.0 [^50]~100.8 dB [^51] 중 94% [^52]~99% [^53] 를 «디테일 0 인 평판» 이 이미 산다. (같은 숫자가 절 3 «지도교수 지적에 답한다» 축 ③ 행 «메쉬 − 구 간격 62.0~100.8 dB», 절 4 P1 «메쉬 − 구 = 62~77 dB» 로 세 번 인용된다)
- **냄새** a ratio/difference that is large because the DENOMINATOR (reference arm) is degenerate — the value equals a numerical NULL FLOOR, not a physical quantity; and the quoted range is set by where that flo
- **왜 인공물인가** 간격 = mesh 의 in_band_ac_over_dc_db − 등가부피 구의 같은 값. 구는 회전대칭이라 변조가 정확히 0 이고(본문도 «계산이 아니라 기하학» 이라고 적는다), 구 팔이 내는 -84.96 / -97.40 dB 는 전부 격자 잔재다. 프로젝트 원장이 이미 이것을 증명해 뒀다 — outputs/report16_rung_sphere_eqvol.json 의 null_is_numerical 절: 구 잔차의 지배 차수가 경도 분할 수 seg 의 별칭이고(alias_of_seg=true, mini2 seg 39 → 지배 차수 50, matrice4e seg 71 → 43; 메쉬는 2 와 14), sphere_metrics_interpretable_frac = 0.0 (구 AC 전력의 86.5% / 96.4% 가 운동학이 허용하는 대역 **밖**에 있다), 분할을 촘촘히 하면 잔차가 옥타브당 -12.8 / -6.9 dB 로 내려간다. 즉 인용된 62.0 dB 는 «메쉬가 구보다 62 dB 세다» 가 아니라 «메쉬가 그날의 구 테셀레이션 바닥보다 62 dB 위였다» 이고, 바닥은 −∞ 로 간다. 게다가 인용된 62.0~100.8 dB 라는 **폭 38.8
- **직접 돌린 검산** ① outputs/report16_metric_sphere_eqvol.json level_vs_modulation 12행: mesh 값 폭 10.50 dB(-29.82..-19.32), sphere 값 폭 38.82 dB(-123.78..-84.96), gap 폭 38.76 dB(62.04..100.80) — 폭 전부가 널 바닥. ② 같은 원장이 이미 계산해 둔 가장 촘촘한 구로 바꿔 재계산: mini2 구 seg 39→157 이면 바닥 -84.96→-125.75, 인용된 간격 62.04 dB → 102.83 dB (+40.8 dB); matrice4e seg 71→277 이면 -97.40→-113.12, 76.83 dB → 92.56 dB (+15.7 dB). 생산 테셀레이션(seg 39)은 4점 수렴열에서 **가장 나쁜(가장 높은) 바닥*
- ⭐**고칠 문장** 절 3 결과 4 · 절 3 축 ③ 표 · 절 4 P1 의 「메쉬 − 구 간격 62.0~100.8 dB」(및 「62~77 dB」) 는 측정된 크기가 아니라 **구 테셀레이션이 정한 하한**이다. 다음처럼 고쳐 적어야 한다.  1. 크기를 인용하지 말고 하한으로 적는다. 구는 회전대칭이라 변조가 정확히 0 이고(본문도 그렇게 적는다), 구 팔이 내는 -84.96 / -97.40 dB 는 전부 격자 잔재다 — 지배 차수가 경도 분할 수 seg 의 별칭이고(내가 직접 돌린 seg 21/39/79/155 네 판 전부), 대역 안 AC 몫이 0.135 / 0.036 (메쉬 1.000) 이며, report16_base 자신이 «sphere = 계산기 자체의 수치 바닥» 이라고 적어 뒀다. 따라서 62.0 dB 는 「메쉬가 구보다 62 dB 세다」가 아니라 「메쉬가 그날의 구 격자 바닥보다 62 dB 위였다」이고, 참값은 −∞ 로 간다.  2. 그 값이 얼마나 흔들리는지 함께 적는다. 구만 4배 촘촘히 쪼개면 같은 숫자가 mini2 62.04 → 102.83 dB (+40.8), matrice4e 76.83 → 92.56 dB (+15.7) 로 움직인다(내 재계산: seg
- 확신도 high

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 4 «일곱 가지» 아래 본문 (cell 38 마지막 문단)
- **주장** P1 이 드는 «메쉬 − 구» 간격은 기체별 집계이고, **방위 극값까지 펴면** 62.0 [^115]~100.8 dB [^116] 다 — 같은 대조를 두 규약으로 읽은 것이다.
- **냄새** a range attributed to one axis (azimuth) that is actually produced by a sweep over CONVENTIONS — band and wavefront — i.e. the spread is a property of which settings were pooled, not of the physics na
- **왜 인공물인가** 62.0~100.8 dB 를 만드는 12개 행은 하나하나가 이미 **방위 24점 평균**이다 — benchmark/report16_metric_sphere_eqvol.py:836-837 이 per_az[...]['mean'] 끼리 뺀다. 방위는 이미 평균으로 지워졌으므로 «방위 극값까지 편» 범위일 수가 없다. 실제로 넓어진 이유는 두 가지 규약을 풀에 넣었기 때문이다: 밴드(3.5 GHz → 15.86 GHz)와 파면(구면 → 평면). 최소 62.04 는 main|mini2|spherical, 최대 100.80 은 hi|matrice4e|plane 이다. 하필 그 두 규약이 이 편이 다른 데서 «다른 체제» 라고 못 박은 것들이다 — 15.86 GHz 는 P6 가 «같은 문턱으로 FAIL» 이라고 적은 밴드이고, 평면파는 널 바닥을 가장 크게 흔드는 손잡이다(최대 13.9 dB). 즉 «두 규약으로 읽었다» 는 말은 맞지만, 그 규약이 방위가 아니라 밴드·파면이다.
- **직접 돌린 검산** ① 코드 확인: report16_metric_sphere_eqvol.py:836-837 modulation_gap_db = m['per_az']['in_band_ac_over_dc_db']['mean'] − s[...]['mean'] (방위 평균끼리의 차). ② 풀을 이 편의 규약(main 밴드 · 구면파)으로 제한하면 mini2 62.04 / matrice4e 76.83 → 정확히 P1 의 «62~77». 전체 풀의 argmin/argmax = main|mini2|spherical / hi|matrice4e|plane. ③ 진짜로 «방위 극값까지 펴면» 얼마인지 npz 원표에서 방위 24점을 하나씩 재계산했다(report16_base_tables.npz, B.md_metrics16): mini2 51.7~74.7 dB, matrice4e 6
- ⭐**고칠 문장** Replace the last paragraph of cell 38 with something like: "P1 이 드는 «메쉬 − 구» 간격 62~77 dB 는 이 편의 규약(3.5 GHz · 구면파 · 방위 24점 평균)에서 두 기체를 모은 값이다. 62.0 [^115]~100.8 dB [^116] 는 방위를 편 값이 아니라 — 두 값 모두 이미 방위 24점 평균이다(report16_metric_sphere_eqvol.py:836-837 이 per_az 평균끼리 뺀다) — 같은 방위평균 대조를 두 대역(3.5 / 15.86 GHz) × 두 파면(구면 / 평면) × 세 기체, 12 칸으로 넓힌 풀의 최소·최대다. 최소 62.04 는 main|mini2|구면파(=이 편의 규약)이고 최대 100.80 은 hi|matrice4e|평면파다. ⚠ 넓어진 몫의 대부분은 신호가 아니라 널의 수치 바닥이 규약을 따라 움직인 것이다 — 12 칸에서 메쉬 변조는 −19.3~−29.8 dB 안에서만 움직이는데 구의 바닥은 −85.0~−123.8 dB 움직인다(파면 선택만으로 최대 13.9 dB, 메쉬는 0.8 dB). 게다가 최대값이 나온 15.86 GHz 는 바로 위 P6 
- 확신도 high

#### 🟡 minor · **지금도 인용됨**

- **자리** 절 3 «읽는 법 — 네 구간» 첫 항목 (cell 28)
- **주장** 도는 부품의 삼각형을 절반으로 줄이면 검출 단면적이 -0.01 dB, 템플릿 손실이 0.00 dB 움직인다. **방위에 따른 흔들림 7.99 dB [^82] 에 묻히는 크기라 실측이 가르는 범위 밖이다.**
- **냄새** the yardstick is a number from a different quantity / different ledger / max-over-configurations than the text implies — 잣대가 재는 양과 다르다
- **왜 인공물인가** 7.99 dB 는 professor_answer.axis3.azimuth_sd_db.mesh_max = **sigma_eq_mean_dbsm(총 평균 RCS)** 의 방위 표준편차를, 그것도 3기체 × 2밴드 × 2파면 12배열의 **최대값**으로 잡은 것이다(다른 원장 report16_metric_sphere_eqvol.json). 그런데 ±0.01 dB 는 σ_ac_peak(검출 단면적)의 **짝지어 뺀** 차이다 — 애초에 방위를 짝으로 지워서 만든 양이라 방위 산포와 같은 자에 놓을 수 없고, 같은 양의 방위 산포는 7.99 가 아니라 mini2 4.05 dB · matrice4e 2.91 dB 다. 결론(«공짜») 자체는 무너지지 않는다 — 짝지은 차이의 방위 표준편차가 0.012 / 0.069 dB 로 평균값과 같은 자릿수여서 훨씬 강한 근거가 이미 원장에 있다. 문제는 인용된 잣대가 2~2.7배 부풀려져 있고 다른 양·다른 원장에서 왔다는 점이다.
- **직접 돌린 검산** report16_synthesis.json: ladder_C_matched_flight.{mini2,matrice4e}.mesh_full.sigma_ac_peak_dbsm.sd = 4.05 / 2.91 dB (n=24). 같은 파일 professor_answer.axis3_time_modulation.azimuth_sd_db.mesh_max = 7.9885 (sigma_eq_mean_dbsm 의 방위 sd, 12배열 최대). 짝지은 차이: ladder_C...mesh_half_tri.paired_vs_mesh.d_sigma_ac_peak_db = mini2 mean +0.0131 sd 0.0120, matrice4e mean -0.0081 sd 0.0691.
- ⭐**고칠 문장** Replace the yardstick with the same quantity, same airframes, from the same ledger block — the ladder_C paired statistics already contain a much stronger version of the argument:  "**공짜 — 해상도.** 도는 부품의 삼각형을 절반으로 줄이면 검출 단면적이 -0.01 dB [^45], 템플릿 손실이 0.00 dB [^46] 움직인다. 같은 양(검출 단면적)이 방위에 따라 Mini 2 4.05 dB · Matrice 4E 2.91 dB (n=24) 흔들리는 데 비해, 방위를 짝지어 뺀 이 차이는 24 방위 전부에서 표준편차 0.012 / 0.069 dB · 최대 |Δ| 0.045 / 0.123 dB 안에 머문다 — 실측이 가르는 범위 밖이다."  Keys: ladder_C_matched_flight.{mini2,matrice4e}.mesh_full.sigma_ac_peak_dbsm.sd (4.047 / 2.912) and ladder_C_matched_flight.{mini2,matrice4e}.mesh_half_tri
- 확신도 high

### `06_1_scene.ipynb` — 3 건 (살아 있음 3)

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 3 «모양의 유무는 수십 dB…» — 결과 1, cell 22; «읽는 법 — 네 구간» cell 28; 한 줄 요약 cell 29; 절 4 «어디까지 인용해도 되나» 표 cell 41. 원장 키 professor_answer.axis4….rows.{mini2,matrice4e}.disc.sigma_ac_peak_err_db [^42][^43]
- **주장** «낭떠러지» — 날개를 회전대칭 원판으로 바꾸면 검출 단면적이 -56.48 dB · -54.44 dB 무너진다 … 원판으로 바꾸면 검출 단면적이 -54.44 dB 무너진다. 이것만은 어떤 커널 결함에도 안 흔들리는 기하학이다 / ⭐ «모양이 있느냐 없느냐» 는 50 dB 대를 가른다 (절 4 인용범위 표: «부호와 자릿수까지»)
- **냄새** a ratio that is large because the DENOMINATOR is tiny/degenerate (여기서는 분모가 점구름 이산화 잔차 바닥) — 값이 SATURATION/FLOOR 값인데 물리 효과로 보고됨
- **왜 인공물인가** 회전대칭 원판의 참 변조는 0(보고서 자신도 «남는 것은 격자 잔재다», quotable_frac=0, in_band_ac_frac=0.0007/0.009 이라 적음)이다. 따라서 «낭떠러지 깊이» 는 물리량이 아니라 원판 점구름의 이산화 잔차 바닥까지의 거리이고, 점밀도라는 자유 모수 하나로 값이 정해진다. 실제로 disc 팔의 AC 첨두는 차수 111(matrice4e, 운동학 한계 band=30) · 49(mini2, band=13) 에 앉아 있다 — 운동학적으로 불가능한 자리다. 그러므로 «어떤 커널 결함에도 안 흔들리는 기하학» 은 부호에만 참이고 크기에는 거짓이며, «50 dB 대» 를 자릿수까지 인용하라는 지시는 근거가 없다(4배 촘촘히 깔면 73~90 dB 대가 된다). 이 라운드가 바로 그 반론을 막으려고 돌려 둔 `_fine` 대조군이 report16_base.json 에 이미 들어 있는데(disc 의 dc_ac_db 가 +17.74/+35.30 dB 이동, mesh 는 +0.52/+0.39 dB) 노트북은 이 대조군을 한 번도 언급하지 않는다. 같은 잔차가 절 1·2 표의 원판·구 행(검출 단면적 -102.59/-110.31/-110.83
- **직접 돌린 검산** outputs/report16_base_tables.npz 에서 24 방위 전력평균 sigma_ac_peak(=원장과 같은 정의)을 다시 계산: matrice4e disc -101.62 dBsm vs disc_fine(4배 점밀도) -137.27 dBsm (Δ -35.65 dB), mesh -47.30 vs mesh_fine -47.33 (Δ -0.03 dB) → 낭떠러지가 -54.32 dB 에서 -89.94 dB 로 이동. mini2 disc -109.25 vs disc_fine -125.70 (Δ -16.45 dB), mesh -52.49 vs -52.49 (Δ -0.00 dB) → -56.75 dB 에서 -73.21 dB 로 이동. 독립 확인: outputs/report16_base.json.point_density_control.del
- ⭐**고칠 문장** Keep the sign and the mechanism; drop the magnitude and the decade.  절 3 결과 1 (cell 22) — replace with roughly: "1. 낭떠러지 — 날개를 회전대칭 원판으로 바꾸면 검출 단면적이 **최소 54 dB 이상** 무너진다. 회전대칭체의 참 변조는 정확히 0 이므로 이 값은 «깊이» 가 아니라 **우리 점구름의 이산화 바닥까지의 거리**다 — 점을 4배 촘촘히 깔면 같은 값이 mini2 -72.9 dB · Matrice 4E -89.9 dB 로 더 내려간다(같은 조건에서 CAD 메쉬는 0.03 dB 만 움직인다). 원판 팔의 AC 첨두는 차수 49 · 111 로 운동학 한계(band 13 · 30)의 3.7~3.8배 위에 앉아 있고 in_band_ac_frac = 0.009 · 0.0007 이다."  절 3 «읽는 법» (cell 28) 낭떠러지 항 — replace "이것만은 어떤 커널 결함에도 안 흔들리는 기하학이다" with: "안 흔들리는 것은 **부호**뿐이다 — 회전대칭이면 변조가 원리적으로 0 이므로 오차는 언제나 크게 음수다. **크기는 안 흔들리지 않는다**: 점
- 확신도 high

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 3 결과 4 · 네 축 표 ③ (cells 22, 30), 절 4 P1 아래 주석 «P1 이 드는 «메쉬 − 구» 간격은 기체별 집계이고, 방위 극값까지 펴면 62.0~100.8 dB 다» (cell 38). 규약은 절 1 방법 표 [^9][^10][^11] (3.5 GHz · 앙각 15° · 구면파 · 방위 24 점)
- **주장** «62.0~100.8 dB» 를 절의 규약(반송파 3.5 GHz · 구면파 · 기체 mini2·matrice4e)으로 잰 값처럼 싣고, 절 4 의 62~77 dB 와 다른 이유를 «방위 극값까지 펴면» 이라고 설명한다
- **냄새** a number from a ledger built with a DIFFERENT band / wavefront convention than the surrounding text implies (그리고 그 차이의 사유가 잘못 적혀 있다)
- **왜 인공물인가** 62.0~100.8 은 12 행(2 대역 × 3 기체 × 2 파면)의 min/max 다. 최대 100.80 dB 는 `hi|matrice4e|plane` — 즉 PO 무릎 대조 대역 15.86 GHz + 평면파 대조군 행이다. 절이 선언한 규약(3.5 GHz 헤드라인 · 구면파 헤드라인)만으로 같은 대조를 읽으면 62.0~76.8 dB 이고, 이것이 절 4 P1 이 든 «62~77 dB» 와 정확히 일치한다. 두 규약 차이는 «방위» 가 아니다 — 각 행은 이미 24 방위를 집계한 값이고(행마다 sigma_azimuth_sd_db 가 따로 있다), 실제로 벌어진 축은 대역과 파면이다. 게다가 대역을 올리면 구 잔차가 낮아지는 것은(점 간격이 λ/11 이라 파장이 짧을수록 점이 촘촘해진다) 물리가 아니라 표집이라, 15.86 GHz 행을 넣어 상한을 100.8 로 올린 것은 F2 의 바닥 효과를 그대로 증폭한 것이다. 같은 노트북 절 4 P6 은 15.86 GHz 를 «판정이 뒤집히는 대역» 으로 따로 취급하면서 헤드라인 숫자에는 그 대역을 섞어 넣었다.
- **직접 돌린 검산** outputs/report16_metric_sphere_eqvol.json.level_vs_modulation.rows 를 규약별로 갈랐다 — main(3.5 GHz)+spherical+{mini2,matrice4e} 만: 62.04 / 76.83 → 62.0~76.8 dB. 12 행 전체: 62.04~100.80, argmax = 'hi|matrice4e|plane'. 대역 정의는 report16_base.json.protocol 의 fc_main_hz=3.5e9 · fc_po_knee_hz=1.586e10, wavefront_headline='spherical' · wavefront_control='plane' 로 확인.
- ⭐**고칠 문장** Two fixes, both in reports/03_2_size-law.ipynb (via src/build_part06_ladder.py).  1. Cell 38's note is wrong about the axis and should not invoke azimuth. Replace:    "P1 이 드는 «메쉬 − 구» 간격은 기체별 집계이고, 방위 극값까지 펴면 62.0~100.8 dB 다 — 같은 대조를 두 규약으로 읽은 것이다"    with something like:    "P1 이 드는 62~77 dB 는 이 절이 선언한 규약(3.5 GHz · 구면파 · mini2·matrice4e)으로 읽은 값이다. 원장의 12 행 전부 — 두 대역(3.5 / 15.86 GHz) × 세 기체 × 두 파면(구면파 헤드라인 · 평면파 대조군) — 를 한 통에 넣으면 62.0~100.8 dB 가 되는데, 상한 100.8 dB 는 hi|matrice4e|plane 행, 즉 P6 이 «판정이 뒤집히는 대역» 이라 적은 15.86 GHz 의 평면파 대조군 행이다. 각 행은 이미 24 방위 평균이므로 이 폭은 방위가 아니라 대역·파면 축에서 나온 것이다(실제로 방위
- 확신도 high

#### 🟡 minor · **지금도 인용됨**

- **자리** 절 4 «치명적인 둘» P4 (cell 39), 절 4 일곱 가지 표 P4 행 (cell 38), 절 1 결과 3 (cell 2), 몫 분해 표 (cell 9). 원장 키 shape_vs_kinematics.rows.*.ac_power_db_LENS_CONVENTION.cube_eqvol.kinematics_share
- **주장** «정육면체 대 메쉬» 로 인용되는 차이의 55% [^104] ~ 74% [^105] 가 형상이 아니라 운동학이다 / 운동학 비중 74% · 55%
- **냄새** a ratio whose DENOMINATOR is a convention, not the quantity the sentence names
- **왜 인공물인가** 원장의 kinematics_share 는 |kin|/(|kin|+|mat|+|shp|) — 세 몫의 절댓값 합으로 나눈 정규화값이지, 본문이 말하는 «인용되는 차이(total_db)» 로 나눈 값이 아니다. 두 값이 크게 다르다: matrice4e 에서 총 차이는 15.11 dB 인데 운동학 몫은 23.30 dB 로 총 차이의 154% 이고(형상 몫 -13.71 dB 가 반대 부호로 상쇄한다), mini2 는 23.42/26.05 = 90% 다. 즉 55%·74% 는 물리량의 비중이 아니라 이 정규화 규약이 만든 수다. 결론의 방향(운동학이 형상보다 크다)은 오히려 강화되므로 과장은 아니지만, «차이의 55%» 라는 문장은 원장 정의와 맞지 않는다.
- **직접 돌린 검산** report16_synthesis.py:700-710 에서 den=abs(kin)+abs(mat)+abs(shp), kinematics_share=abs(kin)/den 확인. 원장값으로 재계산: mini2 cube (23.42+5.494+2.855=31.769 → 23.42/31.769=0.7372 = 원장 74%), 총 대비 23.42/26.05=0.899. matrice4e cube (23.30+5.525+13.71=42.535 → 23.30/42.535=0.5477 = 원장 55%), 총 대비 23.30/15.11=1.542.
- ⭐**고칠 문장** FILE: the fix belongs in /workspace/sionna/reports/03_2_size-law.ipynb (NOT 06_1_scene.ipynb), and the true source is the generator /workspace/sionna/benchmark/report16_synthesis.py:1513-1515 — edit the generator, not the notebook.  Leave cell 9's table, cell 2 결과 3, and cell 38's P4 row exactly as they are: «운동학 비중» is an honest label for |kin|/(|kin|+|mat|+|shp|), and their attached assertions hold under either normalizer.  Change only the sentence emitted at report16_synthesis.py:1513-1515 (which lands in cell 39 P4 and cell 35 결과 2). Instead of    «인용되는 «정육면체 대 메쉬» 차이의 55%~74% 가 형상이 아니라 운동
- 확신도 high

### `06_2_engines.ipynb` — 3 건 (살아 있음 3)

#### 🟠 serious · **지금도 인용됨**

- **자리** Cell 1 — 「세 엔진이 각각 무엇을 하나」, the ⚠ paragraph under the three-engine table
- **주장** 「가림만 떼어낸 깨끗한 축은 report15b 의 F(동체 Γ=0) ↔ G(동체 면만 제거) 이고, 이 편의 자세(배 쪽)에서 그 실측은 레벨 +1.31 dB · 변조 깊이 -4.79 dB 다」
- **냄새** a metric whose value is set by the ray-grid geometry (sub-cell plate offset) rather than the signal; a conclusion that would flip if a free parameter were nudged
- **왜 인공물인가** These are presented as THE clean, occlusion-only measurement. But F and G do not share a geometry (F has a body, G has its faces deleted), so the frozen plate's sub-cell offset bias does not cancel between them. Move the frozen ray plate by half a grid cell — a pure measurement-setup parameter, zero physics change — and both numbers change sign. The source ledger itself says so: report15b_microdoppler.json carries occlusion_plate_caveat_ko = 「판을 반 칸 옮기면 위 두 dB 가 인용값보다 크게 움직인다 … 크기를 쓰려면 오프셋 여러 판의 앙상블 평균이 먼저다」, and the sibling volume 06_3, which owns this figure, prints a ⛔ block saying exactly 
- **직접 돌린 검산** outputs/freeze_plate_sensitivity.json :: cells['matrice4e/belly'].findings — three plates identical in ray count, spacing and size, differing only by half-cell centre shifts: occlusion_level_db = [1.533, 2.122, -2.041] (p-p 4.163 dB, sign flips), occlusion_ptp_db = [-17.978, -18.266, +8.259] (p-p 26.525 dB, sign flips). Quoted values 1.315 and -4.792, so the plate-induced spread is 3.2x and 5.5x the quoted magnitude.
- ⭐**고칠 문장** 06_2 Cell 1's ⚠ paragraph should keep the axis claim but drop the bare magnitudes, matching the rule 06_3 already enforces. E.g.: 「⚠ 둘째와 셋째는 가림 말고 이산화 방식도 다르다(광선 격자 ↔ 점구름). 그래서 둘의 차이가 «가림만» 의 값은 아니다. 가림만 떼어낸 단일축은 report15b 의 F(동체 Γ=0 — 막되 산란 안 함) ↔ G(동체 면만 제거, 정점은 남겨 광선 격자 동일) 이고, 이 편의 자세(배 쪽)에서 세우는 것은 «동체가 막으면 레벨과 변조 깊이가 함께 움직인다» 는 존재까지다. ⛔ 그 dB 크기는 본문 밖이다 — 얼린 판의 중심을 반 칸만 옮기면 레벨 차가 4.16 dB, 깊이 차가 26.52 dB 흔들려 원장 값(+1.31 / -4.79 dB)을 부호까지 덮는다(outputs/freeze_plate_sensitivity.json : verdict). 두 팔은 같은 판을 쓰지만 기하가 달라(막는 팔은 동체가 있고 안 막는 팔은 동체 면이 없다) 판 오프셋 편향이 공통모드로 빠지지 않는다. 크기를 쓰려면 오프셋 여러 판의 앙상블 평균
- 확신도 high

#### 🟠 serious · **지금도 인용됨**

- **자리** Cell 3 — 「광선 격자를 어디에 매나」 → 「이 판을 믿을 근거 두 가지 ①」
- **주장** 「이 판을 믿을 근거 두 가지 — ① 판의 위치에 둔하다. 같은 «얼림» 을 다른 봉투로 잡은 판(E_froz_div12)과 견주면 진폭 상관 0.993 · 레벨 차 -0.006 dB 다 … 차이를 만든 것은 판의 위치가 아니라 판이 움직였다는 사실이다」
- **냄새** a null result produced by a perturbation far below the scale that matters (grid-resolution floor) reported as robustness; contradicted by the project's own dedicated audit
- **왜 인공물인가** The 「insensitive to plate position」 test compares two frozen plates whose envelopes differ by ~0.1 mm on a 7.138 mm cell — about 1.4 % of one cell, i.e. essentially the same sub-cell sampling phase. It cannot detect position sensitivity. The project's dedicated adversarial audit, which moved the plate by half a cell (3.57 mm), finds the same arm's absolute level moves 1.549 dB p-p (belly) / 3.452 dB p-p (nose) and the occlusion-axis two-arm difference 4.163 dB p-p with a sign flip. So the 0.006 dB null is a property of how small the perturbation was, not of the method. The notebook's own 「대가」 
- **직접 돌린 검산** outputs/freeze_before_after.json :: ledgers['report07_three_engines/sbr'].plate_choice_check = {amp_corr 0.99297, level_db_delta -0.00606, note_ko: 「봉투가 0.1 mm 남짓 다르다」}; spacing = 0.007137915 m → 0.1/7.138 = 1.4 % of a cell. Against outputs/freeze_plate_sensitivity.json :: cells['matrice4e/belly'].arms.A_sbr_locked.level_db.ptp = 1.549 dB and cells['matrice4e/nose'] = 3.452 dB for half-cell shifts — 250x to 570x the 
- ⭐**고칠 문장** Scope ① to what was actually varied, and put the position number where the claim is.  Suggested replacement for 「이 판을 믿을 근거 두 가지 ①」:  **① 봉투를 어떻게 잡든 같은 판이 나온다.** 같은 «얼림» 을 다른 봉투로 잡은 판(`E_froz_div12` — 자세 4,096 개 전부의 합집합)과 견주면 진폭 상관 0.993 · 레벨 차 -0.006 dB 다. ⚠ 다만 이것은 **판의 위치**를 흔든 시험이 아니다 — 두 판은 한 변 칸수(124)·간격(7.138 mm)이 같고 중심이 가로로 **0.109 mm(한 칸의 1.5 %)** 어긋날 뿐이라 서브셀 오프셋이 사실상 같다. 판을 **반 칸** 옮기면 같은 잣대가 진폭 상관 0.819 · 레벨 차 +1.41 dB 로 벌어진다⟨`outputs/sbr_grid_freeze_falsify.npz : E_froz ↔ E_froz_half` — 같은 자세·같은 판 크기, 재현 게이트 비트 동일⟩. 그러므로 이 항이 말하는 것은 «봉투 선택(로터 한 바퀴를 몇 등분해 합집합을 잡나)이 결과를 안 바꾼다» 이지 «판의 
- 확신도 high

#### 🟡 minor · **지금도 인용됨**

- **자리** Cell 4 — 「블레이드 플래시를 세 엔진으로 나란히 (60 ms 확대)」, final ⚠⚠ paragraph
- **주장** 「원장의 실측 격차 -65.5 dB 에서 환산을 빼면 남는 것은 -24.5 dB 이고, 그것이 «프롭 정반사 경로가 0 칸» 으로 설명해야 할 몫이다」
- **냄새** a value set by one Monte-Carlo seed draw and an unconverged ray budget, quoted to 0.1 dB and given a physical cause
- **왜 인공물인가** The unit conversion is correct (-20log10(4*pi*R^2) is exactly the h-to-PO-amplitude factor once sigma = 4*pi*|E|^2/lambda^2), so the arithmetic is fine. What is not fine is that the residual inherits the Sionna arm's absolute level, which this very notebook establishes two cells earlier to be a single lottery draw that swings 18 dB with seed and that does not converge in ray count. Neither fact is carried into the residual — the ⚠⚠ there warns only about units. At the geometry actually used (matrice4e, az 0 / el -15, 3 m, spp 1.0M), changing only the seed moves the level 4.95 dB, and raising s
- **직접 돌린 검산** outputs/report07_three_engines.json :: levels_db.sionna -117.0758, levels_db.sbr -51.5455 → gap -65.530; CONV = -20*log10(4*pi*3^2) = -41.070 → RESID -24.46 (matches src/make_report08_microdoppler.py:155-160). Seed sensitivity: outputs/probe_8m_anomaly.json :: runs_512pose.LEDGER_R3_first512.db_of_mean_abs = -117.033 vs E_R3_spp1.0M_seed2 = -121.979 → 4.95 dB, same range/spp/pose set. Budget: prior_probe_reanalysis.s
- ⭐**고칠 문장** Keep the unit conversion and the gap, but stop presenting the remainder as a quotable figure with a cause attached. Replace the closing of the cell-4 ⚠⚠ (generated at src/make_report08_microdoppler.py:1057-1060) with something like:  「원장의 실측 격차 -65.5 dB 에서 환산을 빼면 -24.5 dB 가 남는다. ⚠⚠ 그러나 이 몫은 인용할 수 있는 수가 아니다 — 위 «추첨 한 장» 절이 밝힌 대로 Sionna 팔의 절대 레벨은 시드 한 장이고 광선 수에 수렴하지 않는다. 같은 기하·같은 자세·같은 자세열에서 시드만 바꾸면 잔차가 -29.4 dB(seed 2) · -16.9 dB(자세별 시드) 이고, 광선 수를 이 편의 표가 15 m 에 쓴 25M 로 올리면 -5.9 dB 다(레벨 -117.03 → -98.51, +18.5 dB — `outputs/probe_8m_anomaly.json:runs_512pose` · `prior_probe_reanalysis.ctrl_same
- 확신도 high

### `06_3_pattern.ipynb` — 3 건 (살아 있음 3)

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 2 «시간표본마다 자세를 새로 놓고…» — 결과 3·4 (cell 19) and the table 「창이 분해능을 정한다」 (cell 23); sources [^13]–[^17] (cell 27)
- **주장** 「표본율 19700 Hz [^13] 로 6000 개 [^14] 를 이어 붙여 창 길이 0.505 s [^15] 를 얻었다. 그 창이 주는 도플러 분해능은 1.98 Hz [^16] 이고, 날개끝까지 621 칸 [^17] 이 든다.」 — and the table in 「창이 분해능을 정한다」: 표본율 19700 Hz · 표본 수 6000 개 · 창 길이 0.505 s · 도플러 분해능 1.98 Hz · 날개끝까지 621 칸
- **냄새** a metric whose value is set by a WINDOW LENGTH / FFT SIZE rather than the signal — here the quoted window and resolution are the NOMINAL values the script asked for, silently invalidated by a hard-cod
- **왜 인공물인가** benchmark/report15b_microdoppler_recompute.py:119 is `n_t = int(min(MAX_SAMPLES, round(prf*dur)))` with `MAX_SAMPLES = 6000` (line 106). For the headline Matrice 4E cell the requested window (64 blade periods) needs 19700×0.50526 = 9954 samples, so the cap CLIPS it to 6000. But `duration_s`, `doppler_resolution_hz` and `bins_to_ftip` (lines 121-123) are all computed from the UNCLIPPED nominal (`dur = N_FLASH_PERIODS/f_flash`, `f_flash/64`), so the ledger keeps reporting the resolution of a window that was never run. The actual record is 0.3046 s = 38.6 blade periods, not 64. This is not a roun
- **직접 돌린 검산** (1) Read the ledger physics dict for all 6 cells: matrice4e/* have n_t=6000, prf=19700, duration_s=0.5053 → n_t/prf = 0.3046 s, i.e. quoted duration is 1.659× the real one; mini5pro/* have n_t=5551, prf=15900, duration 0.3491 = 5551/15900 exactly (uncapped, consistent). (2) Read the frequency axis actually stored with the spectra: `np.load('outputs/report15b_series.npz')['matrice4e/belly/B_sbr_spread/spec_f']` has 60
- ⭐**고칠 문장** 절 2 결과 3·4 and the table 「창이 분해능을 정한다」 should read (matrice4e/belly):    표본율 19700 Hz · 표본 수 6000 개 · 창 길이 0.305 s · 도플러 분해능 3.28 Hz · 날개끝까지 374 칸  i.e. 결과 3: «표본율 19700 Hz 로 6000 개를 이어 붙여 창 길이 0.305 s 를 얻었다 — 블레이드 38.6 주기다.» 결과 4: «그 창이 주는 도플러 분해능은 3.28 Hz 이고, 날개끝까지 374 칸이 든다.»  Plus a ⚠ note, because the gap between what was asked and what was run is itself the point: «⚠ 스크립트는 64 블레이드 주기(0.505 s · 9954 표본)를 요청했지만 `MAX_SAMPLES = 6000` 안전 상한에 걸려 6000 표본에서 잘렸다. 실제 창은 38.6 주기다. 원장의 `duration_s` · `doppler_resolution_hz` · `bins_to_ftip` 은 잘리기 전 이름값으로 계산돼 있어 그대로 인용하면 안 된다 — matrice4e 칸만 해당하고, min
- 확신도 high

#### 🟠 serious · **지금도 인용됨**

- **자리** 앞머리 그림 「블레이드는 강하고 동체가 덮는다」 (cell 3); 절 6 결과 1 (cell 61), 표 「두 채널의 값」 (cell 64), 「그래서 무엇이 어려운가」 (cell 65); 절 5 결과 2 (cell 51) and 표 (cell 54)
- **주장** 「전체 드론 채널의 변조 깊이는 5.36 dB p-p 인데, 프로펠러 채널만 떼면 50.32 dB p-p 다 — 9 배 차이다」 / 「프로펠러 채널의 변조는 전체 채널보다 아홉 배 넘게 깊다」 / 「SBR 팔이 낸 프로펠러 채널의 변조 자체는 50.3 dB 로 깊다」; also 절 5's in-text F 50.32 dB / G 55.12 dB
- **냄새** a ratio that is large because the DENOMINATOR is tiny/degenerate (max/min where the min is a single coherent-sum null), compounded by a metric whose value is set by the SAMPLE COUNT rather than the si
- **왜 인공물인가** `modulation_ptp_db` is literally `db.max() - db.min()` on 20log10|E| (report15b_microdoppler_recompute.py:225). The full-drone channel keeps the body's static return as a DC pedestal (dc_over_ac = 9.42), so |E| never approaches zero and the p-p is a stable statistic. The blade-only channel has the body absorbed away (dc_over_ac = 0.761), so the coherent sum passes through nulls and the minimum is whatever the sample grid happens to land nearest to a zero — i.e. the 50.32 dB is set by n_t and by luck, not by how deep the blade modulation is. The project already knows this: `outputs/report07_dep
- **직접 돌린 검산** From outputs/report15b_series.npz, matrice4e/belly: F_blade_occ p-p = 50.32 dB, but p5–p95 = 19.44 dB, p1–p99 = 27.93 dB; deleting the single deepest of 6000 samples drops it to 43.33 dB (−6.99 dB from ONE sample; the min is 3.55e-6 while the next-smallest is 7.95e-6 and the median is 2.54e-4). Decimating to every 10th sample over the SAME window gives 33.57–49.79 dB depending on offset (16.2 dB spread). Decimating b
- ⭐**고칠 문장** The section's conclusion is right; only the statistic carrying it needs replacing. Concretely:  1. Stop quoting `modulation_ptp_db` as an absolute depth. Apply 06_2's own rule and the project's existing `report07_depth_robust.json` convention to the report15b arms as well: quote p-p and p5~p95 together, plus the ratio as the stability figure.     | 무엇을 | 전체 드론 채널 (B_sbr_spread) | 프로펠러 채널 (F_blade_occ) |    |---|---|---|    | 변조 깊이 p5~p95 | 2.44 dB | 19.44 dB |    | 변조 깊이 p-p | ⛔ 5.36 dB — 본문 밖 | ⛔ 50.32 dB — 본문 밖 |    | 변조 깊이 std | 0.73 dB | 5.93 dB |    | 동체:날개 비 | 9.42 | 0.761 |  2. Replace 
- 확신도 high

#### 🟡 minor · **지금도 인용됨**

- **자리** 절 3 「세 엔진을 같은 격자에 태우면」 (cell 33), source [^38] = outputs/report07_three_engines.json:ptp_db.sionna = 32.65
- **주장** 세 엔진 표: 「| S | Sionna PathSolver | 32.6 dB [^38] | 5.06% | 얼룩이 대역을 채우고… | / | B | 5.3 dB | / | P | 2.8 dB |」 presented as the 변조 p-p of the three engines
- **냄새** a difference smaller than (in fact entirely inside) the RUN-TO-RUN SPREAD being reported as a difference; the same max/min-over-samples statistic as above
- **왜 인공물인가** The project's own audit ledger outputs/deck0818_plan.json records this exact quantity as `{"k": "Sionna p-p", "type": "run_to_run_instability", "values_db": [7.68, 15.42, 32.65], "why_ko": "같은 양이 4배 이상 흔들린다"}` and puts it on the 「한 자리도 쓰지 않는다」 list (teammeeting_0818/ROADMAP.md §1-C #5: 「원인은 물리가 아니라 광선 표본화 — 경로를 거의 못 찾은 자세 하나가 전폭을 혼자 정한다」). The sibling report 06_2_engines.ipynb prints the same table WITH the guard — a p5~p95 column and 「⚠ 이 표의 깊이를 물리량으로 인용하지 마라… p-p 가 32.6 / 2.5 / 50.1 dB 로 요동친다(3 / 8 / 15 m)」. 06_3 is declared the 근거 절 for that comparison, but its copy of the table drops the p
- **직접 돌린 검산** outputs/report07_depth_robust.json (a ledger built for exactly this purpose — «본문에 손으로 적혀 있던 수치를 대체한다») gives, for the same 4096-sample series: sionna ptp 32.646 / p5p95 7.506 / ptp_over_p5p95 4.35 / ptp_db_drop1 27.10; sbr 5.327 / 2.452 / 2.17; po 2.765 / 1.203 / 2.30. Its sionna_by_range block gives ptp 32.65 (3 m), 2.48 (8 m), 50.11 (15 m) for the same arm — a 47.6 dB swing with range. Ratio check: 32.646/5.327 = 
- ⭐**고칠 문장** 06_3 §3 cell 33 should carry the same guard its own summary volume already carries, i.e. the table becomes  | 팔 | 무엇으로 쟀나 | p-p | p5~p95 | 비 | 전체 전력 중 날개끝 밖 | 무늬 | | S | Sionna PathSolver | 32.6 dB | 7.5 dB | 4.3× | 5.06% | … | | B | Ours (SBR+PO, 기본) | 5.3 dB | 2.5 dB | 2.2× | 0.18% | … | | P | Ours, nothing blocked (control) | 2.8 dB | 1.2 dB | 2.3× | 0.00007% | … |  with the warning ported from 06_2 and one sentence added that 06_2 does not yet have:  「⚠ 이 표의 깊이를 **물리량으로 인용하지 마라** — 특히 S 열의 32.6 dB. p-p 는 자세 N 개에 대한 max−min 이라 N 에 딸려 자란다: 같은 4096 표본 열에서 부분표본 p-p 중앙값이 N=64 13.5 → 512 18.3 → 
- 확신도 high

### `08_detector.ipynb` — 3 건 (살아 있음 3)

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 2, cell 13 「직접파를 얼마나 지울 수 있는가」 (footnotes 29-31; verify_eca.json S3_pilot_vs_tx[6,7,8].rd_offzero_peak_over_nfloor_db)
- **주장** 「데이터 잔류가 0-도플러 행에 앉으므로 RD 맵의 비-0도플러 첨두는 잡음 플로어 대비 WiFi -164.8 dB [^29] · LTE -41.0 dB [^30] · 5G -180.2 dB [^31] 다.」
- **냄새** a value that equals a noiseless/numerical-zero value being reported as an effect; causal language where the stated mechanism is contradicted by a sibling key in the same ledger
- **왜 인공물인가** -180.2 dB and -164.8 dB below a noise floor are not measurements — they are the float64 rounding floor of an exact null. The DPI/clutter residual is built from tx_frame (pilot+data) while the correlator reference is ref_frame (pilot only); the data REs are exactly orthogonal to the pilot template under this synthesis (integer frame tiling, no CFO, no timing offset, delay = pure per-subcarrier phase), so the residual produces *nothing* anywhere in the RD map. The stated mechanism is also wrong: the ledger's own sibling key rd_zerodop_peak_over_nfloor_db is -137.7 dB (5G G3) and -122.3 dB (WiFi 
- **직접 돌린 검산** Recomputed S3 for 5G G3 and WiFi G3 with verify_eca.Setup/ECACanceller/range_doppler, then perturbed only arithmetically irrelevant things. 5G G3: float64 (ledger) rd_off = -180.2 dB, rd_zd = -137.7 dB; rounding the *same* residual to complex64 and back -> rd_off = -130.4 dB (+49.8 dB), rd_zd = -87.9 dB; multiplying the residual by exp(j2pi*0.01Hz*t) (0.00024 of one 41.7 Hz Doppler bin) -> rd_off = -98.8 dB (+81.4 dB
- ⭐**고칠 문장** The sentence in cell 13 (and its source, reports/_parts/52_eca.ipynb) should drop the three rd_offzero numbers entirely, and split the mechanism by waveform. Suggested replacement, in house style:  「두 열 모두 직접파를 기준신호로 합성한 판이다(`benchmark/verify_eca.py:146,147`). 헤드라인 사슬은 직접파를 송신 파형 전체(파일럿+데이터)로 합성하고(`benchmark/run_min_cell.py:164`), 그 판의 시간영역 깊이는 WiFi 0.35 dB [^27] · LTE 1.33 dB [^28] · 5G 1.60 dB [^11] 다 — 시간영역에서는 거의 지워지지 않아 잔류가 열잡음보다 WiFi +31.4 dB · LTE +61.3 dB · 5G +44.7 dB 크다. 그런데도 RD 맵에서 이 잔류가 서는 자리는 파형마다 다르다.  · LTE 만 «0-도플러 행에 앉는다» 는 그림에 맞는다 — 0-도플러 첨두가 잡음 플로어 대비 +1.5 dB 로 실재하고, 0-도플러 마스
- 확신도 high

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 4, cell 31 결과 2 and cell 35 「셀 상관은 어느 검출기에나 있다」 (ladder table in cell 33; verify_cfar.json control_*_NR100 vs chain.NR100.dpi_eca.op)
- **주장** 「거리축 항까지 끄면 1.02 [^61] 로 눈금이 1 로 돌아온다 — 두 항이 배율의 전부다.」 … 「그 사다리가 위 표이고, 마지막 줄과 첫 줄 사이의 간격이 곧 두 항의 몫이다.」
- **냄새** causal language where the control does not cover the step being explained — the ladder's last row is produced by a stage no control turns off
- **왜 인공물인가** All three controls (control_rect_window_NR100, control_whitened_mf_NR100, control_whitened_mf_rect_NR100) are run by verify_cfar.py:695 with mode="noise" — no DPI, no ECA. So they can only account for the white->noise step, 0.9966 -> 1.2465. The ladder's last row, 전체 사슬 1.5213, comes from the dpi_eca branch, and the residual factor 1.5213/1.2465 = 1.2205 is turned off by nothing. In dB terms the total excess is +1.83 dB and the two named terms explain +0.96 dB of it; +0.87 dB — nearly half — is unattributed. The ledger even shows where it comes from: rho_range lag-1 is 0.071 in the noise map b
- **직접 돌린 검산** Read verify_cfar.py:686-702 (all three controls call exp_chain(..., "noise", ...)) and pulled the g2x2_t6x6 / mask=1 / pfa_nom=1e-4 rows: white 48x24 ratio 0.9966 (56209 hits / 5.64e8 cells); NR100 noise op 1.2465 (1406/1.128e7); NR100 dpi_eca op 1.5213 (1716/1.128e7). 1.5213/1.2465 = 1.2205. Whiteness diagnostics: rho_range[0] = 0.071 (noise) vs 0.534 (dpi_eca).
- ⭐**고칠 문장** 절 4 결과 2 and cell 35 should limit the two-term claim to the noise map and name the uncontrolled remainder.  결과 2 (cell 31): "거리축 항까지 끄면 잡음 맵의 눈금이 1.02 로 돌아온다 — **잡음 맵**의 배율은 이 두 항이 전부다(+0.97 dB). 운용 형상(전체 사슬)의 1.52 는 거기서 ×1.22(+0.87 dB) 더 크고, 그 몫을 끄는 대조군은 아직 없다 — 대조군 셋은 모두 `mode="noise"` 에서 돌았다(`benchmark/verify_cfar.py:695`)."  cell 35: "그 사다리가 위 표이고, **잡음 맵 줄과 대조군 줄 사이**의 간격(+0.97 dB)이 두 항의 몫이다. 마지막 줄(전체 사슬)까지 남는 +0.87 dB — 전체 초과의 47% — 는 대조군이 끄지 않은 DPI+ECA 단계의 몫이다."  Optionally add the mechanism, which the ledger already pins down: the extra ×1.22 is a 0-도플러 노치 어깨 효과, not a third cell-corre
- 확신도 high

#### 🟡 minor · **지금도 인용됨**

- **자리** 절 2, cell 11 결과 4 and cell 15 「대가 — 0-도플러 노치」 (footnotes 12-16; verify_eca.json S4_target_loss)
- **주장** 「3 dB 손실 지점은 f_d/Δf_d = 0.596 [^12] 이고 세 파형이 같다 — 속도 문턱은 λ 가 가른다.」 with the table 「3 dB 속도 문턱 (프레임 48개): WiFi 0.39 m/s · LTE 1.10 m/s · 5G 1.16 m/s」
- **냄새** a comparison whose ordering is set by a fixed-frame-count convention rather than by the waveform; the conclusion flips when the free parameter (M vs CPI duration) is nudged
- **왜 인공물인가** λ does not gate the ordering. At M=48 the three arms do not share a CPI duration: WiFi and LTE get 48 ms (Lf = 1 ms) but 5G gets 24 ms (Lf = 0.5 ms), so 5G's Δf_d is 41.67 Hz against 20.83 Hz for the others. 5G ends up worst (1.16 m/s) not because of its wavelength — λ = 0.0857 m sits between WiFi's 0.0575 and LTE's 0.1627 — but because the fixed-48-frame convention halves its coherent integration time. The report's own ledger contains the equal-duration comparison: at M=96 (5G T_cpi = 48 ms, matching the others) the thresholds are WiFi 0.3906, 5G 0.5777, LTE 1.1042 m/s — 5G becomes second-bes
- **직접 돌린 검산** Read all nine S4_target_loss entries. fd_3db_over_dfd = 0.6129 / 0.5957 / 0.5919 at M = 16 / 48 / 96, identical across all three waveforms at each M (so the collapse claim itself holds, though the constant drifts 3.5% with M). v_3db_ms: at M=48 WiFi 0.3906, LTE 1.1042, 5G 1.1628 (T_cpi 48/48/24 ms); at M=96 WiFi 0.1941, LTE 0.5486, 5G 0.5777 (T_cpi 96/96/48 ms). Equal-duration set (WiFi M=48, LTE M=48, 5G M=96, all 4
- ⭐**고칠 문장** 절 2 cell 11 결과 3-4 and cell 15 should keep the collapse and the table but drop the λ-only attribution, e.g.:  「3 dB 손실 지점은 f_d/Δf_d = 0.596 이고 세 파형이 같다 — 속도 문턱을 가르는 것은 λ 와 Δf_d(=1/T_CPI) 둘이다.」  and under the table add the convention's cost:  「프레임 수를 48 로 고정하면 세 파형의 CPI 가 같지 않다 — 프레임 길이가 WiFi·LTE 1 ms, 5G 0.5 ms 라 CPI 는 48 · 48 · 24 ms 다. 그래서 5G 의 문턱 1.16 m/s 는 λ 만으로 예상되는 0.58 m/s 의 정확히 2.000 배이고, 5G 가 LTE 보다 나쁜 것(1.16 vs 1.10, 5%)은 λ 가 아니라 이 규약이 만든 순서다 — λ 만 보면 5G 는 LTE 의 0.53 배로 오히려 낫다. 같은 원장에서 CPI 를 48 ms 로 맞추면(5G 프레임 96개) 문턱은 WiFi 0.39 · 5G 0.58 · LTE 1.10 m/s 로, 그때 비로소 λ 순서가 된다.」  Add ledg
- 확신도 high

### `01_map.ipynb` — 2 건 (살아 있음 2)

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 3 «주장마다 판정 범위를…» — 결과 5 (cell 28), 반복: «모서리 회절 행» (cell 32); 출처 [^32] outputs/p3_validation.json:residual.vs_yuan_theta90_measured_curve.mean_db, [^33] outputs/p3_validation_v2.json:v1_vs_v2.level_db.v2
- **주장** 레벨 행의 눈감기 사전값은 고도정합 실측곡선 대비 밴드평균 -4.91 dB [^32] 이고, 사진 실측 v2 메쉬에서는 -3.30 dB [^33] 다.
- **냄새** a metric whose value is set by the averaging window (band) rather than by the signal — the ledger's own averaging range (1.8–18.2 GHz) is 5x wider than the band the claim is used to judge (1.843–5.21 
- **왜 인공물인가** Both numbers are means over the ANCHOR paper's measurement range 1.8–18.2 GHz, not over the campaign's own bands. All three campaign carriers (LTE 1.843 / 5G 3.5 / WiFi 5.21 GHz, report06_derived.slope.campaign_window_ghz = [1.843, 5.21]) sit in the lowest quarter of that range, and the residual is strongly frequency-structured. Both ledgers already compute the in-band figure in an `our_operating_band` block (1.8–6.0 GHz) and neither report quotes it. In-band the level deficit is v1 -5.78 dB and v2 -5.16 dB, i.e. the v2 mesh's deficit inside the operating band (-5.16 dB) is WORSE than the v1 h
- **직접 돌린 검산** p3_validation.json / p3_validation_v2.json, key vs_yuan_theta90_measured_curve: full-band mean v1 = -4.913 dB, v2 = -3.304 dB (change +1.609). our_operating_band.level_error_db.mean (1.8–6.0 GHz): v1 = -5.783 dB, v2 = -5.165 dB (change +0.619). Interpolating the residual curve at the three campaign centres: v1 = [-7.91, -7.52, -3.58] dB (mean -6.34), v2 = [-5.19, -6.59, -3.69] dB (mean -5.16). So the report's -3.30 d
- ⭐**고칠 문장** Add the window and the in-band figure to both occurrences (cell 28 result 5, cell 32), e.g.:  "레벨 행의 눈감기 사전값은 고도정합 실측곡선 대비 **앵커 전대역(1.8–18.2 GHz)** 평균으로 -4.91 dB (v1 메쉬) · -3.30 dB (v2 메쉬) 다. ⚠ 단 이 캠페인이 송신하는 창은 1.843–5.21 GHz 뿐이고, 같은 잔차를 1.8–6.0 GHz 로 자르면 v1 -5.78 dB · v2 -5.16 dB 다 (`our_operating_band.level_error_db.mean`). v2 잔차는 0.192 ± 0.039 dB/GHz (5.0σ) 로 주파수 구조가 있어 전대역 평균이 우리 대역의 결손을 1.86 dB 낮춰 적는다 — 전대역 개선폭 1.61 dB 중 대역 안에 남는 것은 0.62 dB 이고 나머지는 6 GHz 위에서 온다. 옆 행의 기울기 문턱 1.77 dB [^37] 는 이미 밴드정합(1.8–6.0 GHz)값을 쓴다. 원장 자신이 '전대역 평균이 구조를 감춘다' 와 '규약 분기가 0.93 dB — 단일값으로 적으면 거짓 정밀이다' 를 적어 두었다.
- 확신도 medium

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 3 — 결과 4 (cell 28); repeated in «모서리 회절 행» 표 (cell 32) and 다음 단계 (cell 35); 출처 [^31] outputs/ptd_wiring.json:verdict.cost_increase_pct = 47.17
- **주장** PTD(모서리 회절) 행도 `결판` 이다 — 켠 비용은 +47.2% [^31] 이고, 정면입사만 재면 판별력이 0 이라 비스듬한 입사를 함께 잰다.
- **냄새** a metric whose value is set by the grid resolution and by the timing estimator / GPU contention rather than by the thing being measured; a difference straddling the run-to-run spread reported as a sin
- **왜 인공물인가** +47.2% is the median of paired wall-clock ratios on ONE setting (synthetic drone-like target, div=16, 120 poses, 11 paired reps) timed on a GPU shared with a 100%-util job — the ledger's own D_cost.measurement_caveat says single-shot wall clock swung by 2.5x and that 'ratio_min<1 인 반복이 남아 있는 것은 경합 잡음이다'. The edge term's per-pose cost is nearly constant while the surface integral grows as grid^2, so the percentage is a property of the grid: D_cost.model states '증가율은 설정 의존이다. 측정 범위 +8 ~ +154 %'. Report 01 quotes the single 47.2% three times as the decision-relevant cost of enabling PTD, with no 
- **직접 돌린 검산** outputs/ptd_wiring.json:D_cost — headline median +47.2% but ratio_min = 0.979 (PTD-on FASTER than PTD-off in at least one paired rep) and ratio_max = 1.801. Same-tag by_setting rows: 'drone-like div16 (production)' median +62.3% (vs the 47.2% headline for the same setting, a 15-point swing from rep count alone) but min-of-7 reps +5.3%; 'div16 short sweep' median +52.7%, min-of-7 -35.9%; 'div24 fine grid' median +8.1%
- ⭐**고칠 문장** 01_map cell 28 (결과 4), cell 32 (표) and cell 35 (다음 단계) should stop quoting the bare "+47.2%". The number is a paired-ratio median on ONE setting on a contended GPU, and the ledger's own D_cost.model says the increase rate is setting-dependent over +8 ~ +154 %. Suggested replacement wording for the 결과 line (and the same clause in cells 32/35):  "PTD(모서리 회절) 행도 `결판` 이다 — 켠 비용은 설정에 따라 **+8 ~ +154 %** 이고(생산 격자 div=16·drone-like 합성표적·120 자세에서 짝지은 비율 중앙값 +47.2 % [^31], 같은 설정을 7 회로 다시 잰 판은 +62.3 %, div=24 는 +8.1 %, div=12 셸은 +154 %), 모서리항의 per-pose 비용이 거의 상수이고 면적분이 격자² 로 커지기 때문에 이 백분율은 **격자가 정한다**. 이
- 확신도 high

### `04_elevation-coverage.ipynb` — 2 건 (살아 있음 1)

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 3 «물리 상한 위 누설» — section heading (cell 45), 결과 2 (cell 46), 표 «세 팔이 상한 위에 남기는 몫» (cell 52), «우리 팔도 −15°·−30° 두 자리에서 샌다» (cell 55)
- **주장** 「물리 상한 위 누설은 우리 팔 0.22~17.18 %」 (절 3 제목·결과 2) and 「el −15°·−30° 는 이 표에서 우리 팔이 물리를 끈 PathSolver 보다 높은 두 자리다 — 각각 6.53% · 1.06% 위다. 같은 잣대가 우리 팔에도 인공물을 드러낸다.」 (cell 55)
- **냄새** a difference smaller than the run-to-run spread being reported as a difference; a conclusion that would flip if a free parameter (ray-grid density / grid phase) were nudged
- **왜 인공물인가** 17.18% and 10.62% are not engine properties — they are one realization of the frozen λ/12 ray grid. The project already measured this: outputs/grid_convergence_check.json records a pre-registered grid-dispersion band for this exact metric (grid_dispersion_bands.layer2_statistics, metric above_f_tip_pp, band = 12.55 %p, median 5.40 %p) with the instruction «두 팔의 차이가 이 밴드 안이면 판정 불가». All three gaps the report reads as findings (el−15: 10.65 %p, el−30: 9.56 %p, el−45: 0.88 %p) are inside that band. The same file's arm_order_tables.prereg_3arms marks above_f_tip_pct at el−15 and el−45 as verdict «
- **직접 돌린 검산** Re-ran build_wideband_energy_fig.py's own spectrum()/above_f_tip_frac on outputs/elevation_sweep_md.npz (CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark). above f_tip [% of AC power] at el 0/−15/−30/−45/−60/−75 — ours_r15_n8192 (λ/12): 2.70 / 17.18 / 10.62 / 1.81 / 1.76 / 0.22 (exactly reproduces the ledger). ours_r15_n8192_div24 (λ/24, n_missing=0 at all 7 el): 1.52 / 4.63 / 1.36 / 0.27 / 0.47 / 0.04. ours_r15_n819
- ⭐**고칠 문장** §3 heading and 결과 2 should carry the mandated tag and the range should not be quoted bare:    «물리 상한 위 누설은 **λ/12 격자에서** 우리 팔 0.22~17.18 %, 스톡 PathSolver 0.81~96.17 % …»   결과 2 → «… 0.22 %~17.18 % 사이다(λ/12 한정 — 같은 잣대·같은 원장의 λ/24 판에서는 0.04 %~4.63 % 로 내려간다).»  Cell 55 should be rewritten. Corrected text:    «우리 팔은 λ/12 판에서 el −15 (17.18 %) · −30 (10.62 %) · −45 (1.81 %) **세 자리**에서 물리를 끈 PathSolver(6.53 · 1.06 · 0.94 %)보다 높다. 그런데 그 세 자리의 여유(10.65 · 9.56 · 0.88 %p)는 전부 이 잣대의 격자 산포 밴드 12.55 %p (`outputs/grid_convergence_check.json` : `grid_dispersion_bands.bands.layer2_statistics` / `above_f_tip_pp
- 확신도 high

#### 🟠 serious · 이미 사문화

- **자리** 절 2 «대역 추적» — 결과 5 (cell 25), 정규화 표 (cell 37), «분모를 바꿔도 같은 결론이 서는가» (cells 38–39), 그림 4 part79_normalization_r15
- **주장** 「−60° 에서는 반송파 몫이 -8.31 dB 로 내려앉아 «전체 대비» 몫이 혼자 뛴다」 (절 2 결과 5); 「우리 팔의 반송파 몫은 −60° 를 뺀 여섯 점에서 -1.82 dB ~ -3.35 dB 안에 있다 … −60° 가 그 자리다 — 반송파 몫이 -8.31 dB 로 내려앉고, 전체 대비 추적 몫 -6.21 dB 가 우리 팔 여섯 점 중 가장 커진다」; 「반송파 기준으로 재면 −60° 는 +2.10 dB 로 우리 팔 여섯 점 중 유일한 양수가 되어 오히려 더 튄다」; 「이 내려앉음은 우리 팔 한 칸의 성질이다」
- **냄새** a difference smaller than the run-to-run (grid-realization) spread being reported as a difference; a conclusion that would flip if a free parameter were nudged
- **왜 인공물인가** The whole «−60° carrier null» sub-section rests on one cell whose value is set by the λ/12 ray-grid realization, not by the geometry. Refining the frozen grid to λ/24 — the only nuisance axis available at this elevation, same target, same poses, same range, n_missing=0 — moves carrier_share at el−60 by +4.19 dB while moving it by ≤0.39 dB at all five other elevations. So ~4 dB of the ~5–6 dB «drop» is grid, and what remains (−4.12 dB against a −1.79…−3.74 dB band) is a 0.4 dB outlier, not a null. Both downstream statements invert at λ/24: the largest total-referenced track share moves from el−
- **직접 돌린 검산** Recomputed build_ch1_elevation_figs.py's carrier_share_db (DC bin / total, 8192-pt Hann FFT) and share_track_db from outputs/elevation_sweep_md.npz. ours_r15_n8192 (λ/12) el 0/−15/−30/−45/−60/−75 carrier_share: −1.89 / −1.82 / −3.35 / −2.48 / −8.31 / −2.17 (reproduces ledger). ours_r15_n8192_div24 (λ/24): −1.97 / −1.79 / −3.74 / −2.23 / −4.12 / −2.17. Per-elevation Δ(λ/24 − λ/12): −0.08 / +0.03 / −0.39 / +0.25 / +4.1
- ⭐**고칠 문장** 절 2 should stop treating the el−60 carrier share as a measured property and tag it as grid-limited. Concretely:  - Result 5 (cell 25) and cell 38: replace "−60° 에서는 반송파 몫이 -8.31 dB 로 내려앉아 «전체 대비» 몫이 혼자 뛴다" with something like: "λ/12 판에서 −60° 의 반송파 몫은 -8.31 dB 로 다른 여섯 점(-1.82 ~ -3.35 dB)에서 떨어져 나온다. 그런데 같은 팔·같은 자세·같은 거리에서 격자만 λ/24 로 조이면(`ours_r15_n8192_div24`, n_missing=0) 그 값이 -4.12 dB 로 +4.19 dB 움직인다 — 나머지 다섯 점에서 같은 조임이 만드는 이동은 0.39 dB 이하이고, 같은 λ/12 격자를 반 칸 옮긴 `shift0.5` 팔에서도 0.81 dB 이하다. 즉 이 «내려앉음» 은 격자 실현에 매달려 있어 **판정 불가**다."  - cell 38's ranking claim must go or be qualified: at λ/24 the la
- 확신도 high

### `06_4_sampling.ipynb` — 2 건 (살아 있음 2)

#### 🟠 serious · **지금도 인용됨**

- **자리** 셀 1 «거리 — 벽인가 예산인가», §1 비용표 + «정본 서술» 문단 (builder src/make_report08_microdoppler.py:1420-1443)
- **주장** ⭐ 그러므로 원거리 마이크로도플러에서 팔을 고르는 잣대는 **예산**이다 — 40 m 규칙 예산에서 PathSolver 는 자세당 0.495 s 로 우리 팔(0.635 s) 아래에 있고 ... (표 머리: ⭐ **비용을 두 팔에서 실제로 쟀다** — 아래는 자세당 벽시계 초다. 세 원장이 같은 판이라 바로 견줄 수 있다)
- **냄새** a difference smaller than the RUN-TO-RUN SPREAD being reported as a difference; a conclusion that would flip if a free parameter were nudged
- **왜 인공물인가** The two arms were timed under different concurrency regimes, and the report only checked that the *configurations* matched (drone/az/el/fc/PRF/n=4096). The S-arm 3 m and 15 m entries come from report07_three_engine_ranges.py, a single unsharded process (seconds = one time.time() span, no --shard option); the B-arm entries come from an 8-way sharded run of deck_ours_by_range.py whose cpu_seconds is sum(shard secs). Opening outputs/ours_range_shards/*.npz shows the 8 B-arm shards — each doing 512 poses of provably identical work (grid_ref frozen, so _grid_for/_ray_grid are identical and range_m 
- **직접 돌린 검산** Per-shard s/pose from outputs/ours_range_shards (secs / idx.size): R3 min 0.2567 max 0.9268 (3.61x, CV 51.3%, mean 0.6006); R15 0.2230-0.7553 (3.39x, CV 51.7%, mean 0.5115); R40 0.3690-0.9263 (2.51x, CV 43.4%, mean 0.6347). S arm 40 m 178M seed1 shards: 0.4555 0.4479 0.4585 0.6002 0.4585 0.4653 0.4657 0.6059 -> ledger 0.4947. Uncontended-subset comparison at 40 m: B 0.3784 vs S 0.4586 s/pose -> ordering FLIPS. Cited 
- ⭐**고칠 문장** The 40 m rule-budget clause of the ⭐ verdict should be withdrawn or demoted; the budget-ladder clause should be kept and is the real result. Suggested replacement text and table caveat:  ⚠ 이 표의 초는 **같은 부하 조건에서 잰 것이 아니다.** S 팔 3 · 15 m 는 샤드 없이 한 프로세스가 잰 벽시계이고(`report07_three_engine_ranges.py`), S 팔 40 m 와 B 팔 세 칸은 모두 **8 샤드 동시 실행의 초를 더한 값**이다 — 그래서 "자세당 벽시계 초" 가 아니라 "자세당 샤드 초 합" 이다. B 팔 40 m 는 샤드마다 0.369~0.926 s/자세로 **2.5 배** 흔들리고(3 m 3.6 배 · 15 m 3.4 배), 같은 실행의 S 팔은 0.448~0.606 s(1.35 배)로 훨씬 조용하다. **더 결정적인 것은 B 팔 자체다** — 우리 커널은 격자를 얼려 두어 자세당 일이 거리와 무관한데(`range_m` 은 rcs_sbr.py 의 위상 한 줄만 바꾼다) 원장
- 확신도 high

#### 🟡 minor · **지금도 인용됨**

- **자리** 셀 1 «거리 — 벽인가 예산인가», «정본 서술» 문단 마지막 문장
- **주장** 우리 팔은 3 → 40 m 를 0.512~0.635 s 폭 안에서 돈다
- **냄새** a metric whose value is set by the measurement harness rather than the signal (run-to-run spread reported as a measured band)
- **왜 인공물인가** Presented as the measured range behaviour of our kernel, but the kernel's per-pose work is range-independent by construction: deck_ours_by_range.py builds grid_ref once from the pose union and passes it to every sbr_field call, so _grid_for returns the same (ctr, Rout, n), the ray grid is identical, and range_m changes only the value inside one exp() (rcs_sbr.py:1183-1187). The three numbers should be equal; the 0.123 s 폭 is pure scheduling noise, and it is smaller than the scatter among the 8 shards inside any single one of those three runs. The band is also non-monotonic in range (3 m 0.601 
- **직접 돌린 검산** Ledger values 2460.2/4096 = 0.6006, 2095.2/4096 = 0.5115, 2599.9/4096 = 0.6347 s/pose. Between-range spread max-min = 0.1232 s. Within-range shard spread at 15 m = 0.7553-0.2230 = 0.5323 s, i.e. 4.3x larger than the band being quoted.
- ⭐**고칠 문장** In 셀 1 «거리 — 벽인가 예산인가», replace the last sentence of the «정본 서술» paragraph — "우리 팔은 3 → 40 m 를 0.512~0.635 s 폭 안에서 돈다" — with the structural statement plus the noise caveat the project's own RETRACTION_LOG R26 already carries:  "우리 팔은 거리에 비용이 안 걸린다 — 구조로 그렇다. 얼린 격자 한 벌을 세 거리가 그대로 쓰므로 `_grid_for` 가 돌려주는 (ctr, Rout, n) 이 셋 다 같고(ctr 동일 · Rout 0.44215 m · 한 변 124 칸), `range_m` 은 exp() 안의 값 하나만 바꾼다 — 자세당 연산 수가 같다. 자세당 ≈0.6 s 한 수로 인용한다. ⚠ 원장의 0.601 / 0.512 / 0.635 s 는 거리의 함수가 아니라 그날 기계의 함수다. 그 폭 0.123 s 는 잡음이다 — 같은 거리 안에서 8 샤드(각 자세 512, 비용이 같은 자세들)의 자세당 초가 15 m 에서 0.223~0.755 s 로 흩어져 그 폭의 4.3 배다. 세 
- 확신도 high

### `07_illuminators.ipynb` — 2 건 (살아 있음 0)

#### 🟠 serious · 이미 사문화

- **자리** 절 6 «검출기가 실제로 쓰는 커널 그대로 모호함수를 그렸다» — 결과 4 (cell 50), «부엽과 도플러 레플리카» 표 (cell 55), 그림 7(a) report03_f7_af_sidelobe
- **주장** 「부엽과 ±PRF 레플리카는 표준마다 다르다 — 2D 부엽 최대가 LTE -5.3 [^83] · 5G -18.0 dB [^84] 이고」 / 표: WiFi VHT-LTF -14.3 dB, LTE CRS -5.3 dB, 5G SSB -18.0 dB, 그리고 「부엽은 강한 표적이 평면 다른 곳의 약한 표적을 덮는 정도이고」
- **냄새** a metric whose value is set by a window length / axis extent rather than the signal — 그리고 그 창을 바꾸면 결론(표준 간 순위)이 뒤집힌다
- **왜 인공물인가** 인용된 psl_2d_db 는 프레임 전체(순환 지연축 ±150 km)에서 잡은 전역 최대 부엽이다. 그 최대를 만드는 봉우리는 WiFi 가 Rb=±959.3 m, LTE 가 Rb=±6655.5 m 에 있다. 그런데 검출기의 RD 맵 거리축은 benchmark/geometry.py:143 RB_WINDOW_M=60.0 → chamber_window() → src/passive_process.py:141 의 RP=RP[:, :n_range] 로 Rb∈[0,60) m 뿐이다. 즉 리포트가 '강한 표적이 약한 표적을 덮는 정도'라고 설명한 그 봉우리는 검출기 화면에 존재하지 않는다. 값도 순위도 지연축을 어디까지 열었느냐가 정한다. 같은 원장에 검출기 창 안 값 psl_chamber_db 가 이미 계산되어 있고, verify_ambiguity.py:281 의 저자 주석이 '전역 PSL/ISL 은 km 단위 지연축까지 적분하므로 검출기가 보는 값이 아니다'라고 직접 경고하는데 빌더(src/build_part08_illuminators.py:615,670)가 전역값을 집어 왔다. 같은 그림에 함께 그려진 isl_2d_db 도 동일 문제다(LTE +4.16 dB vs 챔
- **직접 돌린 검산** 각 기준 프레임(run_min_cell.frame_len 규약)의 zero-Doppler 순환 자기상관을 재계산: 전역 PSL = WiFi -14.33 dB @ Rb=+959.3 m, LTE -5.31 dB @ Rb=+6655.5 m, 5G -18.00 dB @ Rb=+61.0 m (원장 psl_2d_db 와 소수 둘째 자리까지 일치). 같은 곡선을 |Rb|<=60 m 로 자르면 WiFi -23.39 dB @ 7.5 m, LTE -14.96 dB @ 39.0 m, 5G -18.30 dB @ 58.6 m (원장 psl_chamber_db 와 일치). 순위 역전: 보고값은 LTE 가 5G 보다 12.69 dB 나쁨, 검출기 창 안에서는 LTE 가 5G 보다 3.33 dB 좋음.
- ⭐**고칠 문장** 절 6 의 결과 4 와 «부엽과 도플러 레플리카» 표·그림 7(a) 는 전역 psl_2d_db / isl_2d_db 대신 같은 원장의 psl_chamber_db / isl_chamber_db 를 써야 한다.  결과 4 는 이렇게 되어야 한다: "부엽과 ±PRF 레플리카는 표준마다 다르다 — 검출기 거리창(Rb∈[0,60) m) 안의 2D 부엽 최대가 LTE -15.0 · 5G -18.3 dB 이고, 레플리카는 WiFi -0.00 · LTE -23.27 dB 다."  표는 2D 부엽 최대 열을 WiFi -23.4 dB · LTE -15.0 dB · 5G -18.3 dB 로 고쳐야 하고, 그림 7(a) 의 두 막대도 챔버창 값으로 다시 그려야 한다(ISL: WiFi -13.0 · LTE -12.4 · 5G -22.9 dB).  전역값을 굳이 함께 싣는다면 방법 표에 한 줄이 필요하다: "인용한 PSL/ISL 은 프레임 전체 순환 지연축(WiFi·LTE ±149.9 km, 5G ±74.9 km)에서 잡은 값이다. 검출기 RD 맵의 거리축은 `benchmark/geometry.py:143` RB_WINDOW_M=60.0 → `src/passive_process.py
- 확신도 high

#### 🟠 serious · 이미 사문화

- **자리** 절 6 «검출기가 실제로 쓰는 커널 그대로 모호함수를 그렸다» — 결과 2 (cell 50), «주엽 — 닫힌형과 대조» (cell 53), 그림 6
- **주장** 「거리 주엽은 $c/B_{ref}$ 예측의 89% [^79] (WiFi) · 92% [^80] (LTE) · 94% [^81] (5G) 다」 (그림 6 캡션: 「측정한 모호함수 주엽이 닫힌형 예측과 몇 % 안에서 맞는가?」)
- **냄새** a number that looks like a measurement-vs-theory residual but is set by the WIDTH DEFINITION (-3 dB vs first-null) — 규약을 맞추면 잔차의 부호와 세 표준의 순위가 모두 뒤집힌다
- **왜 인공물인가** 분자 dR_meas 는 benchmark/verify_ambiguity.py 의 _half_width() 가 재는 -3 dB 전폭이고, 분모 dR_theory = c/B_ref 는 첫 널(Rayleigh) 규약이다 — 절 4 가 교과서 모노스태틱 c/2B 와 2배로 짝지은 바로 그 규약. 이상적 평탄 스펙트럼이면 이 비는 항상 0.8859 이므로, 보고된 89~94% 중 88.6%p 는 파형이 아니라 폭의 정의가 낳은 상수다. 노트북 본문 어디에도 '-3 dB' 라는 말이 없어 독자는 이를 복원할 수 없고, '측정이 닫힌형보다 6~11% 좁다 / 5G 가 가장 잘 맞는다'로 읽게 된다. 같은 원장의 널 기준 대조(range_null_m)를 쓰면 결론이 반대다.
- **직접 돌린 검산** |sinc(x)| 의 -3 dB 전폭을 수치로 계산: 0.885894 × (c/B). 원장 값 dR_meas/dR_theory = 0.8950(WiFi) / 0.9196(LTE) / 0.9416(5G) → 정의 상수 0.8859 를 뺀 파형 고유분은 +1.0% / +3.8% / +6.3% 뿐. 규약을 맞춘 대조 range_null_m/dR_theory_m = 3.950/3.916=1.0088, 18.000/16.669=1.0798, 46.450/41.638=1.1156 (셋 다 range_null_found=true) → 측정 주엽은 닫힌형보다 넓고, 5G 가 가장 크게 어긋난다(+11.6%).
- ⭐**고칠 문장** 셀 50 결과 2 / 셀 53 / 그림 6 캡션을 규약을 밝힌 형태로 바꾼다. 예:  「거리 주엽의 **-3 dB 전폭**은 $c/B_{ref}$ 의 89%(WiFi) · 92%(LTE) · 94%(5G) 다 — 다만 **이 88.6% 는 파형이 아니라 폭의 정의가 낳는 상수다**. $c/B_{ref}$ 는 첫 널 간격(절 4 규약)이고 측정값은 -3 dB 전폭이라, 스펙트럼이 완전히 평탄한 이상적 파형도 이 눈금에서는 0.8859(=|sinc| 의 -3 dB 전폭)로 읽힌다. 정의를 빼면 파형 고유분은 +1.0% · +3.8% · +6.3% 뿐이다.  규약을 맞춰 **첫 널끼리** 대조하면(같은 원장 `range_null_m`, 세 경우 모두 `range_null_found=true`) 3.95/3.92 = 1.009 · 18.00/16.67 = 1.080 · 46.45/41.64 = 1.116 이다 — 측정 주엽은 닫힌형보다 **넓고**, 5G SSB 가 +11.6% 로 가장 크게 어긋난다. 즉 «측정이 닫힌형보다 좁다 · 5G 가 가장 잘 맞는다» 가 아니라 «측정이 닫힌형보다 넓다 · 5G 가 가장 크게 어긋난다» 이며, 그 초과분은 $B_{ref}$
- 확신도 high

### `02_kernel.ipynb` — 1 건 (살아 있음 1)

#### 🟠 serious · **지금도 인용됨**

- **자리** 절 1, 「얼리면 무엇이 오고 무엇을 잃나」 (cell 12); 같은 수치가 절 1 결과 5 (cell 2) 를 뒷받침한다. 각주 [^47]~[^53], outputs/outofband_power.json convergence.*.slope_ge12
- **주장** 「div ≥ 12 에서 잰 기울기가 생산 -0.56 (R² 0.946) · 위상고정 -2.33 (R² 0.848) · 얼림 -2.19 (R² 0.998) 다 — 예측 위에 서는 것은 위상고정과 얼림 둘이고」 (예측 기울기 ≈ −2)
- **냄새** a trend that only exists because a SWEEP WAS CUT at a particular endpoint (here the LOW end: div=8 dropped from the fit) — compounded by a fit whose confidence interval spans zero
- **왜 인공물인가** The ladder actually sampled is DIVS=[8,12,16,24,32] and the same ledger already stores the full-ladder fit right next to the quoted one (convergence.prod.slope_full = -2.2045, phase.slope_full = -3.8492, froz.slope_full = -2.2122). Restricting the fit to div≥12 is what produces the per-arm verdict: with the full ladder the PRODUCTION arm sits at -2.205, i.e. exactly on the −2 d² prediction, and the PHASE-FIXED arm sits at -3.85, further from −2 than production's own ge12 value. Nothing in benchmark/ledger_outofband_power.py:407 (`ge12 = [d for d in DIVS if d >= 12]`) justifies dropping div=8; 
- **직접 돌린 검산** Refit the log-log slope of convergence.<arm>.P_out_per_div over every contiguous window of the sampled ladder, plus t-based 95% CIs on the ge12 fit (n=4). prod: ge8 -2.205 (R²0.671) / ge12 -0.560 (R²0.946) / ge16 -0.713 (R²0.999) / 8–24 -2.869. phase: ge8 -3.849 / ge12 -2.330 / ge16 -3.273 / 8–24 -4.004. froz: ge8 -2.212 (R²0.999) / ge12 -2.191 / ge16 -2.093 / 8–24 -2.268. 95% CI on ge12: prod -0.97..-0.15 (excludes 
- ⭐**고칠 문장** 절 1 「얼리면 무엇이 오고 무엇을 잃나」(cell 12)의 해당 문장을, 창을 고른 결과가 아니라 창에 무관한 것만 남기도록 고쳐 쓴다.  지금 문장: 「div ≥ 12 에서 잰 기울기가 생산 -0.56 (R² 0.946) · 위상고정 -2.33 (R² 0.848) · 얼림 -2.19 (R² 0.998) 다 — 예측 위에 서는 것은 위상고정과 얼림 둘이고, 얼린 팔이 적합도와 절대 바닥에서 앞선다.」  고친 문장(제안): 「⭐ 격자 사다리 다섯 칸(λ/8 · λ/12 · λ/16 · λ/24 · λ/32)의 세 팔을 예측 기울기 ≈ −2 에 맞대면, **예측 위에 서는 것은 얼린 팔 하나뿐이다.** 얼린 팔은 사다리 전체에서 -2.21 (R² 0.999) 이고, 칸을 하나씩 빼도 -2.19 ~ -2.27 (폭 0.08), 이웃칸 국소 기울기도 -1.94 ~ -2.44 (폭 0.50) 안에 머문다 — 어느 창으로 잘라도 같은 지수가 나온다. 나머지 두 팔에는 **지수라고 부를 것이 없다.** 생산 팔의 국소 기울기는 -7.52 → -0.12 → -0.68 → -0.76 이고 위상고정 팔은 -9.49 → +0.01 → -2.11 → -5.11 이라, 하나의 멱
- 확신도 high

### `06_5_bistatic.ipynb` — 1 건 (살아 있음 0)

#### 🟠 serious · 이미 사문화

- **자리** 절 4 «플래시 — 주기는 로터가, 시각은 방위가 정한다» (cell 7), the ⭐ block under the flash table; the same two numbers also appear in that table's «도플러 축척 — 순수 PO 팔» column, in 절 1's 실측 column, and in the 모노↔바이스태틱 대조표 row «도플러 축척 (실측)» (cel
- **주장** ⭐ 표를 가로로 읽지 말고 두 세로줄을 비교하라. · `el60` — 도플러는 0.891 로 이미 11 % 줄었는데 플래시열은 상관 0.986 로 제자리다. · `az60` — 도플러는 거의 그대로(0.983)인데 플래시열 상관은 0.494 로 무너진다. 두 칸의 β 는 같다. 다른 것은 이등분선의 방위가 돌았는가 뿐이다.
- **냄새** a conclusion that would flip if a free parameter were nudged; a difference smaller than the estimator's own spread reported as a difference
- **왜 인공물인가** The two Doppler numbers come from `inst_max_doppler` (benchmark/report07b_bistatic_md.py:216), whose free parameter `drop_db` is hard-set to 20. I re-ran that exact estimator on outputs/report07b_bistatic_md.npz['E_po'] for drop_db = 12..28 dB. az60 and el60 return IDENTICAL ratios at 12,13,14,15,16,17,18 dB (0.890, 0.890, 0.882, 0.882, 0.891, 0.891, 0.891) and again at 23-28 dB (0.908/0.900, 0.908/0.908, 0.908/0.901, ...). Only in the narrow 19-21 dB window does az60 step one staircase notch ahead (0.983/0.992) while el60 stays at 0.891 — and at 22 dB el60 jumps too (0.992 vs 0.983). The repo
- **직접 돌린 검산** Re-ran md_mapstyle.ridge_spec + the inst_max_doppler recipe on outputs/report07b_bistatic_md.npz['E_po'] with drop_db swept 12..28 dB. az60 / el60 ratios: 12dB 0.890/0.890, 14dB 0.882/0.882, 17dB 0.891/0.891, 19dB 0.983/0.891, 20dB 0.983/0.891 (as reported), 22dB 0.992/0.983, 25dB 0.908/0.901, 28dB 0.908/0.908. Ledger's own po_ratio_lo (25 dB) / po_ratio_hi (15 dB) confirm: az60 0.9084/0.8824 vs el60 0.9008/0.8824. B
- ⭐**고칠 문장** The 절 4 ⭐ bullet should drop the Doppler contrast and rest on the flash column alone, because the flash column is what is actually robust here. Something like:  ⭐ 표를 가로로 읽지 말고 두 세로줄을 비교하라. · `az60` 과 `el60` 은 β 가 같고, 도플러 축척도 임계값에 강건한 범위에서는 **같다**(±5 dB 를 흔들면 15 dB 에서 둘 다 0.882, 25 dB 에서 0.908 대 0.901). 그런데 플래시열 상관은 az60 0.494 대 el60 0.986 으로 갈린다. · 즉 **도플러가 같은데 플래시가 갈린다** — 다른 것은 이등분선의 방위가 돌았는가 뿐이다. ⚠ 표의 «도플러 축척» 열 자체는 임계값에 민감하다. 이 추정기의 자유 파라미터 `drop_db` 를 12~33 dB 로 흔들면 az60 과 el60 의 값은 대부분의 임계값에서 **완전히 같고**(12~18, 24, 28~33 dB), 19~21 dB 의 좁은 창에서만 az60 이 계단 한 칸 앞선다. 표의 0.983 대 0.891 은 그 창 안의
- 확신도 high

### `08_2_two_channel.ipynb` — 1 건 (살아 있음 0)

#### 🟠 serious · 이미 사문화

- **자리** 절 5 (cell 11) — 「팔 | 플래시 선 세기」 table and the ⭐ paragraph under it; repeated in 절 7 (cell 13) 세 문장으로 #3
- **주장** 「플래시 선은 85.3 → 32.5 → 24.4 dB 로 모두 60.9 dB 내려가는데, 그 중 52.8 dB 가 첫 칸에서 빠진다 … 여유를 잃는 속도는 빗살 쪽이 훨씬 빠르다」 and the §5 table rows `ideal` 85.3 dB / `refSNR+20dB` 32.5 dB / `refSNR+10dB` 24.4 dB / `MDR-20dB` 85.2 dB / `noECA` 77.2 dB, repeated in §7 sentence 3 as 「Pd 가 0.00 인 한 칸에서 빗살 선은 아직 배경보다 24.4 dB 위에 있었다 — 다만 이상 팔의 85.3 
- **냄새** a metric whose value is set by a WINDOW LENGTH, BIN WIDTH, or FFT SIZE rather than the signal; a ratio that is large because the DENOMINATOR is tiny/degenerate
- **왜 인공물인가** flash_line_db = 10log10(peak at f_flash / median(Sx[1:])) where Sx is the rfft of the tip-band power time series (md_metrics, passive_two_channel_md.py:594-606). That series is produced by a sliding STFT of nper=68 frames with hop=2 (md_mapstyle.FLASH_HOP, commented 「겹침 — 시간 슬롯을 촘촘히」, a display convention). The window admits modulation only up to prf/nper = 282.8 Hz, but the series is sampled at prf/hop = 9615 Hz, so the rfft runs to 4808 Hz and only 55 of 945 bins (5.8%) lie inside the window's passband. The 'background median' is therefore 94% out-of-band bins where nothing can exist by cons
- **직접 돌린 검산** Reproduced the ledger exactly from outputs/passive_two_channel.npz (e2_wifi__*__S): line_all = 85.28 / 32.47 / 24.38 / 85.18 / 77.21 dB for ideal / refSNR+20dB / refSNR+10dB / MDR-20dB / noECA, matching md_survival to 2 dp. Split the background median by frequency: medALL / medIN(<=282.8 Hz) / medOUT(>565.6 Hz) = 7.13e15 / 3.16e22 / 5.03e15 (ideal), 3.02e21 / 1.36e24 / 2.44e21 (refSNR+20dB), 1.49e24 / 5.66e25 / 1.23e
- ⭐**고칠 문장** §5 and §7 should not quote `flash_line_db` as a comb-vs-background margin in dB, because at the house hop=2 setting 94% of the bins in its background median lie outside what the nper=68 STFT window can pass, so the denominator is a window leakage skirt for the clean arms (ideal: -73.7 dB at 2264-4808 Hz, still falling) and a genuine broadband floor for the noisy arms (refSNR+10dB: flat at -17.9 dB). The two ends of the ladder are normalised against floors of different origin.  Honest re-normalisation against the in-band background only (harmonics excluded, robust over cutoffs 0.5-2.0x BW) give
- 확신도 high

### `03_anchor.ipynb` — 1 건 (살아 있음 0)

#### 🟡 minor · 이미 사문화

- **자리** 절 1 · 결과 3-4, 모드 표, «세 인자, 각각의 출처» 표 (cells 2, 7, 9); footnotes [^16]-[^19]
- **주장** 3. 정렬 후 7 기종 기울기가 모두 0.210 dB/GHz 위에 서고, 기종 간 산포는 1.9e-15 dB/GHz 다.  4. 레벨이동 절대 최대는 0.00 dB, 재보정 후 정규화 각패턴 변화는 1.9e-15 dB 다 — 주파수 눈금만 측정에서 오고 레벨과 모양은 그대로다.
- **냄새** a quantity pinned at the numerical floor so the 'law' is an identity, not a measurement (Worked Example 2)
- **왜 인공물인가** slope_only in src/sigma_anchor.py sets target = mu_anchor + (mean(mu_our) - mean(mu_anchor)), and anchor_mu_dbsm returns exactly a*f + b + (a scalar convention offset). So (i) the post-alignment slope is identically the anchor slope 0.21 for every airframe, (ii) mean(delta) is identically 0, and (iii) sigma_corr = sigma * scalar, so the normalized angular pattern is bitwise unchanged. All three quoted numbers are float round-off, not agreement across 7 airframes. The ledger itself says so — outputs/report02_derived.json anchor_modes.definition reads «slope_only 는 밴드 비가중 평균 레벨을 축으로 회전만 시키므로 이 값
- **직접 돌린 검산** Confirmed the ledger values (7 airframes: slope_after = 0.209999999999998..0.210000000000000, mean(delta) = 0..4.7e-15, shape_invariance 9.6e-16..1.9e-15). Then imported src/sigma_anchor and ran the same pivot formula on 5 sets of RANDOM mu_our (rng.normal(-25, 8, 3), nothing to do with any airframe, input slopes +1.236 / +0.629 / -4.786 / +3.105 / +2.525 dB/GHz): every one returned slope_after = 0.209999999999995..0
- ⭐**고칠 문장** 절 1 결과 3-4 와 «세 인자, 각각의 출처» 표에 «정의상» 을 명시하고, 기체 간 실제 차이는 정렬 **전** 값에 있다고 적는다.  결과 3 (고쳐 쓴 안): 「slope_only 는 각 기체의 밴드 비가중 평균 레벨을 축으로 회전만 시키므로, 정렬 후 7 기종 기울기는 **정의상** 앵커 기울기 0.210 dB/GHz 와 같아진다 — 산포 1.9e-15 dB/GHz 는 기체 간 일치가 아니라 부동소수 반올림이다. 기체 간 실제 차이는 정렬 **전** 기울기 +0.742 (x500v2) ~ +1.699 dB/GHz (phantom4) 에 있다.」  결과 4 (고쳐 쓴 안): 「slope_only 는 밴드 비가중 평균 레벨을 보존하는 밴드별 스칼라 곱이므로, 세 밴드 **평균** 레벨이동은 정의상 0 이고(밴드별 이동은 -2.41 ~ +2.70 dB 로 0 이 아니다), 스칼라 곱은 정규화 각패턴을 바꾸지 않는다. 표의 0.00 dB · 1.9e-15 dB 는 그 설계가 코드에서 실제로 지켜졌는지의 **구현 검산값**이지, 레벨과 모양이 우리 커널에서 온다는 것의 관측 증거가 아니다 — 그것은 앵커 모드의 설계다.」  «세 인자, 각각의 출처» 표 (
- 확신도 high

### `11_measurement.ipynb` — 1 건 (살아 있음 1)

#### 🟡 minor · **지금도 인용됨**

- **자리** 절 3 «대역별 점표적 조건» 표
- **주장** 대역별 점표적 조건 표: 400 MHz 행에서 Mini 5 Pro 「⚠ 퍼짐」, 여유 -0.001 m
- **냄새** a conclusion that would flip if a free parameter were nudged — a 1.2 mm margin decided by a stale mesh generation; the report prints two different values for the same defined quantity
- **왜 인공물인가** The 400 MHz verdict for mini5pro rests on a 1.24 mm margin (0.33% of D_bbox). measurement_plan.json (07-30 generation) gives D_bbox = 0.37598 m, but measurement_layers.json — used by §5 of this same notebook for the identical 'bbox = 프로펠러 포함 수평 최대치수' definition — gives 0.36042 m, which flips the cell to 점표적 with +14.3 mm. measurement_layers.json : stale_table_drift documents the 07-31 mesh reorganisation and instructs that the 07-30 generation be noted whenever these numbers are printed; the notebook carries the 2026-08-04 CAD caveat but not this one, and prints matrice4e D_bbox as 0.5993 in §
- **직접 돌린 검산** c/(2*400e6) = 0.374741 m. With D_bbox = 0.3759833 (measurement_plan) margin = -0.001243 m -> '⚠ 퍼짐'; with D_bbox = 0.3604240 (measurement_layers, current mesh) margin = +0.014317 m -> '점표적'. stale_table_drift.rows.mini5pro: printed 0.376 -> current 0.360424, delta -15.58 mm; matrice4e printed 0.5993 -> current 0.59474, delta -4.56 mm.
- ⭐**고칠 문장** Two edits, both confined to what the ledgers already record.  1. §3 «대역별 점표적 조건» — add a caveat under the table (matching the style §7 already uses):     ⚠ 이 표는 `measurement_plan.json` 07-30 생성(07-31 메쉬 개편 이전) 의 D_bbox 위에 있다. Mini 5 Pro 400 MHz 칸의 여유 -0.001 m 는 D_bbox 의 세대간 드리프트 -15.6 mm (`measurement_layers.json : stale_table_drift.rows.mini5pro.delta_mm`) 보다 훨씬 작아, 현재 메쉬(D_bbox = 0.360 m)로 다시 계산하면 +0.014 m 로 뒤집혀 «점표적» 이 된다. 두 기체를 함께 만족시키는 최대 서브밴드가 200 MHz 라는 결론은 Matrice 4E 가 정하므로(여유 -0.220 m, 세대와 무관) 바뀌지 않는다.     Alternatively, regenerate `measurement_plan.json` on the current mesh — but tha
- 확신도 high

## 3. 총평 (검증 요원)

# 과거 작업 검증 — 분류와 처방

## 1. 한 줄 진단

89건 제기 → **59건 확정, 30건 기각**(오경보 34%). 확정 59건 중 **49건이 아직 살아 있다**.

오염은 **넓지만 얕다**. 리포트 13편 중 12편에 흔적이 있지만, 대부분은 「결론의 방향은 맞고 **인쇄한 크기와 순위가 못 쓴다**」다. 재실험이 필요한 건 거의 없고 문장·표 수정이다. 결론 자체가 뒤집히는 것은 10건 남짓이며 **그중 절반이 어제·오늘 만든 `12_outdoor-scene` 한 편에 몰려 있다**.

걱정할 수준인가 — **한 편은 지금 멈춰야 하고, 나머지는 정정 작업이다.** 아카이브 전체를 의심할 상황은 아니다.

---

## 2. 살아 있는 것 (49건) — 심각도 순

### 티어 0 · 결론이 뒤집힌다 — 지금 멈춰라

**① `12_outdoor-scene.ipynb` 전체 (4건, 오늘 작업)**
자유공간 대비 「실외에서 박자가 사라진다(ρ +0.974 → +0.005)」와 「정지 클러터를 걷어내도 안 돌아온다」가 **둘 다 반대**다. 원인은 물리가 아니라 **솔버 낙차**: el −30 에서 8,192 자세 중 74개(0.90%), el −60 에서 92개(1.12%)가 한 자세만 지면·건물 에코를 통째로 잃고 다음 자세(50.8 µs 뒤)에 완전히 복구된다. 그 자세들이 AC 전력의 99%를 쥐고 있어 ρ를 0으로 끌어내린다. 낙차 자세의 |E|는 같은 자세의 **자유공간 값과 같고**, el −30 낙차 74개 중 57개가 el −60과 **같은 자세 번호**다 — 기하가 아니라 자세 인덱스에 걸린 버그다. 메우면 ρ +0.974 / +0.976, ECA 잔차와 자유공간의 상관 0.023 → 0.988.
→ **절 1·2의 결론 문장 전부 철회.** 살아남는 것은 레벨 상승(+53.6/+45.1 dB)과 절 3(격자 비용)뿐. 정직한 결론은 「박자가 사라졌다」가 아니라 「정지 지면 에코 아래 54 dB 묻혀 있고, 우리 잣대가 1% 낙차에 잡아먹혔다」. `benchmark/outdoor_scene_0901.py`에 자세별 |E|/중앙값 이상치 감사를 **잣대 계산 전에** 넣고 재생성.
→ 부수: 절 3 「2×2 m 조각 23배면 감당된다」도 틀렸다. 격자는 **합집합 bbox**로 정해지는데 정반사점이 드론에서 21.5 m 떨어져 있어 합치면 **~780배**(1,280만 점)다. 23배는 조각을 자기 원점에 홀로 놓은 값이다. 별편 12-2 설계는 이 문제부터.

**② `05_2_switch-grid.ipynb` 깊이 축 −60° (fatal)**
「바닥 +12.7 dB · 리듬 −54.3 %p」는 **자세 #3399 하나**가 만든다(|E−평균|이 중앙값의 20.1배, 둘째는 2.89배). 그 자세만 이웃 평균으로 바꾸면 깊이 3이 깊이 1과 붙는다. **이건 2026-08-16에 `outputs/depth_axis_verdict_0816.json`이 이미 「철회」·「인용 금지」로 못 박은 숫자**이고 `docs/RESUME.md`에도 두 번 적혀 있는데, 08-24 노트북이 그대로 인쇄 중이다.
→ 셀 11 §2 삭제, 「13쌍 중 5쌍」→「4쌍」, 「깊이는 바닥을 올리는 축」 문장 삭제. **그리고 `docs/NEXT_EXPERIMENTS.md:509`의 R26 발주를 취소하라** — 철회된 숫자를 근거로 GPU를 사려던 참이다.

**③ `02_2_stock-engine.ipynb` §5·§6 (fatal + serious)**
「면 1→0 계단 −42.97 dB」·「붕괴폭 49.02 dB」의 마지막 단은 **정반사 경로가 0개**다. 그 값은 확산 켠 coh_db, 즉 **광선예산 바닥**이고 spp를 4e6→1.024e9로 바꾸면 29.9 dB 움직인다(스크립트 헤더 자신이 「√spp로 발산 — 알려진 인공물」). 「−6.05 dB = 20log₁₀(1/2)」는 잔차 5.5e-07 dB로 붙는데, 그건 물리가 아니라 **image-method 중복 경로**다(인코히어런트 전력도 정확히 3.010 dB 차, 위상차 상한 0.04°).
→ 두 숫자 삭제. **`outputs/facet_attack.json`(08-03)이 이미 두 숫자를 must_not_say에 올려 뒀다** — 노트북(08-24)이 자기 적대검증 원장을 지나쳤다. Z4 결론(「스톡 정반사로는 메쉬 예산 못 잰다」)은 **오히려 강해진다**.

**④ `06_6_microdoppler-limits.ipynb` 가림 dB (fatal)**
`occlusion_ptp_db`는 max−min이라 **표본수에 상한이 없다**(n=100→35 dB, 6000→79 dB, 계속 상승). +23.19 dB는 6,000 자세 중 **가장 깊은 하나**가 18.5 dB를 낸 것이고, 깊은 5개만 빼면 +3.65, 10개 빼면 −0.41이다. 수렴하는 잣대(5-95 백분위·dB 표준편차·평균전력비) 전부에서 부호가 뒤집힌다.
→ p-p 열 폐기, 5-95 백분위(+0.12 / −1.65 / −1.85 dB)로 교체. 「세 자세가 다른 값을 낸다」도 못 쓴다 — 같은 기록 솎기만 해도 −20~+38 dB로 흩어진다. 남는 것은 「앙각 부호에 따라 가림 유무가 갈린다」까지. 같은 절의 「판 셋 흩어짐 26.52 dB」도 **150 자세(stride 40)에서 잰 값을 6,000 자세 표와 나란히 놓은 것**이라, 그 26.5 dB의 대부분이 판이 아니라 표본수다.

### 티어 1 · 크기·순위를 못 쓴다 (숫자 교체, 결론은 대체로 생존)

**격자/창을 안 흔들어 본 것 (11건)**
- `02_kernel` div≥12 기울기: **맨 아랫칸 λ/8을 뺐을 때만** 「위상고정과 얼림 둘이 예측 위」가 된다. 다섯 칸 중 다른 어느 칸을 빼도 −3.85~−4.33. 전체 사다리로는 생산 −2.20 · 얼림 −2.21이 −2에 가장 가깝고 위상고정 −3.85가 이상치 — **그룹이 정확히 반대**다. 남는 결론: 「얼린 팔만 d²로 수렴, 나머지 둘은 λ/12에서 꺾인다」.
- `04_elevation-coverage` 물리 상한 위 누설: λ/12 한 판이다. λ/24로 조이면 el −15에서 17.18%→4.63%로 **물리를 끈 PathSolver 아래로 내려가 순서가 뒤집힌다**. `outputs/grid_convergence_check.json`이 이미 「λ/12 한정 꼬리표 강제」를 발동해 뒀다. 꼬리표를 달고, 「두 자리」→「세 자리」(el −45도 있다).
- `10_results` CPI 배수 11.0~19.0배: 분모가 720점 헤딩 격자의 **2칸**이다. 72,000점으로 올리면 10.6~11.6배 상수 — **결론(「CPI로 안 없어진다」)이 오히려 깨끗해진다**. 같은 격자 문제로 패리티 CPI 1.00 s → 1.06 s, 10.00배 → 10.6배, 「20 m/s까지」 → 「15 m/s까지」, 「16칸 중 8칸」 → 7칸.
- `06_3_pattern` 창 길이 0.505 s · 분해능 1.98 Hz: `MAX_SAMPLES = 6000` 상한에 걸려 실제 창은 **0.305 s · 3.28 Hz · 374칸**이다(요청은 9,954 표본). 6000/19700 ≠ 0.505 s — 표의 네 수가 서로 안 맞는다. matrice4e 칸만 해당, mini5pro는 정상.
- `06_3_pattern` p-p 50.32 dB / 「9배」: 위 ④와 같은 병. p5~p95로 19.44 dB, 비는 8.0배. 세 엔진 표의 32.6 dB도 N에 수렴 안 한다(N=64→13.5, 4096→32.6, 여전히 배증마다 +5.5 dB). **자매편 `06_2`는 같은 표를 p5~p95 열과 경고와 함께 인쇄한다 — 생성기만 갈아 끼우면 된다**(`build_part07_microdoppler.py:467`).
- `03_2_size-law` 62.0~100.8 dB 「메쉬 − 구」: 구 잔차는 **경도 분할 수의 별칭**이고, 인용 폭 38.8 dB의 100%가 바닥의 이동이다(메쉬는 0.06 dB만 움직인다). 분할 4배면 +16~41 dB. 그리고 그 폭이 「방위 극값까지 펴서」가 **아니다** — 12행은 이미 24방위 평균이고, 넓어진 축은 **대역(3.5↔15.86 GHz)과 파면**이다. 절 자신의 규약(3.5 GHz·구면파)으로 자르면 62~77 dB.
- `03_2_size-law` 낭떠러지 −54.44 / −56.48 dB: 회전대칭 원판의 참 변조는 0이므로 이건 **점밀도 바닥까지의 거리**다. 점을 4배 촘촘히 깔면 −72.9 / −89.9 dB(메쉬는 0.03 dB만 움직인다). 부호만 인용하고 「50 dB 대를 자릿수까지」는 삭제. 방향은 보수적이라 결론 무사.
- `02_3_target-mesh` m600 +1.80 dB: 우리 M600이 6회 대칭인데 방위 48칸(7.5°)이 60° 주기의 **대칭축 여섯 곳에 정확히 얹힌다** — 그 6칸이 우리 쪽 평균의 91.9%. 격자를 반칸 밀거나 4배 조이면 +1.8 dB가 사실상 사라진다. 세 값 다 소수 둘째 자리로 인용 금지(부트스트랩 SE 0.9/0.5/1.9 dB).
- `10_2_robustness` 지면반사 78%: 손으로 적은 27점 격자 계수(21/27)이고, **더 큰 손잡이는 대역**이다 — 400 MHz 게이팅이면 96%, 100 MHz면 48%. 그런데 실제 게이팅은 400 MHz다(`MEASUREMENT_PLAN` §1-7).
- `11_measurement` mini5pro 400 MHz 「⚠퍼짐」: 여유 −1.24 mm인데 D_bbox의 세대간 드리프트가 −15.6 mm다. 현재 메쉬로는 **점표적으로 뒤집힌다**. `stale_table_drift._rule`이 이미 「07-30 생성이라고 적어라」고 지시해 뒀다. 200 MHz 헤드라인은 matrice4e가 정하므로 무사.
- `06_4_sampling` 40 m 비용 0.495 vs 0.635 s: 두 팔을 **다른 동시실행 조건**에서 쟀다(S는 단일 프로세스, B는 8샤드 합). B 샤드끼리 2.5~3.6배 흔들리고, 덜 붐빈 샤드끼리 견주면 순서가 뒤집힌다. 살아남는 건 예산 축 하나 — 4,000M 발에서 6.5배(CV 0.5%). 「3→40 m를 0.512~0.635 s 폭」도 잡음이다 — 얼린 격자라 자세당 일이 거리와 무관하다.

**원장이 이미 경고했는데 안 옮긴 것 (별도 티어로 안 나눔 — 위아래 전반에 섞여 있다)**
- `06_2_engines` F↔G 가림 +1.31 / −4.79 dB: 판을 반 칸 옮기면 4.16 / 26.52 dB 흔들려 **부호까지 덮는다**. `report15b`의 `occlusion_plate_caveat_ko`와 자매편 `06_3`의 ⛔ 블록이 둘 다 이걸 적어 뒀는데 `06_2`만 맨 숫자를 싣는다. 생성기 `make_report08_microdoppler.py:905` 수정 필요.
- `06_2_engines` 「판의 위치에 둔하다(ρ 0.993, 0.006 dB)」: 비교한 두 판이 **한 칸의 1.5%**만 떨어져 있다. 반 칸 옮기면 ρ 0.819 · 1.41 dB. 이 항이 말하는 건 「봉투 선택이 결과를 안 바꾼다」이지 판 위치가 아니다. 세 줄 아래 「대가」 표가 이미 반대를 말하고 있어 자기모순이다.
- `01_map` PTD 비용 +47.2%: 원장 `D_cost.model`이 「설정 의존, +8~+154%」라고 적었고 100% util GPU에서 잰 벽시계다(짝 반복 중 켠 쪽이 더 빨랐던 판이 남아 있다). 밴드와 경합 주의를 달 것. PTD 행의 `결판` 지위는 무사.
- `01_map` 레벨 −4.91 / −3.30 dB: **앵커 전대역(1.8~18.2 GHz) 평균**인데 캠페인 창은 1.843~5.21 GHz다. 대역 안에서는 −5.78 / −5.16, 개선폭 1.61 → 0.62 dB. 옆 행의 기울기 문턱은 이미 밴드정합값을 쓰고 있다. 원장이 「전대역 평균이 구조를 감춘다」고 두 번 적었다.
- `10_2_robustness` M1 (2건): ⓐ 「+0.00 dB」는 **눈금 자체**다 — 동작점을 M1 위에 잡았으니 어떤 추정량으로도 0이고, 네 각주는 같은 항등식 하나다. p10에서 M1이 최악이 되는 것도 분산 0의 산술이다. ⓑ M1의 「평평함」은 3GPP가 아니라 우리 규약이다 — TR 38.901의 σ_S(3.74 dB)를 우리가 껐다. 켜면 **M3−M1이 7.52 → 3.02 dB**. `tm_attack.json`의 ⭐must_fix가 이 두 개를 이미 지목했는데 리포트는 같은 파일의 숫자만 20곳에서 인용했다.
- `02_3_target-mesh` Typhoon −0.40 dB: `compare_real_cad.py:ours_body_only()`가 **실물 STL의 bbox를 우리 메쉬에 덮어씌운다**(z를 48% 눌러서). 정합을 끄면 +2.5~3.9 dB — 셋 중 가장 좋은 일치가 가장 나쁜 일치가 된다. `docs/PRIOR_WORK_COMPARISON.md` §3이 이미 「독립 재현이 아니다」라고 적었다.
- `05_2_switch-grid` 원장 세대 불일치: `switch_grid.json`이 08-27에 **다섯 팔·깊이 2·정본 메쉬**로 다시 구워졌는데 노트북은 여덟 팔·깊이 1 표를 그대로 들고 있다. 인쇄된 여덟 개 h1 값 중 **하나도 그 파일에 없고**, V3 교차검증(0.04 %p)은 다시 돌리면 `KeyError`로 죽는다. 그림 네 장도 캡션과 안 맞는다(다섯 패널인데 「윗줄·아랫줄」).

**나머지 serious (짧게)**
- `02_3` σ를 「로브 위치」로 인용해도 된다는 ⭐ 허가 — 뒷받침 원장이 없고, 방위 격자(7.5°)가 로브 폭보다 넓어 애초에 못 잰다. 이웃칸 자기상관 −0.19~+0.11.
- `02_3` 자세별 RMS 5.2~10.0 dB — 두 메쉬 요각이 정합돼 있지 않다. Phantom 4·M600은 무작위 짝짓기 널의 83·81 백분위. Typhoon만 정합돼 있다.
- `05_2` 1차 선 8.17/8.46 dB — 이 잣대의 백색 귀무 중앙값이 8.13이다(p≈0.47). 봉우리가 넷 다 126.1 Hz인 것도 탐색창이 13칸이라서다. **결론은 2차 선(20.19/20.48 dB, 귀무 최댓값 12.07 밖)으로 살릴 수 있다**.
- `05_2` 담김계수 3σ — σ가 얹힌 항 크기에 비례해서, el −15는 3σ 띠가 |a|≤2.61까지 열려 있다(실측 a=1.96인데 통과). 잘 측정된 −60이 떨어지고 못 잰 −15가 통과한다.
- `08_detector` rd_offzero −164.8/−180.2 dB — float64 0이고, 마스크 폭 규약이 정한다(9행 전부 0-도플러와 정확히 42.52 dB 차 = np.hanning(48)의 ±2빈 부엽). 주기 Hann이면 −325 dB.
- `08_detector` 「두 항이 배율의 전부」 — 대조군 셋이 전부 `mode="noise"`라 운용 형상의 ×1.22(+0.87 dB, 초과의 47%)를 끄는 대조군이 없다. 원인은 ECA 노치 어깨(초과 히트 310 중 263이 |행−zd|≤8).
- `10_results` R90 — ψ=0이 φ=90°에서 **정확히 0-도플러 헤딩**이다(f_d ≈ 1e−4 Hz, 가드 15 Hz). 즉 15칸 전부가 검출기가 지우는 헤딩의 거리다. 같은 리프의 `E_psi_Pd_at_R90`이 5G 다섯 칸 전부 **0.0**. km 열은 도달거리이지 검출거리가 아니다.
- `10_results` 취약성 상관 −0.62 — **기각하는 쪽(크기, p=0.27/spearman p=0.037)이 채택하는 쪽(산포, −0.31, p=0.61)보다 강하다.** n=5. 자매편 `03_anchor`는 이미 세 상관을 다 싣고 「서술용」이라 적었다. 실제로 문턱을 정하는 건 총격차 최솟값(r=+0.99).
- `10_2` WiFi +0.21 dB — W1·W3는 기준신호·대역·프레임 수가 **전부 같다**. 움직인 건 데이터 점유뿐이고, 그게 결과에 들어오는 이유는 상관 기준이 **송신파형 전체**이기 때문이다. 그런데 `07_illuminators` §3은 「데이터 심볼은 템플릿이 못 된다」고 적어 뒀다 — 두 편의 규약이 충돌한다.

**minor (기록·문구만)**: `02_3` CAD 6.90%(정의 불일치 — 벤더 GLB 실측하면 916.96 vs 공표 917 mm, 0.005% 일치), `03_2` 7.99 dB 잣대(다른 양·다른 기체·12배열 최댓값), `03_2` 운동학 55~74%(분모가 절댓값 합), `06_2` −24.5 dB 잔차(시드·예산에 −6~−29 dB), `08_detector` 3 dB 문턱(M=48 고정이라 5G만 CPI 절반), `10_2` LTE +0.08 dB(시드 7개 재현 +0.011±0.010, 부호도 바뀜).

---

## 3. 이미 죽은 것 (10건) — 기록만

인용이 끊겼거나 값이 갱신돼 더 추적할 필요 없는 것들. **재작업 불필요, RETRACTION_LOG에 한 줄씩만.**

| 리포트 | 무엇 | 왜 죽었다고 보나 |
|---|---|---|
| `03_anchor` | slope_only 「7기종 산포 1.9e-15」 | 부동소수 반올림. 입력 무작위로 넣어도 같은 수 |
| `04_elevation` | −60° 반송파 −8.31 dB 「내려앉음」 | λ/24면 −4.12, 두 파생 문장이 뒤집힘 |
| `06_5_bistatic` | az60 도플러 0.983 vs el60 0.891 | drop_db 19~21 dB 창에서만 갈린다. 결론은 플래시 열로 더 강하게 선다 |
| `07_illuminators` | 2D 부엽 LTE −5.3 dB | 전역 ±150 km 지연축 값. 검출기 창(60 m) 안에서는 −15.0. ISL은 +4.16 → −12.44 |
| `07_illuminators` | 주엽 89/92/94% | −3 dB 폭 ÷ 첫 널 간격. 이상적 파형도 88.6%. 규약 맞추면 부호와 순위가 반대 |
| `08_2_two_channel` | 플래시 선 85.3 → 24.4 dB | 배경 중앙값의 94%가 STFT 창 통과대역 밖. hop 2→34면 85.3 → 18.5 |
| `09_observability` ×3 | 1RX 57.75 m / 천장 66.81 dB / 클램프 4.6~22.5% | 각각 pinv rcond, β게이트 첫 칸, 게이트 전 분모 |
| `09_observability` | LTE 자기 문턱 +0.047 dB | Wilson 구간이 겹친다. dopoff 칸 옮기면 부호 반전 |

⚠ **위치 정정**: 「06_1_scene.ipynb」로 접수된 3건은 그 파일에 없다. 실제로는 **`03_2_size-law.ipynb`** cells 16-18/22/28-29/35/38-39/41이다. 엉뚱한 파일 열지 마라.

---

## 4. 실수 패턴 — 이름 붙이기

다섯 개다. 빈도순.

**① 「자기 원장의 경고를 안 옮겼다」 — 49건 중 최소 18건.**
압도적 1위이고, **가장 고치기 쉽다.** `facet_attack.json`, `depth_axis_verdict_0816.json`, `grid_convergence_check.json`, `freeze_plate_sensitivity.json`, `tm_attack.json`, `ptd_wiring.json:D_cost.model`, `p3_validation.json:verdict`, `stale_table_drift._rule`, `docs/PRIOR_WORK_COMPARISON.md`, `docs/GRID_PHASE_NULL.md`, `RESUME.md:인용 금지`, 심지어 스크립트가 **stdout으로 찍는 경고**(`verify_observability.py:627`)와 소스 주석(`experiment_detection.py:117`)까지 — 전부 이미 존재한다. 숫자는 원장에서 주입하면서 **경고는 손으로 옮겨야 해서 안 옮겨진다.** 05_2는 자기 적대검증 원장보다 21일 뒤에 쓰였고, 02_2는 21일, 10_2는 must_fix를 20번 인용하면서 한 줄도 안 옮겼다.

**② 「자유 손잡이를 안 흔들었다」 — 최소 14건.**
격자(λ/12, 720점 ψ, 방위 48칸, div≥12, 27점, psi_n), 창(MAX_SAMPLES 6000, FLASH_HOP, nper, drop_db, rcond, fcut, 탐색창 13칸), 표본수(p-p가 n에 발산). 「메모리에 이미 있는 습관」인데 — **자기 실험의 축은 흔들면서, 잣대 안의 상수는 안 흔든다.**

**③ 「분모가 바닥」 — 6건.**
구 테셀레이션 잔차, 확산 켠 coh_db, 회전대칭 원판 이산화, pinv 영공간, STFT 창 밖 누설, 백색 귀무 중앙값. 널 팔을 기준선으로 쓰면 「간격」이 물리량으로 보인다. 특징: **방향은 항상 맞고 크기만 무한대로 부풀 수 있다.**

**④ 「구성상 참을 결과로」 — 4건.**
M1 눈금(+0.00 dB), slope_only 항등식, bbox 강제 정합, 「21/21 전수」. 공통 신호: **잔차가 1e-15 인데 물리 결론이 붙어 있다.**

**⑤ 「창 이름과 쓰임이 다르다」 — 5건.**
밴드평균(전대역 vs 캠페인 창), PSL(전역 vs 챔버창), 주엽(−3 dB vs 첫 널), R90(ψ=0이 곧 0-도플러 헤딩), p-p(150 자세 vs 6,000 자세). **각각 원장 키는 정확한데, 옆에 붙은 산문이 다른 창을 시사한다.**

---

## 5. 습관 두 개 (이것만 지키면 ①②가 거의 다 죽는다)

**습관 A — 「원장이 경고하면 본문이 인용한다」를 기계로 강제.**
빌더에 규칙 하나: **숫자를 주입한 JSON에 `caveat` / `must_not_say` / `do_not_write_ko` / `limitations` / `_rule` / `note_ko` 키가 있으면, 그 키를 인용하지 않은 채로 빌드하면 실패.** 지금 상황은 「숫자는 자동, 경고는 수동」이라 구조적으로 경고만 떨어진다. 이 한 줄이 18건 중 대부분을 막았다. 부수로: 원장 쪽에도 규칙을 하나 — **철회한 숫자는 다음 재생성 때 필드를 지우거나 `RETRACTED_` 접두어를 붙여라.** `switch_factorial.json`은 08-16 철회 뒤 08-27에 다시 구워졌는데 철회 표시가 없어서 노트북이 계속 읽고 있다.

**습관 B — 「비를 인쇄하기 전에 분모를 한 번 흔든다」.**
숫자 하나를 본문에 올리기 직전, **딱 한 줄**을 원장에 같이 낸다: 그 값을 만든 자유 파라미터를 **2배·½배**로 바꾼 값. 격자면 λ/2 판, 표본수면 절반 판, 문턱이면 ±5 dB, 창이면 다른 폭. 그리고 **본문은 흔들어도 안 변한 자릿수까지만 인용한다.** 이미 이 습관의 절반은 있다(「머리기사 숫자는 흔들어 보고」) — 빠진 절반은 **잣대 안의 상수도 자유 파라미터라는 것**이다. 흔들어서 결론이 뒤집히는 걸 발견하면 그건 실패가 아니라 그 절의 진짜 결과다(div≥12, CPI 배수, 낭떠러지 셋 다 흔들면 **결론이 오히려 깨끗해졌다**).

덧: p-p(max−min)는 이 저장소에서 **네 번** 사고를 냈다(06_3 두 곳, 06_6 두 곳). `report07_depth_robust.json`이 이미 대체 규약을 갖고 있으니, **p-p 단독 인용을 집 규칙으로 금지**하고 p5~p95를 항상 나란히 내는 게 맞다.

## 4. 이 검증이 놓친 것 (완성도 비판)

## A. 덱에는 있는데 리포트에 한 줄도 없는 것

리포트 25편 전문(마크다운·출력 전부)을 텍스트로 뽑아 대조했다. `/tmp/claude-0/-workspace/8ed65148-4553-4ebc-8477-9670ae39b001/scratchpad/txt/`

**A-1. 0827 2부 전체 — PathSolver 비결정성이 리포트에 없다.**
25편에서 `비결정`·`#1175`·`재실행 문턱` 검색 결과 **0회**. 원장은 있다 — `outputs/depth_axis_verdict_0816.json : null_bands.pathsolver_repeatability` (회절 끔 1.9e-15 dB / 회절 켬 8~26 자세, |E| 최대 23 %, 요동 0.072 dB, 비트차 1666~7067 자세).
  ⛔**그 원장 값은 2026-09-03 에 갈아탔다** — E0↔E1 짝이라 «모서리는 무동작» 을 가정해야 했고 7 쌍 중 4 쌍이 확산 끔(F0) 팔이었다. 지금 인용할 것은 진짜 재실행 `outputs/true_repeat_0903.json` 이다(`docs/DEEP_DROP_0902.md` ⓐ).
가장 아픈 자리: `reports/02_2_stock-engine.ipynb` 셀에서 **바로 그 해시 테이블 코드를 인용한다** — 「면 해시로 만든 경로 지문의 카운터를 원자적으로 올리고 `samples_counter == 0` 인 광선만 저장한다(`sb_candidate_generator.py:484-498`)」. 확인했다: 설치된 sionna **2.0.1** 의 그 줄이 `dr.scatter_inc` 이고 주석에 race condition 이 적혀 있다. 리포트는 기전을 정확히 적고 **결과(같은 입력 다른 답)를 안 적었다.** 그래서 회절 켠 팔의 dB 를 유효숫자 셋으로 적지 말라는 0827 규약도 리포트에 없다.

**A-2. 튕김 사다리 비감쇠 — 어느 리포트에도 없다.**
`outputs/depth_axis_verdict_0816.json : bounce_ladder` → `third_over_second = 4.867`, 튄 자세 1·8 개를 빼도 4.671·4.847, `decaying_series = false`. 0825 덱 13 장이 이걸 발표했다. 리포트에서 `튕김`·`4.9 배`·`third_over_second` 전부 **0 회**. PathSolver 에 대한 가장 무거운 미해결 이상인데 항구 기록에 없다.

**A-3. 0825 덱 1·3·4 부가 통째로 없다.** 셸 0.75 mm −6.24 dB / 프롭 0.9 mm −16.99 dB / 두께 사다리(−7.13·−6.24·−4.14) / 날 평면형 27~39 % / 읽기 거리 656~47 m / 비행창 20.7 → 11.6 dB / 로터 요동 2.50 %·분류 6.14 %p / 프레임 76-76 / 정면 3 기체 +22.0·+0.3·−0.8 dB / 학습 선 0.624·0.736·0.823 — 리포트 검색 전부 0 회.

**A-4. 0825·0827 원장 4 개를 인용하는 리포트가 0 편이다.**
`clutter_removal_verdict_0825.json` · `why_angle_matters_0825.json` · `crossterm_elev_sweep_0825.json` · `rhythm_share_knob_audit_0825.json` — 25 편 전수 검색에서 파일명 언급 0 회.

---

## B. 덱 주장 중 이번 스윕이 못 본 «측정 설정의 성질» (직접 계산해 확인)

`outputs/elevation_sweep_md.npz` 의 `sionna_p4000000000_r15_n8192_d1/el+0`(통짜) · `..._partsnoprop_..._d1/el+0`(동체만) · `..._partsprop_..._d1/el+0`(프로펠러만) — 세 팔 DC 가 −63.25 ↔ −63.23 dB 로 같아 같은 판이다.

**B-1. 0827 5 장 「흔들림의 100.00 % 가 교차항」은 항등식이다.**
실측: 동체 |E| 의 `std/mean = 2.04e-16`(정확한 상수), 동체/프로펠러 진폭비 **7845.5 = 77.89 dB**. 상수 × 7845 배이면 2Re(B·P\*) 의 AC rms 가 |P|² 의 **4060 배(36.1 dB)** 이므로 교차항 몫이 99.97 % 말고 다른 값이 나올 수 없다. 잰 것이 아니라 계산된 것이다.

**B-2. 그런데 그 교차항으로 통짜를 설명하지 못한다 — 28.4 dB 모자란다.**
AC(전력) rms: 통짜 **−76.55 dB**, 동체+프로펠러 해석적 합 **−104.92 dB**. `corr(|통짜|, |동체+프로펠러|) = 0.0052`(섞기 널 0.0089 · 1/√N 0.011), `corr(|통짜|,|프로펠러|) = −0.0127`. 「도는 날개가 동체로 가는 경로를 자른다」는 이름이 붙은 기전은 원장에서 28 dB 작고 무상관이다. 관찰(«합이 통짜와 다르다»)은 참이고, 이름(«동체×날개 교차항»)이 과잉이다.

**B-3. 결정타 — 그 팔의 요동 99.29 % 가 8192 자세 중 58 자세에 있다.**

| 팔 (el+0) | 봉우리 10 % 위 자세 | 섬광 개수 | 폭 중앙값 | 그 자세의 AC 에너지 |
|---|---|---|---|---|
| 통짜 · PathSolver 물리끔 | **58 / 8192** | 57 | **1 자세**(최대 2) | 99.29 % |
| 프로펠러만 · 같은 팔 | 5996 | 701 | 5 | 98.59 % |
| 우리 SBR 커널 | 5638 | 931 | 3 | 98.80 % |

문턱 없이 말해도 같다 — **상위 64 자세가 AC 에너지의 99.29 %** 다. 0827 1 부의 모든 수(|상관| 0.019 · AC −94.43 dB · 「100 % 교차항」 · 「합의 2,400 배」)는 파형이 아니라 **1 자세짜리 스파이크 57 개의 성질**이다. 0827 마지막 장이 바로 그 폭 문제로 수렴 시험을 제안하면서, 1 부 결론에는 그 꼬리표를 안 달았다.

**B-4. 「섬광 8 회 = 138 Hz ↔ 통과 127 Hz」는 창 길이가 정한 수다.** 58 ms 창에서 개수 세기의 분해능이 1/T = **17.2 Hz** 다(7 회 = 121, 8 회 = 138). 127 과 138 을 가를 수 없는 잣대다. 같은 프로젝트에 0.005 Hz 안에서 되찾는 박자 추정기가 있고 `reports/05_2_switch-grid.ipynb` V6 가 여덟 팔 전부 **126.1 Hz** 로 잰 적이 있다.

---

## C. 잣대가 내려졌는데 리포트가 계속 쓰는 것

**C-1. 리듬 몫.** `outputs/rhythm_share_knob_audit_0825.json : _meta.판정` = 「흔들린다 — **덱·주장 문장에서 내렸다.** 자유 파라미터 없는 물리량만 쓴다」. 그런데 `reports/A_atlas.ipynb` 가 **277 회**, `reports/05_2_switch-grid.ipynb` 가 **20 회** 쓴다. 아틀라스 §13.2 는 이 잣대를 팔 사이 비교의 정본으로 지정한다.
흔들림 크기(같은 데이터, el 0): `f_above` 를 1.5·f_flash / f_tip / 2·f_tip 로 바꾸면 우리 커널이 **98.93 → 63.36 → 51.53 %**(47 %p). 창 반폭 hw 를 2/8/16/32 로 흔들면 백색 대조군이 기하 바닥 2·hw/f_flash 를 그대로 따라간다(3.38/13.37/26.21/50.44 ↔ 3.16/12.63/25.26/50.53) — 널이 신호가 아니라 노브가 정한다.

**C-2. 아틀라스 §13.3 의 유의성 밴드가 정면 값 하나다.** 「리듬 몫 21.8 %p · 움직이는 전력 3.86 dB … 앙각 네 점에서 잰 최대값」. 그 원장 `outputs/grid_convergence_check.json` 은 앙각 **0·−15·−30·−45 네 점만** 쟀다. 이미 앙각별 값이 `depth_axis_verdict_0816.json : null_bands.grid_dispersion_ac_db_by_el` 에 있다 — 0° **3.86** · −15° 1.31 · −30° 0.37 · −45° 0.09 · −60° **0.02** · −75° 0.10 · −90° 5.62 dB. 아틀라스는 −60·−75·−90 칸에도 3.86 을 대는데 그 자리엔 λ/24 팔이 아예 없고 실제 밴드는 **10~193 배 좁다**. 그 원장 자신이 적어 뒀다 — 「⚠전역값이라 앙각별 밴드보다 넓다 — 넓은 밴드는 «판정 불가» 쪽으로 기울어 «안 바뀐다» 라는 결론에 유리하다」(`scorecard.band_rule_caveat_ko`). 0825 덱 22 장이 이 정정을 발표했고 아틀라스는 안 받았다.

**C-3. 상관을 근거로 쓰는 자리 전체.** `grid_convergence_check.json : rho_reference_rulers` — 「같은 커널·같은 격자에서 **앙각만** 15~45° 바꿔도 |ρ| 가 0.27~0.78 다 … 상관을 근거로 쓰는 모든 주장이 이 자 위에서 다시 읽혀야 한다」, 격자만 바꾼 |ρ| 바닥은 **0.5724**. 0827 1 부는 |ρ| **0.568·0.615** 를 「안 됨」, **0.964·0.991** 을 「됨」으로 가르는데 그 칼금이 정확히 이 자 안에 있다. 이 자를 인용한 리포트는 **0 편**이다.

---

## D. 낡은 원장을 계속 읽는 자리 · 출처 부패

**D-1. `reports/05_2_switch-grid.ipynb` 깊이 절이 «낡았다» 도장 찍힌 파일을 읽는다.**
그 절의 출처는 ⟨`outputs/switch_factorial.json` : verdict.B_\* · depth_pairs⟩ 인데, `depth_axis_verdict_0816.json : _meta.sources.r13` 이 그 파일을 「2026-08-15 · 새 칸 들어오기 전 — **이 파일의 깊이 결론은 낡았다**」로 적고, `closure.retractions_ko` 가 「`switch_factorial.json` B_failures 첫 줄(R0D0E0F1 · el −60 · 12.74 dB · −54.25 %p)과 B_why_ko 의 ②는 **자세 하나의 튐이다 — 인용하지 말 것**」이라고 명시한다. `reports/A_atlas.ipynb` 는 그 정정(#3399, 85.5 ↔ 85.2 %)을 이미 싣고 있고, 0818 덱 소스도 「철회됐다」로 주석했고, 0825 덱 11 장이 발표까지 했다. **05_2 만 안 고쳐졌다.** 스윕이 이 문장을 fatal 로 잡았지만, 「누가 맞는가」는 이미 저장소 안에 답이 있다는 점이 빠졌다 — 고칠 자리는 문장이 아니라 출처다.

**D-2. 04·05 편 각주의 `rows[N]` 위치 인덱스 39/40 개가 다른 행을 가리킨다.**
`outputs/elevation_sweep_md.json` 이 337 행 → **1433 행**으로 자랐다(mavic4pro·`mfixbatteryi5_blperairframe`·앙각 −52/−68/−82 신설). 각주 라벨이 지목하는 팔과 실제 행이 갈린다:

- `reports/05_engine-physics.ipynb` [^29][^30][^31][^54][^150][^177] 라벨 `sionna_phys/el-90` → 실제 `rows[219]` = **`ours_r15_n8192_mfixbatteryi5_blperairframe_div24/el-52`**(우리 커널·div24 격자)
- `reports/04_elevation-coverage.ipynb` [^17] `rows[28].f_tip_hz` 인용 **1273** ↔ 실제 **1135.1**(mavic4pro/el−15) · [^27] 인용 **0** ↔ 실제 **304.1**

값 자체는 아직 맞다(안정키로 확인: `sionna_phys/el-90 → rows[1429].level_db = -64.23`). 부패한 것은 출처다. `benchmark/check_report_links.py` 는 「출처 2183 개 · 위반 0 건」으로 통과시킨다 — **키의 존재만 보고 안정키와 인덱스가 같은 행인지는 안 본다.** 빌더는 이미 알고 있다(`src/build_part12_elevation.py:112`, `src/build_part13_engine_physics.py:363` — 「병합마다 인덱스가 밀린다」). 두 편이 최신 원장으로 재빌드되지 않은 것이다. 검사기에 한 줄(`rows[i]` 의 engine/el 이 화살표 라벨과 같은가)을 더하면 잡힌다.

**D-3. 자동검사 사각지대 — 25 편 중 7 편이 각주·⟨⟩ 태그 0 개다.**
`05_2_switch-grid`(⟨⟩ 7) · `06_1_scene`(0) · `06_2_engines`(0) · `06_4_sampling`(0) · `06_5_bistatic`(⟨⟩ 3) · `08_2_two_channel`(⟨⟩ 1) · **`A_atlas`(0)**. 06_5·08_2 는 본문에 원장 이름을 성실히 박고 「원장 없음」도 적어 두므로 내용은 건전하다. 문제는 **A_atlas** — 수치 1,000 여 개, 빗살 대비 258 회·리듬 몫 277 회를 싣고 키 단위 출처가 하나도 없어 어떤 자동검사도 안 받는다. 그리고 C-1·C-2 의 문제가 그 안에 있다.

**D-4. 메쉬 정정(2026-08-04) 도장이 빠진 두 자리.** 03_anchor·09·10_results·10_2·11 은 도장 있음을 확인했다(여기는 지적 없음). 없는 곳:
- `reports/05_engine-physics.ipynb` [^155][^156][^187][^188][^189] 가 `outputs/das_fleet_validation.json`(생성 **2026-08-03**, mini2 포함)의 `prereg_judgement.verdict = NOT_VALIDATED` 를 인용. `meshfix_attack.json : Q6_invalidated_outputs.critical` 이 「mini2 메쉬가 바뀌었으므로 … «메쉬 방법 검증 N=4» 는 **재계산 전까지 보류**」로 critical 판정. 이 편에 `2026-08-04` 문자열 **0 회**.
- `reports/02_3_target-mesh.ipynb` [^33][^34] 가 `outputs/mesh_compare_photo.json`(생성 **2026-07-31**)의 x500v2 IoU 0.8748 을 인용. 같은 원장이 「matrice4e·mini2·x500v2 행이 전부 낡았고 등록부가 3→17·3→4·3→4 로 넓어졌는데 재생성 안 됨 — **두 겹으로 낡았다**」로 high 판정.
- (확인 후 제외) 02_kernel 의 `facet_count.json` 은 `meta.drone = mavic4pro` 라 메쉬 정정 대상이 아니다.

---

## E. 스윕 자신의 라벨 오류

확정 목록에서 **`06_1_scene.ipynb`** 로 적힌 3 건(«낭떠러지» −56.48/−54.44 dB · «62.0~100.8 dB» · «운동학 74 %·55 %»)은 실제로 **`reports/03_2_size-law.ipynb`** 에 있다. `06_1_scene.ipynb` 본문에는 `낭떠러지`·`56.48`·`100.8` 이 각각 0 회다. 그 라벨대로 고치면 엉뚱한 노트북을 연다.

또 `reports/` 에는 `.ipynb` 가 **25 편**인데 스윕은 24 편을 덮었다. findings 가 0 건인 편은 `01_2_prior-work` · `05_engine-physics` · `A_atlas` 셋이고, 그중 **A_atlas 가 아틀라스 전체의 읽는 규약(§13.2·§13.3)을 정하는 편**이며 위 C-1·C-2 가 그 안에 있다.
