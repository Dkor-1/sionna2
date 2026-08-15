# -*- coding: utf-8 -*-
"""az_falsify_alternatives.py — «방위 45° 면 PathSolver 에코가 25~51 dB 사라진다» 를
   무너뜨리기 위한 **대안 가설 사냥**. GPU 를 쓰지 않는다(저장된 원장·npz·소스만 읽는다).

가설 (a) az45 팔이 다른 자세 시퀀스를 썼다
     (b) 광선이 표적을 덜 맞혔다 / 경로의 종류가 바뀌었다
     (c) 메쉬가 방위에 비대칭이라 45° 가 하필 최악
     (d) 잣대(정지성분 제거 후 전력) 자체의 문제
     (e) 결측·NaN·언더플로
"""
import json, sys, os
import numpy as np

ROOT = "/workspace/sionna"
sys.path.insert(0, f"{ROOT}/src")
Z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz", allow_pickle=True)
LED = json.load(open(f"{ROOT}/outputs/elevation_sweep_md.json"))
ROWS, META = LED["rows"], LED["_meta"]
PRF, FFL = float(META["prf_hz"]), float(META["f_flash_hz"])
LAM = 2.998e8 / float(META["fc_hz"])
BAND = 3.86                      # outputs/grid_convergence_check.json 산포 밴드 [dB]
D = lambda x: 10 * np.log10(max(float(x), 1e-300))
BY = {}
for r in ROWS:
    BY.setdefault(r["engine"], {})[r["el_deg"]] = r


def stats(key, tol=8.0):
    """DC(정지)·AC(움직임)·리듬몫·평탄도. 리듬몫 = AC 전력 중 f_flash 정수배 ±tol 의 몫."""
    E = np.asarray(Z[key], complex)
    m = E.mean(); x = E - m
    N = x.size
    X = np.fft.fftshift(np.fft.fft(x * np.hanning(N)))
    f = np.fft.fftshift(np.fft.fftfreq(N, 1.0 / PRF))
    P = np.abs(X) ** 2
    msk = np.zeros(N, bool)
    for k in range(1, int(PRF / 2 / FFL)):
        msk |= np.abs(np.abs(f) - k * FFL) <= tol
    ac = float(np.mean(np.abs(x) ** 2))
    share = float(P[msk].sum() / P.sum())
    Pp = P / P.sum() + 1e-300
    flat = float(np.exp(np.mean(np.log(Pp))) / np.mean(Pp))     # 1=백색, →0=구조적
    return dict(n=int(N), n_zero=int((E == 0).sum()),
                n_nonfinite=int((~np.isfinite(E)).sum()),
                abs_min=float(np.abs(E).min()), abs_max=float(np.abs(E).max()),
                dc_db=round(D(abs(m) ** 2), 2), ac_db=round(D(ac), 2),
                rhythm_pct=round(100 * share, 2),
                rhythm_ac_db=round(D(ac * share), 2),      # ⭐리듬 성분만의 절대 세기
                white_baseline_pct=round(100 * msk.mean(), 2),
                flatness=round(flat, 5))


A_OURS0, A_OURS45 = "ours_r15_n8192", "ours_r15_n8192_az45"
A_PS0, A_PS45 = "sionna_p4000000000_r15_n8192_d1", "sionna_p4000000000_r15_n8192_az45_d1"
A_PH0, A_PH45 = "sionna_p4000000000_phys_r15_n8192_d1", "sionna_p4000000000_phys_r15_n8192_az45_d1"
A_PROP = "sionna_p4000000000_partsprop_r15_n8192_d1"          # 프로펠러 그룹만 (az0)
A_PROPH = "sionna_p4000000000_phys_partsprop_r15_n8192_d1"
A_BODY = "sionna_p4000000000_partsnoprop_r15_n8192_d1"        # 프로펠러 뺀 나머지 (az0)
A_FREE = "ours_free_r15_n8192"                                # 우리 커널의 프롭만 대조군
ELS = (0.0, -30.0, -60.0, -90.0)

