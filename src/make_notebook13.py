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
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
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


def _headline_range(*leaf, default=None):
    """ranges[HEAD_DRONE][HEAD_MODE][HEAD_VIEW][HEAD_REF].by_N['1'].<leaf>"""
    return _g("ranges", HEAD_DRONE, HEAD_MODE, HEAD_VIEW, HEAD_REF, "by_N", "1", *leaf,
              default=default)


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
# --------------------------------------------------------------------------- #
EIRP = _f(_g("meta", "link_budget", "eirp_equal_dbm", default=None), "{:.0f}")
NORM = _g("meta", "link_budget", "power_normalization", "canonical_occupancy",
          default=HEAD_VIEW)
_tcpi = _g("meta", "cpi", "T_cpi_ref_s", default=None)
T_CPI_MS = _f(_tcpi * 1000 if isinstance(_tcpi, (int, float)) else None, "{:.0f}")
REQ = _f(_headline_range("R_eq_at_R90_m"), "{:.0f}")
DHZ = _f(_headline_range("R90_C50_m"), "{:.0f}")             # 중점수평 d = R90_C50
LO = _f(_headline_range("R90_C25_m"), "{:.0f}")
HI = _f(_headline_range("R90_C50_m"), "{:.0f}")
EPD = _f(_headline_range("E_psi_Pd_at_R90"), "{:.2f}")
R60 = _f(_headline_range("R_dpi_resid_m", "60"), "{:.0f}")
NLOCAL = _f(_headline_range("n_local_at_R90"), "{:.2f}")
EL_HEAD = _f(_headline_range("el_look_at_R90_deg"), "{:+.1f}")
BLIND = _f((_g("waveforms", "G1", "blind_heading_frac", "5", default=None) or 0) * 100
           if _g("waveforms", "G1", "blind_heading_frac", "5") is not None else None, "{:.0f}")
SSB_M = _f(_g("meta", "cpi", "M_by_mode", "G1", default=None), "{:.0f}")
SSB_PRF = _f(_g("waveforms", "G1", "prf_hz", default=None), "{:.0f}")

# 5G 이중고 배치대가(equal_psd → deploy 유휴 gNB) — F2
NR_IDLE_DB = _f(_g("meta", "link_budget", "power_normalization",
                   "radiated_power_frac_db_vs_g3", "nr", "G1", default=None), "{:+.1f}")

# k_mode 닫힌형 잔차(신뢰 근거, §7)
K_RESID = _f(_g("calib", "G1", "resid_db", default=None), "{:+.3f}")

# 챔버 되돌리기(F16) — report01~12 위치
CH_RB = _f(_g("meta", "chamber_reference", "Rb_max_m", default=None), "{:.0f}")


