#!/usr/bin/env python
"""광선 예산에 따라 «낙차» 와 «덜 적힌 줄» 이 어떻게 움직이나 — 이미 구운 샤드만 읽는다.

⛔2026-09-10 낱말 정정 — 「벌」은 CLAUDE.md:98 이 금지 예로 못 박은 우리끼리 쓰는 말이다
  (「벌」 ✗ → 「같은 줄이 몇 번 적히나」 ✓). 이 파일의 표 머리·읽기 줄을 전부 풀어 썼다.

■ 왜 이걸 만들었나
  2026-09-10 에 덱 6 쪽의 수(광선 40 배 · 경로 30 배 · 세 벌 그대로)를 샤드로 검산하다가,
  같은 사다리에서 **낙차 자세 수가 0 → 14 → 37 로 늘어나는 것**을 봤다. 덱은 그 축을
  「the count of copies did not move at all」로만 말한다 — 「같은 줄이 몇 번 적히나」의
  중앙값(3)은 맞지만
  **예외 자세 수는 움직인다.** 그 움직임을 원장으로 남긴다.

■ 무엇을 세나 (⛔둘은 다른 잣대다)
  · «줄<3»   — n_dup < 2 인 자세. 즉 같은 줄이 세 번 안 적힌 자세.
  · «낙차»   — |E| 가 자세 중앙값의 0.9 배 아래인 자세(덱 2 쪽이 쓰는 규칙).
  이 둘이 **같은 자세 집합인지**가 덱 3 쪽의 「낙차 자세에서 세 줄 중 하나가 빠져 있다」다.

■ ⛔이 판독기가 답하지 않는 것
  · ⛔«낙차가 광선의 산물이다» 로 읽지 않는다. 1e8 은 경로 중앙이 31 개뿐이라
    애초에 구조가 성기다 — 「적으면 안 보인다」와 「많으면 생긴다」를 이 축으로 못 가른다.
  · ⛔사다리가 있는 팔은 R0D0E0F1 하나뿐이다(다른 팔은 4e9 한 점씩). 팔을 건너 못 읽는다.
  · ⛔솔버 씨앗은 이 축에서 고정이다(elevation_sweep_md.py:893 seed=1 하드코딩).
    씨앗을 흔든 판은 40 m·el −15° 에만 있고 레벨 표준편차가 1.833 dB 다
    (outputs/raybudget_seed_ladder.json) — 이 칸에 옮겨 읽지 않는다.
  · ⛔실기 계측 대조는 0 건이다.

쓰는 법 (⛔CPU 전용 · 코어를 묶는다):
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" taskset -c 8-11 \
      /workspace/.venvs/py312/bin/python benchmark/read_dropladder_0910.py
"""
from __future__ import annotations
import glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
try:
    if len(os.sched_getaffinity(0)) > 8:
        os.sched_setaffinity(0, set(range(8, 12)))
except Exception:
    pass
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "2")

import numpy as np                                             # noqa: E402

SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "read_dropladder_0910.json")
MESH = "mfixbatteryi5_blperairframe"
EL, RNG, DEPTH, NPOSE = 0, 15, 2, 8192
DIP = 0.9                                   # 덱 2 쪽이 쓰는 낙차 규칙
ARMS = ("R0D0E0F1", "R0D1E0F1", "R0D1E1F1", "R1D0E0F1", "R1D1E1F1")
SPPS = (100_000_000, 1_000_000_000, 4_000_000_000)


