<!-- 생성물 — `src/make_reports_index.py` 가 각 편의 여는 블록에서 읽어 쓴다. -->

# 다시 돌리기 — 편 → 명령 → 출력 → 소요

읽기 경로 ③ 이다. **리포트를 읽지 않는다** — 어느 숫자를 재생산하려는지만 알면 된다.
그 숫자가 사는 편을 아래 표에서 찾아 명령을 그대로 돌린다.

```bash
cd /home/yunjung/workspace/sionna2
PY=~/.venvs/py312/bin/python
```

노트북만 다시 조립하려면(계산 없음 · 수 초):

```bash
for f in src/build_part*.py; do PYTHONPATH=src $PY "$f"; done
PYTHONPATH=src $PY src/make_reports_index.py     # 색인·이 문서·논문 목차
PYTHONPATH=src $PY src/make_readme.py            # README
PYTHONPATH=src $PY benchmark/check_report_links.py   # 편 사이 참조 검사
```

기계용 사본은 [`outputs/reports_index.json`](../outputs/reports_index.json) 이다.
부 단위 재현 메모는 [`docs/repro/`](repro/) 에 있다.

---

## 부 0 — 지도

| 편 | 명령 | 출력 | 소요 |
|---|---|---|---|
| [00](../reports/00_map.ipynb) map | `PYTHONPATH=src python src/make_reports_index.py`<br>`PYTHONPATH=src python src/build_part00_map.py`<br>`PYTHONPATH=src python benchmark/check_report_links.py` | `outputs/reports_index.json` | 약 5초 (GPU 0장) |

## 부 1 — 스톡 엔진이 하는 일과 안 하는 일

| 편 | 명령 | 출력 | 소요 |
|---|---|---|---|
| [01](../reports/01_stock-says.ipynb) stock-says | `~/.venvs/py312/bin/python prior_work/src/build_prior_survey.py`<br>`PYTHONPATH=src python src/build_part01_stock_engine.py` | `outputs/prior_work_survey.json` | 약 1분 (CPU 만 쓴다) |
| [02](../reports/02_engine-paths.ipynb) engine-paths | `PYTHONPATH=src python src/build_part01_stock_engine.py` | `outputs/report00_sionna_anatomy.json`<br>`outputs/report00_sionna_probe.json`<br>`outputs/report00_evidence.json` | 약 1분 (GPU 0장 — JSON 읽기다) |
| [03](../reports/03_engine-amplitude.ipynb) engine-amplitude | `PYTHONPATH=src python src/figs_report00.py`<br>`PYTHONPATH=src python src/build_part01_stock_engine.py` | `outputs/report00_sionna_anatomy.json`<br>`outputs/report00_sionna_probe.json` | 약 1분 (GPU 0장) |
| [04](../reports/04_eight-factors.ipynb) eight-factors | `PYTHONPATH=src python src/figs_report00.py`<br>`PYTHONPATH=src python src/build_part01_stock_engine.py` | `outputs/report00_sionna_anatomy.json`<br>`outputs/report00_evidence.json`<br>`outputs/report00_po_case.json` | 약 1분 (GPU 0장) |
| [05](../reports/05_size-sweep.ipynb) size-sweep | `PYTHONPATH=src python src/figs_report00.py`<br>`PYTHONPATH=src python src/build_part01_stock_engine.py` | `outputs/report00_evidence.json` | 약 1분 (GPU 0장 — JSON 읽기와 그림 그리기다) |
| [06](../reports/06_decision-table.ipynb) decision-table | `PYTHONPATH=src python benchmark/build_report00_decision_map.py`<br>`PYTHONPATH=src python src/figs_report00.py`<br>`PYTHONPATH=src python src/build_part01_stock_engine.py` | `outputs/report00_decision_map.json`<br>`outputs/report00_po_case.json` | 약 1분 (GPU 0장) |
| [07](../reports/07_why-po.ipynb) why-po | `PYTHONPATH=src python benchmark/build_report00_po_case.py`<br>`PYTHONPATH=src python src/build_part01_stock_engine.py` | `outputs/report00_po_case.json` | 약 1분 (GPU 0장 — JSON 읽기다) |

## 부 2 — 선행연구

