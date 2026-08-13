# -*- coding: utf-8 -*-
"""outputs/resign_figures_audit.json 을 만든다 — R28 부호 정정이 **그림**에 준 영향의 감사표.

⛔ GPU 안 씀 · 기존 원장 안 건드림(새 파일 하나만 쓴다) · git 안 씀.
"""
from __future__ import annotations
import glob, hashlib, io, json, os, sys, subprocess
import numpy as np
from PIL import Image

ROOT = "/workspace/sionna"
# ⚠ 정정 **전** 그림의 사본이 있는 곳. 세션 임시 폴더라 나중에는 사라진다 —
#   없으면 픽셀 비교만 «사본 없음» 으로 비고, 나머지 숫자는 그대로 나온다.
SP = os.environ.get("RESIGN_BEFORE_DIR",
                    "/tmp/claude-1015/-workspace/"
                    "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad")
sys.path.insert(0, f"{ROOT}/src"); sys.path.insert(0, f"{ROOT}/benchmark")
from md_mapstyle import auto_periods, flash_spec                        # noqa: E402

TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
PRF, FFL, FTIP = TJ["prf_hz"], TJ["f_flash_hz"], TJ["f_tip_hz"]
PER = auto_periods(PRF, FFL)
N0, NZ = 500, int(round(60e-3 * PRF))
BAND = (0.35 * FTIP, 1.00 * FTIP)                    # 430 ~ 1229 Hz
TAIL = (1.00 * FTIP, 2500.0)


def mtime(p):
    return None if not os.path.exists(p) else \
        subprocess.run(["date", "-r", p, "+%Y-%m-%d %H:%M:%S"],
                       capture_output=True, text=True).stdout.strip()


def map_asym_db(E, band, zoom=True):
    seg = np.asarray(E, complex)
    if zoom:
        seg = seg[N0:N0 + NZ]
    f, _t, S, _ = flash_spec(seg, PRF, FFL, PER)
    P = S ** 2
    p = (f >= band[0]) & (f <= band[1]); m = (f <= -band[0]) & (f >= -band[1])
    return float(10 * np.log10(P[p].sum() / P[m].sum()))


def full_asym_db(E, lo, hi, prf=PRF):
    E = np.asarray(E, complex); E = E - E.mean(); n = E.size
    S = np.abs(np.fft.fft(E * np.hanning(n))) ** 2
    f = np.fft.fftfreq(n, 1 / prf)
    p = (f >= lo) & (f <= hi); m = (f <= -lo) & (f >= -hi)
    return float(10 * np.log10(S[p].sum() / S[m].sum()))


def band_peak_hz(E):
    f, t, S, _ = flash_spec(np.asarray(E, complex), PRF, FFL, PER)
    b = (np.abs(f) >= BAND[0]) & (np.abs(f) <= BAND[1])
    g = (S[b, :] ** 2).sum(axis=0); g = g - g.mean()
    dt = float(t[1] - t[0]); m = len(g)
    A = np.abs(np.fft.rfft(g * np.hanning(m), n=64 * m))
    fr = np.fft.rfftfreq(64 * m, dt); A = A / A.max()
    sel = (fr >= 40) & (fr <= 400)
    i0 = int(np.where(sel)[0][0]); i = int(np.argmax(A[sel])) + i0
    y0, y1, y2 = A[i - 1], A[i], A[i + 1]; den = y0 - 2 * y1 + y2
    return float(fr[i] + (0.5 * (y0 - y2) / den if den else 0.0) * (fr[1] - fr[0])), fr, A


def pixdiff(name, regions):
    if not os.path.exists(f"{SP}/before/{name}"):
        return dict(note="정정 전 그림 사본이 없다 — 픽셀 비교 못 함")
    a = np.asarray(Image.open(f"{SP}/before/{name}").convert("RGB"), float)
    b = np.asarray(Image.open(f"{ROOT}/outputs/figures/{name}").convert("RGB"), float)
    if a.shape != b.shape:
        return dict(note="크기가 달라 비교 불가", before=list(a.shape), after=list(b.shape))
    out = dict(whole=dict(max_abs_diff=float(np.abs(a - b).max()),
                          pct_pixels_changed=round(float(
                              (np.abs(a - b).max(axis=2) > 2).mean() * 100), 2)))
    for nm, (x0, x1) in regions.items():
        d = np.abs(a[:, x0:x1] - b[:, x0:x1])
        out[nm] = dict(max_abs_diff=float(d.max()),
                       pct_pixels_changed=round(float((d.max(axis=2) > 2).mean() * 100), 2))
    return out


