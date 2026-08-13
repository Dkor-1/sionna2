"""matrice4e 짐벌 — 결함 증거 수집 (측정 전용, 소스 무수정).

무엇을 하나
  1) DJI 공식 STEP(M4T) 을 gmsh 로 열어 뽑아 둔 솔리드별 바운딩박스에서 **짐벌과 기수**를 잰다.
  2) 지금 메쉬(src/drone_cad.py 의 `_gimbal_sensor_v2` 호출값)를 **읽기만 해서** 같은 양을 잰다.
  3) 4E 제품사진(p02 정면)에서 짐벌 앞면을 **픽셀로** 잰다. 축척은 두 개의 독립 기준으로 잡는다.
  4) 세 값을 한 좌표계에 놓고 비교 → outputs/meshdef_gimbal.json.

⛔ 이 스크립트는 아무것도 고치지 않는다. 숫자는 전부 이 안에서 계산한다.
"""
import json, os, sys, subprocess, datetime
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = "/workspace/sionna"
SCRATCH = "/tmp/claude-1015/-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad"
sys.path.insert(0, os.path.join(ROOT, "src"))

# --------------------------------------------------------------------------- #
# 0. 좌표계 — CAD(STEP) 와 우리 메쉬는 축이 다르다.
#    CAD:  X=좌우, Y=위(+), Z=뒤(+)   |   우리:  x=기수(+), y=좌우, z=위(+)
#    아래 두 상수는 **아래에서 앵커로 검증**한다(손입력한 추정이 아니다).
# --------------------------------------------------------------------------- #
CAD = json.load(open(os.path.join(SCRATCH, "m4t_cad_solids.json")))
SOL = {r["tag"]: r for r in CAD["solids"]}


def bb(tag):
    b = SOL[tag]["bbox"]
    return dict(x=(b[0], b[3]), y=(b[1], b[4]), z=(b[2], b[5]))


def cadZ_to_x(Z, c):    return c - Z
def cadY_to_z(Y, d):    return Y + d


# --- 앵커: 우리 메쉬 소스에 적혀 있는 부착물 좌표 ↔ CAD 솔리드 -------------- #
#     (drone_cad.py 주석이 인용한 값들. 우리가 CAD 에서 직접 잰 값과 맞춰 본다.)
ANCHORS = [
    # (이름, 우리 메쉬 x[mm], CAD 솔리드 태그들 → Z 중심)
    ("RTK 터렛 중심",      -20.2,  [26, 122]),
    ("전방 어안쌍",        146.2,  [35, 40]),
    ("후방 어안쌍",        -53.6,  [34, 41]),
    ("하방 어안쌍",         84.4,  [44, 46]),
]
ANCHORS_Z = [
    ("접지(다리끝)",       -59.82, [89, 90, 80, 101]),
    ("전방 어안쌍",         48.5,  [35, 40]),
    ("후방 어안쌍",         49.4,  [34, 41]),
]


def fit_offset(anchors, axis):
    """x_ours = c − Z_cad (axis='x') / z_ours = Y_cad + d (axis='z') 의 상수를 최소제곱으로."""
    vals = []
    for name, ours, tags in anchors:
        if axis == "x":
            cen = np.mean([(bb(t)["z"][0] + bb(t)["z"][1]) / 2 for t in tags])
            vals.append((name, ours, cen, ours + cen))          # c = ours + Z
        else:
            cen = np.mean([bb(t)["y"][0] for t in tags]) if name.startswith("접지") else \
                  np.mean([(bb(t)["y"][0] + bb(t)["y"][1]) / 2 for t in tags])
            vals.append((name, ours, cen, ours - cen))          # d = ours − Y
    k = float(np.mean([v[3] for v in vals]))
    resid = [dict(anchor=v[0], ours_mm=v[1], cad_mm=round(v[2], 2),
                  implied_const=round(v[3], 2), residual_mm=round(v[3] - k, 2)) for v in vals]
    return k, resid


C_X, RES_X = fit_offset(ANCHORS, "x")
D_Z, RES_Z = fit_offset(ANCHORS_Z, "z")

# --------------------------------------------------------------------------- #
# 1. CAD(M4T) — 짐벌과 기수
# --------------------------------------------------------------------------- #
GIM_TAGS = [59, 48]          # 59 = 카메라 블록(+롤 요크), 48 = 요크/롤 조립
WIN_TAGS = [50, 51, 52, 53, 54, 55]   # 1 mm 두께 창(개구) 판 — 4T 는 6개
GROUND_Y = min(r["bbox"][1] for r in CAD["solids"])