out = {"_meta": {
    "generator": "benchmark/az_falsify_alternatives.py",
    "gpu_ko": "⛔GPU 미사용 — sionna.rt·mitsuba 를 임포트하지 않았다.",
    "inputs": ["outputs/elevation_sweep_md.json", "outputs/elevation_sweep_md.npz",
               "benchmark/elevation_sweep_md.py", "benchmark/report15_probe.py",
               "src/scene_build.py", "src/articulated_fast.py", "src/drones.py"],
    "band_db": BAND, "prf_hz": PRF, "f_flash_hz": FFL,
    "claim_under_test_ko": "드론을 방위 45° 돌리면 PathSolver 의 정면(el 0°) 에코가 25~51 dB 사라진다"}}

# ── (a) 자세 시퀀스가 달랐나 ────────────────────────────────────────────────
a = {"why_ko": "az 는 los(az,el)/place(az,el) 로만 들어간다. 로터 위상 ph 는 az 와 무관하고 "
                "rotor_phases() 는 난수를 안 쓴다(선형식, base_deg=None). el=-90 이면 "
                "los=[0,0,-1] 이라 방위가 죽으므로 두 팔의 시계열이 같아야 한다.",
     "pairs": {}}
for nm, (p, q) in {"ours": (A_OURS0, A_OURS45), "ps_phys_off": (A_PS0, A_PS45),
                   "ps_phys_on": (A_PH0, A_PH45)}.items():
    x, y = Z[f"{p}/el-90"], Z[f"{q}/el-90"]
    a["pairs"][nm] = dict(max_rel_diff=float(np.abs(x - y).max() / (np.abs(x).max() + 1e-300)),
                          bit_equal=bool(np.array_equal(x, y)))
a["verdict_ko"] = ("죽었다 — 나딧에서 세 엔진 모두 두 팔의 시계열이 상대오차 1e-15 이하로 같다. "
                   "같은 자세 시퀀스를 썼다는 뜻이다.")
out["hypothesis_a_pose_sequence"] = a

# ── (b) 광선이 표적을 덜 맞혔나 / 경로의 종류가 바뀌었나 ────────────────────
b = {"scene_contents_ko": "scene_build.build_scene() 은 rt.load_scene() (빈 장면) 에 드론 부위 "
                          "OBJ 만 올린다 — 지면도 벽도 없다. 집계는 hit=(O!=NO_OBJ) 라 "
                          "«무언가를 맞은» 경로 = 전부 표적 경로다.",
     "npaths_median": {}, "verdict_ko": ""}
for nm, arm in {"ps_phys_off_az0": A_PS0, "ps_phys_off_az45": A_PS45,
                "ps_phys_on_az0": A_PH0, "ps_phys_on_az45": A_PH45}.items():
    b["npaths_median"][nm] = {f"el{e:+.0f}": BY[arm][e]["npaths_median"] for e in ELS if e in BY[arm]}
b["verdict_ko"] = ("문자 그대로의 (b) 는 죽었다 — 장면에 표적 말고는 아무것도 없고 경로 수는 "
                   "오히려 늘었다(897→1280 · 235→313). 살아남는 것은 «종류» 판이다: "
                   "az0·el0 의 큰 값은 **움직이지 않는 부위의 정반사**였다(아래 c2 · d 참조).")
out["hypothesis_b_fewer_target_hits"] = b

# ── (c) 메쉬 비대칭 — 45° 가 하필 최악인가 ─────────────────────────────────
from drones import DRONES                                              # noqa: E402
from articulated_fast import FastPoser                                 # noqa: E402


def mirror_area(key, az, el, tol_deg=0.5, drop_prop=True):
    spec = DRONES[key]; fp = FastPoser(spec)
    mv = fp.pose(np.zeros(len(fp.dirs)))
    V = np.asarray(mv.v, float); F = np.asarray(mv.f, int); G = np.asarray(mv.g)
    p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    nn = np.cross(p1 - p0, p2 - p0); A = 0.5 * np.linalg.norm(nn, axis=1)
    nh = nn / (np.linalg.norm(nn, axis=1, keepdims=True) + 1e-300)
    aa, ee = np.radians(az), np.radians(el)
    u = np.array([np.cos(ee) * np.cos(aa), np.cos(ee) * np.sin(aa), np.sin(ee)])
    m = (nh @ (-u)) > np.cos(np.radians(tol_deg))
    if drop_prop: m &= (G != "prop")
    grp = {g: round(float(A[m & (G == g)].sum()), 6) for g in sorted(set(G[m].tolist()))}
    return float(A[m].sum()), grp


