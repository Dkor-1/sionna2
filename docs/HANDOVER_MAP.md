# Where the conventions live — a one-page map

This records only **what a newcomer should read, and where**. The conventions themselves are not copied here
(copying makes two versions that soon diverge). This document is a **table of contents**.

Created 2026-09-10. ⛔When editing this document, also check that the links are still alive.

---

## 0. The first 30 minutes

| Order | What to read | What is in it |
|---|---|---|
| 1 | [`CLAUDE.md`](../CLAUDE.md) | **All standing conventions.** Claim gate · figures · reports · team-meeting boundary · the rest |
| 2 | [`docs/CLAIM_GATE.md`](CLAIM_GATE.md) | The two axes a number must pass before it goes up (factual support · over-conclusion) |
| 3 | [`docs/QUEUE_RUNBOOK.md`](QUEUE_RUNBOOK.md) | How to run the queue. **The 2-tier structure (keeper + supervisor)** is in section 1 |
| 4 | `docs/RESUME_0916.md` | Where the work stands today. **This is the handover** — GPU rules, running queues, what is established and what is not, what waits on the user. Earlier daily editions are in `work/sweep_0904/RESUME_<date>.md` |

---

## 1. Conventions — which document covers what

| Document | Covers | ⛔What causes an incident if missed |
|---|---|---|
| [`CLAUDE.md`](../CLAUDE.md) | The **main body** of the standing conventions | Do not invent words · do not hard-code paths that will disappear into source · CPU-only jobs hide the GPUs |
| [`docs/CLAIM_GATE.md`](CLAIM_GATE.md) | Claim gate | Headline numbers are released only after shaking the knobs |
| [`docs/NEW_FILE_RULES.md`](NEW_FILE_RULES.md) | What new files and ledgers must obey | The gate `benchmark/check_new_file_rules.py` enforces this |
| [`docs/GATES_0902.md`](GATES_0902.md) | Places where citation has been blocked | The el 0° empty-sky records are blocked from citation |
| [`docs/EQUIVALENCE_GATES.md`](EQUIVALENCE_GATES.md) | Conditions under which you may say 「같다」 [the same] | |
| [`../team_meeting/DECK_CONVENTION.md`](../../team_meeting/DECK_CONVENTION.md) | Deck wording | ⛔No insider words (priority 0) · a title is a name, not an explanation |
| [`../team_meeting/CLAUDE.md`](../../team_meeting/CLAUDE.md) | Deck work in general | Decks: a **new version every time**. Do not overwrite an old edition |
| [`docs/RETRACTION_LOG.md`](RETRACTION_LOG.md) | List of retracted claims | Check whether a claim is here before citing it |

⭐**The headers of readers and builders are conventions too.** The first 30 lines of each script state 「이것이 답하지 않는 것」 [what this does not answer],
and that is the rule for reading that ledger. Do not cite by looking at the ledger alone.

---

## 2. Queue — up to the point where one job runs

```
① runners/make_jobs_XXXX.py   writes 물음·죽는조건·안답함 [question · kill condition · does not answer] and emits job lines
② runners/jobs_XXXX.txt        python make_jobs_XXXX.py > jobs_XXXX.txt
③ runners/filter_jobs.sh       ⭐mandatory before queueing — splits into NEW · DONE · STALE
④ runners/queue_chain_XXXX.txt ⛔create the file first, then list it here
⑤ runners/queue_keeper_0827.sh when there are 0 supervisors, launches the next line of the chain
⑥ runners/worker_supervisor.py runs one queue. Enforces GPU allocation and caps
⑦ benchmark/elevation_sweep_md.py  the actual computation → outputs/elev_sweep_shards/*.npz
```

- For details, see [`docs/QUEUE_RUNBOOK.md`](QUEUE_RUNBOOK.md) sections 1~9.
- ⛔Do not use `pgrep -f` — if that name appears in the same command line, **your own shell dies** (exit 144).
  Use `sup()`·`wrk()` from runbook section 4.
- The supervisor **reads the queue when it starts** — if you edit the job file while it is running, it does not read the change.
- When the chain runs dry, the keeper **exits on its own**. Create the next job file before it runs dry.

---

## 3. Data — what accumulates where

| Location | What | How to read |
|---|---|---|
| `outputs/elev_sweep_shards/*.npz` | Elevation sweep **shards** (complex field per pose) | Several files are filled interleaved by `idx` — **you must sort by idx** to get a time series |
| `outputs/elevation_sweep_md.{json,npz}` | The **ledger** merged from those shards | `fc_hz`·`f_tip_hz` differ per row. Do not compute everything in bulk with default values |
| `outputs/*.json` | Ledgers produced by readers and builders | `_meta.generator` records **how to regenerate it** |
| `outputs/figures/` · `atlas/` | Figures · atlas | ⛔Do not edit by hand — fix the builder and regenerate |
| `reports/*.ipynb` | Reports | ⛔Reports are **Jupyter notebooks**. Do not publish them as web pages |

⭐Keys of one shard: `idx` · `E` · `meta`(elevation · shard · number of shards · pose count · PRF · seconds) · `cfg`;
Sionna arms additionally carry `npaths`·`nret`·`E_dedup`·`n_dup`·`n_trunc`.
⚠`n_trunc` is a two-entry array [number of poses near the cap, the cap used at the time] and is counted with **the threshold in effect when it was generated** —
the threshold was once lowered from 0.999 → 0.99, so generations are mixed. Do not cite it as is;
recount it from the stored `nret` and the stored cap (see `benchmark/read_canyonnull_0910.py`).

---

## 4. ⛔Limits still in force — always check before citing

- **Comparisons against real-hardware measurements: 0.** Never write any result so that it reads as 「검증됐다」 [verified].
- Do not conclude 「우리 커널이 맞고 Sionna 가 틀렸다」 [our kernel is right and Sionna is wrong] — both are approximations.
- Varying the ray budget by ±5 % is **not a null.** The initial rays are a deterministic grid with no seed, so repetition measures reproducibility,
  and a budget change is 「격자를 갈았을 때의 민감도」 [the sensitivity when the grid is changed]. It is neither a confidence interval nor a decision threshold.
- If the cap determines the result, shelve that axis (if the path count follows the cap, it cannot be measured).
- No citing σ(dBsm) · no comparing absolute levels between the two engines.

---

## 5. What to do every day

1. Check the queue status — runbook section 4 `sup()`·`wrk()` and the tail of the supervisor log.
2. Commit newly landed shards **only after opening and checking them with `np.load`** (exclude anything written within the last 2 minutes).
3. Check how much of the chain remains. Create the next job file before it runs dry.
4. Write the day's work into `docs/RESUME_<날짜>.md` [date] and repoint `/workspace/RESUME_NOW.md` at it — **the next person starts reading from there**.
5. Team-meeting outputs get commit + push on the spot (`/workspace/team_meeting`).
