# What is where

> Tidied 2026-09-02. The top level was littered with 59 wheels (2.8 GB) and 8 old-generation notebooks, so
> **the reports themselves could not be seen.** The one place a reader should look is `reports/`.

## Where to read

| | |
|---|---|
| **[`reports/`](reports/)** | ⭐**Start here.** The canonical source for the volume structure and how things are counted is [`docs/REPORTS_VOLUMES.md`](docs/REPORTS_VOLUMES.md), and the counts are taken by `_meta` in `outputs/volumes_index.json` (`n_volumes` · `n_companions` · `n_notebooks` — in the 2026-09-05 build: 13 main volumes · 7 companion volumes · 33 notebooks). [`01_map.ipynb`](reports/01_map.ipynb) is the map. ⛔The 「본편 11 권 · 별편 8 편」 [11 main volumes · 8 companion volumes] that used to be written here disagreed with that ledger and was removed |
| [`docs/`](docs/) | Conventions and audit records. [`CLAIM_GATE.md`](docs/CLAIM_GATE.md) · [`AUDIT_REPORTS_0901.md`](docs/AUDIT_REPORTS_0901.md) · [`RESUME.md`](docs/RESUME.md) |
| [`README.md`](README.md) | Report table of contents (generated — produced by `src/build_volumes.py`) |
| [`CLAUDE.md`](CLAUDE.md) | Standing conventions for working in this repository |

## Where things are made

| | |
|---|---|
| `src/` | Kernel and builders. `build_part*.py` → parts, `build_volumes.py` → volumes |
| `benchmark/` | Experiment scripts. They produce the ledgers (`outputs/*.json`) |
| `runners/` | Queue and supervisor. `queue_keeper_*.sh` · `worker_supervisor.py` |
| `outputs/` | Ledgers (JSON) · figures · shards. **Every number in the reports comes from here** |
| `assets/` · `report_mesh/` | Meshes and scenes |

## Where things are stored

| | |
|---|---|
| `vendor/wheels/` | 59 wheels for installation. ⛔Not kept in git |
| `archive/legacy_reports/` | 8 notebooks from **before** the 2026-08-16 reorganisation. Do not read them — `reports/` is the current set |
| `work/` | Temporary work (`scratchpad`, `scratchpad_verify`) |
| `prior_work/` · `refs/` · `jihyuck/` | Prior work and reference material |
| `atlas/` | Micro-Doppler atlas (analysis output) |

⛔**Presentation material is not here** — it is managed only in `/workspace/team_meeting/` (`CLAUDE.md`).

⛔**Never edit notebooks by hand.** Every `reports/*.ipynb` is generated —
fix `src/build_part*.py` and re-run `src/build_volumes.py`.
