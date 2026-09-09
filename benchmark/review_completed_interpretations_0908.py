#!/usr/bin/env python
"""Rebuild an interpretation review from current notebooks and existing ledgers.

Run:
    CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 /workspace/.venvs/py312/bin/python benchmark/review_completed_interpretations_0908.py

This rechecks recorded numbers and small mathematical counterexamples. It does
not rerun GPU experiments or certify the current simulator against measurements.
"""
from pathlib import Path
import hashlib
import json
import math
import os
import subprocess
import sys

os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs/completed_interpretations_review_0908.json'
MEMO = ROOT/'docs/COMPLETED_INTERPRETATIONS_REVIEW_0908.md'
SOURCES = {}
BASELINE_REV = '2f82d34bfe0986b0cf0baff86028a13f2cd772c8'

def baseline(path):
    raw = subprocess.check_output(["git", "show", f"{BASELINE_REV}:{path}"], cwd=ROOT)
    SOURCES[f"{BASELINE_REV}:{path}"] = hashlib.sha256(raw).hexdigest()
    return raw.decode()



def read(path):
    raw = (ROOT/path).read_bytes()
    SOURCES[path] = hashlib.sha256(raw).hexdigest()
    return raw.decode()


def ledger(name):
    return json.loads(read('outputs/'+name+'.json'))


def source(path, needle):
    lines = baseline(path).splitlines()
    hits = [i+1 for i, line in enumerate(lines) if needle in line]
    assert hits, (path, needle)
    return dict(path=path, line=hits[0], text=lines[hits[0]-1].strip())


def quote(name, cell, needle):
    path = f'reports/{name}.ipynb'
    nb = json.loads(baseline(path))
    text = ''.join(nb['cells'][cell]['source'])
    hits = [line for line in text.splitlines() if needle in line]
    assert hits, (name, cell, needle)
    return dict(path=path, cell_zero_based=cell, text=hits[0])


def checks():
    b = ledger('report15_attack_stats')['q1_noise_floor']['budget_law']
    calculated_boost = b['slope_db_per_db_of_paths_median']*10*math.log10(
        b['median_path_count_ratio_m4e_over_mini2'])
    assert abs(calculated_boost-b['implied_mini2_boost_if_budget_matched_db']) < 1e-3
    s = ledger('sbr_defect_fixes')['d3_multibounce_phase']
    errors = [r['sbr_2bounce_dbsm']-r['exact_dbsm'] for r in s['rows']]
    assert abs(max(map(abs, errors))-s['max_abs_err_db']) < 1e-9
    # Magnitude cannot identify global complex phase.
    field = np.array([1+2j, -3+.5j])
    rotated = field*np.exp(1j*.73)
    phase_invariance = float(np.max(np.abs(abs(field)**2-abs(rotated)**2)))
    assert phase_invariance < 1e-12
    # Integer periods and no window: phase modulation has spectral lines above
    # the maximum instantaneous phase derivative. This is not a drone fit.
    n, periods, beta = 8192, 64, .5
    t = np.arange(n)/n
    e = np.exp(1j*beta*np.sin(2*np.pi*periods*t))
    power = abs(np.fft.fft(e-e.mean()))**2
    freq = np.fft.fftfreq(n, 1/n)
    tip = beta*periods
    tail = float(power[abs(freq)>tip].sum()/power.sum())
    assert tail > .999
    # Correlated components have a cross term; subtraction is an attribution
    # convention unless that term is measured or controlled.
    x = np.sin(2*np.pi*periods*t)
    total = float(np.mean(abs(x+x)**2))
    separated = float(2*np.mean(abs(x)**2))
    fs = ledger('report13_freespace')
    ranges = {}
    for drone, modes in fs['ranges'].items():
        for mode, node in modes.items():
            c = node['equal_psd']['full_waveform_capture']['by_N']['1']
            ranges[f'{drone}/{mode}'] = {k:c[k] for k in
                ('R90_C50_m', 'E_psi_Pd_at_R90', 'blind_heading_frac')}
    nr = [v for k,v in ranges.items() if k.endswith('/G1')]
    c = ledger('diag_physics_paths_el-90')
    settings = {k:{p:v[p] for p in ('max_depth','refraction','diffraction','edge_diffraction')}
                for k,v in c['cases'].items()}
    assert any(v['refraction'] for v in settings.values())
    assert any(v['max_depth'] != 1 for v in settings.values())
    hw = ledger('report06_measurement')['hw']
    ideal = 6.0206*hw['adc_bits']+1.76
    assert abs(ideal-hw['dynamic_range_db']) < 1e-9
    return dict(
        budget=dict(calculated_boost_db=calculated_boost,
                    ledger_boost_db=b['implied_mini2_boost_if_budget_matched_db'],
                    budget_matched_rerun_possible=b['spp_cap']['match_is_possible'],
                    slope_cells=b['slope_n_cells']),
        dihedral=dict(max_magnitude_error_db=max(map(abs,errors)), n_sizes=len(errors),
                      phase_rotation_power_error=phase_invariance),
        pure_phase_counterexample=dict(n=n, periods=periods, modulation_index=beta,
            max_instantaneous_frequency=tip, non_dc_power_above_max_fraction=tail,
            caveat='Synthetic analytic signal, integer periods, no window. '
                   'This challenges a strict spectral cutoff, not the measured drone attribution.'),
        nonorthogonal_counterexample=dict(total_power=total, separate_power_sum=separated,
                                          cross_term=total-separated),
        range_cells=ranges, nr_heading_average_zero_count=sum(v['E_psi_Pd_at_R90']==0 for v in nr),
        nr_count=len(nr), physics_settings=settings,
        ideal_adc_snr_db=ideal,
        blind_verdict=ledger('p3_attack')['Q1_was_the_answer_seen']['verdict'],
        nadir_split=ledger('refute_nadir_mechanism_final')['R5_detection']['nadir_ac_split'],
        realistic_span_db=ledger('sigma_sensitivity')['differential']['realistic_span_db'])