| 편 | 명령 | 출력 | 소요 |
|---|---|---|---|
| [08](../reports/08_census-published.ipynb) census-published | `~/.venvs/py312/bin/python prior_work/src/build_prior_survey.py`<br>`PYTHONPATH=src python src/report01_paper_facts.py`<br>`PYTHONPATH=src python src/figs_report01.py`<br>`PYTHONPATH=src python src/build_part02_prior_work.py` | `outputs/prior_work_survey.json`<br>`outputs/report01_paper.json` | 근거 5 s [^13] · 나머지 각 수 초 · CPU 만 쓴다 |
| [09](../reports/09_census-preprint.ipynb) census-preprint | `~/.venvs/py312/bin/python prior_work/src/build_prior_survey.py`<br>`PYTHONPATH=src python src/report01_paper_facts.py`<br>`PYTHONPATH=src python src/build_part02_prior_work.py` | `outputs/prior_work_survey.json`<br>`outputs/report01_paper.json` | 약 1분 (CPU 만 쓴다) |
| [10](../reports/10_procurement.ipynb) procurement | `~/.venvs/py312/bin/python prior_work/src/build_prior_survey.py`<br>`PYTHONPATH=src python src/report01_paper_facts.py`<br>`PYTHONPATH=src python src/figs_report01.py`<br>`PYTHONPATH=src python src/build_part02_prior_work.py` | `outputs/prior_work_survey.json`<br>`outputs/report01_paper.json` | 약 1분 (CPU 만 쓴다) |
| [11](../reports/11_procurement-catalog.ipynb) procurement-catalog | `~/.venvs/py312/bin/python prior_work/src/build_prior_survey.py`<br>`PYTHONPATH=src python src/report01_paper_facts.py`<br>`PYTHONPATH=src python src/build_part02_prior_work.py` | `outputs/prior_work_survey.json`<br>`outputs/report01_paper.json` | 약 1분 (CPU 만 쓴다) |
| [12](../reports/12_injection.ipynb) injection | `PYTHONPATH=src python src/build_part02_prior_work.py` | `outputs/injection_archive.json`<br>`outputs/injection_classification_audit.json`<br>`outputs/injection_verdict.json`<br>`outputs/injection_validation_hunt.json` | 약 1분 (CPU 만 쓴다 — 다른 워크플로의 원장을 읽는다) |
| [13](../reports/13_where-we-stand.ipynb) where-we-stand | `~/.venvs/py312/bin/python prior_work/src/build_prior_survey.py`<br>`PYTHONPATH=src python src/report01_paper_facts.py`<br>`PYTHONPATH=src python src/figs_report01.py`<br>`PYTHONPATH=src python src/build_part02_prior_work.py` | `outputs/prior_work_survey.json`<br>`outputs/report01_paper.json`<br>`outputs/sbr_kr_sweep.json`<br>`outputs/verify_cfar.json`<br>`outputs/s2r_prior.json` | 약 1분 (CPU 만 쓴다) |
| [14](../reports/14_borrowed.ipynb) borrowed | `PYTHONPATH=src python benchmark/build_report00_po_case.py`<br>`PYTHONPATH=src python src/build_part02_prior_work.py` | `outputs/report00_po_case.json` | 약 1분 (GPU 0장 — JSON 읽기다) |

## 부 3 — 표적 메쉬

| 편 | 명령 | 출력 | 소요 |
|---|---|---|---|
| [15](../reports/15_mesh-build.ipynb) mesh-build | `PYTHONPATH=src python src/make_report02_target.py --derive-only`<br>`PYTHONPATH=src python src/viz_mesh_gallery.py`<br>`PYTHONPATH=src python src/build_part03_target_mesh.py` | `outputs/report02_derived.json`<br>`outputs/meshfix_applied.json` | 약 2분 (GPU 0장 — 메쉬 조립과 렌더다) |
| [16](../reports/16_mesh-vs-real.ipynb) mesh-vs-real | `PYTHONPATH=src python src/make_report02_target.py --derive-only`<br>`PYTHONPATH=src python src/viz_mesh_photo.py`<br>`PYTHONPATH=src python src/build_part03_target_mesh.py` | `outputs/report02_derived.json`<br>`outputs/phantom4_scan_compare.json`<br>`outputs/real_cad_compare.json`<br>`outputs/community_compare.json` | 약 3분 (GPU 0장 — 사진 정합과 표 조립이다) |
| [17](../reports/17_materials.ipynb) materials | `PYTHONPATH=src python src/make_report02_target.py --derive-only`<br>`PYTHONPATH=src python src/viz_mesh_material.py`<br>`PYTHONPATH=src python src/build_part03_target_mesh.py` | `outputs/report02_derived.json` | 약 2분 (GPU 0장) |

