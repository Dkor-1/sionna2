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
- Do not translate or rename existing artifacts wholesale; apply this preference
  to new work and edits where relevant.

## Current ISAC experiment constraints

- Use one USRP X410 as the main hardware platform.
- Minimize reliance on older USRPs; treat them as optional validation equipment.
- Six directional antennas are available; models, bands, and calibrated patterns
  are still unspecified. Do not infer their coverage from the radio's coverage.
- Include a Wi-Fi/LTE/5G NR waveform benchmark alongside detection and tracking.
  Distinguish a standards-based waveform from a conformant complete protocol stack,
  and keep communication and sensing resource accounting explicit.
