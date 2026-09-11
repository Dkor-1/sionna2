#!/usr/bin/env python
"""협곡의 «널» 을 읽는다 — 0922 A 묶음. ⛔이미 구운 샤드만 쓴다(GPU 안 씀).

■ 왜 필요한가
  협곡에서 「걸린 자세 목록」을 다른 손잡이와 견주려면 **아무것도 안 바꿨을 때 얼마나
  흔들리나** 를 먼저 알아야 한다. 우리 씬(outdoor01_ground)에서는 그 값이 있는데
  (RESUME_0909 §① — 82 중 80), **협곡에서는 한 번도 없었다.**
  0922 A 가 그것을 샀다: 같은 설정 되풀이(rep1·rep2)와 광선 예산 ±5 %(3.8e9·4.2e9).

■ ⛔이 판독기가 답하지 않는 것 — 이름부터 조심한다
  · ⛔**«널» 이 아니다.** 초기 광선은 씨앗 없는 결정적 피보나치 격자다
    (sionna/rt/utils/ray_tracing.py:24-30). 같은 설정 되풀이가 자카드 1.000 이면
    그것은 «수치 재현성» 이지 «표본 흔들기» 가 아니다(RESUME_0909 §②).
    ⇒ 광선 예산 쪽은 **«격자를 갈았을 때의 민감도»** 로만 부른다. 신뢰구간이 아니다.
  · ⛔광선 수를 바꾸면 경로 수와 **경로당 가중치**가 함께 움직인다
    (field_calculator.py:221 의 4π/samples_per_src). 단일 변수가 아니다.
    ⛔이것을 «솔버의 결함» 으로도 «상쇄되니 괜찮다» 로도 읽지 않는다 — 재 보지 않았다.
  · ⛔D = E_장면 − E_빈하늘 은 «환경 산란» 이 아니다 — 차폐·드론 경로 변화·후보 탐색
    차이가 함께 들어간다. 「장면이 얹은 몫」으로만 부른다.
  · ⛔approx_* 는 균일·독립 추출을 가정한 참고값이다. 자세는 시각이고 로터 위상
    구조가 있다 — 유의성 검정이 아니다.
  · ⛔실기 계측 대조는 0 건이다.

■ 잣대는 benchmark/read_0918B_0909.py 를 **그대로 가져다 쓴다**(import). 새로 만들지 않는다.

쓰는 법 (⛔CPU 전용 · 코어를 묶는다):
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" taskset -c 8-11 \
      /workspace/.venvs/py312/bin/python benchmark/read_canyonnull_0910.py
"""
from __future__ import annotations
import glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, os.path.join(ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    if len(os.sched_getaffinity(0)) > 8:
        os.sched_setaffinity(0, set(range(8, 12)))
except Exception:
    pass
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "2")

import numpy as np                                    # noqa: E402
from read_0918B_0909 import measure, DEV, CAP         # noqa: E402

SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "read_canyonnull_0910.json")
MESH = "mfixbatteryi5_blperairframe"
ARM, ENV = "R0D0E0F1", "sionna:simple_street_canyon"
ENVTAG = "envsionna-simple_street_canyon"
ELS = (-30.0, -60.0)
#: (이름, spp, rep) — ⛔«널» 이라 부르지 않는다
CELLS = [("기준선 (4e9)",           4_000_000_000, 0),
         ("되풀이 1 (같은 설정)",    4_000_000_000, 1),
         ("되풀이 2 (같은 설정)",    4_000_000_000, 2),
         ("격자 3.8e9 (−5 %)",      3_800_000_000, 0),
         ("격자 4.2e9 (+5 %)",      4_200_000_000, 0)]


def stem(spp: int, rep: int, env: bool) -> str:
    """⛔elevation_sweep_md 의 이름 차례를 그대로 — rep 가 env 앞이다(:449-471)."""
    s = f"sionna_p{spp}_sw{ARM}_r15_n8192"
    if rep:
        s += f"_rep{rep}"
    if env:
        s += f"_{ENVTAG}"
    return f"{s}_{MESH}_d2"


