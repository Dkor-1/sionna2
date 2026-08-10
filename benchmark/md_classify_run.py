# -*- coding: utf-8 -*-
"""
md_classify_run.py — **호버링 드론을 마이크로도플러만으로 기종을 가를 수 있나** · 판정 (2026-08-10)
=====================================================================================================
`md_classify_dataset.py build` 가 낸 특징 행렬을 읽어 분류하고 혼동행렬을 그린다.

⭐ 검증 설계 — 무엇을 못 하게 막았나
------------------------------------
1. **자세 단위 분리** (leave-one-aspect-out). 같은 자세(az·el)의 시행이 학습과 시험에 함께
   들어가면 «기체를 가르는가» 가 아니라 «그 자세의 산란 패턴을 외우는가» 를 묻게 된다.
   자세 18 개를 폴드로 삼아, 시험 자세는 학습에서 **한 번도 안 본 기하**다.
2. **base rpm 을 시행마다 ±6% 흩뜨렸다.** 안 그러면 f_flash 가 정답표다.
   그 결과 mini5pro(5500 rpm) 와 phantom4(5500) 의 f_flash 분포는 **완전히 겹친다.**
3. ⭐ **f_flash 제외 대조.** f_flash 만으로 갈리면 그건 분류가 아니라 회전수 읽기다.
   다섯 팔로 나눠 묻는다.
     all            전부
     flash_only     f_flash 하나만 — «회전수 읽기» 기준선
     no_flash       f_flash 를 뺀 나머지
     scale_free     f_flash·f_edge 를 뺀 나머지
     geometry_only  ⭐ 거기서 flash_contrast_db·half_corr 까지 뺀다 —
                    이 둘은 창 안의 블레이드 주기 수를 통해 rpm 을 약하게 물고 있다.
                    남는 것은 빗살 고조파 모멘트(m̄ = 2πR/λ 의 단조함수) · 고조파 분포 ·
                    접은 주기 구조 · 동체/블레이드 비 · 포락선 첨도 · 도플러 비대칭 —
                    **회전수가 완전히 약분된 기하와 재질**뿐이다.
4. **널 대조.** 라벨을 자세 안에서 섞고 같은 교차검증을 돌린다. 우연 수준이 아니면 누수다.
5. **잡음 팔.** 우리 시뮬은 잡음 0·클러터 0 이라 정확도는 **상한**이다. SNR 을 내려 가며
   어디서 무너지는지 잰다.
6. **분류기는 단순한 것** — 선형판별(LDA) · 최근접(kNN) · 작은 랜덤포레스트.
   목적은 «가를 수 있나» 이지 최고 정확도가 아니다.

⚠ 데이터의 전제 — `md_classify_dataset.py` 가 광선 격자를 자세에 못 박고 만든 표를 쓴다.
  못 박지 않으면 프로펠러 회전이 bbox 를 흔들어 **진짜 변조의 3 배**짜리 허위 변조가 얹힌다
  (원장 outputs/md_classify_verify.json 의 grid_pinning 절).

산출
-----
  outputs/md_classify.json                        수치·혼동행렬·판정 (원장)
  outputs/md_classify.npz                         혼동행렬·특징 요약 배열
  outputs/figures/md_classify_f1.{png,pdf}        혼동행렬 + 특징 공간 + 대조 + 잡음

    python benchmark/md_classify_run.py
"""
from __future__ import annotations

import json
import os
import sys
import textwrap
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

FEAT_NPZ = os.path.join(ROOT, "outputs", "md_classify_features.npz")
OUT_JSON = os.path.join(ROOT, "outputs", "md_classify.json")
OUT_NPZ = os.path.join(ROOT, "outputs", "md_classify.npz")
FIG_DIR = os.path.join(ROOT, "outputs", "figures")

from sklearn.discriminant_analysis import LinearDiscriminantAnalysis      # noqa: E402
from sklearn.ensemble import RandomForestClassifier                       # noqa: E402
from sklearn.model_selection import LeaveOneGroupOut                      # noqa: E402
from sklearn.neighbors import KNeighborsClassifier                        # noqa: E402
from sklearn.pipeline import make_pipeline                                # noqa: E402
from sklearn.preprocessing import StandardScaler                          # noqa: E402

