#!/usr/bin/env python
"""인증 매트릭스 JSON → 사람이 브라우저로 읽는 표(HTML 한 장).

`outputs/mesh_cert_matrix_0816.json` 만 읽는다 — 수는 여기서 다시 계산하지 않는다.
실행: PYTHONPATH=src:benchmark python benchmark/make_mesh_cert_matrix_html_0816.py
"""
from __future__ import annotations

import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "outputs", "mesh_cert_matrix_0816.json")
OUT = os.path.join(ROOT, "outputs", "mesh_cert_matrix_0816.html")

SHORT = {"mini5pro": "Mini 5 Pro", "mavic4pro": "Mavic 4 Pro", "matrice4e": "Matrice 4E",
         "s1000plus": "S1000+", "phantom4": "Phantom 4", "typhoonh480": "Typhoon H480",
         "x500v2": "X500 V2", "phantom3": "Phantom 3", "m350rtk": "M350 RTK", "mini2": "Mini 2"}

STATE = {           # 판정 → (클래스, 글리프, 뜻)
    "통과": ("ok", "●", "통과"),
    "통과(⚠의심 포함)": ("susp", "◍", "통과(의심 포함)"),
    "⚠어긋남": ("warn", "▲", "참값과 어긋남"),
    "⚠사각지대": ("blind", "◐", "검사기 사각지대"),
    "실패": ("fail", "✕", "실패"),
    "해당없음": ("na", "–", "해당없음"),
    "빈칸": ("blank", "○", "빈칸(참값 없음)"),
}


def e(x) -> str:
    return html.escape("" if x is None else str(x))


def num(x) -> str:
    if x is None:
        return ""
    if isinstance(x, float):
        return f"{x:g}"
    return str(x)


