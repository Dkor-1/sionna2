# -*- coding: utf-8 -*-
"""
provenance.py — **이 결과가 어디서 어떻게 나왔는가**를 리포트에 자동으로 박아 넣는다
=======================================================================================
사용자 요구(2026-07-14):
  "mesh 제작같은거 했을때 어떤 자료를 참고했는지와, 어떤 라이브러리같은것을 사용했는지,
   렌더링은 어디서 했으며, 실험은 sionna 내부에서 돌린것인지 아니면 별도의 실험을 거친것인지 —
   **직접적으로 참여한 사람이 아니여도 알아볼 수 있게끔** 가독성에 신경써서."

그래서 모든 리포트 맨 앞에 **같은 형식의 "출처·도구·실행환경" 표**를 넣는다.
숫자와 버전은 **실행 시점에 실제로 읽어온다** — 손으로 적지 않는다(어긋날 수 없다).

쓰는 법 (make_notebook*.py 안에서):
    from provenance import provenance_cells
    cells += provenance_cells(
        report="report1",
        what="챔버 환경 + 드론 5종 3D 메쉬",
        sources=[...],            # 참고 자료 (URL·문서)
        libs=["trimesh", ...],    # 이 리포트가 실제로 쓴 라이브러리
        engines={...},            # 그림·실험을 무엇이 만들었나
    )
"""
from __future__ import annotations

import importlib.metadata as _md
import os
import platform
import subprocess


# --------------------------------------------------------------------------- #
#  실행환경을 **실제로 읽어온다**
# --------------------------------------------------------------------------- #
def lib_versions(names) -> dict[str, str]:
    out = {}
    for n in names:
        try:
            out[n] = _md.version(n)
        except Exception:
            try:
                mod = __import__(n)
                out[n] = getattr(mod, "__version__", "설치됨(버전 미상)")
            except Exception:
                out[n] = "❌ 없음"
    return out


def gpu_info() -> list[str]:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=8, check=True).stdout
        return [ln.strip() for ln in out.strip().splitlines()]
    except Exception:
        return ["(nvidia-smi 없음)"]


def env_summary() -> dict:
    return dict(
        python=platform.python_version(),
        os=f"{platform.system()} {platform.release()}",
        gpus=gpu_info(),
        cuda_visible=os.environ.get("CUDA_VISIBLE_DEVICES", "(자동선택 — src/gpu.py)"),
    )


# --------------------------------------------------------------------------- #
#  리포트 앞머리에 붙일 markdown 셀
# --------------------------------------------------------------------------- #
#  엔진 이름 → (무엇인가, 어디서 도는가)
ENGINE_DESC = {
    "sionna-rt": ("Sionna RT `PathSolver` — 광선추적(전파)",
                  "**Sionna 내부** (Mitsuba 3 / OptiX, GPU)"),
    "sionna-render": ("Sionna RT `Scene.render_to_file()` — 씬·경로·라디오맵 렌더",
                      "**Sionna 내부** (Mitsuba 3 경로추적 렌더러, GPU)"),
    "sionna-radiomap": ("Sionna RT `RadioMapSolver` — 전파 세기 분포",
                        "**Sionna 내부** (GPU)"),
    "sionna-phy": ("Sionna PHY (`ofdm` / `nr` / `channel`) — OFDM 변조·3GPP 뉴머롤로지·채널 적용",
                   "**Sionna 내부** (PyTorch 백엔드)"),
    "sbr": ("SBR (`src/rcs_sbr.py`) — **Mitsuba 광선 + PO 표면적분**으로 RCS",
            "**별도 실험** — Sionna 가 아니라 우리가 짰다. 단, 광선추적은 Sionna 가 쓰는 **Mitsuba 3** 를 그대로 쓴다 (GPU)"),
    "po": ("순수 물리광학(`src/rcs_po.py`) — 점구름 PO. **가림 없음**",
           "**별도 실험** (numpy, CPU). 비교·검증용으로만 남겨둔다"),
    "trimesh-cad": ("CAD 모델링 (`src/cadkit.py` + `src/drone_cad.py`) — 로프트·스윕·회전체·**불리언(CSG)**",
                    "**별도** (trimesh + manifold3d + shapely + scipy, CPU)"),
    "trimesh-check": ("메쉬 검증 (`src/mesh_check.py`) — watertight·winding·법선·퇴화면",
                      "**별도** (trimesh, CPU)"),
    "radar-dsp": ("레이더 신호처리 (`src/passive_process.py`) — ECA · 거리-도플러 · CA-CFAR",
                  "**별도 실험** — Sionna 에 레이더 DSP 는 없다 (numpy, CPU)"),
    "matplotlib": ("matplotlib — 도표·그래프",
                   "**별도** (CPU). 광선추적 결과를 *그리기만* 한다"),
}