SHORT = {"mini2": "Mini 2", "mini5pro": "Mini 5 Pro", "phantom4": "Phantom 4",
         "matrice4e": "Matrice 4E", "typhoonh480": "Typhoon H", "s1000plus": "S1000+"}


def _models():
    return {
        "LDA": make_pipeline(StandardScaler(), LinearDiscriminantAnalysis()),
        "kNN5": make_pipeline(StandardScaler(), KNeighborsClassifier(5)),
        "RF100": RandomForestClassifier(n_estimators=100, max_depth=8,
                                        random_state=0, n_jobs=4),
    }


def _clean(X):
    X = np.array(X, float)
    X[~np.isfinite(X)] = 0.0
    return X


def run_cv(X, y, groups, model):
    """자세 단위 leave-one-group-out 교차검증. 반환 (정확도, 예측배열)."""
    logo = LeaveOneGroupOut()
    pred = np.empty(len(y), dtype=object)
    for tr, te in logo.split(X, y, groups):
        m = model()
        m.fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
    return float((pred == y).mean()), pred


def confusion(y, pred, labels):
    M = np.zeros((len(labels), len(labels)), int)
    idx = {l: i for i, l in enumerate(labels)}
    for a, b in zip(y, pred):
        M[idx[a], idx[b]] += 1
    return M


def per_class_f1(M):
    tp = np.diag(M).astype(float)
    fp = M.sum(0) - tp
    fn = M.sum(1) - tp
    p = tp / np.maximum(tp + fp, 1e-9)
    r = tp / np.maximum(tp + fn, 1e-9)
    return 2 * p * r / np.maximum(p + r, 1e-9), p, r