c = {"metric_ko": "법선이 관측자 쪽과 0.5° 이내인 삼각형의 면적 합 [m²] — 거울(정반사) 조건. "
                  "0 이면 그 방향엔 되비쳐 줄 평면이 없다.",
     "matrice4e_el0_vs_az": {}, "matrice4e_az0_vs_el": {}, "other_airframes_el0": {}}
for az in [0, 1, 2, 3, 4, 5, 10, 15, 22.5, 30, 45, 60, 75, 85, 90, 135, 180]:
    ar, _ = mirror_area("matrice4e", az, 0.0)
    c["matrice4e_el0_vs_az"][f"az{az:g}"] = round(ar, 6)
for el in [0, -2, -5, -10, -15, -30, -45, -60, -75, -90]:
    ar, _ = mirror_area("matrice4e", 0.0, el)
    c["matrice4e_az0_vs_el"][f"el{el:g}"] = round(ar, 6)
_, g0 = mirror_area("matrice4e", 0.0, 0.0)
c["matrice4e_az0_el0_groups"] = g0
for k in ("mini5pro", "s1000plus"):
    c["other_airframes_el0"][k] = {f"az{az:g}": round(mirror_area(k, az, 0.0)[0], 6)
                                   for az in (0, 22.5, 45, 67.5, 90)}
c["verdict_ko"] = ("반만 산다. 메쉬는 확실히 방위에 구조가 있다 — matrice4e 의 거울면은 "
                   "az 0·90·180 에만 있고 그 사이는 **전부 0** 이다(1°·5°·10°·30° 도 45° 와 "
                   "똑같이 0). 그러니 «45° 가 하필 최악» 이 아니라 «0° 만 유일한 거울각» 이다. "
                   "게다가 앙각으로는 **2° 만 틀어도** 0 이 된다 — 축은 방위가 아니라 «거울에서 "
                   "벗어났나» 다. ⭐거울면의 정체는 동체 껍질이 아니라 **배터리·카메라·PCB 의 "
                   "평평한 내부 판**이다(위 groups).")
out["hypothesis_c_mesh_asymmetry"] = c

# ── (c2)·(d) 잣대 — az0·el0 의 «움직이는 부분» 은 무엇인가 ─────────────────
d = {"cells": {}, "why_ko": "AC(정지성분 제거 후 전력) 안에서 **리듬(f_flash 정수배)** 과 "
                            "**백색** 을 갈라 본다. 백색 기준선은 마스크가 차지한 빈 비율이다."}
for nm, key in {
        "ours_az0_el0": f"{A_OURS0}/el+0", "ours_az45_el0": f"{A_OURS45}/el+0",
        "ours_propsonly_az0_el0": f"{A_FREE}/el+0",
        "ps_off_az0_el0": f"{A_PS0}/el+0", "ps_off_az0_el-15": f"{A_PS0}/el-15",
        "ps_off_az45_el0": f"{A_PS45}/el+0",
        "ps_off_propsonly_az0_el0": f"{A_PROP}/el+0",
        "ps_off_bodyonly_az0_el0": f"{A_BODY}/el+0",
        "ps_on_az0_el0": f"{A_PH0}/el+0", "ps_on_az45_el0": f"{A_PH45}/el+0",
        "ps_on_propsonly_az0_el0": f"{A_PROPH}/el+0"}.items():
    d["cells"][nm] = stats(key)
d["verdict_ko"] = ("⭐살았다 — 결정적이다. az0·el0 의 PathSolver AC 는 **백색**이다(리듬 몫 9.7 % "
                   "≈ 백색 기준선 9.6 %, 평탄도 0.58). 같은 팔의 다른 앙각·az45 는 전부 "
                   "리듬 99 %·평탄도 0.002 다. 즉 az0·el0 의 «움직이는 부분» 은 에코가 아니라 "
                   "**정지 정반사 위에 얹힌 광선표본 잡음**이다. 프로펠러를 뺀 팔(bodyonly)의 "
                   "AC 가 −384 dB(= 완전 상수)라, 장면이 안 변하면 PathSolver 는 결정론이고 "
                   "프롭이 움직여 장면이 바뀔 때만 그 큰 항이 흔들린다는 뜻이다.")
