# Readout 0918 — queues 0957-0963 (generated)

`benchmark/readout_0918.py` · 2026-09-18T06:03:08Z · git `7c34aab2a679` · sionna-rt 2.1.0 · runtime 85.4 s

> Simulation bookkeeping from stored PathSolver shards and their path-list sidecars. No RF measurement, no comparison with hardware, and nothing here says why the solver lists or omits a path. Every verdict below is the queue header's own pre-set working rule applied to the numbers in the same row; a threshold that is not reached is written «threshold not crossed», never «no effect».

**Scope of every number.** PathSolver, drone matrice4e, ranges 100/15/30/30.41/60 m, rays 1,000,000,000/2,000,000,000/250,000,000/4,000,000,000/90,000,000, switches R0D0E0F1 (diffuse on, refraction/diffraction off), record lengths 1,024/4,096/8,192 positions, max_depth 2 unless the row says d3, cap 2,000,000, 3.5 GHz working assumption, tr38901 as a stand-in (not the six real antennas), flat mirror ground (scattering coefficient 0), hover at constant rpm, one run per cell except the named seed pairs; bandwidths 20 / 100 / 200 MHz, Hann range-bin window with the rectangular window as the knob.

## 1. Queue manifest

| queue | file | lines (queued / held) | named stems | cells | shards present / expected | complete cells | sidecars present / expected | running now |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 957 | `jobs_0957_path_lists_nadir_check_30m_partners.txt` | 10 / 0 | 10 | 5 | 10 / 10 | 5 | 10 / 10 | 0 |
| 958 | `jobs_0958_full_scene_30m_two_positions_HOLD.txt` | 0 / 8 | 8 | 4 | 0 / 8 | 0 | 0 / 0 | 0 |
| 959 | `jobs_0959_open_sky_partners_0950_offdiag.txt` | 4 / 4 | 8 | 4 | 4 / 8 | 2 | 0 / 0 | 0 |
| 960 | `jobs_0960_thin_drone_slab_bridge.txt` | 10 / 0 | 10 | 5 | 10 / 10 | 5 | 10 / 10 | 0 |
| 961 | `jobs_0961_open_sky_range_and_symbol_rate_standins.txt` | 18 / 0 | 18 | 9 | 18 / 18 | 9 | 2 / 2 | 0 |
| 962 | `jobs_0962_drone_ground_ghost_low_grazing_tripod.txt` | 40 / 0 | 40 | 20 | 40 / 40 | 20 | 40 / 40 | 0 |
| 963 | `jobs_0963_aspect_fade_library_open_sky_n1024.txt` | 73 / 90 | 163 | 163 | 23 / 163 | 23 | 0 / 0 | 10 |

### 957 — `jobs_0957_path_lists_nadir_check_30m_partners.txt`

| job lines | hold | cell | shards | complete | sidecars | positions | median paths | reason |
|---|---|---|---:|---|---:|---:|---:|---|
| 1-2 | – | `sionna_p4000000000_swR0D0E0F1_r15_n4096_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 2/2 | yes | 2/2 | 4,096 | 1,319 |  |
| 3-4 | – | `sionna_p4000000000_swR0D0E0F1_r30_n4096_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 2/2 | yes | 2/2 | 4,096 | 321 |  |
| 5-6 | – | `sionna_p2000000000_swR0D0E0F1_r30_n4096_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 2/2 | yes | 2/2 | 4,096 | 158 |  |
| 7-8 | – | `sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_ground_alt9.26_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 2/2 | yes | 2/2 | 4,096 | 620 |  |
| 9-10 | – | `sionna_p4000000000_swR0D0E0F1_r15_n4096_envoutdoor01_ground_alt5.4_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 2/2 | yes | 2/2 | 4,096 | 2,463 |  |

### 958 — `jobs_0958_full_scene_30m_two_positions_HOLD.txt`

| job lines | hold | cell | shards | complete | sidecars | positions | median paths | reason |
|---|---|---|---:|---|---:|---:|---:|---|
| 1-2 | HOLD | `sionna_p4000000000_swR0D0E0F1_r30_n4096_az90_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/2 | no | 0/0 | – | – | no shard on disk |
| 3-4 | HOLD | `sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_alt9.26_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/2 | no | 0/0 | – | – | no shard on disk |
| 5-6 | HOLD | `sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_alt9.26_az90_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/2 | no | 0/0 | – | – | no shard on disk |
| 7-8 | HOLD | `sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_ground_alt9.26_az90_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/2 | no | 0/0 | – | – | no shard on disk |

### 959 — `jobs_0959_open_sky_partners_0950_offdiag.txt`

| job lines | hold | cell | shards | complete | sidecars | positions | median paths | reason |
|---|---|---|---:|---|---:|---:|---:|---|
| 1-2 | HOLD | `sionna_p4000000000_swR0D0E0F1_r15_n8192_ss2_mfixbatteryi5_blperairframe_rt210_d2_el+0` | 0/2 | no | no --dump-paths | – | – | no shard on disk |
| 3-4 | HOLD | `sionna_p4000000000_swR0D0E0F1_r15_n8192_mp32000000_ss2_mfixbatteryi5_blperairframe_rt210_d2_el+0` | 0/2 | no | no --dump-paths | – | – | no shard on disk |
| 5-6 | – | `sionna_p4000000000_swR0D0E0F1_r15_n8192_mfixbatteryi5_blperairframe_orTgt_rt210_d2_el-60` | 2/2 | yes | no --dump-paths | – | – |  |
| 7-8 | – | `sionna_p4000000000_swR0D0E0F1_r15_n8192_mfixbatteryi5_blperairframe_anttr38901_orDev_rt210_d2_el-60` | 2/2 | yes | no --dump-paths | – | – |  |

### 960 — `jobs_0960_thin_drone_slab_bridge.txt`

| job lines | hold | cell | shards | complete | sidecars | positions | median paths | reason |
|---|---|---|---:|---|---:|---:|---:|---|
| 1-2 | – | `sionna_p4000000000_swR0D0E0F1_r15_n4096_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 2/2 | yes | 2/2 | 4,096 | 1,319 |  |
| 3-4 | – | `sionna_p4000000000_swR0D0E0F1_r15_n4096_envoutdoor01_ground_alt5.4_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 2/2 | yes | 2/2 | 4,096 | 2,463 |  |
| 5-6 | – | `sionna_p4000000000_swR0D0E0F1_r30_n4096_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 2/2 | yes | 2/2 | 4,096 | 321 |  |
| 7-8 | – | `sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_ground_alt9.26_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 2/2 | yes | 2/2 | 4,096 | 620 |  |
| 9-10 | – | `sionna_p4000000000_swR0D0E0F1_r15_n4096_ss2_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 2/2 | yes | 2/2 | 4,096 | 1,282 |  |