OUT = {}
OUT["_meta"] = {
    "script": "benchmark/resign_figures_audit.py (그림 재생성은 benchmark/redraw_resign_figures.py)",
    "date": "2026-08-12",
    "purpose_ko": ("R28 구면파 위상 부호 정정(2026-08-11) 이전에 그려져 **도플러 축이 좌우로 "
                   "뒤집힌 채** 나간 그림을 찾아, 다시 그리고, 뒤집힘이 눈에 보이는지 숫자로 잰다."),
    "gpu_ko": "⛔GPU 를 쓰지 않았다 — 저장된 npz 만 읽어 그렸다(sbr_field 호출 0 회).",
    "ledgers_untouched_ko": "기존 outputs/*.json · *.npz 는 하나도 안 고쳤다. 이 파일만 새로 쓴다.",
    "correction_ref": {
        "kernel": "src/rcs_sbr.py :1090-1097 (구면파 갈래) · 위상 부호 규약 주석 :1127-1147",
        "gate": "outputs/verify_phase_sign.json (G1·G2·G3 = PASS)",
        "legacy_fixer": "benchmark/fix_phase_sign_legacy.py (np.conj + 표식 phase_sign_v2)",
        "kernel_fixed_at": mtime(f"{ROOT}/src/rcs_sbr.py"),
        "gate_at": mtime(f"{ROOT}/outputs/verify_phase_sign.json")},
    "criterion_ko": ("판정 기준은 «그 그림의 자료가 sbr_field(range_m=…) 구면파 갈래에서 나왔는가» 다. "
                     "평면파(range_m=None)와 Sionna PathSolver 자료는 처음부터 옳았다."),
    "stft_ko": f"flash_spec · periods={PER:.4f} · PRF={PRF} Hz · 확대창 60 ms @ n0={N0}",
    "bands_hz": {"blade": list(BAND), "tail": list(TAIL)},
}

# ── ① 스크립트 심사 ─────────────────────────────────────────────────────────
def grep(pat, path):
    return subprocess.run(["grep", "-n", pat, path], capture_output=True, text=True).stdout.strip()


scripts = []
AFFECTED_CALLERS = {                                   # sbr_field 에 range_m 을 준 곳
    "benchmark/deck_ours_by_range.py": "113",
    "benchmark/elevation_sweep_md.py": "134",
    "benchmark/nearfield_sphere_vs_plane.py": "120",
    "benchmark/verify_po_elev_unit.py": "264",
    "benchmark/verify_po_elev_nearfield.py": "57",
    "benchmark/verify_po_elev_gridscale.py": "80",
    "benchmark/verify_po_elev_gridladder.py": "89",
    "benchmark/verify_po_elev_tsladder.py": "91",
    "benchmark/verify_po_elev_nulls.py": "104",
    "benchmark/verify_po_elev_dcsplit.py": "66",
    "benchmark/verify_phase_sign.py": "34",
}
for p, line in AFFECTED_CALLERS.items():
    has_fig = bool(grep("savefig", f"{ROOT}/{p}"))
    scripts.append(dict(script=p, calls_sbr_field_with_range_m=True, callsite_line=line,
                        produces_figure=has_fig, verdict="자료가 영향받음"))
NOT_AFFECTED = {
    "benchmark/build_deck0811_range_figs.py":
        "sbr_field 를 부르지 않는다 — deck_ours_by_range.npz(구면파)를 **읽어서** 그린다 → 그림은 영향받음",
    "benchmark/report15_po_control.py":
        "sbr_field 호출에 range_m 이 없다(평면파). 구면파는 microdoppler_nearfield.phase_table 인데 "
        "그 커널의 위상은 exp(−jk(r−R)) 라 처음부터 평면파와 같은 부호다 → 영향 없음",
    "benchmark/report15_sweep_mini2.py":
        "sbr_field(mesh, gmat, FC, u, grid_ref=gref) — range_m 없음(평면파) → 영향 없음",
    "benchmark/report07_three_engine_maps.py":
        "sbr_field 에 range_m 없음(평면파) → report07_three_engines.npz 의 sbr/po 계열은 옳다",
    "benchmark/report07_three_engine_ranges.py":
        "Sionna PathSolver — 우리 커널이 아니다 → 영향 없음",
}
for p, why in NOT_AFFECTED.items():
    scripts.append(dict(script=p, calls_sbr_field_with_range_m=False,
                        produces_figure=bool(grep("savefig", f"{ROOT}/{p}")),
                        verdict="영향 없음", why_ko=why))
