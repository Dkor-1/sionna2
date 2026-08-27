# -*- coding: utf-8 -*-
"""materials_min.py — 커널이 쓰는 재질 계산만. **외부 의존 없음**(numpy 뿐).

숫자는 `materials_frozen.json` 에서 읽는다. 그 파일은 `freeze_materials.py` 가
`/workspace/sionna/src/materials.py` 에서 동결한 것이고, `verify.py` 가 저장소를 볼 수
있을 때마다 다시 대조한다.

식은 원본과 **글자 그대로 같다**:
    gamma_bulk : Γ = (1 − √εc)/(1 + √εc),  εc = εr − j·σ/(ω·ε0)
    gamma_po   : MATERIALS[k]['gamma_po'] 가 있으면 그 실효값, 없으면 gamma_bulk
    gamma_shape: √((|Γ_TE|²+|Γ_TM|²)/2) 를 수직입사 값으로 나눈 **상대 각도 모양**
"""
from __future__ import annotations

import json
import os

import numpy as np

EPS0 = 8.8541878128e-12
_HERE = os.path.dirname(os.path.abspath(__file__))
_PATH = os.path.join(_HERE, "materials_frozen.json")

try:
    with open(_PATH, encoding="utf-8") as _fh:
        _DOC = json.load(_fh)
except FileNotFoundError:                                    # pragma: no cover
    raise SystemExit(f"⛔ {_PATH} 이 없다 — `python freeze_materials.py` 로 만들 것 "
                     f"(저장소가 있어야 한다).")

META: dict = _DOC["_meta"]
TABLE: dict = _DOC["materials"]


def _spec(mat_key: str) -> dict:
    """모르는 키는 **조용히 안 넘어간다** — 원본과 같은 규약(예전에 plastic 으로 조용히
    흐르다 |Γ| 가 −12.26 dB 어긋난 적이 있다). PEC 는 재질 이름이 아니라 float 1.0 로 줄 것."""
    spec = TABLE.get(mat_key)
    if spec is None:
        raise KeyError(f"materials_min: 모르는 재질 키 {mat_key!r}. 아는 키 = {sorted(TABLE)}. "
                       f"완전도체는 group_mat 에 **float 1.0**(=|Γ|)을 넣을 것.")
    return spec


def material_params(mat_key: str, fc: float = 3.5e9) -> tuple[float, float, float]:
    """재질 키 → (εr, σ[S/m], S)."""
    s = _spec(mat_key)
    g = float(fc) / 1e9
    return (s["eps_a"] * g ** s["eps_b"], s["sig_c"] * g ** s["sig_d"], s["S"])


def gamma_bulk(mat_key: str, fc: float = 3.5e9) -> float:
    er, sg, _ = material_params(mat_key, fc)
    eps_c = er - 1j * sg / (2 * np.pi * float(fc) * EPS0)
    return float(abs((1.0 - np.sqrt(eps_c)) / (1.0 + np.sqrt(eps_c))))


def gamma_po(mat_key: str, fc: float = 3.5e9) -> float:
    """PO 가 쓰는 수직입사 |Γ|. 실효값이 있으면 그것, 없으면 벌크 프레넬."""
    s = _spec(mat_key)
    return float(s["gamma_po"]) if "gamma_po" in s else gamma_bulk(mat_key, fc)


def _fresnel_te_tm(cos_i, er, sigma, fc):
    w = 2 * np.pi * float(fc)
    erc = er - 1j * sigma / (w * EPS0)
    ci = np.clip(np.asarray(cos_i, float), 0.0, 1.0)
    sq = np.sqrt(erc - (1.0 - ci ** 2))
    return (ci - sq) / (ci + sq), (erc * ci - sq) / (erc * ci + sq)


def gamma_shape(mat_key: str, fc: float, cos_i):
    """수직입사 대비 **상대** 각도 모양 |Γ(θ)|/|Γ(0)| — 전력 평균(TE·TM)."""
    er, sg, _ = material_params(mat_key, fc)
    te, tm = _fresnel_te_tm(cos_i, er, sg, fc)
    g = np.sqrt((np.abs(te) ** 2 + np.abs(tm) ** 2) / 2.0)
    te0, tm0 = _fresnel_te_tm(1.0, er, sg, fc)
    g0 = np.sqrt((np.abs(te0) ** 2 + np.abs(tm0) ** 2) / 2.0)
    return g / max(float(g0), 1e-12)


def table(fc: float = 3.5e9) -> str:
    out = [f"{'재질':16s} {'출처':7s} {'eps_r':>8} {'sigma[S/m]':>12} {'|Γ|벌크':>9} {'|Γ|PO':>7}"]
    for k in sorted(TABLE):
        er, sg, _ = material_params(k, fc)
        out.append(f"{k:16s} {'ITU' if TABLE[k]['itu'] else 'custom':7s} "
                   f"{er:8.3f} {sg:12.5g} {gamma_bulk(k, fc):9.4f} {gamma_po(k, fc):7.3f}")
    return "\n".join(out)


if __name__ == "__main__":
    print(f"동결본 {_PATH}\n  {META.get('출처')}\n  {META.get('생성')} "
          f"· 원본 commit {META.get('원본_commit')}\n")
    print(table(3.5e9))