### 961 — `jobs_0961_open_sky_range_and_symbol_rate_standins.txt`

| job lines | hold | cell | shards | complete | sidecars | positions | median paths | reason |
|---|---|---|---:|---|---:|---:|---:|---|
| 1-2 | – | `sionna_p1000000000_swR0D0E0F1_r15_n4096_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 2/2 | yes | no --dump-paths | – | – |  |
| 3-4 | – | `sionna_p250000000_swR0D0E0F1_r15_n4096_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 2/2 | yes | no --dump-paths | – | – |  |
| 5-6 | – | `sionna_p1000000000_swR0D0E0F1_r30_n4096_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 2/2 | yes | no --dump-paths | – | – |  |
| 7-8 | – | `sionna_p4000000000_swR0D0E0F1_r60_n4096_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 2/2 | yes | no --dump-paths | – | – |  |
| 9-10 | – | `sionna_p4000000000_swR0D0E0F1_r60_n4096_ss2_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 2/2 | yes | no --dump-paths | – | – |  |
| 11-12 | – | `sionna_p90000000_swR0D0E0F1_r15_n4096_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 2/2 | yes | no --dump-paths | – | – |  |
| 13-14 | – | `sionna_p4000000000_swR0D0E0F1_r100_n4096_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 2/2 | yes | no --dump-paths | – | – |  |
| 15-16 | – | `sionna_p4000000000_swR0D0E0F1_r15_n4096_prf28029_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 2/2 | yes | 2/2 | 4,096 | 1,319 |  |
| 17-18 | – | `sionna_p4000000000_swR0D0E0F1_r100_n4096_ss2_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 2/2 | yes | no --dump-paths | – | – |  |

### 962 — `jobs_0962_drone_ground_ghost_low_grazing_tripod.txt`

| job lines | hold | cell | shards | complete | sidecars | positions | median paths | reason |
|---|---|---|---:|---|---:|---:|---:|---|
| 1-2 | – | `sionna_p4000000000_swR0D0E0F1_r30_n4096_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 2/2 | yes | 2/2 | 4,096 | 271 |  |
| 3-4 | – | `sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_ground_alt4.11_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 2/2 | yes | 2/2 | 4,096 | 520 |  |
| 5-6 | – | `sionna_p4000000000_swR0D0E0F1_r30_n4096_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-2.5` | 2/2 | yes | 2/2 | 4,096 | 270 |  |
| 7-8 | – | `sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_ground_alt2.81_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-2.5` | 2/2 | yes | 2/2 | 4,096 | 504 |  |
| 9-10 | – | `sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_ground_alt4.11_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d3_el-5` | 2/2 | yes | 2/2 | 4,096 | 553 |  |
| 11-12 | – | `sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_ground_alt2.81_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d3_el-2.5` | 2/2 | yes | 2/2 | 4,096 | 544 |  |
| 13-14 | – | `sionna_p4000000000_swR0D0E0F1_r30_n4096_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-10` | 2/2 | yes | 2/2 | 4,096 | 299 |  |
| 15-16 | – | `sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_ground_alt6.71_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-10` | 2/2 | yes | 2/2 | 4,096 | 567 |  |
| 17-18 | – | `sionna_p4000000000_swR0D0E0F1_r15_n4096_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 2/2 | yes | 2/2 | 4,096 | 1,104 |  |
| 19-20 | – | `sionna_p4000000000_swR0D0E0F1_r15_n4096_envoutdoor01_ground_alt2.81_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 2/2 | yes | 2/2 | 4,096 | 2,021 |  |
| 21-22 | – | `sionna_p4000000000_swR0D0E0F1_r30.41_n4096_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-10.62` | 2/2 | yes | 2/2 | 4,096 | 294 |  |
| 23-24 | – | `sionna_p4000000000_swR0D0E0F1_r30_n4096_ss2_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 2/2 | yes | 2/2 | 4,096 | 300 |  |
| 25-26 | – | `sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_ground_alt4.11_ss2_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 2/2 | yes | 2/2 | 4,096 | 549 |  |
| 27-28 | – | `sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_ground_alt4.11_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_orTgt_rt210_d2_el-5` | 2/2 | yes | 2/2 | 4,096 | 520 |  |
| 29-30 | – | `sionna_p4000000000_swR0D0E0F1_r30_n4096_az90_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 2/2 | yes | 2/2 | 4,096 | 339 |  |
| 31-32 | – | `sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_ground_alt4.11_az90_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 2/2 | yes | 2/2 | 4,096 | 673 |  |
| 33-34 | – | `sionna_p4000000000_swR0D0E0F1_r30_n4096_az180_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 2/2 | yes | 2/2 | 4,096 | 266 |  |
| 35-36 | – | `sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_ground_alt4.11_az180_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 2/2 | yes | 2/2 | 4,096 | 494 |  |
| 37-38 | – | `sionna_p4000000000_swR0D0E0F1_r60_n4096_az45_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 2/2 | yes | 2/2 | 4,096 | 90 |  |
| 39-40 | – | `sionna_p4000000000_swR0D0E0F1_r60_n4096_envoutdoor01_ground_alt6.73_az45_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 2/2 | yes | 2/2 | 4,096 | 164 |  |

### 963 — `jobs_0963_aspect_fade_library_open_sky_n1024.txt`

| job lines | hold | cell | shards | complete | sidecars | positions | median paths | reason |
|---|---|---|---:|---|---:|---:|---:|---|
| 1 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 1/1 | yes | no --dump-paths | – | – |  |
| 2 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az18_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 1/1 | yes | no --dump-paths | – | – |  |
| 3 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az36_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 1/1 | yes | no --dump-paths | – | – |  |
| 4 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az54_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 1/1 | yes | no --dump-paths | – | – |  |
| 5 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az72_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 1/1 | yes | no --dump-paths | – | – |  |
| 6 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az90_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 1/1 | yes | no --dump-paths | – | – |  |
| 7 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az108_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 1/1 | yes | no --dump-paths | – | – |  |
| 8 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az126_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 1/1 | yes | no --dump-paths | – | – |  |
| 9 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az144_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 1/1 | yes | no --dump-paths | – | – |  |
| 10 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az162_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 1/1 | yes | no --dump-paths | – | – |  |
| 11 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_ss2_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 1/1 | yes | no --dump-paths | – | – |  |
| 12 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_ss2_az54_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 1/1 | yes | no --dump-paths | – | – |  |
| 13 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_ss2_az90_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 1/1 | yes | no --dump-paths | – | – |  |
| 14 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az342_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 1/1 | yes | no --dump-paths | – | – |  |
| 15 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az324_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 1/1 | yes | no --dump-paths | – | – |  |
| 16 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az306_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 1/1 | yes | no --dump-paths | – | – |  |
| 17 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az288_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 1/1 | yes | no --dump-paths | – | – |  |
| 18 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az270_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 1/1 | yes | no --dump-paths | – | – |  |
| 19 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-4` | 1/1 | yes | no --dump-paths | – | – |  |
| 20 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-10` | 1/1 | yes | no --dump-paths | – | – |  |
| 21 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-16` | 1/1 | yes | no --dump-paths | – | – |  |
| 22 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-22` | 1/1 | yes | no --dump-paths | – | – |  |
| 23 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-28` | 1/1 | yes | no --dump-paths | – | – |  |
| 24 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-34` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 25 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-40` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 26 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 27 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az18_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 28 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az36_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 29 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az54_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 30 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az72_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 31 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az6_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 32 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az12_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 33 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az24_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 34 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az30_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 35 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az42_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 36 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az48_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 37 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az60_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 38 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az66_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 39 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az78_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 40 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az84_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 41 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az96_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 42 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az102_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 43 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az114_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 44 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az120_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 45 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az132_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 46 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az138_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 47 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az150_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 48 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az156_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 49 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az168_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 50 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az174_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 51 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-2` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 52 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-6` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 53 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-8` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 54 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-12` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 55 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-14` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 56 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-18` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 57 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-20` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 58 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-24` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 59 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-26` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 60 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-30` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 61 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-32` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 62 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-36` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 63 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-38` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 64 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az6_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 65 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az12_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 66 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az24_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 67 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az30_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 68 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az42_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 69 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az48_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 70 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az60_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 71 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az66_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 72 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az78_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 73 | – | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az84_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 74 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az2_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 75 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az4_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 76 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az8_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 77 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az10_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 78 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az14_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 79 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az16_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 80 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az20_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 81 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az22_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 82 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az26_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 83 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az28_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 84 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az32_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 85 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az34_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 86 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az38_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 87 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az40_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 88 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az44_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 89 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az46_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 90 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az50_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 91 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az52_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 92 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az56_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 93 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az58_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 94 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az62_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 95 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az64_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 96 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az68_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 97 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az70_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 98 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az74_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 99 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az76_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 100 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az80_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 101 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az82_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 102 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az86_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 103 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az88_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 104 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az92_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 105 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az94_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 106 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az98_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 107 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az100_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 108 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az104_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 109 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az106_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 110 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az110_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 111 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az112_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 112 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az116_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 113 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az118_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 114 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az122_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 115 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az124_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 116 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az128_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 117 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az130_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 118 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az134_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 119 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az136_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 120 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az140_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 121 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az142_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 122 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az146_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 123 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az148_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 124 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az152_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 125 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az154_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 126 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az158_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 127 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az160_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 128 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az164_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 129 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az166_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 130 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az170_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 131 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az172_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 132 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az176_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 133 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az178_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-5` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 134 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az2_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 135 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az4_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 136 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az8_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 137 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az10_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 138 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az14_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 139 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az16_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 140 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az20_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 141 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az22_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 142 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az26_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 143 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az28_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 144 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az32_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 145 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az34_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 146 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az38_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 147 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az40_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 148 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az44_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 149 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az46_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 150 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az50_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 151 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az52_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 152 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az56_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 153 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az58_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 154 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az62_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 155 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az64_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 156 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az68_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 157 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az70_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 158 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az74_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 159 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az76_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 160 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az80_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 161 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az82_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 162 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az86_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |
| 163 | HOLD-rev1 | `sionna_p4000000000_swR0D0E0F1_r15_n1024_az88_shell0.75mm_prop1.43mm_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` | 0/1 | no | no --dump-paths | – | – | no shard on disk |

