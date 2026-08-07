<!-- from: 편 13 where-we-stand (구 report01_prior.ipynb c20) -->
# 신규성 문단 — 논문 II 절에 그대로 붙인다

참조번호 [4] · [12] · [14] 는 `outputs/report01_paper.json:citations` 의 `n` 번호를 가리킨다 (Rzewuski · Ziganshin 저널판 · LAMBDA).

> Prior work obtains a UAV target signature along one of seven routes, and the route fixes the size of the claim a paper can make: chamber measurement buys an absolute RCS for one airframe, an external full-wave solver buys a bistatic RCS and the coverage budget that consumes it, injection of a pre-computed RCS buys aspect-dependent amplitude without touching the engine, an analytic blade model buys the shape of a micro-Doppler signature, an abstract coefficient buys a closed-form signal model, and the stock interactions of a ray engine buy kinematic structure.
>
> We adjudicate twelve candidates against four prongs — (P1) published in a venue of record, (P2) the UAV carried as a 3-D surface mesh, (P3) the scattered field computed inside a Sionna-class differentiable GPU ray engine, and (P4) the computed amplitude compared against measurement or a reference solution — and no candidate satisfies all four. Two qualifications bound that statement.
>
> First, the end product exists in published prior art: Rzewuski et al. [4] solved the monostatic and bistatic RCS of a Parrot AR.Drone with FDTD, fed it into a passive-radar coverage budget, and closed with an over-the-air detection at 50 m; the whole of their gap to our four prongs is the engine prong. Our contribution is therefore the engine, its integration into a single pipeline, and the calibrated waveform comparison it enables.
>
> Second, the word published carries the claim: with preprints admitted the gap narrows to a seam, because LAMBDA [14] ships UAV RCS beside Sionna ray paths and the journal version of Ziganshin et al. [12] validates mesh scattering inside Sionna against a bistatic measurement, a validation its authors themselves call qualitative. Neither work does both, and neither has been refereed.
>

## 두 단서의 근거

- **Q1** — Rzewuski 는 Parrot AR.Drone 2.0 의 모노·바이스태틱 RCS 를 FDTD(QuickWave-3D)로 풀어 WiFi 대역 −40~0 dBsm 을 보고하고(p.5), 패시브 커버리지 예산을 세워 바이스태틱 50 m 실측 검출까지 닫았다(p.9) ⟨outputs/report01_paper.json : h8.q1_counter_paper⟩.
- **Q2** — Ziganshin 저널판은 검증을 저자 스스로 정성적이라 적는다(p.7) ⟨outputs/prior_settled_h8.json : h8_candidates⟩.
- **주입** — 주입 아키텍처 자체는 이미 게재돼 있다. 재판독으로 확정된 게재 주입 3 편 ⟨outputs/injection_classification_audit.json : corrected_tally.peer_reviewed_confirmed_injections⟩ 은 전부 자기 서명을 실측 또는 기준체와 맞대고 수치를 인쇄했다.

생성기: `src/build_part02_prior_work.py:write_paper_docs`