def provenance_cells(report: str, what: str, sources: list, libs: list,
                     engines: list, extra_notes: str = "") -> list:
    """리포트 맨 앞에 넣을 '출처·도구·실행환경' markdown 셀들을 만든다."""
    def md(*lines):
        s = "\n".join(lines).splitlines(keepends=True)
        return {"cell_type": "markdown", "metadata": {}, "source": s or [""]}

    V = lib_versions(libs)
    E = env_summary()

    rows = []
    rows.append("## 📋 이 리포트는 어떻게 만들어졌나")
    rows.append("")
    rows.append(f"> **{report} — {what}**")
    rows.append(">")
    rows.append("> 이 절은 **직접 참여하지 않은 사람도** 결과의 출처를 따라갈 수 있도록 넣었습니다. "
                "여기 적힌 버전·GPU 는 노트북을 만든 시점에 **실제로 읽어온 값**입니다.")
    rows.append("")

    # ── 1. 무엇을 참고했나
    rows.append("### 1️⃣ 무엇을 참고했나 (자료 출처)")
    rows.append("")
    rows.append("| 항목 | 출처 | 성격 |")
    rows.append("|---|---|---|")
    for s in sources:
        rows.append(f"| {s.get('item','')} | {s.get('src','')} | {s.get('kind','')} |")
    rows.append("")

    # ── 2. 어떤 도구로 만들었나
    rows.append("### 2️⃣ 어떤 도구가 무엇을 했나")
    rows.append("")
    rows.append("| 도구 | 하는 일 | **어디서 도는가** |")
    rows.append("|---|---|---|")
    for e in engines:
        d = ENGINE_DESC.get(e)
        if d:
            rows.append(f"| `{e}` | {d[0]} | {d[1]} |")
    rows.append("")
    rows.append("> 🔑 **\"Sionna 내부\" vs \"별도 실험\"** — 이 구분이 중요합니다. "
                "전파(경로·지연·도플러·렌더)는 **Sionna 가** 합니다. "
                "표적 RCS(SBR)와 레이더 신호처리(ECA/CFAR)는 **Sionna 에 없어서 우리가 짰습니다** — "
                "다만 SBR 의 광선추적은 Sionna 가 쓰는 **Mitsuba 3 엔진을 그대로** 씁니다.")
    rows.append("")

    # ── 3. 라이브러리 버전
    rows.append("### 3️⃣ 라이브러리 (실행 시점 실측 버전)")
    rows.append("")
    rows.append("| 라이브러리 | 버전 | 무엇에 쓰나 |")
    rows.append("|---|---|---|")
    USE = {
        "sionna": "광선추적(RT) + PHY(OFDM/NR/채널) — **이 프로젝트의 중심**",
        "mitsuba": "Sionna RT 의 렌더러/광선추적 백엔드 (OptiX, GPU)",
        "drjit": "Mitsuba 의 JIT — GPU 커널",
        "torch": "Sionna PHY 백엔드 (Sionna 2.0 은 TensorFlow 가 아니라 PyTorch)",
        "trimesh": "**메쉬 CAD·검증** — 로프트/스윕/불리언/watertight·법선 검사",
        "manifold3d": "**불리언(CSG) 엔진** — trimesh 가 백엔드로 사용. 겹친 파트의 내부 면을 녹여 없앤다",
        "shapely": "2D 단면 폴리곤 (버퍼·오프셋) → 로프트 입력",
        "scipy": "스플라인 (단면 보간·암 스윕 경로) · 신호처리(STFT)",
        "numpy": "수치 계산 전반",
        "matplotlib": "도표",
        "Pillow": "GIF 합성",
    }
    for k, v in V.items():
        rows.append(f"| `{k}` | {v} | {USE.get(k, '')} |")
    rows.append("")

    # ── 4. 실행 환경
    rows.append("### 4️⃣ 어디서 돌렸나 (하드웨어·환경)")
    rows.append("")
    rows.append(f"- **Python** {E['python']} · {E['os']}")
    rows.append(f"- **GPU** (`src/gpu.py` 가 여유 메모리를 보고 자동 선택 — 하드코딩 없음):")
    for g in E["gpus"]:
        rows.append(f"  - {g}")
    rows.append(f"- `CUDA_VISIBLE_DEVICES` = {E['cuda_visible']}")
    rows.append("")

    if extra_notes:
        rows.append("### 5️⃣ 덧붙임")
        rows.append("")
        rows.append(extra_notes)
        rows.append("")

    rows.append("---")
    return [md(*rows)]


if __name__ == "__main__":
    print("라이브러리:", lib_versions(["sionna", "mitsuba", "torch", "trimesh", "manifold3d",
                                       "shapely", "scipy", "numpy"]))
    print("환경:", env_summary())
