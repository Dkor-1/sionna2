"""Rebuild a scoped critique of current research claims and experiment design.

Run: CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_research_logic_0916.py
Writes only outputs/research_logic_review_0916.json and docs/RESEARCH_LOGIC_REVIEW_0916.ipynb.
Uses saved ledgers and analytic CPU counterexamples, not RF measurements or new simulation runs.
"""
from __future__ import annotations
import ast
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/research_logic_review_0916.json'
NB = ROOT / 'docs/RESEARCH_LOGIC_REVIEW_0916.ipynb'

SOURCES = {
    'scope': ('docs/MOBICOM_PIPELINE_PLAN_0916.md', 'Differentiation from LaSen'),
    'ofdm': ('docs/MOBICOM_PIPELINE_PLAN_0916.md', 'divides each received resource element'),
    'all_ground': ('docs/MOBICOM_PIPELINE_PLAN_0916.md', 'check for isolated jumps before trusting a spectrum'),
    'rotor': ('docs/MOBICOM_PIPELINE_PLAN_0916.md', 'does a confirmed track'),
    'channels': ('docs/MOBICOM_PIPELINE_PLAN_0916.md', 'sensing RX 3'),
    'bearing': ('docs/MOBICOM_PIPELINE_PLAN_0916.md', 'sector amplitude ratio'),
    'placement': ('docs/MOBICOM_PIPELINE_PLAN_0916.md', 'omnidirectional antenna'),
    'admission': ('benchmark/isac_plan_positioning_0915.py', 'tolerance, fixed before'),
    'observability': ('src/build_part09_detector.py', 'title="한 순간의'),
    'gramian': ('benchmark/verify_observability.py', 'def gramian('),
    'pinv': ('benchmark/verify_observability.py', 'pinv 가 영공간을'),
    'threshold': ('src/build_part10_results.py', 'title="자유공간 형상에서 문턱'),
    'threshold_gap': ('src/build_part10_results.py', '직접 재지 못한다'),
    'rank': ('src/build_part10_results.py', '자세평균에서 가장 견고한 것은'),
    'rank_generator': ('benchmark/sigma_sensitivity.py', 'smallest_airframe_rank_aspect_averaged'),
    'correlation': ('src/build_part05_anchor.py', '쪽이 크다(⛔2026-09-16 정정'),
    'known_height': ('benchmark/design_isac_campaign_0915.py', 'known target height'),
    'truth': ('benchmark/design_isac_campaign_0915.py', 'ground_truth_role'),
    'policy': ('benchmark/design_isac_campaign_0915.py', 'processing window alone'),
    'shared_clock': ('benchmark/design_isac_waveform_benchmark_0915.py', 'communication_receiver_clock'),
    'fairness': ('benchmark/design_isac_waveform_benchmark_0915.py', "'id':'resource_matched'"),
    'negative_trials': ('benchmark/design_isac_campaign_0915.py', 'Correlated adjacent captures'),
    'novelty': ('src/build_part02_prior_work.py', '## 네 관문'),
    'replacement': ('benchmark/isac_plan_corpus_0915.py', 'def outliers(E, k):'),
}