## 2. What each header's gate says now

### 0957

- **check 0** `sionna_p4000000000_swR0D0E0F1_r15_n4096_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15`: max |Σ_hit a·exp(−j2πf_cτ) − E|/|E| = 4.04e-15 over 4,096 positions (threshold 1e−4) → passed; n_dup > 0 at 0 positions.
- **check 0** `sionna_p4000000000_swR0D0E0F1_r30_n4096_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15`: max |Σ_hit a·exp(−j2πf_cτ) − E|/|E| = 1.80e-15 over 4,096 positions (threshold 1e−4) → passed; n_dup > 0 at 0 positions.
- **check 0** `sionna_p2000000000_swR0D0E0F1_r30_n4096_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15`: max |Σ_hit a·exp(−j2πf_cτ) − E|/|E| = 1.05e-15 over 4,096 positions (threshold 1e−4) → passed; n_dup > 0 at 0 positions.
- **check 0** `sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_ground_alt9.26_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15`: max |Σ_hit a·exp(−j2πf_cτ) − E|/|E| = 4.13e-15 over 4,096 positions (threshold 1e−4) → passed; n_dup > 0 at 0 positions.
- **check 0** `sionna_p4000000000_swR0D0E0F1_r15_n4096_envoutdoor01_ground_alt5.4_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15`: max |Σ_hit a·exp(−j2πf_cτ) − E|/|E| = 4.55e-15 over 4,096 positions (threshold 1e−4) → passed; n_dup > 0 at 0 positions.
- **reading 1 (replay)** `sionna_p4000000000_swR0D0E0F1_r15_n4096_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` against positions 0-4095 of `sionna_p4000000000_swR0D0E0F1_r15_n8192_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15`: 19 of 4,096 positions with |ΔE|/median|E| > 1e−5 (max 0.00236); path counts differ at 14 positions (0.3 %), mean |Δn|/n 0.00 %.
- **reading 1 (replay)** `sionna_p4000000000_swR0D0E0F1_r15_n4096_envoutdoor01_ground_alt5.4_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` against positions 0-4095 of `sionna_p4000000000_swR0D0E0F1_r15_n8192_envoutdoor01_ground_alt5.4_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15`: 16 of 4,096 positions with |ΔE|/median|E| > 1e−5 (max 0.00045); path counts differ at 13 positions (0.3 %), mean |Δn|/n 0.00 %.
- **P** `sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_ground_alt9.26_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` (radar 1.495 m): a single environment-only path of length 2h within 1 cm at 100.00 % of the positions outside event positions; measured − predicted in-bin power at most 0.05 dB over Hann/rect × 20/100 MHz → in ground only, the environment term in the drone's range bin is the radar's own ground reflection seen through the range window (threshold not crossed)
- **P** `sionna_p4000000000_swR0D0E0F1_r15_n4096_envoutdoor01_ground_alt5.4_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15` (radar 1.518 m): a single environment-only path of length 2h within 1 cm at 100.00 % of the positions outside event positions; measured − predicted in-bin power at most 0.20 dB over Hann/rect × 20/100 MHz → in ground only, the environment term in the drone's range bin is the radar's own ground reflection seen through the range window (threshold not crossed)
- **B** `sionna_p4000000000_swR0D0E0F1_r30_n4096_envoutdoor01_ground_alt9.26_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15`: event_in_bin 1.99, event_share 28.6 % over 7 event positions (20 MHz Hann) → B failed - both numbers are written
- **B** `sionna_p4000000000_swR0D0E0F1_r15_n4096_envoutdoor01_ground_alt5.4_mfixbatteryi5_blperairframe_anttr38901_rt210_d2_el-15`: event_in_bin 4.47, event_share 100.0 % over 32 event positions (20 MHz Hann) → B failed - both numbers are written
- **A** at 20 MHz: contrast_gated ground 24.24 dB vs open sky 24.41 dB (Δ -0.16 dB) → the all-delay contrast deficit of the aimed tripod cell does not reach the drone's bin at B (threshold not crossed)
- **A** at 100 MHz: contrast_gated ground 24.38 dB vs open sky 24.41 dB (Δ -0.03 dB) → the all-delay contrast deficit of the aimed tripod cell does not reach the drone's bin at B (threshold not crossed)
- **C** 30 m open sky, 2e9 → 4e9 rays: Δcontrast_raw 2.29 dB, Δcontrast_gated(20 MHz) 2.29 dB, Δlvl_db 1.93 dB → steep in rays at 30 m - no 30 m cell is read further and 0958 is not launched

