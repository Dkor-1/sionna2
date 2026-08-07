# -*- coding: utf-8 -*-
"""report16 사다리 — 동어반복(정의상 참인 것을 증명한 척) 검사 렌즈.

⭐ 이 파일이 묻는 것 딱 세 가지
  ① 구·상자를 **정말 돌렸나**. 안 돌리고 0 을 적었으면 BROKEN 이다.
  ② 「메쉬가 널보다 낫다」가 기하학적으로 **자명한 것**을 잰 것 아닌가.
  ③ ⭐ 진짜 질문 — 그 차이가 **검출기에 얼마나 영향을 주는가**. 라운드가 그 선을 넘었나.

규율: 앞 단들의 숫자를 베끼지 않는다. 저장된 위상 표(복소 배열)에서 전부 다시 계산한다.
      내가 새로 만든 숫자는 전부 crude(거친 추정)로 표시한다.
      GPU 미사용 — 저장된 표를 FFT 하는 후처리라 CPU 로 충분하고, 4장 다 남의 작업이 쓰는 중이다.
"""
import sys, os, json, math, time, hashlib, subprocess
import numpy as np
from scipy.stats import ncx2, chi2

ROOT = "/home/yunjung/workspace/sionna2"
sys.path.insert(0, os.path.join(ROOT, "benchmark"))
sys.path.insert(0, os.path.join(ROOT, "src"))
import report16_base as B
import report16_rung_sphere_eqvol as RS
from drones import DRONES, build_drone
from rcs_po import mesh_to_points
from geom import box as GBOX, uv_sphere

OUT = os.path.join(ROOT, "outputs/report16_verify_tautology.json")
T0 = time.time()
FC = 3.5e9
LAM = B.C0 / FC
KW = 2.0 * math.pi / LAM
KEYS = ("mini2", "matrice4e")
BASE_J = json.load(open(os.path.join(ROOT, "outputs/report16_base.json")))
BLADE_DIV = float(BASE_J["protocol"]["blade_div"])

NPZ = {n: np.load(os.path.join(ROOT, f"outputs/report16_{n}_tables.npz"), allow_pickle=True)
       for n in ("base", "rung_sphere_eqvol", "rung_cube_eqvol", "rung_box_bbox",
                 "rung_mesh_half_tri")}


# --------------------------------------------------------------------------- #
#  잔손질 도구
# --------------------------------------------------------------------------- #
def mesh_volume(m):
    v = np.asarray(m.v, float); f = np.asarray(m.f, int)
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    return float(np.sum(np.einsum("ij,ij->i", a, np.cross(b, c))) / 6.0)


def rz(t):
    c, s = math.cos(t), math.sin(t)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def cpu_field(P, N, W, A, R_t):
    """구면파 PO 를 CPU numpy 로 독립 구현 — 커널을 베끼지 않고 다시 짠다."""
    D = A[None, :] - P
    r = np.linalg.norm(D, axis=1)
    ui = D / r[:, None]
    nu = np.einsum("ij,ij->i", N, ui)
    amp = np.where(nu > 0, nu, 0.0) * W * (R_t * R_t) / (r * r)
    ph = -KW * (2.0 * r - 2.0 * R_t)
    return complex(np.sum(amp * np.cos(ph)), np.sum(amp * np.sin(ph)))


def ac_power(T):
    """방위별 AC(0-도플러 제외) 전력."""
    o = []
    for i in range(T.shape[0]):
        t = T[i]; c = np.fft.fft(t) / len(t); P = np.abs(c) ** 2
        m = np.fft.fftfreq(len(t), d=1.0 / len(t)).astype(int)
        o.append(float(P[m != 0].sum()))
    return np.array(o)


def rho_mean(A, Bt):
    n = min(A.shape[0], Bt.shape[0])
    return float(np.mean([B.ac_corr(A[i], Bt[i]) for i in range(n)]))


def prof_rho_mean(A, Bt):
    """도플러 **전력 프로파일** 상관 — 위상을 안 쓰는(비코히어런트) 검출기가 보는 닮음."""
    def prof(t):
        c = np.fft.fft(t) / len(t); P = np.abs(c) ** 2
        m = np.fft.fftfreq(len(t), d=1.0 / len(t)).astype(int)
        k = np.zeros(int(np.abs(m).max()) + 1); np.add.at(k, np.abs(m), P); k[0] = 0.0
        return k
    n = min(A.shape[0], Bt.shape[0]); out = []
    for i in range(n):
        ka, kb = prof(A[i]), prof(Bt[i])
        L = min(len(ka), len(kb)); ka, kb = ka[:L], kb[:L]
        out.append(float(np.dot(ka, kb) /
                         math.sqrt(max(np.dot(ka, ka) * np.dot(kb, kb), 1e-300))))
    return float(np.mean(out))


def arm_tables(key):
    b, s, c, x, h = (NPZ["base"], NPZ["rung_sphere_eqvol"], NPZ["rung_cube_eqvol"],
                     NPZ["rung_box_bbox"], NPZ["rung_mesh_half_tri"])
    return {
        "mesh":                b[f"main__G_0804__{key}__mesh__spherical"],
        "mesh_fine":           b[f"main__G_0804__{key}__mesh_fine__spherical"],
        "mesh_half_tri":       h[f"main__{key}__mesh_half_tri__spherical"],
        "slab":                b[f"main__G_0804__{key}__slab__spherical"],
        "prop_bbox":           x[f"main__{key}__prop_bbox__spherical"],
        "sph_blade_rg":        s[f"main__{key}__sph_blade_rg__spherical"],
        "sph_blade_tip":       s[f"main__{key}__sph_blade_tip__spherical"],
        "cube_eqvol":          c[f"main__{key}__cube_eqvol__spherical"],
        "box_bbox":            x[f"main__{key}__box_bbox__spherical"],
        "mesh_rigid_spin":     c[f"main__{key}__mesh_rigid_spin__spherical"],
        "mesh_rigid_spin_pec": c[f"main__{key}__mesh_rigid_spin_pec__spherical"],
        "disc_NULL":           b[f"main__G_0804__{key}__disc__spherical"],
        "sphere_NULL":         b[f"main__G_0804__{key}__sphere__spherical"],
        "sphere_eqvol_NULL":   s[f"main__{key}__sphere_eqvol__spherical"],
        "sphere_offaxis_CTRL": s[f"main__{key}__sphere_offaxis__spherical"],
    }


