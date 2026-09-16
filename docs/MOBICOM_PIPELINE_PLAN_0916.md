# MobiCom pipeline plan — drone detection and tracking with one X410 (working notes, 2026-09-16)

> Agent-facing working notes. The user-facing Korean version goes into the ISAC plan report
> (`docs/ISAC_DETECTION_TRACKING_PLAN_0915.ipynb`, section on the experiment pipeline, built by
> `benchmark/build_isac_plan_0915.py`). Numbers below come from the ledgers named next to them or from the web sources
> listed; items marked *inference* are not facts. Nothing in this repository has been compared with RF measurements yet.

## 0. Decisions and user statements recorded

| Date (KST) | Statement | Status |
|---|---|---|
| 2026-09-15 | Target ACM MobiCom next year; a real DJI Matrice 4E has arrived | recorded in `AGENTS.md` |
| 2026-09-15 | Engine roles: our kernel is the free-space reference for PathSolver; environments are simulated with PathSolver alone | `AGENTS.md` "Engine roles" |
| 2026-09-16 | 「사용하려고 하는 파형이 상용 OFDM 구조와 가까운 형태」 [the waveform will be close to commercial OFDM structure] | adopted, with the conditions in §3 |
| 2026-09-16 | 「분류도 분류인데 디텍션+트래킹이 더 현실성 있을 것 같은데」 [classification aside, detection + tracking looks more realistic] | agreed: detection + tracking is the core (§5); rotor signature only as a track-confirmation feature |

## 1. Venue facts (checked 2026-09-15)