### 0958

- HOLD - no line launched: 8 job lines, 0 shards on disk. Readings G and F are not computable.
- Release triggers (any one): 0957 check 0/2 pass, C is not steep, and the CPU receiver has run on the 0957 open-sky and ground-only path lists; an X410 capture shows a failure a wall return or wall multipath could explain; the user asks for it.
- runners/jobs_0964_full_scene_30m_thin_slab.txt (2026-09-18) states that it replaces this file and that 0958 is superseded, not released: the 8 held lines carry no --shell-mm / --prop-mm and would buy the same four cells at the Sionna default 0.1 m slab.

### 0959

- **(b) ground**: 4 of 4 antenna cells complete. iso_device: env_field_drop_halfmedian 82, Jaccard with iso/device 1.0000, median |scene − sky| -74.36 dB, isolated_20xmedian 90, contrast_raw -0.03 dB; iso_target: env_field_drop_halfmedian 82, Jaccard with iso/device 1.0000, median |scene − sky| -74.35 dB, isolated_20xmedian 90, contrast_raw 0.14 dB; tr_target: env_field_drop_halfmedian 82, Jaccard with iso/device 1.0000, median |scene − sky| -118.20 dB, isolated_20xmedian 0, contrast_raw 29.28 dB; tr_device: env_field_drop_halfmedian 82, Jaccard with iso/device 1.0000, median |scene − sky| -104.37 dB, isolated_20xmedian 90, contrast_raw -0.11 dB → the field-drop set did not follow pattern or orientation at 2e6 (threshold not crossed)
- **(b) canyon**: 4 of 4 antenna cells complete. iso_device: env_field_drop_halfmedian 0, Jaccard with iso/device –, median |scene − sky| -73.00 dB, isolated_20xmedian 339, contrast_raw 0.34 dB; iso_target: env_field_drop_halfmedian 0, Jaccard with iso/device –, median |scene − sky| -72.99 dB, isolated_20xmedian 339, contrast_raw 0.25 dB; tr_target: env_field_drop_halfmedian 0, Jaccard with iso/device –, median |scene − sky| -106.69 dB, isolated_20xmedian 0, contrast_raw 29.56 dB; tr_device: env_field_drop_halfmedian 0, Jaccard with iso/device –, median |scene − sky| -103.01 dB, isolated_20xmedian 338, contrast_raw 0.09 dB (street canyon iso/device has 0 drops (0959 header), so the canyon row is read on level only)
- **(a)** lines 1-4 are «#HOLD »; the seed-pair threshold T of the 0952 cap comparison stays unavailable.

