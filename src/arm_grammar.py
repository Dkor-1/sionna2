#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""팔 이름(engine)을 **되읽는다** — 대조군을 즉석 정규식으로 짓지 않기 위해 (2026-09-13).

왜 있나
-------
같은 종류의 사고를 이 레포에서 네 번 냈다.

  · `sc()` 가 `sionna-munich` 를 몰라 4 칸이 **조용히** 버려졌다(행에도 없고 건너뜀에도 없다)
  · `twin_name()` 이 모르는 장면을 자기 자신과 짝지었다
  · `by_engine` 이 engine 만 키로 써서 마지막 앙각이 앞을 덮었다(58 칸 거부)
  · 반송파 비교를 즉석 필터로 지어 **다른 기체(s1000plus)와 다른 대역(24 GHz)** 이 섞여
    들어왔다 — 20 dB·48 dB 폭이 나왔는데 그것은 표적이 아니라 섞임이었다
  · 환경 정규식이 `outdoor01_fc3550` 을 **환경 이름으로** 삼켰다(2026-09-13)

공통점은 하나다 — **이름을 부분문자열·정규식으로 긁었다.** 긁으면 모르는 것이 조용히
사라지거나 조용히 딸려 온다. 여기서는 그 대신 이름을 **문법으로 되읽고**, 되읽은 것을
다시 지어 원본과 글자까지 같은지 **확인한다**. 안 맞으면 소리를 낸다.

문법은 어디서 왔나
------------------
⛔지어내지 않았다. `benchmark/elevation_sweep_md.py` 가 이름을 **짓는** 그 자리에서 그대로
옮겼다(:453 `tagr` · :645 우리 커널 · :760 PathSolver). 이름은 **고정 순서**로 이어 붙인
선택적 꼬리표들이라 되읽기에 모호함이 없다.

    PathSolver  sionna _p<spp> _phys _sw<R#D#E#F#> _stockdef _only<…> _parts<…>
                <공통> _d<깊이>
    우리 커널   ours|ours_free|ours_gpu _ptd <공통> _div<나눔> _shift<옮김>
    <공통>      _<기체> _r<거리> _n<자세> _prf<표집률> _rep<되풀이> _env<환경>
                _mp<경로상한> _gnd<지면><고도> _nospread _S<산란> _alt<고도>
                _ps<프롭배율> _fs<프레임배율> _bs<동체배율> _pw _det _az<방위>
                _rot<로터> _fc<반송파MHz> _shell<두께>mm _prop<두께>mm _mfix<수리> _bl<날법칙>

⚠꼬리표 **둘**은 밑줄을 품는다 — `_env`(예: `outdoor01_ground` · `sionna-simple_street_canyon`)
와 `_rot`(예: `outdoor_v2`). 그래서 이 둘은 «다음 꼬리표가 나올 때까지 먹는다». 이것이
`outdoor01_fc3550` 사고의 정확한 반대다 — `fc` 는 뒤에 오는 꼬리표라 거기서 멈춘다.

쓰는 법
-------
    from arm_grammar import parse, unparse, matched_groups, ArmNameError

    f = parse("sionna_p4000000000_swR0D0E0F1_r15_n8192_envoutdoor01_fc3450_mfixbatteryi5_…")
    f["env"], f["fc"]            # ('outdoor01', '3450')   ⭐환경에 fc 가 안 딸려 온다
    unparse(f) == 원본            # 언제나 참이어야 한다(아니면 ArmNameError)

    # ⭐대조군은 «한 축만 다르고 나머지는 글자까지 같은» 팔들이다
    groups = matched_groups(arms, vary=["fc"])