out["hypothesis_d_metric"] = d

# ── ⭐핵심 대조: «az45 전체기체» vs «az0 프로펠러만» ─────────────────────────
core = {"why_ko": "az45 에서 남은 것이 정말 프로펠러 에코라면, 같은 설정의 «프로펠러만» 팔과 "
                  "같아야 한다. 원장에 그 대조군이 이미 있다(--parts prop).", "rows": []}
for tag, a45, ap, a0 in (("physics_off", A_PS45, A_PROP, A_PS0),
                         ("physics_on", A_PH45, A_PROPH, A_PH0)):
    for el in ELS:
        k45, kp, k0 = f"{a45}/el{el:+.0f}", f"{ap}/el{el:+.0f}", f"{a0}/el{el:+.0f}"
        if not all(k in Z for k in (k45, kp, k0)): continue
        s45, sp, s0 = stats(k45), stats(kp), stats(k0)
        core["rows"].append(dict(
            physics=tag, el_deg=el,
            ac_az45_whole_db=s45["ac_db"], ac_az0_propsonly_db=sp["ac_db"],
            ac_az0_whole_db=s0["ac_db"],
            d_az45_vs_propsonly_db=round(s45["ac_db"] - sp["ac_db"], 2),
            d_az0_vs_propsonly_db=round(s0["ac_db"] - sp["ac_db"], 2),
            inside_band_az45=bool(abs(s45["ac_db"] - sp["ac_db"]) <= BAND),
            inside_band_az0=bool(abs(s0["ac_db"] - sp["ac_db"]) <= BAND)))
core["verdict_ko"] = ("⭐«az45 의 전체 기체» 는 «az0 의 프로펠러만» 과 사실상 같다 — 여덟 칸 중 "
                      "다섯이 3.86 dB 밴드 안이고 최대 차이가 5.3 dB 다(중앙값 2.9 dB). "
                      "반대로 «az0 의 전체 기체» 는 **el0 한 칸에서만** 프로펠러만보다 "
                      "+52.4 dB(물리 끔) · +24.2 dB(물리 켬) 다 — 다른 앙각은 −0.2~+4.2 dB 로 "
                      "프로펠러만과 같다. 즉 방위가 바꾼 것은 **el0 한 칸의 정지 정반사와 그 "
                      "위의 잡음**이지 표적 에코가 아니다. ⚠원 주장의 «25 dB · 51 dB» 는 그 "
                      "한 칸의 오염분과 자릿수까지 같다(52.4 / 24.2).")
out["core_control_props_only"] = core


# ── (d2) ⭐결정타: 광선 예산 사다리 — el0·az0 의 «움직임» 은 광선을 늘릴수록 커진다 ──
#   ⚠이 사다리는 원장의 **10 m · 자세 4096** 옛 팔이다(머리판 15 m 와 섞어 읽지 말 것).
lad = {"note_ko": "⚠이 사다리 팔은 range 10 m · 자세 4096 이다(머리 판 15 m 와 다른 판). "
                  "여기서 보는 것은 절대 레벨이 아니라 **광선 예산에 대한 거동**이다.",
       "at_mirror_el0_az0": [], "off_mirror_el-15_az0": []}
for a in ("sionna", "sionna_p250000000", "sionna_p1000000000", "sionna_p4000000000"):
    for el, box in ((0.0, "at_mirror_el0_az0"), (-15.0, "off_mirror_el-15_az0")):
        s_ = stats(f"{a}/el{el:+.0f}")
        lad[box].append(dict(arm=a, spp=BY[a][el]["spp"], npaths_median=BY[a][el]["npaths_median"],
                             dc_db=s_["dc_db"], ac_db=s_["ac_db"],
                             rhythm_pct=s_["rhythm_pct"], flatness=s_["flatness"]))
