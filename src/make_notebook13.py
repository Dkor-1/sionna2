# -*- coding: utf-8 -*-
"""
make_notebook13.py — report13.ipynb 생성기 (자유공간 드론 검지거리)
==========================================================================================
report13 — "챔버를 벗어나면 이 드론을 몇 m 에서 잡나: 자유공간(FS-1) 검지거리"

⚠ 이 파일이 진짜 소스다. report13.ipynb 를 직접 고치지 말고 여기를 고쳐 재실행할 것.
⚠ **모든 숫자는 outputs/report13_freespace.json 에서 읽어 넣는다**(손으로 적은 숫자 없음, spec §9).
   JSON 이 아직 없으면(다른 그룹 산출물) placeholder("—")로 graceful 하게 셀만 조립한다.

★ 설계 근거 (왜 이렇게 했나)
  1. **provenance_cells 사용**(spec §9/§13). engines 태그는 5개 —
       ["sbr","sionna-phy","sionna-render","radar-dsp","matplotlib"] — 전부 ENGINE_DESC 에 이미 등록됨을
     import 시점에 검사한다(없는 태그는 provenance 가 **조용히 누락**하는 report12 함정 회피).
  2. **절 구성은 spec §13 표**(§0 왜 챔버 벗어나나 … §8 말할 수 없는 것)를 그대로 따른다. 각 절 상단에
     §1.1 헤드라인 문장을 f-string 으로 주입한다.
  3. **graceful**: JSON 부재/키 부재는 전부 `_g()`/`_f()` 가 placeholder 로 흡수 —
     생성기는 무조건 돌아야 한다(스모크 규칙).
  4. **GPU 불필요**: 이 파일은 mitsuba/scene_build 를 import 하지 않는다(순수 JSON→노트북).
  5. **선행 인용은 `docs/PRIOR_WORK_COMPARISON.md` §13 처방을 옮긴 것**이고, 인용한 사실은 전부 원문
     PDF 에서 재확인했다(Asilomar 식 (8)/(9)·Table I·"idealized scenario" 원문 / Rzewuski 식 (4) F_u ·
     FDTD QuickWave-3D · WiFi 대역 −40~0 dBsm · D0 8 dB 트랙레벨 근거 / Demissie Pfa 1e-2→1e-4 시
     2700→약 1500 m · CUT 진동=직접경로+반사 1개 / Sun WiSec '22 포스터 20 m 실측 + 반사체 부착 /
     Ji arXiv:2602.08203 알루미늄박 상자 표적).
     ⚠ **기각 기록(지우지 말 것)**: 점유 F(Asilomar 식 9)와 듀티 F_u(Rzewuski 식 4)를 **동시에** 쓰자는
     안은 기각됐다 — 같은 물리손실의 **대체 파라미터화**라 곱하면 이중계상이다. §4·용어풀이에 명시한다.
     같은 이유로 Rzewuski D0=8 dB(트랙 레벨 문턱)를 우리 단일-CPI 문턱과 직접 비교하는 것,
     모드별 D0 를 선행 식에 갈아끼우는 것(모드마다 경험 Pfa 가 다름, report10)도 기각이다.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# ─────────────────────────────────────────────────────────────────────────────
# ⚠ 이 파일은 **스크립트**다 (main() 없이 최상위에서 전부 실행된다).
#   임포트하면 그 자리에서 리포트 노트북을 **덮어쓴다**. 2026-07-29 실제로 검증 에이전트가
#   "임포트 되는지" 점검하다가 report07/08/13 을 덮어썼고 복구해야 했다. linter·문서도구·
#   테스트수집기도 같은 사고를 낸다 — 게다가 계산이 도는 중이면 **중간 숫자**가 박힌다.
#   → 실행은 `python src/make_notebook13.py` 로만.
if __name__ != "__main__":
    raise RuntimeError(
        "make_notebook13.py 는 스크립트다 — 임포트하면 리포트를 덮어쓴다. "
        "`python src/make_notebook13.py` 로 실행할 것. (2026-07-29 실사고)")
# ─────────────────────────────────────────────────────────────────────────────

ROOT = os.path.abspath(os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from provenance import provenance_cells, ENGINE_DESC             # noqa: E402

NB = os.path.join(ROOT, "report13.ipynb")
# 정본 경로는 outputs/. 스모크는 SIONNA2_R13_JSON 으로 /tmp 스모크 JSON 을 주입해 셀 조립을 확인한다
# (spec: '실험그룹 /tmp 스모크 JSON 으로 셀 조립만 확인'). 정본 실행 때는 환경변수를 두지 않는다.
FREESPACE_JSON = os.environ.get("SIONNA2_R13_JSON",
                                os.path.join(ROOT, "outputs", "report13_freespace.json"))
VERIFY_JSON = os.path.join(ROOT, "outputs", "verify_freespace.json")
SIGMA_JSON = os.path.join(ROOT, "outputs", "report13_sigma_grid.json")

ENGINES = ["sbr", "sionna-phy", "sionna-render", "radar-dsp", "matplotlib"]
# ⚠ report12 함정 방지: 등록 안 된 태그는 provenance 가 조용히 빠뜨린다 → 미리 검사·경고.
_missing = [e for e in ENGINES if e not in ENGINE_DESC]
if _missing:
    print(f"⚠ ENGINE_DESC 미등록 태그 {_missing} — provenance 에서 누락됨(먼저 등록 필요)")


# --------------------------------------------------------------------------- #
#  JSON 로드 (graceful — 없으면 빈 dict)
# --------------------------------------------------------------------------- #
def _load(path):
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except Exception as e:
            print(f"⚠ {os.path.basename(path)} 파싱 실패: {e}")
    return {}


J = _load(FREESPACE_JSON)
JV = _load(VERIFY_JSON)
HAVE_JSON = bool(J)
if not HAVE_JSON:
    print(f"⚠ {os.path.relpath(FREESPACE_JSON, ROOT)} 없음 → 숫자는 placeholder('—')로 조립")

# 헤드라인 기준 축(선언) — 대표 기체·모드·전력규약·기준채널·N.
HEAD_DRONE = "mavic4pro"        # 프로젝트 메인 뷰 타깃(대표 기체). 캡션에 명시.
HEAD_MODE = "L1"                # LTE CRS(상시)
HEAD_VIEW = "equal_psd"         # 점유축 정본
HEAD_REF = "full_waveform_capture"


# --------------------------------------------------------------------------- #
#  네비게이션 · 포맷 헬퍼 (키/값 없으면 placeholder)
# --------------------------------------------------------------------------- #
def _g(*path, default=None, root=None):
    """중첩 dict 를 안전하게 탐색. 도중 키가 없으면 default."""
    cur = J if root is None else root
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def _f(x, fmt="{:.0f}", d="—"):
    """수치면 포맷, 아니면 placeholder."""
    try:
        if x is None:
            return d
        return fmt.format(float(x))
    except (ValueError, TypeError):
        return d


def _range_leaf(drone, mode, *leaf, default=None):
    """ranges[drone][mode][HEAD_VIEW][HEAD_REF].by_N['1'].<leaf>"""
    return _g("ranges", drone, mode, HEAD_VIEW, HEAD_REF, "by_N", "1", *leaf, default=default)


def _headline_range(*leaf, default=None):
    """ranges[HEAD_DRONE][HEAD_MODE][HEAD_VIEW][HEAD_REF].by_N['1'].<leaf>"""
    return _range_leaf(HEAD_DRONE, HEAD_MODE, *leaf, default=default)


def _s(lines):
    out = "\n".join(lines).splitlines(keepends=True)
    return out if out else [""]


def md(*l):
    return {"cell_type": "markdown", "metadata": {}, "source": _s(list(l))}


def fig(name, alt=""):
    return md(f"![{alt}](outputs/figures/{name}.png)")


def gif(name, alt="", sub=""):
    body = f"![{alt}](outputs/renders/anim/{name}.gif)"
    if sub:
        body += f"\n\n<sub>{sub}</sub>"
    return md(body)


# --------------------------------------------------------------------------- #
#  헤드라인 숫자 추출 (전부 JSON — 없으면 '—')
#  ⚠ **경로는 생산자가 실제로 쓰는 키여야 한다.** 없는 키를 읽으면 (a) 조용히 '—' 가 본문에 박히거나
#    (b) 더 나쁘게 모듈 기본값이 JSON 주입값처럼 보인다. 그래서 헤드라인에 들어가는 값은 전부
#    `_need()` 를 통과시키고, 파일 맨 끝에서 `_MISSING` 을 크게 출력한다(조용한 실패 금지).
# --------------------------------------------------------------------------- #
_MISSING = []


def _need(val, where):
    """헤드라인 문장에 쓰이는 값 — 없으면 조용히 넘기지 않고 경로를 기록한다."""
    if val is None:
        _MISSING.append(where)
    return val


def _solve_val(key, default=None):
    """solve[HEAD_MODE].<key> — 보고한 거리 역해에 **실제로 쓰인** 실행 파라미터."""
    v = _g("solve", HEAD_MODE, key)
    if v is None:
        for s in (_g("solve", default={}) or {}).values():
            if isinstance(s, dict) and s.get(key) is not None:
                v = s[key]
                break
    return default if v is None else v


def _views_in_ranges():
    """ranges 트리에 실재하는 뷰(전력규약) 키 목록."""
    return sorted({k for d in (_g("ranges", default={}) or {}).values() if isinstance(d, dict)
                   for mv in d.values() if isinstance(mv, dict) for k in mv})


def _canon_view():
    """정본 점유·전력규약 뷰 이름과 **그것이 JSON 에서 온 값인지** 여부.

    (1) meta.link_budget.power_normalization.canonical_occupancy (생산자 정본)
    (2) verify_freespace.json 의 canonical_occupancy_view 선언
    (3) ranges 트리에 뷰가 하나뿐이면 그 키
    셋 다 없으면 모듈 상수를 쓰되 '(선언)' 을 붙여 **주입값이 아님을 드러낸다**."""
    v = _g("meta", "link_budget", "power_normalization", "canonical_occupancy")
    if not v:
        v = _g("checks", "cpi_M_from_prf", "canonical_occupancy_view", root=JV)
    if not v:
        vs = _views_in_ranges()
        v = vs[0] if len(vs) == 1 else None
    return (str(v), True) if v else (HEAD_VIEW, False)


EIRP = _f(_need(_g("meta", "link_budget", "eirp_dbm"), "meta.link_budget.eirp_dbm"), "{:.0f}")
NORM, _norm_injected = _canon_view()
if not _norm_injected:                       # 상수를 주입값처럼 보이게 두지 않는다
    _MISSING.append("meta.link_budget.power_normalization.canonical_occupancy")
    NORM = f"{NORM}(선언)"
_tcpi = _need(_solve_val("T_cpi_s"), "solve.<mode>.T_cpi_s")
T_CPI_MS = _f(_tcpi * 1000 if isinstance(_tcpi, (int, float)) else None, "{:.0f}")
REQ = _f(_need(_headline_range("R_eq_at_R90_m"), "ranges…R_eq_at_R90_m"), "{:.0f}")
EPD = _f(_need(_headline_range("E_psi_Pd_at_R90"), "ranges…E_psi_Pd_at_R90"), "{:.2f}")
R60 = _f(_need(_headline_range("R_dpi_resid_m", "60"), "ranges…R_dpi_resid_m.60"), "{:.0f}")
NLOCAL = _f(_need(_headline_range("n_local_at_R90"), "ranges…n_local_at_R90"), "{:.2f}")
EL_HEAD = _f(_need(_headline_range("el_look_at_R90_deg"), "ranges…el_look_at_R90_deg"), "{:+.1f}")

# 커버리지 밴드 — C50(헤딩 50% 가 Pd≥0.9)과 C25(25%)는 **서로 다른 키**다. 이번 산출처럼 둘이
# 같으면(C25 는 대량 실행 집계 몫) 폭 0 밴드를 찍지 않고 단일값 + 사유로 적는다.
_c50 = _need(_headline_range("R90_C50_m"), "ranges…R90_C50_m")
_c25 = _headline_range("R90_C25_m")
DHZ = _f(_c50, "{:.0f}")                                     # 중점수평 d = R90_C50
if isinstance(_c50, (int, float)) and isinstance(_c25, (int, float)):
    _lo, _hi = sorted((float(_c50), float(_c25)))
    BAND = (f"C50 = C25 = {_lo:.0f} m (C25 는 대량 실행 집계 몫이라 이번 산출에선 C50 과 같다)"
            if _hi - _lo < 1.0 else f"C50–C25 {_lo:.0f}–{_hi:.0f} m")
else:
    BAND = f"C50 {DHZ} m (C25 미산출)"

_blind = _need(_range_leaf(HEAD_DRONE, "G1", "blind_heading_frac"), "ranges…G1…blind_heading_frac")
BLIND = _f(_blind * 100 if isinstance(_blind, (int, float)) else None, "{:.0f}")
SSB_M = _f(_need(_g("waveforms", "G1", "M"), "waveforms.G1.M"), "{:.0f}")
SSB_PRF = _f(_need(_g("waveforms", "G1", "prf_hz"), "waveforms.G1.prf_hz"), "{:.0f}")

# 5G 이중고 배치대가(equal_psd → deploy 유휴 gNB) — F2. 부호는 G3 기준 '차'라 음수이므로
# 본문에는 **낙폭(양수)** 으로 넣는다("약 −17 dB 낮다" 같은 이중부정 방지).
_nr_idle = _need(_g("meta", "link_budget", "power_normalization",
                    "radiated_power_frac_db_vs_g3", "nr", "G1"),
                 "meta.link_budget.power_normalization.radiated_power_frac_db_vs_g3.nr.G1")
NR_IDLE_DROP = _f(-float(_nr_idle) if isinstance(_nr_idle, (int, float)) else None, "{:.1f}")

# k_mode 닫힌형 잔차(신뢰 근거, §7)
K_RESID = _f(_need(_g("calib", "G1", "resid_db"), "calib.G1.resid_db"), "{:+.3f}")

# FS-0 모드간 SNR90 동일성 — **검증에 실제로 들어간 모드 수**와 퍼짐(verify_freespace.json)
_fs0 = _g("checks", "fs0_mode_snr90", root=JV) or {}
FS0_N = _f(_need(len(_fs0.get("snr90_by_mode") or {}) or None,
                 "verify_freespace…fs0_mode_snr90.snr90_by_mode"), "{:.0f}")
FS0_SPREAD = _f(_need(_fs0.get("fs0_mode_snr90_spread_db"),
                      "verify_freespace…fs0_mode_snr90_spread_db"), "{:.2f}")

# 보고 범위(기종·모드·뷰)는 **JSON 이 실제로 담은 것**에서 센다(스펙 의도가 아니라 산출물 기준).
_RANGE_TREE = _g("ranges", default={}) or {}
SCOPE_DRONES = sorted(_RANGE_TREE.keys())
SCOPE_MODES = list(_g("meta", "modes", default=[]) or []) or sorted(
    {m for d in _RANGE_TREE.values() if isinstance(d, dict) for m in d})
_VIEW_LABEL = {"equal_psd": "equal-PSD", "equal_total": "equal-total", "deploy": "deploy-EIRP"}
VIEWS = " | ".join(_VIEW_LABEL.get(v, v) for v in _views_in_ranges()) or NORM
SCOPE = (f"{len(SCOPE_DRONES)}기종 × {len(SCOPE_MODES)}모드({'·'.join(SCOPE_MODES)})"
         if SCOPE_DRONES and SCOPE_MODES else "이번 산출 범위")


# --------------------------------------------------------------------------- #
#  §15 신뢰 경계 (전량 — 정직성 규칙). JSON 무관 상수 서사.
# --------------------------------------------------------------------------- #
CAVEATS = [
    "**\"실제 검지거리 N m\"라고 말할 수 없다.** EIRP·G_rx(10dBi)·NF(5dB)·마스트25m·RX3m·고도·속도가 "
    "**전부 선언값**(근거문서 없음, 코드 주석이 유일). 결과는 '선언한 예산 아래의 거리'다. "
    "외삽 정직성은 선행 템플릿을 따른다 — Sun 외(*POSTER: Passive Drone Localization Using LTE Signals*, "
    "ACM WiSec '22)는 검출반경 20 m 실측을 셀타워 링크버짓으로 넓혀 지오펜싱 **면적**으로 보고한다. "
    "**검증된 것은 체인이지 거리가 아니다.**",
    "**이 편만 FS-1(자유공간)이다 — 챔버 상한선이 아니라 기준정규화다.** 평면지면만으로 F⁴∈[−20,+11.5]dB"
    "(거리 0.32~1.94배) 변조(FS-3). 실외는 클러터·다중경로·간섭까지 더해 **다를** 뿐 반드시 나쁘진 않다.",
    "**낙관 방향**: (a) 무클러터·무지면(FS-1)은 상한 아님(FS-3가 방향 보임) (b) 기준채널=무잡음 "
    "full-waveform(현실 2채널 CAF 아님) (c) 비요동은 **CPI 내부**만(inter-look 은 E_ψ[Pd]로 포함) "
    "(d) SBR+PO few-λ 낙관.",
    "**σ 절대값 ±수 dB 앵커.** 격자불확실성·편파 없음(스칼라|Γ|)·PTD/크리핑파 없음. Mavic4Pro·Matrice4E "
    "실측RCS 문헌 없음. 신뢰도가 (기종×밴드)마다 다름(mini5pro@LTE 2.32λ 최악) — D/λ 지도로.",
    "**널깊이·σ_min·aspect-peak 인용 금지.**",
    "**바이스태틱 σ는 β≲90°만 유효**(전방산란 σ≡0). 근거리·큰 L 은 걸림 — 해칭·수치금지. 상반성 깊은널 rms 5~9dB.",
    "**ECA는 무한이상화가 아니다.** 정본 ridge_rel=0 은 측정상 사실상 이상적(잔류≈0). 진짜 낙관은 **실장 "
    "유한 소거깊이**(통상 40~90dB)·위상잡음·상호변조가 모델에 없다는 것 → `dpi_residual` 감도축으로 정량화.",
    "**ADC는 1차근사.** 균일양자화+백색. AGC·SFDR·상호변조 미모델. '12-bit 가 벽'이라 단정 안 함(조건부).",
    "**검출기 형상 둘·성격 다름.** S-G(게이트)=탐색없는 거리, S-W(전체창)=CPI당 오경보 수(분해능셀 기준). "
    "검출정의=표적근방 문턱초과(전역 argmax 아님).",
    "**N^¼ 이득은 이상적 상한**(완전코히런트·완벽조향·무상관). 개구는 밴드마다 다름.",
    "**기준=full-waveform capture 정본** — 패시브인데 상시신호만은 아니라는 유보 승계(pilot-only 병기).",
    "**CAF 2채널 승격 안 함** — 이상적 레퍼런스 정합필터 SNR(report12 동일 열린과제).",
    "**문헌 실적치와 우열비교 안 함**(`prior_compare` 조건열 강제). 특히 (a) Rzewuski 외(NATO "
    "STO-MP-MSG-SET-183)의 D0 = 8 dB 는 '연속 조명 + 높은 갱신율' 을 근거로 한 **트랙 레벨** 문턱이라 우리 "
    "**단일 CPI** 문턱과 나란히 놓지 않는다. (b) 모드별 D0 를 선행 링크버짓 식에 갈아끼우지 않는다 — "
    "모드마다 경험 Pfa 가 다르다(report10). (c) Sun 외(ACM WiSec '22)와 Ji 외(IEEE WCL 2026, "
    "arXiv:2602.08203, 알루미늄박을 씌운 25×20×40 cm 상자를 매단 쿼드콥터)의 표적은 **반사체를 붙인 개조 "
    "상태**라 맨몸 드론 실적으로 인용하지 않는다.",
    "**호버·저속·앨리어싱 미검출은 거리무관.** 유휴 5G SSB(PRF50Hz)는 v=5m/s 전 헤딩 접힘 — 거리 이전에 "
    "도플러로 죽는다(하한 hover-blind + 상한 나이퀴스트 둘 다).",
    "**자세=수평(roll=pitch=0)·yaw만.** 실전 진비행 pitch 10~30° 미모델 — **모른다**.",
    "**el 격자 보간**: el≤−15° 는 β>90° 겹쳐 표본 적음. 헤드라인 el≈−2° 라 부호정정 효과는 헤드라인서 "
    "작다(d≲400m 한정). el>0(공중조명원) 범위 밖.",
    "**원거리장**: s1000plus@5.21G 63.1m 최악. 그 아래 σ 인용 안 함.",
    f"**'{SCOPE} 한 규약 선행사례 확인 못함'까지만** — 부재증명 아님, '최초' 안 씀.",
    "**단일 CPI·단일 표적.** 스캔누적·M-of-N·트래킹 없음(future work). 상호그림자 없음.",
    "**대기감쇠·전파수평선은 숫자와 함께 무시**(FS-1엔 항 자체 없음, FS-3서만): 산소흡수 5km<0.1dB, "
    "수평선≈39km≫20km.",
    "**비단조·천장.** SNR(d)는 φ의 다수서 내부최대 — 이분법 무효, 최외곽교차로 해결. 천장보다 어두운 "
    "헤딩은 어떤 거리서도 미검출(거리문제 아니라 해 없음).",
    "**비선형.** R∝σ^¼ 는 R_eq 축서만 정확. d 축 국소지수 1.03~4.00 이라 dB↔배율 환산 금지. "
    "k_mode(곱셈상수)는 이 기하 비선형 흡수 못함.",
    "**동일채널 간섭** 한 항으로 거리 한자릿수 감소 가능(INR20dB 이웃셀) — 감도축으로만, 정본엔 미포함.",
    "**파형↔반송파 결속.** 등전력만으론 파형효과 미분리 — 공통3.5GHz 반사실로 5항 분해. '어느 파형이 멀리 "
    "보나'는 밴드·σ(f)·반복률·fs선택의 합성이다.",
]


# =========================================================================== #
#  노트북 셀 조립
# =========================================================================== #
cells = []
cells += provenance_cells(
    report="report13",
    what="자유공간 드론 검지거리 (FS-1)",
    question="챔버(report01~12)를 벗어나 반사체 없는 자유공간이라면, 이 드론들을 어떤 통신 신호로 몇 m 에서 잡나?",
    spine=dict(
        core=(f"앞 리포트의 표적(SBR σ)·신호(Sionna PHY)·검출기(레이더 DSP)를 **자유공간(FS-1)** 무대에 "
              f"올려, **Pd 0.9 @ 셀당 Pfa 1e-4·단일 CPI·이상 DPI소거 기준 검지거리**를 닫힌형+측정으로 낸다. "
              f"헤드라인은 LTE CRS(L1)·전력규약 {NORM}·T_CPI {T_CPI_MS} ms 에서 대표 기체({HEAD_DRONE}) "
              f"R_eq **{REQ} m**(중점수평 d {DHZ} m). ★새 정보는 σ(음의 앙각)와 **기하(Cassini·비단조·천장)**다."),
        gap=("Sionna 는 경로·도플러·렌더(RT)와 파형·채널(PHY)은 담보하나, **표적 σ 는 산란적분 부재로 못 "
             "내고**(report06), **패시브 레이더 검출 파이프라인은 아예 없다**. FS-1 에는 챔버의 정적 클러터가 "
             "**애초에 없어**(죽은 파라미터), 그 자리를 §6 '벽 지도'(열잡음·ADC·DPI잔류·range-walk)가 대신한다."),
        prior=(f"패시브 바이스태틱 드론탐지 선행은 표적 산란을 외부에서 구해 채널에 주입(h=h_bg+h_target)하고 "
               "표준 검출 체인(ECA/CAF/CFAR)으로 잡는다. **검지거리를 보고하는 규약은 선행 것을 따른다** — "
               "Cassini oval 형태의 최대검지영역과 링크버짓 전항목 공개(Table I 형식)는 "
               "Maksymiuk·Abratkiewicz·Samczyński, *UAV Intrusion Detection with Passive Radar Based on the "
               "5G Network*(59th Asilomar Conference on Signals, Systems, and Computers, 2025, "
               "DOI 10.1109/IEEECONF67917.2025.11443758) 식 (8)·(9) 의 규약이고, 등가 모노스태틱 축 "
               "**R_eq=√(R1·R2)** 는 같은 연구팀의 *Remote Sensing* 14(23):6146(2022, DOI 10.3390/rs14236146), "
               "**검지거리를 단일 숫자가 아니라 Pfa 의 함수로** 내는 규약은 Demissie 외(*2024 International "
               "Radar Conference (RADAR)*, LTE450 실측)에서 왔다. WiFi 대역 커버리지를 RCS_min 으로 다룬 "
               "Rzewuski·Kulpa 외(NATO STO-MP-MSG-SET-183)는 σ 자릿수 대조(§2)와 문턱 정의 구분(§8)에만 쓴다. "
               "조사한 선행은 대개 **단일 조명원·챔버 없는 실외**라, "
               f"**{SCOPE} 를 한 규약으로 검지거리 비교한 사례는 확인하지 못했다**(부재증명 아님)."),
        lib=("σ 는 **SBR+PO**(Mitsuba 광선+PO 표면적분), 에코 지연펄스정형은 **Sionna PHY** 커널, 검출은 "
             "**pyAPRiL 로 검증된 ECA/CFAR 체인**(radar-dsp), 렌더는 **Sionna RT**(sionna-render). 새 파형·산란 "
             "엔진을 만들지 않고 검증된 조각만 자유공간 예산으로 결합한다."),
        verify=(f"FS-0 SNR90 동일성({FS0_N}모드, 퍼짐 {FS0_SPREAD} dB)·닫힌형 링크버짓 대조"
                f"(k_mode 잔차 {K_RESID} dB)·ECA바닥(ridge=0 "
                f"잔류≈0)·이등분선↔멀티스태틱 Δσ(β)·나이퀴스트폴드·챔버 되돌리기. 절대 σ 는 실측 문헌 드론 "
                f"RCS 로 앵커(report08)."),
    ),
    sources=[
        dict(item="검지거리·커버리지·감도·벽지도", src="outputs/report13_freespace.json",
             kind="닫힌형 전파 + 몬테카를로 문턱측정"),
        dict(item="표적 밝기 σ (음의 앙각 격자·멀티스태틱)", src="outputs/report13_sigma_grid.json → SBR(Mitsuba+PO)",
             kind="SBR+PO 배치계산 (GPU)"),
        dict(item="검증(닫힌형·ECA바닥·FS-0·챔버)", src="outputs/verify_freespace.json",
             kind="교차검증"),
        dict(item="절대 σ 앵커", src="공개 문헌 드론 RCS (report08)", kind="외부 앵커 (±수 dB)"),
    ],
    engines=ENGINES,
    libs=["sionna", "mitsuba", "torch", "numpy", "matplotlib", "Pillow"],
    reproduce=[
        "# σ격자(GPU 3~4장 ~1.5h)",
        "SIONNA2_GPU=3 PYTHONPATH=src:benchmark python src/experiment_freespace_sigma.py",
        "# 문턱·거리역해·감도·벽지도(GPU 1~2장 ~2~4h)",
        "PYTHONPATH=src:benchmark python src/experiment_freespace_range.py --stage=all",
        "# 검증 / 그림 / RT렌더 / 이 노트북",
        "PYTHONPATH=src:benchmark python benchmark/verify_freespace.py",
        "PYTHONPATH=src:benchmark python src/viz_report13.py",
        "SIONNA2_GPU=3 PYTHONPATH=src:benchmark python src/render_report13.py --which all",
        "PYTHONPATH=src:benchmark python src/make_notebook13.py",
    ],
    artifacts=[
        dict(file="outputs/report13_freespace.json", what="검지거리·커버리지·감도·벽지도(모든 본문 숫자의 출처)"),
        dict(file="outputs/report13_sigma_grid.json", what="음의 앙각 σ 격자·멀티스태틱·D/λ·공통반송파 반사실"),
        dict(file="outputs/verify_freespace.json", what="닫힌형·ECA바닥·FS-0·챔버 되돌리기 검증"),
        dict(file="outputs/figures/report13_*.png", what="그림 F1~F16"),
        dict(file="outputs/renders/anim/r13_*.gif", what="RT/도식 GIF R1~R8"),
        dict(file="outputs/renders/r13_*.png", what="RT 스틸 22장"),
    ],
    caveats=CAVEATS,
    cost="σ격자 GPU 3~4장 ~1.5h · 문턱MC GPU 1~2장 ~2~4h · 렌더 1장 ~60min · 그림/노트북 CPU ~30min",
    related=[
        dict(rep="report06~08", rel="표적 σ (Sionna 한계·SBR·RCS 결과) — 이 편이 소비하는 밝기"),
        dict(rep="report12", rel="챔버 안 9모드 벤치마크 — 이 편은 그 검출기를 **자유공간 예산**으로 옮긴 것"),
        dict(rep="report09~11", rel="바닥유령·CFAR교정·관측성 — FS-3 정직성 점검·벽 지도의 뿌리"),
    ],
    glossary=[
        ("FS-0/1/2/3 (가정 사다리)",
         "FS-0=표적에코+열잡음 상한, **FS-1=+직접파·ECA·0도플러가드(헤드라인)**, FS-2=+ADC양자화, "
         "FS-3=+평면지면 2-ray(정직성 점검). FS-1 은 **상한이 아니라 기준정규화**다."),
        ("R1 / R2 / R_b / R_eq",
         "R1=TX→표적, R2=표적→RX, R_b=R1+R2−L(바이스태틱 거리), **R_eq=√(R1·R2)**(σ^¼ 이 정확한 축). "
         "d=중점 수평거리(장면을 펼치는 축)."),
        ("커버리지 C(d) / E_ψ[Pd]",
         "C(d)=거리 d 에서 Pd≥0.9 인 **헤딩의 비율**. E_ψ[Pd]=헤딩 평균 검출확률. 단일 '검지거리'가 아니라 "
         "**분포**로 말한다."),
        ("점유·전력규약 (equal_psd/equal_total/deploy)",
         "같은 조명을 어떻게 정규화하나. **equal_psd**(정본)=per-RE 송신전력 동일 → 시간희소 SSB(G1)의 낮은 "
         "평균방사전력을 물리반영. deploy=배치현실(유휴 gNB≠풀 gNB). ⚠ 선행 링크버짓 식으로 옮길 때 "
         "**점유 F(Asilomar 식 (9))와 듀티 F_u(Rzewuski 식 (4))는 택일**이다 — 같은 손실의 대체 "
         "파라미터화라 곱하면 이중계상이다(§4)."),
        ("5G 이중고 (SSB)",
         "유휴 5G SSB(G1)는 반복률 50Hz·협대역 7.2MHz라 **거리도 속도도 나쁘다** — 상시 3인방 중 꼴찌. "
         "PRS(측위세션)면 전대역이지만 상시는 아니다."),
        ("dpi_residual (실장 유한 소거)",
         "실제 ECA·아날로그 소거는 무한이 아니다(40~90dB). 그 잔류 직접파가 만드는 잡음바닥 → 자유공간 최대 벽."),
    ],
)


# --------------------------------------------------------------------------- #
#  본문 §0 ~ §8 (spec §13 표)
# --------------------------------------------------------------------------- #
def _numnote():
    if HAVE_JSON:
        return ""
    return ("\n\n> ⚠️ **`outputs/report13_freespace.json` 이 아직 없어 숫자는 `—` 로 표시됩니다.** "
            "실험(experiment_freespace_range.py)을 돌린 뒤 이 생성기를 재실행하면 채워집니다.")


# ── §0 왜 챔버를 벗어나나 ────────────────────────────────────────────────────
cells.append(md(
    "## §0 — 왜 챔버를 벗어나나 (가정 사다리 FS-0/1/2/3)", "",
    "report01~12 는 30×20×11 m 무향실 **안**의 실험이었다. 이 편은 **반사체가 없는 자유공간(FS-1)** 을 "
    "가정한다. 다만 자유공간은 **상한선이 아니라 기준정규화**다 — 평면지면 하나만 놓아도(FS-3) 에코가 "
    "F⁴∈[−20,+11.5]dB 로 흔들린다(정직성 점검). 사다리:",
    "",
    "| 단계 | 포함 | 재는 것 | 헤드라인 |",
    "|---|---|---|---|",
    f"| **FS-0** | 표적에코+열잡음 | 열잡음 상한, {FS0_N}모드 SNR90 동일성 | — |",
    "| **FS-1** | +직접파·ECA(ridge=0)·0도플러가드·이상 DPI소거 | **보고하는 R90** | ✅ |",
    "| **FS-2** | +ADC 양자화 | 동적범위 벽(조건부) | — |",
    "| **FS-3** | +평면지면 2-ray·fresnel·대기감쇠 | 정직성 점검(자유공간은 상한 아님) | — (동반) |",
    "",
    "**\"반사체가 전혀 없는 자유공간\"을 명시적 연구대상으로 삼은 패시브 드론 검출 선행은 확인하지 못했다.** "
    "문헌은 야외 실측이거나 도시 매크로셀 가정이고, Demissie 외(*2024 International Radar Conference "
    "(RADAR)*, LTE450 실측)는 CUT 최대전력의 진동을 **직접경로와 반사 하나의 간섭**으로 해석한다 — "
    "**야외 실측조차 자유공간이 아니다**. 그래서 FS-1 은 비교 대상이 아니라 **이상화**다. 선행도 같은 성격의 "
    "유보를 단다: Maksymiuk 외(59th Asilomar 2025)는 자기 검지거리 예측에 \"these predictions assume the "
    "target is located at the center of the base station antenna beam, which represents an **idealized "
    "scenario**\" 라고 명시한다.",
    _numnote(),
))
cells.append(fig("report13_geometry", "자유공간 바이스태틱 기하 — 거리 셋, 측정 하나"))
cells.append(gif("r13_geometry_orbit", "챔버가 사라진 순간 — 자유공간 바이스태틱 기하 궤도",
                 "TX 마스트(25m)·RX(3m)·표적. 바닥·벽 없음. 실제 베이스라인은 압축했고 프레임에 'scale break' 를 표기한다."))
cells.append(fig("report13_chamber_vs_freespace_and_ground",
                 "report01~12(챔버)가 R_b 축의 어디 있고, 평면지면(FS-3)이 무엇을 할지"))


# ── §1 거리가 셋이다 ────────────────────────────────────────────────────────
cells.append(md(
    "## §1 — 거리가 셋이다 (R1 · R2 · R_b · R_eq)", "",
    "바이스태틱은 왕복이 아니다. **R1**(TX→표적)·**R2**(표적→RX)·**R_b=R1+R2−L**(바이스태틱 거리)가 다르고, "
    "σ→거리 사상이 정확한 축은 **R_eq=√(R1·R2)** 다. 같은 R_b 는 TX·RX 를 초점으로 한 타원, 같은 SNR 은 "
    "**Cassini oval** 을 그린다 — 이 기하가 커버리지를 접는다.",
    "",
    "이 두 축은 선행 규약을 그대로 쓴 것이다. Cassini oval 형태의 최대검지영역과 링크버짓 전항목을 표 하나에 "
    "공개하는 형식(Table I)은 Maksymiuk 외(59th Asilomar Conference on Signals, Systems, and Computers, "
    "2025) 식 (8)·(9), 등가 모노스태틱 축 **R_eq=√(R1·R2)** 는 같은 연구팀의 *Remote Sensing* "
    "14(23):6146(2022)에서 왔다. 다만 선행은 문턱 D0 를 10/15/20 dB 로 **가정하고 스윕**하는 반면, 이 편의 "
    "D0 는 §3 에서 몬테카를로로 **측정**한다.",
    "",
    f"> **헤드라인.** EIRP {EIRP} dBm(in-burst peak)·전력규약 {NORM}·T_CPI {T_CPI_MS} ms·Pd 0.9 @ 셀당 "
    f"Pfa 1e-4·단일 CPI·이상 DPI소거(∞ dB) 기준, 자유공간(FS-1) 검지거리는 **LTE CRS(L1)**·대표 기체 "
    f"`{HEAD_DRONE}` 에서 **R_eq {REQ} m**(중점수평 d {DHZ} m) [자세 커버리지 {BAND}], "
    f"헤딩평균 검출확률 E_ψ[Pd]={EPD}. **실장 소거 60 dB 기준 {R60} m.**",
))
cells.append(fig("report13_geometry", "거리 셋과 하나의 측정 — iso-R_b 타원 + Cassini oval"))
cells.append(gif("r13_cassini_baseline", "베이스라인 L 스윕 — Cassini 단일→이엽 (β>90° 해칭)",
                 "기하가 커버리지를 접는다 — L 을 늘리면 등감도선이 단일 오벌에서 두 잎으로 갈린다."))


# ── §2 표적 ────────────────────────────────────────────────────────────────
cells.append(md(
    f"## §2 — 표적 ({len(SCOPE_DRONES)}기종 · σ 는 방위와 앙각의 함수)", "",
    f"{len(SCOPE_DRONES)}기종은 **target_extent(메쉬 bbox 최대 수평치수) 오름차순**으로 고정한다: "
    "`mini5pro < phantom4 < mavic4pro < matrice4e < s1000plus`. σ 는 단일 숫자가 아니라 **(방위, 앙각)의 "
    "함수**다. 지상 TX/RX + 공중 표적이라 이등분선 앙각은 **전 구간 음수** — 우리는 드론의 **배(belly)** 를 본다.",
    "",
    "> **선행 σ 대조(자릿수 확인용이지 우열비교 아님).** Maksymiuk 외(59th Asilomar 2025)의 검지거리 예측은 "
    "표적 밝기를 Table I 에서 S0 = 0.1 m² 또는 0.05 m² 로 **가정**하고, 그 σ 의 정의(방위평균 여부·편파·"
    "바이스태틱각)는 밝히지 않는다. 소형 쿼드콥터를 독립 엔진으로 푼 값도 있다 — Rzewuski·Kulpa 외"
    "(NATO STO-MP-MSG-SET-183)는 Parrot AR.Drone 2.0(폴리프로필렌 기체 + 탄소섬유 크로스튜브·프로펠러)을 "
    "FDTD(QuickWave-3D)로 계산해 **WiFi 대역 σ −40 ~ 0 dBsm(평균 약 −20 dBsm)** 를 보고한다. "
    "⚠ 표적·해석엔진(FDTD vs SBR+PO)·편파(Eφ vs 스칼라 미분리)·앙각이 모두 달라 **사과-대-사과가 아니다**. "
    "위 격자가 그 자릿수를 벗어나지 않는지 보는 용도이며, 어느 쪽이 정확한지의 근거로는 쓰지 않는다.",
))
cells.append(gif("r13_five_lineup_orbit", "5기종 동일 축척 1열 궤도(target_extent 순)",
                 "메쉬·재질색·실제 크기 대비. 스케일바로 1 m 를 표시한다."))
cells.append(fig("report13_sigma_grid_5", "RCS σ(방위, 앙각≤0) — 5기종 @3.5 GHz (배를 올려다본다)"))
cells.append(gif("r13_aspect_mavic4pro", "기종별 자세각 다이얼 — yaw 0→360°(프롭 위상), 시선은 음의 앙각",
                 "좌: RT 드론 회전(이 모듈). 우 σ(ψ) 극좌표 다이얼은 matplotlib(viz_report13)가 합성한다."))


# ── §3 언제 보이나 ──────────────────────────────────────────────────────────
cells.append(md(
    "## §3 — 언제 보이나 (Pd(SNR) 측정 · 도플러 오프셋 · argmax 아님)", "",
    "검출 문턱은 **측정한다**(가정 12dB 아님): 몬테카를로로 Pd0.9 가 되는 RD 출력 SNR 을 찾고, Pfa 는 셀당 "
    "1e-4 로 경험 교정한다. 검출 정의는 **표적 근방(±2) 문턱 초과**(전역 argmax 아님). 전이곡선은 표적의 "
    "**도플러 오프셋**에 의존하므로 여러 오프셋 빈에서 잰다.",
    "",
    f"> **5G 이중고.** 유휴 5G SSB(G1)는 반복률 {SSB_PRF} Hz·협대역 7.2 MHz라 거리도 속도도 나쁘다: "
    f"대표 기체 `{HEAD_DRONE}` 기준 v=5 m/s 에서 헤딩의 **{BLIND}%** 가 도플러 블라인드다. 코히런트 적분도 "
    f"T_CPI {T_CPI_MS} ms 에 M={SSB_M} 프레임뿐이라 이득이 낮아 상시 3인방 중 꼴찌다.",
))
cells.append(fig("report13_detector", "측정한 Pd(SNR) + 경험 Pfa + 도플러 오프셋 의존"))
cells.append(gif("r13_rd_recede", "거리-도플러 맵의 표적 봉우리 소멸 — d 200 m → 5 km",
                 "실 MC RD맵(`passive_process.range_doppler`): 표적이 멀어질수록 거리빈이 밀려나가고 "
                 "봉우리가 잡음바닥으로 가라앉는다 — 검지거리가 '거리 문제'로 보이는 물리."))


# ── §4 몇 m 인가 ────────────────────────────────────────────────────────────
cells.append(md(
    "## §4 — 몇 m 인가 (R90_C50 + E_ψ[Pd] 병기 · 5G 꼴찌)", "",
    "단일 '검지거리'는 없다. **R90_C50**(헤딩의 50%가 Pd≥0.9 인 최외곽 거리)와 **E_ψ[Pd]**(헤딩 평균 검출확률)를 "
    "**함께** 말한다. 커버리지 밴드는 C50–C25 이며, 커버리지 천장 C_max=1−b_blind 상대다(b_blind>10%면 C10 은 미정의). "
    f"헤드라인 밴드는 {BAND}.",
    "",
    f"> 전력규약을 배치현실(deploy)로 바꾸면 **유휴 5G(NR G1)가 무너진다**: 유휴 gNB 는 SSB 만 켜므로 같은 "
    f"per-RE 전력에서 **평균 방사전력**이 풀 gNB(점유 G3) 대비 약 {NR_IDLE_DROP} dB 낮다. 보고한 거리는 "
    f"{NORM} 뷰이고, 이 낙폭은 자원격자 점유율에서 나온 **전력 항**이다 — 상시 3인방 순위 전복은 이 "
    f"프로젝트의 핵심 서사(5G 이중고)다.",
    "",
    "**단일 숫자를 내지 않는 것도 선행 규약이다.** Demissie 외(*2024 International Radar Conference "
    "(RADAR)*)는 같은 실험·같은 기체(DJI Matrice M210, 88×88×39 cm)에서 오경보율만 Pfa 1e-2 → 1e-4 로 "
    "조이자 최대 바이스태틱 검지거리가 **2700 m → 약 1500 m** 로 줄어드는 것을 실측으로 보였다 — "
    "**Pfa 를 밝히지 않은 검지거리는 무의미하다.** 이 편의 모든 거리는 셀당 Pfa 1e-4 · Pd 0.9 · 단일 CPI 에 "
    "고정된 위에서 커버리지 밴드로 낸다.",
    "",
    "> ⚠ **점유 F 와 듀티 F_u 는 곱하지 않는다(택일).** Asilomar 식 (9)에는 적분시간 동안의 자원격자 점유율 "
    "**F** 만 들어가고, Rzewuski 식 (4)에는 **F_u**(duty factor — WiFi 는 패킷 전송이라 적분구간 내내 신호가 "
    "있지 않다는 뜻) 만 들어간다. 둘은 **같은 물리손실의 대체 파라미터화**이지 곱할 대상이 아니다 — 함께 "
    "넣으면 같은 손실을 두 번 매긴다. 우리 점유축(`occ_pct` · equal_psd)이 시간축 희소성을 이미 포함하는지 "
    "정의가 확정되기 전까지는 **둘 중 하나만** 쓴다. 선행 식에 우리 점유를 대입할 때는 대역 B 도 모드별 "
    "`ref_bw_mhz` 로 **함께** 치환해야 한다 — B 를 선행 고정값(50 MHz)에 둔 채 F 만 바꾸면 협대역 SSB 가 "
    "광대역과 같은 적분이득을 받는 **존재하지 않는 하이브리드**가 된다.",
))
cells.append(fig("report13_range_bars",
                 "자유공간 검지거리 — 5기종 × 상시 3인방 (채운 띠=C25–C50, 캡=CI95)"))
cells.append(fig("report13_matrix", f"R90 행렬 — {SCOPE} · {VIEWS} 뷰"))
cells.append(fig("report13_coverage_curves", "커버리지 C(d) 와 평균 Pd — 헤딩 비율 vs 헤딩평균"))


# ── §5 왜 밴드가 넓나 ───────────────────────────────────────────────────────
cells.append(md(
    "## §5 — 왜 밴드가 넓나 (σ 파이프라인 추정량 · R_eq 축 · 분산이 결론)", "",
    "검지거리 밴드의 정체는 **σ의 자세 분산**이다. 밴드는 파이프라인과 **동일한 추정량**(5점 m² 평균, 음의 "
    "앙각)으로 재산출하고, dB↔배율 환산은 하지 않는다(국소지수 n_local 병기, R_eq 축서만 σ^¼ 정확).",
    "",
    f"> **분산이 결론.** d≳1 km 에서는 **자세**가, 그 아래에서는 **기하(φ)**가 분산을 지배한다. 헤드라인 "
    f"지점의 국소지수 n_local≈{NLOCAL}, 앙각 el≈{EL_HEAD}°. (전 캡션 φ=90° 명시.)",
))
cells.append(fig("report13_sigma_to_range", "RCS 분포에서 거리 분포로 (파이프라인 추정량)"))
cells.append(fig("report13_heading_footprint",
                 "표적 헤딩 대 거리 — 자세·도플러 블라인드·앨리어싱이 한 축에서 작용"))
cells.append(fig("report13_elevation", "배를 올려다본다 — σ vs (음의) 이등분선 앙각, 헤드라인의 위치"))


# ── §6 무엇이 거리를 정하나 ─────────────────────────────────────────────────
cells.append(md(
    "## §6 — 무엇이 거리를 정하나 (벽 지도: 열잡음·ADC·DPI잔류·range-walk·INR)", "",
    "**어느 하나를 벽으로 세우지 않는다** — 셀마다 `limit` 라벨이 붙는다(`thermal/adc/dpi_residual/walk/"
    "farfield/beta/nonlinear`). 조명 전력은 R∝EIRP^¼, CPI 는 R∝T^¼ 로만 사는데, ADC·DPI잔류 바닥은 EIRP 와 "
    f"무관하다. **진짜 큰 벽은 dpi_residual**(실장 유한 소거)다 — 소거 60 dB 기준 헤드라인은 {R60} m 로 준다.",
    "",
    "range-walk 은 대역폭이 넓을수록 이르게 온다(ΔR_b=c/B → T_max=ΔR_b/v). 동일채널 간섭(INR)은 이웃 셀 "
    "하나로 거리를 한 자릿수 줄일 수 있어 감도축으로만 냈다.",
))
cells.append(fig("report13_eirp_ladder",
                 "거리는 조명 전력의 네제곱근으로 — ADC·DPI잔류 바닥은 그렇지 않다"))
cells.append(fig("report13_walls", "어느 벽이 붙나? thermal / ADC / DPI-residual / walk, 밴드·베이스라인별"))
cells.append(fig("report13_cpi_walk", "긴 CPI 는 R∝T^¼ 를 사지만 — range-walk(가장 좁은 벽)까지만"))
cells.append(fig("report13_resolution_vs_range", "대역폭은 위치를 사지 검출을 사지 않는다"))
cells.append(fig("report13_elevation", "헤드라인 앙각 효과가 작음을 정직 표기"))


# ── §7 믿어도 되나 ──────────────────────────────────────────────────────────
cells.append(md(
    "## §7 — 믿어도 되나 (닫힌형 대조 · ECA바닥 · 멀티스태틱 · 챔버 되돌리기)", "",
    f"측정 파이프라인은 닫힌형 링크버짓과 ±0.1 dB 로 맞는다(k_mode 잔차 {K_RESID} dB). ECA 바닥은 "
    "ridge_rel=0 에서 잔류≈0(설계 원안 1e-6 은 오히려 +25 dB 누설). 이등분선↔멀티스태틱 Δσ(β)·나이퀴스트 "
    f"폴드·FS-0 {FS0_N}모드 SNR90 동일성(퍼짐 {FS0_SPREAD} dB)·챔버 되돌리기(F16)까지 교차검증한다.",
))
cells.append(fig("report13_verify",
                 "검증 — 닫힌형 vs 측정, ECA 바닥(ridge=0), 이등분선 vs 멀티스태틱"))
cells.append(fig("report13_chamber_vs_freespace_and_ground",
                 "report01~12 의 위치와 평면지면(FS-3)이 할 일 — 정직성"))


# ── §8 말할 수 없는 것 ──────────────────────────────────────────────────────
cells.append(md(
    "## §8 — 말할 수 없는 것 (살아남은 한계 — 전량)", "",
    "> 정직함이 이 프로젝트의 규칙이다. 아래는 이 리포트가 **보장하지 않는 것들**이다(요약; 상세는 상단 "
    "프로venance §8️⃣ 과 동일).", "",
    *[f"{i+1}. {c}" for i, c in enumerate(CAVEATS)],
    "",
    "> ### ▶ 다음 일 (future work): 추적",
    "> 이 리포트는 **탐지**까지다. 위치·궤적을 잇는 **추적**은 감시 배열의 각도(AoA)로 3D 관측가능성을 "
    "확보해야 한다(report11). 본 실험이 쓴 다중 수신기 배열이 그 출발점이다.",
))


# =========================================================================== #
#  조용한 실패 방지 — 죽은 JSON 경로/남은 placeholder 를 **생성 시점에** 크게 알린다.
#  (2026-07-30: 생산자가 쓰지 않는 키 5개를 읽어 본문에 '— dB/ms/m' 가 실렸던 사고 재발 방지.)
# =========================================================================== #
_PH = re.compile(r"—\s*(dBsm|dBm|dB|ms|Hz|m|%|°)(?![A-Za-z가-힣])")
_hits = []
for _c in cells:
    for _ln in _c.get("source", []):
        if _PH.search(_ln):
            _hits.append(_ln.strip()[:120])
if HAVE_JSON and _MISSING:
    print(f"⚠⚠ JSON 에 없는 경로 {len(_MISSING)}개를 읽었다(본문이 placeholder 가 된다): {_MISSING}")
if _hits:
    print(f"⚠⚠ '—+단위' placeholder {len(_hits)}곳 잔존:")
    for _h in _hits:
        print(f"     · {_h}")
elif HAVE_JSON:
    print("✔ '—+단위' placeholder 0곳")

nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "py312", "language": "python", "name": "py312"},
                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
with open(NB, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print(f"✅ {os.path.relpath(NB, ROOT)}  ({len(cells)} cells)  |  "
      f"JSON={'있음' if HAVE_JSON else '없음(placeholder)'}  |  engines={ENGINES}")
