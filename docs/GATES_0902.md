# The three gates — results (night of 2026-09-02)

Of the 34 lines pulled to the front of the queue (16 gate + 18 baseline), **the three gates have finished.** These three are where the value
of the other axes is judged.

## ⭐E3 — sub-degree azimuth: **az 0 is not one point on a curve**

el 0 · everything off · depth 2 · matrice4e:

| Azimuth | Step drops | Ratio the drops cluster at | N |
|---|---|---|---|
| **0°** | **36** | **0.6667** | **3** |
| 0.5° | 707 | 0.8928 | 9 |
| 1° | 845 | 0.8983 | 10 |
| 2° | 442 | 0.8976 | 10 |
| 22.5° | 259 | 0.8885 | 9 |
| 45° | 15 | 0.8951 | 10 |

⭐**N is 3 at az 0 and already jumps to 9 at az 0.5°.** After that it does not change much, staying at 9~10.
⇒ **az = 0 is a special cell because the geometry is symmetric**. It is not 「N 이 방위에 따라 매끄럽게 변한다」 [N changes smoothly with azimuth] but
   **「0 만 다르고 나머지는 비슷하다」 [only 0 differs and the rest are similar]**.
⚠**The number of drops is not monotonic in azimuth** (corrected 2026-09-04) — it jumps from 36 at 0° to 442~845 at 0.5~2°,
   then comes back down to 259 at 22.5° and **15 at 45°**. ⛔The previous edition's 「우리 코퍼스(전부 az 0)가
   인공물이 가장 적은 경우였다」 [our corpus (all az 0) was the case with the fewest artefacts] **is refuted by the last row of this very table** — 15 at 45° is
   fewer than 36 at az 0°. Only one thing is certain:
   **N is 3 only at az 0 and 9~10 everywhere else**.
⇒ The 144 azimuth lines are **worth running**. But how to read them changes.

## ⭐B1 — grid phase null: **el 0 has not converged at λ/12**

Shift the grid by **half a cell** (same spacing, same number of cells — nothing physical changes):

| Elevation | Baseline | Half cell | Difference | Width (baseline → shifted) |
|---|---|---|---|---|
| **0°** | −53.59 dB | −65.49 dB | **−11.91 dB** | **65.4 % → 309.9 %** |
| −15° | −51.11 | −50.64 | +0.47 | 56.8 → 40.4 |
| −30° | −58.06 | −58.81 | −0.74 | 120.8 → 203.1 |

⭐**Only el 0 moves by 12 dB.** The other elevations move 0.5~0.7 dB.
⭐**With a finer grid (λ/24) the same shift shrinks to +1.45 dB** — the signature of convergence.
⇒ **Our kernel's el 0 «level» and «width» cannot be used at λ/12.**

## ⭐B2 — propeller scale × λ/24: the non-monotonicity disappears

At λ/12 the ps ladder was **non-monotonic** (0.7/1/1.4/2 → −64.41 / −53.53 / −53.77 / −60.22 dB).
Measured at λ/24 it is **monotonic**: **baseline −59.53 → propeller ×2 −57.73 dB (+1.80)**.
⇒ That non-monotonicity was **grid churn**, not physics.

## ✅The deck's claim still stands — the comb does not depend on the grid

Comb SNR (floor p99 ≈ 8.4 · maximum over 2,000 runs 9.6):

| Our kernel run | el 0 | el −15 | el −30 |
|---|---|---|---|
| Baseline λ/12 | **51.3** | 46.7 | 49.8 |
| Half cell λ/12 | **52.9** | 46.6 | 47.9 |
| λ/24 | **54.5** | 52.2 | 52.5 |
| λ/24 + half cell | **53.1** | — | — |

All four runs are 51~55. **The «present/absent» of the blade beat does not depend on the grid.**
For comparison, PathSolver at el 0 gives 3.1 / 4.2 / 10.7 / 12.7.

⇒ 「**At 0° only our kernel shows stripes**」 on deck slide 12 **is a qualitative claim, so it is safe.**
⛔However, **our kernel's el 0 «level» or «width» must not be cited as numbers** — it has not converged.
   (The deck does not contain those numbers. Checked.)

## Remaining gates

E1b canonical holes (el −45 · −75 × four arms) 4/8 done. The azimuth axis uses them as reference points at those elevations.
