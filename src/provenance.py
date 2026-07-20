# -*- coding: utf-8 -*-
"""
provenance.py — **리포트 앞머리(front matter)** 를 자동으로 만든다
====================================================================
목적: **직접 참여하지 않은 사람이 이 리포트를 혼자 읽고 이해하고 재현할 수 있게** 한다.

그러려면 결과만으론 부족하다. 읽는 사람이 실제로 궁금해하는 것들:

  0. 이 리포트가 **답하는 질문**이 뭔가?           → question
  1. **어디부터 읽나?** 바쁘면 뭘 보면 되나?        → tldr / roadmap
  2. **뭘 참고했나?** 그 숫자 어디서 났나?          → sources
  3. **뭐가 뭘 했나?** — 특히 **Sionna 내부인가,     → engines  ← 가장 자주 오해받는 지점
     우리가 따로 짠 건가?**
  4. **라이브러리·버전·GPU** 는?                    → libs / env  (실행 시점 실측)
  5. **어떻게 다시 돌리나?**                        → reproduce   ← 이게 없으면 리포트가 아니다
  6. 본문 숫자는 **하드코딩인가 측정값인가?**       → data_flow
  7. **믿으면 안 되는 건 뭔가?** (신뢰 경계)        → caveats     ← 정직함의 핵심
  8. 모르는 용어가 나오면?                          → glossary
  9. **얼마나 걸리나?** (GPU 몇 장, 몇 분)          → cost
 10. **뭐가 산출되나?** (그림·JSON)                 → artifacts
 11. 앞뒤 리포트와의 **관계**                       → related

버전·GPU 는 **실행 시점에 실제로 읽어온다** — 손으로 적지 않으니 어긋날 수 없다.
"""
from __future__ import annotations

import importlib.metadata as _md
import os
import platform
import subprocess


# --------------------------------------------------------------------------- #
#  실행환경을 실제로 읽어온다
# --------------------------------------------------------------------------- #
def lib_versions(names) -> dict[str, str]:
    out = {}
    for n in names:
        try:
            out[n] = _md.version(n)
        except Exception:
            try:
                out[n] = getattr(__import__(n), "__version__", "설치됨(버전 미상)")
            except Exception:
                out[n] = "❌ 없음"
    return out


def gpu_info() -> list[str]:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,memory.total,driver_version",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=8, check=True).stdout
        return [ln.strip() for ln in out.strip().splitlines()]
    except Exception:
        return ["(nvidia-smi 없음)"]


def env_summary() -> dict:
    return dict(python=platform.python_version(),
                os=f"{platform.system()} {platform.release()}",
                gpus=gpu_info(),
                cuda_visible=os.environ.get("CUDA_VISIBLE_DEVICES",
                                            "(고정 안 함 — src/gpu.py 가 여유 메모리 보고 자동 선택)"))