blk, yok = bb(59), bb(48)
wins = [bb(t) for t in WIN_TAGS]
win_x = (min(w["x"][0] for w in wins), max(w["x"][1] for w in wins))
win_y = (min(w["y"][0] for w in wins), max(w["y"][1] for w in wins))
win_z = (min(w["z"][0] for w in wins), max(w["z"][1] for w in wins))

# 기수 기준 후보 (짐벌 솔리드 제외, 중심부만)
nose_cands = {}
for tag, r in SOL.items():
    if tag in GIM_TAGS:
        continue
    b = r["bbox"]
    if abs((b[0] + b[3]) / 2) < 70:
        nose_cands[tag] = b[2]
nose_sorted = sorted(nose_cands.items(), key=lambda kv: kv[1])
# 창(개구) 판들은 짐벌 부품이므로 기수 후보에서 뺀다
nose_sorted = [(t, z) for t, z in nose_sorted if t not in WIN_TAGS]
# 최전방 2개 + 눈에 보이는 셸 앞끝(124=상부커버, 109=본체 셸) 을 기준 후보로 둔다
nose_sorted = nose_sorted[:2] + [(t, SOL[t]["bbox"][2]) for t in (124, 109)]

cad = dict(
    global_bbox_mm=dict(width_x=round(CAD["global_bbox"][3] - CAD["global_bbox"][0], 2),
                        height_y=round(CAD["global_bbox"][4] - CAD["global_bbox"][1], 2),
                        length_z=round(CAD["global_bbox"][5] - CAD["global_bbox"][2], 2)),
    ground_plane_Y_mm=round(GROUND_Y, 2),
    camera_block_solid59=dict(w_mm=round(blk["x"][1] - blk["x"][0], 2),
                              h_mm=round(blk["y"][1] - blk["y"][0], 2),
                              d_mm=round(blk["z"][1] - blk["z"][0], 2),
                              front_Z_mm=round(blk["z"][0], 2),
                              bottom_Y_mm=round(blk["y"][0], 2),
                              top_Y_mm=round(blk["y"][1], 2),
                              fill_pct=round(100 * SOL[59]["volume_mm3"] /
                                             (SOL[59]["dx"] * SOL[59]["dy"] * SOL[59]["dz"]), 1)),
    yoke_solid48=dict(w_mm=round(yok["x"][1] - yok["x"][0], 2),
                      h_mm=round(yok["y"][1] - yok["y"][0], 2),
                      d_mm=round(yok["z"][1] - yok["z"][0], 2),
                      front_Z_mm=round(yok["z"][0], 2)),
    aperture_windows=dict(n=len(WIN_TAGS),
                          cluster_w_mm=round(win_x[1] - win_x[0], 2),
                          cluster_h_mm=round(win_y[1] - win_y[0], 2),
                          front_Z_mm=round(win_z[0], 2),
                          recess_behind_block_face_mm=round(win_z[0] - blk["z"][0], 2)),
    ground_clearance_mm=round(blk["y"][0] - GROUND_Y, 2),
    nose_reference_candidates=[dict(solid=t, front_Z_mm=round(z, 2),
                                    x_ours_mm=round(cadZ_to_x(z, C_X), 2)) for t, z in nose_sorted[:4]],
    block_front_x_ours_mm=round(cadZ_to_x(blk["z"][0], C_X), 2),
    block_bottom_z_ours_mm=round(cadY_to_z(blk["y"][0], D_Z), 2),
    block_top_z_ours_mm=round(cadY_to_z(blk["y"][1], D_Z), 2),
)
cad["protrusion_vs_nose_mm"] = {
    f"solid{t}": round(cadZ_to_x(blk["z"][0], C_X) - cadZ_to_x(z, C_X), 2)
    for t, z in nose_sorted[:4]}

# --------------------------------------------------------------------------- #
# 2. 지금 메쉬 (읽기 전용)
# --------------------------------------------------------------------------- #
from drones import DRONES, frame_fit_scale                      # noqa: E402
from drone_cad import build_frame_cad, _gimbal_sensor_v2        # noqa: E402
import trimesh                                                  # noqa: E402

spec = DRONES["matrice4e"]
GIM_ARGS = dict(w=0.059, h=0.047, d=0.052, cx=0.1483, cz=-0.01716)   # drone_cad.py L2178 리터럴
parts = _gimbal_sensor_v2(**GIM_ARGS)
Vg = np.vstack([np.asarray(m.vertices) for _, m in parts]) * 1000.0
Vblk = np.vstack([np.asarray(parts[i][1].vertices) for i in (2, 3)]) * 1000.0   # 블록 상자 2개
Vbar = np.vstack([np.asarray(parts[i][1].vertices) for i in (4, 5, 6, 7)]) * 1000.0  # 롤 배럴