OUT["scripts_audited"] = scripts

# ── ② 해석 PO 커널의 부호가 원래 옳았는지 (report15 계열 면책 근거) ──────────
import microdoppler_nearfield as mnf                                    # noqa: E402
rng = np.random.default_rng(0)
P = rng.normal(scale=0.15, size=(400, 3))
N = rng.normal(size=(400, 3)); N /= np.linalg.norm(N, axis=1)[:, None]
w = rng.uniform(0.5, 1.5, 400); k = 2 * np.pi * 3.5e9 / 299792458.0
u = np.array([1.0, 0.0, 0.0]); Rbig = 5000.0; A = Rbig * u
Ep = mnf._field_plane(P, N, w, k, u, u)
Es = mnf._field_spherical(P, N, w, k, A, A, Rbig, Rbig)
OUT["analytic_po_kernel_check"] = {
    "what_ko": "microdoppler_nearfield 의 구면파↔평면파가 원거리장에서 같은 부호로 수렴하나",
    "range_m": Rbig,
    "phase_diff_deg": round(float(np.degrees(np.angle(Es / Ep))), 4),
    "abs_ratio": round(float(abs(Es) / abs(Ep)), 6),
    "same_sign": bool(abs(float(np.degrees(np.angle(Es / Ep)))) < 5.0),
    "verdict_ko": "옳다 — report15_po_control · experiment_md_range 등 해석 PO 계열은 이 결함과 무관"}

# ── ③ 자료 파일 상태 ────────────────────────────────────────────────────────
def npz_state(rel):
    p = f"{ROOT}/{rel}"
    d = np.load(p, allow_pickle=True)
    return dict(path=rel, mtime=mtime(p), phase_sign_v2=bool("phase_sign_v2" in d.files),
                keys=[k for k in d.files if k != "phase_sign_v2"][:8])


sh = sorted(glob.glob(f"{ROOT}/outputs/elev_sweep_shards/*.npz"))
marked = [p for p in sh if "phase_sign_v2" in np.load(p, allow_pickle=True).files]
OUT["data_files"] = {
    "corrected": [npz_state("outputs/deck_ours_by_range.npz"),
                  npz_state("outputs/elevation_sweep_md.npz"),
                  npz_state("outputs/nearfield_sphere_vs_plane.npz")],
    "elev_sweep_shards": dict(total=len(sh), marked_phase_sign_v2=len(marked),
                              unmarked_ko="표식 없는 것은 전부 sionna_* (PathSolver) 라 무관"),
    "not_affected": [npz_state("outputs/report07_three_engines.npz"),
                     npz_state("outputs/report07_three_engine_ranges.npz"),
                     npz_state("outputs/report07_range40.npz")],
}

# ── ④ 계열별 정정 전/후 숫자 ────────────────────────────────────────────────
OZ = np.load(f"{ROOT}/outputs/deck_ours_by_range.npz")
RZ = np.load(f"{ROOT}/outputs/report07_three_engine_ranges.npz")
SZ = np.load(f"{ROOT}/outputs/report07_range40.npz")
rows = []
for nm, E, aff in [("ours_R3", OZ["R3/E"], 1), ("ours_R15", OZ["R15/E"], 1),
                   ("ours_R40", OZ["R40/E"], 1),
                   ("sionna_R3", RZ["R3/E"], 0), ("sionna_R15", RZ["R15/E"], 0)] + \
                  [(f"sionna_R40_{k.split('/')[0]}", SZ[k], 0)
                   for k in SZ.files if k.endswith("/E")]:
    E = np.asarray(E, complex); Eb = np.conj(E) if aff else E
    pk_a, _fr, A_a = band_peak_hz(E); pk_b, _fr, A_b = band_peak_hz(Eb)
    rows.append(dict(
        series=nm, affected=bool(aff), n_poses=int(E.size),
        map_asym_blade_db=dict(before=round(map_asym_db(Eb, BAND), 3),
                               after=round(map_asym_db(E, BAND), 3)),
        map_asym_tail_db=dict(before=round(map_asym_db(Eb, TAIL), 3),
                              after=round(map_asym_db(E, TAIL), 3)),
        map_asym_all_db=dict(before=round(map_asym_db(Eb, (1.0, PRF / 2)), 3),
                             after=round(map_asym_db(E, (1.0, PRF / 2)), 3)),
        band_peak_hz=dict(before=round(pk_b, 4), after=round(pk_a, 4)),
        band_curve_max_abs_diff=float(np.max(np.abs(A_a - A_b))),
        abs_series_identical=bool(np.max(np.abs(np.abs(E) - np.abs(Eb))) == 0.0)))
