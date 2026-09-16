"""Rebuild a read-only review of the hash/buffer diagnostic and follow-up design.

Run: CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_hash_diagnostic_0916.py
Writes outputs/hash_diagnostic_review_0916.json and docs/HASH_DIAGNOSTIC_REVIEW_0916.ipynb.
No solver run, queue mutation, production edit, or canonical ledger overwrite.
"""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/hash_diagnostic_review_0916.json'
NB=ROOT/'docs/HASH_DIAGNOSTIC_REVIEW_0916.ipynb'
SOURCES={
 'scope':('benchmark/dropout_hash_vs_buffer_0916.py','CANNOT: why a candidate is lost.'),
 'allocation':('benchmark/dropout_hash_vs_buffer_0916.py','class ZerosSpy:'),
 'buffer':('benchmark/dropout_hash_vs_buffer_0916.py','class KnobProbe:'),
 'replay':('benchmark/dropout_hash_vs_buffer_0916.py','n_scored=int(sum(1 for i in idx'),
 'contrast':('benchmark/dropout_hash_vs_buffer_0916.py','n_no_longer_isolated=int(sum(1 for i in iso_idx'),
 'path_ref':('benchmark/dropout_hash_vs_buffer_0916.py','Reference path per chosen isolated pose:'),
 'save':('benchmark/dropout_hash_vs_buffer_0916.py','if ARGS.keep_paths:'),
 'queue':('runners/jobs_0946_cap_antenna.txt','the antenna axis is independent of'),
 'stability':('benchmark/dropout_knobs_0916.py','union = set(map(int, idx))'),
 'pilot':('benchmark/design_isac_waveform_benchmark_0915.py',"'resource_matched'"),
}