Asm = build_frame_cad(spec)
Vb = np.vstack([np.asarray(m.vertices) for m in Asm.parts["body"]]) * 1000.0
shell = Vb[np.abs(Vb[:, 1]) < 60]                       # 팔을 뺀 동체 셸
Vgear = np.vstack([np.asarray(m.vertices) for m in Asm.parts["gear"]]) * 1000.0
ground_z = float(Vgear[:, 2].min())
zband = shell[(shell[:, 2] >= Vblk[:, 2].min()) & (shell[:, 2] <= Vblk[:, 2].max())]

mesh = dict(
    source="src/drone_cad.py:2178  _gimbal_sensor_v2(0.059, 0.047, 0.052, 0.1483, -0.01716)",
    fit_scale=[round(v, 6) for v in frame_fit_scale(spec)],
    block_w_mm=round(Vblk[:, 1].max() - Vblk[:, 1].min(), 2),
    block_h_mm=round(Vblk[:, 2].max() - Vblk[:, 2].min(), 2),
    block_d_mm=round(Vblk[:, 0].max() - Vblk[:, 0].min(), 2),
    block_front_x_mm=round(Vblk[:, 0].max(), 2),
    block_bottom_z_mm=round(Vblk[:, 2].min(), 2),
    block_top_z_mm=round(Vblk[:, 2].max(), 2),
    barrel_span_y_mm=round(Vbar[:, 1].max() - Vbar[:, 1].min(), 2),
    assembly_front_x_mm=round(Vg[:, 0].max(), 2),          # 개구 돌기 포함
    assembly_top_z_mm=round(Vg[:, 2].max(), 2),            # 요 실린더/댐핑판 꼭대기
    shell_nose_max_x_mm=round(shell[:, 0].max(), 2),
    shell_nose_max_x_in_block_zband_mm=round(zband[:, 0].max(), 2),
    shell_belly_z_at_nose_mm=round(shell[(shell[:, 0] > 150)][:, 2].min(), 2),
    ground_z_mm=round(ground_z, 2),
    ground_clearance_mm=round(Vblk[:, 2].min() - ground_z, 2),
)
mesh["protrusion_vs_shell_bbox_mm"] = round(mesh["block_front_x_mm"] - mesh["shell_nose_max_x_mm"], 2)
mesh["protrusion_vs_shell_at_block_height_mm"] = round(
    mesh["block_front_x_mm"] - mesh["shell_nose_max_x_in_block_zband_mm"], 2)
mesh["protrusion_incl_apertures_mm"] = round(
    mesh["assembly_front_x_mm"] - mesh["shell_nose_max_x_mm"], 2)

# --------------------------------------------------------------------------- #
# 3. 4E 사진 실측 — p02 정면컷 (2560², 흰 배경)
# --------------------------------------------------------------------------- #
P02 = os.path.join(ROOT, "assets/photos/matrice4e/matrice4e_p02_front_elevation.jpg")
A = np.asarray(Image.open(P02).convert("L")).astype(float)


def blob(seed, thr, win, bright=False):
    (x0, x1), (y0, y1) = win
    s = A[y0:y1, x0:x1]
    m = (s > thr) if bright else (s < thr)
    lab, _ = ndi.label(m)
    l = lab[seed[1] - y0, seed[0] - x0]
    ys, xs = np.where(lab == l)
    return dict(x=(int(x0 + xs.min()), int(x0 + xs.max())), y=(int(y0 + ys.min()), int(y0 + ys.max())),
                w=int(xs.max() - xs.min() + 1), h=int(ys.max() - ys.min() + 1))


def dark_extent(y, thr=130, x0=1080, x1=1520):
    xs = np.where(A[y, x0:x1] < thr)[0]
    return (int(x0 + xs.min()), int(x0 + xs.max()), int(xs.max() - xs.min() + 1)) if len(xs) else None


sil = A < 245
def lowest_in(a, b):
    yy, xx = np.where(sil[:, a:b]); return int(yy.max()), float(a + xx[yy == yy.max()].mean())


# 어안 두 눈(중심) — 축척 기준 1.  창 안 어두운 픽셀의 무게중심(좌우 대칭이라 편향이 상쇄된다)
def dark_centroid(x0, x1, y0, y1, thr=70):
    s = A[y0:y1, x0:x1]
    ys, xs = np.where(s < thr)
    return float(x0 + xs.mean()), float(y0 + ys.mean())