def _trunc_of(z, fname):
    """샤드 하나의 «경로 상한에 붙은 자세 수». 없으면 None.

    ⛔⛔**저장값을 그대로 싣지 않는다** (2026-09-10 검증에서 잡혔다).
      `n_trunc` 는 [잘린 자세 수, 그때 쓴 상한] 두 칸인데, 그 첫 칸은 **구울 때의 문턱**으로
      센 값이다. 문턱은 0.999 → 0.99 로 한 번 내려갔고(elevation_sweep_md.py:957-959
      「문턱을 0.999 로 잡았더니 실제 포화를 놓쳤다 ⇒ 0.99 로 내린다」), 옛 문턱으로 구운
      샤드가 창고에 남아 있다. 실측: `n_trunc`·`nret` 을 함께 가진 샤드 576 장 가운데
      **14 장이 어긋나고, 그중 12 장은 저장값이 0 인데 지금 규칙으로는 전 자세가 «상한 근접
      경고» 에 해당**한다. ⛔「잘렸다」로 옮겨 적지 않는다 — 아래 단서 그대로 이것은 돌아온
      경로 수의 어림수이지 후보가 잘렸다는 직접 증거가 아니다(검토자 지적 2026-09-10).
      ⇒ 저장값은 `stored` 로만 남기고, **저장된 `nret` 과 저장된 상한으로 지금 규칙을
        다시 계산**한 값을 싣는다. `nret` 이 없는 옛 샤드는 `None`(진단 미수집)이다.
      ⛔«경고 없음» 과 «진단 미수집» 을 같은 것으로 세지 않는다.
    ⚠`nret` 은 돌아온 경로 수라 상한 근접의 **어림수**다 — 후보가 잘렸는지를 직접 잰 것이
      아니다. 0 이라고 «안 잘렸다» 가 증명되지는 않는다.
    """
    has_nt = "n_trunc" in z.files
    stored, cap = None, None
    if has_nt:
        _nt = np.asarray(z["n_trunc"]).ravel()
        stored = int(_nt[0])
        cap = int(_nt[1]) if _nt.size > 1 else None
    #: ⛔상한이 안 적힌 샤드를 규약값 CAP 으로 메우지 않는다 — 그 샤드가 어느 상한으로
    #  구워졌는지 모르는 채 «경고 없음» 을 만들어 내게 된다(검토자 지적 2026-09-10).
    #  ⇒ «미확인» 으로 남긴다.
    if cap is None:
        return dict(file=fname, stored=stored, cap=None, recomputed=None,
                    note_ko="샤드에 상한이 안 적혔다 — 미확인(규약값으로 메우지 않는다)")
    if "nret" not in z.files:
        return dict(file=fname, stored=stored, cap=cap, recomputed=None,
                    note_ko="nret 없음 — 진단 미수집")
    nr = np.asarray(z["nret"])
    return dict(file=fname, stored=stored, cap=cap,
                #: ⭐이름 그대로 «상한 근접 경고에 해당하는 자세 수» 다. ⛔«잘린 자세 수» 가 아니다.
                recomputed=int(np.count_nonzero(nr >= 0.99 * cap)),
                nret_max=int(nr.max()), n_poses=int(nr.size))