### 0960

- **G0** (15 m open sky, canonical slab vs 0.1 m): thickness_delta(lvl_db) -15.60 dB, thickness_delta(ac_level_db) -9.87 dB, hits_per_pose 1319 vs 1319 (0.0 % apart, within 3 %) → the thickness flags changed the cell (G0 passed); 0961-0963 may read.
- **seed_diff** (0960 lines 9-10 vs 1-2): lvl_db 1.21 dB, ac_level_db 0.97 dB, ac_to_static_db 2.18 dB, contrast_raw 0.16 dB, isolated_20xmedian 0 positions → T_q = max(floor, 3·seed_diff).
- **T1** → the drone slab thickness changes receiver-facing quantities at this geometry (threshold crossed): ac_to_static_db +7.78 dB >= max(3, 6.54); env_in_bin_db +9.84 dB at 20 MHz; env_in_bin_db +9.85 dB at 100 MHz; env_in_bin_db +8.12 dB at 20 MHz; env_in_bin_db +8.12 dB at 100 MHz
- **T2 (ghost, written not gated)** 15 m ground alt 5.4: class_power_db([g,d]) − class_power_db([d]) = -34.32 dB at 20 MHz beside the computed -32.4 dB.
- **T2 (ghost, written not gated)** 30 m ground alt 9.26: class_power_db([g,d]) − class_power_db([d]) = -25.98 dB at 20 MHz beside the computed -26.8 dB.

### 0961

- **R0** hits_per_pose / (spp/R²) over 8 landed cells: median 7.63e-05, outside ±10 %: 100 m @ 4e9 → R0 premise fails - no range reading is written; cells listed.
- **R1** group 1e9 (15 m @ 1e9, 30 m @ 4e9): lvl_at_15m_db 0.82 dB vs T 3.62 dB; ac_to_static_db 1.25 dB vs T 6.54 dB; contrast_raw 0.43 dB vs T 1.00 dB → with matched rays on the drone, range did not cross the threshold (open sky, 15 deg up). ⚠ R0 has not passed, so under the header's own rule no range reading is written: this row is listed as data, not read as a result.
- **R1** group 2.5e8 (15 m @ 2.5e8, 30 m @ 1e9, 60 m @ 4e9): lvl_at_15m_db 2.16 dB vs T 7.10 dB; ac_to_static_db 2.05 dB vs T 6.54 dB; contrast_raw 1.29 dB vs T 1.38 dB → with matched rays on the drone, range did not cross the threshold (open sky, 15 deg up). ⚠ R0 has not passed, so under the header's own rule no range reading is written: this row is listed as data, not read as a result.
- **R1** group 9e7 (15 m @ 9e7, 100 m @ 4e9): lvl_at_15m_db 0.15 dB vs T 7.10 dB; ac_to_static_db 2.98 dB vs T 6.54 dB; contrast_raw 2.65 dB vs T 2.52 dB → range changes the open-sky cell beyond ray density at 15 deg up. ⚠ R0 has not passed, so under the header's own rule no range reading is written: this row is listed as data, not read as a result.
- **R2** 15 m @ 9e7 -> 15 m @ 2.5e8: Δcontrast_raw -1.39 dB, Δac_to_static_db -3.76 dB, 15 m @ 2.5e8 -> 15 m @ 1e9: Δcontrast_raw 0.67 dB, Δac_to_static_db -7.59 dB, 15 m @ 1e9 -> 15 m @ 4e9: Δcontrast_raw 2.25 dB, Δac_to_static_db -1.78 dB → steep in rays between the 30 m and 15 m densities - runners/jobs_0962 reads its 30 m cells only as class mean-level ratios (P1-P3, W).
- **R3** 0957 reading C Δcontrast_raw 2.29 dB (Δcontrast_gated 20 MHz 2.29 dB) beside the 15 m 1e9 → 4e9 step Δcontrast_raw 2.25 dB and the 15 m seed difference of contrast_raw 0.16 dB — written side by side (0961 R3); no verdict of its own.
- **T1 (B)** interp_resid_db (linear) -13.11 dB, band-limited -12.15 dB; rerun_floor_db -59.06 dB, seed_floor_db -1.21 dB → between -20 and -10 dB: both numbers written; the receiver uses symbol-rate records for rotor-part readouts and interpolation for levels.
- **T2 (B)** above_nyq_share 1.623 % → at least 1 % of the rotor-part power lies above the 19.7 kHz Nyquist limit at 15 deg up; |E28(0) − E19.7(0)|/|mean E| = 2.01e-16.

### 0962