- MobiCom 2027 call is out; the summer round closed on 2026-09-02; every winter-round date is still TBD
  (https://www.sigmobile.org/mobicom/2027/cfp.html).
- *Inference* from the 2023-2026 calls: winter abstract about 2027-03-05..12, paper about 2027-03-12..19.
- A rejection bars MobiCom resubmission for 11 months from the last deadline used (same page); a one-shot revision goes to
  the next deadline. Fallbacks: MobiCom workshops (DroneCom, WiNTECH; 2026 workshop deadline was 2026-06-05), demo track.
- 12 pages excluding references, double blind, two review stages with early reject; accepted papers need a 90-second teaser.
- Evaluation bar seen in recent accepted RF-sensing and drone papers (BSense MobiSys'26, mmTunnel MobiCom'25, LiSWARM
  MobiSys'25, mmE-Loc SenSys'25, Wi2SAR MobiCom'26): real hardware at 2 or more sites, many flights or hours, independent
  ground truth in most (GPS, RTK, LiDAR), several comparison methods plus ablations, multi-target and cross-site cases.
  Simulation was never the only evaluation (used for scale, hard-to-stage cases, or as the contribution checked against
  measurements).

## 2. Closest work and the gap (search scope: web search plus MobiCom 2021-2026, MobiSys 2025-2026, SenSys 2024/2026 titles)

- **LaSen (SenSys 2026)** — the same airframe (Matrice 4E, plus Mini 4 Pro), NI USRP-2954R, NR-structured OFDM at 5.8 GHz
  (78.12 MHz, 30 kHz) generated with the MATLAB 5G Toolbox, rooftop and lawn, detection to 108 m, RTK ground truth, sparse
  recovery plus a Kalman filter. Its Discussion names angle of arrival (two RX channels), receive beamforming against
  ground/building multipath and rotor micro-Doppler as possible extensions. No communication metric, no simulation.
- **BSense (MobiSys 2026)** — commercial 5G-Advanced base station point clouds, urban, ranges up to 1,000 m; no micro-Doppler.
- **OpenISAC (arXiv 2601.03535)** — BSD-2 real-time OFDM ISAC on X310/B210-compatible radios, a Mavic Air 3S target at 3.1 GHz.
- **CellSense** (USRP + OAI + Sionna scenes, cuboid target), **Gurung et al. 2608.05826 / 2608.10784** (Sionna emulation, point
  target, rotor micro-Doppler excluded), **HiSAC (SenSys'24)** (5G-NR plus 802.11ay pilots fused indoors, no drone).
- Combinations not found within that scope (not a "first" claim): 4-channel raw-waveform angle-capable multi-drone tracking with a
  communication waveform; sector/aimed antennas compared in the field for drones; one SDR benchmarking Wi-Fi, LTE and NR with a
  drone target and communication metrics together; a rotor-resolved drone in a site-specific ray tracer matched to same-site
  measurements.

## 3. Waveform: close to commercial OFDM (NR-structured CP-OFDM first)

Suitable, with conditions. OFDM radar processing divides each received resource element by the known transmitted one, so the
target response carries no data-dependent structure — the noise does not follow: Y / X = H + N / X scales the noise by
1 / |X| at each element, so the range-Doppler noise floor does depend on the constellation. At equal mean symbol energy
E[1/|X|^2] is 1.000 for QPSK and 1.889 for 16-QAM, i.e. 2.76 dB more average noise after plain division
(`outputs/research_logic_review_0916.json : ofdm.qpsk_inverse_energy, ofdm.qam_inverse_energy, ofdm.noise_ratio_db`;
an analytic average on an ideal elementwise model — not an end-to-end detection loss, and not a regularised divider).
This is the reason for the constant-modulus row below. LaSen already used an NR-structured waveform with this drone.

| Condition | Why | Evidence |
|---|---|---|
| Own transmitter; use **every** OFDM symbol as a known reference | one reference symbol per slot gives 1 / 2 / 4 kHz slow-time for NR 15 / 30 / 60 kHz, below the blade-tip need | `outputs/isac_plan_waveforms_0915.json : slow_time_rates`; `outputs/isac_plan_link_budget_0915.json : tip_doppler_rows` (3.5 GHz hover el 0 needs 2,546 Hz; 5.8 GHz 4,219 Hz) |
| Contiguous symbols for the micro-Doppler window (no UL slots, SSB gaps or idle symbols inside it) | uniform slow-time sampling; gaps alias or smear the rotor lines | *inference* from sampling theory |
| Prefer 30 kHz subcarrier spacing at 3.5 GHz | blade-tip Doppler as a fraction of spacing: 0.085 at 15 kHz, 0.042 at 30 kHz (3.5 GHz hover) — less inter-carrier leakage | `isac_plan_link_budget_0915.json : intra_symbol_doppler_rows` |
| Constant-modulus sensing symbols where possible (QPSK/DMRS-like) | per-element division scales noise by 1 / \|X\|: at equal mean symbol energy 16-QAM carries 2.76 dB more average noise than QPSK | `outputs/research_logic_review_0916.json : ofdm.noise_ratio_db` |
| Linear average power around +5 dBm and measured TX-RX isolation of about 40-45 dB | OFDM PAPR (11 dB assumed) and ADC/TX-noise limits | `isac_plan_link_budget_0915.json : isolation_summary_rows` (3.5 GHz, +5 dBm OFDM: 43.5 dB, TX noise binding) |
| Call it "NR-structured", not "5G NR compliant", unless a conformant stack (OAI) is used | honesty about what is standard | `AGENTS.md` ISAC constraints |
| Carrier and outdoor transmit licence decided before waveform work | the Matrice 4E video link uses 5.725-5.850 GHz and 2.4 GHz (5.150-5.250 GHz listed as CE-only); 3.5 GHz is a licensed band | DJI M4 spec page; licence rules not verified |

Installed Sionna 2.1.0 gives a complete NR PUSCH coded chain and runs on CPU (BER 0 noise-free, CRC fails on a corrupted
control); it has no synchronisation/CFO estimator, no downlink signal generators, no 802.11 or LTE implementation
(`isac_plan_waveforms_0915.json : nr_pusch, native_bridge, sionna_phy_inventory, installed_elsewhere`).

## 4. Micro-Doppler map with this waveform

Correct if done as an OFDM-radar slow-time spectrogram:
1. per OFDM symbol: channel estimate = received element / transmitted element; inverse FFT over subcarriers → range profile;
2. pick the drone's range bin(s) from the tracker (range migrates when the drone moves);
3. remove the static part (MTI or mean over the window) and compensate the body Doppler from the track before the STFT;
4. STFT over contiguous symbols at the symbol rate (14 / 28 / 56 kHz for NR 15 / 30 / 60 kHz).

Conditions and cautions:
- slow-time rate must exceed 2 (f_tip + |f_body|): 3.5 GHz hover 2,546 Hz; with 21 m/s radial body motion 3,527 Hz
  (`tip_doppler_rows`); at 7,500 rpm (disputed upper bracket) up to 6,005 Hz;
- blade returns in published measurements are 17-25 dB below the body (link-budget sources), so rotor lines need longer
  coherent windows or closer ranges than body detection;
- static leakage into the STFT band must be removed before reading lines (memory note `static-leaks-into-stft-band`);
- check for isolated jumps before trusting a spectrum: in the simulation corpus every one of the 24 omnidirectional-antenna
  cells of the ground-only scene carries 49-99 isolated poses holding 94.8-99.4 % of that cell's varying power, and the
  same 49-99 at the 10, 20 and 50 times thresholds; but of the 4 cells of that scene with the aimed TR 38.901 element 3
  carry none at all, and the fourth carries 53 of its 8,192 poses (62.3 % of the varying power) at the 20 times threshold
  and 0 at the 50 times one — the aimed condition is not the same picture, and the full-outdoor and street-canyon scenes
  carry omnidirectional cells only, so the antenna axis is untested there
  (`outputs/isac_plan_corpus_0915.json : dropout.summary[scene=outdoor01_ground,ant=iso]`,
  `dropout.summary[scene=outdoor01_ground,ant=tr38901]`,
  `dropout.rows[scene=outdoor01_ground,ant=tr38901,env_alt_m=5.4]`); real captures can have their own jumps
  (ADC clipping, gain changes, packet loss) and must be screened the same way;
- this repository's rotor numbers use hover rpm 3,800 (an estimate; DJI publishes no hover rpm) and the Matrice 4E logs no
  motor rpm in the paths checked, so rotor speed on the day is read from the spectrum itself or an acoustic sensor.

## 5. Scope: detection + tracking core, classification not in the core

- Detection + tracking is measurable against RTK ground truth with one drone type, fits the six-month window, and matches
  what the closest accepted systems evaluated. Classification needs many negative targets (birds, other drones) and more data.
- Keep the rotor signature as a **track-confirmation feature** (does a confirmed track carry blade lines?) and report its
  effect on false tracks as an ablation; multi-class identification is future work.
- Differentiation from LaSen has to come from: angle via 4 RX channels and sector antennas, multi-drone association,
  communication metrics next to sensing, and site-specific design of antenna aim and height.

## 6. Pipeline layers

1. Hardware and site — X410 variant (standard vs "L") and host NIC (10 GbE → 200 MHz per channel; continuous 400 MHz needs
   CG_400 over 100 GbE, UHD manual); TX 1, sensing RX 3 on overlapping sectors, RX 1 as coupled TX sample or communication
   receiver; GPS time on the X410 and Matrice 4E RTK logs; camera for non-drone events.
2. Waveform TX — NR-structured slot from installed Sionna at 30.72 Msps native raster; LTE and Wi-Fi arms written later; OAI
   optional for a conformant NR link.
3. Capture — UHD streaming, SigMF metadata, per-session calibration injected into every RX (X410 channel phase is not fixed
   across initialisations), isolation and ADC headroom measured first.
4. Sensing front end — per-frame reference, leakage/direct-path cancellation, complex range-Doppler cube per channel,
   float64 CFAR, cell clustering into a detection list (range, Doppler, sector amplitude ratio → azimuth, SNR).
5. Tracking — Stone Soup (EKF/UKF, GNN then JPDA, M-of-N confirmation; `OPENSOURCE.md`); metrics: TR 38.765 P_md,
   P_fa Type 1 and 2, error against RTK, GOSPA, continuity, time to confirm.
6. Track confirmation by rotor lines (§4, §5).
7. Digital twin — site model, measured antenna patterns and mount heights in PathSolver; settings admitted only after the
   free-space kernel cross-check and the isolated-pose check; used for aim/height design and expected clutter; compared with
   captures on relative quantities only.
8. Campaign — 2-3 sites, 20-300 m, several heights, hover and 5-15 m/s, two drones, several days; comparisons: single
   omnidirectional antenna, no sectors, placement without the twin; ablations: waveform, aim/sector, rotor-line confirmation,
   CPI length; release code and SigMF data.

## 7. Month plan (assuming a mid-March 2027 deadline)

| Period | Work |
|---|---|
| late Sep-Oct 2026 | band and licence, antenna specs, X410 bench (isolation, calibration, streaming), detection-chain fixes, path listing at isolated poses, site 1 twin |
| Nov 2026 | first outdoor captures: background, reference reflector, hover, single-sector NR detection, ground-truth sync |
| Dec 2026 | sector angle, Stone Soup tracking, moving trajectories, two drones, LTE/Wi-Fi arms, communication metrics |
| Jan 2027 | main campaign at sites 1-2, rotor-line confirmation, comparison methods, twin-guided placement |
| Feb 2027 | ablations, cross-site test, simulation-capture comparison, writing |
| early Mar 2027 | abstract and paper |

## 8. Open decisions (user)

Carrier and outdoor licence; antenna models; X410 variant and NIC; whether the three-standard benchmark stays in the same
paper; real-time system or offline processing; pilot certificate, airspace and flight approval.