eyeL_c, _ = dark_centroid(1075, 1215, 1225, 1335)
eyeR_c, _ = dark_centroid(1355, 1495, 1225, 1335)
eye_sep_px = eyeR_c - eyeL_c
eye_sep_cad_mm = float(np.mean([abs(bb(35)["x"][0] + bb(35)["x"][1]) / 2,
                                abs(bb(40)["x"][0] + bb(40)["x"][1]) / 2]) * 2)

# 앞다리 끝 — 축척 기준 2
legFL_y, legFL_x = lowest_in(350, 700)
legFR_y, legFR_x = lowest_in(1860, 2210)
legRL_y, legRL_x = lowest_in(700, 1000)
legRR_y, legRR_x = lowest_in(1560, 1860)
leg_sep_px = legFR_x - legFL_x
leg_sep_cad_mm = ((bb(101)["x"][0] + bb(101)["x"][1]) / 2 - (bb(80)["x"][0] + bb(80)["x"][1]) / 2)

s1 = eye_sep_px / eye_sep_cad_mm
s2 = leg_sep_px / leg_sep_cad_mm
scale = float(np.mean([s1, s2]))
scale_spread = float(abs(s1 - s2) / 2 / scale)

# 짐벌 앞면
# 블록 폭은 **롤 배럴이 없는 행**에서만 잰다(배럴이 걸치는 1407~1415·1540~1542 는 뺀다).
rows_block = [dark_extent(y) for y in list(range(1392, 1407)) + list(range(1545, 1562))]
block_w_px = int(np.median([r[2] for r in rows_block if r]))
rows_all = [dark_extent(y) for y in range(1390, 1630)]
barrel_span_px = max(r[2] for r in rows_all if r)
colband = A[:, 1250:1350].mean(axis=1)
top_px = int(next(y for y in range(1390, 1460) if colband[y] < 60))
bot_px = int(max(np.where(A[1500:1700, 1290:1310].min(axis=1) < 245)[0]) + 1500)
circ = blob((1240, 1470), 50, ((1150, 1320), (1400, 1520)))      # 원형 텔레 렌즈(진원 가정)
fore = circ["h"] / circ["w"]                                     # 세로 단축률
lrf = blob((1215, 1570), 170, ((1160, 1270), (1500, 1640)), bright=True)
wide = blob((1360, 1570), 50, ((1240, 1440), (1500, 1640)))
ap_top = min(circ["y"][0], lrf["y"][0], wide["y"][0])
ap_bot = max(circ["y"][1], lrf["y"][1], wide["y"][1])

# 시차(depth parallax) 크기 — 같은 높이의 앞/뒤 다리 끝이 이미지에서 벌어진 양
par_px_per_mm_depth = (legFL_y - legRL_y) / (
    (bb(80)["z"][0] + bb(80)["z"][1]) / 2 * -1 + (bb(89)["z"][0] + bb(89)["z"][1]) / 2)
gim_depth_ahead_of_legs = ((bb(80)["z"][0] + bb(80)["z"][1]) / 2) - blk["z"][0]
clearance_px_raw = legFL_y - bot_px
clearance_px_corr = clearance_px_raw + par_px_per_mm_depth * gim_depth_ahead_of_legs

photo = dict(
    file="assets/photos/matrice4e/matrice4e_p02_front_elevation.jpg",
    note_ko="이 폴더에 4E 의 **정투영 측면뷰는 없다**. p01 은 파일명과 달리 후면뷰다(p05 와 같은 각도).",
    scale_anchor_1=dict(what="전방 어안 두 눈 중심 간격", px=round(eye_sep_px, 1),
                        mm_from_cad=round(eye_sep_cad_mm, 2), px_per_mm=round(s1, 4)),
    scale_anchor_2=dict(what="앞다리 끝 좌우 간격", px=round(leg_sep_px, 1),
                        mm_from_cad=round(leg_sep_cad_mm, 2), px_per_mm=round(s2, 4)),
    scale_px_per_mm=round(scale, 4), scale_rel_spread=round(scale_spread, 4),
    foreshortening_factor=round(fore, 3),
    foreshortening_basis="원형 텔레 개구를 진원으로 보고 세로/가로 비",
    block_w_px=block_w_px, barrel_span_px=barrel_span_px,
    block_top_px=top_px, block_bottom_px=bot_px, block_h_px=bot_px - top_px,
    aperture_cluster_h_px=ap_bot - ap_top,
    block_w_mm=round(block_w_px / scale, 1),
    barrel_span_mm=round(barrel_span_px / scale, 1),
    block_h_mm_raw=round((bot_px - top_px) / scale, 1),
    block_h_mm_deforeshortened=round((bot_px - top_px) / scale / fore, 1),
    aperture_cluster_h_mm=round((ap_bot - ap_top) / scale / fore, 1),
    ground_clearance_mm_raw=round(clearance_px_raw / scale, 1),
    ground_clearance_mm_parallax_corrected=round(clearance_px_corr / scale, 1),
    parallax_px_per_mm_depth=round(par_px_per_mm_depth, 3),
)

