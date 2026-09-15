"""Rebuild the directory review from inventory, CPU probes, and existing gates.

Run: CUDA_VISIBLE_DEVICES='' SIONNA2_ALLOW_CPU=1 /workspace/.venvs/py312/bin/python benchmark/review_directory_0915.py
Writes only outputs/directory_review_0915.json and docs/DIRECTORY_REVIEW_0915.ipynb.
This is a repository review and synthetic numerical check, not an RF validation.
"""
from __future__ import annotations

import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import warnings

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/directory_review_0915.json'
NOTEBOOK = ROOT / 'docs/DIRECTORY_REVIEW_0915.ipynb'
GATES = ('check_reader_gate', 'check_report_links', 'check_retracted',
         'check_stale_titles', 'check_row_pointers', 'check_new_file_rules')


def collect():
    os.environ.update(CUDA_VISIBLE_DEVICES='', SIONNA2_ALLOW_CPU='1',
                      OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
                      MKL_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    if hasattr(os, 'sched_getaffinity'):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'benchmark')]
    import numpy as np
    import audit_isac_detection_0915 as audit

    data = {'_meta': {
        'generator': 'benchmark/review_directory_0915.py',
        'command': f'{sys.executable} benchmark/review_directory_0915.py',
        'started_utc': datetime.now(timezone.utc).isoformat(),
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'scope': 'File inventory, source review, read-only gates, CPU synthetic probes. No full simulation rebuild or RF measurement.',
        'versions': {p: version(p) for p in ('sionna', 'sionna-rt', 'mitsuba', 'drjit', 'numpy', 'torch')},
        'snapshot_note': 'Live workers can add files during inventory; counts describe this scan.'},
        'inventory': {}, 'gates': {}, 'source_sha256': {}}
    for name in ('src', 'benchmark', 'runners', 'outputs', 'reports', 'docs', 'assets', 'vendor', 'work'):
        files = [p for p in (ROOT / name).rglob('*') if p.is_file()]
        data['inventory'][name] = {'files': len(files), 'bytes': sum(p.stat().st_size for p in files)}
    sources = sorted(p for folder in ('src', 'benchmark', 'runners')
                     for p in (ROOT / folder).rglob('*.py'))
    errors = []
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', SyntaxWarning)
        for p in sources:
            try:
                ast.parse(p.read_text(), filename=str(p))
            except (SyntaxError, UnicodeError) as exc:
                errors.append({'file': str(p.relative_to(ROOT)), 'error': str(exc)})
    data['syntax'] = {'files': len(sources), 'errors': errors, 'error_count': len(errors)}
    tracked = subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines()
    data['working_tree'] = dict(Counter(line[:2] for line in tracked))
    names = {'pyproject.toml', 'requirements.txt', 'uv.lock', 'environment.yml', 'setup.py', 'pytest.ini', 'Makefile'}
    data['setup_files'] = sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and p.name in names)
    data['volumes'] = json.loads((ROOT / 'outputs/volumes_index.json').read_text())['_meta']
    env = dict(os.environ, PYTHONPATH=f'{ROOT / "src"}:{ROOT / "benchmark"}')
    for name in GATES:
        start = time.monotonic()
        result = subprocess.run([sys.executable, f'benchmark/{name}.py'], cwd=ROOT,
                                env=env, capture_output=True, text=True, timeout=120)
        data['gates'][name] = {'exit_code': result.returncode, 'seconds': time.monotonic() - start,
                               'stdout': result.stdout, 'stderr': result.stderr}
    data['gate_count'] = len(GATES)
    data['gate_pass_count'] = sum(r['exit_code'] == 0 for r in data['gates'].values())
    data['cfar'] = audit.cfar_precision()
    data['range_and_steering'] = audit.oracle_and_steering()
    data['eca'] = audit.eca_low_doppler()
    rng = np.random.default_rng(915)
    frames, length, delay, offset, fs = 32, 128, 7, 5, 128000.0
    original = np.exp(0.5j * np.pi * rng.integers(0, 4, (frames, length)))
    rows = []
    for repeated in (True, False):
        ref = np.tile(original[0], (frames, 1)) if repeated else original
        echo = np.roll(ref, delay, axis=1) * np.exp(2j * np.pi * offset * np.arange(frames) / frames)[:, None]
        _, _, production = audit.pp.range_doppler(echo.ravel(), ref.ravel(), fs, frames, length)
        profiles = np.fft.ifft(np.fft.fft(echo, axis=1) * np.conj(np.fft.fft(ref, axis=1)), axis=1)
        correct = abs(np.fft.fftshift(np.fft.fft(profiles * np.hanning(frames)[:, None], axis=0), axes=0))
        target = (frames // 2 + offset, delay)
        rows.append({'repeated': repeated, 'production_peak': float(production[target]),
                     'matched_peak': float(correct[target]),
                     'target_cell_ratio_db': float(20 * np.log10(production[target] / correct[target])),
                     'production_argmax': list(map(int, np.unravel_index(production.argmax(), production.shape)))})
    data['reference_frames'] = {'setup': {'frames': frames, 'length': length, 'delay': delay,
                                          'doppler_offset': offset, 'fs_hz': fs, 'seed': 915}, 'rows': rows}
    for name in ('README.md', 'DIRECTORY.md', 'OPENSOURCE.md', 'g.xml',
                 'src/passive_process.py', 'src/detection_gpu.py', 'src/experiment_detection.py',
                 'src/waveforms_sionna.py', 'src/rcs_sbr.py', 'runners/SOLVER_BUILDS.json',
                 'benchmark/review_directory_0915.py', 'benchmark/audit_isac_detection_0915.py'):
        data['source_sha256'][name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    return data


def build(data):
    from report_style import build_notebook, from_json, header, md, next_steps
    source = from_json(str(OUT.relative_to(ROOT)))
    blocks = [header(
        num='디렉터리 점검', title='연구 자산의 구성과 다음 수정 우선순위',
        did='디렉터리 구성·핵심 처리 코드·문서·기존 검사를 대조하고 합성 입력으로 계산을 확인했다.',
        results=[
            f"선택한 검사 {source.num('gate_count')}개 중 {source.num('gate_pass_count')}개가 종료 코드 기준으로 통과했다.",
            '강한 셀을 포함한 합성 입력에서 CFAR 누적 정밀도 차이에 따른 추가 검출을 재현했다.',
            '현재 거리 표시와 배열 이득 실험에는 정답 위치·이상적 조향 가정이 들어 있다.',
            '새 실험의 출발점은 입력 계약·환경 재현·발간 범위를 함께 정리하는 것이다.'],
        method=[('파일·문서', '파일 목록과 Python 구문을 검사하고 핵심 경로를 선별해서 읽었다.'),
                ('계산', 'CPU 합성 반례와 대조 입력을 사용했다. 실측과 전체 GPU 실험 재실행은 이번 범위 밖이다.')],
        repro={'cmd': f'{sys.executable} benchmark/review_directory_0915.py',
               'out': str(OUT.relative_to(ROOT)), 'runtime': 'CPU 단일 코어; 검사별 소요는 원장 참조'}),
        md('## 구성과 강점', '',
           '| 위치 | 역할 |', '|---|---|',
           '| `src/` | 산란 커널·신호 처리·보고서 빌더 |',
           '| `benchmark/` | 실험·합성 반례·원장 생성·검사 |',
           '| `runners/` | 작업 목록·supervisor·솔버 버전 장부 |',
           '| `outputs/` | 수치 원장·그림·자세별 shard |',
           '| `reports/` | 독자용 notebook과 생성용 조각 |',
           '| `docs/` | 규약·재현 안내·진행 및 검토 기록 |',
           '| `assets/` · `vendor/` · `work/` | 형상 자산·설치 wheel·중간 작업 |'),
        md('원장 → 빌더 → notebook의 경로, 철회 기록, 입력 유한값 검사, 솔버 버전 꼬리표는 유지할 가치가 있다.', '',
           f"권 색인에는 본편 {source.num('volumes.n_volumes')}권·별편 {source.num('volumes.n_companions')}편·notebook {source.num('volumes.n_notebooks')}개가 기록돼 있다.",
           '파일 수는 작업 중 스냅샷이다. 내용 검토는 핵심 코드와 문서를 선별한 범위다.'),
        md('## 우선 수정: CFAR 누적 정밀도', '',
           f"합성 RD 크기 {source.num('cfar.setup.shape[0]')}×{source.num('cfar.setup.shape[1]')}, "
           f"명목 Pfa {source.num('cfar.setup.pfa_nominal')}, 강한 셀 [{source.num('cfar.setup.strong_cell[0]')}, {source.num('cfar.setup.strong_cell[1]')}], "
           f"배경 단위전력 대비 {source.num('cfar.rows[4].peak_over_unit_background_power_db')} dB 조건이다.",
           f"중앙 guard 행을 제외한 검출 수는 float32 {source.num('cfar.rows[4].torch32_off_guard_hits')}셀, "
           f"float64 {source.num('cfar.rows[4].torch64_off_guard_hits')}셀이다.", '',
           '관찰: `src/detection_gpu.py`는 누적합을 입력 dtype으로 계산한다. 강한 셀 주변 누적합의 차를 구하는 과정이 점검 대상이다.',
           '권고: 높은 정밀도의 누적합과 직접 training-window 합을 대조하는 회귀검사를 먼저 마련한다.', '',
           '범위: CPU 합성 입력의 수치 반례다. 기존 원장 Pd/Pfa에 미친 영향은 실제 IQ별 재평가가 필요하다.'),
        md('## 추적 확장 전: 정답과 수신 처리를 분리', '',
           f"동일 IQ의 정답 메타데이터를 {source.num('range_and_steering.same_IQ_different_ground_truth_range.truth_ranges_m[0]')} m에서 "
           f"{source.num('range_and_steering.same_IQ_different_ground_truth_range.truth_ranges_m[1]')} m로 바꾸면 "
           f"표시 축이 {source.num('range_and_steering.same_IQ_different_ground_truth_range.axis_shift_min_m')} m 이동한다.",
           'RD 배열은 같은 상태다. `Precomputed`의 거리축은 표적 정답에 맞춘 시각화다.', '',
           '`gpu_montecarlo`는 steering vector 길이로 이상적인 배열 이득을 적용한다. 실제 방향 추정·조향 오차는 별도 평가 항목이다.',
           '권고: delay 기준과 수신 시각으로 거리축을 정하고, 표적 truth는 평가 단계에서 결합한다.', '',
           '`src/passive_process.py` 머리말은 다중프레임 판정과 Kalman을 향후 범위로 명시한다. 탐지 결과를 추적 완성도로 읽을 때 이 구분이 필요하다.'),
        md('## 파형 확장 전: 프레임별 기준신호 계약', '',
           '`range_doppler`와 `rd_batch`는 첫 프레임 기준신호를 여러 프레임에 재사용한다.',
           f"독립 QPSK {source.num('reference_frames.setup.frames')}프레임·길이 {source.num('reference_frames.setup.length')}표본·"
           f"지연 {source.num('reference_frames.setup.delay')}표본·Doppler offset {source.num('reference_frames.setup.doppler_offset')}빈 합성 입력에서 "
           f"정답 셀 피크는 프레임별 정합 대비 {source.num('reference_frames.rows[1].target_cell_ratio_db', fmt='{:.2f}')} dB다.",
           f"같은 프레임 반복 대조 입력에서는 {source.num('reference_frames.rows[0].target_cell_ratio_db', fmt='{:.2f}')} dB다.",
           '해석: payload가 프레임마다 달라지는 실험에는 프레임별 reference 처리 계약이 필요하다. 표준 파형이나 RF 성능을 측정한 값은 아니다.', '',
           '`waveforms_sionna.crosscheck`는 같은 자작 resource grid를 두 OFDM 변조기에 넣는다. 변조 계산의 일치와 전체 표준 파형 적합성은 검사 범위가 다르다.'),
        md('## 환경·문서의 현재 상태', '',
           f"설치 메타데이터의 Sionna RT는 `{data['_meta']['versions']['sionna-rt']}`이고, `runners/SOLVER_BUILDS.json`에 그 조합이 기록돼 있다.",
           '`README.md`와 `benchmark/README.md`의 도입부는 이전 솔버 버전을 안내한다. 과거 결과 환경과 새 실험 환경을 나눠 표시하는 것이 좋다.', '',
           '조사한 setup 파일명 범위에서는 주 프로젝트의 dependency manifest와 lockfile이 검색되지 않았다. `jihyuck/po_mdoppler/requirements.txt`는 별도 코드용이다.',
           '`g.xml`은 지면 장면을 절대경로로 참조한다. 이름·용도·생성 경로를 문서화하고 다른 checkout에서의 사용 여부를 확인할 필요가 있다.', '',
           '`docs/RESUME.md`는 과거 날짜를 안내하고 최근 일일 resume에도 이전 운영 상태가 남아 있다. 현재 상태를 읽는 입구를 한 곳으로 정하는 것이 좋다.'),
        md('## 통과한 검사와 남는 범위', '',
           f"Python 구문 검사 대상은 {source.num('syntax.files')}파일, 구문 오류는 {source.num('syntax.error_count')}건이다.",
           '아래 종료 코드는 검사 범위에서의 결과다. 물리적 타당성이나 전체 빌드 성공과는 별도다.',
           '| 검사 | 종료 코드 |', '|---|---|',
           *[f"| `{name}` | {source.num(f'gates.{name}.exit_code')} |" for name in GATES]),
        md('`check_new_file_rules`는 기준선 이후 새 항목을 차단한다. 기존 기준선 항목도 검사 출력에 남는다.', '',
           '`check_reader_gate`도 알려진 미차단 표시 패턴을 출력하며 통과한다. 통과 코드만 요약하면 이 범위가 사라진다.', '',
           '`docs/MESH_GALLERY_STALE_0914.md`에는 표적 보고서 빌더의 갤러리 원장 불일치가 기록돼 있다. 이번에는 그 빌더를 실행하지 않았으므로 현재 실패를 재확인한 결과로 세지 않았다.', '',
           '기존 결과의 실제 영향, 전체 report 재빌드, 실제 장비 비교는 후속 점검 범위다.'),
        next_steps([
            ('CFAR 누적합과 동적 범위 회귀검사', '기존 검출 원장을 재계산할 범위를 결정한다', '`src/detection_gpu.py`'),
            ('수신 처리의 truth 분리와 프레임별 reference 지원', '거리·방향·추적 성능 평가에 쓸 입력 계약을 결정한다', '`src/experiment_detection.py` · `src/passive_process.py`'),
            ('설치 조합 기록과 CPU smoke 실행 경로 정리', '새 checkout에서 재현 가능한 최소 실행 경로를 결정한다', '`runners/SOLVER_BUILDS.json` · `docs/REPRODUCE.md`'),
            ('최신 상태 입구와 보고서 빌드 문제 정리', '다음 실험에 쓸 문서·원장·빌더의 기준을 결정한다', '`docs/RESUME.md` · `docs/MESH_GALLERY_STALE_0914.md`'),
        ])]
    build_notebook(str(NOTEBOOK), blocks, strict=True)


if __name__ == '__main__':
    os.chdir(ROOT)
    result = collect()
    build(result)
    print(json.dumps({'notebook': str(NOTEBOOK), 'gates_passed': result['gate_pass_count'],
                      'syntax': result['syntax']}, ensure_ascii=False))