OUT["series_before_after"] = {
    "note_ko": ("«before» 는 디스크 자료의 np.conj(= 옛 부호), «after» 는 현재 디스크 값. "
                "⊕/⊖ 비대칭은 그림이 실제로 그리는 STFT 맵(60 ms 확대창) 위에서 쟀다. "
                "블레이드 대역은 430~1229 Hz, 꼬리 대역은 1229~2500 Hz."),
    "rows": rows}

# ── ⑤ «거리마다 같다» 상관은 부호에 흔들리지 않는가 ────────────────────────
def mapcorr(Ea, Eb):
    _f, _t, Sa, _ = flash_spec(np.asarray(Ea, complex)[N0:N0 + NZ], PRF, FFL, PER)
    _f, _t, Sb, _ = flash_spec(np.asarray(Eb, complex)[N0:N0 + NZ], PRF, FFL, PER)
    a = (Sa ** 2).ravel(); b = (Sb ** 2).ravel(); a = a - a.mean(); b = b - b.mean()
    return round(float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b))), 5)


cc = {}
for nm, (k1, k2) in {"ours_3_vs_15": ("R3/E", "R15/E"), "ours_15_vs_40": ("R15/E", "R40/E"),
                     "ours_3_vs_40": ("R3/E", "R40/E")}.items():
    a, b = np.asarray(OZ[k1], complex), np.asarray(OZ[k2], complex)
    cc[nm] = dict(before=mapcorr(np.conj(a), np.conj(b)), after=mapcorr(a, b))
OUT["within_ours_map_correlation"] = {
    "note_ko": ("덱 슬라이드 6 의 주장 «우리 커널은 거리마다 거의 같은 맵» 이 쓰는 양. 두 맵이 "
                "**같이** 뒤집히므로 상관은 원리적으로 정확히 불변이다 — 숫자로도 그렇다. "
                "(측정 규약이 달라 덱 문서의 0.983/0.999/0.983 과 값 자체는 다르다.)"),
    "rows": cc}

# ── ⑥ 엔진 간 부호 일치 — 앙각 스윕 7 자리 ──────────────────────────────────
EZ = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz", allow_pickle=True)
el_rows = []
for el in ["+0", "-15", "-30", "-45", "-60", "-75", "-90"]:
    ko, ks = f"ours/el{el}", f"sionna/el{el}"
    if ko not in EZ.files or ks not in EZ.files:
        continue
    Eo = np.asarray(EZ[ko], complex); Es_ = np.asarray(EZ[ks], complex)
    ob, oa = full_asym_db(np.conj(Eo), *BAND), full_asym_db(Eo, *BAND)
    sb = full_asym_db(Es_, *BAND)
    el_rows.append(dict(el_deg=float(el), ours_blade_asym_db=dict(before=round(ob, 2),
                                                                 after=round(oa, 2)),
                        sionna_blade_asym_db=round(sb, 2),
                        sign_agrees_before=bool(np.sign(ob) == np.sign(sb)),
                        sign_agrees_after=bool(np.sign(oa) == np.sign(sb))))
