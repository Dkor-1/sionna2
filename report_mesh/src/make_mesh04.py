# -*- coding: utf-8 -*-
"""make_mesh04.py — mesh04 ipynb 생성기. ⚠ 이 파일이 소스다.

mesh04 — "몸체 만들기 — 스펙 숫자가 드론 모양이 되기까지"
  DroneSpec(공식 숫자) → build_frame_cad(조립) → envelope fit(공식 외형 맞춤) →
  드론별 개성(Mini vs Phantom) → 좌우대칭 검증(B_symmetry).
배정 그림: wireframe_mini5pro.png, wireframe_phantom4.png
모든 수치는 outputs/mesh_verify.json + src/drones.py 의 DRONES 에서 읽어 f-string 주입.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RM = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(RM, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

V = json.load(open(os.path.join(RM, "outputs", "mesh_verify.json"), encoding="utf-8"))
from drones import DRONES  # noqa: E402  (스펙의 단일 진리원)

from mesh_ledger import ledger_order   # noqa: E402  (원장↔레지스트리 일치 강제)
KEYS = ledger_order(V)                     # = DRONES 레지스트리 전수
A, B, C = V["A_geometry"], V["B_symmetry"], V["C_dims"]
NAME = {k: DRONES[k].name for k in KEYS}

from drones import drone_label  # noqa: E402
sys.path.insert(0, HERE)
import mesh_facts_0816 as MF  # noqa: E402  (2026-08-16 원장 공용 로더)

# --------------------------------------------------------------------------- #
#  ⭐ §2·§2.1 의 «어느 함수가 어느 기종을 짓나» 는 **추적해서 얻는다**
#
#  왜: 이 표를 손으로 유지하면 곧바로 낡는다. `drone_cad` 의 조립 분기는 스펙 필드
#  (`gear`)로 갈리는 곳도 있고 **기종 키**로 갈리는 곳도 있어서 스펙만 봐서는 알 수 없다.
#  그래서 생성 시점에 `build_frame_cad` 를 10종 전부 돌리되, 조립 헬퍼를 감싸 **실제로
#  불린 함수**를 기록한다(약 6초). 소스 줄 번호도 `inspect` 로 읽는다 — 손으로 안 적는다.
#  ⛔ 감싸기는 이 생성기 프로세스 안에서만 일어나고 저장소 코드는 건드리지 않는다.
# --------------------------------------------------------------------------- #
import functools  # noqa: E402
import inspect    # noqa: E402
import drone_cad as _DC  # noqa: E402
import cadkit as _CK     # noqa: E402


def LN(fn_name: str, mod=None) -> int:
    """`drone_cad`(기본) 안 함수의 **현재** 정의 줄 번호."""
    mod = mod or _DC
    return inspect.getsourcelines(getattr(mod, fn_name))[1]


def SRC(fn_name: str, mod=None) -> str:
    """`src/<모듈>.py:<줄>` 표기 — 인용문에 그대로 넣는다."""
    mod = mod or _DC
    return f"src/{mod.__name__}.py:{LN(fn_name, mod)}"


def _trace_builders():
    """기종 → 실제로 불린 조립 헬퍼 이름 집합. (원본 함수는 끝나면 되돌린다)"""
    names = [n for n in dir(_DC)
             if n.startswith(("_body", "_arm", "_gimbal", "_gear", "_motor_bell",
                              "_deck", "_rtk", "_fisheye", "_lidar", "_nose"))
             and callable(getattr(_DC, n))]
    seen, orig = {}, {n: getattr(_DC, n) for n in names}

    def wrap(name, fn):
        @functools.wraps(fn)
        def w(*a, **k):
            seen.setdefault(name, 0)
            seen[name] += 1
            return fn(*a, **k)
        return w

    for n in names:
        setattr(_DC, n, wrap(n, orig[n]))
    used = {}
    try:
        for k in KEYS:
            seen.clear()
            _DC.build_frame_cad(DRONES[k])
            used[k] = dict(seen)
    finally:
        for n in names:
            setattr(_DC, n, orig[n])
    return used


USED = _trace_builders()

#  짐벌 검사기 게이트 A/B/C — 원장에서 그대로 읽는다(손숫자 금지).
_GSUM = MF.GIMBAL["_summary"]
_GA = _GSUM["gate_A_fail"][0]
_GC = _GSUM["gate_C_over_declared"]
_GB_FLOAT = sorted({x["drone"] for x in _GSUM["gate_B_floating"]}, key=KEYS.index)
_GB_SWAL = sorted({x["drone"] for x in _GSUM["gate_B_swallowed"]}, key=KEYS.index)

#  셸 형상표(초타원 지수·코 처짐) — 값은 `drone_cad._SHELL_SHAPE` 에서 읽는다(손숫자 금지).
SHELL_NPOW_ROWS = ["| 기체 | 초타원 지수 n | 코 처짐 |", "|---|---|---|"] + [
    f"| {drone_label(k)} | {_DC._SHELL_SHAPE[k]['npow']:g} | {_DC._SHELL_SHAPE[k]['ndrop']:g} |"
    for k in KEYS if k in getattr(_DC, "_SHELL_SHAPE", {})
]


def users_of(*fn_names, label=True):
    """그 함수를 **실제로 부르는** 기종의 표시명 — 없으면 '(해당 기종 없음)'."""
    who = [drone_label(k) if label else k
           for k in KEYS if any(f in USED[k] for f in fn_names)]
    return "·".join(who) if who else "(해당 기종 없음)"


def _no_gimbal_users():
    """조립에서 카메라 부품을 하나도 안 붙이는 기종."""
    who = [drone_label(k) for k in KEYS
           if not any(n.startswith("_gimbal") for n in USED[k])
           and DRONES[k].gimbal_style in (None, "none")]
    return "·".join(who) if who else "(해당 기종 없음)"

# ---- 생성기에서 미리 계산해 두는 값(전부 JSON/DRONES 출처) ----------------------
mini, ph, mav = DRONES["mini5pro"], DRONES["phantom4"], DRONES["mavic4pro"]
worst_key = max(KEYS, key=lambda k: C[k]["worst_err_pct"])
worst_pct = C[worst_key]["worst_err_pct"]                       # 크기(부호 없음)
_wd = C[worst_key]["checks"].get("diagonal")                   # 최악은 대각(종속값) — 부호 살리기
worst_diag_signed = ((_wd["measured"] - _wd["official"]) / _wd["official"] * 100
                     if _wd and _wd.get("official") else -worst_pct)

#  ⚠ 2026-07-30 (Phase 3): 아래 두 값이 산문에 **손타이핑**돼 있었다 — 프롭 오차 "+0.84%"
#     (블레이드 대공사로 스윕디스크 정규화가 들어간 뒤 낡았다)와 s1000plus 면내 배율
#     "(0.999, 0.999)". 원장에서 읽는다.
_prop_errs = [C[k]["checks"]["prop_dia"]["err_pct"] for k in KEYS
              if "prop_dia" in C[k]["checks"]]
_prop_err_txt = (f"{min(_prop_errs):+.2f}~{max(_prop_errs):+.2f}%" if _prop_errs else "(원장에 없음)")
_s1000_fs = C["s1000plus"]["fit_scale"]
sym_p95 = {k: B[k]["frame_only"]["chamfer_mm"]["p95"] for k in KEYS}
sym_worst_key = max(sym_p95, key=sym_p95.get)
full_p95 = {k: B[k]["full"]["chamfer_mm"]["p95"] for k in KEYS}
mav_fs = C["mavic4pro"]["fit_scale"]  # §3.1 본문에서 표와 같은 출처로 인용

#  ⚠ 2026-08-16 (적대검증): §5 의 로터 배치 서술이 손타이핑된 각도(123.7/236.3)를 쓰면서
#     «마주보는 쌍이 정확히 180°» 라고 적고 있었다 — mini5pro 의 실제 값은 사다리꼴이라
#     그 문장이 거짓이다. 아래 값을 스펙에서 직접 계산해 주입한다.
_m5 = tuple(float(a) for a in mini.rotor_deg)
_m5_opp = abs(((_m5[2] - _m5[0]) + 180.0) % 360.0 - 180.0)          # 마주보는 쌍의 실제 사잇각
_m5_wb = None
for _f in MF.BODY.get("findings", []):                              # B12 = 사다리꼴 선언
    if _f.get("id") == "B12":
        _m5_wb = float(_f["evidence"]["wheelbase_mm"])
if _m5_wb is None:                                                  # 원장이 바뀌면 조용히 넘기지 말 것
    raise SystemExit("mesh04: body_arms 원장에 B12(mini5pro 축간거리)가 없다 — 서술을 고쳐야 한다")
#  §1b 의 스캔 chamfer 도 손타이핑(5.3 mm)이었다 — 원장에서 읽는다.
_scan_p50 = V["G_scan"]["scan_to_cad_mm"]["p50"]


def _dim_cell(k, name):
    """C_dims 의 한 항목을 '공식→실측 (오차%)' 문자열로. 없으면 공식값이 없다는 뜻."""
    chk = C[k]["checks"].get(name)
    if chk is None:
        return "— (공식값 없음)"
    return f"{chk['official']:.1f} → {chk['measured']:.1f} ({chk['err_pct']:+.2f}%)"


cdims_rows = []
for k in KEYS:
    fs = C[k]["fit_scale"]
    cdims_rows.append(
        f"| {NAME[k]} | {_dim_cell(k,'L')} | {_dim_cell(k,'W')} | {_dim_cell(k,'H')} | "
        f"{_dim_cell(k,'diagonal')} | {_dim_cell(k,'prop_dia')} | "
        f"**{C[k]['worst_err_pct']:.2f}%** | ({fs[0]:.3f}, {fs[1]:.3f}, {fs[2]:.3f}) |")
CDIMS_TABLE = "\n".join(cdims_rows)

sym_rows = []
for k in KEYS:
    fo = B[k]["frame_only"]["chamfer_mm"]
    fu = B[k]["full"]["chamfer_mm"]
    ok = "PASS" if fo["p95"] <= 2.0 else "FAIL"
    sym_rows.append(
        f"| {NAME[k]} | {B[k]['frame_only']['n_points']:,} | {fo['p50']:.2f} | {fo['p95']:.2f} | "
        f"{fo['max']:.2f} | {fu['p95']:.1f} | {ok} |")
SYM_TABLE = "\n".join(sym_rows)


def md(*lines):
    src = "\n".join(lines).splitlines(keepends=True)
    return {"cell_type": "markdown", "metadata": {}, "source": src or [""]}


def code(*lines):
    src = "\n".join(lines).splitlines(keepends=True)
    return {"cell_type": "code", "metadata": {}, "source": src or [""],
            "outputs": [], "execution_count": None}


cells = [

# ── 1. 제목 + 경고 + 요약 + 용어풀이 ─────────────────────────────────────────────
md(
"# mesh04 — 몸체 만들기: 스펙 숫자가 드론 모양이 되기까지",
"",
*MF.head_md(
    "mesh04",
    "공표 제원의 숫자가 어떤 순서로 드론 형상이 되는가 — 그리고 그 과정에서 "
    "형상이 «어디서 정확하고 어디서 대가를 치르는가».",
    ["verify", "body_arms", "gimbal", "meshfix_m4e", "audit"]),
"",
f"**한 줄 요약** — DJI 공식 제원 숫자(대각거리·외형 L×W×H·프로펠러 지름)를 담은 `DroneSpec`",
f"데이터클래스에서 출발해, 로프트·스윕·회전체·불리언으로 드론 {len(KEYS)}종의 몸체(프레임)를 조립하고,",
f"마지막에 공식 외형에 자동 스케일(envelope fit)해서 **치수 최악 오차 {worst_pct:.2f}%**",
f"({NAME[worst_key]}), **좌우대칭 p95 ≤ 2 mm**(전 기종)를 달성하는 과정을 소스코드를 따라가며 설명한다.",
"",
"| 용어 | 뜻 |",
"|---|---|",
"| 메쉬(mesh) | 3D 표면을 작은 삼각형 조각들로 표현한 것. 전파 시뮬레이터가 먹는 형식 |",
"| 데이터클래스(dataclass) | '필드(변수)만 모아둔 파이썬 클래스'. 스펙 표를 코드로 옮긴 것 |",
"| 대각거리(diagonal, 휠베이스) | 마주보는 두 모터 축 사이 거리. 드론 크기의 대표 숫자 |",
"| 외형(envelope) | 암 펼침·**프로펠러 제외** 상태의 L×W×H 바운딩박스. DJI 공식 스펙 항목 |",
"| 바운딩박스(bounding box) | 물체를 꼭 맞게 감싸는 축 정렬 직육면체 |",
"| 로프트(loft) | 단면(고리)들을 순서대로 이어 붙여 곡면을 만드는 기법. 조선소에서 배 만들던 방식 |",
"| 초타원(superellipse) | 타원과 직사각형의 중간 곡선. 지수 n=2 면 타원, n 이 클수록 모서리 둥근 사각 |",
"| 스윕(sweep) | 경로(곡선)를 따라 단면을 밀어서 튜브 모양을 만드는 기법 |",
"| 회전체(revolve) | 옆모습 프로파일을 축 둘레로 한 바퀴 돌려 만든 형상. 도자기 물레와 같다 |",
"| 베지에 곡선(Bézier) | 제어점 몇 개로 정의되는 매끈한 곡선. 암의 휘어짐에 사용 |",
"| 불리언 합집합(boolean union) | 겹쳐 놓은 입체들을 하나로 녹여 **속에 파묻힌 면을 제거**하는 연산 |",
"| watertight | 구멍 없이 완전히 닫힌 표면('물을 부어도 안 새는'). 부피·법선 검증의 전제 |",
"| 짐벌(gimbal) | 기체가 흔들려도 카메라를 수평으로 유지해 주는 회전 마운트 |",
"| 챔퍼 거리(chamfer distance) | 두 점 구름 사이 '가장 가까운 짝' 거리의 통계. 대칭성 측정에 사용 |",
),

# ── 2. §0 개요 ────────────────────────────────────────────────────────────────
md(
"## §0. 이 리포트의 위치 — 왜 몸체를 '직접' 만드나",
"",
"mesh01~03 에서 파이프라인 전체 지도, 원본 스펙 조사, 다운로드/스캔 모델 대조를 다뤘다.",
"이번 편은 그 스펙 숫자가 **몸체(프레임 = 프로펠러를 제외한 모든 부위)** 메쉬가 되는 과정이다.",
"프로펠러(익형 블레이드)는 다음 편에서 따로 다룬다.",
"",
"인터넷에서 받은 3D 모델을 쓰지 않고 **파라메트릭 CAD**(숫자를 넣으면 모양이 나오는 코드)로",
"직접 만드는 이유는 소스코드 머리말에 적혀 있다:",
"",
"> \"RCS 는 **외형(투영면적)과 재질 분포**가 결정한다. 실루엣이 틀리면 σ 가 틀린다.\"",
"> ← 출처: src/drone_cad.py 모듈 docstring",
"",
"다운로드 모델은 (1) 치수가 공식 스펙과 얼마나 다른지 알 수 없고, (2) 부위별 재질 라벨(어디가",
"금속이고 어디가 플라스틱인지)이 없고, (3) 라이선스가 제각각이다(← 출처:",
"assets/meshes/reference/SOURCES.md — 다운로드 모델은 '대조용'으로만 쓴다).",
"파라메트릭이면 **모든 치수가 스펙에서 유도**되고, 부위마다 그룹 이름이 붙어 재질을 정확히 배정할 수 있다.",
"",
"도구는 `trimesh`(메쉬 컨테이너·검증) + `manifold3d`(불리언 엔진) + `shapely`(2D 단면 폴리곤)",
"+ `scipy`(스플라인 보간)다. 왜 이 조합인가 — 드론 형상에는 로프트·스윕·불리언·스무딩과",
"watertight/법선 검증이 전부 필요한데, 이를 검증된 라이브러리에 맡기는 것이 `cadkit.py` 의",
"설계다(← 출처: src/cadkit.py '무엇을 쓰나·핵심 규약'). 프로젝트 자체 모듈 geom.py 는",
"드론 제작 도구가 아니라 **Mesh 컨테이너(꼭짓점 v·면 f·그룹 g) + 챔버·범용 프리미티브**",
"(box/cylinder/uv_sphere/pyramid_field 등) 담당이고, cadkit 의 `Assembly` 가 조립 결과를 마지막에",
"geom.Mesh 로 변환해 기존 파이프라인에 넘긴다(← src/cadkit.py to_geom docstring).",
"",
"조립 흐름 한 눈에:",
"",
"```",
"DroneSpec(공식 숫자, src/drones.py)          §1",
"   → build_frame_cad(부위 조립, src/drone_cad.py)   §2",
"   → 불리언 합집합(내부 면 제거, src/drone_cad.py)   §2",
"   → frame_fit_scale(공식 외형 맞춤, src/drones.py)  §3",
"   → 검증: C_dims(치수)·B_symmetry(대칭)                §3·§5",
"```",
),

# ── 3. code: 준비 ─────────────────────────────────────────────────────────────
code(
"# 준비 — 검증 JSON 과 스펙 원본을 읽는다 (노트북은 report_mesh/ 에서 실행된다고 가정)",
"import json, os, sys",
"sys.path.insert(0, os.path.abspath('../src'))          # 저장소 src/ — 스펙의 단일 진리원",
"V = json.load(open('outputs/mesh_verify.json', encoding='utf-8'))   # 측정치는 전부 여기서",
"from drones import DRONES, DroneSpec                   # ← src/drones.py (DroneSpec 정의)",
"",
"print('메쉬 엔진 :', V['meta']['mesh_engine'])",
"print('검증 주파수:', V['meta']['fc_ghz'], 'GHz')",
"print()",
"for k in V['meta']['drones']:",
"    s = DRONES[k]",
"    print(f'{k:10s} {s.name:16s} 대각 {s.diagonal_mm:6.1f} mm · 로터 {s.num_rotors} · '",
"          f'프롭 {s.prop_dia_mm:5.1f} mm · {s.weight_g:.0f} g')",
),

# ── 4. §1 DroneSpec 두 부류 ───────────────────────────────────────────────────
md(
"## §1. DroneSpec — '공식 숫자'와 '외형 파라미터'는 다른 신분이다",
"",
"`DroneSpec`(src/drones.py)은 드론 한 종의 모든 정보를 담는 데이터클래스인데,",
"필드가 **두 부류**로 나뉜다. 이 구분이 이 시리즈 전체의 정직성 장치다:",
"",
"**(a) 실측 제원 — 웹 조사 + 독립 교차검증을 거친 숫자** (틀리면 안 되는 값)",
"",
"| 필드 | 뜻 | Mini 5 Pro | Phantom 4 | 출처 |",
"|---|---|---|---|---|",
f"| `diagonal_mm` | 모터-모터 대각거리 | {mini.diagonal_mm:.0f} (추정, §1.1) | {ph.diagonal_mm:.0f} (공식) | docs/SPECS.md·dji.com/phantom-4/info |",
f"| `weight_g` | 이륙중량 | {mini.weight_g:g} | {ph.weight_g:g} | docs/SPECS.md·dji.com/mini-5-pro/specs |",
f"| `prop_dia_mm` | 프로펠러 지름 | {mini.prop_dia_mm:g} (DJI 6028F) | {ph.prop_dia_mm:g} (DJI 9450) | docs/SPECS.md·support.dji.com |",
f"| `prop_blades`/`num_rotors` | 날개 수/로터 수 | {mini.prop_blades}/{mini.num_rotors} | {ph.prop_blades}/{ph.num_rotors} | docs/SPECS.md |",
f"| `envelope_mm` | 공식 외형 L×W×H(프롭 제외) | (None, None, {mini.envelope_mm[2]:g}) — 높이만 공식 | {ph.envelope_mm} | DJI 공식(§1.1)·src/drones.py,173 |",
"",
"**(b) 외형 스타일 — 사진·3면도에서 눈으로 맞춘 렌더 파라미터** (실루엣 담당, 공식 스펙 아님)",
"",
"| 필드 | 뜻 | Mini 5 Pro | Phantom 4 |",
"|---|---|---|---|",
f"| `body_lw` | 동체 (길이,폭)/허브 비 — 접이식 슬림기는 길쭉·좁게 | {mini.body_lw} | {ph.body_lw} |",
f"| `rotor_deg` | 모터 각도 배치[deg] | {mini.rotor_deg} | {ph.rotor_deg} (X자 기본) |",
f"| `rotor_z_mm` | 로터별 높이 오프셋[mm] | {mini.rotor_z_mm} | 없음(전부 같은 높이) |",
f"| `gimbal_style` | 짐벌 형태(§2) | {mini.gimbal_style!r} | {ph.gimbal_style!r} |",
f"| `gear` | 착륙장치(§2) | {mini.gear!r}(없음) | {ph.gear!r}(스키드 다리) |",
f"| `fixed_arm` | 고정암 여부 | {mini.fixed_arm} (접이식) | {ph.fixed_arm} (고정암) |",
f"| `body_frac` | 동체 크기/대각 비 | {mini.body_frac} | {ph.body_frac} |",
"",
"← 출처: 필드 정의와 주석 src/drones.py, 값은 src/drones.py(mini5pro)·163-173(phantom4)",
"",
"왜 나눴나 — (a)는 **RCS·마이크로도플러 물리에 직접 들어가는 값**이라 출처와 신뢰도(confidence)를",
"달고 관리하고, (b)는 실루엣(그럴듯한 겉모습)만 담당해서 사진과 눈대중으로 조정해도 되는 값이기",
"때문이다. 섞어 두면 '어느 숫자가 검증된 것인지' 나중에 알 수 없게 된다.",
),

# ── 5. §1.1 추정값 정직 공개 ──────────────────────────────────────────────────
md(
"### §1.1 추정값은 추정값이라고 적는다 — 세 가지 사례",
"",
"**사례 1: Mini 5 Pro 의 대각거리는 DJI 가 공개하지 않는다.**",
"스펙의 note 필드에 그대로 남겨 놨다(← 출처: src/drones.py):",
"",
f"> \"{mini.note.split('.')[0]}.\"",
"",
"조사 시점 추정 250 mm 이었는데, 공식 외형에 맞춘 뒤 로터 좌표(±76, ±114 mm ← 조사 근거,",
f"src/drones.py 주석)에서 역산하면 **{mini.diagonal_mm:.0f} mm** 가 된다. 심지어 언폴드 L×W",
"조차 '프롭 제외' 값은 비공개다 — DJI 가 공개한 것은 폴디드 157×95×68 과 언폴드(**프롭 포함**)",
f"304×380×91 뿐이라, envelope 은 **높이 {mini.envelope_mm[2]:g} mm 만** 강제하고 L/W 는 로터",
"배치가 정하게 뒀다(← 출처: src/drones.py 주석, docs/SPECS.md Mini 5 Pro 검증 절).",
"",
"**사례 2: Mavic 4 Pro 는 추정 대각과 공식 외형이 서로 모순이었다.**",
"추정 400 mm 로는 공식 외형 328.7×390.5 mm 를 기하학적으로 만들 수 없다(대각 400 짜리 사각형은",
f"이 외형보다 작다). 그래서 **공식 외형이 이기고**, 대각은 외형에서 유도한 {mav.diagonal_mm:.1f} mm 로",
"갱신했다(← 출처: src/drones.py note — \"The envelope (official) wins; diagonal_mm is",
"kept only as an arm/motor thickness scale\").",
"",
f"**사례 3: Phantom 4 는 대각 {ph.diagonal_mm:.0f} mm 가 진짜 공식이다.** 외형",
f"{ph.envelope_mm[0]:g}×{ph.envelope_mm[1]:g}×{ph.envelope_mm[2]:g} mm 는 DJI Quick Start Guide",
"v1.2(프롭 제외)에서 왔다(← 출처: src/drones.py 주석, docs/SPECS.md Phantom 4 절·",
"fullcompass.com 공식 스펙시트 PDF).",
"",
"이렇게 '어느 숫자가 공식이고 어느 숫자가 추정인지'를 필드 단위로 기록해 두면, §3 의 자동 맞춤이",
"**무엇을 기준으로 삼아야 하는지**(공식 외형 > 추정 대각)가 코드에서 결정 가능해진다.",
),

# ── 6. code: 전 기종 스펙 표 ──────────────────────────────────────────────────
code(
"# 전 기종의 '공식 숫자' 필드 — 값은 전부 src/drones.py 의 DRONES 에서 읽는다",
"print(f\"{'key':10s} {'이름':16s} {'대각[mm]':>8s} {'외형 L×W×H [mm]':>22s} {'프롭[mm]':>8s} {'로터':>4s} {'신뢰도':>6s}\")",
"for k in V['meta']['drones']:",
"    s = DRONES[k]",
"    env = ('×'.join('?' if e is None else f'{e:g}' for e in s.envelope_mm)",
"           if s.envelope_mm else '(없음)')",
"    print(f'{k:10s} {s.name:16s} {s.diagonal_mm:8.1f} {env:>22s} '",
"          f'{s.prop_dia_mm:8.1f} {s.num_rotors:4d} {s.confidence:>6s}')",
"print()",
"print('note(주의 문구) 첫 문장 — 추정/모순이 있으면 여기 적혀 있다:')",
"for k in V['meta']['drones']:",
"    print(f'  {k:10s}:', DRONES[k].note.split('. ')[0][:110])",
),

# ── 6b. §1b 닮음의 출처 (청중 질문 반영: "사진을 가져와 만든 건가?") ─────────────
md(
"## §1b. 닮음은 어디서 오나 — 사진을 베끼지 않고 닮게 만드는 법",
"",
"완성된 메쉬가 실물과 닮아 보여서 자주 받는 질문: **\"3D 모델을 가져와서 스펙에 맞게 고친 건가?\"** "
"— 아니다. **어떤 외부 3D 메쉬도 기하로 가져오지 않았다.** 다만 «전부 스펙에서 나왔다» 도 정확한 "
"말이 아니다. 닮음은 **네 층**이 쌓여 만들어지고, 층마다 근거의 성격이 다르다:",
"",
"| 층 | 무엇이 | 어떻게 닮음을 만드나 | ← 출처 |",
"|---|---|---|---|",
"| **① 공표 치수** | 대각·언폴드 L×W×H·프롭 지름 | 크기·비율·로터 배치를 **숫자로 강제** — "
"비율이 정확하면 실루엣의 절반은 이미 맞는다. 빌드 끝에 `frame_fit_scale` 이 외형을 공식 envelope 에 "
"맞춘다(§3) | 제조사 공식 스펙 → `docs/SPECS.md`(URL 포함) → `DroneSpec` |",
"| **② 형태 관찰** | 제품 사진·공식 소개에서 **사람이 뽑은 형태 특징** | \"마빅=눈물방울 동체+등 "
"배터리+렌즈 3개 짐벌\", \"팬텀=고정암+착륙다리\", \"미니=앞뒤 로터 높이 차\" 같은 관찰을 **코드 "
"파라미터로 번역**(`gimbal_style`·`gear`·`rotor_deg`·`body_lw`…) | `docs/SPECS.md` 의 기체별 "
"'착륙장치/짐벌/색상' 항목 → `src/drone_cad.py` 기종별 분기 주석 |",
"| **③ 사진 계측** ⭐ | 공표 숫자가 **안 정하는** 치수(셸 비율·암 폭·다리 길이·짐벌 크기) "
"| 사진 안에서 길이를 아는 것 하나로 mm/px 축척을 잡고 **픽셀로 잰다.** 값마다 밴드(대개 ±15 %)와 "
"픽셀 근거를 함께 남긴다 | `assets/photos/` → `drone_cad._SHELL_SHAPE`·`_ARM_WIDTH`·`_ARM_SECTION`, "
"`src/drones.py` note (자세히는 mesh03 §1.5) |",
"| **④ 실물 CAD** | 공식 CAD 가 있는 기체의 형상 상수 | matrice4e 는 공식 STEP 로 상수 14건, "
"mini2 는 공식 GLB 로 전 상수를 **직접 실측**해 넣는다 | `outputs/meshfix_matrice4e.json` · "
"`assets/meshes/reference/` (mesh03 §3.2) |",
"| **⑤ 사후 채점** | 실기체 스캔·외부 CAD 와 **사후 대조** | 만들고 나서 닮음을 측정으로 확인 — "
f"Phantom 4 스캔점의 절반이 CAD 표면 {_scan_p50:.1f} mm 이내(→ mesh08 §3) "
"| `mesh_verify.json` G_scan · `outputs/real_cad_compare.json` |",
"",
"즉 **② 가 '어떤 특징을 만들지'를 정하고, ①③④ 가 '그 특징의 크기'를 정하고, ⑤ 가 '그래서 "
"닮았는가'를 채점**한다. ⚠ ⑤ 중에서 **제작에 한 번도 안 들어간 채점자는 실기체 스캔뿐이다** — "
"공식 CAD 는 ④ 로 제작에 들어갔으므로 같은 CAD 로 다시 재면 «독립 검증» 이 아니라 «반영 확인» 이다"
"(mesh03 §3.2·mesh08 §1.5). 외부 3D 메쉬를 가져오지 않는 이유는 mesh01 §2(라이선스·치수 미검증·"
"부위=재질 불가)에서 다뤘다.",
),

# ── 7. §2 조립 순서 (동체~모터) ───────────────────────────────────────────────
md(
"## §2. 조립 순서 — build_frame_cad 를 소스코드 따라 걷기",
"",
f"프레임 조립은 `build_frame_cad(spec)`({SRC('build_frame_cad')}) 한 함수가 담당한다.",
"",
"⚠ **«한 가지 공통 순서» 가 아니다 — 동체를 짓는 길이 셋이다.** 아래 표는 생성 시점에 10종을",
"실제로 조립하면서 **어느 함수가 불렸는지 추적해** 만든 것이다(손으로 적은 목록이 아니다):",
"",
"| 동체 경로 | 무엇인가 | 쓰는 기종 |",
"|---|---|---|",
f"| `_body_folding` + `_canopy` ({SRC('_body_folding')}) | 몰드 셸 — 초타원 단면을 길이 방향으로 "
f"로프트한 뒤 등에 캐노피를 얹는다 | {users_of('_body_folding')} |",
f"| `_body_plate_stack` ({SRC('_body_plate_stack')}) | 판 스택 — 셸이 없는 열린 프레임. 카본 상·하판 "
f"+ 스탠드오프 | {users_of('_body_plate_stack')} |",
f"| `_body_profiled` ({SRC('_body_profiled')}) | 평면형 기반 — x 가 아니라 **z 를 따라** 단면을 쌓아 "
f"위에서 본 윤곽을 먼저 정한다 | {users_of('_body_profiled')} |",
"",
f"암도 둘로 갈린다 — 접이식 스윕 `_arm_folding`({users_of('_arm_folding')}) ·"
f" 카본 튜브 `_arm_tube`({users_of('_arm_tube')}) ·"
f" 상반각 튜브 `_arm_dihedral`({users_of('_arm_dihedral')}).",
"",
"아래 1~4단계는 **몰드 셸 경로**(가장 많은 기종이 쓰는 길)를 따라 걷는다.",
"",
f"**1단계. 동체 — 초타원 단면의 로프트** (`_body_folding`, {SRC('_body_folding')})",
"",
"동체 길이 방향(x)의 6개 지점마다 반폭·반높이·중심높이를 정해 두고(코는 좁고 살짝 처지고,",
"허리에서 가장 넓고, 꼬리는 완만히 좁아진다), 스플라인으로 30개 단면으로 보간한 뒤",
f"(`spline_sections`, {SRC('spline_sections', _CK)}) 이어 붙인다(`loft`, {SRC('loft', _CK)}).",
"",
"**왜 단면이 원이 아니라 초타원인가** — 실제 드론 동체 단면은 순수 타원도 상자도 아니고 그 중간,",
"'모서리가 둥근 각진 타원'이다. 초타원의 지수 n 하나로 이 정도를 조절한다(← 출처:",
f"{SRC('superellipse', _CK)} docstring — \"실제 드론 단면은 순수 타원도 박스도 아니고 이 중간이다\").",
"지수 n 과 코 처짐은 **기종별 형상표**(`drone_cad._SHELL_SHAPE`)가 정한다 — 지금 값은:",
"",
*SHELL_NPOW_ROWS,
"",
"n 이 클수록 단면이 상자에 가깝고(모서리가 각지고), 코 처짐이 0 이면 기수가 안 숙는다.",
"이 값들은 사진·CAD 대조로 기종마다 따로 잡혔다 — 손으로 고른 «접이식 공통값» 이 아니다.",
"",
f"**2단계. 캐노피 — 등에 얹힌 배터리 돔** (`_canopy`, {SRC('_canopy')})",
"",
"실물은 배터리가 동체 등에 얹힌 낮고 평평한 돔 모양이라, 동체보다 작은 로프트를 하나 더 만들어",
"z 위로 올려 붙인다. 그룹 이름은 `canopy` — 재질 배정(플라스틱)이 그룹 단위로 따라온다.",
"",
f"**3단계. 암 — 베지에 경로의 스윕** (`_arm_folding`, {SRC('_arm_folding')})",
"",
"허브(동체 가장자리)에서 모터 위치까지 2차 베지에 곡선으로 **완만히 위로 휘는** 경로를 만들고,",
"그 경로를 따라 '둥근 직사각' 단면을 밀어(스윕) 테이퍼 튜브를 만든다. 원기둥을 꽂는 대신 스윕을",
"쓰는 이유: 실물 접이식 암은 직선 봉이 아니라 동체에서 모터로 갈수록 가늘어지며 휘는 형상이기",
"때문이다. 굵기는 대각거리에 비례시키되 고정암(Phantom)은 더 굵게 — arm_r0 = 접이식 0.055·diag",
"vs 고정암 0.085·diag. ⚠ 실측 폭이 있는 기종은 그 비례식 대신 **사진에서 잰 뿌리·끝 폭**을 쓴다"
"(`drone_cad._ARM_WIDTH`).",
"",
f"**4단계. 모터 벨 — 회전체** (`_motor_bell`, {SRC('_motor_bell')})",
"",
"(r,z) 프로파일 9개 점을 z축으로 한 바퀴 돌린 회전체다. \"아래가 잘록하고 위가 부푼 실제",
"아웃러너(outrunner: 겉통이 도는 드론 모터) 형상\"(← 해당 함수 docstring). 회전체 구현에는",
"규약이 하나 있다 — **r=0 인 점은 링이 아니라 하나의 꼭짓점(apex)으로 접는다**. 링으로 두면",
"같은 자리에 정점이 seg개 생겨 면적 0 퇴화 삼각형이 쏟아지고, 퇴화면은 법선이 정의되지 않아",
f"PO/SBR 의 조명판정(n̂·û>0)을 오염시키기 때문이다(← 출처: `revolve` {SRC('revolve', _CK)} 주석).",
),

# ── 8. §2 계속 (짐벌·착륙장치·내부 산란체·불리언) ─────────────────────────────
md(
"### §2.1 짐벌·착륙장치 분기 — 드론마다 왜 다르게 만들었나",
"",
"짐벌과 착륙장치는 **드론 실루엣의 핵심 식별 특징**이라 기종별로 함수를 나눴다.",
"착륙장치는 스펙 필드 `DroneSpec.gear` 가 분기를 정하고, **짐벌은 아직 기종 키로 갈린다.**",
"",
"⭐ 아래 두 표의 «쓰는 기종» 열은 **추적한 값**이다 — 생성 시점에 10종을 실제로 조립하면서",
"어느 함수가 불렸는지 기록했다. 줄 번호도 `inspect` 로 읽는다.",
"",
"**짐벌·카메라**",
"",
"| 함수 | 형태 | 쓰는 기종 | 왜 |",
"|---|---|---|---|",
f"| `_gimbal_hasselblad` ({LN('_gimbal_hasselblad')}행) | 넓은 3렌즈 블록 + 요크 "
f"| {users_of('_gimbal_hasselblad')} | 실물이 기수와 일직선인 **큰 전면 짐벌**(3렌즈)이라서 — "
"매달린 상자로 만들면 실루엣이 틀린다 |",
f"| `_gimbal_sensor_v2` ({LN('_gimbal_sensor_v2')}행) | 3축 마운트 + 렌즈 3 + 레이저 측거 "
f"| {users_of('_gimbal_sensor_v2')} | 측량 페이로드(카메라 클러스터 + 레이저 거리계)가 공식 "
"구성이라서 — RTK 돔도 캐노피 위에 추가된다 |",
f"| `_gimbal_compact3` ({LN('_gimbal_compact3')}행) | 좌우로 넓은 소형 3축 유닛 "
f"| {users_of('_gimbal_compact3')} | Mini 계열은 기수 함몰부에 들어앉은 컴팩트 유닛이라 "
"Phantom 류의 방진판·요 샤프트가 없다 |",
f"| `_gimbal_hanging` ({LN('_gimbal_hanging')}행) | 방진판 + 요크 + 카메라 상자 + 렌즈 "
f"| {users_of('_gimbal_hanging')} | 코 아래 **매달린** 전통 짐벌. Phantom 은 함몰(recessed)이라 "
"동체에 더 붙여 배치 |",
f"| `_gimbal_cgo3` ({LN('_gimbal_cgo3')}행) | CGO3 실물 부품 치수 그대로 "
f"| {users_of('_gimbal_cgo3')} | 실물 CAD 가 있는 기체라 부품 치수를 그대로 세운다 |",
"| (전용 조립) | 방진판 + 요 샤프트 + 카메라 블록 | Phantom 3 Professional | 매뉴얼 정투영 "
"정면도·측면도에서 부품마다 따로 실측한 값을 쓴다 — 공용 함수의 내부 비율과 안 맞았다 |",
f"| (짐벌 없음) | — | {_no_gimbal_users()} | 카메라가 아예 없는 개발 프레임. "
"`gimbal_style='none'` 으로 **선언**한다 — 선언이 없으면 조립이 예외를 던진다 |",
"",
"⚠ `_gimbal_infinity` 는 소스에 남아 있지만 **지금 함대에서 부르는 기체가 없다**(추적 결과 0종).",
"코드에 있는 함수 목록을 그대로 옮겨 적으면 «Mavic 4 Pro 가 쓴다» 처럼 틀리게 된다.",
"",
"**착륙장치**",
"",
"| 함수 | 형태 | 쓰는 기종 | 왜 |",
"|---|---|---|---|",
f"| `_gear_arch` ({LN('_gear_arch')}행) | 뒤집힌 U 자 아치 다리 2개 | {users_of('_gear_arch')} "
"| 일체형 흰 셸에 붙은 고정 착륙다리가 Phantom 정체성. 비율은 **정면사진 실측** |",
f"| `_gear_tall_tube` ({LN('_gear_tall_tube')}행) | 길게 벌어지는 카본 봉 + 스키드 바 "
f"| {users_of('_gear_tall_tube')} | 벨리 짐벌·페이로드 공간을 확보하는 긴 다리 |",
f"| `_gear_arm_spikes` ({LN('_gear_arm_spikes')}행) | 암 끝 아래로 뻗은 짧은 발 4개 "
f"| {users_of('_gear_arm_spikes')} | 전용 스키드 없이 **암 끝**으로 앉는 기종 |",
f"| `_gear_motor_legs` ({LN('_gear_motor_legs')}행) | 앞 모터 포드 밑 두 갈래 다리 2개 "
f"| {users_of('_gear_motor_legs')} | 접이식 소형기는 전용 스키드 대신 **앞쪽 모터 포드 아래에만** "
"다리가 달린다(뒤쪽 포드는 매끈하다) — 제품사진 계측, 밴드 ±15 % |",
"| (인라인 조립) | 카본 튜브 다리 + 스키드 | Matrice 350 RTK | 다리 형상이 기종 전용이라 "
"자기 분기 안에서 직접 스윕한다 |",
"",
f"⚠ `_gear_skids`({LN('_gear_skids')}행) · `_gear_tall`({LN('_gear_tall')}행) ·"
f" `_gear_feet`({LN('_gear_feet')}행)도 소스에 있지만 지금 부르는 기체가 없다 —"
" 앞의 두 함수를 쓰는 자리를 각각 `_gear_arch` · `_gear_tall_tube` 가 받았고,"
" `_gear_feet` 는 자기 docstring 이 스스로 **폐기된 옛 형상**이라고 적는다.",
"",
"⭐ 이 표가 다시 낡지 않게 하는 방법이 요점이다 — **소스를 읽어 옮겨 적지 말고, 돌려서 기록한다.**",
"기종을 추가하면 표가 저절로 따라온다.",
"",
"### §2.1b ⚠ 짐벌 조립의 지금 남은 어긋남 셋",
"",
"짐벌은 «작은 부품» 처럼 보이지만 이 함대에서 가장 무거운 결함이 여기 있다. 전용 검사기가",
"게이트 넷(A 부착 · B 뜸/삼킴 · C 선언 대비 실제 크기 · D 재질 민감도)으로 10종을 훑는다",
"← 출처: `outputs/mesh_inspect_gimbal_sensors_0816.json` · `benchmark/check_gimbal_sensors_0816.py`.",
"",
"**① 게이트 A — 짐벌이 바닥을 정하는 기체가 하나 있다.** " + (
    f"{drone_label(_GA['drone'])} 는 카메라 최저점이 착륙발보다 "
    f"{abs(_GA['camera_below_gear_mm']):.2f} mm 아래다. 그 최저점이 세로 배율을 정하므로 "
    f"(§3.2) 발을 바닥으로 놓고 같은 규칙을 풀면 배율이 {_GA['sz_now']:.4f} → "
    f"{_GA['sz_if_bottom_were_the_feet']:.4f}({_GA['vertical_scale_error_pct']:.2f} %) 로 커진다 — "
    "흔들리는 것은 카메라가 아니라 **기체 전 부위의 세로 치수**다."),
"",
"**② 게이트 C — 헬퍼에 넣은 «선언 치수» 와 실제로 지어지는 크기가 다르다.** 헬퍼가 인자로 받은",
"상자 크기 위에 요크·렌즈·마운트를 더 붙이기 때문이고, 지금 그 배율은 이만큼이다:",
"",
"| 헬퍼(인자) | 쓰는 기종 | 선언 [mm] | 실제 [mm] | 배율 |",
"|---|---|---|---|---|",
*[f"| `{r['helper']}` | {', '.join(r['used_by'])} "
  f"| {'×'.join(f'{v:g}' for v in r['declared_xyz_mm'])} "
  f"| {'×'.join(f'{v:g}' for v in r['built_xyz_mm'])} "
  f"| {'×'.join(f'{v:.2f}' for v in r['built_over_declared'])} |"
  for r in _GC],
"",
"⭐ 읽는 법: **인자를 실물 치수라고 믿고 쓰면 안 된다.** 실물 치수를 맞추려면 mini2 처럼 "
"«원하는 결과 bbox → 인자» 로 **역산**해야 한다(그 기체는 그렇게 해서 공식 CAD bbox 와 맞는다).",
"",
f"**③ 게이트 B — 짐벌 부품이 기체에 안 닿거나(뜸) 다른 부품에 완전히 묻힌다(삼킴).** "
f"뜬 것은 {', '.join(drone_label(k) for k in _GB_FLOAT)}, 삼켜진 것은 "
f"{', '.join(drone_label(k) for k in _GB_SWAL)} 에 있다. σ 로는 작지만 "
"**PO 와 SBR 이 같은 메쉬를 다르게 읽게** 만든다 — 묻힌 면을 SBR 은 가리고 PO 는 센다"
"(mesh07 §8.3).",
"",
"### §2.2 보이지 않는 부품 — 내부 battery/pcb 를 왜 넣나",
"",
"조립 마지막에 렌더에선 절대 안 보이는 상자 두 개가 셸 **안에** 들어간다"
"(← `src/drone_cad.py` 내부 산란체 주석):",
"",
"> \"내부 금속 산란체 (RCS 지배) — 셸 안이라 렌더엔 안 보이지만 PO/SBR 이 센다\"",
"",
"이유: 드론 셸은 플라스틱이라 GHz 전파에 **반투명**하다(진폭 반사계수 |Γ|≈0.24~0.28 — 즉 전파",
"대부분이 셸을 뚫고 들어간다 ← 출처: src/materials.py plastic 정의·note). 그래서 실물",
"드론의 레이더 반사는 셸이 아니라 **안에 있는 배터리팩·ESC/메인보드·모터 금속**이 지배한다",
"(← 출처: `src/drone_cad.py` \"내부 금속 산란체 (RCS 지배)\" 주석). 재질 배정도 이에 맞춰",
"battery=metal(\"GHz 에서 파우치 포일은 사실상 금속\"), pcb=FR-4+구리 그라운드플레인이다",
"(← src/drones.py, DRONE_GROUP_MAT). 치수는 기종별 실물이 비공개라 동체 대비 대표",
"비율(파라메트릭)로 정의된다(← 같은 자리, bl·bw·bh 비율) — 추정값이라는 점은",
"'현재 한계'로 정리에 적는다.",
"",
"### §2.3 마지막 손질 — 불리언 합집합",
"",
"부위를 겹쳐 쌓기만 하면 '동체 속에 파묻힌 암 뿌리' 같은 **내부 면**이 메쉬에 그대로 남아,",
"레이더 계산(PO/SBR)이 존재하지 않는 면을 헛세게 된다. 그래서 그룹별로 불리언 합집합을 돌려",
"겹친 파트를 한 껍질로 녹인다 — \"그런 면이 **애초에 존재하지 않는다**\"(← src/drone_cad.py).",
"이 겹침 검증 결과(F_overlap)는 mesh07 에서 다룬다.",
),

# ── 8b. §2.4 매끈함의 대가 ────────────────────────────────────────────────────
md(
"### §2.4 매끈하게 만드는 두 단계에는 대가가 있다",
"",
"동체를 실물처럼 만드는 두 도구 — **스플라인 보간**(단면 사이를 잇는다)과 **Taubin 스무딩**",
"(각진 로프트를 다듬는다) — 은 둘 다 형상을 **바꾼다**. 지금 그 크기를 재 놓았다.",
"",
"**① 스플라인이 제어점 사이에서 넘친다.** 3차 스플라인은 기울기까지 연속으로 잇느라",
"제어점 사이에서 값을 살짝 벗어난다. 형상표가 «잘록한 허리 → 넓은 어깨» 로 꺾이면 특히 그렇다:",
"",
"| 기체 | 무엇 | 형상표 의도 | 메쉬 실측 | 어긋남 |",
"|---|---|---|---|---|",
"| matrice4e | 셸 배(아래쪽) | −30.38 mm (형상표) · −30.81 mm (공식 CAD) | −34.74 mm | **CAD 대비 3.93 mm 더 아래** |",
"| mini5pro | 셸 최대 반폭 | 35.21 mm | 37.87 mm | **+7.6 %** |",
"| mini2 | 셸 높이 | 44.80 mm | 48.36 mm | **+8.0 %** |",
"",
"⭐ **부호가 늘 같은 쪽이다** — 항상 «더 크게(= 전파에 더 밝게)». 우연이 아니라 넘침의 성질이다.",
"고치는 길은 제어점을 6 → 8~10 으로 늘리거나, 넘치지 않는 보간(단조 스플라인)으로 바꾸는 것이다.",
"둘 다 전 기종 메쉬가 바뀌므로 별도 라운드의 일이다.",
"",
"**② 스무딩이 끝단 캡을 안으로 당긴다.** 로프트의 앞뒤 마감면은 삼각형 팬으로 닫혀 있는데,",
"스무딩이 그 테두리 링을 안쪽으로 끌어당긴다(스무딩 0회 ↔ 4회 대조):",
"",
"| 기체 | 어디 | 스무딩 전 | 스무딩 후 | 남은 비율 |",
"|---|---|---|---|---|",
"| matrice4e | 기수 단면(반폭×반높이) | 41.02×36.88 mm | 23.42×21.31 mm | 약 57 % |",
"| mavic4pro | 꼬리 단면 | 42.63×28.57 mm | 24.58×16.43 mm | 약 57 % |",
"| phantom3 | 기수 단면 | 26.04×22.01 mm | 16.30×12.96 mm | 약 61 % |",
"",
"**가운데 4개 스테이션은 형상표를 0.5 % 안에서 재현한다** — 손실은 끝단 전용이다.",
"방위평균 투영면적으로는 −0.00~−0.06 dB 밖에 안 움직이므로 **레벨 결함이 아니다.**",
"흔들리는 것은 «기수를 정면으로 봤을 때의 정반사 형상» 이고, 그 크기는 아직 커널로 안 쟀다.",
"",
"← 출처: `outputs/mesh_inspect_body_arms_0816.json` `findings`(로프트 끝단 캡·스플라인 넘침).",
"고칠 자리는 선택 인자로 뚫려 있다(`_body_folding(..., smooth_iters=)`) — **기본값이 옛 값이라",
"지금 메쉬는 비트동일**하다.",
),

# ── 9. code: 스타일 분기 + 실제 그룹 ─────────────────────────────────────────
code(
"# 스펙의 스타일 필드가 실제 메쉬 그룹으로 이어졌는지 — A_geometry(측정)와 대조",
"print(f\"{'key':10s} {'gimbal_style':>13s} {'gear':>5s} {'암':>10s}   실제 생성된 그룹(mesh_verify.json A_geometry)\")",
"for k in V['meta']['drones']:",
"    s = DRONES[k]; g = V['A_geometry'][k]",
"    arm = '고정암' if s.fixed_arm else '접이식'",
"    print(f\"{k:10s} {s.gimbal_style:>13s} {s.gear:>5s} {arm:>8s}   \"",
"          f\"{g['n_faces']:,}tri · {sorted(g['groups'])}\")",
"# gear 필드가 어떤 값이든 다리를 짓는 기종에는 'gear' 그룹이 있어야 정상",
"#  (mini5pro·mavic4pro 는 gear='motor_legs' — 앞 모터 포드 밑 다리를 짓는다)",
),

# ── 10. §3 envelope fit ──────────────────────────────────────────────────────
md(
"## §3. envelope fit — 공식 외형에 자동으로 맞추기 (frame_fit_scale)",
"",
"실루엣 파라미터를 눈으로 아무리 다듬어도, 완성된 프레임의 바운딩박스가 DJI 공식 L×W×H 와",
"같아진다는 보장이 없다 — 파라메트릭 비율(body_frac·body_lw 등)은 실루엣용이지 치수 보증용이",
"아니기 때문이다.",
"",
"이게 왜 중요한가 — 챔버 기하(낮은 앙각 el≈15°)에서는 **높이가 측면 투영면적을 지배**하고,",
"평판 극한에서 RCS 는 σ ∝ (투영면적)² 이므로, 높이가 수십 % 어긋나면 σ 가 수 dB 단위로",
"틀어진다. 즉 모양이 예뻐도 크기가 틀리면 탐지 확률 계산이 통째로 틀린다(← 출처:",
"src/drones.py envelope fit 절 주석).",
"",
"**규약** (`frame_fit_scale`, src/drones.py): 실루엣은 그대로 두고, 완성된 프레임의",
"바운딩박스를 재서 **공식 envelope_mm 과 같아지도록 축별 배율 (sx, sy, sz)** 를 곱한다.",
"공식값이 없는 축(None)은 건드리지 않는다 — Mini 5 Pro 는 높이만 맞추는 이유가 이것이다(§1.1).",
"모터 위치(`rotor_layout`)에도 같은 배율을 걸어 프로펠러가 모터 위에 정확히 앉는다",
"(← src/drones.py — \"프레임과 **같은** 외형보정 배율\").",
"",
"**대가도 명시돼 있다**(← src/drones.py): 축마다 배율이 다르므로(비등방)",
"모터 원통이 약간 타원이 된다. \"RCS 가 보는 것은 투영면적과 외형이므로 이쪽을 맞추는 것이",
"옳다는 판단.\" 그리고 **프로펠러는 스케일하지 않는다** — 프롭 지름(prop_dia_mm)은 별도 공식",
"스펙이 있기 때문이다(← src/drones.py).",
"",
"### §3.1 결과 — 치수 검증 C_dims (공식 → 실측, 오차%)",
"",
"아래 수치는 완성 메쉬를 실제로 재서 공식값과 비교한 것이다",
"(← 출처: outputs/mesh_verify.json §C_dims, 측정 코드 report_mesh/src/verify_mesh_suite.py):",
"",
"| 기종 | L [mm] | W [mm] | H [mm] | 대각 [mm] | 프롭 [mm] | 최악오차 | fit_scale (sx,sy,sz) |",
"|---|---|---|---|---|---|---|---|",
CDIMS_TABLE,
"",
f"읽는 법 — envelope 을 직접 맞춘 L/W/H 는 오차 0%. 전체 최악은 {NAME[worst_key]} 의 대각",
#  ⚠ 2026-07-30 (Phase 3): 여기 (공식 438.8 → 실측 428.7) 이 **손타이핑**이었고, matrice4e
#     로터 배치 정정(2026-07-28) 뒤에는 **낡은 값**이 됐다. 이제 원장에서 읽는다.
f"{worst_diag_signed:+.2f}% 다(공식 {_wd['official']:.1f} → 실측 {_wd['measured']:.1f})."
    if _wd else f"{worst_diag_signed:+.2f}% 다.",
"⚠ 이 기체의 대각 오차는 **배율 탓이 아니다** — 면내 배율이 1.000 이라 늘리거나 줄인 것이 없다.",
"원인은 로터를 사다리꼴로 놓은 **선언된 선택**이고(§5), 그래서 마주보는 로터 거리가 공표 대각보다",
"짧게 나온다. 배율에 끌려간 대각은 **Phantom 4** 쪽이다 — 세 축을 전부 강제하는 기체라 면내 배율",
f"{C['phantom4']['fit_scale'][0]:.4f} 가 모터 위치까지 밀어 축간거리를 +1.98 % 부풀린다",
"(외형이 우선 ← src/drones.py 주석).",
f"프로펠러 지름 오차가 전 기종 {_prop_err_txt} 로 좁게 모이는 것은 빌드가 **날을 지은 뒤 실제 최대반경을",
"재서 공표 지름으로 되돌리기** 때문이다 — «맞다» 가 아니라 «맞춰 놓았다» 로 읽어야 한다(mesh05 §6).",
"fit_scale 을 보면 기종마다 실루엣이 공식 외형에서 얼마나 멀었는지도",
f"보인다: {NAME['mavic4pro']} 는 ({mav_fs[0]:.3f}, {mav_fs[1]:.3f}, {mav_fs[2]:.3f}), S1000+ 는 수평",
f"({_s1000_fs[0]:.3f}, {_s1000_fs[1]:.3f}) 다.",
),

# ── 10b. §3.2 배율이 커지면 그것은 «맞춤» 이 아니라 «늘리기» 다 ────────────────
md(
"### §3.2 ⭐ 배율이 커지면 그것은 «맞춤» 이 아니라 «늘리기» 다",
"",
"위 표의 `fit_scale` 은 **형상을 통째로 늘리거나 줄이는 배율**이다. 값이 1 에 가까우면",
"«형상이 이미 공표 외형과 맞았다» 는 뜻이라 교정이 무해하다. 그러나 값이 1 에서 크게 벗어나면,",
"그것은 **형상이 틀렸다는 신호를 배율로 덮은 것**이다 — 부품 하나하나가 다 함께 늘어난다.",
"",
"지금 상태를 그대로 적는다:",
"",
"| 기체 | 세로 배율 | 무엇을 뜻하나 |",
"|---|---|---|",
*[f"| {NAME[k]} | {C[k]['fit_scale'][2]:.4f} | "
   + ("**형상이 세로로 부족해 전 부품을 늘려 공표 높이를 맞춘다**"
      if C[k]['fit_scale'][2] > 1.05 else
      ("형상이 세로로 넘쳐 눌러 맞춘다" if C[k]['fit_scale'][2] < 0.95 else
       "형상이 이미 맞는다(교정 무해)")) + " |" for k in KEYS],
"",
"← 출처: `mesh_verify.json` `C_dims.*.fit_scale`.",
"",
f"**mini5pro 와 mavic4pro 가 그 자리다.** 사진에서 잰 셸 높이",
f"{MF.BODY['per_drone']['mini5pro']['shell_h_mm']['table']:.2f} / "
f"{MF.BODY['per_drone']['mavic4pro']['shell_h_mm']['table']:.2f} mm 가 메쉬에서는",
f"{MF.BODY['per_drone']['mini5pro']['shell_h_mm']['delivered']:.2f} / "
f"{MF.BODY['per_drone']['mavic4pro']['shell_h_mm']['delivered']:.2f} mm 로 나온다.",
"평판극한 상한으로 방위평균 σ **+2.27 / +2.62 dB**(el 0°)다.",
"",
f"mavic4pro 에는 **원인이 하나 더** 있다 — 짐벌이 착륙발보다",
f"{abs(MF.GIMBAL['_summary']['gate_A_fail'][0]['camera_below_gear_mm']):.2f} mm 아래에 있어서",
"기체의 최저점이 카메라다. 그 15 mm 가 세로 예산의 구멍을 가려 배율을 **작아 보이게** 만든다.",
"발을 바닥으로 놓고 같은 규칙을 다시 풀면 배율이",
f"{MF.GIMBAL['_summary']['gate_A_fail'][0]['sz_now']:.4f} → "
f"{MF.GIMBAL['_summary']['gate_A_fail'][0]['sz_if_bottom_were_the_feet']:.4f} 로 커진다.",
"",
"⚠ **아직 못 정한 것** — 공표 언폴드 높이는 공식이지만, 그 높이를 다리·셸·짐벌·모터에 **어떻게**",
"나누는지는 사진 한 장으로 안 풀린다. matrice4e 처럼 공식 CAD 가 필요한데 DJI 는 Mavic 4 Pro",
"CAD 를 공개하지 않는다 ← 출처: `outputs/mesh_inspect_body_arms_0816.json` `not_settled_this_round`.",
"",
"**대조군** — 공식 CAD 로 세로 배분을 다시 푼 matrice4e 는 배율이",
f"{C['matrice4e']['fit_scale'][2]:.4f} 로, 형상 자체가 공표 높이를 낸다.",
),

# ── 11. §4 개성 대비 intro + Mini 그림 ───────────────────────────────────────
md(
"## §4. 드론별 개성 — 같은 코드, 다른 스펙, 다른 드론",
"",
"조립 코드는 하나지만 스펙 필드가 다르니 다른 드론이 나온다. 배정된 두 그림으로 양 극단을",
"대비한다: **접이식 초소형**(Mini 5 Pro)과 **고정암 클래식**(Phantom 4).",
"",
f"![Mini 5 Pro wireframe](outputs/figures/wireframe_mini5pro.png)",
"",
f"*그림 1 — DJI Mini 5 Pro: 셰이딩(색=재질) / 와이어프레임(삼각형 {A['mini5pro']['n_faces']:,}개) /",
f"탑뷰. 그룹 {A['mini5pro']['n_groups']}개. ← 출처: 그림 생성 report_mesh/src/viz_mesh_reports.py",
"fig_wireframes(), 삼각형·그룹 수는 mesh_verify.json §A_geometry.*",
"",
"Mini 에서 볼 것 세 가지:",
"",
f"1. **전방 스윕 로터 배치** — `rotor_deg={mini.rotor_deg}`. 탑뷰에서 앞 모터가 45° 가 아니라",
"   56.3° 로 옆으로 벌어져 있다. 조사에서 확인한 로터 좌표 (±76, ±114) mm 그대로다(← src/drones.py).",
f"2. **앞 모터가 낮다** — `rotor_z_mm={mini.rotor_z_mm}`. 프롭 지름({mini.prop_dia_mm:g} mm)이",
"   앞뒤 모터 간격(152 mm)보다 커서 **프롭 디스크가 겹치는** 기체라, 실물은 앞 모터를 낮춰 충돌을",
f"   피한다. 와이어프레임 패널에서 앞쪽 프롭 두 개가 뒤쪽보다 {mini.rotor_z_mm[1] - mini.rotor_z_mm[0]:g} mm 낮게 앉은 게 보인다(← src/drones.py",
"   주석 — \"실물은 앞 모터가 더 낮다(간섭 회피). 조사 확인\").",
f"3. **착륙장치가 전용 스키드가 아니라 모터 포드 밑 다리다** — `gear={mini.gear!r}`,",
f"   다리 길이 {mini.gear_h_mm:g} mm. 앞쪽 두 모터 포드 아래에만 두 갈래 다리가 달리고 뒤쪽 포드에는 없다",
"   (← src/drones.py mini5pro note — 제품사진 계측, 밴드 ±15 %). 이 다리가 기체의 최저점이다.",
"",
"색 규칙(모든 기종 공통): 플라스틱=밝은 회색(프로펠러 포함), 모터·배터리=파랑(금속), 카본(암)=검정, 카메라=주황,",
"PCB=초록 — **색이 곧 재질**이라 그림만 봐도 전파 물성이 읽힌다(← src/drones.py",
"MATERIAL_COLOR·drone_colors docstring).",
),

# ── 12. Phantom 그림 ─────────────────────────────────────────────────────────
md(
f"![Phantom 4 wireframe](outputs/figures/wireframe_phantom4.png)",
"",
f"*그림 2 — DJI Phantom 4: 같은 3분할. 삼각형 {A['phantom4']['n_faces']:,}개 /",
f"그룹 {A['phantom4']['n_groups']}개. ← 출처: 동일(viz_mesh_reports.py fig_wireframes,",
"mesh_verify.json §A_geometry).*",
"",
"Phantom 에서 볼 것 세 가지:",
"",
f"1. **고정암 X자** — `fixed_arm={ph.fixed_arm}`, `rotor_deg={ph.rotor_deg}` 의 대칭 X자.",
"   접이식과 달리 암이 굵고(0.085·diag) 덜 휜다(bend 0.02 vs 0.06). 암 그룹도 카본이 아니라",
"   동체와 같은 흰 셸(plastic)이다 — `arm_style='body'` 면 암을 body 그룹에 넣는다",
"   (← `src/drone_cad.py` 의 암 굵기·휨 분기).",
f"2. **일체형 착륙다리** — `gear={ph.gear!r}` → `_gear_arch`(뒤집힌 U 자 아치 다리 2개 + 바닥 레일).",
"   다리가 아래로 길게 뻗어, 접이식 소형기엔 없는 수직 구조물이 생긴다. 이게 높이 "
+ f"{ph.envelope_mm[2]:g} mm(공표 대각 {ph.diagonal_mm:g} mm 의 "
+ f"{ph.envelope_mm[2] / ph.diagonal_mm:.2f} 배 — 소비자 쿼드 중 가장 높은 비율)의 이유다.",
f"3. **함몰 짐벌** — `gimbal_style={ph.gimbal_style!r}`. 같은 `_gimbal_hanging` 을 쓰되 동체에 바짝",
"   붙인다(cx 를 0.62 배로). 기수 아래 작은 비전센서 2개도 붙는다"
"   (← `src/drone_cad.py` phantom4 짐벌 분기).",
"",
f"**두 그림을 나란히 두면** — 동체 단면 지수"
f"({_DC._SHELL_SHAPE['mini5pro']['npow']:g} vs {_DC._SHELL_SHAPE['phantom4']['npow']:g}), "
f"코 처짐({_DC._SHELL_SHAPE['mini5pro']['ndrop']:g} vs {_DC._SHELL_SHAPE['phantom4']['ndrop']:g}), 암 굵기, 착륙장치",
"유무, 짐벌 위치가 전부 스펙 필드 몇 개에서 갈라져 나왔음을 볼 수 있다. 이것이 파라메트릭 CAD 의",
"요점이다: **개성은 데이터(스펙)에, 솜씨는 코드(조립 함수)에** 나눠 담긴다.",
),

# ── 13. §4.1 두 기종 숫자 대비 ───────────────────────────────────────────────
md(
"### §4.1 두 기종 숫자로 대비 (전부 mesh_verify.json·DRONES 출처)",
"",
"| 항목 | Mini 5 Pro | Phantom 4 | 출처 |",
"|---|---|---|---|",
f"| 대각(공식→실측) | {_dim_cell('mini5pro','diagonal')} | {_dim_cell('phantom4','diagonal')} | mesh_verify.json §C_dims |",
f"| 높이(공식→실측) | {_dim_cell('mini5pro','H')} | {_dim_cell('phantom4','H')} | 〃 |",
f"| 프롭 지름(공식→실측) | {_dim_cell('mini5pro','prop_dia')} | {_dim_cell('phantom4','prop_dia')} | 〃 |",
f"| 삼각형 수 | {A['mini5pro']['n_faces']:,} | {A['phantom4']['n_faces']:,} | mesh_verify.json §A_geometry |",
f"| 그룹 수 | {A['mini5pro']['n_groups']} | {A['phantom4']['n_groups']} | 〃 |",
f"| 이륙중량 | {mini.weight_g:g} g | {ph.weight_g:g} g | src/drones.py DRONES·docs/SPECS.md |",
f"| 암/착륙장치 | 접이식 · 모터 포드 아래 다리({mini.gear_h_mm:g} mm) | 고정암 · 스키드 다리 | src/drones.py,170 |",
f"| 로터 z 오프셋 | {mini.rotor_z_mm} mm | 없음 | src/drones.py |",
"",
f"그룹 수가 {A['mini5pro']['n_groups']} 대 {A['phantom4']['n_groups']} 로 갈리는 것은 **`accent`(전방 식별용 소형 파트 — 재질=플라스틱이라 셸과 같은 회색) 한 그룹 때문**이다 —",
"Mini 에는 있고 Phantom 에는 없다. `gear`(착륙장치)는 둘 다 있다(위 코드 셀 출력 참조).",
f"참고로 Mavic 4 Pro 도 accent 가 없어 {A['mavic4pro']['n_groups']}개다(← mesh_verify.json §A_geometry).",
),

# ── 14. §5 좌우대칭 ──────────────────────────────────────────────────────────
md(
"## §5. 좌우대칭 — 설계 이유와 실측 검증",
"",
"**왜 좌우대칭인가.** 멀티로터는 무게중심이 로터 배치의 중심에 있어야 호버링이 안정된다.",
"그래서 조립 규약이 코드에 명시돼 있다(← 출처: src/drones.py `motor_angles` docstring):",
"",
"> \"rotor_deg 는 좌우대칭이고 마주보는 쌍이 180° → 대각거리 스펙 보존 + 무게중심 중앙(비행안정)\"",
"",
f"Mini 의 전방 스윕 배치 {mini.rotor_deg} 는 그 규약의 **앞쪽 절반만** 지킨다.",
f"좌우대칭은 성립한다 — {_m5[0]:.2f}°/{_m5[3]:.2f}° 와 {_m5[1]:.2f}°/{_m5[2]:.2f}° 가 각각 xz 평면 거울상이다.",
f"그러나 마주보는 쌍은 정확히 180° 가 **아니다**: {_m5[0]:.2f}°↔{_m5[2]:.2f}° 는 {_m5_opp:.1f}° 차이다.",
"로터가 정사각형이 아니라 **사다리꼴**로 놓여 있기 때문이고(앞 트랙이 뒤 트랙보다 넓다),",
"그래서 이 기체만 «대각거리 스펙 보존» 이 성립하지 않는다 — 마주보는 로터 거리는",
f"{_m5_wb:.2f} mm 로 공표 대각 {mini.diagonal_mm:g} mm 보다 {100*(_m5_wb-mini.diagonal_mm)/mini.diagonal_mm:.1f} % 작다.",
"⭐ 이것은 결함이 아니라 **선언된 선택**이다(스펙 `note` 가 그렇게 적는다). 다만 §3.1 표의 대각 오차가",
"그 선택의 결과라는 것, 그리고 **로터 간격을 인용할 때는 공표 대각이 아니라 축간거리를 써야 한다는 것**을",
"함께 읽어야 한다 ← 출처: `outputs/mesh_inspect_body_arms_0816.json` `findings` B12.",
"나머지 9기종은 마주보는 쌍이 정확히 180° 라 규약 그대로다.",
"",
"**실측 검증(B_symmetry).** 완성 메쉬 표면에서 점을 뽑아 y→−y 로 뒤집은 점 구름과의 챔퍼 거리를",
"잰다 — 완벽 대칭이면 0 이 된다(← 출처: outputs/mesh_verify.json §B_symmetry, 측정 코드",
"report_mesh/src/verify_mesh_suite.py). 단위는 mm:",
"",
"| 기종 | 표본점 수(frame) | frame p50 | frame p95 | frame max | (참고) full p95 | 판정 p95≤2mm |",
"|---|---|---|---|---|---|---|",
SYM_TABLE,
"",
f"프레임(비회전부)은 전 기종 **p95 ≤ 2 mm** — 최악이 {NAME[sym_worst_key]} 의",
f"{sym_p95[sym_worst_key]:.2f} mm 다. 남는 잔차는 대칭이 아닌 부품(레이저 측거처럼 한쪽에만 있는",
"센서, 짐벌 요크 디테일)과 표본 추출 노이즈다.",
"",
f"**full(프로펠러 포함) p95 는 {min(full_p95.values()):.0f}~{max(full_p95.values()):.0f} mm 로 크다",
"— 버그가 아니다.** 프로펠러는 장착 위상(+12° 오프셋 ← src/drones.py)과 교대 회전 방향으로",
"앉아 있어 어느 순간의 스냅샷도 좌우 거울상이 아니다. 실물도 마찬가지다. 그래서 대칭 검증은",
"**frame_only(프레임만)** 로 판정한다 — full 수치는 '프롭이 대칭을 깨는 정도'의 참고값으로만 싣는다.",
),

# ── 15. code: 대칭 표 재현 + 판정 ────────────────────────────────────────────
code(
"# 좌우대칭 실측 — mesh_verify.json §B_symmetry 를 그대로 표로. 판정: frame p95 ≤ 2 mm",
"print(f\"{'key':10s} {'frame p50':>10s} {'frame p95':>10s} {'frame max':>10s} {'full p95':>9s}\")",
"for k in V['meta']['drones']:",
"    fo = V['B_symmetry'][k]['frame_only']['chamfer_mm']",
"    fu = V['B_symmetry'][k]['full']['chamfer_mm']",
"    print(f\"{k:10s} {fo['p50']:10.2f} {fo['p95']:10.2f} {fo['max']:10.2f} {fu['p95']:9.1f}\")",
"",
"assert all(V['B_symmetry'][k]['frame_only']['chamfer_mm']['p95'] <= 2.0",
"           for k in V['meta']['drones'])",
"print()",
"print('PASS — 전 기종 프레임 좌우대칭 p95 ≤ 2 mm (full 은 프로펠러 위상 때문에 원래 크다)')",
),

# ── 16. 마무리 ───────────────────────────────────────────────────────────────
md(
"## 정리",
"",
"1. **스펙과 스타일을 분리했다** — 공식 숫자(출처·신뢰도 부착)는 물리로, 눈대중 파라미터는",
"   실루엣으로만 들어간다. 추정값(Mini 대각, Mavic 대각 모순)은 note 에 그대로 남겼다(§1).",
"2. **조립은 4가지 기법의 반복이다** — 초타원 로프트(동체·캐노피), 베지에 스윕(암·다리),",
"   회전체(모터 벨·RTK 돔), 불리언 합집합(내부 면 제거). 짐벌 3종·착륙장치 3종·내부",
"   battery/pcb 가 기종 개성과 레이더 물리를 담당한다(§2).",
f"3. **공식 외형이 최종 기준이다** — envelope fit 후 치수 최악 오차 {worst_pct:.2f}%",
f"   ({NAME[worst_key]}). 공식값을 강제한 축은 오차 0 인데, 그 0 은 «검증» 이 아니라",
"   **«구성상 보장»** 이다 — 어느 축을 강제하는지는 기체마다 다르다(§3.1·§3.2, 자세히는 mesh08 §1).",
f"4. **좌우대칭은 규약 + 실측으로 보증한다** — 프레임 p95 ≤ 2 mm 전 기종 통과(§5).",
"",
"**현재 남은 한계** — 있는 그대로 적는다:",
"",
MF.defect_table(),
"",
"← 출처: `outputs/mesh_inspect_body_arms_0816.json` `findings` · "
"`outputs/mesh_inspect_gimbal_sensors_0816.json` `_summary` · "
"`outputs/mesh_inspect_materials_check_0816.json` `findings`. "
"위 표의 dB 는 대부분 **평판극한 상한**이지 커널이 계산한 σ 가 아니다.",
"",
"거기에 더해: 내부 battery/pcb 치수는 기종별 실물이 비공개라 동체 비율 추정이고,",
"비등방 배율 때문에 모터 원통이 약간 타원이다.",
"",
"### 지금 «모른다» 고 선언한 것",
"",
*MF.unresolved_list(),
"",
"⭐ **빈칸이 가짜 값보다 낫다.** 위 항목들은 값을 채워 넣는 대신 비워 두었다.",
),

# ── 17. 재현 + 다음 ──────────────────────────────────────────────────────────
md(
"## 재현 명령",
"",
"```bash",
"cd /workspace/sionna/report_mesh",
"# 1) 검증 수치(mesh_verify.json) 재생성",
"/workspace/.venvs/py312/bin/python src/verify_mesh_suite.py",
"# 2) 그림(outputs/figures/*.png) 재생성",
"/workspace/.venvs/py312/bin/python src/viz_mesh_reports.py",
"# 3) 이 노트북 재생성",
"/workspace/.venvs/py312/bin/python src/make_mesh04.py",
"```",
"",
"**다음 리포트** — mesh05: 프로펠러 편(진짜 익형 블레이드 — NACA 단면·모델별 기하 피치·시미터",
"스윕, 그리고 지름을 «맞춰 놓는» 정규화가 무엇을 보증하고 무엇을 안 보증하는지).",
"같은 폴더의 `mesh05_*.ipynb`.",
),

]

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "py312",
      "language": "python", "name": "py312"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
out = os.path.join(RM, "mesh04_body_cad.ipynb")
for _i, _c in enumerate(nb["cells"]):
    _c["id"] = f"m04-{_i:02d}"

json.dump(nb, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", out, len(cells), "cells")