## 부 4 — 산란 커널

| 편 | 명령 | 출력 | 소요 |
|---|---|---|---|
| [18](../reports/18_kernel-what.ipynb) kernel-what | `PYTHONPATH=src python src/make_report02_target.py --derive-only`<br>`PYTHONPATH=src python src/build_part04_kernel.py` | `outputs/report02_derived.json`<br>`outputs/prior_settled_sionna.json`<br>`outputs/report3_rt.json` | 약 2분 (GPU 0장 — 원장 조립이다) |
| [19](../reports/19_kernel-vs-stock.ipynb) kernel-vs-stock | `PYTHONPATH=src python benchmark/facet_count.py`<br>`PYTHONPATH=src python benchmark/runtime_benchmark.py`<br>`PYTHONPATH=src python src/build_part04_kernel.py` | `outputs/facet_count.json`<br>`outputs/facet_mechanism.json`<br>`outputs/runtime_benchmark.json` | 약 40분 (GPU 1장 — 스톡 솔버와 우리 커널을 같은 카드에서 돌린다) |
| [20](../reports/20_bistatic-exit.ipynb) bistatic-exit | `PYTHONPATH=src python benchmark/verify_sbr_defect_fixes.py`<br>`PYTHONPATH=src python src/build_part04_kernel.py` | `outputs/sbr_defect_fixes.json` | 약 25분 (GPU 1장) |
| [21](../reports/21_kernel-vs-reference.ipynb) kernel-vs-reference | `PYTHONPATH=src python benchmark/sbr_kr_sweep.py`<br>`PYTHONPATH=src python benchmark/verify_sbr_defect_fixes.py`<br>`PYTHONPATH=src python src/build_part04_kernel.py` | `outputs/sbr_kr_sweep.json`<br>`outputs/sbr_defect_fixes.json`<br>`outputs/report00_po_case.json`<br>`outputs/report02_derived.json` | 약 1시간 (GPU 1장 — kr 스윕이 대부분이다) |
| [22](../reports/22_po-knee.ipynb) po-knee | `PYTHONPATH=src python benchmark/lowfreq_anchor.py`<br>`PYTHONPATH=src python src/build_part04_kernel.py` | `outputs/lowfreq_anchor.json`<br>`outputs/lowfreq_attack.json`<br>`outputs/report00_po_case.json`<br>`outputs/report02_derived.json` | 약 15분 (GPU 0장 — 2D MoM 은 CPU 다) |
| [23](../reports/23_kernel-open-items.ipynb) kernel-open-items | `PYTHONPATH=src python src/build_part04_kernel.py` | `outputs/report00_po_case.json`<br>`outputs/ptd_wiring.json`<br>`outputs/report00_evidence.json` | 약 1분 (GPU 0장 — 이미 잰 값을 모은 표다) |

## 부 5 — 앵커와 검증

