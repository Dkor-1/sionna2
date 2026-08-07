# po_mdoppler — PO 마이크로-도플러 시뮬레이터 (리팩토링본)

기존 `sionna_sim/sim_ablation.py` (단일 파일)을 **재사용 가능한 모듈**로 분해한
버전입니다. 물리·수치 로직은 원본과 **동일**하며(검증된 값 그대로), 구조만
정리했습니다. 기존 코드는 그대로 두고 이 폴더에 새로 작성되었습니다.

> 한 줄 요약: PX4 비행 텔레메트리(위치·자세·ESC RPM) → 드론 3D 메쉬에 물리광학(PO)
> 패싯 산란 적용 → X-대역(9.85 GHz) 레이더 마이크로-도플러 **복소 신호**(윈도우당 5000펄스)를
> 생성. 신호는 **분해 저장**(body/blade × 재질 × occlusion)되어, occlusion×재질
> ablation 9조합을 사후 덧셈으로 복원.

---

## 폴더 구조

```
po_mdoppler/                  # ← 이 폴더만 압축해서 넘겨도 그대로 동작 (self-contained)
├── Mesh/                     # 삼각화 + 법선 외향 보정 메쉬 (drone_body, blade_1..4)
│                             #   = 구 Phantom4_Mesh_normals_out 복사본
├── data/sim_data/            # PX4 입력 (clean_*.csv) grade_0..7 번들 — 패키지에 포함됨
├── configs/
│   └── default.py            # SimConfig(레이더/샘플링) + 재질 + airframe 기하 + 경로
├── po_sim/                   # 순수 라이브러리 (configs 를 import 하지 않음)
│   ├── mesh.py               # PLY 로드 + body/blade → world 조립   ("매쉬 조립")
│   ├── kinematics.py         # PX4 CSV → 펄스별 pose + 블레이드각    ("기동")
│   ├── physics.py            # Fresnel Γ + PO 패싯 산란 프리미티브   ("PO 전용")
│   ├── occlusion.py          # Embree BVH 레이캐스팅 가시성 마스크
│   └── engine.py             # 펄스 분해 + 윈도우 루프 + multiprocessing
├── scripts/
│   └── generate_ablation.py  # CLI 진입점 (구 sim_ablation.py)
├── examples/                 # 사용법 + 시각적 예시 (ipynb, 그림 임베드)
│   ├── 01_modules_overview.ipynb      # 각 파일 역할 + 최소 API 데모
│   ├── 02_mesh_and_motion.ipynb       # 메쉬·블레이드·기체 회전·PX4 궤적
│   └── 03_normals_and_occlusion.ipynb # 법선 외향 확인 + 레이더 기준 occlusion
├── requirements.txt          # 의존성 (pip install -r)
└── README.md
```

**설계 원칙**: `po_sim/` 는 인자로만 동작하는 순수 라이브러리입니다.
`SimConfig`(어떻게: 레이더/샘플링)와 `SceneSpec`(무엇을: 재질+기하)를 주입받고,
기본값은 `configs/default.py` 에서 CLI 가 읽어 넣습니다.

---

## 설치 & 인계 (self-contained)

이 폴더만 압축해서 넘기면 그대로 동작합니다. 메쉬·입력데이터(grade_0..7)·노트북(그림 포함)이
모두 안에 있습니다. 받는 쪽:

```bash
cd po_mdoppler
python -m venv .venv && source .venv/bin/activate   # (선택) 가상환경
pip install -r requirements.txt
# 노트북 보기/재실행
jupyter lab examples/
# 시뮬 생성 (예: grade_2 서브셋)
python scripts/generate_ablation.py --grade 2 --max-windows 2 --workers 2
```

- **입력 데이터**: `configs/default.py` 가 주변 `sionna_sim/260115_sim/sim_data` 가 있으면
  그걸(개발 머신, 전 grade), 없으면 번들된 `data/sim_data/` 를 자동으로 사용합니다.
- **출력**: `/data/...` 가 없으면 `po_mdoppler/output/` 에 저장됩니다 (`--out` 로 변경 가능).
- **Occlusion**: `embreex`(레이캐스팅 백엔드)만 있으면 됩니다. 별도 시스템 Embree/구 pyembree 불필요.

---

## 파이프라인