# Positive markers verify that the edited builders reached the published volumes.
FIX_MARKERS = [
    '가드 해제·단일 헤딩 기준 거리의 앵커 일차 보정값',
    'Phantom 3 계산을 문헌값과 대조했다',
    '경로수 일치 재실험은 미완료 상태다',
    '복소 위상 오차는 별도로 대조해야 한다',
    '드론 전체의 RCS·검출거리 오차 방향은 정할 수 없다',
    '다른 기체 속성의 기여는 미분리다',
    '잔여 방식으로 나눈 AC 전력 비율',
    '순시 주파수 최대값과 FFT의 지지구간은 서로 다른 개념이다',
    '나머지 행의 굴절·깊이는 설정 표를 따른다',
    '이 결과의 적용 범위는 기존 통제 기하와 기준신호 모델이다',
    '공칭 ADC 비트 수의 이상적 양자화 SNR은',
    '모델-앵커 기울기차로 정한 민감도 범위',
    '자세별 검출확률이나 검출거리를 계산한 뒤 평균한 결과는 아니다',
]


def current_status(findings):
    assert len(findings) == len(FIX_MARKERS)
    obsolete = ['다중반사 위상이 맞는다는 뜻이다', '가 광선 격자 표본화 잡음이다',
                '날개가 낼 수 없는 대역', '경로수를 맞췄을 때 Mini 2 상승분',
                '갈린 축은 대역도 전기적 크기도', '정적 클러터는 ECA 뒤에서 죽은 파라미터다']
    for r, marker in zip(findings, FIX_MARKERS):
        nb = json.loads(read(r['quote']['path']))
        cells = [(i, ''.join(c['source'])) for i,c in enumerate(nb['cells'])]
        matches = [i for i,t in cells if marker in t]
        remaining = [bad for bad in obsolete if any(bad in t for _,t in cells)]
        assert not remaining, (r['quote']['path'], remaining)
        r['current_revision'] = dict(applied=bool(matches), marker=marker, cells=matches)
    return dict(applied=sum(r['current_revision']['applied'] for r in findings),
                total=len(findings),
                scope='Verified wording in published notebooks; no new physical validation.')