| 편 | 명령 | 출력 | 소요 |
|---|---|---|---|
| [24](../reports/24_anchor-mode.ipynb) anchor-mode | `PYTHONPATH=src python src/make_report02_target.py --derive-only`<br>`PYTHONPATH=src python benchmark/rcs_anchor.py`<br>`PYTHONPATH=src python src/build_part05_anchor.py` | `outputs/report02_derived.json`<br>`outputs/rcs_anchor.json`<br>`outputs/sigma_anchor.json` | 약 3분 (GPU 0장 — 이미 낸 σ 격자에 적합을 다시 건다) |
| [25](../reports/25_anchor-ledger.ipynb) anchor-ledger | `PYTHONPATH=src python src/make_report02_target.py --derive-only`<br>`PYTHONPATH=src python src/build_part05_anchor.py` | `outputs/sigma_anchor.json`<br>`outputs/report02_derived.json`<br>`outputs/lowfreq_anchor.json` | 약 2분 (GPU 0장) |
| [26](../reports/26_blind-p3.ipynb) blind-p3 | `PYTHONPATH=src python benchmark/p3_ours.py`<br>`PYTHONPATH=src python benchmark/p3_validation.py`<br>`PYTHONPATH=src python src/build_part05_anchor.py` | `outputs/p3_ours.json`<br>`outputs/p3_validation.json`<br>`outputs/lowfreq_anchor.json`<br>`outputs/lowfreq_attack.json` | 약 4시간 (GPU 1장 — 전대역 σ 를 다시 낸다) |
| [27](../reports/27_box-sphere-control.ipynb) box-sphere-control | `PYTHONPATH=src python benchmark/p3_validation_v2.py`<br>`PYTHONPATH=src python src/build_part05_anchor.py` | `outputs/p3_validation_v2.json`<br>`outputs/das_fleet_validation.json` | 약 2시간 (GPU 1장 — 대조군 형상마다 σ 를 다시 낸다) |
| [28](../reports/28_fleet-prereg.ipynb) fleet-prereg | `PYTHONPATH=src python benchmark/das_fleet_validation.py`<br>`PYTHONPATH=src python src/build_part05_anchor.py` | `outputs/das_fleet_validation.json`<br>`outputs/das_fleet_prereg.json`<br>`outputs/das_fleet_attack.json` | 약 3시간 (GPU 1장 — 네 기체를 문헌 격자에서 다시 낸다) |
| [29](../reports/29_sigma-robustness.ipynb) sigma-robustness | `PYTHONPATH=src python benchmark/sigma_sensitivity.py`<br>`PYTHONPATH=src python src/build_part05_anchor.py` | `outputs/sigma_sensitivity.json`<br>`outputs/report02_derived.json` | 약 20분 (GPU 1장 — 검출 사슬을 오차마다 다시 푼다) |

## 부 6 — 표적 사다리

| 편 | 명령 | 출력 | 소요 |
|---|---|---|---|
| [30](../reports/30_ladder-three.ipynb) ladder-three | `PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report16_synthesis.py` | `outputs/report16_synthesis.json` | 약 3 초 (CPU — 저장된 위상표 후처리) |
| [31](../reports/31_ladder-calibrated.ipynb) ladder-calibrated | `PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report16_synthesis.py` | `outputs/report16_synthesis.json` | 약 3 초 (CPU — 저장된 위상표 후처리) |
| [32](../reports/32_ladder-answer.ipynb) ladder-answer | `PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report16_synthesis.py` | `outputs/report16_synthesis.json` | 약 3 초 (CPU — 저장된 위상표 후처리) |
| [33](../reports/33_ladder-premature.ipynb) ladder-premature | `PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report16_verify_tautology.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report16_verify_kernel.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report16_verify_detector.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report16_synthesis.py` | `outputs/report16_verify_tautology.json`<br>`outputs/report16_verify_kernel.json`<br>`outputs/report16_verify_detector.json`<br>`outputs/report16_synthesis.json` | 약 40 분 (GPU 1장 — 커널 렌즈의 가림 재계산이 대부분) |

## 부 7 — 마이크로도플러

