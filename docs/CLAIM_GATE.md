# Claim Gate — Two Axes: Factual Support · Over-Conclusion

> **Why this document exists.** On 2026-09-01 an incident happened on slide 13 of the team meeting deck.
> We concluded 「회절이 무늬에 천장을 씌운다」 [Diffraction puts a ceiling on the pattern] and even made a figure, but on checking,
> that «ceiling» was **each arm's noise-free comb contrast**. An artifact created by cutting the sweep off at +24 dB
> was read as a physical discovery. Extending to +60 dB, **all** five arms
> saturate at their own noise-free values.
>
> User instruction (2026-09-01): 「자꾸 뭘 결론짓는 버릇이 있는거같은데 / 현상 자체를
> 어떤 에너지 plot이나 STFT Plot같은것을 토대로 관찰 위주로하고 / 결론 지으려고
> 하는 행위를 좀 줄여줘」 [You seem to keep having a habit of concluding things / focus on observing the phenomenon itself, based on something like an energy plot or STFT plot / and cut down on trying to draw conclusions] · 「ⓐ사실 뒷받침 ⓑ과잉 결론 두 축으로 공격 →
> 독립 재검증 → 관찰 위주로 보기를 앞으로 작업하면서 항시 해줘. 규약으로 정해두고」 [Attack along two axes, ⓐ factual support and ⓑ over-conclusion → independent re-verification → observation-first viewing; always do this from now on as you work. Set it down as a rule]
>
> ⛔**This document is that rule.** Before putting a number or claim on a slide, in a report, or in an update to the user, pass it through this gate.

---

## 0. Two axes

| Axis | What it asks | If it fails |
|---|---|---|
| **ⓐ Factual support** | Is this number a property of **physics**, or a property of the **measurement setup**? | Remove the number |
| **ⓑ Over-conclusion** | Is this something I **saw**, or something I **judged**? | Remove it from the figure and move it down to the presenter notes |

The two axes are independent. Something can pass ⓐ and still be caught at ⓑ — if the number is right but you say 「because of A, B」,
that is a ⓑ violation. Conversely, something can be clean on ⓑ and still be caught at ⓐ.

---

## 1. ⓐ Factual support — 「Did I read the measurement setup as physics?」

### 1-1. Smell list

We marked with ⭐ the ones we actually stepped on.

| Smell | Form |
|---|---|
| ⭐**Saturation** | The reported value turns out to be the **noise-free, steady-state value**. Not an effect but the value the curve converges to |
| ⭐**Truncated sweep** | The trend depends only on **where the sweep was cut off**. Extend it and it disappears |
| ⭐**Search floor** | The value is **pinned** to the grid resolution or the search lower bound. The 「law」 is an identity |
| ⭐**Degenerate denominator** | The ratio is large not because the numerator is large but because **the denominator is close to 0** |
| **Window/cell width** | What sets the value is not the signal but the FFT length, window, or cell half-width |
| **Below scatter** | The difference is **smaller than the run-to-run reproduction scatter** |
| **No ledger** | The quoted number has no ledger, or the ledger was built with a **different mesh, range, or convention** |
| **Stale** | The ledger is right, but the kernel or mesh changed afterward and only the description remains |

### 1-2. Shaking the knobs — mandatory gate for headline numbers

Before raising a number to a headline, **shake the free parameters.** If shaking changes the conclusion,
it is not physics but the measurement setup.

Things to shake: **both ends of the sweep** · window length and type · cell half-width · threshold · grid spacing · seed · number of poses

⭐**Extending the ends is the cheapest check and catches the most.** The slide 13 incident could have been prevented
by a single 30-second check extending the sweep from +24 → +60 dB.

### 1-3. Extreme-case checks

- **Compute the noise-free value first.** The value a noisy curve converges to is almost always this
- **Try feeding noise only.** Does the metric go to 0 or to a null value?
- **Deliberately break one arm.** Does the metric respond?

---

## 2. ⓑ Over-conclusion — 「Did I see it, or did I judge it?」

### 2-1. Separating observation / judgment