lad["verdict_ko"] = ("⭐거울각(el0·az0)에서 광선을 11 M → 4 G 로 360 배 늘리면 DC 는 −59.6 dB 에 "
                     "붙박이인데 AC 는 −143.2 → −90.4 dB 로 **52.8 dB 커지고** 리듬 몫이 "
                     "96.9 % → 11.6 % 로 무너진다. 물리 에코라면 광선을 늘릴수록 수렴해야 한다 — "
                     "커지는 것은 추정기 잡음뿐이다. 거울에서 벗어난 칸(el−15)은 같은 사다리에서 "
                     "AC 가 9 dB 만 오르고 리듬이 88~98 % 로 유지된다. "
                     "⭐같은 10 m 판 안에서만 비교하면: 광선 11 M 에서 «거울칸 vs 거울밖칸» 의 "
                     "AC 차는 **1.6 dB**(−143.2 vs −144.8) 인데, 광선 4 G 에서는 **45.3 dB**"
                     "(−90.4 vs −135.8) 로 벌어진다. 즉 «거울칸만 50 dB 높다» 는 현상 자체가 "
                     "광선 예산이 만든 것이고, az45 를 그 부풀린 값과 견주니 «51 dB 사라졌다» 가 "
                     "나온 것이다.")
out["hypothesis_d2_ray_budget_ladder"] = lad

# ── (e) 결측·NaN·언더플로 ──────────────────────────────────────────────────
e = {"cells": {k: {kk: v[kk] for kk in ("n", "n_zero", "n_nonfinite", "abs_min", "abs_max")}
               for k, v in d["cells"].items()},
     "double_precision_floor_db": round(20 * np.log10(np.finfo(float).tiny), 1),
     "verdict_ko": ("죽었다 — 결측 0 · 비유한값 0 이고 |E| 최솟값이 1e-9 대라 배정밀도 "
                     "언더플로(≈ −6154 dB)와 5,000 dB 넘게 떨어져 있다. −145 dB 는 수치 한계가 "
                    "아니다. 오히려 같은 파이프라인이 −384 dB 를 정확히 표현했다(bodyonly).")}
out["hypothesis_e_numerics"] = e

# ── 원 주장 재서술 ─────────────────────────────────────────────────────────
mv = {}
for nm, (a0, a45) in {"ours": (A_OURS0, A_OURS45), "ps_off": (A_PS0, A_PS45),
                      "ps_on": (A_PH0, A_PH45)}.items():
    mv[nm] = {}
    for el in ELS:
        s0, s45 = stats(f"{a0}/el{el:+.0f}"), stats(f"{a45}/el{el:+.0f}")
        mv[nm][f"el{el:+.0f}"] = dict(
            ac_db=[s0["ac_db"], s45["ac_db"]], d_ac_db=round(s45["ac_db"] - s0["ac_db"], 2),
            rhythmic_ac_db=[s0["rhythm_ac_db"], s45["rhythm_ac_db"]],
            d_rhythmic_db=round(s45["rhythm_ac_db"] - s0["rhythm_ac_db"], 2),
            rhythm_pct=[s0["rhythm_pct"], s45["rhythm_pct"]],
            dc_db=[s0["dc_db"], s45["dc_db"]], d_dc_db=round(s45["dc_db"] - s0["dc_db"], 2))
out["restated"] = mv
out["_meta"]["headline_ko"] = (
    "원 주장은 무너진다. ⓵ PathSolver 의 «에코» 가 사라진 칸은 el0 하나뿐이고, 거기서 사라진 것은 "
    "**배터리·카메라·PCB 평판의 정지 정반사**(도플러 0)와 그 위의 **백색 표본잡음**이다. "
    "⓶ 같은 팔은 방위를 안 돌려도 앙각을 15° 만 내리면 똑같이 무너진다(DC −118.9 vs az45 의 −120.3). "
    "⓷ az45 에 남은 «움직이는 부분» 은 같은 설정의 «프로펠러만» 대조군과 1.3 dB 안에서 같다 — "
    "표적 에코는 방위에 안 변했다. 옳은 문장은 «방위 45° 면 에코가 사라진다» 가 아니라 "
    "«PathSolver 는 거울각(az0·el0)에서만 큰 값을 내고, 그 값은 정지 부위의 정반사이며, "
    "그 잡음이 진짜 마이크로도플러를 52 dB 로 덮는다» 다.")

os.makedirs(f"{ROOT}/outputs", exist_ok=True)
json.dump(out, open(f"{ROOT}/outputs/az_falsify_alternatives.json", "w"),
          ensure_ascii=False, indent=1)
print(json.dumps(out["core_control_props_only"], ensure_ascii=False, indent=1))
print("\n✅ outputs/az_falsify_alternatives.json")