def load(name: str, el: float):
    """샤드를 idx 로 이어 붙인다. ⭐idx 를 **버리지 않고** 온전성을 함께 싣는다.

    ⛔⛔2026-09-10 검증 정정 — 전에는 `argsort` 의 재료로만 쓰고 idx 를 버려서
      **중복·누락을 못 봤다.** 합성 자료로 재현했다: 8,192 행이지만 고유 인덱스가 4,096 뿐인
      칸을 그대로 받아들였다(길이만 맞으면 통과).
    ⚠그렇다고 여기서 **거절하지는 않는다.** 샤드는 여러 장으로 엇갈려 채워지고 큐가 도는
      중에는 반쪽 칸이 정상적으로 존재한다. 판정은 부르는 쪽(main·_deck_mask_table)이 한다.
    """
    fs = sorted(glob.glob(f"{SHD}/{name}_el{el:+g}_*.npz"))
    if not fs:
        return None, 0
    E, I, P, D, TR = [], [], [], [], []
    n_expected, prf, meta_mismatch = None, None, []
    for f in fs:
        z = np.load(f)
        E.append(z["E"]); I.append(z["idx"])
        P.append(z["npaths"] if "npaths" in z.files else np.full(z["idx"].shape, -1))
        D.append(z["n_dup"] if "n_dup" in z.files else np.full(z["idx"].shape, -1))
        TR.append(_trunc_of(z, os.path.basename(f)))
        if "meta" in z.files:
            _m = np.asarray(z["meta"]).ravel()
            if _m.size > 3:
                #: ⛔⛔2026-09-11 — 샤드마다 **선언 표본수·표집률이 같은지** 본다.
                #  전에는 마지막 샤드의 값으로 덮어써서, 8,192 짜리와 4,096 짜리가 한 칸에
                #  섞여도 통과했다. 다르면 그 사실을 실어 부르는 쪽이 거절하게 한다.
                _n, _prf = int(_m[3]), (float(_m[4]) if _m.size > 4 else None)
                if n_expected is not None and _n != n_expected:
                    meta_mismatch.append(dict(file=os.path.basename(f),
                                              n_poses=_n, seen=n_expected))
                if prf is not None and _prf is not None and _prf != prf:
                    meta_mismatch.append(dict(file=os.path.basename(f),
                                              prf_hz=_prf, seen=prf))
                n_expected, prf = _n, (_prf if _prf is not None else prf)
    idx = np.concatenate(I)
    o = np.argsort(idx)
    idx_sorted = idx[o]
    n_uni = int(np.unique(idx).size)
    Ecat = np.concatenate(E)[o]
    #: ⛔비유한 전계도 잡는다 — 전에는 idx 만 봤다(2026-09-11).
    #  ⛔⛔`E.view(float)` 로 세면 **complex64 에서 못 잡는다**(비트 재해석이지 형 변환이 아니다).
    #    실측 2026-09-11: complex64 에 NaN 하나를 넣어도 view(float) 로는 0 건이 나온다.
    #    ⇒ **복소 배열에 그대로** np.isfinite 를 건다. 지금 샤드는 complex128 이라 값은 안 바뀐다.
    n_bad = int(np.count_nonzero(~np.isfinite(Ecat)))
    ok = bool(n_uni == idx.size
              and (n_expected is None or idx.size == n_expected)
              and np.array_equal(idx_sorted, np.arange(idx.size))
              and not meta_mismatch
              and n_bad == 0)
    #: 진단 미수집(옛 샤드)과 «경고 없음» 을 가른다
    _rec = [t["recomputed"] for t in TR if t["recomputed"] is not None]
    return dict(E=Ecat, npaths=np.concatenate(P)[o],
                n_dup=np.concatenate(D)[o], n_shards=len(fs),
                trunc=TR,
                n_trunc_now=(int(sum(_rec)) if _rec else None),
                n_shards_without_diag=int(len(TR) - len(_rec)),
                idx_ok=ok, n_rows=int(idx.size), n_unique=n_uni,
                n_expected=n_expected, prf_hz=prf,
                meta_mismatch=meta_mismatch, n_nonfinite=n_bad,
                files=[os.path.basename(f) for f in fs]), len(fs)


#: ⭐덱이 쓰는 잣대로도 함께 잰다 — ⛔다시 구현하지 않고 **덱의 함수를 그대로 부른다**.
#   두 잣대가 갈리면 그 자체가 알아야 할 사실이라 나란히 남긴다.
DECK = "/workspace/team_meeting/teammeeting_0910"


