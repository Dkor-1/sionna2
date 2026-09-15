# When creating a new file or a new memo

> **Why this document exists.** On 2026-09-04~06 the repository was audited line by line, **900 findings** were
> confirmed and all of them fixed. Grouping those 900 by root cause gave **16 kinds**, and those 16 cover the 900
> almost entirely. So **if new work avoids just these 16, those 900 will not come back.**
> Every rule below is **something that actually got caught**, and each item records that incident as it happened.

Gate: `benchmark/check_new_file_rules.py` catches what can be caught mechanically (only new ones after the baseline).

## ⚠The gate catches only **five** of the 16

| | What | How |
|---|---|---|
| ✅ Gate | Dead temporary paths · missing Python · writes outside the repo · required arguments not written · unbuildable ledgers · placeholders | `check_new_file_rules.py` |
| ⛔ Gate cannot | The other 11 — hand-typed numbers · absence without a population · causation without a control · calling simulation a measurement · a face stronger than the body … | **A human reads it, or an audit** |

⭐**Why this split is written down.** On 2026-09-06 the person who wrote this document went on to create 11 new files
**without running the eight-line checklist even once**, and one of them broke rule ⑥
(「기능은 검증됐지만」 [the function has been verified, but] in `runners/make_jobs_0911.py` — that gate measures only whether it is
self-consistent with the repository's 2-line model). The gate cannot catch that.
⇒ **Passing the gate does not mean the rules were followed.** The 11 outside the gate must be read by a person
  before saving, and what is missed is caught only by an audit.
Source data: `work/sweep_0904/rootcauses_0906.json`

---

## ⭐First — these eight lines before saving a file

1. Did every **number** written in this file come from a ledger key via an f-string? Is there even one hand-typed number?
2. Is the **cell** that produced each number (airframe · elevation · azimuth · range · frequency · sample count) **in the same sentence**?
3. If you wrote 「없다·유일·최초·가장·전부」 [none · only · first · most · all], is the **population counted** in the same sentence?
4. If you wrote 「때문이다·A 가 아니라 B 다」 [because · it is B, not A], is there a **control arm that switched that variable off and on** in the ledger?
5. If you wrote 「실측·검증됨·독립」 [measured · verified · independent], is it an **external measurement**? (This repository has 0 comparisons against real hardware measurements)
6. Is the **title · headline · caption** no stronger than the body? Was it cut from the body's weakest sentence?
7. If this file is in `outputs/`, does a **real script in the repo** rebuild it with one command?
8. Are any `{}` · `?` · TBD · nan left?

---

## The sixteen — in order of how often they recurred

### 1. Published numbers were typed by hand into sentences · docstrings · captions · labels instead of being read from the ledger — when the ledger reruns the number does not follow, and even within one file it splits into two values

**152 findings.** Machine-checkable

⭐**Rule** — every number written in a new file is printed from a ledger key via an f-string — hand-typed numbers (including numbers given as examples · sample counts · parameters in labels) do not go into sentences

**What actually happened** — benchmark/mesh_cert_symmetry_derived_0816.py:239 「부피×밀도 질량이 공표 TOW 의 1.1~5.0 배다(감사 I9, 이 라운드가 재확인)」 [the volume×density mass is 1.1~5.0× the published TOW (audit I9, reconfirmed by this round)] — line 190 of the same file and the ledger say 5.2 (5503/1063=5.18), yet it went out with the extra reassurance «재확인» [reconfirmed]. In the same way, src/report_registry.py:39 「본편 11 권 + 별편 8 편, 곧 노트북 23 개다」 [11 main volumes + 8 companion volumes, i.e. 23 notebooks] disagreed with the 33 on disk and the canonical 13 main / 7 companion volumes

<details><summary>Machine check</summary>

Hits of `[-+]?\d+(\.\d+)?\s*(dB|dBsm|%p|%|mm|m|Hz|GHz|배|편|권|칸|기체|개)` in string literals without an f prefix in builder .py files → fail (constant-definition lines excepted). A literal tail after an f-string, `f"[^"]*\{[^}]+\}[^"]*\d+\.\d+`, also fails. If a number in a ledger prose field appears in none of the numeric fields of the same JSON (rel_tol 1e-3), warn; if one file has two values for a quantity with the same name and unit, fail. Counts · ordering · monotonicity are backed by len() · max() · sorted() + assert

</details>

### 2. Ledger JSON · hand-written docs were written by hand without an in-repo script, or with the generator recorded at a path that does not exist (scratchpad · /tmp), and the file:line · § cited as evidence did not exist either — corrections have nowhere to flow back to

**148 findings.** Machine-checkable

⭐**Rule** — keep in outputs/ only files that a real in-repo script rebuilds with one command (that path in _meta.generator), and confirm that every reference written in a document (file · line · section · builder) exists at the point of writing — if you cannot, do not write the number and send it to notes/

**What actually happened** — the two files that meta.builder in outputs/reference_library.json points to do not exist in a repo-wide find, yet three statements that came only from that ledger — 「표준 관행」 [standard practice] · 「유일한 게재 논문」 [the only published paper] · 「이 라이브러리에 없다」 [not in this library] — flowed straight into docs/REFERENCE_LIBRARY.md. docs/EXPERIMENT_BACKLOG.md:247 cites RESUME.md:386 from an already-deleted .bak edition as evidence

<details><summary>Machine check</summary>

For each outputs/**.json, `_meta.(generator|producer|builder|generated_by)` ① exists ② every `\S+\.py` in it exists relative to repo_root ③ is not `^(scratchpad/|/tmp/|/home/|/Users/)` ④ that script opens this JSON path (grep) — if any of these breaks, put it on the UNBUILDABLE list and fail every src · benchmark · docs · reports line that cites that file. On the document side, check `([A-Za-z0-9_./-]+\.(md|py|json|ipynb))(:(\d+))?` for existence and being within the line count, and `§[\d.]+` for an existing heading

</details>

### 3. Sentences were closed with 「없다·유일·처음·가장·전부·아무도」 [none · only · first · most · all · nobody] without writing the population · range that was scanned — not finding something in the few papers we read was promoted to absence from the whole literature

**139 findings.** Machine-checkable

⭐**Rule** — use 「없다·0 편·유일·최초·가장·전부·아무도」 [none · 0 papers · only · first · most · all · nobody] only when the same sentence states the population counted (what, how many papers · cells, which search terms, as of when) and the gaps not looked at — if you cannot, downgrade to 「우리가 훑은 N 안에서는 못 찾았다」 [not found within the N we scanned]

**What actually happened** — docs/REFERENCE_LIBRARY.md:107 「표적 산란을 스스로 계산하고 그 위에 검출을 세운 드론 논문이 없다」 [there is no drone paper that computes target scattering itself and builds detection on top of it] — in fact this is a gap within the library's 94 papers · 64 read closely, but there is no range phrase. outputs/reflib_sweep_sionna.json:1471 writes 「…가 이 분야의 기본값이다」 [… is the default in this field], but counts in the same file is 1/137

<details><summary>Machine check</summary>

A sentence (split at periods) that hits `(없다|없음|전무|0\s*편|유일|처음|최초|가장|최고|제일|전부|모두|아무도|어디서도|한 번도|표준 관행|only|never|nobody|the first)` but has no population token `(\d+\s*(편|건|칸|기체|종|점|papers)|아카이브|코퍼스|우리가 (훑|찾|읽|센)|범위에서|\d+\s*/\s*\d+|as of \d{4})` fails. In titles · ⭐ · headline*/tldr/claim fields it fails without exception. If the same file has counts · n_papers keys, stating those values alongside is required. The only exemptions are correction lines starting with ⛔/⚠ and other people's sentences inside quotation marks

</details>

### 4. After withdrawing a value · verdict, the other places that wording lives (builder f-strings · twin md · summary tables · section titles · comments) were not followed up, so the retracted sentence came back on rebuild

**114 findings.** Machine-checkable

⭐**Rule** — when withdrawing a value or sentence, grep the whole repo for that string, and write «내렸다» [withdrawn] only after every hit is fixed in the same commit or stamped with ⛔+date; before writing a new sentence, first compare it as a string against RETRACTION_LOG and the ⛔ lists

**What actually happened** — reports/_parts/82_el-nadir-floor.ipynb c10:1 「## 사각지대는 반각 몇 도짜리 원뿔이다」 [## the blind spot is a cone with a half-angle of so many degrees] — c0 of the same file retracted it with ⛔ on 2026-09-04 and the builder comment (src/build_part12_elevation.py:925~932) also records the retraction, but only the title string (:1320) was not fixed, so it comes back on every rebuild. 「세 두께가 소수점까지 같은 리듬 80.5 % 를 낸다」 [the three thicknesses give the same rhythm 80.5 % down to the decimal] in atlas/00_since_deck.html:253 is also a value R29 (docs/RETRACTION_LOG.md:1318) withdrew, but it carries no tag

<details><summary>Machine check</summary>

Make «내린 문구» [the withdrawn wording] a mandatory quoted field for every RETRACTION_LOG entry → merge it with the ledger wording under `⛔|must_fix|인용 금지|refuted_ko` into banned_strings.json → run `grep -rF -n` over everything → fail if there is no `⛔|⚠|철회|정정|R\d+|20\d\d-\d\d-\d\d` within ±3 lines of a hit. If only the generated output is fixed and the same string remains in src/**.py · benchmark/**.py literals, fail separately as «재빌드 부활» [resurrection on rebuild]. If any self_check in the output JSON has passed=false, exit the builder non-zero

</details>

### 5. The same verdict sentence was copied by hand to several places (new edition · old builder · generated notebook · twin md · Korean/English pair · copies of plan JSON), so fixing one left the rest with the old wording

**110 findings.** Machine-checkable

⭐**Rule** — do not keep the same sentence in two places — make one place (a ledger key or a builder constant) the canonical source of the wording and have the rest read and print it; on any unavoidable copy, attach 「출처: 파일#키」 [source: file#key] and put the same qualifiers · ⚠ on both sides

**What actually happened** — 「취약성을 정하는 것은 기체 크기가 아니라 밴드 간 σ 로브 산포다」 [what decides vulnerability is not airframe size but the inter-band σ lobe spread] in outputs/paper_kit.json sits in five places in the same file — 5785 · 5794 · 5803 · 5812 · 13529 — while the current builder src/build_part10_results.py:1239 already writes the opposite wording as 「⛔ 옛 제목」 [old title] — citing parties split on which edition to copy

<details><summary>Machine check</summary>

Across all of src · benchmark · outputs · docs · reports · atlas · prior_work, hash Korean sentences of 40 or more characters (or 12 or more words) after normalising whitespace · digits · particles · emphasis marks, and list any that occur in 2 or more places as failures (a register of duplicate wording). The pairs `src/build_part*.py` ↔ `src/make_report*.py`, `prior_work/src/make_pw*.py` ↔ `prior_work/*.ipynb`, and HTML render ↔ readme render are always checked. The pairs `*_ko`/`*_en` and `headline_*`/`verdict` pass only if their sets of number tokens and their counts of qualifier tokens match. The exception is the single place where an f-string is injected from the ledger

</details>

### 6. Runs not made · quantities not measured · simulation outputs · our kernel's self-checks were called 「실측·측정됨·검증됨·독립·확증」 [measured in the field · measured · verified · independent · confirmed], or gaps were filled with neighbouring values · inference and asserted as if measured

**99 findings.** Machine-checkable

⭐**Rule** — use 「실측·측정·계측·measured·검증됨·독립」 [field measurement · measurement · instrumentation · measured · verified · independent] only for external instruments · measured curves in the literature; call our outputs 「원장 재계산(파일:키)」 [ledger recomputation (file:key)] · 「우리 커널 계산」 [our kernel's computation] · 「자기일치 바닥」 [self-consistency floor], and for conditions not run write 「아직 안 쟀다」 [not measured yet] in the same sentence

**What actually happened** — outputs/das_fleet_ours.json:43 「평판 실측이 β≤60° 에서 0.3 dB 안으로 그 예측과 맞는다」 [the plate measurement matches that prediction within 0.3 dB at β≤60°] — the cited outputs/sbr_defect_fixes.json is a self-check of a PEC plate run with our SBR, and this repository has 0 comparisons against real hardware measurements. The comb_repaired key cited by 「제거는 박자를 되찾는다」 [removal recovers the beat] at reports/12_outdoor-scene.ipynb c9:14 never passes through the notch (cs_eca) at all

<details><summary>Machine check</summary>

Fail if the evidence path on a line hitting `(실측|측정된|측정으로 확인|계측|검증(됐|되었|완료)|확증|\bmeasured\b)` is outputs/*.json · benchmark/*.py (the whitelist of real hardware measurements currently has 0 entries). Fail if a key whose ledger confidence is medium|low, or whose value contains 「미확정·추론·못 찾」 [unsettled · inference · could not find], gets a «확인» [confirmed] stamp. Fail if a file with `_meta.env.gpu == false` asserts GPU-engine results. Catch violations with a verb↔key table (removal · notch · ECA ↔ comb_repaired/fill forbidden), and for 「독립·따로 쟀」 [independent · measured separately], fail if the import graphs of the two builders overlap

</details>

### 7. Short layers such as titles · headlines · one-line summaries · figure captions · table cells were written by hand separately from the body, so conditions and ⚠ · qualifiers fell off and superlatives · causation absent from the body were newly attached — the only line the audience reads is stronger than the body

**83 findings.** Machine-checkable

⭐**Rule** — do not write titles · headlines · one-line summaries · figure captions afresh; cut the weakest sentence from the body as is, and do not put up any number · verdict whose conditions (airframe · elevation · range · band · sample count) and qualifiers do not fit in that spot

**What actually happened** — src/build_part12_elevation.py:934(TITLE_82) 「나딧 잔여의 64 % 는 광선 격자 표본화 잡음이고」 [64 % of the nadir residual is ray-grid sampling noise, and] — the caveat_ko of the ledger outputs/refute_nadir_mechanism_final.json says «이 나눗셈은 어림이고 64 % 는 하한» [this division is a rough estimate and 64 % is a lower bound] and the value is from the 10 m run, but the title has neither the lower bound nor the range. This title appears alone, without the body, in six places across the README · indexes

<details><summary>Machine check</summary>

Extract only face strings: `^#{1,4} `, the first 40 lines of a document, «한 줄 요약/TL;DR» [one-line summary/TL;DR] blocks, the first line of notebook md cells, the first table column, keys `^(headline\w*|title|one_line|so_what|reading|verdict|summary|answer|paper_caption|replace_with|citable\w*|can_write\w*)$`, and the arguments of builder `TITLE_\w+` · `set_title|suptitle|supxlabel|fig\.text|annotate`. ① if it is not a substring of any sentence in the body, mark it «새로 쓴 요약» [newly written summary] ② if it contains a number but fewer than 2 condition tokens, fail ③ if the same file has ⚠ · ⛔ · qualifiers but the face does not, fail ④ if the face has superlatives · universals · causation · 「A 가 아니라 B 다」 [it is B, not A], fail

</details>

### 8. Closing words that harden an observation into a verdict (「뿐·유일·완전·절대·불가능·정답·검증된·A 가 아니라 B 다」 [merely · only · complete · absolutely · impossible · the right answer · verified · it is B, not A]) and verdicts ranking tools were written — with 0 comparisons against real measurements, our approximation stood as the grader

**83 findings.** Machine-checkable

⭐**Rule** — do not write closing words, or superiority · impossibility verdicts with a tool · method as the subject — write 「이 설정(기체·앙각·거리·팔)에서 본 것은 …까지다」 [what was seen in this setting (airframe · elevation · range · arm) goes as far as …], write implementation limits as 「현재 구현으로는」 [with the current implementation], and deliver verdicts in the presenter notes

**What actually happened** — docs/PRIOR_WORK_COMPARISON.md:197 「Ziganshin 의 HH/VV 편파 분리. **물리적으로 불가능**하다: `grep -ci polari` = 0」 [Ziganshin's HH/VV polarisation separation. It is **physically impossible**: the grep count = 0] — promoted the fact that our implementation is scalar into a property of physics. 「⇒ 탐지 축에서 PathSolver 는 경쟁자가 아니다」 [⇒ on the detection axis PathSolver is not a competitor] at docs/RETRACTION_LOG.md:1058 has the same shape and is a head-on violation of the standing rule 「시오나가 틀렸다고 하지 않는다」 [do not say Sionna is wrong]

<details><summary>Machine check</summary>

Block the forbidden-word regex in a commit hook: `뿐이(다|고)|유일(한|하게)|완전(한|히)|절대 (못|안)|불가능|정답|검증된|틀렸다|이긴다|보다 낫다|앞선다|우월|경쟁자가 아니|[^.]{2,30}(이|가) 아니라 [^.]{2,30}다` + the engine-specific `(Sionna|스톡|PathSolver|SBR|PO|우리 커널)[^.]{0,40}(틀리|부정확|과대|과소|못 (낸|한|따라)|불가능|지배력이 없)`. The string 「물리적으로 불가능」 [physically impossible] fails unconditionally, with or without conditions (→ 「현재 구현으로는」 [with the current implementation]). The exceptions are other people's words inside quotation marks, and cases where a control pair (band · ground truth · counterexample cell) and the ledger path are in the same sentence

</details>

### 9. When writing a number, the cell that produced it (airframe · elevation · azimuth · range · frequency · sample count · run) was detached from the sentence, so a value measured in one cell reads like an unconditional constant · physics (for values with a spread, the maximum hardened into the representative value)

**82 findings.** Machine-checkable

⭐**Rule** — in a sentence containing a number, attach the cell that produced it (airframe · elevation · azimuth · range · frequency · sample count) and the ledger key in the same sentence, and if there is a spread, write the ledger's min/max as the spread — if you cannot attach them, do not use the number

**What actually happened** — outputs/outofband_power.json:922 「⭐격자를 얼리면 대역밖 절대 전력이 λ/12 에서 13.1 dB, λ/32 에서 20.1 dB 내려간다」 [freezing the grid lowers the absolute out-of-band power by 13.1 dB at λ/12 and 20.1 dB at λ/32] — the _meta of the same file is a single cell, matrice4e · az 0° · el −15° · 3.5 GHz · PRF 19700, yet it was carried into reports/02_kernel.ipynb without conditions. 「PathSolver 최선의 판(빗살 52 dB)」 [PathSolver's best run (comb 52 dB)] at docs/STANDARD_FRAME.md:60 also moves over 40.5~52.0 dB when the range axis is shaken

<details><summary>Machine check</summary>

Block sentences containing `[-+]?\d+(\.\d+)?\s*(dB|dBsm|%p|%|배|m/s|Hz|kHz|GHz|ms|m)\b` that have no condition token at all. Condition tokens = airframe names (generated automatically from the DRONES keys in src/drones.py) | `el\s*[-−+]?\d|앙각` | `az|방위` | `\d+\s*m\b|거리` | `GHz|MHz` | `n\s*=\s*\d|\d+\s*(칸|자세|점|셀|편|종|판)`. In ledger JSON, applying it only to the values of `headline*/verdict*/so_what*/reading/text_ko` keeps false positives low. Quoting only one end of a key whose ledger also carries min/max fails

</details>

### 10. Causes · mechanisms · counterfactuals were asserted as if observed without a control group that switched that variable off and on — jumping straight from one line of a measured quantity to 「무엇 때문이다 / A 가 아니라 B 다」 [it is because of X / it is B, not A]

**76 findings.** Machine-checkable

⭐**Rule** — write 「때문이다·탓이다·우연이 아니다·였다면·A 가 아니라 B 다」 [because · due to · not a coincidence · had it been · it is B, not A] only when a control arm that switched that cause off and on is in the same ledger — if not, split observation and interpretation into two sentences and write 「…로 읽는다 — 원인은 아직 안 쟀다(후보 기전)」 [read as … — the cause is not measured yet (candidate mechanism)]

**What actually happened** — src/build_report18_switch_grid.py:462 「정면에서는 … 유한한 광선으로 재느라 생긴 계산 흔들림이 상한 위를 백색으로 채워 놨기 때문이다」 [head-on, … it is because the computational jitter from measuring with a finite number of rays filled the region above the cap with white] — this run (15 m · 8192 poses · el 0) has 0 paired runs with a reduced ray count. benchmark/das_fleet_ours.py:512 likewise hardened what line 357 of the same file wrote as 「일 수 있고」 [may be] into 「그것은 …이다」 [it is …]

<details><summary>Machine check</summary>

Hits of `때문이다|탓이다|덕분|라서 |우연이 아니|였다면|이었다면|의 성질이다|기전(은|이)|원인(은|이)|이 아니라 .{0,20}(다|이다)|because|caused by|driven by` → fail if the same ledger has no control key `(control|null|ablation|swap|_off\b|with_|without_|run_id|대조)` (force the wording to 「후보 기전」 [candidate mechanism]). Counterfactual endings (`였다면|이었다면`) go to the human review queue even when evidence is attached — a machine cannot see whether the control group was actually built. Warn if aggregate lines (`중앙값|평균`) lack `n=|칸 중|산포`

</details>

### 11. Numbers decided by free parameters (window half-width hw · grid div · ray budget · threshold · guard width · denominator definition) were written as physical quantities without the knob, and detection floors · nulls · below-threshold were closed as 「없다·불변·0·비트 동일」 [none · invariant · 0 · bit-identical]

**63 findings.** Machine-checkable

⭐**Rule** — before writing a number, shake the knob that made it by one step, and if the conclusion changes do not write the magnitude — when you do write it, put the knob value on the same line, and write floors · nulls · below-threshold only as 「이 잣대로는 못 읽는다(바닥·문턱 값 병기)」 [cannot be read with this yardstick (floor · threshold value stated alongside)]

**What actually happened** — benchmark/r12_azimuth_harvest.py:606 used a rhythm share of 63 % as the basis for the verdict 「익사하지 않는다」 [does not drown], but on the same knobs it is 9.9 % with hw 2 Hz and 98.9 % with f_above left at its default (docs/RETRACTION_LOG.md:1318 R29). benchmark/report15_null_control_v2_append.py:24 wrote a ptp of 0.0045 dB as 「변조가 0 이다」 [the modulation is 0]

<details><summary>Machine check</summary>

Ledger entries must carry `knobs` (hw · f_above · div · spp · seed · budget · THRESH · PROM · HALF_WIDTH · guard) and `shaken` (the range shaken) — prose that cites the entry without writing the knobs fails. Grade · eligibility strings (`A_convention_free|headline_eligible`) are forbidden as literals and granted only when the knobs_varied set difference is empty. On a degenerate denominator (`f_tip==0|cos(el)==0|n_independent==1|is_saturated`), block ratio output. Nulls · floors: fail if `(p99\.?9?|분위|null|바닥|floor|SNR\s*\d|p\s*=|\de-0\d)` and `(없다|불변|죽은 파라미터|0 ?개|정확히 0|비트 동일|무시가능|못 넘는다)` are in the same sentence (pass if 「못 읽는다·검출 바닥 아래」 [cannot be read · below the detection floor] is stated alongside)

</details>

### 12. What was seen in one cell (1 airframe · 1 elevation · 1 pose · 1 paper · 2~3 points) was raised into a property, law or trend of a whole class · tool · field

**57 findings.** Machine-checkable

⭐**Rule** — make the subject of the sentence the same size as the sample — with 1 airframe write that airframe's name, and with 3 or fewer points or a difference within the spread, do not use trend words (the more … · proportional · monotonic · what decides it is) and just list the values

**What actually happened** — benchmark/adv_rf_layer_0816.py:279-282 「el −30 에서는 n≈0.9 라 20log10 은 정확히 2배 과대」 [at el −30, n≈0.9, so 20log10 is exactly 2× too large] — K2b in the same ledger is 1.802 / 1.654 / 0.881 / −1.197 per airframe, yet the value of matrice4e alone was generalised without naming the airframe. benchmark/sigma_sensitivity.py:652 built 「취약성을 정하는 것은 …이다」 [what decides vulnerability is …] on five airframes and a correlation coefficient of +0.091

<details><summary>Machine check</summary>

Make `drones` · `n_samples` fields mandatory for every ledger entry, and if `n_samples==1 or len(drones)==1` while the citing prose has a plural subject `(모든|전 기체|기체별로|공통 성질|들은|every|all|분야|문헌 전반)`, fail unconditionally. Trend words `(일수록|비례|반비례|단조|커질수록|줄어들수록|경향|법칙|정하는 것은|지배한다)` pass only when the number of evidence points ≥ 4 and the correlation coefficient |r| ≥ 0.5. If a conclusion field has a universal word, force printing the axis length of that output (cells · rows · airframe count) alongside, and fail if that number is 1~2

</details>

### 13. Only the value was quoted, without carrying over the qualifiers the ledger · source attached to it (caveat · note · n · confidence · range · exceptions · ⚠ · citation ban) — keeping caveats apart from the value let the tag fall off

**46 findings.** Machine-checkable

⭐**Rule** — when quoting a ledger key or someone else's sentence, carry the qualifiers attached to that value (caveat · note · n · confidence · range · exceptions · ⚠) into the same sentence — do not substitute 「다른 절 참조」 [see another section], and if you drop conditions or add words, remove the quotation marks and mark it as our verdict

**What actually happened** — docs/S2R_JEPA_POSITION.md:171 「Trinh 2026 이 배경 정렬 하나로 chance 50 % → 97 % 를 만들었다」 [Trinh 2026 took chance 50 % → 97 % with background alignment alone] — §9 of the same document says «확인 전 인용 금지» [do not cite before confirming], but the value itself carries no mark, and docs/SIM2REAL_PLAN.md:294 inherited it as is. outputs/psolve_adopt.json:830 carried over 「616 ms」 while stripping «LUMI 8노드(MI250X 32장)» [LUMI 8 nodes (32 MI250X cards)] from line 433 of the same file

<details><summary>Machine check</summary>

Make it a rule that ledger values keep caveats inside the value object (`{"value":…, "caveat":…}`), not in sibling keys, and fail a sentence citing a key that has `caveat|note|note_ko|warning|but|limits|confidence|precision|held_fixed|_what` if it lacks the key words of that wording (「하한|상한|어림|예외|한정|미확정」 [lower bound|upper bound|rough|exception|limited|unsettled]|⚠|⛔). Compare strings inside quotation marks («…»/「…」/"…") with the source quote field for an exact match after normalising whitespace · particles — block on mismatch. A line containing someone else's number must have at least one hardware · target token

</details>

### 14. Two numbers with different axes (unit · airframe · elevation · band · fit range · metric definition · window · sample independence) were placed side by side in one sentence · table row and judged with ✅ · 「범위 안·일치·N 배」 [within range · agrees · N×]

**45 findings.** Machine-checkable

⭐**Rule** — do subtraction · ranges · ratios · 「범위 안·일치」 [within range · agrees] only between cells whose axes are all the same, and if even one differs write 「대조 불가」 [not comparable] and why — fill in the four cells band · fit range · metric definition · sample independence first

**What actually happened** — docs/INJECTION_PRECEDENT.md:153 「밴드 기울기 6-18.2 GHz | ✅ 0.264 dB/GHz — 실측 0.21~0.315 범위 안」 [band slope 6-18.2 GHz, 0.264 dB/GHz — within the measured 0.21~0.315] — we fit the partial band 6~18.2 GHz while the literature fits the full 1.8~18.2 GHz band once, so measured over the same interval it is 2.07×. 「레벨차 60 dB 는 확정」 [the 60 dB level difference is settled] in outputs/deck0811_redundancy.json:77 is likewise the difference between an area integral [m²] and a channel amplitude that includes free-space loss

<details><summary>Machine check</summary>

Axis tags (`unit, drone, el_deg, band, fit_range, arm, window, metric, n`) are mandatory on every numeric ledger entry. If prose linking two numbers (`대|vs|보다|→|차이|같은 크기|배|범위 안|일치|✅|INSIDE|steeper`) cites two keys with different tags, fail. If a comparison sentence has neither the interval notation `[0-9.]+\s*[-–~]\s*[0-9.]+\s*GHz` nor the sample notation `\d+\s*(기체|점|편)`, fail. If the unit nouns (cell · row · paper · arm) of the numbers before and after a 「그중」 [of which] link differ, fail; citing a sum key (`or|plus|합계|total|_and_`) as a standalone noun also fails. Make margin/ratio only through functions that take value · budget as one tuple, and block ratio output when the denominator is degenerate

</details>

### 15. Standing rules (outdoor environment only · no chamber · no insider words) were broken outright in newly written presentation paragraphs · glossaries

**10 findings.** Machine-checkable

⭐**Rule** — in new files · presentation paragraphs · glossaries, do not describe a chamber · indoor controlled geometry as our setting, and do not coin insider words · abbreviations — explain a tool in one line on the spot by what it does, not by its environment

**What actually happened** — prior_work/src/make_pw03.py:105 「우리는 NVIDIA Sionna RT 로 챔버 전파를 담보하고(선행 Deterministic-Modeling·SimART 와 같은 용례)」 [we secure chamber propagation with NVIDIA Sionna RT (the same usage as prior Deterministic-Modeling · SimART)] — the header on the very next line itself declares a presentation spot, «§4. 정직한 한 문단 (외부에 말할 때)» [§4. One honest paragraph (when speaking externally)], and the two prior works it attributes this to are outdoor cases per the ledger, so «같은 용례» [the same usage] does not hold

<details><summary>Machine check</summary>

`grep -rn '챔버|무반향|anechoic' <신규·변경 파일>` → fail if the sentence describes our setting (subject `우리|본 연구|our_row`). In presentation spots (titles · one-line summaries · glossary tables · «외부에 말할 때» [when speaking externally] sections) it fails even with a literature source; quoting a literature description passes only when `arXiv|doi|[A-Z][a-z]+ 20\d\d` is on the same line. Grep presentation spots for the coined-word dictionary and the tool names (Sionna · PathSolver · SBR · PO), and fail if the same line has no one-line explanation

</details>

### 16. The conclusion sentence was fixed before its numbers were filled in or checked, so placeholders · failed counts were published together with the conclusion

**6 findings.** Machine-checkable

⭐**Rule** — write a conclusion sentence after the numbers in it are filled in and checked — if `{}` · `?` · TBD · nan remain or a count · collection failed, do not emit that sentence at all (no conclusions without numbers)

**What actually happened** — docs/DECK_FACTS.md:407 (benchmark/deck_facts.py:1100) 「'rcs' 라는 단어가 ?회, 'radar_cross_section' 이 ?회 나온다 — 즉 산란적분도 σ 출력도 없다」 [the word 'rcs' appears ? times and 'radar_cross_section' ? times — so there is neither a scattering integral nor a σ output] — the numbers of the same item are {"error": "No module named 'sionna'"}, yet the absence-verdict sentence remained, and because its grade is computed-by-us the audience reads it as counted in this run

<details><summary>Machine check</summary>

After the build, pass only if `grep -nE '\{[A-Za-z_0-9.]+\}|%\.?[0-9]*[dfs]|\?\s*(회|개|dB|%|Hz)|TBD|N/?A|None|nan|\{\}' outputs/*.json docs/*.md reports/**/*.ipynb` has 0 hits. The claim of any item whose `numbers` has an `error` key must not be published. Hand-done conversions (「N 분의 일·N 배」 [one N-th · N×]) pass only with the calculation in adjacent parentheses, and when wavelength and frequency are on the same line, recompute automatically with λ=c/f and fail if the error exceeds 10 %

</details>

---

## 17. When creating a new heavy computation, **pin the cores** (not machine-checkable — a human checks)

⭐**Rule** — this machine always has the GPU queue running, and our share of CPUs is 16. The supervisor
**does not launch GPU workers at all when our cgroup's CPU utilisation exceeds 0.85.** So
a newly created computation script **must decide for itself how many cores it uses.**

⛔⛔**`OMP_NUM_THREADS=1` does not stop it.** The SBR kernel's parallelism does not follow that environment variable.
The only thing that stops it is **`os.sched_setaffinity`**:

```python
ap.add_argument("--max-cores", type=int, default=2)
...
if a.max_cores > 0 and hasattr(os, "sched_setaffinity"):
    _all = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, set(_all[:max(1, min(a.max_cores, len(_all)))]))
```

**What actually happened — the same incident happened twice in one day (2026-09-07).**
① An `audit_*.py` launched by an audit subagent was eating **1,433 %**, and the three supervisors
   had been stuck at 「⛔대기: CPU 사용률 1.00 > 0.85」 [waiting: CPU utilisation 1.00 > 0.85] in 20/20 of the latest checks.
② **Right after** fixing that, `benchmark/ground_reciprocity_0907.py` was launched with
   `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 19`,
   and it ate **1,484 %**. The new supervisor `sup_jobs_0913b` had taken 55 lines
   and **could not launch a single line for 20 minutes** (queue 0/55). Having set every environment variable did not
   mean 「막았다」 [it was stopped] — **nobody measured it.**

⇒ After launching a heavy computation, **look at the actual % once** with `ps -eo pid,pcpu,args`.
  Not the number of settings — that percentage is the evidence.

---

## When editing this document

⛔This document is **not grown by hand.** Add a new item only when there is an incident that actually got caught, and
record that incident under 「What actually happened」 with file:line. Rules without evidence do not get followed.