- **P1** A: class_power_db([g,d]) − class_power_db([d,g]) = 24.96 dB (median paths per position: [g,d] 247, [d,g] 1) → |class_power_db([g,d]) - class_power_db([d,g])| above 1 dB.
- **P1** B: class_power_db([g,d]) − class_power_db([d,g]) = – dB (median paths per position: [g,d] 235, [d,g] 0) → not defined: no [d,g] path is listed at any position of this cell.
- **P1** C: class_power_db([g,d]) − class_power_db([d,g]) = 32.80 dB (median paths per position: [g,d] 266, [d,g] 1) → |class_power_db([g,d]) - class_power_db([d,g])| above 1 dB.
- **P1** E: class_power_db([g,d]) − class_power_db([d,g]) = – dB (median paths per position: [g,d] 918, [d,g] 0) → not defined: no [d,g] path is listed at any position of this cell.
- **P1** F: class_power_db([g,d]) − class_power_db([d,g]) = 25.08 dB (median paths per position: [g,d] 71, [d,g] 1) → |class_power_db([g,d]) - class_power_db([d,g])| above 1 dB.
- Written beside P1, not a verdict: the two one-bounce orderings are not listed in equal numbers in these depth-2 sidecars (see the medians above). Nothing here says why.
- **P2** A: measured [g,d] − [d] = -17.98 dB, computed -9.61 dB, D2 = -8.37 dB → |D2| above 3 dB - the listed ghost level does not follow the computed two-ray level at psi.
- **P2** B: measured [g,d] − [d] = -11.07 dB, computed -6.98 dB, D2 = -4.09 dB → |D2| above 3 dB - the listed ghost level does not follow the computed two-ray level at psi.
- **P2** C: measured [g,d] − [d] = -16.99 dB, computed -16.28 dB, D2 = -0.71 dB → the ghost follows the computed two-ray level at psi (threshold not crossed).
- **P2** E: measured [g,d] − [d] = -15.53 dB, computed -16.59 dB, D2 = 1.06 dB → the ghost follows the computed two-ray level at psi (threshold not crossed).
- **P2** F: measured [g,d] − [d] = -2.62 dB, computed -6.8 dB, D2 = 4.18 dB → |D2| above 3 dB - the listed ghost level does not follow the computed two-ray level at psi.
- **P2d** A: excess_cm 41.40 cm against the computed 40.7 cm (Δ 0.70 cm) → the ghost delay follows the two-ray excess (threshold not crossed).
- **P2d** B: excess_cm 30.39 cm against the computed 28.0 cm (Δ 2.39 cm) → the ghost delay follows the two-ray excess (threshold not crossed).
- **P2d** C: excess_cm 70.56 cm against the computed 66.4 cm (Δ 4.16 cm) → the ghost delay follows the two-ray excess (threshold not crossed).
- **P2d** E: excess_cm 55.12 cm against the computed 55.3 cm (Δ -0.18 cm) → the ghost delay follows the two-ray excess (threshold not crossed).
- **P2d** F: excess_cm 35.60 cm against the computed 33.6 cm (Δ 2.00 cm) → the ghost delay follows the two-ray excess (threshold not crossed).
- **M2** → P2 crossed - the tracker's fade model takes the listed class ratios, interpolated in psi; nothing outside psi 8.2-16.1 deg is modelled from these cells.
- **M3** D2(C) -0.71 dB, D2(E) 1.06 dB, Δ -1.77 dB → range did not move D2 beyond threshold at psi 15.5-16.1 deg.
- **P3** A: measured -51.05 dB vs computed -18.99 dB (Δ -32.06 dB) → outside +-2 dB of the computed value; depth 3 − depth 2 of [d], [g,d], [d,g] **outside** ±1 dB ([d] -0.03 dB, [g,d] 2.23 dB, [d,g] 3.84 dB); median listed paths per position [d] 276, [g,d] 267, [d,g] 9, [g,d,g] 1, [g] 1.
- **P3** B: measured -51.82 dB vs computed -13.97 dB (Δ -37.85 dB) → outside +-3 dB of the computed value; depth 3 − depth 2 of [d], [g,d], [d,g] within ±1 dB ([d] 0.01 dB, [g,d] 0.36 dB, [d,g] – dB); median listed paths per position [d] 280, [g,d] 253, [d,g] 9, [g,d,g] 1, [g] 1.
- **W** [d] w_err -0.00 dB (tol ±0.5), [g,d] w_err 0.01 dB (tol ±1.0), [d,g] w_err -0.02 dB (tol ±1.0), [g] w_err 0.00 dB (tol ±1.0) → per-class re-weighting reproduces the aimed pattern at this geometry (threshold not crossed).
- **AS** az 90 20 MHz: D2 -0.59 dB, D2 − D2(az 0) 7.77 dB; az 90 100 MHz: D2 -0.67 dB, D2 − D2(az 0) 7.69 dB; az 180 20 MHz: D2 -0.19 dB, D2 − D2(az 0) 8.17 dB; az 180 100 MHz: D2 -0.08 dB, D2 − D2(az 0) 8.28 dB → the fade model carries aspect at this psi.
- **P6** event_in_bin 3.13, event_share 64.29 % → P6 crossed - both numbers and the 100 MHz values written.
- ⚠ precondition (3) of the 0962 header: runners/jobs_0961 R2 is «steep», so the 30 m cells of this file are read only on P1-P3 and W (class mean-level ratios). contrast_raw, contrast_gated and the event readings (P6) at 30 m are written as data below, not read as results.
- **F** (60 m, psi 7.84 deg) is read only if runners/jobs_0961 R1 did not cross in group 2.5e8. R0 has not passed, so no R1 reading is written and F is not read; its cells are listed.

### 0963

