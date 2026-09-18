# Repository guidance

Read `CLAUDE.md` and `docs/HANDOVER_MAP.md` for the repository's existing research,
publication, and queue rules. Explicit user instructions take precedence.

## Language

The «Language Policy» and «Working Principles» sections at the top of `CLAUDE.md` apply (user, 2026-09-16);
they replace the language preference recorded here on 2026-09-15.

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

## User decisions, 2026-09-18 (answers to the strategy review's open questions)

Source: `docs/STRATEGY_REVIEW_0917.md` §6. Recorded verbatim in Korean with an English gloss.

- **Central question: still open.** 「이건 아직 열린 질문으로 생각해줘」 [treat this as still open]. Neither
  the communication-resource / observation-gap question nor twin-guided placement is chosen yet, so
  `docs/MOBICOM_PIPELINE_PLAN_0916.md` §9 and `docs/RESUME_0917.md` keep their present wording. Write both
  options in any plan text; do not present one as decided.
- **Band and licence: assume the permit is in place.** 「일단 허가 받은 상태라고 인식」 [take it as licensed for
  now]. Plan on transmitting outdoors; the carrier itself is still unspecified, so keep 3.5 GHz as the working
  value and state it as an assumption in any result.
- **Equipment: specs come later, keep asking.** 「스펙은 추후에 알아볼께 계속 요청해줘」 [I will look the specs up
  later, keep asking]. Still unspecified: COTS 5G module, SIMs and reader, OAI host and NIC, outdoor enclosure,
  and the six directional antennas' model, band and gain. Ask again whenever a decision depends on them, and
  never fill them in with assumed numbers.
- **Wi-Fi / LTE / NR comparison: full protocol stacks are in scope.** 「실제 프로토콜 스택까지 한다고 생각해줘」
  [assume we go as far as the real protocol stacks]. So the benchmark is not limited to waveform- or
  trace-level comparison; plan for conformant stacks, and keep the controlled comparison and the native-profile
  comparison separate as before.
- **Real time is not required.** 「지금 실시간성은 딱히 필요하지 않을 것 같아」 [real-time does not look necessary
  now]. Live communication with offline sensing processing is acceptable: record during the live link and
  process afterwards. Latency claims must then be about the communication link, not about sensing.
