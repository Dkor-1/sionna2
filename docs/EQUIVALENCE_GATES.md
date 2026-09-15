# How sameness is judged — the 3 layers of equivalence gates

> **Why this document exists.** The phrase 「비트 동일」 [bit-identical] appears all over the repository, but **where it applies
> and where it does not was written down nowhere.** So on 2026-08-28 it was actually misread
> — while reviewing a pose-batching optimisation, someone judged «결과가 바뀌면 샤드 4,500 개가 전부 무효» [if the results change, all 4,500 shards are invalid],
> but **the repository has never required solver outputs to be bit-identical.**
>
> ⛔**Do not speak of 「비트 동일」 [bit-identical] as the default expectation.** Pick a layer and say which.

---

## 0. Why one yardstick does not work

**PathSolver is not deterministic.** ⚠State the evidence precisely (corrected 2026-09-03) —
NVlabs/sionna Discussion #1175 is a case of diffraction-wedge sampling in **`RadioMapSolver`**
(`docs/SIONNA_NONDETERMINISM_0902.md` §1 separated it as 「우리가 잡은 것은 #1175 이 아니다」 [what we caught is not #1175]),
and the evidence on the **PathSolver** side is not a vendor admission but ⓐ «해시 충돌로 후보
유실» [candidates lost to hash collisions] as written in the candidate generator's preamble (`sb_candidate_generator.py:43-45·55-57`) and ⓑ our own measurement.
On reruns with the same settings our kernel is bit-identical 6/6, while PathSolver fails to match in all 12 cells of four arms
(`outputs/true_repeat_0903.json`). The old edition was measured too — **across 15 old↔old pairs run with the same code · the same seed (seed=1 hard-coded) · the same machine,
the median relative difference is 8.187e-4** (`outputs/adv_refute_hashlottery_0824.json`).

⇒ Demanding bit-identity of solver outputs means **nothing can ever be fixed.** It becomes shackles, not a convention.

Conversely, **mesh generation and our PO kernel are deterministic.** There, bit-identity is achievable,
cheap, and guarantees the ability to roll back. In practice that mechanism has prevented incidents.

⇒ **Not one yardstick but three layers.**

---

## Layer A · bit-identical — only for what is deterministic

**Applies to**
- Mesh generation (`report_mesh/`) — `sha256(float32 정점 + int32 삼각형)`
- Internal comparisons of our PO/SBR kernel (`bit_identical` in `benchmark/verify_bistatic_field.py`)
- **Pure refactors** — renames · I/O paths · caching · logging. Changes that do not touch numerics

**Verdict** Same fingerprint passes, different fails. No statistics needed.

**⭐What it protects — its meaning has already changed once.**
The table that `report_mesh/src/make_mesh02.py:791` wrote down itself:

| | Preparation stage | After landing (now) |
|---|---|---|
| What the bit-identity test protects | «not changed yet» | **«the old edition can be brought back exactly»** |

So what layer A protects now is **not** «do not change it» **but the ability to roll back**.
That is why the rollback switch (`MESH_FIX=none BLADE_LAW=legacy`) and the **filename tag** come as a pair.

⛔**The tag is half of layer A.** If the edition has split but the name is the same, the worker skips it as 「있음」 [exists]
and the old result poses as the new edition. The 2026-08-16 mesh incident (10 lines passed with rc=0 and ≈20 worker-hours
evaporated) and the 2026-08-27 PRF near-miss were **both at this spot**.

---

## Layer B · within natural spread — changes that alter the order of computation

**Applies to**
- **Everything that uses PathSolver**
- Optimisations such as pose batching · scene reuse · parallelisation, where **the floating-point summation order can change**
- Library version upgrades

**Verdict — the order matters**
1. **First measure the «old↔old» spread.** Run the same cell **several times** (≥6) on the pre-change path and
   produce the distribution of relative differences between runs. This is that cell's **natural spread**.
2. Run the new path a few times (≥3).
3. **If the «old↔new» relative difference is within the «old↔old» distribution, pass.** If outside, fail.
4. When judging, **also look at the path count (`npaths`)** — if the path sets diverge, what changed is the geometry,
   not the summation order.

⭐**A precedent already exists: `benchmark/adv_refute_hashlottery_0824.py`.**
It refuted 「`--inmem` 이 회절 팔을 깨뜨렸다」 [--inmem broke the diffraction arm] in exactly this way — old↔old alone diverged by the same size
(8.187e-4), and `npaths` was 41 in all 9 runs. **Use this script as the model
for a layer-B gate.**

⛔**«Ran it once, looked similar, done» is not layer B.** Without measuring the spread first you
cannot say «within the band».

---

## Layer C · designed comparison — changes that alter the algorithm

**Applies to** changes where the computation method itself differs. E.g. batch processing that solves grouped poses at once,
replacing the solver, introducing an approximation.

**Verdict** The comparison does not hold automatically. **Declare in advance what must be the same**, then test.
- Which physical quantity must be preserved (level? spectrum? path count? phase?)
- In which cells to test (elevation · arm · range)
- Set the pass line **in advance** — if you set it after seeing the result, it is not a gate
- ⚠If the difference exceeds the layer-B spread, it is not «an optimisation» but «a different method». Then do not overwrite the old results;
  **stack the new ones separately under a new arm name** (layer A's tag convention).

---

## How to pick the layer

```
Does the change leave numerics untouched?       → A
  ↓ no
Does it go through PathSolver / change summation order? → B
  ↓ no (the algorithm itself is different)
                                      → C
```

**When in doubt, go one layer up.** If you expected to pass under A and did not, that in itself is information —
it means 「손 안 댈 줄 알았는데 댔다」 [you thought you were not touching it, but you did].

---

## ⛔When citing

- Use 「비트 동일하다」 [is bit-identical] **only for layer-A items**. Used on solver results, it is wrong.
- For solver results write **「자연 산포 안에서 같다」 [same within natural spread]** · **「기계 정밀도 안에서 같다」 [same within machine precision]**.
  (The withdrawal of the expressions 「적대 검증 7/7」 [adversarial verification 7/7] · 「자가검사 12/12」 [self-check 12/12] on 2026-08-18 was for the same reason.)
- ⚠**Do not assume 「같은 씨앗이면 같은 답」 [same seed, same answer].** `seed=1` is hard-coded, but
  that does not guarantee determinism (#1175).
