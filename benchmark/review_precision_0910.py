"""Rebuild the precision review from existing shards; never run a ray solver."""
from __future__ import annotations
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['OPENBLAS_NUM_THREADS'] = '1'
if hasattr(os, 'sched_setaffinity'):
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
import ast
import hashlib
import json
import math
import re
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SHARDS = ROOT/'outputs/elev_sweep_shards'
OUT = ROOT/'outputs/precision_review_0910.json'
MEMO = ROOT/'docs/PRECISION_REVIEW_0910.md'
NB = ROOT/'docs/PRECISION_REVIEW_0910.ipynb'
SOLVER = Path(sys.prefix)/'lib/python3.12/site-packages/sionna/rt'
PLOT = ROOT.parent/'team_meeting/teammeeting_0910/bake_outdoor.py'
HASHES = {}
CACHE = {}


def read(path):
    p = Path(path)
    if not p.is_absolute(): p = ROOT/p
    raw = p.read_bytes()
    key = str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
    HASHES[key] = hashlib.sha256(raw).hexdigest()
    return raw.decode()


def js(path): return json.loads(read(path))


def source(path, needle):
    """살아 있는 grep 으로 원문을 뜬다. ⛔없으면 «고쳐졌다» 로 적는다 — 죽지 않는다.

    ⛔2026-09-10: 이 검토가 지적한 문구 셋이 실제로 **고쳐지자** next() 가
      StopIteration 으로 죽어 생성기 전체가 못 돌았다(이 파일이 굽는 .md·.ipynb·
      .json 이 낡은 판으로 굳었다). 바늘을 새 글자로 갈면 «검토가 겨눈 옛 글자» 를
      가리키지 못하므로, 바늘은 그대로 두고 **못 찾았다는 사실**을 남긴다.
    """
    lines = read(path).splitlines()
    line = next((i for i, s in enumerate(lines, 1) if needle in s), None)
    if line is None:
        return dict(path=str(path), line=None, quote=needle, fixed=True)
    full = lines[line-1]
    start = max(0, full.index(needle)-60)
    return dict(path=str(path), line=line, quote=full[start:start+500].strip(),
                fixed=False)


def pure_functions(path, names, globals_):
    tree = ast.parse(read(path))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert len(nodes) == len(names)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), globals_)
    return globals_


