# Review of the 09-17 MobiCom ISAC strategy document

> Reviewed document: /workspace/sionna_mobicom_research_strategy_2026-09-17.md (outside git). Produced 2026-09-17 by a workflow: three independent lenses (novelty and MobiCom fit with a literature search, feasibility with the stated hardware, fit with repo assets) and a synthesis judge that re-checked disagreements. Judgement, not a user decision: the central question and the open questions in section 6 are the user's to answer.

# Synthesis verdict: the MobiCom ISAC strategy document (2026-09-17)

Document: `/workspace/sionna_mobicom_research_strategy_2026-09-17.md` (563 lines, last changed 08:56 UTC)

## Where the three lenses disagreed, and what I found when I checked

- **"Nobody runs a live NR gNB and senses with its own downlink" (novelty lens): partly wrong.** I fetched arXiv 2608.16705 (Saifullin, Ahmed, Alouini at KAUST; revised 2026-09-02). It runs a live OAI gNB with a commercial UE on n78 (3.348 GHz, X300). It does real-time monostatic radar on its own downlink. Goodput is 172.7 Mbit/s with sensing on and 172.9 Mbit/s with it off. Sensing bandwidth follows the scheduler: 58.29 MHz under load, about 4.44 MHz when idle. The paper names the coupling to the scheduler as a limitation. Its tests were indoor only (walking people, chairs), with no drone and no track-continuity metric. `grep` finds no citation of it anywhere in `/workspace/sionna` or in the strategy document. So the document's first success criterion (line 354) repeats a published result. What is still open is narrower: outdoor drones, track continuity, and control through scheduling.
- **Velocity ambiguity (feasibility lens #7): half right.** With our own transmitter, every downlink symbol can serve as reference. The unambiguous Doppler is then set by the symbol rate inside a burst (±14 kHz in the pilot table), not by "4 soundings per 10 ms". The real effect is that the periodic TDD gaps gate slow time. That creates Doppler replicas spaced at 1/(TDD period): 200 Hz, or ±8.6 m/s at 3.5 GHz, for a 5 ms period. This is exactly the phenomenon the document's hypothesis is about, so it belongs in the analysis, not on the risk list.
- **"Recover continuity at no extra energy or latency cost" (novelty lens #8): cannot be a strict constraint.** Moving downlink delivery in time costs latency. Filling idle slots costs energy. The claim has to be a Pareto front (continuity vs p99 latency vs radiated energy at a fixed offered load), not an equality.
- **Why 0957 is not running (fit lens): the cause has changed since that lens looked.** At 21:28 KST the CPU gate is 0.70–0.83, below the 0.85 cap, so it is no longer the binding limit.
  - Every running supervisor (0950–0957, 0959) was started with a total worker cap of 8, and 9 workers are running (G4 is at 4 against a cap of 3).
  - That is why 0957 is still at 0 of 10 lines launched and 0959 at 1 of 4. Whichever supervisor polls first gets the next free slot.
  - The workers running now are 0952 el=0 with a 1e6 path cap, el −60 aim-offset runs, a street canyon at el −60 with a 16e6 cap, outdoor01_bldg at el −30, and ground at el −60 with target orientation. None of these feeds the strategy's question.
- **Confirmed in the repo:**
  - `docs/RESUME_0917.md:10` and plan §9 (`MOBICOM_PIPELINE_PLAN_0916.md:197-200`) still name twin-guided placement as the central question.
  - `src/experiment_detection.py` is passive chamber ECA/CAF with a known target cell ("챔버 기하" = chamber geometry, docstring).
  - The document has no band, no licence, no range target, and no dates or go/no-go dates. Frequency appears once, as "to confirm" (line 79).
  - Link-budget ledger `rmax_rows[123]` = 89.2 m (+5 dBm, 12 dBi, 10 ms, −20 dBsm, Swerling 1).
  - Pilot: at equal integrated SNR, Doppler estimates stay within about 5 Hz from k=1 to k=28, and body Doppler aliases at k=56. The pilot itself says "the folding itself is sampling-theorem arithmetic" (`OFDM_PILOT_0917.md:265`). With ±10 Hz clutter drift the frame false-alarm rate is 0.783 against a 1e-2 target (:158).
- **The user's own constraint.** `AGENTS.md:33` asks for a Wi-Fi/LTE/5G NR waveform benchmark. Two lenses say drop it; that is the user's call, not ours (see §6).

---

## 1. Overall verdict

**Grade: B−. Follow its rules, not its scope.**

- **As an evaluation and claims guide it is A-grade.** Its rules on references, resource accounting, H0 data, holdouts and implementation level are correct and match the repo's own ledgers.
- **As a plan to execute it is C-grade.** It has no dates, no band or licence, and no range target. It misses the closest prior art (KAUST 2608.16705). It was written before the pilot landed (pilot commit e012482d at 09:47 UTC). It points to the wrong code as "current". It carries four research directions for one person with about 6 months left.
- **The core hypothesis is not yet sharp enough to survive review.** "Equal total resource, different arrangement" is only obviously true past a sampling limit, unless it is restated around fades, clutter and real traffic.

It is worth following once it is narrowed to one question, dated gates are added, and it is reconciled with plan §9.

## 2. What it gets right (top 5)

1. **Rules on references and resource accounting (§4.1 :171-173, §4.4, §9 stop rules :490-495).**
   - The payload must change and be decoded.
   - Reprocessing stored IQ with a different CPI is not a resource trade-off.
   - A gain that comes only from extra energy or deadline violations does not count.
   - This matches plan :172-177 and `isac_campaign_design_0915.json : campaign[stage=isac_policy].pass_rule`. Pilot §4.3 supports it: a stale reference put the strongest peak within one cell of the target in 0 of 4 frames.
2. **Separate H0 sets for calibration and evaluation, with the UE live and the drone absent (:143, :230).** The pilot shows why: thresholds set on static clutter give a 0.783 frame false-alarm rate under ±10 Hz drift.
3. **Implementation-level ladder (§3.6 :147-153).** Custom OFDM, then OAI replay, then a live link, with trace-based evaluation kept separate from live control. This is the fallback structure the schedule needs.
4. **Receiver first, placement fixed, minimum ray tracing (§6.2 :285-287, §6.4 :312-316, §9 :475, :484-486).** Delay-bearing channels are required. A single field E(t) cannot give per-delay paths. Solver path loss must not be written up as track breaks (:279-281). Queue 0957's header already follows this.
5. **It admits overlap and the knob it can really control (:53-61, :373).** It says novelty is unverified, names LaSen, CARTS and full-duplex LTE/NR radar, and limits control to one standard-permitted scheduling variable a COTS UE follows unchanged. The control set in §7.4 is right: default, periodic, random at equal budget, covariance-only, and a prior sparse receiver.

## 3. What is weak, missing or wrong (top 5, with evidence)

1. **It misses KAUST 2608.16705 and overstates what is new.**
   - The §7.3 first success criterion (:354) is KAUST's result on an X300.
   - The gap-arrangement idea is also covered in parts by others:
     - DASC'26 (arXiv 2606.21677, verified): adaptive 5G sensing allocation for UAV M-of-N continuity under load, simulation only.
     - LaSen: non-uniform NR resources with the same airframe.
     - SenCom (MobiCom'23): sensing from irregular traffic.
     - ElaSe and van Keuk–Blackman: state-driven revisit.
   - "Tracker uncertainty + queue state" (:53) will be read as recombination.
2. **The first hypothesis can be derived on a whiteboard as written (§1 :49, §7.1).**
   - The pilot shows spacing does nothing at equal integrated SNR until aliasing sets in.
   - The testable version is different: whether gaps land on target fades (aspect-dependent), during clutter drift, or during low-load periods where energy per CPI collapses.
   - The document never asks what share of track breaks come from gaps versus clutter drift versus SNR or attitude fades. If gaps are a minor cause, the paper's core is wrong.
3. **No band, licence, range target, equipment list or schedule.**
   - Korea 3.40–3.70 GHz is held by the operators; the private 5G band is 4.72–4.82 GHz (n79), granted per site. Plan :64 and :192 list the licence as unverified. The strategy document never mentions a licence.
   - Range at realistic duty is far below plan §9's 20–300 m. Ledger: 89 m at full duty. Scaling by the fourth root of energy gives about 82 m with a ~70 % downlink TDD pattern and about 43 m at idle-scheduler occupancy (KAUST's 4.44/58.29 MHz ratio).
   - Missing equipment: COTS UE module, programmable SIMs and reader, a separate OAI host with a QSFP NIC, antenna models, and an outdoor shelter (X410 is rated indoor only).
   - No dates, no go/no-go points, and the 11-month MobiCom resubmission bar (plan :22) goes unmentioned.
4. **Too broad, and it conflicts with the repo's recorded central question.**
   - It keeps live OAI, custom OFDM, a three-standard P2 (:473), a new tracker/policy, the twin, and a CW/FMCW alternative (§8, 70 lines). It warns about this itself (:35) and keeps them anyway.
   - `RESUME_0917.md:10` and plan §9 still say twin placement, and plan §9.1-9.3's evaluation contract is written for placement. The 0957/0958 headers already follow the strategy document.
   - Two central questions are live at once.
5. **Stale or wrong about the repo, and silent on what the ray tracer cannot give.**
   - P0 "custom OFDM two delays, motion, H0" (:468) is mostly done by the pilot. What remains: decoding in the same waveform, CFO/timing, leakage, burst/gap patterns.
   - §5.3 (:249) names `src/experiment_detection.py` as the "current detection experiment". It is passive bistatic in chamber geometry, which house rules exclude. The base should be `benchmark/ofdm_receiver_pilot_0917.py`.
   - It omits `src/waveforms.py` (`wifi_80211ac` 5.21 GHz, `lte_downlink` 1.843 GHz, `nr_downlink` 3.5 GHz: uncoded, on different carriers, which breaks its own common-carrier rule at :199).
   - It fixes no numerology: design 15 kHz vs pilot and plan 30 kHz.
   - It omits OAI integration facts: the X410 is not in OAI's COTS-UE tutorial list, the IQ recorder saves antenna 0 only, and CARTS hit missing aperiodic SRS support.
   - It omits TX–RX residual frequency offset (KAUST: clutter suppression −16.4 dB at the bad carrier vs 38.0 dB after correction).
   - It never says what the current ray-tracing setup cannot supply: H0 data, moving clutter, trajectories, the UE channel, sector angles, or anything beyond 15–30 m. The ground is a mirror (S=0), so diffuse scattering acts on the drone only.

## 4. Concrete changes I would make

1. **Rewrite the central question as one sentence** and record it in `RESUME_0917.md` and plan §9 (the user decides; the main session edits):
   > On a live NR gNB serving a COTS UE, how much of outdoor drone track discontinuity comes from traffic- and TDD-driven observation gaps, and does gNB-side transmission timing or reference insertion move the continuity–latency–energy Pareto front beyond default scheduling, periodic reference insertion, and a LaSen-style non-uniform receiver?
   
   Rewrite §9.1-9.3's evaluation contract for this question. Twin placement becomes a robustness appendix at most.
2. **Replace hypothesis 1 with a decomposition of break causes.**
   - Log OAI slot and PRB occupancy traces with a COTS UE under real apps (video, web, VoIP, bursty upload). This is bench work with no drone and no echo.
   - Replay them on CPU through the pilot receiver, with target fading taken from stored cells and clutter drift.
   - Report the share of miss runs and track breaks due to gaps, fades, drift and aliasing, against a threshold written in advance.
   - Only if gaps pass the threshold build the policy. Otherwise pivot the core to clutter-robust tracking under live traffic.
3. **Cite and position against KAUST 2608.16705 and DASC'26 2606.21677.** Make LaSen-style reconstruction a baseline and also a combination arm (receiver plus policy), not just related work.
4. **Add §0, "Hard constraints and gates", with dates:**
   - **By 09-25:** band chosen (n79 private 5G or other) checked against UE module and antenna labels; experimental permit query and filing; UE module, SIMs, reader and OAI host NIC ordered.
   - **CP1, 10-16:** cabled OAI on the X410 with the UE attached and 30 min stable iperf; bench isolation, TX–RX residual offset, ADC headroom.
   - **CP2, 11-06:** tap working: TX grid plus one sensing RX recorded during downlink with timestamps; corner reflector at a known range; goodput with sensing on vs off (the KAUST replication).
   - **CP3, 11-27:** licence and flight approval; outdoor hover detection at 50 m or more with drone-absent H0 under live traffic.
   - **CP4, 12-18:** gap experiment at fixed offered load.
   - **CP5, 01-22:** two sites.
   - Each gate has a written fallback: custom OFDM over the air with OAI-derived gaps, or trace level only. Failing CP4 or CP5 means skip the winter round rather than spend the 11-month bar.
5. **State a range claim of 100 m or less in the document.** Recompute the ledger at real TDD duty, PRB occupancy and integration time before any flight matrix.
6. **Cut or demote.**
   - Move §8 CW/FMCW to a separate one-page note.
   - Make the Wi-Fi/LTE arm waveform-level only: standards-derived grids and gap statistics replayed on one carrier, labelled as trace-based. Live AP–STA and eNB–EPC stacks go out of the MobiCom paper, if the user agrees (AGENTS.md:33 constraint).
   - Drop the P3 angle and 2D tracking from this paper.
7. **Fix the stale items.**
   - Mark P0 as "pilot done; remaining: decoding in the same waveform, CFO/timing, leakage, burst/gap masks, tracker".
   - Replace the `experiment_detection.py` reference with the pilot script.
   - Fix numerology (30 kHz at 3.5 GHz or n79) before any dependent cell.
   - Add TX–RX residual offset per carrier, TDD-gating Doppler replicas, and the OAI multi-RX recording change (C real-time path, antenna-0-only recorder) to the §3.5 checklist.
8. **Add a §6.5 simulation contract.**
   - Ray tracing supplies relative quantities only: in-bin target fluctuation over aspect, rotor-to-body ratio, drone–ground ghost level and delay.
   - Absolute SNR comes from the link-budget ledger, never from PathSolver levels.
   - Body motion is added analytically.
   - Traffic and gaps come from OAI traces.

## 5. What this means for the GPU queue now

The critical path is CPU work plus X410/OAI bring-up. Beyond 0957, the GPU work of real value over the next two weeks is about 3–10 slot-hours. Free cards are not a reason to buy lines.

**High value**
- **0957 (per-path a/tau dumps, open sky and ground only, aimed tr38901, 15/30 m).** It is the only running or queued work that feeds the receiver. It is starved right now: 0 of 10 lines launched, because all supervisors cap at 8 total and 9 workers are running. The main session should give it the next cards 3/4 slots (for example by holding the unlaunched lines of 0952, 0953, 0955 and the 0954/0956 pair via `GPU_HOLD.json`, which supervisors re-read each loop). The user or main session owns that change. Run check 0 on the first GPU sidecar before reading anything.
- **CPU checks before any further GPU purchase:**
  - (a) Feed 0957 path lists through the pilot receiver at 20 and 100 MHz, with body translation added analytically.
  - (b) Test whether open-sky E(t) equals the in-bin response. Drone diagonal 0.78 m is under the 1.5 m cell at 100 MHz. If it holds, the stored 2.1.0 open-sky aimed cells at el −15/−30/−60 are already a target-fluctuation library.
  - (c) Decimate 19.7 kHz records to the OFDM symbol rate (28,029 Hz at 30 kHz with CP 72).
  - (d) Measure in-bin level spread over aspect on stored cells. Pilot Pd goes from 0.16 to 0.92 over 4 dB, so few-dB fades decide miss runs.
- **Conditional:**
  - Azimuth-aspect open-sky cells (az 90/180, el −15, 15 m, aimed, 4,096 positions, about 2 slot-h). Buy only if (d) shows a spread of 3 dB or more; the ray-count sensitivity is already 0.6–0.8 dB.
  - A `--prf 28029` twin of 0957 lines 1–2. Buy only if (c) error exceeds a bound written in advance.

**Low value now (hold the unlaunched lines, re-dry-run before any release)**
- Remaining 0952 cap-ladder rungs (including the el=0 1e6 shards currently running).
- 0959 part (a).
- 0953 (other airframes; the Matrice 4E is the only real drone).
- 0954/0956 aim offsets at el −60.
- 0955 A/B deck rechecks and C street canyon at a 32e6 cap.
- Any mast-height or cap ladder.
- Omni-only cells.
- 8,192-position cells meant as receiver input.
- Rotor presets.
- 5.8 GHz before the band decision.
- Three-sector receive cells (need real antenna patterns).
- UE-channel ray tracing (no GPU needed).
- 0958 walls, only on its own release triggers.

**Principle:** a GPU line is worth buying only if its readout changes a receiver, tracker, band or placement decision named in the rewritten §9. Solver-behaviour characterisation beyond the cells the receiver will actually use does not qualify. Running lines should not be killed; this is about what launches next.

## 6. Open questions only the user can answer

1. **Central question:** is the paper ISAC observation gaps and scheduling, or twin-guided placement? Can plan §9 and RESUME be rewritten to match?
2. **Band and licence:** which carrier (n79 4.72–4.82 GHz private 5G, an n77 slice, other)? Has the lab or university applied for, or does it hold, an experimental station permit or a private-5G licence at a flight site? Who files, and when?
3. **Equipment and budget:**
   - Can you buy a COTS 5G module (RM520N-class), programmable SIMs and reader, and a dedicated OAI host with a 100 GbE QSFP NIC now?
   - What are the six directional antennas (model, band, gain)?
   - Is there an outdoor enclosure and power for the X410?
4. **Deadline flexibility:** is MobiCom winter 2027 hard, or are MobiSys/SenSys 2027 or a later MobiCom round acceptable if CP3 slips? Is a workshop or demo fallback acceptable?
5. **The Wi-Fi/LTE/NR benchmark (AGENTS.md:33):** must it be live stacks inside this paper, or is a same-carrier, waveform- and trace-level comparison enough?
6. **Real-time requirement:** must sensing run online during the live link, or is live communication with offline sensing plus trace-based policy evaluation acceptable for the first paper?
7. **Field logistics:**
   - Who flies the Matrice 4E while you run the X410?
   - Is a second outdoor site available?
   - Is a second physical drone available for multi-target runs?
   - Pilot certificate and flight/filming approval status?
8. **Deck and queue load:** how much weekly team-meeting work still depends on solver-behaviour queues (0952–0956, 0959)? That decides whether holding them costs you slides you need.