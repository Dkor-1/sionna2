# An Investigation on the Radar Signatures of Small Consumer Drones
- **Authors**: Y. Li, H. Ling
- **Venue**: IEEE Antennas and Wireless Propagation Letters (AWPL), 2017
- **Citations**: ~99
- **Band**: 3–6 GHz (VNA turntable, sphere-calibrated S11)  ← **우리 3.5 GHz 밴드 일치(BEST ANCHOR)**
- **Drones & measured peak RCS**:
  - DJI Phantom 2 (35 cm diag): **−27.5 dBsm** (AZ 194°)
  - 3DR Solo (46 cm): −24.2 dBsm (AZ 90°)
  - DJI Inspire 1 (56 cm): −13.7 dBsm (AZ 270°)
  - + in-flight DJI Phantom 3 Advanced (PulsON 440 UWB)
- **Key**: RCS at 3–6 GHz ~12 dB lower than 12–15 GHz. Aspect spread ~14 dB.
- **우리 프로젝트 대조**: 시뮬 Mavic 4 Pro 의 **방위평균 @3.5 GHz** 가 3DR Solo(−24.2)~Inspire 1(−13.7) 사이에 든다 = **실측 aspect-peak 범위 안**.
  - ⚠ **숫자를 여기 박지 않는다** — 엔진·메쉬가 바뀌면 곧바로 낡는다. 현행값 출처는
    `outputs/report2_waveform_rcs.json` → `rcs.drones.mavic4pro.bands["5G NR 3.5 GHz"].mean_dbsm`
    (밴드평균은 세 밴드 `mean_dbsm` 의 산술평균). 리포트에서는 report08 이 같은 키를 주입해 쓴다.
  - ⚠ **비교 대칭성 주의**: 우리 값은 **방위평균**이고 위 문헌값은 **aspect-peak** 이다. 방위평균끼리 견주면
    우리는 소형드론 실측 포락선(S밴드 −28~−16 dBsm, 중앙 ~−22)의 **밝은 상단**에 있다(report08 §6).
  - 자세별 값과 혼동 금지: 검출 실험의 특정 자세(az≈24°)는 **널**이라 포락선 **하단**이다.
- URL: https://www.semanticscholar.org/paper/9c6129ed653d2e8eb3cc321f3cd9365ed04494c0
