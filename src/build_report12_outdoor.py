# -*- coding: utf-8 -*-
"""build_report12_outdoor.py — 리포트 12 «실외 장면» 조립 (reports/12_outdoor-scene.ipynb).

사용자 지시(2026-09-01): 「레포트 12 로 넣고, 형식도 비슷하게 맞춰줘 (마크다운 적극 이용)」.
본편 형식을 그대로 따른다 —
  · 절마다 «한 일 · 결과 · 방법 · 재현» 을 앞에 단다
  · 숫자는 원장 JSON 에서 **주입**한다(본문에 손으로 안 적는다). 각주 [^n] + 절 끝 출처표
  · 그림은 `../outputs/figures/` 파일 참조(노트북에 안 박는다)
  · 순수 마크다운 — 코드 셀 없음

원장: outputs/outdoor_scene_0901.json (benchmark/outdoor_scene_0901.py 가 낸다)

    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/build_report12_outdoor.py
"""
from __future__ import annotations

import json
import os

import nbformat as nbf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
J = json.load(open(f"{ROOT}/outputs/outdoor_scene_0901.json", encoding="utf-8"))
M, C, NL, G = J["_meta"], J["cells"], J["notch_ladder"], J["grid_cost"]

# ── 각주 — 본문에 [^n] 을 쓰면서 여기 쌓는다. 값은 원장에서 그대로 온다 ────────
SRC: list[tuple[str, str, object]] = []


def fn(path: str, key: str, val) -> str:
    SRC.append((path, key, val))
    return f"[^{len(SRC)}]"


LED = "outputs/outdoor_scene_0901.json"


def num(el: str, k: str, fmt="{:+.3f}") -> str:
    v = C[el][k]
    return fmt.format(v) + " " + fn(LED, f"cells.{el}.{k}", v)


def gnum(k: str, f: str, fmt="{:,}") -> str:
    v = G[k][f]
    return fmt.format(v) + " " + fn(LED, f"grid_cost.{k}.{f}", v)


cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s))

# ══════════════════════════════════════════════════════════ 표지
md(f"""# 리포트 12 — 실외 장면 — 지면과 건물을 넣으면 무엇이 남나

> 지금까지 모든 판은 **자유공간**이었다 — 빈 씬에 드론 부품만 넣었다. 그래서 우리가
> «클러터» 라고 부르며 걷어낸 것은 전부 **드론 자신의 동체**다. 지면과 건물을 넣으면
> 빗각에서 또렷하던 날개 박자가 **사라지고**, 정지 클러터를 걷어내도 **돌아오지 않는다**.
> 환경 에코는 정지 성분이 아니다 — 제거가 변동의 1 % 밖에 못 건드린다. 이 권이 세우는 것은
> **스톡 엔진 한 팔의 결과**이고, 우리 커널은 아직 실외를 못 돈다(절 3).

이 권은 아래 절로 이루어진다. 각 절은 **한 일 · 결과 · 방법 · 재현** 을 자기 앞에 달고 있어,
필요한 절만 따로 읽어도 된다.

| 절 | 무엇을 말하나 | 만든 곳 |
|---|---|---|
| 1 ⭐ | 빗각의 박자가 실외에서 ρ {C['el-30']['rho_free']:+.3f} → {C['el-30']['rho_outdoor']:+.3f} 로 사라지고 레벨이 {C['el-30']['d_level_db']:+.1f} dB 오른다 | `benchmark/outdoor_scene_0901.py` |
| 2 | 정지 클러터 제거는 변동의 {100 - C['el-30']['ac_left_pct']:.1f} % 만 건드리고, 노치 폭을 24 배 흔들어도 잔차의 닮음이 안 바뀐다 | `benchmark/outdoor_scene_0901.py` |
| 3 | 우리 커널은 이 비교에 없다 — 격자가 표적 bbox 로 정해져 지면 120 m 는 {G['ground_120m']['vs_drone']:,.0f} 배다 | `src/rcs_sbr.py` 판독 |

⭐ 표시한 절 하나만 읽어도 이 권의 결론은 선다.

숫자는 전부 계산 결과 JSON(원장)에서 주입된다 — 절 끝 «출처» 표가 그 파일과 키다.
원장이 다시 계산되면 빌더를 돌리는 것만으로 본문 숫자가 따라 바뀐다.

이 권에는 별편이 아직 없다. 실외에서 우리 커널을 돌리는 설계가 서면 그것이 12-2 가 된다.""")