- **S1** el -5, az 0-162 in 18 deg (lines 1-10): 10 of 10 cells landed; T_s = 17.54 dB (seed_diff 5.85 dB, replay_diff_db 0.000) → heading crossed the 3 dB fade threshold at el -5 at 18 deg sampling.
- max − min lvl_db 26.34 dB, max − min ac_to_static_db 21.79 dB.
- **S4** az 18: 2.41 dB, az 36: -2.01 dB, az 54: -17.83 dB, az 72: 1.08 dB, az 90: -0.00 dB (T = 17.54 dB) → mirror not assumed - |mirror_diff_db| above max(1 dB, T_s) at one or more of the five pairs.
- **S6** max − min ac_to_static_db 21.79 dB over 10 cells; share with ac_to_static_db ≥ 0 dB 20.00 % → the rotor-to-body ratio follows heading at el -5 (threshold crossed) -> the n4096 extension at the headings of its maximum and minimum.
- **S5** not computable yet: 5 of 7 elevation cells complete.

## 3. Still missing

- 0958: every line is still «#HOLD » - no shard, no sidecar; its readings G and F are not computable, and runners/jobs_0964_full_scene_30m_thin_slab.txt says it is superseded (the held lines are at the 0.1 m slab).
- 0959 (a): lines 1-4 (seed 2 of open sky 0 deg at 2e6 and 32e6) are «#HOLD »; the 0952 T threshold from a seed pair is therefore still unavailable and the 0952 fall is read at one seed only.
- 0963: lines 74-163 are «#HOLD-rev1 » (mesh revision 1); lines 1-73 are the revision-0 baseline.
- env_path_missing is not computable from shards or from these sidecars for the 0957-0963 cells: the existing path-list ledger outputs/dropout_paths_0916_diff.json covers other cells only.
- Nothing here identifies which solver candidate was lost or why, and no absolute level is a radar cross section (a PathSolver level is not sigma).

## 4. Tables

The full numbers, index sets and per-window values are in `outputs/readout_0918.json` (`gates.0957`, `gates.0959`, `gates.0960`, `gates.0961`, `gates.0962`, `gates.0963`).

### 0960 T1 — thin-slab bridge (canonical slab − 0.1 m slab, dB)

| pair | Δ lvl_db | Δ ac_level_db | Δ ac_to_static_db | Δ contrast_raw | Δ env_in_bin_db 20 MHz | Δ contrast_gated 20 MHz | T(ac_to_static) |
|---|---|---|---|---|---|---|---|
| 15 m open sky | -15.60 | -9.87 | 5.74 | -3.39 | – | -3.39 | 6.54 |
| 15 m ground alt 5.4 | -5.14 | -1.54 | 3.60 | -8.24 | 9.84 | -3.98 | 6.54 |
| 30 m open sky | -15.87 | -8.10 | 7.78 | -3.20 | – | -3.20 | 6.54 |
| 30 m ground alt 9.26 | 0.06 | -0.22 | -0.27 | -3.84 | 8.12 | -3.22 | 6.54 |

### 0961 (A) — open-sky range and ray-density cells

| cell | spp | R m | hits_per_pose | hits/(spp/R²) | lvl_db | lvl_at_15m_db | ac_to_static_db | contrast_raw |
|---|---|---|---|---|---|---|---|---|
| 15 m @ 4e9 | 4e+09 | 15.0 | 1,319 | 7.419e-05 | -119.30 | -119.30 | -19.61 | 21.02 |
| 15 m @ 1e9 | 1e+09 | 15.0 | 338 | 7.605e-05 | -123.28 | -123.28 | -17.84 | 18.77 |
| 15 m @ 2.5e8 | 2.5e+08 | 15.0 | 80 | 7.2e-05 | -131.39 | -131.39 | -10.25 | 18.09 |
| 15 m @ 9e7 | 9e+07 | 15.0 | 31 | 7.75e-05 | -132.33 | -132.33 | -6.49 | 19.49 |
| 30 m @ 4e9 | 4e+09 | 30.0 | 321 | 7.223e-05 | -136.14 | -124.10 | -16.58 | 19.20 |
| 30 m @ 1e9 | 1e+09 | 30.0 | 88 | 7.92e-05 | -145.37 | -133.33 | -8.57 | 16.80 |
| 60 m @ 4e9 | 4e+09 | 60.0 | 85 | 7.65e-05 | -157.63 | -133.55 | -8.20 | 17.57 |
| 100 m @ 4e9 | 4e+09 | 100.0 | 37 | 9.25e-05 | -165.43 | -132.48 | -9.48 | 16.83 |

### 0962 — class_power_db at 20 MHz Hann (dB) and D2

| cell | ψ row | [d] | [g,d] | [d,g] | [g] | [g,d,g] | env_in_bin_db | D2 |
|---|---|---|---|---|---|---|---|---|
| p4000000000_r30_n4096_envoutdoor01_ground_alt4.11_d2_el-5 | A | -140.42 | -158.39 | -183.36 | -153.82 | – | -0.81 | -8.37 |
| p4000000000_r30_n4096_envoutdoor01_ground_alt2.81_d2_el-2.5 | B | -137.78 | -148.86 | – | -153.81 | – | 0.28 | -4.09 |
| p4000000000_r30_n4096_envoutdoor01_ground_alt6.71_d2_el-10 | C | -140.62 | -157.61 | -190.41 | -153.82 | – | 0.56 | -0.71 |
| p4000000000_r15_n4096_envoutdoor01_ground_alt2.81_d2_el-5 | E | -125.29 | -140.82 | – | -131.72 | – | 5.70 | 1.06 |
| p4000000000_r60_n4096_envoutdoor01_ground_alt6.73_az45_d2_el-5 | F | -158.89 | -161.51 | -186.58 | -173.13 | – | -8.28 | 4.18 |