| 편 | 명령 | 출력 | 소요 |
|---|---|---|---|
| [34](../reports/34_md-paths-doppler.ipynb) md-paths-doppler | `PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_probe.py` | `outputs/report15_probe.json` | 약 7 분 (GPU 1장) |
| [35](../reports/35_md-slowtime.ipynb) md-slowtime | `PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15b_microdoppler_recompute.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15b_stamp_provenance.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_report15b_figs.py` | `outputs/report15b_microdoppler.json`<br>`outputs/report15b_series.npz` | 약 25 분 (GPU 1장 — 광선 추적이 6칸 × 4팔) |
| [36](../reports/36_md-two-engines.ipynb) md-two-engines | `PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_po_control.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_verdict_geomref.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_verdict.py` | `outputs/report15_po_control.json`<br>`outputs/report15_verdict_geomref.json`<br>`outputs/report15_verdict.json` | 약 30 분 (GPU 1장) |
| [37](../reports/37_md-rpm.ipynb) md-rpm | `PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15b_microdoppler_recompute.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15b_stamp_provenance.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_report15b_figs.py` | `outputs/report15b_microdoppler.json`<br>`outputs/report15b_series.npz` | 약 25 분 (GPU 1장 — 광선 추적이 6칸 × 4팔) |
| [38](../reports/38_md-occlusion.ipynb) md-occlusion | `PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15b_microdoppler_recompute.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15b_stamp_provenance.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_report15b_figs.py` | `outputs/report15b_microdoppler.json`<br>`outputs/report15b_series.npz` | 약 25 분 (GPU 1장 — 광선 추적이 6칸 × 4팔) |
| [39](../reports/39_md-blade-vs-body.ipynb) md-blade-vs-body | `PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15b_microdoppler_recompute.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15b_stamp_provenance.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_report15b_figs.py` | `outputs/report15b_microdoppler.json`<br>`outputs/report15b_series.npz` | 약 25 분 (GPU 1장 — 광선 추적이 6칸 × 4팔) |
| [40](../reports/40_md-attitude.ipynb) md-attitude | `PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15b_microdoppler_recompute.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15b_stamp_provenance.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_report15b_figs.py` | `outputs/report15b_microdoppler.json`<br>`outputs/report15b_series.npz` | 약 25 분 (GPU 1장 — 광선 추적이 6칸 × 4팔) |
| [41](../reports/41_md-calibration.ipynb) md-calibration | `PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_null_control_v2.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_verdict_geomref.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_verdict.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_attack_stats.py` | `outputs/report15_null_control.json`<br>`outputs/report15_verdict_geomref.json`<br>`outputs/report15_verdict.json`<br>`outputs/report15_attack_stats.json` | 약 35 분 (GPU 1장 — 널 팔 20 개) |
| [42](../reports/42_md-ray-budget.ipynb) md-ray-budget | `PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_attack_spp_ladder.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report15_attack_stats.py` | `outputs/report15_attack_spp_ladder.json`<br>`outputs/report15_attack_stats.json` | 약 36 분 (GPU 1장 — 사다리 전량 재추적) |
| [43](../reports/43_md-prf.ipynb) md-prf | `PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_md_range.py` | `outputs/md_range_sweep.json` | 약 12 분 (GPU 1장) |

## 부 8 — 조명원

