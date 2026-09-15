# ρ measures «smoothness», not «rhythm» (2026-09-02)

## What the problem is

`benchmark/outdoor_scene_0901.py:rho` — the envelope autocorrelation (lag 1) — is **report 12's canonical yardstick**, and
its scale there is written as 「잡음 −0.06~+0.07 · 박자 +0.92~+0.99」 [noise −0.06~+0.07 · beat +0.92~+0.99].

⛔**That scale separates only «smooth» from «white»; it does not separate «rhythm» from «no rhythm».**
Signals with **no oscillation at all** land in the 「박자」 [beat] cell (independent recomputation 2026-09-02, N=8192):

| Signal | ρ |
|---|---|
| Straight-line slope | **0.9996** |
| 2nd-order trend | **0.9996** |
| A single step in the middle | **0.9996** |
| AR(1) red noise φ=0.99 | **0.9748** |
| Band-limited noise (no pure tone) | **0.9975** |
| White noise (control) | −0.0289 |

It leaks in the opposite direction too: **a real flash train** gives 0.9986 at 126.7 Hz but 0.2410 at 4 kHz and
**−0.8872** at 9 kHz. ρ **cannot see** fast rhythm.

## What was actually misread

In the 2026-09-02 verdict on the outdoor environment mesh, **12 of 40 cells were ρ false negatives**.
Looking again with an independent detector (harmonic SNR of the comb at f_flash = 126.7 Hz, null distribution from 2,000 white-noise runs:
median 8.2 · p95 12.5 · p99 15.2 ⛔(values withdrawn below in 「First, my own mistake」 — this implementation's canonical floor is p99 ≈ 8.4 · maximum over 2,000 runs 9.6) · maximum 25.2):

| Cell | ρ (after repair) | Comb SNR | Verdict |
|---|---|---|---|
| diffraction / outdoor / −45° | 0.070 | **114.5** | beat present (p<0.0005) |
| diffraction / outdoor / −75° | 0.055 | **127.3** | beat present |
| both / outdoor / −30° | 0.047 | **59.1** | beat present |
| all off / outdoor / −60° | 0.041 | **121.3** (2nd harmonic 253 Hz) | beat present |
| all off / outdoor / **+0°** | −0.004 | **2.4** (p=0.14) | ⭐**there really is no comb** |

Mechanism: in the false-negative cells, **74~80 % of the variation lies above 2 kHz**. The lag-1 statistic is pressed down to 0 by it
and cannot see the comb at 127~634 Hz (which carries ~20 % of the variation).

⇒ ⛔「회절 팔은 실외에서 박자가 죽는다」 [the diffraction arm loses the beat outdoors] · 「−60° 가 이웃과 다르다」 [−60° differs from its neighbours] were **statements about ρ,
   not statements about the records.** ⭐**Only 0° survives** — there, the independent detector also finds no comb.

## The yardstick for drop repair was wrong too

The aggressiveness of the repair was measured as 「자세의 몇 % 를 건드렸나」 [what % of poses were touched], but the right yardstick is **the share of variation (variance)**:

| | Share of poses | **Share of variation** |
|---|---|---|
| all off / outdoor / −30° (74 poses) | 0.90 % | **99.09 %** |
| all off / free / −30° (2,954 poses) | 36.06 % | **36.92 %** |

⇒ **The outdoor repair is more aggressive.** 「1 % 만 건드렸으니 안전」 [only 1 % was touched, so it is safe] does not hold.
   What justifies the outdoor repair is **that the independent detector confirms what remains**, not that few poses were touched.

⭐Still, the conclusion of (B) (the free-space repair cannot be used) stands — in free space **the drop indicator itself is the rhythm**
(for all off / free / −30°, the drop indicator's f_flash line against background is 119.7 and its median spacing is 1 pose).
There, «repair» erases the signal.

## What survived

⭐**The suspicion that interpolation inflates ρ was rejected** — the real drop masks were transplanted onto «rhythm-free» signals
   to measure the ρ that interpolation creates from nothing:

| Mask | ρ created |
|---|---|
| Outdoor (0.9~1.0 %, longest run 2) | **−0.011 ~ +0.020** |
| Free −30° (36.1 %, longest run 34) | +0.205 ~ +0.368 |
| Free −60° (41.7 %, longest run 78) | +0.205 ~ +0.392 |

⇒ The outdoor 0.005 → 0.974 **is not an interpolation artefact.** Of the free-space repaired values 0.757~0.983,
   **+0.32~+0.39 was created by interpolation**.

## Going forward

⛔**Do not say 「박자가 있다/없다」 [the beat is present/absent] from ρ alone.** At minimum, also report the **comb harmonic SNR**.
⭐When using ρ, check **whether the value remains after a 100 Hz high-pass** (to rule out smooth-trend false positives).
   The 0.9+ cells in this table passed that test (0.79~0.99 after high-pass) — there were in fact no false positives.

⚠**The scale sentence in report 12 must be fixed** — 「잡음 −0.06~+0.07 · 박자 +0.92~+0.99」 [noise −0.06~+0.07 · beat +0.92~+0.99] gives the impression
   that ρ is a rhythm detector.

---

# Verdicts redone with comb SNR (night of 2026-09-02)

## ⛔First, my own mistake — I used someone else's null distribution for my detector

「중앙 8.2 · p95 12.5 · p99 15.2 ⛔(아래 「먼저 내 실수」에서 철회한 값이다 — 이 구현의 정본 바닥은 p99 ≈ 8.4 · 2,000 판 최대 9.6)」 [median 8.2 · p95 12.5 · p99 15.2 (values withdrawn in this section — this implementation's canonical floor is p99 ≈ 8.4 · maximum over 2,000 runs 9.6)] are values **the verification agent produced with its own implementation**,
and I copied them as is into `benchmark/comb_snr.py`. The null distribution **of this implementation** was re-established
with 2,000 white-noise runs:

| Elevation | Median | p95 | p99 | p99.9 | Max |
|---|---|---|---|---|---|
| 0° | 6.03 | 7.49 | **8.19** | 8.81 | 8.91 |
| −30° | 6.09 | 7.73 | **8.40** | 9.01 | 9.07 |
| −60° | 6.10 | 7.82 | **8.61** | 9.33 | 9.57 |

⇒ **The floor is p99 ≈ 8.4, maximum over 2,000 runs 9.6**. Use these values from now on.

## ⭐False-positive control — passed

It was first applied to a record **proven to have no rhythm** (body only, width exactly 0.0000 %):

| Record | Width % | Comb SNR | |
|---|---|---|---|
| **Body only** `partsnoprop` el 0 | **0.0000** | **5.1** | ✅floor — no false positive |
| Whole drone el 0 | 33.35 | 4.9 | not visible |
| **Propeller only** el 0 | 239.88 | **51.9** | ⭐the blades are definitely there |
| Whole drone el −30 | 264.14 | 60.1 | present |

⇒ 0° is **drowning** — the blades modulate (51.9), but the body covers them so they are not visible on the whole drone (4.9).
⛔`partsprop`/`partsnoprop` are **depth 1 · old mesh**. Say so when putting them on a slide.

## ⭐⭐Outdoor — a solver artefact was hiding the comb

The raw outdoor records are at the floor in every arm and every elevation (2.5~12.7). But filling in the **deep-drop poses
(= poses where the ground-reflection path fell out of the hash bucket, [`DEEP_DROP_0902.md`](DEEP_DROP_0902.md))**
brings it up:

| Arm | Elevation | Drops | Raw | **After removing the artefact** | Random control (5 seeds) |
|---|---|---|---|---|---|
| All off | −15° | 60 | 5.8 | **47.3** | 5.9 ± 0.2 |
| | −30° | 74 | 4.3 | **59.7** | 4.4 ± 0.3 |
| | −45° | 83 | 6.7 | **58.0** | 6.6 ± 0.2 |
| | −60° | 84 | 2.5 | **16.5** | 2.6 ± 0.3 |
| | −75° | 82 | 7.0 | **66.4** | 7.1 ± 0.1 |
| Refraction only | −15° | 33 | 6.7 | **34.2** | |
| | −30° | 35 | 4.9 | **45.7** | |
| | −45° | 46 | 6.1 | **43.2** | |
| | −60° | 59 | 3.5 | **15.7** | |
| | −75° | 31 | 3.8 | **47.7** | |

⭐**Filling the same number of random poses does not raise it** (2.6~7.1). It is not an interpolation artefact.
⇒ **The blade comb is present outdoors too. A solver artefact was hiding it.**
Mechanism: the artefact poses are impulses, so they **raise the broadband floor** and enlarge the comb detector's denominator.

⚠**This differs from the morning's ρ trap** — this detector subtracts the mean, so the revived ground carrier
cannot help it, and **the random control passed**.

⛔**el 0° is still at the floor** (4.4 → 4.4, 0 drops). 0° is not an artefact problem but **the body drowning the blades**.

## ⛔Fix to `benchmark/comb_snr.py` (2026-09-02)

`f_tip(el) = FTIP0 · cos(el)` **had no carrier term.** The blade-tip Doppler is
`2 v_tip / λ = 2 v_tip · fc / c`, so it is proportional to the carrier. Reading the `--fc-ghz` runs (5.8/10/24 GHz)
as they were puts the band off by up to **6.86×**, and **every cell is falsely judged 「빗살 안 보임」 [comb not visible]**.
Fixed to read `_fc<MHz>` from the arm name and multiply.

## ⚠Report 12 must be fixed

`reports/12_outdoor-scene.ipynb` has **42 lines** citing ρ. In particular:
- 「버리기만 해도 실외 ρ 는 +0.973 · +0.976」 [just discarding them makes outdoor ρ +0.973 · +0.976] ⛔ — that value reads **the smoothness of the revived ground
  carrier**.
- The whole outdoor verdict must be replaced with the comb SNR table above.
⭐And the identity of 「실외에서 오른 +53.6 dB 정지 성분」 [the +53.6 dB static component that rose outdoors] that the section spoke of turned out to be
**the ground mirror reflection** (ε_r = 5.26 ≈ ITU concrete 5.24).

⛔`ρ` in other reports **means something different** — `08_2` reference-channel SNR · `08` whiteness autocorrelation ·
`02_2` radius of curvature · `01_2` complex scattering coefficient. Do not touch them.