"""
from __future__ import annotations

import re
from typing import Iterable


class ArmNameError(ValueError):
    """이름을 문법으로 못 읽었다 — ⛔조용히 넘기지 않는다."""


#: ⭐발주서가 실제로 쓴 값들(`grep -o -- '--env …' runners/jobs_*.txt`). 검증표로만 쓴다 —
#  여기 없는 값이 나오면 «틀렸다» 가 아니라 «새 값이니 사람이 보라» 는 뜻이다.
KNOWN_ENVS = {
    "outdoor01", "outdoor01_bldg", "outdoor01_ground",
    "sionna-munich", "sionna-simple_street_canyon",
}
KNOWN_DRONES = {
    "m350rtk", "matrice4e", "mavic4pro", "mini5pro", "phantom4", "s1000plus", "x500v2",
}
KNOWN_ROTORS = {"legacy", "outdoor", "outdoor_v2"}
#: ⛔⛔**로터 씨앗은 «앞에 무엇이 오든» 밑줄 없이 달라붙는다.** 빌더(:487)가
#      + ("" if not int(getattr(a, "rotor_seed", 0)) else f"s{int(a.rotor_seed)}")
#  로 **독립해서** 이어 붙이기 때문이다 — 바로 앞이 `_rot…` 이면 로터에, `_az…` 면
#  방위각에, 로터도 방위각도 없으면 `_gnd…`·`_env…`·`_nospread` 에 붙는다.
#  ⛔2026-09-13(6) 실측: 그래서 원장의 4 팔이 `az0.7s1`·`az0.7s2` 로 읽혀
#    **방위각 축 대조군**에 0.7 과 «0.7s1» 이 다른 방위각인 척 같이 들어왔다
#    (원장 행의 az_deg 는 셋 다 0.7 이다). 왕복은 맞는데 뜻이 틀린 자리다.
#  ⇒ 씨앗을 **값에서 떼어** 따로 싣는다(`rotor_seed`). 되지을 때 원래 자리에 붙인다.
_SEED_RE = re.compile(r"^(?P<head>.*?)s(?P<seed>\d+)$")
_ROTOR_FORMS = {p + (f"s{k}" if k else "") for p in KNOWN_ROTORS for k in range(0, 9)}
#: 밑줄을 품는 꼬리표만 이 표를 쓴다. ⭐발주서(`runners/jobs_*.txt`)가 정본이다.
KNOWN_VALUES = {"env": KNOWN_ENVS, "rotor": _ROTOR_FORMS,
                #: 지금까지 발주서가 쓴 솔버 판. 처음 보는 판은 ⚠로 짚는다(막지는 않는다).
                "solver_build": ("210",)}

_NUM = r"-?\d+(?:\.\d+)?"


class _F:
    """꼬리표 하나. `absorbs` 면 다음 꼬리표가 나올 때까지 밑줄 건너 먹는다."""

    __slots__ = ("name", "rx", "pre", "absorbs", "flag")

    def __init__(self, name: str, pre: str, body: str, *,
                 absorbs: bool = False, flag: bool = False):
        self.name, self.pre, self.absorbs, self.flag = name, pre, absorbs, flag
        self.rx = re.compile(rf"^{re.escape(pre)}{body}$")

    def match(self, tok: str) -> bool:
        return self.rx.match(tok) is not None

    def value(self, tok: str) -> str:
        return True if self.flag else tok[len(self.pre):]

    def render(self, v) -> str:
        return "_" + self.pre if self.flag else "_" + self.pre + str(v)


#: ⭐순서가 곧 문법이다 — elevation_sweep_md.py 가 이어 붙이는 그 순서 그대로.
_COMMON = [
    _F("drone", "", r"(?:%s)" % "|".join(sorted(map(re.escape, KNOWN_DRONES)))),
    _F("range_m", "r", _NUM),
    _F("n_poses", "n", r"\d+"),
    _F("prf", "prf", _NUM),
    _F("rep", "rep", r"\d+"),
    _F("env", "env", r"[A-Za-z0-9:.-]+", absorbs=True),
    _F("max_paths", "mp", r"\d+"),
    _F("ground", "gnd", r"[A-Za-z]+%s" % _NUM),
    _F("nospread", "nospread", r"", flag=True),
    _F("env_scat", "S", _NUM),
    _F("env_alt", "alt", _NUM),
    _F("prop_scale", "ps", _NUM),
    _F("frame_scale", "fs", _NUM),
    _F("body_scale", "bs", _NUM),
    _F("plane_wave", "pw", r"", flag=True),
    _F("det", "det", r"", flag=True),
    #: ⚠`_az0.7s1` — 로터 씨앗은 **앞 꼬리표에 바로 붙는다**(빌더가 밑줄을 안 넣는다).
    #: ⚠씨앗이 붙을 수 있다 — 아래 `_split_seed` 가 떼어 `rotor_seed` 로 옮긴다.
    _F("az", "az", r"%s(?:s\d+)?" % _NUM),
    _F("rotor", "rot", r"[A-Za-z0-9.-]+", absorbs=True),
    _F("fc", "fc", r"\d+"),
    _F("shell_mm", "shell", r"%smm" % _NUM),
    _F("prop_mm", "prop", r"%smm" % _NUM),
    _F("mesh_fix", "mfix", r"[A-Za-z0-9]+"),
    _F("blade_law", "bl", r"[A-Za-z0-9]+"),
    #: ⭐⭐**솔버 판** (2026-09-14 신설) — `_rt210` = sionna-rt 2.1.0 으로 구웠다는 뜻.
    #  ⛔**기준 판(2.0.1)에는 안 붙는다.** 창고 7,730 개가 전부 그 판이라 이름이 그대로여야
    #    이어진다. 그러니 「꼬리표가 없다」 = 「2.0.1 로 구웠다」로 읽는다 —
    #    그 근거는 샤드가 스스로 적는 `solver_build` 이고, 적히기 전 세대는
    #    「모든 샤드가 2.0.1 설치(08-13) 이후」라는 창고 사실로 뒷받침한다.
    #  ⛔이름은 sionna-rt 판만 담는다. mitsuba·drjit 만 움직인 경우는 이름이 못 담으므로
    #    빌더(`elevation_sweep_md.build_tag`)가 **아예 멈춘다.**
    _F("solver_build", "rt", r"\d+"),
]

_SIONNA_HEAD = [
    _F("spp", "p", r"\d+"),
    _F("physics", "phys", r"", flag=True),
    _F("switches", "sw", r"R[01]D[01]E[01]F[01]"),
    _F("stock", "stockdef", r"", flag=True),
    _F("only", "only", r"[A-Za-z0-9]+"),
    _F("parts", "parts", r"[A-Za-z0-9]+"),
]
_SIONNA_TAIL = [_F("max_depth", "d", r"\d+")]

_OURS_HEAD = [_F("ptd", "ptd", r"", flag=True)]
_OURS_TAIL = [
    _F("grid_div", "div", r"\d+"),
    _F("grid_shift", "shift", r"[0-9.x-]+"),
]

FIELDS = {
    "sionna": _SIONNA_HEAD + _COMMON + _SIONNA_TAIL,
    "ours": _OURS_HEAD + _COMMON + _OURS_TAIL,
}
#: 엔진 머리 — 길이가 긴 것부터 본다(`ours_free` 가 `ours` 보다 먼저 걸려야 한다).
ENGINES = ("ours_free", "ours_gpu", "ours", "sionna")


def _family(engine: str) -> str:
    return "sionna" if engine == "sionna" else "ours"


def parse(engine: str, *, strict: bool = True) -> dict:
    """팔 이름을 꼬리표 사전으로 되읽는다. ⛔못 읽으면 ArmNameError 를 던진다.

    strict : 되짓기가 원본과 글자까지 같은지 확인한다(기본 참). ⭐이것이 이 모듈의 핵심
             장치다 — 조용히 잘못 읽는 일을 구조적으로 못 하게 만든다.
    """
    head = next((e for e in ENGINES if engine == e or engine.startswith(e + "_")), None)
    if head is None:
        raise ArmNameError(f"엔진 머리를 모른다: {engine!r} (아는 것: {ENGINES})")
    out: dict = {"engine": head}
    rest = engine[len(head):]
    toks = [t for t in rest.split("_") if t != ""]
    fields = FIELDS[_family(head)]

    i, fi = 0, 0
    while i < len(toks):
        tok = toks[i]
        j = fi
        while j < len(fields) and not fields[j].match(tok):
            j += 1
        if j >= len(fields):
            raise ArmNameError(
                f"{engine!r} 의 조각 {tok!r} 이 어느 꼬리표에도 안 맞는다 "
                f"(여기부터 볼 수 있는 꼬리표: "
                f"{[f.name for f in fields[fi:fi + 6]]}). "
                f"⭐빌더에 꼬리표가 새로 생겼으면 이 표에 **같은 자리**로 넣어라.")
        f = fields[j]
        if f.absorbs:
            #: ⭐먼저 **발주서가 실제로 쓴 값** 중 가장 긴 것을 맞춰 본다. 이것이 정본이다.
            #  ⛔왜 필요한가(2026-09-13 실측): 장면 `outdoor01_bldg` 의 `bldg` 가 날 법칙
            #    꼬리표 `bl…` 과 앞글자가 겹쳐, 「다음 꼬리표에서 멈춘다」 규칙만으로는
            #    환경이 `outdoor01` 에서 잘리고 `bldg` 가 날 법칙으로 읽혔다(팔 4 개).
            known = KNOWN_VALUES.get(f.name) or ()
            hit = None
            for cand in sorted(known, key=len, reverse=True):
                want = (f.pre + cand).split("_")
                if toks[i:i + len(want)] == want:
                    hit = (cand, len(want))
                    break
            if hit is not None:
                out[f.name], i = hit[0], i + hit[1]
            else:
                #: 처음 보는 값 — 다음 꼬리표가 나올 때까지 먹는다. `outdoor01_ground` 는
                #  먹고 `outdoor01` + `fc3450` 은 안 먹는다(fc 가 뒤 꼬리표이므로).
                #  ⚠이 길로 온 값은 `warnings_for` 가 «처음 보는 것» 으로 짚는다.
                got, i = [tok], i + 1
                while i < len(toks) and not any(
                        fields[k].match(toks[i]) for k in range(j + 1, len(fields))):
                    got.append(toks[i])
                    i += 1
                out[f.name] = "_".join(got)[len(f.pre):]
        else:
            out[f.name] = f.value(tok)
            i += 1
        fi = j + 1

    #: ⭐씨앗을 값에서 떼어 따로 싣는다 — 어느 꼬리표에 붙어 있었는지도 적는다.
    _split_seed(out)

    if strict:
        back = unparse(out)
        if back != engine:
            raise ArmNameError(
                f"되짓기가 원본과 다르다 — 되읽기를 믿으면 안 된다\n"
                f"  원본 {engine}\n  되짓기 {back}\n  읽은 것 {out}")
    return out


#: 씨앗이 달라붙을 수 있는 꼬리표 — 빌더의 이어붙이기 차례에서 `_rot` **앞뒤**로
#  올 수 있는 것들. 뒤 꼬리표(fc·shell·prop·mfix·bl)는 씨앗보다 뒤에 붙으므로 제외한다.
_SEED_HOSTS = ("rotor", "az", "det", "plane_wave", "body_scale", "frame_scale",
               "prop_scale", "env_alt", "env_scat", "nospread", "ground", "max_paths",
               "env")


def _split_seed(out: dict) -> None:
    """값 끝에 달라붙은 로터 씨앗 `s<N>` 을 떼어 `rotor_seed` 로 옮긴다.

    ⛔`rotor` 는 예외다 — 아는 형태 표(_ROTOR_FORMS)가 씨앗까지 포함해 맞추므로
      이미 «그 로터 설정의 그 씨앗» 이라는 한 값이다. 나머지 꼬리표에 붙은 것만 뗀다.
    ⛔떼어도 `unparse` 가 **같은 자리에** 다시 붙이므로 왕복은 그대로 성립한다.
    """
    for k in _SEED_HOSTS:
        v = out.get(k)
        if k == "rotor" or not isinstance(v, str):
            continue
        m = _SEED_RE.match(v)
        if not m or not m.group("head"):
            continue
        head = m.group("head")
        #: 떼어낸 머리가 그 꼬리표의 정규식에 맞아야 «씨앗이었다» 고 본다.
        fld = next((f for f in _COMMON if f.name == k), None)
        if fld is None or not fld.match(fld.pre + head):
            continue
        out[k] = head
        out["rotor_seed"] = int(m.group("seed"))
        out["_seed_host"] = k
        return


def unparse(fields: dict) -> str:
    """꼬리표 사전을 다시 이름으로. `parse` 의 역이고, 둘의 왕복이 이 모듈의 검사다."""
    head = fields["engine"]
    host = fields.get("_seed_host")
    seed = fields.get("rotor_seed")
    out = [head]
    for f in FIELDS[_family(head)]:
        v = fields.get(f.name)
        if v is None or v is False:
            continue
        piece = f.render(v)
        #: ⭐떼어낸 씨앗을 **원래 붙어 있던 꼬리표 뒤에** 밑줄 없이 되붙인다.
        if host == f.name and seed is not None:
            piece += f"s{int(seed)}"
        out.append(piece)
    return "".join(out)


def warnings_for(fields: dict) -> list[str]:
    """⚠문법은 맞는데 **처음 보는 값** — 틀렸다는 뜻이 아니라 사람이 보라는 뜻이다."""
    w = []
    if fields.get("env") and fields["env"] not in KNOWN_ENVS:
        w.append(f"처음 보는 환경 {fields['env']!r} (아는 것 {sorted(KNOWN_ENVS)})")
    #: ⚠끝의 숫자를 씨앗으로 떼면 안 된다 — `outdoor_v2` 는 이름 자체가 숫자로 끝난다.
    #  씨앗까지 포함한 형태 표(_ROTOR_FORMS)와 통째로 맞춘다.
    if fields.get("rotor") and fields["rotor"] not in _ROTOR_FORMS:
        w.append(f"처음 보는 로터 {fields['rotor']!r} (아는 것 {sorted(KNOWN_ROTORS)} + 씨앗)")
    #: ⚠처음 보는 **솔버 판**. 꼬리표가 없으면 기준 판(2.0.1)이라 경고하지 않는다.
    #  ⛔막지는 않는다 — 판을 올리는 날 발주서가 먼저 오고 이 표가 뒤따르는 것이 정상이다.
    sb = fields.get("solver_build")
    if sb and sb not in (KNOWN_VALUES.get("solver_build") or ()):
        w.append(f"처음 보는 솔버 판 {sb!r} (아는 것 "
                 f"{sorted(KNOWN_VALUES.get('solver_build') or ())} · 꼬리표 없음 = 2.0.1)")
    return w


def key_without(fields: dict, vary: Iterable[str]) -> tuple:
    """`vary` 를 뺀 나머지 꼬리표 전부 — 이것이 같아야 **대조군**이다.

    ⛔`_seed_host` 는 «씨앗이 어느 꼬리표에 붙어 있었나» 라는 **표기 사정**일 뿐
      물리 축이 아니다. 열쇠에 넣으면 같은 조건인데 묶음이 갈린다 — 뺀다.
      씨앗 자체(`rotor_seed`)는 진짜 축이므로 남긴다.
    """
    skip = set(vary) | {"_seed_host"}
    return tuple(sorted((k, v) for k, v in fields.items() if k not in skip))


def matched_groups(arms: Iterable[str], vary: Iterable[str],
                   *, strict: bool = True) -> dict:
    """⭐«한 축만 다르고 나머지는 글자까지 같은» 팔 묶음.

    즉석 필터 대신 이것을 써라. 반송파를 견주려면 `vary=["fc"]` 다 — 그러면 기체·거리·
    팔·환경·표집률이 하나라도 다른 팔은 **다른 묶음**으로 가지 섞이지 않는다.

    돌려주는 것: {나머지꼬리표키: {vary값: 팔이름}}

    ⛔⛔**한 묶음이라는 것은 필요조건이지 충분조건이 아니다** (2026-09-13 실측).
      `vary=["fc"]` 로 가른 자유공간 묶음 하나에 3.450·3.475·3.500·3.525·3.550 GHz **와
      24 GHz 가 같이** 들어온다 — 꼬리표가 fc 하나만 다르니 문법으로는 한 묶음이 맞다.
      그런데 「5G NR 100 MHz 대역 안이 평평한가」를 물으면서 24 GHz 를 넣으면 그것은
      대역 평탄성이 아니라 **반송파 의존성**이다(퍼짐 4.24 dB 대 28.32 dB).
      ⇒ 부르는 쪽이 **읽을 범위를 따로 선언**해야 한다. 이 함수는 «섞임» 만 막는다.
    """
    vary = list(vary)
    out: dict = {}
    for a in arms:
        f = parse(a, strict=strict)
        k = key_without(f, vary)
        out.setdefault(k, {})[tuple(f.get(v) for v in vary)] = a
    return out


def describe(fields: dict) -> str:
    """사람이 읽는 한 줄 — ⛔덱에는 안 쓴다(우리끼리 쓰는 말이다)."""
    bits = [fields["engine"]]
    for f in FIELDS[_family(fields["engine"])]:
        v = fields.get(f.name)
        if v is None or v is False:
            continue
        bits.append(f.name if v is True else f"{f.name}={v}")
    return " · ".join(bits)