| | Observation | Judgment |
|---|---|---|
| Sentence | 「−30° 에서는 빗살이 보이고 0° 에서는 안 보인다」 [At −30° the comb is visible and at 0° it is not] | 「회절이 빗살을 묻는다」 [Diffraction buries the comb] |
| | 「③④ 는 10~11 dB, ①②⑤ 는 38~53 dB」 [③④ are 10~11 dB, ①②⑤ are 38~53 dB] | 「회절이 천장을 씌운다」 [Diffraction imposes a ceiling] |
| Basis | **Visible as is** in the figure | Brings in a **mechanism not visible** in the figure |

⛔**Do not write mechanism or causation on the slide face.** 「X buries/covers/causes Y」,
「this is not A but B」 are all judgments. **Move them down to the presenter notes** — saying them out loud is fine.
Once stamped on a slide, they remain there without their basis.

### 2-2. The figure comes first

A figure shows the **phenomenon** — STFT, energy distribution, modulation spectrum. This is the way the user originally worked.
Derived judgment figures (bars, badges, judgment lines) **do not replace** observation figures.

⛔Do not put judgment badges or square boxes inside the figure (2026-09-01 instruction). The figure speaks through curves,
and the presenter speaks the judgment.

### 2-3. Write down separately what can and cannot be said

For every number, state the **verified scope**. Our standard wording:

> 검증: 팔 사이 **순서**. 미검증: **절대 미터** — 실측 대조 0 건. [Verified: **order** between arms. Unverified: **absolute meters** — 0 comparisons against real measurement.]

If an axis is not a physical quantity, write that in the axis name — e.g. `per-sample SNR (a sweep, not a range)`.

---

## 3. 3 tiers — when, and how far

The costs differ, so the checks are split into tiers. **Tier 1 always**, tiers 2 and 3 depending on weight.

| Tier | When | What | Cost |
|---|---|---|---|
| **1. Self-questioning** | **Every claim. No exceptions** | Ask yourself the two questions ⓐⓑ. Scan the smell list | 0 |
| **2. Shaking the knobs** | When a number becomes a **headline** — slide face, report result, reporting to the user | Shake the free parameters per §1-2 and run the §1-3 extreme-case checks | minutes |
| **3. Adversarial verification** | **Anything that gets presented or stamped into a report** | Multi-agent: attack along both axes ⓐⓑ → **re-verify by independent recomputation** → rewrite observation-first | hours |

⭐**The core of tier 3 is «independent re-verification».** Do not trust findings raised by the attack as is —
reflect only what another agent has confirmed by **re-running the numbers directly**. False alarms are also a cost.
So the attack prompt must explicitly state **「문제 없음도 정상 답」** ["no problem" is also a normal answer].

---

## 4. Reporting rules

When giving verification results to the user:

- Report **what was confirmed and what were false alarms separately**. If it was a false alarm, say plainly that it was a false alarm
- If there are few problems, say **clearly that there are few** — do not inflate to reassure, nor inflate to alarm
- If something I made was wrong, say **that it was wrong first**. Do not defend it

---

## 5. Incidents this rule should have caught

| Incident | Axis | Smell | If we had shaken |
|---|---|---|---|
| Slide 13 «diffraction ceiling» (0901) | ⓐ+ⓑ | Saturation · truncated sweep | Immediately, had we extended the sweep to +60 |
| PRF ladder «θ_half ∝ 1/k» | ⓐ | Search floor | Had we seen that the widths were all pinned at 2 poses |
| Reading dB(peak÷floor) as beat strength | ⓐ | Degenerate denominator | Had we tried feeding an impulse train with missing poses |
| Describing el 0 as «gradual» | ⓐ | — | Had we seen that the record is a complex constant |
| 「우리 커널이 맞고 PathSolver 가 틀렸다」 [Our kernel is right and PathSolver is wrong] | ⓑ | — | Had we acknowledged that both are approximations |
| 「수신기 2대면 위치가 풀린다」 [Two receivers resolve position] (0916) | ⓑ | Local rank read as global uniqueness; a pinv bound read as an achieved error | Had we mirrored the state in the TX–RX–RX2 plane and recomputed (R_b, f_d), and had we swept the pinv rcond |

---

## Related documents

- [`EQUIVALENCE_GATES.md`](EQUIVALENCE_GATES.md) — what we use to judge 「sameness」
- [`REPORTS_ADVERSARIAL_0810.md`](REPORTS_ADVERSARIAL_0810.md) — precedent of adversarial verification across all report volumes
- [`DECK_FACTS.md`](DECK_FACTS.md) — ledger cross-check table for the numbers the deck quotes