def main() -> int:
    c = json.load(open(SRC, encoding="utf-8"))
    keys = list(c["matrix"][c["checks"][0]["id"]].keys())
    s = c["summary"]
    L: list[str] = []
    A = L.append

    A('<title>메쉬 인증 매트릭스</title>')
    A("<style>")
    A(CSS)
    A("</style>")

    # ── 머리 ────────────────────────────────────────────────────────────────
    A('<header class="masthead">')
    A('<div class="wrap">')
    A('<p class="eyebrow">2026-08-17 · 드론 메쉬 검증</p>')
    A('<h1>메쉬 인증 매트릭스</h1>')
    A(f'<p class="lede">{e(c["headline_ko"])}</p>')
    A('<dl class="stats">')
    for label, val, sub in [
        ("칸", f'{s["n_cells"]}', f'기체 {s["n_airframes"]} × 검사 {s["n_checks"]}'),
        ("통과", f'{s["n_pass"]}', "예산·규약 안"),
        ("참값 어긋남", f'{s["n_mismatch"]}', "실물과 다름"),
        ("사각지대", f'{s["n_blindspot"]}', "검사기가 못 본 자리"),
        ("적대 대조", f'{s["controls_passed"]}/{s["controls_total"]}', f'스위트 {s["n_suites"]}개'),
        ("양성 대조 없는 검사", f'{s["n_checks_without_positive_control"]}', f'검사 {s["n_checks"]}개 중'),
        ("봉인 일치", f'{s["seal_ok"]}/{s["seal_total"]}', "인증서 4종 × 10기체"),
    ]:
        A(f'<div><dt>{e(label)}</dt><dd>{e(val)}</dd><p>{e(sub)}</p></div>')
    A("</dl>")
    A("</div></header>")

    A('<main class="wrap">')

    # ── 읽는 법 ─────────────────────────────────────────────────────────────
    A('<section><h2>읽는 법</h2>')
    A('<ul class="legend">')
    for verdict, (cls, glyph, mean) in STATE.items():
        A(f'<li><span class="chip {cls}">{glyph}</span> {e(mean)}</li>')
    A("</ul>")
    A('<p class="note">「양성 대조」 = 그 검사를 겨냥해 <b>일부러 결함을 만들어 먹였더니 걸렸다</b>는 시험. '
      '없으면 그 자리는 «잡는다» 를 아직 증명하지 못한 것이고, 다른 검사에 우연히 걸리는 것은 근거로 세지 않는다.</p>')
    A("</section>")

    # ── 매트릭스 ────────────────────────────────────────────────────────────
    A('<section><h2>매트릭스</h2>')
    A('<div class="scroll"><table class="matrix">')
    A("<thead><tr><th class=\"lead\">검사</th><th>범주</th><th>양성대조</th>"
      + "".join(f'<th class="rot"><span>{e(SHORT.get(k, k))}</span></th>' for k in keys)
      + "</tr></thead><tbody>")
    for ch in c["checks"]:
        rid = ch["id"]
        ctrl = ch["controls"]
        pc = (f'<span class="pc yes">{ctrl["n_positive"]}</span>' if ctrl["positive_control_ok"]
              else '<span class="pc no">없음</span>')
        A(f'<tr><th class="lead"><a href="#chk-{e(rid)}"><b>{e(rid)}</b> {e(ch["name_ko"])}</a></th>'
          f'<td class="cat">{e(ch["category"])}</td><td class="mid">{pc}</td>')
        for k in keys:
            cell = c["matrix"][rid][k]
            cls, glyph, mean = STATE.get(cell["verdict"], ("na", "?", cell["verdict"]))
            tip = f'{SHORT.get(k, k)} · {mean}'
            if cell["value"] is not None:
                tip += f' · {num(cell["value"])} {cell["unit"]}'
            if cell["budget"] is not None:
                tip += f' / 예산 {cell["budget"]}'
            A(f'<td class="mid"><span class="chip {cls}" title="{e(tip)}">{glyph}</span></td>')
        A("</tr>")
    A("</tbody></table></div>")
    A("</section>")

    # ── 양성 대조가 없는 자리 ────────────────────────────────────────────────
    A('<section><h2>양성 대조가 없는 검사 <span class="tag warn">'
      f'{s["n_checks_without_positive_control"]}개</span></h2>')
    A('<p class="note">이 라운드가 «장담» 이라고 부를 수 없는 자리다. 검사는 돌고 값도 나오지만, '
      '«결함을 심으면 걸린다» 를 아직 보이지 않았다.</p>')
    A('<div class="scroll"><table class="rows"><thead><tr><th>검사</th><th>범주</th>'
      '<th>왜 없는가 · 대신 무엇이 있는가</th></tr></thead><tbody>')
    for ch in c["checks"]:
        if not ch["controls"]["positive_control_ok"]:
            A(f'<tr><td><b>{e(ch["id"])}</b> {e(ch["name_ko"])}</td><td class="cat">{e(ch["category"])}</td>'
              f'<td>{e(ch["controls"].get("indirect_ko", ""))}</td></tr>')
    A("</tbody></table></div></section>")

    # ── 통과 못한 칸 ────────────────────────────────────────────────────────
    A('<section><h2>통과하지 못한 칸</h2>')
    A('<div class="scroll"><table class="rows"><thead><tr><th>검사</th><th>기체</th><th>판정</th>'
      '<th>내용</th></tr></thead><tbody>')
    for f in c["failures"]:
        cls = STATE.get(f["verdict"], ("na", "", ""))[0]
        A(f'<tr><td><b>{e(f["check"])}</b> {e(f["name_ko"])}</td><td>{e(SHORT.get(f["key"], f["key"]))}</td>'
          f'<td><span class="tag {cls}">{e(f["verdict"])}</span></td><td>{e(f["detail"])}</td></tr>')
    A("</tbody></table></div></section>")

    # ── 어긋난 치수 ─────────────────────────────────────────────────────────
    A('<section><h2>바깥 참값과 어긋난 치수</h2>')
    A('<p class="note">순환 뜻 — <b>independent</b> 는 그 수를 메쉬에 넣은 적이 없다(진짜 대조) · '
      '<b>circular</b> 는 우리가 넣은 수를 되읽는 것(회귀 감시용) · <b>partly_circular</b> 는 그 중간. '
      '«실물과 맞다» 를 주장할 수 있는 것은 independent 행뿐이다.</p>')
    A('<div class="scroll"><table class="rows num"><thead><tr><th>기체</th><th>행</th><th>부품</th>'
      '<th>무엇</th><th>잰 값</th><th>참값</th><th>잔차</th><th>U</th><th>U 의 배수</th>'
      '<th>등급</th><th>순환</th></tr></thead><tbody>')
    for r in c["dimension_mismatch_rows"]:
        res = "" if r["residual"] is None else f'{r["residual"]:+.4f}'
        pct = "" if r.get("residual_pct") is None else f' <span class="dim">({r["residual_pct"]:+.2f} %)</span>'
        over = r["over_U"]
        cls = "warn" if (over or 0) > 1 else ""
        A(f'<tr><td>{e(SHORT.get(r["key"], r["key"]))}</td><td class="mono">{e(r["rid"])}</td>'
          f'<td>{e(r["part"])}</td><td>{e(r["quantity"])}</td><td>{e(num(r["measured"]))}</td>'
          f'<td>{e(num(r["reference"]))}</td><td class="{cls}">{res}{pct}</td>'
          f'<td>{"" if r["U"] is None else f"{r['U']:.3f}"}</td><td>{e(num(over))}</td>'
          f'<td class="mono">{e(r["grade"])}</td><td class="dim">{e(r["circularity"])}</td></tr>')
    A("</tbody></table></div></section>")

    # ── 떠 있는 부품 ────────────────────────────────────────────────────────
    A('<section><h2>떠 있는 부품 — 설계인가 결함인가</h2>')
    A('<div class="scroll"><table class="rows num"><thead><tr><th>기체</th><th>부품</th><th>이격</th>'
      '<th>가장 가까운 것</th><th>등급</th><th>왜</th></tr></thead><tbody>')
    for f in sorted(c["floating_parts"], key=lambda x: -x["gap_mm"]):
        cls = {"P": "ok", "B": "warn", "D": "susp"}.get(f["grade"], "")
        A(f'<tr><td>{e(SHORT.get(f["key"], f["key"]))}</td><td class="mono">{e(f["pid"])}</td>'
          f'<td>{f["gap_mm"]:.3f} mm</td><td class="mono dim">{e(f.get("nearest"))}</td>'
          f'<td><span class="tag {cls}">{e(f["grade"])}</span></td><td>{e(f["why"])}</td></tr>')
    A("</tbody></table></div>")
    A('<p class="note">등급 <b>P</b> = 물리적 필연(돌아가는 프롭은 벨에 닿을 수 없다) · '
      '<b>B</b> = 공식 사진·렌더로 «실물은 붙어 있다» 를 확인 · <b>D</b> = 확인 안 함. '
      'B 와 D 는 형상 라운드의 할 일이다.</p></section>')

    # ── 빠듯한 잔차 ─────────────────────────────────────────────────────────
    A('<section><h2>허용 안에 있지만 빠듯한 잔차</h2>')
    A('<p class="note">⚠ 먼저 읽을 것 — 이 저장소의 예산 상당수는 «실측 + 약 10 %» 로 못 박은 <b>선언</b>이라, '
      '잔차가 하나도 안 움직여도 빠듯함이 구조적으로 90.9 % 에 앉는다. 정말 볼 것은 그 규약보다도 빠듯한 줄이다.</p>')
    A('<div class="scroll"><table class="rows num"><thead><tr><th>검사</th><th>기체</th><th>잔차</th>'
      '<th>예산</th><th>빠듯함</th><th>예산의 성질</th></tr></thead><tbody>')
    for r in c["residuals_near_budget"]:
        star = "★ " if (r.get("tighter_than_convention")
                        or r["budget_kind"].startswith(("물리", "설계", "스펙", "규약"))) else ""
        bar = min(100.0, r["margin_pct"])
        A(f'<tr><td>{star}<b>{e(r["check"])}</b> {e(r["name_ko"])}</td>'
          f'<td>{e(SHORT.get(r["key"], r["key"]))}</td><td>{e(num(r["value"]))} {e(r["unit"])}</td>'
          f'<td>{e(num(r["budget"]))}</td>'
          f'<td><span class="meter"><i style="width:{bar:.0f}%"></i></span>{r["margin_pct"]:.1f} %</td>'
          f'<td class="dim">{e(r["budget_kind"])}</td></tr>')
    A("</tbody></table></div></section>")

    # ── 범주 지도 ───────────────────────────────────────────────────────────
    A('<section><h2>범주 지도 — 결함이 있을 수 있는 자리 20칸</h2>')
    A('<p class="note">메쉬는 (정점 · 삼각형 · 그룹 라벨) 셋과, 그것을 만든 빌더 입력, 그 라벨을 뜻으로 바꾸는 '
      '바깥 표 — 모두 다섯 상태뿐이라 결함은 그중 하나에 반드시 나타난다. 그래서 이 목록이 닫혀 있다.</p>')
    A('<div class="scroll"><table class="rows"><thead><tr><th>범주</th><th>무엇</th><th>이 매트릭스의 행</th>'
      '<th>지금</th></tr></thead><tbody>')
    for m in c["category_map"]:
        cls = {"있음": "ok", "부분": "warn", "없음": "fail"}.get(m["status_now"], "")
        A(f'<tr><td class="mono">{e(m["id"])}</td><td>{e(m["name"])}</td>'
          f'<td class="mono dim">{e(", ".join(m["matrix_rows"]) or "—")}</td>'
          f'<td><span class="tag {cls}">{e(m["status_now"])}</span></td></tr>')
    A("</tbody></table></div></section>")

    # ── 근거 등급 ───────────────────────────────────────────────────────────
    gm = c["grade_matrix"]
    A('<section><h2>근거 등급 — 기체 × 부품</h2>')
    A('<div class="scroll"><table class="matrix grade"><thead><tr><th class="lead">기체</th>'
      + "".join(f"<th>{e(p)}</th>" for p in gm["parts"]) + "</tr></thead><tbody>")
    for k in keys:
        row = gm["matrix"].get(k, {})
        A(f'<tr><th class="lead">{e(SHORT.get(k, k))}</th>')
        for p in gm["parts"]:
            g = row.get(p, {}).get("grade", "모름")
            cls = {"A": "ok", "B": "warn", "B-": "warn", "C": "susp"}.get(g, "blank")
            A(f'<td class="mid"><span class="chip {cls}">{e(g if g != "모름" else "○")}</span></td>')
        A("</tr>")
    A("</tbody></table></div>")
    A(f'<p class="note">{e(gm["coverage_ko"])}</p></section>')

    # ── 대조·재현성·봉인 ────────────────────────────────────────────────────
    A('<section class="two"><div>')
    A("<h2>적대 대조</h2>")
    A('<table class="rows"><thead><tr><th>스위트</th><th>지키는 검사기</th><th>결과</th></tr></thead><tbody>')
    for name, suite in c["controls"].items():
        A(f'<tr><td class="mono">{e(name)}</td><td class="mono dim">{e(suite["guards"])}</td>'
          f'<td><span class="tag ok">{suite["n_passed"]}/{suite["n"]}</span> '
          f'<span class="dim">나가는 값 {e(suite["exit_code"])}</span></td></tr>')
    A("</tbody></table>")
    rp = c.get("reproducibility") or {}
    if rp.get("n"):
        A("<h2>재현성</h2>")
        A(f'<p class="note">{e(rp["what_ko"])} 기체 {rp["n"]}대를 다시 돌려 '
          f'<b>{rp["n_identical"]}대가 비트 동일</b>'
          f'({e(", ".join(SHORT.get(r["key"], r["key"]) for r in rp["rows"] if r["identical"]))}).</p>')
    A("</div><div>")
    A("<h2>봉인 — 어느 메쉬의 표인가</h2>")
    A('<p class="note">네 인증서(위상·치수·대칭·배치)가 박아 둔 지문과 지금 메쉬를 견준다. '
      '형상이 바뀌면 이 표는 재발급 대상이 된다.</p>')
    A('<table class="rows"><thead><tr><th>기체</th><th>위상</th><th>치수·대칭</th><th>배치</th>'
      '<th>일치</th></tr></thead><tbody>')
    for k in keys:
        sp = c["seal"]["per_airframe"][k]
        ok = sp["all_match"]
        A(f'<tr><td>{e(SHORT.get(k, k))}</td><td class="mono dim">{e(sp["topology"][:10])}</td>'
          f'<td class="mono dim">{e(sp["dimension"][:10])}</td>'
          f'<td class="mono dim">{e(sp["placement_mesh"][:10])}</td>'
          f'<td><span class="tag {"ok" if ok else "fail"}">{"전부" if ok else e(sp["mismatch"])}</span></td></tr>')
    A("</tbody></table></div></section>")

    # ── 결과에서 몇 dB 인가 ──────────────────────────────────────────────────
    A('<section><h2>이 수들이 결과에서 몇 dB 인가</h2><dl class="deflist">')
    for k, v in c["consequences_ko"].items():
        A(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>")
    A("</dl></section>")

    # ── 예산의 출처 ─────────────────────────────────────────────────────────
    A('<section><h2>예산은 어디서 왔는가</h2><dl class="deflist">')
    for k, v in c["budget_provenance_ko"].items():
        A(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>")
    A("</dl>")
    A(f'<p class="note">{e(c["snapshot_count_rows_ko"])}</p></section>')

    # ── 못 하는 것 ──────────────────────────────────────────────────────────
    A('<section class="limits"><h2>못 하는 것 — 이 표가 장담하지 않는 범위</h2><ol>')
    for t in c["limits_ko"]:
        A(f"<li>{e(t)}</li>")
    A("</ol></section>")

    # ── 검사 하나하나 ───────────────────────────────────────────────────────
    A('<section><h2>검사 하나하나 — 잔차 · 허용오차 · 근거등급</h2>')
    for ch in c["checks"]:
        rid = ch["id"]
        ctrl = ch["controls"]
        pc = (f'양성 {ctrl["n_positive_passed"]}/{ctrl["n_positive"]} · '
              f'음성 {ctrl["n_negative_passed"]}/{ctrl["n_negative"]}'
              if ctrl["n"] else "대조 없음")
        A(f'<details id="chk-{e(rid)}"><summary><b>{e(rid)}</b> {e(ch["name_ko"])} '
          f'<span class="tag">{e(ch["category"])}</span> '
          f'<span class="dim">{e(pc)}</span></summary>')
        A(f'<p class="note">코드 <code>{e(ch["code"])}</code><br>허용오차 — {e(ch["tolerance_ko"])}'
          + (f'<br>{e(ctrl["indirect_ko"])}' if ctrl.get("indirect_ko") else "") + "</p>")
        A('<div class="scroll"><table class="rows num"><thead><tr><th>기체</th><th>판정</th><th>잔차</th>'
          '<th>예산</th><th>빠듯함</th><th>근거등급</th><th>비고</th></tr></thead><tbody>')
        for k in keys:
            cell = c["matrix"][rid][k]
            cls, glyph, mean = STATE.get(cell["verdict"], ("na", "?", cell["verdict"]))
            mar = "" if cell["margin_pct"] is None else f'{cell["margin_pct"]:.1f} %'
            A(f'<tr><td>{e(SHORT.get(k, k))}</td>'
              f'<td><span class="chip {cls}">{glyph}</span> {e(cell["verdict"])}</td>'
              f'<td>{e(num(cell["value"]))} {e(cell["unit"])}</td><td>{e(num(cell["budget"]))}</td>'
              f'<td>{mar}</td><td class="dim">{e(cell["grade"])}</td>'
              f'<td class="note-cell">{e(cell["note"])}</td></tr>')
        A("</tbody></table></div></details>")
    A("</section>")

    # ── 꼬리 ────────────────────────────────────────────────────────────────
    m = c["_meta"]
    A('<footer><p>')
    A(f'{e(m["generated_kst"])} 생성 · {e(m["role_ko"])}<br>')
    A(f'{e(m["policy_ko"])}<br>')
    A(f'원자료 <code>{e(m["inputs"]["raw_dir"])}</code> · 인증서 '
      f'<code>outputs/mesh_cert_matrix_0816.json</code> · 표 '
      f'<code>outputs/mesh_cert_matrix_0816.md</code><br>')
    A(f'<span class="dim">{e(m["warning_ko"])}</span>')
    A("</p></footer>")
    A("</main>")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print("→", OUT)
    return 0


CSS = """
:root{
  --paper:#eef1f5; --card:#ffffff; --ink:#111820; --ink-2:#4a5563; --dim:#79859a;
  --rule:#d5dce6; --rule-2:#e7ecf2;
  --blue:#1d5b86; --blue-soft:#e3edf5;
  --ok:#2c7a5d; --ok-bg:#dcefe6;
  --warn:#a4620b; --warn-bg:#f7ead4;
  --susp:#6b4fa0; --susp-bg:#eae4f6;
  --fail:#a92a20; --fail-bg:#f8e0dd;
  --blank:#8d97a8; --blank-bg:#e6eaf0;
  --shadow:0 1px 2px rgba(17,24,32,.06), 0 8px 24px -18px rgba(17,24,32,.35);
  --sans:"Pretendard","Apple SD Gothic Neo","Noto Sans KR","Malgun Gothic",
         ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono","JetBrains Mono",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --paper:#0d1219; --card:#151c25; --ink:#e4eaf2; --ink-2:#aab6c6; --dim:#7f8b9d;
    --rule:#26313e; --rule-2:#1e2731;
    --blue:#74b4dd; --blue-soft:#152634;
    --ok:#68c39b; --ok-bg:#142b23;
    --warn:#e0a95a; --warn-bg:#2e2412;
    --susp:#b39ce4; --susp-bg:#241d33;
    --fail:#f08d84; --fail-bg:#33191a;
    --blank:#7f8b9d; --blank-bg:#1c242e;
    --shadow:0 1px 2px rgba(0,0,0,.5), 0 10px 30px -20px rgba(0,0,0,.9);
  }
}
:root[data-theme="dark"]{
  --paper:#0d1219; --card:#151c25; --ink:#e4eaf2; --ink-2:#aab6c6; --dim:#7f8b9d;
  --rule:#26313e; --rule-2:#1e2731;
  --blue:#74b4dd; --blue-soft:#152634;
  --ok:#68c39b; --ok-bg:#142b23;
  --warn:#e0a95a; --warn-bg:#2e2412;
  --susp:#b39ce4; --susp-bg:#241d33;
  --fail:#f08d84; --fail-bg:#33191a;
  --blank:#7f8b9d; --blank-bg:#1c242e;
  --shadow:0 1px 2px rgba(0,0,0,.5), 0 10px 30px -20px rgba(0,0,0,.9);
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
     font-size:15px;line-height:1.65;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:0 24px}
.masthead{background:var(--card);border-bottom:1px solid var(--rule);padding:44px 0 28px}
.eyebrow{margin:0 0 6px;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--blue);
         font-weight:650}
h1{margin:0 0 12px;font-size:clamp(30px,4.4vw,46px);line-height:1.1;letter-spacing:-.02em;
   font-weight:750;text-wrap:balance}
.lede{margin:0;max-width:74ch;color:var(--ink-2);font-size:15.5px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(148px,1fr));gap:1px;margin:26px 0 0;
       background:var(--rule);border:1px solid var(--rule);border-radius:10px;overflow:hidden}
.stats>div{background:var(--card);padding:12px 14px}
.stats dt{font-size:11.5px;letter-spacing:.06em;color:var(--dim);text-transform:uppercase}
.stats dd{margin:2px 0 0;font-size:26px;font-weight:700;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.stats p{margin:0;font-size:11.5px;color:var(--dim)}
main{padding:34px 0 70px;display:flex;flex-direction:column;gap:38px}
section{display:flex;flex-direction:column;gap:12px}
section.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:30px;align-items:start}
section.two>div{display:flex;flex-direction:column;gap:12px}
h2{margin:0;font-size:19px;font-weight:700;letter-spacing:-.01em;
   padding-bottom:8px;border-bottom:2px solid var(--blue);align-self:start}
.note{margin:0;color:var(--ink-2);font-size:13.5px;max-width:88ch}
.dim{color:var(--dim)}
code{font-family:var(--mono);font-size:12.5px;background:var(--rule-2);padding:1px 5px;border-radius:4px}
.scroll{overflow-x:auto;background:var(--card);border:1px solid var(--rule);border-radius:10px;
        box-shadow:var(--shadow)}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--rule-2);vertical-align:top}
thead th{position:sticky;top:0;background:var(--card);border-bottom:1px solid var(--rule);
         font-size:11.5px;letter-spacing:.05em;text-transform:uppercase;color:var(--dim);font-weight:650;
         white-space:nowrap;z-index:2}
tbody tr:last-child td,tbody tr:last-child th{border-bottom:0}
tbody tr:hover td,tbody tr:hover th{background:var(--rule-2)}
.num td{font-variant-numeric:tabular-nums}
.mono{font-family:var(--mono);font-size:12px}
.mid{text-align:center}
.cat{font-family:var(--mono);font-size:11.5px;color:var(--dim);white-space:nowrap}
.note-cell{max-width:46ch;color:var(--ink-2);font-size:12.5px}
table.matrix th.lead{position:sticky;left:0;background:var(--card);z-index:1;font-weight:500;
        font-size:12.5px;max-width:340px;border-right:1px solid var(--rule)}
table.matrix thead th.lead{z-index:3}
table.matrix th.lead a{color:inherit;text-decoration:none;border-bottom:1px dotted var(--rule)}
table.matrix th.lead a:hover{color:var(--blue)}
table.matrix th.rot span{display:block;writing-mode:vertical-rl;transform:rotate(180deg);
        height:92px;font-weight:600}
table.grade th.lead{font-weight:600}
.chip{display:inline-flex;align-items:center;justify-content:center;min-width:22px;height:22px;
      padding:0 6px;border-radius:6px;font-size:12px;font-weight:700;line-height:1}
.chip.ok{color:var(--ok);background:var(--ok-bg)}
.chip.warn{color:var(--warn);background:var(--warn-bg)}
.chip.susp{color:var(--susp);background:var(--susp-bg)}
.chip.fail{color:var(--fail);background:var(--fail-bg)}
.chip.blind{color:var(--susp);background:var(--susp-bg)}
.chip.na,.chip.blank{color:var(--blank);background:var(--blank-bg)}
.tag{display:inline-block;padding:1px 7px;border-radius:5px;font-size:11.5px;font-weight:650;
     background:var(--blank-bg);color:var(--ink-2);white-space:nowrap}
.tag.ok{background:var(--ok-bg);color:var(--ok)}
.tag.warn{background:var(--warn-bg);color:var(--warn)}
.tag.susp{background:var(--susp-bg);color:var(--susp)}
.tag.fail{background:var(--fail-bg);color:var(--fail)}
.pc{display:inline-block;padding:1px 7px;border-radius:5px;font-size:11.5px;font-weight:700;
    font-variant-numeric:tabular-nums}
.pc.yes{background:var(--ok-bg);color:var(--ok)}
.pc.no{background:var(--warn-bg);color:var(--warn)}
.legend{display:flex;flex-wrap:wrap;gap:8px 20px;margin:0;padding:0;list-style:none;font-size:13px}
.legend li{display:flex;align-items:center;gap:7px}
.meter{display:inline-block;width:72px;height:6px;border-radius:3px;background:var(--rule);
       margin-right:8px;vertical-align:middle;overflow:hidden}
.meter i{display:block;height:100%;background:var(--blue)}
.deflist{margin:0;display:flex;flex-direction:column;gap:10px}
.deflist dt{font-weight:700;font-size:13.5px;color:var(--blue)}
.deflist dd{margin:2px 0 0;color:var(--ink-2);font-size:13.5px;max-width:92ch}
.limits ol{margin:0;padding-left:22px;display:flex;flex-direction:column;gap:8px;
           color:var(--ink-2);font-size:13.5px;max-width:92ch}
details{background:var(--card);border:1px solid var(--rule);border-radius:10px;padding:10px 14px;
        box-shadow:var(--shadow)}
details+details{margin-top:8px}
summary{cursor:pointer;font-size:13.5px;display:flex;flex-wrap:wrap;gap:8px;align-items:baseline}
summary::marker{color:var(--dim)}
details[open]{padding-bottom:14px}
details[open] summary{margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--rule-2)}
details .scroll{box-shadow:none}
footer{border-top:1px solid var(--rule);padding-top:18px;color:var(--dim);font-size:12.5px}
footer p{margin:0;max-width:92ch}
a:focus-visible,summary:focus-visible{outline:2px solid var(--blue);outline-offset:2px;border-radius:4px}
@media (max-width:720px){
  .wrap{padding:0 16px}
  table.matrix th.lead{max-width:190px}
}
"""


if __name__ == "__main__":
    sys.exit(main())