| 편 | 명령 | 출력 | 소요 |
|---|---|---|---|
| [44](../reports/44_illuminators.ipynb) illuminators | `cd /home/yunjung/workspace/sionna2`<br>`~/.venvs/py312/bin/python src/viz_report2.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part08_illuminators.py` | `outputs/report2_waveform_rcs.json`<br>`outputs/report03_illuminators.json` | ① 3412 s [^11] (대부분 같은 스크립트의 RCS 스윕) · ② CPU 20초 안쪽 |
| [45](../reports/45_5g-double-cost.ipynb) 5g-double-cost | `cd /home/yunjung/workspace/sionna2`<br>`~/.venvs/py312/bin/python src/viz_report2.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part08_illuminators.py` | `outputs/report2_waveform_rcs.json`<br>`outputs/report03_illuminators.json` | CPU 20초 안쪽 (JSON 을 읽어 노트북을 조립한다) |
| [46](../reports/46_cost-ledger.ipynb) cost-ledger | `cd /home/yunjung/workspace/sionna2`<br>`~/.venvs/py312/bin/python src/viz_report2.py`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/verify_ambiguity.py`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/report4_fixups.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part08_illuminators.py` | `outputs/report2_waveform_rcs.json`<br>`outputs/report4_fixups.json`<br>`outputs/report5_results.json`<br>`outputs/report03_illuminators.json` | ③ 556 s [^15] · ④ CPU 20초 안쪽 |
| [47](../reports/47_range-convention.ipynb) range-convention | `PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/verify_ambiguity.py`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/report4_fixups.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part08_illuminators.py` | `outputs/verify_ambiguity.json`<br>`outputs/report4_fixups.json` | ② GPU 1장 수 분 · ③ 556 s [^11] |
| [48](../reports/48_waveform-check.ipynb) waveform-check | `cd /home/yunjung/workspace/sionna2`<br>`~/.venvs/py312/bin/python src/viz_report2.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part08_illuminators.py` | `outputs/report2_waveform_rcs.json` | ① 3412 s [^12] · ② CPU 20초 안쪽 |
| [49](../reports/49_ambiguity.ipynb) ambiguity | `PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/verify_ambiguity.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part08_illuminators.py` | `outputs/verify_ambiguity.json`<br>`outputs/report03_illuminators.json` | ② GPU 1장 수 분 · ④ CPU 20초 안쪽 |
| [50](../reports/50_doppler-fold.ipynb) doppler-fold | `PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/verify_ambiguity.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part08_illuminators.py` | `outputs/verify_ambiguity.json` | ② GPU 1장 수 분 · ④ CPU 20초 안쪽 |

## 부 9 — 검출기

| 편 | 명령 | 출력 | 소요 |
|---|---|---|---|
| [51](../reports/51_chain.ipynb) chain | `cd /home/yunjung/workspace/sionna2`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/verify_eca.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/viz_report04_detector.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part09_detector.py` | `outputs/verify_eca.json` | ECA 검증 · 그림은 각각 수 분 (GPU 1장) |
| [52](../reports/52_eca.ipynb) eca | `cd /home/yunjung/workspace/sionna2`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/verify_eca.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/viz_report04_detector.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part09_detector.py` | `outputs/verify_eca.json` | ECA 검증 · 그림은 각각 수 분 (GPU 1장) |
| [53](../reports/53_cfar-calib.ipynb) cfar-calib | `cd /home/yunjung/workspace/sionna2`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/verify_cfar.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/viz_report04_detector.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part09_detector.py` | `outputs/verify_cfar.json`<br>`outputs/prior_census.json` | CFAR 측정이 2717 s [^1] (GPU 1장) |
| [54](../reports/54_cfar-why.ipynb) cfar-why | `cd /home/yunjung/workspace/sionna2`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/verify_cfar.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/viz_report04_detector.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part09_detector.py` | `outputs/verify_cfar.json` | CFAR 측정이 2717 s [^6] (GPU 1장) |
| [55](../reports/55_observability.ipynb) observability | `cd /home/yunjung/workspace/sionna2`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/verify_observability.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/viz_report04_detector.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part09_detector.py` | `outputs/verify_observability.json` | 관측가능성 계산 · 그림은 각각 수 분 |

## 부 10 — 검출 결과

