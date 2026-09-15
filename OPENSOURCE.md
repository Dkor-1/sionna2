# Open-source replacement and verification map (open-source reliance map)

Goal (user policy, 2026-07-20): **replace what we built ourselves with open source as far as possible** to raise reliability and
reduce repeated manual work. The principle, however, is **"verify, then replace"** — swapping out code that has already been
verified against theory (plate/sphere) wholesale without verification would **lower** reliability instead. So each piece is replaced in 2 steps:
① **cross-verify** against the open-source tool → ② if they agree within tolerance, **move the authoritative source to the open-source tool**.

Background research: `prior_work/` (pw01 papers · pw02 tools · pw03 positioning) · `prior_work/outputs/prior_work.json`.

## Replacement verdict per piece

| Our implementation | Open-source replacement/verifier | License | Replace now? | Plan |
|---|---|---|---|---|
| **Detection chain ECA·CAF·CFAR** (`passive_process.py`) | ⭐ **pyAPRiL** (GPLv3, ECA/ECA-S·CAF·CA-CFAR·DoA) | GPLv3 | ✅ **Verified in practice** | `benchmark/verify_pyapril.py`: in all **3 runs of a wideband QPSK reference signal (differing only in seed)** **the range bin of the CAF peak matched the ground truth** (range_bin_error=0), and CFAR also fired at the true cell (`detected_at_truth=true`·`n_fired=5` in ledger `outputs/verify_pyapril.json`). In these 3 runs it worked without a waveform-specific module (from the reference I/Q alone) — but only one waveform family was tested, so the general claim 「파형 무관」 [waveform-agnostic] is not demonstrated by this. ⛔Correction 2026-09-06 — the first edition wrote this cell as 「NR/WiFi/LTE 3모드」 [NR/WiFi/LTE, 3 modes] · 「파형 무관」 [waveform-agnostic] (in fact they are random-seed variants of the same QPSK generator; real standard waveforms were verified separately in report05), and also wrote 「detected_at_truth=false」, which a 2026-07-24 rerun overturned (docs/AUDIT_FINDINGS_0722.md C-3). Only the large MC keeps `detection_gpu.py` (GPU), cross-checked against pyAPRiL |
| **SBR+PO drone RCS** (`rcs_sbr.py`·`rcs_po.py`) | (no library replacement) | — | ✖ Keep our own | Of the three routes prior work uses (commercial full-wave · in-house SBR+PO · point scatterers), we follow **in-house SBR+PO** (the same method as BVH SBR+PO arXiv:2604.09243). RadarSimPy is not adopted because its C++ engine is closed (gated); RaytrAMP is monostatic- and PEC-only, which is insufficient. Verification: theory (plate/sphere) + **measured literature RCS anchors** (report08) |
| **Propeller micro-Doppler** (`microdoppler.py`) | (keep our own) | — | ✖ | Same kind of approach as prior work (Costa & Thomä, IEEE J-STEAP 2025), which modelled the propeller as thin-wire point scatterers + PO. Can be compared with measured micro-Doppler |
| **Waveform synthesis** (`waveforms.py`) | **Sionna PHY** (`sionna.phy.nr`, OFDM) | Apache-2.0 | ✅ OFDM modulation step only | `waveforms_sionna.crosscheck()` feeds the **same resource grid and CP lengths that `waveforms.py` built** to our modulator and to Sionna's `OFDMModulator`: NMSE −138.3 dB (Wi-Fi), −135.6 dB (LTE), −135.2 dB (NR) (`outputs/report2_waveform_rcs.json : crosscheck.*.nmse_db`). That checks the inverse FFT and CP insertion for a given grid. It does **not** check resource mapping, reference-signal placement or conformance to the Wi-Fi/LTE/NR standards, because the grid itself comes from our code. (Narrowed 2026-09-16 — the earlier edition said 「Already verified」 and 「Keep Sionna PHY as the waveform source of truth」.) |
| **Delay channel** (`sionna_chain.py`) | **Sionna PHY** (`cir_to_time_channel`) | Apache-2.0 | ✅ Already in use | Keep |
| **Tracking** (future work, not implemented) | **Stone Soup** (EKF/UKF · particle · JPDA, MIT) | MIT | ✅ Adopt (do not write it ourselves) | Write only the bistatic custom nonlinear measurement model (ρ_b=R_T+R_R−L, f_D=(û_T+û_R)·v/λ) |
| **Measurement (X410 OTA bistatic)** | **OpenISAC** + **GNU Radio** (SigMF I/Q) | Open source / GPLv3 | ✅ Adopted for the measurement stage | OTA bistatic synchronisation ties directly into the X410 plan. Unify simulated (Sionna) I/Q and measured (X410) I/Q in the **same SigMF format** → the same processing code |
| **Drone mesh CAD** (`drone_cad.py`) | (no replacement — official DJI CAD is not published) | — | ✖ | Keep parametric. Verification via scans of the real airframe and measured literature RCS anchors |

