# Repository guidance

Read `CLAUDE.md` and `docs/HANDOVER_MAP.md` for the repository's existing research,
publication, and queue rules. Explicit user instructions take precedence.

## Language preference

User preference recorded on 2026-09-15:

- Write progress updates and technical explanations during ongoing work in English.
- Write final responses and directly user-facing research reports in Korean.
- Write new code, identifiers, comments, docstrings, internal working notes,
  configuration descriptions, and machine-oriented artifacts in English.
- Korean report prose may live in report templates or report data when needed to
  generate the Korean report. Preserve exact source quotations and official names.
- Existing agent-facing documents (conventions, runbooks, audit and review memos,
  internal READMEs) are being migrated to English **one file at a time, not in
  parallel** (user decision 2026-09-15). Translate line for line, keep machine
  strings, paths and numbers byte-identical, keep Korean user quotations verbatim
  with an English gloss, and check each file mechanically against the original
  before installing it. Do not rename files. Reports (notebooks), deck scripts and
  other text the user reads directly stay Korean.

## Current ISAC experiment constraints

- Use one USRP X410 as the main hardware platform.
- Minimize reliance on older USRPs; treat them as optional validation equipment.
- Six directional antennas are available; models, bands, and calibrated patterns
  are still unspecified. Do not infer their coverage from the radio's coverage.
- Engine roles (user decision 2026-09-15, evening KST; supersedes the "PathSolver only" note in
  runners/jobs_0936_attrib.txt:3): our kernel is the free-space reference that establishes under which
  settings PathSolver output is reasonable, and environments are then modelled and simulated with
  PathSolver alone. User wording: 「방향성을 free space에서 우리 커널과 비교했을때 PathSolver로도 충분히
  합리적이라고 볼 수 있는 결과물을 낼 수 있는 방법론들을 정리해뒀으며 그 내용을 토대로 환경 모델링해서
  PathSolver만으로 시뮬레이션을 돌릴 수 있다가 되면」. Compare the engines only on relative quantities;
  never compare their absolute levels or declare either one right.
- A real DJI Matrice 4E (the simulated airframe `matrice4e`) is on hand (user, 2026-09-15).
- Include a Wi-Fi/LTE/5G NR waveform benchmark alongside detection and tracking.
  Distinguish a standards-based waveform from a conformant complete protocol stack,
  and keep communication and sensing resource accounting explicit.