### 0957 reading 2 — per cell and bandwidth (Hann; rect in the JSON)

| cell | B | contrast_raw | contrast_gated | env_in_bin_db | event_in_bin | event_share % | field difference due to the environment |
|---|---|---|---|---|---|---|---|
| p4000000000_r15_n4096_d2_el-15 | 20 MHz | 24.41 | 24.41 | – | – | – | – |
| p4000000000_r15_n4096_d2_el-15 | 100 MHz | 24.41 | 24.41 | – | – | – | – |
| p4000000000_r15_n4096_d2_el-15 | 200 MHz | 24.41 | 24.42 | – | – | – | – |
| p4000000000_r30_n4096_d2_el-15 | 20 MHz | 22.40 | 22.40 | – | – | – | – |
| p4000000000_r30_n4096_d2_el-15 | 100 MHz | 22.40 | 22.41 | – | – | – | – |
| p4000000000_r30_n4096_d2_el-15 | 200 MHz | 22.40 | 22.41 | – | – | – | – |
| p2000000000_r30_n4096_d2_el-15 | 20 MHz | 20.11 | 20.11 | – | – | – | – |
| p2000000000_r30_n4096_d2_el-15 | 100 MHz | 20.11 | 20.11 | – | – | – | – |
| p2000000000_r30_n4096_d2_el-15 | 200 MHz | 20.11 | 20.10 | – | – | – | – |
| p4000000000_r30_n4096_envoutdoor01_ground_alt9.26_d2_el-15 | 20 MHz | 3.89 | 22.43 | -9.26 | 1.99 | 28.57 | -144.56 |
| p4000000000_r30_n4096_envoutdoor01_ground_alt9.26_d2_el-15 | 100 MHz | 3.89 | 22.44 | -72.88 | 1.49 | 0.00 | -147.37 |
| p4000000000_r30_n4096_envoutdoor01_ground_alt9.26_d2_el-15 | 200 MHz | 3.89 | 22.44 | -84.80 | 1.49 | 0.00 | -148.56 |
| p4000000000_r15_n4096_envoutdoor01_ground_alt5.4_d2_el-15 | 20 MHz | 11.90 | 24.24 | -2.55 | 4.47 | 100.00 | -138.06 |
| p4000000000_r15_n4096_envoutdoor01_ground_alt5.4_d2_el-15 | 100 MHz | 11.90 | 24.38 | -78.09 | 0.79 | 0.00 | -137.75 |
| p4000000000_r15_n4096_envoutdoor01_ground_alt5.4_d2_el-15 | 200 MHz | 11.90 | 24.38 | -90.09 | 0.79 | 0.00 | -139.28 |

### 0963 — landed 1,024-position cells

| line | cell | lvl_db | ac_to_static_db |
|---|---|---|---|
| 1 | p4000000000_r15_n1024_d2_el-5 | -125.55 | -12.65 |
| 2 | p4000000000_r15_n1024_az18_d2_el-5 | -133.64 | -4.45 |
| 3 | p4000000000_r15_n1024_az36_d2_el-5 | -128.16 | -11.07 |
| 4 | p4000000000_r15_n1024_az54_d2_el-5 | -125.78 | -12.67 |
| 5 | p4000000000_r15_n1024_az72_d2_el-5 | -129.40 | -10.39 |
| 6 | p4000000000_r15_n1024_az90_d2_el-5 | -114.67 | -20.75 |
| 7 | p4000000000_r15_n1024_az108_d2_el-5 | -125.40 | -14.44 |
| 8 | p4000000000_r15_n1024_az126_d2_el-5 | -141.01 | 1.04 |
| 9 | p4000000000_r15_n1024_az144_d2_el-5 | -138.36 | 0.15 |
| 10 | p4000000000_r15_n1024_az162_d2_el-5 | -129.06 | -8.94 |
| 11 | p4000000000_r15_n1024_ss2_d2_el-5 | -124.82 | -15.29 |
| 12 | p4000000000_r15_n1024_ss2_az54_d2_el-5 | -131.63 | -7.56 |
| 13 | p4000000000_r15_n1024_ss2_az90_d2_el-5 | -112.88 | -23.91 |
| 14 | p4000000000_r15_n1024_az342_d2_el-5 | -131.23 | -8.15 |
| 15 | p4000000000_r15_n1024_az324_d2_el-5 | -130.17 | -8.14 |
| 16 | p4000000000_r15_n1024_az306_d2_el-5 | -143.61 | 4.64 |
| 17 | p4000000000_r15_n1024_az288_d2_el-5 | -128.32 | -12.50 |
| 18 | p4000000000_r15_n1024_az270_d2_el-5 | -114.67 | -23.51 |
| 19 | p4000000000_r15_n1024_d2_el-4 | -124.39 | -13.44 |
| 20 | p4000000000_r15_n1024_d2_el-10 | -122.97 | -17.16 |
| 21 | p4000000000_r15_n1024_d2_el-16 | -119.50 | -20.22 |
| 22 | p4000000000_r15_n1024_d2_el-22 | -120.86 | -14.75 |
| 23 | p4000000000_r15_n1024_d2_el-28 | -133.15 | -1.20 |
| 24 | p4000000000_r15_n1024_d2_el-34 | not complete | – |
| 25 | p4000000000_r15_n1024_d2_el-40 | not complete | – |
| 26 | p4000000000_r15_n1024_d2_el-15 | not complete | – |
| 27 | p4000000000_r15_n1024_az18_d2_el-15 | not complete | – |
| 28 | p4000000000_r15_n1024_az36_d2_el-15 | not complete | – |
| 29 | p4000000000_r15_n1024_az54_d2_el-15 | not complete | – |
| 30 | p4000000000_r15_n1024_az72_d2_el-15 | not complete | – |

