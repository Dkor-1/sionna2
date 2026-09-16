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
- Combinations not found within that scope (not a "first" claim): raw-waveform angle-capable multi-drone tracking with a
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
- replacing the isolated poses is a sensitivity analysis, never a correction: the headline spectrum and every detection
  and tracking number stay on the raw field, with the replaced field reported beside it. In the 24 ground-only isotropic
  cells the 49..99 isolated poses out of 8,192 (0.6-1.2 %) already carry 94.8-99.4 % of the varying power, and replacing
  them moves the blade-line comb contrast (power in the blade-flash harmonic bins over the other bins) from -0.6..6.0 dB
  to 27.4..32.2 dB, while replacing the same number of randomly drawn non-isolated poses raises it by at most 0.001 dB
  (`outputs/isac_plan_corpus_0915.json : dropout.summary[scene=outdoor01_ground,ant=iso].n_outlier_poses_min /
  .n_outlier_poses_max / .share_min / .share_max / .contrast_stored_min_db / .contrast_stored_max_db /
  .contrast_replaced_min_db / .contrast_replaced_max_db / .random_control_minus_stored_max_db`;
  `dropout.rows[scene=outdoor01_ground,ant=iso].n_poses`). The selection threshold does not set the result: k = 10, 20 and
  50 median deviations select the same 49..99 poses and give the same 27.4..32.2 dB (`.n_outlier_poses_f10_min_max`,
  `.n_outlier_poses_f50_min_max`, `.contrast_replaced_f10_min_max_db`, `.contrast_replaced_f50_min_max_db`). So the gain
  measures that a 0.6-1.2 % sample dominates the metric, not that removing it is physically right;
- which path changes is now listed, for a sample: 16 isolated poses of one ground-only cell and 16 of one street-canyon
  cell (build 2.1.0, depth 2, el -60). In the ground cell 30 of the 32 isolated-vs-neighbour pairs differ by exactly one
  absent path with none added - the environment specular return `env_ground` primitive 0 - and the other 2 differ by
  nothing, while all 16 neighbour-vs-neighbour control pairs differ by nothing; in the canyon cell 28 of 30 pairs miss
  one path and 2 miss two (`floor` specular, and an `unnamed[0]`-`building_6` double bounce), with all 14 control pairs
  identical (`outputs/dropout_paths_0916_diff.json : cells[0] / cells[1] .pair_counts, .missing_path_keys_by_pairs,
  .control_neighbour_pair_counts`; `outputs/dropout_paths_0916.json : _meta.parameters.n_outliers`). That ledger states
  that it does not identify why a path is omitted (`_meta.scope`), and the other cells are not listed, so these poses are
  still not classified as a numerical artefact or as physical scattering, and nothing here says the replaced spectrum is
  closer to a real signal;
- a contrast gain is not a detection gain: before the replacement rule is used for anything it has to move P_d at a fixed
  measured false-alarm rate, and then track continuity (§6.5), each measured on data that did not set the rule (§9);
- on captures the screening rule is fixed before the flight and every removed frame must carry an independent record
  (packet loss, ADC clipping, gain change, §6.3); frames with no such record are reported as removed, not silently
  deleted;
- this repository's rotor numbers use hover rpm 3,800 (an estimate; DJI publishes no hover rpm) and the Matrice 4E logs no
  motor rpm in the paths checked, so rotor speed on the day is read from the spectrum itself or an acoustic sensor.

## 5. Scope: detection + tracking core, classification not in the core

- Detection + tracking is measurable against RTK ground truth with one drone type, fits the six-month window, and matches
  what the closest accepted systems evaluated. Classification needs many negative targets (birds, other drones) and more data.
- Keep the rotor signature as a **track-confirmation feature** (does a confirmed track carry blade lines?) and report its
  effect on false tracks as an ablation; multi-class identification is future work. The ablation may not be read off
  surviving tracks only: the rotor test and a persistence/SNR-only confirmation rule run over the *same* candidate-track
  list, at the same observation time and the same confirmation delay, on sessions that include moving clutter and
  non-target candidates (vehicles, pedestrians, birds, moving vegetation, logged by the §6.1 camera), and the report
  gives true-track rejection and time to confirm next to the false-track reduction, never the reduction alone.