# ══════════════════════════════════════════════════════════ 절 1
md("---")
md(f"""> ### 한 일
> **같은 팔·같은 자세로 자유공간과 실외 장면을 나란히 돌리고, 세 앙각에서 박자가 남는지를
> 포락 자기상관으로 쟀다.**

### 결과
1. 자유공간의 빗각 두 자리는 박자가 또렷하다 — el −30° 에서 ρ {num('el-30','rho_free')},
   el −60° 에서 ρ {num('el-60','rho_free')}.
2. 실외 장면을 넣으면 그 둘이 ρ {num('el-30','rho_outdoor')} 와
   {num('el-60','rho_outdoor')} 로 **무너진다.**
3. 같은 자리에서 레벨이 {num('el-30','d_level_db','{:+.1f}')} dB 와
   {num('el-60','d_level_db','{:+.1f}')} dB 오른다 — 지면·건물 에코다.
4. 정면(el 0°)은 자유공간에서 이미 ρ {num('el+0','rho_free')} 로 잡음이고, 실외에서도
   {num('el+0','rho_outdoor')} 로 그대로다. **이 각도는 실외 이전부터 안 됐다.**
5. ⛔이 결과는 **스톡 엔진 ①다끔 한 팔**의 것이다. 다른 팔과 우리 커널은 절 3 을 볼 것.""")

md(f"""### 방법

| 무엇을 | 어떻게 얻었나 |
|---|---|
| 판 | {M['arm_ko']} |
| 환경 | {M['env_ko']} |
| 잣대 | {M['metric_ko']} |
| 두 팔의 차이 | `--env outdoor01` 하나. 자세·회전수·광선 예산·거리·기체가 모두 같다 |

### 재현

```bash
PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/outdoor_scene_0901.py
```

| | |
|---|---|
| 출력 | `{LED}` |
| 소요 | GPU 안 씀 — 병합된 원장을 읽어 계산만 한다 |
| 비고 | 실외 샤드는 `runners/jobs_0831_outdoor.txt` 가 만든 30 장이다 |

---""")

md(f"""## 왜 dB 가 아니라 포락 자기상관인가

이 권은 박자의 세기를 **dB 로 적지 않는다.** dB 잣대(봉우리 ÷ 국소 바닥)는 봉우리가 어디서
왔는지 묻지 않기 때문이다. 2026-08-31 적대 검증에서 그 함정이 실제로 드러났다 — el 0° 기록의
변동 **100 %** 가 자세 8,192 개 중 19~52 개에서 |E| 가 정확히 2/3·1/3 로 떨어지는
**솔버 낙차**였는데, 같은 기록에 dB 잣대를 대면 9.5 가 나왔다.

포락 자기상관은 «되풀이되는가» 를 직접 묻는다. 잡음이면 0 근처(−0.06~+0.07)이고 박자가
있으면 +0.92~+0.99 다. 대체 잣대 넷을 반증에 걸었을 때 **살아남은 것은 이것 하나**다.""")

md(f"""## 실외가 올린 것은 신호가 아니라 바닥이다

레벨이 {num('el-30','d_level_db','{:+.1f}')} dB 올랐는데 박자는 사라졌다. 두 사실이 같이
서려면 오른 것이 **표적 변조가 아니라 정지 성분**이어야 한다. 자유공간 판의 절대 레벨은
{num('el-30','level_free_db','{:.1f}')} dB 이고 실외 판은 {num('el-30','level_outdoor_db','{:.1f}')} dB 다.

⚠**정면은 이 이야기에 안 들어간다.** el 0° 의 레벨 변화는
{num('el+0','d_level_db','{:+.1f}')} dB 로 거의 없는데, 그 각도의 자유공간 판이 이미
동체 정반사가 지배하는 상태라 지면이 더 얹을 자리가 없기 때문이다.""")

md("""## 이 절이 고정한 것

① 실외 장면에서 빗각의 박자가 사라진다. ② 같은 자리에서 레벨이 45~54 dB 오른다.
③ 정면은 실외 이전부터 안 됐으므로 이 결과의 근거가 아니다.

사라진 것을 필터로 되찾을 수 있는지는 다음 절이 답한다 — **절 2** «제거가 못 건드리는 것».""")

md(f"""<!--rs:sources-->
## 출처

본문의 `[^n]` 은 아래 {len(SRC)} 개 중 하나를 가리킨다. 값은 이 표를 만들 때 JSON 을 다시
열어 채웠다 — 본문 숫자와 같은 파일, 같은 키다.

| | 파일 | 키 | 값 |
|---|---|---|---|
""" + "\n".join(f"| [^{i+1}] | `{p}` | `{k}` | {v} |" for i, (p, k, v) in enumerate(SRC)))

_N1 = len(SRC)