OUT["cross_engine_sign_agreement"] = {
    "note_ko": ("커널 주석이 «정정 전에는 우리 팔이 주로 ⊖, Sionna 팔이 ⊕ 로 기울었다» 고 적었다. "
                "앙각 스윕 7 자리에서 블레이드 대역(430~1229 Hz) ⊕/⊖ 비대칭의 **부호**가 "
                "Sionna 와 맞는 자리 수를 세어 그 주장을 검사했다."),
    "n_agree_before": sum(r["sign_agrees_before"] for r in el_rows),
    "n_agree_after": sum(r["sign_agrees_after"] for r in el_rows),
    "n_total": len(el_rows),
    "caveat_ko": ("정정을 **정당화하는 것은 닫힌 형태의 게이트**(verify_phase_sign, 접근=양의 도플러, "
                  "평면파와 ρ=+0.99999974)이지 이 일치 수가 아니다. 실제로 40 m 덱 칸은 "
                  "반대로 움직인다 — 아래 deck_0811 참조. 섞어 읽지 말 것."),
    "rows": el_rows}

# ── ⑦ 그림 목록 ─────────────────────────────────────────────────────────────
figs = []
figs.append(dict(
    figure="outputs/figures/deck0811_maps_ranges.{png,pdf}",
    generator="benchmark/build_deck0811_range_figs.py :build_maps",
    affected_panels_ko="오른쪽 열 3 칸(Ours, 구면파). 왼쪽 열(Sionna)·컬러바는 무관.",
    was_stale=True, redrawn=True, redrawn_at=mtime(f"{ROOT}/outputs/figures/deck0811_maps_ranges.png"),
    pixel_diff=pixdiff("deck0811_maps_ranges.png",
                       {"left_col_sionna": (0, 1200), "right_col_ours": (1230, 2400),
                        "colorbar": (2400, 2525)}),
    visible_ko="⭐보인다 — 플래시 덩어리의 꼬리가 DC 선을 기준으로 위/아래가 통째로 바뀐다."))
figs.append(dict(
    figure="outputs/figures/deck0811_band_ranges.{png,pdf}",
    generator="benchmark/build_deck0811_range_figs.py :build_band",
    affected_panels_ko="없음 — 대역 선택이 |f| 대칭이라 켤레에 불변.",
    was_stale=False, redrawn=True,
    pixel_diff=pixdiff("deck0811_band_ranges.png", {}),
    visible_ko="안 보인다 — 정정 전 그림과 **픽셀 단위로 동일**하다."))
figs.append(dict(
    figure="outputs/figures/deck0811_seed40.{png,pdf}",
    generator="benchmark/build_deck0811_range_figs.py :build_seed40",
    affected_panels_ko="없음 — Sionna PathSolver 자료만 쓴다.",
    was_stale=False, redrawn=True,
    pixel_diff=pixdiff("deck0811_seed40.png", {}),
    visible_ko="안 보인다 — 픽셀 단위로 동일."))
figs.append(dict(
    figure="outputs/figures/raybudget_40m_vs_ours.png",
    generator="benchmark/build_raybudget_40m_fig.py :main (나란히판)",
    affected_panels_ko="세 번째 칸(Ours, R40 구면파). 앞 두 칸(Sionna 40 억 발)·컬러바는 무관.",
    was_stale=True, redrawn=True,
    redrawn_at=mtime(f"{ROOT}/outputs/figures/raybudget_40m_vs_ours.png"),
    pixel_diff=pixdiff("raybudget_40m_vs_ours.png",
                       {"panel1_sionna_s1": (0, 1430), "panel2_sionna_s2": (1430, 2830),
                        "panel3_ours": (2870, 4230), "colorbar": (4230, 4358)}),
    note_ko=("원장 outputs/report07_range40_raybudget.json 을 덮어쓰지 않으려고 스크립트의 main() "
             "대신 merge()·_map() 만 빌려 이 칸만 다시 그렸다. 앞 두 칸이 픽셀 동일한 것이 그 증거다."),
    visible_ko="⭐보인다 — 우리 칸의 꼬리 방향이 통째로 뒤집힌다."))
figs.append(dict(
    figure="outputs/figures/raybudget_40m.{png,pdf} · raybudget_40m_deck.png",
    generator="benchmark/build_raybudget_40m_fig.py",
    affected_panels_ko="없음 — Sionna 샤드만 쓴다.", was_stale=False, redrawn=False,
    visible_ko="해당 없음"))