- Count false alarms separately per resolution cell, per frame and per track; the sample-size arithmetic assumes
  independent target-absent trials, and needs 2,995 of them with no false alarm observed to bound a 1e-3 frame
  false-alarm probability at 95 % one-sided confidence (`outputs/isac_campaign_design_0915.json :
  false_alarm_design.zero_false_positive_independent_trials_needed`, `.target_frame_false_alarm_probability`,
  `.one_sided_confidence`). Consecutive CPIs of one session are correlated and are not that many independent trials, so
  uncertainty is taken at block or session level and the calibration captures are not the evaluation captures
  (`false_alarm_design.meaning`).
- Differentiation from LaSen has to come from: azimuth from the three sensing channels and sector antennas - the X410's
  fourth receive channel carries the coupled TX sample or the communication receiver (§6.1), so the angle observation
  uses three channels and not four (`outputs/isac_campaign_design_0915.json : hardware.x410_sensing_rx_used` = 3,
  `.x410_communication_rx_used` = 1; `tracking.constraint`, "three sensing elements"), and the rule that turns those
  three channels into a bearing (§6.4) is calibrated in its own experiment before the tracker uses it (§9) - then
  multi-drone association, communication metrics next to sensing, and site-specific design of antenna aim and height.

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
8. Campaign — 2-3 sites, 20-300 m, several heights, hover and 5-15 m/s, two drones, several days; release code and SigMF
   data. Two comparison families, reported apart. (a) Sensor comparisons, which deliberately change the hardware: single
   omnidirectional antenna, no sectors — they answer what the antennas buy, not what the twin decides. (b) Placement
   comparison, the only family a twin claim may be read from: antenna model, aim rule, channel count, aperture and RF
   budget held fixed while only mast position, height and aim differ, over four methods on the same candidate set — a
   fixed default placement, a written geometric heuristic, a measured search given the same calibration time and the same
   number of captures the twin needed, and the twin's placement — evaluated on flights and days that did not choose it
   (§9). Ablations: waveform, aim/sector, rotor-line confirmation, CPI length. A CPI-length sweep is receive-side policy
   on stored IQ and is not by itself an ISAC resource trade-off; a resource claim needs a transmit-side resource that
   actually changes — transmit airtime, transmit power, resource elements given to sensing, or burst/revisit scheduling —
   at a fixed offered load (`outputs/isac_campaign_design_0915.json : campaign[stage=isac_policy].inputs`, "fixed,
   random, covariance-only and proposed burst/revisit policies"; `.pass_rule`, "same payload demand, total RF
   energy/airtime or explicit Pareto comparison; processing window alone is not transmit overhead").

## 7. Month plan (assuming a mid-March 2027 deadline)

| Period | Work |
|---|---|
| late Sep-Oct 2026 | band and licence, antenna specs, X410 bench (isolation, calibration, streaming), detection-chain fixes, extend the isolated-pose path listing beyond the two cells already listed on 2026-09-15 (`outputs/dropout_paths_0916_diff.json`) and find why the path is missing, site 1 twin |
| Nov 2026 | first outdoor captures: background, reference reflector, hover, single-sector NR detection, ground-truth sync |
| Dec 2026 | sector angle, Stone Soup tracking, moving trajectories, two drones, LTE/Wi-Fi arms, communication metrics |
| Jan 2027 | main campaign at sites 1-2, rotor-line confirmation, comparison methods, twin-guided placement |
| Feb 2027 | ablations, cross-site test, simulation-capture comparison, writing |
| early Mar 2027 | abstract and paper |

## 8. Open decisions (user)

Carrier and outdoor licence; antenna models; X410 variant and NIC; whether the three-standard benchmark stays in the same
paper; real-time system or offline processing; pilot certificate, airspace and flight approval.

## 9. Central question and evaluation contract

**Central question.** Does a site-specific ray-traced twin, used only to place and aim one transmitter and three sector
receive antennas on a single X410, give better track continuity (§6.5) on a DJI Matrice 4E between 20 and 300 m than a
written geometric heuristic or a measured search given the same calibration budget, on flights and days the twin never
saw?

Fixed and written down before any result is looked at, and not changed afterwards: the detector threshold and the CFAR
guard/training geometry (calibrated on target-absent captures only); the tracker's M-of-N rule, gate and process-noise
model; the isolated-jump screening rule of §4; the rotor-confirmation rule of §5; the placement candidate set of §6.8(b)
and the rule each competing method uses to pick one candidate; the metric list of §6.5 and which single metric is the
headline. The size of difference that would count as a positive answer is not fixed yet; it is agreed with the user
before the January 2027 campaign, not after the numbers are seen.

Which data chooses settings and which data evaluates them:
- calibration sessions (target absent, plus reference-reflector runs) set thresholds and calibration constants and never
  appear in a reported detection or tracking number (`outputs/isac_campaign_design_0915.json :
  campaign[stage=offline_receiver].pass_rule`, "calibrate framewise false alarms on H0");
- placement-selection flights choose mast position, height and aim; final performance is reported only on evaluation
  flights from other days with other trajectories (`campaign[stage=offline_receiver].pass_rule`, "separate holdout
  trajectories and complex RX data"; `campaign[stage=outdoor_structure].pass_rule`, "holdout sessions");
- ground truth (Matrice 4E RTK, X410 GPS time) is for rendering and evaluation only and is excluded from the receive
  chain (`tracking.ground_truth_role`, "excluded from detection search, angle steering, range-axis calibration and
  association"). That list does not name the tracker's state prior, so it is said here: a target height taken from RTK is
  a prior, not truth. The early campaign's known-height runs (`tracking.constraint`, "known target height and front field
  of view") are reported as height-aided tracking, separately from unknown-height runs, and any oracle-angle or
  oracle-height run is labelled an upper bound, not a result;
- the mapping from the three sector channels to azimuth (§6.4) is calibrated in its own experiment — measured against an
  independent angle reference at known static positions, as the campaign ledger's hardware stage already requires
  (`campaign[stage=hardware_static]`), at several ranges, several target attitudes and with ground multipath present —
  and its error is reported before the tracker consumes it;
- headline numbers are reported per flight and per day as well as pooled, and the raw field, not any screened or replaced
  field, carries them (§4).

### 9.1 What "better track continuity" has to mean (to be fixed before the campaign)

The follow-up review of 2026-09-16 (`docs/FIXES_FOLLOWUP_0916.ipynb`) is right that the headline metric is still open.
These are the parts that must be written down, with numbers, before the January 2027 campaign, and never after seeing
results:

- **The same evaluation volume and the same denominator for every placement.** The volume is a fixed geometric region
  (range, azimuth and height limits around the site), identical for all four placement methods, decided from the site
  map and not from any method's coverage. The denominator is the seconds of RTK-truth track inside that volume, so a
  placement cannot win by being scored only where it happens to see well.
- **A position-matching tolerance and an identity rule.** A track point counts as matched when it is within a fixed
  distance of the truth position at that time; the tolerance is one number, fixed in advance. Identity switches are
  counted separately and never absorbed into continuity.
- **A coasting allowance.** Prediction without detection is allowed to bridge at most a fixed number of seconds; beyond
  that the track is broken at the last detection. A tracker that predicts a wrong position for a long time must not be
  paid for continuity.
- **What counts as an improvement.** The headline difference is agreed with the user in advance, and it only counts if
  the false-track rate and the position error are no worse at the same time (a three-part criterion, not one number).
- **Reported alongside, never instead:** time to first confirmation, track breaks per flight, false tracks per minute,
  and position error inside the matched segments.

### 9.2 From twin output to a chosen placement (the rule, fixed in advance)

A twin that is only "consulted" cannot be evaluated. The selection rule is written down before the campaign:

- **Which twin outputs enter the score.** Relative quantities only (the two-engine absolute-level rule stands): the
  predicted target-to-clutter ratio at the drone position, and the fraction of the trajectory prior where the drone
  stays inside the beam and above the ground-clutter floor. Free-space kernel agreement is a precondition for trusting a
  setting, not a term in the score.
- **A trajectory prior.** The candidate placements are scored against one written set of trajectories with weights
  (approach, crossing, hover at several heights), fixed before scoring.
- **One scalar.** The terms are combined into a single score with fixed weights, and the ranking of the whole candidate
  set is recorded before any flight is measured — so the twin's prediction is testable, not just its winner.
- **Regret, not only rank.** After the campaign, report how much the twin's chosen placement loses against the measured
  best candidate, and how far off its predicted ranking was (rank correlation over the candidate set). That number is
  the twin's contribution; "the twin's placement worked" is not.

### 9.3 Why holdout days are not enough

Moving the mast and measuring methods one after another confounds the method with wind, interference and flight
conditions. So:

- all four placement methods are flown in the **same sessions** where the site allows it, with the same trajectory set
  repeated per method, and the order randomised or balanced across sessions;
- one **fixed reference placement** is re-measured at intervals inside every session, so drift over the day is visible
  and can be removed;
- session and day enter the analysis as blocks; a difference that only appears between sessions is reported as such.