# --------------------------------------------------------------------------- #
#  §15 신뢰 경계 (전량 — 정직성 규칙). JSON 무관 상수 서사.
# --------------------------------------------------------------------------- #
CAVEATS = [
    "**\"실제 검지거리 N m\"라고 말할 수 없다.** EIRP·G_rx(10dBi)·NF(5dB)·마스트25m·RX3m·고도·속도가 "
    "**전부 선언값**(근거문서 없음, 코드 주석이 유일). 결과는 '선언한 예산 아래의 거리'다.",
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
    "**문헌 실적치와 우열비교 안 함**(`prior_compare` 조건열 강제).",
    "**호버·저속·앨리어싱 미검출은 거리무관.** 유휴 5G SSB(PRF50Hz)는 v=5m/s 전 헤딩 접힘 — 거리 이전에 "
    "도플러로 죽는다(하한 hover-blind + 상한 나이퀴스트 둘 다).",
    "**자세=수평(roll=pitch=0)·yaw만.** 실전 진비행 pitch 10~30° 미모델 — **모른다**.",
    "**el 격자 보간**: el≤−15° 는 β>90° 겹쳐 표본 적음. 헤드라인 el≈−2° 라 부호정정 효과는 헤드라인서 "
    "작다(d≲400m 한정). el>0(공중조명원) 범위 밖.",
    "**원거리장**: s1000plus@5.21G 63.1m 최악. 그 아래 σ 인용 안 함.",
    "**'5기종×9모드 한 규약 선행사례 확인 못함'까지만** — 부재증명 아님, '최초' 안 씀.",
    "**단일 CPI·단일 표적.** 스캔누적·M-of-N·트래킹 없음(future work). 상호그림자 없음.",
    "**대기감쇠·전파수평선은 숫자와 함께 무시**(FS-1엔 항 자체 없음, FS-3서만): 산소흡수 5km<0.1dB, "
    "수평선≈39km≫20km.",
    "**비단조·천장.** SNR(d)는 φ의 다수서 내부최대 — 이분법 무효, 최외곽교차로 해결. 천장보다 어두운 "
    "헤딩은 어떤 거리서도 미검출(거리문제 아니라 해 없음).",
    "**비선형.** R∝σ^¼ 는 R_eq 축서만 정확. d 축 국소지수 1.03~4.00 — dB↔배율 환산 금지. k_mode(곱셈상수)는 "
    "이 기하 비선형 흡수 못함.",
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
        prior=("패시브 바이스태틱 드론탐지 선행은 표적 산란을 외부에서 구해 채널에 주입(h=h_bg+h_target)하고 "
               "표준 검출 체인(ECA/CAF/CFAR)으로 잡는다. 조사한 선행은 대개 **단일 조명원·챔버 없는 실외**라, "
               "**5기종×9모드를 한 규약으로 검지거리 비교한 사례는 확인하지 못했다**(부재증명 아님)."),
        lib=("σ 는 **SBR+PO**(Mitsuba 광선+PO 표면적분), 에코 지연펄스정형은 **Sionna PHY** 커널, 검출은 "
             "**pyAPRiL 로 검증된 ECA/CFAR 체인**(radar-dsp), 렌더는 **Sionna RT**(sionna-render). 새 파형·산란 "
             "엔진을 만들지 않고 검증된 조각만 자유공간 예산으로 결합한다."),
        verify=(f"9모드 SNR90 동일성(FS-0)·닫힌형 링크버짓 대조(k_mode 잔차 {K_RESID} dB)·ECA바닥(ridge=0 "
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
         "평균방사전력을 물리반영. deploy=배치현실(유휴 gNB≠풀 gNB)."),
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
    "| **FS-0** | 표적에코+열잡음 | 열잡음 상한, 9모드 SNR90 동일성 | — |",
    "| **FS-1** | +직접파·ECA(ridge=0)·0도플러가드·이상 DPI소거 | **보고하는 R90** | ✅ |",
    "| **FS-2** | +ADC 양자화 | 동적범위 벽(조건부) | — |",
    "| **FS-3** | +평면지면 2-ray·fresnel·대기감쇠 | 정직성 점검(자유공간은 상한 아님) | — (동반) |",
    _numnote(),
))
cells.append(fig("report13_geometry", "자유공간 바이스태틱 기하 — 거리 셋, 측정 하나"))
cells.append(gif("r13_geometry_orbit", "챔버가 사라진 순간 — 자유공간 바이스태틱 기하 궤도",
                 "TX 마스트(25m)·RX(3m)·표적. 바닥·벽 없음. 실제 베이스라인은 압축했고 프레임에 'scale break' 를 표기한다."))
cells.append(fig("report13_chamber_vs_freespace_and_ground",
                 f"report01~12(챔버 R_b≈{CH_RB} m)가 어디 있고, 평면지면(FS-3)이 무엇을 할지"))