def _deck_mask_table(loadfn, stemfn, els, cells):
    """덱의 hampel_mask(win=51, k=5.0)로 같은 칸을 다시 센다. 못 부르면 None."""
    if DECK not in sys.path:
        sys.path.insert(0, DECK)
    try:
        from bake_outdoor import hampel_mask          # noqa: PLC0415
    except Exception as e:                            # noqa: BLE001
        return {"unavailable_ko": f"덱 모듈을 못 불렀다 — {type(e).__name__}: {e}"}
    out = {}
    for el in els:
        base, _nb = loadfn(stemfn(4_000_000_000, 0, True), el)
        #: ⛔⛔2026-09-11 — 기준선 자신의 온전성을 안 봤다. 비교 대상만 검사하면
        #  기준선이 반쪽이어도 그 위에서 잰 자카드가 그대로 실린다.
        if base is None or _nb < 2 or not base["idx_ok"]:
            out[f"{el:+g}"] = {"unavailable_ko": (
                "기준선 칸이 온전하지 않다 — "
                f"샤드 {_nb} · " + ("불러오기 실패" if base is None else
                f"자세 {base['n_unique']}/{base['n_rows']}(기대 {base['n_expected']})"))}
            continue
        mb = hampel_mask(np.abs(base["E"]), 51, 5.0)
        rows = {}
        for nm, spp, rep in cells:
            c, n = loadfn(stemfn(spp, rep, True), el)
            #: ⭐2026-09-10 — 길이만 보던 게이트에 **idx 온전성**을 더한다. 이 표가 덱의
            #  96·339 를 만드는 자리라 main() 쪽만 고치면 덱이 옛 게이트에 남는다.
            #: ⛔2026-09-11(2) — 이 표도 **비교 쌍의 표집률**을 봐야 한다. 길이·idx 만 보면
            #  19,700 Hz 기준선과 10,000 Hz 비교판이 그대로 견줘진다.
            if (c is None or n < 2 or c["E"].size != mb.size or not c["idx_ok"]
                    or (c.get("prf_hz") and base.get("prf_hz") and c["prf_hz"] != base["prf_hz"])):
                continue
            m = hampel_mask(np.abs(c["E"]), 51, 5.0)
            inter = int((m & mb).sum()); uni = int((m | mb).sum())
            rows[nm] = dict(n_mask=int(m.sum()), n_common=inter,
                            jaccard=round(inter / max(uni, 1), 4))
        out[f"{el:+g}"] = rows
    return out