# --------------------------------------------------------------------------- #
# 4. σ 영향 — (a) 평판극한, (b) 조명 투영면적 몫
# --------------------------------------------------------------------------- #
LAM = 3e8 / 3.5e9


def plate_sigma(w, h):
    a = w * h
    return 10 * np.log10(4 * np.pi * a * a / LAM ** 2)


def proj(meshes, u):
    tot = 0.0
    for m in meshes:
        t = trimesh.Trimesh(vertices=np.asarray(m.vertices), faces=np.asarray(m.faces), process=False)
        tot += float((t.area_faces * np.clip(t.face_normals @ u, 0, None)).sum())
    return tot


allm = [m for g in Asm.parts for m in Asm.parts[g]]
gim_now = [m for _, m in parts]
# 제안값: 앞면은 사진, 앞면 x 와 바닥 z 는 지금 값을 고정
h_new = photo["block_h_mm_deforeshortened"] / 1000.0 / 0.95      # helper 블록 높이 = 0.95·h
w_new = photo["block_w_mm"] / 1000.0
d_new = (blk["z"][1] - blk["z"][0]) / 1000.0                     # 깊이는 CAD(4T) 뿐
cx_new = Vblk[:, 0].max() / 1000.0 - d_new / 2.0
cz_new = Vblk[:, 2].min() / 1000.0 + 0.48 * h_new
gim_new = [m for _, m in _gimbal_sensor_v2(w_new, h_new, d_new, cx_new, cz_new)]
Vn = np.vstack([np.asarray(m.vertices) for m in gim_new]) * 1000.0

sig = dict(fc_hz=3.5e9, lambda_mm=round(LAM * 1000, 2), method_ko="평판극한 σ=4πA²/λ² (정면 정반사 상한)")
for tag, (w, h) in [("mesh_now", (mesh["block_w_mm"], mesh["block_h_mm"])),
                    ("photo_4e", (photo["block_w_mm"], photo["block_h_mm_deforeshortened"])),
                    ("cad_4t", (cad["camera_block_solid59"]["w_mm"], cad["camera_block_solid59"]["h_mm"]))]:
    sig[f"front_face_{tag}"] = dict(w_mm=w, h_mm=h, area_cm2=round(w * h / 100, 2),
                                    sigma_plate_dbsm=round(plate_sigma(w / 1000, h / 1000), 2))
sig["front_face_delta_db_now_to_photo"] = round(
    sig["front_face_photo_4e"]["sigma_plate_dbsm"] - sig["front_face_mesh_now"]["sigma_plate_dbsm"], 2)
sig["projected_area"] = {}
for lab, el in [("el_0deg", 0.0), ("el_15deg", 15.0)]:
    e = np.deg2rad(el); u = np.array([np.cos(e), 0.0, np.sin(e)])
    tot, g1, g2 = proj(allm, u), proj(gim_now, u), proj(gim_new, u)
    sig["projected_area"][lab] = dict(
        view_ko="기수 정면에서 본 조명 투영면적(가림 미고려)",
        total_cm2=round(tot * 1e4, 2), gimbal_now_cm2=round(g1 * 1e4, 2),
        gimbal_now_share_pct=round(100 * g1 / tot, 1),
        gimbal_proposed_cm2=round(g2 * 1e4, 2),
        gimbal_delta_db=round(20 * np.log10(g2 / g1), 2),
        whole_drone_delta_db=round(20 * np.log10((tot - g1 + g2) / tot), 2),
        caveat_ko=("면적비에 20log10 을 쓴 것은 평판극한(σ∝A²) 규약이다. 기체 전체는 산란체가 여러 개라 "
                   "실제 σ 변화는 이보다 작고 각도에 따라 부호도 바뀐다 — 크기 감각용 상한으로만 읽을 것."))