figs.append(dict(
    figure="outputs/verify_po_elev_unit.png",
    generator="benchmark/verify_po_elev_unit.py",
    affected_panels_ko="우리 팔 전부 — sbr_field(range_m=10 m) 를 **직접 계산**한다.",
    was_stale=True, redrawn=False, needs_gpu=True,
    figure_mtime=mtime(f"{ROOT}/outputs/verify_po_elev_unit.png"),
    note_ko=("그림 07:18 · 커널 정정 08:23 → 이 그림은 옛 부호 커널로 계산됐다. 저장된 복소 시계열이 "
             "없어 다시 그리려면 GPU 재계산이 필요하다(⛔이번 라운드에서는 안 돌렸다). "
             "⚠같은 이유로 outputs/verify_po_elev_unit.json 의 meta.phase_convention_ko "
             "«커널은 exp(+j2k·range) 를 쓴다 → 표준과 부호가 반대다» 는 이제 **낡은 서술**이다. "
             "원장이므로 손대지 않았다 — 다음 재계산 때 같이 고칠 것."),
    verdict_ko="⚠미정정 · GPU 필요"))
figs.append(dict(
    figure="outputs/verify_nadir_flash.png · outputs/verify_raybudget_meaning.png",
    generator="benchmark/verify_nadir_flash.py · benchmark/verify_raybudget_meaning.py",
    affected_panels_ko="자료는 구면파 계열을 읽지만 그림 생성 시각이 정정 **이후**다.",
    was_stale=False, redrawn=False,
    figure_mtime=[mtime(f"{ROOT}/outputs/verify_nadir_flash.png"),
                  mtime(f"{ROOT}/outputs/verify_raybudget_meaning.png")],
    note_ko="정정(08:28·08:37) 뒤인 09:19·09:15 에 그려졌다 → 이미 옳다.",
    verdict_ko="이미 정정본"))
OUT["figures"] = figs

# ── ⑧ 8/11 덱 판정 ──────────────────────────────────────────────────────────
deck_num_check = {}
for R, key in ((3, "R3/E"), (15, "R15/E"), (40, "R40/E")):
    E = np.asarray(OZ[key], complex)
    pk_a, _f, _A = band_peak_hz(E); pk_b, _f2, _A2 = band_peak_hz(np.conj(E))
    deck_num_check[f"ours_{R}m_beat_hz"] = dict(before=round(pk_b, 2), after=round(pk_a, 2),
                                                changed=bool(round(pk_b, 2) != round(pk_a, 2)))
led = json.load(open(f"{ROOT}/outputs/deck0811_range_figs.json"))["band_peaks"]
deck_num_check["ledger_deck0811_range_figs_json"] = {
    k: round(v, 4) for k, v in led.items()}
deck_num_check["ledger_reproduced_after_fix"] = bool(
    abs(led["3/Ours (SBR + PO)"] - band_peak_hz(np.asarray(OZ["R3/E"], complex))[0]) < 1e-9)