def review_notebook(out):
    sys.path.insert(0, str(ROOT/'src'))
    from report_style import header, md, table, next_steps, build_notebook
    j='outputs/completed_interpretations_review_0908.json'
    state=out['implementation']
    blocks=[header(num='검토', title='완료 실험의 해석 범위와 표현 수정 기록',
        did='완료 실험의 제목·요약·본문을 원장과 생성 코드에 대조하고 확인된 표현을 수정했다.',
        results=[
            f"검토한 해석 {state['total']}건 중 본편 반영 {state['applied']}건 ⟨{j} : implementation⟩.",
            f"기존 한정이 적절한 해석 {len(out['preserved'])}건을 유지했다 ⟨{j} : preserved⟩.",
            f"예산 외삽과 RCS 크기 대조를 원장에서 재검산했다 ⟨{j} : checks⟩."],
        method=[('범위','아래 리포트의 지적 문장과 관련 본문·원장·코드를 대조했다. 전체 저장소의 모든 실험에 대한 전수 검증은 별도 범위다.'),
                ('증거 수준','기존 수치의 재계산과 수학적 반례를 사용했다. GPU 재실험·외부 계측은 후속 과제다.'),
                ('이력','수정 전 커밋의 인용문을 보존하고 현재 본편에서 반영 문구를 확인했다.')],
        repro=dict(cmd=["CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 /workspace/.venvs/py312/bin/python benchmark/review_completed_interpretations_0908.py --check-reports"],out=[j],runtime='CPU 한 코어의 원장·문서 대조'))]
    for i,r in enumerate(out['findings']):
        blocks.append(md(f"## {i+1}. {r['title']}", '',
            '**유지하는 결과:** '+r['retained'], '',
            f"**수정 반영:** {'확인' if r['current_revision']['applied'] else '대기'} · "
            f"[{Path(r['quote']['path']).stem}](../{r['quote']['path']}) · "
            f"[수정 전 인용·근거·권장 문장](COMPLETED_INTERPRETATIONS_REVIEW_0908.md) ⟨{j} : findings[{i}]⟩"))
    blocks.append(next_steps([
        ('가시성이 맞는 기본 장면 대조와 씨앗·로터 자세 교차 실험을 읽는다','무사건 이유와 후보 생성기 내부 원인의 구분','OUTDOOR_DESIGN_REVIEW_0908.md'),
        ('복소 위상·맞춘 광선 예산·자세별 검출확률을 각각 대조한다','현재 원장이 뒷받침하는 범위의 확장','COMPLETED_INTERPRETATIONS_REVIEW_0908.md'),
        ('기존 원장의 생성 경로 누락과 보고용 산문을 정리한다','기록 재현성과 후속 인용의 개선','COMPLETED_INTERPRETATIONS_REVIEW_0908.md')]))
    return build_notebook(str(ROOT/'docs/COMPLETED_INTERPRETATIONS_REVIEW_0908.ipynb'),blocks,strict=True)