def load(files):
    paths = [SHARDS/Path(f).name for f in files]
    key = tuple(str(p) for p in paths)
    if key in CACHE: return CACHE[key]
    idx, fields, prfs, declared_n = [], [], [], []
    for p in paths:
        HASHES[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
        with np.load(p, allow_pickle=False) as z:
            idx.append(z['idx']); fields.append(z['E'])
            prfs.append(float(z['meta'][4])); declared_n.append(int(z['meta'][3]))
            cfg = z['cfg']
            spp = int(re.search(r'sionna_p(\d+)_', p.name).group(1))
            depth = int(re.search(r'_d(\d+)_el', p.name).group(1))
            assert float(cfg[0]) == 15 and int(cfg[1]) == depth
            assert int(cfg[2]) == spp and int(z['meta'][6]) == spp
    i, e = np.concatenate(idx), np.concatenate(fields)
    order = np.argsort(i)
    assert len(set(prfs)) == len(set(declared_n)) == 1
    assert np.array_equal(i[order], np.arange(declared_n[0])), key
    assert np.isfinite(e).all()
    result = dict(E=e[order], prf=prfs[0], files=[p.name for p in paths], n=len(e))
    CACHE[key] = result
    return result


def load_stem(stem, el):
    files = sorted(SHARDS.glob(f'{stem}_el{el:+g}_*.npz'))
    assert files, stem
    return load(files)


def flags(F, O):
    assert F['prf'] == O['prf'] and F['n'] == O['n']
    d = O['E']-F['E']
    center = complex(np.median(d.real), np.median(d.imag))
    return np.abs(d-center) > .5*abs(center)


def overlap(a, b):
    intersection = int((a & b).sum())
    union = int((a | b).sum())
    return dict(n_a=int(a.sum()), n_b=int(b.sum()), intersection=intersection,
                union=union, jaccard=intersection/union,
                only_a=int((a & ~b).sum()), only_b=int((b & ~a).sum()))


def expected_jaccard(N, a, b):
    # Exact expectation under independent uniform fixed-size subset selection.
    prob = math.exp(sum(math.log((N-a-j)/(N-j)) for j in range(b)))
    terms, mass = [], 0.
    for k in range(min(a, b)+1):
        terms.append(prob*k/(a+b-k)); mass += prob
        prob *= (a-k)*(b-k)/((k+1)*(N-a-b+k+1))
    assert abs(mass-1) < 1e-10
    den = math.comb(N,b)
    independent = sum((math.comb(a,k)*math.comb(N-a,b-k)/den)*k/(a+b-k)
                      for k in range(min(a,b)+1))
    assert math.isclose(sum(terms), independent, rel_tol=1e-12, abs_tol=1e-14)
    return sum(terms)


def calculate():
    b = js('outputs/read_0918B_0909.json')
    old = js('outputs/read_0914_0908.json')
    B, arrays, phase_checks, notch_checks = {}, {}, {}, {}
    for name, row in b['cells'].items():
        F, O = load(row['files_free']), load(row['files_outdoor'])
        flag = flags(F, O)
        assert int(flag.sum()) == row['n_static_changed'], name
        B[name] = flag; arrays[name] = (F, O)
        d = O['E']-F['E']
        angles = np.linspace(0, 2*np.pi, 37)[:-1]
        changed = []
        for angle in angles:
            rotated = d*np.exp(1j*angle)
            center = complex(np.median(rotated.real), np.median(rotated.imag))
            f = np.abs(rotated-center) > .5*abs(center)
            changed.append(int((f != flag).sum()))
        phase_checks[name] = dict(n_angles=len(angles), max_changed=max(changed))
        X = np.fft.fft(F['E']-F['E'].mean())
        freq = np.fft.fftfreq(F['n'], 1/F['prf'])
        energy = abs(X)**2
        remove = (abs(freq) <= 100) & (freq != 0)
        notch_checks[name] = dict(prf=F['prf'], n=F['n'], fcut=100,
            removed_free_ac_percent=float(100*energy[remove].sum()/energy.sum()))
    A = {}
    for name, row in old['cells'].items():
        if name.startswith('기준/') or name.startswith('D 크기/') or '깊이 3' in name:
            F = load_stem(row['stem_free'], old['_meta']['el_deg'])
            O = load_stem(row['stem_outdoor'], old['_meta']['el_deg'])
            A[name] = flags(F, O)
            assert int(A[name].sum()) == row['n_static_changed']
    base_a = next(k for k in A if k.startswith('기준/'))
    body = {}
    for name in A:
        if name.startswith('D 크기/'):
            key = base_a+' ∩ '+name
            body[key] = overlap(A[base_a], A[name])
            assert round(body[key]['jaccard'], 4) == old['cross_cell_overlap'][key]['jaccard']
    wrong_key = 'C 깊이/깊이 3 ∩ D 크기/동체 ×0.5'
    wrong_pair = overlap(A['C 깊이/깊이 3'], A['D 크기/동체 ×0.5'])
    assert round(wrong_pair['jaccard'],4) == old['cross_cell_overlap'][wrong_key]['jaccard']
    base_b = next(k for k in B if k.startswith('배율 없음'))
    assert np.array_equal(A[base_a], B[base_b])
    budget = {}
    for name in B:
        if name.startswith('광선 '):
            r = overlap(B[base_b], B[name]); N=len(B[name])
            r.update(expected_intersection=r['n_a']*r['n_b']/N,
                     expected_jaccard=expected_jaccard(N,r['n_a'],r['n_b']), n=N)
            budget[name] = r
    # Current geometry implementation, with zero translation/rotation; no RT import.
    sys.path.insert(0, str(ROOT/'src'))
    read('src/articulated_fast.py'); read('src/drones.py'); read('src/geom.py')
    from articulated_fast import FastPoser
    from drones import DRONES
    small = FastPoser(DRONES['matrice4e'])
    frame = FastPoser(DRONES['matrice4e'], frame_scale=1.5)
    both = FastPoser(DRONES['matrice4e'], frame_scale=1.5, prop_scale=1.5)
    stop = small._rotor_slices[0][0]
    frame_scaled = np.allclose(frame.v[:stop], 1.5*small.v[:stop], rtol=0, atol=1e-12)
    hub_scaled = all(np.allclose(a[:3,3]*1.5,b_[:3,3]) for a,b_ in zip(small._rotor_const,frame._rotor_const))
    prop_same = all(np.array_equal(a,b_) for a,b_ in zip(small._rotor_local,frame._rotor_local))
    props_scaled = all(np.allclose(a[:,:3]*1.5,b_[:,:3]) for a,b_ in zip(small._rotor_local,both._rotor_local))
    assert frame_scaled and hub_scaled and prop_same and props_scaled
    geometry = dict(frame_scale=1.5, frame_vertices_scaled=bool(frame_scaled),
        hubs_scaled=bool(hub_scaled), local_prop_unchanged=bool(prop_same),
        paired_scales_expand_local_props=bool(props_scaled),
        scope='Current coordinate transforms at zero body translation/rotation; no historical mesh or EM validation.')
    # Reproduce the mask used for the corrected street-canyon statement.
    ns = pure_functions(PLOT, ['hampel_mask', 'drop_outliers'], {'np':np})
    notch_ns = pure_functions('benchmark/clutter_parts_ladder_0824.py', ['cs_eca'],
                             {'np':np,'FCUT':100.,'PRF':19700.})
    marked, processing_order = {}, {}
    base_stem = b['cells'][base_b]['stem_free']
    for el in (-30., -60.):
        F=load_stem(base_stem,el)
        O=load_stem(base_stem.replace('_mfix','_envsionna-simple_street_canyon_mfix'),el)
        H=ns['hampel_mask'](abs(O['E'])); G=flags(F,O)
        levels=20*np.log10(abs(O['E'])/np.median(abs(O['E'])))
        marked[str(el)] = dict(n=O['n'], n_marked=int(H.sum()),
            n_above_global_median=int((levels[H]>0).sum()), n_residual_events=int(G.sum()),
            n_common=int((H&G).sum()), median_marked_db=float(np.median(levels[H])),
            min_marked_db=float(levels[H].min()), max_marked_db=float(levels[H].max()),
            reference='Median amplitude of the entire outdoor record, before notch or interpolation.')
        assert marked[str(el)]['n_marked'] == marked[str(el)]['n_above_global_median']
        notch_ns['PRF'] = O['prf']
        notch = notch_ns['cs_eca']
        first_fill = notch(ns['drop_outliers'](O['E'])[0])
        notched = notch(O['E'])
        first_notch = ns['drop_outliers'](notched)[0]
        Hn = ns['hampel_mask'](abs(notched))
        processing_order[str(el)] = dict(mask_from_original=int(H.sum()),
            mask_from_notched=int(Hn.sum()), mask_symmetric_difference=int((H!=Hn).sum()),
            output_relative_l2_difference=float(np.linalg.norm(first_fill-first_notch)/np.linalg.norm(first_fill)))
        assert math.isfinite(processing_order[str(el)]['output_relative_l2_difference'])
    return dict(condition=dict(drone='matrice4e', elevation_deg=-60,
        range_m=15, arm='R0D0E0F1', mesh='mfixbatteryi5_blperairframe',
        n=arrays[base_b][0]['n'], prf=arrays[base_b][0]['prf']),
        body_vs_baseline=body, miscited_pair=dict(key=wrong_key,**wrong_pair),
        budget_controls=budget, geometry=geometry, phase_rotation=phase_checks,
        notch_on_free_ac=notch_checks, corrected_marked_positions=marked, processing_order=processing_order,
        validated_unique_shards=len({p for paths in CACHE for p in paths}))


def make_findings(c):
    fs=[]
    def add(title, issue, evidence, replacement, followup, refs):
        fs.append(dict(title=title,issue=issue,evidence=evidence,replacement=replacement,
                       followup=followup,sources=[source(*r) for r in refs]))
    body=list(c['body_vs_baseline'].values()); wrong=c['miscited_pair']
    add('동체 대조의 기준선이 잘못 연결됐다',
        '재개 요약의 동체 대조 값은 깊이도 다른 설정과의 교집합이다. 동체만의 효과로 읽는 기준선과 다르다.',
        "원본 샤드 재계산: 기준 깊이를 유지한 동체 대조는 " + ", ".join(f"{k.split(' ∩ ')[1]} = {v['jaccard']:.4f}" for k,v in c['body_vs_baseline'].items()) + "다. "
        f"인용된 {wrong['jaccard']:.4f}는 {wrong['key']} 값이다. 조건은 checks.condition에 기록했다.",
        '깊이를 고정한 기준선과 각 동체 배율을 따로 비교한다. 동체의 영향 배제는 현재 대조에서 미확정이다.',
        '요약표의 비교 키를 바로잡고 각 배율의 공통·추가·소실 사건을 함께 표시한다.',
        [('work/sweep_0904/RESUME_0909.md','| 동체만'),
         ('outputs/read_0914_0908.json',wrong['key'])])
    q=next(iter(c['budget_controls'].values()))
    add('자카드 옆에 기대 교집합 개수를 같은 척도로 배치했다',
        '재개 요약의 우연이면 열은 기대 교집합 개수다. 자카드는 무차원 비율이므로 이 두 수를 나란히 같은 기준처럼 비교하면 안 된다.',
        f"첫 광선 대조에서 관측 자카드는 {q['jaccard']:.6f}, 균일·독립 고정 크기 집합 모형의 기대 교집합은 "
        f"{q['expected_intersection']:.6f}개다. 같은 모형의 기대 자카드를 정확 합산하면 {q['expected_jaccard']:.6f}다. "
        '이는 단위 혼동 확인용 모형 계산이며 로터 위상 구조를 반영한 유의성 검정은 아니다.',
        '관측 교집합 개수와 기대 교집합 개수를 비교하고 자카드는 별도 열로 표시한다. 기대 자카드를 쓸 때는 귀무모형을 함께 명시한다.',
        '표 머리글에 개수와 비율을 명시하고 기대값과 관측값을 같은 척도로 대응시킨다.',
        [('work/sweep_0904/RESUME_0909.md','| 무엇을 바꿨나 | 자카드'),
         ('benchmark/read_0918B_0909.py','"expected_if_unrelated":')])
    nulls=[r['jaccard'] for r in c['budget_controls'].values()]
    add('광선 예산 민감도 대조를 독립 재표본화 널 구간으로 읽는다',
        '초기 광선은 결정적인 피보나치 격자다. 광선 수를 바꾸면 격자의 한 좌표와 표본 수가 함께 바뀌고, 솔버 씨앗은 고정된다. 다른 초기 배치를 시험한 사실과 같은 예산의 독립 반복이라는 실험 지위는 구분해야 한다. 두 설정의 범위 자체가 신뢰구간이나 동등성 구간은 아니다.',
        f"광선 예산 대조의 자카드는 {min(nulls):.4f}~{max(nulls):.4f}다. "
        f"문제의 다른 짝 값 {wrong['jaccard']:.4f}도 이 수치 범위 밖이다. y=ns/(num_points-1), x의 격자식 및 seed 고정을 설치본·하네스에서 확인했다.",
        '광선 예산 변경에 따른 사건 집합의 민감도를 확인했다. 동일 예산에서의 독립 반복 분포와 동등성 판정은 후속 실험 대상이다.',
        '같은 예산의 씨앗 반복과 예산 변경 대조를 분리한다. 초기 광선 배치의 무작위화가 필요한 가설이면 별도 설계하고 기록한다.',
        [('work/sweep_0904/RESUME_0909.md','동체(0.86)는 널 안이다'),
         ('benchmark/read_0918B_0909.py','표본을 통째로 다시 뽑는 널은'),
         (SOLVER/'utils/ray_tracing.py','y = ns/(num_points-1)'),
         ('benchmark/elevation_sweep_md.py','max_num_paths_per_src=RP.MAX_PATHS, seed=1')])
    add('프레임 배율은 허브 위치만 바꾸는 대조가 아니다',
        '프레임 배율은 정적 프레임 정점 전체와 로터 허브 위치를 함께 바꾼다. 프롭 로컬 형상은 고정되지만 동체·팔·모터 등 정적 형상의 변화가 섞인다. 프레임 대조를 허브만의 원인 근거로 쓰면 범위를 넘는다.',
        f"현재 기하 생성기를 CPU에서 실행해 프레임 배율 {c['geometry']['frame_scale']:g}에서 "
        '정적 프레임 정점·허브 위치가 함께 확대되고 프롭 로컬 정점이 유지됨을 확인했다. 프롭과 프레임을 같은 배율로 확대한 조합은 코드 설명대로 기하 전체 확대에 해당한다.',
        '프레임과 허브 위치를 함께 바꾼 대조에서 사건 집합이 변했다. 허브 위치만의 기여는 미분리다.',
        '허브만 움직이는 대조가 필요한지 먼저 정하고, 정적 형상과 로터 배치를 분리한 좌표·간섭 검사를 설계한다.',
        [('src/articulated_fast.py','_fv = np.asarray(frame.v, float) * self.frame_scale'),
         ('src/articulated_fast.py','np.asarray(rot["center"], float) * self.frame_scale'),
         ('work/sweep_0904/RESUME_0909.md','프롭·허브 기하가 정한다')])
    vals=[r['removed_free_ac_percent'] for r in c['notch_on_free_ac'].values()]
    add('날개 박자보다 낮은 노치라는 이유로 신호 불변을 주장한다',
        '노치는 정지 클러터의 출처를 식별하지 않고 지정 대역의 복소 성분을 지운다. 날개 박자 주파수가 노치 밖에 있다는 사실만으로 드론 신호 전체가 보존되지는 않는다.',
        f"검사한 자유공간 짝의 평균 제거 후 AC 에너지 중 노치 대역에 있는 비율은 {min(vals):.6f}~{max(vals):.6f}%다. "
        '이 비율은 작으며 관측 무늬가 무효라는 뜻은 아니다. 계산된 자유공간 AC에는 수치 성분도 포함될 수 있어 실물 신호 손실률로 바꾸지 않는다.',
        '저주파 대역을 제거했으며 자유공간 짝에도 같은 처리를 적용해 비교한다. 박자 주파수 보존과 전체 복소 신호 보존을 구분한다.',
        '처리 전후 AC 대역 에너지를 기록하고 스펙트럼 비교의 자유공간 기준에도 동일 노치를 적용한 결과를 함께 본다.',
        [('benchmark/clutter_parts_ladder_0824.py','FCUT = 100.0'),
         ('benchmark/clutter_parts_ladder_0824.py','신호를 안 건드린다'),
         ('benchmark/clutter_parts_ladder_0824.py','X[np.abs(fr) <= fcut] = 0.0')])
    add('같은 자세를 보간해도 노치와 보간의 순서가 결과를 바꾼다',
        '그림은 노치 전후를 순서대로 보여주지만 마지막 결과는 원본에서 이상치를 찾고 보간한 뒤 노치를 적용한 값이다. 노치 결과의 줄을 찾아 직접 제거한 연산으로 설명하면 마스크 입력과 적용 순서가 달라진다.',
        '생성기의 실제 배열은 F, O, cs_eca(O), cs_eca(Of)이며 Of는 원본 O에서 검출·보간된다. '
        + ' '.join(f"앙각 {el}°에서 원본 검출 마스크 {v['mask_from_original']}개, 노치 후 검출 마스크 {v['mask_from_notched']}개이며 두 마스크의 대칭차는 {v['mask_symmetric_difference']}개다. "
                   f"출력 상대 L2 차이는 {v['output_relative_l2_difference']:.6g}다."
                   for el,v in c['processing_order'].items())
        + ' 두 앙각에서 선택 마스크는 같았지만 출력은 달랐다. 상대 L2의 분모는 보간 후 노치를 적용한 출력의 L2다. 이는 실제 두 함수의 순서를 교환한 CPU 재계산이며 어느 처리가 실제 신호에 더 정확한지의 판정은 아니다.',
        '원본 진폭에서 이상치를 검출해 복소 전계를 보간한 뒤 노치를 적용했다. 그림은 처리 순서와 비교 결과를 함께 설명한다.',
        '마스크가 참조한 입력과 보간·노치 순서를 파이프라인 기록에 명시한다.',
        [(PLOT,'bad = hampel_mask(np.abs(E), win, k)'),
         (PLOT,'dat.append([F, O, cs_eca(O), cs_eca(Of)])')])
    add('표본 수가 가중치에 들어간다는 사실만으로 예산 대조를 부정하면 과하다',
        '전달된 검증문은 표본 수가 초기 입체각에 들어간다는 사실을 예산만 바꾸는 실험이 아니라는 근거로 쓴다. 표본 수에 따른 정규화는 수치 적분에서 정상적인 구성이다. 그것만으로 물리 조건이 달라졌다거나 예산 대조가 부당하다고 결론 낼 수 없다.',
        '설치 전계 계산의 표본 수·선택 확률 보정은 확인했다. 일반적인 중요도 표본화 평균 sum(f(X)/q(X))/N은 N에 따라 항의 가중치가 바뀌어도 가정된 기대 적분값을 유지한다. 이 항등식은 현재 솔버 전체의 불편성을 증명하는 용도로 쓰지 않는다.',
        '표본 수 변경은 추정량의 정규화와 표본 배치를 함께 바꾼다. 후보 누락·상한·편향·분산을 따로 확인해 예산 대조를 해석한다.',
        '가중치를 임의로 고정하는 대조를 해법으로 삼기 전에 추정 대상과 정규화 식을 확인한다. 경로 수 맞춤 외삽의 한정은 유지한다.',
        [(SOLVER/'path_solvers/field_calculator.py','solid_angle = dr.full'),
         (SOLVER/'path_solvers/field_calculator.py','solid_angle[active] *= dr.rcp(probs)'),
         ('work/wf/verify_critique_0909_result.json','표본 수는 확산 ray tube')])
    return fs


def render(out):
    j=str(OUT.relative_to(ROOT)); c=out['checks']
    lines=['# 시오나 정밀 후속 검토', '',
        '기존 정정 이후의 추가 검토다. 아래 항목은 현재 소스·기존 원장·명시한 샤드에 한정한다. GPU 재실험과 외부 계측은 수행하지 않았다.', '',
        '**상태:** 수정 제안과 재계산 기록이다. 기존 실험 코드·원장·발표 자료는 변경하지 않았다.', '',
        '[주피터 노트북](PRECISION_REVIEW_0910.ipynb) · [재계산 원장](../outputs/precision_review_0910.json) · [생성기](../benchmark/review_precision_0910.py)', '',
        '```bash','cd /workspace/sionna',"CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_precision_0910.py",'```','',
        '**동체·예산 대조 조건:** '+json.dumps(c['condition'],ensure_ascii=False), '',
        f"원본 샤드 {c['validated_unique_shards']}개에서 인덱스 유일성·완전성·유한 전계·대조 쌍의 표집률을 확인했다. "
        '이 검사는 저장 이전의 누락 경로나 물리적 정확성을 검증한 뜻이 아니다.', '']
    for i,f in enumerate(out['findings']):
        lines += [f"## {i+1}. {f['title']}",'','**문제:** '+f['issue'],'',
                  '**근거와 범위:** '+f['evidence'],'','**권장 표현:** '+f['replacement'],'',
                  '**다음 확인:** '+f['followup'],'','**원문:**','']
        for s in f['sources']:
            p=Path(s['path']); target=str(p) if p.is_absolute() else '../'+str(p)
            if s.get('fixed'):
                lines += [f"- [{p.name}]({target}) — ⭐**이 문구는 그 뒤 고쳐져 "
                          '현재 파일에 없다.** 아래는 검토 당시 원문이다.',
                          '> '+s['quote'],'']
            else:
                lines += [f"- [{p.name}:{s['line']}]({target}#L{s['line']})",
                          '> '+s['quote'],'']
    lines += ['## 이번에 유지한 정정과 드러나지 않은 문제','']
    for el,r in c['corrected_marked_positions'].items():
        lines += [f"- 거리 협곡 앙각 {el}°: 표시 마스크 {r['n_marked']}개 중 {r['n_above_global_median']}개가 "
                  f"원본 실외 기록 전체 진폭 중앙값보다 높았다. 그 집합의 중앙 상승량은 {r['median_marked_db']:.6f} dB다. "
                  f"복소 잔차 문턱 사건은 {r['n_residual_events']}개이며 마스크와의 공통은 {r['n_common']}개다."]
    angles=next(iter(c['phase_rotation'].values()))['n_angles']
    max_changed=max(v['max_changed'] for v in c['phase_rotation'].values())
    lines += [f"- 실험 조건 {len(c['phase_rotation'])}개에 공통 위상 회전 {angles}개를 적용했을 때 사건 판정 변화 최댓값은 "
              f"{max_changed}개였다. 성분별 중앙값의 일반적 회전 불변성까지 증명한 것은 아니며, 이 조건에서 추가 문제로 집계하지 않았다.",
              '- 프롭·프레임을 같은 배율로 바꾸는 조합은 현재 좌표 변환에서 기체 전체 확대에 해당한다. 이 이름 자체를 오류로 지적하지 않았다.',
              '- 그림의 색상 막대는 판별 개별 정규화를 명시한다. 같은 색을 절대 레벨 비교로 읽지 않는다는 기존 한정을 유지한다.',
              '- 로터 씨앗 근거의 부재라는 옛 지적은 재사용하지 않았다. 이번 씨앗 검토는 설치본의 초기 광선 배치와 새 널 정의에 한정한다.', '']
    MEMO.write_text('\n'.join(lines))
    sys.path.insert(0,str(ROOT/'src'))
    from report_style import header,md,next_steps,build_notebook
    blocks=[header(num='정밀 검토',title='추가 대조에서 확인한 기준선과 해석 범위',
        did='기존 샤드와 현재 코드를 대조해 기준선·지표·처리 순서를 검토했다.',
        results=[f"추가 검토 {len(out['findings'])}건에 수정안을 기록했다 ⟨{j} : findings⟩.",
                 f"원본 샤드 {c['validated_unique_shards']}개의 정렬과 입력 조건을 확인했다 ⟨{j} : checks.validated_unique_shards⟩.",
                 f"거리 협곡 표시 집합 {len(c['corrected_marked_positions'])}건의 상승 방향 정정을 재현했다 ⟨{j} : checks.corrected_marked_positions⟩."],
        method=[('검산','저장된 복소 전계와 실제 마스크 함수, 현재 좌표 생성기를 CPU에서 사용'),
                ('범위','원본 GPU 재실험과 외부 계측은 후속 과제이며 수정안은 제안 상태')],
        repro=dict(cmd=["CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_precision_0910.py"],out=[j],runtime='CPU 한 코어의 샤드·소스 검토'))]
    for i,f in enumerate(out['findings']):
        blocks.append(md(f"## {i+1}. {f['title']}",'',f['replacement'],'',
                         f"[원문·재계산·한정](PRECISION_REVIEW_0910.md) ⟨{j} : findings[{i}]⟩"))
    blocks.append(next_steps([
        ('비교표의 기준선 키와 지표 단위를 정정한다','동체 대조와 기대 교집합의 올바른 대응','PRECISION_REVIEW_0910.md'),
        ('예산 민감도와 동일 예산 반복을 분리한다','독립 반복·민감도·동등성의 구분','PRECISION_REVIEW_0910.md')]))
    build_notebook(str(NB),blocks,strict=True)


def main():
    c=calculate(); fs=make_findings(c)
    out=dict(_meta=dict(generator='benchmark/review_precision_0910.py',source_sha256=HASHES,
        scope='Bounded reanalysis of stored shards and current source; no GPU runs or field measurements.'),checks=c,findings=fs)
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    render(out)
    print(f"Wrote {len(fs)} findings and checked {c['validated_unique_shards']} unique shards")


if __name__ == '__main__': main()
