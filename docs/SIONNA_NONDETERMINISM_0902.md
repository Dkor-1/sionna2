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

## 4. ⛔확산을 끄는 권고는 **우리 태스크에 못 쓴다** (2026-09-02 정정)

문서는 재현성을 위해 `diffuse_reflection=False` 도 권한다. **우리는 못 쓴다 — 신호가 아예 없어진다.**

원장 `outputs/switch_factorial.json : cells.*.zero_echo` (이미 있던 측정):

| 팔 | el +0 | el −15 | −30 | −45 | −60 | −75 | −90 |
|---|---|---|---|---|---|---|---|
| `R1D0E0F0` 굴절만·**확산 끔** | false | **true** | **true** | **true** | **true** | **true** | **true** |
| `R0D0E0F0` **둘 다 끔** | — | — | **true**(d1·d3) | — | — | — | — |

`zero_echo = true` 는 **`npaths = 0 · E ≡ 0`** 이다. 빗각에서 **문자 그대로 아무것도 안 돌아온다.**

기작(`docs/MATERIAL_CORRECTION.md`):
1. `src/materials.py` 가 ITU 금속 계열(`metal`·`camera_assembly`·`pcb`)의 산란계수 **S = 0.0** 으로 고정한다
   → 금속에서는 확산이 **원리적으로 안 나온다**
2. 빗각에는 **시선에 정렬한 삼각형이 0 개**다(`az_falsify_verdict_attack2.json : kill_3`)
   → 정반사도 안 나온다

⇒ **빗각 PathSolver 에코는 원리적으로 100 % 플라스틱·탄소의 확산 산란이다.**
   확산을 끄면 남는 것이 없다. **우리 태스크(빗각 마이크로도플러)가 성립하지 않는다.**

⛔**내 실수(2026-09-02)**: 「`R0D0E0F0` 를 한 번도 안 돌렸으니 진단으로 돌려 보자」고 적었는데,
   원장에 **el −30 d1·d3 로 이미 있고 둘 다 `zero_echo = true`** 였다.
   원장을 안 보고 제안했다 — CLAIM_GATE 의 «원장 없음» 냄새 그대로다.

⚠디스크의 F0 샤드는 **전부 el −30** 뿐이고(176 개), 그중 에코가 있는 것은
   **회절을 켠 팔**(`R0D1E0F0`·`R0D1E1F0`·`R1D1E1F0`·`R1D1E0F0`)뿐이다.
   즉 우리 자료에서 「확산 끔 + 회절 끔」은 **측정 자체가 불가능**하다.

⭐그래서 남는 정직한 문장은 이것이다:
> **공개 논의가 권하는 재현성 설정(`diffraction=False` + `diffuse_reflection=False`)은
> 우리 표적에서 빗각 에코를 0 으로 만든다. 우리는 그 권고를 따를 수 없고, 따라서
> 재현성을 설정으로 사지 못한다 — 대신 «얼마나 안 맞는지» 를 재서 함께 싣는다.**

## 5. 남는 것

1. 해시 통 수(`max_num_paths_per_src`) 사다리를 판 수를 늘려 다시 — 오늘 40 판으로는
   1e6 → 1/40, 2e6 → 3/40, 8e6 → 0/40, 32e6 → 0/40 이라 **유의하지 않았다**
2. 다음 Sionna release 에서 확인할 것: #1175 wedge fix · `deterministic` PathSolver 옵션
3. ⭐**공개 논의에 올릴 값어치가 있다** — 「회절을 꺼도 PathSolver 후보 생성기의 해시
   경합으로 경로가 통째로 사라진다」는 사례는 #1175·#1071·#851·#917·#1142 어디에도 없다.
   재현기가 이미 있다(`benchmark/probe_drop_0902.py`).
   ⭐그리고 우리에게는 **확산을 끌 수 없다는 사정**이 있어, 그들의 회피책이 안 통한다는 점도
   함께 말할 수 있다.
4. 반복(rep) 판으로 **산포를 재서 결과에 함께 싣는다** — 설정으로 못 사면 그렇게라도 정직해진다