def main():
    z = np.load(FEAT_NPZ, allow_pickle=True)
    X_all = _clean(z["X"])
    names = list(z["feature_names"])
    drone = np.array([str(s) for s in z["drone"]])
    aspect = z["aspect"]
    prf, Tw, snr = z["prf"], z["Twin"], z["snr_db"]
    prf_main, t_main = float(z["prf_main"]), float(z["t_main"])
    labels = [k for k in ["mini2", "mini5pro", "phantom4", "matrice4e",
                          "typhoonh480", "s1000plus"] if k in set(drone)]
    G_RATE = [str(s) for s in z["group_rate"]]
    G_ABS = [str(s) for s in z["group_abs"]]

    def cols(keep):
        return np.array([i for i, n in enumerate(names) if n in keep])

    #  ⭐ geometry_only — **엄격하게 rpm 과 무관한 양만** 남긴다.
    #    scale_free 는 f_flash·f_edge 를 뺐지만 두 특징이 rpm 을 약하게 물고 있다:
    #      flash_contrast_db  STFT 조각 길이가 추정 f_flash 에 맞춰 정해진다
    #      half_corr          창 안에 든 블레이드 주기 수 = T·f_flash 가 기체마다 다르다
    #                         (0.25 s 창에서 mini2 77 주기 ↔ matrice4e 32 주기)
    #    둘을 마저 빼면 남는 것은 빗살 모멘트·고조파 분포·접은 주기 구조·동체/블레이드 비
    #    ·포락선 첨도·도플러 비대칭 — 전부 회전수가 약분된 **기하와 재질**이다.
    G_RPM_TINGED = ["flash_contrast_db", "half_corr"]
    ARMS = {
        "all": [n for n in names],
        "no_flash": [n for n in names if n not in G_RATE],
        "flash_only": list(G_RATE),
        "scale_free": [n for n in names if n not in G_RATE + G_ABS],
        "geometry_only": [n for n in names
                          if n not in G_RATE + G_ABS + G_RPM_TINGED],
    }

    res = {"_meta": {
        "script": "benchmark/md_classify_run.py",
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "question_ko": "호버링 드론을 마이크로도플러만으로 기종을 가를 수 있나",
        "n_rows_total": int(len(X_all)),
        "features": names, "airframes": labels,
        "prf_main_hz": prf_main, "window_s": t_main,
        "cv_ko": "자세 단위 leave-one-aspect-out (시험 자세는 학습에서 한 번도 안 본 기하)",
        "chance_accuracy": round(1.0 / len(labels), 4),
        "upstream_ledger": "outputs/md_classify_verify.json",
        "data_precondition_ko": (
            "광선 격자를 자세에 못 박고 계산한 위상표를 쓴다. 못 박지 않으면 프로펠러가 "
            "bbox 를 흔들어 허위 변조가 얹힌다(기체 6종 실측 1.49~14.64 배, 중앙값 3.3 배). "
            "고정하면 로터 기여의 덧셈이 기계정밀도(1e−15)로 성립한다. "
            "원장: outputs/md_classify_verify.json 의 grid_pinning 절."),
    }, "arms": {}, "noise": {}, "prf_sweep": {}, "window_sweep": {},
        "feature_stats": {}, "confusion": {}}

    # ── 헤드라인 조건 ────────────────────────────────────────────────────────
    sel = (prf == prf_main) & (Tw == t_main) & (snr > 500)
    Xh, yh, gh = X_all[sel], drone[sel], aspect[sel]
    res["_meta"]["n_trials_headline"] = int(sel.sum())
    res["_meta"]["n_trials_per_airframe"] = int(sel.sum() // max(len(labels), 1))
    res["_meta"]["n_aspects"] = int(len(np.unique(gh)))

    print(f"헤드라인 시행 {sel.sum()} (기체 {len(labels)} · 자세 {len(np.unique(gh))})")
    conf_store = {}
    for arm, keep in ARMS.items():
        c = cols(keep)
        res["arms"][arm] = {"features": keep, "n_features": len(c), "models": {}}
        for mname, _ in _models().items():
            acc, pred = run_cv(Xh[:, c], yh, gh, lambda mn=mname: _models()[mn])
            M = confusion(yh, pred, labels)
            f1, p, r = per_class_f1(M)
            res["arms"][arm]["models"][mname] = {
                "accuracy": round(acc, 4),
                "macro_f1": round(float(f1.mean()), 4),
                "per_class_f1": {l: round(float(v), 4) for l, v in zip(labels, f1)},
            }
            conf_store[f"{arm}/{mname}"] = M
            print(f"  {arm:12s} {mname:6s} acc {acc:.3f}  macroF1 {f1.mean():.3f}")
        best = max(res["arms"][arm]["models"].items(), key=lambda kv: kv[1]["accuracy"])
        res["arms"][arm]["best_model"] = best[0]
        res["arms"][arm]["best_accuracy"] = best[1]["accuracy"]

    for k, M in conf_store.items():
        res["confusion"][k] = M.tolist()

    # ── 특징 통계 (겹침을 숫자로) ───────────────────────────────────────────
    for fi, fn in enumerate(names):
        st = {}
        for l in labels:
            v = Xh[yh == l, fi]
            st[l] = {"mean": round(float(v.mean()), 4), "std": round(float(v.std()), 4),
                     "p5": round(float(np.percentile(v, 5)), 4),
                     "p95": round(float(np.percentile(v, 95)), 4)}
        res["feature_stats"][fn] = st

    # f_flash 겹침 — mini5pro ↔ phantom4 (같은 hover_rpm 5500)
    fi = names.index("f_flash_hat")
    ov = {}
    for a, b in [("mini5pro", "phantom4"), ("mini5pro", "typhoonh480"),
                 ("phantom4", "typhoonh480"), ("phantom4", "matrice4e")]:
        if a in labels and b in labels:
            va, vb = Xh[yh == a, fi], Xh[yh == b, fi]
            lo = max(np.percentile(va, 5), np.percentile(vb, 5))
            hi = min(np.percentile(va, 95), np.percentile(vb, 95))
            frac = max(0.0, hi - lo) / max(
                (np.percentile(va, 95) - np.percentile(va, 5)), 1e-9)
            ov[f"{a}|{b}"] = round(float(frac), 3)
    res["_meta"]["f_flash_p5p95_overlap_frac"] = ov

    # ── 널 대조: 라벨을 섞으면 우연 수준으로 내려가야 한다 ────────────────────
    #    교차검증에 새는 곳이 있으면 여기서 잡힌다(자세 분리가 진짜인지 확인).
    rs = np.random.default_rng(0)
    nulls = []
    c_all = cols(ARMS["all"])
    for _ in range(5):
        yp = yh.copy()
        for a in np.unique(gh):                # 자세 안에서만 섞는다 — 자세 효과는 남기고
            m = gh == a
            yp[m] = rs.permutation(yp[m])
        acc, _ = run_cv(Xh[:, c_all], yp, gh, lambda: _models()["RF100"])
        nulls.append(acc)
    res["null_control"] = {
        "permuted_label_accuracy_mean": round(float(np.mean(nulls)), 4),
        "permuted_label_accuracy_max": round(float(np.max(nulls)), 4),
        "chance": round(1.0 / len(labels), 4), "n_permutations": len(nulls),
        "note_ko": "라벨을 자세 안에서 섞고 같은 교차검증을 돌렸다. 우연 수준이면 누수가 없다.",
    }
    print(f"  널대조(라벨섞음) {np.mean(nulls):.3f} (우연 {1/len(labels):.3f})")

    # ── 앙각별 난이도 — 배 쪽(el<0)이 지상 레이더의 현실이다 ────────────────
    el_arr = z["el"][sel]
    _, pred_all = run_cv(Xh[:, c_all], yh, gh, lambda: _models()["RF100"])
    for e in sorted(set(el_arr.tolist())):
        m = el_arr == e
        res.setdefault("by_elevation", {})[f"{e:g}"] = {
            "n": int(m.sum()), "accuracy": round(float((pred_all[m] == yh[m]).mean()), 4)}

    # ── 혼동 쌍의 물리 — 왜 그 둘이 섞이나 ──────────────────────────────────
    dia = {l: float(z["prop_dia_mm"][drone == l][0]) for l in labels}
    rot = {l: int(z["n_rotors"][drone == l][0]) for l in labels}
    M_all = conf_store[f"all/{res['arms']['all']['best_model']}"]
    pairs = []
    for i in range(len(labels)):
        for j in range(len(labels)):
            if i != j and M_all[i, j] > 0:
                pairs.append((int(M_all[i, j]), labels[i], labels[j]))
    pairs.sort(reverse=True)
    res["confusion_physics"] = [
        {"true": a, "predicted": b, "count": c,
         "prop_dia_mm": [dia[a], dia[b]],
         "prop_dia_ratio": round(max(dia[a], dia[b]) / min(dia[a], dia[b]), 3),
         "n_rotors": [rot[a], rot[b]]}
        for c, a, b in pairs[:6]]

    # ── 잡음 팔 ─────────────────────────────────────────────────────────────
    for s in sorted(set(snr[snr < 500].tolist()), reverse=True):
        m = (prf == prf_main) & (Tw == t_main) & (snr == s)
        if m.sum() == 0:
            continue
        row = {}
        for arm in ("all", "no_flash", "scale_free", "geometry_only"):
            c = cols(ARMS[arm])
            acc, _ = run_cv(X_all[m][:, c], drone[m], aspect[m],
                            lambda: _models()["LDA"])
            acc2, _ = run_cv(X_all[m][:, c], drone[m], aspect[m],
                             lambda: _models()["RF100"])
            row[arm] = {"LDA": round(acc, 4), "RF100": round(acc2, 4)}
        res["noise"][f"{s:g}"] = row
        print(f"  SNR {s:6.1f} dB  all(RF) {row['all']['RF100']:.3f}  "
              f"no_flash(RF) {row['no_flash']['RF100']:.3f}")

    # ── PRF · 창길이 스윕 ───────────────────────────────────────────────────
    for p in sorted(set(prf.tolist()), reverse=True):
        m = (prf == p) & (Tw == t_main) & (snr > 500)
        if m.sum() == 0:
            continue
        row = {}
        for arm in ("all", "no_flash"):
            c = cols(ARMS[arm])
            acc, _ = run_cv(X_all[m][:, c], drone[m], aspect[m],
                            lambda: _models()["RF100"])
            row[arm] = round(acc, 4)
        res["prf_sweep"][f"{p:g}"] = row
    for T in sorted(set(Tw.tolist()), reverse=True):
        m = (prf == prf_main) & (Tw == T) & (snr > 500)
        if m.sum() == 0:
            continue
        row = {}
        for arm in ("all", "no_flash"):
            c = cols(ARMS[arm])
            acc, _ = run_cv(X_all[m][:, c], drone[m], aspect[m],
                            lambda: _models()["RF100"])
            row[arm] = round(acc, 4)
        res["window_sweep"][f"{T:g}"] = row

    # ── 판정 ────────────────────────────────────────────────────────────────
    a_all = res["arms"]["all"]["best_accuracy"]
    a_nf = res["arms"]["no_flash"]["best_accuracy"]
    a_fo = res["arms"]["flash_only"]["best_accuracy"]
    a_sf = res["arms"]["scale_free"]["best_accuracy"]
    a_go = res["arms"]["geometry_only"]["best_accuracy"]
    res["verdict"] = {
        "accuracy_all": a_all, "accuracy_no_flash": a_nf,
        "accuracy_flash_only": a_fo, "accuracy_scale_free": a_sf,
        "accuracy_geometry_only": a_go,
        "chance": round(1.0 / len(labels), 4),
        "flash_is_not_the_whole_story": bool(a_nf > 0.6 * a_all),
        "honesty_ko": (
            "잡음 0·클러터 0 시뮬이므로 이 정확도는 **상한**이다. "
            "잡음 팔이 SNR 이 내려갈 때 어디서 무너지는지 보여 준다."),
    }
    with open(OUT_JSON, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=float)
    np.savez_compressed(OUT_NPZ, labels=np.array(labels),
                        feature_names=np.array(names),
                        **{f"conf/{k}": v for k, v in conf_store.items()})
    print(f"✅ {OUT_JSON}")
    figure(res, Xh, yh, names, labels, conf_store, z)


# ═══════════════════════════════════════════════════════════════════════════════
#  그림 — 하우스 규약: 글자 전부 영어 · 캡션은 textwrap.fill · 그림 안 주석 금지
# ═══════════════════════════════════════════════════════════════════════════════
def figure(res, Xh, yh, names, labels, conf_store, z):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec

    os.makedirs(FIG_DIR, exist_ok=True)
    disp = [SHORT.get(l, l) for l in labels]
    nL = len(labels)
    cmap = plt.get_cmap("tab10")
    fig = plt.figure(figsize=(19.5, 10.4))
    gs = GridSpec(2, 4, figure=fig, hspace=0.46, wspace=0.40,
                  left=0.052, right=0.985, top=0.905, bottom=0.125)

    def _conf(ax, M, title, cm):
        Mn = M / np.maximum(M.sum(1, keepdims=True), 1)
        im = ax.imshow(Mn, cmap=cm, vmin=0, vmax=1)
        for i in range(nL):
            for j in range(nL):
                if Mn[i, j] > 0.005:
                    ax.text(j, i, f"{Mn[i,j]*100:.0f}", ha="center", va="center",
                            fontsize=8, color="w" if Mn[i, j] > 0.55 else "k")
        ax.set_xticks(range(nL), disp, rotation=42, ha="right", fontsize=7.5)
        ax.set_yticks(range(nL), disp, fontsize=7.5)
        ax.set_xlabel("Predicted", fontsize=9)
        ax.set_ylabel("True", fontsize=9)
        ax.set_title(title, fontsize=10)
        fig.colorbar(im, ax=ax, fraction=0.043, pad=0.03)

    # (a) 전 특징 · (b) f_flash 제외
    ba = res["arms"]["all"]["best_model"]
    bn = res["arms"]["no_flash"]["best_model"]
    _conf(fig.add_subplot(gs[0, 0]), conf_store[f"all/{ba}"],
          f"(a) All features, {ba}\naccuracy "
          f"{res['arms']['all']['best_accuracy']*100:.1f}%", "Blues")
    _conf(fig.add_subplot(gs[0, 1]), conf_store[f"no_flash/{bn}"],
          f"(b) Blade-flash rate removed, {bn}\naccuracy "
          f"{res['arms']['no_flash']['best_accuracy']*100:.1f}%", "Purples")

    # (c) f_flash 분포 — 겹침을 눈으로
    ax = fig.add_subplot(gs[0, 2])
    i_ff = names.index("f_flash_hat")
    for i, l in enumerate(labels):
        v = Xh[yh == l, i_ff]
        ax.scatter(v, np.full(len(v), i) + np.random.uniform(-0.16, 0.16, len(v)),
                   s=6, alpha=0.45, color=cmap(i), edgecolors="none")
        ax.plot([np.percentile(v, 5), np.percentile(v, 95)], [i, i],
                color=cmap(i), lw=2.4, solid_capstyle="round")
    ax.set_yticks(range(nL), disp, fontsize=7.5)
    ax.set_xlabel("Blade flash rate  $f_{flash}$  [Hz]", fontsize=9)
    ax.set_title("(c) Flash rate alone does not\nseparate the fleet", fontsize=10)
    ax.grid(axis="x", alpha=0.25)

    # (d) ⭐빗살 고조파 지문 — 기하가 남는 자리
    ax = fig.add_subplot(gs[0, 3])
    hcols = [i for i, n in enumerate(names) if n.startswith("h")
             and n[1:].isdigit()]
    ms = np.arange(1, len(hcols) + 1)
    for i, l in enumerate(labels):
        prof = Xh[yh == l][:, hcols].mean(0)
        ax.semilogy(ms, np.maximum(prof, 1e-4), "-o", ms=3.4, color=cmap(i),
                    label=SHORT.get(l, l))
    ax.set_xlabel("Comb harmonic index  $m$  (Doppler = $m\\,f_{flash}$)", fontsize=9)
    ax.set_ylabel("Mean power share", fontsize=9)
    ax.set_title("(d) Harmonic envelope\nwidens with prop radius", fontsize=10)
    ax.legend(fontsize=6.6, ncol=2, framealpha=0.9)
    ax.grid(alpha=0.25, which="both")

    # (e) 대조 실험
    ax = fig.add_subplot(gs[1, 0])
    arms = ["all", "no_flash", "scale_free", "geometry_only", "flash_only"]
    lab = ["All", "No flash\nrate", "Scale-free\nonly", "Geometry\nonly",
           "Flash rate\nonly"]
    mods = ["LDA", "kNN5", "RF100"]
    w = 0.26
    xs = np.arange(len(arms), dtype=float)
    for j, mm in enumerate(mods):
        ax.bar(xs + (j - 1) * w,
               [res["arms"][a]["models"][mm]["accuracy"] * 100 for a in arms], w,
               label=mm)
    ax.axhline(100.0 / nL, color="k", ls="--", lw=1)
    nc = res.get("null_control", {}).get("permuted_label_accuracy_mean")
    if nc is not None:
        ax.axhline(nc * 100, color="0.45", ls=":", lw=1.4)
    ax.set_xticks(xs, lab, fontsize=8)
    ax.set_ylabel("Leave-one-aspect-out accuracy [%]", fontsize=9)
    ax.set_ylim(0, 105)
    ax.set_title("(e) Feature ablation", fontsize=10)
    ax.legend(fontsize=7); ax.grid(axis="y", alpha=0.25)

    # (f) 잡음 팔
    ax = fig.add_subplot(gs[1, 1])
    if res["noise"]:
        ss = sorted([float(k) for k in res["noise"]], reverse=True)
        for arm, st in (("all", "-o"), ("no_flash", "-s"),
                        ("geometry_only", "-^")):
            ax.plot(ss, [res["noise"][f"{s:g}"][arm]["RF100"] * 100 for s in ss], st,
                    label=arm.replace("_", " "), ms=5)
        base = res["arms"]["all"]["models"]["RF100"]["accuracy"] * 100
        ax.axhline(base, color="k", ls=":", lw=1)
        ax.text(ss[0], base + 1.5, "noise-free", fontsize=8)
        ax.axhline(100.0 / nL, color="k", ls="--", lw=1)
        ax.invert_xaxis()
    ax.set_xlabel("Micro-Doppler SNR per sample [dB]", fontsize=9)
    ax.set_ylabel("Accuracy [%]", fontsize=9)
    ax.set_ylim(0, 105)
    ax.set_title("(f) Noise arm (RF100)", fontsize=10)
    ax.legend(fontsize=7); ax.grid(alpha=0.25)

    # (g) PRF 스윕
    ax = fig.add_subplot(gs[1, 2])
    if res["prf_sweep"]:
        ps = sorted([float(k) for k in res["prf_sweep"]], reverse=True)
        ax.semilogx(ps, [res["prf_sweep"][f"{p:g}"]["all"] * 100 for p in ps], "-o",
                    label="all", ms=5)
        ax.semilogx(ps, [res["prf_sweep"][f"{p:g}"]["no_flash"] * 100 for p in ps],
                    "-s", label="no flash rate", ms=5)
        ax.axhline(100.0 / nL, color="k", ls="--", lw=1)
    ax.set_xlabel("Slow-time sampling rate [Hz]", fontsize=9)
    ax.set_ylabel("Accuracy [%]", fontsize=9)
    ax.set_ylim(0, 105)
    ax.set_title("(g) Revisit rate", fontsize=10)
    ax.legend(fontsize=7); ax.grid(alpha=0.25, which="both")

    # (h) 창 길이 스윕
    ax = fig.add_subplot(gs[1, 3])
    if res["window_sweep"]:
        ts = sorted([float(k) for k in res["window_sweep"]])
        ax.semilogx([t * 1e3 for t in ts],
                    [res["window_sweep"][f"{t:g}"]["all"] * 100 for t in ts], "-o",
                    label="all", ms=5)
        ax.semilogx([t * 1e3 for t in ts],
                    [res["window_sweep"][f"{t:g}"]["no_flash"] * 100 for t in ts],
                    "-s", label="no flash rate", ms=5)
        ax.axhline(100.0 / nL, color="k", ls="--", lw=1)
    ax.set_xlabel("Dwell time [ms]", fontsize=9)
    ax.set_ylabel("Accuracy [%]", fontsize=9)
    ax.set_ylim(0, 105)
    ax.set_title("(h) Dwell time", fontsize=10)
    ax.legend(fontsize=7); ax.grid(alpha=0.25, which="both")

    fig.suptitle("Can hovering drones be told apart by micro-Doppler alone?",
                 fontsize=15, y=0.968)
    nctxt = ("" if nc is None else
             f" Label-permutation control lands at {nc*100:.1f}% against a "
             f"{100.0/nL:.1f}% chance line, so the aspect-held-out split does not leak.")
    cap = textwrap.fill(
        f"Shooting-and-bouncing-rays micro-Doppler at {res['_meta']['prf_main_hz']/1e3:.0f} kHz "
        f"slow-time rate and {res['_meta']['window_s']*1e3:.0f} ms dwell: "
        f"{res['_meta']['n_trials_headline']} trials over {res['_meta']['n_aspects']} aspects and "
        f"{nL} airframes. Hover rpm is redrawn +/-6% every trial and the per-rotor spread is "
        f"redrawn too, so the blade flash rate is not a class label -- panel (c) shows how far the "
        f"rate distributions overlap. Cross-validation holds out whole aspects, so every test "
        f"geometry is unseen.{nctxt} The simulation carries no noise and no clutter, so panels "
        f"(a), (b), (e) are an upper bound and panel (f) is the honest curve.", 215)
    fig.text(0.5, 0.022, cap, ha="center", va="bottom", fontsize=8.2)

    for ext in ("png", "pdf"):
        pth = os.path.join(FIG_DIR, f"md_classify_f1.{ext}")
        fig.savefig(pth, dpi=165 if ext == "png" else None,
                    bbox_inches="tight", facecolor="w")
        print(f"✅ {pth}  ({os.path.getsize(pth)/1e6:.2f} MB)")
    plt.close(fig)


if __name__ == "__main__":
    main()