```
PX4 CSV (grade_{G}/clean_{position,attitude,esc}.csv)
        │  kinematics.load_flight  (위치=선형, 자세=SLERP, RPM=누적각 적분 ×rpm_scale)
        ▼
35 kHz 보간 → 펄스별 (position, rot_matrix, blade_angle)      [kinematics.window_poses]
        ▼
메쉬 조립: body = R·v+p,  blade = R·Rspin·v + p + R·offset     [mesh.body/blade_facets]
        ▼
PO 패싯 산란  s_i = Γ(θ;er,σ)·A·cosθ/R² · e^(−j2kR)          [physics]
   + 가시성(법선 cosθ>0) + occlusion(Embree 레이캐스팅)        [occlusion]
        ▼
펄스별 분해 합산 → window_XXXXX.npz (복소 (5000,) × 키들)      [engine]
```

## 출력 (윈도우당 npz 키)

각 `window_XXXXX.npz` 는 아래 complex128 `(n_pulses,)` 신호를 담습니다:

```
body_none, body_occ
blade_none_{nylon,cf,metal}
blade_occ_{nylon,cf,metal}
```

**ablation 9조합 사후 복원** (body 는 metal 고정):

| occlusion | 재질 X | = |
|-----------|--------|---|
| none | X | `body_none + blade_none_X` |
| body | X | `body_occ  + blade_none_X` |
| full | X | `body_occ  + blade_occ_X`  |

`X ∈ {nylon, cf, metal}`. 노이즈·전역스케일·body/blade 비·벌크도플러·DC제거·
STFT 파라미터는 **전부 사후** 적용(이 패키지 범위 밖, downstream).

---

## 실행

```bash
cd po_mdoppler

# 서브셋 스모크 테스트 (2 윈도우, 워커 2)
python scripts/generate_ablation.py --grade 2 --max-windows 2 --workers 2 --out /tmp/po_test

# 전체 grade_2 (표준 RPM ×5.73 + rpm 증강 스윕)
python scripts/generate_ablation.py --grade 2 --rpm-scale 5.73 --rpm-sweep 5.16,6.30
```

주요 옵션: `--grade`, `--workers`, `--max-windows`, `--out`, `--rpm-scale`,
`--rpm-sweep lo,hi`, `--radar-{azimuth,range,height}`,
`--blade-cf-{eps,sigma}`(cf RCS 물리보정), `--per-rotor`(1D 컴포넌트 refine용).

> **성능 주의**: 스크립트가 numpy import 전에 BLAS 스레드를 워커당 1로 캡합니다
> (`OMP/OPENBLAS/MKL_NUM_THREADS=1`). 이걸 빼면 워커마다 스레드풀이 겹쳐 load~800,
> ~7배 느려집니다. 프로세스 수는 `--workers` 또는 `PO_WORKERS` 로 조절하세요.

## 라이브러리로 사용

```python
import sys; sys.path.insert(0, "po_mdoppler")
from configs.default import SimConfig, BODY_MAT, BLADE_MATS, BLADE_MAT_KEYS, \
    BLADE_OFFSETS, BLADE_DIRS, MESH_DIR, DATA_BASE
from po_sim.engine import run_generation, SceneSpec

cfg  = SimConfig(rpm_scale=5.73)
spec = SceneSpec(BODY_MAT, dict(BLADE_MATS), list(BLADE_MAT_KEYS),
                 BLADE_OFFSETS, BLADE_DIRS)
run_generation(cfg, spec, grade=2, data_dir=f"{DATA_BASE}/grade_2",
               out_dir="/tmp/po_test/grade_2", mesh_dir=MESH_DIR,
               workers=2, max_windows=2)
```

---

## 입력 데이터

`../260115_sim/sim_data/grade_{0..7}/` (원위치 참조, 이동 없음):
`clean_position.csv`(~50 Hz), `clean_attitude.csv`(쿼터니언, SLERP),
`clean_esc.csv`(4채널 ESC RPM, 누적각 적분).

## 원본 대비

- `sim_ablation.py` 의 물리·CLI·출력 포맷을 그대로 보존(동일 결과).
- 구 `run_po_batch*.py` 변형들(단일재질/차폐 on-off/무잡음)은 이 분해 출력으로
  전부 사후 복원되므로 별도 포팅하지 않음.
- 메쉬는 `Phantom4_Mesh_normals_out` (법선 외향 보정본)만 사용.
