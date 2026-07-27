# Compact-Range RCS Measurements and Modeling of Small Drones at 15 GHz and 25 GHz
- **Authors**: Ezuma, Funderburk, Guvenc (NC State), arXiv:1911.05926, 2019
- **Band**: 15 & 25 GHz (compact-range, 20-ft parabolic reflector, azimuth-avg 0-360°)
- **Drones & average RCS**:
  - DJI Phantom 4 Pro: **−15.03 dBsm (15 GHz)**, **−12.40 dBsm (25 GHz)**
  - DJI Inspire 1: −14.24 / −11.09 dBsm
  - Trimble zx5
- **Key**: RCS increases with frequency (+2.6~+4.75 dB from 15→25 GHz).
- **우리 대조**: 15→25 GHz 에서 +2.6 dB — RCS 의 주파수 단조증가 **방향**이 우리 밴드 추세와 일치.
  - 절대값은 밴드갭(15/25 GHz ↔ 우리 1.8/3.5/5.2 GHz)이 커서 **참고 수준**이다. S밴드로 외삽하면 ~−26 dBsm 이고,
    우리 방위평균은 그보다 밝다 — report08 이 그 격차를 **최대 ~7~10 dB** 로 명시한다.
  - ⚠ **숫자를 여기 박지 않는다**: 현행 우리값은 `outputs/report2_waveform_rcs.json` →
    `rcs.drones.mavic4pro.bands["5G NR 3.5 GHz"].mean_dbsm`. 격차 수치는 report08 §6 이 단일 출처다.
- URL: https://arxiv.org/abs/1911.05926