| 편 | 명령 | 출력 | 소요 |
|---|---|---|---|
| [56](../reports/56_geometry.ipynb) geometry | `cd /home/yunjung/workspace/sionna2`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_freespace_sigma.py`<br>`for D in mini5pro mavic4pro matrice4e phantom4 s1000plus; do \`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_freespace_range.py \`<br>`--stage all --mode W1,L1,G1 --drone $D; done`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part10_results.py` | `outputs/report13_freespace.json`<br>`outputs/verify_freespace.json`<br>`outputs/sbr_defect_fixes.json`<br>`outputs/phi_sweep.json` | σ 격자 · 검지거리 4단계 · 검증 · 스윕을 합쳐 7.8 h [^12] (GPU 2 [^13]장). 이 빌더 자신은 CPU 수 초다 |
| [57](../reports/57_sensitivity-chain.ipynb) sensitivity-chain | `cd /home/yunjung/workspace/sionna2`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_freespace_sigma.py`<br>`for D in mini5pro mavic4pro matrice4e phantom4 s1000plus; do \`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_freespace_range.py \`<br>`--stage all --mode W1,L1,G1 --drone $D; done`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part10_results.py` | `outputs/report13_freespace.json`<br>`outputs/verify_linkbudget.json`<br>`outputs/sigma_sensitivity.json`<br>`outputs/report05_derived.json` | σ 격자 · 검지거리 4단계 · 검증 · 스윕을 합쳐 7.8 h [^12] (GPU 2 [^13]장). 이 빌더 자신은 CPU 수 초다 |
| [58](../reports/58_shared-threshold.ipynb) shared-threshold | `cd /home/yunjung/workspace/sionna2`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_freespace_sigma.py`<br>`for D in mini5pro mavic4pro matrice4e phantom4 s1000plus; do \`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_freespace_range.py \`<br>`--stage all --mode W1,L1,G1 --drone $D; done`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part10_results.py` | `outputs/report13_freespace.json`<br>`outputs/report05_derived.json` | σ 격자 · 검지거리 4단계 · 검증 · 스윕을 합쳐 7.8 h [^10] (GPU 2 [^11]장). 이 빌더 자신은 CPU 수 초다 |
| [59](../reports/59_slope-anchor.ipynb) slope-anchor | `cd /home/yunjung/workspace/sionna2`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/sigma_anchor.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part10_results.py` | `outputs/sigma_anchor.json`<br>`outputs/lowfreq_attack.json`<br>`outputs/report05_derived.json` | σ 격자 · 검지거리 4단계 · 검증 · 스윕을 합쳐 7.8 h [^6] (GPU 2 [^7]장). 이 빌더 자신은 CPU 수 초다 |
| [60](../reports/60_r90.ipynb) r90 | `cd /home/yunjung/workspace/sionna2`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_freespace_sigma.py`<br>`for D in mini5pro mavic4pro matrice4e phantom4 s1000plus; do \`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_freespace_range.py \`<br>`--stage all --mode W1,L1,G1 --drone $D; done`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/sigma_anchor.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part10_results.py` | `outputs/report13_freespace.json`<br>`outputs/sigma_anchor.json`<br>`outputs/sigma_sensitivity.json`<br>`outputs/report05_derived.json` | σ 격자 · 검지거리 4단계 · 검증 · 스윕을 합쳐 7.8 h [^8] (GPU 2 [^9]장). 이 빌더 자신은 CPU 수 초다 |
| [61](../reports/61_rank-durability.ipynb) rank-durability | `cd /home/yunjung/workspace/sionna2`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_detection.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part10_results.py` | `outputs/sigma_sensitivity.json` | σ 격자 · 검지거리 4단계 · 검증 · 스윕을 합쳐 7.8 h [^10] (GPU 2 [^11]장). 이 빌더 자신은 CPU 수 초다 |
| [62](../reports/62_cpi-sweep.ipynb) cpi-sweep | `cd /home/yunjung/workspace/sionna2`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/sigma_sensitivity.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part10_results.py` | `outputs/cpi_guard_sweep.json` | σ 격자 · 검지거리 4단계 · 검증 · 스윕을 합쳐 7.8 h [^9] (GPU 2 [^10]장). 이 빌더 자신은 CPU 수 초다 |
| [63](../reports/63_cpi-residual.ipynb) cpi-residual | `cd /home/yunjung/workspace/sionna2`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/sigma_sensitivity.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part10_results.py` | `outputs/cpi_guard_sweep.json` | σ 격자 · 검지거리 4단계 · 검증 · 스윕을 합쳐 7.8 h [^11] (GPU 2 [^12]장). 이 빌더 자신은 CPU 수 초다 |
| [64](../reports/64_sigma-free-axis.ipynb) sigma-free-axis | `cd /home/yunjung/workspace/sionna2`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_detection.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part10_results.py` | `outputs/detection_rx_sweep.json`<br>`outputs/report05_derived.json` | σ 격자 · 검지거리 4단계 · 검증 · 스윕을 합쳐 7.8 h [^9] (GPU 2 [^10]장). 이 빌더 자신은 CPU 수 초다 |
| [65](../reports/65_target-model-swap.ipynb) target-model-swap | `cd /home/yunjung/workspace/sionna2`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part10_results.py` | `outputs/tm_result.json`<br>`outputs/tm_attack.json` | σ 격자 · 검지거리 4단계 · 검증 · 스윕을 합쳐 7.8 h [^10] (GPU 2 [^11]장). 이 빌더 자신은 CPU 수 초다 |
| [66](../reports/66_rx-elements.ipynb) rx-elements | `cd /home/yunjung/workspace/sionna2`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/experiment_detection.py`<br>`PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part10_results.py` | `outputs/detection_rx_sweep.json`<br>`outputs/report05_derived.json` | σ 격자 · 검지거리 4단계 · 검증 · 스윕을 합쳐 7.8 h [^9] (GPU 2 [^10]장). 이 빌더 자신은 CPU 수 초다 |

