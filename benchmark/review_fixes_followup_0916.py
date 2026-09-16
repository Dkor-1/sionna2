"""Rebuild the follow-up review with CPU probes and source snapshots.

Run: CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_fixes_followup_0916.py
Writes outputs/fixes_followup_0916.json and docs/FIXES_FOLLOWUP_0916.ipynb.
No RF measurements, GPU jobs, production edits, or canonical ledger overwrites.
"""
from __future__ import annotations
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/fixes_followup_0916.json'
NB = ROOT / 'docs/FIXES_FOLLOWUP_0916.ipynb'
SOURCES = {
    'scale': ('benchmark/verify_observability.py', 'H = np.concatenate(Hs, 0) @'),
    'unscale': ('benchmark/verify_observability.py', 'sigma_vel_ms=[float(x / t_obs)'),
    'known_fix': ('benchmark/report4_fixups.py', 'legacy_factor_for_pre_0916_ledgers'),
    'paper': ('docs/paper/04_detector.md', '송수신 한 쌍의 한 순간 관측량은 3차원 위치에 대해 랭크 2 이고'),
    'paper_builder': ('src/build_part09_detector.py', 'def _patch_paper_doc('),
    'review': ('benchmark/review_research_logic_0916.py', "d['checks']['both_rank_claim_contradicted']"),
    'stale_review': ('benchmark/review_research_logic_0916.py', '계획의 차별점은 네 RX 각도'),
    'endpoint': ('docs/MOBICOM_PIPELINE_PLAN_0916.md', 'and the rule each competing method'),
    'holdout': ('docs/MOBICOM_PIPELINE_PLAN_0916.md', '- placement-selection flights'),
    'placement': ('docs/MOBICOM_PIPELINE_PLAN_0916.md', 'comparison, the only family a twin claim'),
    'cfar': ('src/detection_gpu.py', 'P = rd.to(torch.float64) ** 2'),
    'reference': ('src/passive_process.py', 'def range_doppler('),
    'ideal_scope': ('src/experiment_detection.py', 'gpu_montecarlo uses the steering vector'),
    'threshold': ('src/build_part10_results.py', 'title="자유공간 형상에서 문턱'),
    'rank': ('src/build_part10_results.py', '자세평균에서 가장 견고한 것은'),
    'correlation': ('src/build_part05_anchor.py', '_STRONGER_KO ='),
    'observability': ('src/build_part09_detector.py', 'title="한 순간의'),
}