def main() -> int:
    out = {"_meta": {#: ⭐관문(check_new_file_rules.py:166)이 보는 키는 «generator» 다 —
                     #  «made» 로 적어 «못 굽는 원장» 으로 걸리던 것을 고친다(2026-09-10).
                     "generator": "benchmark/read_canyonnull_0910.py",
                     "scene": ENV, "arm": ARM, "range_m": 15, "depth": 2,
                     "n_poses": 8192, "dev_rule": DEV, "path_cap": CAP,
                     "what_ko": "협곡에서 «아무것도 안 바꿨을 때» 사건 목록이 얼마나 흔들리나",
                     "naming_ko": ("⛔«널» 이라 부르지 않는다 — 초기 광선은 씨앗 없는 결정적 "
                                   "피보나치 격자다. 되풀이는 «수치 재현성», 예산 변경은 "
                                   "«격자를 갈았을 때의 민감도» 다.")},
           "by_el": {}}
    for el in ELS:
        print(f"\n■ 앙각 {el:+g} · 협곡 · 팔 {ARM} · 깊이 2 · 잣대 DEV={DEV}")
        flags, cells, missing = {}, {}, []
        for nm, spp, rep in CELLS:
            sc, ns = load(stem(spp, rep, True), el)
            fr, nf = load(stem(spp, rep, False), el)
            if sc is None or fr is None or ns < 2 or nf < 2:
                missing.append(dict(cell=nm, scene_shards=ns, free_shards=nf))
                print(f"  ⏳{nm:<24} 샤드 부족 (협곡 {ns} · 빈하늘 {nf}) — 건너뛴다")
                continue
            #: ⭐2026-09-10 — 자세 인덱스가 빠짐없이 한 번씩 있는 칸만 읽는다.
            #  ⛔거절 사유를 «샤드 부족» 과 섞지 않는다 — 반쪽 칸이 조용히 실리던 자리다.
            #: ⛔⛔2026-09-11 — **비교 쌍의 시간축이 같은지** 본다. 전에는 한 칸 안의 샤드끼리만
            #  봐서, 빈하늘 19,700 Hz · 장면 10,000 Hz 인 짝이 그대로 비교됐다(합성으로 재현).
            _pair = []
            if sc.get("prf_hz") and fr.get("prf_hz") and sc["prf_hz"] != fr["prf_hz"]:
                _pair.append(dict(what="표집률", scene=sc["prf_hz"], free=fr["prf_hz"]))
            if sc.get("n_expected") and fr.get("n_expected") and sc["n_expected"] != fr["n_expected"]:
                _pair.append(dict(what="선언 표본수", scene=sc["n_expected"], free=fr["n_expected"]))
            if _pair:
                missing.append(dict(cell=nm, why="비교 쌍의 시간축이 다르다", mismatch=_pair))
                print(f"  ⛔{nm:<24} 비교 쌍 시간축 불일치 — {_pair}")
                continue
            if not (sc["idx_ok"] and fr["idx_ok"]):
                missing.append(dict(cell=nm, why="자세 인덱스가 온전하지 않다",
                                    scene=dict(rows=sc["n_rows"], unique=sc["n_unique"],
                                               expected=sc["n_expected"]),
                                    free=dict(rows=fr["n_rows"], unique=fr["n_unique"],
                                              expected=fr["n_expected"])))
                print(f"  ⛔{nm:<24} 자세 인덱스 불완전 "
                      f"(협곡 {sc['n_unique']}/{sc['n_rows']} · 빈하늘 {fr['n_unique']}/{fr['n_rows']})")
                continue
            if sc["E"].size != fr["E"].size:
                missing.append(dict(cell=nm, why="자세 수 불일치")); continue
            r = measure(fr, sc)
            if r is None:
                missing.append(dict(cell=nm, why="measure 실패")); continue
            flags[nm] = r.pop("_flag")
            r["files_scene"] = sc["files"]
            #: ⭐상한 근접 진단 — 지금 규칙(0.99×저장된 상한)으로 다시 센 값. 미수집은 따로 센다.
            r["path_cap"] = dict(
                scene=dict(n_trunc_now=sc["n_trunc_now"],
                           shards_without_diag=sc["n_shards_without_diag"]),
                free=dict(n_trunc_now=fr["n_trunc_now"],
                          shards_without_diag=fr["n_shards_without_diag"]),
                note_ko=("«상한 근접 경고에 해당하는 자세 수» 다 — 저장된 nret 과 저장된 "
                         "상한으로 지금 문턱(0.99)을 다시 적용해 셌다. ⛔«잘린 자세 수» 로 "
                         "옮겨 적지 않는다: nret 은 돌아온 경로 수의 어림수이지 후보가 잘렸다는 "
                         "직접 계측이 아니다. 샤드에 적힌 n_trunc 는 구울 때의 문턱(0.999 세대가 "
                         "섞여 있다)이라 그대로 싣지 않고 stored 로만 남긴다. "
                         "null 은 «진단 미수집·미확인» 이고 «경고 없음» 이 아니다."))
            cells[nm] = r
            print(f"  {nm:<24} 사건 {r['n_static_changed']:>4} ({r['share_pct']:>5} %)"
                  f" · 경로중앙 {r.get('npaths_median')}"
                  f"{'  ⛔상한' if r.get('at_path_cap') else ''}", flush=True)
        base = "기준선 (4e9)"
        pairs = {}
        if base in flags:
            fb = flags[base]; nb = int(fb.sum())
            print(f"\n  기준선 사건 {nb} 개 — 그 중 몇 개가 살아남나")
            print(f"    {'칸':<24}{'남음':>6}{'잃음':>6}{'새로':>6}{'자카드':>9}{'참고 자카드':>12}")
            for nm, fa in flags.items():
                if fa.size != fb.size:
                    continue
                inter = int((fa & fb).sum()); uni = int((fa | fb).sum())
                na = int(fa.sum()); e = na * nb / fa.size
                pairs[nm] = dict(n_a=na, n_b=nb, n_intersect=inter,
                                 kept=inter, lost=int((fb & ~fa).sum()),
                                 brand_new=int((~fb & fa).sum()),
                                 jaccard=round(inter / max(uni, 1), 4),
                                 expected_intersect_if_unrelated=round(e, 3),
                                 approx_jaccard_if_unrelated=round(e / max(na + nb - e, 1e-9), 5))
                p = pairs[nm]
                print(f"    {nm:<24}{p['kept']:>6}{p['lost']:>6}{p['brand_new']:>6}"
                      f"{p['jaccard']:>9.4f}{p['approx_jaccard_if_unrelated']:>12.5f}")
        out["by_el"][f"{el:+g}"] = dict(cells=cells, pairs=pairs, missing=missing,
                                        baseline_events=(int(flags[base].sum())
                                                         if base in flags else None))
    out["deck_rule_hampel"] = _deck_mask_table(load, stem, ELS, CELLS)
    out["deck_rule_note_ko"] = (
        "⭐덱(teammeeting_0910)이 그림에 쓰는 잣대는 이 파일의 D-편차 규칙이 아니라 "
        "|E| 에 건 Hampel(win=51 · k=5.0)이다. 발표에서 말하는 96·339 가 그 수다. "
        "⛔다시 구현하지 않고 덱의 함수를 그대로 불러 쟀다. "
        "실측(2026-09-10): el−30 은 96 → 114(−5 %)·112(+5 %) 로 **수까지 움직이고**, "
        "el−60 은 339 → 332·335 로 **수는 안정한데 집합이 0.80·0.83 만 겹친다** — "
        #: ⛔2026-09-10 정정 — 분모를 적는다. 셋이 서로 다른 수다.
        "겹침 0.80 은 **합집합에서 공통이 아닌 몫** 이 20.1 %(75/373)라는 뜻이다 — "
        "기준 사건의 탈락률은 12.1 %(41/339)이고 전체 자세 8,192 중 판정이 바뀐 몫은 "
        "0.92 %(75/8,192)다. 세 비율의 분모가 다르니 «다섯 중 하나» 를 분모 없이 말하지 않는다.")
    out["approx_jaccard_note_ko"] = (
        "⛔이름을 2026-09-11 에 expected_ → approx_ 로 고쳤다. 이 값은 «자카드의 기댓값» 이 "
        "**아니다** — 기대 교집합 n_a·n_b/N 을 비율식 J = ∩/(a+b−∩) 에 **넣은 근삿값**이다. "
        "비율의 기댓값과 기댓값의 비율은 다르다(이 예에서 0.00503 대 0.00506). "
        "⛔애초에 유의성 검정이 아니다 — 자세는 시각이고 로터 위상 구조가 있다.")
    out["limits_ko"] = [
        "⛔«널» 이 아니다 — 초기 광선은 씨앗 없는 결정적 피보나치 격자다"
        "(sionna/rt/utils/ray_tracing.py:24-30). 되풀이가 1.000 이면 «수치 재현성» 이고, "
        "예산 변경은 «격자를 갈았을 때의 민감도» 다. 두 점은 신뢰구간이 아니다.",
        "⛔광선 수를 바꾸면 경로 수와 경로당 가중치가 함께 움직인다"
        "(field_calculator.py:221). 단일 변수가 아니다. ⛔이것을 «솔버의 결함» 으로도 "
        "«상쇄되니 괜찮다» 로도 읽지 않는다 — 재 보지 않았다.",
        "⛔D = E_장면 − E_빈하늘 은 «환경 산란» 이 아니다 — 차폐·드론 경로 변화·후보 "
        "탐색 차이가 함께 들어간다.",
        "⛔approx_* 는 균일·독립 추출을 가정한 참고값이다 — 유의성 검정이 아니다.",
        "⛔잣대 DEV=0.5 는 자유 파라미터다. 다른 값에서 수가 달라진다.",
        "⛔실기 계측 대조는 0 건이다."]
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n  원장 → {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