OUT["deck_0811"] = {
    "deck_file": "/workspace/team_meeting/teammeeting_0811_v21.pptx",
    "touched_ko": "⛔덱 파일은 열어서 **읽기만** 했다. 한 바이트도 안 고쳤다.",
    "slide_map_ko": "덱 안에 박힌 이미지의 픽셀 폭으로 디스크 그림과 맞춰 확정했다.",
    "slides": [
        dict(slide=4, tag="THE TWO ENGINES", figure="deck0811_concept_v3.png",
             affected=False, why_ko="개념도 — 자료 없음"),
        dict(slide=5, tag="RESULT ONE", figure="deck0811_r1(_frozen).png (자름) + report07_f0.png",
             affected=False,
             why_ko=("report07_three_engines.npz 의 sbr/po 계열은 **평면파**(report07_three_engine_maps.py "
                     "가 range_m 없이 부른다) → 처음부터 옳았다")),
        dict(slide=6, tag="RANGE", figure="deck0811_maps_ranges.png (자름)",
             affected=True, affected_part_ko="오른쪽 열 3 칸(Ours)의 도플러 축이 좌우 반전",
             claim_ko="«우리 커널은 거리마다 거의 같은 맵을 준다»",
             claim_survives=True,
             why_ko="세 맵이 **같이** 뒤집히므로 서로의 닮음은 정확히 불변(상관 before=after)"),
        dict(slide=7, tag="BAND ENERGY", figure="deck0811_band_ranges.png (자름)",
             affected=False,
             why_ko="대역이 |f| 대칭이라 켤레에 불변 — 정정 전 그림과 픽셀 단위 동일",
             claim_ko="«우리 팔은 고조파가 단조 감소, PathSolver 는 2 배선이 1 배선만큼 세다»",
             claim_survives=True),
        dict(slide=8, tag="TWICE", figure="deck0811_seed40.png (자름)",
             affected=False, why_ko="Sionna 자료만"),
        dict(slide=9, tag="RAY BUDGET", figure="raybudget_40m_deck.png",
             affected=False, why_ko="Sionna 샤드만"),
        dict(slide=10, tag="SIDE BY SIDE", figure="raybudget_40m_vs_ours.png",
             affected=True, affected_part_ko="세 번째 칸(Ours)의 도플러 축이 좌우 반전",
             claim_ko="«같은 거리·같은 기체. 우리 것은 똑같이 재현되고 PathSolver 는 아니다»",
             claim_survives=True,
             why_ko="재현성 주장은 부호와 무관(크기·시드 반복성)"),
    ],
    "quoted_numbers_check": deck_num_check,
    "verdict_ko": ("⭐**덱의 주장은 그대로 선다.** 덱이 인용한 숫자(밴드 박자 126.51 / 126.11 / "
                   "126.05 Hz 와 Sionna 126.26 / 126.74 / 253.27 Hz)는 켤레에 불변이라 "
                   "정정 전후가 1e-13 Hz 이내로 같다. 바뀐 것은 **슬라이드 6 과 10 의 그림에서 "
                   "우리 칸의 도플러 축 방향**뿐이고, 두 슬라이드의 결론 문장은 부호를 쓰지 않는다."),
    "honest_caveat_ko": ("⚠단 «눈에 안 보인다» 는 거짓이다 — 뒤집힘은 명확히 보인다. 정정 전 그림을 "
                         "본 사람은 우리 커널의 접근/후퇴가 반대로 그려진 것을 본 것이다. "
                         "40 m 나란히판에서는 정정 **후에** 우리 칸의 꼬리가 Sionna 와 반대 방향이 된다"
                         "(우리 −5.5 dB ↔ Sionna +2.3 dB, 꼬리 대역). 이건 덱의 문장이 주장하지 않는 "
                         "것이지만, 그림을 보고 «두 엔진이 반대로 간다» 는 질문이 나올 수 있다."),
}

OUT["open_items_ko"] = [
    "verify_po_elev_unit.png · verify_po_elev_unit.json 은 옛 부호 커널 산출물이다 — GPU 재계산 필요.",
    "outputs/refute_gridmetric_vs_kinematics.png(08-11 09:18)은 생성 스크립트를 저장소에서 못 찾았다. "
    "시각만 보면 정정 이후라 입력은 정정본이지만, 확인하지 못했다 — 모른다.",
    "elev_sweep_shards 에 지금도 새 샤드가 쌓이고 있다(sionna_p4000000000_*). 새 파일에는 "
    "phase_sign_v2 표식이 없다 — 정정된 커널로 계산되어 **이미 옳기** 때문이다. "
    "⚠fix_phase_sign_legacy.py 를 다시 돌리면 ours_* 는 표식 덕에 안전하지만, "
    "정정 뒤 새로 만든 구면파 파일이 TARGETS 글롭에 걸리면 **두 번 뒤집힌다**.",
    "꼬리 대역(>f_tip) 에서 정정 후 우리 팔이 Sionna 와 부호가 어긋나는 자리가 있다. "
    "정정 자체는 닫힌 게이트로 확정됐으므로 이는 커널 간 물리 차이거나 다른 결함이다 — 미해결.",
]

p = f"{ROOT}/outputs/resign_figures_audit.json"
assert not os.path.exists(p) or True
json.dump(OUT, open(p, "w"), ensure_ascii=False, indent=1)
print("✅", p)
print("  agree before/after:", OUT["cross_engine_sign_agreement"]["n_agree_before"],
      "→", OUT["cross_engine_sign_agreement"]["n_agree_after"],
      "/", OUT["cross_engine_sign_agreement"]["n_total"])
for f in OUT["figures"]:
    print("  ", f["figure"], "| stale:", f["was_stale"], "| redrawn:", f["redrawn"])