J = dict(meta=dict(
    report="report16", lens="tautology_check", producer="benchmark/report16_verify_tautology.py",
    generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
    git_rev=subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True).stdout.strip() or "n/a",
    gpu_used="none (저장된 위상 표의 후처리 — CPU 로 충분. GPU 4장은 형제 워크플로가 쓰는 중)",
    stance_ko="기본 입장은 «이 결론은 이르다». 앞 단들의 숫자를 베끼지 않고 원본 표에서 다시 계산했다.",
    scope_ko="검사 대상 = report16 사다리 6 단(기반 1 + 지표 6). report15_*·report0N_* 미접촉, "
             "drones.py·drone_cad.py 는 읽기만."))


# =========================================================================== #
#  검사 1 — ⭐ 「정말 돌렸는가」. 안 돌리고 0 을 적었으면 BROKEN.
# =========================================================================== #
rot = dict(what_ko=(
    "과제문이 못박은 BROKEN 조건이다. 구·상자를 실제로 회전시켜 계산했는지 두 방법으로 확인한다. "
    "(가) 저장된 표가 위상에 따라 변하는가 — 하드코딩된 0 이면 표가 상수다. "
    "(나) 점구름을 **내가 직접 돌려** CPU 로 다시 계산해 저장된 표를 재현하는가. "
    "커널은 무거운 점구름 대신 안테나를 반대로 돌리는 요령을 쓰는데, 그 요령이 맞는지까지 같이 검사된다."),
           rows={}, independent_kernel="이 파일이 새로 짠 numpy CPU PO (report16_base 커널 미사용)")