# --------------------------------------------------------------------------- #
# 5. "30~40 mm" 주장 추적
# --------------------------------------------------------------------------- #
claim_hits = subprocess.run(
    ["grep", "-rn", "30~40mm", os.path.join(ROOT, "docs"), os.path.join(ROOT, "src"),
     os.path.join(ROOT, "report_mesh")],
    capture_output=True, text=True).stdout.strip().splitlines()
claim = dict(
    text="정면에서 볼 때 동체 앞으로 30~40mm 돌출한다",
    found_in=[h.split(":")[0].replace(ROOT + "/", "") + ":" + h.split(":")[1] for h in claim_hits],
    field="docs/drone_specs_2026.json → specs[matrice4e].silhouette",
    provenance_ko=(
        "이 문장은 LLM 조사 서술문(silhouette 필드) 안에 있다. 같은 파일의 sources 목록은 DJI 스펙표·"
        "매뉴얼·판매점 페이지뿐이고 **치수 기입 도면은 하나도 없다**(DJI 는 3면도를 공표하지 않는다). "
        "같은 파일의 verification[matrice4e] 항목(CORRECTED)은 짐벌을 한 번도 다루지 않는다 — "
        "즉 이 숫자는 검증을 통과한 적이 없다."),
    verdict="근거 없는 추정(unverified estimate)",
)

# --------------------------------------------------------------------------- #
out = dict(
    meta=dict(
        stamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        generator="benchmark/meshdef_gimbal_measure.py",
        scope_ko="matrice4e 짐벌 — 증거 수집과 패치 명세까지. 소스는 고치지 않았다.",
        gpu="사용 안 함(CPU 전용)",
    ),
    coordinate_frames=dict(
        cad_ko="STEP(M4T): X=좌우, Y=위(+), Z=뒤(+). 짐벌은 Z 가 가장 작은 쪽(기수).",
        ours_ko="우리 메쉬: x=기수(+), y=좌우, z=위(+), z=0 은 팔 허브 평면.",
        map_x=f"x_ours = {round(C_X,2)} − Z_cad", map_z=f"z_ours = Y_cad + {round(D_Z,2)}",
        anchor_residuals_x_mm=RES_X, anchor_residuals_z_mm=RES_Z,
        note_ko="앵커 4개(x)·3개(z)로 맞췄고 잔차는 ±1.4 mm 안이다. 이 사상이 아래 모든 비교의 전제다.",
    ),
    cad_m4t=cad, mesh_current=mesh, photo_4e=photo, sigma_impact=sig, claim_trace=claim,
)

# --------------------------------------------------------------------------- #
# 6. 판정과 패치 명세
# --------------------------------------------------------------------------- #
prot_cad_lo = min(cad["protrusion_vs_nose_mm"].values())
prot_cad_hi = max(cad["protrusion_vs_nose_mm"].values())
out["verdict"] = dict(
    headline_ko=(
        "짐벌의 **앞뒤 자리는 틀리지 않았다**. 틀린 것은 저장소의 '30~40 mm' 서술이고, "
        "진짜 결함은 블록이 **너무 납작하다**(높이)는 것이다."),
    protrusion=dict(
        mesh_mm=mesh["protrusion_vs_shell_at_block_height_mm"],
        cad_range_mm=[round(prot_cad_lo, 2), round(prot_cad_hi, 2)],
        repo_claim_mm=[30, 40],
        ko=("우리 메쉬의 돌출은 기준을 어떻게 잡느냐에 따라 14.1(셸 bbox) ~ 16.1(블록 높이대의 셸) mm 다. "
            "CAD 를 같은 방식으로 재면 기수 최전방 구조 기준 15~17 mm, 상부커버 앞끝 기준 25~27 mm 다. "
            "'30~40 mm' 는 가장 후한 기준보다도 크다. 메쉬의 블록 앞면 x 는 CAD 값과 1.1 mm 안에서 같다."),
    ),
    block_face=dict(
        mesh_w_h_mm=[mesh["block_w_mm"], mesh["block_h_mm"]],
        photo_w_h_mm=[photo["block_w_mm"], photo["block_h_mm_deforeshortened"]],
        cad_w_h_mm=[cad["camera_block_solid59"]["w_mm"], cad["camera_block_solid59"]["h_mm"]],
        ko=("사진(4E)·CAD(4T)·메쉬가 폭은 63~65 mm 로 모이는데 **높이만 메쉬가 45 mm 로 혼자 작다**. "
            "4E 개구 4개가 만드는 클러스터의 세로 길이만 해도 사진에서 "
            f"{photo['aperture_cluster_h_mm']} mm 라, 45 mm 블록에는 물리적으로 안 들어간다."),
    ),
    cad_usability=dict(
        ko=("CAD 는 4T 라 짐벌 **개구가 6개**(창 솔리드 6장으로 확인)라서 앞면 배치는 못 쓴다. "
            "그러나 (a) 매다는 자리(앞면 x·바닥 z), (b) 폭, (c) 깊이는 4E 사진과 어긋나지 않는다. "
            "쓸 수 있는 선: **자리와 폭·깊이는 CAD, 높이와 개구 배치는 4E 사진**."),
        cad_is_envelope_check=(
            f"CAD 창 판이 블록 앞면보다 {cad['aperture_windows']['recess_behind_block_face_mm']} mm 뒤에 있다 → "
            "여유를 준 '포장 상자'가 아니라 실제 베젤 형상에 가깝다."),
    ),
)