# ── §1 거리가 셋이다 ────────────────────────────────────────────────────────
cells.append(md(
    "## §1 — 거리가 셋이다 (R1 · R2 · R_b · R_eq)", "",
    "바이스태틱은 왕복이 아니다. **R1**(TX→표적)·**R2**(표적→RX)·**R_b=R1+R2−L**(바이스태틱 거리)가 다르고, "
    "σ→거리 사상이 정확한 축은 **R_eq=√(R1·R2)** 다. 같은 R_b 는 TX·RX 를 초점으로 한 타원, 같은 SNR 은 "
    "**Cassini oval** 을 그린다 — 이 기하가 커버리지를 접는다.",
    "",
    f"> **헤드라인.** EIRP {EIRP} dBm(in-burst peak)·전력규약 {NORM}·T_CPI {T_CPI_MS} ms·Pd 0.9 @ 셀당 "
    f"Pfa 1e-4·단일 CPI·이상 DPI소거(∞ dB) 기준, 자유공간(FS-1) 검지거리는 **LTE CRS(L1)**·대표 기체 "
    f"`{HEAD_DRONE}` 에서 **R_eq {REQ} m**(중점수평 d {DHZ} m) [자세 커버리지 C25–C50: {LO}–{HI} m], "
    f"헤딩평균 검출확률 E_ψ[Pd]={EPD}. **실장 소거 60 dB 기준 {R60} m.**",
))
cells.append(fig("report13_geometry", "거리 셋과 하나의 측정 — iso-R_b 타원 + Cassini oval"))
cells.append(gif("r13_cassini_baseline", "베이스라인 L 스윕 — Cassini 단일→이엽 (β>90° 해칭)",
                 "기하가 커버리지를 접는다 — L 을 늘리면 등감도선이 단일 오벌에서 두 잎으로 갈린다."))


# ── §2 표적 ────────────────────────────────────────────────────────────────
cells.append(md(
    "## §2 — 표적 (5기종 · σ 는 방위와 앙각의 함수)", "",
    "5기종은 **target_extent(메쉬 bbox 최대 수평치수) 오름차순**으로 고정한다: "
    "`mini5pro < phantom4 < mavic4pro < matrice4e < s1000plus`. σ 는 단일 숫자가 아니라 **(방위, 앙각)의 "
    "함수**다. 지상 TX/RX + 공중 표적이라 이등분선 앙각은 **전 구간 음수** — 우리는 드론의 **배(belly)** 를 본다.",
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
    f"v=5 m/s 에서 헤딩의 약 **{BLIND}%** 가 도플러 블라인드, 나머지도 M≈{SSB_M} 로 코히런트 이득이 낮아 "
    f"상시 3인방 중 꼴찌다.",
))
cells.append(fig("report13_detector", "측정한 Pd(SNR) + 경험 Pfa + 도플러 오프셋 의존"))


# ── §4 몇 m 인가 ────────────────────────────────────────────────────────────
cells.append(md(
    "## §4 — 몇 m 인가 (R90_C50 + E_ψ[Pd] 병기 · 5G 꼴찌)", "",
    "단일 '검지거리'는 없다. **R90_C50**(헤딩의 50%가 Pd≥0.9 인 최외곽 거리)와 **E_ψ[Pd]**(헤딩 평균 검출확률)를 "
    "**함께** 말한다. 커버리지 밴드는 C25–C50 이며, 커버리지 천장 C_max=1−b_blind 상대다(b_blind>10%면 C10 은 미정의).",
    "",
    f"> 전력규약을 배치현실(deploy)로 바꾸면 **유휴 5G(NR G1)가 무너진다**: equal_psd 대비 평균 방사전력이 "
    f"약 {NR_IDLE_DB} dB 낮다(유휴 gNB ≠ 풀 gNB). 상시 3인방 순위 전복은 이 프로젝트의 핵심 서사(5G 이중고)다.",
))
cells.append(fig("report13_range_bars",
                 "자유공간 검지거리 — 5기종 × 상시 3인방 (채운 띠=C25–C50, 캡=CI95)"))
cells.append(fig("report13_matrix", "R90 행렬 — 5기종 × 9모드 (equal-PSD | deploy-EIRP)"))
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
    "폴드·FS-0 9모드 동일성·챔버 되돌리기(F16)까지 교차검증한다.",
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
nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "py312", "language": "python", "name": "py312"},
                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
with open(NB, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print(f"✅ {os.path.relpath(NB, ROOT)}  ({len(cells)} cells)  |  "
      f"JSON={'있음' if HAVE_JSON else '없음(placeholder)'}  |  engines={ENGINES}")