## 부 11 — 실측 설계

| 편 | 명령 | 출력 | 소요 |
|---|---|---|---|
| [67](../reports/67_hardware.ipynb) hardware | `PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/plan_measurement.py`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python -c "import sigma_anchor as S; S.write_measurement_plan()"`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/make_report06_measurement.py` | `outputs/report06_measurement.json`<br>`outputs/measurement_plan.json`<br>`outputs/report06_derived.json` | 약 10 초 (CPU) |
| [68](../reports/68_sigma-checklist.ipynb) sigma-checklist | `PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/plan_measurement.py`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python -c "import sigma_anchor as S; S.write_measurement_plan()"`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/make_report06_measurement.py` | `outputs/report06_measurement.json`<br>`outputs/measurement_plan.json`<br>`outputs/report06_derived.json` | 약 10 초 (CPU) |
| [69](../reports/69_site-geometry.ipynb) site-geometry | `PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/plan_measurement.py`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python -c "import sigma_anchor as S; S.write_measurement_plan()"`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/make_report06_measurement.py` | `outputs/report06_measurement.json`<br>`outputs/measurement_plan.json`<br>`outputs/report06_derived.json` | 약 10 초 (CPU) |
| [70](../reports/70_calibration-sphere.ipynb) calibration-sphere | `PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/plan_measurement.py`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python -c "import sigma_anchor as S; S.write_measurement_plan()"`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/make_report06_measurement.py` | `outputs/report06_measurement.json`<br>`outputs/measurement_plan.json`<br>`outputs/report06_derived.json` | 약 10 초 (CPU) |
| [71](../reports/71_subband.ipynb) subband | `PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/plan_measurement.py`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python -c "import sigma_anchor as S; S.write_measurement_plan()"`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/make_report06_measurement.py` | `outputs/report06_measurement.json`<br>`outputs/measurement_plan.json`<br>`outputs/report06_derived.json` | 약 10 초 (CPU) |
| [72](../reports/72_attitude.ipynb) attitude | `PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/plan_measurement.py`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python -c "import sigma_anchor as S; S.write_measurement_plan()"`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/make_report06_measurement.py` | `outputs/report06_measurement.json`<br>`outputs/measurement_plan.json`<br>`outputs/report06_derived.json` | 약 10 초 (CPU) |
| [73](../reports/73_three-layers.ipynb) three-layers | `PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/plan_measurement.py`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python -c "import sigma_anchor as S; S.write_measurement_plan()"`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/make_report06_measurement.py` | `outputs/report06_measurement.json`<br>`outputs/measurement_plan.json`<br>`outputs/report06_derived.json` | 약 10 초 (CPU) |
| [74](../reports/74_sim-vs-meas.ipynb) sim-vs-meas | `PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/plan_measurement.py`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python -c "import sigma_anchor as S; S.write_measurement_plan()"`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/make_report06_measurement.py` | `outputs/report06_measurement.json`<br>`outputs/measurement_plan.json`<br>`outputs/report06_derived.json` | 약 10 초 (CPU) |
| [75](../reports/75_decision-matrix.ipynb) decision-matrix | `PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/plan_measurement.py`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python -c "import sigma_anchor as S; S.write_measurement_plan()"`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/make_report06_measurement.py` | `outputs/report06_measurement.json`<br>`outputs/measurement_plan.json`<br>`outputs/report06_derived.json` | 약 10 초 (CPU) |
| [76](../reports/76_session-drift.ipynb) session-drift | `PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/plan_measurement.py`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python -c "import sigma_anchor as S; S.write_measurement_plan()"`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/make_report06_measurement.py` | `outputs/report06_measurement.json`<br>`outputs/measurement_plan.json`<br>`outputs/report06_derived.json` | 약 10 초 (CPU) |
| [77](../reports/77_size-law-differential.ipynb) size-law-differential | `PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/plan_measurement.py`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python -c "import sigma_anchor as S; S.write_measurement_plan()"`<br>`PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/make_report06_measurement.py` | `outputs/report06_measurement.json`<br>`outputs/measurement_plan.json`<br>`outputs/report06_derived.json` | 약 10 초 (CPU) |