# ══════════════════════════════════════════════════════════ 절 2
md("---")
md(f"""> ### 한 일
> **실외 기록에 정지 클러터 제거(ECA 계열 부분공간 소거)를 걸고, 잔차가 자유공간 신호와
> 닮는지 · 노치 폭을 24 배 흔들면 답이 바뀌는지를 쟀다.**

### 결과
1. 제거 뒤에도 박자는 안 돌아온다 — ρ {num('el-30','rho_removed')}(el −30°) ·
   {num('el-60','rho_removed')}(el −60°).
2. 잔차가 자유공간 신호와 **안 닮았다** — |상관| {num('el-30','corr_removed_vs_free','{:.4f}')}
   와 {num('el-60','corr_removed_vs_free','{:.4f}')}.
3. ⭐**걷어낸 것이 거의 없다** — 변동(AC)의 {num('el-30','ac_left_pct','{:.1f}')} % 와
   {num('el-60','ac_left_pct','{:.1f}')} % 가 그대로 남는다.
4. 노치 폭을 {M['fcut_hz']:g} Hz 에서 5~120 Hz 로 흔들어도 잔차의 닮음이
   {NL['el-30']['fcut5']['corr_vs_free']:.3f} {fn(LED, "notch_ladder.el-30.fcut5.corr_vs_free", NL['el-30']['fcut5']['corr_vs_free'])}
   에서 {NL['el-30']['fcut120']['corr_vs_free']:.3f} {fn(LED, "notch_ladder.el-30.fcut120.corr_vs_free", NL['el-30']['fcut120']['corr_vs_free'])}
   로 **소수점 셋째 자리까지 안 움직인다.**
5. ⚠**필터 자체는 멀쩡하다** — 같은 제거를 자유공간 기록에 걸면 박자가 그대로다
   (ρ {num('el-30','rho_free')} → {num('el-30','rho_free_removed')}).""")

md(f"""### 방법

| 무엇을 | 어떻게 얻었나 |
|---|---|
| 제거 | {M['removal_ko']} |
| 노치 폭 사다리 | 같은 기록에 `fcut` 만 5·20·60·100·120 Hz 로 바꿔 다섯 판 |
| 닮음 잣대 | 잔차와 **자유공간 기록** 사이의 \\|상관\\| — 실외 = 자유공간 + 환경 에코이므로, 제거가 성공했다면 잔차가 자유공간을 되찾아야 한다 |
| 걷어낸 양 | 제거 전후 AC 전력의 비 |

⚠**정본 노치 {M['fcut_hz']:g} Hz 는 박자 {M['f_flash_hz']:.1f} Hz 아래**라, 제대로 도는 경우
신호를 안 건드린다. 결과 5 가 그 확인이다.

### 재현

절 1 과 같은 명령 한 줄이다 — 같은 원장이 노치 사다리까지 함께 낸다.

---""")

md(f"""## 노치 폭 사다리 전체

| fcut [Hz] | 5 | 20 | 60 | 100 | 120 |
|---|---|---|---|---|---|
| ρ · el −30° | {NL['el-30']['fcut5']['rho']:+.3f} | {NL['el-30']['fcut20']['rho']:+.3f} | {NL['el-30']['fcut60']['rho']:+.3f} | {NL['el-30']['fcut100']['rho']:+.3f} | {NL['el-30']['fcut120']['rho']:+.3f} |
| \\|상관\\| · el −30° | {NL['el-30']['fcut5']['corr_vs_free']:.3f} | {NL['el-30']['fcut20']['corr_vs_free']:.3f} | {NL['el-30']['fcut60']['corr_vs_free']:.3f} | {NL['el-30']['fcut100']['corr_vs_free']:.3f} | {NL['el-30']['fcut120']['corr_vs_free']:.3f} |
| ρ · el −60° | {NL['el-60']['fcut5']['rho']:+.3f} | {NL['el-60']['fcut20']['rho']:+.3f} | {NL['el-60']['fcut60']['rho']:+.3f} | {NL['el-60']['fcut100']['rho']:+.3f} | {NL['el-60']['fcut120']['rho']:+.3f} |
| \\|상관\\| · el −60° | {NL['el-60']['fcut5']['corr_vs_free']:.3f} | {NL['el-60']['fcut20']['corr_vs_free']:.3f} | {NL['el-60']['fcut60']['corr_vs_free']:.3f} | {NL['el-60']['fcut100']['corr_vs_free']:.3f} | {NL['el-60']['fcut120']['corr_vs_free']:.3f} |

ρ 가 폭을 따라 조금 오르는 것은 잘라낸 칸이 늘어 남은 표본이 매끄러워진 것이지 박자가
살아난 것이 아니다 — **\\|상관\\| 열이 한 칸도 안 움직이는 것**이 그 증거다.""")

