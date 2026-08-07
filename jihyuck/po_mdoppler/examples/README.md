# examples — 사용법 & 시각적 예시

`po_mdoppler` 패키지의 **각 모듈 역할**과 **시뮬레이션 전 형상/기하 검증**을 담은 노트북입니다.
모두 새 `po_sim` 모듈을 그대로 호출하며, 그림이 임베드되어 있어 열기만 해도 결과가 보입니다.

| 노트북 | 내용 |
|--------|------|
| [01_modules_overview.ipynb](01_modules_overview.ipynb) | 각 파일 역할 + 최소 API 데모 (config·mesh·kinematics·physics·occlusion·engine 한 펄스) |
| [02_mesh_and_motion.ipynb](02_mesh_and_motion.ipynb) | **메쉬 로드 모양 → 블레이드 회전(스냅샷·실 ESC RPM) → 기체 자세 회전 → 실제 PX4 궤적** |
| [03_normals_and_occlusion.ipynb](03_normals_and_occlusion.ipynb) | **법선 외향 확인 → 레이더 기하 → 가시성(cosθ>0) → Occlusion(레이캐스팅) 시각화** |

## 실행

Jupyter 에서 열면 임베드된 그림이 바로 보입니다. 다시 실행하려면 이 `examples/` 폴더(또는
패키지 루트 `po_mdoppler/`)에서 커널을 띄우세요 — 노트북이 알아서 패키지 경로를 잡습니다.

```bash
cd po_mdoppler/examples
/workspace/sionna_env/bin/jupyter lab   # 또는 notebook
```

> **주의**: 그림 임베드용으로 재실행할 때 `MPLBACKEND=Agg` 로 실행하지 마세요(인라인 캡처 안 됨).
> 노트북 첫 셀의 `%matplotlib inline` 이 올바른 백엔드를 잡습니다.

## 어떤 원본 노트북을 정리한 것?

- `02` ← 구 `mesh_mapping.ipynb` (메쉬·블레이드·자세 변환 검증)
- `03` ← 구 `test_stft*.ipynb` 의 법선/가시성/차폐 진단 셀들

원본은 하드코딩된 인라인 코드였고, 여기서는 `po_sim.{mesh,kinematics,physics,occlusion}` 모듈
호출로 대체해 리팩토링본과 1:1로 대응됩니다.