def main():
    c = checks()
    c['wideband_recorded_cells_unchanged'] = {}
    for name in ('wideband_energy', 'wideband_energy_r15'):
        current = ledger(name)['cells']
        previous = json.loads(baseline('outputs/'+name+'.json'))['cells']
        assert current == previous, name
        c['wideband_recorded_cells_unchanged'][name] = len(current)
    findings = []
    def add(title, nb, cell, needle, issue, retained, replacement, refs, status='확인된 해석 범위 초과'):
        findings.append(dict(title=title, quote=quote(nb,cell,needle), status=status,
                             issue=issue, retained=retained, replacement=replacement,
                             sources=[source(*r) for r in refs]))

    add('헤딩 커버리지 거리처럼 보이는 R90은 가드를 끈 단일 헤딩 해다',
        '10_results',12,'앵커 σ 위의 R90',
        f"같은 리포트의 R90 정의는 공칭 헤딩 하나에서 도플러 가드를 끈 해라고 명시한다. "
        f"C50 키 이름의 커버리지 정의와 실제 값이 다르다. 원래 거리 원장의 G1 {c['nr_count']}개 기체 "
        f"중 {c['nr_heading_average_zero_count']}개에서 형제 키 E_psi_Pd_at_R90이 영이다. "
        '이 형제 키는 보정 전 거리 원장의 값이므로 앵커 보정 후 거리에서 재계산한 확률로 옮기면 안 된다. '
        '최종 km 열 자체도 기존 거리 해에 국소 지수를 적용한 일차 전이이며 보정 후 전체 검출 재실행이 아니다.',
        '선언된 송신 전력·기하·완전한 기준채널·단일 헤딩·가드 해제 조건의 거리 계산과 국소 보정값은 남는다.',
        '도플러 가드를 끈 단일 헤딩의 기준 거리 해를 앵커 보정으로 일차 전이했다. 헤딩 커버리지와 가드 적용 성능은 별도로 계산한다.',
        [('src/make_report05_results.py','A = {k: R[k] * 10 **'),
         ('src/build_part10_results.py','공칭 헤딩')])

    add('취소한 눈감기 검증이 절 제목에 남아 있다','03_anchor',22,'문헌값을 보지 않고',
        '본문은 눈감기 라벨을 취소했고 원장은 blind_intact = FALSE라고 기록한다. '
        '그런데 절 제목과 표에는 눈감기 산출 표현이 남아, 독립적인 사전 예측 검증처럼 읽힌다. '
        '이는 의도적으로 결과를 맞췄다는 증거를 뜻하지 않는다.',
        '해당 메쉬와 주파수 창에서 계산한 문헌 대조값은 남는다. 사전 비열람이라는 실험 지위만 제외한다.',
        'Phantom 3 계산을 문헌값과 대조했다. 문헌 비열람 조건은 유지되지 않아 눈감기 검증으로 분류하지 않는다.',
        [('src/build_part05_anchor.py','눈감기'),('outputs/p3_attack.json','Q1_was_the_answer_seen')])

    add('예산 보정의 예측을 예산을 맞춘 관측으로 서술한다','06_6_microdoppler-limits',25,'경로수를 맞췄을 때',
        f"원장 상승분은 {c['budget']['ledger_boost_db']:.3f} dB다. 이는 사다리 기울기와 기체 간 경로수 비로 "
        f"재계산한 {c['budget']['calculated_boost_db']:.3f} dB와 일치한다. 같은 예산으로 다시 돌린 관측값이 아니다. "
        '본문도 그 재실험이 표본 상한 때문에 미완료라고 적는다. 따라서 메쉬 품질을 배제하거나 무변조 칸의 원인을 예산으로 확정할 수 없다.',
        '기하를 고정한 예산 사다리의 통계 변화와 그 관계를 외삽한 예측은 남는다.',
        '예산 사다리에서 얻은 관계를 적용하면 지표 상승이 예측된다. 경로수를 맞춘 기체 비교는 미완료이므로 메쉬와 예산의 기여는 미분리다.',
        [('benchmark/report15_attack_stats.py','boost = sl_med *'),
         ('src/build_part07_microdoppler.py','메쉬 품질이 아니라')])

    add('RCS 크기 일치를 복소 위상 검증으로 확대한다','02_kernel',35,'다중반사 위상이 맞는다는',
        f"이면각 원장은 {c['dihedral']['n_sizes']}개 크기에 대한 RCS 오차를 비교하며 최대는 "
        f"{c['dihedral']['max_magnitude_error_db']:.3f} dB다. 이 결과는 다중반사 구현의 유용한 점검이지만 "
        '복소장의 위상 오차를 직접 기록하지 않는다. 전체 복소장을 같은 위상만큼 회전시켜도 RCS는 변하지 않는다. '
        '실제 코드에 위상 오류가 있다는 지적이 아니라 현재 검증 문장의 범위에 관한 지적이다.',
        '시험한 PEC 이면각의 크기·입사·주파수 조건에서 이중반사 RCS가 기준식과 가까웠다는 관측.',
        '시험한 PEC 이면각에서 이중반사 RCS가 기준식에 근접했다. 복소 위상은 위상 기준을 둔 별도 대조가 필요하다.',
        [('src/build_part04_kernel.py','다중반사 위상이 맞는다는'),
         ('benchmark/verify_sbr_defect_fixes.py','d3_multibounce_phase')])

    add('얇은 띠의 편파별 오차로 드론 탐지가 보수적이라고 읽는다','02_kernel',51,'보수적(비관적)',
        '같은 문단에 TM과 TE의 오차 부호가 반대라고 적혀 있고 현재 스칼라 커널은 그 편파를 구분하지 않는다. '
        '얇은 금속 띠의 대조를 복합 재질 드론 전체의 오차 방향으로 옮길 대조가 없다. '
        '여러 산란 성분의 복소 합에서는 부품별 크기 오차의 부호도 전체 크기의 부호를 보장하지 않는다. '
        '무릎 폭을 드론 부품에 옮긴 표 역시 진단용 지표이며 드론 전체의 유효성 인증선은 아니다.',
        '시험한 얇은 띠에서 PO와 해당 기준 계산의 편파별 차이가 컸다는 관측과 격자 수렴 결과.',
        '얇은 띠 대조에서는 편파에 따라 오차 방향이 달랐다. 드론 전체 RCS와 탐지거리 오차의 방향은 아직 정하지 못했다.',
        [('src/build_part04_kernel.py','보수적(비관적)'),
         ('src/build_part04_kernel.py','po_validity_knee')])

    add('형상 증거와 오차의 동행을 원인 확정으로 적는다','03_anchor',45,'갈린 축은 대역도',
        '같은 셀 아래에는 소표본의 사전 지정 분할을 가설 생성으로 읽으라는 단서와 미완료·구형 메쉬·재계산 대기 단서가 있다. '
        '그런데 첫 문장은 대역·전기적 크기·기체 크기를 배제하고 형상 증거가 원인이라고 확정한다. '
        '형상 제약만 바꾼 대조 없이 각 기체의 다른 속성을 제외할 수 없다.',
        '그 원장 세대에서 사전 지정한 그룹 사이의 레벨오차 차이와 NOT_VALIDATED 판정.',
        '해당 원장에서는 형상 증거가 있는 그룹의 레벨오차가 작았다. 원인 해석은 가설이며 구형·미완료 행을 갱신한 대조가 필요하다.',
        [('src/build_part05_anchor.py','갈린 축은 형상 증거의 유무다')])

    add('비직교 성분의 잔여 배분을 수치 잡음의 확정 하한으로 읽는다','04_elevation-coverage',67,'남은 변조의',
        '원장은 성분들이 직교하지 않아 분해가 어림이라고 명시한다. 코드도 총 AC 비에서 서로 다른 대조의 근접장·가림 비를 빼고 음수를 잘라 잔여를 만든다. '
        '이 잔여에는 교차항과 대조 조건의 차이가 포함될 수 있다. 가림 항을 상한으로 놓았다는 이유만으로 물리적 격자 잡음 전력의 엄밀한 하한이 증명되지는 않는다. '
        '재현기와 원본의 높은 상관도 같은 성분 비율을 보장하지 않는다.',
        '격자·거리·가림 대조에서 변조가 바뀐 관측과 선언된 배분 규약 아래의 어림값.',
        '비직교 성분을 잔여 방식으로 배분하면 격자 관련 성분이 크게 추정된다. 이 비율은 교차항을 분리한 인과적 전력 분해나 엄밀한 하한은 아니다.',
        [('benchmark/refute_nadir_mechanism_final.py','p_grid = max(p_tot - p_nf - p_occ'),
         ('src/build_part12_elevation.py','남은 변조의')])

    add('순시 도플러 최대값을 넘는 FFT 성분을 불가능한 신호로 부른다','04_elevation-coverage',56,'날개가 낼 수 없는 대역',
        '같은 절 앞부분은 f_tip을 순시 도플러 최대값으로 정의하고 창 누설·가림·위상변조 꼬리와 원인 귀속을 구분한다. '
        '뒤에서는 날개가 낼 수 없는 대역이므로 엔진이 만들었다고 단정한다. 순시 위상 변화율의 최대값은 유한 시간 신호의 엄밀한 주파수 지지구간이 아니다. '
        '정수 주기·무창의 순수 위상변조 반례에서도 그 값 위에 주파수 성분이 있다. 반례는 실제 드론의 큰 꼬리가 물리적이라는 증명이 아니다.',
        '정의한 f_tip 기준 밖에 놓인 전력 몫과 격자를 조일 때 그 몫이 달라진 관측.',
        '정의한 순시 도플러 범위 밖에 큰 스펙트럼 성분이 관측된다. 진폭변조·위상변조 꼬리·창 효과와 후보 유실을 대조한 뒤 원인을 판단한다.',
        [('src/build_part12_elevation.py','날개가 낼 수 없는 대역')])

    add('여섯 물리 설정의 공통 조건을 실제와 다르게 요약했다','05_engine-physics',21,'여섯 판 모두',
        '리포트는 여섯 판 모두 굴절을 끈 같은 반사 깊이라고 적지만, 표와 생성 코드에는 굴절을 켠 판과 더 깊은 다중반사 판이 있다. '
        '모서리회절만 켠 행도 회절 활성 조건이 충족되지 않아 독립적인 물리 효과 대조가 아니다. '
        '그 점은 뒤 본문에서 항등식이라고 바로잡았지만 절 첫 결과 목록은 독립 스위치처럼 남아 있다.',
        '기준과 회절만 켠 특정 두 판의 레벨 차이 및 각 행의 기록된 설정.',
        '기준과 회절만 켠 판은 다른 조건을 맞췄다. 나머지 행은 표에 기록한 굴절·깊이 조건을 따르며 비활성 모서리회절 행은 효과 크기로 해석하지 않는다.',
        [('src/build_part13_engine_physics.py','여섯 판 모두'),
         ('benchmark/diag_physics_paths.py','CASES =')],status='현재 본문과 실험 설정의 직접 불일치')

    add('통제된 ECA 결과를 정적 클러터 일반의 무해성으로 확대한다','08_detector',17,'죽은 파라미터다',
        '근거 생성기는 기준신호의 지연 조합으로 클러터를 만들고 그 기저에 사영하는 통제 실험이다. '
        '생성기는 geometry.py의 통제 기하를 사용한다. 같은 절의 다중경로 소거 열은 그 기하 때문에 이미 인용을 내렸는데 이 결론은 남아 있다. '
        '기준신호 불일치·탭 밖 지연·채널 변화·유한 동적범위를 연 실외 일반 결과로 옮길 수 없다.',
        '그 기준신호·지연 기저·수치 정밀도·기하에서 클러터 진폭을 바꿔도 SCR이 거의 같았다는 통제 결과.',
        '검사한 통제 모델에서는 클러터 세기 변화에 SCR이 둔감했다. 실제 기준채널과 실외 지연·변동 조건에서 정적 클러터의 영향을 별도로 확인한다.',
        [('benchmark/verify_eca.py','def sec5_clutter_dead'),
         ('benchmark/geometry.py','from bistatic_scene import'),
         ('src/build_part09_detector.py','정적 클러터는 ECA 뒤에서')])

    add('이상적 ADC 양자화 SNR을 직접파 제거의 천장으로 부른다','10_2_robustness',29,'ADC 동적범위',
        f"원장의 {c['ideal_adc_snr_db']:.2f} dB는 코드의 비트 수 공식으로 재현된다. "
        '이 공식은 이상적 ADC의 풀스케일 정현파와 양자화 잡음을 비교하는 조건부 SNR이다. '
        '장비의 실측 유효 비트 수·왜곡·포화 여유·입력 파형·처리 대역폭을 반영한 직접파 소거 깊이의 보편적 상한이 아니다. '
        '리포트가 실제 바닥은 계측해야 한다고 단서를 붙인 것은 적절하지만 제목과 표의 천장 표현은 남는다.',
        '공칭 비트 수와 그 공식으로 얻은 이상적 양자화 SNR 계산값.',
        '공칭 비트 수로 이상적 양자화 SNR을 계산했다. 실장비의 소거 한계는 입력 여유·유효 비트 수·대역폭·왜곡과 수신 처리를 포함해 측정해야 한다.',
        [('src/experiment_x410.py','return 6.0206 * self.adc_bits'),
         ('src/build_part11_measurement.py','직접파 제거의 천장')])

    add('선언한 모델 차이 규모를 현실 오차 봉투라고 부른다','10_results',26,'현실 봉투',
        f"원장의 봉투 {c['realistic_span_db']:.3f} dB는 원 PO 최대 기울기와 문헌 앵커 기울기의 차이에 밴드 폭을 곱한 값이다. "
        '실제 기체군의 오차 분포나 신뢰구간을 계측해 정한 범위가 아니다. '
        '그 안에서 순위가 뒤집힌다는 결과는 선택한 민감도 시나리오의 결과이며 현실에서 그 확률로 뒤집힌다는 뜻은 아니다. 그림에 남아 있던 «모든 문턱이 범위 안»이라는 요약도 일부 막대가 기준선 밖에 있어 삭제했다.',
        '선언한 공통·차분 오차 시나리오에서 재계산한 순위와 뒤집힘 문턱.',
        '모델과 앵커의 기울기 차이에서 정한 민감도 범위 안에 뒤집힘 문턱이 놓인다. 이 범위는 실측 오차 분포나 신뢰구간이 아니다.',
        [('benchmark/sigma_sensitivity.py','REALISTIC_SPAN_DB ='),
         ('src/build_part10_results.py','현실 봉투 안이다')])

    add('평균 RCS를 넣은 순위를 자세 평균 탐지 성능처럼 읽기 쉽다','10_results',20,'자세를 평균하면',
        '계산은 고도별 방위 RCS를 선형 평균한 뒤 그 평균을 거리 솔버에 넣는다. '
        '각 자세의 검출확률이나 검출거리를 계산해서 평균한 것이 아니다. 비선형 문턱을 거치므로 평균 RCS의 성능과 자세별 성능의 평균은 일반적으로 다르다. '
        '공통 σ 오프셋에서 순위가 유지된다는 사실도 차분 오차·관측 조건을 넘는 실측 순위 검증은 아니다.',
        '해당 방위 선형평균 RCS를 대입한 모델에서 얻은 밴드 순위.',
        '방위 선형평균 RCS를 대입한 거리 모델에서는 밴드 순위가 모였다. 자세별 검출확률 평균과 커버리지는 별도 지표다.',
        [('benchmark/sigma_sensitivity.py','rows = sm.mean(axis=1)'),
         ('src/build_part05_anchor.py','논문이 절대 σ 에 기대는 곳은 여기서 끝난다')])

    preserved = [
        dict(title='해석 PO와 Mie의 검증 범위를 나눈 본문',
             quote=quote('02_kernel',37,'수치 수렴의 과녁은 해석 PO'),
             note='구에서의 구현 오차와 모델 간극을 구분한 본문은 유지한다. 구 결과를 드론 전체 정확도로 확대하는 문장만 제한한다.'),
        dict(title='CFAR의 잡음 맵 대조와 전체 사슬의 미해결 부분',
             quote=quote('08_detector',35,'원인 지목은 여기서 멈춘다'),
             note='현재 본문은 대조가 지나지 않은 DPI+ECA 구간을 구분한다. 기존 감사의 과잉 귀속 지적을 그대로 현재 결함으로 되풀이하지 않는다.'),
        dict(title='같은 원본을 다른 분석 대역으로 읽은 비교',
             quote=quote('04_elevation-coverage',24,'대역을 어디에 놓았는가'),
             note='분석 대역 선택에 따른 수치 차이로 읽는 것은 적절하다. 그 수를 탐지거리나 분류 정확도 향상으로 옮기지 않는다.'),
        dict(title='함대 대조의 NOT_VALIDATED 결과',
             quote=quote('03_anchor',44,'판정은 **NOT_VALIDATED'),
             note='이 원장 세대의 사전 지정 판정 결과는 유지한다. 실패 원인이 형상 증거로 확정됐다는 해석과 분리한다.')]
    external = [
        dict(url='https://kb.ettus.com/X410', title='Ettus X410 공식 사양',
             use='공칭 ADC 비트 수의 출처. 소거 깊이의 보장으로 사용하지 않는다.'),
        dict(url='https://www.analog.com/en/resources/technical-articles/defining-and-testing-dynamic-parameters-in-highspeed-adcs-part-1.html',
             title='Analog Devices: ADC 동적 파라미터 정의',
             use='이상적 SNR, 실제 ENOB, 처리 대역에 따른 이득의 구분.')]
    out = dict(_meta=dict(generator='benchmark/review_completed_interpretations_0908.py',
                         scope='Current completed-experiment interpretations in the referenced notebooks; '
                               'not an exhaustive audit of every repository artifact.',
                         source_sha256=SOURCES, baseline_revision=BASELINE_REV),
               checks=c, findings=findings, preserved=preserved, external_sources=external,
               implementation=current_status(findings))
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    if '--check-reports' in sys.argv:
        out['document_checks'] = {}
        for gate in ('check_stale_titles', 'check_retracted', 'check_row_pointers', 'check_new_file_rules', 'check_report_links'):
            proc = subprocess.run([sys.executable, str(ROOT/'benchmark'/f'{gate}.py')], cwd=ROOT,
                env=dict(os.environ, CUDA_VISIBLE_DEVICES='', PYTHONPATH='src:benchmark'),
                capture_output=True, text=True)
            out['document_checks'][gate] = dict(exit_code=proc.returncode, output=proc.stdout+proc.stderr)
        out['preexisting_provenance_issues'] = {}
        for name in ('deck_audit_0908', 'jaccard_0914_0908', 'read_0918A_0909'):
            path = 'outputs/'+name+'.json'
            out['preexisting_provenance_issues'][path] = (read(path) == baseline(path))
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    render(out)
    review_notebook(out)
    print(f'{len(findings)} findings, {len(preserved)} bounded interpretations retained')
    print(MEMO.relative_to(ROOT))