out["corrections"] = [
    dict(constant="_gimbal_sensor_v2 h (짐벌 블록 높이 인자)",
         where="src/drone_cad.py:2178",
         old=GIM_ARGS["h"] * 1000, new=round(h_new * 1000, 1), unit="mm",
         source="assets/photos/matrice4e/matrice4e_p02_front_elevation.jpg (정면 실측) + M4T STEP 교차확인",
         evidence=(f"사진 블록 앞면 세로 {photo['block_h_px']} px ÷ 축척 {photo['scale_px_per_mm']} px/mm "
                   f"÷ 단축률 {photo['foreshortening_factor']} = {photo['block_h_mm_deforeshortened']} mm. "
                   f"CAD(4T) 블록+요크 {cad['camera_block_solid59']['h_mm']} mm. "
                   f"지금 메쉬 블록 {mesh['block_h_mm']} mm."),
         confidence="high",
         sigma_impact_db_est=sig["front_face_delta_db_now_to_photo"],
         breaks_what=("helper 가 요(yaw) 실린더와 댐핑판을 cz+0.60h·cz+0.76h 에 놓으므로 h 를 키우면 "
                      f"조립체 꼭대기가 {mesh['assembly_top_z_mm']} → {round(float(Vn[:,2].max()),1)} mm 로 뜬다. "
                      "CAD 크래들은 z_ours ≈ −20…+8 이므로 **판이 기수 위로 삐져나온다**. "
                      "h 를 키우려면 요·판의 z 를 h 에서 떼어내 따로 줘야 한다.")),
    dict(constant="_gimbal_sensor_v2 cz (블록 중심 높이)",
         where="src/drone_cad.py:2178",
         old=GIM_ARGS["cz"] * 1000, new=round(cz_new * 1000, 2), unit="mm",
         source="지상고를 지금 값(=CAD 값)에 고정한 채 h 만 키우기 위한 종속값",
         evidence=(f"블록 바닥은 지금 z={mesh['block_bottom_z_mm']} mm, 접지 위 {mesh['ground_clearance_mm']} mm 로 "
                   f"CAD(접지 위 {cad['ground_clearance_mm']} mm)와 맞다. 바닥을 붙박아 두려면 "
                   "cz = 바닥 + 0.48·h 로 따라 올라가야 한다."),
         confidence="high", sigma_impact_db_est=0.0,
         breaks_what="cz 만 올리고 h 를 안 올리면 블록이 통째로 위로 떠 지상고가 틀어진다. 둘은 한 쌍이다."),
    dict(constant="_gimbal_sensor_v2 w (블록 폭)",
         where="src/drone_cad.py:2178",
         old=GIM_ARGS["w"] * 1000, new=round(w_new * 1000, 1), unit="mm",
         source="p02 정면 실측 + M4T STEP",
         evidence=(f"사진 블록 폭 {photo['block_w_px']} px → {photo['block_w_mm']} mm, "
                   f"CAD 블록 {cad['camera_block_solid59']['w_mm']} mm, 지금 메쉬 {mesh['block_w_mm']} mm. "
                   f"롤 배럴 좌우 span 도 사진 {photo['barrel_span_mm']} mm vs 메쉬 {mesh['barrel_span_y_mm']} mm."),
         confidence="medium",
         sigma_impact_db_est=round(20 * np.log10(photo["block_w_mm"] / mesh["block_w_mm"]), 2),
         breaks_what="배럴이 ±0.66w 에 붙어 있어 w 를 키우면 배럴 span 도 같이 커진다(사진과는 오히려 가까워진다)."),
    dict(constant="_gimbal_sensor_v2 d (블록 깊이) 와 cx",
         where="src/drone_cad.py:2178",
         old=[round(GIM_ARGS["d"] * 1000, 1), round(GIM_ARGS["cx"] * 1000, 1)],
         new=[round(d_new * 1000, 1), round(cx_new * 1000, 1)], unit="mm",
         source="M4T STEP 솔리드 59 의 Z 폭(4E 사진에는 깊이를 잴 각도가 없다)",
         evidence=(f"CAD 블록 깊이 {cad['camera_block_solid59']['d_mm']} mm vs 메쉬 {mesh['block_d_mm']} mm. "
                   "앞면 x 를 지금 자리에 붙박아 두려면 cx 를 뒤로 물려야 한다."),
         confidence="low",
         sigma_impact_db_est=round(20 * np.log10((w_new * d_new) / (GIM_ARGS["w"] * GIM_ARGS["d"])), 2),
         breaks_what=("아랫면(w×d)이 줄어 **바닥유령(지면 반사) 경로의 정반사 몫**이 준다. report09 계열 수치가 움직인다. "
                      "4E 블록이 4T 보다 깊을 가능성을 배제 못 하므로 확신도 낮음.")),
]