# --------------------------------------------------------------------------- #
#  도구 사전 — "이게 Sionna 인가 우리가 짠 건가"를 명확히
# --------------------------------------------------------------------------- #
#  (설명, 어디서 도는가, 실행위치 태그)
ENGINE_DESC = {
    "sionna-rt": (
        "Sionna RT `PathSolver` — 전파 광선추적. 경로별 **지연 τ · 도플러 f_d · 복소이득 · 반사점 좌표**를 준다",
        "🟢 **Sionna 내부** (Mitsuba 3 / OptiX, GPU)", "sionna"),
    "sionna-render": (
        "Sionna RT `Scene.render_to_file()` — 씬·**추적된 광선**·라디오맵을 사진처럼 렌더",
        "🟢 **Sionna 내부** (Mitsuba 3 경로추적 렌더러, GPU)", "sionna"),
    "sionna-radiomap": (
        "Sionna RT `RadioMapSolver` — 공간별 전파 세기 분포",
        "🟢 **Sionna 내부** (GPU)", "sionna"),
    "sionna-phy": (
        "Sionna PHY (`ofdm`/`nr`/`channel`) — OFDM 변복조 · 3GPP 뉴머롤로지 · RT 경로를 신호에 적용",
        "🟢 **Sionna 내부** (PyTorch 백엔드, GPU)", "sionna"),
    "sbr": (
        "SBR (`src/rcs_sbr.py`) — **Mitsuba 광선 + PO 표면적분**으로 RCS. 가림(occlusion) 포함",
        "🟡 **우리가 짰다** — 다만 광선추적은 Sionna 가 쓰는 **Mitsuba 3 엔진 그대로** (GPU). "
        "Sionna 에 RCS 솔버가 없기 때문", "hybrid"),
    "po": (
        "순수 물리광학 (`src/rcs_po.py`) — 점구름 PO. **가림 없음**",
        "🔴 **별도** (numpy, CPU). **비교·검증용으로만** 남겨둠 — 기본 엔진은 SBR", "ours"),
    "trimesh-cad": (
        "CAD 모델링 (`src/cadkit.py` + `src/drone_cad.py`) — 로프트·스윕·회전체·**불리언(CSG)**",
        "🔴 **별도** (trimesh + manifold3d + shapely + scipy, CPU)", "ours"),
    "trimesh-check": (
        "메쉬 검증 (`src/mesh_check.py`) — watertight · winding · 법선방향 · 퇴화면",
        "🔴 **별도** (trimesh, CPU). 빌드 게이트로 회귀를 막는다", "ours"),
    "radar-dsp": (
        "레이더 신호처리 (`src/passive_process.py`) — ECA(직접파 제거) · 거리-도플러 · CA-CFAR",
        "🔴 **별도** (numpy, CPU). **Sionna 에 레이더 DSP 는 없다**", "ours"),
    "microdoppler": (
        "마이크로도플러 (`src/microdoppler.py`) — 회전 블레이드의 슬로타임 복소장 → STFT",
        "🟡 **우리가 짰다** — 자세별 산란장은 SBR(Mitsuba 광선)로 계산 (GPU)", "hybrid"),
    "matplotlib": (
        "matplotlib — 도표·그래프",
        "🔴 **별도** (CPU). 계산 결과를 *그리기만* 한다", "ours"),
}

LIB_USE = {
    "sionna": "광선추적(RT) + PHY(OFDM/NR/채널) — **이 프로젝트의 중심**",
    "mitsuba": "Sionna RT 의 렌더러·광선추적 백엔드 (OptiX, GPU). SBR 도 이걸 쓴다",
    "drjit": "Mitsuba 의 JIT 컴파일러 — GPU 커널 생성",
    "torch": "Sionna PHY 백엔드 — ⚠ Sionna 2.0 은 TensorFlow 가 아니라 **PyTorch**",
    "trimesh": "메쉬 CAD·**검증** — 로프트/스윕/불리언 + watertight·법선·퇴화면 검사",
    "manifold3d": "**불리언(CSG) 엔진** — trimesh 백엔드. 겹친 파트의 내부 면을 녹여 없앤다",
    "shapely": "2D 단면 폴리곤(버퍼·오프셋) → 로프트 입력",
    "scipy": "스플라인(단면 보간·암 경로) · STFT(스펙트로그램)",
    "numpy": "수치 계산 전반",
    "matplotlib": "도표",
    "Pillow": "GIF 합성",
}

GLOSSARY_DEFAULT = [
    ("RCS (σ)", "레이더 반사 단면적 [m²]. '이 표적이 얼마나 밝게 되비추는가'. dBsm = 10·log₁₀(σ/1 m²)"),
    ("PO", "물리광학(Physical Optics). 표면에 유도된 전류를 **적분**해 산란장을 구한다. σ 는 이 적분에서 나온다"),
    ("GO", "기하광학. 표면을 '국소 무한 거울'로 본다. 벽·바닥엔 정확하지만 **면적 항이 없어 σ 를 못 준다**"),
    ("SBR", "Shooting-and-Bouncing Rays. **광선(GO)으로 조명면을 찾고 그 위에서 PO 적분**. 상용 EM 솔버의 표준 방법"),
    ("가림(occlusion)", "앞의 면에 막혀 실제로는 안 보이는 면. 이걸 안 빼면 σ 를 과대평가한다"),
    ("바이스태틱", "송신기와 수신기가 **떨어져 있는** 레이더. 패시브 레이더가 이 형태"),
    ("도플러", "표적이 움직여 생기는 주파수 변화. 정지 물체(클러터)와 표적을 가르는 축"),
    ("마이크로도플러", "표적의 **부분 운동**(프로펠러 회전)이 만드는 도플러 미세구조. 드론의 지문"),
    ("ECA", "직접파(TX→RX 가시선)를 지워 표적을 드러내는 전처리. 지연된 기준신호 부분공간으로 사영해 뺀다"),
    ("CFAR", "일정 오경보율 검출기. 주변 셀의 잡음 수준을 보고 문턱을 정한다"),
    ("semi-anechoic", "**벽·천장만** 흡수체이고 **바닥은 반사성**인 챔버. 우리 챔버가 이것 (anechoic 아님)"),
]