def collect():
    os.environ.update(CUDA_VISIBLE_DEVICES='',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    import numpy as np
    src=ROOT/'outputs/dropout_hash_vs_buffer_0916.json';x=json.loads(src.read_text());c=x['cells'][0];meta=c['meta']
    rows={(r['grid_point'],r['pose']):r for r in c['rows']};groups=c['summary']['groups'];grid=x['_meta']['grid'];factor=meta['factor']
    center=complex(*meta['cell_complex_median']);tol=x['_meta']['parameters']['noise_tol']
    def z(r,key='E_recomputed'):return complex(*r[key])
    def iso(g,i):return rows[g,i]['dev_recomputed_over_scale']>factor
    d={'_meta':{'generator':'benchmark/review_hash_diagnostic_0916.py','command':f'{sys.executable} benchmark/review_hash_diagnostic_0916.py',
       'utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
       'scope':'CPU reaggregation of saved simulation records and source/design review; no new solver or RF run.',
       'independent_review':'verify_review independently aggregated diagnostic rows; design_review independently examined class differences and inference scope.'},
       'sources':{},'hashes':{str(src.relative_to(ROOT)):hashlib.sha256(src.read_bytes()).hexdigest()},
       'cell':meta,'grid_count':len(grid),'pose_count':len(meta['selected']['solve_order']),'row_count':len(c['rows']),
       'checkpoint_rows':sum(r['from_checkpoint'] for r in c['rows']),'noise_tol':tol,'grids':[],'checks':{}}
    for key,(path,needle) in SOURCES.items():
        t=(ROOT/path).read_text();matches=[i+1 for i,l in enumerate(t.splitlines()) if needle in l]
        if not matches:raise ValueError((path,needle))
        d['sources'][key]={'path':path,'line':matches[0]};d['hashes'][path]=hashlib.sha256(t.encode()).hexdigest()
    for g in grid:
        name=g['name'];rr=[r for r in c['rows'] if r['grid_point']==name]
        d['grids'].append({'name':name,'buffer':g['buffer_max_num_paths_per_src'],'hash':g['hash_counter_entries_per_source'],
          'rows':len(rr),'recovered_n':len(groups['recovered']),'recovered_isolated':sum(iso(name,i) for i in groups['recovered']),
          'core_isolated':sum(iso(name,i) for i in groups['core']),
          'controls_moved':sum(abs(z(rows[name,i])-z(rows['production',i]))/abs(center)>tol for i in groups['control']),
          'max_candidates':max(r['knobs_read_back']['candidates_stored'] for r in rr),
          'binding_rows':sum(r['knobs_read_back']['buffer_was_binding'] for r in rr),
          'measured_hash_allocations':[r['knobs_read_back']['hash_counter_entries_total_measured'] for r in rr if 'hash_counter_entries_total_measured' in r['knobs_read_back']]})
    missing_refs=[r for r in c['summary']['reference_env_paths'] if not r['present_at_isolated_pose_in_production']]
    d['reference_counts']={'neighbour_comparisons':len(missing_refs),'unique_poses':len({r['pose'] for r in missing_refs})}
    d['replay']={'max_normalized_error':max(r['abs_err_over_abs_cell_median'] for r in c['rows'] if r['grid_point']=='production'),
       'label_mismatches':sum(iso('production',i)!=rows['production',i]['isolated_by_definition'] for i in meta['selected']['solve_order'])}
    eligible=[i for i in meta['selected']['solve_order'] if rows['production',i]['isolated_by_definition'] and iso('production',i)]
    changes=[]
    for i in meta['selected']['solve_order']:
        a,b=rows['hash8',i],rows['both8',i]
        changes.append({'pose':i,'npaths_from':a['n_paths_returned'],'npaths_to':b['n_paths_returned'],
                        'normalized_field_change':abs(z(b)-z(a))/abs(center)})
    contrast=next(v for v in c['summary']['paired_contrasts'] if v['frm']=='hash8' and v['to']=='both8')
    d['buffer_comparison']={'from':'hash8','to':'both8','eligible':len(eligible),
       'ledger_n_no_longer_isolated':contrast['n_no_longer_isolated'],
       'incremental_recoveries':sum(iso('hash8',i) and not iso('both8',i) for i in eligible),
       'incremental_losses':sum(not iso('hash8',i) and iso('both8',i) for i in eligible),
       'changed_path_counts':[r for r in changes if r['npaths_from']!=r['npaths_to']],
       'max_field_change':max(r['normalized_field_change'] for r in changes),
       'above_tolerance_poses':[r['pose'] for r in changes if r['normalized_field_change']>tol]}
    d['core']=[]
    for i in groups['core']:
        r=rows['production',i];prev=rows['production',i-1];nxt=rows['production',i+1]
        delta=z(r)-(z(prev)+z(nxt))/2
        dc={k:complex(*v['sum'])-(complex(*prev['class_sums'][k]['sum'])+complex(*nxt['class_sums'][k]['sum']))/2 for k,v in r['class_sums'].items()}
        d['core'].append({'pose':i,'env_only_paths':r['n_env_only_paths'],'vertices_available':r['vertices_available'],
           'dominant_class_in_local_difference':max(dc,key=lambda k:abs(dc[k])),
           'both_residual_fraction':abs(delta-dc['both'])/abs(delta),'env_delta_abs':abs(dc['env_only']),
           'sum_closure_relative':abs(delta-sum(dc.values()))/abs(delta),
           'interpretation':'Class accounting against neighbour average; not a physical counterfactual or causal/energy fraction.'})
    d['core_summary']={'sampled':len(d['core']),'population':meta['n_core_all'],
        'with_env':sum(r['env_only_paths']>0 for r in d['core']),
        'without_env':sum(r['env_only_paths']==0 for r in d['core']),
        'both_dominant':sum(r['dominant_class_in_local_difference']=='both' for r in d['core'])}
    d['checks']={'complete_grid_rows':len(rows)==len(grid)*d['pose_count'],
       'recovered_counts_match':[r['recovered_isolated'] for r in d['grids']]==[6,1,0,1],
       'nonbinding_completed_rows':all(r['binding_rows']==0 for r in d['grids']),
       'baseline_labels_match':d['replay']['label_mismatches']==0,
       'baseline_error_under_tolerance':d['replay']['max_normalized_error']<tol,
       'buffer_incremental_recovery_zero':d['buffer_comparison']['incremental_recoveries']==0,
       'class_accounting_closes':all(r['sum_closure_relative']<1e-10 for r in d['core'])}
    if not all(d['checks'].values()):raise ValueError(d['checks'])
    d['queue']={'hold':json.loads((ROOT/'runners/GPU_HOLD.json').read_text())['gpus'],'logs':{}}
    for name in ['sup_cap_0945.log','sup_cap_antenna_0946.log']:
        lines=(ROOT/'runners/logs'/name).read_text().splitlines()
        d['queue']['logs'][name.replace('.','_')]=next(l for l in reversed(lines) if '상태 ' in l)
    d['check_count']=len(d['checks'])
    OUT.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');return d


def build(d):
    sys.path.insert(0,str(ROOT/'src'))
    from report_style import header,md,from_json,next_steps,build_notebook
    s=from_json(str(OUT.relative_to(ROOT)))
    def refs(*keys):return '근거: '+' · '.join(f'[{d["sources"][k]["path"]}](../{d["sources"][k]["path"]}) 행 {s.num("sources."+k+".line")}' for k in keys)
    blocks=[header(num='해시 진단 재검토',title='해시 크기 개입의 효과와 남은 경로 진단',
      did='새 진단의 개별 자세 원장을 다시 집계하고 결론·비교 지표·후속 실험의 범위를 검토했다.',
      results=[f"완료된 {s.num('grid_count')}설정·{s.num('pose_count')}자세의 {s.num('row_count')}개 기록을 대조했다.",
       '선택된 회복 자세에서 hash 크기만 늘려 고립 판정과 참조 환경 경로가 회복된 결과를 확인했다.',
       '버퍼 단독 변경의 추가 회복은 없지만 경로 수와 작은 복소장 차이는 남는다.',
       '잔존 자세의 경로 클래스가 갈리므로 단일한 다른 원인으로 묶기 전에 세부 진단이 필요하다.'],
      method=[('재집계','완료 원장 개별 행의 고립 판정·후보 수·복소장·클래스 합 대조'),('범위','저장된 simulation 자료의 CPU 재계산과 설계 검토. 새 GPU·RF 결과는 별도다.')],
      repro={'cmd':f'{sys.executable} benchmark/review_hash_diagnostic_0916.py','out':str(OUT.relative_to(ROOT)),'runtime':'CPU 단일 코어 경량 재계산'}),
      md('## 현황 스냅샷','',f"관측 시각: {s.num('_meta.utc')}",'',
         s.num('queue.logs.sup_cap_0945_log'),'',s.num('queue.logs.sup_cap_antenna_0946_log'),'',
         '각 supervisor의 worker 표시는 같은 전역 집계다. 큐 위치는 발주 진행이며 완료 결과 수와 구분한다. 실행·중단·GPU 보류 설정은 그대로 두었다.'),
      md('## 진단이 실제로 보여 준 것','',
         f"대상은 {s.num('cell.drone')}·지면 장면·el {s.num('cell.el_deg')}°·거리 {s.num('cell.range_m')} m·carrier {s.num('cell.carrier_hz')} Hz·광선 {s.num('cell.spp_used')}·깊이 {s.num('cell.max_depth')}의 선택 자세다.",'',
         '| 설정 | 후보 버퍼 | hash 크기 | 회복 대상 중 고립 자세 | 최대 저장 후보 |','|---|---|---|---|---|',
         *[f"| {r['name']} | {s.num(f'grids[{i}].buffer')} | {s.num(f'grids[{i}].hash')} | {s.num(f'grids[{i}].recovered_isolated')}/{s.num(f'grids[{i}].recovered_n')} | {s.num(f'grids[{i}].max_candidates')} |" for i,r in enumerate(d['grids'])],
         '완료된 설정에서는 후보 버퍼 비포화가 기록됐다. 메모리 부족으로 끝나지 않은 both32는 이 표의 관측 범위 밖이다.'),
      md('## 결론 문구: hash 크기의 개입 효과와 충돌 기전을 구분한다','',
         '버퍼를 고정한 hash 확대가 선택 자세의 회복을 이끌었다. 같은 hash에서 버퍼 확대의 추가 회복 수는 원장에 따로 기록했다. 이는 이전의 결합 cap ladder보다 강한 대조다.', '',
         '권장 문장: «검사한 지면 셀의 선택 자세에서 후보 버퍼 포화 없이 hash 크기 확대가 참조 환경 경로를 회복시켰다. 해시 충돌에 의한 억제는 유력한 설명이며, 탈락한 후보와 회복 경로의 직접 대응은 추가 계측 대상이다.»', '',
         '소스의 제한 문구도 같은 범위를 명시한다. 충돌 확정이라는 제목과 직접 충돌을 세지 않았다는 본문은 강도를 맞춘다.', '',refs('scope','allocation','buffer')),
      md('## 확인된 집계 문제: 누적 회복과 새 회복이 섞인다','',
         f"hash8 → both8의 paired_contrasts.n_no_longer_isolated는 {s.num('buffer_comparison.ledger_n_no_longer_isolated')}지만 실제 이 전환의 추가 회복은 {s.num('buffer_comparison.incremental_recoveries')}이다.",'',
         '현재 계산은 도착 설정이 생산 기준보다 회복됐는지만 센다. 출발 설정에서 이미 회복된 자세도 포함한다. 결과적으로 버퍼 변경의 효과를 이 열에서 읽으면 잘못 귀속할 수 있다.', '',
         '누적 회복은 별도 열로 두고, 추가 회복은 출발에서 고립 AND 도착에서 정상인 자세를 센다. 반대 전환인 추가 악화도 함께 기록한다. 이번 버퍼 단독 대조에서 추가 환경 경로 회복이 없다는 결론은 유지된다.', '',refs('contrast')),
      md('## «버퍼 변경은 아무것도 바꾸지 않았다»의 범위','',
         f"hash8 → both8에서 최대 |ΔE|/|median(E)|는 {s.num('buffer_comparison.max_field_change')}이고, 선언한 이동 문턱은 {s.num('noise_tol')}이다.",'',
         *[f"자세 {s.num(f'buffer_comparison.changed_path_counts[{i}].pose')}의 반환 경로 수는 {s.num(f'buffer_comparison.changed_path_counts[{i}].npaths_from')} → {s.num(f'buffer_comparison.changed_path_counts[{i}].npaths_to')}다." for i in range(len(d['buffer_comparison']['changed_path_counts']))], '',
         '따라서 같은 것은 선택 자세의 회복 판정과 참조 환경 경로 회복 결과다. 작은 출력 차이를 버퍼 효과 또는 반복 변동으로 가르려면 같은 설정의 추가 반복이 필요하다. 차이를 관찰한 뒤 문턱을 올려 동등성을 선언하는 방식은 피한다.'),
      md('## «핵 자세는 다른 현상»도 아직 분류 가설이다','',
         f"전체 잔존 집합은 {s.num('core_summary.population')}자세이고 이번 진단은 그중 {s.num('core_summary.sampled')}자세를 골랐다. 환경 전용 경로가 있는 것은 {s.num('core_summary.with_env')}, 없는 것은 {s.num('core_summary.without_env')}자세다.",'',
         f"환경 경로가 있는 표본에서는 이웃 평균 대비 복소장 차이를 주로 drone+environment 클래스가 설명하며, 그 클래스가 지배적인 표본은 {s.num('core_summary.both_dominant')}개다.",'',
         '이는 클래스별 복소수 합산 관찰이다. 물리 차폐·다중경로 간섭·다른 경로의 hash 억제는 추가로 구분할 가설이다. 환경 경로 하나의 부재 여부만으로 원인이 전부 다르다고 묶기보다 잔존 자세를 분류할 근거로 쓴다.', '',refs('path_ref')),
      md('## 표본·재현 범위는 이미 얻은 결과와 분리한다','',
         f"생산 기준 재실행의 최대 정규화 오차는 {s.num('replay.max_normalized_error')}, 고립 라벨 불일치는 {s.num('replay.label_mismatches')}다. 현재 자료는 선언한 오차 문턱 안에 들어간다.",'',
         '회복 표본은 큰 cap에서 회복된 집합에서 미리 골랐다. 이 선택은 동일 자세의 개입 비교에 적합하지만 회복 확률의 무작위 표본이나 모든 장면의 성공률로 읽기 어렵다.', '',
         f"참조 경로 평가의 {s.num('reference_counts.neighbour_comparisons')}개 항목은 고유 자세 {s.num('reference_counts.unique_poses')}개의 이웃별 비교다. 이를 독립 자세 수로 세면 분모가 커진다.", '',
         '후속 자동 실행에는 라벨 일치·복소장 허용오차·설정 read-back을 하드 관문으로 두고 실패 수를 선정 시점의 분모와 함께 남긴다. 제외 후 분모만 제시하면 재현 실패가 숨는다.', '',refs('replay')),
      md('## 안테나 큐의 판정도 출력 전체를 봐야 한다','',
         '현행 큐는 조준 안테나에서 고립 자세가 계속 없으면 안테나 축이 solver 설정과 독립이라고 읽는다. 고립 개수는 문턱 판정이므로 같은 개수가 같은 복소장·스펙트럼·검출 성능을 보장하지 않는다.', '',
         '공통 자세 전체의 raw spectrum·rotor 대비·경로 클래스와 iso 대비 차이를 cap별로 평가한다. 정상 자세만 남긴 안정성과 전체 구간의 안정성을 따로 표시한다. 배경의 큰 정적 성분으로 나눈 작은 오차가 rotor 성분에는 클 수 있다.', '',
         '안테나 이득의 변화량은 cap별 aimed−iso 지표 차이를 다시 비교하고, 사전 허용오차와 반복 변동을 함께 둔다. 판정이 유지돼도 범위는 검사한 장면·패턴·설정에 붙인다.', '',refs('queue','stability')),
      md('## 다음 작업 순서','',
         '| 작업 | 우선순위와 종료 조건 |','|---|---|',
         '| 원장·계획의 문구 및 paired 비교 집계 | 먼저 수행. 완료 설정·표본 분모·누적/추가 회복을 구분하면 독자가 같은 결과를 읽는다. |',
         '| 잔존 자세의 세부 경로 | 전체 잔존 집합과 이웃·정상 대조에 한정. 클래스 차이와 경로 대응이 설명되는 지점에서 범위를 넓힐지 결정한다. |',
         '| OFDM 수신기 pilot | CPU의 독립 합성 채널부터 병행. 정확한 delay/Doppler 복원과 H0 보정이 먼저다. |',
         '| 더 큰 cap·새로운 대규모 sweep | 현재 안테나 비교와 경로 진단 결과를 읽은 뒤 필요성을 결정한다. |'),
      md('## 잔존 자세 진단의 최소 산출물','',
         '전체 드론을 유지하고 잔존 자세·앞뒤 이웃·정상 대조에서 경로 ID와 중복 수, 지연, 복소 계수, interaction, primitive, 반사점 좌표를 저장한다. 같은 설정 반복으로 작은 차이의 범위를 먼저 얻는다.', '',
         '환경 전용·드론 전용·혼합 경로를 나눠 복소장 차이의 잔차를 계산한 뒤, 큰 차이에 기여한 경로의 차폐와 경계 통과를 검사한다. 복소장 합산이 닫히는 것은 원인 입증과 구분한다.', '',
         '현행 기본 실행은 선택 경로 설명과 클래스 집계를 보관했다. keep_paths 경로에도 전체 vertices 배열의 저장 여부를 확인해 필요한 필드를 보강해야 한다. GPU 진단은 공유 카드의 메모리 여유를 별도로 확보한 소규모 작업으로 편성한다.', '',refs('save')),
      md('## OFDM pilot의 채널 가정을 명시한다','',
         '첫 단계는 알려진 합성 delay/Doppler 채널과 변하는 payload로 수신기를 점검한다. 사용 RE와 null RE를 구분하고 QPSK·QAM의 에너지 정규화, division·regularization의 잡음 효과를 비교한다.', '',
         'H0 보정 데이터와 평가 H0/H1을 분리한다. 같은 관측시간·송신 에너지·잡음 조건에서 실제 Pfa·Pd·delay/Doppler 오차를 보고하며 truth는 신호 주입과 사후 점수에만 쓴다.', '',
         '현재 합산 E(t)를 OFDM에 곱하면 flat-fading 가정을 둔 pilot이 된다. 거리 분해·주파수 선택성·파형 간 비교로 확장하려면 경로별 지연과 복소 계수, 시간 변화가 포함된 채널이 필요하다. 이 pilot을 완전한 Wi-Fi/LTE/NR 또는 실제 RF 검증으로 소개하지 않는다.', '',refs('pilot')),
      next_steps([('누적/추가 회복과 결론 범위를 원 생성기에 반영한다','버퍼·hash의 효과를 같은 분모로 해석한다','진단 builder와 원장'),
       ('잔존 집합의 경로별 자료와 같은 설정 반복을 확보한다','혼합 경로 변화와 반복 변동·가시성을 가른다','소규모 GPU 진단'),
       ('합성 OFDM 수신기 pilot을 병행한다','신호 처리 오류를 장면 모델 오류와 분리한다','CPU 수신기 시험'),
       ('안테나 큐 완료 뒤 raw 지표의 교차 효과를 읽는다','패턴 효과의 적용 범위를 정한다','기존 실행 큐 결과')])]
    build_notebook(str(NB),blocks,strict=True)


if __name__=='__main__':
    os.chdir(ROOT);d=collect();build(d)
    print(json.dumps({'report':str(NB),'checks':d['checks'],'buffer_comparison':d['buffer_comparison'],'core_summary':d['core_summary']},ensure_ascii=False))