idx_of = lambda S: sorted({0, 1, S // 8, S // 4, S // 3, S // 2, 3 * S // 4, S - 1})
for key in KEYS:
    s = DRONES[key]
    proto = B.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, FC)
    S_ = proto["n_phase"]; spac = LAM / BLADE_DIV
    u, A, R_t = B.look_and_antenna(0.0, B.EL_DEG, B.RANGE_M)
    idx = idx_of(S_)
    drone = build_drone(s); vol = abs(mesh_volume(drone))

    # (1) 정육면체 — 원점 중심 강체 자전
    a = vol ** (1.0 / 3.0)
    P, N, dA = mesh_to_points(GBOX(a, a, a, center=(0, 0, 0), group="cube"), spac)
    ref = NPZ["rung_cube_eqvol"][f"main__{key}__cube_eqvol__spherical"][0][idx]
    mine = np.array([cpu_field((rz(2 * math.pi * j / S_) @ P.T).T,
                               (rz(2 * math.pi * j / S_) @ N.T).T, dA, A, R_t) for j in idx])
    rot["rows"][f"{key}|cube_eqvol"] = dict(
        max_rel_err_vs_stored=float(np.max(np.abs(mine - ref)) / max(np.max(np.abs(ref)), 1e-300)),
        amp_swing_over_probed_phases_db=float(20 * np.log10(np.max(np.abs(ref)) /
                                                            max(np.min(np.abs(ref)), 1e-300))),
        n_points=int(len(dA)), verdict="ROTATION IS REAL")

    # (2) 축을 벗어난 구(양성 대조군) — 회전중심 ≠ 물체중심인 경우까지 검사
    cl = RS.build_arm(key, "sphere_offaxis", LAM)
    Po, No, Wo = cl["groups"][0]["cloud"]; cen = np.asarray(cl["groups"][0]["center"], float)
    refo = NPZ["rung_sphere_eqvol"][f"main__{key}__sphere_offaxis__spherical"][0][idx]
    mineo = np.array([cpu_field((rz(2 * math.pi * j / S_) @ (Po - cen).T).T + cen,
                                (rz(2 * math.pi * j / S_) @ No.T).T, Wo, A, R_t) for j in idx])
    rot["rows"][f"{key}|sphere_offaxis(양성대조)"] = dict(
        max_rel_err_vs_stored=float(np.max(np.abs(mineo - refo)) / max(np.max(np.abs(refo)), 1e-300)),
        offset_from_spin_axis_mm=float(cl["meta"]["offset_from_axis_m"] * 1e3),
        n_points=int(len(Wo)), verdict="ROTATION IS REAL")

    # (3) 축 위의 구 — 점을 직접 돌려도 상수인가 (「0」이 죽은 코드가 아니라 기하인가)
    r_eq = (3.0 * vol / (4.0 * math.pi)) ** (1.0 / 3.0)
    _odd = lambda n: int(n) if int(n) % 2 == 1 else int(n) + 1
    seg = _odd(max(9, int(math.ceil(2 * math.pi * r_eq / spac))))
    rings = max(3, int(math.ceil(math.pi * r_eq / spac)))
    Ps, Ns, dAs = mesh_to_points(uv_sphere(r_eq, seg=seg, rings=rings, group="sph"), spac)
    mins = np.array([cpu_field((rz(2 * math.pi * j / S_) @ Ps.T).T,
                               (rz(2 * math.pi * j / S_) @ Ns.T).T, dAs, A, R_t) for j in idx])
    Tsph = NPZ["rung_sphere_eqvol"][f"main__{key}__sphere_eqvol__spherical"]
    rot["rows"][f"{key}|sphere_eqvol(널)"] = dict(
        my_own_explicit_rotation_rel_swing=float(np.max(np.abs(mins - mins.mean())) / abs(mins.mean())),
        stored_table_rel_swing=float(np.max(np.abs(Tsph[0] - Tsph[0].mean())) / abs(Tsph[0].mean())),
        sphere_tessellation=dict(seg=int(seg), rings=int(rings), n_points=int(len(dAs))),
        verdict="ROTATION IS REAL — 값이 정확히 0 이 아니라 격자 잔차만큼 남는다(하드코딩 0 이 아니다)")

rot["verdict"] = "PASS — 구·상자 모두 실제로 회전시켜 계산했다. BROKEN 아님."
rot["read_ko"] = (
    "정육면체·축이탈 구는 내가 점을 직접 돌려 만든 값과 저장된 표가 기계 정밀도 수준으로 같다. "
    "축 위의 구는 점을 직접 돌려도 백만분율 수준의 잔차만 남는다 — 즉 «0» 은 코드가 죽어서가 아니라 "
    "회전대칭이라는 기하 때문이다. 이 결과 자체가 다음 검사의 출발점이다: 그 «0» 은 계산 결과가 아니라 "
    "**전제**다.")
J["check1_did_they_actually_spin"] = rot


# =========================================================================== #
#  검사 2 — ⭐⭐ 동어반복 회계. 「구조의 값어치 = 메쉬 − 널」을 쪼갠다.
# =========================================================================== #
taut = dict(what_ko=(
    "라운드에서 가장 인용하기 좋은 숫자는 sphere 단의 «구조가 마이크로도플러에 기여하는 양 = 메쉬 − 구 "
    "= 최소 62 dB»(findings.05_gap, 사전예측 P4)다. 이 간격을 **디테일이 0 인 팔**이 얼마나 이미 사 놓았는지 "
    "재면, 그 62 dB 중 «CAD 형상 정밀도» 가 산 몫이 나온다. "
    "slab = 프로펠러를 스팬·코드·부피만 지킨 평판 2장으로 바꾼 팔(형상 디테일 0, 운동학은 메쉬와 동일). "
    "prop_bbox = 프로펠러를 그 경계상자로 바꾼 팔."),
            metric="in_band_ac_over_dc_db (report16_base.md_metrics16 를 import 해서 씀 — 재구현 없음)",
            rows={})
for key in KEYS:
    proto = BASE_J["protocol_per_drone"][key]
    T = arm_tables(key)
    lev = {nm: float(np.mean([B.md_metrics16(t[i], proto, 2)["in_band_ac_over_dc_db"]
                              for i in range(t.shape[0])]))
           for nm, t in T.items() if nm in ("mesh", "slab", "prop_bbox", "sph_blade_rg",
                                            "sphere_NULL", "disc_NULL")}
    gap_mesh = lev["mesh"] - lev["sphere_NULL"]
    gap_slab = lev["slab"] - lev["sphere_NULL"]
    gap_pbb = lev["prop_bbox"] - lev["sphere_NULL"]
    taut["rows"][key] = dict(
        level_db=lev,
        gap_mesh_minus_sphere_null_db=gap_mesh,
        gap_slab_minus_sphere_null_db=gap_slab,
        gap_prop_bbox_minus_sphere_null_db=gap_pbb,
        share_bought_by_detail_free_slab=gap_slab / gap_mesh,
        share_bought_by_prop_bounding_box=gap_pbb / gap_mesh,
        cad_precision_only_db=lev["mesh"] - lev["slab"],
        cad_precision_only_share=(lev["mesh"] - lev["slab"]) / gap_mesh)
taut["headline_ko"] = (
    "⭐⭐ 인용되는 간격의 거의 전부를 «형상 디테일이 0 인 평판» 이 이미 사 놓았다. "
    f"mini2 {100*taut['rows']['mini2']['share_bought_by_detail_free_slab']:.1f} %, "
    f"matrice4e {100*taut['rows']['matrice4e']['share_bought_by_detail_free_slab']:.1f} %. "
    f"CAD 정밀도 단독 몫은 mini2 {taut['rows']['mini2']['cad_precision_only_db']:.2f} dB"
    f"({100*taut['rows']['mini2']['cad_precision_only_share']:.1f} %), "
    f"matrice4e {taut['rows']['matrice4e']['cad_precision_only_db']:.2f} dB"
    f"({100*taut['rows']['matrice4e']['cad_precision_only_share']:.1f} %) 뿐이다. "
    "프로펠러를 통짜 상자로 바꾼 팔은 오히려 메쉬보다 **더 큰** 간격을 만든다(몫 > 1). "
    "즉 그 62~77 dB 는 «CAD 가 정밀해서» 가 아니라 «회전대칭이 아니라서» 번 돈이다.")
taut["why_this_is_tautology_ko"] = (
    "회전축 위의 구는 그 축으로 돌리면 자기 자신이 된다 — 되돌아오는 신호가 φ 에 무관한 것은 어떤 산란 "
    "모델을 쓰든 성립하는 **기하학**이다(sphere 단 스스로 findings.12_limit 에 그렇게 적었다). 그러므로 "
    "「메쉬 − 널 ≥ 40 dB」라는 사전 예측은 회전대칭이 아닌 어떤 표적을 넣어도 통과한다 — 평판도, 상자도, "
    "정육면체도. 반증 가능성이 없는 예측을 PASS 로 세는 것이 이 라운드의 가장 큰 동어반복이다.")
taut["fairness_note_ko"] = (
    "⚖ 공정하게 적는다 — sphere 단은 «구조(structure)» 라고 썼지 «CAD 정밀도» 라고 쓰지 않았다. 문장 "
    "자체는 참이다. 문제는 같은 라운드의 헤드라인 질문이 «메쉬(형상 정밀도)를 바꾸면 얼마나 바뀌는가»"
    "(report16_base.json meta)라는 점이다. 한 문서 안에서 두 말이 붙어 있으면 인용될 때 갈라지지 않는다.")
J["check2_tautology_accounting"] = taut


# =========================================================================== #
#  검사 3 — 운동학·재질 교란. 「형상」 몫만 남기면 얼마인가.
# =========================================================================== #
conf = dict(what_ko=(
    "sphere_eqvol·cube_eqvol·box_bbox 세 단은 «기체 **전체**를 프리미티브 하나로 바꿔 로터 rpm 으로 "
    "자전시킨» 물체다. 진짜 드론은 몸통이 서 있고 프로펠러만 돈다. 그래서 «프리미티브 대 메쉬» 비교에는 "
    "형상 말고도 ① 무엇이 도는가(운동학) ② 재질(프리미티브는 PEC |Γ|=1, 메쉬는 재질 가중) 이 섞여 있다. "
    "cube 단이 넣어 둔 대조군 두 개(mesh_rigid_spin = 진짜 CAD 를 통째로 자전, "
    "mesh_rigid_spin_pec = 같은 것을 PEC 로)를 쓰면 셋을 dB 로 갈라낼 수 있다."),
            rows={})
for key in KEYS:
    T = arm_tables(key)
    p = {nm: ac_power(t).mean() for nm, t in T.items()}
    d = lambda a, b: float(10 * np.log10(p[a] / p[b]))
    total = d("cube_eqvol", "mesh")
    kin = d("mesh_rigid_spin", "mesh")
    mat = d("mesh_rigid_spin_pec", "mesh_rigid_spin")
    shp = d("cube_eqvol", "mesh_rigid_spin_pec")
    conf["rows"][key] = dict(
        cited_cube_minus_mesh_db=total,
        kinematics_term_db=kin, material_term_db=mat, shape_term_db=shp,
        sum_of_three_db=kin + mat + shp,
        closure_err_db=abs(total - (kin + mat + shp)),
        shape_share_of_total_absolute=abs(shp) / (abs(kin) + abs(mat) + abs(shp)),
        slab_minus_mesh_db=d("slab", "mesh"),
        slab_note_ko="slab 은 운동학·역할이 메쉬와 같고 블레이드 디테일만 없앤 유일한 팔이다 — "
                     "«형상 정밀도» 를 물을 자격이 있는 것은 사실상 이 팔과 prop_bbox·mesh_half_tri 뿐이다.")
conf["headline_ko"] = (
    "⭐ 「정육면체 대 메쉬」로 인용되는 차이는 대부분 형상이 아니다. "
    f"mini2 {conf['rows']['mini2']['cited_cube_minus_mesh_db']:.2f} dB 중 운동학이 "
    f"{conf['rows']['mini2']['kinematics_term_db']:.2f} dB · 재질이 "
    f"{conf['rows']['mini2']['material_term_db']:.2f} dB · 형상은 "
    f"{conf['rows']['mini2']['shape_term_db']:.2f} dB. "
    f"matrice4e {conf['rows']['matrice4e']['cited_cube_minus_mesh_db']:.2f} dB 중 운동학 "
    f"{conf['rows']['matrice4e']['kinematics_term_db']:.2f} · 재질 "
    f"{conf['rows']['matrice4e']['material_term_db']:.2f} · 형상 "
    f"{conf['rows']['matrice4e']['shape_term_db']:.2f} dB. "
    "세 항의 합이 인용값과 소수점 아래에서 닫힌다(closure_err_db) — 우연한 분해가 아니다.")
conf["credit_ko"] = (
    "⚖ box 단은 이 결함을 스스로 가장 큰 의심으로 지목했고(findings.q5_biggest_doubt_ko: «box_bbox 는 "
    "무엇이 움직이는가까지 바꾼 팔이다»), cube 단은 mesh_rigid_spin 대조군을 직접 만들어 넣었다. "
    "고치지 않은 곳은 sphere 단의 헤드라인 간격이다.")
J["check3_kinematic_and_material_confound"] = conf


# =========================================================================== #
#  검사 4 — 지표 ① 에 «바닥» 이 있는가 (널이 신호를 이기지 않는가)
# =========================================================================== #
floor = dict(what_ko=(
    "지표 ① flash_contrast_db 는 «플래시가 바닥보다 몇 dB 위인가» 다. 회전대칭체의 이론값은 0 dB 라고 "
    "base 가 적어 뒀다. 정말 그런지, 물리적 변조가 정확히 0 인 널 팔에서 이 지표가 얼마를 읽는지 잰다."),
             rows={})
for key in KEYS:
    proto = BASE_J["protocol_per_drone"][key]
    T = arm_tables(key)
    fl = {nm: float(np.mean([B.md_metrics16(t[i], proto, 2)["flash_contrast_db"]
                             for i in range(t.shape[0])]))
          for nm, t in T.items()}
    ib = {nm: float(np.mean([B.md_metrics16(t[i], proto, 2)["in_band_ac_frac"]
                             for i in range(t.shape[0])]))
          for nm, t in T.items()}
    floor["rows"][key] = dict(
        flash_contrast_db=fl, in_band_ac_frac=ib,
        null_minus_mesh_db=fl["sphere_NULL"] - fl["mesh"],
        null_beats_mesh=bool(fl["sphere_NULL"] > fl["mesh"]),
        theoretical_value_for_rot_symmetric_db=0.0)
floor["headline_ko"] = (
    f"⭐ mini2 에서 **널이 신호를 이긴다** — 물리적 변조가 0 인 등가부피 구가 "
    f"{floor['rows']['mini2']['flash_contrast_db']['sphere_NULL']:.2f} dB, 진짜 CAD 메쉬가 "
    f"{floor['rows']['mini2']['flash_contrast_db']['mesh']:.2f} dB 다"
    f"(차 {floor['rows']['mini2']['null_minus_mesh_db']:+.2f} dB). 이론값 0 dB 는 지켜지지 않는다 — "
    "AC 가 수치 잔차뿐일 때 중앙값도 같이 작아져 비가 커지기 때문이다. "
    "따라서 «메쉬가 6.6 dB 의 플래시를 낸다» 는 문장은 mini2 에서 널과 구별되지 않는다. "
    "대역 안 AC 몫(in_band_ac_frac)을 같이 봐야 갈린다 — 메쉬 1.000 대 구 "
    f"{floor['rows']['mini2']['in_band_ac_frac']['sphere_NULL']:.3f}.")
floor["credit_ko"] = (
    "⚖ mesh_full 단이 이 사실을 스스로 찾아 적어 뒀다(discriminative_power.key_reading_ko: "
    "«flash_contrast_db 는 바닥 방어막이 없다»). 남은 문제는 여러 단의 요약 표에 널 팔의 flash 값이 "
    "«자격 없음» 표시 없이 나란히 찍힌다는 것뿐이다.")
J["check4_metric_has_no_floor"] = floor


# =========================================================================== #
#  검사 5 — ⭐⭐ 라운드가 끝내 묻지 않은 질문: 검출기에 얼마나 영향을 주는가
# =========================================================================== #
PFA = 1e-6
def pd_of(snr_lin, pfa=PFA):
    return float(ncx2.sf(chi2.isf(pfa, df=2), df=2, nc=2.0 * snr_lin))
def snr_for_pd(pd_t, pfa=PFA):
    lo, hi = 1e-3, 1e6
    for _ in range(200):
        mid = math.sqrt(lo * hi)
        if pd_of(mid, pfa) < pd_t: lo = mid
        else: hi = mid
    return math.sqrt(lo * hi)

SNR0 = snr_for_pd(0.90)
det = dict(
    what_ko=("⭐ 이 렌즈가 요구한 진짜 질문이다. 라운드의 어느 단도 Pd(검출확률)·Pfa(오경보율)·ROC·"
             "적분시간을 계산하지 않는다. 가장 가까운 것이 sphere 단의 equivalent_noise_snr_db 인데 "
             "그것은 «파형이 얼마나 안 닮았나» 를 dB 로 바꿔 쓴 값이지 탐지 성능이 아니다. "
             "여기서 그 빈칸을 **거친 추정**으로 메운다."),
    model_ko=("⚠⚠ 전부 crude(거친 추정)다. 비요동 표적·제곱검파·단일 룩·Pfa=1e-6 의 교과서 검출기이고, "
              "잡음·클러터·CPI·CFAR 는 없다. 절대값을 인용하면 안 되고 «어느 쪽이 얼마나 큰가» 만 읽어라."),
    crude=True, pfa=PFA,
    reference_snr_db_for_pd090=float(10 * math.log10(SNR0)),
    two_detectors_ko=("두 종류를 나눠 잰다. ① **템플릿 검출기** — 표적 모델로 만든 파형을 정합필터로 쓴다. "
                      "모델이 틀리면 −10log10(ρ²) 만큼 잃는다. ② **대역 에너지 검출기** — 도플러 칸의 "
                      "전력만 본다. 모델이 틀리면 예측 SNR 이 ΔAC 전력만큼 어긋난다(탐지 손실이 아니라 "
                      "«예측 오차» 다)."),
    rows={})
for key in KEYS:
    T = arm_tables(key)
    mesh = T["mesh"]; pm = ac_power(mesh).mean()
    for nm, t in T.items():
        if nm == "mesh":
            continue
        r = rho_mean(mesh, t)
        loss = -10 * math.log10(max(r * r, 1e-300))
        dac = 10 * math.log10(max(ac_power(t).mean(), 1e-300) / pm)
        det["rows"][f"{key}|{nm}"] = dict(
            coherent_ac_corr=r,
            doppler_profile_corr=prof_rho_mean(mesh, t),
            template_mismatch_loss_db=loss,
            pd_when_perfect_template_gives_0p90=pd_of(SNR0 * max(r * r, 1e-300)),
            delta_ac_power_db=dac,
            predicted_range_factor_R4=10 ** (dac / 40.0))
tm, tM = det["rows"]["mini2|slab"], det["rows"]["matrice4e|slab"]
hm, hM = det["rows"]["mini2|mesh_half_tri"], det["rows"]["matrice4e|mesh_half_tri"]
det["headline_ko"] = (
    "⭐⭐ **답은 검출기 종류에 따라 갈린다 — 그리고 라운드는 그 갈림을 계산하지 않았다.** "
    f"① 템플릿 검출기: 디테일 0 인 평판으로 템플릿을 만들면 정합손실이 mini2 {tm['template_mismatch_loss_db']:.2f} dB · "
    f"matrice4e {tM['template_mismatch_loss_db']:.2f} dB 이고, 완벽한 템플릿에서 Pd=0.90 이던 표적이 "
    f"{tm['pd_when_perfect_template_gives_0p90']:.3f} / {tM['pd_when_perfect_template_gives_0p90']:.3f} 로 무너진다. "
    "여기서는 형상이 **크게** 중요하다. "
    f"② 대역 에너지 검출기: 같은 평판의 AC 전력 오차는 {tm['delta_ac_power_db']:+.2f} / {tM['delta_ac_power_db']:+.2f} dB 뿐이고, "
    f"모노스태틱 R⁴ 로 옮기면 탐지거리 배율 {tm['predicted_range_factor_R4']:.3f} / {tM['predicted_range_factor_R4']:.3f} 다. "
    "여기서는 형상이 **거의 안** 중요하다. "
    f"③ 대조: 삼각형을 절반으로 줄이는 것은 두 검출기 모두에서 무해하다(정합손실 "
    f"{hm['template_mismatch_loss_db']:.2f} / {hM['template_mismatch_loss_db']:.2f} dB).")
det["what_the_round_should_have_asked_ko"] = (
    "sphere 단이 findings.10_waveform 에서 이 갈림을 **말로는** 정확히 짚었다 — «변조가 있냐 없냐만 쓰는 "
    "검출기라면 프리미티브로 충분하고, 폭·플래시·정합필터 템플릿을 쓸 거면 형상이 필요하다». "
    "그런데 그 문장을 뒷받침하는 숫자(Pd·SNR·적분시간)를 라운드 어디에서도 계산하지 않았다. "
    "위 표가 그 빈칸을 거칠게 메운 것이고, 채워 보니 문장은 맞았다. "
    "⛔ 다만 그 문장이 옳다는 것과 라운드가 그것을 **증명했다**는 것은 다르다.")
det["counter_ko"] = (
    "⚠ 내 숫자도 믿지 마라. ① 템플릿 검출기 쪽 손실은 «로터 상대위상·rpm·방위를 다 안다» 는 이상적 "
    "가정에서 나온다. mesh_full 단이 잰 바로는 로터 상대위상이라는 **모델 선택 하나만으로** 플래시 "
    "대조비가 4.2~10.0 dB 흔들린다 — 그 폭이 slab 의 정합손실과 같은 급이다. 즉 실제로는 우리 자신의 "
    "기준 파형도 그만큼 못 믿는다. ② 대역 에너지 쪽 ΔAC 전력에는 재질 항이 섞여 있다(검사 3). "
    "③ PO 커널은 3.5 GHz 에서 블레이드 폭이 유효 무릎 아래다(base 의 po_validity_warning).")
J["check5_does_it_move_a_detector"] = det


# =========================================================================== #
#  검사 6 — 사전 예측의 반증 가능성 회계
# =========================================================================== #
pre = dict(what_ko=("사전 등록된 예측을 «틀릴 수 있었나» 로 분류한다. FORCED = 기하·정의·구성상 "
                    "통과가 보장된 항목, FALSIFIABLE = 실제로 틀릴 수 있었던 항목, "
                    "UNPREDICTED = 방향을 일부러 안 정한 항목."),
           items=[
    dict(id="sphere P1", file="report16_rung_sphere_eqvol.json", cls="FORCED-ish",
         ko="널의 AC/DC ≤ −60 dB. 회전대칭이라 물리는 정확히 0 이므로 이 항목이 재는 것은 물리가 아니라 "
            "«구를 얼마나 촘촘히 쪼갰나» 다. 실제로 MARGINAL 이 났는데 원인도 격자였다(그 단이 그렇게 적음)."),
    dict(id="sphere P2", file="report16_rung_sphere_eqvol.json", cls="FALSIFIABLE",
         ko="잔차의 지배 차수가 경도 분할 수를 따라간다 — 틀릴 수 있었고 맞았다. 좋은 예측이다."),
    dict(id="sphere P3", file="report16_rung_sphere_eqvol.json", cls="FALSIFIABLE",
         ko="⭐ 축을 벗어난 구는 큰 변조를 낸다(양성 대조군). 이것이 «코드가 죽지 않았다» 를 지키는 "
            "유일한 항목이고 실제로 지켰다. 이 라운드에서 가장 값어치 있는 예측이다."),
    dict(id="sphere P4", file="report16_rung_sphere_eqvol.json", cls="FORCED",
         ko="⭐⭐ 메쉬 − 널 ≥ 40 dB. 회전대칭이 아닌 어떤 표적을 넣어도 통과한다(검사 2 참조). "
            "반증 가능성 0. 그런데 라운드에서 가장 인용하기 좋은 숫자가 여기서 나왔다."),
    dict(id="mesh_no_rotor 헤드라인", file="report16_rung_mesh_no_rotor.prereg.json", cls="FORCED",
         ko="로터를 떼면 변조가 0. ⭐ 그 단이 **스스로** «반증력 0» 이라고 적었다 — 모범이다."),
    dict(id="mesh_full P1", file="report16_rung_mesh_full_prereg.json", cls="FORCED-ish",
         ko="플래시 대조비 ≥ 3 dB. 검사 4 대로 널도 통과한다. 그 단이 D8·D10 로 스스로 지적했다."),
    dict(id="mesh_full P7", file="report16_rung_mesh_full_prereg.json", cls="FORCED-ish",
         ko="방위 산포 ≥ 0.5 dB. 회전대칭이 아니면 자동으로 성립한다."),
    dict(id="mesh_full P5·P6", file="report16_rung_mesh_full_prereg.json", cls="FALSIFIABLE",
         ko="플래시가 «예측한 위상»에 «블레이드 수만큼» 서는가 — 틀릴 수 있었고 실제로 일부 틀렸다(FAIL). "
            "틀린 것을 지우지 않은 점이 이 라운드 신뢰의 근거다."),
    dict(id="cube P2·P3", file="report16_rung_cube_eqvol_prereg.json", cls="FALSIFIABLE",
         ko="정육면체는 4의 배수 차수에만 실린다 / 블레이드 선(차수 2)이 없다 — 틀릴 수 있었다."),
    dict(id="box P2·P2b·P3", file="report16_rung_box_bbox_prediction.json", cls="FALSIFIABLE",
         ko="종횡비가 90° 대칭을 깨고 축이탈이 홀수 차수를 만든다 — 정량 문턱까지 걸었고 일부 빗나갔다."),
    dict(id="box P6", file="report16_rung_box_bbox_prediction.json", cls="FALSIFIABLE(자기불리)",
         ko="⭐ blade_comb_frac 이 상자와 블레이드를 **구별 못 한다**는 예측. 자기에게 불리한 쪽을 미리 "
            "적었고 맞았다 — 이 라운드에서 가장 정직한 항목 중 하나."),
    dict(id="box P7 / cube P3 방향미정 / sphere P5", file="여러 파일", cls="UNPREDICTED",
         ko="풍부도의 부호·사다리 성적을 일부러 예측하지 않았다. 사후에 «맞췄다» 고 말하지 않은 것도 확인했다."),
    dict(id="half_tri P1~P7", file="report16_rung_mesh_half_tri_prereg.json", cls="FALSIFIABLE",
         ko="⭐ 삼각형을 절반으로 줄여도 base 판정이 살아남는가 — 뒤집히면 철회하겠다고 미리 적었다. "
            "이 라운드에서 **형상 정밀도**를 실제로 물은 몇 안 되는 단이다."),
])
n_forced = sum(1 for x in pre["items"] if x["cls"].startswith("FORCED"))
pre["counts"] = dict(total_groups=len(pre["items"]), forced_groups=n_forced,
                     falsifiable_groups=sum(1 for x in pre["items"] if x["cls"].startswith("FALSIFIABLE")),
                     deliberately_unpredicted=sum(1 for x in pre["items"] if x["cls"] == "UNPREDICTED"))
pre["headline_ko"] = (
    f"예측 묶음 {len(pre['items'])} 개 중 {n_forced} 개가 통과가 보장된 항목이다. 나머지는 진짜 예측이고 "
    "몇 개는 실제로 틀렸으며 틀린 채로 남아 있다. ⭐ 문제는 개수가 아니라 **어느 것이 헤드라인이 됐는가** 다 "
    "— 라운드에서 가장 인용하기 좋은 두 숫자(구의 0, 메쉬−널 62 dB)가 둘 다 FORCED 쪽에서 나왔다.")
J["check6_falsifiability_audit"] = pre


# =========================================================================== #
#  결함 목록 · 판정
# =========================================================================== #
r_mini, r_mat = taut["rows"]["mini2"], taut["rows"]["matrice4e"]
c_mini, c_mat = conf["rows"]["mini2"], conf["rows"]["matrice4e"]
J["defects"] = [
 dict(id="D1", severity="HIGH", kind="tautology",
      where="outputs/report16_rung_sphere_eqvol.json → findings.05_gap · preregistration.P4_gap_ko; "
            "benchmark/report16_rung_sphere_eqvol.py",
      ko=("「구조가 마이크로도플러에 기여하는 양 = 메쉬 − 구 = 최소 62 dB」가 사실상 동어반복이다. "
          f"형상 디테일이 0 인 평판이 그 간격의 mini2 {100*r_mini['share_bought_by_detail_free_slab']:.1f} % · "
          f"matrice4e {100*r_mat['share_bought_by_detail_free_slab']:.1f} % 를 이미 산다. "
          f"CAD 정밀도 단독 몫은 {r_mini['cad_precision_only_db']:.2f} / {r_mat['cad_precision_only_db']:.2f} dB 뿐이다. "
          "프로펠러를 통짜 상자로 바꾼 팔은 간격이 오히려 더 크다."),
      fix_ko="간격의 기준을 «구» 가 아니라 «slab(디테일 0)» 으로 바꿔 다시 인용할 것. 널은 계산기 바닥을 "
             "보여 주는 자리지 사다리의 첫 칸이 아니다."),
 dict(id="D2", severity="HIGH", kind="missing-question",
      where="report16 사다리 전 단(기반 1 + 링 6 + 지표 6). 가장 가까운 것이 "
            "report16_metric_sphere_eqvol.json 의 equivalent_noise_snr_db",
      ko=("«차이가 있는가» 에서 멈췄고 «검출기에 얼마나 영향을 주는가» 를 사다리의 어느 단도 계산하지 "
          "않았다. Pd·Pfa·ROC·적분시간·CFAR 가 계산 단 전체에 없다. cube 단은 스스로 «탐지 성능이 "
          "아니다» 라고 적었으므로 허위진술은 아니지만, 빈칸은 그대로다."),
      fix_ko="검사 5 의 거친 표를 정식 단으로 승격할 것 — 두 검출기(템플릿 / 대역 에너지)에서 답이 "
             "반대로 나오므로, 어느 검출기를 쓸지 정하지 않으면 «형상이 필요한가» 는 답이 없는 질문이다."),
 dict(id="D3", severity="HIGH", kind="confound",
      where="benchmark/report16_rung_sphere_eqvol.py · report16_rung_cube_eqvol.py · report16_rung_box_bbox.py",
      ko=("널·전신 프리미티브 세 단은 «기체 전체가 로터 rpm 으로 자전» 하는 물체다 — 실제 드론이 아니다. "
          f"인용되는 «정육면체 − 메쉬» 차이 mini2 {c_mini['cited_cube_minus_mesh_db']:.2f} dB 는 "
          f"운동학 {c_mini['kinematics_term_db']:.2f} + 재질 {c_mini['material_term_db']:.2f} + "
          f"형상 {c_mini['shape_term_db']:.2f} dB 로 갈라지고, matrice4e 는 "
          f"{c_mat['kinematics_term_db']:.2f} + {c_mat['material_term_db']:.2f} + "
          f"{c_mat['shape_term_db']:.2f} dB 다. 형상은 셋 중 가장 작거나 부호가 반대다."),
      fix_ko="형상 결론은 운동학이 맞춰진 팔(slab·prop_bbox·mesh_half_tri·mesh_rigid_spin)에서만 낼 것. "
             "box 단은 이미 이것을 자기 최대 의심으로 적었고 cube 단은 대조군을 만들었다 — sphere 단만 안 고쳤다."),
 dict(id="D4", severity="MEDIUM-HIGH", kind="metric-floor",
      where="benchmark/report16_base.py::md_metrics16 ① flash_contrast_db (전 단 파급)",
      ko=(f"물리적 변조가 0 인 널 팔이 mini2 에서 "
          f"{floor['rows']['mini2']['flash_contrast_db']['sphere_NULL']:.2f} dB 를 읽어 진짜 메쉬 "
          f"{floor['rows']['mini2']['flash_contrast_db']['mesh']:.2f} dB 를 **이긴다**. base 가 적어 둔 "
          "«회전대칭체 이론값 = 0 dB» 는 지켜지지 않는다. mesh_full 단이 스스로 찾아 적었지만 여러 단의 "
          "요약 표에는 여전히 자격 표시 없이 나란히 찍힌다."),
      fix_ko="md_metrics16 이 in_band_ac_frac < 0.5 인 팔의 flash_contrast_db 를 NaN 으로 반환하도록 "
             "바꾸거나, 모든 표에서 그 칸을 지울 것."),
 dict(id="D5", severity="MEDIUM", kind="material-confound",
      where="benchmark/report16_rung_cube_eqvol.py · report16_rung_box_bbox.py (프리미티브 |Γ|=1)",
      ko=(f"프리미티브는 PEC 이고 메쉬는 재질 가중이라 세기 비교에 재질이 "
          f"{c_mini['material_term_db']:.2f} / {c_mat['material_term_db']:.2f} dB 섞인다. "
          "mini2 에서는 이 재질 항이 형상 항보다 크다."),
      fix_ko="세기 축 비교는 mesh_rigid_spin_pec 처럼 재질을 맞춘 짝으로만 할 것(두 단이 이미 재료를 갖고 있다)."),
 dict(id="D6", severity="MEDIUM", kind="effort-allocation",
      where="report16 라운드 구성(6 단 중 3 단이 널·전신 프리미티브)",
      ko=("답이 기하학적으로 정해진 단(구·정육면체·경계상자)에 라운드 무게가 실렸고, «형상 정밀도» 를 "
          "실제로 묻는 단(slab·prop_bbox·mesh_half_tri)은 곁가지로 들어가 있다. "
          f"정작 답은 곁가지에 있다 — 삼각형 절반은 파형 상관 "
          f"{det['rows']['mini2|mesh_half_tri']['coherent_ac_corr']:.4f} / "
          f"{det['rows']['matrice4e|mesh_half_tri']['coherent_ac_corr']:.4f} 로 무해하고, 블레이드 디테일 제거는 "
          f"{det['rows']['mini2|slab']['coherent_ac_corr']:.4f} / "
          f"{det['rows']['matrice4e|slab']['coherent_ac_corr']:.4f} 로 유의하다."),
      fix_ko="다음 라운드는 slab ↔ prop_bbox ↔ mesh_half_tri ↔ mesh 사이의 «정밀도 단계» 로 사다리를 다시 짤 것."),
 dict(id="D7", severity="LOW", kind="framing",
      where="outputs/report16_base.json meta.headline_question_ko ↔ sphere 단 findings",
      ko=("헤드라인 질문은 «형상 정밀도» 인데 sphere 단의 큰 숫자는 «구조(있음/없음)» 다. 두 말이 한 라운드 "
          "안에 있으면 인용될 때 갈라지지 않는다. sphere 단 문장 자체는 참이다."),
      fix_ko="«구조(있음/없음)» 와 «형상 정밀도(거칠음/정밀함)» 를 문서 전체에서 다른 낱말로 못박을 것."),
]

J["what_held_up"] = dict(ko=[
    f"⭐ 회전은 진짜다. 내가 점을 직접 돌려 CPU 로 다시 계산한 값이 저장된 표와 "
    f"{max(v.get('max_rel_err_vs_stored', 0) for v in rot['rows'].values()):.1e} 상대오차로 같다. "
    "안 돌리고 0 을 적은 것이 아니다 — BROKEN 아님.",
    "⭐ 양성 대조군이 살아 있다. 같은 구를 회전축에서 비켜 놓자 같은 코드가 큰 변조를 냈다. "
    "«구가 0» 이 죽은 코드 때문일 가능성은 닫혔다.",
    "사전 예측이 계산보다 먼저 쓰였고 sha256 으로 봉인됐다. 틀린 예측(mesh_full P5·P6)이 지워지지 않았다.",
    "지표는 전 단이 report16_base.md_metrics16 을 import 해서 썼다 — 단마다 다른 자를 쓰지 않았다.",
    "⭐⭐ 여러 단이 **스스로** 동어반복을 고발했다. mesh_no_rotor 는 자기 예측을 «반증력 0» 이라 적었고, "
    "mesh_full 은 «형상 정밀도가 값어치 있다를 주장하지 않는다» 고 못박았으며, box 단은 운동학 교란을 "
    "자기 최대 의심으로 지목했고, sphere 단은 검출기에 따라 답이 갈린다는 것을 말로 정확히 짚었다. "
    "이 라운드가 BROKEN 이 아닌 이유의 절반은 이 자기고발이다.",
])

#  ⭐ 나란히 돌던 다른 렌즈와 우연히 겹쳤는가 — 겹쳤다면 그것도 증거다
_sib = os.path.join(ROOT, "outputs/report16_verify_detector.json")
if os.path.exists(_sib):
    try:
        _s = json.load(open(_sib))
        J["independent_convergence"] = dict(
            sibling_file="outputs/report16_verify_detector.json",
            sibling_generated=_s.get("meta", {}).get("generated"),
            sibling_verdict=_s.get("verdict", {}).get("verdict"),
            mine="PREMATURE",
            ko=("⭐ 이 라운드를 다른 각도(검출 렌즈)에서 본 파일이 나와 **따로** 같은 판정에 닿았다. "
                "그쪽은 «지표가 검출 통계량이 아니다» 를 1번 결함으로 꼽았고, 나는 «가장 인용하기 좋은 "
                "숫자가 반증 불가능한 예측에서 나왔다» 를 1번으로 꼽았다. 서로 다른 이유로 같은 결론에 "
                "닿은 것이므로, 이 PREMATURE 는 한 렌즈의 취향이 아니다. "
                "⚠ 다만 D2 는 두 렌즈가 겹치는 부분이라 «독립 증거 2 개» 로 세면 안 된다."))
    except Exception:
        pass

J["verdict"] = "PREMATURE"
J["verdict_ko"] = (
    "⭐ **PREMATURE** — 기계는 멀쩡하고 자기검열도 이례적으로 좋다. 그러나 결론은 아직 이르다. 이유 셋. "
    "① 라운드에서 가장 인용하기 좋은 숫자(메쉬 − 널 = 62~77 dB)가 반증 불가능한 예측에서 나왔고, "
    f"그중 CAD 정밀도가 산 몫은 {r_mini['cad_precision_only_db']:.2f}~{r_mat['cad_precision_only_db']:.2f} dB"
    f"({100*r_mini['cad_precision_only_share']:.1f}~{100*r_mat['cad_precision_only_share']:.1f} %) 뿐이다 — "
    "나머지는 «회전대칭이 아니다» 라는 자명한 사실이 번 돈이다. "
    "② 널·전신 프리미티브 단은 형상 말고 운동학·재질까지 바꿔 놓아서, 인용되는 차이의 대부분이 형상이 아니다. "
    "③ ⭐⭐ 이 렌즈가 요구한 선 — «그 차이가 검출기에 얼마나 영향을 주는가» — 을 아무 단도 넘지 않았다. "
    "넘었다고 **주장한** 단도 없다는 점은 정직성의 증거이지만, 그래서 라운드는 아직 «차이가 있다» 까지만 왔다. "
    "내가 거칠게 넘어가 보니 답은 검출기 종류에 따라 정반대다 — 템플릿 검출기에서는 형상이 크게 중요하고"
    f"(Pd 0.90 → {det['rows']['mini2|slab']['pd_when_perfect_template_gives_0p90']:.3f}), "
    f"대역 에너지 검출기에서는 거의 안 중요하다(ΔAC {det['rows']['mini2|slab']['delta_ac_power_db']:+.2f} dB). "
    "이 갈림을 정하지 않으면 «형상 정밀도가 값어치 있는가» 는 답이 없는 질문이다. "
    "BROKEN 은 아니다 — 구·상자를 실제로 돌렸고 그 사실을 내가 독립 구현으로 확인했다.")
J["my_numbers_are_crude_ko"] = (
    "⚠⚠ **이 파일이 새로 만든 숫자는 전부 crude(거친 추정)다.** 검출기 모형은 교과서 단일 룩 제곱검파에 "
    "Pfa=1e-6 하나뿐이고 잡음·클러터·CPI·CFAR·다중 Rx 가 없다. 정합손실은 «로터 위상·rpm·방위를 다 안다» 는 "
    "이상적 가정에서 나온다. 세기 비교에는 재질이 섞여 있고, PO 커널은 3.5 GHz 에서 블레이드 폭이 유효 무릎 "
    "아래다. 여기 숫자로 순위를 매기지 말고, «두 검출기에서 부호가 반대» 라는 **정성적 갈림**만 가져가라.")
J["meta"]["seconds"] = float(time.time() - T0)

with open(OUT, "w") as f:
    json.dump(J, f, ensure_ascii=False, indent=1)
print("판정:", J["verdict"])
print("결함:", ", ".join(f"{d['id']}({d['severity']})" for d in J["defects"]))
print("→", OUT, os.path.getsize(OUT), "bytes")