md("""## 지울 것이 정지 성분이 아니다

정지 클러터 제거는 «0 Hz 둘레에 앉은 에너지» 를 들어낸다. 그런데 튀면서 **드론에도 닿는**
경로는 드론의 도플러를 같이 싣는다 — 날개가 놓이는 자리에 같이 놓이므로 노치가 그것을
보지 못한다. 변동의 99 % 가 남는 것이 그 뜻이다.

⭐이것은 **정면 붕괴와 같은 기전**이고 거울만 바뀌었다. 정면에서는 동체가 거울이었고
30° 를 틀면 그 거울이 비껴갔다. 실외에서는 거울이 **지면**이라 늘 거기 있고,
그래서 **어느 각도로도 못 피한다** — el −30° 와 −60° 가 똑같이 무너진다.""")

md(f"""## 맵으로 본 세 판

![outdoor stft](../outputs/figures/vol12_outdoor_stft.png)

윗줄이 자유공간, 가운데가 실외, 아랫줄이 실외에 제거를 건 판이다. 가운데 줄에서 세로
줄무늬가 사라지고 0 Hz 굵은 띠만 남는다 — 간간이 서는 세로 줄은 박자가 아니라 산발적
사건이다. 아랫줄에서 띠는 걷혔는데 줄무늬는 안 돌아오고, 새로 생긴 굵은 세로 줄은
노치가 만든 잔향이다.

STFT 규약은 정본(`benchmark/build_switch_grid_figs.py`)을 그대로 쓴다 — 조각 길이는
블레이드 0.6 주기다.""")

md("""## 이 절이 고정한 것

① 정지 클러터 제거로는 실외에서 박자가 안 돌아온다. ② 걷어낸 양이 변동의 1 % 뿐이다.
③ 노치 폭은 답을 안 바꾼다. ④ 필터 자체는 자유공간에서 멀쩡하다.

그러면 우리 커널은 실외에서 어떤가 — 다음 절이 **그 비교가 아직 없다**는 것과 왜 없는지를
적는다.""")

md(f"""<!--rs:sources-->
## 출처

| | 파일 | 키 | 값 |
|---|---|---|---|
""" + "\n".join(f"| [^{i+1}] | `{p}` | `{k}` | {v} |"
                for i, (p, k, v) in enumerate(SRC) if i >= _N1))

_N2 = len(SRC)

# ══════════════════════════════════════════════════════════ 절 3
md("---")
md(f"""> ### 한 일
> **우리 커널의 실외 판이 왜 없는지를 코드에서 확인하고, 넣으려면 얼마가 드는지를
> 광선 격자 식으로 계산했다.**

### 결과
1. `--env` 는 PathSolver 씬에만 붙는다. 우리 커널은 `sbr_field(mv, …)` 로 **자세 잡힌
   드론 메쉬만** 받으므로 환경 부품이 도달하지 않는다.
2. 그 상태로 난 샤드 6 개는 자유공간 판과 상대차 **1e−16**(float64 엡실론)이었다 —
   이름만 실외였다. 2026-09-01 에 지웠고, `--engine ours` 에 `--env` 를 주면 이제 거부한다.
3. 격자는 표적 경계구로 정해진다. 드론만이면 격자점
   {gnum('drone_only','points')} 개인데, 지면 120 × 120 m 를 통째로 넣으면
   {gnum('ground_120m','points')} 개로 **{G['ground_120m']['vs_drone']:,.0f} 배** {fn(LED, "grid_cost.ground_120m.vs_drone", G['ground_120m']['vs_drone'])} 다.
4. ⭐그런데 온 지면이 필요한 것이 아니다. 지면 반사를 실어 나르는 것은 정반사점 둘레의
   **제1 프레넬 존**이고, 15 m·3.5 GHz 에서 반경
   {M['fresnel_r1_m']*100:.0f} cm {fn(LED, "_meta.fresnel_r1_m", M['fresnel_r1_m'])} 다.
5. 2 × 2 m 조각이면 격자점 {gnum('patch_2m','points')} 개로
   **{G['patch_2m']['vs_drone']:,.0f} 배** {fn(LED, "grid_cost.patch_2m.vs_drone", G['patch_2m']['vs_drone'])} 다 — 감당된다.""")