def render(out):
    fs = out['findings']
    notebooks = sorted({r['quote']['path'] for r in fs+out['preserved']})
    lines = ['# 완료 실험 결과 해석 검토 메모', '',
             f"수정 전 기준 커밋의 리포트 {len(notebooks)}개에서 결과 해석 {len(fs)}건을 구체적으로 짚었다. "
             '이는 오류 개수나 전체 실험의 실패 개수가 아니다. 숫자가 맞아도 관측·예측·원인 귀속·현실 적용 범위가 다른 항목을 구분했다.', '',
             '**범위:** '+', '.join(Path(p).stem for p in notebooks)+'. 제목뿐 아니라 해당 결과 본문·단서·원장 키·생성 코드를 대조했다. '
             '전체 노트북의 모든 셀, 선행연구 전편, 발표 자료를 전수검토한 것은 아니다.', '',
             '**검증 수준:** 기존 원장의 수치와 계산식을 재계산하고 작은 수학적 반례를 실행했다. GPU 원본 재실험과 새로운 외부 계측은 수행하지 않았다. '
             '원문은 원장에 명시한 수정 전 기준 커밋의 셀에서 자동 추출했으며 각주의 원래 번호를 보존했다. 셀 번호는 파일 내부의 영 기준 번호다.', '',
             '[재현 코드](../benchmark/review_completed_interpretations_0908.py) · '
             '[검산·인용 원장](../outputs/completed_interpretations_review_0908.json) · '
             '[실외 설계 검토 메모](OUTDOOR_DESIGN_REVIEW_0908.md)', '',
             '```bash', 'cd /workspace/sionna',
             "CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 /workspace/.venvs/py312/bin/python benchmark/review_completed_interpretations_0908.py --check-reports", '```', '']
    for i,r in enumerate(fs,1):
        q=r['quote']
        lines += [f"## {i}. {r['title']}", '', f"**수정 전 판정:** {r['status']}", '',
                  f"**현재 본편 반영:** {'확인' if r['current_revision']['applied'] else '대기'} — `{r['current_revision']['marker']}`", '',
                  f"**원문:** [{Path(q['path']).name}](../{q['path']}) · 셀 {q['cell_zero_based']}", '',
                  '> '+q['text'], '', '**왜 오해가 생기나:** '+r['issue'], '',
                  '**남는 결과:** '+r['retained'], '', '**권장 문장:** '+r['replacement'], '',
                  '**생성 코드:** '+' · '.join(f"[{s['path']}:{s['line']}](../{s['path']}#L{s['line']})" for s in r['sources']), '']
    lines += ['## 현재 한정이 적절해 유지할 해석', '']
    for r in out['preserved']:
        q=r['quote']
        lines += [f"- **{r['title']}** — {r['note']} "
                  f"[{Path(q['path']).name}](../{q['path']}) · 셀 {q['cell_zero_based']}."]
    lines += ['', '## 외부 정의 확인', '']
    for s in out['external_sources']:
        lines += [f"- [{s['title']}]({s['url']}) — {s['use']}"]
    lines += ['', '## 적용 범위와 남은 작업', '',
              '취소한 문헌 비열람 라벨, 거리 키와 가드 조건, 예산 외삽과 물리 설정의 요약을 빌더에서 수정했다. '
              '위상 검증·오차 방향·주파수 상한·비직교 분해·ADC·클러터의 표현도 본편에 반영했다. '
              '원래 실험 원장의 판정 산문과 구형 문헌 대조 기록은 역사적 기록으로 남아 있다. 이 메모의 한정을 함께 읽는다. 전체 과거 원장의 산문을 모두 다시 발행한 것은 아니다.', '',
              '이 메모의 인용문은 수정 전 기록이다. 각 항목의 현재 반영 표시는 생성된 본편 문구를 확인한 결과다. 문서 검사에서는 제목·철회·행 각주·링크를 확인하며, 기존 원장 일부의 생성 경로 누락은 별도 미해결 항목이다. 실행 중 GPU 큐는 이번 검토 범위에서 제외했다.', '']
    if 'document_checks' in out:
        lines += ['## 문서 검사 결과', '', '| 검사 | 종료 코드 |', '|---|---:|']
        lines += [f"| `{k}` | {v['exit_code']} |" for k,v in out['document_checks'].items()]
        lines += ['', '새 파일 규칙에서 남은 생성 경로 문제는 다음 기존 원장이다. 기준 커밋과 내용이 같은지 함께 확인했다.', '']
        lines += [f"- `{k}` — 수정 전과 동일: {v}" for k,v in out['preexisting_provenance_issues'].items()]
        lines += ['', '추가로 대역 그림 재현 명령에 누락된 반사 깊이 비교 팔을 넣었다. 재생성한 두 대역 원장의 수치 행이 기준 커밋과 일치함을 검산 원장에 기록했다.', '']
    MEMO.write_text('\n'.join(lines))


if __name__ == '__main__':
    main()