**Reference (not code to port):** NIST 5GNRad (usnistgov/5GNRad, h=h_bg+h_target architecture) · NIST ISAC-PLM (WiFi 802.11bf sensing, but 60GHz) · MATLAB (1st baseline) · OAI (real 5G NR, final stage) · openEMS (full-wave RCS).

## ⚠ Correction to the 1st survey
An earlier edition said "there is no drop-in open source for passive bistatic ECA", but that was **wrong** — **pyAPRiL** is
exactly that drop-in (GPLv3, verified on DVB-T/FM measurements). Pointed out by the user's in-depth survey and confirmed directly on GitHub.

## 5-stage replacement roadmap
1. Minimum working pipeline: Sionna RT+PHY channel → **pyAPRiL** ECA/CAF/CFAR (← we are here)
2. Tracking: +**Stone Soup** (bistatic EKF/UKF)
3. Drone physics: multi-scatterer (1 body + 4 motors + 8~16 blade tips) — with SBR+PO we are already here
4. AI · sim-to-real: +PyTorch (classification · domain randomization)
5. Measurement: +**OpenISAC**+**GNU Radio**+**X410** (unify sim↔real with SigMF)

## Why "verify, then replace" (reliability logic)

- The **detection chain** was actually replaced with pyAPRiL (open source) and **the CAF range bin matched** — what was tested is 3 runs of a wideband QPSK reference signal (differing only in seed), and CFAR also fired at the true cell (`outputs/verify_pyapril.json`: `detected_at_truth=true`·`n_fired=5`). ⛔Correction 2026-09-06 — the first edition's 「파형무관하게」 [regardless of waveform] is withdrawn (there is only one waveform family; real standard waveforms are in report05). 「CFAR 발화까지는 아님」 [not as far as CFAR firing] is also an old value overturned by the 2026-07-24 rerun.
- For **RCS**, library replacement has high friction (RadarSimPy = closed engine, RaytrAMP = monostatic·PEC). So we follow the
  **in-house SBR+PO** approach prior work uses, but establish reliability with **measured literature RCS anchors** (stronger than sim vs sim).
- Principle: where replacement pays off and is reproducible (detection = pyAPRiL, measurement = OpenISAC, tracking = Stone Soup), use a library;
  where replacement friction is high and the code is already verified (RCS = SBR+PO), follow prior work's approach plus measured anchors.

## Where this is reflected (reports)

- report06 §3 — the RCS-limit claim is supported by prior work (Deterministic-Modeling EuCAP · the Sionna-RT founding paper) + 3 categories of workaround.
- report07 — states that SBR+PO is the method prior work (BVH SBR+PO) uses; verification is theory + measured anchors.
- report08 — marks the position of prior methodology (diffuse S vs RCS injection vs SBR/PO) in the literature comparison.
- report08 — **absolute-value anchors from a table of measured literature drone RCS** (cross-verification). report12 §6 — pyAPRiL comparison · architecture consistency.
- prior_work/ 3 papers — full evidence and sources.