DATA_FLOW_DEFAULT = (
    "이 노트북의 **숫자는 손으로 적지 않았습니다.** 측정 스크립트가 JSON 을 남기고, "
    "노트북 생성기(`src/make_notebook*.py`)가 그 JSON 을 읽어 본문에 주입합니다. "
    "→ **그림과 글이 어긋날 수 없습니다.** 숫자가 이상하면 JSON 을 보세요."
)


# --------------------------------------------------------------------------- #
def provenance_cells(report: str, what: str, question: str = "",
                     tldr: list = None, roadmap: list = None,
                     sources: list = None, engines: list = None, libs: list = None,
                     reproduce: list = None, artifacts: list = None,
                     caveats: list = None, cost: str = "", related: list = None,
                     glossary: list = None, data_flow: str = None,
                     spine: dict = None) -> list:
    """리포트 앞머리 markdown 셀들. 인자는 전부 선택 — 있는 것만 렌더한다.

    spine 이 주어지면 상단을 **'라이브러리 척추'** 리드로 렌더한다(❓질문/⚡TL;DR/🗺️roadmap 대신):
      spine = dict(core=..., gap=..., prior=..., lib=..., verify=...)
    각 리포트가 '무엇이 부족했고(gap) 선행은 어떻게 했고(prior) 어떤 라이브러리로 결합해(lib)
    어떻게 검증했나(verify)' 를 한 표로 못박는다.
    """
    def md(*lines):
        s = "\n".join(lines).splitlines(keepends=True)
        return {"cell_type": "markdown", "metadata": {}, "source": s or [""]}

    L, R = [], []

    # ── 헤드 ────────────────────────────────────────────────────────────────
    if spine:
        # 라이브러리 척추 리드 — 비유·Q&A 스캐폴딩 없이 '공백→선행→라이브러리→검증' 한눈에
        L += [f"# {report} — {what}", ""]
        if spine.get("core"):
            L += [f"**핵심.** {spine['core']}", ""]
        L += ["| 이 리포트의 척추 |  |", "|---|---|"]
        if spine.get("gap"):
            L += [f"| **① Sionna 의 공백** | {spine['gap']} |"]
        if spine.get("prior"):
            L += [f"| **② 선행 연구의 방식** | {spine['prior']} |"]
        if spine.get("lib"):
            L += [f"| **③ 쓴 라이브러리·결합** | {spine['lib']} |"]
        if spine.get("verify"):
            L += [f"| **④ 검증** | {spine['verify']} |"]
        L += ["", "---", ""]
    else:
        L += [f"# {report} — {what}", "",
              f"> ### ❓ 이 리포트가 답하는 질문", f"> **{question}**", ""]

        if tldr:
            L += ["### ⚡ 결론부터 (TL;DR)", ""]
            L += [f"{i+1}. {t}" for i, t in enumerate(tldr)]
            L += [""]

        if roadmap:
            L += ["### 🗺️ 어디부터 읽나", "", "| 절 | 무엇을 |  |", "|---|---|---|"]
            L += [f"| {r.get('sec','')} | {r.get('what','')} | {r.get('why','')} |" for r in roadmap]
            L += [""]
        L += ["---", ""]
    cells = [md(*L)]

    # ── 출처·도구·환경 ──────────────────────────────────────────────────────
    R += ["## 📋 이 결과가 어디서 어떻게 나왔나", "",
          "> 이 절은 **직접 참여하지 않은 사람도 출처를 따라가고 재현할 수 있도록** 넣었습니다. "
          "버전·GPU 는 노트북 생성 시점에 **실제로 읽어온 값**입니다.", ""]

    if sources:
        R += ["### 1️⃣ 무엇을 참고했나", "", "| 항목 | 출처 | 성격 |", "|---|---|---|"]
        R += [f"| {s.get('item','')} | {s.get('src','')} | {s.get('kind','')} |" for s in sources]
        R += [""]

    if engines:
        R += ["### 2️⃣ 어떤 도구가 무엇을 했나 — **Sionna 내부인가, 우리가 짠 건가**", "",
              "| 도구 | 하는 일 | 어디서 도는가 |", "|---|---|---|"]
        for e in engines:
            d = ENGINE_DESC.get(e)
            if d:
                R += [f"| `{e}` | {d[0]} | {d[1]} |"]
        R += ["",
              "> 🔑 **이 구분이 이 프로젝트에서 가장 자주 오해받는 지점입니다.**",
              "> - **전파**(경로·지연·도플러·렌더·라디오맵)는 🟢 **Sionna 가** 합니다.",
              "> - **표적 RCS** 는 🟡 우리가 짠 **SBR** 이 합니다 — Sionna 에 RCS 솔버가 없기 때문입니다. "
              "다만 광선추적은 Sionna 가 쓰는 **Mitsuba 3 엔진을 그대로** 씁니다.",
              "> - **레이더 신호처리**(ECA/CFAR)는 🔴 우리가 짰습니다 — Sionna 에 레이더 DSP 가 없습니다.",
              ""]

    if libs:
        V = lib_versions(libs)
        R += ["### 3️⃣ 라이브러리 (실행 시점 **실측** 버전)", "",
              "| 라이브러리 | 버전 | 무엇에 쓰나 |", "|---|---|---|"]
        R += [f"| `{k}` | {v} | {LIB_USE.get(k,'')} |" for k, v in V.items()]
        R += [""]

    E = env_summary()
    R += ["### 4️⃣ 어디서 돌렸나", "",
          f"- **Python** {E['python']} · {E['os']}",
          "- **GPU** — `src/gpu.py` 가 **여유 메모리를 보고 자동 선택**합니다 (하드코딩 없음):"]
    R += [f"  - {g}" for g in E["gpus"]]
    R += [f"- `CUDA_VISIBLE_DEVICES` = {E['cuda_visible']}"]
    if cost:
        R += ["", f"- **계산 비용**: {cost}"]
    R += [""]

    if reproduce:
        R += ["### 5️⃣ 어떻게 다시 돌리나 (재현)", "", "```bash"]
        R += list(reproduce)
        R += ["```", ""]

    R += ["### 6️⃣ 본문 숫자는 어디서 오나", "", (data_flow or DATA_FLOW_DEFAULT), ""]

    if artifacts:
        R += ["### 7️⃣ 무엇이 산출되나", "", "| 산출물 | 무엇 |", "|---|---|"]
        R += [f"| `{a.get('file','')}` | {a.get('what','')} |" for a in artifacts]
        R += [""]

    if caveats:
        R += ["### 8️⃣ ⚠️ 믿으면 안 되는 것 (신뢰 경계)", "",
              "> 정직함이 이 프로젝트의 규칙입니다. **아래는 이 리포트가 보장하지 않는 것들입니다.**", ""]
        R += [f"- {c}" for c in caveats]
        R += [""]

    if related:
        R += ["### 9️⃣ 앞뒤 리포트", "", "| 리포트 | 관계 |", "|---|---|"]
        R += [f"| {r.get('rep','')} | {r.get('rel','')} |" for r in related]
        R += [""]

    g = glossary if glossary is not None else GLOSSARY_DEFAULT
    if g:
        R += ["<details><summary><b>🔤 용어집 — 모르는 말이 나오면 여기</b> (클릭)</summary>", "",
              "| 용어 | 뜻 |", "|---|---|"]
        R += [f"| **{k}** | {v} |" for k, v in g]
        R += ["", "</details>", ""]

    R += ["---", ""]
    cells.append(md(*R))
    return cells


if __name__ == "__main__":
    for k, v in lib_versions(["sionna", "mitsuba", "torch", "trimesh", "manifold3d",
                              "shapely", "scipy", "numpy"]).items():
        print(f"  {k:12s} {v}")
    e = env_summary()
    print(f"\n  python {e['python']} · {e['os']}")
    for g in e["gpus"]:
        print(f"  GPU {g}")