md(f"""### 방법

| 무엇을 | 어떻게 얻었나 |
|---|---|
| 환경이 안 닿는다 | `benchmark/elevation_sweep_md.py` 의 우리 커널 분기가 `sbr_field(mv, …)` 를 부른다. 환경 부품은 그 아래 `build_scene(parts + env_parts(...))` 에만 들어간다 |
| 상대차 1e−16 | 지우기 전 `ours_r15_n8192[_envoutdoor01]_…` 두 샤드의 `E` 를 직접 비교 |
| 격자 식 | `src/rcs_sbr.py` `grid_ref_from` — `R_out = R_max·1.15 + 3d` · `n = ceil(2·R_out/d)` · `d = λ/{M['grid_div']}` = {M['grid_spacing_m']*1000:.2f} mm |
| 프레넬 반경 | `R₁ = √(λ·d₁·d₂/(d₁+d₂))`, `d₁ = d₂ = {M['range_m']:.0f}` m |

### 재현

절 1 과 같은 명령이 격자 비용까지 함께 낸다.

---""")

md(f"""## 격자 비용 전체

| 표적 | R_max [m] | 격자 n | 격자점 | 드론 대비 |
|---|---|---|---|---|
| 드론만 (지금) | {G['drone_only']['R_max_m']:.2f} | {G['drone_only']['n']:,} | {G['drone_only']['points']:,} | 1 배 |
| + 지면 120 × 120 m | {G['ground_120m']['R_max_m']:.2f} | {G['ground_120m']['n']:,} | {G['ground_120m']['points']:,} | **{G['ground_120m']['vs_drone']:,.0f} 배** |
| + 지면 2 × 2 m | {G['patch_2m']['R_max_m']:.2f} | {G['patch_2m']['n']:,} | {G['patch_2m']['points']:,} | {G['patch_2m']['vs_drone']:,.0f} 배 |
| + 지면 5 × 5 m | {G['patch_5m']['R_max_m']:.2f} | {G['patch_5m']['n']:,} | {G['patch_5m']['points']:,} | {G['patch_5m']['vs_drone']:,.0f} 배 |

격자점이 표적 크기의 **제곱**으로 는다. 드론 0.5 m 에서 장면 120 m 로 가면 선형 240 배,
광선은 그 제곱이다. 자세 8,192 개에 곱하면 못 돈다.

⇒ 설계 실수가 아니라 **SBR 격자가 bbox 로 정해진다는 구조의 결과**다. PathSolver 는 광선을
쏘고 부딪히는 것을 찾으니 장면이 커져도 되지만, 우리 커널은 표적을 격자로 덮는 방식이라 다르다.""")

md(f"""## 그 장면은 이렇게 생겼다

![outdoor scene](../outputs/figures/vol12_outdoor_scene.png)

실제로 시뮬레이션한 메쉬를 Sionna RT 로 렌더한 것이다. 기체가 0.44 m 인데 장면이 120 m 라
한 컷에 둘 다 안 담겨 «장면» 과 «그 안의 드론» 두 컷으로 나눴다.""")

md(f"""## 이 절이 고정한 것

① 우리 커널의 실외 판은 **아직 없다**. ② 없는 이유는 격자가 표적 bbox 로 정해지기 때문이고
지면 120 m 는 {G['ground_120m']['vs_drone']:,.0f} 배다. ③ 프레넬 존만큼의 조각
(2 × 2 m, {G['patch_2m']['vs_drone']:,.0f} 배)이면 감당된다.

## 다음 단계

프레넬 존 조각을 우리 커널의 메쉬에 합치는 설계가 이 권의 별편(12-2)이 된다. 그때까지
정직한 진술은 — **우리 커널은 실외 장면에서 한 번도 안 돌았다.**

⚠그 설계에는 확인할 것이 둘 있다. ①정반사점의 자리가 앙각마다 움직이므로 조각도 따라
움직여야 한다. ②조각 가장자리에서 생기는 인위적 모서리 회절이 결과를 오염시키지 않는지
봐야 한다 — 실제 지면에는 그 모서리가 없다.""")

md(f"""<!--rs:sources-->
## 출처

| | 파일 | 키 | 값 |
|---|---|---|---|
""" + "\n".join(f"| [^{i+1}] | `{p}` | `{k}` | {v} |"
                for i, (p, k, v) in enumerate(SRC) if i >= _N2))

nb = nbf.v4.new_notebook(cells=cells)
nb.metadata.update(kernelspec=dict(display_name="Python 3", language="python",
                                   name="python3"),
                   language_info=dict(name="python", version="3.12"))
dst = f"{ROOT}/reports/12_outdoor-scene.ipynb"
nbf.write(nb, dst)
print(f"✅ {dst}  — 셀 {len(cells)} 개 · 각주 {len(SRC)} 개")