def cell(arm: str, spp: int):
    """⛔n8192 와 메쉬 사이에 꼬리표가 **하나도 없는** 판만 — az·rep·bs·ps 를 섞지 않는다.

    ⚠2026-09-10 에 실제로 물렸다: 넓은 glob 으로 뽑았더니 자세가 65,536 개로 나왔다
      (같은 idx 를 쓰는 다른 판들이 겹쳐 들어왔다). 아래 이름은 **정확히** 맞춘다.
    """
    pat = (f"{SHD}/sionna_p{spp}_sw{arm}_r{RNG}_n{NPOSE}_{MESH}"
           f"_d{DEPTH}_el{EL:+g}_*.npz")
    fs = sorted(glob.glob(pat))
    if not fs:
        return None
    E, I, D, P = [], [], [], []
    n_expected = None
    for f in fs:
        z = np.load(f)
        E.append(z["E"]); I.append(z["idx"])
        D.append(z["n_dup"] if "n_dup" in z.files else np.full(z["idx"].shape, -1))
        P.append(z["npaths"] if "npaths" in z.files else np.full(z["idx"].shape, -1))
        if "meta" in z.files:
            _m = np.asarray(z["meta"]).ravel()
            if _m.size > 3:
                n_expected = int(_m[3])          # 이 칸이 원래 몇 자세짜리인가
    idx = np.concatenate(I)
    o = np.argsort(idx)
    #: ⭐2026-09-10 — idx 를 정렬 재료로만 쓰고 버리던 것을 고친다. 판정은 main() 이 한다.
    n_uni = int(np.unique(idx).size)
    ok = bool(n_uni == idx.size
              and (n_expected is None or idx.size == n_expected)
              and np.array_equal(idx[o], np.arange(idx.size)))
    return dict(n_shards=len(fs), files=[os.path.basename(f) for f in fs],
                E=np.concatenate(E)[o], D=np.concatenate(D)[o], P=np.concatenate(P)[o],
                idx_ok=ok, n_rows=int(idx.size), n_unique=n_uni, n_expected=n_expected)


def _copies_txt(r: dict) -> str:
    """화면에 찍을 «같은 줄이 몇 번». 중앙값이 정수가 아니면 그 사실을 보인다.

    ⛔2026-09-11 정정 — 09-10 에 `copies_median=None` 을 넣으면서 f-문자열 정렬이
      TypeError 로 죽었다(n_dup 중앙값이 1.5 인 칸). None 을 숫자 자리에 그대로 넣은 탓이다.
      ⚠«정수가 아니다» 는 «모르겠다» 이지 «못 찍는다» 가 아니다 — 중앙값을 괄호로 보인다.
    """
    c = r.get("copies_median")
    if c is not None:
        return str(c)
    m = r.get("n_dup_median")
    return "?" if m is None else f"?({m:g})"