def collect():
    os.environ.update(CUDA_VISIBLE_DEVICES='', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    if hasattr(os, 'sched_getaffinity'):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    import numpy as np
    d = {'_meta': {'generator': 'benchmark/review_research_logic_0916.py',
          'command': f'{sys.executable} benchmark/review_research_logic_0916.py',
          'utc': datetime.now(timezone.utc).isoformat(),
          'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
          'scope': 'Selected current plans, report headlines, builders and ledgers; analytic counterexamples. No exhaustive literature review, RF measurement, full rebuild, or GPU job.',
          'interpretation': 'Confirmed source/ledger inconsistencies are separated from proposed-design risks. Existing acknowledgments remain attached.'},
          'sources': {}, 'source_sha256': {}, 'checks': {}}
    for key, (path, needle) in SOURCES.items():
        p = ROOT / path
        lines = p.read_text().splitlines()
        matches = [i for i, line in enumerate(lines) if needle in line]
        if not matches:
            raise ValueError(f'Review source changed; re-review {path}: {needle}')
        i = matches[0]
        d['sources'][key] = {'path': path, 'line': i + 1, 'excerpt': '\n'.join(lines[max(0, i-1):i+3])}
        d['source_sha256'][path] = hashlib.sha256(p.read_bytes()).hexdigest()
    def ledger(path):
        p = ROOT / path
        d['source_sha256'][path] = hashlib.sha256(p.read_bytes()).hexdigest()
        return json.loads(p.read_text())
    s = ledger('outputs/sigma_sensitivity.json')['size_vs_fragility']
    rows = s['by_drone']
    order = {name: sorted(rows, key=lambda k: rows[k][field], reverse=True)
             for name, field in [('single', 'flip_span_single_aspect_db'), ('average', 'flip_span_aspect_avg_db')]}
    extent = [x['extent_m'] for x in rows.values()]
    margin = [x['flip_span_single_aspect_db'] for x in rows.values()]
    spread = [x['max_band_sigma_spread_db'] for x in rows.values()]
    d['ranking'] = {'rows': rows, 'order': order, 'n_airframes': len(rows),
                    'mini_single_rank': order['single'].index('mini5pro') + 1,
                    'mini_average_rank': order['average'].index('mini5pro') + 1,
                    'corr_extent': float(np.corrcoef(extent, margin)[0, 1]),
                    'corr_spread': float(np.corrcoef(spread, margin)[0, 1])}
    d['checks']['ledger_correlations_recomputed'] = bool(np.isclose(d['ranking']['corr_extent'], s['corr_extent_vs_flip_single']) and np.isclose(d['ranking']['corr_spread'], s['corr_sigma_spread_vs_flip_single']))
    d['checks']['both_rank_claim_contradicted'] = order['single'][0] == 'mini5pro' and order['average'][0] != 'mini5pro'
    d['threshold'] = ledger('outputs/report05_derived.json')['threshold']
    d['checks']['nr_threshold_skipped'] = d['threshold']['g1_skipped_cells'] == d['threshold']['g1_total_cells']
    corpus = ledger('outputs/isac_plan_corpus_0915.json')
    d['aimed_ground'] = next(x for x in corpus['dropout']['summary'] if x['scene'] == 'outdoor01_ground' and x['ant'] == 'tr38901')
    d['checks']['all_ground_claim_contradicted'] = d['aimed_ground']['n_cells_with_outliers'] < d['aimed_ground']['n_cells']
    d['kernel_scope'] = ledger('outputs/isac_plan_kernel_match_0915.json')['not_computed']
    # Exact constellation enumeration isolates post-division noise variance.
    qpsk = np.array([a + 1j*b for a in (-1, 1) for b in (-1, 1)]) / np.sqrt(2)
    qam = np.array([a + 1j*b for a in (-3, -1, 1, 3) for b in (-3, -1, 1, 3)]) / np.sqrt(10)
    factors = [float(np.mean(1 / abs(x)**2)) for x in (qpsk, qam)]
    d['ofdm'] = {'model': 'Y = H X + N, elementwise diagonal channel; equal mean symbol energy; independent additive noise',
                  'qpsk_inverse_energy': factors[0], 'qam_inverse_energy': factors[1],
                  'noise_ratio_db': float(10*np.log10(factors[1]/factors[0])),
                  'limit': 'Analytic average noise after elementwise division, not end-to-end detection loss.'}
    # Plane reflection gives a global ambiguity even for a locally full-rank Jacobian.
    tree = ast.parse((ROOT / 'benchmark/verify_observability.py').read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_rows_pair')
    scope = {'np': np}
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'production_rows_pair', 'exec'), scope)
    tx, rx1, rx2 = map(np.array, ([0., 0., 10.], [5., 0., 10.], [0., 8., 10.]))
    p, v = np.array([10., 3., 14.]), np.array([1., 2., -.3])
    pm, vm = p.copy(), v.copy(); pm[2] = 20 - pm[2]; vm[2] *= -1
    times = np.linspace(0, 3, 16); wavelength = .1
    def measurements(pos, vel):
        result = []
        for t in times:
            q = pos + vel*t
            for rx in (rx1, rx2):
                a, b = q-tx, q-rx
                ra, rb = np.linalg.norm(a), np.linalg.norm(b)
                result.append([ra+rb, float((a/ra+b/rb)@vel/wavelength)])
        return np.array(result)
    h = np.concatenate([scope['_rows_pair'](p + v*t, v, wavelength, t, 1., 1., tx, rx)
                        for t in times for rx in (rx1, rx2)])
    eig = np.linalg.eigvalsh(h.T@h); rank_tol = 1e-8
    d['observability'] = {'tx': tx.tolist(), 'receivers': [rx1.tolist(), rx2.tolist()],
                         'p': p.tolist(), 'v': v.tolist(), 'mirrored_p': pm.tolist(), 'mirrored_v': vm.tolist(),
                         'times': times.tolist(), 'wavelength_m': wavelength, 'relative_eigenvalue_tolerance': rank_tol,
                         'local_rank': int(np.sum(eig/eig.max() > rank_tol)),
                         'max_range_difference_m': float(np.max(abs(measurements(p,v)[:,0]-measurements(pm,vm)[:,0]))),
                         'max_doppler_difference_hz': float(np.max(abs(measurements(p,v)[:,1]-measurements(pm,vm)[:,1]))),
                         'position_separation_m': float(np.linalg.norm(p-pm)),
                         'limit': 'Synthetic geometry with stations in a horizontal plane and both trajectories above ground. Additional side-of-plane or height priors may resolve ambiguity.'}
    d['checks']['mirror_counterexample'] = d['observability']['local_rank'] == 6 and d['observability']['max_range_difference_m'] < 1e-10 and d['observability']['max_doppler_difference_hz'] < 1e-10
    campaign = ledger('outputs/isac_campaign_design_0915.json')
    fa = campaign['false_alarm_design']; pfa = fa['target_frame_false_alarm_probability']; alpha = 1-fa['one_sided_confidence']
    n = math.ceil(math.log(alpha)/math.log(1-pfa))
    d['false_alarm'] = {'target': pfa, 'confidence': 1-alpha, 'independent_trials': n,
                        'upper_bound_zero': 1-alpha**(1/n), 'limit': 'Independent identically distributed target-absent trials only; not adjacent-frame independence or track-level false-alarm validation.'}
    d['checks']['binomial_plan_recomputed'] = n == fa['zero_false_positive_independent_trials_needed']
    if not all(d['checks'].values()):
        raise ValueError(f'Review conclusions require revision: {d["checks"]}')
    d['check_count'] = len(d['checks'])
    d['source_sha256']['benchmark/review_research_logic_0916.py'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    return d


def build(d):
    sys.path.insert(0, str(ROOT/'src'))
    from report_style import header, md, from_json, next_steps, build_notebook
    s = from_json(str(OUT.relative_to(ROOT)))
    def refs(*keys):
        return '근거: ' + ' · '.join(f'[{d["sources"][k]["path"]}](../{d["sources"][k]["path"]}) 행 {s.num("sources." + k + ".line")}' for k in keys)
    def finding(title, status, observation, meaning, action, keys):
        return md('## '+title, '', '**구분:** '+status, '', '**관찰:** '+observation, '',
                  '**해석:** '+meaning, '', '**권고:** '+action, '', refs(*keys))
    blocks = [header(num='논리·설계 검토', title='주장 범위와 실험이 결정할 것',
        did='현행 계획과 보고서의 주장·원장·생성 코드를 대조하고 순위와 해석식 반례를 재계산했다.',
        results=[f"정량 재계산과 근거 대조 {s.num('check_count')}항목이 빌더의 명시한 조건을 통과했다.",
                 '공유 문턱·위치 복원·파형 독립성·기체 순위의 일부 문장은 근거 범위보다 크다.',
                 '자유공간 비교에서 실외 배치·추적 성능으로 넘어가는 구간에는 별도 평가가 필요하다.',
                 '원장에 이미 적힌 제한과 새 실험에서 정할 조건을 구분했다.'],
        method=[('직접 확인', '현행 계획·선별 보고서·빌더·원장의 대조와 CPU 해석 계산'),
                ('검토 범위', '실측·문헌 전체 조사·GPU 재실행은 범위 밖이다. 합성 반례는 가정의 범위를 확인한다.')],
        repro={'cmd': f'{sys.executable} benchmark/review_research_logic_0916.py',
               'out': str(OUT.relative_to(ROOT)), 'runtime': 'CPU 단일 코어의 경량 계산'}),
        md('## ⚠ 이 편은 2026-09-16 오전의 스냅샷이다', '',
           '여기서 든 문장들은 같은 날 안에 고쳐졌다 — 공유 문턱은 R38, 기체 순위·상관은 R37, '
           '속도 CRLB 스케일은 R39 로 `docs/RETRACTION_LOG.md` 에 적혔고, 관측가능성 본편·계획 문구도 '
           '함께 바뀌었다. **지금 저장소가 뭐라고 적고 있는지**는 `docs/FIXES_FOLLOWUP_0916.ipynb` 가 든다. '
           '이 편은 그때의 근거와 반례를 남겨 두는 자리다 — 아래 문장들을 현재 상태로 읽지 않는다.', ''),
        md('## 전체 흐름에 대한 판단', '',
           '현재 자료는 산란·수치 동작을 자세히 설명한다. 다음 연구에서는 그 관찰이 어떤 수신 처리·배치 결정을 바꾸며, 실제 탐지와 추적에 무엇을 더하는지 연결해야 한다.', '',
           '권장 흐름: 해결할 실패 상황 → 원인 후보 → 통제 실험 → 사용할 방법 → 같은 자원의 비교 → 별도 세션에서의 평가.', '',
           '새 기능의 수와 연구 기여는 구분한다. 아래의 확정 문장 오류는 수정 대상으로, 설계 위험은 앞으로 가를 가설로 읽는다.'),
        finding('문턱 공유는 실험 결과와 가정을 나눠 써야 한다', '확인된 제목과 본문의 범위 차이',
            f"공유 문턱의 출처는 {s.num('threshold.snr90_source_mode')}다. NR은 검사 칸 {s.num('threshold.g1_total_cells')}개 중 {s.num('threshold.g1_skipped_cells')}개가 건너뛰어져 자기 문턱이 비어 있다.",
            '본문은 W1 문턱을 함께 쓰는 선택이라고 설명하지만 제목은 여러 밴드에서 같은 문턱을 발견한 것처럼 읽힌다.',
            '제목을 공유 문턱 가정의 영향 평가로 바꾸고, 각 파형의 유효 Doppler 축에서 별도 교정·평가를 한다. 겹치는 신뢰구간과 동등성 입증도 구분한다.',
            ('threshold', 'threshold_gap')),
        finding('수신기 추가와 전역 위치 복원은 다른 주장이다', '기하 반례와 코드로 확인',
            f"합성 배치에서 국소 상태 랭크는 {s.num('observability.local_rank')}이며, 거울상 궤적 간 위치 간격은 {s.num('observability.position_separation_m')} m다. 그런데 거리 차는 {s.num('observability.max_range_difference_m')} m, Doppler 차는 {s.num('observability.max_doppler_difference_hz')} Hz다.",
            '이 반례는 수신기 개수나 국소 full rank만으로 전역 유일성을 보장할 수 있는지를 시험한다. 실제 보고서 기하의 제약은 별도이며, pinv가 버린 영공간의 불확실성을 유한 RMS로 읽어서도 안 된다.',
            '관측시간·운동모델·센서 배치·허용 높이·가시영역을 붙여 표현하고, 허용 상태 전체에서 모호성을 확인한다. CRLB와 실제 추적 오차를 별도로 보고한다.',
            ('observability', 'gramian', 'pinv')),
        finding('기체 순위와 상관 해석은 원장 수치에 맞춰 고쳐야 한다', '직접 재계산한 서술 오류',
            f"현재 원장의 {s.num('ranking.n_airframes')}기체에서 mini5pro는 단일 자세 {s.num('ranking.mini_single_rank')}위, 자세평균 {s.num('ranking.mini_average_rank')}위다. Pearson 상관은 크기 {s.num('ranking.corr_extent', fmt='{:.3f}')}, σ 산포 {s.num('ranking.corr_spread', fmt='{:.3f}')}다.",
            '양쪽에서 가장 견고하다는 문장과 크기 쪽 상관이 더 강하다는 문장이 숫자와 어긋난다. 후자는 Pearson 절댓값 비교이며 인과관계는 별도 실험의 대상이다.',
            '단일 자세와 자세평균 순위를 각각 계산해 문장을 생성한다. 보고서와 원장 생성기의 산문을 함께 수정해 재빌드에도 같은 범위를 유지한다.',
            ('rank', 'rank_generator', 'correlation')),
        finding('알려진 OFDM 심볼로 나눠도 잡음 특성은 데이터에 의존한다', '해석식으로 확인한 과한 표현',
            f"동일 평균 심볼 에너지의 QPSK와 16-QAM을 열거하면 E[|X|⁻²]는 각각 {s.num('ofdm.qpsk_inverse_energy', fmt='{:.3f}')}와 {s.num('ofdm.qam_inverse_energy', fmt='{:.3f}')}다. 단순 나눗셈 후 평균 잡음 차는 {s.num('ofdm.noise_ratio_db', fmt='{:.3f}')} dB다.",
            'Y=HX+N에서 Y/X=H+N/X다. 잡음 없는 대각 채널 성분의 복원과 실제 RD·검출 성능의 데이터 독립성은 다르다. 이 수치는 검출 손실을 측정한 값이 아니다.',
            '문장을 잡음 없는 대각 채널로 한정한다. 같은 채널·잡음·자원에서 payload와 변조를 바꾸고, ICI·clipping·가중 추정의 영향을 별도 평가한다. 계획 표에는 이미 관련 경고가 있다.',
            ('ofdm',)),
        finding('모든 지면 장면이라는 표현에 조준 안테나 반례가 있다', '기존 원장으로 확인한 범위 오류',
            f"조준 안테나를 쓴 지면 묶음은 {s.num('aimed_ground.n_cells')}칸이며 고립 자세가 있는 칸은 {s.num('aimed_ground.n_cells_with_outliers')}칸이다.",
            '영문 계획의 every ground scene은 등방 조건에서 본 현상을 조준 안테나 조건까지 넓힌다. 한국어 초안은 조준 조건의 예외를 이미 설명한다.',
            '장면·안테나·높이·표본 범위를 같은 문장에 붙인다. 다른 조건을 합친 전칭 문장을 사용하기 전에 원장 묶음을 다시 센다.',
            ('all_ground',)),
        finding('자유공간 교차 비교 뒤에 실외 예측력을 따로 평가해야 한다', '아직 닫히지 않은 실험 설계',
            '계획은 커널과의 자유공간 비교 뒤 PathSolver로 환경을 모델링한다. 사전 허용 오차는 현재 positioning builder의 추가 작업에 적혀 있다.',
            '자유공간 일치는 그 조건의 일관성을 보여 준다. 지면·건물·안테나를 넣은 뒤 배치 순위와 추적 누락까지 예측하는지는 별도 문제다. 현재 규약도 두 근사의 일관성과 실측 타당성을 구분한다.',
            '설정 선택에 쓸 기하와 평가 기하를 분리하고 상대 지표·허용 오차를 먼저 고정한다. 선택한 설정을 고정한 채 지면·벽·실제 비행의 배치 순위 및 실패를 평가한다.',
            ('admission', 'placement')),
        finding('고립 자세 대체는 원인 확인과 분리해야 한다', '원인 추론 및 전처리 선택의 위험',
            '고립 자세를 복소 중앙값으로 바꾸면 빗살 대비가 커지고, 같은 수의 비고립 자세를 바꾸는 대조에서는 효과가 작다. 현재 원장은 원인 미확정을 명시한다.',
            '큰 편차를 골라 지웠다는 대조는 그 자세가 지표를 좌우함을 보여 준다. 수치 오류·물리적인 flash·실제 장애 중 무엇을 제거했는지는 추가 근거가 필요하다. 대비 회복도 탐지·추적 회복과 별도다.',
            '원자료 결과를 유지하고 대체 결과는 민감도로 병기한다. 경로 목록, packet loss, gain 및 clipping 기록으로 사유를 확인하고, 규칙을 고정한 별도 세션에서 실패율까지 평가한다.',
            ('replacement', 'all_ground')),
        finding('각도·높이 관측과 수신 채널 배분을 먼저 고정해야 한다', '현행 계획 간 조건 불일치',
            '계획의 차별점은 네 RX 각도를 말하지만 배분은 감시 RX 세 개와 기준 또는 통신 RX 한 개다. 캠페인의 초기 상태는 알려진 표적 높이를 가정한다.',
            'sector amplitude ratio에서 azimuth로 가는 보정 관계와 불확실성이 필요하다. RTK 높이를 수신 처리에 주면 보조 정보가 있는 추적이 된다. 기존 캠페인은 truth를 평가에만 사용하도록 규정한다.',
            '보유 안테나의 실제 배치·패턴을 정하고 별도 위치에서 각도 오차를 평가한다. 알려진 높이 실험과 미지 높이 실험을 분리하고, oracle angle은 상한 대조로 표시한다.',
            ('scope', 'channels', 'bearing', 'known_height', 'truth')),
        finding('디지털 트윈의 기여를 같은 하드웨어에서 가려야 한다', '비교군 설계가 더 필요함',
            '제시된 비교군은 단일 무지향 안테나, sector 제거, 트윈 없는 배치다.',
            '안테나 패턴·채널 수·개구·커버리지까지 바뀌면 효과를 트윈의 배치 판단에 귀속하기 어렵다. 트윈 없는 배치도 선택 규칙을 고정해야 비교가 재현된다.',
            '같은 안테나·채널·설치 후보·RF 예산에서 고정 배치, 기하 휴리스틱, 같은 보정 예산의 실측 탐색, 트윈 배치를 비교한다. 선정 뒤 별도 비행·날짜에서 평가한다.',
            ('placement', 'fairness')),
        finding('ISAC 자원 절충에는 송신 측 개입이 필요하다', '계획은 인식하지만 실행 계약은 미정',
            '모든 알려진 payload를 sensing에 쓰면서 revisit를 바꾸는 설계가 있다. 캠페인은 처리 창 변경만으로 송신 overhead가 생기는 것은 아니라고 명시한다.',
            '같은 송신 IQ를 재처리하는 실험은 계산·추적 정책 평가다. 통신과 sensing의 RF 자원 경쟁을 주장하려면 실제 바뀐 송신 자원이 있어야 한다. 같은 X410의 통신 RX는 공유 clock 조건의 실험이다.',
            '송신 IQ 고정·수신 처리만 변경한 대조를 먼저 둔다. 이후 airtime·전력·자원 배치 중 개입할 것을 정하고 동일 offered load에서 goodput·지연·추적 연속성을 비교한다.',
            ('policy', 'shared_clock', 'fairness')),
        finding('로터 확인은 실패한 후보와 비표적도 포함해야 한다', '선택 편향 및 오경보 단위의 위험',
            '계획은 이미 확인된 track에 blade line이 있는지 보고 false track 감소를 평가하려 한다. 위치 bin과 동체 Doppler도 tracker에서 받는다.',
            '살아남은 track만 고르면 로터 관측이 어려운 사례가 빠진다. 다중 분류를 제외해도 false track 감소 주장은 움직이는 clutter와 비표적 후보를 요구한다.',
            '같은 후보 목록에 로터 사용·미사용을 적용하고 관측시간과 확인 지연을 맞춘 persistence/SNR baseline을 둔다. 참 track 거부·확인 시간·시간당 거짓 track을 함께 보고, 비행·날짜 단위로 나눠 평가한다.',
            ('rotor', 'negative_trials')),
        md('## 표본 수 계산의 조건', '',
           f"오경보 목표 {s.num('false_alarm.target')}·단측 신뢰수준 {s.num('false_alarm.confidence')}에서 무오경보 상한을 계산하면 독립 H0 시행 {s.num('false_alarm.independent_trials')}회가 필요하다.", '',
           '이 값은 캠페인 원장의 이항 계산을 재현한 것이다. 연속 프레임을 그 수만큼 모으는 것과 독립 시행 확보는 다르며, cell·frame·track의 오경보 단위도 구분한다.', '',
           '환경과 궤적을 보고 문턱을 정한 데이터는 최종 성능 평가에서 분리한다. 세션 단위 오차와 실패 구간 길이도 함께 보고한다.'),
        finding('기술 조합의 희소성에서 연구 기여로 바로 넘어가지 않기', '연구 구성에 대한 판단',
            '기존 보고서는 드론 메쉬·특정 엔진·진폭 대조·게재 여부의 교집합을 조사한다. 새 계획에는 각도·다중 표적·통신 지표·트윈 배치가 차별점으로 나열된다.',
            '같은 구현 조합을 찾지 못했다는 사실과 중요한 미해결 문제를 해결했다는 사실은 다른 근거가 필요하다. 이번 검토는 문헌 전체의 신규성을 판정한 것이 아니다.',
            '주요 질문을 먼저 정한다. 예를 들어 같은 안테나와 통신 자원에서 트윈이 고른 배치가 기하 휴리스틱·실측 탐색보다 별도 비행의 track 단절을 줄이는지 시험할 수 있다. 나머지 기능은 그 질문의 근거로 배치한다.',
            ('novelty', 'scope')),
        md('## 이미 적절히 제한된 부분', '',
           '- 현재 한국어 계획은 조준 전후 대비의 원인을 미확정으로 남겨 두었다.',
           '- hover·단일 거리·합쳐진 채널 자료로 추적 정확도를 얻을 수 없다는 범위를 적었다.',
           '- 캠페인에는 truth 분리, holdout, 독립 H0 조건, 동일 자원 비교가 이미 들어 있다.',
           '- 커널과 PathSolver의 일치는 실측 타당성 대조와 구분돼 있다.', '',
           '이 항목들은 이미 마련된 제한으로 분류했다. 짧은 계획·제목·실행 코드까지 같은 조건을 유지하는 것이 과제다.'),
        next_steps([
            ('문턱·순위·OFDM·지면·관측가능성 문장 범위를 바로잡는다', '독자가 실제 계산 범위를 읽게 된다', '해당 원장 생성기와 report builder'),
            ('주요 연구 질문과 비교할 배치·수신 정책을 고정한다', '무엇이 연구 기여인지 평가할 기준이 정해진다', '현행 pipeline plan'),
            ('안테나·채널·높이·통신 자원 계약을 고정한다', '실험이 실제로 제공할 관측과 자원이 정해진다', 'campaign 및 waveform design'),
            ('보정 데이터와 평가 비행을 나누고 실패 사례까지 보고한다', '설정 선택 이후 새 조건의 예측력을 평가한다', '별도 날짜·비행·장면의 측정 계획'),
        ])]
    build_notebook(str(NB), blocks, strict=True)


if __name__ == '__main__':
    os.chdir(ROOT)
    result = collect()
    build(result)
    print(json.dumps({'report': str(NB), 'checks': result['checks'], 'ranking': result['ranking']['order']}, ensure_ascii=False))
