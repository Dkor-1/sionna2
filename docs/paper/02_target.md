<!-- 생성물 — `src/make_reports_index.py:write_paper_02()` 가 옛 노트북에서 옮긴다. -->
<!-- from: 옛 report02_target.ipynb c25 (pk:methods) -->

# 논문 조각 — 표적 모델(방법 문단)

옛 02편이 부 3 「표적 메쉬」 · 부 4 「산란 커널」 · 부 5 「앵커와 검증」 셋으로 갈렸다.
이 문단은 그 셋을 한 문단으로 쓰는 논문용 서술이다.

| 무엇을 대는가 | 어느 부 |
|---|---|
| 메쉬를 무엇에서 지었나 | 부 3 (편 15~17) |
| 광선 가림 + PO 면적분 · 기준해 대조 | 부 4 (편 18~23) |
| σ 를 측정에 맞추는 축과 그 검증 | 부 5 (편 24~29) |

---

## Methods

Each airframe is a watertight triangle mesh built from the published outer dimensions, the motor-to-motor diagonal and the propeller diameter, with every face keeping its part-level material group (metal, PCB, camera assembly, carbon, plastic shell, propeller); the reflection coefficients are the ITU-R P.2040 values that Sionna 2.0.1 itself uses. For one incidence direction we call Sionna's Mitsuba/OptiX ray engine for a first-hit visibility test on a ray grid of pitch lambda/12, then integrate the physical-optics surface current over the lit facets only, E = sum_i |Gamma_i| exp(j 2 k p_i . u) dA and sigma = 4 pi |E|^2 / lambda^2; thin dielectric shells are transmitted with the round-trip factor tau = 1 - |Gamma|^2 and the metal behind them is summed coherently, and for a bistatic pair a second shadow ray is cast from every hit point toward the receiver. The kernel is checked against three closed-form reference solutions - the analytic physical-optics sphere, the exact Mie PEC sphere and the PEC dihedral 8 pi a^2 b^2 / lambda^2 - over kr = 1 to 100 at 21 points and 48 incidence directions. The absolute level of sigma is the kernel output; only the frequency slope is re-anchored, onto the measured 0.210 dB/GHz of Das et al., which rotates sigma(f) about the band-mean level and leaves the normalised aspect pattern unchanged. Software: Sionna 2.0.1, Sionna-RT 2.0.1, Mitsuba 3.8.0, Dr.Jit 1.3.1, NumPy 2.5.0, Python 3.12.