def collect():
    os.environ.update(CUDA_VISIBLE_DEVICES='', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    sys.path.insert(0, str(ROOT / 'src'))
    import numpy as np
    import torch
    from detection_gpu import cfar_batch, rd_batch, validate
    from passive_process import range_doppler
    d = {'_meta': {'generator': 'benchmark/review_fixes_followup_0916.py',
         'command': f'{sys.executable} benchmark/review_fixes_followup_0916.py',
         'utc': datetime.now(timezone.utc).isoformat(),
         'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
         'scope': 'Selected source/publication review and CPU analytic probes. Design assessments are human-reviewed snapshot judgments, not automatic proof of design adequacy.',
         'independent_review': 'design_review reviewed the evaluation contract; verify_review independently checked published claims and velocity scaling.'},
         'sources': {}, 'source_sha256': {}, 'checks': {}}
    for key, (path, needle) in SOURCES.items():
        text = (ROOT / path).read_text()
        lines = [i+1 for i, line in enumerate(text.splitlines()) if needle in line]
        if not lines:
            raise ValueError(f'Source changed; re-review {path}: {needle}')
        d['sources'][key] = {'path': path, 'line': lines[0], 'excerpt': text.splitlines()[lines[0]-1]}
        d['source_sha256'][path] = hashlib.sha256(text.encode()).hexdigest()
    d['checks']['existing_cpu_kernel_validation'] = bool(validate(verbose=False))
    # Direct local sums are independent of the summed-area implementation.
    rows = []
    for seed in (915, 916):
        rng = np.random.default_rng(seed)
        rd = rng.rayleigh(size=(64, 32)).astype(np.float32)
        rd[32, 2] = 1e5
        power = rd.astype(np.float64)**2
        expected = np.zeros_like(rd, dtype=bool)
        for i in range(rd.shape[0]):
            for j in range(rd.shape[1]):
                mask = np.zeros_like(rd, dtype=bool)
                mask[max(0,i-8):i+9, max(0,j-8):j+9] = True
                mask[max(0,i-2):i+3, max(0,j-2):j+3] = False
                n = mask.sum()
                expected[i,j] = power[i,j] > n*(1e-4**(-1/n)-1)*power[mask].mean()
        actual = cfar_batch(torch.from_numpy(rd)[None])[0][0].numpy()
        rows.append({'seed': seed, 'mismatched_cells': int(np.sum(actual != expected))})
    d['cfar'] = {'shape': [64,32], 'strong_amplitude': 1e5, 'pfa': 1e-4, 'rows': rows,
                 'mismatched_cells': sum(row['mismatched_cells'] for row in rows)}
    d['checks']['cfar_direct_local_sum'] = d['cfar']['mismatched_cells'] == 0
    rng = np.random.default_rng(916)
    m, length, lag, doppler = 32, 256, 7, 3
    refs = np.exp(1j*np.pi/2*rng.integers(0,4,(m,length)))
    surv = np.roll(refs, lag, axis=1)*np.exp(2j*np.pi*doppler*np.arange(m)/m)[:,None]
    _, _, rd = range_doppler(surv.ravel(),refs.ravel(),1e6,m,32,per_frame_ref=True)
    rd_t = rd_batch(torch.from_numpy(surv.reshape(1,-1)), torch.from_numpy(refs),m,32)[0].numpy()
    peak = list(map(int, np.unravel_index(rd.argmax(),rd.shape)))
    d['reference'] = {'frames':m,'frame_length':length,'expected_peak':[m//2+doppler,lag],
                      'actual_peak':peak,'relative_numpy_torch_error':float(np.max(abs(rd-rd_t))/rd.max())}
    d['checks']['variable_frame_target_peak'] = peak == d['reference']['expected_peak'] and np.allclose(rd,rd_t)
    # Extract only the pure Jacobian routines; do not import the experiment driver.
    obs = json.loads((ROOT/'outputs/verify_observability.json').read_text())
    meta = obs['meta']
    ns = {'np':np,'TXv':np.array(meta['tx']),'RXv':np.array(meta['rx']),
          'TGT':np.array(meta['target']),'VTRUE':np.array(meta['vel'])}
    tree = ast.parse((ROOT/'benchmark/verify_observability.py').read_text())
    funcs = [node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ('_rows_pair','gramian')]
    exec(compile(ast.Module(body=funcs,type_ignores=[]),'production_jacobian','exec'),ns)
    cell = next(c for c in obs['cells'] if c['key']==obs['gramian']['ref_cfg'])
    pairs = [(ns['TXv'],ns['RXv']),(ns['TXv'],np.array(obs['fixes']['_rx2']))]
    scale_rows=[]
    for duration in (1.,obs['gramian']['t_obs_s']):
        h = np.concatenate([ns['_rows_pair'](ns['TGT']+ns['VTRUE']*t,ns['VTRUE'],cell['lam_m'],t,cell['sigma_rb_m'],cell['sigma_fd_hz'],tx,rx)
                            for t in np.linspace(-duration/2,duration/2,16) for tx,rx in pairs])
        physical = np.sqrt(np.diag(np.linalg.inv(h.T@h)))
        g,_,_ = ns['gramian'](cell,16,duration,pairs=pairs)
        existing = np.sqrt(np.diag(np.linalg.pinv(g,rcond=1e-13)))
        wrong = existing[3:]/duration
        scale_rows.append({'duration_s':duration,'physical_velocity_std_ms':physical[3:].tolist(),
                           'current_velocity_std_ms':wrong.tolist(),'understatement_factor':(physical[3:]/wrong).tolist(),
                           'physical_position_rms_m':float(np.linalg.norm(physical[:3])),
                           'current_position_rms_m':float(np.linalg.norm(existing[:3]))})
    d['velocity']={'cell':cell['key'],'epochs':16,'tx':meta['tx'],'rx':meta['rx'],'rx2':obs['fixes']['_rx2'],
                   'target':meta['target'],'velocity':meta['vel'],'rows':scale_rows,
                   'factor':obs['gramian']['t_obs_s']**2}
    # ⛔2026-09-16 (R39): the generator was fixed after this review was written, so the two checks below
    #   now read "is the fix in" instead of "is the bug reproduced". The pre-fix numbers stay in
    #   velocity.history_pre_r39 so the review's own arithmetic can still be read.
    d['velocity']['history_pre_r39'] = dict(
        understatement_factor_per_duration={r['duration_s']: r['duration_s'] ** 2 for r in scale_rows},
        pre_fix_2rx_sigma_vel_ms=[0.0010405608570125146, 0.0018594292040108897, 0.010044676780703973],
        note='before R39 the velocity columns were multiplied by t_obs and the sigmas divided by it again')
    d['checks']['velocity_scaling_fixed'] = all(np.allclose(r['understatement_factor'], 1.0, rtol=1e-5)
                                                for r in scale_rows)
    d['checks']['position_full_rank_invariant'] = all(np.isclose(r['physical_position_rms_m'],r['current_position_rms_m'],rtol=1e-5) for r in scale_rows)
    d['checks']['canonical_velocity_matches_physical_units'] = bool(
        np.allclose(scale_rows[-1]['physical_velocity_std_ms'], obs['fixes']['2RX']['sigma_vel_ms'], rtol=1e-5))
    d['check_count']=len(d['checks'])
    if not all(d['checks'].values()):
        raise ValueError(d['checks'])
    for path in ('outputs/verify_observability.json','outputs/report4_fixups.json'):
        d['source_sha256'][path]=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    OUT.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    return d


def build(d):
    from report_style import header, md, from_json, next_steps, build_notebook
    s=from_json(str(OUT.relative_to(ROOT)))
    def nums(key, count):
        return '[' + ', '.join(s.num(f'{key}[{i}]') for i in range(count)) + ']'
    def refs(*keys):
        return '근거: '+' · '.join(f'[{d["sources"][k]["path"]}](../{d["sources"][k]["path"]}) 행 {s.num("sources."+k+".line")}' for k in keys)
    blocks=[header(num='수정 후 재검토',title='수정 반영 상태와 남은 평가 계약',
        did='수정된 소스와 보고서를 대조하고 수치 반례를 CPU에서 다시 계산했다.',
        results=[f"경량 검사 {s.num('check_count')}항목이 각 명시 조건을 통과했다.",
                 '문턱 공유·순위·OFDM·지면 조건과 주요 비교군 설계의 문구가 개선됐다.',
                 f"속도 표준편차를 {s.num('velocity.factor')}배 작게 쓰던 오류는 원 생성기에서 고쳐졌다(R39) — 원장이 이제 물리 단위다.",
                 '논문 조각과 이전 검토 보고서에는 수정 전 판단이 남아 있다.'],
        method=[('계산','직접 국소 합 CFAR 대조, 변하는 프레임의 표적 피크, 물리 단위 Jacobian 역행렬'),
                ('범위','선별 파일의 수정 반영과 설계 검토. RF 측정·GPU 실행·전체 원장 재생성은 별도 작업이다.')],
        repro={'cmd':f'{sys.executable} benchmark/review_fixes_followup_0916.py','out':str(OUT.relative_to(ROOT)), 'runtime':'CPU 단일 코어 경량 계산'}),
        md('## 개선된 부분', '',
           '| 항목 | 현재 판단 |', '|---|---|',
           '| 공유 SNR 문턱 | 먼저 얻은 파형의 값을 공유한다는 가정과 NR 자체 문턱 공백을 명시했다. |',
           '| 기체 순위·상관 | 단일 자세와 자세평균의 순위를 분리하고 더 큰 상관 열을 원장에서 읽는다. |',
           '| 관측가능성 본편 | 국소 상태 랭크·관측가능 부분공간 CRLB·전역 모호성을 구분했다. |',
           '| 계획 | OFDM 잡음, 지면 조건, 원자료 평가, 동일 후보 로터 비교, 감시 채널 배분, 송신 자원 개입, 동일 하드웨어 배치 비교를 구체화했다. |',
           '', '문구와 설계의 수정 상태이며 실외 성능을 얻었다는 뜻과 구분한다.', '', refs('threshold','rank','correlation','observability')),
        md('## 구현 수정도 확인한 부분', '',
           f"CPU·RD 크기 {nums('cfar.shape', 2)}·강한 셀 진폭 {s.num('cfar.strong_amplitude')}·명목 Pfa {s.num('cfar.pfa')}에서 직접 국소 합과 현재 CFAR의 불일치는 {s.num('cfar.mismatched_cells')}셀이다.", '',
           f"서로 다른 QPSK 기준 프레임 {s.num('reference.frames')}개·프레임 길이 {s.num('reference.frame_length')}에서 주입 피크 {nums('reference.expected_peak', 2)}와 복원 피크 {nums('reference.actual_peak', 2)}가 일치했다.", '',
           '프레임별 기준 입력을 선택하는 경로를 검사했다. 반복 프레임용 기본 경로를 사용하는 호출부는 실제 파형 조건과 맞춰야 한다. 과거 결과의 재계산 여부는 이 검사와 별개다.', '', refs('cfar','reference')),
        md('## 속도 스케일 정정이 원 계산에 합쳐졌다 (R39)', '',
           f"원장 조건 {s.num('velocity.cell')}·관측 {s.num('velocity.rows[1].duration_s')} s·epoch {s.num('velocity.epochs')}개·두 수신 위치는 원장에 보존했다.", '',
           f"물리 단위 Jacobian에서 얻은 속도 표준편차는 {nums('velocity.rows[1].physical_velocity_std_ms', 3)} m/s, 현재 계산은 {nums('velocity.rows[1].current_velocity_std_ms', 3)} m/s다.", '',
           '현재 H의 속도 열에 T를 곱하면 좌표는 v/T가 된다. 그 공분산을 속도로 되돌릴 때 T를 곱해야 하지만 코드는 나눈다. 문서대로 vT 좌표를 쓰려면 처음부터 H의 속도 열을 T로 나눠야 한다.', '',
           f"대조 관측시간 {s.num('velocity.rows[0].duration_s')} s에서는 배율 오류가 숨는다. 해당 full-rank 위치 CRLB(rms)는 {s.num('velocity.rows[1].physical_position_rms_m')} m로 유지된다.", '',
           '이는 새로 발견된 보정식이 아니라 별도 fixups에 이미 기록된 정정의 통합 누락이다. 특이 행렬의 pinv·상대 고유값 판정은 좌표를 일관되게 고친 뒤 따로 재평가한다.', '', refs('scale','unscale','known_fix')),
        md('## 문구 전파와 검토 보고서의 현재성', '',
           '논문 조각에는 순간 위치 랭크와 시간 누적 상태 랭크를 연결하고 CRLB를 위치 RMS로 부르는 옛 문장이 남아 있다. 생성기는 축약된 archive notebook에서 논문 조각 생성을 건너뛰며 기존 파일을 보존한다.', '',
           '앞서 작성한 검토 보고서도 현재 상태에 맞춘 상태 구분이 필요하다. 순위 재계산 조건은 이전 문장의 반례를 확인하지만 현재 문장에 그 주장이 남았는지 검사하지 않는다. 수정된 채널 배분·비교군을 다시 미해결로 출력하는 부분도 있다.', '',
           '이전 검토는 당시 스냅샷으로 보존하고 항목별 수정·부분 수정·미해결 상태를 별도로 연결한다. 재계산 통과와 수정 반영 완료를 나눠 표시한다.', '', refs('paper','paper_builder','review','stale_review')),
        md('## 추가 설계 과제: 추적 연속성의 분모와 성공 조건', '',
           '중심 질문은 배치에 따른 track continuity 개선으로 좁혀졌다. 다음 단계는 공통 평가 공간·전체 비행시간 분모·truth 매칭 허용오차·ID 변경·최대 coasting·구간 제외 규칙을 고정하는 일이다.', '',
           '각 배치가 잘 보이는 구간만 분모로 삼으면 좁은 coverage가 유리해질 수 있다. 검출이 끊겨도 예측만 지속하는 tracker에는 위치 매칭이 틀어진 뒤 연속성 점수를 주지 않도록 한다.', '',
           '주요 지표·최소 의미 효과·false-track 및 위치오차 제약·비행/날짜 단위 표본 수와 불확실성 계획을 함께 적는다. 현행 계획은 효과 크기 미정을 솔직하게 표시한다.', '', refs('endpoint')),
        md('## 추가 설계 과제: 트윈이 배치를 고르는 규칙', '',
           '같은 후보와 하드웨어를 쓰는 비교군은 마련됐다. 이제 상대 RT 출력에서 후보 점수로 가는 식, 예상 궤적의 가중치, 통신 제약과 설정 허용오차를 고정한다.', '',
           '자유공간 일치 → rotor 대비 → 배치 순위 → 실제 추적 연속성은 서로 다른 평가 단계다. 평가 비행 전에 순위를 예측하고 선택 배치의 성능과 실측 최선 후보 대비 손실을 함께 보고한다.', '',
           '실측 최선 후보를 평가 뒤 구하면 oracle 진단으로 표시하고 그 추가 탐색 비용을 실용 measured-search baseline의 보정 예산과 구분한다.', '', refs('placement','endpoint')),
        md('## 추가 설계 과제: holdout과 배치 비교의 교란 통제', '',
           '다른 날짜·궤적을 평가에 쓰면 설정 선택의 누설을 줄인다. 장비를 옮겨 순서대로 측정하는 배치 비교에서는 날짜·바람·간섭·비행 조건 차이를 추가로 통제해야 한다.', '',
           '공통 날짜/세션 블록 안에서 각 방법에 같은 궤적군을 반복하고 순서를 무작위화하거나 균형 배치한다. 고정 기준 배치를 다시 측정해 drift를 기록하고 블록 내 성능 차이를 비교한다.', '',
           '사이트 일반화는 새 사이트별 보정 허용과 무보정 전이를 구분해 정의한다.', '', refs('holdout')),
        md('## 기존 시뮬레이션의 해석 범위', '',
           'truth에 붙인 거리축과 steering vector 길이에 따른 이상적 배열 이득은 현재 소스가 제한으로 명시한다. 이 단순화를 실제 거리·방위·추적 정확도로 인용하는 경우 별도의 독립 수신 처리와 truth 사후 평가가 필요하다.', '', refs('ideal_scope')),
        next_steps([
            ('속도 좌표계 정정을 원 생성기에 통합하고 관련 원장을 다시 계산한다','원장과 보정 파일 사이의 단위 일관성','관측가능성 계산'),
            ('논문 조각과 검토 보고서에 최신 상태를 연결한다','재빌드 뒤에도 독자가 같은 범위의 주장을 읽는다','논문 생성 경로와 검토 이력'),
            ('연속성 정의·배치 점수·블록 실험 순서를 고정한다','측정 전에 주효과와 인과 비교가 결정된다','현행 pipeline 평가 계약')])]
    build_notebook(str(NB),blocks,strict=True)


if __name__=='__main__':
    os.chdir(ROOT)
    data=collect()
    build(data)
    print(json.dumps({'report':str(NB),'checks':data['checks']},ensure_ascii=False))