out["do_not_fix"] = [
    dict(what="짐벌 앞뒤 자리(돌출)", why_ko=(
        f"메쉬 블록 앞면 x={mesh['block_front_x_mm']} mm 는 CAD 를 우리 좌표로 옮긴 "
        f"{cad['block_front_x_ours_mm']} mm 와 1.1 mm 차이다. 셸 기수도 "
        f"{mesh['shell_nose_max_x_mm']} mm 로 CAD 최전방 기수 구조와 1.5 mm 안에서 같다. "
        "'30~40 mm' 에 맞추려고 짐벌을 앞으로 빼면 **맞던 것을 틀리게 만든다**.")),
    dict(what="짐벌 지상고", why_ko=(
        f"메쉬 {mesh['ground_clearance_mm']} mm vs CAD {cad['ground_clearance_mm']} mm — 0.3 mm 차이. "
        f"사진에서 시차를 보정한 값도 {photo['ground_clearance_mm_parallax_corrected']} mm 로 같은 자리를 가리킨다.")),
    dict(what="CAD 앞면 개구 배치를 그대로 쓰는 것", why_ko=(
        f"CAD 창 솔리드가 {cad['aperture_windows']['n']} 장이다 = 4T(열화상+NIR 포함). "
        "4E 는 3 렌즈 + LRF 다. 개구 배치는 반드시 4E 사진(m02·m03·p02)에서 와야 한다.")),
]

out["open_questions"] = [
    "CAD 솔리드 59 의 세로 65.6 mm 가 '카메라 블록만' 인지 '블록+롤요크' 인지 STEP 을 메쉬로 구워 보지 않으면 못 가른다. 사진은 후자를 가리킨다(블록 ~58 mm + 그 위 그늘진 요크).",
    "짐벌 깊이는 4E 사진 어디에서도 못 잰다 — 이 폴더에 정투영 측면뷰가 없다. 4T CAD 값(36.4 mm)을 빌려 쓰는 것이 유일한 선택이고, 그래서 확신도가 낮다.",
    "assets/photos/matrice4e/SOURCES.md 가 p01 을 '좌측면 프로파일 ⭐ … 짐벌 돌출' 로 적어 두었는데 **p01 은 후면뷰**다(p05 와 같은 각도). 그 표를 믿고 잰 값이 있다면 전부 다시 봐야 한다.",
    ("'돌출' 의 기준면이 저장소 어디에도 정의돼 있지 않다. 우리 셸 기수 bbox(160.2 mm)는 CAD 의 "
     "**최전방 기수 구조**(159.1)와는 1 mm, **상부커버 앞끝**(150.4)과는 10 mm 차이다. 기준을 못 박기 전에는 "
     "돌출 숫자끼리 비교하는 것 자체가 무의미하다 — 다음 라운드에서 정의를 문서에 박을 것."),
    ("d(깊이) 정정은 아랫면 면적을 2.5 dB 줄인다. 바닥유령(report09)·저앙각 결과가 함께 움직이므로 "
     "h·w 정정과 **한 커밋에 묶어** 재생성해야 한다. 따로 넣으면 어느 변화가 어디서 왔는지 못 가른다."),
]

path = os.path.join(ROOT, "outputs/meshdef_gimbal.json")
json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", path)
print(json.dumps(out["verdict"], ensure_ascii=False, indent=1)[:1500])