def main() -> int:
    print(f"■ 앙각 {EL:+g} · {RNG} m · 깊이 {DEPTH} · 빈 하늘 · 자세 {NPOSE} · 낙차 규칙 {DIP}\n")
    print(f"  {'팔':<10}{'광선':>15}{'샤드':>5}{'자세':>7}{'경로중앙':>9}"
          f"{'줄<3':>6}{'낙차':>6}{'공통':>6}{'줄수중앙':>9}")
    rows, skipped = [], []
    for arm in ARMS:
        for spp in SPPS:
            c = cell(arm, spp)
            if c is None:
                continue
            E, D, P = c["E"], c["D"], c["P"]
            if (D < 0).all():
                continue
            #: ⭐⭐2026-09-10 — **완전성 게이트를 새로 단다.** 전에는 샤드 수도 배열 길이도
            #  자세 인덱스도 안 봐서, 반쪽 칸이 들어오면 아무 말 없이 그 위에서 중앙값을 쟀다
            #  (창고에 지금 `sionna_p4000000000_el-75` 가 샤드 4 개·2,048/4,096 로 있다).
            #  ⛔거절 사유를 화면과 원장에 남긴다 — 조용히 건너뛰지 않는다.
            if not c["idx_ok"]:
                skipped.append(dict(arm=arm, spp=spp, why="자세 인덱스가 온전하지 않다",
                                    rows=c["n_rows"], unique=c["n_unique"],
                                    expected=c["n_expected"], n_shards=c["n_shards"]))
                print(f"  ⛔{arm:<10}{spp:>15,}  자세 인덱스 불완전 "
                      f"({c['n_unique']}/{c['n_rows']}, 기대 {c['n_expected']}) — 건너뛴다",
                      flush=True)
                continue
            a = np.abs(E); med = float(np.median(a))
            #: ⛔⛔2026-09-10 정정 — **결측을 «덜 적힌 줄» 로 세지 않는다.**
            #  `n_dup` 이 없는 세대의 샤드는 −1 로 채워 두는데, 옛 `short = D < 2` 는 그 −1 을
            #  전부 「세 번 안 적힌 자세」로 셌다. 합성 자료로 재현했다: n_dup 미기록 4,096 행이
            #  short 4,096 건으로 잡혔다. ⇒ 계측된 자세(`have`)만 분모로 쓰고, 미계측은 따로 센다.
            #  ⚠발간 7 칸에서는 미기록이 0 이라 지금 수는 안 바뀐다 — 잠재 결함을 닫는 것이다.
            have = D >= 0
            short = have & (D < 2)              # 같은 줄이 세 번 안 적힌 자세(계측된 것만)
            dip = (a / med) < DIP               # 덱 2 쪽 규칙
            #: ⛔중앙값이 정수가 아닐 때 int() 가 0 쪽으로 잘라 **한 줄 적게** 찍히던 자리다
            #  (n_dup 1 과 2 가 같은 수면 중앙 1.5 → 2 로 찍혀 3 이 아니라 2 가 된다).
            #  ⇒ 중앙값을 그대로 싣고, 정수일 때만 «몇 줄» 로 부른다.
            _dmed = float(np.median(D[have])) if have.any() else None
            _copies = (int(_dmed) + 1) if (_dmed is not None and float(_dmed).is_integer()) else None
            r = dict(arm=arm, spp=spp, n_shards=c["n_shards"], n_poses=int(E.size),
                     npaths_median=(int(np.median(P[P >= 0])) if (P >= 0).any() else None),
                     n_short=int(short.sum()), n_dip=int(dip.sum()),
                     n_both=int((short & dip).sum()),
                     n_measured=int(have.sum()), n_unmeasured=int((~have).sum()),
                     n_dup_median=_dmed, copies_median=_copies,
                     #: ⚠«한 줄이 몇 번 적혔나» 로 부르려면 **중복 무리가 하나** 여야 한다.
                     #  n_dup 은 «전체 행 − 고유 키» 라 서로 다른 무리로도 같은 총수가 나온다.
                     #  이 판독기는 그 조건을 **검사하지 않는다** — 무리가 하나라는 것은 경로
                     #  목록을 직접 뜬 outputs/copies_id_0903.json 이 세운 것이지 이 수가 아니다.
                     copies_median_caveat_ko=("중복 무리가 하나일 때만 «한 줄이 몇 번» 으로 "
                                              "읽는다. 이 판독기는 그 조건을 검사하지 않는다 "
                                              "— 근거는 outputs/copies_id_0903.json 이다."),
                     #: ⛔⛔2026-09-11 정정 — 이 딱지는 **계측된 자세 안에서만** 성립한다.
                     #  n_dup 이 없는 자세(−1)는 short 에서 빠지므로, 절반만 계측된 칸에서도
                     #  「완전 일치」로 찍혔다(합성 입력으로 재현). ⇒ 계측이 온전한 칸에서만
                     #  True 를 주고, 아니면 None 으로 둔다 — «모른다» 와 «같다» 를 가른다.
                     dip_equals_short=(
                         bool(int(short.sum()) == int(dip.sum()) == int((short & dip).sum()))
                         if bool(have.all()) else None),
                     dip_equals_short_scope_ko=(
                         "계측된 자세 전부에서 잰다. n_dup 이 없는 자세가 하나라도 있으면 "
                         "null 이다 — 그때는 «낙차 = 줄<3» 을 전체 자세에 대해 말할 수 없다."),
                     files=c["files"])
            rows.append(r)
            print(f"  {arm:<10}{spp:>15,}{r['n_shards']:>5}{r['n_poses']:>7}"
                  f"{str(r['npaths_median']):>9}{r['n_short']:>6}{r['n_dip']:>6}"
                  f"{_copies_txt(r):>9}"
                  f"{'  ⭐일치' if r['dip_equals_short'] else ('' if r['dip_equals_short'] is False else '  ⚠부분계측')}",
                  flush=True)

    lad = [r for r in rows if r["arm"] == "R0D0E0F1"]
    lad.sort(key=lambda r: r["spp"])
    print("\n  ── 읽기 ──")
    if len(lad) > 1:
        print(f"  광선 사다리(R0D0E0F1): 낙차 {[r['n_dip'] for r in lad]} "
              f"· 줄<3 {[r['n_short'] for r in lad]} · 경로중앙 {[r['npaths_median'] for r in lad]}")
        print(f"  같은 줄이 몇 번 적히나(중앙): {[_copies_txt(r) for r in lad]}"
              f"  ← 덱 6 쪽의 «Still three»")
    n_eq = sum(1 for r in rows if r["dip_equals_short"] is True)
    n_partial = sum(1 for r in rows if r["dip_equals_short"] is None)
    print(f"  «낙차 = 줄<3» 이 정확히 맞는 칸: {n_eq}/{len(rows)}"
          + (f"  (⚠계측이 반쪽이라 못 재는 칸 {n_partial})" if n_partial else ""))

    out = {"_meta": {#: ⭐관문(check_new_file_rules.py:166)이 보는 키는 «generator» 다 —
                     #  «made» 로 적어 «못 굽는 원장» 으로 걸리던 것을 고친다(2026-09-10).
                     "generator": "benchmark/read_dropladder_0910.py",
                     "elevation_deg": EL, "range_m": RNG, "depth": DEPTH,
                     "scene": "빈 하늘", "mesh": MESH, "n_poses": NPOSE,
                     "dip_rule": DIP,
                     "dip_rule_ko": "|E| / 자세중앙값 < 0.9 — 덱 2 쪽이 쓰는 규칙",
                     "short_rule_ko": ("n_dup < 2 — 같은 줄이 세 번 안 적힌 자세. "
                                       "⛔n_dup 이 없는 세대의 자세(−1)는 «미계측» 으로 "
                                       "따로 세고 이 수에 넣지 않는다(2026-09-10 정정)."),
                     "skipped": skipped},
           "rows": rows,
           "limits_ko": [
               "⛔«낙차가 광선의 산물이다» 로 읽지 않는다. 1e8 은 경로 중앙이 31 개뿐이라 "
               "구조가 애초에 성기다 — 「적으면 안 보인다」와 「많으면 생긴다」를 못 가른다.",
               "⛔사다리가 있는 팔은 R0D0E0F1 하나뿐이다. 다른 팔은 4e9 한 점씩이라 "
               "팔을 건너 읽을 수 없다.",
               "⛔솔버 씨앗은 이 축에서 고정이다(elevation_sweep_md.py:893 seed=1). "
               "씨앗을 흔든 판은 40 m·el −15° 에만 있고 레벨 표준편차 1.833 dB 다"
               "(outputs/raybudget_seed_ladder.json) — 이 칸에 옮겨 읽지 않는다.",
               "⛔광선 수를 바꾸면 경로 수와 경로당 가중치가 함께 움직인다"
               "(field_calculator.py:221 의 4π/samples_per_src). 단일 변수가 아니다. "
               "⛔이것을 «솔버의 결함» 으로도 «상쇄되니 괜찮다» 로도 읽지 않는다 — 재 보지 않았다.",
               "⛔낙차 규칙 0.9 는 자유 파라미터다. 다른 문턱에서 수가 달라진다.",
               "⛔실기 계측 대조는 0 건이다. 이 판으로도 안 생긴다."]}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n  원장 → {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
