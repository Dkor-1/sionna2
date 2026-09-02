# Sionna RT 비결정성 — 공개 자료와 우리 관측의 관계 (2026-09-02)

바탕 문서: `/workspace/Sionna_RT_Diffraction_Nondeterminism_Reproducibility_2026-09-02.md`
(GitHub Discussion #1175 · #851 · #917 · #1142, Issue #1071 정리)

## ⭐한 줄

**우리가 오늘 잡은 것은 #1175 이 아니다.** #1175 은 `diffraction=False` 로 사라지는데,
**우리 것은 `diffraction=False` 에서 난다.** 자리가 다르다.

## 1. 두 기작을 가른다

| | **#1175 (공개 보고)** | **우리 관측 (2026-09-02)** |
|---|---|---|
| 어디 | `RadioMapSolver` 의 **회절 wedge** 수집·표본추출 | `PathSolver` 의 **정반사 사슬 중복제거** |
| 파일 | `radio_map_solvers/radio_map_solver.py` | `path_solvers/sb_candidate_generator.py:484-498` |
| 기작 | wedge 를 해시 표에 넣는 **순서**가 병렬 실행에 좌우 → 같은 seed 라도 뽑히는 wedge 가 달라짐 | 정반사 사슬의 해시 통을 **먼저 올린 스레드만** 그 경로를 남김(`dr.scatter_inc`) → 경로가 **통째로 사라짐** |
| 회절 끄면 | **사라진다**(보고자 확인) | ⛔**그대로 난다** |
| 크기 | path_gain 최대 **~3.7 dB** | 계단 **−3.5 dB**(2/3) · 지면 반사 탈락 **−51 dB** |
| 우리가 쓰나 | ⛔안 쓴다(`RadioMapSolver` 는 렌더링에만) | ✅**측정 전 경로가 여기를 지난다** |

⭐**우리 팔이 회절을 끈 상태라는 확인**(`elevation_sweep_md.py:566-568`):
```python
r_, d_, e_, f_ = bits            # R0D0E0F1
sw = dict(refraction=r_, diffraction=d_, edge_diffraction=e_)
diffuse = f_
```
⇒ `R0D0E0F1` = refraction **False** · diffraction **False** · edge **False** · diffuse **True**.
그리고 `PathSolver.__init__` 이 `SBCandidateGenerator()` 를 만든다(`path_solver.py:117`) —
**회절 여부와 무관하게** 후보 생성기를 지난다.

⇒ **회절을 꺼도 재현이 안 되는 PathSolver 사례**다. 공개 논의에 이 경우는 없다.

## 2. 문서가 권하는 것 중 **우리가 못 쓰는 것**

설치본 `sionna 2.0.1` 의 `PathSolver.__call__` 인자 전체:
```
scene · max_depth · max_num_paths_per_src · samples_per_src · synthetic_array
los · specular_reflection · diffuse_reflection · refraction
diffraction · edge_diffraction · diffraction_lit_region · seed
```
⛔**`rr_depth` 가 없다** — 문서의 `rr_depth=-1` 권고는 `RadioMapSolver` 쪽이다.
⛔**`deterministic` 옵션도 없다**(#1142 에서 «향후 release» 로 예고된 것).

⚠우리 `--det`(경로를 지연 기준으로 정렬해 합)은 **이 문제를 못 고친다** — 순서를 고정할 뿐,
**애초에 안 돌아온 경로는 되살릴 수 없다.**

## 3. 문서의 «크기 기준» 으로 본 우리 값

문서는 `~1e-5 dB` = 부동소수점 축약 수준, `≥ 1 dB` = 알고리즘 비결정성으로 가른다.

| 우리 값 | dB | 판정 |
|---|---|---|
| 정상 자세끼리 재실행 차 | `|ΔE|/|E|` 중앙 **1.57e-16** | 기계 정밀도 — 부동소수점 축약 |
| 계단(2/3) | **−3.52 dB** | ⭐알고리즘 비결정성 |
| 지면 반사 탈락 | **−51 dB** | ⭐⭐알고리즘 비결정성 |

⇒ 문서의 기준으로도 **명백히 알고리즘 쪽**이다. 그리고 #1175 의 3.7 dB 보다 크다.

## 4. 확산(diffuse)의 몫 — 아직 안 갈렸다

문서는 재현성을 위해 `diffuse_reflection=False` 도 권한다. 우리 자료에서도 조짐이 있다 —
**확산을 끈 네 팔은 깊은 전멸이 0 개**이고 최소비가 0.579 에서 멈춘다(890 표본, 기대 ~13 건).

⛔**다만 그 네 팔은 전부 회절이 켜져 있다**(`R0D1E1F0` · `R0D1E0F0` · `R1D1E1F0` · `R1D1E0F0`).
**회절과 확산을 둘 다 끈 팔(`R0D0E0F0`)을 우리는 한 번도 안 돌렸다.**
⇒ 「둘 다 끄면 깨끗한가」는 **아직 모른다.** 그것이 문서 권고를 우리 설정에서 시험하는 유일한 칸이다.

⚠**팀 규약은 「확산은 항상 켠다」**이다. 이 칸은 **비교 팔이 아니라 진단**으로만 쓴다 —
돌린다면 그렇게 이름 붙이고, 다섯 팔 축에는 올리지 않는다.

## 5. 남는 것

1. ⭐`R0D0E0F0` 진단 칸 — 회절·확산을 둘 다 꺼도 계단이 남나 (규약 예외라 승인 필요)
2. 해시 통 수(`max_num_paths_per_src`) 사다리를 판 수를 늘려 다시 — 오늘 40 판으로는
   1e6 → 1/40, 2e6 → 3/40, 8e6 → 0/40, 32e6 → 0/40 이라 **유의하지 않았다**
3. 다음 Sionna release 에서 확인할 것: #1175 wedge fix · `deterministic` PathSolver 옵션
4. ⭐**공개 논의에 올릴 값어치가 있다** — 「회절을 꺼도 PathSolver 후보 생성기의 해시
   경합으로 경로가 통째로 사라진다」는 사례는 #1175·#1071·#851·#917·#1142 어디에도 없다.
   재현기가 이미 있다(`benchmark/probe_drop_0902.py`).
